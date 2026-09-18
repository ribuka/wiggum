"""Claude Code CLI adapter: wraps Claude Code process functions behind ProviderAdapter."""

from __future__ import annotations

from wiggum.claude_process import (
    build_claude_command,
    is_retryable_claude_failure,
    read_claude_usage,
    resolve_claude_executable,
    run_claude,
)
from wiggum.providers.constants import CLAUDE
from wiggum.providers.contract import CommandOptions, ProviderAdapter


def build_command(options: CommandOptions) -> list[str]:
    """Build the non-interactive Claude Code CLI command for one loop.

    Parameters
    ----------
    options : CommandOptions
        Uniform command options for this loop.

    Returns
    -------
    list[str]
        Claude Code subprocess argument vector.
    """
    return build_claude_command(options.executable, options.model, options.auto_approve)


def adapter() -> ProviderAdapter:
    """Build a fresh Claude Code ProviderAdapter.

    Returns
    -------
    ProviderAdapter
        Adapter wired to this module's Claude Code-specific functions, looked
        up from this module's own globals at call time so tests can
        monkeypatch them here.
    """
    return ProviderAdapter(
        name=CLAUDE,
        resolve_executable=resolve_claude_executable,
        build_command=build_command,
        run=run_claude,
        is_retryable_failure=is_retryable_claude_failure,
        read_usage=read_claude_usage,
    )
