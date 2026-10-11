import json
import time
import urllib.request
import urllib.error

STATE_URL = "http://127.0.0.1:8765/state"
ACTION_URL = "http://127.0.0.1:8765/action"

POLL_INTERVAL = 2.0


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


print("Mindustry Continuous Resource Agent")
print("Policy: mine whichever resource is currently lower")
print("Press Ctrl+C to stop.\n")

current_task = None
current_unit_id = None

try:
    while True:
        state = get_state()

        if state.get("status") == "waiting":
            print("[WAIT] No game running")
            time.sleep(POLL_INTERVAL)
            continue

        resources = state.get("resources", {})
        copper = resources.get("copper", 0)
        lead = resources.get("lead", 0)

        monos = [
            unit for unit in state.get("units", [])
            if unit.get("type") == "mono"
        ]

        if not monos:
            print("[WAIT] No Mono found")
            time.sleep(POLL_INTERVAL)
            continue

        mono = monos[0]

        print(
            f"[OBSERVE] Copper={copper} Lead={lead} "
            f"Mono=#{mono['id']}"
        )

        if copper <= lead:
            desired_task = "copper"
        else:
            desired_task = "lead"

        # A newly spawned Mono must receive a command even
        # if the previous unit had the same task.
        if mono["id"] != current_unit_id:
            current_unit_id = mono["id"]
            current_task = None

        if desired_task != current_task:
            print(
                f"[DECIDE] Change task: "
                f"{current_task or 'none'} -> {desired_task}"
            )

            result = send_mine(mono["id"], desired_task)

            if result.get("success"):
                current_task = desired_task
                print(
                    f"[ACT] Mono #{mono['id']} "
                    f"now mining {desired_task}"
                )
            else:
                print(f"[ERROR] Bridge rejected action: {result}")

        else:
            print(f"[DECIDE] Keep mining {current_task}")

        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    print("\nContinuous Resource Agent stopped.")

except Exception as e:
    print(f"\nAgent error: {e}")
