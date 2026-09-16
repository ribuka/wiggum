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
- `--reasoning-effort LEVEL` — Codex の推論量（既定値: `medium`）。
- `--model-verbosity LEVEL` — Codex の出力 verbosity（既定値: `low`）。
- `--tool-output-token-limit N` — モデル履歴に保持するツール出力の上限（既定値: `12000` tokens）。
- `--lean` — ユーザーの Codex 設定を読み込まず、reasoning summary を無効化します。認証情報は引き続き利用されます。
- `--max-loops N`、`--codex PATH`、`--model NAME`、`--auto-approve`、`--api-retry-count N`、`--api-retry-interval-sec N`、`--codex-timeout-sec N`。

各 Codex 試行では JSONL の `turn.completed` イベントから input、cached input、output、
reasoning output の token 使用量を集計し、タスク累計と実行全体の累計をログに表示します。Codex
がツール出力を切り詰めたイベントを報告した場合は、その件数と設定上限も警告します。

すべてのオプションと終了コードは、`uv run wiggum run --help` で確認できます。

### pytest だけを sandbox 外で実行する

Windows の通常のユーザー Temp を必要とする pytest を実行する場合でも、
`--auto-approve` は不要です。Codex の command rule で `uv run -m pytest` だけを
sandbox 外で許可し、wiggum には `--no-managed-env` を指定してください。後者は
Codex 子プロセスの `TMP`、`TEMP`、`UV_CACHE_DIR` を変更しないため、pytest は親プロセスの
通常の Temp 設定を継承します。

`%USERPROFILE%\\.codex\\rules\\pytest.rules` に次を作成します。

```starlark
prefix_rule(
    pattern = ["uv", "run", "-m", "pytest"],
    decision = "allow",
    justification = "Run required pytest outside the Codex sandbox using the normal Windows user Temp.",
)
```

プロジェクト固有の rule を使う場合は `<repo>/.codex/rules/pytest.rules` に置けますが、
Codex がそのプロジェクトの `.codex` 設定を trusted として読み込む必要があります。ユーザー
階層の rule は複数のリポジトリに適用されるため、必要最小限の prefix にしてください。

プロジェクトの pytest 指示では、昇格要求ではなく `uv run -m pytest` を直接実行するよう
明記してください。rule が拒否された場合は sandbox 内実行や Temp の変更で回避せず、検証を
blocked として報告します。PowerShell では次で rule の一致を確認できます。

```powershell
codex execpolicy check --pretty --rules "$env:USERPROFILE\.codex\rules\pytest.rules" -- uv run -m pytest
uv run wiggum run --no-managed-env
```

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
- `--reasoning-effort LEVEL` — Codex reasoning effort (default: `medium`).
- `--model-verbosity LEVEL` — Codex output verbosity (default: `low`).
- `--tool-output-token-limit N` — maximum tool-output tokens retained in model
  history (default: `12000`).
- `--lean` — ignore user Codex configuration and disable reasoning summaries;
  saved authentication remains available.
- `--max-loops N`, `--codex PATH`, `--model NAME`, `--auto-approve`,
  `--api-retry-count N`, `--api-retry-interval-sec N`, `--codex-timeout-sec N`.

For every Codex attempt, wiggum reads the JSONL `turn.completed` event and logs
input, cached input, output, and reasoning-output token usage together with task
and run totals. If Codex reports truncated tool-output events, wiggum also logs
their count and configured limit as a warning.

Run `uv run wiggum run --help` for the full option list and exit codes.

### Run only pytest outside the sandbox

When pytest requires the normal Windows user Temp directory, you do not need
`--auto-approve`. Use a Codex command rule to allow only `uv run -m pytest`
outside the sandbox, and pass `--no-managed-env` to wiggum. The latter leaves
`TMP`, `TEMP`, and `UV_CACHE_DIR` unchanged for the Codex child process, so
pytest inherits the parent's normal Temp configuration.

Create `%USERPROFILE%\\.codex\\rules\\pytest.rules` with:

```starlark
prefix_rule(
    pattern = ["uv", "run", "-m", "pytest"],
    decision = "allow",
    justification = "Run required pytest outside the Codex sandbox using the normal Windows user Temp.",
)
```

For a repository-specific rule, use `<repo>/.codex/rules/pytest.rules`; Codex
must trust that project's `.codex` configuration before it loads the rule.
User-level rules apply to multiple repositories, so keep their command prefixes
as narrow as possible.

Project pytest instructions must tell Codex to run `uv run -m pytest` directly,
not request escalation. If the rule denies the command, report verification as
blocked rather than running pytest in the sandbox or changing the temporary
directory. In PowerShell, verify the rule match and run wiggum with:

```powershell
codex execpolicy check --pretty --rules "$env:USERPROFILE\.codex\rules\pytest.rules" -- uv run -m pytest
uv run wiggum run --no-managed-env
```

## Development

```bash
uv run -m pytest
uv run -m ruff check .
```
