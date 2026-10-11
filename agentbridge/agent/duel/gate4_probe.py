"""Gate 4: two distinct small models decide from one frozen duel snapshot."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

from .coordinator import DuelBridge, DuelCoordinator
from .ollama_provider import DEFAULT_MODELS, DuelOllamaProvider
from .runtime import apply_slot_intent, resolve_slot_intent


def prepare(coordinator, providers):
    views = coordinator.observe_round()
    result = {"phase": "prepare", "worldId": views["A"]["worldId"],
              "tick": views["A"]["tick"], "models": {
                  agent_id: providers[agent_id].model for agent_id in ("A", "B")},
              "rosters": {agent_id: sorted(coordinator.sessions[agent_id].roster)
                          for agent_id in ("A", "B")},
              "initialHealth": {agent_id: {str(unit["id"]): unit["health"]
                                             for unit in views[agent_id]["own"]["units"]
                                             if unit["type"] == "dagger"}
                                for agent_id in ("A", "B")}}
    if not all(result["rosters"].values()) or views["A"]["gameOver"]:
        result["status"] = "invalid_fixture"
        return result

    def decide(agent_id):
        started = time.monotonic()
        decision, usage = providers[agent_id].decide(views[agent_id])
        return {"decision": decision, "usage": usage,
                "seconds": round(time.monotonic() - started, 3)}

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {agent_id: pool.submit(decide, agent_id) for agent_id in ("A", "B")}
        for agent_id in ("A", "B"):
            try:
                result[agent_id] = futures[agent_id].result()
            except Exception as error:
                result[agent_id] = {"error": f"{type(error).__name__}: {error}"}
    if any("error" in result[agent_id] for agent_id in ("A", "B")):
        result["status"] = "provider_error"
        return result

    fresh = coordinator.observe_round()
    if fresh != views:
        result["status"] = "stale_snapshot"
        return result
    try:
        commands = {agent_id: resolve_slot_intent(
            coordinator, agent_id, result[agent_id]["decision"]) for agent_id in ("A", "B")}
    except Exception as error:
        result["status"] = "invalid_decision"
        result["error"] = f"{type(error).__name__}: {error}"
        return result
    result["commands"] = commands
    result["actions"] = {}
    for agent_id in ("A", "B"):
        try:
            result["actions"][agent_id] = apply_slot_intent(
                coordinator, agent_id, result[agent_id]["decision"], commands[agent_id])
        except Exception as error:
            result["status"] = "command_error"
            result["error"] = f"{type(error).__name__}: {error}"
            return result
    result["status"] = "commands_accepted"
    return result


def check(coordinator, prior):
    views = coordinator.observe_round()
    a, b = views["A"], views["B"]
    result = {"phase": "check", "worldId": a["worldId"], "tick": a["tick"],
              "gameOver": a["gameOver"], "rosters": {
                  "A": sorted(coordinator.sessions["A"].roster),
                  "B": sorted(coordinator.sessions["B"].roster)},
              "fighters": {"A": sorted(unit["id"] for unit in a["own"]["units"]
                                      if unit["type"] == "dagger"),
                           "B": sorted(unit["id"] for unit in b["own"]["units"]
                                      if unit["type"] == "dagger")},
              "health": {"A": [unit["health"] for unit in a["own"]["units"]
                              if unit["type"] == "dagger"],
                         "B": [unit["health"] for unit in b["own"]["units"]
                              if unit["type"] == "dagger"]}}
    if prior is None or prior.get("status") != "commands_accepted":
        result["status"] = "missing_prepared_round"
    elif a["worldId"] != prior["worldId"] or a["tick"] <= prior["tick"]:
        result["status"] = "world_or_tick_not_advanced"
    else:
        baseline = prior.get("initialHealth", {})
        casualties = any(len(result["fighters"][side]) < len(baseline.get(side, {}))
                         for side in ("A", "B"))
        damage = any(
            unit["health"] < baseline.get(side, {}).get(str(unit["id"]), unit["health"])
            for side, view in (("A", a["own"]), ("B", b["own"]))
            for unit in view["units"] if unit["type"] == "dagger")
        result["status"] = "combat_observed" if casualties or damage else "no_damage_observed"
    alive_a, alive_b = bool(result["fighters"]["A"]), bool(result["fighters"]["B"])
    result["fixtureWinner"] = (
        "sharded" if alive_a and not alive_b else "crux" if alive_b and not alive_a
        else "DRAW" if not alive_a and not alive_b else "ONGOING")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "check"))
    parser.add_argument("--model-a", default=DEFAULT_MODELS["A"])
    parser.add_argument("--model-b", default=DEFAULT_MODELS["B"])
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    coordinator = DuelCoordinator(DuelBridge(), args.model_a, args.model_b)
    if args.phase == "prepare":
        result = prepare(coordinator, {"A": DuelOllamaProvider(args.model_a),
                                       "B": DuelOllamaProvider(args.model_b)})
    else:
        prior = None
        if args.log.exists():
            for line in args.log.read_text().splitlines():
                entry = json.loads(line)
                if entry.get("phase") == "prepare":
                    prior = entry
        result = check(coordinator, prior)
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a") as output:
        output.write(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    if result["status"] not in {"commands_accepted", "combat_observed"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
