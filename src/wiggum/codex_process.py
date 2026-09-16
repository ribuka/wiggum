"""Codex CLI process construction and execution for one Ralph loop."""

from __future__ import annotations

import os
import subprocess
import tempfile
from collections.abc import Sequence
from pathlib import Path

from wiggum.defaults import (
    DEFAULT_CODEX_TIMEOUT_SEC,
    DEFAULT_MODEL_VERBOSITY,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT,
)
from wiggum.executable_resolution import resolve_executable


def resolve_codex_executable(executable: str) -> str | None:
    """Resolve a Codex executable name to an absolute executable path.

    Parameters
    ----------
    executable : str
        Codex executable name or path.

    Returns
    -------
    str | None
        Absolute executable path, or ``None`` when it cannot be found.
    """
    return resolve_executable(executable)


def build_codex_command(
    executable: str,
    repo: Path,
    output_path: Path,
    model: str | None,
    auto_approve: bool = False,
    *,
    reasoning_effort: str = DEFAULT_REASONING_EFFORT,
    model_verbosity: str = DEFAULT_MODEL_VERBOSITY,
    tool_output_token_limit: int = DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT,
    lean: bool = False,
) -> list[str]:
    """Build the non-interactive Codex command for one loop.

    Parameters
    ----------
    executable : str
        Codex executable name or path.
    repo : Path
        Repository working directory.
    output_path : Path
        File receiving the final Codex message.
    model : str | None
        Optional model override.
    auto_approve : bool, default False
        Automatically approve Codex requests in the workspace-write sandbox.
    reasoning_effort : str, default "medium"
        Reasoning effort passed as an inline Codex configuration override.
    model_verbosity : str, default "low"
        Model verbosity passed as an inline Codex configuration override.
    tool_output_token_limit : int, default 12000
        Maximum tokens retained from each tool output in model history.
    lean : bool, default False
        Ignore user configuration and disable reasoning summaries to avoid
        loading optional tools and context that the Ralph loop does not need.

    Returns
    -------
    list[str]
        Subprocess argument vector.
    """
    command = [
        executable,
        "exec",
        "--ephemeral",
        "--json",
        "--disable",
        "unbounded_connection_retries",
        "--cd",
        str(repo),
        "--output-last-message",
        str(output_path),
    ]
    if lean:
        command.append("--ignore-user-config")
    if auto_approve:
        command.append("--approve-for-me")
    else:
        command.extend(["--sandbox", "workspace-write"])
    if model is not None:
        command.extend(["--model", model])
    command.extend(
        [
            "--config",
            f'model_reasoning_effort="{reasoning_effort}"',
            "--config",
            f'model_verbosity="{model_verbosity}"',
            "--config",
            f"tool_output_token_limit={tool_output_token_limit}",
        ]
    )
    if lean:
        command.extend(["--config", 'model_reasoning_summary="none"'])
    # Read the prompt from standard input. Passing multi-line text as an
    # argument to the Windows npm ``codex.cmd`` shim truncates it at the first
    # line.
    command.append("-")
    return command


def build_codex_environment(
    temp_dir: Path,
    *,
    uv_cache_dir: Path,
    manage_process_env: bool = True,
) -> dict[str, str]:
    """Build a child-process environment for one Codex invocation.

    Parameters
    ----------
    temp_dir : Path
        Root temporary directory used to create this loop's isolated runtime
        directory.
    uv_cache_dir : Path
        Directory used for ``UV_CACHE_DIR``.
    manage_process_env : bool, default True
        Whether to inject ``UV_CACHE_DIR``, ``TMP``, and ``TEMP`` into the
        child environment. Disable this for projects that do not use uv or
        that manage their own temporary directories.

    Returns
    -------
    dict[str, str]
        Copy of the current environment, optionally directed into isolated
        cache and temporary paths.
    """
    environment = os.environ.copy()
    if not manage_process_env:
        return environment

    runtime_root = (temp_dir / "runtime").resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    runtime_directory = Path(tempfile.mkdtemp(prefix="ralph-", dir=runtime_root))
    uv_cache_directory = uv_cache_dir.resolve()
    uv_cache_directory.mkdir(parents=True, exist_ok=True)

    environment["UV_CACHE_DIR"] = str(uv_cache_directory)
    environment["TMP"] = str(runtime_directory)
    environment["TEMP"] = str(runtime_directory)
    return environment


def run_codex(
    command: Sequence[str],
    repo: Path,
    log_path: Path,
    environment: dict[str, str],
    prompt: str,
    timeout_sec: int = DEFAULT_CODEX_TIMEOUT_SEC,
) -> subprocess.CompletedProcess[str]:
    """Run Codex and write its combined output to a loop log.

    Parameters
    ----------
    command : Sequence[str]
        Codex subprocess argument vector.
    repo : Path
        Repository working directory.
    log_path : Path
        File receiving Codex standard output and standard error.
    environment : dict[str, str]
        Environment passed to the Codex child process.
    prompt : str
        Full Ralph loop prompt supplied to Codex through standard input.
    timeout_sec : int, default 1800
        Maximum time to wait for the Codex child process.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed Codex process.
    """
    with log_path.open("w", encoding="utf-8") as log_file:
        return subprocess.run(
            command,
            cwd=repo,
            check=False,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            env=environment,
            input=prompt,
            timeout=timeout_sec,
        )


def is_retryable_codex_failure(log_path: Path) -> bool:
    """Return whether a Codex log contains a transient transport failure.

    Parameters
    ----------
    log_path : Path
        UTF-8 log emitted by a failed Codex child process.

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
    )
    return any(marker in output for marker in markers)
