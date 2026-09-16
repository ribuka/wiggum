# Ralph Loop Rules

The runner selects exactly one task. Complete only that task, then end the
loop. Project instructions may add constraints but never weaken these rules.

1. Read the provided task contract and only the files needed to implement it.
2. Add or update focused tests, make the smallest correct change, and run the
   required task and project checks.
3. Verify the requirements, review this loop's diff, and update the selected
   task and project progress state.
4. Never weaken requirements or tests, change unrelated behavior, add tasks, or
   leave debug/generated artifacts.

Mark a task completed only when requirements, relevant tests, required checks,
and architecture constraints pass. Report incomplete when work remains without
an external decision; report blocked when human input or an unavailable external
dependency is required. Preserve existing changes in either case.

Keep the final response to four short lines: task, changes, checks, and notes.
Its last non-empty line must be exactly `TASK_COMPLETED: TASK-XXX`,
`TASK_INCOMPLETE: TASK-XXX`, or `TASK_BLOCKED: TASK-XXX`, matching repository
state.
