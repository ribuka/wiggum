"""Loop log file naming, creation, and finalization under ``logs/``."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path


def create_running_log(logs_directory: Path, started_at: datetime, task_id: str | None) -> Path:
    """Create an empty log using the known start-time and task identifier.

    Parameters
    ----------
    logs_directory : Path
        Directory that stores loop logs.
    started_at : datetime
        Time at which the loop started.
    task_id : str | None
        Ralph task identifier selected before the loop starts.

    Returns
    -------
    Path
        Newly created running log path in the form
        ``ralph_YYYYMMDDTHHMMSS_NNN_running.log``.
    """
    task_number = int(task_id.removeprefix("TASK-")) if task_id is not None else 0
    timestamp = started_at
    while True:
        filename = f"ralph_{timestamp:%Y%m%dT%H%M%S}_{task_number:03d}_running.log"
        running_path = logs_directory / filename
        try:
            with running_path.open("x", encoding="utf-8"):
                pass
        except FileExistsError:
            timestamp += timedelta(seconds=1)
        else:
            return running_path


def finalize_log(
    temporary_path: Path,
    logs_directory: Path,
    started_at: datetime,
    task_id: str | None,
    status: str,
) -> Path:
    """Move a loop log to its final, descriptive filename.

    Parameters
    ----------
    temporary_path : Path
        Path of the log written while the loop was running.
    logs_directory : Path
        Directory that stores finalized logs.
    started_at : datetime
        Time at which the loop started.
    task_id : str | None
        Ralph task identifier, if a valid task result was reported.
    status : str
        Final loop status.

    Returns
    -------
    Path
        Final log path in the form
        ``ralph_YYYYMMDDTHHMMSS_NNN_status.log``.
    """
    task_number = int(task_id.removeprefix("TASK-")) if task_id is not None else 0
    timestamp = started_at
    while True:
        filename = f"ralph_{timestamp:%Y%m%dT%H%M%S}_{task_number:03d}_{status}.log"
        final_path = logs_directory / filename
        if not final_path.exists():
            temporary_path.replace(final_path)
            return final_path
        timestamp += timedelta(seconds=1)
