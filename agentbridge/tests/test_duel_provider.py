import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from duel.coordinator import CommandRejected, DuelCoordinator
from duel.provider import combat_summary, parse_opencode_events, strict_json, validate_decision
from duel.runtime import apply_intent


def state():
    return {"contract": "DUEL_DEMO_OMNISCIENT_V0", "worldId": "w", "tick": 1,
            "gameOver": False, "teams": {
                "sharded": {"resources": {"copper": 0, "lead": 0},
                            "cores": [{"x": 10, "y": 20}],
                            "units": [{"id": 1, "type": "dagger", "health": 150,
                                       "maxHealth": 150, "commandable": True}]},
                "crux": {"resources": {"copper": 0, "lead": 0}, "cores": [],
                         "units": [{"id": 2, "type": "dagger", "health": 150,
                                    "maxHealth": 150, "commandable": True}]}}}


class Bridge:
    def __init__(self):
        self.state = state()
        self.commands = []

    def observe(self):
        return copy.deepcopy(self.state)

    def command(self, payload):
        self.commands.append(copy.deepcopy(payload))
        return {"accepted": True, "team": payload["team"], "action": payload["action"]}


ATTACK = {"intent": "ATTACK", "target": "enemy-force", "unit_group": "main", "reason": "Enemy is exposed"}


class ProviderContractTests(unittest.TestCase):
    def test_cloud_prompt_summary_excludes_ids_coordinates_resources_and_world(self):
        bridge = Bridge()
        views = DuelCoordinator(bridge).observe_round()
        summary = combat_summary(views["A"])
        self.assertEqual(summary["own"], {"fighters": 1, "healthFraction": [1.0],
                                          "corePresent": True})
        serialized = json.dumps(summary)
        for secret_or_raw_field in ("worldId", "tick", "resources", "copper", '"id"', '"x"', '"y"'):
            self.assertNotIn(secret_or_raw_field, serialized)

    def test_strict_json_and_decision_shape(self):
        for text in ('{"intent":"ATTACK","intent":"WAIT"}', '{"x":NaN}', "not json"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                strict_json(text)
        self.assertEqual(validate_decision(ATTACK), ATTACK)
        for bad in ({**ATTACK, "target": "own-core"}, {**ATTACK, "unitIds": [1]},
                    {**ATTACK, "reason": ""}):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_decision(bad)

    def test_opencode_events_reject_tool_use_and_parse_one_decision(self):
        output = json.dumps({"type": "text", "part": {"text": json.dumps(ATTACK)}}) + "\n"
        decision, usage = parse_opencode_events(output)
        self.assertEqual(decision, ATTACK)
        self.assertEqual(usage, [])
        with self.assertRaises(ValueError):
            parse_opencode_events(json.dumps({"type": "tool_use", "part": {}}) + "\n" + output)

    def test_attack_intent_maps_to_own_group_and_only_enemy(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge)
        coordinator.observe_round()
        result = apply_intent(coordinator, "A", ATTACK)
        self.assertTrue(result["accepted"])
        self.assertEqual(bridge.commands, [{"team": "sharded", "action": "attack",
                                            "unitIds": [1], "targetUnitId": 2}])

    def test_wait_does_not_send_and_ambiguous_attack_target_rejects(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge)
        coordinator.observe_round()
        wait = {"intent": "WAIT", "target": "none", "unit_group": "main", "reason": "Hold position"}
        self.assertEqual(apply_intent(coordinator, "A", wait)["action"], "wait")
        self.assertEqual(bridge.commands, [])
        bridge.state["teams"]["crux"]["units"].append(
            {"id": 3, "type": "dagger", "health": 150,
             "maxHealth": 150, "commandable": True})
        coordinator.observe_round()
        with self.assertRaises(CommandRejected):
            apply_intent(coordinator, "A", ATTACK)
        self.assertEqual(bridge.commands, [])

    def test_defend_uses_observed_core_without_strategy_choice(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge)
        coordinator.observe_round()
        defend = {"intent": "DEFEND", "target": "own-core", "unit_group": "main", "reason": "Protect core"}
        apply_intent(coordinator, "A", defend)
        self.assertEqual(bridge.commands[0], {"team": "sharded", "action": "move",
                                              "unitIds": [1], "x": 80, "y": 160})


if __name__ == "__main__":
    unittest.main()
