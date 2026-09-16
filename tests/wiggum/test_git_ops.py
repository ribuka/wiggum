"""Tests for Git helpers used to validate and commit Ralph loop changes."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from wiggum.git_ops import (
    commit_count,
    commit_loop_changes,
    require_clean_worktree,
    require_git_output,
)


def _init_repo(repo: Path) -> None:
    """Initialize a Git repository with a committed placeholder file.

    Parameters
    ----------
    repo : Path
        Directory that becomes the repository root.
    """
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    (repo / "README.md").write_text("placeholder\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit", "--quiet"], cwd=repo, check=True)


def test_require_clean_worktree_accepts_a_clean_repository(tmp_path: Path) -> None:
    """Accept a repository with no tracked or untracked changes."""
    _init_repo(tmp_path)

    require_clean_worktree(tmp_path)


def test_require_clean_worktree_rejects_untracked_files(tmp_path: Path) -> None:
    """Reject a repository containing an untracked file."""
    _init_repo(tmp_path)
    (tmp_path / "untracked.txt").write_text("data\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="working tree is not clean"):
        require_clean_worktree(tmp_path)


def test_commit_loop_changes_commits_staged_and_untracked_files(tmp_path: Path) -> None:
    """Commit every loop change with a completed-status subject."""
    _init_repo(tmp_path)
    before = require_git_output(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "feature.py").write_text("value = 1\n", encoding="utf-8")

    commit_loop_changes(tmp_path, "TASK-001", "completed")

    after = require_git_output(tmp_path, "rev-parse", "HEAD")
    assert commit_count(tmp_path, before, after) == 1
    subject = require_git_output(tmp_path, "log", "-1", "--format=%s")
    assert subject == "feat(TASK-001): Ralph loop changes"
    require_clean_worktree(tmp_path)


def test_commit_loop_changes_uses_wip_subject_for_incomplete_and_blocked(tmp_path: Path) -> None:
    """Use a wip subject for incomplete and blocked loop results."""
    _init_repo(tmp_path)
    (tmp_path / "feature.py").write_text("value = 1\n", encoding="utf-8")

    commit_loop_changes(tmp_path, "TASK-002", "blocked")

    subject = require_git_output(tmp_path, "log", "-1", "--format=%s")
    assert subject == "wip(TASK-002): Ralph loop changes"


def test_commit_loop_changes_raises_for_unknown_status(tmp_path: Path) -> None:
    """Reject a status outside the known Ralph terminal statuses."""
    _init_repo(tmp_path)
    (tmp_path / "feature.py").write_text("value = 1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="cannot commit loop status: unknown"):
        commit_loop_changes(tmp_path, "TASK-003", "unknown")


def test_commit_loop_changes_raises_when_there_is_nothing_to_commit(tmp_path: Path) -> None:
    """Reject committing a loop that produced no repository changes."""
    _init_repo(tmp_path)

    with pytest.raises(RuntimeError, match="produced no changes to commit"):
        commit_loop_changes(tmp_path, "TASK-004", "completed")


def test_commit_count_counts_commits_between_two_revisions(tmp_path: Path) -> None:
    """Count exactly the commits reachable from after but not before."""
    _init_repo(tmp_path)
    before = require_git_output(tmp_path, "rev-parse", "HEAD")
    (tmp_path / "a.txt").write_text("a\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "a", "--quiet"], cwd=tmp_path, check=True)
    (tmp_path / "b.txt").write_text("b\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "b", "--quiet"], cwd=tmp_path, check=True)
    after = require_git_output(tmp_path, "rev-parse", "HEAD")

    assert commit_count(tmp_path, before, after) == 2
    assert commit_count(tmp_path, before, before) == 0
