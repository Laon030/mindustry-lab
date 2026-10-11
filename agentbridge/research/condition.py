"""Memory-condition adapter used by the unchanged logistics runtime."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

from .provider import DecisionProvider
from .scratchpad import ScratchpadStore


_ALLOWED_INTENTS = {
    "continue_bootstrap",
    "establish_copper_logistics",
    "wait",
    "reconsider",
}


class MemoryCondition(str, Enum):
    NO_SCRATCHPAD = "no_scratchpad"
    STRUCTURED_SCRATCHPAD = "structured_scratchpad"
    RECENT_HISTORY = "recent_history"


EventSink = Callable[[str, Any], None]


class ResearchDecisionAdapter:
    """Give LogisticsRuntime its existing decide(summary) interface."""

    def __init__(
        self,
        provider: DecisionProvider,
        *,
        condition: MemoryCondition,
        goal: str,
        run_directory: str | Path,
        context_reset_every: int = 0,
        event_sink: Callable[..., None] | None = None,
    ):
        if condition is MemoryCondition.RECENT_HISTORY:
            raise ValueError("recent_history is reserved for a later controlled condition")
        if context_reset_every < 0:
            raise ValueError("context_reset_every cannot be negative")
        self.provider = provider
        self.condition = condition
        self.goal = goal
        self.context_reset_every = context_reset_every
        self.event_sink = event_sink or (lambda *_args, **_kwargs: None)
        self.decision_count = 0
        self.reset_count = 0
        self.store: ScratchpadStore | None = None
        if condition is MemoryCondition.STRUCTURED_SCRATCHPAD:
            self.store = ScratchpadStore(Path(run_directory) / "scratchpad.json", goal)
            value = self.store.initialize()
            self.event_sink("SCRATCHPAD", event="initialized", revision=value["revision"], bytes=self.store.size_bytes())

    def decide(self, observation: Mapping[str, Any]):
        if self.context_reset_every and self.decision_count and self.decision_count % self.context_reset_every == 0:
            self.provider.reset_context()
            self.reset_count += 1
            # Legacy event name retained for log readers. Calling a hook does not
            # establish that any conversational information was actually erased.
            fields: dict[str, Any] = {"event": "context_reset", "resetIndex": self.reset_count,
                                      "context_loss": False, "semantics": "boundary_hook_only"}
            if self.store is not None:
                reloaded = self.store.load()
                fields.update(scratchpadRevision=reloaded["revision"], scratchpadBytes=self.store.size_bytes())
            self.event_sink("CONTEXT RESET", **fields)

        context: dict[str, Any] = {"goal": self.goal, "observation": dict(observation)}
        if self.store is not None:
            context["scratchpad"] = self.store.load()
        response = self.provider.decide(context)
        expected = {"intent", "reason", "scratchpad"} if self.store is not None else {"intent", "reason"}
        if set(response.payload) != expected:
            raise ValueError(f"provider response fields must be exactly {sorted(expected)}")
        intent = response.payload.get("intent")
        reason = response.payload.get("reason")
        if intent not in _ALLOWED_INTENTS:
            raise ValueError("invalid high-level logistics intent")
        if not isinstance(reason, str) or not 1 <= len(reason) <= 400:
            raise ValueError("decision reason must be 1..400 characters")

        scratchpad_bytes = 0
        scratchpad_revision = None
        if self.store is not None:
            updated = self.store.update(response.payload["scratchpad"])
            scratchpad_revision = updated["revision"]
            scratchpad_bytes = self.store.size_bytes()
            self.event_sink(
                "SCRATCHPAD",
                event="updated",
                revision=scratchpad_revision,
                bytes=scratchpad_bytes,
            )

        self.decision_count += 1
        usage = {
            "provider": self.provider.provider_id,
            "providerUsage": response.usage,
            "latencySeconds": response.latency_seconds,
            "scratchpadBytes": scratchpad_bytes,
            "scratchpadRevision": scratchpad_revision,
        }
        return {"intent": intent, "reason": reason}, usage

    def close(self) -> None:
        self.provider.close()
