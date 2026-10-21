#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
REPO_ROOT="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)"
LOCAL_ROOT="${MINDUSTRY_LOCAL_ROOT:-$REPO_ROOT/.local}"

die() {
    printf 'error: %s\n' "$*" >&2
    exit 1
}
require_command() {
    command -v "$1" >/dev/null 2>&1 || die "$1 was not found on PATH."
}

find_python() {
    if command -v python3 >/dev/null 2>&1; then
        command -v python3
    elif command -v python >/dev/null 2>&1; then
        command -v python
    else
        die "Python 3.10 or newer was not found on PATH."
    fi
}

find_java() {
    if [[ -n "${JAVA_HOME:-}" && -x "$JAVA_HOME/bin/java" ]]; then
        printf '%s\n' "$JAVA_HOME/bin/java"
        return
    fi
    if [[ "$(uname -s)" == "Darwin" && -x /usr/libexec/java_home ]]; then
        local mac_java_home
        mac_java_home="$(/usr/libexec/java_home -v 17 2>/dev/null || true)"
        if [[ -n "$mac_java_home" && -x "$mac_java_home/bin/java" ]]; then
            printf '%s\n' "$mac_java_home/bin/java"
            return
        fi
    fi
    command -v java 2>/dev/null || die "JDK 17 was not found. Set JAVA_HOME or add java to PATH."
}

download_file() {
    local url="$1"
    local destination="$2"
    local temporary="${destination}.part.$$"
    rm -f "$temporary"
    if command -v curl >/dev/null 2>&1; then
        curl --fail --location --retry 3 --output "$temporary" "$url"
    elif command -v wget >/dev/null 2>&1; then
        wget --output-document="$temporary" "$url"
    else
        die "curl or wget is required to download Mindustry."
    fi
    mv "$temporary" "$destination"
}

port_is_open() {
    local python_bin="$1"
    local port="$2"
    "$python_bin" - "$port" <<'PY'
import socket
import sys

sock = socket.socket()
sock.settimeout(0.25)
try:
    result = sock.connect_ex(("127.0.0.1", int(sys.argv[1])))
finally:
    sock.close()
raise SystemExit(0 if result == 0 else 1)
PY
}

mindustry_data_dir() {
    if [[ -n "${MINDUSTRY_DATA_DIR:-}" ]]; then
        printf '%s\n' "$MINDUSTRY_DATA_DIR"
        return
    fi
    case "$(uname -s)" in
        Darwin) printf '%s\n' "$HOME/Library/Application Support/Mindustry" ;;
        Linux) printf '%s\n' "${XDG_DATA_HOME:-$HOME/.local/share}/Mindustry" ;;
        *) die "Unsupported platform. Set MINDUSTRY_DATA_DIR explicitly." ;;
    esac
}
