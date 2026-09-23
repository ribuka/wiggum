"""Shared TOML document loading and path resolution for wiggum/config.toml."""

from __future__ import annotations

import tomllib
from pathlib import Path

CONFIG_PATH = Path("wiggum/config.toml")

_REQUIRED_TOP_LEVEL_KEYS = {"paths"}
_OPTIONAL_TOP_LEVEL_KEYS = {"dir", "run"}


class ConfigurationError(ValueError):
    """Raised when a repository's wiggum configuration is unusable."""


def reject_unknown_keys(table: dict[str, object], allowed: set[str], label: str) -> None:
    """Reject keys in a configuration table that are not supported.

    Parameters
    ----------
    table : dict[str, object]
        Parsed TOML table to validate.
    allowed : set[str]
        Names accepted in ``table``.
    label : str
        Table name included in a validation error.

    Raises
    ------
    ConfigurationError
        If ``table`` includes an unsupported key.
    """
    unknown_keys = set(table) - allowed
    if unknown_keys:
        raise ConfigurationError(f"{label} has unsupported keys: {', '.join(sorted(unknown_keys))}")


def require_int_in_range(
    table: dict[str, object],
    key: str,
    label: str,
    *,
    default: int,
    minimum: int,
) -> int:
    """Read a required-range integer from a configuration table.

    Parameters
    ----------
    table : dict[str, object]
        Parsed TOML table containing the setting.
    key : str
        Setting name in ``table``.
    label : str
        Fully-qualified setting name for validation errors.
    default : int
        Value used when ``key`` is absent.
    minimum : int
        Inclusive lower bound.

    Returns
    -------
    int
        Validated configured or default value.

    Raises
    ------
    ConfigurationError
        If the value is not an integer at least ``minimum``.
    """
    value = table.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value < minimum:
        qualifier = "a non-negative integer" if minimum == 0 else f"at least {minimum}"
        raise ConfigurationError(f"{label} must be {qualifier}")
    return value


def require_optional_int_in_range(
    table: dict[str, object],
    key: str,
    label: str,
    *,
    default: int | None,
    minimum: int,
) -> int | None:
    """Read an optional required-range integer from a configuration table.

    Parameters
    ----------
    table : dict[str, object]
        Parsed TOML table containing the setting.
    key : str
        Setting name in ``table``.
    label : str
        Fully-qualified setting name for validation errors.
    default : int | None
        Value used when ``key`` is absent.
    minimum : int
        Inclusive lower bound for non-null values.

    Returns
    -------
    int | None
        Validated configured or default value.

    Raises
    ------
    ConfigurationError
        If a non-null value is not an integer at least ``minimum``.
    """
    value = table.get(key, default)
    if value is None:
        return None
    return require_int_in_range({key: value}, key, label, default=0, minimum=minimum)


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
        raise ConfigurationError(
            f"Required configuration does not exist: {configuration_path}"
        ) from error
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigurationError(f"Invalid configuration: {configuration_path}: {error}") from error
    if not isinstance(document, dict):
        raise ConfigurationError("configuration must be a TOML table")
    if not _REQUIRED_TOP_LEVEL_KEYS.issubset(document):
        raise ConfigurationError(
            "configuration must contain [paths] and may optionally contain [dir] and [run]"
        )
    reject_unknown_keys(
        document,
        _REQUIRED_TOP_LEVEL_KEYS | _OPTIONAL_TOP_LEVEL_KEYS,
        "configuration",
    )
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
