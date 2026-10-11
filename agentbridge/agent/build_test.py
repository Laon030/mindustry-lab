"""Submit one build plan and record observations; completion needs tile evidence."""

import argparse
import json
import math
import time
import urllib.error
import urllib.request


BASE_URL = "http://127.0.0.1:8765"


def request_json(path, payload=None):
    request = urllib.request.Request(
        BASE_URL + path,
        data=None if payload is None else json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=7) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(
            f"HTTP {error.code}: {error.read().decode('utf-8', errors='replace')}"
        ) from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--unit-id", type=int, help="Required when multiple Polys exist")
    parser.add_argument("--tile-x", type=int, required=True)
    parser.add_argument("--tile-y", type=int, required=True)
    parser.add_argument("--rotation", type=int, choices=range(4), default=0)
    parser.add_argument("--observe-seconds", type=int, default=20, help="Observation duration: 1–120 seconds")
    args = parser.parse_args()
    if not 1 <= args.observe_seconds <= 120:
        parser.error("--observe-seconds must be between 1 and 120")

    try:
        state = request_json("/state")
        polys = [unit for unit in state.get("units", []) if unit.get("type") == "poly"]
        if args.unit_id is not None:
            polys = [unit for unit in polys if unit["id"] == args.unit_id]
        if len(polys) != 1:
            raise RuntimeError("Select exactly one live Poly with --unit-id; connect a client first.")
        unit = polys[0]
        action = {
            "action": "build", "unitId": unit["id"], "block": "conveyor",
            "tileX": args.tile_x, "tileY": args.tile_y, "rotation": args.rotation,
        }
        print(json.dumps({"before": state, "request": action}), flush=True)
        result = request_json("/action", action)
        print(json.dumps({"response": result}), flush=True)
        if not result.get("success"):
            raise RuntimeError("Build request was rejected")

        deadline = time.monotonic() + args.observe_seconds
        while time.monotonic() < deadline:
            state = request_json("/state")
            observed = next((u for u in state.get("units", []) if u["id"] == unit["id"]), None)
            if observed is None:
                raise RuntimeError("Poly disappeared or game stopped during observation")
            print(json.dumps({
                "tick": state.get("tick"), "unit": observed,
                "distanceToTarget": math.hypot(observed["x"] - args.tile_x * 8,
                                               observed["y"] - args.tile_y * 8),
                "resources": state.get("resources"),
            }), flush=True)
            time.sleep(0.25)

        print("Plan accepted; /state cannot prove completion. Verify target tile and normal construction in SERVER/CLIENT.")
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, f"Build test failed: {error}\n")


if __name__ == "__main__":
    main()
