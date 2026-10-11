from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from logistics_planner import (ConveyorStep, FlowVerifier, choose_plan, find_route,
                               plan_complete, resources_sufficient)


DRILL = ((0, 0), (0, 1), (1, 0), (1, 1))


def observation(cells=None, candidates=None):
    cells = cells or [(x, 0, 15) for x in (2, 3, 4)]
    candidates = candidates or [{"tileX": 0, "tileY": 0, "oreItem": "copper",
                                 "oreTiles": 4, "footprint": [list(p) for p in DRILL]}]
    return {"core": {"tileX": 5, "tileY": 0, "size": 1, "footprint": [[5, 0]],
                     "copper": 40, "receivedCopper": 0},
            "content": {"drill": {"name": "mechanical-drill", "size": 2,
                                     "requirements": {"copper": 12}},
                        "conveyor": {"name": "conveyor", "size": 1,
                                     "requirements": {"copper": 1}}},
            "conveyorCells": [list(cell) for cell in cells],
            "drillCandidates": candidates, "buildings": []}


class RouteTests(unittest.TestCase):
    def test_route_is_contiguous_and_rotated_toward_core(self):
        route = find_route({(x, 0): 15 for x in (2, 3, 4)}, DRILL, {(5, 0)})
        self.assertEqual(route, tuple(ConveyorStep(x, 0, 0) for x in (2, 3, 4)))

    def test_route_avoids_obstacle_and_turns(self):
        points = [(0, 2), (0, 3), (1, 3), (2, 3), (3, 3), (4, 3),
                  (4, 2), (4, 1), (4, 0)]
        route = find_route({p: 15 for p in points}, DRILL, {(5, 0)})
        self.assertEqual([(s.x, s.y) for s in route], points)
        self.assertEqual([s.rotation for s in route], [1, 0, 0, 0, 0, 3, 3, 3, 0])
        self.assertNotIn((3, 0), [(s.x, s.y) for s in route])

    def test_invalid_or_missing_route(self):
        self.assertIsNone(find_route({(2, 0): 1}, DRILL, {(5, 0)}))
        with self.assertRaisesRegex(ValueError, "No valid copper"):
            choose_plan(observation(cells=[(2, 0, 1)]))


class SelectionAndCostTests(unittest.TestCase):
    def test_candidate_selection_and_actual_costs(self):
        plan = choose_plan(observation(), safety_margin=10)
        self.assertEqual((plan.drill_x, plan.drill_y, plan.ore_tiles), (0, 0, 4))
        self.assertEqual(plan.drill_cost, 12)
        self.assertEqual(plan.conveyor_cost, 1)
        self.assertEqual(plan.construction_cost, 15)
        self.assertEqual(plan.required_copper, 25)

    def test_insufficient_resources(self):
        plan = choose_plan(observation(), safety_margin=10)
        self.assertFalse(resources_sufficient(24, plan))
        self.assertTrue(resources_sufficient(25, plan))
        self.assertFalse(resources_sufficient(True, plan))


class VerificationTests(unittest.TestCase):
    def plan_and_state(self):
        plan = choose_plan(observation(), safety_margin=0)
        buildings = [{"tileX": 0, "tileY": 0, "block": "mechanical-drill",
                      "team": "sharded", "dominantItem": "copper",
                      "lastDrillSpeed": 0.1, "copper": 0}]
        buildings.extend({"tileX": s.x, "tileY": s.y, "block": "conveyor",
                          "team": "sharded", "rotation": s.rotation, "copper": 0}
                         for s in plan.conveyors)
        state = {"team": "sharded", "logistics": {"core": {
            "copper": 20, "receivedCopper": 3}, "buildings": buildings}}
        return plan, state

    def test_completion_requires_exact_blocks_and_rotations(self):
        plan, state = self.plan_and_state()
        self.assertTrue(plan_complete(state, plan))
        state["logistics"]["buildings"][1]["rotation"] = 2
        self.assertFalse(plan_complete(state, plan))
        state["logistics"]["buildings"][1].update(block="build1", constructing="conveyor")
        self.assertFalse(plan_complete(state, plan))

    def test_resource_flow_requires_isolation_drill_conveyor_and_core_gain(self):
        plan, state = self.plan_and_state()
        verifier = FlowVerifier(state, plan)
        self.assertFalse(verifier.update(state, "copper", True))
        self.assertFalse(verifier.update(state, "lead", True))
        state["logistics"]["buildings"][1]["copper"] = 1
        self.assertFalse(verifier.update(state, "lead", True))
        state["logistics"]["core"].update(copper=21, receivedCopper=4)
        self.assertTrue(verifier.update(state, "lead", True))
        self.assertEqual(verifier.evidence()["conveyorCopperSeen"], True)


if __name__ == "__main__":
    unittest.main()
