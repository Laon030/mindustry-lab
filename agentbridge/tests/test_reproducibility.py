from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

from scripts.check_environment import python_supported
from scripts.validate_metadata import validate_metadata
from scripts.verify_artifacts import verify

ROOT = Path(__file__).resolve().parents[1]


class EnvironmentContractTests(unittest.TestCase):
    def test_exact_tested_python_only(self):
        self.assertTrue(python_supported("3.13.5", "CPython"))
        for version in ("3.9.6", "3.13.6", "3.14.0"):
            self.assertFalse(python_supported(version, "CPython"))
        self.assertFalse(python_supported("3.13.5", "PyPy"))

    def test_no_undeclared_pip_dependencies_and_ci_uses_pin(self):
        lines = (ROOT / "requirements-dev.txt").read_text().splitlines()
        self.assertTrue(all(not line.strip() or line.startswith("#") for line in lines))
        workflow = (ROOT / ".github/workflows/gradle.yml").read_text()
        for required in ("python-version-file: '.python-version'", "java-version: 17",
                         "python -m unittest discover -s tests -v", "compileall",
                         "build/libs/MindustryAgentBridge.jar", "--no-index"):
            self.assertIn(required, workflow)
        self.assertIn("rootProject.name = 'MindustryAgentBridge'", (ROOT / "settings.gradle").read_text())

    def test_dependency_verification_matches_artifact_digest(self):
        namespace = {"g": "https://schema.gradle.org/dependency-verification"}
        tree = ET.parse(ROOT / "gradle/verification-metadata.xml")
        component = tree.find(".//g:component", namespace)
        self.assertEqual("v159.7", component.attrib["version"])
        digest = component.find(".//g:sha256", namespace).attrib["value"]
        artifacts = json.loads((ROOT / "experiments/artifacts.json").read_text())["artifacts"]
        self.assertEqual(digest, next(a["sha256"] for a in artifacts if a["id"] == "mindustry-dependency"))
        self.assertRegex((ROOT / "gradle/wrapper/gradle-wrapper.properties").read_text(), r"distributionSha256Sum=[0-9a-f]{64}")


class ApiAlignmentTests(unittest.TestCase):
    def test_inventory_matches_registered_methods_actions_and_source(self):
        api = json.loads((ROOT / "contracts/agentbridge_api.json").read_text())
        server = (ROOT / "src/agentbridge/StateHttpServer.java").read_text()
        actions = (ROOT / "src/agentbridge/ActionHttpHandler.java").read_text()
        self.assertEqual(set(api["endpoints"]), set(re.findall(r'createContext\("([^"]+)"', server)))
        self.assertIn('"GET".equals(exchange.getRequestMethod())', server)
        self.assertIn('"POST".equals(exchange.getRequestMethod())', actions)
        actual_actions = set(re.findall(r'"(\w+)"\.equals\(request.action\)', actions))
        self.assertEqual(set(api["endpoints"]["/action"]["actions"]), actual_actions)
        for path, expected in api["source_sha256"].items():
            self.assertEqual(expected, hashlib.sha256((ROOT / path).read_bytes()).hexdigest(), path)

    def test_v1_manifest_uses_real_api_not_normalized_fixture_shape(self):
        spec = json.loads((ROOT / "experiments/logistics_benchmark.json").read_text())
        api = json.loads((ROOT / "contracts/agentbridge_api.json").read_text())
        obs = spec["observation"]
        self.assertEqual(["/state"], obs["endpoints"])
        self.assertEqual("/action", obs["action_endpoint"])
        self.assertEqual(api["endpoints"]["/state"]["active_required_fields"], obs["required_fields"])
        self.assertIn("NOT raw /state", obs["fixture_verification"])
        self.assertEqual(360, spec["budgets"]["timeout_seconds"])
        self.assertEqual(80, spec["budgets"]["action_budget"])
        artifacts = json.loads((ROOT / "experiments/artifacts.json").read_text())["artifacts"]
        self.assertEqual(spec["fixture"]["sha256"], next(a["sha256"] for a in artifacts if a["id"] == "logistics-save"))
        self.assertFalse(Path(spec["fixture"]["save_path"]).is_absolute())


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.manifest = {"schema_version": 1, "artifacts": [{"id": "fixture", "bundle_path": "save.msav",
                           "sha256": hashlib.sha256(b"original").hexdigest()}]}

    def test_missing_matching_corrupt_and_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual("missing", verify(self.manifest, root)[0]["status"])
            path = root / "save.msav"
            path.write_bytes(b"original")
            self.assertEqual("verified", verify(self.manifest, root)[0]["status"])
            path.write_bytes(b"corrupt")
            self.assertEqual("mismatch", verify(self.manifest, root)[0]["status"])
            self.assertEqual(b"corrupt", path.read_bytes())

    def test_unknown_id_traversal_and_bad_digest_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                verify(self.manifest, Path(directory), ["unknown"])
            for key, value in (("bundle_path", "../save"), ("bundle_path", "/save"), ("sha256", "unknown")):
                bad = deepcopy(self.manifest)
                bad["artifacts"][0][key] = value
                with self.assertRaises(ValueError):
                    verify(bad, Path(directory))


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.example = json.loads((ROOT / "contracts/experiment_metadata.example.json").read_text())

    def test_explicit_unknowns_and_known_values(self):
        validate_metadata(self.example)
        self.example["dirty_worktree"] = {"status": "known", "value": False, "source": "git status"}
        self.example["temperature"] = {"status": "known", "value": 0.0, "source": "effective provider config"}
        self.example["exact_model_revision"] = {"status": "unavailable", "value": None, "source": "provider did not expose digest"}
        validate_metadata(self.example)

    def test_missing_fake_unknown_and_bad_known_values_fail(self):
        missing = deepcopy(self.example)
        missing.pop("model_identifier")
        with self.assertRaises(ValueError):
            validate_metadata(missing)
        for field, item in (("seed", {"status": "unknown", "value": 0, "source": "not measured"}),
                            ("top_p", {"status": "known", "value": 2.0, "source": "config"}),
                            ("max_output_tokens", {"status": "known", "value": True, "source": "config"}),
                            ("agentbridge_jar_sha256", {"status": "known", "value": "fake", "source": "file"}),
                            ("temperature", {"status": "known", "value": float("nan"), "source": "config"})):
            bad = deepcopy(self.example)
            bad[field] = item
            with self.assertRaises(ValueError):
                validate_metadata(bad)


if __name__ == "__main__":
    unittest.main()
