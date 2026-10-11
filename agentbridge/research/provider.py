"""Provider boundary shared by controlled memory conditions."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import json
import os
import signal
import subprocess
import tempfile
import threading
import time
from typing import Any, Callable, Mapping, Protocol

try:
    from autonomous_llm_agent import MODEL as DEFAULT_MODEL, strict_json
except ImportError:  # package-style imports
    from agent.autonomous_llm_agent import MODEL as DEFAULT_MODEL, strict_json


@dataclass(frozen=True)
class ProviderResponse:
    payload: Mapping[str, Any]
    usage: Mapping[str, Any] | None
    latency_seconds: float


class DecisionProvider(Protocol):
    provider_id: str

    def decide(self, context: Mapping[str, Any]) -> ProviderResponse: ...
    def reset_context(self) -> None: ...
    def close(self) -> None: ...


class OpenCodeResearchProvider:
    """Current Qwen/OpenCode prototype behind the research provider interface."""

    def __init__(self, model: str = DEFAULT_MODEL, timeout_seconds: float = 120.0):
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.provider_id = f"opencode:{model}"
        self._lock = threading.Lock()
        self._process: subprocess.Popen[str] | None = None
        self._closed = False

    def decide(self, context: Mapping[str, Any]) -> ProviderResponse:
        prompt = self._prompt(context)
        started = time.monotonic()
        config = {
            "permission": {"*": "deny"},
            "share": "disabled",
            "agent": {
                "research-decision": {
                    "mode": "primary",
                    "prompt": "Return only the requested intent JSON. No tools.",
                    "permission": {"*": "deny"},
                    "tools": {"*": False},
                }
            },
        }
        env = dict(
            os.environ,
            OPENCODE_CONFIG_CONTENT=json.dumps(config),
            OPENCODE_PERMISSION=json.dumps({"*": "deny"}),
            OPENCODE_DISABLE_PROJECT_CONFIG="1",
            OPENCODE_DISABLE_AUTOUPDATE="1",
        )
        with tempfile.TemporaryDirectory(prefix="mindustry-research-") as directory:
            with self._lock:
                if self._closed:
                    raise RuntimeError("provider closed")
                self._process = subprocess.Popen(
                    [
                        "opencode", "run", "--pure", "--format", "json",
                        "--agent", "research-decision", "-m", self.model, prompt,
                    ],
                    cwd=directory,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True,
                )
                proc = self._process
            try:
                stdout, stderr = proc.communicate(timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                self._terminate(proc)
                try:
                    stdout, stderr = proc.communicate(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    stdout, stderr = proc.communicate()
                raise RuntimeError("provider timed out")
            finally:
                with self._lock:
                    self._process = None
        latency = time.monotonic() - started
        if proc.returncode != 0:
            detail = stderr.strip() or stdout.strip()
            raise RuntimeError(f"opencode failed ({proc.returncode}): {detail[-500:]}")

        text_parts: list[str] = []
        usage_records: list[Mapping[str, Any]] = []
        for line in stdout.splitlines():
            event = strict_json(line)
            if not isinstance(event, dict):
                raise ValueError("provider event must be a JSON object")
            if event.get("type") in {"error", "tool_use"}:
                raise ValueError("provider returned an error or attempted a tool call")
            if event.get("type") == "text" and isinstance(event.get("part"), dict):
                text = event["part"].get("text")
                if isinstance(text, str):
                    text_parts.append(text)
            if isinstance(event.get("usage"), dict):
                usage_records.append(event["usage"])
            if event.get("type") == "step_finish" and isinstance(event.get("part"), dict):
                part = event["part"]
                if isinstance(part.get("tokens"), dict):
                    usage_records.append({"tokens": part["tokens"], "reportedCost": part.get("cost")})
        if not text_parts:
            raise ValueError("provider returned no text event")
        payload = strict_json("\n".join(text_parts))
        if not isinstance(payload, dict):
            raise ValueError("provider response must be a JSON object")
        usage: Mapping[str, Any] | None = {"records": usage_records} if usage_records else None
        return ProviderResponse(payload=payload, usage=usage, latency_seconds=latency)

    def reset_context(self) -> None:
        # Each `opencode run` is already stateless. This explicit boundary lets a
        # future conversational/local provider clear its hidden message history.
        return None

    def close(self) -> None:
        with self._lock:
            self._closed = True
            if self._process is not None:
                self._terminate(self._process)

    @staticmethod
    def _terminate(process: subprocess.Popen[str]) -> None:
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass

    @staticmethod
    def _prompt(context: Mapping[str, Any]) -> str:
        scratchpad = context.get("scratchpad")
        response_shape = (
            '{"intent":"continue_bootstrap|establish_copper_logistics|wait",'
            '"reason":"..."}'
        )
        memory_instruction = ""
        if scratchpad is not None:
            response_shape = (
                '{"intent":"continue_bootstrap|establish_copper_logistics|wait",'
                '"reason":"...","scratchpad":{...complete updated scratchpad...}}'
            )
            memory_instruction = (
                "Update the supplied structured scratchpad explicitly. Return the complete "
                "bounded scratchpad in the response; do not add free-form memory.\n"
            )
        return (
            "You are the strategic planner for a frozen Mindustry logistics benchmark. "
            "Python performs all coordinates, routing, costs, validation, and execution. "
            "Choose only the next high-level intent. Do not invent observations or mechanics.\n"
            f"Goal: {context['goal']}\n"
            f"Current observation: {json.dumps(context['observation'], sort_keys=True)}\n"
            + (f"Structured scratchpad: {json.dumps(scratchpad, sort_keys=True)}\n" if scratchpad is not None else "")
            + memory_instruction
            + f"Return exactly one JSON object shaped as {response_shape}. No prose or markdown."
        )


class LegacyQwenProviderAdapter:
    """Expose the already runtime-tested logistics provider through the new boundary."""

    def __init__(self, legacy_provider: Any):
        self.legacy_provider = legacy_provider
        self.provider_id = f"legacy:{getattr(legacy_provider, 'model', 'qwen')}"

    def decide(self, context: Mapping[str, Any]) -> ProviderResponse:
        started = time.monotonic()
        decision, usage = self.legacy_provider.decide(dict(context["observation"]))
        return ProviderResponse(decision, usage, time.monotonic() - started)

    def reset_context(self) -> None:
        return None

    def close(self) -> None:
        self.legacy_provider.close()


class MockDecisionProvider:
    """Deterministic provider for repeatable runner and unit tests."""

    def __init__(self, policy: Callable[[Mapping[str, Any]], Mapping[str, Any]], provider_id: str = "mock"):
        self.policy = policy
        self.provider_id = provider_id
        self.contexts: list[Mapping[str, Any]] = []
        self.reset_count = 0
        self.closed = False

    def decide(self, context: Mapping[str, Any]) -> ProviderResponse:
        copied = deepcopy(dict(context))
        self.contexts.append(copied)
        started = time.monotonic()
        payload = deepcopy(dict(self.policy(copied)))
        return ProviderResponse(payload, {"input_tokens": 0, "output_tokens": 0}, time.monotonic() - started)

    def reset_context(self) -> None:
        self.reset_count += 1

    def close(self) -> None:
        self.closed = True
