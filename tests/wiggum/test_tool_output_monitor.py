"""Tests for Codex tool-output limit monitoring."""

from __future__ import annotations

from pathlib import Path

from wiggum.tool_output_monitor import ToolOutputMonitor, read_tool_output_monitor


def test_read_tool_output_monitor_counts_completed_tool_outputs(
    tmp_path: Path,
) -> None:
    """Count command and MCP output events without inferring token counts."""
    log_path = tmp_path / "codex.log"
    log_path.write_text(
        "diagnostic output\n"
        '{"type":"item.completed","item":{"type":"command_execution"}}\n'
        '{"type":"item.completed","item":{"type":"mcp_tool_call",'
        '"metadata":{"truncated":true}}}\n'
        '{"type":"item.completed","item":{"type":"agent_message",'
        '"truncated":true}}\n',
        encoding="utf-8",
    )

    assert read_tool_output_monitor(log_path) == ToolOutputMonitor(2, 1)


def test_read_tool_output_monitor_returns_zero_for_missing_or_invalid_logs(
    tmp_path: Path,
) -> None:
    """Ignore unavailable logs and malformed JSON events."""
    assert read_tool_output_monitor(tmp_path / "missing.log") == ToolOutputMonitor()

    log_path = tmp_path / "codex.log"
    log_path.write_text("not json\n", encoding="utf-8")

    assert read_tool_output_monitor(log_path) == ToolOutputMonitor()
