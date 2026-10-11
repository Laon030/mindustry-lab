import json
import urllib.request

STATE_URL = "http://127.0.0.1:8765/state"
ACTION_URL = "http://127.0.0.1:8765/action"


def get_state():
    with urllib.request.urlopen(STATE_URL, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


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

if copper <= lead:
    target_resource = "copper"
else:
    target_resource = "lead"

print()
print("[DECIDE]")
print(f"  {target_resource} is currently more needed.")

result = send_mine(mono["id"], target_resource)

print()
print("[ACT]")
print(f"  Command Mono #{mono['id']} to mine {target_resource}.")
print()
print("[BRIDGE]")
print(json.dumps(result, indent=2))
