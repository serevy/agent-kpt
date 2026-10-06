import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from agent_kpt.review import apply_review_actions
from agent_kpt.workflow import (
    _summarize_diagnostics,
    build_analysis_packet,
    discover_claude_code_paths,
    ledger_status,
)


def write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")


class WorkflowTests(unittest.TestCase):
    def test_diagnostics_group_by_code_with_bounded_message_samples(self):
        diagnostics = [
            {
                "code": "unsupported-record-shape",
                "severity": "warning",
                "recoverable": True,
                "message": f"Unknown record type '{name}' was skipped.",
            }
            for name in ("a", "b", "c", "d", "e")
        ]
        summary = _summarize_diagnostics(diagnostics)
        self.assertEqual(len(summary), 1)
        self.assertEqual(summary[0]["count"], 5)
        self.assertEqual(len(summary[0]["messages"]), 3)
        self.assertEqual(
            summary[0]["messages"],
            [
                "Unknown record type 'a' was skipped.",
                "Unknown record type 'b' was skipped.",
                "Unknown record type 'c' was skipped.",
            ],
        )

    def test_discovery_packet_and_local_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "project"
            project.mkdir()
            claude_root = base / "claude-projects"
            state_home = base / "agent-kpt-home"

            main = claude_root / "encoded" / "session-a.jsonl"
            child = claude_root / "encoded" / "session-a" / "subagents" / "agent-a123456.jsonl"
            write_jsonl(
                main,
                [
                    {
                        "type": "user",
                        "uuid": "u-main",
                        "cwd": str(project),
                        "timestamp": "2026-09-28T00:00:00Z",
                        "version": "2.1.synthetic",
                        "message": {"content": "SECRET prompt"},
                    },
                    {
                        "type": "user",
                        "uuid": "missing-ts-1",
                        "cwd": str(project),
                        "message": {"content": "ignored"},
                    },
                    {
                        "type": "user",
                        "uuid": "missing-ts-2",
                        "cwd": str(project),
                        "message": {"content": "ignored"},
                    },
                    {
                        "type": "assistant",
                        "uuid": "a-main",
                        "requestId": "req-main",
                        "cwd": str(project),
                        "timestamp": "2026-09-28T00:00:01Z",
                        "version": "2.1.synthetic",
                        "message": {
                            "id": "msg-main",
                            "model": "claude-synthetic",
                            "usage": {
                                "input_tokens": 10,
                                "output_tokens": 5,
                                "cache_read_input_tokens": 90,
                            },
                            "content": [
                                {
                                    "type": "tool_use",
                                    "id": "agent-1",
                                    "name": "Agent",
                                    "input": {"subagent_type": "Explore", "prompt": "SECRET"},
                                }
                            ],
                        },
                    },
                    {
                        "type": "tool_error",
                        "uuid": "err-main",
                        "cwd": str(project),
                        "timestamp": "2026-09-28T00:00:03Z",
                        "version": "2.1.synthetic",
                        "tool": "Bash",
                        "message": "No such file or directory: SECRET/private/path",
                    },
                ],
            )
            write_jsonl(
                child,
                [
                    {
                        "type": "assistant",
                        "uuid": "a-child",
                        "requestId": "req-child",
                        "timestamp": "2026-09-28T00:00:02Z",
                        "version": "2.1.synthetic",
                        "message": {
                            "id": "msg-child",
                            "model": "claude-synthetic",
                            "usage": {"input_tokens": 2, "output_tokens": 2},
                            "content": [{"type": "text", "text": "SECRET child"}],
                        },
                    }
                ],
            )

            with patch.dict(os.environ, {"AGENT_KPT_HOME": str(state_home)}):
                paths = discover_claude_code_paths(project=project, root=claude_root)
                self.assertEqual(len(paths), 2)

                packet = build_analysis_packet(
                    "weekly",
                    project=project,
                    root=claude_root,
                    now=datetime(2026, 9, 29, tzinfo=timezone.utc),
                )
                self.assertEqual(packet["metrics"]["session_metrics"]["unique_root_lineages"], 1)
                self.assertEqual(packet["signals"]["subagent_types"]["Explore"], 1)
                self.assertEqual(packet["signals"]["tokens"]["cache_read_percent"], 88.2)
                self.assertFalse(packet["privacy"]["raw_prompt_text_persisted"])
                self.assertFalse(packet["privacy"]["raw_error_text_persisted"])
                serialized_packet = json.dumps(packet, ensure_ascii=False)
                self.assertNotIn("SECRET", serialized_packet)
                self.assertNotIn("user.message", {item["kind"] for item in packet["evidence"]})

                error_evidence = next(item for item in packet["evidence"] if item["kind"] == "error")
                self.assertEqual(error_evidence["category"], "path")
                self.assertEqual(error_evidence["subtype"], "file-not-found")
                self.assertEqual(error_evidence["tool"], "Bash")
                self.assertEqual(packet["signals"]["errors"]["groups"][0]["category"], "path")

                missing_ts = next(
                    item for item in packet["diagnostics"]
                    if item["code"] == "missing-event-timestamp"
                )
                self.assertEqual(missing_ts["count"], 2)

                evidence = next(
                    item for item in packet["evidence"] if item["kind"] == "subagent.invoke"
                )
                actions = {
                    "schema_version": "agent-kpt.review/v0alpha1",
                    "problems": [
                        {
                            "fingerprint": "workflow:parallel-agent-overuse",
                            "title": "Parallel agent usage worth watching",
                            "target_type": "workflow",
                            "evidence_ids": [evidence["id"]],
                            "next_try": {
                                "kind": "workflow",
                                "summary": "Try fewer parallel agents for bounded work",
                            },
                        }
                    ],
                }
                ledger = apply_review_actions(actions, packet, project=str(project))
                self.assertEqual(len(ledger["problems"]), 1)
                self.assertEqual(
                    ledger["problems"][0]["interventions"][0]["decision"],
                    "proposed",
                )

                status = ledger_status(project=project)
                self.assertEqual(status["ledger"]["problem_count"], 1)
                self.assertIsNotNone(status["last_report"])


if __name__ == "__main__":
    unittest.main()
