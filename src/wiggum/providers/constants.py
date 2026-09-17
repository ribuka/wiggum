"""Provider names, defaults, and known reasoning-effort levels.

Reasoning-effort support depends on the selected model, not the selected AI
model vendor. This module therefore tracks the union of effort strings known
to the supported CLIs; the underlying provider CLI is responsible for
rejecting a value its selected model does not support.
"""

from __future__ import annotations

CODEX = "codex"
COPILOT = "copilot"
PROVIDERS = (CODEX, COPILOT)
DEFAULT_PROVIDER = CODEX
DEFAULT_EXECUTABLES = {CODEX: "codex", COPILOT: "copilot"}

# Union of every reasoning-effort level known to either provider CLI. Actual
# support for a given level ultimately depends on the selected model, so this
# set is intentionally permissive rather than gated per provider.
REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")
