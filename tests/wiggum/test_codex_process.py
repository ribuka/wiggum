"""Tests for Codex CLI process construction and execution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from wiggum.codex_process import (
    build_codex_command,
    build_codex_environment,
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

    command = build_codex_command("codex", tmp_path, output_path, "do work", None)

    assert command[0] == "codex"
    assert "--sandbox" in command
    assert command[command.index("--sandbox") + 1] == "workspace-write"
    assert "--approve-for-me" not in command
    assert command[-1] == "do work"
    assert str(tmp_path) in command
    assert str(output_path) in command


def test_build_codex_command_uses_approve_for_me_when_auto_approve(tmp_path: Path) -> None:
    """Request unattended approval instead of a sandbox flag when requested."""
    output_path = tmp_path / "last-message.txt"

    command = build_codex_command(
        "codex",
        tmp_path,
        output_path,
        "do work",
        "gpt-test",
        auto_approve=True,
    )

    assert "--approve-for-me" in command
    assert "--sandbox" not in command
    assert command[command.index("--model") + 1] == "gpt-test"


def test_build_codex_environment_sets_isolated_paths_by_default(tmp_path: Path) -> None:
    """Inject UV_CACHE_DIR, TMP, and TEMP when process env management is enabled."""
    temp_dir = tmp_path / "tmp"
    uv_cache_dir = tmp_path / ".uv-cache"

    environment = build_codex_environment(temp_dir, uv_cache_dir=uv_cache_dir)

    assert environment["UV_CACHE_DIR"] == str(uv_cache_dir.resolve())
    assert environment["TMP"] == environment["TEMP"]
    assert Path(environment["TMP"]).is_dir()
    assert Path(environment["TMP"]).is_relative_to((temp_dir / "runtime").resolve())
    assert uv_cache_dir.is_dir()


def test_build_codex_environment_is_a_no_op_when_disabled(tmp_path: Path) -> None:
    """Leave the environment untouched when process env management is disabled."""
    temp_dir = tmp_path / "tmp"
    uv_cache_dir = tmp_path / ".uv-cache"

    environment = build_codex_environment(
        temp_dir,
        uv_cache_dir=uv_cache_dir,
        manage_process_env=False,
    )

    assert not uv_cache_dir.exists()
    assert not (temp_dir / "runtime").exists()
    assert environment.get("UV_CACHE_DIR") is None


def test_run_codex_writes_combined_output_to_the_log_file(tmp_path: Path) -> None:
    """Write standard output and standard error to the loop log file."""
    log_path = tmp_path / "loop.log"
    command = [sys.executable, "-c", "print('hello from codex')"]

    completed = run_codex(command, tmp_path, log_path, environment=os.environ.copy())

    assert completed.returncode == 0
    assert "hello from codex" in log_path.read_text(encoding="utf-8")
