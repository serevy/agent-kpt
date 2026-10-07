from __future__ import annotations

from html import escape
from typing import Any, Mapping

REPORT_SCHEMA_VERSION = "agent-kpt.report/v0alpha1"

_MAX_KPIS = 4
_MAX_KEEP = 3
_MAX_PROBLEMS = 3
_MAX_TRENDS = 3
_FORBIDDEN_SCORING_KEYS = {"score", "rating", "grade", "rank"}

_COPY = {
    "ja": {
        "period": "対象期間",
        "kpis": "ぱっと見る",
        "keep": "うまくいったこと",
        "problems": "ちょっと気になること",
        "next_try": "次に1つだけ試す",
        "trends": "変化",
        "environment": "環境の変化",
        "details": "詳しく見る（数字・根拠）",
        "metrics": "生の回数と実質的な再発",
        "signal": "項目",
        "raw": "見えた回数",
        "sessions": "セッション",
        "lineages": "独立した作業",
        "days": "日数",
        "weeks": "週数",
        "evidence": "根拠",
        "error_breakdown": "エラー分類",
        "category": "分類",
        "subtype": "種類",
        "tool": "ツール",
        "outcome": "結果",
        "rule": "分類ルール",
        "provider_version": "Provider版",
        "representative": "代表Evidence",
        "all_evidence": "全Evidenceを見る",
        "error_privacy_note": "エラー本文は保存せず、分類結果と集計情報のみ保持しています。",
        "diagnostics": "取り込み時の注意",
        "source": "出所",
        "lineage": "作業系統",
        "none": "特になし",
    },
    "en": {
        "period": "Period",
        "kpis": "At a glance",
        "keep": "What worked",
        "problems": "Worth watching",
        "next_try": "Try just one thing",
        "trends": "Changes",
        "environment": "Environment changes",
        "details": "Show details (numbers and evidence)",
        "metrics": "Raw counts vs independent recurrence",
        "signal": "Signal",
        "raw": "Raw",
        "sessions": "Sessions",
        "lineages": "Independent work",
        "days": "Days",
        "weeks": "Weeks",
        "evidence": "Evidence",
        "error_breakdown": "Error classification",
        "category": "Category",
        "subtype": "Subtype",
        "tool": "Tool",
        "outcome": "Outcome",
        "rule": "Rule",
        "provider_version": "Provider version",
        "representative": "Representative evidence",
        "all_evidence": "Show all evidence",
        "error_privacy_note": "Raw error text is not persisted; derived classifications and aggregate telemetry are retained.",
        "diagnostics": "Ingestion notes",
        "source": "Source",
        "lineage": "Lineage",
        "none": "None",
    },
}


def validate_report_model(report: Mapping[str, Any]) -> None:
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise ValueError(f"unsupported report schema: {report.get('schema_version')!r}")

    _require_text(report, "headline")
    _require_text(report, "summary")
    _require_text(report, "locale")

    period = report.get("period")
    if not isinstance(period, Mapping):
        raise ValueError("period must be an object")
    for key in ("kind", "start", "end", "timezone"):
        _require_text(period, key, prefix="period.")

    kpis = _require_list(report, "kpis")
    keep = _require_list(report, "keep")
    problems = _require_list(report, "problems")
    trends = _require_list(report, "trends")
    env_markers = _require_list(report, "environment_markers")

    if len(kpis) > _MAX_KPIS:
        raise ValueError(f"kpis must contain at most {_MAX_KPIS} items")
    if len(keep) > _MAX_KEEP:
        raise ValueError(f"keep must contain at most {_MAX_KEEP} items")
    if len(problems) > _MAX_PROBLEMS:
        raise ValueError(f"problems must contain at most {_MAX_PROBLEMS} items")
    if len(trends) > _MAX_TRENDS:
        raise ValueError(f"trends must contain at most {_MAX_TRENDS} items")

    for item in kpis:
        _validate_kpi(item)
    for item in keep:
        _validate_card(item, "keep")
    for item in problems:
        _validate_card(item, "problem")
    for item in trends:
        _validate_trend(item)
    for item in env_markers:
        _validate_environment_marker(item)

    next_try = report.get("next_try")
    if next_try is not None:
        if not isinstance(next_try, Mapping):
            raise ValueError("next_try must be one object or null; do not return a list")
        _validate_card(next_try, "next_try")

    details = report.get("details")
    if not isinstance(details, Mapping):
        raise ValueError("details must be an object")
    metrics = _require_list(details, "metrics", prefix="details.")
    evidence = _require_list(details, "evidence", prefix="details.")
    diagnostics = _require_list(details, "diagnostics", prefix="details.")

    evidence_ids: set[str] = set()
    for item in evidence:
        if not isinstance(item, Mapping):
            raise ValueError("details.evidence items must be objects")
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str) or not evidence_id:
            raise ValueError("details.evidence.id must be a non-empty string")
        evidence_ids.add(evidence_id)
        _require_text(item, "title", prefix="details.evidence.")
        _require_text(item, "observed_at", prefix="details.evidence.")
        _require_text(item, "source", prefix="details.evidence.")

    for item in metrics:
        _validate_metric(item)

    for item in diagnostics:
        if not isinstance(item, Mapping):
            raise ValueError("details.diagnostics items must be objects")
        _require_text(item, "message", prefix="details.diagnostics.")

    for section_name, cards in (("keep", keep), ("problems", problems)):
        for card in cards:
            _validate_evidence_refs(card, evidence_ids, section_name)
    if next_try is not None:
        _validate_evidence_refs(next_try, evidence_ids, "next_try")

    scoring_path = _find_forbidden_scoring_key(report)
    if scoring_path:
        raise ValueError(
            f"user-facing report must not score or rank people/agents; remove {scoring_path}"
        )


def render_report_markdown(report: Mapping[str, Any]) -> str:
    validate_report_model(report)
    text = _copy_for(report)
    period = report["period"]
    lines = [
        f"# {report['headline']}",
        "",
        report["summary"],
        "",
        f"> {text['period']}: {period['start']} → {period['end']} · {period['timezone']}",
        "",
        f"## {text['kpis']}",
        "",
        "| | |",
        "| --- | ---: |",
    ]
    for item in report["kpis"]:
        hint = f" — {item['hint']}" if item.get("hint") else ""
        lines.append(f"| {item['label']}{hint} | **{item['value']}** |")

    if report["keep"]:
        lines.extend(["", f"## 👍 {text['keep']}", ""])
        for item in report["keep"]:
            lines.extend(_markdown_card(item))

    if report["problems"]:
        lines.extend(["", f"## ⚠️ {text['problems']}", ""])
        for item in report["problems"]:
            lines.extend(_markdown_card(item))

    next_try = report.get("next_try")
    if next_try:
        lines.extend(["", f"## 🌱 {text['next_try']}", ""])
        lines.extend(_markdown_card(next_try))

    if report["trends"]:
        lines.extend(["", f"## {text['trends']}", ""])
        for item in report["trends"]:
            symbol = {"up": "↑", "down": "↓", "flat": "→", "new": "NEW"}.get(item["direction"], "→")
            lines.append(f"- **{symbol} {item['label']}** — {item['body']}")

    if report["environment_markers"]:
        lines.extend(["", f"## {text['environment']}", ""])
        for item in report["environment_markers"]:
            lines.append(
                f"- **{item['label']}**: {item['previous']} → {item['current']} — {item['body']}"
            )

    lines.extend(["", "---", "", f"## {text['details']}", ""])
    lines.extend(_markdown_details(report, text))
    return "\n".join(lines).rstrip() + "\n"


def render_report_html(report: Mapping[str, Any]) -> str:
    validate_report_model(report)
    text = _copy_for(report)
    period = report["period"]
    locale = str(report["locale"])
    lang = locale.split("-", 1)[0].lower() or "en"

    kpis = "".join(
        '<div class="kpi"><span class="kpi-label">'
        + escape(str(item["label"]))
        + '</span><strong class="kpi-value">'
        + escape(str(item["value"]))
        + "</strong>"
        + (f'<span class="kpi-hint">{escape(str(item["hint"]))}</span>' if item.get("hint") else "")
        + "</div>"
        for item in report["kpis"]
    )

    keep_html = _html_cards(report["keep"], "keep")
    problem_html = _html_cards(report["problems"], "problem")
    next_try = report.get("next_try")
    next_html = _html_cards([next_try] if next_try else [], "try")

    trends = "".join(
        '<li><span class="trend-mark">'
        + escape({"up": "↑", "down": "↓", "flat": "→", "new": "NEW"}.get(item["direction"], "→"))
        + "</span><strong>"
        + escape(str(item["label"]))
        + "</strong><span>"
        + escape(str(item["body"]))
        + "</span></li>"
        for item in report["trends"]
    )

    env = "".join(
        '<li><strong>'
        + escape(str(item["label"]))
        + "</strong><span>"
        + escape(str(item["previous"]))
        + " → "
        + escape(str(item["current"]))
        + "</span><p>"
        + escape(str(item["body"]))
        + "</p></li>"
        for item in report["environment_markers"]
    )

    details_html = _html_details(report, text)

    return f"""<!doctype html>
<html lang="{escape(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(str(report["headline"]))} · agent-kpt</title>
<style>
:root{{--bg:#f7f7f4;--panel:#fff;--text:#202124;--muted:#666;--line:#ddd;--keep:#28784a;--problem:#a15c00;--try:#3168b2;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.55}}
main{{max-width:980px;margin:0 auto;padding:32px 18px 64px}}
header{{margin-bottom:24px}}
.eyebrow{{color:var(--muted);font-size:.9rem;margin:0 0 8px}}
h1{{font-size:clamp(1.7rem,5vw,2.6rem);line-height:1.2;margin:0 0 12px}}
.lead{{font-size:1.08rem;max-width:70ch;margin:0}}
h2{{font-size:1.15rem;margin:28px 0 12px}}
.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
.kpi,.card,.panel,details{{background:var(--panel);border:1px solid var(--line);border-radius:14px}}
.kpi{{padding:14px;display:flex;flex-direction:column;gap:4px}}
.kpi-label,.kpi-hint{{color:var(--muted);font-size:.84rem}}
.kpi-value{{font-size:1.7rem}}
.card-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}}
.card{{padding:16px;border-left-width:5px}}
.card.keep{{border-left-color:var(--keep)}} .card.problem{{border-left-color:var(--problem)}} .card.try{{border-left-color:var(--try)}}
.card h3{{font-size:1rem;margin:0 0 6px}} .card p{{margin:0}}
.badge{{display:inline-block;font-size:.72rem;border:1px solid var(--line);border-radius:999px;padding:2px 7px;margin-bottom:8px;color:var(--muted)}}
.panel{{padding:14px 16px}}
.panel ul{{margin:0;padding-left:20px}} .panel li+li{{margin-top:8px}}
.trend-mark{{display:inline-block;min-width:2.6em;font-weight:700}}
details{{margin-top:32px;padding:0 16px 16px}}
.evidence-all{{margin-top:12px;padding:0 12px 12px}}
.evidence-all summary{{padding:12px 0}}
summary{{cursor:pointer;font-weight:700;padding:16px 0}}
table{{width:100%;border-collapse:collapse;font-size:.9rem}}
th,td{{border-bottom:1px solid var(--line);padding:8px;text-align:left;vertical-align:top}}
th:not(:first-child),td:not(:first-child){{text-align:right}}
.evidence{{display:grid;gap:10px}}
.evidence article{{border-top:1px solid var(--line);padding-top:10px}}
.evidence h4{{margin:0 0 4px}} .evidence p{{margin:2px 0;color:var(--muted);font-size:.9rem}}
.note{{color:var(--muted);font-size:.9rem}}
@media (max-width:620px){{main{{padding-top:22px}} table{{font-size:.8rem}} th,td{{padding:6px 4px}}}}
</style>
</head>
<body>
<main>
<header>
<p class="eyebrow">{escape(text["period"])}: {escape(str(period["start"]))} → {escape(str(period["end"]))} · {escape(str(period["timezone"]))}</p>
<h1>{escape(str(report["headline"]))}</h1>
<p class="lead">{escape(str(report["summary"]))}</p>
</header>

<section aria-labelledby="kpi-title">
<h2 id="kpi-title">{escape(text["kpis"])}</h2>
<div class="kpi-grid">{kpis}</div>
</section>

{_html_section("keep-title", "👍 " + text["keep"], keep_html) if keep_html else ""}
{_html_section("problem-title", "⚠️ " + text["problems"], problem_html) if problem_html else ""}
{_html_section("try-title", "🌱 " + text["next_try"], next_html) if next_html else ""}

{f'<section aria-labelledby="trend-title"><h2 id="trend-title">{escape(text["trends"])}</h2><div class="panel"><ul>{trends}</ul></div></section>' if trends else ""}
{f'<section aria-labelledby="env-title"><h2 id="env-title">{escape(text["environment"])}</h2><div class="panel"><ul>{env}</ul></div></section>' if env else ""}

<details class="drilldown">
<summary>{escape(text["details"])}</summary>
{details_html}
</details>
</main>
</body>
</html>
"""


def _markdown_card(item: Mapping[str, Any]) -> list[str]:
    badge = f" `{item['badge']}`" if item.get("badge") else ""
    return [f"### {item['title']}{badge}", "", str(item["body"]), ""]


def _markdown_details(report: Mapping[str, Any], text: Mapping[str, str]) -> list[str]:
    details = report["details"]
    lines = [
        f"### {text['metrics']}",
        "",
        f"| {text['signal']} | {text['raw']} | {text['sessions']} | {text['lineages']} | {text['days']} | {text['weeks']} |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in details["metrics"]:
        lines.append(
            f"| {item['label']} | {item['raw_occurrences']} | {item['unique_sessions']} | "
            f"{item['unique_root_lineages']} | {item['distinct_days']} | {item['distinct_weeks']} |"
        )
        if item.get("plain_note"):
            lines.append(f"| ↳ {item['plain_note']} |  |  |  |  |  |")

    error_groups = _group_error_evidence(details["evidence"])
    if error_groups:
        lines.extend(["", f"### {text['error_breakdown']}", "", text["error_privacy_note"], ""])
        lines.extend(
            [
                f"| {text['category']} | {text['subtype']} | {text['outcome']} | {text['tool']} | {text['rule']} | {text['raw']} | {text['sessions']} | {text['lineages']} |",
                "| --- | --- | --- | --- | --- | ---: | ---: | ---: |",
            ]
        )
        for group in error_groups:
            lines.append(
                f"| {_markdown_safe(group['category'])} | {_markdown_safe(group['subtype'])} | "
                f"{_markdown_safe(group['outcome'])} | {_markdown_safe(group['tool'])} | "
                f"{_markdown_safe(group['rule_scope'])}:{_markdown_safe(group['rule_id'])}@{_markdown_safe(group['ruleset_version'])} | "
                f"{group['raw_occurrences']} | {group['unique_sessions']} | {group['unique_root_lineages']} |"
            )

        lines.extend(["", f"### {text['representative']}", ""])
        for group in error_groups:
            lines.append(
                f"#### {_markdown_safe(group['category'])} / {_markdown_safe(group['subtype'])} "
                f"· {_markdown_safe(group['outcome'])} · {_markdown_safe(group['tool'])} "
                f"· {_markdown_safe(group['rule_scope'])}:{_markdown_safe(group['rule_id'])}@{_markdown_safe(group['ruleset_version'])} "
                f"({group['raw_occurrences']})"
            )
            lines.append("")
            for item in group["representative"]:
                lines.extend(_markdown_evidence_item(item, text))
            lines.append("")

    lines.extend(["", f"### {text['evidence']}", ""])
    if not details["evidence"]:
        lines.append(text["none"])
    for item in details["evidence"]:
        lines.extend(_markdown_evidence_item(item, text))

    if details["diagnostics"]:
        lines.extend(["", f"### {text['diagnostics']}", ""])
        for item in details["diagnostics"]:
            count = item.get("count", 1)
            suffix = f" ×{count}" if isinstance(count, int) and count > 1 else ""
            lines.append(f"- {item['message']}{suffix}")
    return lines


def _markdown_safe(value: Any) -> str:
    escaped = escape(str(value), quote=False)
    return (
        escaped.replace("|", "&#124;")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "<br>")
    )


def _markdown_code(value: Any) -> str:
    return f"<code>{_markdown_safe(value)}</code>"


def _markdown_evidence_item(item: Mapping[str, Any], text: Mapping[str, str]) -> list[str]:
    lineage = item.get("root_lineage_id") or "-"
    extras = []
    if item.get("category"):
        extras.append(f"{text['category']}: {_markdown_code(item['category'])}")
    if item.get("subtype"):
        extras.append(f"{text['subtype']}: {_markdown_code(item['subtype'])}")
    if item.get("outcome"):
        extras.append(f"{text['outcome']}: {_markdown_code(item['outcome'])}")
    if item.get("tool"):
        extras.append(f"{text['tool']}: {_markdown_code(item['tool'])}")
    if item.get("rule_id"):
        scope = item.get("rule_scope") or "unknown"
        ruleset = item.get("ruleset_version") or "unknown"
        rule_label = f"{scope}:{item['rule_id']}@{ruleset}"
        extras.append(f"{text['rule']}: {_markdown_code(rule_label)}")
    if item.get("provider_version"):
        extras.append(
            f"{text['provider_version']}: {_markdown_code(item['provider_version'])}"
        )
    lines = [
        f"- **{_markdown_safe(item['title'])}**",
        f"  - {_markdown_safe(item['observed_at'])} · {text['lineage']}: {_markdown_code(lineage)} "
        f"· {text['source']}: {_markdown_code(item['source'])}",
    ]
    if extras:
        lines.append("  - " + " · ".join(extras))
    if item.get("note"):
        lines.append(f"  - {_markdown_safe(item['note'])}")
    return lines

def _html_cards(items: list[Mapping[str, Any]], kind: str) -> str:
    blocks: list[str] = []
    for item in items:
        badge = f'<span class="badge">{escape(str(item["badge"]))}</span>' if item.get("badge") else ""
        blocks.append(
            f'<article class="card {escape(kind)}">{badge}<h3>{escape(str(item["title"]))}</h3>'
            f'<p>{escape(str(item["body"]))}</p></article>'
        )
    return "".join(blocks)


def _html_section(section_id: str, title: str, cards: str) -> str:
    return (
        f'<section aria-labelledby="{escape(section_id)}"><h2 id="{escape(section_id)}">{escape(title)}</h2>'
        f'<div class="card-grid">{cards}</div></section>'
    )


def _html_details(report: Mapping[str, Any], text: Mapping[str, str]) -> str:
    details = report["details"]
    rows: list[str] = []
    for item in details["metrics"]:
        label = escape(str(item["label"]))
        if item.get("plain_note"):
            label += f'<div class="note">{escape(str(item["plain_note"]))}</div>'
        rows.append(
            "<tr>"
            f"<td>{label}</td>"
            f"<td>{item['raw_occurrences']}</td>"
            f"<td>{item['unique_sessions']}</td>"
            f"<td>{item['unique_root_lineages']}</td>"
            f"<td>{item['distinct_days']}</td>"
            f"<td>{item['distinct_weeks']}</td>"
            "</tr>"
        )

    error_groups = _group_error_evidence(details["evidence"])
    error_html = ""
    if error_groups:
        group_rows = "".join(
            "<tr>"
            f"<td>{escape(str(group['category']))}</td>"
            f"<td>{escape(str(group['subtype']))}</td>"
            f"<td>{escape(str(group['outcome']))}</td>"
            f"<td>{escape(str(group['tool']))}</td>"
            f"<td>{escape(str(group['rule_scope']))}:{escape(str(group['rule_id']))}@{escape(str(group['ruleset_version']))}</td>"
            f"<td>{group['raw_occurrences']}</td>"
            f"<td>{group['unique_sessions']}</td>"
            f"<td>{group['unique_root_lineages']}</td>"
            "</tr>"
            for group in error_groups
        )
        representative = []
        for group in error_groups:
            blocks = "".join(_html_evidence_item(item, text) for item in group["representative"])
            representative.append(
                f"<section><h4>{escape(str(group['category']))} / {escape(str(group['subtype']))} "
                f"· {escape(str(group['outcome']))} · {escape(str(group['tool']))} "
                f"· {escape(str(group['rule_scope']))}:{escape(str(group['rule_id']))}@{escape(str(group['ruleset_version']))} "
                f"({group['raw_occurrences']})</h4>"
                f'<div class="evidence">{blocks}</div></section>'
            )
        error_html = (
            f'<h3>{escape(text["error_breakdown"])}</h3>'
            f'<p class="note">{escape(text["error_privacy_note"])}</p>'
            '<div style="overflow-x:auto"><table>'
            f'<thead><tr><th>{escape(text["category"])}</th><th>{escape(text["subtype"])}</th>'
            f'<th>{escape(text["outcome"])}</th><th>{escape(text["tool"])}</th>'
            f'<th>{escape(text["rule"])}</th><th>{escape(text["raw"])}</th>'
            f'<th>{escape(text["sessions"])}</th><th>{escape(text["lineages"])}</th></tr></thead>'
            f'<tbody>{group_rows}</tbody></table></div>'
            f'<h3>{escape(text["representative"])}</h3>'
            + "".join(representative)
        )

    all_evidence = "".join(_html_evidence_item(item, text) for item in details["evidence"])
    evidence_html = (
        f'<details class="evidence-all"><summary>{escape(text["all_evidence"])} '
        f'({len(details["evidence"])})</summary>'
        f'<div class="evidence">{all_evidence}</div></details>'
        if details["evidence"]
        else f'<p class="note">{escape(text["none"])}</p>'
    )

    diagnostics = "".join(
        "<li>"
        + escape(str(item["message"]))
        + (
            f" ×{item['count']}"
            if isinstance(item.get("count"), int) and item.get("count", 1) > 1
            else ""
        )
        + "</li>"
        for item in details["diagnostics"]
    )
    diagnostics_html = (
        f'<h3>{escape(text["diagnostics"])}</h3><ul>{diagnostics}</ul>' if diagnostics else ""
    )

    return (
        f'<h3>{escape(text["metrics"])}</h3>'
        '<div style="overflow-x:auto"><table>'
        f'<thead><tr><th>{escape(text["signal"])}</th><th>{escape(text["raw"])}</th>'
        f'<th>{escape(text["sessions"])}</th><th>{escape(text["lineages"])}</th>'
        f'<th>{escape(text["days"])}</th><th>{escape(text["weeks"])}</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table></div>'
        + error_html
        + f'<h3>{escape(text["evidence"])}</h3>'
        + evidence_html
        + diagnostics_html
    )


def _html_evidence_item(item: Mapping[str, Any], text: Mapping[str, str]) -> str:
    lineage = item.get("root_lineage_id") or "-"
    note = f'<p>{escape(str(item["note"]))}</p>' if item.get("note") else ""
    extras = []
    if item.get("category"):
        extras.append(f'{escape(text["category"])}: <code>{escape(str(item["category"]))}</code>')
    if item.get("subtype"):
        extras.append(f'{escape(text["subtype"])}: <code>{escape(str(item["subtype"]))}</code>')
    if item.get("outcome"):
        extras.append(f'{escape(text["outcome"])}: <code>{escape(str(item["outcome"]))}</code>')
    if item.get("tool"):
        extras.append(f'{escape(text["tool"])}: <code>{escape(str(item["tool"]))}</code>')
    if item.get("rule_id"):
        scope = item.get("rule_scope") or "unknown"
        ruleset = item.get("ruleset_version") or "unknown"
        extras.append(
            f'{escape(text["rule"])}: <code>{escape(str(scope))}:{escape(str(item["rule_id"]))}@{escape(str(ruleset))}</code>'
        )
    if item.get("provider_version"):
        extras.append(
            f'{escape(text["provider_version"])}: <code>{escape(str(item["provider_version"]))}</code>'
        )
    extra_html = f'<p>{" · ".join(extras)}</p>' if extras else ""
    return (
        "<article>"
        f"<h4>{escape(str(item['title']))}</h4>"
        f"<p>{escape(str(item['observed_at']))} · {escape(text['lineage'])}: "
        f"<code>{escape(str(lineage))}</code> · {escape(text['source'])}: "
        f"<code>{escape(str(item['source']))}</code></p>"
        f"{extra_html}{note}</article>"
    )


def _group_error_evidence(evidence: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[
        tuple[str, str, str, str, str, str, str, str],
        list[Mapping[str, Any]],
    ] = {}
    for item in evidence:
        if item.get("kind") != "error" and not item.get("category"):
            continue
        key = (
            str(item.get("category") or "unknown"),
            str(item.get("subtype") or "unknown"),
            str(item.get("outcome") or "unknown"),
            str(item.get("tool") or "unknown"),
            str(item.get("rule_scope") or "common"),
            str(item.get("rule_id") or "classifier.unknown"),
            str(item.get("ruleset_version") or "unknown"),
            str(item.get("provider_version") or "unknown"),
        )
        groups.setdefault(key, []).append(item)

    output = []
    for (
        category,
        subtype,
        outcome,
        tool,
        rule_scope,
        rule_id,
        ruleset_version,
        provider_version,
    ), items in groups.items():
        sessions = {item.get("session_id") for item in items if item.get("session_id")}
        lineages = {
            item.get("root_lineage_id")
            for item in items
            if item.get("root_lineage_id")
        }
        output.append(
            {
                "category": category,
                "subtype": subtype,
                "outcome": outcome,
                "tool": tool,
                "rule_scope": rule_scope,
                "rule_id": rule_id,
                "ruleset_version": ruleset_version,
                "provider_version": provider_version,
                "raw_occurrences": len(items),
                "unique_sessions": len(sessions),
                "unique_root_lineages": len(lineages),
                "representative": _representative_evidence(items, limit=3),
            }
        )
    output.sort(
        key=lambda group: (
            -group["raw_occurrences"],
            group["category"],
            group["subtype"],
            group["outcome"],
            group["tool"],
            group["rule_scope"],
            group["rule_id"],
            group["ruleset_version"],
            group["provider_version"],
        )
    )
    return output


def _representative_evidence(
    items: list[Mapping[str, Any]], *, limit: int
) -> list[Mapping[str, Any]]:
    selected: list[Mapping[str, Any]] = []
    selected_object_ids: set[int] = set()
    seen_lineages: set[str] = set()
    for item in items:
        lineage = item.get("root_lineage_id")
        if isinstance(lineage, str) and lineage not in seen_lineages:
            selected.append(item)
            selected_object_ids.add(id(item))
            seen_lineages.add(lineage)
        if len(selected) >= limit:
            return selected
    for item in items:
        if id(item) not in selected_object_ids:
            selected.append(item)
            selected_object_ids.add(id(item))
        if len(selected) >= limit:
            break
    return selected

def _validate_kpi(item: Any) -> None:
    if not isinstance(item, Mapping):
        raise ValueError("kpi items must be objects")
    _require_text(item, "label", prefix="kpis.")
    value = item.get("value")
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        raise ValueError("kpis.value must be a string or number")


def _validate_card(item: Any, section: str) -> None:
    if not isinstance(item, Mapping):
        raise ValueError(f"{section} items must be objects")
    _require_text(item, "title", prefix=f"{section}.")
    _require_text(item, "body", prefix=f"{section}.")
    refs = item.get("evidence_ids", [])
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref for ref in refs):
        raise ValueError(f"{section}.evidence_ids must be a list of strings")


def _validate_trend(item: Any) -> None:
    if not isinstance(item, Mapping):
        raise ValueError("trend items must be objects")
    _require_text(item, "label", prefix="trends.")
    _require_text(item, "body", prefix="trends.")
    if item.get("direction") not in {"up", "down", "flat", "new"}:
        raise ValueError("trends.direction must be up/down/flat/new")


def _validate_environment_marker(item: Any) -> None:
    if not isinstance(item, Mapping):
        raise ValueError("environment markers must be objects")
    for key in ("label", "previous", "current", "body"):
        _require_text(item, key, prefix="environment_markers.")


def _validate_metric(item: Any) -> None:
    if not isinstance(item, Mapping):
        raise ValueError("details.metrics items must be objects")
    _require_text(item, "label", prefix="details.metrics.")
    for key in (
        "raw_occurrences",
        "unique_sessions",
        "unique_root_lineages",
        "distinct_days",
        "distinct_weeks",
    ):
        value = item.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"details.metrics.{key} must be a non-negative integer")


def _validate_evidence_refs(card: Mapping[str, Any], evidence_ids: set[str], section: str) -> None:
    missing = [ref for ref in card.get("evidence_ids", []) if ref not in evidence_ids]
    if missing:
        raise ValueError(f"{section} references missing evidence ids: {', '.join(missing)}")


def _require_list(mapping: Mapping[str, Any], key: str, *, prefix: str = "") -> list[Any]:
    value = mapping.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{prefix}{key} must be a list")
    return value


def _require_text(mapping: Mapping[str, Any], key: str, *, prefix: str = "") -> None:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{prefix}{key} must be a non-empty string")


def _copy_for(report: Mapping[str, Any]) -> Mapping[str, str]:
    locale = str(report.get("locale", "en"))
    language = locale.split("-", 1)[0].lower()
    return _COPY.get(language, _COPY["en"])


def _find_forbidden_scoring_key(value: Any, path: str = "$") -> str | None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            next_path = f"{path}.{key}"
            if str(key).lower() in _FORBIDDEN_SCORING_KEYS:
                return next_path
            found = _find_forbidden_scoring_key(child, next_path)
            if found:
                return found
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found = _find_forbidden_scoring_key(child, f"{path}[{index}]")
            if found:
                return found
    return None
