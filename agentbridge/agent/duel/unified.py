"""One bounded strategic intent contract across the weekend duel phases."""

import json
import urllib.request

from .economy import resolve_intent as resolve_economy
from .production import resolve_intent as resolve_production
from .provider import combat_summary, strict_json


def summary(observation):
    def side(view):
        site = view.get("economy", {}).get("duoSite", {})
        factory = view.get("production", {}).get("factory", {})
        stock, recipe = factory.get("stock", {}), factory.get("cost", {})
        supply = factory.get("supply", {})
        reserve = supply.get("stock", {}) if supply.get("routeReady") is True else {}
        fighters = sorted((unit for unit in view["units"] if unit["type"] == "dagger"),
                          key=lambda unit: unit["id"])
        return {
            "copper": view["resources"].get("copper", 0),
            "copperOreTiles": view.get("economy", {}).get("nearbyCopperOreTiles", 0),
            "duoStatus": site.get("status", "absent"),
            "duoCostCopper": site.get("copperCost", 35),
            "duoAffordableNow": site.get("status") == "empty"
            and site.get("placeable") is True
            and view["resources"].get("copper", 0) >= site.get("copperCost", float("inf")),
            "factoryStatus": factory.get("status", "absent"),
            "factoryStock": stock,
            "factoryReserve": reserve,
            "factorySupplyRouteReady": supply.get("routeReady") is True,
            "daggerCost": recipe,
            "factoryReadyNow": factory.get("status") == "idle" and bool(recipe)
            and all(stock.get(item, 0) + reserve.get(item, 0) >= amount
                    for item, amount in recipe.items()),
            "monoCount": sum(unit["type"] == "mono" for unit in view["units"]),
            "polyCount": sum(unit["type"] == "poly" for unit in view["units"]),
            "daggerHealthFraction": [round(unit["health"] / unit["maxHealth"], 2)
                                     for unit in fighters],
            "corePresent": bool(view["cores"]),
        }
    return {"own": side(observation["own"]), "enemy": side(observation["enemy"])}


def legal_intents(observation):
    own = observation["own"]
    site = own.get("economy", {}).get("duoSite", {})
    factory = own.get("production", {}).get("factory", {})
    stock, recipe = factory.get("stock", {}), factory.get("cost", {})
    supply = factory.get("supply", {})
    reserve = supply.get("stock", {}) if supply.get("routeReady") is True else {}
    mine_units = [unit for unit in own["units"] if unit["type"] == "mono"
                  and unit.get("commandable")]
    builders = [unit for unit in own["units"] if unit["type"] == "poly"
                and unit.get("commandable")]
    fighters = [unit for unit in own["units"] if unit["type"] == "dagger"
                and unit.get("commandable")]
    enemy_fighters = [unit for unit in observation["enemy"]["units"]
                      if unit["type"] == "dagger" and unit["health"] > 0]
    legal = []
    if (len(mine_units) == 1 and site.get("status") == "empty"
            and own["resources"].get("copper", 0) < site.get("copperCost", float("inf"))
            and own.get("economy", {}).get("nearbyCopperOreTiles", 0) > 0):
        legal.append("MINE")
    if (len(builders) == 1 and site.get("status") == "empty"
            and site.get("placeable") is True
            and own["resources"].get("copper", 0) >= site.get("copperCost", float("inf"))):
        legal.append("BUILD")
    if (factory.get("status") == "idle" and recipe
            and all(stock.get(item, 0) + reserve.get(item, 0) >= amount
                    for item, amount in recipe.items())):
        legal.append("PRODUCE")
    if fighters:
        legal.extend(f"ATTACK_{slot}" for slot in range(len(enemy_fighters)))
    if fighters and own["cores"]:
        legal.append("DEFEND")
    legal.append("WAIT")
    return legal


def decision_schema(observation):
    return {"type": "object", "properties": {
        "intent": {"type": "string", "enum": legal_intents(observation)},
        "reason": {"type": "string", "minLength": 1, "maxLength": 120},
    }, "required": ["intent", "reason"], "additionalProperties": False}


def decision_prompt(observation, memory=None):
    state = summary(observation)
    if (state["own"]["duoStatus"] == "complete"
            and state["enemy"]["duoStatus"] == "complete"
            and state["own"]["daggerHealthFraction"]
            and state["enemy"]["daggerHealthFraction"]):
        return (
            "You control one Mindustry team. Choose ONE combat strategy for this "
            "round. Objective: eliminate the enemy fighter. ATTACK_0 orders your "
            "fighter to attack enemy fighter slot 0. DEFEND moves it to own Core. "
            "WAIT issues no command. Repeated DEFEND or WAIT cannot eliminate the "
            "enemy. The game engine handles movement, aiming, damage and death. "
            "Choose one legal intent: " + ",".join(legal_intents(observation))
            + '. Return ONLY JSON {"intent":"...","reason":"under 120 characters"}. '
            "Observation: "
            + json.dumps(combat_summary(observation), separators=(",", ":"))
        )
    compact = {side: {"copper": view["copper"],
                      "duo": view["duoStatus"],
                      "duoAffordable": view["duoAffordableNow"],
                      "factoryReady": view["factoryReadyNow"],
                      "factoryReserve": view["factoryReserve"],
                      "daggers": len(view["daggerHealthFraction"])}
               for side, view in state.items()}
    memory = memory or {}
    repeat = memory.get("combatNoDamageRounds", 0)
    lesson = (f"Your last intent was {memory.get('lastIntent', 'none')}; "
              f"{repeat} consecutive combat rounds caused no HP change. "
              f"Only {memory.get('roundsRemaining') or 'a few'} rounds remain before "
              "a DRAW timeout. DEFEND and WAIT cannot damage the enemy; "
              "ATTACK_N starts combat and is necessary to win. "
              if repeat >= 2 else "")
    return (
        "Mindustry duel. Goal: build one Duo, produce a Dagger, defeat the enemy "
        "Dagger. Act on the next unfinished goal. MINE gains copper; BUILD spends "
        "35 copper on Duo; PRODUCE uses ready factory; ATTACK_N fights enemy "
        "Dagger N; DEFEND guards Core; WAIT delays. " + lesson
        + "State: " + json.dumps(compact, separators=(",", ":"))
        + " Legal: " + ",".join(legal_intents(observation))
        + '. Reply JSON {"intent":"...","reason":"brief"}.'
    )


class UnifiedOllamaProvider:
    def __init__(self, model, timeout=150, endpoint="http://127.0.0.1:11434/api/chat"):
        if endpoint != "http://127.0.0.1:11434/api/chat":
            raise ValueError("Duel model endpoint must remain localhost")
        self.model, self.timeout, self.endpoint = model, timeout, endpoint

    def decide(self, observation, memory=None):
        payload = {"model": self.model,
                   "messages": [{"role": "user", "content": decision_prompt(observation, memory)}],
                   "stream": False, "format": decision_schema(observation),
                   "think": False, "keep_alive": "10m",
                   "options": {"temperature": 0, "num_ctx": 2048, "num_predict": 256}}
        request = urllib.request.Request(
            self.endpoint, data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            result = strict_json(response.read().decode())
        if (not isinstance(result, dict) or result.get("model") != self.model
                or result.get("done") is not True or result.get("done_reason", "stop") != "stop"
                or not isinstance(result.get("message"), dict)
                or result["message"].get("tool_calls")):
            raise ValueError("Malformed or incomplete local model response")
        choice = strict_json(result["message"].get("content", ""))
        if (not isinstance(choice, dict) or set(choice) != {"intent", "reason"}
                or choice["intent"] not in legal_intents(observation)
                or not isinstance(choice["reason"], str)
                or not 1 <= len(choice["reason"]) <= 120):
            raise ValueError("Invalid cross-phase decision")
        return choice, {"reportedModel": result["model"],
                        "promptTokens": result.get("prompt_eval_count"),
                        "outputTokens": result.get("eval_count")}


def resolve_intent(coordinator, agent_id, choice):
    """Mechanical resolution only; never substitutes an unselected strategy."""
    session = coordinator.sessions[agent_id]
    observation = session.observation
    intent = choice["intent"]
    if intent not in legal_intents(observation):
        raise ValueError("Intent no longer legal")
    if intent == "WAIT":
        return None
    if intent in {"MINE", "BUILD"}:
        return resolve_economy(coordinator, agent_id, choice)
    if intent == "PRODUCE":
        return resolve_production(coordinator, agent_id, choice)
    own = observation["own"]
    fighters = sorted(unit["id"] for unit in own["units"]
                      if unit["type"] == "dagger" and unit["id"] in session.roster)
    if intent == "DEFEND":
        core = own["cores"][0]
        return {"team": session.team, "action": "move", "unitIds": fighters,
                "x": core["x"] * 8, "y": core["y"] * 8}
    enemies = sorted(unit["id"] for unit in observation["enemy"]["units"]
                     if unit["type"] == "dagger" and unit["health"] > 0)
    slot = int(intent.removeprefix("ATTACK_"))
    return {"team": session.team, "action": "attack", "unitIds": fighters,
            "targetUnitId": enemies[slot]}
