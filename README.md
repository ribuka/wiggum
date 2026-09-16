# wiggum

wiggum is a reusable Ralph loop runner for the Codex CLI. It selects one
pending task from a project's `TASKS.md` ledger, runs `codex exec` for exactly
one Ralph loop, verifies the loop's terminal status, and commits the loop's
changes, repeating until the ledger is complete or a stopping condition is hit.

wiggum itself does not define your project's specification or tasks; use
`wiggum init` to scaffold the Ralph loop files into your repository, then edit
them for your project.

## Install

```bash
uv add wiggum
```

```bash
uv add git+https://github.com/ribuka/wiggum.git
```

## Scaffold a repository

```bash
uv run wiggum init
```

This writes `RALPH.md`, `RALPH_PROJECT.md`, `ralph_prompt.md`, and `TASKS.md`
into the target repository (`--repo` defaults to the current directory). Edit
`RALPH_PROJECT.md` and `TASKS.md` to match your project before running loops.
Use `--force` to overwrite files that already exist.

## Run Ralph loops

```bash
uv run wiggum run --dry-run
uv run wiggum run
```

Useful options:

- `--repo PATH` — repository to operate on (default: current directory).
- `--tasks-file PATH` — task ledger (default: `<repo>/TASKS.md`).
- `--prompt-file PATH` — prompt passed to Codex for each loop (default:
  wiggum's bundled Ralph loop prompt).
- `--logs-dir PATH` / `--temp-dir PATH` / `--uv-cache-dir PATH` — override
  where wiggum writes loop logs, temporary files, and the uv cache.
- `--no-managed-env` — do not set `UV_CACHE_DIR`, `TMP`, and `TEMP` for the
  Codex child process.
- `--max-loops N`, `--codex PATH`, `--model NAME`, `--auto-approve`,
  `--api-retry-count N`, `--api-retry-interval-sec N`, `--codex-timeout-sec N`.

Run `uv run wiggum run --help` for the full option list and exit codes.

## Development

```bash
uv run -m pytest
uv run -m ruff check .
```
