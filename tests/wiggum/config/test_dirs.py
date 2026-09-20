"""Tests for the optional [dir] table."""

from __future__ import annotations

from pathlib import Path

import pytest

from wiggum.config.dirs import DirSettings, parse_dir_settings
from wiggum.config.document import ConfigurationError


def test_parse_dir_settings_defaults_when_dir_table_is_absent(tmp_path: Path) -> None:
    """Fall back to wiggum's built-in defaults when [dir] is omitted."""
    document: dict[str, object] = {"paths": {}}

    settings = parse_dir_settings(tmp_path, document)

    assert settings == DirSettings(
        log=tmp_path / "logs",
        temp=tmp_path / "tmp",
        uv_cache=tmp_path / ".uv-cache",
    )


def test_parse_dir_settings_applies_every_configured_override(tmp_path: Path) -> None:
    """Apply every configured [dir] override."""
    document = {
        "paths": {},
        "dir": {
            "log": "custom-logs",
            "temp": "custom-tmp",
            "uv_cache": "custom-cache",
        },
    }

    settings = parse_dir_settings(tmp_path, document)

    assert settings == DirSettings(
        log=tmp_path / "custom-logs",
        temp=tmp_path / "custom-tmp",
        uv_cache=tmp_path / "custom-cache",
    )


@pytest.mark.parametrize(
    ("dir_table", "message"),
    [
        ("not-a-table", r"\[dir\] must be a table"),
        ({"unsupported": "value"}, r"\[dir\] has unsupported keys"),
        ({"logs_dir": "logs"}, r"\[dir\] has unsupported keys"),
        ({"log": "../escape"}, "must stay inside"),
    ],
)
def test_parse_dir_settings_rejects_invalid_values(
    tmp_path: Path,
    dir_table: object,
    message: str,
) -> None:
    """Reject an invalid [dir] table or a path outside the repository."""
    document = {"paths": {}, "dir": dir_table}

    with pytest.raises(ConfigurationError, match=message):
        parse_dir_settings(tmp_path, document)
