"""Monitor Codex JSONL events for truncated tool outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wiggum.providers.process_output import iter_json_events

_TOOL_ITEM_TYPES = frozenset({"command_execution", "mcp_tool_call"})
_TRUNCATION_KEYS = frozenset({"truncated", "is_truncated", "output_truncated", "was_truncated"})


@dataclass(frozen=True)
class ToolOutputMonitor:
    """Counts observed tool outputs and explicit truncation signals.

    Attributes
    ----------
    outputs : int
        Number of completed command or MCP tool outputs observed.
    truncated_outputs : int
        Number of those outputs marked as truncated by Codex.
    """

    outputs: int = 0
    truncated_outputs: int = 0


def _contains_truncation_signal(value: object) -> bool:
    """Return whether a JSON value contains an explicit truncation signal.

    Parameters
    ----------
    value : object
        Untrusted value from a Codex JSON event.

    Returns
    -------
    bool
        ``True`` when a recognized truncation field is set to ``true``.
    """
    if isinstance(value, dict):
        for key, nested_value in value.items():
            if key in _TRUNCATION_KEYS and nested_value is True:
                return True
            if _contains_truncation_signal(nested_value):
                return True
    elif isinstance(value, list):
        return any(_contains_truncation_signal(item) for item in value)
    return False


def read_tool_output_monitor(log_path: Path) -> ToolOutputMonitor:
    """Read completed tool-output observations from a Codex JSONL log.

    The Codex JSONL stream can contain non-JSON diagnostic lines because the
    runner combines standard output and standard error. Those lines and unknown
    event shapes are ignored. A warning is emitted only when Codex explicitly
    marks a completed tool output as truncated; the monitor never estimates
    token counts from character length.

    Parameters
    ----------
    log_path : Path
        Combined Codex process log.

    Returns
    -------
    ToolOutputMonitor
        Counts of completed tool outputs and explicit truncation signals.
    """
    outputs = 0
    truncated_outputs = 0
    for event in iter_json_events(log_path):
        if event.get("type") != "item.completed":
            continue
        item = event.get("item")
        if not isinstance(item, dict) or item.get("type") not in _TOOL_ITEM_TYPES:
            continue
        outputs += 1
        if _contains_truncation_signal(item):
            truncated_outputs += 1
    return ToolOutputMonitor(outputs, truncated_outputs)
