"""Tests for shared child-process environment construction."""

from __future__ import annotations

from pathlib import Path

from wiggum.process_environment import build_process_environment


def test_build_process_environment_sets_isolated_paths_by_default(tmp_path: Path) -> None:
    """Inject UV_CACHE_DIR, TMP, and TEMP when process env management is enabled."""
    temp_dir = tmp_path / "tmp"
    uv_cache_dir = tmp_path / ".uv-cache"

    environment = build_process_environment(temp_dir, uv_cache_dir=uv_cache_dir)

    assert environment["UV_CACHE_DIR"] == str(uv_cache_dir.resolve())
    assert environment["TMP"] == environment["TEMP"]
    assert Path(environment["TMP"]).is_dir()
    assert Path(environment["TMP"]).is_relative_to((temp_dir / "runtime").resolve())
    assert uv_cache_dir.is_dir()


def test_build_process_environment_is_a_no_op_when_disabled(tmp_path: Path) -> None:
    """Leave the environment untouched when process env management is disabled."""
    temp_dir = tmp_path / "tmp"
    uv_cache_dir = tmp_path / ".uv-cache"

    environment = build_process_environment(
        temp_dir,
        uv_cache_dir=uv_cache_dir,
        manage_process_env=False,
    )

    assert not uv_cache_dir.exists()
    assert not (temp_dir / "runtime").exists()
    assert environment.get("UV_CACHE_DIR") is None
