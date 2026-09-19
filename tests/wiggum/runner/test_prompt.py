"""Tests for Ralph loop prompt resolution."""

from __future__ import annotations

from wiggum.runner.prompt import prompt_for_selected_task


def _task(task_id: str, **overrides: object) -> dict[str, object]:
    """Create a valid JSON task contract.

    Parameters
    ----------
    task_id : str
        Task identifier.
    **overrides : object
        Contract field replacements.

    Returns
    -------
    dict[str, object]
        Valid task contract.
    """
    task: dict[str, object] = {
        "id": task_id,
        "title": "A task",
        "status": "pending",
        "priority": 1,
        "depends_on": [],
        "requirements": ["Implement it."],
        "tests": ["Test it."],
        "acceptance_commands": ["uv run -m pytest"],
    }
    task.update(overrides)
    return task


def test_prompt_formats_contract_as_json() -> None:
    """Format selected task contracts as readable JSON."""
    prompt = prompt_for_selected_task("base", "TASK-001", _task("TASK-001"))

    assert "```json" in prompt
    assert '"id": "TASK-001"' in prompt
