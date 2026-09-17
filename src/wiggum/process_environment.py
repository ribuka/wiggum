"""Shared child-process environment construction for one Ralph loop attempt.

Both Codex CLI and GitHub Copilot CLI child processes are launched with the
same isolated cache and temporary directories, regardless of which provider
is selected, so this construction lives outside any provider-specific module.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def build_process_environment(
    temp_dir: Path,
    *,
    uv_cache_dir: Path,
    manage_process_env: bool = True,
) -> dict[str, str]:
    """Build a child-process environment for one provider invocation.

    Parameters
    ----------
    temp_dir : Path
        Root temporary directory used to create this loop's isolated runtime
        directory.
    uv_cache_dir : Path
        Directory used for ``UV_CACHE_DIR``.
    manage_process_env : bool, default True
        Whether to inject ``UV_CACHE_DIR``, ``TMP``, and ``TEMP`` into the
        child environment. Disable this for projects that do not use uv or
        that manage their own temporary directories.

    Returns
    -------
    dict[str, str]
        Copy of the current environment, optionally directed into isolated
        cache and temporary paths.
    """
    environment = os.environ.copy()
    if not manage_process_env:
        return environment

    runtime_root = (temp_dir / "runtime").resolve()
    runtime_root.mkdir(parents=True, exist_ok=True)
    runtime_directory = Path(tempfile.mkdtemp(prefix="ralph-", dir=runtime_root))
    uv_cache_directory = uv_cache_dir.resolve()
    uv_cache_directory.mkdir(parents=True, exist_ok=True)

    environment["UV_CACHE_DIR"] = str(uv_cache_directory)
    environment["TMP"] = str(runtime_directory)
    environment["TEMP"] = str(runtime_directory)
    return environment
