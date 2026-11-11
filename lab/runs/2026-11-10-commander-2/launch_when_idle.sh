#!/usr/bin/env bash
# Start the night's run once the owner is away: wait for START (default midnight), then
# every 10 minutes look at the owner's login sessions. Launch when every one of them has
# been idle for IDLE_MIN minutes (logind's IdleHint) and no game is running; then run
# morning.sh when training ends. Run it detached:
#
#   nohup setsid lab/runs/2026-11-10-commander-2/launch_when_idle.sh \
#       > lab/runs/2026-11-10-commander-2/launch.out 2>&1 &
#
# Env: START ("00:00"), DEADLINE ("08:00"), IDLE_MIN (15), OWNER (timg).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-10-commander-2
START=${START:-"00:00"}
DEADLINE=${DEADLINE:-"08:00"}
IDLE_MIN=${IDLE_MIN:-15}
OWNER=${OWNER:-timg}

start_at=$(date -d "$START" +%s)
# A START already past today means tomorrow's (launched in the evening for midnight).
(( start_at > $(date +%s) )) || start_at=$(date -d "tomorrow $START" +%s)
deadline_at=$(date -d "$DEADLINE" +%s)
(( deadline_at > start_at )) || deadline_at=$(date -d "tomorrow $DEADLINE" +%s)
echo "$(date +%H:%M:%S) waiting for $(date -d "@$start_at" '+%F %H:%M'); deadline $(date -d "@$deadline_at" '+%F %H:%M')"
sleep $(( start_at - $(date +%s) ))

owner_away() {
    local session idle since now
    now=$(date +%s)
    while read -r session; do
        [[ -n $session ]] || continue
        idle=$(loginctl show-session "$session" -p IdleHint --value)
        since=$(loginctl show-session "$session" -p IdleSinceHint --value)
        [[ $idle == yes ]] || { echo "session $session is in use"; return 1; }
        if (( now - since / 1000000 < IDLE_MIN * 60 )); then
            echo "session $session idle under $IDLE_MIN min"
            return 1
        fi
    done < <(loginctl list-sessions --no-legend | awk -v u="$OWNER" '$3 == u {print $1}')
    # By process name, not command line: Steam's reaper wraps every game it starts,
    # wineserver runs under every Proton or Wine game.
    if pgrep -u "$OWNER" -x 'reaper|wineserver|gamescope.*' > /dev/null; then
        echo "a game is running"
        return 1
    fi
    return 0
}

until why=$(owner_away); do
    echo "$(date +%H:%M:%S) not yet: $why"
    if (( $(date +%s) > deadline_at - 3600 )); then
        echo "$(date +%H:%M:%S) under an hour to the deadline: no run tonight"
        exit 1
    fi
    sleep 600
done
echo "$(date +%H:%M:%S) owner away: launching"
DEADLINE="@$deadline_at" "$HERE/run.sh" >> "$HERE/run.out" 2>&1
"$HERE/morning.sh" > "$HERE/morning.out" 2>&1
echo "$(date +%H:%M:%S) done: night"
