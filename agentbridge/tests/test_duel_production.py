import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from duel.coordinator import CONTRACT, CommandRejected, DuelCoordinator
from duel.gate6_probe import run_round
from duel.production import decision_schema, legal_intents, production_summary, resolve_intent


def snapshot(stock=10):
    def team(y, unit_id):
        return {"resources": {"copper": 0, "lead": 0},
                "cores": [{"x": 159, "y": y, "health": 1100}],
                "units": [{"id": unit_id, "type": "mono", "health": 100,
                           "commandable": True}],
                "production": {"factory": {"x": 151, "y": y + 6,
                                           "block": "ground-factory", "unit": "dagger",
                                           "status": "idle", "stock": {"silicon": stock, "lead": stock},
                                           "cost": {"silicon": 10, "lead": 10},
                                           "progress": 0}},
                "economy": {}, "buildings": []}
    return {"contract": CONTRACT, "worldId": "g6", "tick": 0, "gameOver": False,
            "teams": {"sharded": team(52, 1), "crux": team(132, 2)}}


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
        return {"intent": self.intent, "reason": "provider decision"}, {"reportedModel": self.model}


class DuelProductionTests(unittest.TestCase):
    def test_symmetric_funded_factory_and_independent_choice(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge, "deepseek", "glm")
        views = coordinator.observe_round()
        self.assertEqual(production_summary(views["A"]), production_summary(views["B"]))
        self.assertEqual(legal_intents(views["A"]), ["PRODUCE", "WAIT"])
        self.assertEqual(decision_schema(views["A"])["properties"]["intent"]["enum"],
                         ["PRODUCE", "WAIT"])
        self.assertIsNone(resolve_intent(coordinator, "A", {"intent": "WAIT"}))
        result = run_round(coordinator, {"A": Provider("deepseek", "PRODUCE"),
                                         "B": Provider("glm", "WAIT")})
        self.assertEqual(result["status"], "commands_accepted")
        self.assertEqual([command["team"] for command in bridge.commands], ["sharded"])

    def test_factory_ownership_and_exact_candidate(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge, "deepseek", "glm")
        coordinator.observe_round()
        command = resolve_intent(coordinator, "B", {"intent": "PRODUCE"})
        self.assertEqual(command, {"team": "crux", "action": "produce",
                                   "buildingX": 151, "buildingY": 138, "unit": "dagger"})
        coordinator.command("B", command)
        with self.assertRaises(CommandRejected):
            coordinator.command("A", {**command, "team": "sharded"})
        with self.assertRaises(CommandRejected):
            coordinator.command("B", {**command, "buildingY": 58})
        self.assertEqual(len(bridge.commands), 1)

    def test_missing_stock_and_active_factory_rejected(self):
        for state in (snapshot(9), snapshot()):
            if state["teams"]["sharded"]["production"]["factory"]["stock"]["lead"] == 10:
                state["teams"]["sharded"]["production"]["factory"]["status"] = "active"
            bridge = Bridge(state)
            coordinator = DuelCoordinator(bridge, "deepseek", "glm")
            coordinator.observe_round()
            with self.assertRaises(CommandRejected):
                coordinator.command("A", {"team": "sharded", "action": "produce",
                                          "buildingX": 151, "buildingY": 58, "unit": "dagger"})
            self.assertEqual(bridge.commands, [])


if __name__ == "__main__":
    unittest.main()
