"""Provider adapter registry for the Ralph loop runner.

Codex CLI and GitHub Copilot CLI each expose their own executable
resolution, command construction, process execution, retry-failure
detection, and token-usage reporting. This module wraps those provider
implementations behind one uniform :class:`ProviderAdapter` interface so
``wiggum.runner`` only orchestrates the Ralph loop and never branches on
``provider`` itself.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from wiggum.codex_process import (
    build_codex_command,
    is_retryable_codex_failure,
    resolve_codex_executable,
    run_codex,
)
from wiggum.codex_usage import TokenUsage, read_codex_usage
from wiggum.copilot_process import (
    build_copilot_command,
    is_retryable_copilot_failure,
    resolve_copilot_executable,
    run_copilot,
)
from wiggum.providers import CODEX, COPILOT, PROVIDERS


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


def _codex_build_command(options: CommandOptions) -> list[str]:
    return build_codex_command(
        options.executable,
        options.repo,
        options.output_path,
        options.model,
        options.auto_approve,
        reasoning_effort=options.reasoning_effort,
        model_verbosity=options.model_verbosity,
        tool_output_token_limit=options.tool_output_token_limit,
        lean=options.lean,
    )


def _codex_run(
    command: list[str],
    repo: Path,
    log_path: Path,
    environment: dict[str, str],
    prompt: str,
    output_path: Path,
    timeout_sec: int,
) -> subprocess.CompletedProcess[str]:
    del output_path  # Codex writes its own file via --output-last-message.
    return run_codex(command, repo, log_path, environment, prompt, timeout_sec)


def _copilot_build_command(options: CommandOptions) -> list[str]:
    return build_copilot_command(
        options.executable,
        options.model,
        options.auto_approve,
        reasoning_effort=options.reasoning_effort,
    )


def _copilot_read_usage(log_path: Path) -> TokenUsage:
    del log_path  # GitHub Copilot CLI exposes no comparable usage event.
    return TokenUsage()


def _codex_adapter() -> ProviderAdapter:
    return ProviderAdapter(
        name=CODEX,
        resolve_executable=resolve_codex_executable,
        build_command=_codex_build_command,
        run=_codex_run,
        is_retryable_failure=is_retryable_codex_failure,
        read_usage=read_codex_usage,
    )


def _copilot_adapter() -> ProviderAdapter:
    return ProviderAdapter(
        name=COPILOT,
        resolve_executable=resolve_copilot_executable,
        build_command=_copilot_build_command,
        run=run_copilot,
        is_retryable_failure=is_retryable_copilot_failure,
        read_usage=_copilot_read_usage,
    )


_ADAPTER_FACTORIES: dict[str, Callable[[], ProviderAdapter]] = {
    CODEX: _codex_adapter,
    COPILOT: _copilot_adapter,
}


def get_adapter(provider: str) -> ProviderAdapter:
    """Return the process-lifecycle adapter for one AI model vendor.

    Parameters
    ----------
    provider : str
        Selected AI model vendor; one of :data:`wiggum.providers.PROVIDERS`.

    Returns
    -------
    ProviderAdapter
        Adapter exposing executable resolution, command construction,
        process execution, retry-failure detection, and usage parsing for
        ``provider``.

    Raises
    ------
    ValueError
        If ``provider`` is not one of :data:`wiggum.providers.PROVIDERS`.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"--provider has an unsupported value: {provider}")
    return _ADAPTER_FACTORIES[provider]()
