"""Process exit codes produced by the Ralph loop runner."""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    """Process exit codes produced by the Ralph loop runner."""

    SUCCESS = 0
    CODEX_FAILURE = 10
    PROTOCOL_ERROR = 11
    GIT_STATE_ERROR = 12
    TASK_INCOMPLETE = 20
    TASK_BLOCKED = 21
    MAX_LOOPS_REACHED = 22
    PREFLIGHT_ERROR = 23
