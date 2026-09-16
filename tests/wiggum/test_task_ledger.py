"""Tests for Ralph task ledger parsing and selection."""

from __future__ import annotations

from pathlib import Path

import pytest

from wiggum.task_ledger import (
    read_ralph_tasks,
    read_task_section,
    task_progress,
    task_snapshot,
)


def test_task_progress_counts_uncompleted_tasks(tmp_path: Path) -> None:
    """Count every task while treating only completed status as resolved."""
    task_file = tmp_path / "TASKS.md"
    task_file.write_text(
        """## TASK-001: first

- Status: completed
- Priority: 1
- Depends on: none

## TASK-002: second

- Status: pending
- Priority: 2
- Depends on: TASK-001

## TASK-003: third

- Status: blocked
- Priority: 3
- Depends on: TASK-002""",
        encoding="utf-8",
    )

    assert task_progress(task_file) == (2, 3)


def test_task_snapshot_selects_by_dependencies_priority_and_id(tmp_path: Path) -> None:
    """Select the lowest-priority eligible task and use its ID as a tie-breaker."""
    task_file = tmp_path / "TASKS.md"
    task_file.write_text(
        """## TASK-001: completed dependency

- Status: completed
- Priority: 1
- Depends on: none

## TASK-004: blocked by an incomplete dependency

- Status: pending
- Priority: 1
- Depends on: TASK-003

## TASK-003: eligible later ID

- Status: pending
- Priority: 2
- Depends on: TASK-001

## TASK-002: eligible earlier ID

- Status: pending
- Priority: 2
- Depends on: TASK-001
""",
        encoding="utf-8",
    )

    assert task_snapshot(task_file) == (3, 4, "TASK-002")


def test_task_snapshot_returns_none_when_no_task_is_eligible(tmp_path: Path) -> None:
    """Report no eligible task when every pending task has an incomplete dependency."""
    task_file = tmp_path / "TASKS.md"
    task_file.write_text(
        """## TASK-001: blocked

- Status: blocked
- Priority: 1
- Depends on: none

## TASK-002: dependent

- Status: pending
- Priority: 2
- Depends on: TASK-001
""",
        encoding="utf-8",
    )

    assert task_snapshot(task_file) == (2, 2, None)


def test_read_task_section_returns_only_the_requested_task(tmp_path: Path) -> None:
    """Return a task heading and body without adjacent task sections."""
    task_file = tmp_path / "TASKS.md"
    task_file.write_text(
        """## TASK-001: first

- Status: completed

## TASK-002: selected

- Status: pending
- Requirements: preserve this text

## TASK-003: later

- Status: pending
""",
        encoding="utf-8",
    )

    assert read_task_section(task_file, "TASK-002") == (
        "## TASK-002: selected\n\n- Status: pending\n"
        "- Requirements: preserve this text"
    )


def test_read_task_section_rejects_an_unknown_task(tmp_path: Path) -> None:
    """Reject a request for a task identifier that has no section."""
    task_file = tmp_path / "TASKS.md"
    task_file.write_text("## TASK-001: only task\n", encoding="utf-8")

    with pytest.raises(ValueError, match="task section not found: TASK-002"):
        read_task_section(task_file, "TASK-002")


def test_read_ralph_tasks_rejects_missing_status_field(tmp_path: Path) -> None:
    """Reject a task section missing the required Status field."""
    task_file = tmp_path / "TASKS.md"
    task_file.write_text(
        """## TASK-001: missing status

- Priority: 1
- Depends on: none
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="TASK-001 has no Status field"):
        read_ralph_tasks(task_file)


def test_read_ralph_tasks_rejects_invalid_status_value(tmp_path: Path) -> None:
    """Reject a Status value outside the allowed set."""
    task_file = tmp_path / "TASKS.md"
    task_file.write_text(
        """## TASK-001: invalid status

- Status: done
- Priority: 1
- Depends on: none
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="TASK-001 has invalid status: done"):
        read_ralph_tasks(task_file)


def test_read_ralph_tasks_rejects_duplicate_task_ids(tmp_path: Path) -> None:
    """Reject a ledger that declares the same task ID twice."""
    task_file = tmp_path / "TASKS.md"
    task_file.write_text(
        """## TASK-001: first

- Status: pending
- Priority: 1
- Depends on: none

## TASK-001: duplicate

- Status: pending
- Priority: 2
- Depends on: none
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate task IDs"):
        read_ralph_tasks(task_file)


def test_read_ralph_tasks_rejects_unknown_dependency(tmp_path: Path) -> None:
    """Reject a task that depends on an identifier absent from the ledger."""
    task_file = tmp_path / "TASKS.md"
    task_file.write_text(
        """## TASK-001: dangling dependency

- Status: pending
- Priority: 1
- Depends on: TASK-999
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unknown task dependencies: TASK-999"):
        read_ralph_tasks(task_file)


def test_read_ralph_tasks_rejects_empty_ledger(tmp_path: Path) -> None:
    """Reject a ledger file that defines no tasks."""
    task_file = tmp_path / "TASKS.md"
    task_file.write_text("# Tasks\n\nNo tasks yet.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="no tasks found"):
        read_ralph_tasks(task_file)
