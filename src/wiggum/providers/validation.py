"""Validation for options the selected provider CLI cannot honor."""

from __future__ import annotations

from wiggum.defaults import DEFAULT_MODEL_VERBOSITY, DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT
from wiggum.providers.constants import (
    CLAUDE,
    CLAUDE_REASONING_EFFORTS,
    CODEX,
    PROVIDERS,
)


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
        Requested reasoning effort. For Codex and GitHub Copilot CLI, support
        for a given level depends on the selected model, not the provider, so
        it is not validated here; the provider CLI is responsible for
        rejecting values its model does not support. Claude Code CLI's
        ``--effort`` flag has a fixed, provider-level set of accepted values
        (:data:`wiggum.providers.constants.CLAUDE_REASONING_EFFORTS`)
        regardless of model, so a value outside that set is rejected here.
    model_verbosity : str
        Requested model verbosity, from the Codex-only ``[run.codex]``
        configuration table.
    tool_output_token_limit : int
        Requested tool-output token limit, from the Codex-only
        ``[run.codex]`` configuration table.
    lean : bool
        Whether user Codex configuration and reasoning summaries should be
        ignored, from the Codex-only ``[run.codex]`` configuration table.
    auto_approve : bool
        Whether requests are automatically approved. Neither GitHub Copilot
        CLI nor Claude Code CLI has an interactive-approval fallback in a
        Ralph loop, so both require this to be enabled.

    Returns
    -------
    str | None
        Human-readable validation error, or ``None`` when every requested
        option is supported by ``provider``.
    """
    if provider not in PROVIDERS:
        return f"--provider has an unsupported value: {provider}"
    if provider == CODEX:
        return None

    unsupported: list[str] = []
    if model_verbosity != DEFAULT_MODEL_VERBOSITY:
        unsupported.append("run.codex.model_verbosity")
    if tool_output_token_limit != DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT:
        unsupported.append("run.codex.tool_output_token_limit")
    if lean:
        unsupported.append("run.codex.lean")
    if provider == CLAUDE and reasoning_effort not in CLAUDE_REASONING_EFFORTS:
        unsupported.append("--reasoning-effort")
    if unsupported:
        joined = ", ".join(unsupported)
        return f"--provider {provider} does not support: {joined}"
    if not auto_approve:
        return f"--provider {provider} requires --auto-approve"
    return None
