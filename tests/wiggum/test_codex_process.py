"""Tests for Codex CLI process construction and execution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from wiggum.codex_process import (
    build_codex_command,
    is_retryable_codex_failure,
    resolve_codex_executable,
    run_codex,
)


def test_resolve_codex_executable_accepts_an_existing_file_path() -> None:
    """Resolve an executable given as a direct, existing file path."""
    resolved = resolve_codex_executable(sys.executable)

    assert resolved == str(Path(sys.executable).resolve())


def test_resolve_codex_executable_returns_none_for_unknown_name() -> None:
    """Return None for a name that is neither a file nor on PATH."""
    assert resolve_codex_executable("no-such-codex-executable-xyz") is None


def test_build_codex_command_uses_sandbox_by_default(tmp_path: Path) -> None:
    """Request the workspace-write sandbox unless auto-approve is set."""
    output_path = tmp_path / "last-message.txt"

    command = build_codex_command("codex", tmp_path, output_path, None)

    assert command[0] == "codex"
    assert "--json" in command
    assert "--sandbox" in command
    assert command[command.index("--sandbox") + 1] == "workspace-write"
    assert "--approve-for-me" not in command
    assert command[-1] == "-"
    assert str(tmp_path) in command
    assert str(output_path) in command
    assert 'model_reasoning_effort="medium"' in command
    assert 'model_verbosity="low"' in command
    assert "tool_output_token_limit=12000" in command


def test_build_codex_command_uses_approve_for_me_when_auto_approve(tmp_path: Path) -> None:
    """Request unattended approval instead of a sandbox flag when requested."""
    output_path = tmp_path / "last-message.txt"

    command = build_codex_command(
        "codex",
        tmp_path,
        output_path,
        "gpt-test",
        auto_approve=True,
    )

    assert "--approve-for-me" in command
    assert "--sandbox" not in command
    assert command[command.index("--model") + 1] == "gpt-test"


def test_build_codex_command_applies_token_controls_and_lean_mode(
    tmp_path: Path,
) -> None:
    """Build an isolated command with explicit token-saving configuration."""
    command = build_codex_command(
        "codex",
        tmp_path,
        tmp_path / "last-message.txt",
        None,
        reasoning_effort="medium",
        model_verbosity="high",
        tool_output_token_limit=1234,
        lean=True,
    )

    assert "--ignore-user-config" in command
    assert 'model_reasoning_effort="medium"' in command
    assert 'model_verbosity="high"' in command
    assert "tool_output_token_limit=1234" in command
    assert 'model_reasoning_summary="none"' in command


def test_run_codex_writes_combined_output_and_stdin_prompt_to_the_log_file(tmp_path: Path) -> None:
    """Write combined output while passing the complete prompt through standard input."""
    log_path = tmp_path / "loop.log"
    command = [sys.executable, "-c", "import sys; print(sys.stdin.read())"]

    completed = run_codex(
        command,
        tmp_path,
        log_path,
        environment=os.environ.copy(),
        prompt="first line\nsecond line",
    )

    assert completed.returncode == 0
    assert log_path.read_text(encoding="utf-8") == "first line\nsecond line\n"


def test_run_codex_encodes_standard_input_as_utf8(tmp_path: Path) -> None:
    """Send non-ASCII prompts to Codex as UTF-8 regardless of the system locale."""
    log_path = tmp_path / "loop.log"
    prompt = "日本語のプロンプト"
    command = [sys.executable, "-c", "import sys; print(sys.stdin.buffer.read().hex())"]

    completed = run_codex(
        command,
        tmp_path,
        log_path,
        environment=os.environ.copy(),
        prompt=prompt,
    )

    assert completed.returncode == 0
    assert log_path.read_text(encoding="utf-8") == f"{prompt.encode('utf-8').hex()}\n"


def test_is_retryable_codex_failure_matches_only_transport_errors(tmp_path: Path) -> None:
    """Recognize known transient connection failures in Codex logs."""
    log_path = tmp_path / "codex.log"
    log_path.write_text("stream disconnected before completion", encoding="utf-8")

    assert is_retryable_codex_failure(log_path)

    log_path.write_text("invalid local configuration", encoding="utf-8")

    assert not is_retryable_codex_failure(log_path)
