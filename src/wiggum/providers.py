"""Provider selection and option validation for Ralph loop runners."""

from __future__ import annotations

from wiggum.defaults import (
    DEFAULT_MODEL_VERBOSITY,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT,
)

SUPPORTED_PROVIDERS = ("codex", "copilot")
DEFAULT_COPILOT_EXECUTABLE = "copilot"


def default_executable_for_provider(
    provider: str,
    codex_executable: str,
    provider_executable: str | None,
) -> str:
    """Return the effective executable for the selected provider.

    Parameters
    ----------
    provider : str
        Selected provider identifier.
    codex_executable : str
        Backward-compatible Codex executable override.
    provider_executable : str | None
        Provider-agnostic executable override.

    Returns
    -------
    str
        Executable to resolve and run.
    """
    if provider_executable is not None:
        return provider_executable
    if provider == "copilot":
        return DEFAULT_COPILOT_EXECUTABLE
    return codex_executable


def validate_provider_options(
    provider: str,
    reasoning_effort: str,
    model_verbosity: str,
    tool_output_token_limit: int,
    lean: bool,
    auto_approve: bool,
) -> str | None:
    """Validate provider-specific option compatibility.

    Parameters
    ----------
    provider : str
        Selected provider identifier.
    reasoning_effort : str
        Requested reasoning effort.
    model_verbosity : str
        Requested model verbosity.
    tool_output_token_limit : int
        Requested tool-output token limit.
    lean : bool
        Whether lean mode was requested.
    auto_approve : bool
        Whether unattended approval was requested.

    Returns
    -------
    str | None
        Human-readable validation error, or ``None`` when the configuration is
        supported.
    """
    if provider not in SUPPORTED_PROVIDERS:
        return f"--provider has an unsupported value: {provider}"
    if provider == "codex":
        return None
    if not auto_approve:
        return "--auto-approve is required for provider copilot"
    if reasoning_effort != DEFAULT_REASONING_EFFORT:
        return "--reasoning-effort is unsupported for provider copilot"
    if model_verbosity != DEFAULT_MODEL_VERBOSITY:
        return "--model-verbosity is unsupported for provider copilot"
    if tool_output_token_limit != DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT:
        return "--tool-output-token-limit is unsupported for provider copilot"
    if lean:
        return "--lean is unsupported for provider copilot"
    return None
