"""Optional ``[dir]`` table: directories wiggum uses while running a loop."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wiggum.config.document import (
    ConfigurationError,
    reject_unknown_keys,
    resolve_optional_path,
)

_ALLOWED_DIR_KEYS = {"log", "temp", "uv_cache"}


@dataclass(frozen=True)
class DirSettings:
    """Resolved ``[dir]`` directories for a Ralph loop.

    Parameters
    ----------
    log : Path
        Directory that stores loop logs.
    temp : Path
        Directory used for loop-scoped temporary files.
    uv_cache : Path
        Directory used for ``UV_CACHE_DIR`` when ``[run].manage_process_env``
        is enabled.
    """

    log: Path
    temp: Path
    uv_cache: Path


def parse_dir_settings(repo: Path, document: dict[str, object]) -> DirSettings:
    """Parse the optional ``[dir]`` table from a configuration document.

    Parameters
    ----------
    repo : Path
        Resolved Git repository root.
    document : dict[str, object]
        Parsed TOML document returned by
        :func:`wiggum.config.document.read_document`.

    Returns
    -------
    DirSettings
        Resolved directories, falling back to built-in defaults for every
        absent key.

    Raises
    ------
    ConfigurationError
        If ``[dir]`` has an invalid schema or names a path outside ``repo``.
    """
    dir_table = document.get("dir", {})
    if not isinstance(dir_table, dict):
        raise ConfigurationError("[dir] must be a table")
    reject_unknown_keys(dir_table, _ALLOWED_DIR_KEYS, "[dir]")

    return DirSettings(
        log=resolve_optional_path(repo, "[dir].log", dir_table.get("log"), Path("logs")),
        temp=resolve_optional_path(repo, "[dir].temp", dir_table.get("temp"), Path("tmp")),
        uv_cache=resolve_optional_path(
            repo, "[dir].uv_cache", dir_table.get("uv_cache"), Path(".uv-cache")
        ),
    )
