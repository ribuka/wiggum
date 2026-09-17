"""Command-line entry point for the wiggum Ralph loop tool."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from loguru import logger

from wiggum.console_logging import configure_console_logging
from wiggum.defaults import (
    DEFAULT_API_RETRY_COUNT,
    DEFAULT_API_RETRY_INTERVAL_SEC,
    DEFAULT_CODEX_TIMEOUT_SEC,
    DEFAULT_MAX_LOOPS,
    DEFAULT_MODEL_VERBOSITY,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT,
    MODEL_VERBOSITIES,
)
from wiggum.exit_codes import ExitCode
from wiggum.providers import DEFAULT_PROVIDER, PROVIDERS, REASONING_EFFORTS
from wiggum.runner import run
from wiggum.scaffold import scaffold


def _add_run_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments accepted by the ``run`` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser receiving the ``run`` arguments.
    """
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--tasks-file",
        type=Path,
        default=None,
        help="Ralph task ledger; defaults to <repo>/TASKS.md",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=None,
        help="defaults to wiggum's bundled Ralph loop prompt",
    )
    parser.add_argument(
        "--logs-dir",
        type=Path,
        default=None,
        help="defaults to <repo>/logs",
    )
    parser.add_argument(
        "--temp-dir",
        type=Path,
        default=None,
        help="defaults to <repo>/tmp",
    )
    parser.add_argument(
        "--uv-cache-dir",
        type=Path,
        default=None,
        help="defaults to <repo>/.uv-cache",
    )
    parser.add_argument(
        "--no-managed-env",
        action="store_true",
        help="do not set UV_CACHE_DIR, TMP, and TEMP for the Codex child process",
    )
    parser.add_argument("--max-loops", type=int, default=DEFAULT_MAX_LOOPS)
    parser.add_argument("--api-retry-count", type=int, default=DEFAULT_API_RETRY_COUNT)
    parser.add_argument(
        "--api-retry-interval-sec",
        type=int,
        default=DEFAULT_API_RETRY_INTERVAL_SEC,
    )
    parser.add_argument(
        "--codex-timeout-sec",
        type=int,
        default=DEFAULT_CODEX_TIMEOUT_SEC,
        help="maximum seconds to wait for each provider child process",
    )
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        default=DEFAULT_PROVIDER,
        help="AI model vendor used to run each Ralph loop; defaults to codex",
    )
    parser.add_argument(
        "--executable",
        default=None,
        help=(
            "provider CLI executable name or path; defaults to codex or copilot "
            "depending on --provider"
        ),
    )
    parser.add_argument(
        "--codex",
        default=None,
        help="[deprecated alias for --executable] Codex executable name or path",
    )
    parser.add_argument("--model", help="optional model override")
    parser.add_argument(
        "--reasoning-effort",
        choices=REASONING_EFFORTS,
        default=DEFAULT_REASONING_EFFORT,
        help=(
            "reasoning effort; defaults to medium. Support for a given "
            "level depends on the selected model, not the provider; an "
            "unsupported combination is rejected by the provider CLI"
        ),
    )
    parser.add_argument(
        "--model-verbosity",
        choices=MODEL_VERBOSITIES,
        default=DEFAULT_MODEL_VERBOSITY,
        help="Codex model verbosity; defaults to low (codex provider only)",
    )
    parser.add_argument(
        "--tool-output-token-limit",
        type=int,
        default=DEFAULT_TOOL_OUTPUT_TOKEN_LIMIT,
        help=(
            "maximum tokens retained from each tool output; defaults to 6000 "
            "(codex provider only)"
        ),
    )
    parser.add_argument(
        "--lean",
        action="store_true",
        help=(
            "ignore user Codex config and disable reasoning summaries "
            "(codex provider only)"
        ),
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help=(
            "automatically approve requests in the workspace-write sandbox "
            "(codex), or allow all tools (copilot); required for the copilot "
            "provider"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate inputs and print one provider command without running it",
    )


def _add_init_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments accepted by the ``init`` subcommand.

    Parameters
    ----------
    parser : argparse.ArgumentParser
        Subparser receiving the ``init`` arguments.
    """
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing Ralph loop files",
    )


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Parameters
    ----------
    argv : Sequence[str] | None, default None
        Optional argument sequence. Defaults to ``sys.argv``.

    Returns
    -------
    argparse.Namespace
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        prog="wiggum",
        description=(
            "Run Ralph loop tasks with Codex CLI or GitHub Copilot CLI, or "
            "scaffold Ralph loop files into a repository."
        ),
        epilog=(
            "run exit codes: 0=all complete/dry run, 10=agent failure, "
            "11=protocol error, 12=Git state error, 20=task incomplete, "
            "21=task blocked, 22=max loops, 23=preflight error."
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="run Ralph loops until a terminal status is reached",
    )
    _add_run_arguments(run_parser)

    init_parser = subparsers.add_parser(
        "init",
        help="scaffold Ralph loop template files into a repository",
    )
    _add_init_arguments(init_parser)

    return parser.parse_args(argv)


def _run_command(args: argparse.Namespace) -> ExitCode:
    """Execute the ``run`` subcommand.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed ``run`` arguments.

    Returns
    -------
    ExitCode
        Runner outcome.
    """
    return run(
        repo=args.repo,
        prompt_path=args.prompt_file,
        max_loops=args.max_loops,
        provider=args.provider,
        codex_executable=args.codex if args.codex is not None else "codex",
        executable=args.executable,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        model_verbosity=args.model_verbosity,
        tool_output_token_limit=args.tool_output_token_limit,
        lean=args.lean,
        auto_approve=args.auto_approve,
        dry_run=args.dry_run,
        api_retry_count=args.api_retry_count,
        api_retry_interval_sec=args.api_retry_interval_sec,
        codex_timeout_sec=args.codex_timeout_sec,
        tasks_path=args.tasks_file,
        logs_dir=args.logs_dir,
        temp_dir=args.temp_dir,
        uv_cache_dir=args.uv_cache_dir,
        manage_process_env=not args.no_managed_env,
    )


def _init_command(args: argparse.Namespace) -> ExitCode:
    """Execute the ``init`` subcommand.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed ``init`` arguments.

    Returns
    -------
    ExitCode
        ``SUCCESS`` on completion, ``PREFLIGHT_ERROR`` if scaffolding failed.
    """
    try:
        written = scaffold(args.repo, force=args.force)
    except FileExistsError as error:
        logger.error("{}", error)
        return ExitCode.PREFLIGHT_ERROR
    for path in written:
        logger.success("Wrote {}", path)
    return ExitCode.SUCCESS


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command-line entry point.

    Parameters
    ----------
    argv : Sequence[str] | None, default None
        Optional argument sequence. Defaults to ``sys.argv``.

    Returns
    -------
    int
        Process exit code.
    """
    args = _parse_args(argv)
    configure_console_logging()
    if args.command == "run":
        return int(_run_command(args))
    if args.command == "init":
        return int(_init_command(args))
    raise AssertionError(f"unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
