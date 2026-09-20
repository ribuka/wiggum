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
uv run wiggum run --dry-run
uv run wiggum run
```

#### リポジトリの初期化

`wiggum init` は対象リポジトリの `wiggum/` 配下に `config.toml`、`RALPH_PROJECT.md`、
`TASKS.json`、`PROGRESS.md` を作成します（`--repo` の既定値はカレントディレクトリです）。
Ralph の共通ルールは wiggum に同梱されています。ループを実行する前に、プロジェクトに
合わせて `wiggum/RALPH_PROJECT.md` と `wiggum/TASKS.json` を編集してください。既存の
ファイルを上書きするには `--force` を使用します。

#### Ralph ファイルの設定

`wiggum run` は必ず対象リポジトリの `wiggum/config.toml` を読みます。設定ファイルが
ない場合は preflight error で終了します。既定の設定と配置は次のとおりです。

```toml
[paths]
tasks = "wiggum/TASKS.json"
project = "wiggum/RALPH_PROJECT.md"
progress = "wiggum/PROGRESS.md"
```

`[paths]` の全項目は必須で、対象リポジトリ内の相対パスを指定します。設定された
タスク台帳、プロジェクト指示、進捗記録の3ファイルはすべて必要です。

- `.git/` — リポジトリのメタデータ。`--repo` にはこの Git ルートを指定します。

対象リポジトリに `RALPH.md` は不要です。Ralph の共通ルールは wiggum が提供します。
`ralph_prompt.md` は任意であり、`--prompt-file` で指定した場合のみ使用されます。
`SPEC.md` や `AGENTS.md` など、設定されたプロジェクト指示ファイルが読むよう指定するファイルは、その設定で
指定されている場合にのみ必要です。

### オプション一覧

基本オプション（プロバイダ共通）:

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--repo PATH` | カレントディレクトリ | 操作対象のリポジトリ。 |
| `--prompt-file PATH` | wiggum 同梱の Ralph ループプロンプト | 各ループでエージェントに渡すプロンプト。 |
| `--logs-dir PATH` / `--temp-dir PATH` / `--uv-cache-dir PATH` | — | ループログ、一時ファイル、uv キャッシュの出力先を上書きします。 |
| `--no-managed-env` | — | 子プロセスに `UV_CACHE_DIR`、`TMP`、`TEMP` を設定しません。 |
| `--max-loops N` | — | — |
| `--model NAME` | — | — |
| `--auto-approve` | — | 要否はプロバイダによって異なります。詳細は[プロバイダ別の注意点](#プロバイダ別の注意点)を参照。 |
| `--api-retry-count N` | — | — |
| `--api-retry-interval-sec N` | — | — |
| `--codex-timeout-sec N` | — | 名前に反してプロバイダ共通です。各プロバイダの子プロセスを待つ最大秒数。 |

プロバイダ選択:

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--provider {codex,copilot,claude}` | `codex` | 使用する AI モデルベンダー。 |
| `--executable PATH` | `codex`、`copilot`、または `claude`（選択したプロバイダに対応するもの） | ベンダーの CLI 実行ファイル。`--codex PATH` は Codex 用の非推奨エイリアスとして引き続き利用できます。 |

推論量:

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--reasoning-effort LEVEL` | `medium` | 推論量。指定可能な値: `none`/`minimal`/`low`/`medium`/`high`/`xhigh`/`max`。プロバイダごとの対応状況は[プロバイダ別の注意点](#プロバイダ別の注意点)を参照。 |

#### Codex 専用オプション

以下のオプションは `--provider codex` を選択した場合のみ有効です。Copilot または
Claude を選択した状態で既定値以外を指定すると検証エラーになります。

| オプション | 既定値 | 説明 |
| --- | --- | --- |
| `--model-verbosity LEVEL` | `low` | Codex の出力 verbosity。 |
| `--tool-output-token-limit N` | `12000` tokens | モデル履歴に保持するツール出力の上限。 |
| `--lean` | — | ユーザーの Codex 設定を読み込まず、reasoning summary を無効化します。認証情報は引き続き利用されます。 |

すべてのオプションと終了コードは、`uv run wiggum run --help` で確認できます。

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
the ledger is complete or a stopping condition is hit. The default vendor is
Codex CLI (`codex exec`), the same as explicitly passing `--provider codex`.

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
uv run wiggum run --dry-run
uv run wiggum run
```

#### Scaffold a repository

`wiggum init` writes `config.toml`, `RALPH_PROJECT.md`, `TASKS.json`, and `PROGRESS.md`
under `wiggum/` in the target repository (`--repo` defaults to the current
directory). The general Ralph rules are bundled with wiggum. Edit
`wiggum/RALPH_PROJECT.md` and `wiggum/TASKS.json` to match your project before
running loops. Use `--force` to overwrite files that already exist.

#### Ralph file configuration

`wiggum run` always reads `wiggum/config.toml` in the target repository. A
missing configuration is a preflight error. The default configuration is:

```toml
[paths]
tasks = "wiggum/TASKS.json"
project = "wiggum/RALPH_PROJECT.md"
progress = "wiggum/PROGRESS.md"
```

Every `[paths]` key is required and must name a relative path inside the target
repository. The configured task ledger, project instructions, and progress
record must all exist.

- `.git/` — the repository metadata; `--repo` must name this Git root.

`RALPH.md` is not required in the target repository; wiggum provides the
general Ralph rules. `ralph_prompt.md` is optional and is only used when passed
with `--prompt-file`. Any files named by the configured project instructions,
such as `SPEC.md` or `AGENTS.md`, are required only when those instructions say
to read them.

### Options reference

Basic options (shared by all providers):

| Option | Default | Description |
| --- | --- | --- |
| `--repo PATH` | current directory | Repository to operate on. |
| `--prompt-file PATH` | wiggum's bundled Ralph loop prompt | Prompt passed to the agent for each loop. |
| `--logs-dir PATH` / `--temp-dir PATH` / `--uv-cache-dir PATH` | — | Override where wiggum writes loop logs, temporary files, and the uv cache. |
| `--no-managed-env` | — | Do not set `UV_CACHE_DIR`, `TMP`, and `TEMP` for the child process. |
| `--max-loops N` | — | — |
| `--model NAME` | — | — |
| `--auto-approve` | — | Whether this is required depends on the provider; see [Provider differences](#provider-differences). |
| `--api-retry-count N` | — | — |
| `--api-retry-interval-sec N` | — | — |
| `--codex-timeout-sec N` | — | Despite the name, this applies to all providers: the maximum time to wait for each provider's child process. |

Provider selection:

| Option | Default | Description |
| --- | --- | --- |
| `--provider {codex,copilot,claude}` | `codex` | AI model vendor to use. |
| `--executable PATH` | `codex`, `copilot`, or `claude` (matching the selected provider) | Vendor CLI executable. `--codex PATH` remains available as a deprecated alias for Codex. |

Reasoning effort:

| Option | Default | Description |
| --- | --- | --- |
| `--reasoning-effort LEVEL` | `medium` | Reasoning effort. Accepted values: `none`, `minimal`, `low`, `medium`, `high`, `xhigh`, `max`. Support varies by provider; see [Provider differences](#provider-differences). |

#### Codex-only options

The following options are only effective with `--provider codex`. Passing a
non-default value together with `--provider copilot` or `--provider claude`
is a validation error.

| Option | Default | Description |
| --- | --- | --- |
| `--model-verbosity LEVEL` | `low` | Codex output verbosity. |
| `--tool-output-token-limit N` | `12000` tokens | Maximum tool-output tokens retained in model history. |
| `--lean` | — | Ignore user Codex configuration and disable reasoning summaries; saved authentication remains available. |

Run `uv run wiggum run --help` for the full option list and exit codes.

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
