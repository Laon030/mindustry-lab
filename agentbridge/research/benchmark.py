"""Frozen benchmark manifest loading and deterministic fixture checks."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


_REQUIRED_TOP_LEVEL = {
    "benchmark_id",
    "benchmark_version",
    "mindustry_version",
    "fixture",
    "observation",
    "actions",
    "planner_executor",
    "goal",
    "success_criteria",
    "budgets",
}


@dataclass(frozen=True)
class BenchmarkSpec:
    """Immutable, fingerprinted configuration for one benchmark version."""

    data: Mapping[str, Any]
    source: Path
    fingerprint: str

    @classmethod
    def load(cls, path: str | Path) -> "BenchmarkSpec":
        source = Path(path)
        raw = source.read_bytes()
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("benchmark manifest must be a JSON object")
        missing = sorted(_REQUIRED_TOP_LEVEL - data.keys())
        extra = sorted(data.keys() - _REQUIRED_TOP_LEVEL)
        if missing or extra:
            raise ValueError(f"invalid benchmark keys: missing={missing}, extra={extra}")
        if data["benchmark_version"] != 1:
            raise ValueError("unsupported benchmark_version")
        if data["mindustry_version"] != "v159.7":
            raise ValueError("benchmark requires Mindustry v159.7")
        return cls(data=data, source=source.resolve(), fingerprint=hashlib.sha256(raw).hexdigest())

    @property
    def goal(self) -> str:
        return str(self.data["goal"])

    @property
    def timeout_seconds(self) -> int:
        return int(self.data["budgets"]["timeout_seconds"])

    @property
    def action_budget(self) -> int:
        return int(self.data["budgets"]["action_budget"])

    def metadata(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.data["benchmark_id"],
            "benchmark_version": self.data["benchmark_version"],
            "benchmark_fingerprint": self.fingerprint,
            "mindustry_version": self.data["mindustry_version"],
            "fixture_sha256": self.data["fixture"]["sha256"],
            "planner_executor": self.data["planner_executor"],
            "timeout_seconds": self.timeout_seconds,
            "action_budget": self.action_budget,
        }

    def verify_initial_state(self, state: Mapping[str, Any]) -> list[str]:
        """Return human-readable fixture mismatches without mutating the game."""
        fixture = self.data["fixture"]
        mismatches: list[str] = []
        if state.get("map") != fixture["map"]:
            mismatches.append(f"map={state.get('map')!r}")
        if state.get("wave") != 1:
            mismatches.append(f"wave={state.get('wave')!r}")
        resources = state.get("resources", {})
        for item, expected in fixture["resources"].items():
            actual = resources.get(item) if isinstance(resources, Mapping) else None
            if actual != expected:
                mismatches.append(f"resources.{item}={actual!r}, expected {expected}")
        units = state.get("unitCounts", {})
        if isinstance(units, Mapping):
            for unit, expected in fixture["units"].items():
                if units.get(unit) != expected:
                    mismatches.append(f"unitCounts.{unit}={units.get(unit)!r}, expected {expected}")
        else:
            mismatches.append("unitCounts is missing")
        rules = state.get("rules", {})
        if isinstance(rules, Mapping):
            for name, expected in fixture["rules"].items():
                if rules.get(name) != expected:
                    mismatches.append(f"rules.{name}={rules.get(name)!r}, expected {expected}")
        else:
            mismatches.append("rules is missing")
        core = state.get("core", {})
        actual_footprint = core.get("footprint") if isinstance(core, Mapping) else None
        if actual_footprint != fixture["core"]["footprint"]:
            mismatches.append("core.footprint does not match benchmark")
        return mismatches
