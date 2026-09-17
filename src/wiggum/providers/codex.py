"""Codex CLI adapter: wraps Codex process functions behind ProviderAdapter."""

from __future__ import annotations

import subprocess
from pathlib import Path

from wiggum.codex_process import (
    build_codex_command,
    is_retryable_codex_failure,
    resolve_codex_executable,
    run_codex,
)
from wiggum.codex_usage import read_codex_usage
from wiggum.providers.constants import CODEX
from wiggum.providers.contract import CommandOptions, ProviderAdapter


def build_command(options: CommandOptions) -> list[str]:
    """Build the non-interactive Codex command for one loop.

    Parameters
    ----------
    options : CommandOptions
        Uniform command options for this loop.

    Returns
    -------
    list[str]
        Codex subprocess argument vector.
    """
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


def run(
    command: list[str],
    repo: Path,
    log_path: Path,
    environment: dict[str, str],
    prompt: str,
    output_path: Path,
    timeout_sec: int,
) -> subprocess.CompletedProcess[str]:
    """Run Codex for one loop attempt.

    Parameters
    ----------
    command : list[str]
        Codex subprocess argument vector.
    repo : Path
        Repository working directory.
    log_path : Path
        File receiving Codex standard output and standard error.
    environment : dict[str, str]
        Environment passed to the Codex child process.
    prompt : str
        Full Ralph loop prompt supplied to Codex through standard input.
    output_path : Path
        Unused; Codex writes its own final message via
        ``--output-last-message`` instead of relying on this argument.
    timeout_sec : int
        Maximum time to wait for the Codex child process.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed Codex process.
    """
    del output_path
    return run_codex(command, repo, log_path, environment, prompt, timeout_sec)


def adapter() -> ProviderAdapter:
    """Build a fresh Codex ProviderAdapter.

    Returns
    -------
    ProviderAdapter
        Adapter wired to this module's Codex-specific functions, looked up
        from this module's own globals at call time so tests can monkeypatch
        them here.
    """
    return ProviderAdapter(
        name=CODEX,
        resolve_executable=resolve_codex_executable,
        build_command=build_command,
        run=run,
        is_retryable_failure=is_retryable_codex_failure,
        read_usage=read_codex_usage,
    )
