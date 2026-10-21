#!/usr/bin/env bash

set -Eeuo pipefail
source "$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/common.sh"

mindustry_version="${1:-${MINDUSTRY_VERSION:-v159.7}}"
server_root="$LOCAL_ROOT/server"
plugin_dir="$server_root/config/mods"
server_jar="$server_root/server-release.jar"

"$SCRIPT_DIR/build-plugin.sh"
mkdir -p "$plugin_dir"
if [[ ! -f "$server_jar" ]]; then
    download_file \
        "https://github.com/Anuken/Mindustry/releases/download/$mindustry_version/server-release.jar" \
        "$server_jar"
fi
cp "$REPO_ROOT/build/libs/mindustry-llm-bridge.jar" "$plugin_dir/mindustry-llm-bridge.jar"
printf 'Server ready at %s\n' "$server_root"
