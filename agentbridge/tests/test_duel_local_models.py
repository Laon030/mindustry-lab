import copy
import json
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from duel.coordinator import DuelCoordinator
from duel.gate4_probe import check, prepare
from duel.gate3_probe import run as gate3_run
from duel.ollama_provider import DEFAULT_MODELS, DuelOllamaProvider, decision_prompt, decision_schema, validate_slot_decision


def state():
    return {"contract": "DUEL_DEMO_OMNISCIENT_V0", "worldId": "w", "tick": 0,
            "gameOver": False, "teams": {
                "sharded": {"resources": {}, "cores": [{"x": 10, "y": 20}], "units": [
                    {"id": 1, "type": "dagger", "health": 150, "maxHealth": 150,
                     "commandable": True},
                    {"id": 2, "type": "dagger", "health": 150, "maxHealth": 150,
                     "commandable": True}]},
                "crux": {"resources": {}, "cores": [], "units": [
                    {"id": 3, "type": "dagger", "health": 150, "maxHealth": 150,
                     "commandable": True}]}}}


class Bridge:
    def __init__(self):
        self.snapshot = state()
        self.commands = []
        self.advance_on_second_read = False
        self.reads = 0

    def observe(self):
        self.reads += 1
        if self.advance_on_second_read and self.reads == 2:
            self.snapshot["tick"] += 1
        return copy.deepcopy(self.snapshot)

    def command(self, command):
        self.commands.append(copy.deepcopy(command))
        return {"accepted": True, "team": command["team"], "action": command["action"]}


def attack(slot):
    return {"intent": "ATTACK", "target": "enemy-force", "unit_group": "main",
            "target_slot": slot, "reason": "Attack the chosen fighter"}


class Provider:
    def __init__(self, model, decision, barrier=None, error=None):
        self.model, self.decision, self.barrier, self.error = model, decision, barrier, error

    def decide(self, observation):
        if self.barrier:
            self.barrier.wait(timeout=2)
        if self.error:
            raise self.error
        return self.decision, {"outputTokens": 12}


class LocalDuelTests(unittest.TestCase):
    def test_default_models_are_distinct_local_small_families(self):
        self.assertEqual(DEFAULT_MODELS["A"], "deepseek-r1:1.5b")
        self.assertIn("glm-edge-1.5b", DEFAULT_MODELS["B"])

    def test_slot_choice_is_model_owned_and_validated(self):
        coordinator = DuelCoordinator(Bridge())
        views = coordinator.observe_round()
        self.assertEqual(validate_slot_decision(attack(1), views["B"]), attack(1))
        for invalid in (attack(2), {**attack(1), "target_slot": True},
                        {**attack(1), "target_slot": "1"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                validate_slot_decision(invalid, views["B"])
        with self.assertRaises(ValueError):
            validate_slot_decision({"intent": "DEFEND", "target": "own-core",
                                    "unit_group": "main", "target_slot": None,
                                    "reason": "Retreat"}, views["B"])
        self.assertEqual(len(decision_schema(views["A"])["oneOf"]), 3)
        self.assertEqual(len(decision_schema(views["B"])["oneOf"]), 2)
        self.assertEqual(decision_schema(views["B"])["oneOf"][0]
                         ["properties"]["target_slot"]["maximum"], 1)

    def test_two_models_decide_concurrently_from_one_frozen_snapshot(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge, DEFAULT_MODELS["A"], DEFAULT_MODELS["B"])
        barrier = threading.Barrier(2)
        result = prepare(coordinator, {
            "A": Provider(DEFAULT_MODELS["A"], attack(0), barrier),
            "B": Provider(DEFAULT_MODELS["B"], attack(1), barrier)})
        self.assertEqual(result["status"], "commands_accepted")
        self.assertEqual(result["tick"], 0)
        self.assertEqual(bridge.reads, 2)
        self.assertEqual(bridge.commands, [
            {"team": "sharded", "action": "attack", "unitIds": [1, 2], "targetUnitId": 3},
            {"team": "crux", "action": "attack", "unitIds": [3], "targetUnitId": 2}])
        bridge.snapshot["tick"] = 100
        bridge.snapshot["teams"]["crux"]["units"] = []
        self.assertEqual(check(coordinator, result)["fixtureWinner"], "sharded")

    def test_stale_snapshot_and_provider_error_issue_no_commands(self):
        for stale in (True, False):
            with self.subTest(stale=stale):
                bridge = Bridge()
                bridge.advance_on_second_read = stale
                coordinator = DuelCoordinator(bridge, DEFAULT_MODELS["A"], DEFAULT_MODELS["B"])
                result = prepare(coordinator, {
                    "A": Provider(DEFAULT_MODELS["A"], attack(0)),
                    "B": Provider(DEFAULT_MODELS["B"], attack(1),
                                  error=None if stale else RuntimeError("model unavailable"))})
                self.assertEqual(result["status"], "stale_snapshot" if stale else "provider_error")
                self.assertEqual(bridge.commands, [])

    def test_preexisting_damage_is_not_new_combat_evidence(self):
        bridge = Bridge()
        bridge.snapshot["teams"]["sharded"]["units"][0]["health"] = 42
        coordinator = DuelCoordinator(bridge, DEFAULT_MODELS["A"], DEFAULT_MODELS["B"])
        wait = {"intent": "WAIT", "target": "none", "unit_group": "main",
                "target_slot": None, "reason": "Hold"}
        prior = prepare(coordinator, {"A": Provider(DEFAULT_MODELS["A"], wait),
                                      "B": Provider(DEFAULT_MODELS["B"], wait)})
        self.assertEqual(prior["status"], "commands_accepted")
        self.assertEqual(prior["initialHealth"]["A"]["1"], 42)
        bridge.snapshot["tick"] = 100
        self.assertEqual(check(coordinator, prior)["status"], "no_damage_observed")

    def test_fighter_draw_does_not_count_surviving_workers_as_winner(self):
        bridge = Bridge()
        for team, worker_id in (("sharded", 4), ("crux", 5)):
            bridge.snapshot["teams"][team]["units"].append(
                {"id": worker_id, "type": "mono", "health": 100,
                 "maxHealth": 100, "commandable": True})
        coordinator = DuelCoordinator(bridge, DEFAULT_MODELS["A"], DEFAULT_MODELS["B"])
        prior = prepare(coordinator, {
            "A": Provider(DEFAULT_MODELS["A"], attack(0)),
            "B": Provider(DEFAULT_MODELS["B"], attack(0))})
        bridge.snapshot["tick"] = 100
        for team in ("sharded", "crux"):
            bridge.snapshot["teams"][team]["units"] = [
                unit for unit in bridge.snapshot["teams"][team]["units"]
                if unit["type"] != "dagger"]
        result = check(coordinator, prior)
        self.assertEqual(result["status"], "combat_observed")
        self.assertEqual(result["fixtureWinner"], "DRAW")
        self.assertEqual(result["fighters"], {"A": [], "B": []})

    def test_local_http_payload_uses_aggregate_state_and_strict_json(self):
        coordinator = DuelCoordinator(Bridge())
        view = coordinator.observe_round()["A"]
        prompt = decision_prompt(view)
        for forbidden in ('"worldId"', '"resources"', '"id"', '"x"', '"y"'):
            self.assertNotIn(forbidden, prompt)
        reply = json.dumps({"model": "deepseek-r1:7b", "done": True,
                            "message": {"content": json.dumps(attack(0))},
                            "prompt_eval_count": 80, "eval_count": 22}).encode()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return None

            def read(self):
                return reply

        with patch("duel.ollama_provider.urllib.request.urlopen", return_value=Response()) as urlopen:
            decision, usage = DuelOllamaProvider("deepseek-r1:7b").decide(view)
        self.assertEqual(decision, attack(0))
        self.assertEqual(usage["outputTokens"], 22)
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertEqual(len(json.loads(request.data)["format"]["oneOf"]), 3)

    def test_gate3_local_model_preserves_scripted_opponent(self):
        bridge = Bridge()
        model = Provider("deepseek-r1:7b", attack(0))
        with patch("duel.gate3_probe.DuelBridge", return_value=bridge), patch(
                "duel.gate3_probe.DuelOllamaProvider", return_value=model):
            result = gate3_run("prepare", "deepseek-r1:7b", "ollama")
        self.assertEqual(result["llmDecision"], attack(0))
        self.assertEqual(result["modelB"], "scripted-gate3")
        self.assertEqual([command["team"] for command in bridge.commands],
                         ["sharded", "crux"])


if __name__ == "__main__":
    unittest.main()
