"""Gate 6: one vanilla Ground Factory -> Dagger production decision."""

import json
import urllib.request

from .provider import strict_json


def production_summary(observation):
    factory = observation["own"].get("production", {}).get("factory", {})
    return {"factoryStatus": factory.get("status", "absent"),
            "factoryStock": factory.get("stock", {}),
            "daggerRecipe": factory.get("cost", {}),
            "ownDaggers": sum(unit["type"] == "dagger"
                              for unit in observation["own"]["units"])}


def legal_intents(observation):
    summary = production_summary(observation)
    stock, recipe = summary["factoryStock"], summary["daggerRecipe"]
    if (summary["factoryStatus"] == "idle" and recipe
            and all(stock.get(item, 0) >= amount for item, amount in recipe.items())):
        return ["PRODUCE", "WAIT"]
    return ["WAIT"]


def decision_schema(observation):
    return {"type": "object", "properties": {
        "intent": {"type": "string", "enum": legal_intents(observation)},
        "reason": {"type": "string", "minLength": 1, "maxLength": 120},
    }, "required": ["intent", "reason"], "additionalProperties": False}


def decision_prompt(observation):
    summary = production_summary(observation)
    return (
        "Mindustry team agent. Objective: produce one Dagger using the already placed "
        "Ground Factory and its real item inventory. PRODUCE configures the normal "
        "factory to make Dagger; WAIT does nothing. The adjacent solar fixture powers "
        "the factory when the game runs. Do not request direct unit spawning. "
        "Example: idle factory, silicon=10, lead=10, recipe silicon=10, lead=10 "
        "-> PRODUCE. Choose ONE legal intent: "
        + ", ".join(legal_intents(observation)) + ". "
        'Return only JSON: {"intent":"...","reason":"brief"}. State: '
        + json.dumps(summary, separators=(",", ":"))
    )


class ProductionOllamaProvider:
    def __init__(self, model, timeout=120, endpoint="http://127.0.0.1:11434/api/chat"):
        if endpoint != "http://127.0.0.1:11434/api/chat":
            raise ValueError("Production Ollama endpoint must remain localhost")
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
            raise ValueError("Malformed or incomplete local production response")
        choice = strict_json(result["message"].get("content", ""))
        if (not isinstance(choice, dict) or set(choice) != {"intent", "reason"}
                or choice["intent"] not in legal_intents(observation)
                or not isinstance(choice["reason"], str)
                or not 1 <= len(choice["reason"]) <= 120):
            raise ValueError("Invalid production decision")
        return choice, {"reportedModel": result["model"],
                        "promptTokens": result.get("prompt_eval_count"),
                        "outputTokens": result.get("eval_count")}


def resolve_intent(coordinator, agent_id, choice):
    if choice["intent"] == "WAIT":
        return None
    factory = coordinator.sessions[agent_id].observation["own"]["production"]["factory"]
    return {"team": coordinator.sessions[agent_id].team, "action": "produce",
            "buildingX": factory["x"], "buildingY": factory["y"], "unit": "dagger"}
