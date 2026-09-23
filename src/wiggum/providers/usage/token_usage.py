"""Provider-agnostic token-usage accounting for one Ralph loop attempt."""

from __future__ import annotations

from dataclasses import dataclass


def nonnegative_int(value: object) -> int:
    """Return a non-negative integer value or zero for invalid input.

    Parameters
    ----------
    value : object
        Untrusted value from a provider JSON event.

    Returns
    -------
    int
        Parsed non-negative integer, or zero.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


@dataclass(frozen=True)
class TokenUsage:
    """Token counts reported by one completed provider attempt.

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
        Reasoning-token subset reported by the provider.
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
            cached_input_tokens=(self.cached_input_tokens + other.cached_input_tokens),
            output_tokens=self.output_tokens + other.output_tokens,
            reasoning_output_tokens=(self.reasoning_output_tokens + other.reasoning_output_tokens),
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
