#!/usr/bin/env bash

set -Eeuo pipefail
source "$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/common.sh"

export MINDUSTRY_TEAM_TOKENS="sharded=${PRIMARY_TOKEN:-local-primary-team-token};crux=${DEEPSEEK_TOKEN:-local-deepseek-team-token}"
export MINDUSTRY_AUTO_CORE_DEFENSE="${MINDUSTRY_AUTO_CORE_DEFENSE:-true}"
export PVP_PRIMARY_MODEL="${PRIMARY_MODEL:-glm-5.3-flash:cloud}"
export PVP_DEEPSEEK_MODEL="${DEEPSEEK_MODEL:-deepseek-v4.1-flash:cloud}"
export PVP_PRIMARY_REASONING_EFFORT="${PRIMARY_REASONING_EFFORT:-low}"
export PVP_DEEPSEEK_REASONING_EFFORT="${DEEPSEEK_REASONING_EFFORT:-none}"

printf 'RTS teams: %s=sharded, %s=crux\n' "$PVP_PRIMARY_MODEL" "$PVP_DEEPSEEK_MODEL"
printf 'At the server prompt enter: showcase-rts-start\n'
printf 'Reconnect the client, then enter in game chat: /agent-start 500\n'
printf 'For neutral free-camera viewing enter: /spectate\n'
exec "$SCRIPT_DIR/run-server.sh"
