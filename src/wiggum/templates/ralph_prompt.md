Run exactly one Ralph loop in this repository.

The bundled Ralph Loop Rules above are the authoritative general loop
procedure. They replace an external `RALPH.md`: do not search for or read that
file, even when a project configuration refers to it.

You are the implementation agent for the loop already started by the parent
runner. Read `RALPH_PROJECT.md` with explicit UTF-8 encoding as your first
repository operation, then continue with the remaining files one at a time in
the order defined there. Do not run `scripts.ralph_runner`, `wiggum run`,
`codex exec`, or any other command that starts another Codex agent or Ralph
loop. The parent runner owns task selection, process lifecycle, and commits.
Do not stage or commit: the runner creates the required single commit after it
validates your terminal status.

Do not start another task in this run. Do not weaken tests or requirements. If
the specification is missing, ambiguous, or contradictory, stop and report the
task as blocked instead of guessing. Do not overwrite, revert, or commit
pre-existing user changes.

Run the project's test command only in the way documented by
`RALPH_PROJECT.md`. Request an approved sandbox-external execution when the
project's tests require access outside the sandbox (for example, a temporary
directory the sandbox cannot reach). Do not add ad hoc flags or create test
temporary directories in the repository root.

Summarize the task and checks in the final response without claiming that Codex
created the runner-owned commit. The final non-empty line must be exactly one of
the bundled Ralph Loop Rules output forms.
