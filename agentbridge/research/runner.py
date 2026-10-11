"""Small reproducible experiment harness; mock episodes validate the machinery."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from typing import Any, Callable, Mapping

from .benchmark import BenchmarkSpec
from .condition import MemoryCondition, ResearchDecisionAdapter
from .metrics import calculate_metrics
from .provider import DecisionProvider, MockDecisionProvider, OpenCodeResearchProvider


PROMPT_VERSION = "logistics-strategy-v1"


class EventLog:
    def __init__(self, path: Path):
        self.path = path
        self.events: list[dict[str, Any]] = []
        self.started = time.monotonic()

    def emit(self, event_type: str, *, elapsed_seconds: float | None = None, **fields: Any) -> dict[str, Any]:
        event = {
            "seq": len(self.events),
            "time": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": time.monotonic() - self.started if elapsed_seconds is None else elapsed_seconds,
            "type": event_type,
            **fields,
        }
        self.events.append(event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False, sort_keys=True) + "\n")
        return event


class MockLogisticsBackend:
    """Deterministic state machine for runner tests, never evidence of game success."""

    def __init__(self, spec: BenchmarkSpec, seed: int):
        self.spec = spec
        self.seed = seed
        self.cleaned = False
        self.step_index = 0
        self.copper = 0
        self.topology_complete = False
        self.flow_verified = False
        self.post_completion_replanned = False

    def reset(self) -> dict[str, Any]:
        fixture = self.spec.data["fixture"]
        self.step_index = 0
        self.copper = int(fixture["resources"]["copper"])
        self.topology_complete = False
        self.flow_verified = False
        self.post_completion_replanned = False
        self.cleaned = False
        state = self.observe()
        mismatches = self.spec.verify_initial_state(state)
        if mismatches:
            raise RuntimeError(f"mock fixture mismatch: {mismatches}")
        return state

    def observe(self) -> dict[str, Any]:
        fixture = self.spec.data["fixture"]
        required = 27
        return {
            "map": fixture["map"],
            "wave": 1,
            "resources": {**fixture["resources"], "copper": self.copper},
            "unitCounts": dict(fixture["units"]),
            "rules": dict(fixture["rules"]),
            "core": deepcopy(fixture["core"]),
            "phase": (
                "maintain" if self.flow_verified else
                "verify_flow" if self.topology_complete else
                "build" if self.copper >= required else
                "bootstrap"
            ),
            "resourcesSufficient": self.copper >= required,
            "logisticsBuilt": self.topology_complete,
            "flowVerified": self.flow_verified,
            "postCompletionReplanned": self.post_completion_replanned,
            "observationVersion": self.step_index,
        }

    def apply(self, intent: str) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
        self.validate_intent(intent)
        actions: list[dict[str, Any]] = []
        if intent == "continue_bootstrap" and self.copper < 27:
            actions.append({"action": "mine", "resource": "copper", "accepted": True, "copper_cost": 0})
            self.copper = 27
        elif intent == "establish_copper_logistics" and self.copper >= 27 and not self.topology_complete:
            actions.append({"action": "build", "block": "mechanical-drill", "accepted": True, "copper_cost": 12})
            for index in range(5):
                actions.append({"action": "build", "block": "conveyor", "index": index, "accepted": True, "copper_cost": 1})
            self.copper -= 17
            self.topology_complete = True
        elif intent == "wait" and self.topology_complete and not self.flow_verified:
            self.flow_verified = True
            self.copper += 5
        elif intent == "wait" and self.flow_verified:
            self.post_completion_replanned = True
        self.step_index += 1
        return actions, self.observe(), self.flow_verified

    def cleanup(self) -> None:
        self.cleaned = True

    def action_count_for(self, intent: str) -> int:
        if intent == "continue_bootstrap" and self.copper < 27:
            return 1
        if intent == "establish_copper_logistics" and self.copper >= 27 and not self.topology_complete:
            return 6
        return 0

    def validate_intent(self, intent: str) -> None:
        valid = (
            intent == "continue_bootstrap" and self.copper < 27 and not self.topology_complete
            or intent == "establish_copper_logistics" and self.copper >= 27 and not self.topology_complete
            or intent == "wait" and self.topology_complete
        )
        if not valid:
            raise ValueError(f"intent {intent!r} is not goal-consistent in phase {self.observe()['phase']!r}")


class ExperimentRunner:
    def __init__(
        self,
        spec: BenchmarkSpec,
        *,
        output: Path,
        provider_factory: Callable[[], DecisionProvider],
        provider_config: Mapping[str, Any],
        context_reset_every: int,
        base_seed: int = 20260911,
    ):
        self.spec = spec
        self.output = output
        self.provider_factory = provider_factory
        self.provider_config = dict(provider_config)
        self.context_reset_every = context_reset_every
        self.base_seed = base_seed

    def run(self, condition: MemoryCondition, runs: int) -> dict[str, Any]:
        if runs < 1:
            raise ValueError("runs must be positive")
        condition_directory = self.output / condition.value
        condition_directory.mkdir(parents=True, exist_ok=False)
        results = [self._run_one(condition, index + 1, condition_directory) for index in range(runs)]
        summary = {
            "condition": condition.value,
            "runs": runs,
            "successful_runs": sum(result["metrics"]["task_success"] for result in results),
            "run_metrics": [result["metrics"] for result in results],
            "test_mode": True,
        }
        (condition_directory / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return summary

    def _run_one(self, condition: MemoryCondition, run_number: int, parent: Path) -> dict[str, Any]:
        run_directory = parent / f"run-{run_number:03d}"
        run_directory.mkdir()
        log = EventLog(run_directory / "events.jsonl")
        seed = self.base_seed + run_number - 1
        provider = self.provider_factory()
        backend = MockLogisticsBackend(self.spec, seed)
        pending_reset: dict[str, Any] | None = None

        def adapter_event(stage: str, **fields: Any) -> None:
            nonlocal pending_reset
            event_type = "scratchpad_update" if stage == "SCRATCHPAD" else "context_reset"
            event = log.emit(event_type, **fields)
            if event_type == "context_reset" and fields.get("context_loss") is True:
                pending_reset = event

        metadata = {
            **self.spec.metadata(),
            "run_id": f"{condition.value}-run-{run_number:03d}",
            "condition": condition.value,
            "seed": seed,
            "prompt_version": PROMPT_VERSION,
            "provider": self.provider_config,
            "context_reset_every_decisions": self.context_reset_every,
            "backend": "deterministic_mock",
            "test_mode": True,
            "outcome_contract_version": 2,
            "fairness_invariants": [
                "benchmark_fingerprint",
                "fixture_sha256",
                "mindustry_version",
                "planner_executor",
                "prompt_version",
                "provider",
                "timeout_seconds",
                "action_budget",
                "seed_schedule",
            ],
        }
        (run_directory / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        log.emit("run_start", metadata=metadata)
        adapter: ResearchDecisionAdapter | None = None
        action_count = 0
        construction_copper = 0
        completion_emitted = False
        flow_milestone_emitted = False
        try:
            observation = backend.reset()
            log.emit("fixture_reset", verified=True, fixture_sha256=self.spec.data["fixture"]["sha256"])
            adapter = ResearchDecisionAdapter(
                provider,
                condition=condition,
                goal=self.spec.goal,
                run_directory=run_directory,
                context_reset_every=self.context_reset_every,
                event_sink=adapter_event,
            )
            log.emit("observation", observation=observation)
            for _ in range(12):
                if log.events[-1]["elapsed_seconds"] >= self.spec.timeout_seconds:
                    log.emit("failure", category="timeout", recoverable=False)
                    break
                try:
                    decision, usage = adapter.decide(observation)
                except (ValueError, RuntimeError) as error:
                    log.emit("invalid_action", reason=str(error))
                    break
                decision_event = log.emit(
                    "llm_decision",
                    valid=True,
                    intent=decision["intent"],
                    reason=decision["reason"],
                    usage=usage.get("providerUsage"),
                    latency_seconds=usage["latencySeconds"],
                )
                if decision_event["elapsed_seconds"] >= self.spec.timeout_seconds:
                    log.emit("failure", category="timeout", recoverable=False)
                    break
                try:
                    backend.validate_intent(decision["intent"])
                except ValueError as error:
                    log.emit("goal_loss", intent=decision["intent"], reason=str(error))
                    break
                proposed_actions = backend.action_count_for(decision["intent"])
                if action_count + proposed_actions > self.spec.action_budget:
                    log.emit("failure", category="action_budget", recoverable=False)
                    break
                try:
                    actions, observation, complete = backend.apply(decision["intent"])
                except ValueError as error:
                    log.emit("goal_loss", intent=decision["intent"], reason=str(error))
                    break
                if pending_reset is not None:
                    log.emit(
                        "recovery",
                        trigger_type="context_reset",
                        trigger_seq=pending_reset["seq"],
                        latency_seconds=max(0.0, decision_event["elapsed_seconds"] - pending_reset["elapsed_seconds"]),
                    )
                    pending_reset = None
                for action in actions:
                    action_count += 1
                    construction_copper += int(action.get("copper_cost", 0))
                    action_key = json.dumps({key: action[key] for key in sorted(action) if key != "accepted"}, sort_keys=True)
                    previous = next((event for event in reversed(log.events) if event["type"] == "action"), None)
                    redundant = bool(previous and previous.get("action_key") == action_key and previous.get("observation_version") == observation["observationVersion"])
                    log.emit(
                        "action",
                        accepted=action["accepted"],
                        action=action,
                        action_key=action_key,
                        observation_version=observation["observationVersion"],
                        redundant=redundant,
                    )
                log.emit("observation", observation=observation)
                if complete and not flow_milestone_emitted:
                    log.emit("milestone", name="flow_verified", success=True)
                    flow_milestone_emitted = True
                if complete and observation["postCompletionReplanned"] and not completion_emitted:
                    log.emit(
                        "completion",
                        success=True,
                        post_completion_replanned=True,
                        useful_construction_copper=construction_copper,
                        total_copper_consumed=construction_copper,
                    )
                    completion_emitted = True
                    break
            log.emit("run_end", reason="completed" if completion_emitted else "failed", success=completion_emitted)
        except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
            log.emit("failure", category="infrastructure", recoverable=False, reason=str(error))
            log.emit("run_end", reason="failed", success=False)
        finally:
            if adapter is not None:
                adapter.close()
            else:
                provider.close()
            backend.cleanup()
            log.emit("cleanup", complete=backend.cleaned)

        metrics = calculate_metrics(log.events)
        (run_directory / "metrics.json").write_text(
            json.dumps(metrics, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return {"metadata": metadata, "metrics": metrics}


def mock_provider_factory(condition: MemoryCondition) -> Callable[[], DecisionProvider]:
    def factory() -> DecisionProvider:
        def policy(context: Mapping[str, Any]) -> Mapping[str, Any]:
            observation = context["observation"]
            if observation["logisticsBuilt"]:
                intent, reason = "wait", "verify or maintain resource flow"
            elif not observation["resourcesSufficient"]:
                intent, reason = "continue_bootstrap", "bootstrap construction copper"
            else:
                intent, reason = "establish_copper_logistics", "build the validated route"
            result: dict[str, Any] = {"intent": intent, "reason": reason}
            if condition is MemoryCondition.STRUCTURED_SCRATCHPAD:
                memory = deepcopy(context["scratchpad"])
                memory["revision"] += 1
                memory["current_subgoal"] = observation["phase"]
                memory["known_state"] = {
                    "copper": observation["resources"]["copper"],
                    "logistics_built": observation["logisticsBuilt"],
                    "flow_verified": observation["flowVerified"],
                }
                memory["plan"] = ["bootstrap", "build route", "verify flow", "maintain"]
                if observation["logisticsBuilt"] and "route built" not in memory["completed"]:
                    memory["completed"].append("route built")
                if observation["flowVerified"] and "flow verified" not in memory["completed"]:
                    memory["completed"].append("flow verified")
                memory["next_step"] = reason
                memory["confidence"] = 1.0 if observation["flowVerified"] else 0.8
                result["scratchpad"] = memory
            return result
        return MockDecisionProvider(policy, provider_id="mock:logistics-v1")
    return factory


def qwen_provider_factory(model: str) -> Callable[[], DecisionProvider]:
    return lambda: OpenCodeResearchProvider(model=model)
