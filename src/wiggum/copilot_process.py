"""GitHub Copilot CLI process construction and execution for one Ralph loop."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def resolve_copilot_executable(executable: str) -> str | None:
    """Resolve a GitHub Copilot executable name to an absolute executable path.

    Parameters
    ----------
    executable : str
        GitHub Copilot executable name or path.

    Returns
    -------
    str | None
        Absolute executable path, or ``None`` when it cannot be found.
    """
    executable_path = Path(executable)
    if executable_path.is_file():
        return str(executable_path.resolve())

    resolved_path = shutil.which(executable)
    if resolved_path is None:
        return None
    return str(Path(resolved_path).resolve())


def build_copilot_command(
    executable: str,
    repo: Path,
    output_path: Path,
    model: str | None,
    auto_approve: bool = False,
    *,
    reasoning_effort: str = "medium",
    model_verbosity: str = "low",
    tool_output_token_limit: int = 12_000,
    lean: bool = False,
) -> list[str]:
    """Build the non-interactive GitHub Copilot command for one loop.

    Parameters
    ----------
    executable : str
        GitHub Copilot executable name or path.
    repo : Path
        Repository working directory.
    output_path : Path
        File receiving the final GitHub Copilot message.
    model : str | None
        Optional model override.
    auto_approve : bool, default False
        Whether the caller requested non-interactive execution with pre-approved
        permissions.
    reasoning_effort : str, default "medium"
        Unused placeholder kept for the shared provider command interface.
    model_verbosity : str, default "low"
        Unused placeholder kept for the shared provider command interface.
    tool_output_token_limit : int, default 12000
        Unused placeholder kept for the shared provider command interface.
    lean : bool, default False
        Unused placeholder kept for the shared provider command interface.

    Returns
    -------
    list[str]
        Subprocess argument vector.
    """
    del repo, output_path, reasoning_effort, model_verbosity, tool_output_token_limit, lean

    command = [
        executable,
        "-s",
        "--no-ask-user",
    ]
    if auto_approve:
        command.append("--allow-all")
    if model is not None:
        command.append(f"--model={model}")
    return command


def run_copilot(
    command: list[str],
    repo: Path,
    log_path: Path,
    output_path: Path,
    environment: dict[str, str],
    prompt: str,
    timeout_sec: int,
) -> subprocess.CompletedProcess[str]:
    """Run GitHub Copilot and write its outputs to loop files.

    Parameters
    ----------
    command : list[str]
        GitHub Copilot subprocess argument vector.
    repo : Path
        Repository working directory.
    log_path : Path
        File receiving combined GitHub Copilot standard output and standard
        error.
    output_path : Path
        File receiving the final GitHub Copilot message.
    environment : dict[str, str]
        Environment passed to the GitHub Copilot child process.
    prompt : str
        Full Ralph loop prompt supplied through standard input.
    timeout_sec : int
        Maximum time to wait for the GitHub Copilot child process.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed GitHub Copilot process.
    """
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
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    output_path.write_text(stdout, encoding="utf-8")
    log_path.write_text(f"{stdout}{stderr}", encoding="utf-8")
    return completed


def is_retryable_copilot_failure(log_path: Path) -> bool:
    """Return whether a GitHub Copilot log contains a transient transport failure.

    Parameters
    ----------
    log_path : Path
        UTF-8 log emitted by a failed GitHub Copilot child process.

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
        "stream disconnected",
        "Connection failed: error sending request",
        "failed to connect to websocket",
        "ECONNRESET",
        "network error",
    )
    return any(marker in output for marker in markers)
