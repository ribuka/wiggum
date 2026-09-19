"""Parse token usage from Codex JSONL event logs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from wiggum.providers.usage.token_usage import TokenUsage

__all__ = ["TokenUsage", "read_codex_usage"]


def _nonnegative_int(value: Any) -> int:
    """Return a non-negative integer value or zero for invalid input.

    Parameters
    ----------
    value : Any
        Untrusted value from a Codex JSON event.

    Returns
    -------
    int
        Parsed non-negative integer, or zero.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def read_codex_usage(log_path: Path) -> TokenUsage:
    """Sum token usage from completed-turn events in a Codex JSONL log.

    Non-JSON lines are ignored because Codex diagnostic output written to
    standard error can share the runner's combined log with JSON events.

    Parameters
    ----------
    log_path : Path
        Combined Codex process log.

    Returns
    -------
    TokenUsage
        Sum of every valid ``turn.completed`` usage object in the log. An
        unreadable log or a log without usage events produces all-zero usage.
    """
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return TokenUsage()

    total = TokenUsage()
    for line in lines:
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(event, dict) or event.get("type") != "turn.completed":
            continue
        usage = event.get("usage")
        if not isinstance(usage, dict):
            continue
        total += TokenUsage(
            input_tokens=_nonnegative_int(usage.get("input_tokens")),
            cached_input_tokens=_nonnegative_int(usage.get("cached_input_tokens")),
            output_tokens=_nonnegative_int(usage.get("output_tokens")),
            reasoning_output_tokens=_nonnegative_int(
                usage.get("reasoning_output_tokens")
            ),
        )
    return total
