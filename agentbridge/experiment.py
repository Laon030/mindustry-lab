#!/usr/bin/env python3
"""Run controlled scratchpad-evaluation harness episodes."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from research.benchmark import BenchmarkSpec
from research.condition import MemoryCondition
from research.runner import ExperimentRunner, mock_provider_factory, qwen_provider_factory


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", choices=["logistics"], default="logistics")
    parser.add_argument("--condition", choices=[condition.value for condition in MemoryCondition if condition is not MemoryCondition.RECENT_HISTORY], required=True)
    parser.add_argument("--runs", type=int, default=1)
    parser.add_argument("--provider", choices=["mock", "qwen"], default="mock")
    parser.add_argument("--model", default="ollama-cloud/qwen3.5:397b")
    parser.add_argument("--context-reset-every", type=int, default=None)
    parser.add_argument("--seed", type=int, default=20260911)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parent
    spec = BenchmarkSpec.load(root / "experiments" / "logistics_benchmark.json")
    condition = MemoryCondition(args.condition)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output or root / "build" / "experiments" / f"smoke-{stamp}"
    reset_every = args.context_reset_every
    if reset_every is None:
        reset_every = int(spec.data["budgets"]["context_reset_every_decisions"])
    if args.provider == "mock":
        factory = mock_provider_factory(condition)
        provider_config = {"type": "mock", "policy": "logistics-v1"}
    else:
        factory = qwen_provider_factory(args.model)
        provider_config = {"type": "opencode", "model": args.model}
    runner = ExperimentRunner(
        spec,
        output=output,
        provider_factory=factory,
        provider_config=provider_config,
        context_reset_every=reset_every,
        base_seed=args.seed,
    )
    summary = runner.run(condition, args.runs)
    print(json.dumps({"output": str(output), **summary}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
