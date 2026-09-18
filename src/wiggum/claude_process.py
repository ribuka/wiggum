"""Claude Code CLI process construction and execution for one Ralph loop."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from wiggum.defaults import DEFAULT_CODEX_TIMEOUT_SEC
from wiggum.executable_resolution import resolve_executable
from wiggum.token_usage import TokenUsage

__all__ = [
    "build_claude_command",
    "is_retryable_claude_failure",
    "read_claude_usage",
    "resolve_claude_executable",
    "run_claude",
]


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


def resolve_claude_executable(executable: str) -> str | None:
    """Resolve a Claude Code CLI executable name to an absolute path.

    Parameters
    ----------
    executable : str
        Claude Code executable name or path.

    Returns
    -------
    str | None
        Absolute executable path, or ``None`` when it cannot be found.
    """
    return resolve_executable(executable)


def build_claude_command(
    executable: str,
    model: str | None,
    auto_approve: bool = False,
) -> list[str]:
    """Build the non-interactive Claude Code CLI command for one loop.

    Parameters
    ----------
    executable : str
        Claude Code executable name or path.
    model : str | None
        Optional model override.
    auto_approve : bool, default False
        Bypass permission prompts for every tool. Claude Code CLI has no
        sandboxed, partially-unattended mode comparable to Codex's
        ``workspace-write`` sandbox, so a Ralph loop requires this to be
        enabled; callers must validate that before building the command.

    Returns
    -------
    list[str]
        Subprocess argument vector.
    """
    command = [
        executable,
        "-p",
        "--output-format",
        "json",
    ]
    if auto_approve:
        command.extend(["--permission-mode", "bypassPermissions"])
    if model is not None:
        command.extend(["--model", model])
    # Read the prompt from standard input rather than as a positional
    # argument so multi-line prompts are never truncated by a shell.
    return command


def _extract_result_text(stdout: str) -> str | None:
    """Extract the final assistant message from Claude Code CLI's JSON output.

    Parameters
    ----------
    stdout : str
        Complete standard output produced by ``--output-format json``.

    Returns
    -------
    str | None
        The ``result`` field's text, or ``None`` when ``stdout`` is not the
        expected single JSON object with a string ``result`` field.
    """
    try:
        payload = json.loads(stdout)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(payload, dict):
        return None
    result = payload.get("result")
    return result if isinstance(result, str) else None


def run_claude(
    command: list[str],
    repo: Path,
    log_path: Path,
    environment: dict[str, str],
    prompt: str,
    output_path: Path,
    timeout_sec: int = DEFAULT_CODEX_TIMEOUT_SEC,
) -> subprocess.CompletedProcess[str]:
    """Run Claude Code CLI and capture its final message for one loop.

    Claude Code CLI has no ``--output-last-message`` flag comparable to
    Codex's. With ``--output-format json`` its standard output is a single
    JSON object whose ``result`` field holds the agent's final response, so
    that field is extracted and written to ``output_path`` on its own:
    ``output_path`` must never contain the surrounding JSON, or protocol
    detection for ``TASK_COMPLETED``/``TASK_INCOMPLETE``/``TASK_BLOCKED``
    would break. The loop log still records the raw JSON standard output and
    standard error for troubleshooting and token-usage parsing.

    Parameters
    ----------
    command : list[str]
        Claude Code subprocess argument vector.
    repo : Path
        Repository working directory.
    log_path : Path
        File receiving Claude Code standard output and standard error.
    environment : dict[str, str]
        Environment passed to the Claude Code child process.
    prompt : str
        Full Ralph loop prompt supplied to Claude Code through standard input.
    output_path : Path
        File receiving the final Claude Code message when the process
        succeeds and reports a usable result.
    timeout_sec : int, default 1800
        Maximum time to wait for the Claude Code child process.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed Claude Code process.

    Raises
    ------
    subprocess.TimeoutExpired
        Re-raised after writing whatever standard output and standard error
        the Claude Code process produced before the timeout to ``log_path``,
        so a timed-out attempt still leaves diagnostic output behind.
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
        result_text = _extract_result_text(completed.stdout)
        if result_text is not None:
            output_path.write_text(result_text, encoding="utf-8")
    return completed


def is_retryable_claude_failure(log_path: Path) -> bool:
    """Return whether a Claude Code log contains a transient transport failure.

    Parameters
    ----------
    log_path : Path
        UTF-8 log emitted by a failed Claude Code child process.

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
        "overloaded_error",
        "rate_limit_error",
        "network error",
    )
    return any(marker in output for marker in markers)


def _nonnegative_int(value: Any) -> int:
    """Return a non-negative integer value or zero for invalid input.

    Parameters
    ----------
    value : Any
        Untrusted value from a Claude Code JSON usage object.

    Returns
    -------
    int
        Parsed non-negative integer, or zero.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def read_claude_usage(log_path: Path) -> TokenUsage:
    """Parse token usage from Claude Code CLI's final JSON result object.

    ``--output-format json`` reports ``usage.input_tokens`` net of prompt
    caching, with cache activity broken out separately as
    ``cache_creation_input_tokens`` and ``cache_read_input_tokens``. Both are
    folded into :attr:`TokenUsage.input_tokens` because they were tokens the
    model processed either way; only ``cache_read_input_tokens`` is reported
    as :attr:`TokenUsage.cached_input_tokens`, since that is the subset
    actually served from the cache. Claude Code CLI does not break out
    reasoning/thinking tokens separately, so that field is always zero.

    Parameters
    ----------
    log_path : Path
        Combined Claude Code process log.

    Returns
    -------
    TokenUsage
        Usage parsed from the log's ``result`` event, or all-zero usage when
        the log is unreadable or contains no such event.
    """
    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return TokenUsage()

    for line in lines:
        try:
            payload = json.loads(line)
        except (json.JSONDecodeError, TypeError):
            continue
        if not isinstance(payload, dict) or payload.get("type") != "result":
            continue
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            continue
        cache_read = _nonnegative_int(usage.get("cache_read_input_tokens"))
        cache_creation = _nonnegative_int(usage.get("cache_creation_input_tokens"))
        input_tokens = _nonnegative_int(usage.get("input_tokens"))
        return TokenUsage(
            input_tokens=input_tokens + cache_read + cache_creation,
            cached_input_tokens=cache_read,
            output_tokens=_nonnegative_int(usage.get("output_tokens")),
            reasoning_output_tokens=0,
        )
    return TokenUsage()
