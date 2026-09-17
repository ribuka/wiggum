"""Provider adapter contract shared by every AI model vendor implementation.

Codex CLI and GitHub Copilot CLI each expose their own executable resolution,
command construction, process execution, retry-failure detection, and
token-usage reporting. This module defines the uniform interface those
per-provider implementations must satisfy so ``wiggum.runner`` only
orchestrates the Ralph loop and never branches on the selected provider.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from wiggum.token_usage import TokenUsage


@dataclass(frozen=True)
class CommandOptions:
    """Options needed to build one loop's non-interactive provider command.

    Attributes
    ----------
    executable : str
        Resolved provider executable path.
    repo : Path
        Repository working directory.
    output_path : Path
        File that will receive the provider's final message.
    model : str | None
        Optional model override.
    auto_approve : bool
        Whether tool/approval requests should be granted automatically.
    reasoning_effort : str
        Requested reasoning effort.
    model_verbosity : str
        Requested model verbosity. Codex-only.
    tool_output_token_limit : int
        Maximum tokens retained from one tool output. Codex-only.
    lean : bool
        Whether user configuration and reasoning summaries should be
        ignored. Codex-only.
    """

    executable: str
    repo: Path
    output_path: Path
    model: str | None
    auto_approve: bool
    reasoning_effort: str
    model_verbosity: str
    tool_output_token_limit: int
    lean: bool


RunCallable = Callable[
    [list[str], Path, Path, dict[str, str], str, Path, int],
    "subprocess.CompletedProcess[str]",
]


@dataclass(frozen=True)
class ProviderAdapter:
    """Uniform process-lifecycle operations for one AI model vendor.

    Attributes
    ----------
    name : str
        Provider name; one of :data:`wiggum.providers.PROVIDERS`.
    resolve_executable : Callable[[str], str | None]
        Resolve an executable name or path to an absolute path.
    build_command : Callable[[CommandOptions], list[str]]
        Build the non-interactive command for one loop.
    run : RunCallable
        Run the provider command for one loop, taking ``(command, repo,
        log_path, environment, prompt, output_path, timeout_sec)``.
    is_retryable_failure : Callable[[Path], bool]
        Return whether a failed attempt's log indicates a transient
        transport failure worth retrying.
    read_usage : Callable[[Path], TokenUsage]
        Parse token usage reported by one attempt's log.
    """

    name: str
    resolve_executable: Callable[[str], str | None]
    build_command: Callable[[CommandOptions], list[str]]
    run: RunCallable
    is_retryable_failure: Callable[[Path], bool]
    read_usage: Callable[[Path], TokenUsage]
