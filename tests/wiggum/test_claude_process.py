"""Tests for Claude Code CLI process construction and execution."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from wiggum.claude_process import (
    build_claude_command,
    is_retryable_claude_failure,
    read_claude_usage,
    resolve_claude_executable,
    run_claude,
)
from wiggum.token_usage import TokenUsage


def test_resolve_claude_executable_accepts_an_existing_file_path() -> None:
    """Resolve an executable given as a direct, existing file path."""
    resolved = resolve_claude_executable(sys.executable)

    assert resolved == str(Path(sys.executable).resolve())


def test_resolve_claude_executable_returns_none_for_unknown_name() -> None:
    """Return None for a name that is neither a file nor on PATH."""
    assert resolve_claude_executable("no-such-claude-executable-xyz") is None


def test_build_claude_command_reads_the_prompt_from_standard_input() -> None:
    """Build a non-interactive, JSON-output command with no positional prompt."""
    command = build_claude_command("claude", None)

    assert command[0] == "claude"
    assert "-p" in command
    assert "--output-format" in command
    assert command[command.index("--output-format") + 1] == "json"
    assert command[command.index("--effort") + 1] == "medium"
    assert "--permission-mode" not in command
    assert "--model" not in command


def test_build_claude_command_forwards_reasoning_effort() -> None:
    """Forward a non-default reasoning effort to Claude Code's --effort flag."""
    command = build_claude_command("claude", None, reasoning_effort="high")

    assert command[command.index("--effort") + 1] == "high"


def test_build_claude_command_bypasses_permissions_when_auto_approve() -> None:
    """Request unattended tool approval when auto-approve is enabled."""
    command = build_claude_command("claude", "claude-test", auto_approve=True)

    assert command[command.index("--permission-mode") + 1] == "bypassPermissions"
    assert command[command.index("--model") + 1] == "claude-test"


def _json_stdout_script(result: str, usage: dict[str, int]) -> str:
    """Build a Python one-liner that prints a Claude Code JSON result object.

    Parameters
    ----------
    result : str
        Final assistant message to embed in the ``result`` field.
    usage : dict[str, int]
        Usage counters to embed in the ``usage`` field.

    Returns
    -------
    str
        Source passed to ``python -c``.
    """
    payload = json.dumps({"type": "result", "result": result, "usage": usage})
    return f"import sys; sys.stdin.read(); print({payload!r})"


def test_run_claude_writes_the_log_and_last_message_on_success(tmp_path: Path) -> None:
    """Extract the JSON result field into both the log and the message file."""
    log_path = tmp_path / "loop.log"
    output_path = tmp_path / "last-message.txt"
    command = [
        sys.executable,
        "-c",
        _json_stdout_script("TASK_COMPLETED: TASK-001", {"input_tokens": 1, "output_tokens": 1}),
    ]

    completed = run_claude(
        command,
        tmp_path,
        log_path,
        environment=os.environ.copy(),
        prompt="do the task",
        output_path=output_path,
    )

    assert completed.returncode == 0
    assert output_path.read_text(encoding="utf-8") == "TASK_COMPLETED: TASK-001"
    assert "TASK_COMPLETED: TASK-001" in log_path.read_text(encoding="utf-8")


def test_run_claude_keeps_stderr_off_the_json_result_line_in_the_log(tmp_path: Path) -> None:
    """Never let standard error merge onto the JSON result's log line.

    Regression test: Claude Code CLI can succeed while also writing a
    warning to standard error without its own trailing newline. If the log
    concatenated the two streams directly, that warning would land on the
    same line as the JSON result and break both JSON parsing and
    read_claude_usage's line-by-line usage lookup.
    """
    log_path = tmp_path / "loop.log"
    output_path = tmp_path / "last-message.txt"
    payload = json.dumps(
        {
            "type": "result",
            "result": "TASK_COMPLETED: TASK-001",
            "usage": {"input_tokens": 5, "output_tokens": 3},
        }
    )
    command = [
        sys.executable,
        "-c",
        (
            "import sys; sys.stdin.read(); "
            f"sys.stdout.write({payload!r}); "
            "sys.stderr.write('warning: no trailing newline')"
        ),
    ]

    completed = run_claude(
        command,
        tmp_path,
        log_path,
        environment=os.environ.copy(),
        prompt="",
        output_path=output_path,
    )

    assert completed.returncode == 0
    assert output_path.read_text(encoding="utf-8") == "TASK_COMPLETED: TASK-001"
    log_lines = log_path.read_text(encoding="utf-8").splitlines()
    assert json.loads(log_lines[0]) == {
        "type": "result",
        "result": "TASK_COMPLETED: TASK-001",
        "usage": {"input_tokens": 5, "output_tokens": 3},
    }
    assert read_claude_usage(log_path) == TokenUsage(5, 0, 3, 0)


def test_run_claude_does_not_write_the_last_message_on_failure(tmp_path: Path) -> None:
    """Skip writing the message file when the Claude Code process fails."""
    log_path = tmp_path / "loop.log"
    output_path = tmp_path / "last-message.txt"
    command = [sys.executable, "-c", "import sys; print('boom'); sys.exit(1)"]

    completed = run_claude(
        command,
        tmp_path,
        log_path,
        environment=os.environ.copy(),
        prompt="",
        output_path=output_path,
    )

    assert completed.returncode == 1
    assert "boom" in log_path.read_text(encoding="utf-8")
    assert not output_path.exists()


def test_run_claude_skips_the_last_message_when_stdout_is_not_the_expected_json(
    tmp_path: Path,
) -> None:
    """Leave the message file untouched when stdout has no usable result field."""
    log_path = tmp_path / "loop.log"
    output_path = tmp_path / "last-message.txt"
    command = [sys.executable, "-c", "import sys; sys.stdin.read(); print('not json')"]

    completed = run_claude(
        command,
        tmp_path,
        log_path,
        environment=os.environ.copy(),
        prompt="",
        output_path=output_path,
    )

    assert completed.returncode == 0
    assert not output_path.exists()


def test_run_claude_writes_partial_output_to_the_log_on_timeout(tmp_path: Path) -> None:
    """Preserve whatever output was captured before a Claude Code timeout."""
    log_path = tmp_path / "loop.log"
    output_path = tmp_path / "last-message.txt"
    command = [
        sys.executable,
        "-c",
        "import sys, time; print('partial output', flush=True); time.sleep(5)",
    ]

    with pytest.raises(subprocess.TimeoutExpired):
        run_claude(
            command,
            tmp_path,
            log_path,
            environment=os.environ.copy(),
            prompt="",
            output_path=output_path,
            timeout_sec=1,
        )

    assert "partial output" in log_path.read_text(encoding="utf-8")
    assert not output_path.exists()


def test_is_retryable_claude_failure_matches_only_transport_errors(tmp_path: Path) -> None:
    """Recognize known transient connection failures in Claude Code logs."""
    log_path = tmp_path / "claude.log"
    log_path.write_text("network error while contacting the model", encoding="utf-8")

    assert is_retryable_claude_failure(log_path)

    log_path.write_text("invalid local configuration", encoding="utf-8")

    assert not is_retryable_claude_failure(log_path)


def test_read_claude_usage_folds_cache_activity_into_input_tokens(tmp_path: Path) -> None:
    """Report cache reads/writes as input tokens, with reads also as cached."""
    log_path = tmp_path / "claude.log"
    log_path.write_text(
        json.dumps(
            {
                "type": "result",
                "result": "TASK_COMPLETED: TASK-001",
                "usage": {
                    "input_tokens": 100,
                    "cache_creation_input_tokens": 30,
                    "cache_read_input_tokens": 20,
                    "output_tokens": 40,
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert read_claude_usage(log_path) == TokenUsage(150, 20, 40, 0)


def test_read_claude_usage_treats_missing_or_invalid_counts_as_zero(tmp_path: Path) -> None:
    """Avoid failing a run because the usage object is partial or malformed."""
    log_path = tmp_path / "claude.log"
    log_path.write_text(
        json.dumps(
            {
                "type": "result",
                "usage": {"input_tokens": -1, "output_tokens": "10"},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert read_claude_usage(log_path) == TokenUsage()


def test_read_claude_usage_returns_zero_for_an_unreadable_log(tmp_path: Path) -> None:
    """Return zero usage when the requested log does not exist."""
    assert read_claude_usage(tmp_path / "missing.log") == TokenUsage()


def test_read_claude_usage_returns_zero_when_no_result_event_is_present(tmp_path: Path) -> None:
    """Return zero usage when the log has no ``result`` event."""
    log_path = tmp_path / "claude.log"
    log_path.write_text('{"type":"system"}\ndiagnostic noise\n', encoding="utf-8")

    assert read_claude_usage(log_path) == TokenUsage()
