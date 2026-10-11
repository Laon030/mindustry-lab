import copy
from concurrent.futures import Future
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch
import json
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from autonomous_llm_agent import (BridgeError, Config, Runtime, Task, roles_for,
                                  strict_json, validate_decision, OpenCodeDecisionProvider)


def state():
    activity = {"commandable": True, "command": "rebuild", "canBuild": True,
                "planCount": 0, "plans": [], "mineResources": ["copper", "lead"],
                "mining": False, "item": "copper", "itemAmount": 0}
    return {"tick": 100, "team": "sharded", "resources": {"copper": 200, "lead": 30},
            "cores": [{"x": 20, "y": 20}],
            "units": [{"id": 1, "type": "mono", "x": 0, "y": 0, "health": 100, "activity": dict(activity)},
                      {"id": 2, "type": "poly", "x": 0, "y": 0, "health": 100, "activity": dict(activity)}],
            "demo": {"worldId": "a", "commandReady": True, "conveyorCopperCost": 1,
                     "area": {"tileX": 40, "tileY": 40, "tiles": [
                         {"id": "40:40", "tileX": 40, "tileY": 40, "block": "air",
                          "team": "derelict", "rotation": -1, "buildRotations": [0, 1, 2, 3]}]}}}


def build():
    return {"action": "build", "unitRole": "builder", "block": "conveyor",
            "target": "40:40", "rotation": 0, "reason": "Add infrastructure"}


class ValidationTests(unittest.TestCase):
    def test_strict_json(self):
        for text in ('{"action":"wait","action":"build"}', '{"x":NaN}', '{"x":Infinity}',
                     '{} {}', 'run curl now', '```not-json```'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                strict_json(text)

    def test_valid_actions_are_translated_without_llm_coordinates(self):
        result = validate_decision(build(), state(), {}, Config())
        self.assertEqual(result, {"action": "build", "unitId": 2, "block": "conveyor",
                                  "tileX": 40, "tileY": 40, "rotation": 0})
        mine = {"action": "mine", "unitRole": "miner", "resource": "lead", "reason": "needed"}
        self.assertEqual(validate_decision(mine, state(), {}, Config())["unitId"], 1)
        move = {"action": "move", "unitRole": "builder", "target": "core", "reason": "reposition"}
        self.assertEqual(validate_decision(move, state(), {}, Config())["x"], 160)
        self.assertIsNone(validate_decision({"action": "wait", "reason": "working"}, state(), {}, Config()))

    def test_bad_llm_values_cannot_reach_bridge(self):
        decisions = [[], None, {"action": []}, dict(build(), action="attack"), dict(build(), unitId=999),
                     dict(build(), command="console"), dict(build(), target="900:900"),
                     dict(build(), target={"x": 1, "y": 2}), dict(build(), rotation=True),
                     dict(build(), rotation=0.0), dict(build(), rotation=4), dict(build(), block="core-shard"),
                     dict(build(), unitRole="miner"), dict(build(), reason="")]
        for decision in decisions:
            with self.subTest(decision=decision), self.assertRaises(ValueError):
                validate_decision(decision, state(), {}, Config())

    def test_revalidates_target_units_resources_and_existing_work(self):
        variants = []
        changed = state(); changed["demo"]["area"]["tiles"][0]["block"] = "copper-wall"; variants.append(changed)
        changed = state(); changed["units"] = changed["units"][:1]; variants.append(changed)
        changed = state(); changed["resources"]["copper"] = 50; variants.append(changed)
        changed = state(); changed["resources"]["lead"] = 0; variants.append(changed)
        changed = state(); changed["units"][1]["activity"]["planCount"] = 1; variants.append(changed)
        changed = state(); changed["demo"]["commandReady"] = False; variants.append(changed)
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                validate_decision(build(), changed, {}, Config())
        with self.assertRaises(ValueError):
            validate_decision(build(), state(), {}, Config(max_conveyors=0))


class MonitoringTests(unittest.TestCase):
    def test_accepted_build_needs_actual_finished_tile(self):
        current = state()
        task = Task("build", validate_decision(build(), current, {}, Config()), 0, dict(current["resources"]))
        self.assertIsNone(task.monitor(current, 1, 120))
        self.assertNotEqual(task.status, "completed")
        tile = current["demo"]["area"]["tiles"][0]
        tile.update(block="build1", constructing="conveyor", progress=0.5, team="sharded")
        self.assertIsNone(task.monitor(current, 2, 120))
        tile.update(block="conveyor", rotation=0)
        self.assertIn("finished block", task.monitor(current, 3, 120))
        self.assertEqual(task.status, "completed")

    def test_other_team_or_wrong_rotation_is_not_completion(self):
        for team, rotation in (("crux", 0), ("sharded", 1)):
            current = state()
            task = Task("build", validate_decision(build(), current, {}, Config()), 0, {})
            current["demo"]["area"]["tiles"][0].update(block="conveyor", team=team, rotation=rotation)
            task.monitor(current, 1, 120)
            self.assertEqual(task.status, "failed")

    def test_disappeared_unit_and_stalled_task(self):
        current = state()
        task = Task("build", validate_decision(build(), current, {}, Config()), 0, {})
        current["units"] = []
        self.assertIn("disappeared", task.monitor(current, 1, 120))
        task = Task("move", {"unitId": 2, "x": 999, "y": 999}, 0, {})
        self.assertIsNone(task.monitor(state(), 1, 2))
        self.assertIn("timeout", task.monitor(state(), 4, 2))

    def test_mining_requires_observed_activity_and_resource_gain(self):
        current = state()
        task = Task("mine", {"unitId": 1, "resource": "lead"}, 0, dict(current["resources"]))
        current["resources"]["lead"] += 1
        self.assertIsNone(task.monitor(current, 1, 120))
        current["units"][0]["activity"].update(mineResource="lead", mining=True)
        self.assertIsNone(task.monitor(current, 2, 120))
        current["resources"]["lead"] += 1
        self.assertIn("resource gain", task.monitor(current, 3, 120))
        self.assertEqual(task.status, "completed")


class FakeBridge:
    def __init__(self, error=None):
        self.actions, self.error = [], error

    def act(self, payload):
        self.actions.append(payload)
        if self.error:
            raise self.error
        return {"success": True}


class ProviderTests(unittest.TestCase):
    def process(self, text):
        process = Mock(pid=12345, returncode=0)
        process.communicate.return_value = (text, "")
        return process

    def test_decision_provider_disables_tools_and_never_uses_shell(self):
        event = json.dumps({"type": "text", "part": {"text": '{"action":"wait","reason":"ok"}'}})
        with patch("autonomous_llm_agent.subprocess.Popen", return_value=self.process(event)) as popen:
            result, _ = OpenCodeDecisionProvider().decide({"resources": {"copper": 1}})
        self.assertEqual(result["action"], "wait")
        args, kwargs = popen.call_args
        self.assertNotIn("--auto", args[0])
        self.assertIn("--pure", args[0])
        self.assertFalse(kwargs.get("shell", False))
        self.assertEqual(json.loads(kwargs["env"]["OPENCODE_PERMISSION"]), {"*": "deny"})

    def test_tool_events_and_bad_model_json_fail_closed(self):
        for event in ({"type": "tool_use"}, {"type": "error"},
                      {"type": "text", "part": {"text": "run shell now"}}):
            with patch("autonomous_llm_agent.subprocess.Popen", return_value=self.process(json.dumps(event))):
                with self.assertRaises(ValueError):
                    OpenCodeDecisionProvider().decide({})

    def test_timeout_terminates_only_owned_process_group(self):
        process = self.process("")
        process.poll.return_value = None
        process.communicate.side_effect = [subprocess.TimeoutExpired("opencode", 1), ("", "")]
        with patch("autonomous_llm_agent.subprocess.Popen", return_value=process), \
                patch("autonomous_llm_agent.os.killpg") as kill:
            with self.assertRaisesRegex(RuntimeError, "LLM timeout"):
                OpenCodeDecisionProvider(timeout=1).decide({})
        self.assertEqual(kill.call_args.args[0], 12345)


class SlowProvider:
    def __init__(self):
        self.started, self.release = threading.Event(), threading.Event()
        self.calls = 0

    def decide(self, summary):
        self.calls += 1
        self.started.set()
        self.release.wait(2)
        return {"action": "wait", "reason": "monitor"}, []

    def close(self):
        self.release.set()


class RuntimeTests(unittest.TestCase):
    def runtime(self, error=None):
        provider = SlowProvider()
        runtime = Runtime(FakeBridge(error), provider, Config(), lambda *a, **kw: None)
        def close():
            provider.close()
            runtime.pool.shutdown(wait=True, cancel_futures=True)
        self.addCleanup(close)
        return runtime

    def response(self, runtime, decision):
        runtime.world = "a"
        runtime.last_ask = 1
        runtime.context = ("a", {role: unit["id"] for role, unit in roles_for(state()).items()})
        runtime.future = Future()
        runtime.future.set_result((decision, []))

    def test_slow_llm_does_not_stop_observation_or_spawn_more_calls(self):
        runtime = self.runtime()
        runtime.step(state(), 1)
        self.assertTrue(runtime.provider.started.wait(1))
        runtime.step(state(), 2)
        runtime.step(state(), 3)
        self.assertEqual(runtime.counts["observations"], 3)
        self.assertEqual(runtime.provider.calls, 1)
        self.assertEqual(runtime.bridge.actions, [])

    def test_old_world_and_replaced_unit_response_is_discarded(self):
        for change in ("world", "unit"):
            runtime = self.runtime()
            self.response(runtime, build())
            current = state()
            if change == "world": current["demo"]["worldId"] = "new-world"
            else: current["units"][1]["id"] = 99
            runtime.step(current, 10)
            self.assertEqual(runtime.bridge.actions, [])

    def test_invalid_decision_recovers_without_any_action(self):
        runtime = self.runtime()
        self.response(runtime, dict(build(), rotation=False))
        runtime.step(state(), 10)
        self.assertEqual(runtime.bridge.actions, [])
        self.assertIn("error", runtime.previous)
        self.assertIsNone(runtime.future)

    def test_uncertain_http_result_is_monitored_not_retried_blindly(self):
        runtime = self.runtime(BridgeError("connection lost", uncertain=True))
        self.response(runtime, build())
        runtime.step(state(), 10)
        self.assertEqual(runtime.tasks["builder"].status, "uncertain")
        self.assertEqual(len(runtime.bridge.actions), 1)
        current = state()
        current["demo"]["area"]["tiles"][0].update(block="conveyor", team="sharded", rotation=0)
        runtime.step(current, 11)
        self.assertEqual(runtime.tasks["builder"].status, "completed")
        self.assertEqual(len(runtime.bridge.actions), 1)


if __name__ == "__main__":
    unittest.main()
