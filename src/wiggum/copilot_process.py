"""GitHub Copilot CLI process construction and execution for one Ralph loop."""

from __future__ import annotations

import subprocess
from pathlib import Path

from wiggum.defaults import DEFAULT_CODEX_TIMEOUT_SEC
from wiggum.executable_resolution import resolve_executable


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
    timeout_sec: int = DEFAULT_CODEX_TIMEOUT_SEC,
) -> subprocess.CompletedProcess[str]:
    """Run GitHub Copilot CLI and capture its final message for one loop.

    Unlike Codex, Copilot CLI has no ``--output-last-message`` flag. With
    ``-s`` (silent) its standard output is exactly the agent's final
    response, so that captured output is written to both the loop log and
    ``output_path`` to match the Codex last-message file contract.

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
    """
    completed = subprocess.run(
        command,
        cwd=repo,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        env=environment,
        input=prompt,
        timeout=timeout_sec,
    )
    log_path.write_text(completed.stdout, encoding="utf-8")
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
    try:
        output = log_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False
    markers = (
        "ECONNRESET",
        "rate limit exceeded",
        "network error",
    )
    return any(marker in output for marker in markers)
