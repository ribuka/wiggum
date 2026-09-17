"""Tests for Ralph loop orchestration."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import wiggum.providers.codex as codex_provider_module
import wiggum.providers.copilot as copilot_provider_module
import wiggum.runner as runner_module
from wiggum.exit_codes import ExitCode
from wiggum.runner import run


@pytest.fixture(autouse=True)
def _write_project_configuration(tmp_path: Path) -> None:
    """Provide the required project configuration for runner tests."""
    (tmp_path / "RALPH_PROJECT.md").write_text("project instructions\n", encoding="utf-8")


def _write_tasks(tasks_path: Path, body: str) -> None:
    """Write a Ralph task ledger.

    Parameters
    ----------
    tasks_path : Path
        Destination ``TASKS.md`` file.
    body : str
        Markdown content of the ledger.
    """
    tasks_path.write_text(body, encoding="utf-8")


def _fake_git_output_factory(repo: Path, head: str = "before"):
    """Build a fake ``require_git_output`` for preflight-only Git calls.

    Parameters
    ----------
    repo : Path
        Repository path expected to be treated as the Git root.
    head : str, default "before"
        Value returned for ``rev-parse HEAD``.

    Returns
    -------
    Callable[[Path, *str], str]
        Replacement for ``require_git_output``.
    """

    def fake(target_repo: Path, *args: str) -> str:
        if args == ("rev-parse", "--show-toplevel"):
            return str(target_repo)
        if args == ("rev-parse", "HEAD"):
            return head
        raise AssertionError(args)

    return fake


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_loops": 0}, "--max-loops must be at least 1"),
        ({"api_retry_count": -1}, "--api-retry-count must be at least 0"),
        ({"api_retry_interval_sec": -1}, "--api-retry-interval-sec must be at least 0"),
        ({"codex_timeout_sec": 0}, "--codex-timeout-sec must be at least 1"),
        (
            {"tool_output_token_limit": 0},
            "--tool-output-token-limit must be at least 1",
        ),
    ],
)
def test_run_rejects_invalid_numeric_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kwargs: dict[str, int],
    message: str,
) -> None:
    """Reject out-of-range numeric options before touching Git or Codex."""
    messages: list[str] = []
    monkeypatch.setattr(
        runner_module.logger,
        "error",
        lambda entry, *args: messages.append(entry.format(*args)),
    )

    result = run(repo=tmp_path, prompt_path=None, **kwargs)

    assert result == ExitCode.PREFLIGHT_ERROR
    assert any(message in entry for entry in messages)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"reasoning_effort": "extreme"},
            "--reasoning-effort has an unsupported value: extreme",
        ),
        (
            {"model_verbosity": "verbose"},
            "--model-verbosity has an unsupported value: verbose",
        ),
    ],
)
def test_run_rejects_invalid_model_controls(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    kwargs: dict[str, str],
    message: str,
) -> None:
    """Reject unsupported model controls before touching Git or Codex."""
    messages: list[str] = []
    monkeypatch.setattr(
        runner_module.logger,
        "error",
        lambda entry, *args: messages.append(entry.format(*args)),
    )

    result = run(repo=tmp_path, **kwargs)

    assert result == ExitCode.PREFLIGHT_ERROR
    assert message in messages


def test_run_rejects_a_missing_prompt_file(tmp_path: Path) -> None:
    """Reject a --prompt-file path that does not exist."""
    result = run(repo=tmp_path, prompt_path=tmp_path / "missing-prompt.md")

    assert result == ExitCode.PREFLIGHT_ERROR


@pytest.mark.parametrize("required_name", ["TASKS.md", "RALPH_PROJECT.md"])
def test_run_rejects_a_missing_required_file_before_starting_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    required_name: str,
) -> None:
    """Reject an absent project file before resolving Codex or Git."""
    (tmp_path / required_name).unlink(missing_ok=True)
    if required_name == "RALPH_PROJECT.md":
        (tmp_path / "TASKS.md").write_text("contents\n", encoding="utf-8")
    monkeypatch.setattr(
        codex_provider_module,
        "resolve_codex_executable",
        lambda value: pytest.fail("Codex must not be resolved"),
    )
    monkeypatch.setattr(
        runner_module,
        "require_git_output",
        lambda *args: pytest.fail("Git must not be invoked"),
    )

    result = run(repo=tmp_path)

    assert result == ExitCode.PREFLIGHT_ERROR


def test_run_rejects_an_unresolvable_codex_executable(tmp_path: Path) -> None:
    """Reject a Codex executable name that cannot be resolved."""
    result = run(repo=tmp_path, codex_executable="no-such-codex-executable-xyz")

    assert result == ExitCode.PREFLIGHT_ERROR


def test_run_uses_the_bundled_default_prompt_when_prompt_path_is_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Fall back to wiggum's packaged Ralph loop prompt by default."""
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-001: only task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )
    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", _fake_git_output_factory(tmp_path))
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)

    result = run(repo=tmp_path, prompt_path=None, dry_run=True)

    assert result == ExitCode.SUCCESS
    printed_command = capsys.readouterr().out
    assert printed_command.splitlines()[0].endswith(" -")
    assert "# Ralph Loop Rules" in printed_command
    assert "Run one Ralph loop." in printed_command
    assert "The parent runner selected `TASK-001`" in printed_command
    assert "## TASK-001: only task" in printed_command


def test_default_prompt_uses_bundled_rules_without_an_external_ralph_file() -> None:
    """Use package-owned general rules instead of a repository RALPH.md file."""
    prompt = runner_module._default_prompt_text()

    assert "# Ralph Loop Rules" in prompt
    assert "replace any external `RALPH.md`" in prompt
    assert "Read `RALPH_PROJECT.md` first" in prompt
    assert "run that documented command directly" in prompt
    assert "request escalation for that command" in prompt


def test_run_logs_runner_progress_loop_and_selected_task_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Log the agreed lifecycle and selected task before a dry-run command."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-001: completed

- Status: completed
- Priority: 1
- Depends on: none

## TASK-002: next

- Status: pending
- Priority: 2
- Depends on: TASK-001
""",
    )
    messages: list[str] = []

    def record_info(message: str, *args: object) -> None:
        messages.append(message.format(*args))

    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", _fake_git_output_factory(tmp_path))
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(runner_module.logger, "info", record_info)

    result = run(repo=tmp_path, prompt_path=prompt_path, max_loops=3, dry_run=True)

    assert result == ExitCode.SUCCESS
    assert messages == [
        "Ralph runner start",
        "Incompleted tasks: 1 / All tasks: 2",
        "Total loops: 3",
        "Ralph loop start (1)",
        "Ralph task TASK-002 started",
        "Ralph runner end",
    ]


def test_run_does_not_start_codex_when_all_tasks_are_already_complete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Return success without starting a loop for an already-complete ledger."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-001: completed

- Status: completed
- Priority: 1
- Depends on: none
""",
    )
    success_messages: list[str] = []

    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", _fake_git_output_factory(tmp_path))
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(
        codex_provider_module,
        "run_codex",
        lambda *args, **kwargs: pytest.fail("Codex must not be started"),
    )
    monkeypatch.setattr(
        runner_module.logger,
        "success",
        lambda message, *args: success_messages.append(message.format(*args)),
    )

    result = run(repo=tmp_path, prompt_path=prompt_path, max_loops=3)

    assert result == ExitCode.SUCCESS
    assert success_messages == ["All Ralph tasks are complete"]
    assert list((tmp_path / "logs").iterdir()) == []


def test_run_does_not_start_codex_when_no_incomplete_task_is_eligible(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Return blocked without starting a loop when dependencies prevent selection."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-001: blocked dependency

- Status: blocked
- Priority: 1
- Depends on: none

## TASK-002: dependent task

- Status: pending
- Priority: 2
- Depends on: TASK-001
""",
    )
    warning_messages: list[str] = []

    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", _fake_git_output_factory(tmp_path))
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(
        codex_provider_module,
        "run_codex",
        lambda *args, **kwargs: pytest.fail("Codex must not be started"),
    )
    monkeypatch.setattr(
        runner_module.logger,
        "warning",
        lambda message, *args: warning_messages.append(message.format(*args)),
    )

    result = run(repo=tmp_path, prompt_path=prompt_path, max_loops=3)

    assert result == ExitCode.TASK_BLOCKED
    assert warning_messages == ["Stopped because no incomplete Ralph task is eligible"]
    assert list((tmp_path / "logs").iterdir()) == []


def test_run_completes_the_last_task_and_writes_one_log(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Complete the final task, commit once, and stop without a redundant loop."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    tasks_path = tmp_path / "TASKS.md"
    _write_tasks(
        tasks_path,
        """## TASK-009: final task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )
    commit_created = False
    codex_calls = 0
    success_messages: list[str] = []
    info_messages: list[str] = []
    warning_messages: list[str] = []

    def fake_git_output(repo: Path, *args: str) -> str:
        if args == ("rev-parse", "--show-toplevel"):
            return str(repo)
        if args == ("rev-parse", "HEAD"):
            return "after" if commit_created else "before"
        raise AssertionError(args)

    def fake_commit_loop_changes(repo: Path, task_id: str, status: str) -> None:
        nonlocal commit_created
        assert repo == tmp_path
        assert task_id == "TASK-009"
        assert status == "completed"
        commit_created = True

    def fake_run_codex(
        command: list[str],
        repo: Path,
        log_path: Path,
        environment: dict[str, str],
        prompt: str,
        timeout_sec: int,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal codex_calls
        del environment, prompt
        assert timeout_sec == 1_800
        codex_calls += 1
        assert repo == tmp_path
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text("TASK_COMPLETED: TASK-009\n", encoding="utf-8")
        log_path.write_text(
            '{"type":"item.completed","item":{"type":"command_execution",'
            '"truncated":true}}\n'
            '{"type":"turn.completed","usage":{"input_tokens":100,'
            '"cached_input_tokens":80,"output_tokens":20,'
            '"reasoning_output_tokens":5}}\n',
            encoding="utf-8",
        )
        tasks_path.write_text(
            tasks_path.read_text(encoding="utf-8").replace(
                "- Status: pending",
                "- Status: completed",
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", fake_git_output)
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(
        runner_module,
        "build_codex_environment",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(codex_provider_module, "run_codex", fake_run_codex)
    monkeypatch.setattr(runner_module, "commit_loop_changes", fake_commit_loop_changes)
    monkeypatch.setattr(
        runner_module,
        "commit_count",
        lambda repo, before, after: int(before != after),
    )
    monkeypatch.setattr(
        runner_module.logger,
        "success",
        lambda message, *args: success_messages.append(message.format(*args)),
    )
    monkeypatch.setattr(
        runner_module.logger,
        "info",
        lambda message, *args: info_messages.append(message.format(*args)),
    )
    monkeypatch.setattr(
        runner_module.logger,
        "warning",
        lambda message, *args: warning_messages.append(message.format(*args)),
    )

    result = run(repo=tmp_path, prompt_path=prompt_path, max_loops=3)

    assert result == ExitCode.SUCCESS
    assert codex_calls == 1
    assert success_messages[0].startswith("Completed TASK-009 (logs")
    assert success_messages[1] == "All Ralph tasks are complete"
    assert (
        "Token usage TASK-009 attempt 1: input=100, cached=80, output=20, "
        "reasoning=5, task-total=120, run-total=120"
    ) in info_messages
    assert "Tool output monitor TASK-009 attempt 1: outputs=1, truncated=1, limit=12000" in info_messages
    assert (
        "Tool output limit reached for TASK-009 attempt 1: 1/1 outputs were truncated "
        "at a 12000-token limit"
    ) in warning_messages
    log_names = [path.name for path in (tmp_path / "logs").iterdir()]
    assert len(log_names) == 1
    assert log_names[0].endswith("_009_completed.log")


def test_run_reports_codex_failure_when_the_process_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Stop with a Codex failure exit code when the child process fails."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-010: task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )

    def fake_run_codex(
        command: list[str],
        repo: Path,
        log_path: Path,
        environment: dict[str, str],
        prompt: str,
        timeout_sec: int,
    ) -> subprocess.CompletedProcess[str]:
        del repo, environment, prompt, timeout_sec
        log_path.write_text("boom\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", _fake_git_output_factory(tmp_path))
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(
        runner_module,
        "build_codex_environment",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(codex_provider_module, "run_codex", fake_run_codex)

    result = run(repo=tmp_path, prompt_path=prompt_path, max_loops=1, api_retry_count=0)

    assert result == ExitCode.CODEX_FAILURE
    log_names = [path.name for path in (tmp_path / "logs").iterdir()]
    assert len(log_names) == 1
    assert log_names[0].endswith("_010_codex-failure.log")


def test_run_reports_protocol_error_for_an_invalid_terminal_token(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Stop with a protocol error when Codex reports an invalid status line."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-011: task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )

    def fake_run_codex(
        command: list[str],
        repo: Path,
        log_path: Path,
        environment: dict[str, str],
        prompt: str,
        timeout_sec: int,
    ) -> subprocess.CompletedProcess[str]:
        del repo, environment, prompt, timeout_sec
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text("no valid token\n", encoding="utf-8")
        log_path.write_text("codex output\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", _fake_git_output_factory(tmp_path))
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(
        runner_module,
        "build_codex_environment",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(codex_provider_module, "run_codex", fake_run_codex)

    result = run(repo=tmp_path, prompt_path=prompt_path, max_loops=1, api_retry_count=0)

    assert result == ExitCode.PROTOCOL_ERROR
    log_names = [path.name for path in (tmp_path / "logs").iterdir()]
    assert len(log_names) == 1
    assert log_names[0].endswith("_011_protocol-error.log")


def test_run_does_not_retry_a_non_transient_codex_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Stop after a child failure that has no transient transport marker."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-010: failed task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )
    codex_calls = 0

    def fake_run_codex(
        command: list[str],
        repo: Path,
        log_path: Path,
        environment: dict[str, str],
        prompt: str,
        timeout_sec: int,
    ) -> subprocess.CompletedProcess[str]:
        """Write a local error and return a failed child process."""
        nonlocal codex_calls
        del repo, environment, prompt, timeout_sec
        codex_calls += 1
        log_path.write_text("invalid local configuration\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", _fake_git_output_factory(tmp_path))
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(
        runner_module,
        "build_codex_environment",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(codex_provider_module, "run_codex", fake_run_codex)

    result = run(repo=tmp_path, prompt_path=prompt_path, max_loops=1, api_retry_count=1)

    assert result == ExitCode.CODEX_FAILURE
    assert codex_calls == 1


def test_run_does_not_retry_a_transient_codex_failure_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Stop after one transient Codex failure when retries are disabled."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-010: failed task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )
    codex_calls = 0

    def fake_run_codex(
        command: list[str],
        repo: Path,
        log_path: Path,
        environment: dict[str, str],
        prompt: str,
        timeout_sec: int,
    ) -> subprocess.CompletedProcess[str]:
        """Write a transient transport error and return a failed process."""
        nonlocal codex_calls
        del repo, environment, prompt, timeout_sec
        codex_calls += 1
        log_path.write_text("stream disconnected", encoding="utf-8")
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", _fake_git_output_factory(tmp_path))
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(
        runner_module,
        "build_codex_environment",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(codex_provider_module, "run_codex", fake_run_codex)

    result = run(repo=tmp_path, prompt_path=prompt_path, max_loops=1)

    assert result == ExitCode.CODEX_FAILURE
    assert codex_calls == 1


def test_run_allows_incomplete_task_without_changes_or_commit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Preserve a valid incomplete result when the agent changed no files."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-010: incomplete task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )

    def fake_git_output(repo: Path, *args: str) -> str:
        """Report a clean worktree and stable Git history."""
        if args == ("rev-parse", "--show-toplevel"):
            return str(repo)
        if args == ("rev-parse", "HEAD"):
            return "before"
        raise AssertionError(args)

    def fake_run_codex(
        command: list[str],
        repo: Path,
        log_path: Path,
        environment: dict[str, str],
        prompt: str,
        timeout_sec: int,
    ) -> subprocess.CompletedProcess[str]:
        """Return a valid incomplete token without changing the worktree."""
        del repo, environment, prompt, timeout_sec
        output_path = Path(command[command.index("--output-last-message") + 1])
        output_path.write_text("TASK_INCOMPLETE: TASK-010\n", encoding="utf-8")
        log_path.write_text("agent could not continue\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", fake_git_output)
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(runner_module, "has_worktree_changes", lambda repo: False)
    monkeypatch.setattr(
        runner_module,
        "build_codex_environment",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(codex_provider_module, "run_codex", fake_run_codex)
    monkeypatch.setattr(
        runner_module,
        "commit_loop_changes",
        lambda *args: pytest.fail("a clean incomplete result must not be committed"),
    )
    monkeypatch.setattr(runner_module, "commit_count", lambda repo, before, after: 0)

    result = run(repo=tmp_path, prompt_path=prompt_path, max_loops=1)

    assert result == ExitCode.TASK_INCOMPLETE
    log_names = [path.name for path in (tmp_path / "logs").iterdir()]
    assert len(log_names) == 1
    assert log_names[0].endswith("_010_incompleted.log")


def test_run_rejects_copilot_without_auto_approve(tmp_path: Path) -> None:
    """Reject a Copilot run before touching Git when auto-approve is missing."""
    result = run(repo=tmp_path, provider="copilot")

    assert result == ExitCode.PREFLIGHT_ERROR


def test_run_rejects_codex_only_options_for_copilot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Reject a Codex-only model-verbosity override for the copilot provider."""
    messages: list[str] = []
    monkeypatch.setattr(
        runner_module.logger,
        "error",
        lambda entry, *args: messages.append(entry.format(*args)),
    )

    result = run(
        repo=tmp_path,
        provider="copilot",
        auto_approve=True,
        model_verbosity="high",
    )

    assert result == ExitCode.PREFLIGHT_ERROR
    assert any("--provider copilot does not support: --model-verbosity" in m for m in messages)


def test_run_accepts_a_copilot_only_reasoning_effort_for_codex(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Do not reject reasoning-effort levels by provider in a dry run.

    Support for a given level depends on the selected model, not the
    provider, so ``--reasoning-effort max`` must reach the Codex command even
    though Codex CLI itself has no ``minimal``-style provider gate in wiggum.
    """
    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", _fake_git_output_factory(tmp_path))
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-001: pending task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )

    result = run(repo=tmp_path, prompt_path=prompt_path, reasoning_effort="max", dry_run=True)

    assert result == ExitCode.SUCCESS
    assert 'model_reasoning_effort=\\"max\\"' in capsys.readouterr().out


def test_run_dry_run_prints_a_copilot_command_and_prompt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Print the Copilot command and prompt without invoking any process."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-013: dry run task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )
    monkeypatch.setattr(copilot_provider_module, "resolve_copilot_executable", lambda value: value)
    monkeypatch.setattr(
        runner_module,
        "require_git_output",
        _fake_git_output_factory(tmp_path),
    )
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)

    result = run(
        repo=tmp_path,
        prompt_path=prompt_path,
        provider="copilot",
        auto_approve=True,
        dry_run=True,
    )

    assert result == ExitCode.SUCCESS
    printed = capsys.readouterr().out
    assert (
        "copilot -s --no-ask-user --output-format text --reasoning-effort medium "
        "--allow-all-tools" in printed
    )
    assert "one loop" in printed


def test_run_completes_a_task_with_the_copilot_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Complete a task through the copilot provider using its own process hooks."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    tasks_path = tmp_path / "TASKS.md"
    _write_tasks(
        tasks_path,
        """## TASK-011: copilot task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )
    commit_created = False
    copilot_calls = 0

    def fake_git_output(repo: Path, *args: str) -> str:
        if args == ("rev-parse", "--show-toplevel"):
            return str(repo)
        if args == ("rev-parse", "HEAD"):
            return "after" if commit_created else "before"
        raise AssertionError(args)

    def fake_commit_loop_changes(repo: Path, task_id: str, status: str) -> None:
        nonlocal commit_created
        assert repo == tmp_path
        assert task_id == "TASK-011"
        assert status == "completed"
        commit_created = True

    def fake_run_copilot(
        command: list[str],
        repo: Path,
        log_path: Path,
        environment: dict[str, str],
        prompt: str,
        output_path: Path,
        timeout_sec: int,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal copilot_calls
        del environment, prompt, timeout_sec
        copilot_calls += 1
        assert repo == tmp_path
        assert "--allow-all-tools" in command
        output_path.write_text("TASK_COMPLETED: TASK-011\n", encoding="utf-8")
        log_path.write_text("Copilot completed the task\n", encoding="utf-8")
        tasks_path.write_text(
            tasks_path.read_text(encoding="utf-8").replace(
                "- Status: pending",
                "- Status: completed",
            ),
            encoding="utf-8",
        )
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(copilot_provider_module, "resolve_copilot_executable", lambda value: value)
    monkeypatch.setattr(runner_module, "require_git_output", fake_git_output)
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(
        runner_module,
        "build_codex_environment",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(copilot_provider_module, "run_copilot", fake_run_copilot)
    monkeypatch.setattr(runner_module, "commit_loop_changes", fake_commit_loop_changes)
    monkeypatch.setattr(
        runner_module,
        "commit_count",
        lambda repo, before, after: int(before != after),
    )

    result = run(
        repo=tmp_path,
        prompt_path=prompt_path,
        provider="copilot",
        auto_approve=True,
        max_loops=1,
    )

    assert result == ExitCode.SUCCESS
    assert copilot_calls == 1
    log_names = [path.name for path in (tmp_path / "logs").iterdir()]
    assert len(log_names) == 1
    assert log_names[0].endswith("_011_completed.log")


def test_run_reports_copilot_failure_when_the_process_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Stop with an agent failure exit code when Copilot exits non-zero."""
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("one loop", encoding="utf-8")
    _write_tasks(
        tmp_path / "TASKS.md",
        """## TASK-012: copilot task

- Status: pending
- Priority: 1
- Depends on: none
""",
    )

    def fake_run_copilot(
        command: list[str],
        repo: Path,
        log_path: Path,
        environment: dict[str, str],
        prompt: str,
        output_path: Path,
        timeout_sec: int,
    ) -> subprocess.CompletedProcess[str]:
        del repo, environment, prompt, output_path, timeout_sec
        log_path.write_text("fatal error\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(copilot_provider_module, "resolve_copilot_executable", lambda value: value)
    monkeypatch.setattr(
        runner_module,
        "require_git_output",
        _fake_git_output_factory(tmp_path),
    )
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)
    monkeypatch.setattr(
        runner_module,
        "build_codex_environment",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(copilot_provider_module, "run_copilot", fake_run_copilot)

    result = run(
        repo=tmp_path,
        prompt_path=prompt_path,
        provider="copilot",
        auto_approve=True,
        max_loops=1,
        api_retry_count=None,
    )

    assert result == ExitCode.CODEX_FAILURE
    log_names = [path.name for path in (tmp_path / "logs").iterdir()]
    assert len(log_names) == 1
    assert log_names[0].endswith("_012_copilot-failure.log")
