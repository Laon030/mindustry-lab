"""Bounded, explicit, persistent scratchpad for controlled experiments."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping


SCHEMA_VERSION = 1
MAX_BYTES = 4096
_MAX_TEXT = 500
_MAX_LIST_ITEMS = 8
_MAX_STATE_ITEMS = 16
_FIELDS = {
    "schema_version",
    "revision",
    "goal",
    "current_subgoal",
    "known_state",
    "plan",
    "completed",
    "failures",
    "next_step",
    "confidence",
}


def _canonical(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def initial_scratchpad(goal: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "revision": 0,
        "goal": goal,
        "current_subgoal": "observe deterministic fixture",
        "known_state": {},
        "plan": [],
        "completed": [],
        "failures": [],
        "next_step": "select the next goal-consistent intent",
        "confidence": 0.5,
    }


def validate_scratchpad(
    candidate: Mapping[str, Any],
    *,
    expected_goal: str,
    previous_revision: int | None = None,
) -> dict[str, Any]:
    if not isinstance(candidate, Mapping):
        raise ValueError("scratchpad must be an object")
    if set(candidate) != _FIELDS:
        raise ValueError(f"scratchpad fields must be exactly {sorted(_FIELDS)}")
    result = dict(candidate)
    if result["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported scratchpad schema_version")
    if not isinstance(result["revision"], int) or isinstance(result["revision"], bool):
        raise ValueError("scratchpad revision must be an integer")
    if previous_revision is not None and result["revision"] != previous_revision + 1:
        raise ValueError("scratchpad revision must increment by exactly one")
    if result["goal"] != expected_goal:
        raise ValueError("scratchpad goal is immutable")

    for field in ("goal", "current_subgoal", "next_step"):
        value = result[field]
        if not isinstance(value, str) or not value.strip() or len(value) > _MAX_TEXT:
            raise ValueError(f"scratchpad {field} must be 1..{_MAX_TEXT} characters")

    known_state = result["known_state"]
    if not isinstance(known_state, dict) or len(known_state) > _MAX_STATE_ITEMS:
        raise ValueError("scratchpad known_state must be a small object")
    for key, value in known_state.items():
        if not isinstance(key, str) or not key or len(key) > 80:
            raise ValueError("scratchpad known_state keys must be short strings")
        if value is not None and (not isinstance(value, (str, int, float, bool)) or isinstance(value, float) and not (-1e100 < value < 1e100)):
            raise ValueError("scratchpad known_state values must be finite JSON scalars")
        if isinstance(value, str) and len(value) > 200:
            raise ValueError("scratchpad known_state string is too long")

    for field in ("plan", "completed", "failures"):
        values = result[field]
        if not isinstance(values, list) or len(values) > _MAX_LIST_ITEMS:
            raise ValueError(f"scratchpad {field} must contain at most {_MAX_LIST_ITEMS} entries")
        if any(not isinstance(value, str) or not value.strip() or len(value) > 300 for value in values):
            raise ValueError(f"scratchpad {field} entries must be non-empty strings up to 300 characters")

    confidence = result["confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        raise ValueError("scratchpad confidence must be between 0 and 1")

    encoded = _canonical(result)
    if len(encoded) > MAX_BYTES:
        raise ValueError(f"scratchpad exceeds {MAX_BYTES} bytes")
    return json.loads(encoded)


@dataclass
class ScratchpadStore:
    path: Path
    goal: str

    def initialize(self) -> dict[str, Any]:
        if self.path.exists():
            return self.load()
        value = validate_scratchpad(initial_scratchpad(self.goal), expected_goal=self.goal)
        self._write(value)
        return value

    def load(self) -> dict[str, Any]:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(f"cannot load scratchpad: {error}") from error
        return validate_scratchpad(value, expected_goal=self.goal)

    def update(self, candidate: Mapping[str, Any]) -> dict[str, Any]:
        current = self.load()
        value = validate_scratchpad(
            candidate,
            expected_goal=self.goal,
            previous_revision=current["revision"],
        )
        self._write(value)
        return value

    def size_bytes(self) -> int:
        return len(_canonical(self.load()))

    def _write(self, value: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = _canonical(value) + b"\n"
        descriptor, temporary = tempfile.mkstemp(prefix=f".{self.path.name}.", dir=self.path.parent)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
