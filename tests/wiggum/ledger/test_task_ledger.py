"""Tests for JSON Ralph task ledger validation and selection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wiggum.ledger.task_ledger import (
    read_ralph_tasks,
    read_task_contract,
    task_progress,
    task_snapshot,
)


def _task(task_id: str, **overrides: Any) -> dict[str, object]:
    """Create a valid task object with optional field overrides.

    Parameters
    ----------
    task_id : str
        Task identifier.
    **overrides : Any
        Replacement field values.

    Returns
    -------
    dict[str, object]
        Valid task object.
    """
    value: dict[str, object] = {
        "id": task_id,
        "title": f"Title for {task_id}",
        "status": "pending",
        "priority": 1,
        "depends_on": [],
        "requirements": ["Implement the behavior."],
        "tests": ["Add focused coverage."],
        "acceptance_commands": ["uv run -m pytest"],
    }
    value.update(overrides)
    return value


def _write_ledger(path: Path, tasks: list[dict[str, object]]) -> None:
    """Write JSON task objects to a ledger path.

    Parameters
    ----------
    path : Path
        Destination ledger path.
    tasks : list[dict[str, object]]
        Task objects to serialize.
    """
    path.write_text(json.dumps({"tasks": tasks}), encoding="utf-8")


def test_task_progress_counts_every_non_completed_status(tmp_path: Path) -> None:
    """Count pending, in-progress, and blocked tasks as incomplete."""
    path = tmp_path / "TASKS.json"
    _write_ledger(path, [_task("TASK-001", status="completed"), _task("TASK-002", status="pending"), _task("TASK-003", status="in_progress"), _task("TASK-004", status="blocked")])

    assert task_progress(path) == (3, 4)


def test_snapshot_selects_by_dependencies_priority_and_id(tmp_path: Path) -> None:
    """Select the lowest-priority eligible task, then its ID."""
    path = tmp_path / "TASKS.json"
    _write_ledger(path, [_task("TASK-001", status="completed"), _task("TASK-004", priority=1, depends_on=["TASK-003"]), _task("TASK-003", priority=2, depends_on=["TASK-001"]), _task("TASK-002", priority=2, depends_on=["TASK-001"])])

    assert task_snapshot(path) == (3, 4, "TASK-002")


def test_snapshot_returns_none_when_no_task_is_eligible(tmp_path: Path) -> None:
    """Report no candidate when dependencies are incomplete."""
    path = tmp_path / "TASKS.json"
    _write_ledger(path, [_task("TASK-001", status="blocked"), _task("TASK-002", depends_on=["TASK-001"])])

    assert task_snapshot(path) == (2, 2, None)


def test_read_task_contract_returns_only_selected_json_object(tmp_path: Path) -> None:
    """Return the full JSON contract for the requested task."""
    path = tmp_path / "TASKS.json"
    selected = _task("TASK-002", requirements=["Preserve this text."])
    _write_ledger(path, [_task("TASK-001"), selected, _task("TASK-003")])

    assert read_task_contract(path, "TASK-002") == selected


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ("{", "invalid JSON"),
        (json.dumps({"tasks": []}), "non-empty array"),
        (json.dumps({"tasks": [_task("TASK-1")]}), "invalid id"),
        (json.dumps({"tasks": [_task("TASK-001", status="done")]}), "invalid status"),
        (json.dumps({"tasks": [_task("TASK-001", priority=0)]}), "invalid priority"),
        (json.dumps({"tasks": [_task("TASK-001", title="")]}), "invalid title"),
        (json.dumps({"tasks": [_task("TASK-001", requirements=[])]}), "invalid requirements"),
        (json.dumps({"tasks": [_task("TASK-001", extra="no")]}), "unknown keys"),
    ],
)
def test_read_ralph_tasks_rejects_invalid_json_or_schema(tmp_path: Path, document: str, message: str) -> None:
    """Reject malformed documents and invalid fixed-schema fields."""
    path = tmp_path / "TASKS.json"
    path.write_text(document, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        read_ralph_tasks(path)


def test_read_ralph_tasks_rejects_duplicate_and_invalid_dependencies(tmp_path: Path) -> None:
    """Reject duplicate IDs, undefined dependencies, and self-dependencies."""
    path = tmp_path / "TASKS.json"
    _write_ledger(path, [_task("TASK-001"), _task("TASK-001")])
    with pytest.raises(ValueError, match="duplicate task IDs"):
        read_ralph_tasks(path)

    _write_ledger(path, [_task("TASK-001", depends_on=["TASK-999"])])
    with pytest.raises(ValueError, match="unknown task dependencies"):
        read_ralph_tasks(path)

    _write_ledger(path, [_task("TASK-001", depends_on=["TASK-001"])])
    with pytest.raises(ValueError, match="cannot depend on itself"):
        read_ralph_tasks(path)
