from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from research.benchmark import BenchmarkSpec
from research.condition import MemoryCondition
from research.metrics import calculate_metrics
from research.provider import MockDecisionProvider
from research.runner import ExperimentRunner, mock_provider_factory


ROOT = Path(__file__).resolve().parents[1]


class TerminalOutcomeTests(unittest.TestCase):
    def test_completion_without_terminal_or_followup_is_not_success(self):
        completion = {"type": "completion", "success": True, "elapsed_seconds": 1}
        terminal = {"type": "run_end", "reason": "completed", "success": True}
        self.assertFalse(calculate_metrics([completion])["task_success"])
        self.assertFalse(calculate_metrics([completion, terminal])["task_success"])
        completion["post_completion_replanned"] = True
        self.assertTrue(calculate_metrics([completion, terminal])["task_success"])

    def test_unresolved_goal_loss_and_failed_followup_veto_success(self):
        completed = {"type": "completion", "success": True, "elapsed_seconds": 1,
                     "post_completion_replanned": True}
        terminal = {"type": "run_end", "reason": "completed", "success": True}
        for failure in ("goal_loss", "invalid_action", "failure"):
            events = [completed, {"type": failure}, terminal]
            metrics = calculate_metrics(events)
            self.assertFalse(metrics["task_success"])
            self.assertIsNone(metrics["completion_time_seconds"])
        self.assertFalse(calculate_metrics([completed, {**terminal, "reason": "failed"}])["task_success"])

    def test_terminal_must_be_unique_and_last_except_cleanup(self):
        completion = {"type": "completion", "success": True, "elapsed_seconds": 1,
                      "post_completion_replanned": True}
        terminal = {"type": "run_end", "reason": "completed", "success": True}
        for tail in ([terminal], [{"type": "llm_decision"}], [{"type": "failure"}]):
            self.assertFalse(calculate_metrics([completion, terminal] + tail)["task_success"])
        self.assertTrue(calculate_metrics([completion, terminal, {"type": "cleanup", "complete": True}])["task_success"])

    def test_recovery_must_resolve_a_specific_recoverable_failure(self):
        tail = [{"type": "completion", "success": True, "elapsed_seconds": 2,
                 "post_completion_replanned": True},
                {"type": "run_end", "reason": "completed", "success": True}]
        loss = {"type": "goal_loss", "seq": 0, "recoverable": True}
        for recovery in ({"type": "recovery"}, {"type": "recovery", "trigger_seq": 99, "resolved": True},
                         {"type": "recovery", "trigger_seq": 0}):
            self.assertFalse(calculate_metrics([loss, recovery] + tail)["task_success"])
        recovery = {"type": "recovery", "trigger_seq": 0, "resolved": True}
        self.assertTrue(calculate_metrics([loss, recovery] + tail)["task_success"])
        self.assertFalse(calculate_metrics([{**loss, "recoverable": False}, recovery] + tail)["task_success"])

    def test_runner_reproduces_audit_counterexample_as_failed_episode(self):
        intents = iter(["continue_bootstrap", "establish_copper_logistics", "wait", "reconsider"])
        spec = BenchmarkSpec.load(ROOT / "experiments/logistics_benchmark.json")
        with tempfile.TemporaryDirectory() as directory:
            runner = ExperimentRunner(spec, output=Path(directory),
                provider_factory=lambda: MockDecisionProvider(lambda _: {"intent": next(intents), "reason": "probe"}),
                provider_config={"type": "mock"}, context_reset_every=2)
            result = runner.run(MemoryCondition.NO_SCRATCHPAD, 1)
            self.assertEqual(0, result["successful_runs"])
            self.assertEqual(1, result["run_metrics"][0]["goal_loss_count"])
            events = [json.loads(line) for line in (Path(directory) / "no_scratchpad/run-001/events.jsonl").read_text().splitlines()]
            self.assertTrue(any(e["type"] == "milestone" for e in events))
            self.assertFalse(any(e["type"] == "completion" for e in events))
            self.assertFalse(next(e for e in events if e["type"] == "run_end")["success"])

    def test_transport_failure_is_recorded_not_dropped(self):
        spec = BenchmarkSpec.load(ROOT / "experiments/logistics_benchmark.json")
        def broken(_):
            raise OSError("diagnostic transport failure")
        with tempfile.TemporaryDirectory() as directory:
            runner = ExperimentRunner(spec, output=Path(directory),
                provider_factory=lambda: MockDecisionProvider(broken), provider_config={"type": "mock"},
                context_reset_every=0)
            result = runner.run(MemoryCondition.NO_SCRATCHPAD, 1)
            self.assertFalse(result["run_metrics"][0]["task_success"])
            self.assertTrue((Path(directory) / "no_scratchpad/summary.json").exists())
            self.assertTrue((Path(directory) / "no_scratchpad/run-001/metrics.json").exists())

    def test_stateless_hook_is_not_context_loss_or_recovery(self):
        spec = BenchmarkSpec.load(ROOT / "experiments/logistics_benchmark.json")
        condition = MemoryCondition.NO_SCRATCHPAD
        with tempfile.TemporaryDirectory() as directory:
            runner = ExperimentRunner(spec, output=Path(directory), provider_factory=mock_provider_factory(condition),
                provider_config={"type": "mock"}, context_reset_every=2)
            result = runner.run(condition, 1)
            self.assertTrue(result["run_metrics"][0]["task_success"])
            events = [json.loads(line) for line in (Path(directory) / "no_scratchpad/run-001/events.jsonl").read_text().splitlines()]
            resets = [e for e in events if e["type"] == "context_reset"]
            self.assertTrue(resets)
            self.assertTrue(all(e["context_loss"] is False for e in resets))
            self.assertEqual(0, result["run_metrics"][0]["actual_context_loss_count"])
            self.assertFalse(any(e["type"] == "recovery" for e in events))
            self.assertIsNone(result["run_metrics"][0]["context_reset_recovery_latency_seconds"]["mean"])


if __name__ == "__main__":
    unittest.main()
