# wiggum

## 日本語

wiggum は Codex CLI、GitHub Copilot CLI、Claude Code CLI に対応した、再利用できる
Ralph ループランナーです。プロジェクトの `TASKS.json` 台帳から未完了のタスクを 1 件選び、
選択した AI モデルベンダーの CLI で Ralph ループ 1 回分だけを実行し、ループの終了
ステータスを検証して変更をコミットします。台帳が完了するか、停止条件に達するまで
これを繰り返します。ベンダーの既定値はなく、`--provider` で毎回明示的に指定する
必要があります。

wiggum 自体はプロジェクトの仕様やタスクを定義しません。まず `wiggum init` で Ralph
ループ用のファイルをリポジトリに生成し、その後プロジェクトに合わせて編集してください。

- [インストール](#インストール)
- [クイックスタート](#クイックスタート)
  - [リポジトリの初期化](#リポジトリの初期化)
  - [Ralph ファイルの設定](#ralph-ファイルの設定)
- [オプション一覧](#オプション一覧)
  - [Codex 専用オプション](#codex-専用オプション)
- [プロバイダ別の注意点](#プロバイダ別の注意点)
- [Windows: pytest を sandbox 外で実行する](#windows-pytest-を-sandbox-外で実行する)

### インストール

```bash
uv add wiggum
```

```bash
uv add git+https://github.com/ribuka/wiggum.git
```

### クイックスタート

最短で動かす手順は次のとおりです。

```bash
uv run wiggum init
```

```bash
uv run wiggum run --provider codex --dry-run
uv run wiggum run --provider codex
```

#### リポジトリの初期化

`wiggum init` は対象リポジトリの `wiggum/` 配下に `config.toml`、`RALPH_PROJECT.md`、
`TASKS.json`、`PROGRESS.md` を作成します（`--repo` の既定値はカレントディレクトリです）。
Ralph の共通ルールは wiggum に同梱されています。ループを実行する前に、プロジェクトに
合わせて `wiggum/RALPH_PROJECT.md` と `wiggum/TASKS.json` を編集してください。既存の
ファイルを上書きするには `--force` を使用します。

#### Ralph ファイルの設定

`wiggum run` は必ず対象リポジトリの `wiggum/config.toml` を読みます。設定ファイルが
ない場合は preflight error で終了します。`[paths]` は必須で、対象リポジトリ内の
相対パスを指定します。設定されたタスク台帳、プロジェクト指示、進捗記録の3ファイルは
すべて必要です。`[dir]` と `[run]` は run ごとに変えない運用チューニング値で、
テーブルごと・キーごとに省略可能です（省略時は wiggum 組み込みの既定値）。
既定の設定と配置は次のとおりです。

```toml
[paths]
tasks = "wiggum/TASKS.json"
project = "wiggum/RALPH_PROJECT.md"
progress = "wiggum/PROGRESS.md"
# prompt_file は省略可能。独自プロンプトを使う場合のみコメントを外す。
# prompt_file = "wiggum/ralph_prompt.md"

[dir]
# 以下は全て省略可能。省略した場合は wiggum の組み込みデフォルトを使う。
log = "logs"
temp = "tmp"
uv_cache = ".uv-cache"

[run]
# 以下は全て省略可能。省略した場合は wiggum の組み込みデフォルトを使う。
manage_process_env = true
api_retry_count = 0
api_retry_interval_sec = 5
agent_timeout_sec = 1800

[run.executable]
codex = "codex"
copilot = "copilot"
claude = "claude"

[run.codex]
tool_output_token_limit = 12000
model_verbosity = "low"
lean = false
```

- `.git/` — リポジトリのメタデータ。`--repo` にはこの Git ルートを指定します。

対象リポジトリに `RALPH.md` は不要です。Ralph の共通ルールは wiggum が提供します。
`ralph_prompt.md` は任意であり、`[paths].prompt_file` で指定した場合のみ使用されます。
`SPEC.md` や `AGENTS.md` など、設定されたプロジェクト指示ファイルが読むよう指定するファイルは、その設定で
指定されている場合にのみ必要です。

### オプション一覧

`wiggum run` の CLI フラグは、run ごとに変えることが多い値だけです。それ以外は
すべて `wiggum/config.toml` の `[dir]`・`[run]` テーブルで設定します。

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--repo PATH` | カレントディレクトリ | 操作対象のリポジトリ。 |
| `--max-loops N` | `20` | 起動するエージェントプロセスの最大数。 |
| `--provider {codex,copilot,claude}` | 必須（既定値なし） | 使用する AI モデルベンダー。 |
| `--model NAME` | — | モデルの上書き。省略した場合は wiggum は `--model` フラグを付与せず、選択した provider CLI 自身のデフォルトモデル（CLI設定や利用アカウントの既定）がそのまま使われます。 |
| `--reasoning-effort LEVEL` | `medium` | 推論量。指定可能な値: `none`/`minimal`/`low`/`medium`/`high`/`xhigh`/`max`。プロバイダごとの対応状況は[プロバイダ別の注意点](#プロバイダ別の注意点)を参照。 |
| `--auto-approve` | — | 要否はプロバイダによって異なります。詳細は[プロバイダ別の注意点](#プロバイダ別の注意点)を参照。 |
| `--dry-run` | — | 入力を検証し、実行せずにプロバイダコマンドを1つ表示します。 |

`wiggum/config.toml` の `[paths].prompt_file`・`[dir]`・`[run]` テーブル（すべて
省略可能。既定値は `wiggum init` が生成するテンプレートを参照）:

| キー | 既定値 | 説明 |
| --- | --- | --- |
| `[paths].prompt_file` | wiggum 同梱の Ralph ループプロンプト | 各ループでエージェントに渡すプロンプト。対象リポジトリ内の相対パス。 |
| `[dir].log` / `[dir].temp` / `[dir].uv_cache` | `logs` / `tmp` / `.uv-cache` | ループログ、一時ファイル、uv キャッシュの出力先。対象リポジトリ内の相対パス。 |
| `[run].manage_process_env` | `true` | `false` にすると子プロセスに `UV_CACHE_DIR`、`TMP`、`TEMP` を設定しません。 |
| `[run].api_retry_count` | `0`（リトライ無効） | エージェント API・プロトコル失敗後の追加試行回数。 |
| `[run].api_retry_interval_sec` | `5` | リトライ間隔（秒）。 |
| `[run].agent_timeout_sec` | `1800` | 各プロバイダの子プロセスを待つ最大秒数（プロバイダ共通）。 |
| `[run.executable].codex` / `.copilot` / `.claude` | `codex` / `copilot` / `claude` | 各プロバイダの CLI 実行ファイル名またはパス。 |

#### Codex 専用オプション

以下の `[run.codex]` キーは `--provider codex` を選択した場合のみ有効です。Copilot または
Claude を選択した状態で既定値以外を指定すると検証エラーになります。

| キー | 既定値 | 説明 |
| --- | --- | --- |
| `[run.codex].model_verbosity` | `low` | Codex の出力 verbosity。 |
| `[run.codex].tool_output_token_limit` | `12000` tokens | モデル履歴に保持するツール出力の上限。 |
| `[run.codex].lean` | `false` | ユーザーの Codex 設定を読み込まず、reasoning summary を無効化します。認証情報は引き続き利用されます。 |

すべての CLI オプションと終了コードは、`uv run wiggum run --help` で確認できます。

### プロバイダ別の注意点

`--provider` に応じて、必須になるフラグ、`--reasoning-effort` の対応状況、
トークン使用量の記録方式が異なります。

必須フラグ:

| プロバイダ | `--auto-approve` | 内部で追加されるフラグ |
| --- | --- | --- |
| Codex | 不要 | — |
| Copilot | 必須 | `--allow-all-tools`（Codex の `workspace-write` サンドボックスに相当する半自動モードがないため） |
| Claude | 必須 | `--permission-mode bypassPermissions`（非対話モードでは承認プロンプトに応答できないため） |

`--reasoning-effort` の対応状況:

| プロバイダ | 対応レベル | 非対応時の挙動 |
| --- | --- | --- |
| Codex | モデルに依存 | Codex CLI 自身が検証エラーとして扱います |
| Copilot | モデルに依存 | Copilot CLI 自身が検証エラーとして扱います |
| Claude | `low`/`medium`/`high`/`xhigh`/`max` のみ | `none`/`minimal` を指定すると wiggum 自身が検証エラーとして拒否します |

トークン使用量の記録:

| プロバイダ | 記録内容 |
| --- | --- |
| Codex | `turn.completed` イベントから input・cached input・output・reasoning output を集計し、タスク累計と実行全体の累計をログに表示します。ツール出力を切り詰めたイベントが報告された場合は、その件数と設定上限も警告します。 |
| Copilot | 機械可読な token 使用量イベントを公開していないため、常に使用量 0 として記録されます。 |
| Claude | `--output-format stream-json` の最終 `result` イベントから input・cached input（プロンプトキャッシュから読み取られた分）・output の token 使用量を集計します。reasoning（thinking）token の内訳は公開されていないため、常に 0 として記録されます。 |

### Windows: pytest を sandbox 外で実行する

Windows の通常のユーザー Temp を必要とする pytest を Codex の sandbox 外で実行する
手順は [docs/windows-pytest-sandbox.md](docs/windows-pytest-sandbox.md) を参照してください。

## English

wiggum is a reusable Ralph loop runner that supports Codex CLI, GitHub
Copilot CLI, and Claude Code CLI. It selects one pending task from a project's `TASKS.json` ledger,
runs exactly one Ralph loop with the selected AI model vendor's CLI, verifies
the loop's terminal status, and commits the loop's changes, repeating until
the ledger is complete or a stopping condition is hit. There is no default
vendor; `--provider` must be passed explicitly on every run.

wiggum itself does not define your project's specification or tasks; use
`wiggum init` to scaffold the Ralph loop files into your repository, then edit
them for your project.

- [Install](#install)
- [Quick Start](#quick-start)
  - [Scaffold a repository](#scaffold-a-repository)
  - [Ralph file configuration](#ralph-file-configuration)
- [Options reference](#options-reference)
  - [Codex-only options](#codex-only-options)
- [Provider differences](#provider-differences)
- [Run only pytest outside the sandbox](#run-only-pytest-outside-the-sandbox)

### Install

```bash
uv add wiggum
```

```bash
uv add git+https://github.com/ribuka/wiggum.git
```

### Quick Start

The shortest path to a working loop:

```bash
uv run wiggum init
```

```bash
uv run wiggum run --provider codex --dry-run
uv run wiggum run --provider codex
```

#### Scaffold a repository

`wiggum init` writes `config.toml`, `RALPH_PROJECT.md`, `TASKS.json`, and `PROGRESS.md`
under `wiggum/` in the target repository (`--repo` defaults to the current
directory). The general Ralph rules are bundled with wiggum. Edit
`wiggum/RALPH_PROJECT.md` and `wiggum/TASKS.json` to match your project before
running loops. Use `--force` to overwrite files that already exist.

#### Ralph file configuration

`wiggum run` always reads `wiggum/config.toml` in the target repository. A
missing configuration is a preflight error. `[paths]` is required and every
key must name a relative path inside the target repository; the configured
task ledger, project instructions, and progress record must all exist.
`[dir]` and `[run]` hold run tunables that rarely change between runs; each
table and every key inside it are optional, falling back to wiggum's
built-in defaults when omitted. The default configuration is:

```toml
[paths]
tasks = "wiggum/TASKS.json"
project = "wiggum/RALPH_PROJECT.md"
progress = "wiggum/PROGRESS.md"
# prompt_file is optional; uncomment to use a custom prompt instead of
# wiggum's bundled default.
# prompt_file = "wiggum/ralph_prompt.md"

[dir]
# Every key below is optional; remove a key to use wiggum's built-in default.
log = "logs"
temp = "tmp"
uv_cache = ".uv-cache"

[run]
# Every key below is optional; remove a key to use wiggum's built-in default.
manage_process_env = true
api_retry_count = 0
api_retry_interval_sec = 5
agent_timeout_sec = 1800

[run.executable]
codex = "codex"
copilot = "copilot"
claude = "claude"

[run.codex]
tool_output_token_limit = 12000
model_verbosity = "low"
lean = false
```

- `.git/` — the repository metadata; `--repo` must name this Git root.

`RALPH.md` is not required in the target repository; wiggum provides the
general Ralph rules. `ralph_prompt.md` is optional and is only used when
named by `[paths].prompt_file`. Any files named by the configured project
instructions, such as `SPEC.md` or `AGENTS.md`, are required only when those
instructions say to read them.

### Options reference

`wiggum run`'s CLI flags cover only the values that tend to change from one
run to the next. Everything else lives in `wiggum/config.toml`'s `[dir]` and
`[run]` tables.

| Option | Default | Description |
| --- | --- | --- |
| `--repo PATH` | current directory | Repository to operate on. |
| `--max-loops N` | `20` | Maximum number of agent processes to start. |
| `--provider {codex,copilot,claude}` | required (no default) | AI model vendor to use. |
| `--model NAME` | — | Optional model override. When omitted, wiggum does not pass a `--model` flag at all, so the selected provider CLI's own default model (from its own configuration or the signed-in account) is used. |
| `--reasoning-effort LEVEL` | `medium` | Reasoning effort. Accepted values: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. Support varies by provider; see [Provider differences](#provider-differences). |
| `--auto-approve` | — | Whether this is required depends on the provider; see [Provider differences](#provider-differences). |
| `--dry-run` | — | Validate inputs and print one provider command without running it. |

`wiggum/config.toml`'s `[paths].prompt_file`, `[dir]`, and `[run]` tables
(every key is optional; see the defaults `wiggum init` writes above):

| Key | Default | Description |
| --- | --- | --- |
| `[paths].prompt_file` | wiggum's bundled Ralph loop prompt | Prompt passed to the agent for each loop; a relative path inside the target repository. |
| `[dir].log` / `[dir].temp` / `[dir].uv_cache` | `logs` / `tmp` / `.uv-cache` | Where wiggum writes loop logs, temporary files, and the uv cache; relative paths inside the target repository. |
| `[run].manage_process_env` | `true` | Set to `false` to leave `UV_CACHE_DIR`, `TMP`, and `TEMP` unset for the child process. |
| `[run].api_retry_count` | `0` (retries disabled) | Number of additional attempts after an agent API or protocol failure. |
| `[run].api_retry_interval_sec` | `5` | Seconds to wait between agent API retry attempts. |
| `[run].agent_timeout_sec` | `1800` | Maximum time to wait for each provider's child process (applies to every provider). |
| `[run.executable].codex` / `.copilot` / `.claude` | `codex` / `copilot` / `claude` | Vendor CLI executable name or path for each provider. |

#### Codex-only options

The following `[run.codex]` keys are only effective with `--provider codex`. Passing a
non-default value together with `--provider copilot` or `--provider claude`
is a validation error.

| Key | Default | Description |
| --- | --- | --- |
| `[run.codex].model_verbosity` | `low` | Codex output verbosity. |
| `[run.codex].tool_output_token_limit` | `12000` tokens | Maximum tool-output tokens retained in model history. |
| `[run.codex].lean` | `false` | Ignore user Codex configuration and disable reasoning summaries; saved authentication remains available. |

Run `uv run wiggum run --help` for the full CLI option list and exit codes.

### Provider differences

`--provider` changes which flags are required, how `--reasoning-effort` is
handled, and how token usage is recorded.

Required flags:

| Provider | `--auto-approve` | Flag added internally |
| --- | --- | --- |
| Codex | not required | — |
| Copilot | required | `--allow-all-tools` (no partially-unattended mode comparable to Codex's `workspace-write` sandbox) |
| Claude | required | `--permission-mode bypassPermissions` (cannot answer permission prompts in non-interactive mode) |

`--reasoning-effort` support:

| Provider | Supported levels | Behavior when unsupported |
| --- | --- | --- |
| Codex | depends on the selected model | rejected by the Codex CLI itself |
| Copilot | depends on the selected model | rejected by the Copilot CLI itself |
| Claude | `low`, `medium`, `high`, `xhigh`, `max` only | `none`/`minimal` is rejected by wiggum itself |

Token usage reporting:

| Provider | What is recorded |
| --- | --- |
| Codex | Reads the JSONL `turn.completed` event for input, cached input, output, and reasoning-output token usage, logging task and run totals. If Codex reports truncated tool-output events, wiggum also logs their count and configured limit as a warning. |
| Copilot | Does not expose a machine-readable per-turn usage event comparable to Codex's, so usage is always reported as zero. |
| Claude | Reads the final `result` event of `--output-format stream-json` for input, cached input (tokens served from the prompt cache), and output token usage. Reasoning (thinking) tokens are not broken out, so that count is always zero. |

### Run only pytest outside the sandbox

See [docs/windows-pytest-sandbox.md](docs/windows-pytest-sandbox.md) for the
steps to run pytest outside the Codex sandbox on Windows.
