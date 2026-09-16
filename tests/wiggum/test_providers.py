"""Tests for provider selection and option validation."""

from __future__ import annotations

from wiggum.providers import default_executable_for_provider, validate_provider_options


def test_default_executable_for_provider_keeps_codex_backwards_compatibility() -> None:
    """Prefer the legacy Codex executable unless a generic override is given."""
    assert default_executable_for_provider("codex", "custom-codex", None) == "custom-codex"
    assert (
        default_executable_for_provider("codex", "custom-codex", "provider-binary")
        == "provider-binary"
    )


def test_default_executable_for_provider_uses_copilot_default() -> None:
    """Default Copilot to its own executable name."""
    assert default_executable_for_provider("copilot", "custom-codex", None) == "copilot"


def test_validate_provider_options_accepts_codex_defaults_and_overrides() -> None:
    """Preserve the existing Codex option surface."""
    assert (
        validate_provider_options(
            provider="codex",
            reasoning_effort="high",
            model_verbosity="medium",
            tool_output_token_limit=123,
            lean=True,
            auto_approve=False,
        )
        is None
    )


def test_validate_provider_options_rejects_unsupported_copilot_options() -> None:
    """Reject Copilot combinations that wiggum does not support yet."""
    assert (
        validate_provider_options(
            provider="copilot",
            reasoning_effort="medium",
            model_verbosity="low",
            tool_output_token_limit=12_000,
            lean=False,
            auto_approve=False,
        )
        == "--auto-approve is required for provider copilot"
    )
    assert (
        validate_provider_options(
            provider="copilot",
            reasoning_effort="high",
            model_verbosity="low",
            tool_output_token_limit=12_000,
            lean=False,
            auto_approve=True,
        )
        == "--reasoning-effort is unsupported for provider copilot"
    )
    assert (
        validate_provider_options(
            provider="copilot",
            reasoning_effort="medium",
            model_verbosity="medium",
            tool_output_token_limit=12_000,
            lean=False,
            auto_approve=True,
        )
        == "--model-verbosity is unsupported for provider copilot"
    )
    assert (
        validate_provider_options(
            provider="copilot",
            reasoning_effort="medium",
            model_verbosity="low",
            tool_output_token_limit=1,
            lean=False,
            auto_approve=True,
        )
        == "--tool-output-token-limit is unsupported for provider copilot"
    )
    assert (
        validate_provider_options(
            provider="copilot",
            reasoning_effort="medium",
            model_verbosity="low",
            tool_output_token_limit=12_000,
            lean=True,
            auto_approve=True,
        )
        == "--lean is unsupported for provider copilot"
    )


def test_validate_provider_options_rejects_unknown_provider() -> None:
    """Reject unknown providers in the Python API."""
    assert (
        validate_provider_options(
            provider="mystery",
            reasoning_effort="medium",
            model_verbosity="low",
            tool_output_token_limit=12_000,
            lean=False,
            auto_approve=False,
        )
        == "--provider has an unsupported value: mystery"
    )
