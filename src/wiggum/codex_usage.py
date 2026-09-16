"""Parse token usage from Codex JSONL event logs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class TokenUsage:
    """Token counts reported by completed Codex turns.

    Attributes
    ----------
    input_tokens : int
        Total input tokens, including cached input tokens.
    cached_input_tokens : int
        Input tokens served from the prompt cache.
    output_tokens : int
        Total output tokens, including reasoning output when reported that way
        by the selected model.
    reasoning_output_tokens : int
        Reasoning-token subset reported by Codex.
    """

    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_output_tokens: int = 0

    def __add__(self, other: TokenUsage) -> TokenUsage:
        """Combine two token-usage records.

        Parameters
        ----------
        other : TokenUsage
            Usage record to add.

        Returns
        -------
        TokenUsage
            Field-wise sum of both records.
        """
        if not isinstance(other, TokenUsage):
            return NotImplemented
        return TokenUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            cached_input_tokens=(
                self.cached_input_tokens + other.cached_input_tokens
            ),
            output_tokens=self.output_tokens + other.output_tokens,
            reasoning_output_tokens=(
                self.reasoning_output_tokens + other.reasoning_output_tokens
            ),
        )

    @property
    def total_tokens(self) -> int:
        """Return total input and output tokens without double-counting reasoning.

        Returns
        -------
        int
            Sum of input and output tokens.
        """
        return self.input_tokens + self.output_tokens


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
