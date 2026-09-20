"""Read and validate a repository's ``wiggum/config.toml``.

Submodules
----------
``wiggum.config.document``
    Shared TOML document loading and repository-relative path resolution.
``wiggum.config.paths``
    Required ``[paths]`` table: task ledger, project instructions, and
    progress record locations.
``wiggum.config.dirs``
    Optional ``[dir]`` table: directories wiggum uses while running a loop.
``wiggum.config.run``
    Optional ``[run]`` table: run tunables that rarely change between runs.
``wiggum.config.loader``
    ``load_configuration`` combining ``[paths]``, ``[dir]``, and ``[run]``
    from one TOML read.
"""

from __future__ import annotations

from wiggum.config.dirs import DirSettings
from wiggum.config.document import CONFIG_PATH, ConfigurationError
from wiggum.config.loader import Configuration, load_configuration
from wiggum.config.paths import DEFAULT_PATHS, RalphPaths
from wiggum.config.run import CodexRunSettings, RunSettings

__all__ = [
    "CONFIG_PATH",
    "DEFAULT_PATHS",
    "CodexRunSettings",
    "Configuration",
    "ConfigurationError",
    "DirSettings",
    "RalphPaths",
    "RunSettings",
    "load_configuration",
]
