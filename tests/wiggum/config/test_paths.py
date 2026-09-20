"""Tests for the [paths] table."""

from __future__ import annotations

from pathlib import Path

import pytest

from wiggum.config.document import ConfigurationError
from wiggum.config.paths import RalphPaths, parse_paths


def test_parse_paths_resolves_all_configured_paths(tmp_path: Path) -> None:
    """Resolve the required paths relative to the repository root."""
    document = {
        "paths": {
            "tasks": "planning/tasks.json",
            "project": "instructions/ralph.md",
            "progress": "state/progress.md",
        }
    }

    assert parse_paths(tmp_path, document) == RalphPaths(
        tasks=tmp_path / "planning" / "tasks.json",
        project=tmp_path / "instructions" / "ralph.md",
        progress=tmp_path / "state" / "progress.md",
        prompt_file=None,
    )


def test_parse_paths_resolves_the_optional_prompt_file(tmp_path: Path) -> None:
    """Resolve an explicit prompt_file relative to the repository root."""
    document = {
        "paths": {
            "tasks": "a",
            "project": "b",
            "progress": "c",
            "prompt_file": "wiggum/ralph_prompt.md",
        }
    }

    paths = parse_paths(tmp_path, document)

    assert paths.prompt_file == tmp_path / "wiggum" / "ralph_prompt.md"


@pytest.mark.parametrize(
    ("paths_table", "message"),
    [
        ({"tasks": 1, "project": "a", "progress": "b"}, "must be a non-empty string"),
        ({"tasks": "../tasks.json", "project": "a", "progress": "b"}, "must stay inside"),
        ({"tasks": "a", "project": "b"}, "must contain only"),
        ({"tasks": "a", "project": "b", "progress": "c", "unexpected": "d"}, "must contain only"),
        ("not-a-table", "must contain only"),
    ],
)
def test_parse_paths_rejects_invalid_schema(
    tmp_path: Path,
    paths_table: object,
    message: str,
) -> None:
    """Reject malformed [paths] tables and paths outside the repository."""
    document = {"paths": paths_table}

    with pytest.raises(ConfigurationError, match=message):
        parse_paths(tmp_path, document)
