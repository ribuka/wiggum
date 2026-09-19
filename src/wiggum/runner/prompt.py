"""Ralph loop prompt resolution: default prompt text and task-scoped prompts."""

from __future__ import annotations

import json
from importlib import resources


def default_prompt_text() -> str:
    """Return wiggum's bundled Ralph rules and loop prompt.

    Returns
    -------
    str
        UTF-8 text of the packaged general rules followed by the loop prompt.
    """
    templates_root = resources.files("wiggum") / "templates"
    general_rules = (templates_root / "RALPH.md").read_text(encoding="utf-8")
    loop_prompt = (templates_root / "ralph_prompt.md").read_text(encoding="utf-8")
    return f"{general_rules.rstrip()}\n\n{loop_prompt}"


def prompt_for_selected_task(
    prompt: str,
    selected_task_id: str,
    selected_task_contract: dict[str, object],
) -> str:
    """Append the runner-selected task contract to a Codex prompt.

    Parameters
    ----------
    prompt : str
        Base prompt containing the general Ralph loop instructions.
    selected_task_id : str
        Task identifier selected from the ledger by the parent runner.
    selected_task_contract : dict[str, object]
        Complete JSON object for the selected task.

    Returns
    -------
    str
        Prompt that names the only task the Codex child may process.
    """
    return (
        f"{prompt.rstrip()}\n\n"
        "## Runner-selected task\n\n"
        f"The parent runner selected `{selected_task_id}` for this loop. The complete "
        "task contract is below. Work only on it; do not select or start another task. "
        "Do not read `TASKS.json` to select a task or discover requirements; read it only "
        "when updating this task's status. If the ledger conflicts with this contract, "
        f"preserve existing changes and report `TASK_BLOCKED: {selected_task_id}`.\n\n"
        f"```json\n{json.dumps(selected_task_contract, ensure_ascii=False, indent=2)}\n```\n"
    )
