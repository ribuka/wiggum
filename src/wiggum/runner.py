"""Ralph loop orchestration: task selection, Codex execution, and Git commits."""

from __future__ import annotations

import subprocess
import tempfile
import time
from datetime import UTC, datetime
from importlib import resources
from pathlib import Path

from loguru import logger

from wiggum.codex_process import (
    build_codex_command,
    build_codex_environment,
    is_retryable_codex_failure,
    resolve_codex_executable,
    run_codex,
)
from wiggum.defaults import (
    DEFAULT_API_RETRY_COUNT,
    DEFAULT_API_RETRY_INTERVAL_SEC,
    DEFAULT_CODEX_TIMEOUT_SEC,
    DEFAULT_MAX_LOOPS,
)
from wiggum.exit_codes import ExitCode
from wiggum.git_ops import (
    commit_count,
    commit_loop_changes,
    has_worktree_changes,
    require_clean_worktree,
    require_git_output,
)
from wiggum.loop_log import create_running_log, finalize_log
from wiggum.protocol import classify_output, validate_selected_task
from wiggum.task_ledger import task_snapshot


def _default_prompt_text() -> str:
    """Return wiggum's bundled Ralph rules and loop prompt.

    Returns
    -------
    str
        UTF-8 text of the packaged general rules followed by the loop prompt.
    """
    templates_root = resources.files("wiggum") / "templates"
    general_rules = (templates_root / "RALPH.md").read_text(encoding="utf-8")
    loop_prompt = (templates_root / "ralph_prompt.md").read_text(encoding="utf-8")
    return f"{general_rules.rstrip()}\n\n{loop_prompt}"


def _prompt_for_selected_task(prompt: str, selected_task_id: str) -> str:
    """Append the runner-selected task contract to a Codex prompt.

    Parameters
    ----------
    prompt : str
        Base prompt containing the general Ralph loop instructions.
    selected_task_id : str
        Task identifier selected from the ledger by the parent runner.

    Returns
    -------
    str
        Prompt that names the only task the Codex child may process.
    """
    return (
        f"{prompt.rstrip()}\n\n"
        "## Runner-selected task\n\n"
        f"The parent runner selected `{selected_task_id}` for this loop. Work only on "
        "that task; do not select or start another task. If the task ledger differs "
        "from this selection or prevents work, preserve existing changes and report "
        f"`TASK_BLOCKED: {selected_task_id}`. In every outcome, the final non-empty "
        f"line must use `{selected_task_id}`.\n"
    )


def _run(
    repo: Path,
    prompt_path: Path | None,
    max_loops: int,
    codex_executable: str,
    model: str | None,
    auto_approve: bool,
    dry_run: bool,
    api_retry_count: int | None,
    api_retry_interval_sec: int,
    codex_timeout_sec: int,
    tasks_path: Path,
    logs_dir: Path,
    temp_dir: Path,
    uv_cache_dir: Path,
    manage_process_env: bool,
) -> ExitCode:
    """Run Ralph loops until a terminal status or safety limit is reached.

    Parameters
    ----------
    repo : Path
        Git repository to modify.
    prompt_path : Path | None
        UTF-8 prompt file used for every loop, or ``None`` to use wiggum's
        bundled default prompt.
    max_loops : int
        Maximum number of Codex processes to start.
    codex_executable : str
        Codex executable name or path.
    model : str | None
        Optional model override.
    auto_approve : bool
        Automatically approve Codex requests in the workspace-write sandbox.
    dry_run : bool
        Validate inputs and print the command without invoking Codex.
    api_retry_count : int | None
        Number of additional attempts after a Codex API or protocol failure.
        ``None`` disables retries.
    api_retry_interval_sec : int
        Seconds to wait between Codex API retry attempts.
    codex_timeout_sec : int
        Maximum time to wait for each Codex child process.
    tasks_path : Path
        Ralph task ledger file.
    logs_dir : Path
        Directory that stores loop logs.
    temp_dir : Path
        Directory used for loop-scoped temporary files.
    uv_cache_dir : Path
        Directory used for ``UV_CACHE_DIR`` when ``manage_process_env`` is
        enabled.
    manage_process_env : bool
        Whether to inject ``UV_CACHE_DIR``, ``TMP``, and ``TEMP`` into the
        Codex child process environment.

    Returns
    -------
    ExitCode
        Runner outcome.
    """
    repo = repo.resolve()
    if max_loops < 1:
        logger.error("--max-loops must be at least 1")
        return ExitCode.PREFLIGHT_ERROR
    if api_retry_count is not None and api_retry_count < 0:
        logger.error("--api-retry-count must be at least 0")
        return ExitCode.PREFLIGHT_ERROR
    if api_retry_interval_sec < 0:
        logger.error("--api-retry-interval-sec must be at least 0")
        return ExitCode.PREFLIGHT_ERROR
    if codex_timeout_sec < 1:
        logger.error("--codex-timeout-sec must be at least 1")
        return ExitCode.PREFLIGHT_ERROR
    if prompt_path is not None and not prompt_path.is_file():
        logger.error("Prompt file does not exist: {}", prompt_path)
        return ExitCode.PREFLIGHT_ERROR
    resolved_codex_executable = resolve_codex_executable(codex_executable)
    if resolved_codex_executable is None:
        logger.error("Codex executable not found: {}", codex_executable)
        return ExitCode.PREFLIGHT_ERROR

    try:
        top_level = Path(require_git_output(repo, "rev-parse", "--show-toplevel")).resolve()
        if top_level != repo:
            raise RuntimeError(f"--repo must be the Git root: {top_level}")
        require_clean_worktree(repo)
    except RuntimeError as error:
        logger.error("{}", error)
        return ExitCode.PREFLIGHT_ERROR

    prompt = (
        prompt_path.read_text(encoding="utf-8")
        if prompt_path is not None
        else _default_prompt_text()
    )
    temp_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    try:
        incomplete_tasks, total_tasks, selected_task_id = task_snapshot(tasks_path)
    except (OSError, UnicodeError, ValueError) as error:
        logger.error("{}", error)
        return ExitCode.PREFLIGHT_ERROR
    logger.info("Incompleted tasks: {} / All tasks: {}", incomplete_tasks, total_tasks)
    logger.info("Total loops: {}", max_loops)
    if incomplete_tasks == 0:
        logger.success("All Ralph tasks are complete")
        return ExitCode.SUCCESS
    if selected_task_id is None:
        logger.warning("Stopped because no incomplete Ralph task is eligible")
        return ExitCode.TASK_BLOCKED

    for loop_number in range(1, max_loops + 1):
        if loop_number > 1:
            try:
                incomplete_tasks, _, selected_task_id = task_snapshot(tasks_path)
            except (OSError, UnicodeError, ValueError) as error:
                logger.error("{}", error)
                return ExitCode.PREFLIGHT_ERROR
            if incomplete_tasks == 0:
                logger.success("All Ralph tasks are complete")
                return ExitCode.SUCCESS
            if selected_task_id is None:
                logger.warning("Stopped because no incomplete Ralph task is eligible")
                return ExitCode.TASK_BLOCKED
        logger.info("Ralph loop start ({})", loop_number)
        before = require_git_output(repo, "rev-parse", "HEAD")
        started_at = datetime.now(tz=UTC).astimezone()
        codex_environment = build_codex_environment(
            temp_dir,
            uv_cache_dir=uv_cache_dir,
            manage_process_env=manage_process_env,
        )
        with tempfile.NamedTemporaryFile(
            dir=temp_dir,
            prefix="ralph-last-message-",
            suffix=".txt",
            delete=False,
        ) as output_file:
            output_path = Path(output_file.name)

        if selected_task_id is None:
            raise AssertionError("an eligible task must be selected before starting Codex")
        command = build_codex_command(
            resolved_codex_executable,
            repo,
            output_path,
            _prompt_for_selected_task(prompt, selected_task_id),
            model,
            auto_approve,
        )
        temporary_log_path = create_running_log(logs_dir, started_at, selected_task_id)
        if selected_task_id is not None:
            logger.info("Ralph task {} started", selected_task_id)
        if dry_run:
            print(subprocess.list2cmdline(command))
            output_path.unlink(missing_ok=True)
            temporary_log_path.unlink(missing_ok=True)
            return ExitCode.SUCCESS

        retry_count = 0 if api_retry_count is None else api_retry_count
        for api_attempt in range(1, retry_count + 2):
            try:
                completed = run_codex(
                    command,
                    repo,
                    temporary_log_path,
                    codex_environment,
                    codex_timeout_sec,
                )
                if completed.returncode != 0:
                    failure = f"Codex exited with code {completed.returncode}"
                    exit_code = ExitCode.CODEX_FAILURE
                    retryable = is_retryable_codex_failure(temporary_log_path)
                else:
                    message = output_path.read_text(encoding="utf-8")
                    status, task_id = classify_output(message)
                    validate_selected_task(status, task_id, selected_task_id)
                    break
            except subprocess.TimeoutExpired:
                failure = f"Codex timed out after {codex_timeout_sec} seconds"
                exit_code = ExitCode.CODEX_FAILURE
                retryable = True
            except (OSError, UnicodeError, ValueError) as error:
                failure = str(error)
                exit_code = ExitCode.PROTOCOL_ERROR
                retryable = False

            if not retryable or api_attempt > retry_count:
                log_path = finalize_log(
                    temporary_log_path,
                    logs_dir,
                    started_at,
                    selected_task_id,
                    "codex-failure" if exit_code == ExitCode.CODEX_FAILURE else "protocol-error",
                )
                logger.error("{}; see {}", failure, log_path.relative_to(repo))
                output_path.unlink(missing_ok=True)
                return exit_code

            logger.warning(
                "Codex retry attempt {}/{} failed ({}); retrying in {} seconds",
                api_attempt,
                retry_count + 1,
                failure,
                api_retry_interval_sec,
            )
            output_path.unlink(missing_ok=True)
            time.sleep(api_retry_interval_sec)
        else:
            raise AssertionError("Codex retry loop must return or succeed")

        output_path.unlink(missing_ok=True)

        try:
            after_agent = require_git_output(repo, "rev-parse", "HEAD")
            agent_commits = commit_count(repo, before, after_agent)
            if agent_commits != 0:
                raise RuntimeError(
                    f"Codex created {agent_commits} commits; the runner owns loop commits"
                )
            has_changes = status == "completed" or has_worktree_changes(repo)
            if has_changes:
                commit_loop_changes(repo, task_id, status)
            require_clean_worktree(repo)
            after = require_git_output(repo, "rev-parse", "HEAD")
            new_commits = commit_count(repo, before, after)
        except RuntimeError as error:
            log_path = finalize_log(temporary_log_path, logs_dir, started_at, task_id, "git-error")
            logger.error("{}; see {}", error, log_path.relative_to(repo))
            return ExitCode.GIT_STATE_ERROR

        if status == "completed":
            if new_commits != 1:
                log_path = finalize_log(
                    temporary_log_path,
                    logs_dir,
                    started_at,
                    task_id,
                    "git-error",
                )
                logger.error(
                    "{} reported completion but created {} commits; see {}",
                    task_id,
                    new_commits,
                    log_path.relative_to(repo),
                )
                return ExitCode.GIT_STATE_ERROR
            log_path = finalize_log(temporary_log_path, logs_dir, started_at, task_id, status)
            try:
                incomplete_tasks, _, next_task_id = task_snapshot(tasks_path)
            except (OSError, UnicodeError, ValueError) as error:
                logger.error("{}", error)
                return ExitCode.PREFLIGHT_ERROR
            if incomplete_tasks == 0:
                logger.success("Completed {} ({})", task_id, log_path.relative_to(repo))
                logger.success("All Ralph tasks are complete")
                return ExitCode.SUCCESS
            if next_task_id is None:
                logger.success("Completed {} ({})", task_id, log_path.relative_to(repo))
                logger.warning("Stopped because no incomplete Ralph task is eligible")
                return ExitCode.TASK_BLOCKED
            logger.success(
                "Completed {}; starting the next loop ({})",
                task_id,
                log_path.relative_to(repo),
            )
            continue

        expected_commits = 1 if has_changes else 0
        if new_commits != expected_commits:
            log_path = finalize_log(temporary_log_path, logs_dir, started_at, task_id, "git-error")
            logger.error(
                "Terminal loop created {} commits, expected {}; see {}",
                new_commits,
                expected_commits,
                log_path.relative_to(repo),
            )
            return ExitCode.GIT_STATE_ERROR
        if status == "incompleted":
            finalize_log(temporary_log_path, logs_dir, started_at, task_id, status)
            logger.warning("Stopped because {} is incomplete", task_id)
            return ExitCode.TASK_INCOMPLETE

        finalize_log(temporary_log_path, logs_dir, started_at, task_id, status)
        logger.warning("Stopped because {} is blocked", task_id)
        return ExitCode.TASK_BLOCKED

    logger.warning("Stopped after reaching the {}-loop limit", max_loops)
    return ExitCode.MAX_LOOPS_REACHED


def run(
    repo: Path,
    prompt_path: Path | None = None,
    max_loops: int = DEFAULT_MAX_LOOPS,
    codex_executable: str = "codex",
    model: str | None = None,
    auto_approve: bool = False,
    dry_run: bool = False,
    api_retry_count: int | None = DEFAULT_API_RETRY_COUNT,
    api_retry_interval_sec: int = DEFAULT_API_RETRY_INTERVAL_SEC,
    codex_timeout_sec: int = DEFAULT_CODEX_TIMEOUT_SEC,
    tasks_path: Path | None = None,
    logs_dir: Path | None = None,
    temp_dir: Path | None = None,
    uv_cache_dir: Path | None = None,
    manage_process_env: bool = True,
) -> ExitCode:
    """Run Ralph with one pair of runner lifecycle log messages.

    Parameters
    ----------
    repo : Path
        Git repository to modify.
    prompt_path : Path | None, default None
        UTF-8 prompt file used for every loop. Defaults to wiggum's bundled
        Ralph loop prompt when omitted.
    max_loops : int, default 20
        Maximum number of Codex processes to start.
    codex_executable : str, default "codex"
        Codex executable name or path.
    model : str | None, default None
        Optional model override.
    auto_approve : bool, default False
        Automatically approve Codex requests in the workspace-write sandbox.
    dry_run : bool, default False
        Validate inputs and print the command without invoking Codex.
    api_retry_count : int | None, default None
        Number of additional attempts after a Codex API or protocol failure.
        ``None`` disables retries.
    api_retry_interval_sec : int, default 5
        Seconds to wait between Codex API retry attempts.
    codex_timeout_sec : int, default 1800
        Maximum time to wait for each Codex child process.
    tasks_path : Path | None, default None
        Ralph task ledger file. Defaults to ``<repo>/TASKS.md``.
    logs_dir : Path | None, default None
        Directory that stores loop logs. Defaults to ``<repo>/logs``.
    temp_dir : Path | None, default None
        Directory used for loop-scoped temporary files. Defaults to
        ``<repo>/tmp``.
    uv_cache_dir : Path | None, default None
        Directory used for ``UV_CACHE_DIR``. Defaults to ``<repo>/.uv-cache``.
    manage_process_env : bool, default True
        Whether to inject ``UV_CACHE_DIR``, ``TMP``, and ``TEMP`` into the
        Codex child process environment.

    Returns
    -------
    ExitCode
        Runner outcome.
    """
    repo = Path(repo)
    logger.info("Ralph runner start")
    try:
        return _run(
            repo=repo,
            prompt_path=prompt_path,
            max_loops=max_loops,
            codex_executable=codex_executable,
            model=model,
            auto_approve=auto_approve,
            dry_run=dry_run,
            api_retry_count=api_retry_count,
            api_retry_interval_sec=api_retry_interval_sec,
            codex_timeout_sec=codex_timeout_sec,
            tasks_path=tasks_path if tasks_path is not None else repo / "TASKS.md",
            logs_dir=logs_dir if logs_dir is not None else repo / "logs",
            temp_dir=temp_dir if temp_dir is not None else repo / "tmp",
            uv_cache_dir=uv_cache_dir if uv_cache_dir is not None else repo / ".uv-cache",
            manage_process_env=manage_process_env,
        )
    finally:
        logger.info("Ralph runner end")
