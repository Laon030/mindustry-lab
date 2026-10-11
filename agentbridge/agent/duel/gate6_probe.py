"""Gate 6 headless proof: model-selected vanilla Dagger production."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time

from .coordinator import DuelBridge, DuelCoordinator
from .ollama_provider import DEFAULT_MODELS
from .production import ProductionOllamaProvider, production_summary, resolve_intent


def summarize(views):
    return {side: production_summary(views[side]) for side in ("A", "B")}


def run_round(coordinator, providers):
    views = coordinator.observe_round()
    result = {"phase": "round", "worldId": views["A"]["worldId"],
              "tick": views["A"]["tick"], "before": summarize(views),
              "models": {side: providers[side].model for side in ("A", "B")}}
    if views["A"]["gameOver"] or not all(
            views[side]["own"]["cores"] for side in ("A", "B")):
        result["status"] = "invalid_fixture"
        return result

    def decide(side):
        started = time.monotonic()
        choice, usage = providers[side].decide(views[side])
        return {"choice": choice, "usage": usage,
                "seconds": round(time.monotonic() - started, 3)}

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {side: pool.submit(decide, side) for side in ("A", "B")}
        for side in ("A", "B"):
            try:
                result[side] = futures[side].result()
            except Exception as failure:
                result[side] = {"error": f"{type(failure).__name__}: {failure}"}
    if any("error" in result[side] for side in ("A", "B")):
        result["status"] = "provider_error"
        return result
    if coordinator.observe_round() != views:
        result["status"] = "stale_snapshot"
        return result
    try:
        commands = {side: resolve_intent(coordinator, side, result[side]["choice"])
                    for side in ("A", "B")}
    except Exception as failure:
        result["status"] = "invalid_decision"
        result["error"] = f"{type(failure).__name__}: {failure}"
        return result
    result["commands"] = commands
    result["actions"] = {}
    for side in ("A", "B"):
        try:
            result["actions"][side] = (
                None if commands[side] is None else coordinator.command(side, commands[side]))
        except Exception as failure:
            result["status"] = "command_error"
            result["error"] = f"{type(failure).__name__}: {failure}"
            return result
    result["status"] = "commands_accepted"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("round", "observe"))
    parser.add_argument("--model-a", default=DEFAULT_MODELS["A"])
    parser.add_argument("--model-b", default=DEFAULT_MODELS["B"])
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    coordinator = DuelCoordinator(DuelBridge(), args.model_a, args.model_b)
    if args.phase == "round":
        result = run_round(coordinator, {"A": ProductionOllamaProvider(args.model_a),
                                         "B": ProductionOllamaProvider(args.model_b)})
    else:
        views = coordinator.observe_round()
        result = {"phase": "observe", "worldId": views["A"]["worldId"],
                  "tick": views["A"]["tick"], "state": summarize(views),
                  "gameOver": views["A"]["gameOver"]}
    args.log.parent.mkdir(parents=True, exist_ok=True)
    with args.log.open("a") as output:
        output.write(json.dumps(result, sort_keys=True) + "\n")
    print(json.dumps(result, sort_keys=True))
    if result.get("status") not in {None, "commands_accepted"}:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
