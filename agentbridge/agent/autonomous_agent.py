import json
import time
import urllib.request
import urllib.error

STATE_URL = "http://127.0.0.1:8765/state"
ACTION_URL = "http://127.0.0.1:8765/action"

POLL_INTERVAL = 0.5
PATROL_DISTANCE = 160.0
ARRIVAL_DISTANCE = 15.0


def get_state():
    with urllib.request.urlopen(STATE_URL, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def send_move(unit_id, x, y):
    action = {
        "action": "move",
        "unitId": unit_id,
        "x": x,
        "y": y
    }

    request = urllib.request.Request(
        ACTION_URL,
        data=json.dumps(action).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(request, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))


def distance(a_x, a_y, b_x, b_y):
    return ((a_x - b_x) ** 2 + (a_y - b_y) ** 2) ** 0.5


print("Mindustry Autonomous Agent")
print("Mode: Dagger patrol")
print("Press Ctrl+C to stop.\n")

anchor_x = None
anchor_y = None
target_x = None
target_y = None
going_right = True
controlled_unit_id = None

try:
    while True:
        state = get_state()

        if state.get("status") == "waiting":
            print("[WAITING] No game is running.")
            time.sleep(1)
            continue

        daggers = [
            unit for unit in state.get("units", [])
            if unit.get("type") == "dagger"
        ]

        if not daggers:
            print("[WAITING] No Dagger found.")
            time.sleep(1)
            continue

        unit = daggers[0]

        # Initialize patrol around the Dagger's first observed position.
        if controlled_unit_id != unit["id"]:
            controlled_unit_id = unit["id"]
            anchor_x = unit["x"]
            anchor_y = unit["y"]
            going_right = True

            target_x = anchor_x + PATROL_DISTANCE
            target_y = anchor_y

            print(f"[OBSERVE] Dagger #{controlled_unit_id} found")
            print(f"[DECIDE] Start patrol around ({anchor_x:.1f}, {anchor_y:.1f})")

            result = send_move(controlled_unit_id, target_x, target_y)
            print(f"[ACT] Move RIGHT -> ({target_x:.1f}, {target_y:.1f})")
            print(f"[BRIDGE] {result}")

        current_x = unit["x"]
        current_y = unit["y"]

        remaining = distance(current_x, current_y, target_x, target_y)

        print(
            f"[OBSERVE] #{controlled_unit_id} "
            f"pos=({current_x:.1f},{current_y:.1f}) "
            f"target=({target_x:.1f},{target_y:.1f}) "
            f"distance={remaining:.1f}"
        )

        # Reached current target -> decide the next action autonomously.
        if remaining <= ARRIVAL_DISTANCE:
            going_right = not going_right

            if going_right:
                target_x = anchor_x + PATROL_DISTANCE
                direction = "RIGHT"
            else:
                target_x = anchor_x - PATROL_DISTANCE
                direction = "LEFT"

            target_y = anchor_y

            print(f"[DECIDE] Target reached -> patrol {direction}")

            result = send_move(controlled_unit_id, target_x, target_y)

            print(f"[ACT] Move {direction} -> ({target_x:.1f}, {target_y:.1f})")
            print(f"[BRIDGE] {result}")

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("\nAutonomous Agent stopped.")

except Exception as e:
    print("\nAgent error:", e)
