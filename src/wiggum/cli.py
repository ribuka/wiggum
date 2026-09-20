"""Command-line entry point for the wiggum Ralph loop tool."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from loguru import logger

from wiggum.defaults import DEFAULT_MAX_LOOPS, DEFAULT_REASONING_EFFORT
from wiggum.exit_codes import ExitCode
from wiggum.logging.console_logging import configure_console_logging
from wiggum.providers import PROVIDERS, REASONING_EFFORTS
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
    parser.add_argument("--max-loops", type=int, default=DEFAULT_MAX_LOOPS)
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        required=True,
        help="AI model vendor used to run each Ralph loop",
    )
    parser.add_argument("--model", help="optional model override")
    parser.add_argument(
        "--reasoning-effort",
        choices=REASONING_EFFORTS,
        default=DEFAULT_REASONING_EFFORT,
        help=(
            "reasoning effort; defaults to medium. For codex and copilot, "
            "support for a given level depends on the selected model, not "
            "the provider; an unsupported combination is rejected by the "
            "provider CLI. For claude, only low/medium/high/xhigh/max are "
            "supported regardless of model; none/minimal are rejected"
        ),
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help=(
            "automatically approve requests in the workspace-write sandbox "
            "(codex), allow all tools (copilot), or bypass permission "
            "prompts (claude); required for the copilot and claude providers"
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
        max_loops=args.max_loops,
        provider=args.provider,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        auto_approve=args.auto_approve,
        dry_run=args.dry_run,
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
