"""Parse and inspect provider process output."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def decode_stream_output(output: str | bytes | None) -> str:
    """Decode subprocess output that may be text, bytes, or absent.

    Parameters
    ----------
    output : str | bytes | None
        Captured standard output or standard error. ``TimeoutExpired`` carries
        raw bytes even when a subprocess was configured with ``text=True``.

    Returns
    -------
    str
        Decoded text, or an empty string when ``output`` is ``None``.
    """
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


def iter_json_events(log_path: Path) -> Iterator[dict[str, Any]]:
    """Yield JSON object events from a UTF-8 JSONL process log.

    Parameters
    ----------
    log_path : Path
        Combined process log, which may include diagnostic non-JSON lines.

    Yields
    ------
    dict[str, Any]
        Each JSON object event in log order. Invalid lines and unreadable logs
        are ignored.
    """
    try:
        output = log_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return
    yield from iter_json_events_from_text(output)


def iter_json_events_from_text(output: str) -> Iterator[dict[str, Any]]:
    """Yield JSON object events from JSONL text.

    Parameters
    ----------
    output : str
        JSONL output that may contain diagnostic non-JSON lines.

    Yields
    ------
    dict[str, Any]
        Each JSON object event in input order. Invalid lines are ignored.
    """
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if isinstance(event, dict):
            yield event


def log_contains_any(log_path: Path, markers: tuple[str, ...]) -> bool:
    """Return whether a UTF-8 process log contains any supplied marker.

    Parameters
    ----------
    log_path : Path
        Process log to inspect.
    markers : tuple[str, ...]
        Marker strings that identify transient failures.

    Returns
    -------
    bool
        ``True`` if any marker occurs in a readable log.
    """
    try:
        output = log_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    return any(marker in output for marker in markers)
