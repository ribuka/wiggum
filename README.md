# wiggum

## 日本語

wiggum は Codex CLI 向けに再利用できる Ralph ループランナーです。プロジェクトの
`TASKS.md` 台帳から未完了のタスクを 1 件選び、Ralph ループ 1 回分だけ `codex exec` を
実行し、ループの終了ステータスを検証して変更をコミットします。台帳が完了するか、停止
条件に達するまでこれを繰り返します。

wiggum 自体はプロジェクトの仕様やタスクを定義しません。まず `wiggum init` で Ralph
ループ用のファイルをリポジトリに生成し、その後プロジェクトに合わせて編集してください。

### インストール

```bash
uv add wiggum
```

```bash
uv add git+https://github.com/ribuka/wiggum.git
```

### リポジトリの初期化

```bash
uv run wiggum init
```

このコマンドは対象リポジトリに `RALPH_PROJECT.md`、`ralph_prompt.md`、`TASKS.md` を
作成します（`--repo` の既定値はカレントディレクトリです）。Ralph の共通ルールは
wiggum に同梱されています。ループを実行する前に、プロジェクトに合わせて
`RALPH_PROJECT.md` と `TASKS.md` を編集してください。既存のファイルを上書きするには
`--force` を使用します。

#### リポジトリルートのファイル

標準の `wiggum run` コマンドでは、対象リポジトリに次のファイルが必要です。

- `.git/` — リポジトリのメタデータ。`--repo` にはこの Git ルートを指定します。
- `TASKS.md` — `--tasks-file` で別のパスを指定しない場合のタスク台帳です。
- `RALPH_PROJECT.md` — 検証コマンドと各ループで読むファイルを含む、リポジトリ固有の指示です。

対象リポジトリに `RALPH.md` は不要です。Ralph の共通ルールは wiggum が提供します。
`ralph_prompt.md` は任意であり、`--prompt-file` で指定した場合のみ使用されます。
`SPEC.md` や `AGENTS.md` など、`RALPH_PROJECT.md` が読むよう指定するファイルは、その設定で
指定されている場合にのみ必要です。

### Ralph ループの実行

```bash
uv run wiggum run --dry-run
uv run wiggum run
```

主なオプション:

- `--repo PATH` — 操作対象のリポジトリ（既定値: カレントディレクトリ）。
- `--tasks-file PATH` — タスク台帳（既定値: `<repo>/TASKS.md`）。
- `--prompt-file PATH` — 各ループで Codex に渡すプロンプト（既定値: wiggum 同梱の Ralph ループプロンプト）。
- `--logs-dir PATH` / `--temp-dir PATH` / `--uv-cache-dir PATH` — ループログ、一時ファイル、uv キャッシュの出力先を上書きします。
- `--no-managed-env` — Codex の子プロセスに `UV_CACHE_DIR`、`TMP`、`TEMP` を設定しません。
- `--max-loops N`、`--codex PATH`、`--model NAME`、`--auto-approve`、`--api-retry-count N`、`--api-retry-interval-sec N`、`--codex-timeout-sec N`。

すべてのオプションと終了コードは、`uv run wiggum run --help` で確認できます。

### 開発

```bash
uv run -m pytest
uv run -m ruff check .
```

## English

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

This writes `RALPH_PROJECT.md`, `ralph_prompt.md`, and `TASKS.md` into the
target repository (`--repo` defaults to the current directory). The general
Ralph rules are bundled with wiggum. Edit
`RALPH_PROJECT.md` and `TASKS.md` to match your project before running loops.
Use `--force` to overwrite files that already exist.

### Repository-root files

For the standard `wiggum run` command, the target repository must contain:

- `.git/` — the repository metadata; `--repo` must name this Git root.
- `TASKS.md` — the task ledger, unless `--tasks-file` selects another path.
- `RALPH_PROJECT.md` — repository-specific instructions, including validation
  commands and the files each loop must read.

`RALPH.md` is not required in the target repository; wiggum provides the
general Ralph rules. `ralph_prompt.md` is optional and is only used when passed
with `--prompt-file`. Any files named by `RALPH_PROJECT.md`, such as `SPEC.md`
or `AGENTS.md`, are required only when that configuration says to read them.

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
