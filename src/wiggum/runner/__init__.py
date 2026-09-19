"""Ralph loop orchestration: task selection, agent execution, and Git commits.

Submodules
----------
``wiggum.runner.validation``
    Preflight argument and Git-state validation run once before the first
    loop starts.
``wiggum.runner.loop``
    One Ralph loop's process startup, retry, usage accounting, log
    finalization, and task-ledger progression, plus the public ``run`` entry
    point.
``wiggum.runner.prompt``
    Ralph loop prompt resolution: the bundled default prompt and the
    per-task prompt sent to the selected provider.
"""

from __future__ import annotations

from wiggum.runner.loop import run

__all__ = ["run"]
