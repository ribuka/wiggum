# wiggum

## 日本語

wiggum は Codex CLI、GitHub Copilot CLI、Claude Code CLI に対応した、再利用できる
Ralph ループランナーです。プロジェクトの `TASKS.json` 台帳から未完了のタスクを 1 件選び、
選択した AI モデルベンダーの CLI で Ralph ループ 1 回分だけを実行し、ループの終了
ステータスを検証して変更をコミットします。台帳が完了するか、停止条件に達するまで
これを繰り返します。既定のベンダーは Codex CLI (`codex exec`) で、`--provider codex`
を明示指定した場合と同じ挙動です。

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

このコマンドは対象リポジトリに `RALPH_PROJECT.md`、`ralph_prompt.md`、`TASKS.json` を
作成します（`--repo` の既定値はカレントディレクトリです）。Ralph の共通ルールは
wiggum に同梱されています。ループを実行する前に、プロジェクトに合わせて
`RALPH_PROJECT.md` と `TASKS.json` を編集してください。既存のファイルを上書きするには
`--force` を使用します。

#### リポジトリルートのファイル

標準の `wiggum run` コマンドでは、対象リポジトリに次のファイルが必要です。

- `.git/` — リポジトリのメタデータ。`--repo` にはこの Git ルートを指定します。
- `TASKS.json` — `--tasks-file` で別のパスを指定しない場合のタスク台帳です。
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
- `--tasks-file PATH` — タスク台帳（既定値: `<repo>/TASKS.json`）。
- `--prompt-file PATH` — 各ループでエージェントに渡すプロンプト（既定値: wiggum 同梱の Ralph ループプロンプト）。
- `--logs-dir PATH` / `--temp-dir PATH` / `--uv-cache-dir PATH` — ループログ、一時ファイル、uv キャッシュの出力先を上書きします。
- `--no-managed-env` — 子プロセスに `UV_CACHE_DIR`、`TMP`、`TEMP` を設定しません。
- `--provider {codex,copilot,claude}` — 使用する AI モデルベンダー（既定値: `codex`）。
- `--executable PATH` — ベンダーの CLI 実行ファイル（既定値: `codex`、`copilot`、または `claude`）。`--codex PATH` は Codex 用の非推奨エイリアスとして引き続き利用できます。
- `--reasoning-effort LEVEL` — 推論量（既定値: `medium`。指定可能な値: `none`/`minimal`/`low`/`medium`/`high`/`xhigh`/`max`）。Codex と Copilot では対応レベルがプロバイダではなくモデルに依存するため、wiggum はプロバイダ単位での拒否は行わず、非対応の組み合わせは各プロバイダ CLI 自身が検証エラーとして扱います。Claude Code CLI の `--effort` フラグはモデルによらず `low`/`medium`/`high`/`xhigh`/`max` のみ受け付けるため、`claude` プロバイダで `none`/`minimal` を指定すると検証エラーになります。
- `--model-verbosity LEVEL` — Codex の出力 verbosity（既定値: `low`。Codex 専用）。
- `--tool-output-token-limit N` — モデル履歴に保持するツール出力の上限（既定値: `12000` tokens。Codex 専用）。
- `--lean` — ユーザーの Codex 設定を読み込まず、reasoning summary を無効化します。認証情報は引き続き利用されます（Codex 専用）。
- `--max-loops N`、`--model NAME`、`--auto-approve`、`--api-retry-count N`、`--api-retry-interval-sec N`、`--codex-timeout-sec N`。

`--provider copilot` または `--provider claude` を指定する場合、`--auto-approve` は
必須です。GitHub Copilot CLI には Codex の `workspace-write` サンドボックスに相当する
半自動モードがなく `--allow-all-tools` を渡して全ツールを許可する必要があり、
Claude Code CLI も同様に非対話モードでは承認プロンプトに応答できないため
`--permission-mode bypassPermissions` を渡してすべてのツール実行を許可する必要が
あります。`--reasoning-effort` は Codex と Copilot で利用できます。対応するレベルは
プロバイダではなくモデルに依存するため、wiggum は値をプロバイダ単位で拒否せず、そのまま
各プロバイダ CLI へ転送します。非対応の組み合わせは CLI 側の検証エラーになります。
Claude Code CLI は `--effort` フラグへそのまま転送されますが、モデルによらず
`low`/`medium`/`high`/`xhigh`/`max` のみ受け付けるため、`claude` 選択時に `none`
または `minimal` を指定すると wiggum 自身が検証エラーとして拒否します。また
`--model-verbosity`、`--tool-output-token-limit`、`--lean` は Codex 固有のインライン
設定であり、Copilot または Claude 選択時に既定値以外を指定すると検証エラーになります。

各 Codex 試行では JSONL の `turn.completed` イベントから input、cached input、output、
reasoning output の token 使用量を集計し、タスク累計と実行全体の累計をログに表示します。Codex
がツール出力を切り詰めたイベントを報告した場合は、その件数と設定上限も警告します。
GitHub Copilot CLI は Codex と同等の機械可読な token 使用量イベントを公開していないため、
`--provider copilot` では常に使用量が 0 として記録されます。Claude Code CLI は
`--output-format json` の最終レスポンスに input、cached input（プロンプトキャッシュから
読み取られた分）、output の token 使用量を含めて報告するため、`--provider claude` でも
これらは集計されます。ただし reasoning（thinking）token の内訳は公開されていないため、
その値は常に 0 として記録されます。

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

wiggum is a reusable Ralph loop runner that supports Codex CLI, GitHub
Copilot CLI, and Claude Code CLI. It selects one pending task from a project's `TASKS.json` ledger,
runs exactly one Ralph loop with the selected AI model vendor's CLI, verifies
the loop's terminal status, and commits the loop's changes, repeating until
the ledger is complete or a stopping condition is hit. The default vendor is
Codex CLI (`codex exec`), the same as explicitly passing `--provider codex`.

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

This writes `RALPH_PROJECT.md`, `ralph_prompt.md`, and `TASKS.json` into the
target repository (`--repo` defaults to the current directory). The general
Ralph rules are bundled with wiggum. Edit
`RALPH_PROJECT.md` and `TASKS.json` to match your project before running loops.
Use `--force` to overwrite files that already exist.

### Repository-root files

For the standard `wiggum run` command, the target repository must contain:

- `.git/` — the repository metadata; `--repo` must name this Git root.
- `TASKS.json` — the task ledger, unless `--tasks-file` selects another path.
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
- `--tasks-file PATH` — task ledger (default: `<repo>/TASKS.json`).
- `--prompt-file PATH` — prompt passed to the agent for each loop (default:
  wiggum's bundled Ralph loop prompt).
- `--logs-dir PATH` / `--temp-dir PATH` / `--uv-cache-dir PATH` — override
  where wiggum writes loop logs, temporary files, and the uv cache.
- `--no-managed-env` — do not set `UV_CACHE_DIR`, `TMP`, and `TEMP` for the
  child process.
- `--provider {codex,copilot,claude}` — AI model vendor to use (default:
  `codex`).
- `--executable PATH` — vendor CLI executable (default: `codex`, `copilot`,
  or `claude`). `--codex PATH` remains available as a deprecated alias for
  Codex.
- `--reasoning-effort LEVEL` — reasoning effort (default: `medium`; accepted
  values: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`). For
  Codex and Copilot, support for a given level depends on the selected
  model, not the provider, so wiggum does not reject a level by provider;
  each provider CLI rejects an unsupported combination itself. Claude Code
  CLI's `--effort` flag accepts only `low`, `medium`, `high`, `xhigh`, and
  `max` regardless of model, so `none` and `minimal` are a validation error
  for the `claude` provider.
- `--model-verbosity LEVEL` — Codex output verbosity (default: `low`; Codex
  only).
- `--tool-output-token-limit N` — maximum tool-output tokens retained in model
  history (default: `12000`; Codex only).
- `--lean` — ignore user Codex configuration and disable reasoning summaries;
  saved authentication remains available (Codex only).
- `--max-loops N`, `--model NAME`, `--auto-approve`, `--api-retry-count N`,
  `--api-retry-interval-sec N`, `--codex-timeout-sec N`.

`--auto-approve` is required when `--provider copilot` or `--provider claude`
is selected. GitHub Copilot CLI has no partially-unattended mode comparable
to Codex's `workspace-write` sandbox and must be told to allow every tool
with `--allow-all-tools`; Claude Code CLI likewise cannot answer permission
prompts in non-interactive mode, so wiggum passes
`--permission-mode bypassPermissions` to allow every tool. `--reasoning-effort`
is supported by Codex and Copilot. Support for a given level depends on the
selected model, not the provider, so wiggum forwards the value as-is rather
than rejecting it by provider; an unsupported combination is a validation
error from the provider CLI itself. Claude Code CLI forwards the value to its
`--effort` flag too, but that flag accepts only `low`, `medium`, `high`,
`xhigh`, and `max` regardless of model, so wiggum itself rejects `none` and
`minimal` for the `claude` provider. `--model-verbosity`,
`--tool-output-token-limit`, and `--lean` are Codex-only inline
configuration; passing a non-default value together with `--provider copilot`
or `--provider claude` is a validation error.

For every Codex attempt, wiggum reads the JSONL `turn.completed` event and logs
input, cached input, output, and reasoning-output token usage together with task
and run totals. If Codex reports truncated tool-output events, wiggum also logs
their count and configured limit as a warning. GitHub Copilot CLI does not
expose a machine-readable per-turn usage event comparable to Codex's, so
`--provider copilot` always reports all-zero usage. Claude Code CLI's
`--output-format json` final response reports input, cached input (tokens
served from the prompt cache), and output token usage, so `--provider claude`
tracks those as well; it does not break out reasoning (thinking) tokens, so
that count is always zero.

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
