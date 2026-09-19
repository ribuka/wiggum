"""Ralph loop prompt resolution: default prompt text and task-scoped prompts."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path

from wiggum.config import RalphPaths


def default_prompt_text(paths: RalphPaths, repo: Path) -> str:
    """Return wiggum's bundled Ralph rules and loop prompt.

    paths : RalphPaths
        Resolved Ralph file paths.
    repo : Path
        Resolved repository root used to display relative paths.

    Returns
    -------
    str
        UTF-8 text of the packaged general rules followed by the loop prompt.
    """
    templates_root = resources.files("wiggum") / "templates"
    general_rules = (templates_root / "RALPH.md").read_text(encoding="utf-8")
    loop_prompt = (templates_root / "ralph_prompt.md").read_text(encoding="utf-8")
    return f"{general_rules.rstrip()}\n\n{_render_paths(loop_prompt, paths, repo)}"


def prompt_for_selected_task(
    prompt: str,
    selected_task_id: str,
    selected_task_contract: dict[str, object],
    paths: RalphPaths,
    repo: Path,
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
    paths : RalphPaths
        Resolved Ralph file paths.
    repo : Path
        Resolved repository root used to display relative paths.

    Returns
    -------
    str
        Prompt that names the only task the Codex child may process.
    """
    project_path, tasks_path, progress_path = _display_paths(paths, repo)
    return (
        f"{prompt.rstrip()}\n\n"
        "## Configured Ralph files\n\n"
        f"Read `{project_path}` first. Use `{tasks_path}` only to update the selected "
        f"task's status. Append the loop record to `{progress_path}`.\n\n"
        "## Runner-selected task\n\n"
        f"The parent runner selected `{selected_task_id}` for this loop. The complete "
        "task contract is below. Work only on it; do not select or start another task. "
        f"Do not read `{tasks_path}` to select a task or discover requirements; read it only "
        "when updating this task's status. If the ledger conflicts with this contract, "
        f"preserve existing changes and report `TASK_BLOCKED: {selected_task_id}`.\n\n"
        f"```json\n{json.dumps(selected_task_contract, ensure_ascii=False, indent=2)}\n```\n"
    )


def _render_paths(template: str, paths: RalphPaths, repo: Path) -> str:
    """Replace Ralph-path placeholders in a bundled template.

    Parameters
    ----------
    template : str
        Bundled template text.
    paths : RalphPaths
        Resolved Ralph file paths.
    repo : Path
        Resolved repository root used to display relative paths.

    Returns
    -------
    str
        Template with all Ralph path placeholders replaced.
    """
    project_path, tasks_path, progress_path = _display_paths(paths, repo)
    return (
        template.replace("{{project_path}}", project_path)
        .replace("{{tasks_path}}", tasks_path)
        .replace("{{progress_path}}", progress_path)
    )


def _display_paths(paths: RalphPaths, repo: Path) -> tuple[str, str, str]:
    """Return configured paths as repository-relative POSIX strings.

    Parameters
    ----------
    paths : RalphPaths
        Resolved Ralph file paths.
    repo : Path
        Resolved repository root.

    Returns
    -------
    tuple[str, str, str]
        Project instruction, task ledger, and progress record paths.
    """
    return tuple(path.relative_to(repo).as_posix() for path in (paths.project, paths.tasks, paths.progress))
