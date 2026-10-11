"""Read-only SHA-256 verification. No downloads, restore, copying, or deployment."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(manifest: dict, root: Path, only: list[str] | None = None) -> list[dict]:
    entries = manifest["artifacts"]
    ids = [entry["id"] for entry in entries]
    if manifest["schema_version"] != 1 or len(set(ids)) != len(ids):
        raise ValueError("invalid artifact manifest")
    if only and set(only) - set(ids):
        raise ValueError("unknown artifact id")
    results = []
    for entry in entries:
        if only and entry["id"] not in only:
            continue
        relative = Path(entry["bundle_path"])
        if relative.is_absolute() or ".." in relative.parts or not relative.parts:
            raise ValueError("bundle_path must be relative without traversal")
        expected = entry["sha256"]
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("invalid expected SHA-256")
        path = root / relative
        try:
            actual = sha256(path)
            status = "verified" if actual == expected else "mismatch"
        except FileNotFoundError:
            actual, status = None, "missing"
        except OSError:
            actual, status = None, "unreadable"
        results.append({"id": entry["id"], "path": str(path), "status": status,
                        "expected_sha256": expected, "actual_sha256": actual})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--manifest", type=Path, default=ROOT / "experiments/artifacts.json")
    parser.add_argument("--only", action="append")
    args = parser.parse_args()
    results = verify(json.loads(args.manifest.read_text()), args.root, args.only)
    print(json.dumps({"read_only": True, "artifacts": results}, indent=2))
    statuses = {item["status"] for item in results}
    return 1 if statuses & {"mismatch", "unreadable"} else 2 if "missing" in statuses else 0


if __name__ == "__main__":
    raise SystemExit(main())
