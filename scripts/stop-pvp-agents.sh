#!/usr/bin/env bash

set -Eeuo pipefail
source "$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/common.sh"

state_path="$LOCAL_ROOT/pvp-agents.json"
if [[ ! -f "$state_path" ]]; then
    printf 'No recorded RTS agent processes.\n'
    exit 0
fi
python_bin="$(find_python)"

while IFS='|' read -r team pid; do
    [[ -n "$pid" ]] || continue
    if kill -0 "$pid" 2>/dev/null; then
        command_line="$(ps -p "$pid" -o command= 2>/dev/null || true)"
        if [[ "$command_line" == *mindustry_agent* ]]; then
            kill "$pid"
            printf 'Stopped %s agent PID=%s\n' "$team" "$pid"
        else
            printf 'Skipped PID=%s because it is no longer a Mindustry agent.\n' "$pid" >&2
        fi
    fi
done < <("$python_bin" - "$state_path" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    state = json.load(handle)
for key in ("primary", "qwen", "glm", "deepseek"):
    entry = state.get(key)
    if entry and entry.get("pid"):
        print(f"{entry.get('team', key)}|{entry['pid']}")
PY
)
rm -f "$state_path"
