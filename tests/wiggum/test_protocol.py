"""Tests for the Ralph loop terminal status protocol."""

from __future__ import annotations

import pytest

from wiggum.protocol import classify_output, validate_selected_task


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("TASK_COMPLETED: TASK-001", ("completed", "TASK-001")),
        ("TASK_INCOMPLETE: TASK-002", ("incompleted", "TASK-002")),
        ("TASK_BLOCKED: TASK-003", ("blocked", "TASK-003")),
    ],
)
def test_classify_output_uses_last_non_empty_line(
    token: str,
    expected: tuple[str, str],
) -> None:
    """Recognize each valid terminal status after a human-readable summary."""
    message = f"Loop summary\n\n{token}\n"
    assert classify_output(message) == expected


@pytest.mark.parametrize(
    "message",
    [
        "",
        "TASK_COMPLETED: task-001",
        "TASK_COMPLETED: TASK-1",
        "TASK_COMPLETED: TASK-001 trailing text",
        "TASK_COMPLETED: TASK-001\nsummary after token",
        "ALL_TASKS_COMPLETED",
    ],
)
def test_classify_output_rejects_invalid_terminal_status(message: str) -> None:
    """Reject missing, malformed, or non-terminal Ralph status tokens."""
    with pytest.raises(ValueError, match="invalid Ralph status line"):
        classify_output(message)


def test_validate_selected_task_accepts_a_matching_reported_task() -> None:
    """Accept a terminal token for the task that was selected before launch."""
    validate_selected_task("completed", "TASK-002", "TASK-002")


def test_validate_selected_task_rejects_a_different_reported_task() -> None:
    """Reject a terminal token for a task other than the pre-launch selection."""
    with pytest.raises(ValueError, match="reported TASK-003, expected TASK-002"):
        validate_selected_task("completed", "TASK-003", "TASK-002")
