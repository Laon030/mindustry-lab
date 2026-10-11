"""Gate 3 probe: one real model decision versus a scripted Crux attack."""

import argparse
import json
from pathlib import Path
import time

from .coordinator import DuelBridge, DuelCoordinator
from .provider import DEFAULT_MODEL, DuelOpenCodeProvider
from .ollama_provider import DEFAULT_MODELS, DuelOllamaProvider
from .runtime import apply_intent, apply_slot_intent, resolve_slot_intent


def run(phase, model, provider_type="opencode"):
    coordinator = DuelCoordinator(DuelBridge(), model_a=model, model_b="scripted-gate3")
    views = coordinator.observe_round()
    a = sorted(coordinator.sessions["A"].roster)
    b = sorted(coordinator.sessions["B"].roster)
    result = {"phase": phase, "worldId": views["A"]["worldId"],
              "tick": views["A"]["tick"], "rosterA": a, "rosterB": b,
              "gameOver": views["A"]["gameOver"]}
    if phase == "prepare":
        if len(a) < 2 or len(b) != 1:
            raise AssertionError("Gate 3 probe requires two A and one B live fighters")
        provider = (DuelOllamaProvider(model=model) if provider_type == "ollama"
                    else DuelOpenCodeProvider(model=model))
        started = time.monotonic()
        decision, usage = provider.decide(views["A"])
        result["modelA"] = model
        result["modelB"] = "scripted-gate3"
        result["llmDecision"] = decision
        result["llmSeconds"] = round(time.monotonic() - started, 3)
        result["usage"] = usage
        if provider_type == "ollama":
            command = resolve_slot_intent(coordinator, "A", decision)
            result["actionA"] = apply_slot_intent(coordinator, "A", decision, command)
        else:
            result["actionA"] = apply_intent(coordinator, "A", decision)
        result["actionB"] = coordinator.command("B", {"team": "crux", "action": "attack",
                                                       "unitIds": b, "targetUnitId": a[0]})
    else:
        result["fixtureWinner"] = (
            "sharded" if a and not b else "crux" if b and not a else
            "DRAW" if not a and not b else "ONGOING")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "check"))
    parser.add_argument("--model")
    parser.add_argument("--provider", choices=("opencode", "ollama"), default="opencode")
    parser.add_argument("--log", type=Path)
    args = parser.parse_args()
    model = args.model or (DEFAULT_MODELS["A"] if args.provider == "ollama" else DEFAULT_MODEL)
    result = run(args.phase, model, args.provider)
    line = json.dumps(result, sort_keys=True)
    print(line)
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        with args.log.open("a") as output:
            output.write(line + "\n")


if __name__ == "__main__":
    main()
