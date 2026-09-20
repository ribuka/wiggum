"""Load the full repository-local wiggum configuration in one TOML read."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wiggum.config.dirs import DirSettings, parse_dir_settings
from wiggum.config.document import read_document
from wiggum.config.paths import RalphPaths, parse_paths
from wiggum.config.run import RunSettings, parse_run_settings


@dataclass(frozen=True)
class Configuration:
    """Fully resolved ``wiggum/config.toml`` contents.

    Parameters
    ----------
    paths : RalphPaths
        Resolved Ralph file paths from the required ``[paths]`` table.
    dirs : DirSettings
        Resolved directories from the optional ``[dir]`` table.
    run : RunSettings
        Resolved run tunables from the optional ``[run]`` table.
    """

    paths: RalphPaths
    dirs: DirSettings
    run: RunSettings


def load_configuration(repo: Path) -> Configuration:
    """Load and validate a repository's ``wiggum/config.toml``.

    Parameters
    ----------
    repo : Path
        Resolved Git repository root.

    Returns
    -------
    Configuration
        Resolved Ralph file paths, directories, and run tunables.

    Raises
    ------
    ConfigurationError
        If the configuration is absent, invalid TOML, or has an invalid
        schema.
    """
    document = read_document(repo)
    return Configuration(
        paths=parse_paths(repo, document),
        dirs=parse_dir_settings(repo, document),
        run=parse_run_settings(document),
    )
