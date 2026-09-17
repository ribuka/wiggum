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
    assert args.max_loops == 20
    assert args.api_retry_count is None
    assert args.reasoning_effort == "medium"
    assert args.model_verbosity == "low"
    assert args.tool_output_token_limit == 12_000
    assert args.lean is False
    assert args.provider == "codex"
    assert args.executable is None
    assert args.codex is None


def test_parse_args_run_accepts_a_provider_and_executable() -> None:
    """Parse an explicit provider selection and generic executable override."""
    args = _parse_args(
        [
            "run",
            "--provider",
            "copilot",
            "--executable",
            "/opt/copilot",
            "--auto-approve",
        ]
    )

    assert args.provider == "copilot"
    assert args.executable == "/opt/copilot"
    assert args.auto_approve is True


def test_parse_args_run_rejects_an_unsupported_provider() -> None:
    """Reject a --provider value outside the supported choices."""
    with pytest.raises(SystemExit):
        _parse_args(["run", "--provider", "unsupported"])


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


@pytest.mark.parametrize("reasoning_effort", ("none", "max"))
def test_parse_args_run_accepts_model_specific_reasoning_efforts(
    reasoning_effort: str,
) -> None:
    """Parse reasoning-effort values whose support depends on the model."""
    args = _parse_args(["run", "--reasoning-effort", reasoning_effort])

    assert args.reasoning_effort == reasoning_effort


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
    written = [tmp_path / "RALPH.md", tmp_path / "TASKS.json"]
    monkeypatch.setattr(cli_module, "scaffold", lambda repo, *, force: written)

    exit_code = main(["init", "--repo", str(tmp_path)])

    assert exit_code == ExitCode.SUCCESS


def test_main_init_reports_preflight_error_on_existing_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Report a preflight error when scaffolding refuses to overwrite files."""

    def _raise(repo: Path, *, force: bool) -> list[Path]:
        raise FileExistsError("refusing to overwrite existing files: TASKS.json")

    monkeypatch.setattr(cli_module, "scaffold", _raise)

    exit_code = main(["init", "--repo", str(tmp_path)])

    assert exit_code == ExitCode.PREFLIGHT_ERROR


def test_main_run_forwards_the_default_provider_and_codex_executable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Forward the default provider and the legacy codex_executable value."""
    captured: dict[str, object] = {}

    def fake_run(**kwargs: object) -> ExitCode:
        captured.update(kwargs)
        return ExitCode.SUCCESS

    monkeypatch.setattr(cli_module, "run", fake_run)

    exit_code = main(["run", "--repo", str(tmp_path)])

    assert exit_code == ExitCode.SUCCESS
    assert captured["provider"] == "codex"
    assert captured["codex_executable"] == "codex"
    assert captured["executable"] is None


def test_main_run_forwards_an_explicit_provider_and_executable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Forward an explicit provider selection and executable override."""
    captured: dict[str, object] = {}

    def fake_run(**kwargs: object) -> ExitCode:
        captured.update(kwargs)
        return ExitCode.SUCCESS

    monkeypatch.setattr(cli_module, "run", fake_run)

    exit_code = main(
        [
            "run",
            "--repo",
            str(tmp_path),
            "--provider",
            "copilot",
            "--executable",
            "/opt/copilot",
            "--auto-approve",
        ]
    )

    assert exit_code == ExitCode.SUCCESS
    assert captured["provider"] == "copilot"
    assert captured["executable"] == "/opt/copilot"
    assert captured["auto_approve"] is True
