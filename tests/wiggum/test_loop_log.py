"""Tests for loop log file naming, creation, and finalization."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from wiggum.loop_log import create_running_log, finalize_log


def test_create_running_log_uses_task_number_and_timestamp(tmp_path: Path) -> None:
    """Name the running log after the start time and zero-padded task number."""
    started_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    running_path = create_running_log(tmp_path, started_at, "TASK-007")

    assert running_path == tmp_path / "ralph_20260102T030405_007_running.log"
    assert running_path.is_file()


def test_create_running_log_uses_zero_for_missing_task_id(tmp_path: Path) -> None:
    """Fall back to task number zero when no task was selected."""
    started_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)

    running_path = create_running_log(tmp_path, started_at, None)

    assert running_path.name == "ralph_20260102T030405_000_running.log"


def test_create_running_log_advances_timestamp_on_collision(tmp_path: Path) -> None:
    """Avoid overwriting an existing running log with the same second and task."""
    started_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    first = create_running_log(tmp_path, started_at, "TASK-001")

    second = create_running_log(tmp_path, started_at, "TASK-001")

    assert first != second
    assert second.name == "ralph_20260102T030406_001_running.log"


def test_finalize_log_renames_to_status_suffixed_filename(tmp_path: Path) -> None:
    """Move the running log to a filename carrying the final loop status."""
    started_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    running_path = create_running_log(tmp_path, started_at, "TASK-009")
    running_path.write_text("codex output\n", encoding="utf-8")

    final_path = finalize_log(running_path, tmp_path, started_at, "TASK-009", "completed")

    assert final_path == tmp_path / "ralph_20260102T030405_009_completed.log"
    assert final_path.read_text(encoding="utf-8") == "codex output\n"
    assert not running_path.exists()


def test_finalize_log_advances_timestamp_on_collision(tmp_path: Path) -> None:
    """Avoid overwriting an existing finalized log with the same name."""
    started_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    (tmp_path / "ralph_20260102T030405_009_completed.log").write_text("", encoding="utf-8")
    running_path = create_running_log(tmp_path, started_at, "TASK-009")

    final_path = finalize_log(running_path, tmp_path, started_at, "TASK-009", "completed")

    assert final_path.name == "ralph_20260102T030406_009_completed.log"
