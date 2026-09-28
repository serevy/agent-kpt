import json
import unittest
from pathlib import Path

from agent_kpt.adapters.claude_code import ingest_paths, load_lineage_map

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "fixtures" / "claude-code-v0alpha1"


class ClaudeCodeAdapterTests(unittest.TestCase):
    def _result(self):
        lineage = load_lineage_map(FIXTURE / "lineage.json")
        return ingest_paths(
            [
                FIXTURE / "session-a.jsonl",
                FIXTURE / "session-a-fork-1.jsonl",
                FIXTURE / "session-b.jsonl",
            ],
            lineage_map=lineage,
        )

    def test_lineage_and_fail_soft(self):
        result = self._result()
        sessions = {session["id"]: session for session in result["sessions"]}
        self.assertEqual(sessions["session-a-fork-1"]["root_lineage_id"], "root-a")
        self.assertEqual(sessions["session-a-fork-1"]["parent_session_id"], "session-a")
        self.assertEqual([d["code"] for d in result["diagnostics"]], ["unsupported-record-shape"])
        self.assertTrue(result["diagnostics"][0]["recoverable"])

    def test_duplicate_model_call_becomes_inherited(self):
        result = self._result()
        calls = [event for event in result["events"] if event["type"] == "model.call"]
        self.assertEqual(len(calls), 3)
        roles = [event["history_role"] for event in calls]
        self.assertEqual(roles.count("observed"), 2)
        self.assertEqual(roles.count("inherited"), 1)
        inherited = next(event for event in calls if event["history_role"] == "inherited")
        self.assertIsNotNone(inherited["source_event_id"])

    def test_raw_private_content_is_not_copied(self):
        serialized = json.dumps(self._result(), ensure_ascii=False)
        self.assertNotIn("SECRET", serialized)
        self.assertNotIn("echo SECRET", serialized)
        self.assertNotIn("raw error details", serialized)


if __name__ == "__main__":
    unittest.main()
