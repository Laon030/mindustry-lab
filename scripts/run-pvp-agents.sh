#!/usr/bin/env bash

set -Eeuo pipefail
source "$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/common.sh"

primary_model="${PRIMARY_MODEL:-glm-5.3-flash:cloud}"
deepseek_model="${DEEPSEEK_MODEL:-deepseek-v4.1-flash:cloud}"
primary_token="${PRIMARY_TOKEN:-local-primary-team-token}"
deepseek_token="${DEEPSEEK_TOKEN:-local-deepseek-team-token}"
primary_reasoning="${PRIMARY_REASONING_EFFORT:-low}"
deepseek_reasoning="${DEEPSEEK_REASONING_EFFORT:-none}"
api_url="${MINDUSTRY_API_URL:-http://127.0.0.1:8765}"
api_url="${api_url%/}"
max_turns="${MAX_TURNS:-500}"
python_bin="$(find_python)"

"$python_bin" - "$api_url" "$primary_token" "$deepseek_token" <<'PY'
import json
import sys
import urllib.request

base, primary_token, deepseek_token = sys.argv[1:]
for team, token in (("sharded", primary_token), ("crux", deepseek_token)):
    headers = {"Authorization": f"Bearer {token}", "X-Mindustry-Team": team}

    def get(path):
        request = urllib.request.Request(base + path, headers=headers)
        with urllib.request.urlopen(request, timeout=5) as response:
            return json.load(response)

    health = get("/health")
    state = get("/v1/state")
    if not health.get("ok") or health.get("controlled_team") != team:
        raise SystemExit(f"{team} authentication failed")
    if not state.get("rules", {}).get("pvp") or not state.get("core"):
        raise SystemExit("The RTS showcase is not ready. Enter showcase-rts-start first.")
PY

run_directory="$REPO_ROOT/runs"
state_path="$LOCAL_ROOT/pvp-agents.json"
mkdir -p "$run_directory" "$LOCAL_ROOT"
stamp="$(date '+%Y%m%d-%H%M%S')"
export MINDUSTRY_API_URL="$api_url"
cd "$REPO_ROOT"

nohup "$python_bin" -m mindustry_agent \
    --model "$primary_model" --reasoning-effort "$primary_reasoning" \
    --team sharded --game-token "$primary_token" --max-turns "$max_turns" \
    >"$run_directory/$stamp-pvp-primary.out.log" \
    2>"$run_directory/$stamp-pvp-primary.err.log" </dev/null &
primary_pid=$!

nohup "$python_bin" -m mindustry_agent \
    --model "$deepseek_model" --reasoning-effort "$deepseek_reasoning" \
    --team crux --game-token "$deepseek_token" --max-turns "$max_turns" \
    >"$run_directory/$stamp-pvp-deepseek.out.log" \
    2>"$run_directory/$stamp-pvp-deepseek.err.log" </dev/null &
deepseek_pid=$!

if ! kill -0 "$primary_pid" 2>/dev/null || ! kill -0 "$deepseek_pid" 2>/dev/null; then
    kill "$primary_pid" "$deepseek_pid" 2>/dev/null || true
    die "One or both agent processes failed to start. Check $run_directory/$stamp-pvp-*.err.log"
fi

"$python_bin" - "$state_path" "$primary_pid" "$primary_model" "$deepseek_pid" "$deepseek_model" <<'PY'
import datetime
import json
import sys

path, primary_pid, primary_model, deepseek_pid, deepseek_model = sys.argv[1:]
state = {
    "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "primary": {"pid": int(primary_pid), "model": primary_model, "team": "sharded"},
    "deepseek": {"pid": int(deepseek_pid), "model": deepseek_model, "team": "crux"},
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(state, handle, indent=2)
PY

printf 'RTS agents started: sharded PID=%s, crux PID=%s\n' "$primary_pid" "$deepseek_pid"
printf 'Run records: %s/*.jsonl\n' "$run_directory"
