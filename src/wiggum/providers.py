"""AI model vendor (provider) selection boundary for the Ralph loop runner.

Codex CLI and GitHub Copilot CLI expose different command-line surfaces for
model selection, approval/sandbox handling, and token-usage reporting. This
module defines the provider names wiggum accepts and validates that
Codex-only options are not silently ignored when GitHub Copilot is selected.
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
# GitHub Copilot CLI supports --reasoning-effort but, unlike Codex, has no
# "minimal" level.
COPILOT_REASONING_EFFORTS = ("low", "medium", "high", "xhigh")


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
        Requested reasoning effort. Supported by both providers, but GitHub
        Copilot CLI has no ``"minimal"`` level.
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
    if provider != COPILOT:
        return None

    unsupported: list[str] = []
    if reasoning_effort not in COPILOT_REASONING_EFFORTS:
        unsupported.append("--reasoning-effort minimal")
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
