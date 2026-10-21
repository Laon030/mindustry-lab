#!/usr/bin/env bash

set -Eeuo pipefail
source "$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/lib/common.sh"

mindustry_version="${1:-${MINDUSTRY_VERSION:-v159.7}}"
client_root="$LOCAL_ROOT/client"
client_jar="$client_root/Mindustry.jar"
mkdir -p "$client_root"
if [[ ! -f "$client_jar" ]]; then
    download_file \
        "https://github.com/Anuken/Mindustry/releases/download/$mindustry_version/Mindustry.jar" \
        "$client_jar"
fi
printf 'Mindustry client ready at %s\n' "$client_jar"
