"""Bounded demo-only two-model loop over one already prepared v159.7 world."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import json
from pathlib import Path
import time

from .coordinator import DuelBridge, DuelCoordinator
from .unified import UnifiedOllamaProvider, resolve_intent, summary


AUTO_MODELS = {"A": "deepseek-coder:6.7b-instruct",
               "B": "hf.co/zai-org/glm-edge-4b-chat-gguf:Q4_K_M"}
GUARD_CONTRACT = "DUEL_PAUSED_DECISION_GUARD_V1"
COMPLETED_RESULTS = frozenset({"CRUX_CORE_WIN", "SHARDED_CORE_WIN", "DRAW_CORE",
                               "SHARDED_FIGHTER_WIN", "CRUX_FIGHTER_WIN", "DRAW_FIGHTERS"})


def decision_snapshot(views):
    """Ignore only noncommandable observer alpha positions, not their other state.

    Alpha is absent from this demo's model summary and mechanical intent targets.
    Membership, health, observed commandability and every other unit still count.
    """
    frozen = copy.deepcopy(views)
    for view in frozen.values():
        for team in ("own", "enemy"):
            for unit in view[team]["units"]:
                if unit.get("type") == "alpha" and unit.get("commandable") is False:
                    unit.pop("x", None)
                    unit.pop("y", None)
    return frozen


def match_exit_code(result):
    return 0 if result.get("result") in COMPLETED_RESULTS else 2


def changed_paths(before, after, path=""):
    """Record which paused fields changed, without leaking their values."""
    if isinstance(before, dict) and isinstance(after, dict):
        keys = sorted(set(before) | set(after))
        return [item for key in keys
                for item in changed_paths(before.get(key), after.get(key),
                                          f"{path}/{key}")]
    if isinstance(before, list) and isinstance(after, list) and len(before) == len(after):
        return [item for index, (left, right) in enumerate(zip(before, after))
                for item in changed_paths(left, right, f"{path}/{index}")]
    return [] if before == after else [path]


def scoreboard(views):
    result = {}
    for side in ("A", "B"):
        own = views[side]["own"]
        result[side] = {
            "copper": own["resources"].get("copper", 0),
            "duo": own.get("economy", {}).get("duoSite", {}).get("status"),
            "factory": own.get("production", {}).get("factory", {}).get("status"),
            "factoryStock": own.get("production", {}).get("factory", {}).get("stock", {}),
            "factoryReserve": own.get("production", {}).get("factory", {})
            .get("supply", {}).get("stock", {}),
            "daggers": sorted(unit["id"] for unit in own["units"]
                              if unit["type"] == "dagger"),
            "coreHealth": [core["health"] for core in own["cores"]],
        }
    return result


def round_once(coordinator, providers, advance_ticks=1200, max_advance_seconds=40,
               poll_seconds=0.5, sleep=time.sleep, expected_world_id=None):
    views = coordinator.observe_round()
    if expected_world_id is not None and views["A"]["worldId"] != expected_world_id:
        raise ValueError("Decision round belongs to another world")
    if not views["A"].get("paused") or views["A"]["gameOver"]:
        raise ValueError("Start each decision round in a paused, active world")
    result = {"phase": "round", "worldId": views["A"]["worldId"],
              "guardContract": GUARD_CONTRACT,
              "tick": views["A"]["tick"], "models": {
                  side: providers[side].model for side in ("A", "B")},
              "observation": {side: summary(views[side]) for side in ("A", "B")},
              "before": scoreboard(views),
              "memoryInput": {side: copy.deepcopy(coordinator.sessions[side].prompt_state)
                              for side in ("A", "B")}}

    def decide(side):
        started = time.monotonic()
        choice, usage = providers[side].decide(views[side], result["memoryInput"][side])
        return {"choice": choice, "usage": usage,
                "seconds": round(time.monotonic() - started, 3)}

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {side: pool.submit(decide, side) for side in ("A", "B")}
        for side in ("A", "B"):
            try:
                result[side] = futures[side].result()
            except Exception as error:
                result[side] = {"error": f"{type(error).__name__}: {error}",
                                "errorType": type(error).__name__}
    if any("error" in result[side] for side in ("A", "B")):
        result["status"] = "provider_error"
        return result
    try:
        fresh = coordinator.observe_round()
    except Exception as error:
        result["status"] = "observation_error"
        result["errorType"] = type(error).__name__
        result["error"] = f"{type(error).__name__}: {error}"
        return result
    guarded_before, guarded_after = decision_snapshot(views), decision_snapshot(fresh)
    raw_changes = [path for side in ("A", "B")
                   for path in changed_paths(views[side], fresh[side], side)]
    guarded_changes = [path for side in ("A", "B")
                       for path in changed_paths(guarded_before[side], guarded_after[side], side)]
    result["ignoredObserverPositionChanges"] = [
        path for path in raw_changes if path not in guarded_changes][:20]
    if guarded_before != guarded_after:
        result["status"] = "stale_snapshot"
        result["staleChangedFields"] = guarded_changes[:20]
        return result
    result["commands"] = {}
    try:
        for side in ("A", "B"):
            result["commands"][side] = resolve_intent(
                coordinator, side, result[side]["choice"])
    except Exception as error:
        result["status"] = "invalid_decision"
        result["errorType"] = type(error).__name__
        result["error"] = f"{type(error).__name__}: {error}"
        return result
    result["actions"] = {}
    for side in ("A", "B"):
        command = result["commands"][side]
        try:
            result["actions"][side] = None if command is None else coordinator.command(side, command)
        except Exception as error:
            result["status"] = "command_error"
            result["errorType"] = type(error).__name__
            result["error"] = f"{type(error).__name__}: {error}"
            return result
    result["status"] = "commands_accepted"

    deadline = time.monotonic() + max_advance_seconds
    try:
        coordinator.bridge.control(result["worldId"], False)
        while True:
            current = coordinator.observe_round()
            if current["A"]["worldId"] != result["worldId"]:
                result["status"] = "world_changed"
                break
            if current["A"]["gameOver"] or current["A"]["tick"] >= result["tick"] + advance_ticks:
                break
            if time.monotonic() >= deadline:
                result["status"] = "advance_timeout"
                break
            sleep(poll_seconds)
    except Exception as error:
        result["status"] = "runtime_error"
        result["errorType"] = type(error).__name__
        result["error"] = f"{type(error).__name__}: {error}"
    finally:
        if result["status"] != "world_changed":
            try:
                coordinator.bridge.control(result["worldId"], True)
            except Exception as error:
                result["status"] = "pause_error"
                result["errorType"] = type(error).__name__
                result["pauseError"] = f"{type(error).__name__}: {error}"
    if result["status"] not in {"commands_accepted", "advance_timeout"}:
        return result
    try:
        after = coordinator.observe_round()
        if after["A"]["worldId"] != result["worldId"]:
            raise ValueError("World changed before round completion observation")
    except Exception as error:
        result["status"] = "observation_error"
        result["errorType"] = type(error).__name__
        result["error"] = f"{type(error).__name__}: {error}"
        return result
    result["afterTick"] = after["A"]["tick"]
    result["after"] = scoreboard(after)
    result["gameOver"] = after["A"]["gameOver"]
    for side in ("A", "B"):
        before_fighters = {team: [(unit["id"], unit["health"])
                                  for unit in views[side][team]["units"]
                                  if unit["type"] == "dagger"] for team in ("own", "enemy")}
        after_fighters = {team: [(unit["id"], unit["health"])
                                 for unit in after[side][team]["units"]
                                 if unit["type"] == "dagger"] for team in ("own", "enemy")}
        stalled = (bool(before_fighters["own"]) and bool(before_fighters["enemy"])
                   and before_fighters == after_fighters
                   and result["commands"][side] is not None)
        prior = coordinator.sessions[side].prompt_state.get("combatNoDamageRounds", 0)
        coordinator.sessions[side].prompt_state = {
            "lastIntent": result[side]["choice"]["intent"],
            "combatNoDamageRounds": min(8, prior + 1) if stalled else 0,
            "roundsRemaining": coordinator.sessions[side].prompt_state.get("roundsRemaining")}
    result["memoryOutput"] = {side: copy.deepcopy(coordinator.sessions[side].prompt_state)
                              for side in ("A", "B")}
    return result


def outcome(history, final):
    teams = final["teams"]
    a, b = teams["sharded"], teams["crux"]
    if not a["cores"] and b["cores"]:
        return "CRUX_CORE_WIN"
    if not b["cores"] and a["cores"]:
        return "SHARDED_CORE_WIN"
    if not a["cores"] and not b["cores"]:
        return "DRAW_CORE"
    attacked = any(
        item.get("status") == "commands_accepted"
        and all(item.get("before", {}).get(side, {}).get("daggers") for side in ("A", "B"))
        and any(command and command["action"] == "attack"
                and (item.get("actions", {}).get(side) or {}).get("accepted") is True
                for side, command in item.get("commands", {}).items())
        for item in history)
    if attacked:
        alive = {team: any(unit["type"] == "dagger" for unit in view["units"])
                 for team, view in teams.items()}
        if not alive["sharded"] and not alive["crux"]:
            return "DRAW_FIGHTERS"
        if alive["sharded"] != alive["crux"]:
            return "SHARDED_FIGHTER_WIN" if alive["sharded"] else "CRUX_FIGHTER_WIN"
    return "ONGOING"


def run_match(coordinator, providers, *, log, max_rounds=8, advance_ticks=1200,
              max_stale_retries=2):
    log.parent.mkdir(parents=True, exist_ok=True)
    initial = coordinator.bridge.observe()
    if (initial.get("paused") is not True or initial.get("gameOver")
            or not all(initial["teams"][team]["cores"] for team in ("sharded", "crux"))):
        raise ValueError("A paused, two-core fixture is required")
    world_id = initial["worldId"]
    history = []
    failure = None
    with log.open("a") as output:
        output.write(json.dumps({"phase": "start", "worldId": world_id,
                                 "tick": initial["tick"],
                                 "guardContract": GUARD_CONTRACT,
                                 "models": {side: providers[side].model for side in ("A", "B")}},
                                sort_keys=True) + "\n")
        output.flush()
        for index in range(max_rounds):
            for side in ("A", "B"):
                coordinator.sessions[side].prompt_state["roundsRemaining"] = max_rounds - index
            for attempt in range(max_stale_retries + 1):
                try:
                    result = round_once(coordinator, providers, advance_ticks=advance_ticks,
                                        expected_world_id=world_id)
                except Exception as error:
                    result = {"phase": "round", "worldId": world_id,
                              "status": "runtime_error", "errorType": type(error).__name__,
                              "error": f"{type(error).__name__}: {error}"}
                result["round"] = index + 1
                result["attempt"] = attempt + 1
                output.write(json.dumps(result, sort_keys=True) + "\n")
                output.flush()
                print(json.dumps({"round": index + 1, "attempt": attempt + 1,
                                  "status": result["status"], "tick": result.get("tick"),
                                  "choices": {
                                      side: result.get(side, {}).get("choice", {}).get("intent")
                                      for side in ("A", "B")},
                                  "after": result.get("after"),
                                  "staleChangedFields": result.get("staleChangedFields"),
                                  "ignoredObserverPositionChanges": result.get(
                                      "ignoredObserverPositionChanges", [])},
                                 sort_keys=True), flush=True)
                if result["status"] != "stale_snapshot":
                    break
            history.append(result)
            if result["status"] not in {"commands_accepted"}:
                failure = result
                break
            try:
                state = coordinator.bridge.observe()
                if state["worldId"] != world_id:
                    raise ValueError("World changed after decision round")
                terminal = outcome(history, state) != "ONGOING"
            except Exception as error:
                failure = {"status": "observation_error", "errorType": type(error).__name__,
                           "error": f"{type(error).__name__}: {error}"}
                break
            if terminal:
                break
        final, observed, scores = None, None, None
        try:
            candidate = coordinator.bridge.observe()
            if candidate["worldId"] != world_id:
                raise ValueError("Final observation belongs to another world")
            observed = outcome(history, candidate)
            scores = scoreboard({"A": {"own": candidate["teams"]["sharded"]},
                                 "B": {"own": candidate["teams"]["crux"]}})
            final = candidate
        except Exception as error:
            failure = failure or {"status": "final_observation_error",
                                  "errorType": type(error).__name__,
                                  "error": f"{type(error).__name__}: {error}"}
        if failure:
            timed_out = (failure["status"] == "advance_timeout"
                         or failure.get("errorType") == "TimeoutError"
                         or any(failure.get(side, {}).get("errorType") == "TimeoutError"
                                for side in ("A", "B")))
            verdict = "TIMEOUT" if timed_out else "INFRA_FAILURE"
            reason = failure["status"]
        elif observed in COMPLETED_RESULTS:
            verdict, reason = observed, "battlefield_terminal"
        else:
            verdict, reason = "TIMEOUT", "round_limit"
        finish = {"phase": "finish", "worldId": world_id,
                  "tick": final["tick"] if final else None,
                  "gameOver": final["gameOver"] if final else None,
                  "result": verdict, "observedOutcome": observed,
                  "terminationReason": reason,
                  "finalObservationVerified": final is not None,
                  "failure": failure, "rounds": len(history), "scoreboard": scores}
        output.write(json.dumps(finish, sort_keys=True) + "\n")
        output.flush()
    return finish


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-a", default=AUTO_MODELS["A"])
    parser.add_argument("--model-b", default=AUTO_MODELS["B"])
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--advance-ticks", type=int, default=1200)
    args = parser.parse_args()
    if not 1 <= args.rounds <= 20 or not 1 <= args.advance_ticks <= 3600:
        parser.error("rounds must be 1-20 and advance-ticks 1-3600")
    coordinator = DuelCoordinator(DuelBridge(), args.model_a, args.model_b)
    result = run_match(coordinator, {"A": UnifiedOllamaProvider(args.model_a),
                                     "B": UnifiedOllamaProvider(args.model_b)},
                       log=args.log, max_rounds=args.rounds,
                       advance_ticks=args.advance_ticks)
    print(json.dumps(result, sort_keys=True))
    raise SystemExit(match_exit_code(result))


if __name__ == "__main__":
    main()
