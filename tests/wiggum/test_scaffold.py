"""Tests for scaffolding Ralph loop template files into a repository."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wiggum.config import load_configuration
from wiggum.scaffold import scaffold


def test_scaffold_writes_all_template_files(tmp_path: Path) -> None:
    """Write the repository-specific Ralph configuration files."""
    written = scaffold(tmp_path)

    relative_paths = {path.relative_to(tmp_path).as_posix() for path in written}
    assert relative_paths == {
        "wiggum/config.toml",
        "wiggum/RALPH_PROJECT.md",
        "wiggum/TASKS.json",
        "wiggum/PROGRESS.md",
    }
    for path in written:
        assert path.read_text(encoding="utf-8").strip() != ""
    assert json.loads((tmp_path / "wiggum" / "TASKS.json").read_text(encoding="utf-8"))["tasks"]
    assert "wiggum/TASKS.json" in (tmp_path / "wiggum" / "config.toml").read_text(encoding="utf-8")


def test_scaffold_writes_a_config_toml_that_load_configuration_can_parse(tmp_path: Path) -> None:
    """Parse the scaffolded config.toml, including its [dir] and [run] tables, without error."""
    scaffold(tmp_path)

    configuration = load_configuration(tmp_path)

    assert configuration.paths.tasks == tmp_path / "wiggum" / "TASKS.json"
    assert configuration.dirs.log == tmp_path / "logs"
    assert configuration.run.agent_timeout_sec == 1800


def test_scaffold_refuses_to_overwrite_existing_files_by_default(tmp_path: Path) -> None:
    """Reject scaffolding when a destination file already exists."""
    destination = tmp_path / "wiggum" / "TASKS.json"
    destination.parent.mkdir()
    destination.write_text("existing\n", encoding="utf-8")

    with pytest.raises(FileExistsError, match=r"TASKS\.json"):
        scaffold(tmp_path)

    assert destination.read_text(encoding="utf-8") == "existing\n"
    assert not (tmp_path / "wiggum" / "config.toml").exists()


def test_scaffold_overwrites_existing_files_when_forced(tmp_path: Path) -> None:
    """Overwrite existing destination files when force is enabled."""
    destination = tmp_path / "wiggum" / "TASKS.json"
    destination.parent.mkdir()
    destination.write_text("existing\n", encoding="utf-8")

    scaffold(tmp_path, force=True)

    assert destination.read_text(encoding="utf-8") != "existing\n"
