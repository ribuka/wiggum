"""Tests for the wiggum command-line interface."""

from __future__ import annotations

from pathlib import Path

import pytest

import wiggum.cli as cli_module
from wiggum.cli import _parse_args, main
from wiggum.exit_codes import ExitCode


def test_parse_args_run_defaults_to_the_current_directory() -> None:
    """Default the run subcommand's --repo to the current working directory."""
    args = _parse_args(["run", "--provider", "codex"])

    assert args.command == "run"
    assert args.repo == Path.cwd()
    assert args.max_loops == 20
    assert args.reasoning_effort == "medium"
    assert args.provider == "codex"
    assert args.model is None
    assert args.auto_approve is False
    assert args.dry_run is False


def test_parse_args_run_accepts_a_provider() -> None:
    """Parse an explicit provider selection."""
    args = _parse_args(["run", "--provider", "copilot", "--auto-approve"])

    assert args.provider == "copilot"
    assert args.auto_approve is True


def test_parse_args_run_requires_a_provider() -> None:
    """Reject a run invocation that omits --provider."""
    with pytest.raises(SystemExit):
        _parse_args(["run"])


def test_parse_args_run_rejects_an_unsupported_provider() -> None:
    """Reject a --provider value outside the supported choices."""
    with pytest.raises(SystemExit):
        _parse_args(["run", "--provider", "unsupported"])


def test_parse_args_run_rejects_options_moved_to_config_toml() -> None:
    """Reject flags that now live in wiggum/config.toml's [run] table."""
    with pytest.raises(SystemExit):
        _parse_args(["run", "--tasks-file", "custom.json"])


def test_parse_args_run_rejects_the_removed_codex_only_flags() -> None:
    """Reject Codex-only flags now read from [run.codex]."""
    with pytest.raises(SystemExit):
        _parse_args(["run", "--model-verbosity", "high"])


@pytest.mark.parametrize("reasoning_effort", ("none", "max"))
def test_parse_args_run_accepts_model_specific_reasoning_efforts(
    reasoning_effort: str,
) -> None:
    """Parse reasoning-effort values whose support depends on the model."""
    args = _parse_args(["run", "--provider", "codex", "--reasoning-effort", reasoning_effort])

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


def test_main_run_forwards_the_selected_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Forward the selected provider and no model or auto-approve."""
    captured: dict[str, object] = {}

    def fake_run(**kwargs: object) -> ExitCode:
        captured.update(kwargs)
        return ExitCode.SUCCESS

    monkeypatch.setattr(cli_module, "run", fake_run)

    exit_code = main(["run", "--repo", str(tmp_path), "--provider", "codex"])

    assert exit_code == ExitCode.SUCCESS
    assert captured["provider"] == "codex"
    assert captured["model"] is None
    assert captured["auto_approve"] is False
    assert "codex_executable" not in captured
    assert "executable" not in captured


def test_main_run_forwards_an_explicit_provider_and_model(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Forward an explicit provider selection and model override."""
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
            "--model",
            "gpt-5",
            "--auto-approve",
        ]
    )

    assert exit_code == ExitCode.SUCCESS
    assert captured["provider"] == "copilot"
    assert captured["model"] == "gpt-5"
    assert captured["auto_approve"] is True
