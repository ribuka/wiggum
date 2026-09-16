"""Scaffold Ralph loop template files into a target repository."""

from __future__ import annotations

from importlib import resources
from pathlib import Path

_TEMPLATE_FILES: dict[str, str] = {
    "RALPH_PROJECT.md": "RALPH_PROJECT.md.template",
    "ralph_prompt.md": "ralph_prompt.md",
    "TASKS.md": "TASKS.md.template",
}


def scaffold(repo: Path, *, force: bool = False) -> list[Path]:
    """Copy Ralph loop template files into a target repository.

    Parameters
    ----------
    repo : Path
        Target repository root that receives the scaffolded files.
    force : bool, default False
        Overwrite files that already exist.

    Returns
    -------
    list[Path]
        Paths written by this call, in a stable order.

    Raises
    ------
    FileExistsError
        If a destination file already exists and ``force`` is ``False``.
    """
    templates_root = resources.files("wiggum") / "templates"
    destinations = {name: repo / name for name in _TEMPLATE_FILES}
    if not force:
        existing = sorted(str(path) for path in destinations.values() if path.exists())
        if existing:
            raise FileExistsError(
                "refusing to overwrite existing files: " + ", ".join(existing)
            )

    written: list[Path] = []
    for destination_name, template_name in _TEMPLATE_FILES.items():
        destination = destinations[destination_name]
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = (templates_root / template_name).read_text(encoding="utf-8")
        destination.write_text(content, encoding="utf-8")
        written.append(destination)
    return written
