"""Validate the field-status metadata specification; does not invent run values."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def validate_metadata(value: dict, contract: dict | None = None) -> None:
    spec = contract or json.loads((ROOT / "contracts/experiment_metadata.json").read_text())
    if not isinstance(value, dict) or set(value) != set(spec["fields"]) | {"schema_version"}:
        raise ValueError("metadata fields must match the complete contract")
    if type(value["schema_version"]) is not int or value["schema_version"] != spec["schema_version"]:
        raise ValueError("unsupported metadata schema version")
    types = {"string": (str,), "integer": (int,), "number": (int, float), "boolean": (bool,)}
    for name, rule in spec["fields"].items():
        item = value[name]
        if not isinstance(item, dict) or set(item) != {"status", "value", "source"}:
            raise ValueError(f"{name}: explicit availability/value/source required")
        if item["status"] not in spec["availability"] or not isinstance(item["source"], str) or not item["source"].strip():
            raise ValueError(f"{name}: invalid status or missing provenance/reason")
        data = item["value"]
        if item["status"] != "known":
            if data is not None:
                raise ValueError(f"{name}: unknown/unavailable/not_applicable requires null")
            continue
        if type(data) not in types[rule["type"]]:
            raise ValueError(f"{name}: wrong known value type")
        if isinstance(data, str) and not data.strip():
            raise ValueError(f"{name}: empty string")
        if type(data) in (int, float):
            if not math.isfinite(data) or "minimum" in rule and data < rule["minimum"] or "maximum" in rule and data > rule["maximum"]:
                raise ValueError(f"{name}: out of range")
        if "pattern" in rule and not re.fullmatch(rule["pattern"], data):
            raise ValueError(f"{name}: invalid digest/revision")
        if "enum" in rule and data not in rule["enum"]:
            raise ValueError(f"{name}: invalid enum")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    try:
        validate_metadata(json.loads(args.path.read_text()))
    except (ValueError, OSError) as error:
        print(str(error))
        return 1
    print("Metadata contract valid; availability does not imply experiment execution.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
