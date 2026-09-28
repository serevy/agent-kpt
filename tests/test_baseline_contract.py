import json
import unittest
from pathlib import Path

from agent_kpt.adapters.claude_code import ingest_paths, load_lineage_map
from agent_kpt.metrics import compute_metrics

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_FIXTURE = ROOT / "fixtures" / "claude-code-v0alpha1"
CORE_FIXTURE = ROOT / "fixtures" / "core-v0alpha1" / "expected-metrics.json"


class BaselineContractTests(unittest.TestCase):
    def test_python_reference_explains_core_golden_fixture(self):
        result = ingest_paths(
            [
                CLAUDE_FIXTURE / "session-a.jsonl",
                CLAUDE_FIXTURE / "session-a-fork-1.jsonl",
                CLAUDE_FIXTURE / "session-b.jsonl",
            ],
            lineage_map=load_lineage_map(CLAUDE_FIXTURE / "lineage.json"),
        )
        actual = compute_metrics(result)
        golden = json.loads(CORE_FIXTURE.read_text(encoding="utf-8"))

        for key in ("session_metrics", "recurrence", "model_calls", "adapter_diagnostics"):
            self.assertEqual(actual[key], golden[key])

        delta = golden["baseline_delta"]
        self.assertEqual(
            actual["recurrence"]["error:path-quoting"]["raw_occurrences"],
            delta["raw_path_error_observations"],
        )
        self.assertEqual(
            actual["recurrence"]["error:path-quoting"]["unique_root_lineages"],
            delta["independent_path_error_lineages"],
        )


if __name__ == "__main__":
    unittest.main()
