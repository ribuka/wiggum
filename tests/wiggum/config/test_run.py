"""Tests for the optional [run] table."""

from __future__ import annotations

import pytest

from wiggum.config.document import ConfigurationError
from wiggum.config.run import CodexRunSettings, RunSettings, parse_run_settings
from wiggum.providers.constants import DEFAULT_EXECUTABLES


def test_parse_run_settings_defaults_when_run_table_is_absent() -> None:
    """Fall back to wiggum's built-in defaults when [run] is omitted."""
    document: dict[str, object] = {"paths": {}}

    settings = parse_run_settings(document)

    assert settings == RunSettings(
        manage_process_env=True,
        api_retry_count=None,
        api_retry_interval_sec=5,
        agent_timeout_sec=1800,
        executables=dict(DEFAULT_EXECUTABLES),
        codex=CodexRunSettings(tool_output_token_limit=12_000, model_verbosity="low", lean=False),
    )


def test_parse_run_settings_applies_every_configured_override() -> None:
    """Apply every [run], [run.executable], and [run.codex] override."""
    document = {
        "paths": {},
        "run": {
            "manage_process_env": False,
            "api_retry_count": 3,
            "api_retry_interval_sec": 10,
            "agent_timeout_sec": 60,
            "executable": {"codex": "/opt/codex", "claude": "/opt/claude"},
            "codex": {
                "tool_output_token_limit": 500,
                "model_verbosity": "high",
                "lean": True,
            },
        },
    }

    settings = parse_run_settings(document)

    assert settings.manage_process_env is False
    assert settings.api_retry_count == 3
    assert settings.api_retry_interval_sec == 10
    assert settings.agent_timeout_sec == 60
    assert settings.executables == {
        "codex": "/opt/codex",
        "copilot": "copilot",
        "claude": "/opt/claude",
    }
    assert settings.codex == CodexRunSettings(
        tool_output_token_limit=500, model_verbosity="high", lean=True
    )


@pytest.mark.parametrize(
    ("run_table", "message"),
    [
        ("not-a-table", r"\[run\] must be a table"),
        ({"unsupported": "value"}, r"\[run\] has unsupported keys"),
        ({"prompt_file": "wiggum/ralph_prompt.md"}, r"\[run\] has unsupported keys"),
        ({"logs_dir": "logs"}, r"\[run\] has unsupported keys"),
        ({"manage_process_env": "yes"}, r"\[run\]\.manage_process_env must be a boolean"),
        ({"api_retry_count": -1}, r"\[run\]\.api_retry_count must be a non-negative integer"),
        ({"api_retry_count": True}, r"\[run\]\.api_retry_count must be a non-negative integer"),
        (
            {"api_retry_interval_sec": -1},
            r"\[run\]\.api_retry_interval_sec must be a non-negative integer",
        ),
        ({"agent_timeout_sec": 0}, r"\[run\]\.agent_timeout_sec must be at least 1"),
        ({"executable": "not-a-table"}, r"\[run\.executable\] must be a table"),
        ({"executable": {"unsupported": "x"}}, r"\[run\.executable\] has unsupported keys"),
        ({"executable": {"codex": ""}}, r"\[run\.executable\]\.codex must be a non-empty string"),
        ({"codex": "not-a-table"}, r"\[run\.codex\] must be a table"),
        ({"codex": {"unsupported": "x"}}, r"\[run\.codex\] has unsupported keys"),
        ({"codex": {"tool_output_token_limit": 0}}, r"tool_output_token_limit must be at least 1"),
        ({"codex": {"model_verbosity": "loud"}}, r"model_verbosity has an unsupported value"),
        ({"codex": {"lean": "yes"}}, r"\[run\.codex\]\.lean must be a boolean"),
    ],
)
def test_parse_run_settings_rejects_invalid_values(
    run_table: object,
    message: str,
) -> None:
    """Reject an invalid [run] table or an out-of-range value within it."""
    document = {"paths": {}, "run": run_table}

    with pytest.raises(ConfigurationError, match=message):
        parse_run_settings(document)
