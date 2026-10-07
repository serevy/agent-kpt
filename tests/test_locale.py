import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agent_kpt.cli import main
from agent_kpt.locale import normalize_locale, resolve_report_locale
from agent_kpt.report import render_report_html, render_report_markdown
from agent_kpt.workflow import build_analysis_packet


class ReportLocaleTests(unittest.TestCase):
    def test_precedence_and_normalization(self):
        with patch.dict(os.environ, {"AGENT_KPT_LOCALE": "en_GB"}):
            self.assertEqual(resolve_report_locale("ja", "fr"), ("ja-JP", "explicit"))
            self.assertEqual(resolve_report_locale(None, "ja"), ("en-GB", "environment"))
        with patch.dict(os.environ, {"AGENT_KPT_LOCALE": " "}):
            self.assertEqual(resolve_report_locale(None, "ja_jp"), ("ja-JP", "conversation"))
            self.assertEqual(resolve_report_locale(), ("en-US", "default"))
        self.assertEqual(normalize_locale("ZH_hant_tw"), "zh-Hant-TW")
        self.assertEqual(normalize_locale("en-US-u-ca-gregory"), "en-US-u-ca-gregory")

    def test_malformed_selected_values_fail_without_falling_back(self):
        with patch.dict(os.environ, {"AGENT_KPT_LOCALE": "not a tag"}):
            with self.assertRaises(ValueError):
                resolve_report_locale(None, "ja")
            self.assertEqual(resolve_report_locale("en"), ("en-US", "explicit"))
        for value in ("", "   ", "ja--JP", "ja/JP", "日本語", "en.UTF-8", 42):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_locale(value)

    def test_packet_cli_and_persistence_use_the_same_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with patch.dict(os.environ, {"AGENT_KPT_HOME": str(base / "state"), "AGENT_KPT_LOCALE": "en"}):
                for mode in ("weekly", "monthly"):
                    output = base / f"{mode}.json"
                    self.assertEqual(main([
                        "workflow", "prepare", mode, "--project", tmp,
                        "--claude-root", str(base / "missing"),
                        "--locale", "ja", "--conversation-locale", "fr",
                        "-o", str(output),
                    ]), 0)
                    packet = json.loads(output.read_text(encoding="utf-8"))
                    self.assertEqual(packet["report_contract"]["locale"], "ja-JP")
                    self.assertEqual(packet["report_contract"]["locale_source"], "explicit")
                saved = list((base / "state").rglob("last-packet.json"))
                self.assertEqual(len(saved), 1)
                self.assertEqual(json.loads(saved[0].read_text(encoding="utf-8")), packet)

    def test_fallback_ignores_host_tool_and_readme_language(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {
            "AGENT_KPT_HOME": tmp, "AGENT_KPT_LOCALE": "",
            "LANG": "ja_JP.UTF-8", "LC_ALL": "ja_JP.UTF-8",
        }):
            packet = build_analysis_packet("weekly", project=tmp, root=Path(tmp) / "missing", persist=False)
            self.assertEqual(packet["report_contract"]["locale"], "en-US")
            self.assertEqual(packet["report_contract"]["locale_source"], "default")
            packet = build_analysis_packet("weekly", project=tmp, root=Path(tmp) / "missing", conversation_locale="ja", persist=False)
            self.assertEqual(packet["report_contract"]["locale"], "ja-JP")

    def test_invalid_cli_locale_returns_actionable_error_before_output(self):
        stderr, stdout = io.StringIO(), io.StringIO()
        with redirect_stderr(stderr), redirect_stdout(stdout):
            result = main(["workflow", "prepare", "weekly", "--locale", "not a tag", "--no-persist"])
        self.assertEqual(result, 2)
        self.assertIn("report locale", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")

    def test_renderer_language_labels_do_not_translate_prose(self):
        fixture = Path(__file__).resolve().parents[1] / "fixtures/report-v0alpha1/report-ja.json"
        view = json.loads(fixture.read_text(encoding="utf-8"))
        for locale, label in (("ja-JP", "ぱっと見る"), ("en-US", "At a glance"), ("fr-FR", "At a glance")):
            with self.subTest(locale=locale):
                view["locale"] = locale
                for render in (render_report_html, render_report_markdown):
                    result = render(view)
                    self.assertIn(label, result)
                    self.assertIn(view["headline"], result)


if __name__ == "__main__":
    unittest.main()
