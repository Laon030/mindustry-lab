import json
import time
import urllib.request

STATE_URL = "http://127.0.0.1:8765/state"

def get_state():
    with urllib.request.urlopen(STATE_URL, timeout=2) as response:
        return json.loads(response.read().decode("utf-8"))

print("Mindustry Agent started.")
print("Reading game state from", STATE_URL)
print("Press Ctrl+C to stop.\n")

try:
    while True:
        state = get_state()

        if state.get("status") == "waiting":
            print("[WAITING] No game is running.")
        else:
            resources = state.get("resources", {})
            units = state.get("units", [])

            print(
                f"[Wave {state.get('wave')}] "
                f"Copper={resources.get('copper')} "
                f"Lead={resources.get('lead')} "
                f"Units={len(units)}"
            )

        time.sleep(1)

except KeyboardInterrupt:
    print("\nAgent stopped.")
except Exception as e:
    print("\nAgent error:", e)
