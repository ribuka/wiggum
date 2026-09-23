"""Parse token usage from Codex JSONL event logs."""

from __future__ import annotations

from pathlib import Path

from wiggum.providers.process_output import iter_json_events
from wiggum.providers.usage.token_usage import TokenUsage, nonnegative_int

__all__ = ["TokenUsage", "read_codex_usage"]


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
    total = TokenUsage()
    for event in iter_json_events(log_path):
        if event.get("type") != "turn.completed":
            continue
        usage = event.get("usage")
        if not isinstance(usage, dict):
            continue
        total += TokenUsage(
            input_tokens=nonnegative_int(usage.get("input_tokens")),
            cached_input_tokens=nonnegative_int(usage.get("cached_input_tokens")),
            output_tokens=nonnegative_int(usage.get("output_tokens")),
            reasoning_output_tokens=nonnegative_int(usage.get("reasoning_output_tokens")),
        )
    return total
