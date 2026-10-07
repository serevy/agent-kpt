import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from agent_kpt.review import apply_review_actions
from agent_kpt.workflow import (
    _signals,
    _summarize_diagnostics,
    build_analysis_packet,
    discover_claude_code_paths,
    ledger_status,
)


def write_jsonl(path: Path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(item) for item in records) + "\n", encoding="utf-8")


class WorkflowTests(unittest.TestCase):
    def test_agent_kpt_self_invocation_is_excluded_from_skill_stats(self):
        result = {
            "sessions": [],
            "events": [
                {
                    "type": "skill.invoke",
                    "history_role": "observed",
                    "payload": {"name": "agent-kpt"},
                },
                {
                    "type": "skill.invoke",
                    "history_role": "observed",
                    "payload": {"name": "plugin:agent-kpt"},
                },
                {
                    "type": "skill.invoke",
                    "history_role": "observed",
                    "payload": {"name": "namespace/agent-kpt"},
                },
                {
                    "type": "skill.invoke",
                    "history_role": "observed",
                    "payload": {"name": "advisor"},
                },
            ],
        }
        signals = _signals(result)
        self.assertEqual(signals["skill_invocations"], {"advisor": 1})
        self.assertEqual(signals["event_counts"]["skill.invoke"], 4)

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

    def test_apply_review_reuses_same_intervention_across_weeks(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            project = base / "project"
            state_home = base / "agent-kpt-home"
            project.mkdir()

            actions = {
                "schema_version": "agent-kpt.review/v0alpha1",
                "problems": [
                    {
                        "fingerprint": "error:path:file-not-found",
                        "title": "Path failures recur",
                        "target_type": "workflow",
                        "evidence_ids": ["evidence-path"],
                        "next_try": {
                            "kind": "workflow",
                            "summary": "Check path existence before execution",
                        },
                    }
                ],
            }
            packet = {
                "period": {"end": "2026-10-01T10:00:00Z"},
                "evidence": [
                    {
                        "id": "evidence-path",
                        "kind": "error",
                        "observed_at": "2026-09-30T10:00:00Z",
                        "root_lineage_id": "root-a",
                        "source": "session-a.jsonl",
                        "source_event_id": "event-a",
                        "environment": {},
                    }
                ],
            }

            with patch.dict(os.environ, {"AGENT_KPT_HOME": str(state_home)}):
                first = apply_review_actions(actions, packet, project=str(project))
                first_intervention = first["problems"][0]["interventions"][0]
                self.assertEqual(len(first["problems"][0]["interventions"]), 1)
                self.assertEqual(first_intervention["proposal_count"], 1)

                replay = apply_review_actions(actions, packet, project=str(project))
                replay_intervention = replay["problems"][0]["interventions"][0]
                self.assertEqual(len(replay["problems"][0]["interventions"]), 1)
                self.assertEqual(replay_intervention["proposal_count"], 1)

                next_week = dict(packet)
                next_week["period"] = {"end": "2026-10-08T10:00:00Z"}
                second = apply_review_actions(actions, next_week, project=str(project))
                second_intervention = second["problems"][0]["interventions"][0]
                self.assertEqual(len(second["problems"][0]["interventions"]), 1)
                self.assertEqual(second_intervention["proposal_count"], 2)
                self.assertEqual(
                    second_intervention["last_proposed_at"],
                    "2026-10-08T10:00:00Z",
                )

                status = ledger_status(project=project)
                self.assertEqual(status["ledger"]["intervention_count"], 1)

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
                self.assertEqual(error_evidence["outcome"], "failure")
                self.assertEqual(error_evidence["rule_scope"], "common")
                self.assertEqual(error_evidence["rule_id"], "common.path.file-not-found")
                self.assertEqual(error_evidence["ruleset_version"], "common-v0alpha1")
                self.assertEqual(error_evidence["provider_version"], "2.1.synthetic")
                self.assertEqual(packet["signals"]["errors"]["groups"][0]["category"], "path")
                self.assertEqual(packet["signals"]["errors"]["by_outcome"]["failure"], 1)

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
