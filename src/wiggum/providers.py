"""AI model vendor (provider) selection boundary for the Ralph loop runner.

Codex CLI and GitHub Copilot CLI expose different command-line surfaces for
model selection, approval/sandbox handling, and token-usage reporting. This
module defines the provider names wiggum accepts and validates that
provider-specific options are not silently ignored or misapplied.
"""

from __future__ import annotations

from wiggum.defaults import (
    DEFAULT_MODEL_VERBOSITY,
    DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT,
)

CODEX = "codex"
COPILOT = "copilot"
PROVIDERS = (CODEX, COPILOT)
DEFAULT_PROVIDER = CODEX
DEFAULT_EXECUTABLES = {CODEX: "codex", COPILOT: "copilot"}

# Each provider CLI supports a different set of --reasoning-effort levels:
# Codex has no "max" tier, and GitHub Copilot CLI has no "minimal" tier.
CODEX_REASONING_EFFORTS = ("minimal", "low", "medium", "high", "xhigh")
COPILOT_REASONING_EFFORTS = ("low", "medium", "high", "xhigh", "max")
REASONING_EFFORTS_BY_PROVIDER = {
    CODEX: CODEX_REASONING_EFFORTS,
    COPILOT: COPILOT_REASONING_EFFORTS,
}
# Union of every provider's supported levels, in first-seen order, for CLI
# argument parsing before a provider-specific check can run.
ALL_REASONING_EFFORTS = tuple(
    dict.fromkeys(CODEX_REASONING_EFFORTS + COPILOT_REASONING_EFFORTS)
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
        Selected AI model vendor; one of :data:`PROVIDERS`.
    reasoning_effort : str
        Requested reasoning effort. Each provider supports a different set of
        levels; see :data:`REASONING_EFFORTS_BY_PROVIDER`.
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
    if provider not in PROVIDERS:
        return f"--provider has an unsupported value: {provider}"
    allowed_efforts = REASONING_EFFORTS_BY_PROVIDER[provider]
    if reasoning_effort not in allowed_efforts:
        supported = ", ".join(allowed_efforts)
        return (
            f"--provider {provider} does not support --reasoning-effort "
            f"{reasoning_effort} (supported: {supported})"
        )
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
