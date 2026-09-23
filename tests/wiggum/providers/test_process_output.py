"""Tests for provider process-output parsing helpers."""

from __future__ import annotations

from pathlib import Path

from wiggum.providers.process_output import (
    decode_stream_output,
    iter_json_events,
    log_contains_any,
)


def test_decode_stream_output_handles_all_subprocess_output_types() -> None:
    """Convert bytes and absent subprocess output into text."""
    assert decode_stream_output(b"valid\xff") == "valid�"
    assert decode_stream_output("text") == "text"
    assert decode_stream_output(None) == ""


def test_iter_json_events_ignores_invalid_lines_and_non_object_values(tmp_path: Path) -> None:
    """Yield only JSON objects from a mixed JSONL process log."""
    log_path = tmp_path / "provider.log"
    log_path.write_text('noise\n["array"]\n{"type":"result"}\n', encoding="utf-8")

    assert list(iter_json_events(log_path)) == [{"type": "result"}]


def test_log_contains_any_handles_markers_and_unreadable_logs(tmp_path: Path) -> None:
    """Find known markers without failing for an absent log."""
    log_path = tmp_path / "provider.log"
    log_path.write_text("transient network error", encoding="utf-8")

    assert log_contains_any(log_path, ("network error",))
    assert not log_contains_any(log_path, ("rate limit",))
    assert not log_contains_any(tmp_path / "missing.log", ("network error",))
