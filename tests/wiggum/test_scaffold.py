"""Tests for scaffolding Ralph loop template files into a repository."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wiggum.scaffold import scaffold


def test_scaffold_writes_all_template_files(tmp_path: Path) -> None:
    """Write the repository-specific Ralph configuration files."""
    written = scaffold(tmp_path)

    names = {path.name for path in written}
    assert names == {"RALPH_PROJECT.md", "ralph_prompt.md", "TASKS.json"}
    for path in written:
        assert path.parent == tmp_path
        assert path.read_text(encoding="utf-8").strip() != ""
    assert json.loads((tmp_path / "TASKS.json").read_text(encoding="utf-8"))["tasks"]


def test_scaffold_refuses_to_overwrite_existing_files_by_default(tmp_path: Path) -> None:
    """Reject scaffolding when a destination file already exists."""
    (tmp_path / "TASKS.json").write_text("existing\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match="TASKS.json"):
        scaffold(tmp_path)

    assert (tmp_path / "TASKS.json").read_text(encoding="utf-8") == "existing\n"
    assert not (tmp_path / "RALPH.md").exists()


def test_scaffold_overwrites_existing_files_when_forced(tmp_path: Path) -> None:
    """Overwrite existing destination files when force is enabled."""
    (tmp_path / "TASKS.json").write_text("existing\n", encoding="utf-8")

    scaffold(tmp_path, force=True)

    assert (tmp_path / "TASKS.json").read_text(encoding="utf-8") != "existing\n"
