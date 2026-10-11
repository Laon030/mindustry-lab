"""Gate 2: independent team sessions and mechanical ownership enforcement.

The localhost Java endpoint is not an agent identity boundary. Only this
coordinator may submit demo actions; each live unit roster is replaced from the
latest actual game snapshot before a command is accepted.
"""

from dataclasses import dataclass, field
import copy
import json
import math
import urllib.error
import urllib.request


CONTRACT = "DUEL_DEMO_OMNISCIENT_V0"
TEAMS = {"A": "sharded", "B": "crux"}


class CommandRejected(ValueError):
    pass


class DuelBridge:
    def __init__(self, base="http://127.0.0.1:8765", timeout=7):
        self.base, self.timeout = base, timeout

    def _request(self, path, payload=None):
        request = urllib.request.Request(
            self.base + path,
            data=None if payload is None else json.dumps(payload, allow_nan=False).encode(),
            headers={"Content-Type": "application/json"},
            method="GET" if payload is None else "POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode())
        except urllib.error.HTTPError as error:
            raise CommandRejected(f"Bridge HTTP {error.code}: {error.read().decode(errors='replace')}") from error
        if not isinstance(result, dict) or result.get("error"):
            raise CommandRejected(f"Invalid Bridge response: {result}")
        return result

    def observe(self):
        return self._request("/duel/state")

    def command(self, payload):
        return self._request("/duel/action", payload)

    def control(self, world_id, paused):
        if not isinstance(world_id, str) or type(paused) is not bool:
            raise ValueError("World ID and boolean pause state required")
        result = self._request("/duel/control", {"worldId": world_id, "paused": paused})
        if result.get("worldId") != world_id or result.get("paused") is not paused:
            raise CommandRejected("Duel pause state was not applied")
        return result


@dataclass
class AgentSession:
    agent_id: str
    team: str
    model: str | None = None
    provider: object | None = None
    prompt_state: dict = field(default_factory=dict)
    context: dict | None = None
    decision_counter: int = 0
    last_decision: dict | None = None
    log: list = field(default_factory=list)
    roster: frozenset[int] = frozenset()
    observation: dict | None = None


class DuelCoordinator:
    def __init__(self, bridge, model_a=None, model_b=None, provider_a=None, provider_b=None):
        if model_a is not None and model_b is not None and model_a == model_b:
            raise ValueError("Duel agents must use different model identifiers")
        self.bridge = bridge
        self.sessions = {
            "A": AgentSession("A", "sharded", model_a, provider_a),
            "B": AgentSession("B", "crux", model_b, provider_b),
        }
        self.world_id = None

    def observe_round(self):
        """One server snapshot produces equal-shape observations for both teams."""
        snapshot = self.bridge.observe()
        if snapshot.get("contract") != CONTRACT or not isinstance(snapshot.get("worldId"), str):
            raise ValueError("Unexpected duel observation contract")
        teams = snapshot.get("teams")
        if not isinstance(teams, dict) or set(teams) != set(TEAMS.values()):
            raise ValueError("Both team views are required")
        seen = set()
        for team in TEAMS.values():
            view = teams[team]
            if not isinstance(view, dict) or not isinstance(view.get("units"), list):
                raise ValueError("Malformed team roster")
            for unit in view["units"]:
                unit_id = unit.get("id") if isinstance(unit, dict) else None
                if type(unit_id) is not int or unit_id in seen:
                    raise ValueError("Duplicate or invalid live unit ID")
                seen.add(unit_id)

        self.world_id = snapshot["worldId"]
        observations = {}
        for agent_id, session in self.sessions.items():
            opponent = "crux" if session.team == "sharded" else "sharded"
            session.roster = frozenset(
                unit["id"] for unit in teams[session.team]["units"]
                if unit.get("commandable") is True and unit.get("health", 0) > 0
            )
            observation = {
                "contract": CONTRACT,
                "worldId": self.world_id,
                "tick": snapshot["tick"],
                "paused": snapshot.get("paused"),
                "gameOver": snapshot["gameOver"],
                "own": copy.deepcopy(teams[session.team]),
                "enemy": copy.deepcopy(teams[opponent]),
            }
            session.observation = observation
            observations[agent_id] = observation
        return observations

    def command(self, agent_id, payload):
        """Validate executor IDs against the latest live roster before HTTP dispatch."""
        if agent_id not in self.sessions:
            raise CommandRejected("Unknown agent")
        session = self.sessions[agent_id]
        if session.observation is None or session.observation["worldId"] != self.world_id:
            raise CommandRejected("Observe the current world before commanding")
        if not isinstance(payload, dict) or payload.get("team") != session.team:
            raise CommandRejected("Agent cannot command another team")
        action = payload.get("action")
        if action not in {"move", "attack", "mine", "build", "produce"}:
            raise CommandRejected("Unsupported duel command")
        if action == "produce":
            factory = session.observation["own"].get("production", {}).get("factory", {})
            stock, cost = factory.get("stock", {}), factory.get("cost", {})
            supply = factory.get("supply", {})
            reserve = supply.get("stock", {}) if supply.get("routeReady") is True else {}
            if (set(payload) != {"team", "action", "buildingX", "buildingY", "unit"}
                    or payload["unit"] != "dagger"
                    or type(payload["buildingX"]) is not int
                    or type(payload["buildingY"]) is not int
                    or (payload["buildingX"], payload["buildingY"])
                    != (factory.get("x"), factory.get("y"))
                    or factory.get("status") != "idle"
                    or not cost or any(stock.get(item, 0) + reserve.get(item, 0) < amount
                                       for item, amount in cost.items())):
                raise CommandRejected("Invalid, active, or unfunded team factory")
        else:
            ids = payload.get("unitIds")
            if (not isinstance(ids, list) or not 1 <= len(ids) <= 40
                    or any(type(unit_id) is not int for unit_id in ids)
                    or len(set(ids)) != len(ids) or not set(ids) <= session.roster):
                raise CommandRejected("Unit ID is absent, dead, or belongs to another team")
            if action == "attack":
                target = payload.get("targetUnitId")
                enemy_ids = {unit["id"] for unit in session.observation["enemy"]["units"]}
                if type(target) is not int or target not in enemy_ids or set(payload) != {
                        "team", "action", "unitIds", "targetUnitId"}:
                    raise CommandRejected("Invalid enemy target or attack payload")
            elif action == "move":
                if set(payload) != {"team", "action", "unitIds", "x", "y"} or any(
                        type(payload[axis]) not in {int, float} or not math.isfinite(payload[axis])
                        for axis in ("x", "y")):
                    raise CommandRejected("Invalid move payload")
            elif action == "mine":
                if (set(payload) != {"team", "action", "unitIds", "resource"}
                        or len(ids) != 1 or payload["resource"] != "copper"):
                    raise CommandRejected("Invalid copper mining payload")
            else:
                site = session.observation["own"].get("economy", {}).get("duoSite", {})
                if (set(payload) != {"team", "action", "unitIds", "block", "x", "y"}
                        or len(ids) != 1 or payload["block"] != "duo"
                        or type(payload["x"]) is not int or type(payload["y"]) is not int
                        or (payload["x"], payload["y"]) != (site.get("x"), site.get("y"))
                        or site.get("placeable") is not True
                        or session.observation["own"]["resources"].get("copper", 0)
                        < site.get("copperCost", float("inf"))):
                    raise CommandRejected("Invalid or unaffordable team build candidate")

        session.decision_counter += 1
        result = self.bridge.command(copy.deepcopy(payload))
        if result.get("accepted") is not True or result.get("team") != session.team:
            raise CommandRejected("Bridge did not accept team-scoped command")
        session.last_decision = copy.deepcopy(payload)
        session.log.append({"tick": session.observation["tick"], "command": copy.deepcopy(payload)})
        return result
