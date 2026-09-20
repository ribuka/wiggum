"""Required ``[paths]`` table: repository-local Ralph file locations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wiggum.config.document import (
    ConfigurationError,
    resolve_optional_path_or_none,
    resolve_required_path,
)

DEFAULT_PATHS: dict[str, Path] = {
    "tasks": Path("wiggum/TASKS.json"),
    "project": Path("wiggum/RALPH_PROJECT.md"),
    "progress": Path("wiggum/PROGRESS.md"),
}
_OPTIONAL_PATH_KEYS = {"prompt_file"}


@dataclass(frozen=True)
class RalphPaths:
    """Resolved paths used by a Ralph loop.

    Parameters
    ----------
    tasks : Path
        JSON task ledger path.
    project : Path
        Repository-specific Ralph instruction path.
    progress : Path
        Append-only Ralph progress record path.
    prompt_file : Path | None
        UTF-8 prompt file used for every loop, or ``None`` to use wiggum's
        bundled default prompt.
    """

    tasks: Path
    project: Path
    progress: Path
    prompt_file: Path | None


def parse_paths(repo: Path, document: dict[str, object]) -> RalphPaths:
    """Parse the ``[paths]`` table from a configuration document.

    Parameters
    ----------
    repo : Path
        Resolved Git repository root.
    document : dict[str, object]
        Parsed TOML document returned by
        :func:`wiggum.config.document.read_document`.

    Returns
    -------
    RalphPaths
        Absolute, repository-contained paths from the configuration.

    Raises
    ------
    ConfigurationError
        If ``[paths]`` has an invalid schema or names a path outside ``repo``.
    """
    values = document["paths"]
    required_keys = set(DEFAULT_PATHS)
    if (
        not isinstance(values, dict)
        or not required_keys.issubset(values)
        or set(values) - required_keys - _OPTIONAL_PATH_KEYS
    ):
        raise ConfigurationError("[paths] must contain only tasks, project, progress, and prompt_file")
    resolved_paths = {
        name: resolve_required_path(repo, f"[paths].{name}", values[name]) for name in required_keys
    }
    resolved_paths["prompt_file"] = resolve_optional_path_or_none(
        repo, "[paths].prompt_file", values.get("prompt_file")
    )
    return RalphPaths(**resolved_paths)
