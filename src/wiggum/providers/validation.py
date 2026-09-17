"""Validation for options the selected provider CLI cannot honor."""

from __future__ import annotations

from wiggum.defaults import (
    DEFAULT_MODEL_VERBOSITY,
    DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT,
)
from wiggum.providers.constants import COPILOT, PROVIDERS


def validate_provider_options(
    provider: str,
    *,
    reasoning_effort: str,
    model_verbosity: str,
    tool_output_token_limit: int,
    lean: bool,
    auto_approve: bool,
) -> str | None:
    """Return a validation error for options the selected provider cannot honor.

    Parameters
    ----------
    provider : str
        Selected AI model vendor; one of :data:`wiggum.providers.PROVIDERS`.
    reasoning_effort : str
        Requested reasoning effort. Not validated here because support for a
        given level depends on the selected model, not the provider; the
        provider CLI is responsible for rejecting values its model does not
        support.
    model_verbosity : str
        Requested model verbosity, a Codex-only inline configuration value.
    tool_output_token_limit : int
        Requested tool-output token limit, a Codex-only inline configuration
        value.
    lean : bool
        Whether user Codex configuration and reasoning summaries should be
        ignored; a Codex-only behavior.
    auto_approve : bool
        Whether requests are automatically approved. GitHub Copilot CLI has
        no interactive-approval fallback in a Ralph loop, so it requires
        this to be enabled.

    Returns
    -------
    str | None
        Human-readable validation error, or ``None`` when every requested
        option is supported by ``provider``.
    """
    del reasoning_effort
    if provider not in PROVIDERS:
        return f"--provider has an unsupported value: {provider}"
    if provider != COPILOT:
        return None

    unsupported: list[str] = []
    if model_verbosity != DEFAULT_MODEL_VERBOSITY:
        unsupported.append("--model-verbosity")
    if tool_output_token_limit != DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT:
        unsupported.append("--tool-output-token-limit")
    if lean:
        unsupported.append("--lean")
    if unsupported:
        joined = ", ".join(unsupported)
        return f"--provider copilot does not support: {joined}"
    if not auto_approve:
        return "--provider copilot requires --auto-approve"
    return None
