"""Parsing and selection logic for the Ralph task ledger (``TASKS.md``)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TASK_SECTION_PATTERN = re.compile(
    r"^## (?P<task_id>TASK-\d{3}):.*?$"
    r"(?P<body>.*?)(?=^## TASK-\d{3}:|\Z)",
    re.MULTILINE | re.DOTALL,
)
TASK_ID_PATTERN = re.compile(r"TASK-\d{3}")
TASK_STATUS_FIELD_PATTERN = re.compile(r"^- Status: (?P<value>\w+)$", re.MULTILINE)
TASK_PRIORITY_FIELD_PATTERN = re.compile(r"^- Priority: (?P<value>\d+)$", re.MULTILINE)
TASK_DEPENDENCIES_FIELD_PATTERN = re.compile(
    r"^- Depends on: (?P<value>[^\r\n]+)$",
    re.MULTILINE,
)
TASK_STATUSES = frozenset({"pending", "completed", "blocked"})


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
    """

    task_id: str
    status: str
    priority: int
    dependencies: tuple[str, ...]


def _require_task_field(pattern: re.Pattern[str], body: str, field: str, task_id: str) -> str:
    """Return one required task field from a task section.

    Parameters
    ----------
    pattern : re.Pattern[str]
        Compiled pattern containing a named ``value`` group.
    body : str
        Markdown content belonging to one task.
    field : str
        Human-readable field name for an error message.
    task_id : str
        Identifier of the task being parsed.

    Returns
    -------
    str
        Parsed field value.

    Raises
    ------
    ValueError
        If the required field is absent.
    """
    match = pattern.search(body)
    if match is None:
        raise ValueError(f"{task_id} has no {field} field")
    return match.group("value")


def read_ralph_tasks(tasks_path: Path) -> tuple[RalphTask, ...]:
    """Read task metadata used by the Ralph runner.

    Parameters
    ----------
    tasks_path : Path
        UTF-8 task definition file containing task headings and status fields.

    Returns
    -------
    tuple[RalphTask, ...]
        Parsed task metadata in ledger order.

    Raises
    ------
    ValueError
        If task metadata is missing, duplicated, or invalid.
    """
    text = tasks_path.read_text(encoding="utf-8")
    tasks: list[RalphTask] = []
    for section in TASK_SECTION_PATTERN.finditer(text):
        task_id = section.group("task_id")
        body = section.group("body")
        status = _require_task_field(TASK_STATUS_FIELD_PATTERN, body, "Status", task_id)
        if status not in TASK_STATUSES:
            raise ValueError(f"{task_id} has invalid status: {status}")
        priority = int(
            _require_task_field(TASK_PRIORITY_FIELD_PATTERN, body, "Priority", task_id)
        )
        dependency_field = _require_task_field(
            TASK_DEPENDENCIES_FIELD_PATTERN,
            body,
            "Depends on",
            task_id,
        )
        dependencies = (
            ()
            if dependency_field == "none"
            else tuple(value.strip() for value in dependency_field.split(","))
        )
        if any(TASK_ID_PATTERN.fullmatch(value) is None for value in dependencies):
            raise ValueError(f"{task_id} has invalid dependencies: {dependency_field}")
        tasks.append(RalphTask(task_id, status, priority, dependencies))

    if not tasks:
        raise ValueError(f"no tasks found: {tasks_path}")
    task_ids = {task.task_id for task in tasks}
    if len(task_ids) != len(tasks):
        raise ValueError(f"duplicate task IDs found: {tasks_path}")
    missing_dependencies = {
        dependency
        for task in tasks
        for dependency in task.dependencies
        if dependency not in task_ids
    }
    if missing_dependencies:
        missing = ", ".join(sorted(missing_dependencies))
        raise ValueError(f"unknown task dependencies: {missing}")
    return tuple(tasks)


def task_snapshot(tasks_path: Path) -> tuple[int, int, str | None]:
    """Return task counts and the next eligible task identifier.

    Parameters
    ----------
    tasks_path : Path
        UTF-8 Ralph task ledger.

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
    """Return incomplete and total task counts from a Ralph task file.

    Parameters
    ----------
    tasks_path : Path
        UTF-8 Ralph task ledger.

    Returns
    -------
    tuple[int, int]
        Number of incomplete tasks and total task count.
    """
    incomplete, total, _ = task_snapshot(tasks_path)
    return incomplete, total
