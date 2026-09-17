"""Tests for Codex JSONL token-usage parsing."""

from __future__ import annotations

from pathlib import Path

from wiggum.codex_usage import read_codex_usage
from wiggum.token_usage import TokenUsage


def test_read_codex_usage_sums_completed_turns_and_ignores_other_lines(
    tmp_path: Path,
) -> None:
    """Parse completed turns while tolerating mixed diagnostic output."""
    log_path = tmp_path / "codex.log"
    log_path.write_text(
        "diagnostic output\n"
        '{"type":"turn.started"}\n'
        '{"type":"turn.completed","usage":{"input_tokens":100,'
        '"cached_input_tokens":80,"output_tokens":20,'
        '"reasoning_output_tokens":5}}\n'
        '{"type":"turn.completed","usage":{"input_tokens":50,'
        '"cached_input_tokens":40,"output_tokens":10,'
        '"reasoning_output_tokens":3}}\n',
        encoding="utf-8",
    )

    assert read_codex_usage(log_path) == TokenUsage(150, 120, 30, 8)


def test_read_codex_usage_treats_missing_or_invalid_counts_as_zero(
    tmp_path: Path,
) -> None:
    """Avoid failing a run because a usage event is partial or malformed."""
    log_path = tmp_path / "codex.log"
    log_path.write_text(
        '{"type":"turn.completed","usage":{"input_tokens":-1,'
        '"cached_input_tokens":true,"output_tokens":"10"}}\n',
        encoding="utf-8",
    )

    assert read_codex_usage(log_path) == TokenUsage()


def test_read_codex_usage_returns_zero_for_an_unreadable_log(tmp_path: Path) -> None:
    """Return zero usage when the requested log does not exist."""
    assert read_codex_usage(tmp_path / "missing.log") == TokenUsage()
