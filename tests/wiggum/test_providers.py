"""Tests for AI model vendor provider selection and option validation."""

from __future__ import annotations

import pytest

from wiggum.providers import (
    CODEX,
    COPILOT,
    DEFAULT_EXECUTABLES,
    DEFAULT_PROVIDER,
    PROVIDERS,
    REASONING_EFFORTS,
    get_adapter,
    validate_provider_options,
)


def test_get_adapter_returns_the_matching_provider_name() -> None:
    """Return an adapter whose name matches the requested provider."""
    assert get_adapter(CODEX).name == CODEX
    assert get_adapter(COPILOT).name == COPILOT


def test_get_adapter_rejects_an_unsupported_provider_name() -> None:
    """Reject a provider name outside the supported set."""
    with pytest.raises(ValueError, match="unknown"):
        get_adapter("unknown")


def test_default_provider_is_codex() -> None:
    """Default to Codex so existing behavior remains unchanged."""
    assert DEFAULT_PROVIDER == "codex"
    assert PROVIDERS == ("codex", "copilot")
    assert DEFAULT_EXECUTABLES == {"codex": "codex", "copilot": "copilot"}


def test_reasoning_efforts_are_not_gated_per_provider() -> None:
    """Track every reasoning-effort level known to any provider CLI.

    Support for a given level depends on the selected model, not the
    provider, so wiggum does not reject a level based on provider alone.
    """
    assert REASONING_EFFORTS == ("minimal", "low", "medium", "high", "xhigh", "max")


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


def test_validate_provider_options_allows_a_copilot_only_reasoning_effort_for_codex() -> None:
    """Do not reject reasoning-effort levels by provider; models decide support."""
    error = validate_provider_options(
        "codex",
        reasoning_effort="max",
        model_verbosity="low",
        tool_output_token_limit=12_000,
        lean=False,
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


def test_validate_provider_options_allows_a_codex_only_reasoning_effort_for_copilot() -> None:
    """Do not reject reasoning-effort levels by provider; models decide support."""
    error = validate_provider_options(
        "copilot",
        reasoning_effort="minimal",
        model_verbosity="low",
        tool_output_token_limit=12_000,
        lean=False,
        auto_approve=True,
    )

    assert error is None


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
