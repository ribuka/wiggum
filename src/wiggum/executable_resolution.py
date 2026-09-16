"""Shared executable-path resolution for AI provider CLI processes."""

from __future__ import annotations

import shutil
from pathlib import Path


def resolve_executable(executable: str) -> str | None:
    """Resolve an executable name or path to an absolute executable path.

    Parameters
    ----------
    executable : str
        Executable name or path.

    Returns
    -------
    str | None
        Absolute executable path, or ``None`` when it cannot be found.
    """
    executable_path = Path(executable)
    if executable_path.is_file():
        return str(executable_path.resolve())

    resolved_path = shutil.which(executable)
    if resolved_path is None:
        return None
    return str(Path(resolved_path).resolve())
