"""GitHub Copilot CLI process construction and execution for one Ralph loop."""

from __future__ import annotations

import subprocess
from pathlib import Path

from wiggum.defaults import DEFAULT_CODEX_TIMEOUT_SEC, DEFAULT_REASONING_EFFORT
from wiggum.executable_resolution import resolve_executable


def _decode(output: str | bytes | None) -> str:
    """Decode subprocess output that may be ``str``, ``bytes``, or ``None``.

    Parameters
    ----------
    output : str | bytes | None
        Captured standard output or standard error. ``subprocess.run``
        normally decodes this per ``text``/``encoding``, but
        ``TimeoutExpired`` always carries raw bytes regardless of those
        settings.

    Returns
    -------
    str
        Decoded text, or an empty string when ``output`` is ``None``.
    """
    if output is None:
        return ""
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="replace")
    return output


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
        Callers must validate that this is one of
        :data:`wiggum.providers.COPILOT_REASONING_EFFORTS` before building
        the command; GitHub Copilot CLI has no ``"minimal"`` level.

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
    timeout_sec: int = DEFAULT_CODEX_TIMEOUT_SEC,
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
        partial_stdout = _decode(error.stdout)
        partial_stderr = _decode(error.stderr)
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
