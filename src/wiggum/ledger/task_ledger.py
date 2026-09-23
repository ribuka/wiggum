"""Validation and selection logic for the ``TASKS.json`` Ralph ledger."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

TASK_ID_PATTERN = re.compile(r"TASK-\d{3}")
TASK_STATUSES = frozenset({"pending", "in_progress", "completed", "blocked"})
_TASK_KEYS = frozenset(
    {
        "id",
        "title",
        "status",
        "priority",
        "depends_on",
        "requirements",
        "tests",
        "acceptance_commands",
    }
)


@dataclass(frozen=True)
class RalphTask:
    """Task metadata required for Ralph progress and selection.

    Attributes
    ----------
    task_id : str
        Stable ``TASK-XXX`` identifier.
    status : str
        Current task ledger status.
    priority : int
        Numeric task selection priority.
    dependencies : tuple[str, ...]
        Task identifiers that must be completed first.
    contract : dict[str, object]
        Complete validated JSON task object.
    """

    task_id: str
    status: str
    priority: int
    dependencies: tuple[str, ...]
    contract: dict[str, object]


def _require_string(value: object, field: str, task_id: str) -> str:
    """Validate and return a non-empty task string field.

    Parameters
    ----------
    value : object
        Value declared in the JSON task object.
    field : str
        Field being validated.
    task_id : str
        Task identifier used in diagnostic output.

    Returns
    -------
    str
        The validated string.
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{task_id} has invalid {field}: expected a non-empty string")
    return value


def _require_string_array(
    value: object,
    field: str,
    task_id: str,
    *,
    allow_empty: bool = False,
) -> tuple[str, ...]:
    """Validate and return a non-empty array of non-empty strings.

    Parameters
    ----------
    value : object
        Value declared in the JSON task object.
    field : str
        Field being validated.
    task_id : str
        Task identifier used in diagnostic output.

    Returns
    -------
    tuple[str, ...]
        The validated string values.
    """
    if not isinstance(value, list) or (not value and not allow_empty):
        raise ValueError(f"{task_id} has invalid {field}: expected a non-empty string array")
    values = tuple(value)
    if any(not isinstance(item, str) or not item.strip() for item in values):
        raise ValueError(f"{task_id} has invalid {field}: expected non-empty strings")
    return values


def _parse_task(value: object, index: int) -> RalphTask:
    """Validate one JSON task object.

    Parameters
    ----------
    value : object
        Candidate task object.
    index : int
        Zero-based task position for diagnostics when its identifier is invalid.

    Returns
    -------
    RalphTask
        Validated task metadata and full contract.
    """
    label = f"task at index {index}"
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    keys = set(value)
    if keys != _TASK_KEYS:
        missing = sorted(_TASK_KEYS - keys)
        unknown = sorted(keys - _TASK_KEYS)
        details = []
        if missing:
            details.append("missing keys: " + ", ".join(missing))
        if unknown:
            details.append("unknown keys: " + ", ".join(unknown))
        raise ValueError(f"{label} has invalid schema ({'; '.join(details)})")
    task_id = _require_string(value["id"], "id", label)
    if TASK_ID_PATTERN.fullmatch(task_id) is None:
        raise ValueError(f"{label} has invalid id: {task_id}")
    _require_string(value["title"], "title", task_id)
    status = _require_string(value["status"], "status", task_id)
    if status not in TASK_STATUSES:
        raise ValueError(f"{task_id} has invalid status: {status}")
    priority = value["priority"]
    if not isinstance(priority, int) or isinstance(priority, bool) or priority < 1:
        raise ValueError(f"{task_id} has invalid priority: expected an integer >= 1")
    dependencies = _require_string_array(
        value["depends_on"],
        "depends_on",
        task_id,
        allow_empty=True,
    )
    if any(TASK_ID_PATTERN.fullmatch(dependency) is None for dependency in dependencies):
        raise ValueError(f"{task_id} has invalid depends_on values")
    _require_string_array(value["requirements"], "requirements", task_id)
    _require_string_array(value["tests"], "tests", task_id)
    _require_string_array(value["acceptance_commands"], "acceptance_commands", task_id)
    return RalphTask(task_id, status, priority, dependencies, dict(value))


def read_ralph_tasks(tasks_path: Path) -> tuple[RalphTask, ...]:
    """Read and validate task metadata from a JSON ledger.

    Parameters
    ----------
    tasks_path : Path
        UTF-8 ``TASKS.json`` file.

    Returns
    -------
    tuple[RalphTask, ...]
        Validated task metadata in ledger order.

    Raises
    ------
    ValueError
        If the JSON syntax or fixed ledger schema is invalid.
    """
    try:
        document = json.loads(tasks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {tasks_path}: {error.msg}") from error
    if not isinstance(document, dict) or set(document) != {"tasks"}:
        raise ValueError("ledger must be an object with only a tasks array")
    values = document["tasks"]
    if not isinstance(values, list) or not values:
        raise ValueError("ledger tasks must be a non-empty array")
    tasks = tuple(_parse_task(value, index) for index, value in enumerate(values))
    task_ids = {task.task_id for task in tasks}
    if len(task_ids) != len(tasks):
        raise ValueError(f"duplicate task IDs found: {tasks_path}")
    for task in tasks:
        if task.task_id in task.dependencies:
            raise ValueError(f"{task.task_id} cannot depend on itself")
    missing_dependencies = {
        dependency
        for task in tasks
        for dependency in task.dependencies
        if dependency not in task_ids
    }
    if missing_dependencies:
        raise ValueError("unknown task dependencies: " + ", ".join(sorted(missing_dependencies)))
    return tasks


def read_task_contract(tasks_path: Path, task_id: str) -> dict[str, object]:
    """Return the complete validated JSON object for one task.

    Parameters
    ----------
    tasks_path : Path
        UTF-8 ``TASKS.json`` file.
    task_id : str
        Identifier of the selected task.

    Returns
    -------
    dict[str, object]
        A copy of the selected task's JSON contract.
    """
    for task in read_ralph_tasks(tasks_path):
        if task.task_id == task_id:
            return dict(task.contract)
    raise ValueError(f"task contract not found: {task_id}")


def task_snapshot(tasks_path: Path) -> tuple[int, int, str | None]:
    """Return task counts and the next eligible task identifier.

    Parameters
    ----------
    tasks_path : Path
        UTF-8 ``TASKS.json`` file.

    Returns
    -------
    tuple[int, int, str | None]
        Incomplete count, total count, and next eligible task identifier.
    """
    tasks = read_ralph_tasks(tasks_path)
    statuses = {task.task_id: task.status for task in tasks}
    candidates = [
        task
        for task in tasks
        if task.status == "pending"
        and all(statuses[dependency] == "completed" for dependency in task.dependencies)
    ]
    selected = min(candidates, key=lambda task: (task.priority, task.task_id), default=None)
    return (
        sum(task.status != "completed" for task in tasks),
        len(tasks),
        selected.task_id if selected is not None else None,
    )


def task_progress(tasks_path: Path) -> tuple[int, int]:
    """Return incomplete and total task counts from a JSON Ralph task file.

    Parameters
    ----------
    tasks_path : Path
        UTF-8 ``TASKS.json`` file.

    Returns
    -------
    tuple[int, int]
        Number of incomplete tasks and total task count.
    """
    incomplete, total, _ = task_snapshot(tasks_path)
    return incomplete, total
