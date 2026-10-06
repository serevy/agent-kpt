import unittest

from agent_kpt.ledger import (
    add_intervention,
    assess_revalidation,
    new_ledger,
    retire_problem,
    set_intervention_decision,
    set_intervention_status,
    set_keep_state,
    stable_problem_id,
    upsert_problem,
)


class LedgerTests(unittest.TestCase):
    def _evidence(self, root, event_id, model="claude-synthetic"):
        return {
            "kind": "event",
            "root_lineage_id": root,
            "source": {
                "adapter": "claude-code-jsonl",
                "source": "synthetic.jsonl",
                "event_id": event_id,
            },
            "environment": {
                "model": model,
                "model_family": "claude",
                "harness": "claude-code",
                "harness_version": "2.1.synthetic",
                "adapter": "claude-code-jsonl",
                "adapter_version": "0.1.0",
                "runtime": "python-3.11",
                "os": "synthetic",
            },
        }

    def test_problem_id_is_stable_and_recurrence_is_lineage_aware(self):
        self.assertEqual(stable_problem_id("error:path-quoting"), stable_problem_id("error:path-quoting"))
        ledger = new_ledger()
        problem = upsert_problem(
            ledger,
            fingerprint="error:path-quoting",
            title="Path quoting failure",
            target_type="workflow",
            observed_at="2026-09-21T09:02:00Z",
            evidence=self._evidence("root-a", "event-a"),
        )
        upsert_problem(
            ledger,
            fingerprint="error:path-quoting",
            title="Path quoting failure",
            target_type="workflow",
            observed_at="2026-09-21T09:12:00Z",
            evidence=self._evidence("root-a", "event-a-fork"),
        )
        self.assertEqual(problem["lifecycle"], "observed")
        self.assertEqual(problem["independent_root_lineages"], 1)

        upsert_problem(
            ledger,
            fingerprint="error:path-quoting",
            title="Path quoting failure",
            target_type="workflow",
            observed_at="2026-09-28T09:00:00Z",
            evidence=self._evidence("root-b", "event-b"),
        )
        self.assertEqual(problem["lifecycle"], "recurring")
        self.assertEqual(problem["independent_root_lineages"], 2)
        self.assertEqual(problem["evidence"][0]["source"]["event_id"], "event-a")

    def test_reproposal_reuses_intervention_and_is_idempotent(self):
        ledger = new_ledger()
        problem = upsert_problem(
            ledger,
            fingerprint="error:path-quoting",
            title="Path quoting failure",
            target_type="workflow",
            observed_at="2026-09-21T09:02:00Z",
            evidence=self._evidence("root-a", "event-a"),
        )

        first = add_intervention(
            problem,
            kind="workflow",
            summary="Normalize   quoted paths before tool execution",
            proposed_at="2026-10-01T10:00:00Z",
        )
        replay = add_intervention(
            problem,
            kind="workflow",
            summary="normalize quoted paths before tool execution",
            proposed_at="2026-10-01T10:00:00Z",
        )

        self.assertEqual(len(problem["interventions"]), 1)
        self.assertEqual(replay["id"], first["id"])
        self.assertEqual(first["proposal_count"], 1)
        self.assertEqual(first["first_proposed_at"], "2026-10-01T10:00:00Z")
        self.assertEqual(first["last_proposed_at"], "2026-10-01T10:00:00Z")
        self.assertEqual(first["proposed_at"], "2026-10-01T10:00:00Z")

        later = add_intervention(
            problem,
            kind="workflow",
            summary="Normalize quoted paths before tool execution",
            proposed_at="2026-10-08T10:00:00Z",
        )
        self.assertEqual(len(problem["interventions"]), 1)
        self.assertEqual(later["id"], first["id"])
        self.assertEqual(later["proposal_count"], 2)
        self.assertEqual(later["first_proposed_at"], "2026-10-01T10:00:00Z")
        self.assertEqual(later["last_proposed_at"], "2026-10-08T10:00:00Z")
        self.assertEqual(later["proposed_at"], "2026-10-01T10:00:00Z")

        changed = add_intervention(
            problem,
            kind="workflow",
            summary="Use an absolute path preflight instead",
            proposed_at="2026-10-08T10:00:00Z",
        )
        self.assertNotEqual(changed["id"], first["id"])
        self.assertEqual(len(problem["interventions"]), 2)

    def test_reproposal_preserves_decision_status_and_legacy_id(self):
        for decision in ("accepted", "rejected", "deferred"):
            with self.subTest(decision=decision):
                ledger = new_ledger()
                problem = upsert_problem(
                    ledger,
                    fingerprint=f"error:path-quoting:{decision}",
                    title="Path quoting failure",
                    target_type="workflow",
                    observed_at="2026-09-21T09:02:00Z",
                    evidence=self._evidence("root-a", f"event-{decision}"),
                )
                intervention = add_intervention(
                    problem,
                    kind="workflow",
                    summary="Normalize quoted paths",
                    proposed_at="2026-10-01T10:00:00Z",
                )
                set_intervention_decision(problem, intervention["id"], decision)
                if decision == "accepted":
                    set_intervention_status(
                        problem,
                        intervention["id"],
                        "applied",
                        at="2026-10-01T11:00:00Z",
                    )

                repeated = add_intervention(
                    problem,
                    kind="workflow",
                    summary=" normalize   quoted paths ",
                    proposed_at="2026-10-08T10:00:00Z",
                    decision="proposed",
                )
                self.assertEqual(repeated["decision"], decision)
                self.assertEqual(
                    repeated["status"],
                    "applied" if decision == "accepted" else "not-started",
                )
                self.assertEqual(repeated["proposal_count"], 2)
                self.assertEqual(len(problem["interventions"]), 1)

        ledger = new_ledger()
        problem = upsert_problem(
            ledger,
            fingerprint="error:legacy-intervention",
            title="Legacy intervention identity",
            target_type="workflow",
            observed_at="2026-09-21T09:02:00Z",
            evidence=self._evidence("root-a", "legacy-event"),
        )
        legacy = {
            "id": "intervention-legacy123456",
            "kind": "workflow",
            "summary": "Normalize quoted paths",
            "decision": "rejected",
            "status": "not-started",
            "proposed_at": "2026-10-01T10:00:00Z",
            "applied_at": None,
            "validated_at": None,
            "retired_at": None,
            "validated_environment": {},
            "retire_reason": None,
        }
        problem["interventions"].append(legacy)

        repeated = add_intervention(
            problem,
            kind="workflow",
            summary="normalize quoted paths",
            proposed_at="2026-10-08T10:00:00Z",
        )
        self.assertEqual(repeated["id"], "intervention-legacy123456")
        self.assertEqual(repeated["decision"], "rejected")
        self.assertEqual(repeated["proposal_count"], 2)
        self.assertEqual(repeated["first_proposed_at"], "2026-10-01T10:00:00Z")
        self.assertEqual(repeated["last_proposed_at"], "2026-10-08T10:00:00Z")
        self.assertEqual(len(problem["interventions"]), 1)

    def test_human_decision_intervention_keep_and_graduation(self):
        ledger = new_ledger()
        problem = upsert_problem(
            ledger,
            fingerprint="error:path-quoting",
            title="Path quoting failure",
            target_type="workflow",
            observed_at="2026-09-21T09:02:00Z",
            evidence=self._evidence("root-a", "event-a"),
        )
        intervention = add_intervention(
            problem,
            kind="skill-instruction",
            summary="Add path quoting preflight guidance",
            proposed_at="2026-09-28T10:00:00Z",
        )
        self.assertEqual(intervention["decision"], "proposed")
        set_intervention_decision(problem, intervention["id"], "accepted")
        self.assertEqual(problem["lifecycle"], "try-proposed")
        set_intervention_status(problem, intervention["id"], "applied", at="2026-09-28T10:05:00Z")
        self.assertEqual(problem["lifecycle"], "intervention-applied")
        set_intervention_status(
            problem,
            intervention["id"],
            "effective",
            at="2026-10-05T10:00:00Z",
            environment=self._evidence("root-a", "x")["environment"],
        )
        self.assertEqual(problem["keep"]["state"], "reinforcing")
        set_keep_state(problem, "habituated", at="2026-10-19T10:00:00Z")
        self.assertEqual(problem["lifecycle"], "habituated")
        set_keep_state(problem, "graduated", at="2026-11-02T10:00:00Z")
        self.assertEqual(problem["lifecycle"], "graduated")

    def test_environment_change_requires_revalidation(self):
        ledger = new_ledger()
        problem = upsert_problem(
            ledger,
            fingerprint="error:path-quoting",
            title="Path quoting failure",
            target_type="workflow",
            observed_at="2026-09-21T09:02:00Z",
            evidence=self._evidence("root-a", "event-a"),
        )
        intervention = add_intervention(
            problem,
            kind="workflow",
            summary="Normalize quoted paths before tool execution",
            proposed_at="2026-09-28T10:00:00Z",
            decision="accepted",
        )
        baseline = self._evidence("root-a", "x")["environment"]
        set_intervention_status(problem, intervention["id"], "effective", at="2026-10-05T10:00:00Z", environment=baseline)
        self.assertEqual(assess_revalidation(problem, baseline)["state"], "current")
        changed = dict(baseline)
        changed["model"] = "claude-synthetic-next"
        result = assess_revalidation(problem, changed)
        self.assertEqual(result["state"], "needs-revalidation")
        self.assertEqual(result["reasons"][0]["field"], "model")

    def test_retirement_preserves_history(self):
        ledger = new_ledger()
        problem = upsert_problem(
            ledger,
            fingerprint="error:path-quoting",
            title="Path quoting failure",
            target_type="workflow",
            observed_at="2026-09-21T09:02:00Z",
            evidence=self._evidence("root-a", "event-a"),
        )
        intervention = add_intervention(
            problem,
            kind="workflow",
            summary="Temporary quoting workaround",
            proposed_at="2026-09-28T10:00:00Z",
            decision="accepted",
        )
        set_intervention_status(
            problem,
            intervention["id"],
            "retired",
            at="2026-11-10T10:00:00Z",
            retire_reason="Harness update removed the workaround need",
        )
        self.assertEqual(intervention["status"], "retired")
        self.assertIn("Harness update", intervention["retire_reason"])
        retire_problem(problem, reason="No longer observed after upstream fix", at="2026-11-17T10:00:00Z")
        self.assertEqual(problem["lifecycle"], "retired")
        self.assertEqual(len(problem["evidence"]), 1)


if __name__ == "__main__":
    unittest.main()
