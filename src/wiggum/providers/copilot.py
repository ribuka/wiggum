"""GitHub Copilot CLI adapter: process construction, execution, and ProviderAdapter."""

from __future__ import annotations

import subprocess
from pathlib import Path

from wiggum.defaults import DEFAULT_AGENT_TIMEOUT_SEC, DEFAULT_REASONING_EFFORT
from wiggum.env.executable_resolution import resolve_executable
from wiggum.providers.constants import COPILOT
from wiggum.providers.contract import CommandOptions, ProviderAdapter
from wiggum.providers.process_output import decode_stream_output, log_contains_any
from wiggum.providers.usage.token_usage import TokenUsage


def resolve_copilot_executable(executable: str) -> str | None:
    """Resolve a GitHub Copilot CLI executable name to an absolute path.

    Parameters
    ----------
    executable : str
        Copilot executable name or path.

    Returns
    -------
    str | None
        Absolute executable path, or ``None`` when it cannot be found.
    """
    return resolve_executable(executable)


def build_copilot_command(
    executable: str,
    model: str | None,
    auto_approve: bool = False,
    *,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
) -> list[str]:
    """Build the non-interactive GitHub Copilot CLI command for one loop.

    Parameters
    ----------
    executable : str
        Copilot executable name or path.
    model : str | None
        Optional model override.
    auto_approve : bool, default False
        Allow every tool to run and skip clarifying questions. GitHub
        Copilot CLI has no sandboxed, partially-unattended mode comparable to
        Codex's ``workspace-write`` sandbox, so a Ralph loop requires this to
        be enabled; callers must validate that before building the command.
    reasoning_effort : str, default "medium"
        Reasoning effort passed to Copilot's ``--reasoning-effort`` flag.
        Support for a given level depends on the selected model, not this
        provider; Copilot CLI rejects an unsupported combination itself.

    Returns
    -------
    list[str]
        Subprocess argument vector.
    """
    command = [
        executable,
        "-s",
        "--no-ask-user",
        "--output-format",
        "text",
        "--reasoning-effort",
        reasoning_effort,
    ]
    if auto_approve:
        command.append("--allow-all-tools")
    if model is not None:
        command.extend(["--model", model])
    # Read the prompt from standard input rather than as a positional
    # argument so multi-line prompts are never truncated by a shell.
    return command


def run_copilot(
    command: list[str],
    repo: Path,
    log_path: Path,
    environment: dict[str, str],
    prompt: str,
    output_path: Path,
    timeout_sec: int = DEFAULT_AGENT_TIMEOUT_SEC,
) -> subprocess.CompletedProcess[str]:
    """Run GitHub Copilot CLI and capture its final message for one loop.

    Unlike Codex, Copilot CLI has no ``--output-last-message`` flag. With
    ``-s`` (silent) its standard output is exactly the agent's final
    response, so standard output and standard error are captured separately:
    ``output_path`` only ever receives standard output, so diagnostic text on
    standard error can never land after the final ``TASK_COMPLETED`` /
    ``TASK_INCOMPLETE`` / ``TASK_BLOCKED`` line and break protocol detection.
    The loop log still records both streams for troubleshooting.

    Parameters
    ----------
    command : list[str]
        Copilot subprocess argument vector.
    repo : Path
        Repository working directory.
    log_path : Path
        File receiving Copilot standard output and standard error.
    environment : dict[str, str]
        Environment passed to the Copilot child process.
    prompt : str
        Full Ralph loop prompt supplied to Copilot through standard input.
    output_path : Path
        File receiving the final Copilot message when the process succeeds.
    timeout_sec : int, default 1800
        Maximum time to wait for the Copilot child process.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed Copilot process.

    Raises
    ------
    subprocess.TimeoutExpired
        Re-raised after writing whatever standard output and standard error
        the Copilot process produced before the timeout to ``log_path``, so
        a timed-out attempt still leaves diagnostic output behind.
    """
    try:
        completed = subprocess.run(
            command,
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
            input=prompt,
            timeout=timeout_sec,
        )
    except subprocess.TimeoutExpired as error:
        # TimeoutExpired always carries bytes in stdout/stderr, even when the
        # underlying Popen was configured with text=True.
        partial_stdout = decode_stream_output(error.stdout)
        partial_stderr = decode_stream_output(error.stderr)
        log_path.write_text(partial_stdout + partial_stderr, encoding="utf-8")
        raise
    log_path.write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode == 0:
        output_path.write_text(completed.stdout, encoding="utf-8")
    return completed


def is_retryable_copilot_failure(log_path: Path) -> bool:
    """Return whether a Copilot log contains a transient transport failure.

    Parameters
    ----------
    log_path : Path
        UTF-8 log emitted by a failed Copilot child process.

    Returns
    -------
    bool
        ``True`` when the log contains a known transient connection failure.
    """
    markers = (
        "ECONNRESET",
        "rate limit exceeded",
        "network error",
    )
    return log_contains_any(log_path, markers)


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
