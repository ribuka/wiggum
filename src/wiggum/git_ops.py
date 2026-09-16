"""Git helpers used to validate and commit changes from one Ralph loop."""

from __future__ import annotations

import subprocess
from pathlib import Path


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a Git command and capture its text output.

    Parameters
    ----------
    repo : Path
        Repository working directory.
    *args : str
        Arguments passed to Git.

    Returns
    -------
    subprocess.CompletedProcess[str]
        Completed Git process.
    """
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )


def require_git_output(repo: Path, *args: str) -> str:
    """Return stripped Git output or raise a runtime error.

    Parameters
    ----------
    repo : Path
        Repository working directory.
    *args : str
        Arguments passed to Git.

    Returns
    -------
    str
        Stripped standard output.

    Raises
    ------
    RuntimeError
        If Git exits unsuccessfully.
    """
    result = run_git(repo, *args)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(detail or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def require_clean_worktree(repo: Path) -> None:
    """Raise when the repository contains tracked or untracked changes.

    Parameters
    ----------
    repo : Path
        Repository working directory.

    Raises
    ------
    RuntimeError
        If the working tree is not clean.
    """
    status = require_git_output(repo, "status", "--porcelain", "--untracked-files=all")
    if status:
        raise RuntimeError("working tree is not clean:\n" + status)


def commit_count(repo: Path, before: str, after: str) -> int:
    """Count commits added between two repository states.

    Parameters
    ----------
    repo : Path
        Repository working directory.
    before : str
        Commit hash before the loop.
    after : str
        Commit hash after the loop.

    Returns
    -------
    int
        Number of commits reachable from ``after`` but not ``before``.

    Raises
    ------
    RuntimeError
        If history was rewritten or Git cannot inspect the range.
    """
    ancestor = run_git(repo, "merge-base", "--is-ancestor", before, after)
    if ancestor.returncode != 0:
        raise RuntimeError("the loop rewrote or replaced repository history")
    return int(require_git_output(repo, "rev-list", "--count", f"{before}..{after}"))


def commit_loop_changes(repo: Path, task_id: str, status: str) -> None:
    """Commit all changes produced by one clean-start Ralph loop.

    Parameters
    ----------
    repo : Path
        Repository working directory, verified clean before the loop started.
    task_id : str
        Ralph task identifier reported for the loop.
    status : str
        Terminal Ralph status, either ``completed``, ``incompleted``, or
        ``blocked``.

    Raises
    ------
    RuntimeError
        If the working tree contains no changes or Git cannot stage or commit
        the loop changes.
    ValueError
        If ``status`` is not a task terminal status.
    """
    subjects = {
        "completed": f"feat({task_id}): Ralph loop changes",
        "incompleted": f"wip({task_id}): Ralph loop changes",
        "blocked": f"wip({task_id}): Ralph loop changes",
    }
    try:
        subject = subjects[status]
    except KeyError as error:
        raise ValueError(f"cannot commit loop status: {status}") from error

    require_git_output(repo, "diff", "--check")
    require_git_output(repo, "add", "--all")
    staged = run_git(repo, "diff", "--cached", "--quiet")
    if staged.returncode == 0:
        raise RuntimeError("task loop produced no changes to commit")
    if staged.returncode != 1:
        detail = staged.stderr.strip() or staged.stdout.strip()
        raise RuntimeError(detail or "could not inspect staged changes")
    require_git_output(repo, "diff", "--cached", "--check")
    require_git_output(repo, "commit", "-m", subject)
