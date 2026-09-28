import json
import unittest
from pathlib import Path

from agent_kpt.adapters.claude_code import ingest_paths, load_lineage_map
from agent_kpt.metrics import compute_metrics, render_metrics_markdown

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "claude-code-v0alpha1"


class MetricsTests(unittest.TestCase):
    def test_fixture_matches_expected_metrics(self):
        result = ingest_paths(
            [
                FIXTURE / "session-a.jsonl",
                FIXTURE / "session-a-fork-1.jsonl",
                FIXTURE / "session-b.jsonl",
            ],
            lineage_map=load_lineage_map(FIXTURE / "lineage.json"),
        )
        actual = compute_metrics(result)
        expected = json.loads((FIXTURE / "expected-metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(actual, expected)

    def test_markdown_exposes_raw_and_deduplicated_views(self):
        result = ingest_paths(
            [
                FIXTURE / "session-a.jsonl",
                FIXTURE / "session-a-fork-1.jsonl",
                FIXTURE / "session-b.jsonl",
            ],
            lineage_map=load_lineage_map(FIXTURE / "lineage.json"),
        )
        markdown = render_metrics_markdown(compute_metrics(result))
        self.assertIn("Raw occurrences | 2", markdown)
        self.assertIn("Unique root lineages | 1", markdown)
        self.assertIn("Actual new calls | 2", markdown)
        self.assertIn("Inherited history events | 1", markdown)


if __name__ == "__main__":
    unittest.main()
