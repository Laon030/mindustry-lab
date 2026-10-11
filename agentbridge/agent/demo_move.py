import json
import urllib.request

STATE_URL = "http://127.0.0.1:8765/state"
ACTION_URL = "http://127.0.0.1:8765/action"

# 1. Read current game state
with urllib.request.urlopen(STATE_URL, timeout=2) as response:
    state = json.loads(response.read().decode("utf-8"))

# 2. Find a Dagger
daggers = [u for u in state.get("units", []) if u.get("type") == "dagger"]

if not daggers:
    raise SystemExit("No Dagger unit found.")

unit = daggers[0]

# 3. Move it 160 world units to the right
target_x = unit["x"] + 160
target_y = unit["y"]

action = {
    "action": "move",
    "unitId": unit["id"],
    "x": target_x,
    "y": target_y
}

request = urllib.request.Request(
    ACTION_URL,
    data=json.dumps(action).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST"
)

# 4. Send action and print result
with urllib.request.urlopen(request, timeout=2) as response:
    result = json.loads(response.read().decode("utf-8"))

print(f"Dagger #{unit['id']}")
print(f"Current: ({unit['x']:.1f}, {unit['y']:.1f})")
print(f"Target : ({target_x:.1f}, {target_y:.1f})")
print("Bridge response:")
print(json.dumps(result, indent=2))
