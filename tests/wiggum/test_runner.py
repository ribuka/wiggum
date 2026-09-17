"""Tests for Ralph loop orchestration with JSON task ledgers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import wiggum.providers.codex as codex_provider_module
import wiggum.runner as runner_module
from wiggum.exit_codes import ExitCode
from wiggum.runner import run


@pytest.fixture(autouse=True)
def _write_project_configuration(tmp_path: Path) -> None:
    """Provide the required project configuration for runner tests.

    Parameters
    ----------
    tmp_path : Path
        Per-test temporary repository.
    """
    (tmp_path / "RALPH_PROJECT.md").write_text("project instructions\n", encoding="utf-8")


def _write_tasks(path: Path, tasks: list[dict[str, object]]) -> None:
    """Write a JSON task ledger.

    Parameters
    ----------
    path : Path
        Destination ``TASKS.json`` file.
    tasks : list[dict[str, object]]
        Task contracts to serialize.
    """
    path.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")


def _task(task_id: str, **overrides: object) -> dict[str, object]:
    """Create a valid JSON task contract.

    Parameters
    ----------
    task_id : str
        Task identifier.
    **overrides : object
        Contract field replacements.

    Returns
    -------
    dict[str, object]
        Valid task contract.
    """
    task: dict[str, object] = {
        "id": task_id,
        "title": "A task",
        "status": "pending",
        "priority": 1,
        "depends_on": [],
        "requirements": ["Implement it."],
        "tests": ["Test it."],
        "acceptance_commands": ["uv run -m pytest"],
    }
    task.update(overrides)
    return task


def _configure_dry_run(monkeypatch: pytest.MonkeyPatch, repo: Path) -> None:
    """Stub external runner dependencies for a dry-run test.

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        Pytest monkeypatch fixture.
    repo : Path
        Expected Git repository root.
    """
    monkeypatch.setattr(codex_provider_module, "resolve_codex_executable", lambda value: value)
    monkeypatch.setattr(
        runner_module,
        "require_git_output",
        lambda target, *args: str(repo) if args == ("rev-parse", "--show-toplevel") else "before",
    )
    monkeypatch.setattr(runner_module, "require_clean_worktree", lambda repo: None)


def test_run_defaults_to_tasks_json_and_injects_only_selected_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Use ``TASKS.json`` and keep unselected contracts out of the prompt."""
    _write_tasks(
        tmp_path / "TASKS.json",
        [_task("TASK-001", priority=2, title="Later"), _task("TASK-002", priority=1, title="Selected")],
    )
    _configure_dry_run(monkeypatch, tmp_path)

    assert run(repo=tmp_path, dry_run=True) == ExitCode.SUCCESS

    output = capsys.readouterr().out
    assert "The parent runner selected `TASK-002`" in output
    assert '"title": "Selected"' in output
    assert '"title": "Later"' not in output
    assert "Do not read `TASKS.json` to select a task" in output


def test_run_accepts_an_explicit_tasks_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Allow callers to select a JSON ledger outside the default path."""
    ledger = tmp_path / "custom.json"
    _write_tasks(ledger, [_task("TASK-001")])
    _configure_dry_run(monkeypatch, tmp_path)

    assert run(repo=tmp_path, tasks_path=ledger, dry_run=True) == ExitCode.SUCCESS


def test_run_reports_missing_default_tasks_json_as_preflight_error(tmp_path: Path) -> None:
    """Reject an absent default JSON ledger before external dependencies."""
    assert run(repo=tmp_path) == ExitCode.PREFLIGHT_ERROR


def test_run_reports_invalid_json_as_preflight_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Turn invalid JSON into a runner preflight failure."""
    (tmp_path / "TASKS.json").write_text("{", encoding="utf-8")
    _configure_dry_run(monkeypatch, tmp_path)

    assert run(repo=tmp_path, dry_run=True) == ExitCode.PREFLIGHT_ERROR


def test_run_reports_invalid_utf8_as_preflight_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Turn an unreadable UTF-8 ledger into a runner preflight failure."""
    (tmp_path / "TASKS.json").write_bytes(b"\xff")
    _configure_dry_run(monkeypatch, tmp_path)

    assert run(repo=tmp_path, dry_run=True) == ExitCode.PREFLIGHT_ERROR


def test_prompt_formats_contract_as_json() -> None:
    """Format selected task contracts as readable JSON."""
    prompt = runner_module._prompt_for_selected_task("base", "TASK-001", _task("TASK-001"))

    assert "```json" in prompt
    assert '"id": "TASK-001"' in prompt
