"""Tests for provider-agnostic token-usage accounting."""

from __future__ import annotations

from wiggum.providers.usage.token_usage import TokenUsage


def test_token_usage_adds_counts_without_double_counting_reasoning() -> None:
    """Combine usage records and count reasoning as part of output tokens."""
    combined = TokenUsage(100, 80, 20, 5) + TokenUsage(50, 40, 10, 3)

    assert combined == TokenUsage(150, 120, 30, 8)
    assert combined.total_tokens == 180
