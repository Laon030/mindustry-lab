"""Version 2 policy boundary. No game adapter, history oracle, or strategic fallback.

This module deliberately cannot load benchmark cases. Providers receive only the
public request; evaluator-only histories/outcomes belong to the test harness.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Mapping

from .scratchpad import ScratchpadStore


VERSION = "memory-sensitive-logistics-v2"
MAX_BYTES = 4096
GOAL = "Establish reliable copper delivery; use observed evidence to choose subgoals and recovery."
INTENTS = {"choose_candidate", "retry", "alternative", "inspect", "wait", "abandon"}
CURRENT_PREDICATES = {"survey_copper_tiles", "trial_failure", "trial_result"}
COMMON_PROMPT = (
    "You choose subgoals, candidate preferences, failure interpretations, task transitions, "
    "and retry versus alternative versus abandonment. Python checks legality and executes "
    "your choice; it does not select a strategy. Current visibility is local, so legal "
    "candidates need not be equally useful. Past events are not repeated automatically. "
    "Memory, when supplied, is a fallible claim, not ground truth. Reconcile evidence and "
    "uncertainty yourself. You may inspect, wait, or abandon; these are legal choices, "
    "not automatically goal loss. Return decision {intent,target,reason} and scratchpad. "
    "Use target=null for wait/abandon. For null input memory return scratchpad=null. "
    "Otherwise return the complete bounded updated memory with revision incremented by one."
)


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def _text(value: Any, limit: int = 160) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError("invalid bounded text")
    return value


def _integer(value: Any) -> int:
    if type(value) is not int or value < 0:
        raise ValueError("expected nonnegative integer")
    return value


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", value):
        raise ValueError("invalid identifier")
    return value


def _facts(value: Any) -> list[dict]:
    if not isinstance(value, list) or len(value) > 6:
        raise ValueError("at most six structured facts")
    result = []
    for fact in value:
        if not isinstance(fact, dict) or set(fact) != {"subject", "predicate", "value", "observed_tick"}:
            raise ValueError("fact fields mismatch; raw history is not accepted")
        scalar = fact["value"]
        if type(scalar) not in (str, int, bool) or isinstance(scalar, str) and len(scalar) > 160:
            raise ValueError("fact value must be a bounded scalar")
        if type(scalar) is int and abs(scalar) > 10**9:
            raise ValueError("fact integer too large")
        result.append({"subject": _identifier(fact["subject"]),
                       "predicate": _identifier(fact["predicate"]), "value": scalar,
                       "observed_tick": _integer(fact["observed_tick"])})
    return result


def initial_memory() -> dict:
    return {"schema_version": 2, "revision": 0, "goal": GOAL,
            "selected_subgoal": "assess current evidence", "relevant_events": [],
            "completed_milestones": [], "failures": [], "unresolved_information": [],
            "next_intended_step": "choose a subgoal"}


def validate_memory(value: Mapping[str, Any], previous_revision: int | None = None) -> dict:
    if not isinstance(value, dict) or set(value) != set(initial_memory()):
        raise ValueError("memory fields mismatch; raw history is not accepted")
    result = deepcopy(value)
    if type(result["schema_version"]) is not int or result["schema_version"] != 2 or result["goal"] != GOAL:
        raise ValueError("wrong memory version or immutable goal")
    revision = _integer(result["revision"])
    if previous_revision is not None and revision != previous_revision + 1:
        raise ValueError("revision must increment by one")
    for field in ("selected_subgoal", "next_intended_step"):
        _text(result[field])
    result["relevant_events"] = _facts(result["relevant_events"])
    for field in ("completed_milestones", "unresolved_information"):
        if not isinstance(result[field], list) or len(result[field]) > 6:
            raise ValueError("bounded memory list required")
        for entry in result[field]:
            _text(entry)
    failures = result["failures"]
    if not isinstance(failures, list) or len(failures) > 4:
        raise ValueError("at most four failures")
    for failure in failures:
        if not isinstance(failure, dict) or set(failure) != {"target", "cause", "attempted_alternatives"}:
            raise ValueError("failure fields mismatch")
        _identifier(failure["target"])
        _text(failure["cause"])
        alternatives = failure["attempted_alternatives"]
        if not isinstance(alternatives, list) or len(alternatives) > 4:
            raise ValueError("at most four attempted alternatives")
        for target in alternatives:
            _identifier(target)
    if len(canonical(result)) > MAX_BYTES:
        raise ValueError("memory exceeds 4096 bytes")
    return result


class MemoryStoreV2(ScratchpadStore):
    """Reuse atomic disk I/O only; v1 schema and runtime remain untouched."""

    def __init__(self, path: Path):
        super().__init__(path, GOAL)

    def initialize(self) -> dict:
        if self.path.exists():
            return self.load()
        value = initial_memory()
        self._write(value)
        return value

    def load(self) -> dict:
        return validate_memory(json.loads(self.path.read_text(encoding="utf-8")))

    def update(self, candidate: Mapping[str, Any]) -> dict:
        value = validate_memory(candidate, self.load()["revision"])
        self._write(value)
        return value


def observation(snapshot: Mapping[str, Any]) -> dict:
    """Allowlist projection. Never copy phase, plan, previous decisions or rankings.

    The caller must supply facts from the current visibility window, not an archive.
    Candidate IDs are stable environment identities, sorted independently of history.
    """
    tick = _integer(snapshot["tick"])
    candidates = []
    for candidate in snapshot["candidates"]:
        if type(candidate["legal"]) is not bool:
            raise ValueError("legal must be boolean")
        candidates.append({"id": _identifier(candidate["id"]),
                           "cost": _integer(candidate["cost"]), "legal": candidate["legal"]})
    if not 1 <= len(candidates) <= 8 or len({c["id"] for c in candidates}) != len(candidates):
        raise ValueError("one to eight distinct candidates required")
    if type(snapshot["executor"]["busy"]) is not bool:
        raise ValueError("busy must be boolean")
    events = _facts(snapshot["visible_events"])
    if any(event["observed_tick"] != tick for event in events):
        raise ValueError("historical event cannot enter current observation")
    ids = {c["id"] for c in candidates}
    if any(event["predicate"] not in CURRENT_PREDICATES or event["subject"] not in ids for event in events):
        raise ValueError("unknown current sensor event")
    return {"tick": tick, "resources": {"copper": _integer(snapshot["resources"]["copper"])},
            "executor": {"busy": snapshot["executor"]["busy"]},
            "candidates": sorted(candidates, key=lambda item: item["id"]),
            "visible_events": events}


@dataclass(frozen=True)
class Settings:
    model: str = "ollama-cloud/qwen3.5:397b"
    generation: str = "contract-only-no-inference"
    executor: str = "proposal-only-v2"
    action_budget: int = 4
    timeout_seconds: int = 60

    def __post_init__(self):
        for field in (self.model, self.generation, self.executor):
            _text(field)
        if not _integer(self.action_budget) or not _integer(self.timeout_seconds):
            raise ValueError("budgets must be positive")


def request(settings: Settings, snapshot: Mapping[str, Any], memory: dict | None) -> dict:
    return {"contract": VERSION, "common_prompt": COMMON_PROMPT, "goal": GOAL,
            "settings": asdict(settings), "observation": observation(snapshot),
            "memory_schema": {"template": initial_memory(), "max_bytes": MAX_BYTES,
                              "max_events": 6, "max_milestones": 6, "max_unresolved": 6,
                              "max_failures": 4, "max_alternatives_per_failure": 4,
                              "max_text_chars": 160,
                              "event_fields": ["subject", "predicate", "value", "observed_tick"],
                              "failure_fields": ["target", "cause", "attempted_alternatives"]},
            "scratchpad": None if memory is None else validate_memory(memory)}


def assert_memory_only_difference(first: Mapping[str, Any], second: Mapping[str, Any]) -> None:
    """Fail closed if a paired comparison changes anything except memory input."""
    left, right = deepcopy(dict(first)), deepcopy(dict(second))
    if "scratchpad" not in left or "scratchpad" not in right:
        raise ValueError("missing explicit memory condition")
    left.pop("scratchpad")
    right.pop("scratchpad")
    if canonical(left) != canonical(right):
        raise ValueError("paired requests differ outside scratchpad")


def validate_decision(decision: Mapping[str, Any], current: Mapping[str, Any]) -> dict:
    """Legality only: no memory, history, expected decision, or utility argument."""
    if not isinstance(decision, dict) or set(decision) != {"intent", "target", "reason"}:
        raise ValueError("decision fields mismatch")
    intent, target = decision["intent"], decision["target"]
    if not isinstance(intent, str) or intent not in INTENTS:
        raise ValueError("unknown intent")
    _text(decision["reason"])
    public = observation(current)
    if intent in {"wait", "abandon"}:
        if target is not None:
            raise ValueError("wait/abandon require null target")
    else:
        _identifier(target)
        candidate = next((c for c in public["candidates"] if c["id"] == target), None)
        if candidate is None:
            raise ValueError("unknown candidate")
        if public["executor"]["busy"]:
            raise ValueError("executor is busy")
        if intent != "inspect" and (not candidate["legal"] or candidate["cost"] > public["resources"]["copper"]):
            raise ValueError("currently unavailable or unaffordable candidate")
    return deepcopy(decision)


def decide_once(provider_factory: Callable, settings: Settings, snapshot: Mapping[str, Any],
                memory: dict | None = None) -> dict:
    """One isolated policy call; no automatic strategy or retained decision history.

    Factory/transport must create a fresh conversation. No live provider is wired by
    this milestone. A test double must never receive evaluator state via a closure.
    Caller explicitly persists validated memory; no-memory callers get None back.
    """
    public = request(settings, snapshot, memory)
    provider = provider_factory()
    try:
        response = provider.decide(deepcopy(public))
    finally:
        provider.close()
    if not isinstance(response, dict) or set(response) != {"decision", "scratchpad"}:
        raise ValueError("response fields mismatch")
    decision = validate_decision(response["decision"], public["observation"])
    updated = response["scratchpad"]
    if memory is None:
        if updated is not None:
            raise ValueError("no-memory condition cannot retain scratchpad")
    else:
        updated = validate_memory(updated, public["scratchpad"]["revision"])
    return {"request": public, "request_sha256": hashlib.sha256(canonical(public)).hexdigest(),
            "decision": decision, "scratchpad": updated,
            "context_boundary": "fresh_request", "context_loss": False}
