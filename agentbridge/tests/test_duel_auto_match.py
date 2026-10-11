import copy
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "agent"))
from duel.auto_match import decision_snapshot, match_exit_code, outcome, round_once, run_match
from duel.coordinator import DuelCoordinator
from duel.unified import decision_prompt, legal_intents, resolve_intent, summary


def fixture():
    def team(core_y, base_id):
        return {"resources": {"copper": 0, "lead": 0},
                "cores": [{"x": 159, "y": core_y, "health": 1100}],
                "economy": {"nearbyCopperOreTiles": 25,
                            "duoSite": {"x": 151, "y": core_y, "status": "empty",
                                        "placeable": True, "copperCost": 35}},
                "production": {"factory": {"x": 151, "y": core_y + 6,
                                           "status": "idle",
                                           "stock": {"silicon": 10, "lead": 10},
                                           "cost": {"silicon": 10, "lead": 10}}},
                "units": [{"id": base_id, "type": "mono", "health": 100,
                           "maxHealth": 100, "commandable": True},
                          {"id": base_id + 1, "type": "poly", "health": 400,
                           "maxHealth": 400, "commandable": True}]}
    return {"contract": "DUEL_DEMO_OMNISCIENT_V0", "worldId": "fixture",
            "tick": 0, "paused": True, "gameOver": False,
            "teams": {"sharded": team(52, 1), "crux": team(132, 3)}}


class Bridge:
    def __init__(self):
        self.state = fixture()
        self.commands = []
        self.controls = []

    def observe(self):
        return copy.deepcopy(self.state)

    def command(self, command):
        self.commands.append(copy.deepcopy(command))
        return {"accepted": True, "team": command["team"], "action": command["action"]}

    def control(self, world_id, paused):
        if world_id != self.state["worldId"]:
            raise ValueError("wrong world")
        self.controls.append(paused)
        self.state["paused"] = paused
        if not paused:
            self.state["tick"] += 1200
        return {"worldId": world_id, "paused": paused, "tick": self.state["tick"]}


class Provider:
    def __init__(self, model, intent, barrier=None, error=None):
        self.model, self.intent, self.barrier, self.error = model, intent, barrier, error

    def decide(self, observation, memory=None):
        if self.barrier:
            self.barrier.wait(timeout=2)
        if self.error:
            raise self.error
        return {"intent": self.intent, "reason": "chosen"}, {"reportedModel": self.model}


class AutoMatchTests(unittest.TestCase):
    def run_logged_match(self, bridge, providers=None, **options):
        coordinator = DuelCoordinator(bridge, "deepseek", "glm")
        providers = providers or {"A": Provider("deepseek", "WAIT"),
                                  "B": Provider("glm", "WAIT")}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            result = run_match(coordinator, providers, log=path, **options)
            events = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(events[-1], result)
        return result, events

    def test_cross_phase_legal_choices_and_mechanical_resolution(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge, "deepseek-r1:1.5b", "glm-edge:1.5b")
        view = coordinator.observe_round()["A"]
        self.assertEqual(legal_intents(view), ["MINE", "PRODUCE", "WAIT"])
        self.assertEqual(resolve_intent(coordinator, "A", {"intent": "MINE"})["unitIds"], [1])
        self.assertEqual(resolve_intent(coordinator, "A", {"intent": "PRODUCE"})["buildingY"], 58)
        bridge.state["teams"]["sharded"]["resources"]["copper"] = 40
        view = coordinator.observe_round()["A"]
        self.assertIn("BUILD", legal_intents(view))
        self.assertNotIn("MINE", legal_intents(view))
        self.assertEqual(resolve_intent(coordinator, "A", {"intent": "BUILD"})["unitIds"], [2])
        for team, uid in (("sharded", 5), ("crux", 6)):
            bridge.state["teams"][team]["units"].append(
                {"id": uid, "type": "dagger", "health": 150,
                 "maxHealth": 150, "commandable": True})
        view = coordinator.observe_round()["A"]
        self.assertIn("ATTACK_0", legal_intents(view))
        self.assertEqual(resolve_intent(coordinator, "A", {"intent": "ATTACK_0"})
                         ["targetUnitId"], 6)
        self.assertNotIn('"id"', decision_prompt(view))
        self.assertNotIn('"worldId"', decision_prompt(view))
        self.assertEqual(set(summary(view)), {"own", "enemy"})

    def test_parallel_round_uses_frozen_snapshot_and_controls_advance(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge, "deepseek-r1:1.5b", "glm-edge:1.5b")
        barrier = threading.Barrier(2)
        result = round_once(coordinator, {
            "A": Provider("deepseek-r1:1.5b", "MINE", barrier),
            "B": Provider("glm-edge:1.5b", "PRODUCE", barrier)},
            sleep=lambda _: None)
        self.assertEqual(result["status"], "commands_accepted")
        self.assertEqual(result["afterTick"], 1200)
        self.assertEqual(bridge.controls, [False, True])
        self.assertEqual([cmd["team"] for cmd in bridge.commands], ["sharded", "crux"])
        self.assertEqual([cmd["action"] for cmd in bridge.commands], ["mine", "produce"])

    def test_provider_failure_stops_round_without_substitute_strategy(self):
        bridge = Bridge()
        coordinator = DuelCoordinator(bridge, "deepseek-r1:1.5b", "glm-edge:1.5b")
        result = round_once(coordinator, {
            "A": Provider("deepseek-r1:1.5b", "MINE", error=TimeoutError("late")),
            "B": Provider("glm-edge:1.5b", "MINE")}, sleep=lambda _: None)
        self.assertIn("TimeoutError", result["A"]["error"])
        self.assertEqual(result["status"], "provider_error")
        self.assertNotIn("commands", result)
        self.assertEqual(bridge.commands, [])
        self.assertEqual(bridge.controls, [])

    def test_reserved_items_require_a_real_supply_route(self):
        bridge = Bridge()
        for team in bridge.state["teams"].values():
            factory = team["production"]["factory"]
            factory["stock"] = {"silicon": 0, "lead": 0}
            factory["supply"] = {"routeReady": True,
                                 "stock": {"silicon": 10, "lead": 10}}
        coordinator = DuelCoordinator(bridge, "deepseek", "glm")
        view = coordinator.observe_round()["A"]
        self.assertIn("PRODUCE", legal_intents(view))
        coordinator.command("A", resolve_intent(coordinator, "A", {"intent": "PRODUCE"}))
        bridge.state["teams"]["crux"]["production"]["factory"]["supply"]["routeReady"] = False
        view = coordinator.observe_round()["B"]
        self.assertNotIn("PRODUCE", legal_intents(view))
        with self.assertRaises(ValueError):
            coordinator.command("B", {"team": "crux", "action": "produce",
                                      "buildingX": 151, "buildingY": 138, "unit": "dagger"})

    def test_one_stale_snapshot_retries_fresh_decisions_without_commands(self):
        class OnceStaleBridge(Bridge):
            def __init__(self):
                super().__init__()
                self.reads = 0

            def observe(self):
                self.reads += 1
                if self.reads == 3:
                    self.state["teams"]["sharded"]["resources"]["lead"] = 1
                return super().observe()

        bridge = OnceStaleBridge()
        coordinator = DuelCoordinator(bridge, "deepseek", "glm")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "match.jsonl"
            result = run_match(coordinator,
                               {"A": Provider("deepseek", "WAIT"),
                                "B": Provider("glm", "WAIT")},
                               log=path, max_rounds=1)
            rounds = [json.loads(line) for line in path.read_text().splitlines()
                      if json.loads(line)["phase"] == "round"]
        self.assertEqual([item["status"] for item in rounds],
                         ["stale_snapshot", "commands_accepted"])
        self.assertEqual([item["attempt"] for item in rounds], [1, 2])
        self.assertIn("A/own/resources/lead", rounds[0]["staleChangedFields"])
        self.assertEqual(bridge.commands, [])
        self.assertEqual(bridge.controls, [False, True])
        self.assertEqual(result["rounds"], 1)

    def test_worker_survivors_do_not_turn_fighter_draw_into_win(self):
        state = fixture()
        history = [{"status": "commands_accepted", "before": {
            "A": {"daggers": [5]}, "B": {"daggers": [6]}},
            "commands": {"A": {"action": "attack"}}, "actions": {"A": {"accepted": True}}}]
        self.assertEqual(outcome(history, state),
                         "DRAW_FIGHTERS")

    def test_noncommandable_observer_drift_does_not_repeat_model_calls(self):
        class ObserverBridge(Bridge):
            def __init__(self):
                super().__init__()
                self.state["teams"]["sharded"]["units"].append({
                    "id": 20, "type": "alpha", "health": 150, "maxHealth": 150,
                    "commandable": False, "x": 1, "y": 2})

            def observe(self):
                self.state["teams"]["sharded"]["units"][-1]["y"] += 1
                return super().observe()

        bridge = ObserverBridge()
        coordinator = DuelCoordinator(bridge, "deepseek", "glm")
        before = coordinator.observe_round()
        guarded = decision_snapshot(before)
        self.assertIn("y", before["A"]["own"]["units"][-1])
        self.assertNotIn("y", guarded["A"]["own"]["units"][-1])
        providers = {"A": Provider("deepseek", "MINE"), "B": Provider("glm", "MINE")}
        with patch.object(providers["A"], "decide", wraps=providers["A"].decide) as calls:
            result = round_once(coordinator, providers, sleep=lambda _: None)
        self.assertEqual(calls.call_count, 1)
        self.assertEqual(result["status"], "commands_accepted")
        self.assertEqual(result["ignoredObserverPositionChanges"],
                         ["A/own/units/2/y", "B/enemy/units/2/y"])
        self.assertEqual([item["action"] for item in bridge.commands], ["mine", "mine"])
        after = coordinator.observe_round()
        self.assertEqual(summary(before["A"]), summary(after["A"]))
        self.assertEqual(legal_intents(before["A"]), legal_intents(after["A"]))

    def test_guard_still_rejects_relevant_changes(self):
        for change in ("observer-health", "observer-controller", "observer-membership",
                       "commandable-alpha-position", "mono-position", "poly-position",
                       "dagger-position", "unknown-unit-position", "resource", "world", "tick"):
            with self.subTest(change=change):
                class MutatingBridge(Bridge):
                    reads = 0

                    def observe(self):
                        self.reads += 1
                        if self.reads == 2:
                            units = self.state["teams"]["sharded"]["units"]
                            if change == "observer-health":
                                units[2]["health"] -= 1
                            elif change == "observer-controller":
                                units[2]["commandable"] = True
                            elif change == "observer-membership":
                                units.pop(2)
                            elif change == "commandable-alpha-position":
                                units[2]["x"] += 1
                            elif change == "mono-position":
                                units[0]["x"] = 1
                            elif change == "poly-position":
                                units[1]["x"] = 1
                            elif change in {"dagger-position", "unknown-unit-position"}:
                                units[3]["x"] += 1
                            elif change == "resource":
                                self.state["teams"]["sharded"]["resources"]["copper"] = 40
                            elif change == "world":
                                self.state["worldId"] = "new-world"
                            else:
                                self.state["tick"] += 1
                        return super().observe()

                bridge = MutatingBridge()
                bridge.state["teams"]["sharded"]["units"].extend([
                    {"id": 20, "type": "alpha", "health": 150, "maxHealth": 150,
                     "commandable": change == "commandable-alpha-position", "x": 1, "y": 2},
                    {"id": 21, "type": "flare" if change == "unknown-unit-position" else "dagger",
                     "health": 150, "maxHealth": 150, "commandable": True, "x": 1, "y": 2}])
                result = round_once(DuelCoordinator(bridge, "deepseek", "glm"),
                                    {"A": Provider("deepseek", "WAIT"),
                                     "B": Provider("glm", "WAIT")})
                self.assertEqual(result["status"], "stale_snapshot")
                self.assertTrue(result["staleChangedFields"])
                self.assertEqual(bridge.commands, [])
                self.assertEqual(bridge.controls, [])

    def test_planned_or_rejected_attack_is_not_a_fighter_draw(self):
        for status in ("command_error", "invalid_decision", "stale_snapshot", "commands_accepted"):
            history = [{"status": status, "before": {
                "A": {"daggers": [5]}, "B": {"daggers": [6]}},
                "commands": {"A": {"action": "attack"}},
                "actions": {"A": {"accepted": False}}}]
            self.assertEqual(outcome(history, fixture()), "ONGOING")

    def test_partial_command_failure_is_preserved_and_exits_nonzero(self):
        class PartialBridge(Bridge):
            def command(self, payload):
                if payload["team"] == "crux":
                    for team in self.state["teams"].values():
                        team["units"] = [unit for unit in team["units"] if unit["type"] != "dagger"]
                    raise OSError("second command connection failed")
                return super().command(payload)

        bridge = PartialBridge()
        for team, uid in (("sharded", 5), ("crux", 6)):
            bridge.state["teams"][team]["units"].append({"id": uid, "type": "dagger",
                "health": 150, "maxHealth": 150, "commandable": True})
        result, events = self.run_logged_match(bridge, {
            "A": Provider("deepseek", "ATTACK_0"), "B": Provider("glm", "ATTACK_0")})
        self.assertEqual(events[1]["status"], "command_error")
        self.assertTrue(events[1]["actions"]["A"]["accepted"])
        self.assertNotIn("B", events[1]["actions"])
        self.assertEqual(result["result"], "INFRA_FAILURE")
        self.assertEqual(result["observedOutcome"], "ONGOING")
        self.assertEqual(match_exit_code(result), 2)

    def test_failure_overrides_an_observed_core_win(self):
        bridge = Bridge()

        class DestructiveFailureProvider(Provider):
            def decide(self, *args):
                bridge.state["teams"]["crux"]["cores"] = []
                raise ValueError("invalid model output")

        result, _ = self.run_logged_match(bridge, {
            "A": DestructiveFailureProvider("deepseek", "WAIT"),
            "B": Provider("glm", "WAIT")})
        self.assertEqual(result["observedOutcome"], "SHARDED_CORE_WIN")
        self.assertEqual(result["result"], "INFRA_FAILURE")
        self.assertEqual(result["terminationReason"], "provider_error")
        self.assertEqual(match_exit_code(result), 2)

    def test_round_budget_is_timeout_not_a_draw(self):
        result, _ = self.run_logged_match(Bridge(), max_rounds=1)
        self.assertEqual(result["result"], "TIMEOUT")
        self.assertEqual(result["observedOutcome"], "ONGOING")
        self.assertEqual(result["terminationReason"], "round_limit")
        self.assertEqual(match_exit_code(result), 2)

    def test_provider_timeout_has_no_commands_and_a_durable_finish(self):
        bridge = Bridge()
        result, _ = self.run_logged_match(bridge, {
            "A": Provider("deepseek", "MINE", error=TimeoutError("late")),
            "B": Provider("glm", "MINE")})
        self.assertEqual(result["result"], "TIMEOUT")
        self.assertEqual(result["failure"]["A"]["errorType"], "TimeoutError")
        self.assertEqual(bridge.commands, [])
        self.assertEqual(bridge.controls, [])

    def test_connection_loss_after_dispatch_preserves_actions_and_unknown_final(self):
        class FailingBridge(Bridge):
            failed = False

            def control(self, world_id, paused):
                result = super().control(world_id, paused)
                if not paused:
                    self.failed = True
                return result

            def observe(self):
                if self.failed:
                    raise OSError("connection lost")
                return super().observe()

        bridge = FailingBridge()
        result, events = self.run_logged_match(bridge, {
            "A": Provider("deepseek", "MINE"), "B": Provider("glm", "MINE")})
        self.assertEqual(result["result"], "INFRA_FAILURE")
        self.assertFalse(result["finalObservationVerified"])
        self.assertIsNone(result["observedOutcome"])
        self.assertIsNone(result["tick"])
        self.assertIsNone(result["scoreboard"])
        self.assertTrue(events[1]["actions"]["A"]["accepted"])
        self.assertEqual(bridge.controls, [False, True])

    def test_world_replacement_is_failure_without_pausing_the_new_world(self):
        class ReplacedBridge(Bridge):
            def control(self, world_id, paused):
                result = super().control(world_id, paused)
                if not paused:
                    self.state["worldId"] = "replacement"
                return result

        bridge = ReplacedBridge()
        result, events = self.run_logged_match(bridge)
        self.assertEqual(events[1]["status"], "world_changed")
        self.assertEqual(result["result"], "INFRA_FAILURE")
        self.assertFalse(result["finalObservationVerified"])
        self.assertEqual(bridge.controls, [False])

    def test_pause_failure_does_not_report_a_completed_match(self):
        class PauseFailureBridge(Bridge):
            def control(self, world_id, paused):
                if paused:
                    raise OSError("pause endpoint failed")
                return super().control(world_id, paused)

        result, events = self.run_logged_match(PauseFailureBridge())
        self.assertEqual(events[1]["status"], "pause_error")
        self.assertIn("pause endpoint failed", events[1]["pauseError"])
        self.assertEqual(result["result"], "INFRA_FAILURE")
        self.assertEqual(match_exit_code(result), 2)

    def test_command_timeout_is_distinct_from_completed_combat(self):
        class CommandTimeoutBridge(Bridge):
            def command(self, payload):
                raise TimeoutError("command endpoint did not respond")

        bridge = CommandTimeoutBridge()
        result, _ = self.run_logged_match(bridge, {
            "A": Provider("deepseek", "MINE"), "B": Provider("glm", "MINE")})
        self.assertEqual(result["result"], "TIMEOUT")
        self.assertEqual(result["terminationReason"], "command_error")
        self.assertEqual(bridge.controls, [])

    def test_advance_deadline_preserves_commands_but_marks_timeout(self):
        bridge = Bridge()
        real_round = round_once
        with patch("duel.auto_match.round_once", side_effect=lambda *args, **kwargs:
                   real_round(*args, max_advance_seconds=0, **kwargs)):
            result, events = self.run_logged_match(bridge, {
                "A": Provider("deepseek", "MINE"), "B": Provider("glm", "MINE")},
                max_rounds=1, advance_ticks=2400)
        self.assertEqual(events[1]["status"], "advance_timeout")
        self.assertTrue(events[1]["actions"]["A"]["accepted"])
        self.assertEqual(result["result"], "TIMEOUT")
        self.assertEqual(result["terminationReason"], "advance_timeout")
        self.assertEqual(bridge.controls, [False, True])

    def test_completed_draw_remains_a_successful_process_result(self):
        self.assertEqual(match_exit_code({"result": "DRAW_FIGHTERS"}), 0)
        self.assertEqual(match_exit_code({"result": "ONGOING"}), 2)
        self.assertEqual(match_exit_code({"result": "unexpected"}), 2)

    def test_bounded_no_damage_memory_reaches_next_model_prompt(self):
        bridge = Bridge()
        for team, uid in (("sharded", 5), ("crux", 6)):
            bridge.state["teams"][team]["units"].append(
                {"id": uid, "type": "dagger", "health": 150,
                 "maxHealth": 150, "commandable": True})
        coordinator = DuelCoordinator(bridge, "deepseek", "glm")
        providers = {"A": Provider("deepseek", "DEFEND"),
                     "B": Provider("glm", "DEFEND")}
        first = round_once(coordinator, providers, sleep=lambda _: None)
        second = round_once(coordinator, providers, sleep=lambda _: None)
        self.assertEqual(first["memoryOutput"]["A"]["combatNoDamageRounds"], 1)
        self.assertEqual(second["memoryInput"]["A"]["combatNoDamageRounds"], 1)
        self.assertEqual(second["memoryOutput"]["B"]["combatNoDamageRounds"], 2)
        self.assertIn("ATTACK_N starts combat", decision_prompt(
            coordinator.observe_round()["A"], second["memoryOutput"]["A"]))


if __name__ == "__main__":
    unittest.main()
