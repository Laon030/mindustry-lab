"""Operational metric definitions derived only from recorded episode events."""

from __future__ import annotations

import math
from typing import Any, Iterable, Mapping


def _numbers(value: Any, keys: set[str]) -> list[float]:
    found: list[float] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            if key in keys and isinstance(nested, (int, float)) and not isinstance(nested, bool):
                found.append(float(nested))
            elif isinstance(nested, (Mapping, list)):
                found.extend(_numbers(nested, keys))
    elif isinstance(value, list):
        for nested in value:
            found.extend(_numbers(nested, keys))
    return found


def _nearest_rank_p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def calculate_metrics(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Calculate the predeclared metrics from a complete JSONL event stream."""
    records = list(events)
    completions = [event for event in records if event.get("type") == "completion" and event.get("success") is True]
    decisions = [event for event in records if event.get("type") == "llm_decision" and event.get("valid") is True]
    actions = [event for event in records if event.get("type") == "action" and event.get("accepted") is True]
    invalid = [event for event in records if event.get("type") == "invalid_action"]
    redundant = [event for event in actions if event.get("redundant") is True]
    goal_losses = [event for event in records if event.get("type") == "goal_loss"]
    recoveries = [event for event in records if event.get("type") == "recovery"]
    failures = [event for event in records if event.get("type") == "failure"]
    resets = [event for event in records if event.get("type") == "context_reset"]
    actual_resets = [event for event in resets if event.get("context_loss") is True]

    latencies = [float(event["latency_seconds"]) for event in decisions if isinstance(event.get("latency_seconds"), (int, float))]
    scratchpad_sizes = [
        int(event["bytes"])
        for event in records
        if event.get("type") == "scratchpad_update"
        and event.get("event") == "updated"
        and isinstance(event.get("bytes"), int)
    ]
    input_tokens = _numbers([event.get("usage") for event in decisions], {"input_tokens", "inputTokens", "input"})
    output_tokens = _numbers([event.get("usage") for event in decisions], {"output_tokens", "outputTokens", "output"})

    # A milestone is not episode success. Require an explicit successful terminal
    # record after post-completion judgement; unresolved failures veto success.
    terminals = [(i, event) for i, event in enumerate(records) if event.get("type") == "run_end"]
    unresolved = set()
    for i, event in enumerate(records):
        kind = event.get("type")
        if kind in {"goal_loss", "failure", "invalid_action"}:
            unresolved.add(event.get("seq", i))
        elif kind == "recovery" and event.get("resolved") is True:
            trigger = event.get("trigger_seq")
            prior = next((item for j, item in enumerate(records[:i]) if item.get("seq", j) == trigger), None)
            if prior and prior.get("type") in {"goal_loss", "failure", "invalid_action"} and prior.get("recoverable") is True:
                unresolved.discard(trigger)
    certified = [(i, event) for i, event in enumerate(records)
                 if event.get("type") == "completion" and event.get("success") is True
                 and event.get("post_completion_replanned") is True]
    task_success = bool(len(terminals) == 1 and certified and not unresolved
                        and terminals[0][0] > certified[-1][0]
                        and terminals[0][1].get("reason") == "completed"
                        and terminals[0][1].get("success") is True
                        and all(event.get("type") == "cleanup" for event in records[terminals[0][0] + 1:]))
    completion_time = min((float(event["elapsed_seconds"]) for _, event in certified), default=None) if task_success else None
    resource_events = [event for event in completions if isinstance(event.get("total_copper_consumed"), (int, float))]
    efficiency = None
    if resource_events:
        final = resource_events[0]
        consumed = float(final["total_copper_consumed"])
        useful = float(final.get("useful_construction_copper", 0))
        efficiency = useful / consumed if consumed > 0 else None

    reset_recovery_latencies = [
        float(event["latency_seconds"])
        for event in recoveries
        if event.get("trigger_type") == "context_reset" and isinstance(event.get("latency_seconds"), (int, float))
        and any(reset.get("seq") == event.get("trigger_seq") and "seq" in reset for reset in actual_resets)
    ]
    recoverable_triggers = len(goal_losses) + len(failures) + len(actual_resets)

    return {
        "task_success": task_success,
        "completion_time_seconds": completion_time,
        "llm_decision_count": len(decisions),
        "action_count": len(actions),
        "invalid_action_count": len(invalid),
        "redundant_action_count": len(redundant),
        "goal_loss_count": len(goal_losses),
        "recovery_count": len(recoveries),
        "recovery_rate": len(recoveries) / recoverable_triggers if recoverable_triggers else None,
        "resource_efficiency": efficiency,
        "token_usage": {
            "input": int(sum(input_tokens)) if input_tokens else None,
            "output": int(sum(output_tokens)) if output_tokens else None,
        },
        "decision_latency_seconds": {
            "mean": sum(latencies) / len(latencies) if latencies else None,
            "p95": _nearest_rank_p95(latencies),
        },
        "scratchpad_size_bytes": {
            "mean": sum(scratchpad_sizes) / len(scratchpad_sizes) if scratchpad_sizes else 0,
            "max": max(scratchpad_sizes, default=0),
        },
        "context_reset_count": len(resets),
        "actual_context_loss_count": len(actual_resets),
        "context_reset_recovery_latency_seconds": {
            "mean": sum(reset_recovery_latencies) / len(reset_recovery_latencies) if reset_recovery_latencies else None,
            "p95": _nearest_rank_p95(reset_recovery_latencies),
        },
    }
