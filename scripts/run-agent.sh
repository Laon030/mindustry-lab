#!/usr/bin/env bash

set -Eeuo pipefail
source "$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/common.sh"

model="${LLM_MODEL:-deepseek-v4.1-flash:cloud}"
reasoning_effort="${LLM_REASONING_EFFORT:-none}"
max_turns="${MAX_TURNS:-20}"
dry_run="false"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model) model="$2"; shift 2 ;;
        --reasoning-effort) reasoning_effort="$2"; shift 2 ;;
        --max-turns) max_turns="$2"; shift 2 ;;
        --dry-run) dry_run="true"; shift ;;
        *) die "Unknown option: $1" ;;
    esac
done

export LLM_MODEL="$model"
export LLM_REASONING_EFFORT="$reasoning_effort"
python_bin="$(find_python)"
arguments=(-m mindustry_agent --max-turns "$max_turns")
if [[ "$dry_run" == "true" ]]; then
    arguments+=(--dry-run)
fi
cd "$REPO_ROOT"
exec "$python_bin" "${arguments[@]}"
