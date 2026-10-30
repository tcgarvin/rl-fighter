#!/usr/bin/env bash
# List or stop stray vite servers (preview or dev) belonging to this repo, its worktrees
# included. Orphans of interrupted gate runs keep holding ports (scripts/check_web.sh
# refuses a port that is already in use). Only processes whose vite binary lives under
# this repo are ever touched; other projects' vite servers are left alone.
#
# Usage: scripts/kill_stale_vite.sh                  list this repo's vite servers
#        scripts/kill_stale_vite.sh PID...           stop those (each must be one of ours)
#        scripts/kill_stale_vite.sh --older-than MIN stop every one older than MIN minutes
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# PIDs of node processes running a vite binary under REPO_ROOT.
ours() {
    local pid args
    for pid in $(pgrep -x node || true); do
        args="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null)" || continue
        case "$args" in
            "node $REPO_ROOT/"*"/node_modules/.bin/vite"*) echo "$pid" ;;
        esac
    done
}

age_minutes() { echo $(( $(ps -o etimes= -p "$1") / 60 )); }

list() {
    local pid
    for pid in $(ours); do
        printf '%8s  %5s min  %s\n' "$pid" "$(age_minutes "$pid")" \
            "$(tr '\0' ' ' < "/proc/$pid/cmdline")"
    done
}

stop() {
    local pid=$1 mine
    # Not `ours | grep -q`: grep exits at the first match and, under pipefail, the
    # SIGPIPE in `ours` would read as "not ours".
    mine="$(ours)"
    if ! grep -qx "$pid" <<< "$mine"; then
        echo "Error: $pid is not a vite server of $REPO_ROOT; not touching it" >&2
        return 1
    fi
    kill "$pid"
    echo "stopped $pid"
}

if [[ $# -eq 0 ]]; then
    list
elif [[ $1 == --older-than ]]; then
    [[ $# -eq 2 && $2 =~ ^[0-9]+$ ]] || { echo "Usage: $0 --older-than MIN" >&2; exit 2; }
    for pid in $(ours); do
        if (( $(age_minutes "$pid") >= $2 )); then stop "$pid"; fi
    done
else
    status=0
    for pid in "$@"; do
        [[ $pid =~ ^[0-9]+$ ]] || { echo "Error: not a PID: $pid" >&2; status=2; continue; }
        stop "$pid" || status=1
    done
    exit "$status"
fi
