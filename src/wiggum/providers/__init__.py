"""AI model vendor (provider) selection boundary for the Ralph loop runner.

Codex CLI and GitHub Copilot CLI expose different command-line surfaces for
model selection, approval/sandbox handling, and token-usage reporting. This
package defines the provider names wiggum accepts, the uniform adapter
contract each provider implements, and validation that provider-specific
options are not silently ignored or misapplied.

Submodules
----------
``wiggum.providers.constants``
    Provider names, defaults, and known reasoning-effort levels.
``wiggum.providers.contract``
    ``CommandOptions``/``ProviderAdapter`` dataclasses shared by every
    provider implementation.
``wiggum.providers.codex`` / ``wiggum.providers.copilot`` / ``wiggum.providers.claude``
    Concrete adapters for each supported provider.
``wiggum.providers.registry``
    ``get_adapter`` lookup from provider name to its adapter.
``wiggum.providers.validation``
    ``validate_provider_options`` for options a provider cannot honor.
"""

from __future__ import annotations

from wiggum.providers.constants import (
    CLAUDE,
    CODEX,
    COPILOT,
    DEFAULT_EXECUTABLES,
    DEFAULT_PROVIDER,
    PROVIDERS,
    REASONING_EFFORTS,
)
from wiggum.providers.contract import CommandOptions, ProviderAdapter
from wiggum.providers.registry import get_adapter
from wiggum.providers.validation import validate_provider_options

__all__ = [
    "CLAUDE",
    "CODEX",
    "COPILOT",
    "DEFAULT_EXECUTABLES",
    "DEFAULT_PROVIDER",
    "PROVIDERS",
    "REASONING_EFFORTS",
    "CommandOptions",
    "ProviderAdapter",
    "get_adapter",
    "validate_provider_options",
]
