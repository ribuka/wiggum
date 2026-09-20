"""Shared TOML document loading and path resolution for wiggum/config.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

CONFIG_PATH = Path("wiggum/config.toml")

_REQUIRED_TOP_LEVEL_KEYS = {"paths"}
_OPTIONAL_TOP_LEVEL_KEYS = {"dir", "run"}


class ConfigurationError(ValueError):
    """Raised when a repository's wiggum configuration is unusable."""


def read_document(repo: Path) -> dict[str, object]:
    """Read and validate the top-level shape of ``wiggum/config.toml``.

    Parameters
    ----------
    repo : Path
        Resolved Git repository root.

    Returns
    -------
    dict[str, object]
        Parsed TOML document, containing a required ``paths`` key and
        optional ``dir`` and ``run`` keys.

    Raises
    ------
    ConfigurationError
        If the configuration is absent, invalid TOML, or has an unsupported
        top-level shape.
    """
    configuration_path = repo / CONFIG_PATH
    try:
        document = tomllib.loads(configuration_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ConfigurationError(f"Required configuration does not exist: {configuration_path}") from error
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigurationError(f"Invalid configuration: {configuration_path}: {error}") from error
    if not isinstance(document, dict):
        raise ConfigurationError("configuration must be a TOML table")
    unknown_keys = set(document) - _REQUIRED_TOP_LEVEL_KEYS - _OPTIONAL_TOP_LEVEL_KEYS
    if unknown_keys or not _REQUIRED_TOP_LEVEL_KEYS.issubset(document):
        raise ConfigurationError("configuration must contain [paths] and may optionally contain [dir] and [run]")
    return document


def resolve_required_path(repo: Path, key: str, value: object) -> Path:
    """Resolve one required, repository-contained relative path.

    Parameters
    ----------
    repo : Path
        Resolved Git repository root.
    key : str
        Fully-qualified configuration key used in error messages, e.g.
        ``"[paths].tasks"``.
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
        raise ConfigurationError(f"{key} must be a non-empty string")
    configured_path = Path(value)
    if configured_path.is_absolute():
        raise ConfigurationError(f"{key} must be relative to the repository")
    resolved_path = (repo / configured_path).resolve()
    if not resolved_path.is_relative_to(repo):
        raise ConfigurationError(f"{key} must stay inside the repository")
    return resolved_path


def resolve_optional_path(repo: Path, key: str, value: object, default: Path) -> Path:
    """Resolve one optional, repository-contained relative path.

    Parameters
    ----------
    repo : Path
        Resolved Git repository root.
    key : str
        Fully-qualified configuration key used in error messages.
    value : object
        Raw TOML value, or ``None`` when the key is absent.
    default : Path
        Repository-relative path used when ``value`` is ``None``.

    Returns
    -------
    Path
        Resolved, repository-contained path.
    """
    if value is None:
        return (repo / default).resolve()
    return resolve_required_path(repo, key, value)


def resolve_optional_path_or_none(repo: Path, key: str, value: object) -> Path | None:
    """Resolve one optional, repository-contained relative path with no default.

    Parameters
    ----------
    repo : Path
        Resolved Git repository root.
    key : str
        Fully-qualified configuration key used in error messages.
    value : object
        Raw TOML value, or ``None`` when the key is absent.

    Returns
    -------
    Path | None
        Resolved, repository-contained path, or ``None`` when ``value`` is
        ``None``.
    """
    if value is None:
        return None
    return resolve_required_path(repo, key, value)
