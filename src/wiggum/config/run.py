"""Optional ``[run]`` table: run tunables that rarely change between runs.

``[run]`` holds every ``wiggum run`` tunable that is not expected to change
from one invocation to the next (retry/timeout behavior and per-provider
executables; directory paths live in ``[dir]``), so only run-to-run choices
such as ``--provider`` and ``--model`` remain command-line flags. Every key
is optional; an absent key falls back to wiggum's built-in default.
"""

from __future__ import annotations

from dataclasses import dataclass

from wiggum.config.document import ConfigurationError
from wiggum.defaults import (
    DEFAULT_AGENT_TIMEOUT_SEC,
    DEFAULT_API_RETRY_COUNT,
    DEFAULT_API_RETRY_INTERVAL_SEC,
    DEFAULT_MODEL_VERBOSITY,
    DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT,
    MODEL_VERBOSITIES,
)
from wiggum.providers.constants import DEFAULT_EXECUTABLES, PROVIDERS

_ALLOWED_RUN_KEYS = {
    "manage_process_env",
    "api_retry_count",
    "api_retry_interval_sec",
    "agent_timeout_sec",
    "executable",
    "codex",
}
_ALLOWED_CODEX_KEYS = {"tool_output_token_limit", "model_verbosity", "lean"}


@dataclass(frozen=True)
class CodexRunSettings:
    """Codex-only tunables from ``[run.codex]``.

    Parameters
    ----------
    tool_output_token_limit : int
        Maximum tokens retained from one tool output in model history.
    model_verbosity : str
        Codex model verbosity.
    lean : bool
        Whether to ignore user Codex configuration and reasoning summaries.
    """

    tool_output_token_limit: int
    model_verbosity: str
    lean: bool


@dataclass(frozen=True)
class RunSettings:
    """Resolved ``[run]`` tunables for a Ralph loop.

    Parameters
    ----------
    manage_process_env : bool
        Whether to inject ``UV_CACHE_DIR``, ``TMP``, and ``TEMP`` into the
        agent child process environment.
    api_retry_count : int | None
        Number of additional attempts after an agent API or protocol
        failure. ``None`` disables retries.
    api_retry_interval_sec : int
        Seconds to wait between agent API retry attempts.
    agent_timeout_sec : int
        Maximum time to wait for each agent child process, regardless of
        provider.
    executables : dict[str, str]
        Executable name or path for every provider in
        :data:`wiggum.providers.PROVIDERS`.
    codex : CodexRunSettings
        Codex-only tunables.
    """

    manage_process_env: bool
    api_retry_count: int | None
    api_retry_interval_sec: int
    agent_timeout_sec: int
    executables: dict[str, str]
    codex: CodexRunSettings


def parse_run_settings(document: dict[str, object]) -> RunSettings:
    """Parse the optional ``[run]`` table from a configuration document.

    Parameters
    ----------
    document : dict[str, object]
        Parsed TOML document returned by
        :func:`wiggum.config.document.read_document`.

    Returns
    -------
    RunSettings
        Resolved run tunables, falling back to built-in defaults for every
        absent key.

    Raises
    ------
    ConfigurationError
        If ``[run]``, ``[run.executable]``, or ``[run.codex]`` has an invalid
        schema or an out-of-range value.
    """
    run_table = document.get("run", {})
    if not isinstance(run_table, dict):
        raise ConfigurationError("[run] must be a table")
    unknown_keys = set(run_table) - _ALLOWED_RUN_KEYS
    if unknown_keys:
        raise ConfigurationError(f"[run] has unsupported keys: {', '.join(sorted(unknown_keys))}")

    manage_process_env = run_table.get("manage_process_env", True)
    if not isinstance(manage_process_env, bool):
        raise ConfigurationError("[run].manage_process_env must be a boolean")

    api_retry_count = run_table.get("api_retry_count", DEFAULT_API_RETRY_COUNT)
    if api_retry_count is not None and (
        not isinstance(api_retry_count, int) or isinstance(api_retry_count, bool) or api_retry_count < 0
    ):
        raise ConfigurationError("[run].api_retry_count must be a non-negative integer")

    api_retry_interval_sec = run_table.get("api_retry_interval_sec", DEFAULT_API_RETRY_INTERVAL_SEC)
    if (
        not isinstance(api_retry_interval_sec, int)
        or isinstance(api_retry_interval_sec, bool)
        or api_retry_interval_sec < 0
    ):
        raise ConfigurationError("[run].api_retry_interval_sec must be a non-negative integer")

    agent_timeout_sec = run_table.get("agent_timeout_sec", DEFAULT_AGENT_TIMEOUT_SEC)
    if not isinstance(agent_timeout_sec, int) or isinstance(agent_timeout_sec, bool) or agent_timeout_sec < 1:
        raise ConfigurationError("[run].agent_timeout_sec must be at least 1")

    return RunSettings(
        manage_process_env=manage_process_env,
        api_retry_count=api_retry_count,
        api_retry_interval_sec=api_retry_interval_sec,
        agent_timeout_sec=agent_timeout_sec,
        executables=_parse_executables(run_table.get("executable", {})),
        codex=_parse_codex_settings(run_table.get("codex", {})),
    )


def _parse_executables(value: object) -> dict[str, str]:
    """Parse the ``[run.executable]`` sub-table.

    Parameters
    ----------
    value : object
        Raw TOML value for the ``executable`` key.

    Returns
    -------
    dict[str, str]
        Executable name or path for every provider in
        :data:`wiggum.providers.PROVIDERS`, defaulting to
        :data:`wiggum.providers.DEFAULT_EXECUTABLES` for an unconfigured
        provider.

    Raises
    ------
    ConfigurationError
        If the table has an unsupported key or a non-string value.
    """
    if not isinstance(value, dict):
        raise ConfigurationError("[run.executable] must be a table")
    unknown_keys = set(value) - set(PROVIDERS)
    if unknown_keys:
        raise ConfigurationError(
            f"[run.executable] has unsupported keys: {', '.join(sorted(unknown_keys))}"
        )
    executables = dict(DEFAULT_EXECUTABLES)
    for provider, executable in value.items():
        if not isinstance(executable, str) or not executable.strip():
            raise ConfigurationError(f"[run.executable].{provider} must be a non-empty string")
        executables[provider] = executable
    return executables


def _parse_codex_settings(value: object) -> CodexRunSettings:
    """Parse the ``[run.codex]`` sub-table.

    Parameters
    ----------
    value : object
        Raw TOML value for the ``codex`` key.

    Returns
    -------
    CodexRunSettings
        Resolved Codex-only tunables.

    Raises
    ------
    ConfigurationError
        If the table has an unsupported key or an out-of-range value.
    """
    if not isinstance(value, dict):
        raise ConfigurationError("[run.codex] must be a table")
    unknown_keys = set(value) - _ALLOWED_CODEX_KEYS
    if unknown_keys:
        raise ConfigurationError(f"[run.codex] has unsupported keys: {', '.join(sorted(unknown_keys))}")

    tool_output_token_limit = value.get("tool_output_token_limit", DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT)
    if (
        not isinstance(tool_output_token_limit, int)
        or isinstance(tool_output_token_limit, bool)
        or tool_output_token_limit < 1
    ):
        raise ConfigurationError("[run.codex].tool_output_token_limit must be at least 1")

    model_verbosity = value.get("model_verbosity", DEFAULT_MODEL_VERBOSITY)
    if model_verbosity not in MODEL_VERBOSITIES:
        raise ConfigurationError(f"[run.codex].model_verbosity has an unsupported value: {model_verbosity}")

    lean = value.get("lean", False)
    if not isinstance(lean, bool):
        raise ConfigurationError("[run.codex].lean must be a boolean")

    return CodexRunSettings(
        tool_output_token_limit=tool_output_token_limit,
        model_verbosity=model_verbosity,
        lean=lean,
    )
