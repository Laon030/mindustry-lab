import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from duel.coordinator import CONTRACT, CommandRejected, DuelCoordinator
from duel.economy import decision_schema, economy_summary, legal_intents, resolve_intent
from duel.gate5_probe import run_round


def snapshot(copper=0):
    def team(mono, poly, y):
        return {"resources": {"copper": copper, "lead": 0},
                "cores": [{"x": 159, "y": y, "health": 1100}],
                "units": [{"id": mono, "type": "mono", "health": 100, "commandable": True},
                          {"id": poly, "type": "poly", "health": 400, "commandable": True}],
                "buildings": [],
                "economy": {"nearbyCopperOreTiles": 25,
                            "duoSite": {"x": 151, "y": y, "block": "duo",
                                        "copperCost": 35, "placeable": True, "status": "empty"}}}
    return {"contract": CONTRACT, "worldId": "g5", "tick": 0, "gameOver": False,
            "teams": {"sharded": team(1, 2, 52), "crux": team(3, 4, 132)}}


class Bridge:
    def __init__(self, state=None):
        self.state = snapshot() if state is None else state
        self.commands = []

    def observe(self):
        return copy.deepcopy(self.state)

    def command(self, payload):
        self.commands.append(copy.deepcopy(payload))
        return {"accepted": True, "team": payload["team"], "action": payload["action"]}


class Provider:
    def __init__(self, model, intent):
        self.model, self.intent = model, intent

    def decide(self, observation):
        return {"intent": self.intent, "reason": "selected by provider"}, {"reportedModel": self.model}


class DuelEconomyTests(unittest.TestCase):
    def test_symmetric_summary_and_legality(self):
        coordinator = DuelCoordinator(Bridge(), "deepseek", "glm")
        views = coordinator.observe_round()
        self.assertEqual(economy_summary(views["A"])["own"],
                         economy_summary(views["B"])["enemy"])
        self.assertEqual(legal_intents(views["A"]), ["WAIT", "MINE"])
        self.assertEqual(decision_schema(views["A"])["properties"]["intent"]["enum"],
                         ["WAIT", "MINE"])
        self.assertEqual(resolve_intent(coordinator, "A", {"intent": "WAIT"}), None)
        self.assertEqual(resolve_intent(coordinator, "B", {"intent": "MINE"})["unitIds"], [3])

    def test_build_is_model_choice_and_team_scoped(self):
        bridge = Bridge(snapshot(35))
        coordinator = DuelCoordinator(bridge, "deepseek", "glm")
        views = coordinator.observe_round()
        self.assertIn("BUILD", legal_intents(views["A"]))
        choice = resolve_intent(coordinator, "B", {"intent": "BUILD"})
        self.assertEqual(choice, {"team": "crux", "action": "build", "unitIds": [4],
                                  "block": "duo", "x": 151, "y": 132})
        coordinator.command("B", choice)
        with self.assertRaises(CommandRejected):
            coordinator.command("A", {**choice, "team": "sharded"})
        with self.assertRaises(CommandRejected):
            coordinator.command("A", {"team": "sharded", "action": "build", "unitIds": [2],
                                      "block": "duo", "x": 151, "y": 132})
        self.assertEqual(len(bridge.commands), 1)

    def test_unaffordable_build_and_enemy_miner_rejected(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge, "deepseek", "glm")
        coordinator.observe_round()
        with self.assertRaises(CommandRejected):
            coordinator.command("A", {"team": "sharded", "action": "build", "unitIds": [2],
                                      "block": "duo", "x": 151, "y": 52})
        with self.assertRaises(CommandRejected):
            coordinator.command("B", {"team": "crux", "action": "mine", "unitIds": [1],
                                      "resource": "copper"})
        self.assertEqual(bridge.commands, [])

    def test_parallel_provider_wait_does_not_turn_into_python_mine(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge, "deepseek", "glm")
        result = run_round(coordinator, {"A": Provider("deepseek", "WAIT"),
                                         "B": Provider("glm", "MINE")})
        self.assertEqual(result["status"], "commands_accepted")
        self.assertIsNone(result["commands"]["A"])
        self.assertEqual([command["team"] for command in bridge.commands], ["crux"])


if __name__ == "__main__":
    unittest.main()
