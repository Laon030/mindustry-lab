import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "agent"))

from research.benchmark import BenchmarkSpec
from research.provider import (
    LegacyQwenProviderAdapter,
    MockDecisionProvider,
    OpenCodeResearchProvider,
)


class BenchmarkSpecTests(unittest.TestCase):
    def test_loads_frozen_manifest_and_fingerprints_it(self):
        spec = BenchmarkSpec.load(ROOT / "experiments" / "logistics_benchmark.json")
        self.assertEqual("v159.7", spec.data["mindustry_version"])
        self.assertEqual(360, spec.timeout_seconds)
        self.assertEqual(64, len(spec.fingerprint))

    def test_fixture_verification_reports_exact_mismatch(self):
        spec = BenchmarkSpec.load(ROOT / "experiments" / "logistics_benchmark.json")
        state = {
            "map": "Islands",
            "wave": 1,
            "resources": {"copper": 1, "lead": 0, "graphite": 0, "silicon": 0},
            "unitCounts": {"mono": 1, "poly": 1},
            "rules": dict(spec.data["fixture"]["rules"]),
            "core": dict(spec.data["fixture"]["core"]),
        }
        self.assertEqual(["resources.copper=1, expected 0"], spec.verify_initial_state(state))


class ProviderTests(unittest.TestCase):
    def test_mock_provider_records_context_and_reset(self):
        provider = MockDecisionProvider(lambda _: {"intent": "wait", "reason": "stable"})
        result = provider.decide({"goal": "g", "observation": {"copper": 1}})
        provider.reset_context()
        provider.close()
        self.assertEqual("wait", result.payload["intent"])
        self.assertEqual(1, provider.reset_count)
        self.assertTrue(provider.closed)
        self.assertEqual("g", provider.contexts[0]["goal"])

    def test_legacy_adapter_preserves_existing_decider(self):
        class Legacy:
            model = "existing"
            def decide(self, summary):
                self.summary = summary
                return {"intent": "wait", "reason": "ok"}, {"tokens": 3}
            def close(self):
                self.closed = True

        legacy = Legacy()
        adapter = LegacyQwenProviderAdapter(legacy)
        result = adapter.decide({"goal": "g", "observation": {"phase": "done"}})
        adapter.close()
        self.assertEqual({"phase": "done"}, legacy.summary)
        self.assertEqual(3, result.usage["tokens"])
        self.assertTrue(legacy.closed)

    @patch("research.provider.subprocess.Popen")
    def test_opencode_provider_uses_argument_vector_and_strict_json(self, popen):
        process = popen.return_value
        process.returncode = 0
        process.communicate.return_value = (json.dumps({
            "type": "text",
            "part": {"text": '{"intent":"wait","reason":"done"}'},
            "usage": {"input_tokens": 5, "output_tokens": 2},
        }), "")
        provider = OpenCodeResearchProvider(model="ollama-cloud/qwen3.5:397b")
        result = provider.decide({"goal": "g", "observation": {"phase": "done"}})
        args = popen.call_args.args[0]
        self.assertEqual("opencode", args[0])
        self.assertEqual("run", args[1])
        self.assertNotIn("shell", popen.call_args.kwargs)
        self.assertEqual({"*": "deny"}, json.loads(popen.call_args.kwargs["env"]["OPENCODE_PERMISSION"]))
        self.assertEqual("wait", result.payload["intent"])
        self.assertEqual(5, result.usage["records"][0]["input_tokens"])

    def test_structured_prompt_requests_complete_scratchpad(self):
        prompt = OpenCodeResearchProvider._prompt({
            "goal": "g",
            "observation": {"phase": "build"},
            "scratchpad": {"goal": "g", "next_step": "build"},
        })
        self.assertIn("complete updated scratchpad", prompt)
        self.assertIn('"scratchpad":{...complete updated scratchpad...}', prompt)


if __name__ == "__main__":
    unittest.main()
