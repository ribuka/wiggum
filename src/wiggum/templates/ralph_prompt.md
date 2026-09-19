Run one Ralph loop. The bundled rules replace any external `RALPH.md`.

Read `{{project_path}}` first, then only repository files required by the
provided task contract. Do not start another agent or loop, stage, commit,
overwrite, or revert pre-existing changes; the parent runner owns those actions.
Follow the project's documented test procedure. If requirements conflict or are
ambiguous, report the selected task as blocked rather than guessing.
