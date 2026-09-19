"""Read and validate repository-local wiggum configuration."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_PATH = Path("wiggum/config.toml")
DEFAULT_PATHS: dict[str, Path] = {
    "tasks": Path("wiggum/TASKS.json"),
    "project": Path("wiggum/RALPH_PROJECT.md"),
    "progress": Path("wiggum/PROGRESS.md"),
}


class ConfigurationError(ValueError):
    """Raised when a repository's wiggum configuration is unusable."""


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
    """

    tasks: Path
    project: Path
    progress: Path


def load_ralph_paths(repo: Path) -> RalphPaths:
    """Load required Ralph file paths from ``wiggum/config.toml``.

    Parameters
    ----------
    repo : Path
        Resolved Git repository root.

    Returns
    -------
    RalphPaths
        Absolute, repository-contained paths from the configuration.

    Raises
    ------
    ConfigurationError
        If the configuration is absent, invalid TOML, has an invalid schema,
        or names a path outside ``repo``.
    """
    configuration_path = repo / CONFIG_PATH
    try:
        document = tomllib.loads(configuration_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigurationError(f"Required configuration does not exist: {configuration_path}") from error
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigurationError(f"Invalid configuration: {configuration_path}: {error}") from error
    if not isinstance(document, dict) or set(document) != {"paths"}:
        raise ConfigurationError("configuration must contain only a [paths] table")
    values = document["paths"]
    if not isinstance(values, dict) or set(values) != set(DEFAULT_PATHS):
        raise ConfigurationError("[paths] must contain only tasks, project, and progress")
    resolved_paths = {
        name: _resolve_repository_path(repo, name, value)
        for name, value in values.items()
    }
    return RalphPaths(**resolved_paths)


def _resolve_repository_path(repo: Path, name: str, value: object) -> Path:
    """Resolve one configured path and ensure it stays inside the repository.

    Parameters
    ----------
    repo : Path
        Resolved Git repository root.
    name : str
        Configuration key used in error messages.
    value : object
        Raw TOML value.

    Returns
    -------
    Path
        Resolved, repository-contained path.

    Raises
    ------
    ConfigurationError
        If the value is not a non-empty relative string or escapes ``repo``.
    """
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"[paths].{name} must be a non-empty string")
    configured_path = Path(value)
    if configured_path.is_absolute():
        raise ConfigurationError(f"[paths].{name} must be relative to the repository")
    resolved_path = (repo / configured_path).resolve()
    if not resolved_path.is_relative_to(repo):
        raise ConfigurationError(f"[paths].{name} must stay inside the repository")
    return resolved_path
