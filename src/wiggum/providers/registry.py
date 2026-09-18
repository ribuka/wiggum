"""Provider adapter registry mapping provider names to their adapters."""

from __future__ import annotations

from collections.abc import Callable

from wiggum.providers.claude import adapter as claude_adapter
from wiggum.providers.codex import adapter as codex_adapter
from wiggum.providers.constants import CLAUDE, CODEX, COPILOT, PROVIDERS
from wiggum.providers.contract import ProviderAdapter
from wiggum.providers.copilot import adapter as copilot_adapter

_ADAPTER_FACTORIES: dict[str, Callable[[], ProviderAdapter]] = {
    CODEX: codex_adapter,
    COPILOT: copilot_adapter,
    CLAUDE: claude_adapter,
}


def get_adapter(provider: str) -> ProviderAdapter:
    """Return the process-lifecycle adapter for one AI model vendor.

    Parameters
    ----------
    provider : str
        Selected AI model vendor; one of :data:`wiggum.providers.PROVIDERS`.

    Returns
    -------
    ProviderAdapter
        Adapter exposing executable resolution, command construction,
        process execution, retry-failure detection, and usage parsing for
        ``provider``.

    Raises
    ------
    ValueError
        If ``provider`` is not one of :data:`wiggum.providers.PROVIDERS`.
    """
    if provider not in PROVIDERS:
        raise ValueError(f"--provider has an unsupported value: {provider}")
    return _ADAPTER_FACTORIES[provider]()
