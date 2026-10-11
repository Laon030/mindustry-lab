"""HEADLESS snapshot-guard probe on an already paused, two-core demo server.

Apply duel_observer_drift_probe.console's initialization once before running.
Apply its drift line after GUARD_MODEL_RETURNED appears, during the hold.
Real local model choices are held briefly to make the injection window visible.
This is not the normal match runner or evidence of a completed match.
"""

import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agent"))

from duel.auto_match import AUTO_MODELS, match_exit_code, run_match  # noqa: E402
from duel.coordinator import DuelBridge, DuelCoordinator  # noqa: E402
from duel.unified import UnifiedOllamaProvider  # noqa: E402


class HeldProvider:
    def __init__(self, side, model, seconds):
        self.side, self.model, self.seconds = side, model, seconds
        self.provider = UnifiedOllamaProvider(model)

    def decide(self, observation, memory=None):
        choice, usage = self.provider.decide(observation, memory)
        print(f"3번 AGENT / TEST: GUARD_MODEL_RETURNED side={self.side} hold={self.seconds}s",
              flush=True)
        time.sleep(self.seconds)
        return choice, {**usage, "probeHoldSeconds": self.seconds}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--hold-seconds", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.hold_seconds <= 60:
        parser.error("hold-seconds must be 1-60")
    coordinator = DuelCoordinator(DuelBridge(), AUTO_MODELS["A"], AUTO_MODELS["B"])
    result = run_match(coordinator,
                       {side: HeldProvider(side, model, args.hold_seconds)
                        for side, model in AUTO_MODELS.items()},
                       log=args.log, max_rounds=1, max_stale_retries=0)
    print(json.dumps(result, sort_keys=True), flush=True)
    return match_exit_code(result)


if __name__ == "__main__":
    raise SystemExit(main())
