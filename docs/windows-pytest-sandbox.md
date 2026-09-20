# Windows: pytest を sandbox 外で実行する / Run only pytest outside the sandbox

## 日本語

Windows の通常のユーザー Temp を必要とする pytest を実行する場合でも、
`--auto-approve` は不要です。Codex の command rule で `uv run -m pytest` だけを
sandbox 外で許可し、対象リポジトリの `wiggum/config.toml` に
`[run].manage_process_env = false` を設定してください。これは
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
uv run wiggum run --provider codex
```

## English

When pytest requires the normal Windows user Temp directory, you do not need
`--auto-approve`. Use a Codex command rule to allow only `uv run -m pytest`
outside the sandbox, and set `[run].manage_process_env = false` in the target
repository's `wiggum/config.toml`. This leaves `TMP`, `TEMP`, and
`UV_CACHE_DIR` unchanged for the Codex child process, so pytest inherits the
parent's normal Temp configuration.

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
uv run wiggum run --provider codex
```
