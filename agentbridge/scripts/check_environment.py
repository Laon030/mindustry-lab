"""Read-only environment check; never starts a server, provider, or installer."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def python_supported(version: str, implementation: str) -> bool:
    return version == (ROOT / ".python-version").read_text().strip() and implementation == "CPython"


def inspect_environment(python_only: bool = False) -> dict:
    version, implementation = platform.python_version(), platform.python_implementation()
    result = {"python": {"executable": sys.executable, "version": version,
                          "implementation": implementation, "verified_configuration": python_supported(version, implementation)},
              "mindustry_dependency": re.search(r'mindustryVersion = "([^"]+)"', (ROOT / "build.gradle").read_text()).group(1)}
    result["ok"] = result["python"]["verified_configuration"] and result["mindustry_dependency"] == "v159.7"
    if not python_only:
        java = str(Path(os.environ["JAVA_HOME"]) / "bin/java") if os.environ.get("JAVA_HOME") else shutil.which("java")
        try:
            completed = subprocess.run([java, "-version"], capture_output=True, text=True, timeout=10) if java else None
            output = (completed.stderr + completed.stdout).strip() if completed else ""
            match = re.search(r'version "(\d+)[^"]*"', output)
            valid = bool(completed and completed.returncode == 0 and match and match.group(1) == "17")
        except (OSError, subprocess.TimeoutExpired):
            output, valid = "unavailable", False
        result["java"] = {"executable": java, "version_output": output, "java17": valid}
        result["ok"] = result["ok"] and valid
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python-only", action="store_true")
    result = inspect_environment(parser.parse_args().python_only)
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
