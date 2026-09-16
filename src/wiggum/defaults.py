"""Shared default tunables for the Ralph loop runner."""

from __future__ import annotations

DEFAULT_MAX_LOOPS = 20
DEFAULT_API_RETRY_COUNT = None
DEFAULT_API_RETRY_INTERVAL_SEC = 5
DEFAULT_CODEX_TIMEOUT_SEC = 1_800
DEFAULT_REASONING_EFFORT = "medium"
DEFAULT_MODEL_VERBOSITY = "low"
DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT = 12_000
REASONING_EFFORTS = ("minimal", "low", "medium", "high", "xhigh")
MODEL_VERBOSITIES = ("low", "medium", "high")
