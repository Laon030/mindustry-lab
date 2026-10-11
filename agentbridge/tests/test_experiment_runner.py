import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agent"))

from research.benchmark import BenchmarkSpec
from research.condition import MemoryCondition
from research.metrics import calculate_metrics
from research.provider import MockDecisionProvider
from research.runner import ExperimentRunner, mock_provider_factory


class MetricsTests(unittest.TestCase):
    def test_operational_metrics_are_recomputed_from_events(self):
        events = [
            {"type": "llm_decision", "valid": True, "latency_seconds": 1.0, "usage": {"input_tokens": 10, "output_tokens": 2}},
            {"type": "action", "accepted": True, "redundant": False},
            {"type": "action", "accepted": True, "redundant": True},
            {"type": "invalid_action", "recoverable": True},
            {"type": "goal_loss", "seq": 4, "recoverable": True},
            {"type": "context_reset", "seq": 5, "context_loss": True},
            {"type": "recovery", "trigger_type": "context_reset", "trigger_seq": 5, "latency_seconds": 0.5},
            {"type": "scratchpad_update", "event": "updated", "bytes": 400},
            {"type": "recovery", "trigger_seq": 3, "resolved": True},
            {"type": "recovery", "trigger_seq": 4, "resolved": True},
            {"type": "completion", "success": True, "post_completion_replanned": True,
             "elapsed_seconds": 12.0, "useful_construction_copper": 17, "total_copper_consumed": 20},
            {"type": "run_end", "reason": "completed", "success": True},
        ]
        metrics = calculate_metrics(events)
        self.assertTrue(metrics["task_success"])
        self.assertEqual(12.0, metrics["completion_time_seconds"])
        self.assertEqual(2, metrics["action_count"])
        self.assertEqual(1, metrics["redundant_action_count"])
        self.assertEqual(1, metrics["goal_loss_count"])
        self.assertEqual(0.85, metrics["resource_efficiency"])
        self.assertEqual({"input": 10, "output": 2}, metrics["token_usage"])
        self.assertEqual(0.5, metrics["context_reset_recovery_latency_seconds"]["mean"])


class ExperimentRunnerTests(unittest.TestCase):
    def test_each_condition_resets_logs_metrics_and_cleanup(self):
        spec = BenchmarkSpec.load(ROOT / "experiments" / "logistics_benchmark.json")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for condition in (MemoryCondition.NO_SCRATCHPAD, MemoryCondition.STRUCTURED_SCRATCHPAD):
                output = root / condition.value
                runner = ExperimentRunner(
                    spec,
                    output=output,
                    provider_factory=mock_provider_factory(condition),
                    provider_config={"type": "mock", "policy": "logistics-v1"},
                    context_reset_every=2,
                )
                summary = runner.run(condition, 2)
                self.assertEqual(2, summary["successful_runs"])
                self.assertTrue(all(metrics["action_count"] == 7 for metrics in summary["run_metrics"]))
                self.assertTrue(all(metrics["goal_loss_count"] == 0 for metrics in summary["run_metrics"]))
                for run_number in (1, 2):
                    run_dir = output / condition.value / f"run-{run_number:03d}"
                    events = [json.loads(line) for line in (run_dir / "events.jsonl").read_text().splitlines()]
                    self.assertTrue((run_dir / "metadata.json").exists())
                    self.assertTrue((run_dir / "metrics.json").exists())
                    self.assertEqual(1, sum(event["type"] == "fixture_reset" for event in events))
                    self.assertTrue(any(event["type"] == "cleanup" and event["complete"] for event in events))
                    self.assertTrue(any(event["type"] == "context_reset" for event in events))
                    if condition is MemoryCondition.STRUCTURED_SCRATCHPAD:
                        self.assertTrue((run_dir / "scratchpad.json").exists())
                    else:
                        self.assertFalse((run_dir / "scratchpad.json").exists())

    def test_fairness_metadata_differs_only_by_condition_for_matched_runs(self):
        spec = BenchmarkSpec.load(ROOT / "experiments" / "logistics_benchmark.json")
        with tempfile.TemporaryDirectory() as directory:
            metadata = []
            for condition in (MemoryCondition.NO_SCRATCHPAD, MemoryCondition.STRUCTURED_SCRATCHPAD):
                output = Path(directory) / condition.value
                runner = ExperimentRunner(
                    spec,
                    output=output,
                    provider_factory=mock_provider_factory(condition),
                    provider_config={"type": "mock", "policy": "logistics-v1"},
                    context_reset_every=2,
                    base_seed=99,
                )
                runner.run(condition, 1)
                path = output / condition.value / "run-001" / "metadata.json"
                value = json.loads(path.read_text())
                value.pop("condition")
                value.pop("run_id")
                metadata.append(value)
            self.assertEqual(metadata[0], metadata[1])

    def test_goal_inconsistent_valid_intent_is_classified(self):
        spec = BenchmarkSpec.load(ROOT / "experiments" / "logistics_benchmark.json")
        with tempfile.TemporaryDirectory() as directory:
            runner = ExperimentRunner(
                spec,
                output=Path(directory) / "goal-loss",
                provider_factory=lambda: MockDecisionProvider(
                    lambda _context: {"intent": "reconsider", "reason": "abandon current plan"}
                ),
                provider_config={"type": "mock", "policy": "goal-loss"},
                context_reset_every=2,
            )
            summary = runner.run(MemoryCondition.NO_SCRATCHPAD, 1)
            metrics = summary["run_metrics"][0]
            self.assertFalse(metrics["task_success"])
            self.assertEqual(1, metrics["goal_loss_count"])
            self.assertEqual(0, metrics["action_count"])


if __name__ == "__main__":
    unittest.main()
