from __future__ import annotations

import pathlib
import re
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = (
    "build-plugin.sh",
    "setup-server.sh",
    "run-server.sh",
    "run-rts-server.sh",
    "run-agent.sh",
    "run-pvp-agents.sh",
    "stop-pvp-agents.sh",
    "setup-client.sh",
    "install-client-mod.sh",
    "run-client.sh",
    "lib/common.sh",
)


class CrossPlatformLauncherTest(unittest.TestCase):
    def test_shell_launchers_have_bash_shebangs_and_lf_endings(self) -> None:
        for relative in SCRIPTS:
            data = (ROOT / "scripts" / relative).read_bytes()
            self.assertTrue(data.startswith(b"#!/usr/bin/env bash\n"), relative)
            self.assertNotIn(b"\r\n", data, relative)

    def test_shell_launchers_do_not_embed_windows_paths(self) -> None:
        windows_path = re.compile(r"[A-Za-z]:\\")
        for relative in SCRIPTS:
            text = (ROOT / "scripts" / relative).read_text(encoding="utf-8")
            self.assertIsNone(windows_path.search(text), relative)

    def test_readme_is_english_and_showcase_focused(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIsNone(re.search(r"[가-힣]", readme))
        self.assertIn("showcase-rts-start", readme)
        self.assertIn("./scripts/run-rts-server.sh", readme)
        self.assertIn("Core destruction as the only victory condition", readme)


if __name__ == "__main__":
    unittest.main()
