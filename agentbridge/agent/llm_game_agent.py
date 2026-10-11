import json
import re
import subprocess
import urllib.request

STATE_URL = "http://127.0.0.1:8765/state"
ACTION_URL = "http://127.0.0.1:8765/action"
MODEL = "ollama-cloud/qwen3.5:397b"

ALLOWED_RESOURCES = {"copper", "lead"}


def get_state():
    with urllib.request.urlopen(STATE_URL, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def ask_llm(copper, lead):
    prompt = f"""
You are the decision-making brain of a Mindustry mining agent.

Current game state:
- copper: {copper}
- lead: {lead}

Available actions:
- mine copper
- mine lead

Goal:
Keep copper and lead reasonably balanced.
Choose which resource should be mined next.

Return ONLY valid JSON:
{{"action":"mine","resource":"copper","reason":"short explanation"}}

Rules:
- action must be "mine"
- resource must be either "copper" or "lead"
"""

    result = subprocess.run(
        ["opencode", "run", "-m", MODEL, prompt],
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        raise RuntimeError(
            "OpenCode failed:\n" + (result.stderr or result.stdout)
        )

    match = re.search(r'\{.*?\}', result.stdout, re.DOTALL)

    if not match:
        raise RuntimeError(
            "Could not find JSON in LLM response:\n" + result.stdout
        )

    return json.loads(match.group(0))


def validate_decision(decision):
    if decision.get("action") != "mine":
        raise ValueError(
            f"Rejected LLM action: {decision.get('action')}"
        )

    resource = decision.get("resource")

    if resource not in ALLOWED_RESOURCES:
        raise ValueError(
            f"Rejected LLM resource: {resource}"
        )

    return resource


def send_mine(unit_id, resource):
    action = {
        "action": "mine",
        "unitId": unit_id,
        "resource": resource
    }

    request = urllib.request.Request(
        ACTION_URL,
        data=json.dumps(action).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


state = get_state()

resources = state.get("resources", {})
copper = resources.get("copper", 0)
lead = resources.get("lead", 0)

monos = [
    unit for unit in state.get("units", [])
    if unit.get("type") == "mono"
]

if not monos:
    raise SystemExit("[ERROR] No Mono found.")

mono = monos[0]

print("[OBSERVE]")
print(f"  Copper = {copper}")
print(f"  Lead   = {lead}")
print(f"  Mono   = #{mono['id']}")

print("\n[ASK LLM]")
print(f"  Model = {MODEL}")

decision = ask_llm(copper, lead)

print("\n[LLM DECISION]")
print(json.dumps(decision, indent=2))

resource = validate_decision(decision)

print("\n[VALIDATE]")
print(f"  Approved action: mine {resource}")

result = send_mine(mono["id"], resource)

print("\n[ACT]")
print(f"  Mono #{mono['id']} -> mine {resource}")

print("\n[BRIDGE]")
print(json.dumps(result, indent=2))
