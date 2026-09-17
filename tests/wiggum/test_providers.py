"""Tests for AI model vendor provider selection and option validation."""

from __future__ import annotations

import pytest

from wiggum.providers import (
    ALL_REASONING_EFFORTS,
    CODEX_REASONING_EFFORTS,
    COPILOT_REASONING_EFFORTS,
    DEFAULT_EXECUTABLES,
    DEFAULT_PROVIDER,
    PROVIDERS,
    validate_provider_options,
)


def test_default_provider_is_codex() -> None:
    """Default to Codex so existing behavior remains unchanged."""
    assert DEFAULT_PROVIDER == "codex"
    assert PROVIDERS == ("codex", "copilot")
    assert DEFAULT_EXECUTABLES == {"codex": "codex", "copilot": "copilot"}


def test_reasoning_efforts_differ_per_provider() -> None:
    """Codex has no max tier and Copilot has no minimal tier."""
    assert CODEX_REASONING_EFFORTS == ("minimal", "low", "medium", "high", "xhigh")
    assert COPILOT_REASONING_EFFORTS == ("low", "medium", "high", "xhigh", "max")
    assert "max" not in CODEX_REASONING_EFFORTS
    assert "minimal" not in COPILOT_REASONING_EFFORTS
    assert set(ALL_REASONING_EFFORTS) == set(CODEX_REASONING_EFFORTS) | set(
        COPILOT_REASONING_EFFORTS
    )


def test_validate_provider_options_allows_any_codex_configuration() -> None:
    """Codex accepts every documented reasoning, verbosity, and lean option."""
    error = validate_provider_options(
        "codex",
        reasoning_effort="high",
        model_verbosity="high",
        tool_output_token_limit=1,
        lean=True,
        auto_approve=False,
    )

    assert error is None


def test_validate_provider_options_allows_copilot_defaults_with_auto_approve() -> None:
    """Copilot accepts default Codex-only options when auto-approve is set."""
    error = validate_provider_options(
        "copilot",
        reasoning_effort="medium",
        model_verbosity="low",
        tool_output_token_limit=12_000,
        lean=False,
        auto_approve=True,
    )

    assert error is None


def test_validate_provider_options_requires_auto_approve_for_copilot() -> None:
    """Reject Copilot runs without auto-approve because loops cannot pause."""
    error = validate_provider_options(
        "copilot",
        reasoning_effort="medium",
        model_verbosity="low",
        tool_output_token_limit=12_000,
        lean=False,
        auto_approve=False,
    )

    assert error == "--provider copilot requires --auto-approve"


def test_validate_provider_options_allows_copilot_reasoning_effort_override() -> None:
    """Forward supported reasoning-effort levels to the copilot provider."""
    error = validate_provider_options(
        "copilot",
        reasoning_effort="high",
        model_verbosity="low",
        tool_output_token_limit=12_000,
        lean=False,
        auto_approve=True,
    )

    assert error is None


def test_validate_provider_options_rejects_copilot_max_effort_for_codex() -> None:
    """Reject a Copilot-only reasoning-effort level for the codex provider."""
    error = validate_provider_options(
        "codex",
        reasoning_effort="max",
        model_verbosity="low",
        tool_output_token_limit=12_000,
        lean=False,
        auto_approve=False,
    )

    assert error == (
        "--provider codex does not support --reasoning-effort max "
        "(supported: minimal, low, medium, high, xhigh)"
    )


def test_validate_provider_options_rejects_minimal_effort_for_copilot() -> None:
    """Reject a Codex-only reasoning-effort level for the copilot provider."""
    error = validate_provider_options(
        "copilot",
        reasoning_effort="minimal",
        model_verbosity="low",
        tool_output_token_limit=12_000,
        lean=False,
        auto_approve=True,
    )

    assert error == (
        "--provider copilot does not support --reasoning-effort minimal "
        "(supported: low, medium, high, xhigh, max)"
    )


@pytest.mark.parametrize(
    ("kwargs", "expected_option"),
    [
        ({"model_verbosity": "high"}, "--model-verbosity"),
        ({"tool_output_token_limit": 1}, "--tool-output-token-limit"),
        ({"lean": True}, "--lean"),
    ],
)
def test_validate_provider_options_rejects_codex_only_options_for_copilot(
    kwargs: dict[str, object],
    expected_option: str,
) -> None:
    """Reject Codex-only inline configuration options for the copilot provider."""
    defaults = {
        "reasoning_effort": "medium",
        "model_verbosity": "low",
        "tool_output_token_limit": 12_000,
        "lean": False,
    }
    defaults.update(kwargs)

    error = validate_provider_options(
        "copilot",
        auto_approve=True,
        **defaults,
    )

    assert error is not None
    assert expected_option in error


def test_validate_provider_options_rejects_an_unsupported_provider_name() -> None:
    """Reject a provider name outside the supported set."""
    error = validate_provider_options(
        "unknown",
        reasoning_effort="medium",
        model_verbosity="low",
        tool_output_token_limit=12_000,
        lean=False,
        auto_approve=True,
    )

    assert error == "--provider has an unsupported value: unknown"
