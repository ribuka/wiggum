"""Tests for required repository-local wiggum configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from wiggum.config import ConfigurationError, RalphPaths, load_ralph_paths


def _write_configuration(repo: Path, content: str) -> None:
    """Write configuration content at its required repository location.

    Parameters
    ----------
    repo : Path
        Repository root that receives the configuration.
    content : str
        TOML document content.
    """
    config_dir = repo / "wiggum"
    config_dir.mkdir()
    (config_dir / "config.toml").write_text(content, encoding="utf-8")


def test_load_ralph_paths_resolves_all_configured_paths(tmp_path: Path) -> None:
    """Resolve the required paths relative to the repository root."""
    _write_configuration(
        tmp_path,
        "[paths]\n"
        'tasks = "planning/tasks.json"\n'
        'project = "instructions/ralph.md"\n'
        'progress = "state/progress.md"\n',
    )

    assert load_ralph_paths(tmp_path) == RalphPaths(
        tasks=tmp_path / "planning" / "tasks.json",
        project=tmp_path / "instructions" / "ralph.md",
        progress=tmp_path / "state" / "progress.md",
    )


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("", "configuration must contain only"),
        ("[paths]\ntasks = 1\nproject = 'a'\nprogress = 'b'\n", "must be a non-empty string"),
        ("[paths]\ntasks = '../tasks.json'\nproject = 'a'\nprogress = 'b'\n", "must stay inside"),
        ("[paths]\ntasks = 'a'\nproject = 'b'\n", "must contain only"),
    ],
)
def test_load_ralph_paths_rejects_invalid_schema(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    """Reject malformed configuration and paths outside the repository."""
    _write_configuration(tmp_path, content)

    with pytest.raises(ConfigurationError, match=message):
        load_ralph_paths(tmp_path)


def test_load_ralph_paths_requires_config_file(tmp_path: Path) -> None:
    """Raise when the required repository configuration is absent."""
    with pytest.raises(ConfigurationError, match="Required configuration does not exist"):
        load_ralph_paths(tmp_path)
