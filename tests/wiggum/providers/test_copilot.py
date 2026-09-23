"""Tests for GitHub Copilot CLI process construction and execution."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from wiggum.providers.copilot import (
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


def test_build_copilot_command_reads_the_prompt_from_standard_input() -> None:
    """Build a silent, non-interactive command with no positional prompt."""
    command = build_copilot_command("copilot", None)

    assert command[0] == "copilot"
    assert "-s" in command
    assert "--no-ask-user" in command
    assert "--output-format" in command
    assert command[command.index("--output-format") + 1] == "text"
    assert command[command.index("--reasoning-effort") + 1] == "medium"
    assert "--allow-all-tools" not in command
    assert "--model" not in command


def test_build_copilot_command_forwards_reasoning_effort() -> None:
    """Forward a non-default reasoning effort to the Copilot CLI."""
    command = build_copilot_command("copilot", None, reasoning_effort="high")

    assert command[command.index("--reasoning-effort") + 1] == "high"


def test_build_copilot_command_adds_allow_all_tools_when_auto_approve() -> None:
    """Request unattended tool approval when auto-approve is enabled."""
    command = build_copilot_command("copilot", "gpt-test", auto_approve=True)

    assert "--allow-all-tools" in command
    assert command[command.index("--model") + 1] == "gpt-test"


def test_run_copilot_writes_the_log_and_last_message_on_success(tmp_path: Path) -> None:
    """Capture standard output to both the loop log and the message file."""
    log_path = tmp_path / "loop.log"
    output_path = tmp_path / "last-message.txt"
    command = [sys.executable, "-c", "import sys; print(sys.stdin.read(), end='')"]

    completed = run_copilot(
        command,
        tmp_path,
        log_path,
        environment=os.environ.copy(),
        prompt="TASK_COMPLETED: TASK-001",
        output_path=output_path,
    )

    assert completed.returncode == 0
    assert log_path.read_text(encoding="utf-8") == "TASK_COMPLETED: TASK-001"
    assert output_path.read_text(encoding="utf-8") == "TASK_COMPLETED: TASK-001"


def test_run_copilot_does_not_write_the_last_message_on_failure(tmp_path: Path) -> None:
    """Skip writing the message file when the Copilot process fails."""
    log_path = tmp_path / "loop.log"
    output_path = tmp_path / "last-message.txt"
    command = [sys.executable, "-c", "import sys; print('boom'); sys.exit(1)"]

    completed = run_copilot(
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


def test_run_copilot_excludes_stderr_from_the_last_message(tmp_path: Path) -> None:
    """Keep diagnostic standard error output out of the last-message file."""
    log_path = tmp_path / "loop.log"
    output_path = tmp_path / "last-message.txt"
    command = [
        sys.executable,
        "-c",
        ("import sys; sys.stderr.write('diagnostic noise\\n'); print(sys.stdin.read(), end='')"),
    ]

    completed = run_copilot(
        command,
        tmp_path,
        log_path,
        environment=os.environ.copy(),
        prompt="TASK_COMPLETED: TASK-001",
        output_path=output_path,
    )

    assert completed.returncode == 0
    assert output_path.read_text(encoding="utf-8") == "TASK_COMPLETED: TASK-001"
    assert "diagnostic noise" in log_path.read_text(encoding="utf-8")


def test_run_copilot_writes_partial_output_to_the_log_on_timeout(tmp_path: Path) -> None:
    """Preserve whatever output was captured before a Copilot timeout."""
    log_path = tmp_path / "loop.log"
    output_path = tmp_path / "last-message.txt"
    command = [
        sys.executable,
        "-c",
        "import sys, time; print('partial output', flush=True); time.sleep(5)",
    ]

    with pytest.raises(subprocess.TimeoutExpired):
        run_copilot(
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


def test_is_retryable_copilot_failure_matches_only_transport_errors(tmp_path: Path) -> None:
    """Recognize known transient connection failures in Copilot logs."""
    log_path = tmp_path / "copilot.log"
    log_path.write_text("network error while contacting the model", encoding="utf-8")

    assert is_retryable_copilot_failure(log_path)

    log_path.write_text("invalid local configuration", encoding="utf-8")

    assert not is_retryable_copilot_failure(log_path)
