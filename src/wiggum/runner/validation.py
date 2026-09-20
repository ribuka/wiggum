"""Preflight validation for the Ralph loop runner: arguments and Git state.

Every check here runs once, before the first loop starts, and returns a
human-readable error message instead of logging or raising directly so
:mod:`wiggum.runner.loop` stays the single place that decides how a preflight
failure is reported and which :class:`~wiggum.exit_codes.ExitCode` it maps to.
"""

from __future__ import annotations

from pathlib import Path

from wiggum.config import RalphPaths
from wiggum.git_ops import require_clean_worktree, require_git_output
from wiggum.providers import REASONING_EFFORTS


def _validate_required_files(paths: RalphPaths) -> str | None:
    """Return a preflight error for a missing required repository file.

    Parameters
    ----------
    paths : RalphPaths
        Resolved Ralph file paths selected by the required configuration.

    Returns
    -------
    str | None
        Human-readable error message, or ``None`` when every required file is
        present as a regular file.
    """
    required_paths = (paths.tasks, paths.project, paths.progress)
    for required_path in required_paths:
        if not required_path.is_file():
            return f"Required file does not exist: {required_path}"
    return None


def validate_run_options(*, max_loops: int, reasoning_effort: str) -> str | None:
    """Validate CLI-sourced options that do not depend on repository configuration.

    This runs before ``wiggum/config.toml`` is loaded, so a repository whose
    configuration is absent or invalid does not mask an invalid CLI flag.
    Provider/``[run.codex]`` combination validation happens separately, once
    the configuration is loaded; see
    :func:`wiggum.providers.validate_provider_options`.

    Parameters
    ----------
    max_loops : int
        Maximum number of agent processes to start.
    reasoning_effort : str
        Reasoning effort for each loop.

    Returns
    -------
    str | None
        Human-readable error message, or ``None`` for valid options.
    """
    if max_loops < 1:
        return "--max-loops must be at least 1"
    if reasoning_effort not in REASONING_EFFORTS:
        return f"--reasoning-effort has an unsupported value: {reasoning_effort}"
    return None


def validate_run_arguments(
    *,
    prompt_path: Path | None,
    paths: RalphPaths,
) -> str | None:
    """Validate file arguments and required files before any loop starts.

    Parameters
    ----------
    prompt_path : Path | None
        UTF-8 prompt file used for every loop, or ``None`` to use wiggum's
        bundled default prompt.
    paths : RalphPaths
        Resolved Ralph file paths.

    Returns
    -------
    str | None
        Human-readable error message, or ``None`` when every file is valid.
    """
    if prompt_path is not None and not prompt_path.is_file():
        return f"Prompt file does not exist: {prompt_path}"
    return _validate_required_files(paths)


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
