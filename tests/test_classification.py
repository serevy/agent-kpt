import json
import tempfile
import unittest
from pathlib import Path

from agent_kpt.adapters.claude_code import ingest_paths
from agent_kpt.adapters.claude_code_classifier import classify_claude_code
from agent_kpt.classification import (
    classify_common,
    classify_user,
    load_user_rules,
    unknown_classification,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "classifier-v0alpha1"
EVAL_FIXTURE = FIXTURE_DIR / "eval.json"
USER_RULES = FIXTURE_DIR / "user-rules.json"


def write_jsonl(path: Path, records) -> None:
    path.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )


class ClassificationTests(unittest.TestCase):
    def _pipeline(self, *, error_type, text, tool=None, user_rules=None):
        return (
            classify_common(error_type=error_type, text=text)
            or classify_claude_code(error_type=error_type, text=text)
            or classify_user(user_rules, tool=tool, text=text)
            or unknown_classification()
        )

    def test_versioned_eval_fixture_and_near_misses(self):
        fixture = json.loads(EVAL_FIXTURE.read_text(encoding="utf-8"))
        user_rules, diagnostics = load_user_rules(USER_RULES)
        self.assertEqual(diagnostics, [])
        self.assertIsNotNone(user_rules)

        for case in fixture["cases"]:
            with self.subTest(case=case["id"]):
                layer = case["layer"]
                kwargs = {
                    "error_type": case.get("error_type"),
                    "text": case["text"],
                }
                if layer == "common":
                    result = classify_common(**kwargs)
                elif layer == "provider":
                    result = classify_claude_code(**kwargs)
                elif layer == "user":
                    result = classify_user(
                        user_rules,
                        tool=case.get("tool"),
                        text=case["text"],
                    )
                else:
                    result = self._pipeline(
                        **kwargs,
                        tool=case.get("tool"),
                        user_rules=user_rules,
                    )

                self.assertIsNotNone(result)
                expected = case["expected"]
                self.assertEqual(result.category, expected["category"])
                self.assertEqual(result.subtype, expected["subtype"])
                self.assertEqual(result.outcome, expected["outcome"])
                self.assertEqual(result.rule_id, expected["rule_id"])

    def test_common_then_provider_then_user_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            session = base / "session.jsonl"
            rules = base / "rules.json"
            rules.write_text(
                json.dumps(
                    {
                        "schema_version": "agent-kpt.classifier-rules/v0alpha1",
                        "ruleset_version": "precedence-v1",
                        "rules": [
                            {
                                "id": "user.override.path",
                                "tool": "Bash",
                                "contains_any": ["No such file or directory"],
                                "category": "custom",
                                "subtype": "path-override",
                                "outcome": "warning",
                            },
                            {
                                "id": "user.override.provider",
                                "tool": "Edit",
                                "contains_any": ["File has not been read yet"],
                                "category": "custom",
                                "subtype": "provider-override",
                                "outcome": "warning",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            write_jsonl(
                session,
                [
                    {
                        "type": "tool_error",
                        "uuid": "err-common",
                        "timestamp": "2026-10-01T00:00:00Z",
                        "version": "2.1.synthetic",
                        "tool": "Bash",
                        "message": "No such file or directory: /tmp/missing",
                    },
                    {
                        "type": "tool_error",
                        "uuid": "err-provider",
                        "timestamp": "2026-10-01T00:00:01Z",
                        "version": "2.1.synthetic",
                        "tool": "Edit",
                        "message": "File has not been read yet. Read it before editing.",
                    },
                    {
                        "type": "tool_error",
                        "uuid": "err-user",
                        "timestamp": "2026-10-01T00:00:02Z",
                        "version": "2.1.synthetic",
                        "tool": "Bash",
                        "message": "Unity is compiling scripts; wait and retry.",
                    },
                ],
            )

            fixture_rules = json.loads(USER_RULES.read_text(encoding="utf-8"))
            local_rules = json.loads(rules.read_text(encoding="utf-8"))
            local_rules["rules"].append(fixture_rules["rules"][0])
            rules.write_text(json.dumps(local_rules), encoding="utf-8")

            result = ingest_paths([session], classifier_rules=rules)
            errors = {event["id"]: event for event in result["events"] if event["type"] == "error"}
            payloads = [event["payload"] for event in errors.values()]

            common = next(p for p in payloads if p["rule_id"] == "common.path.file-not-found")
            self.assertEqual(common["rule_scope"], "common")
            self.assertEqual(common["outcome"], "failure")

            provider = next(p for p in payloads if p["rule_id"] == "claude-code.file-not-read")
            self.assertEqual(provider["rule_scope"], "provider")
            self.assertEqual(provider["outcome"], "blocked")

            user = next(p for p in payloads if p["rule_id"] == "user.unity.compiling")
            self.assertEqual(user["rule_scope"], "user")
            self.assertEqual(user["outcome"], "waiting")

            serialized = json.dumps(result, ensure_ascii=False)
            self.assertNotIn("Unity is compiling scripts", serialized)
            self.assertNotIn("File has not been read yet", serialized)

    def test_invalid_user_rule_is_fail_soft(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.json"
            path.write_text(
                json.dumps(
                    {
                        "schema_version": "agent-kpt.classifier-rules/v0alpha1",
                        "ruleset_version": "broken-v1",
                        "rules": [
                            {
                                "id": "Bad Rule Id",
                                "contains_any": ["bad"],
                                "category": "custom",
                                "subtype": "bad",
                                "outcome": "failure",
                            },
                            {
                                "id": "user.valid",
                                "contains_any": ["known local state"],
                                "category": "tool-state",
                                "subtype": "known",
                                "outcome": "waiting",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            ruleset, diagnostics = load_user_rules(path)
            self.assertIsNotNone(ruleset)
            self.assertEqual(len(ruleset.rules), 1)
            self.assertEqual(ruleset.rules[0].rule_id, "user.valid")
            self.assertEqual(diagnostics[0]["code"], "classifier-rule-invalid")


if __name__ == "__main__":
    unittest.main()
