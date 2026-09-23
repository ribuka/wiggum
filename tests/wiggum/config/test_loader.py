"""Integration tests for reading wiggum/config.toml end to end."""

from __future__ import annotations

from pathlib import Path

import pytest

from wiggum.config import (
    Configuration,
    DirSettings,
    RalphPaths,
    RunSettings,
    load_configuration,
)
from wiggum.config.document import ConfigurationError
from wiggum.config.run import CodexRunSettings
from wiggum.providers.constants import DEFAULT_EXECUTABLES


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


def test_load_configuration_defaults_run_settings_when_run_table_is_absent(tmp_path: Path) -> None:
    """Load [paths] and default [run] tunables from a minimal configuration."""
    _write_configuration(
        tmp_path,
        "[paths]\n"
        'tasks = "wiggum/TASKS.json"\n'
        'project = "wiggum/RALPH_PROJECT.md"\n'
        'progress = "wiggum/PROGRESS.md"\n',
    )

    configuration = load_configuration(tmp_path)

    assert configuration == Configuration(
        paths=RalphPaths(
            tasks=tmp_path / "wiggum" / "TASKS.json",
            project=tmp_path / "wiggum" / "RALPH_PROJECT.md",
            progress=tmp_path / "wiggum" / "PROGRESS.md",
            prompt_file=None,
        ),
        dirs=DirSettings(
            log=tmp_path / "logs",
            temp=tmp_path / "tmp",
            uv_cache=tmp_path / ".uv-cache",
        ),
        run=RunSettings(
            manage_process_env=True,
            api_retry_count=None,
            api_retry_interval_sec=5,
            agent_timeout_sec=1800,
            executables=dict(DEFAULT_EXECUTABLES),
            codex=CodexRunSettings(
                tool_output_token_limit=12_000, model_verbosity="low", lean=False
            ),
        ),
    )


def test_load_configuration_reads_the_dir_and_run_tables(tmp_path: Path) -> None:
    """Load [dir] and [run] overrides alongside [paths]."""
    _write_configuration(
        tmp_path,
        "[paths]\n"
        'tasks = "wiggum/TASKS.json"\n'
        'project = "wiggum/RALPH_PROJECT.md"\n'
        'progress = "wiggum/PROGRESS.md"\n'
        "\n"
        "[dir]\n"
        'log = "custom-logs"\n'
        "\n"
        "[run]\n"
        "agent_timeout_sec = 60\n"
        "\n"
        "[run.codex]\n"
        "lean = true\n",
    )

    configuration = load_configuration(tmp_path)

    assert configuration.dirs.log == tmp_path / "custom-logs"
    assert configuration.run.agent_timeout_sec == 60
    assert configuration.run.codex.lean is True


def test_load_configuration_reads_the_optional_prompt_file(tmp_path: Path) -> None:
    """Load an explicit [paths].prompt_file alongside the required paths."""
    _write_configuration(
        tmp_path,
        "[paths]\n"
        'tasks = "wiggum/TASKS.json"\n'
        'project = "wiggum/RALPH_PROJECT.md"\n'
        'progress = "wiggum/PROGRESS.md"\n'
        'prompt_file = "wiggum/ralph_prompt.md"\n',
    )

    configuration = load_configuration(tmp_path)

    assert configuration.paths.prompt_file == tmp_path / "wiggum" / "ralph_prompt.md"


def test_load_configuration_requires_config_file(tmp_path: Path) -> None:
    """Raise when the required repository configuration is absent."""
    with pytest.raises(ConfigurationError, match="Required configuration does not exist"):
        load_configuration(tmp_path)


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("", "configuration must contain \\[paths\\]"),
        ("[paths]\ntasks = 1\nproject = 'a'\nprogress = 'b'\n", "must be a non-empty string"),
        ("[unexpected]\n", "configuration must contain \\[paths\\]"),
        ("not valid toml", "Invalid configuration"),
    ],
)
def test_load_configuration_rejects_invalid_documents(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    """Reject malformed TOML or an invalid top-level or [paths] schema."""
    _write_configuration(tmp_path, content)

    with pytest.raises(ConfigurationError, match=message):
        load_configuration(tmp_path)
