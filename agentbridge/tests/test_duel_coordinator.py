import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from duel.coordinator import CONTRACT, CommandRejected, DuelCoordinator


def snapshot():
    return {
        "contract": CONTRACT, "worldId": "world-1", "tick": 10, "gameOver": False,
        "teams": {
            "sharded": {"resources": {"copper": 10, "lead": 0}, "cores": [],
                        "units": [{"id": 1, "type": "dagger", "health": 150, "commandable": True},
                                  {"id": 2, "type": "alpha", "health": 200, "commandable": False}]},
            "crux": {"resources": {"copper": 10, "lead": 0}, "cores": [],
                     "units": [{"id": 3, "type": "dagger", "health": 150, "commandable": True}]},
        },
    }


class FakeBridge:
    def __init__(self):
        self.state = snapshot()
        self.commands = []

    def observe(self):
        return copy.deepcopy(self.state)

    def command(self, payload):
        self.commands.append(copy.deepcopy(payload))
        return {"accepted": True, "team": payload["team"], "action": payload["action"]}


class DuelCoordinatorTests(unittest.TestCase):
    def setUp(self):
        self.bridge = FakeBridge()
        self.coordinator = DuelCoordinator(self.bridge, model_a="script-A", model_b="script-B")

    def test_symmetric_views_and_independent_sessions(self):
        views = self.coordinator.observe_round()
        self.assertEqual(set(views["A"]), set(views["B"]))
        self.assertEqual(views["A"]["own"], views["B"]["enemy"])
        self.assertEqual(views["A"]["enemy"], views["B"]["own"])
        self.assertEqual(self.coordinator.sessions["A"].roster, frozenset({1}))
        self.assertEqual(self.coordinator.sessions["B"].roster, frozenset({3}))
        self.coordinator.sessions["A"].prompt_state["marker"] = "A-only"
        self.assertNotIn("marker", self.coordinator.sessions["B"].prompt_state)
        self.assertEqual(self.coordinator.sessions["A"].model, "script-A")
        self.assertEqual(self.coordinator.sessions["B"].model, "script-B")

    def test_equal_model_identifiers_are_rejected(self):
        with self.assertRaises(ValueError):
            DuelCoordinator(self.bridge, model_a="same", model_b="same")

    def test_opponent_and_noncommandable_unit_ids_never_reach_bridge(self):
        self.coordinator.observe_round()
        for agent_id, team, forbidden_id in (("A", "sharded", 3), ("B", "crux", 1),
                                             ("A", "sharded", 2)):
            with self.subTest(agent=agent_id, unit=forbidden_id), self.assertRaises(CommandRejected):
                self.coordinator.command(agent_id, {"team": team, "action": "move",
                                                    "unitIds": [forbidden_id], "x": 40, "y": 40})
        with self.assertRaises(CommandRejected):
            self.coordinator.command("A", {"team": "crux", "action": "move",
                                           "unitIds": [1], "x": 40, "y": 40})
        self.assertEqual(self.bridge.commands, [])

    def test_own_commands_pass_and_target_must_be_enemy(self):
        self.coordinator.observe_round()
        accepted = self.coordinator.command("A", {"team": "sharded", "action": "attack",
                                                   "unitIds": [1], "targetUnitId": 3})
        self.assertTrue(accepted["accepted"])
        self.assertEqual(self.bridge.commands[0]["team"], "sharded")
        self.assertEqual(self.coordinator.sessions["A"].decision_counter, 1)
        self.assertEqual(self.coordinator.sessions["B"].decision_counter, 0)
        with self.assertRaises(CommandRejected):
            self.coordinator.command("A", {"team": "sharded", "action": "attack",
                                           "unitIds": [1], "targetUnitId": 1})
        self.assertEqual(len(self.bridge.commands), 1)

    def test_dead_or_despawned_units_leave_roster_on_next_observation(self):
        self.coordinator.observe_round()
        self.bridge.state["teams"]["crux"]["units"] = []
        self.bridge.state["tick"] = 20
        self.coordinator.observe_round()
        self.assertEqual(self.coordinator.sessions["B"].roster, frozenset())
        with self.assertRaises(CommandRejected):
            self.coordinator.command("B", {"team": "crux", "action": "move",
                                           "unitIds": [3], "x": 40, "y": 40})
        self.assertEqual(self.bridge.commands, [])

    def test_malformed_duplicate_roster_is_rejected(self):
        self.bridge.state["teams"]["crux"]["units"][0]["id"] = 1
        with self.assertRaises(ValueError):
            self.coordinator.observe_round()


if __name__ == "__main__":
    unittest.main()
