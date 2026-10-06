[English](README.md) | 日本語

# agent-kpt

**人間とコーディングエージェントの協働を、少しずつ良くするための振り返りツール。**

`agent-kpt` は、コーディングエージェントを使う人向けの実験的な継続改善ツールキットです。

実際のセッション履歴を解析し、機械的に数えられる情報と、意味を読み取る部分を分けて扱います。週次・月次のKPTでは、Agentだけでなく、作業全体を振り返ります。

- **Human** — 指示の粒度、セッションの切り替え、compact / fork / clear のタイミング、モデルの使い分け
- **Agent** — 繰り返す失敗、リトライ、指示の取りこぼし、不要な探索
- **Tooling** — キャッシュ、レイテンシ、スクリプト、コマンド、静的チェック、各種連携
- **Workflow** — 繰り返しの手作業、引き継ぎ、レビューの往復、自動化できそうな作業

人やAgentを採点するのが目的ではありません。**次の1週間を、今週より少し快適にする**ための道具です。

> 日本語版は読みやすさを優先した翻訳です。仕様上の正本は [English README](README.md) とし、内容に差がある場合は英語版を優先します。

## どう動くか

```text
コーディングエージェントのセッション
        |
        v
Provider adapter
        |
        v
機械的に集計できる telemetry
        |
        v
Evidence / 再発分析
        |
        v
週次 / 月次 KPT
        |
        +--> Keep     続けたい良いパターン
        +--> Problem  繰り返している困りごと
        +--> Try      次に試す小さな改善
        |
        v
人が確認・判断
        |
        v
Skill / Script / Config / Workflow の改善
        |
        v
次のセッション
```

良い行動が習慣になったら、いつまでもレポートに残しません。モデルやCLI、ワークフローが変われば、昔は有効だった工夫が不要になることもあります。改善策は積み上げ続けるのではなく、必要に応じて再検証・卒業・retireします。

## 設計方針

- **Deterministic first.** token数、cache、error、latency、tool利用など、数えられるものはコードで数えます。LLMには計算ではなく解釈を任せます。
- **Human-gated.** レポートは改善案を出しますが、利用者の環境を勝手に書き換えません。
- **Evidence-backed.** 表のレポートは短くしても、根拠となる詳細データは残します。
- **Lineage-aware.** fork / branch で増えた履歴を、独立した再発や利用量として二重計上しません。
- **Provider-neutral core.** 最初のAdapterはClaude Codeですが、CoreをClaude Code専用にはしません。
- **Human + Agent.** Agentの失敗だけでなく、人の使い方、Tool、Workflowも改善対象です。
- **Adaptive, not additive.** 改善策には根拠と履歴を持たせ、環境が変わったら再検証し、不要になればretireします。
- **Local-first where practical.** 生の作業履歴は、できるだけ利用者の手元に残します。

## レポート

表側のレポートは、数分で読める量に絞ります。

1. 短いまとめとKPI
2. 変化やトレンド
3. 大事なKeep / Problem
4. **次に1つだけ試すこと**
5. 必要な人だけ開く詳細Evidence

振り返り自体が新しい仕事にならないことを重視しています。

## 最初の対象範囲

最初の公開版では、次を中心に進めます。

- Claude Codeのセッション取り込み
- 週次 / 月次KPT
- context / cache / latency / retry のtelemetry
- session lineage / fork の重複除外
- Problem / Evidence / Intervention の継続追跡
- セッションの区切り方やAgentとのやり取りに関する軽いコーチング
- 短いHTML + Markdownレポート

将来的には Codex、OpenCode、Cursor、Hermes などのAdapterも追加できます。

## やらないこと

- 提案した改善をすべて自動適用する
- 万能な「正しいプロンプトの書き方」を決める
- 相関だけを見て因果関係だと断定する
- 開発者を順位づけする
- 特定のモデルやProviderを強制する
- 既存のobservability / code review製品を置き換える

## 現在の状態

実際に個人運用していたKPTから、OSSとして切り出している初期段階です。InterfaceやSchemaはまだ安定版ではありません。

## License

MIT.

## Project decisions

このリポジトリでは、長く残すべきProject / Product / Process上の判断を [PDDR Kit](https://github.com/serevy/pddr-kit) で記録しています。

- Records: [`docs/records/`](docs/records/)
- Template: [`.pddr/template.md`](.pddr/template.md)
- Validate: `python .pddr/pddr.py validate --allow-empty`

PDDRは作業ログではありません。あとから「なぜそう決めたのか」が必要になる判断だけを残します。

## Baseline

OSS化する前の個人運用は、機密情報を除いたbehavioral baselineとして保存しています。

- [Baseline design](docs/baseline-v0.md)
- [Synthetic fixtures](fixtures/baseline-v0/)
- [Regression contract](fixtures/baseline-v0/regression-check.md)

## Python reference implementation

Coreの契約は言語非依存のまま、最初のreference implementationにはPythonを使っています。

Requirements: Python 3.10+.

```bash
python -m pip install -e .

agent-kpt ingest claude-code ~/.claude/projects/<project>/*.jsonl \
  --lineage-map lineage.json \
  -o normalized.json

agent-kpt metrics normalized.json -o metrics.json
agent-kpt report normalized.json -o report.md
```

Claude CodeのJSONLは安定した公開Schemaとして扱いません。既知のtelemetryだけを正規化し、未知のrecordはrecoverable diagnosticとして残しながら処理を続けます。生のprompt、assistant本文、tool input / outputはnormalized telemetryへコピーしません。

セッションのlineageは明示的に扱います。message単位の `parentUuid` を親**セッション**だとは決めつけず、信頼できるlineage情報がある場合はlineage mapを渡せます。

reference implementationはWindows / macOS / Linuxでテストしています。UTCのレポートには外部timezone dataは不要です。それ以外のIANA timezoneは、OSによって `tzdata` packageが必要になる場合があります。

## 短く読めるコーチングレポート

作業者が最初に見るレポートは、裏側にあるEvidenceより意図的に小さくしています。目的は採点ではなく、短時間で振り返れることです。

表に出す量には上限があります。

- KPI: 最大4
- Keep: 最大3
- Problem: 最大3
- **Next Try: 1つ**
- Trend: 最大3
- 必要な場合だけ環境変更のmarker

raw count、重複除外後の数、lineage、Evidenceは削除せず、詳細側に残します。

Report View ModelからHTMLを生成する場合:

```bash
agent-kpt render-report fixtures/report-v0alpha1/report-ja.json \
  --format html \
  -o report.html
```

Markdown版も生成できます。

```bash
agent-kpt render-report fixtures/report-v0alpha1/report-ja.json \
  --format markdown \
  -o report.md
```

日本語の表現は、必要なら [natural-japanese](https://github.com/coji/natural-japanese) のような外部writing skillで整えられます。ただしcopy polishを行うのは**事実を確定した後**です。KPI、lineage数、lifecycle state、Evidence ID、timestamp、provenanceは変更しません。

詳しくは [Japanese copy polish boundary](docs/japanese-copy-policy.md) を参照してください。


## いつもの入口は `/agent-kpt`

普段はAgent Skillから呼びます。

```text
/agent-kpt
/agent-kpt weekly
/agent-kpt monthly
/agent-kpt status
```

引数なしは `weekly` です。

Skill側はできるだけ薄くしています。Pythonが現在のProjectに対応するClaude Codeログを探し、重複を除いて集計し、privacy-safeなanalysis packetとローカルLedgerを作ります。そのpacketをAgentが読み取って短いレポートを組み立て、最後にdeterministic rendererがHTML / Markdownへ変換します。

既定のpacketには、生のprompt本文、assistant本文、tool input / outputを保存しません。

### このリポジトリから試す

Skill本体は [`skills/agent-kpt/SKILL.md`](skills/agent-kpt/SKILL.md) にあります。利用しているAgent Skillの導入方法でこのSkillを追加すると、`/agent-kpt` を入口にできます。

Claude Code向けには [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) とrepo-local launcherも入っています。開発時はcloneしたこのリポジトリをlocal plugin directoryとして読み込んで検証できます。Pluginとして読み込む場合は、host側のnamespaceがコマンド名に付くことがあります。

インストール済みの `agent-kpt` CLIがあればそれを使い、Claude Code Pluginとしてこのrepoから実行する場合は次のlauncherへfallbackできます。

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/agent-kpt.py" status --project .
```

Python 3.10+ が必要です。Skillが利用者のProjectへ勝手にdependencyをinstallすることはありません。

Ledger、workflow中間ファイル、レポートは既定で対象Projectの外に保存します。

```text
~/.agent-kpt/projects/<hashed-project-path>/
  ledger.json
  last-packet.json
  work/
  reports/
```

state全体の保存場所を変えたい場合は `AGENT_KPT_HOME`、最終レポートだけ変えたい場合は `AGENT_KPT_REPORT_DIR` を使えます。`AGENT_KPT_REPORT_DIR` は明示overrideなので、対象Repository内を指定した場合は意図どおり `git status` にレポートが出る可能性があります。

既定のanalysis packetには、生のprompt本文、assistant本文、tool input / output、エラー本文を保存しません。エラー本文は利用者のローカル環境で一時的に分類へ使い、`category / subtype / tool / fingerprint` などの派生情報だけを保持します。

同じadapter warningはcode単位で件数集約し、`user.message` は個別Evidenceへ大量投入せず、件数や文字数などの集計値だけを残します。

詳しい処理の流れとprivacy boundaryは [One-command workflow](docs/one-command-workflow.md) を参照してください。
