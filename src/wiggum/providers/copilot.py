"""GitHub Copilot CLI adapter: wraps Copilot process functions behind ProviderAdapter."""

from __future__ import annotations

from pathlib import Path

from wiggum.copilot_process import (
    build_copilot_command,
    is_retryable_copilot_failure,
    resolve_copilot_executable,
    run_copilot,
)
from wiggum.providers.constants import COPILOT
from wiggum.providers.contract import CommandOptions, ProviderAdapter
from wiggum.token_usage import TokenUsage


def build_command(options: CommandOptions) -> list[str]:
    """Build the non-interactive GitHub Copilot CLI command for one loop.

    Parameters
    ----------
    options : CommandOptions
        Uniform command options for this loop.

    Returns
    -------
    list[str]
        Copilot subprocess argument vector.
    """
    return build_copilot_command(
        options.executable,
        options.model,
        options.auto_approve,
        reasoning_effort=options.reasoning_effort,
    )


def read_usage(log_path: Path) -> TokenUsage:
    """Return zero token usage for a Copilot attempt.

    Parameters
    ----------
    log_path : Path
        Unused; GitHub Copilot CLI exposes no machine-readable per-turn
        usage event comparable to Codex's ``turn.completed`` JSONL event.

    Returns
    -------
    TokenUsage
        All-zero usage.
    """
    del log_path
    return TokenUsage()


def adapter() -> ProviderAdapter:
    """Build a fresh GitHub Copilot ProviderAdapter.

    Returns
    -------
    ProviderAdapter
        Adapter wired to this module's Copilot-specific functions, looked up
        from this module's own globals at call time so tests can monkeypatch
        them here.
    """
    return ProviderAdapter(
        name=COPILOT,
        resolve_executable=resolve_copilot_executable,
        build_command=build_command,
        run=run_copilot,
        is_retryable_failure=is_retryable_copilot_failure,
        read_usage=read_usage,
    )
