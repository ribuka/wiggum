"""Ralph loop orchestration: task selection, agent execution, and Git commits."""

from __future__ import annotations

import subprocess
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from wiggum.config import ConfigurationError, RalphPaths, load_configuration
from wiggum.defaults import DEFAULT_MAX_LOOPS, DEFAULT_REASONING_EFFORT
from wiggum.env.process_environment import (
    build_process_environment as build_codex_environment,
)
from wiggum.exit_codes import ExitCode
from wiggum.git_ops import (
    commit_count,
    commit_loop_changes,
    has_worktree_changes,
    require_clean_worktree,
    require_git_output,
)
from wiggum.ledger.protocol import classify_output, validate_selected_task
from wiggum.ledger.task_ledger import read_task_contract, task_snapshot
from wiggum.logging.loop_log import create_running_log, finalize_log
from wiggum.providers import CommandOptions, get_adapter, validate_provider_options
from wiggum.providers.usage.token_usage import TokenUsage
from wiggum.runner.prompt import default_prompt_text, prompt_for_selected_task
from wiggum.runner.validation import (
    validate_git_preconditions,
    validate_run_arguments,
    validate_run_options,
)
from wiggum.tool_output_monitor import read_tool_output_monitor


def _run(
    repo: Path,
    prompt_path: Path | None,
    max_loops: int,
    provider: str,
    executable: str,
    model: str | None,
    reasoning_effort: str,
    model_verbosity: str,
    tool_output_token_limit: int,
    lean: bool,
    auto_approve: bool,
    dry_run: bool,
    api_retry_count: int | None,
    api_retry_interval_sec: int,
    agent_timeout_sec: int,
    paths: RalphPaths,
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
        Maximum number of agent processes to start.
    provider : str
        Selected AI model vendor; one of :data:`wiggum.providers.PROVIDERS`.
    executable : str
        Provider CLI executable name or path.
    model : str | None
        Optional model override.
    reasoning_effort : str
        Reasoning effort for each loop. For the ``codex`` and ``copilot``
        providers, support for a given level depends on the selected model,
        not the provider; the provider CLI rejects an unsupported
        combination itself. Claude Code CLI's ``--effort`` flag accepts a
        fixed, provider-level set of values
        (:data:`wiggum.providers.constants.CLAUDE_REASONING_EFFORTS`)
        regardless of model; a value outside that set is rejected for the
        ``claude`` provider.
    model_verbosity : str
        Codex model verbosity for each loop. Codex-only; must be left at its
        default value for the ``copilot`` and ``claude`` providers.
    tool_output_token_limit : int
        Maximum tokens retained from one tool output in model history.
        Codex-only; must be left at its default value for the ``copilot``
        and ``claude`` providers.
    lean : bool
        Whether to ignore user Codex configuration and reasoning summaries.
        Codex-only; must be ``False`` for the ``copilot`` and ``claude``
        providers.
    auto_approve : bool
        Automatically approve agent requests instead of requiring
        interactive confirmation. Required for the ``copilot`` and ``claude``
        providers.
    dry_run : bool
        Validate inputs and print the command without invoking the agent.
    api_retry_count : int | None
        Number of additional attempts after an agent API or protocol
        failure. ``None`` disables retries.
    api_retry_interval_sec : int
        Seconds to wait between agent API retry attempts.
    agent_timeout_sec : int
        Maximum time to wait for each agent child process.
    paths : RalphPaths
        Resolved Ralph file paths.
    logs_dir : Path
        Directory that stores loop logs.
    temp_dir : Path
        Directory used for loop-scoped temporary files.
    uv_cache_dir : Path
        Directory used for ``UV_CACHE_DIR`` when ``manage_process_env`` is
        enabled.
    manage_process_env : bool
        Whether to inject ``UV_CACHE_DIR``, ``TMP``, and ``TEMP`` into the
        agent child process environment.

    Returns
    -------
    ExitCode
        Runner outcome.
    """
    repo = repo.resolve()
    argument_error = validate_run_arguments(
        prompt_path=prompt_path,
        paths=paths,
    )
    if argument_error is not None:
        logger.error("{}", argument_error)
        return ExitCode.PREFLIGHT_ERROR
    adapter = get_adapter(provider)
    resolved_executable = adapter.resolve_executable(executable)
    if resolved_executable is None:
        logger.error("{} executable not found: {}", provider.capitalize(), executable)
        return ExitCode.PREFLIGHT_ERROR

    git_precondition_error = validate_git_preconditions(repo)
    if git_precondition_error is not None:
        logger.error("{}", git_precondition_error)
        return ExitCode.PREFLIGHT_ERROR

    prompt = (
        prompt_path.read_text(encoding="utf-8")
        if prompt_path is not None
        else default_prompt_text(paths, repo)
    )
    temp_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    try:
        incomplete_tasks, total_tasks, selected_task_id = task_snapshot(paths.tasks)
        selected_task_contract = (
            None
            if selected_task_id is None
            else read_task_contract(paths.tasks, selected_task_id)
        )
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

    run_usage = TokenUsage()
    for loop_number in range(1, max_loops + 1):
        if loop_number > 1:
            try:
                incomplete_tasks, _, selected_task_id = task_snapshot(paths.tasks)
                selected_task_contract = (
                    None
                    if selected_task_id is None
                    else read_task_contract(paths.tasks, selected_task_id)
                )
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
        command = adapter.build_command(
            CommandOptions(
                executable=resolved_executable,
                repo=repo,
                output_path=output_path,
                model=model,
                auto_approve=auto_approve,
                reasoning_effort=reasoning_effort,
                model_verbosity=model_verbosity,
                tool_output_token_limit=tool_output_token_limit,
                lean=lean,
            )
        )
        if selected_task_contract is None:
            raise AssertionError("a selected task must have a task contract")
        codex_prompt = prompt_for_selected_task(
            prompt,
            selected_task_id,
            selected_task_contract,
            paths,
            repo,
        )
        temporary_log_path = create_running_log(logs_dir, started_at, selected_task_id)
        if selected_task_id is not None:
            logger.info("Ralph task {} started", selected_task_id)
        if dry_run:
            print(subprocess.list2cmdline(command))
            print(codex_prompt)
            output_path.unlink(missing_ok=True)
            temporary_log_path.unlink(missing_ok=True)
            return ExitCode.SUCCESS

        retry_count = 0 if api_retry_count is None else api_retry_count
        task_usage = TokenUsage()
        for api_attempt in range(1, retry_count + 2):
            attempt_succeeded = False
            try:
                completed = adapter.run(
                    command,
                    repo,
                    temporary_log_path,
                    codex_environment,
                    codex_prompt,
                    output_path,
                    agent_timeout_sec,
                )
                if completed.returncode != 0:
                    failure = f"{provider.capitalize()} exited with code {completed.returncode}"
                    exit_code = ExitCode.CODEX_FAILURE
                    retryable = adapter.is_retryable_failure(temporary_log_path)
                else:
                    message = output_path.read_text(encoding="utf-8")
                    status, task_id = classify_output(message)
                    validate_selected_task(status, task_id, selected_task_id)
                    attempt_succeeded = True
            except subprocess.TimeoutExpired:
                failure = f"{provider.capitalize()} timed out after {agent_timeout_sec} seconds"
                exit_code = ExitCode.CODEX_FAILURE
                retryable = True
            except (OSError, UnicodeError, ValueError) as error:
                failure = str(error)
                exit_code = ExitCode.PROTOCOL_ERROR
                retryable = False

            attempt_usage = adapter.read_usage(temporary_log_path)
            output_monitor = read_tool_output_monitor(temporary_log_path)
            task_usage += attempt_usage
            run_usage += attempt_usage
            logger.info(
                "Token usage {} attempt {}: input={}, cached={}, output={}, "
                "reasoning={}, task-total={}, run-total={}",
                selected_task_id,
                api_attempt,
                attempt_usage.input_tokens,
                attempt_usage.cached_input_tokens,
                attempt_usage.output_tokens,
                attempt_usage.reasoning_output_tokens,
                task_usage.total_tokens,
                run_usage.total_tokens,
            )
            if output_monitor.outputs:
                logger.info(
                    "Tool output monitor {} attempt {}: outputs={}, truncated={}, limit={}",
                    selected_task_id,
                    api_attempt,
                    output_monitor.outputs,
                    output_monitor.truncated_outputs,
                    tool_output_token_limit,
                )
            if output_monitor.truncated_outputs:
                logger.warning(
                    "Tool output limit reached for {} attempt {}: {}/{} outputs were truncated "
                    "at a {}-token limit",
                    selected_task_id,
                    api_attempt,
                    output_monitor.truncated_outputs,
                    output_monitor.outputs,
                    tool_output_token_limit,
                )
            if attempt_succeeded:
                break

            if not retryable or api_attempt > retry_count:
                log_path = finalize_log(
                    temporary_log_path,
                    logs_dir,
                    started_at,
                    selected_task_id,
                    f"{provider}-failure" if exit_code == ExitCode.CODEX_FAILURE else "protocol-error",
                )
                logger.error("{}; see {}", failure, log_path.relative_to(repo))
                output_path.unlink(missing_ok=True)
                return exit_code

            logger.warning(
                "{} retry attempt {}/{} failed ({}); retrying in {} seconds",
                provider.capitalize(),
                api_attempt,
                retry_count + 1,
                failure,
                api_retry_interval_sec,
            )
            output_path.unlink(missing_ok=True)
            time.sleep(api_retry_interval_sec)
        else:
            raise AssertionError("agent retry loop must return or succeed")

        output_path.unlink(missing_ok=True)

        try:
            after_agent = require_git_output(repo, "rev-parse", "HEAD")
            agent_commits = commit_count(repo, before, after_agent)
            if agent_commits != 0:
                raise RuntimeError(
                    f"{provider.capitalize()} created {agent_commits} commits; "
                    "the runner owns loop commits"
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
                incomplete_tasks, _, next_task_id = task_snapshot(paths.tasks)
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
    provider: str,
    model: str | None = None,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    max_loops: int = DEFAULT_MAX_LOOPS,
    auto_approve: bool = False,
    dry_run: bool = False,
) -> ExitCode:
    """Run Ralph with one pair of runner lifecycle log messages.

    Every tunable other than the run-to-run choices below is read from the
    target repository's ``wiggum/config.toml``; see :mod:`wiggum.config.dirs`
    and :mod:`wiggum.config.run` for their schema and defaults.

    Parameters
    ----------
    repo : Path
        Git repository to modify.
    provider : str
        Selected AI model vendor; one of :data:`wiggum.providers.PROVIDERS`.
        No default; the caller must choose explicitly.
    model : str | None, default None
        Optional model override.
    reasoning_effort : str, default "medium"
        Reasoning effort for each loop. For the ``codex`` and ``copilot``
        providers, support for a given level depends on the selected model,
        not the provider; the provider CLI rejects an unsupported
        combination itself. Claude Code CLI's ``--effort`` flag accepts a
        fixed, provider-level set of values
        (:data:`wiggum.providers.constants.CLAUDE_REASONING_EFFORTS`)
        regardless of model; a value outside that set is rejected for the
        ``claude`` provider.
    max_loops : int, default 20
        Maximum number of agent processes to start.
    auto_approve : bool, default False
        Automatically approve agent requests instead of requiring
        interactive confirmation. Required for the ``copilot`` and ``claude``
        providers.
    dry_run : bool, default False
        Validate inputs and print the command without invoking the agent.

    Returns
    -------
    ExitCode
        Runner outcome.
    """
    repo = Path(repo).resolve()
    logger.info("Ralph runner start")
    try:
        option_error = validate_run_options(max_loops=max_loops, reasoning_effort=reasoning_effort)
        if option_error is not None:
            logger.error("{}", option_error)
            return ExitCode.PREFLIGHT_ERROR
        try:
            configuration = load_configuration(repo)
        except ConfigurationError as error:
            logger.error("{}", error)
            return ExitCode.PREFLIGHT_ERROR
        run_settings = configuration.run
        provider_error = validate_provider_options(
            provider,
            reasoning_effort=reasoning_effort,
            model_verbosity=run_settings.codex.model_verbosity,
            tool_output_token_limit=run_settings.codex.tool_output_token_limit,
            lean=run_settings.codex.lean,
            auto_approve=auto_approve,
        )
        if provider_error is not None:
            logger.error("{}", provider_error)
            return ExitCode.PREFLIGHT_ERROR
        return _run(
            repo=repo,
            prompt_path=configuration.paths.prompt_file,
            max_loops=max_loops,
            provider=provider,
            executable=run_settings.executables[provider],
            model=model,
            reasoning_effort=reasoning_effort,
            model_verbosity=run_settings.codex.model_verbosity,
            tool_output_token_limit=run_settings.codex.tool_output_token_limit,
            lean=run_settings.codex.lean,
            auto_approve=auto_approve,
            dry_run=dry_run,
            api_retry_count=run_settings.api_retry_count,
            api_retry_interval_sec=run_settings.api_retry_interval_sec,
            agent_timeout_sec=run_settings.agent_timeout_sec,
            paths=configuration.paths,
            logs_dir=configuration.dirs.log,
            temp_dir=configuration.dirs.temp,
            uv_cache_dir=configuration.dirs.uv_cache,
            manage_process_env=run_settings.manage_process_env,
        )
    finally:
        logger.info("Ralph runner end")
