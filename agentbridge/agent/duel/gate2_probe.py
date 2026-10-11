"""Repeatable, scripted Gate 2 runtime probe; no model or strategy policy."""

import argparse
import json
from pathlib import Path

from .coordinator import CommandRejected, DuelBridge, DuelCoordinator


def run(phase, bridge):
    coordinator = DuelCoordinator(bridge)
    views = coordinator.observe_round()
    if views["A"]["tick"] != views["B"]["tick"]:
        raise AssertionError("Team observations came from different ticks")
    a = sorted(coordinator.sessions["A"].roster)
    b = sorted(coordinator.sessions["B"].roster)
    result = {"phase": phase, "worldId": views["A"]["worldId"],
              "tick": views["A"]["tick"], "rosterA": a, "rosterB": b,
              "gameOver": views["A"]["gameOver"]}
    if phase == "prepare":
        if len(a) < 2 or not b:
            raise AssertionError("The scripted probe requires at least 2 A and 1 B units")
        result["opponentIdRejected"] = []
        for agent_id, team, enemy_id in (("A", "sharded", b[0]), ("B", "crux", a[0])):
            try:
                coordinator.command(agent_id, {"team": team, "action": "attack",
                                               "unitIds": [enemy_id], "targetUnitId": a[0]})
            except CommandRejected as rejected:
                result["opponentIdRejected"].append({"agent": agent_id, "reason": str(rejected)})
            else:
                raise AssertionError("Opponent unit command was accepted")
        result["acceptedA"] = coordinator.command("A", {
            "team": "sharded", "action": "attack", "unitIds": a, "targetUnitId": b[0]})
        result["acceptedB"] = coordinator.command("B", {
            "team": "crux", "action": "attack", "unitIds": [b[0]], "targetUnitId": a[0]})
        result["decisionCounters"] = {
            agent_id: session.decision_counter for agent_id, session in coordinator.sessions.items()}
    else:
        result["fixtureWinner"] = (
            "sharded" if a and not b else "crux" if b and not a else
            "DRAW" if not a and not b else "ONGOING"
        )
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("prepare", "check"))
    parser.add_argument("--log", type=Path)
    args = parser.parse_args()
    result = run(args.phase, DuelBridge())
    line = json.dumps(result, sort_keys=True)
    print(line)
    if args.log:
        args.log.parent.mkdir(parents=True, exist_ok=True)
        with args.log.open("a") as output:
            output.write(line + "\n")


if __name__ == "__main__":
    main()
