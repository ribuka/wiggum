"""Preflight validation for the Ralph loop runner: arguments and Git state.

Every check here runs once, before the first loop starts, and returns a
human-readable error message instead of logging or raising directly so
:mod:`wiggum.runner.loop` stays the single place that decides how a preflight
failure is reported and which :class:`~wiggum.exit_codes.ExitCode` it maps to.
"""

from __future__ import annotations

from pathlib import Path

from wiggum.defaults import MODEL_VERBOSITIES
from wiggum.git_ops import require_clean_worktree, require_git_output
from wiggum.providers import REASONING_EFFORTS, validate_provider_options


def _validate_required_files(repo: Path, tasks_path: Path) -> str | None:
    """Return a preflight error for a missing required repository file.

    Parameters
    ----------
    repo : Path
        Git repository root containing the project configuration.
    tasks_path : Path
        Ralph task ledger selected for this run.

    Returns
    -------
    str | None
        Human-readable error message, or ``None`` when every required file is
        present as a regular file.
    """
    required_paths = (tasks_path, repo / "RALPH_PROJECT.md")
    for required_path in required_paths:
        if not required_path.is_file():
            return f"Required file does not exist: {required_path}"
    return None


def validate_run_arguments(
    *,
    max_loops: int,
    api_retry_count: int | None,
    api_retry_interval_sec: int,
    codex_timeout_sec: int,
    reasoning_effort: str,
    model_verbosity: str,
    tool_output_token_limit: int,
    provider: str,
    lean: bool,
    auto_approve: bool,
    prompt_path: Path | None,
    repo: Path,
    tasks_path: Path,
) -> str | None:
    """Validate runner arguments and required files before any loop starts.

    Parameters
    ----------
    max_loops : int
        Maximum number of agent processes to start.
    api_retry_count : int | None
        Number of additional attempts after an agent API or protocol
        failure. ``None`` disables retries.
    api_retry_interval_sec : int
        Seconds to wait between agent API retry attempts.
    codex_timeout_sec : int
        Maximum time to wait for each agent child process.
    reasoning_effort : str
        Reasoning effort for each loop.
    model_verbosity : str
        Codex model verbosity for each loop.
    tool_output_token_limit : int
        Maximum tokens retained from one tool output in model history.
    provider : str
        Selected AI model vendor; one of :data:`wiggum.providers.PROVIDERS`.
    lean : bool
        Whether to ignore user Codex configuration and reasoning summaries.
    auto_approve : bool
        Automatically approve agent requests instead of requiring
        interactive confirmation.
    prompt_path : Path | None
        UTF-8 prompt file used for every loop, or ``None`` to use wiggum's
        bundled default prompt.
    repo : Path
        Git repository to modify.
    tasks_path : Path
        Ralph task ledger file.

    Returns
    -------
    str | None
        Human-readable error message, or ``None`` when every argument and
        required file is valid.
    """
    if max_loops < 1:
        return "--max-loops must be at least 1"
    if api_retry_count is not None and api_retry_count < 0:
        return "--api-retry-count must be at least 0"
    if api_retry_interval_sec < 0:
        return "--api-retry-interval-sec must be at least 0"
    if codex_timeout_sec < 1:
        return "--codex-timeout-sec must be at least 1"
    if reasoning_effort not in REASONING_EFFORTS:
        return f"--reasoning-effort has an unsupported value: {reasoning_effort}"
    if model_verbosity not in MODEL_VERBOSITIES:
        return f"--model-verbosity has an unsupported value: {model_verbosity}"
    if tool_output_token_limit < 1:
        return "--tool-output-token-limit must be at least 1"
    provider_option_error = validate_provider_options(
        provider,
        reasoning_effort=reasoning_effort,
        model_verbosity=model_verbosity,
        tool_output_token_limit=tool_output_token_limit,
        lean=lean,
        auto_approve=auto_approve,
    )
    if provider_option_error is not None:
        return provider_option_error
    if prompt_path is not None and not prompt_path.is_file():
        return f"Prompt file does not exist: {prompt_path}"
    return _validate_required_files(repo, tasks_path)


def validate_git_preconditions(repo: Path) -> str | None:
    """Validate that the repository is the Git root with a clean worktree.

    Parameters
    ----------
    repo : Path
        Git repository to modify.

    Returns
    -------
    str | None
        Human-readable error message, or ``None`` when the repository is the
        Git root and its worktree is clean.
    """
    try:
        top_level = Path(require_git_output(repo, "rev-parse", "--show-toplevel")).resolve()
        if top_level != repo:
            raise RuntimeError(f"--repo must be the Git root: {top_level}")
        require_clean_worktree(repo)
    except RuntimeError as error:
        return str(error)
    return None
