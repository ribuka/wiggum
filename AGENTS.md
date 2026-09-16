# instructions

- A repository for developing ralph-loop.

## Python

- Always use `uv run -m`. NEVER use `python -m`, `Set-Lacation` or one-liners and here-string in pwsh.

### Verification commands

- Run targeted tests while implementing a task.
- Run the full test suite and lint before marking the task as completed.

#### Test execution

- Use `uv run -m pytest` for full test suite.
- Use `uv run -m pytest <test-path>` for targeted test.
- ALWAYS run pytest outside the Codex sandbox from the first attempt.
- NEVER first attempt pytest inside the sandbox.
  - This is required because pytest temporary directories under the Windows user Temp directory may be inaccessible from the Codex sandbox.

#### Lint

- Lint: `uv run -m ruff check .`

### Architecture and maintainability

- Keep one primary responsibility per Python module.
- NEVER append a distinct responsibility to an existing module; create a focused
  module or package instead.
- Split independently testable stages such as input, validation, preprocessing,
  transformation, and orchestration into cohesive modules when appropriate.
- Keep public API modules and `__init__.py` files thin, explicitly re-export
  public symbols, and preserve documented import paths during refactoring.
- NEVER introduce circular imports or generic catch-all modules such as `utils.py`.
- Organize tests by responsibility and share setup through narrowly scoped pytest
  fixtures. NEVER split modules based on line count alone.

## Temporary files

- Create all temporary scripts and investigation files under `tmp/` at the repository root.
- NEVER create temporary files elsewhere; delete them when the task is complete.
- Store the persistent uv dependency cache in the ignored repository-root `.uv-cache/` directory.

## Rules
- Respond in Japanese
- Include probabilities when providing answers with uncertainty
- Start tasks with Plan mode when more than 3 steps required
- NEVER write code without reading it
- Make changes only where necessary, minimize impact
- Add docstrings for all functions and classes with NumPy style
- Add type hints for all function parameters and return types
