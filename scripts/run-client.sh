#!/usr/bin/env bash

set -Eeuo pipefail
source "$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/common.sh"

client_root="$LOCAL_ROOT/client"
client_jar="$client_root/Mindustry.jar"
if [[ ! -f "$client_jar" ]]; then
    "$SCRIPT_DIR/setup-client.sh"
fi
"$SCRIPT_DIR/install-client-mod.sh"
java_bin="$(find_java)"
java_arguments=()
if [[ "$(uname -s)" == "Darwin" ]]; then
    java_arguments+=(-XstartOnFirstThread)
fi

cd "$client_root"
nohup "$java_bin" "${java_arguments[@]}" -jar "$client_jar" >"$LOCAL_ROOT/client.log" 2>&1 </dev/null &
printf 'Mindustry opened with PID %s. Join 127.0.0.1:6567.\n' "$!"
