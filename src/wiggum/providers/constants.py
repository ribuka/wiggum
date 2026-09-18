"""Provider names, defaults, and known reasoning-effort levels.

Reasoning-effort support depends on the selected model, not the selected AI
model vendor. This module therefore tracks the union of effort strings known
to the supported CLIs; the underlying provider CLI is responsible for
rejecting a value its selected model does not support.
"""

from __future__ import annotations

CODEX = "codex"
COPILOT = "copilot"
CLAUDE = "claude"
PROVIDERS = (CODEX, COPILOT, CLAUDE)
DEFAULT_PROVIDER = CODEX
DEFAULT_EXECUTABLES = {CODEX: "codex", COPILOT: "copilot", CLAUDE: "claude"}

# Union of every reasoning-effort level known to either provider CLI. Actual
# support for a given level ultimately depends on the selected model, so this
# set is intentionally permissive rather than gated per provider.
REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max")

# Reasoning-effort levels Claude Code CLI's --effort flag accepts. Unlike
# Codex and GitHub Copilot CLI, this is a hard provider-level limit rather
# than a model-dependent one: "none" and "minimal" are not in this set and
# are always rejected for the claude provider, regardless of model.
CLAUDE_REASONING_EFFORTS = ("low", "medium", "high", "xhigh", "max")
