"""Gate 5: bounded, team-symmetric economy choice for small local models."""

import json
import urllib.request

from .ollama_provider import DEFAULT_MODELS
from .provider import strict_json


def economy_summary(observation):
    def side(view):
        site = view.get("economy", {}).get("duoSite", {})
        return {
            "copper": view["resources"]["copper"],
            "copperOreTiles": view.get("economy", {}).get("nearbyCopperOreTiles", 0),
            "mono": sum(unit["type"] == "mono" for unit in view["units"]),
            "poly": sum(unit["type"] == "poly" for unit in view["units"]),
            "duoSite": site.get("status", "unknown"),
            "duoCostCopper": site.get("copperCost", 35),
            "duoAffordable": view["resources"]["copper"] >= site.get("copperCost", 35),
            "duoPlaceable": site.get("placeable") is True,
        }
    return {"own": side(observation["own"]), "enemy": side(observation["enemy"])}


def legal_intents(observation):
    own = economy_summary(observation)["own"]
    legal = ["WAIT"]
    if own["mono"] == 1 and own["copperOreTiles"] > 0:
        legal.append("MINE")
    if (own["poly"] == 1 and own["duoPlaceable"]
            and own["copper"] >= own["duoCostCopper"]):
        legal.append("BUILD")
    return legal


def decision_schema(observation):
    return {"type": "object", "properties": {
        "intent": {"type": "string", "enum": legal_intents(observation)},
        "reason": {"type": "string", "minLength": 1, "maxLength": 120},
    }, "required": ["intent", "reason"], "additionalProperties": False}


def decision_prompt(observation):
    summary = economy_summary(observation)["own"]
    if summary["duoSite"] == "complete":
        situation = "The Duo is complete. Avoid duplicate construction. "
    elif summary["duoAffordable"] and summary["duoPlaceable"]:
        situation = (f"You have {summary['copper']} copper; the Duo costs "
                     f"{summary['duoCostCopper']}. Mining is complete for this step. "
                     "Choose the action that begins Duo construction now. ")
    else:
        situation = (f"You have {summary['copper']} copper; the Duo costs "
                     f"{summary['duoCostCopper']}. Choose the action that starts "
                     "collecting copper now. ")
    return (
        "Mindustry early-game team agent. Objective: construct one Duo. "
        "There is no enemy threat nearby. "
        "MINE orders Mono to collect copper. BUILD orders Poly to construct Duo "
        "using 35 copper. WAIT does nothing. "
        "Examples: copper=0, empty site -> MINE; copper=60, empty site, "
        "cost=35 -> BUILD; completed Duo -> WAIT. "
        + situation + "Choose ONE legal intent: "
        + ", ".join(legal_intents(observation)) + ". "
        'Return only JSON: {"intent":"...","reason":"brief"}. State: '
        + json.dumps(summary, separators=(",", ":"))
    )


class EconomyOllamaProvider:
    def __init__(self, model, timeout=120, endpoint="http://127.0.0.1:11434/api/chat"):
        if endpoint != "http://127.0.0.1:11434/api/chat":
            raise ValueError("Economy Ollama endpoint must remain localhost")
        self.model, self.timeout, self.endpoint = model, timeout, endpoint

    def decide(self, observation):
        payload = {"model": self.model,
                   "messages": [{"role": "user", "content": decision_prompt(observation)}],
                   "stream": False, "format": decision_schema(observation),
                   "think": False, "keep_alive": "30s",
                   "options": {"temperature": 0, "num_ctx": 2048, "num_predict": 1024}}
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
            raise ValueError("Invalid economy decision")
        usage = {"reportedModel": result["model"],
                 "promptTokens": result.get("prompt_eval_count"),
                 "outputTokens": result.get("eval_count")}
        return choice, usage


def resolve_intent(coordinator, agent_id, choice):
    """Mechanically bind a model-selected intent to its sole eligible live unit."""
    view = coordinator.sessions[agent_id].observation["own"]
    intent = choice["intent"]
    if intent == "WAIT":
        return None
    unit_type = "mono" if intent == "MINE" else "poly"
    eligible = [unit["id"] for unit in view["units"]
                if unit["type"] == unit_type and unit["id"] in coordinator.sessions[agent_id].roster]
    if len(eligible) != 1:
        raise ValueError(f"Expected one commandable {unit_type}, found {len(eligible)}")
    payload = {"team": coordinator.sessions[agent_id].team,
               "action": intent.lower(), "unitIds": eligible}
    if intent == "MINE":
        payload["resource"] = "copper"
    else:
        site = view["economy"]["duoSite"]
        payload.update({"block": "duo", "x": site["x"], "y": site["y"]})
    return payload
