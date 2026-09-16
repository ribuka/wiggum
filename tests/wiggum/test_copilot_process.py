"""Tests for GitHub Copilot CLI process construction and execution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from wiggum.copilot_process import (
    build_copilot_command,
    is_retryable_copilot_failure,
    resolve_copilot_executable,
    run_copilot,
)


def test_resolve_copilot_executable_accepts_an_existing_file_path() -> None:
    """Resolve an executable given as a direct, existing file path."""
    resolved = resolve_copilot_executable(sys.executable)

    assert resolved == str(Path(sys.executable).resolve())


def test_resolve_copilot_executable_returns_none_for_unknown_name() -> None:
    """Return None for a name that is neither a file nor on PATH."""
    assert resolve_copilot_executable("no-such-copilot-executable-xyz") is None


def test_build_copilot_command_uses_silent_noninteractive_allow_all(tmp_path: Path) -> None:
    """Build a non-interactive command that reads its prompt from standard input."""
    command = build_copilot_command(
        "copilot",
        tmp_path,
        tmp_path / "last-message.txt",
        "gpt-5.4",
        auto_approve=True,
    )

    assert command == [
        "copilot",
        "-s",
        "--no-ask-user",
        "--allow-all",
        "--model=gpt-5.4",
    ]


def test_run_copilot_writes_stdout_to_the_last_message_and_combined_log(
    tmp_path: Path,
) -> None:
    """Persist stdout as the final message while keeping stderr in the log."""
    log_path = tmp_path / "loop.log"
    output_path = tmp_path / "last-message.txt"
    command = [
        sys.executable,
        "-c",
        (
            "import sys; "
            "sys.stdout.write(sys.stdin.read().upper()); "
            "sys.stderr.write('diagnostic\\n')"
        ),
    ]

    completed = run_copilot(
        command,
        tmp_path,
        log_path,
        output_path,
        environment=os.environ.copy(),
        prompt="task_completed: task-001\n",
        timeout_sec=30,
    )

    assert completed.returncode == 0
    assert output_path.read_text(encoding="utf-8") == "TASK_COMPLETED: TASK-001\n"
    assert log_path.read_text(encoding="utf-8") == "TASK_COMPLETED: TASK-001\ndiagnostic\n"


def test_is_retryable_copilot_failure_matches_transport_errors(tmp_path: Path) -> None:
    """Recognize known transient connection failures in Copilot logs."""
    log_path = tmp_path / "copilot.log"
    log_path.write_text("network error while sending request", encoding="utf-8")

    assert is_retryable_copilot_failure(log_path)

    log_path.write_text("invalid local configuration", encoding="utf-8")

    assert not is_retryable_copilot_failure(log_path)
