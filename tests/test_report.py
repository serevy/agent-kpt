import copy
import json
import unittest
from pathlib import Path

from agent_kpt.report import (
    render_report_html,
    render_report_markdown,
    validate_report_model,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "report-v0alpha1" / "report-ja.json"


class ReportViewTests(unittest.TestCase):
    def _report(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_is_valid_and_has_one_next_try(self):
        report = self._report()
        validate_report_model(report)
        self.assertIsInstance(report["next_try"], dict)
        self.assertNotIn("score", json.dumps(report, ensure_ascii=False).lower())

    def test_markdown_is_summary_first_and_evidence_backed(self):
        rendered = render_report_markdown(self._report())
        self.assertLess(rendered.index("🌱 次に1つだけ試す"), rendered.index("詳しく見る（数字・根拠）"))
        self.assertIn("パス指定の失敗 | 2 | 2 | 1 | 1 | 1", rendered)
        self.assertIn("Claude Code", rendered)
        self.assertIn("2.0.synthetic → 2.1.synthetic", rendered)

    def test_html_uses_collapsed_progressive_disclosure(self):
        rendered = render_report_html(self._report())
        self.assertIn('<details class="drilldown">', rendered)
        self.assertNotIn('<details class="drilldown" open', rendered)
        self.assertIn("詳しく見る（数字・根拠）", rendered)
        self.assertIn("独立した作業", rendered)
        self.assertLess(rendered.index("次に1つだけ試す"), rendered.index('<details class="drilldown">'))

    def test_error_evidence_is_grouped_before_full_list(self):
        report = self._report()
        for index, item in enumerate(report["details"]["evidence"]):
            item["kind"] = "error"
            item["session_id"] = f"session-{index}"
            item["category"] = "path"
            item["subtype"] = "file-not-found"
            item["tool"] = "Bash"
        rendered = render_report_html(report)
        self.assertIn("エラー分類", rendered)
        self.assertIn("代表Evidence", rendered)
        self.assertIn("全Evidenceを見る", rendered)
        self.assertIn('class="evidence-all"', rendered)
        self.assertIn("file-not-found", rendered)
        self.assertIn("エラー本文は保存せず", rendered)

    def test_classifier_provenance_is_visible_and_kept_distinct(self):
        report = self._report()
        base = report["details"]["evidence"][0]
        base["kind"] = "error"
        base["session_id"] = "session-a"
        base["category"] = "tool-state"
        base["subtype"] = "unity-busy"
        base["outcome"] = "waiting"
        base["tool"] = "Bash"
        base["rule_scope"] = "user"
        base["rule_id"] = "user.unity.compiling"
        base["ruleset_version"] = "local-v1"
        base["provider_version"] = "2.1.synthetic"

        second = copy.deepcopy(base)
        second["id"] = "evidence-rule-v2"
        second["session_id"] = "session-b"
        second["root_lineage_id"] = "root-b"
        second["rule_id"] = "user.unity.compiling-v2"
        second["ruleset_version"] = "local-v2"
        report["details"]["evidence"].append(second)

        markdown = render_report_markdown(report)
        html = render_report_html(report)
        self.assertIn("waiting", markdown)
        self.assertIn("user:user.unity.compiling@local-v1", markdown)
        self.assertIn("user:user.unity.compiling-v2@local-v2", markdown)
        self.assertIn("Provider版", markdown)
        self.assertIn("2.1.synthetic", markdown)
        self.assertIn("user.unity.compiling", html)
        self.assertIn("local-v2", html)

    def test_markdown_escapes_error_group_values(self):
        report = self._report()
        item = report["details"]["evidence"][0]
        item["kind"] = "error"
        item["session_id"] = "session-a"
        item["category"] = "path|odd"
        item["subtype"] = "file\nnot-found"
        item["tool"] = "Bash|Tool"
        rendered = render_report_markdown(report)
        self.assertIn("path&#124;odd", rendered)
        self.assertIn("file<br>not-found", rendered)
        self.assertIn("Bash&#124;Tool", rendered)
        self.assertNotIn("| path|odd |", rendered)

    def test_counted_diagnostics_render_as_one_line(self):
        report = self._report()
        report["details"]["diagnostics"] = [
            {"message": "Missing timestamp records were skipped.", "count": 15877}
        ]
        rendered = render_report_markdown(report)
        self.assertIn("Missing timestamp records were skipped. ×15877", rendered)

    def test_card_caps_prevent_report_bloat(self):
        report = self._report()
        report["keep"] = report["keep"] * 4
        with self.assertRaisesRegex(ValueError, "keep must contain at most 3"):
            validate_report_model(report)

    def test_next_try_cannot_expand_into_a_list(self):
        report = self._report()
        report["next_try"] = [report["next_try"], copy.deepcopy(report["next_try"])]
        with self.assertRaisesRegex(ValueError, "one object or null"):
            validate_report_model(report)

    def test_scoring_keys_are_rejected(self):
        report = self._report()
        report["kpis"][0]["score"] = 92
        with self.assertRaisesRegex(ValueError, "must not score or rank"):
            validate_report_model(report)

    def test_missing_evidence_reference_is_rejected(self):
        report = self._report()
        report["next_try"]["evidence_ids"] = ["missing-evidence"]
        with self.assertRaisesRegex(ValueError, "missing evidence ids"):
            validate_report_model(report)


if __name__ == "__main__":
    unittest.main()
