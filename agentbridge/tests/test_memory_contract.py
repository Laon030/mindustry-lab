"""Adversarial contract probes. Scripted policies below are NOT game agents."""

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from research.memory_contract import (
    GOAL, MAX_BYTES, VERSION, MemoryStoreV2, Settings, canonical, decide_once,
    assert_memory_only_difference, initial_memory, observation, request, validate_decision, validate_memory,
)


ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "experiments/memory_sensitive_v2.json").read_text())


def memory_from_events(events):
    # Test fixture only: actual memory writing belongs to the model, not Python.
    memory = initial_memory()
    memory["relevant_events"] = deepcopy(events)
    return memory


def proposal(intent, target=None):
    return {"intent": intent, "target": target, "reason": "diagnostic policy choice"}


def score(history, decision):
    # Oracle confined to test/evaluator, never consulted by validator or policy.
    return history["outcome_utility"][f"{decision['intent']}:{decision['target'] or ''}"]


class PublicOnlyProbe:
    """A transparent sensitivity witness, not evidence of LLM competence."""

    def decide(self, context):
        memory = context["scratchpad"]
        events = memory["relevant_events"] if memory else []
        surveys = [e for e in events if e["predicate"] == "survey_copper_tiles"]
        failures = [e for e in events if e["predicate"] == "trial_failure"]
        if surveys:
            chosen = proposal("choose_candidate", max(surveys, key=lambda e: e["value"])["subject"])
        elif failures:
            structural = "disconnected" in failures[0]["value"]
            chosen = proposal("alternative", "route-b") if structural else proposal("retry", "route-a")
        else:
            chosen = proposal("inspect", context["observation"]["candidates"][0]["id"])
        updated = deepcopy(memory)
        if updated is not None:
            updated["revision"] += 1
            updated["next_intended_step"] = chosen["intent"]
        return {"decision": chosen, "scratchpad": updated}

    def close(self):
        pass


class ContractTests(unittest.TestCase):
    def test_versioned_spec_and_common_settings(self):
        self.assertEqual(VERSION, SPEC["benchmark_id"])
        self.assertEqual(asdict(Settings()), SPEC["public_contract"])
        self.assertEqual(2, SPEC["benchmark_version"])
        self.assertEqual(2, len(SPEC["cases"]))
        self.assertNotEqual(SPEC["benchmark_id"], json.loads((ROOT / SPEC["negative_control"]).read_text())["benchmark_id"])

    def test_same_observation_and_different_preferred_next_decisions(self):
        for case in SPEC["cases"]:
            first, second = case["histories"]
            self.assertNotEqual(first["events"], second["events"])
            self.assertNotEqual(first["expected_preference"], second["expected_preference"])
            # Labels and private history must not change any part of the request.
            inputs = [request(Settings(), {**case["current_observation"], "history": h,
                                           "phase": h["id"], "oracle": h["outcome_utility"]}, None)
                      for h in (first, second)]
            self.assertEqual(canonical(inputs[0]), canonical(inputs[1]))
            for history, other in ((first, second), (second, first)):
                preferred = proposal(**history["expected_preference"])
                alternative = proposal(**other["expected_preference"])
                self.assertGreater(score(history, preferred), score(history, alternative))

    def test_validator_accepts_both_strategies_in_both_histories(self):
        for case in SPEC["cases"]:
            for history in case["histories"]:
                raw = {**case["current_observation"], "history": history}
                for other in case["histories"]:
                    choice = proposal(**other["expected_preference"])
                    self.assertEqual(choice, validate_decision(choice, raw))
                for intent in ("wait", "abandon"):
                    self.assertEqual(intent, validate_decision(proposal(intent), raw)["intent"])
                for candidate in raw["candidates"]:
                    for intent in ("inspect", "choose_candidate", "retry", "alternative"):
                        validate_decision(proposal(intent, candidate["id"]), raw)

    def test_none_correct_and_incorrect_memory_have_distinct_visible_inputs(self):
        for case in SPEC["cases"]:
            for index, history in enumerate(case["histories"]):
                other = case["histories"][1 - index]
                variants = (None, memory_from_events(history["events"]), memory_from_events(other["events"]))
                traces = [decide_once(PublicOnlyProbe, Settings(), case["current_observation"], m) for m in variants]
                self.assertEqual(3, len({t["request_sha256"] for t in traces}))
                shared = []
                for trace in traces:
                    self.assertNotIn("expected_preference", canonical(trace["request"]).decode())
                    common = deepcopy(trace["request"])
                    common.pop("scratchpad")
                    shared.append(common)
                self.assertEqual(shared[0], shared[1])
                self.assertEqual(shared[1], shared[2])
                assert_memory_only_difference(traces[0]["request"], traces[1]["request"])
                assert_memory_only_difference(traces[1]["request"], traces[2]["request"])
                self.assertEqual("inspect", traces[0]["decision"]["intent"])
                self.assertEqual(history["expected_preference"], {k: traces[1]["decision"][k] for k in ("intent", "target")})
                self.assertGreater(score(history, traces[1]["decision"]), score(history, traces[2]["decision"]))
                # Incorrect memories remain legal; Python must not oracle-correct them.
                validate_memory(traces[2]["scratchpad"])

    def test_current_state_only_cannot_separate_paired_histories(self):
        for case in SPEC["cases"]:
            public = [observation({**case["current_observation"], "history": h}) for h in case["histories"]]
            self.assertEqual(public[0], public[1])
            candidates = public[0]["candidates"]
            choices = [proposal(intent, candidate["id"]) for candidate in candidates
                       for intent in ("choose_candidate", "retry", "alternative", "inspect")]
            choices += [proposal("wait"), proposal("abandon")]
            # No fixed current-state choice is optimal in both hidden histories.
            for choice in choices:
                optimal = [score(h, choice) == max(h["outcome_utility"].values()) for h in case["histories"]]
                self.assertFalse(all(optimal))

    def test_leakage_canaries_and_history_dependent_order_removed(self):
        case = SPEC["cases"][0]
        base = deepcopy(case["current_observation"])
        poisoned = deepcopy(base)
        for key in ("phase", "summary", "previousDecision", "tasks", "blocked", "plan",
                    "completed", "failures", "expected_preference", "history", "memory_label"):
            poisoned[key] = "CANARY_strategy_from_history"
        poisoned["resources"]["previous_copper"] = "CANARY"
        poisoned["executor"]["last_failure"] = "CANARY"
        for candidate in poisoned["candidates"]:
            candidate["score"] = "CANARY"
            candidate["preferred"] = True
        poisoned["candidates"].reverse()
        self.assertEqual(request(Settings(), base, None), request(Settings(), poisoned, None))
        self.assertNotIn("CANARY", canonical(request(Settings(), poisoned, None)).decode())

    def test_expired_event_cannot_masquerade_as_current(self):
        current = deepcopy(SPEC["cases"][0]["current_observation"])
        current["visible_events"] = SPEC["cases"][0]["histories"][0]["events"]
        with self.assertRaisesRegex(ValueError, "historical"):
            observation(current)

    def test_current_event_cannot_be_python_summary_or_ranking(self):
        current = deepcopy(SPEC["cases"][0]["current_observation"])
        for predicate in ("phase", "recommended_strategy", "previous_decision"):
            current["visible_events"] = [{"subject": "site-a", "predicate": predicate,
                                          "value": "choose site-a", "observed_tick": 100}]
            with self.assertRaisesRegex(ValueError, "sensor event"):
                observation(current)

    def test_pairing_rejects_model_prompt_observation_executor_and_budget_changes(self):
        current = SPEC["cases"][0]["current_observation"]
        baseline = request(Settings(), current, None)
        for field, value in (("model", "other"), ("generation", "other"), ("executor", "other"),
                             ("action_budget", 5), ("timeout_seconds", 61)):
            changed = deepcopy(baseline)
            changed["settings"][field] = value
            with self.assertRaisesRegex(ValueError, "outside scratchpad"):
                assert_memory_only_difference(baseline, changed)
        for field in ("common_prompt", "observation", "memory_schema", "goal"):
            changed = deepcopy(baseline)
            changed[field] = "different"
            with self.assertRaises(ValueError):
                assert_memory_only_difference(baseline, changed)

    def test_no_hidden_policy_state_across_calls_or_provider_mutation(self):
        instances = []

        class MutatingProvider:
            def __init__(self):
                self.calls = 0
                self.closed = False
                instances.append(self)

            def decide(self, context):
                self.calls += 1
                context["observation"]["resources"]["copper"] = 999
                return {"decision": proposal("wait"), "scratchpad": None}

            def close(self):
                self.closed = True

        current = deepcopy(SPEC["cases"][0]["current_observation"])
        one = decide_once(MutatingProvider, Settings(), current)
        two = decide_once(MutatingProvider, Settings(), current)
        self.assertEqual(one, two)
        self.assertEqual(60, current["resources"]["copper"])
        self.assertEqual(60, one["request"]["observation"]["resources"]["copper"])
        self.assertTrue(all(p.calls == 1 and p.closed for p in instances))
        self.assertFalse(one["context_loss"])

    def test_no_memory_cannot_return_hidden_scratchpad(self):
        class BadProvider(PublicOnlyProbe):
            def decide(self, context):
                return {"decision": proposal("wait"), "scratchpad": initial_memory()}
        with self.assertRaisesRegex(ValueError, "cannot retain"):
            decide_once(BadProvider, Settings(), SPEC["cases"][0]["current_observation"])

    def test_illegal_values_rejected_without_strategy_fallback(self):
        current = deepcopy(SPEC["cases"][0]["current_observation"])
        for bad in (proposal("attack", "site-a"), proposal("retry", "unknown"), proposal("wait", "site-a")):
            with self.assertRaises(ValueError):
                validate_decision(bad, current)
        for change in ("unaffordable", "unavailable", "busy"):
            bad = deepcopy(current)
            if change == "unaffordable": bad["resources"]["copper"] = 0
            if change == "unavailable": bad["candidates"][0]["legal"] = False
            if change == "busy": bad["executor"]["busy"] = True
            with self.assertRaises(ValueError):
                validate_decision(proposal("retry", "site-a"), bad)


class MemorySchemaTests(unittest.TestCase):
    def test_all_requested_fields_bounded_and_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStoreV2(Path(directory) / "memory.json")
            original = store.initialize()
            updated = deepcopy(original)
            updated.update(revision=1, selected_subgoal="recover copper flow",
                           relevant_events=SPEC["cases"][1]["histories"][0]["events"],
                           completed_milestones=["survey completed"],
                           failures=[{"target": "route-a", "cause": "builder interruption",
                                      "attempted_alternatives": ["route-b"]}],
                           unresolved_information=["current remote flow unknown"],
                           next_intended_step="consider retry or inspect")
            self.assertEqual(updated, store.update(updated))
            self.assertEqual(updated, MemoryStoreV2(store.path).load())
            self.assertLessEqual(store.size_bytes(), MAX_BYTES)

    def test_raw_history_wrong_revision_and_oversize_leave_file_intact(self):
        with tempfile.TemporaryDirectory() as directory:
            store = MemoryStoreV2(Path(directory) / "memory.json")
            first = store.initialize()
            invalids = [dict(first, revision=1, raw_history=["messages"]),
                        dict(first, revision=3), dict(first, revision=1, goal="different"),
                        dict(first, revision=True), dict(first, schema_version=True),
                        dict(first, revision=1, relevant_events=[{"role": "user", "content": "raw"}])]
            huge = dict(first, revision=1, selected_subgoal="가" * 160,
                        completed_milestones=["가" * 160] * 6,
                        unresolved_information=["가" * 160] * 6)
            invalids.append(huge)
            for candidate in invalids:
                with self.assertRaises(ValueError):
                    store.update(candidate)
                self.assertEqual(first, store.load())

    def test_schema_does_not_oracle_filter_stale_claims(self):
        for case in SPEC["cases"]:
            for history in case["histories"]:
                memory = memory_from_events(history["events"])
                self.assertEqual(memory, validate_memory(memory))
                self.assertEqual(GOAL, memory["goal"])

    def test_memory_update_is_model_output_not_automatic_event_copy(self):
        current = deepcopy(SPEC["cases"][0]["current_observation"])
        event = deepcopy(SPEC["cases"][0]["histories"][0]["events"][0])
        event["observed_tick"] = current["tick"]
        current["visible_events"] = [event]
        result = decide_once(PublicOnlyProbe, Settings(), current, initial_memory())
        self.assertEqual([], result["scratchpad"]["relevant_events"])
        self.assertEqual(1, result["scratchpad"]["revision"])
        self.assertEqual(hashlib.sha256(canonical(result["request"])).hexdigest(), result["request_sha256"])


if __name__ == "__main__":
    unittest.main()
