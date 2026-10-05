import json
import tempfile
import unittest
from pathlib import Path

from agent_kpt.adapters.claude_code import _classify_error, _extract_error_text, ingest_paths


def write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")


class ClaudeCodeRealisticAdapterTests(unittest.TestCase):
    def test_split_assistant_blocks_are_one_call_and_resume_is_inherited(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            root = base / "root.jsonl"
            resume = base / "resume.jsonl"

            first = {
                "type": "user",
                "uuid": "u-shared",
                "timestamp": "2026-09-28T00:00:00Z",
                "version": "2.1.synthetic",
                "message": {"content": "<command-name>/review</command-name> SECRET"},
            }
            assistant_a = {
                "type": "assistant",
                "uuid": "a-one",
                "requestId": "req-1",
                "timestamp": "2026-09-28T00:00:01Z",
                "version": "2.1.synthetic",
                "message": {
                    "id": "msg-1",
                    "model": "claude-synthetic",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 1,
                        "cache_read_input_tokens": 90,
                    },
                    "content": [
                        {"type": "text", "text": "SECRET assistant text"},
                        {
                            "type": "tool_use",
                            "id": "skill-1",
                            "name": "Skill",
                            "input": {"skill": "advisor", "args": "SECRET"},
                        },
                    ],
                },
            }
            assistant_b = {
                "type": "assistant",
                "uuid": "a-two",
                "requestId": "req-1",
                "timestamp": "2026-09-28T00:00:02Z",
                "version": "2.1.synthetic",
                "message": {
                    "id": "msg-1",
                    "model": "claude-synthetic",
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 5,
                        "cache_read_input_tokens": 90,
                    },
                    "content": [{"type": "text", "text": "SECRET final block"}],
                },
            }
            write_jsonl(root, [first, assistant_a, assistant_b])
            write_jsonl(
                resume,
                [
                    first,
                    assistant_a,
                    {
                        "type": "tool_error",
                        "uuid": "err-new",
                        "timestamp": "2026-09-28T01:00:00Z",
                        "version": "2.1.synthetic",
                        "errorType": "path-quoting",
                        "tool": "Bash",
                        "message": "SECRET raw error",
                    },
                ],
            )

            result = ingest_paths([root, resume])
            sessions = {item["id"]: item for item in result["sessions"]}
            self.assertEqual(
                sessions["root"]["root_lineage_id"],
                sessions["resume"]["root_lineage_id"],
            )

            calls = [e for e in result["events"] if e["type"] == "model.call"]
            self.assertEqual(len(calls), 2)
            observed = next(e for e in calls if e["history_role"] == "observed")
            inherited = next(e for e in calls if e["history_role"] == "inherited")
            self.assertEqual(observed["payload"]["usage"]["output_tokens"], 5)
            self.assertIsNotNone(inherited["source_event_id"])

            skills = [e for e in result["events"] if e["type"] == "skill.invoke"]
            commands = [e for e in result["events"] if e["type"] == "command.invoke"]
            self.assertEqual(skills[0]["payload"]["name"], "advisor")
            self.assertEqual(commands[0]["payload"]["name"], "review")

            errors = [e for e in result["events"] if e["type"] == "error"]
            self.assertEqual(len(errors), 1)
            self.assertEqual(errors[0]["payload"]["category"], "path")
            self.assertEqual(errors[0]["payload"]["subtype"], "path-quoting")
            self.assertEqual(errors[0]["payload"]["tool"], "Bash")
            self.assertEqual(errors[0]["fingerprint"], "error:path-quoting")

            serialized = json.dumps(result, ensure_ascii=False)
            self.assertNotIn("SECRET", serialized)


    def test_429_inside_path_is_not_rate_limit(self):
        category, subtype = _classify_error(
            error_type=None,
            text="/tmp/build-4290/x: No such file or directory",
        )
        self.assertEqual((category, subtype), ("path", "file-not-found"))

    def test_http_429_is_rate_limit(self):
        category, subtype = _classify_error(
            error_type=None,
            text="HTTP status 429: request rejected",
        )
        self.assertEqual((category, subtype), ("rate-limit", "rate-limit"))

    def test_deep_error_payload_is_bounded(self):
        value = "leaf"
        for _ in range(100):
            value = {"message": [value]}
        extracted = _extract_error_text(value, max_depth=8)
        self.assertIsInstance(extracted, str)


if __name__ == "__main__":
    unittest.main()
