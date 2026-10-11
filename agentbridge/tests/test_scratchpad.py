import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agent"))

from research.condition import MemoryCondition, ResearchDecisionAdapter
from research.provider import MockDecisionProvider
from research.scratchpad import MAX_BYTES, ScratchpadStore, initial_scratchpad


GOAL = "Build and verify functional copper logistics."


def updated(previous, **changes):
    value = json.loads(json.dumps(previous))
    value.update(changes)
    value["revision"] = previous["revision"] + 1
    return value


class ScratchpadStoreTests(unittest.TestCase):
    def test_round_trip_and_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scratchpad.json"
            store = ScratchpadStore(path, GOAL)
            first = store.initialize()
            second = store.update(updated(first, current_subgoal="bootstrap copper", confidence=0.8))
            reloaded = ScratchpadStore(path, GOAL).load()
            self.assertEqual(1, second["revision"])
            self.assertEqual(second, reloaded)
            self.assertLessEqual(store.size_bytes(), MAX_BYTES)

    def test_goal_and_revision_are_controlled(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ScratchpadStore(Path(directory) / "scratchpad.json", GOAL)
            first = store.initialize()
            with self.assertRaisesRegex(ValueError, "goal is immutable"):
                store.update(updated(first, goal="attack"))
            invalid_revision = updated(first)
            invalid_revision["revision"] = 3
            with self.assertRaisesRegex(ValueError, "increment"):
                store.update(invalid_revision)
            self.assertEqual(first, store.load())

    def test_oversized_update_does_not_replace_file(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ScratchpadStore(Path(directory) / "scratchpad.json", GOAL)
            first = store.initialize()
            too_large = updated(first, plan=["x" * 300 for _ in range(8)], completed=["y" * 300 for _ in range(8)])
            with self.assertRaisesRegex(ValueError, "exceeds"):
                store.update(too_large)
            self.assertEqual(first, store.load())


class ConditionTests(unittest.TestCase):
    def test_no_scratchpad_has_no_hidden_history_and_resets_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            provider = MockDecisionProvider(lambda _: {"intent": "wait", "reason": "observe"})
            adapter = ResearchDecisionAdapter(
                provider,
                condition=MemoryCondition.NO_SCRATCHPAD,
                goal=GOAL,
                run_directory=directory,
                context_reset_every=1,
            )
            adapter.decide({"phase": "one"})
            adapter.decide({"phase": "two"})
            self.assertEqual(1, provider.reset_count)
            self.assertEqual({"goal", "observation"}, set(provider.contexts[1]))
            self.assertEqual({"phase": "two"}, provider.contexts[1]["observation"])
            self.assertNotIn("one", json.dumps(provider.contexts[1]))
            self.assertFalse((Path(directory) / "scratchpad.json").exists())

    def test_structured_scratchpad_persists_across_adapter_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            def policy(context):
                memory = context["scratchpad"]
                return {
                    "intent": "wait",
                    "reason": "retain goal",
                    "scratchpad": updated(memory, current_subgoal="verify flow", next_step="observe core copper"),
                }

            first_provider = MockDecisionProvider(policy)
            first = ResearchDecisionAdapter(
                first_provider,
                condition=MemoryCondition.STRUCTURED_SCRATCHPAD,
                goal=GOAL,
                run_directory=directory,
                context_reset_every=1,
            )
            first.decide({"phase": "build"})
            first.decide({"phase": "flow"})
            first.close()

            second_provider = MockDecisionProvider(policy)
            restarted = ResearchDecisionAdapter(
                second_provider,
                condition=MemoryCondition.STRUCTURED_SCRATCHPAD,
                goal=GOAL,
                run_directory=directory,
            )
            restarted.decide({"phase": "maintain"})
            self.assertEqual(2, second_provider.contexts[0]["scratchpad"]["revision"])
            self.assertEqual(GOAL, second_provider.contexts[0]["scratchpad"]["goal"])

    def test_invalid_scratchpad_update_rejects_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            def policy(context):
                memory = updated(context["scratchpad"], goal="different goal")
                return {"intent": "wait", "reason": "bad", "scratchpad": memory}

            adapter = ResearchDecisionAdapter(
                MockDecisionProvider(policy),
                condition=MemoryCondition.STRUCTURED_SCRATCHPAD,
                goal=GOAL,
                run_directory=directory,
            )
            with self.assertRaisesRegex(ValueError, "goal is immutable"):
                adapter.decide({"phase": "build"})
            self.assertEqual(0, ScratchpadStore(Path(directory) / "scratchpad.json", GOAL).load()["revision"])


if __name__ == "__main__":
    unittest.main()
