"""Tests for the wiggum command-line interface."""

from __future__ import annotations

from pathlib import Path

import pytest

import wiggum.cli as cli_module
from wiggum.cli import _parse_args, main
from wiggum.exit_codes import ExitCode


def test_parse_args_run_defaults_to_the_current_directory() -> None:
    """Default the run subcommand's --repo to the current working directory."""
    args = _parse_args(["run"])

    assert args.command == "run"
    assert args.repo == Path.cwd()
    assert args.tasks_file is None
    assert args.prompt_file is None
    assert args.logs_dir is None
    assert args.temp_dir is None
    assert args.uv_cache_dir is None
    assert args.no_managed_env is False
    assert args.provider == "codex"
    assert args.provider_executable is None
    assert args.provider_timeout_sec == 1_800
    assert args.max_loops == 20
    assert args.api_retry_count is None
    assert args.reasoning_effort == "medium"
    assert args.model_verbosity == "low"
    assert args.tool_output_token_limit == 12_000
    assert args.lean is False


def test_parse_args_run_accepts_token_saving_controls() -> None:
    """Parse explicit reasoning, verbosity, tool-output, and lean settings."""
    args = _parse_args(
        [
            "run",
            "--reasoning-effort",
            "medium",
            "--model-verbosity",
            "high",
            "--tool-output-token-limit",
            "1234",
            "--lean",
        ]
    )

    assert args.reasoning_effort == "medium"
    assert args.model_verbosity == "high"
    assert args.tool_output_token_limit == 1234
    assert args.lean is True


def test_parse_args_run_accepts_provider_specific_options() -> None:
    """Parse explicit provider selection and provider-agnostic aliases."""
    args = _parse_args(
        [
            "run",
            "--provider",
            "copilot",
            "--provider-executable",
            "copilot-nightly",
            "--provider-timeout-sec",
            "45",
            "--auto-approve",
        ]
    )

    assert args.provider == "copilot"
    assert args.provider_executable == "copilot-nightly"
    assert args.provider_timeout_sec == 45
    assert args.auto_approve is True


def test_parse_args_run_keeps_the_legacy_codex_aliases() -> None:
    """Keep ``--codex`` and ``--codex-timeout-sec`` as supported aliases."""
    args = _parse_args(["run", "--codex", "custom-codex", "--codex-timeout-sec", "15"])

    assert args.provider == "codex"
    assert args.provider_executable == "custom-codex"
    assert args.provider_timeout_sec == 15


def test_parse_args_init_defaults_to_the_current_directory() -> None:
    """Default the init subcommand's --repo to the current working directory."""
    args = _parse_args(["init"])

    assert args.command == "init"
    assert args.repo == Path.cwd()
    assert args.force is False


def test_main_requires_a_subcommand() -> None:
    """Reject invocation without a run or init subcommand."""
    with pytest.raises(SystemExit):
        main([])


def test_main_init_reports_success(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report success and log every written path for the init subcommand."""
    written = [tmp_path / "RALPH.md", tmp_path / "TASKS.md"]
    monkeypatch.setattr(cli_module, "scaffold", lambda repo, *, force: written)

    exit_code = main(["init", "--repo", str(tmp_path)])

    assert exit_code == ExitCode.SUCCESS


def test_main_init_reports_preflight_error_on_existing_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report a preflight error when scaffolding refuses to overwrite files."""

    def _raise(repo: Path, *, force: bool) -> list[Path]:
        raise FileExistsError("refusing to overwrite existing files: TASKS.md")

    monkeypatch.setattr(cli_module, "scaffold", _raise)

    exit_code = main(["init", "--repo", str(tmp_path)])

    assert exit_code == ExitCode.PREFLIGHT_ERROR
