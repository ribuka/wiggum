"""Parsing of the Ralph loop terminal status protocol."""

from __future__ import annotations

import re

TASK_COMPLETED_PATTERN = re.compile(r"TASK_COMPLETED: (TASK-\d{3})")
TASK_INCOMPLETE_PATTERN = re.compile(r"TASK_INCOMPLETE: (TASK-\d{3})")
TASK_BLOCKED_PATTERN = re.compile(r"TASK_BLOCKED: (TASK-\d{3})")


def _last_non_empty_line(message: str) -> str:
    """Return the last non-empty line from an agent message.

    Parameters
    ----------
    message : str
        Final Codex agent message.

    Returns
    -------
    str
        Last non-empty stripped line, or an empty string.
    """
    return next((line.strip() for line in reversed(message.splitlines()) if line.strip()), "")


def classify_output(message: str) -> tuple[str, str]:
    """Classify the Ralph protocol token in a final agent message.

    Parameters
    ----------
    message : str
        Final Codex agent message.

    Returns
    -------
    tuple[str, str]
        Protocol status and task ID.

    Raises
    ------
    ValueError
        If the last non-empty line is not a valid Ralph status token.
    """
    token = _last_non_empty_line(message)
    for status, pattern in (
        ("completed", TASK_COMPLETED_PATTERN),
        ("incompleted", TASK_INCOMPLETE_PATTERN),
        ("blocked", TASK_BLOCKED_PATTERN),
    ):
        match = pattern.fullmatch(token)
        if match:
            return status, match.group(1)

    raise ValueError(f"invalid Ralph status line: {token!r}")


def validate_selected_task(status: str, reported_task_id: str, selected_task_id: str) -> None:
    """Validate that Codex processed the task selected before its launch.

    Parameters
    ----------
    status : str
        Classified Ralph terminal status.
    reported_task_id : str
        Task identifier reported by Codex.
    selected_task_id : str
        Task identifier selected from the pre-launch ledger.

    Raises
    ------
    ValueError
        If the terminal status contradicts the pre-launch selection.
    """
    del status
    if reported_task_id != selected_task_id:
        raise ValueError(f"Codex reported {reported_task_id}, expected {selected_task_id}")
