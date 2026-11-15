#!/usr/bin/env bash
# The whole night: training to DEADLINE (run.sh), then the morning's measurements
# (morning.sh), which start only if training ended cleanly. Run it detached:
#
#   DEADLINE="tomorrow 06:30" nohup setsid lab/runs/2026-11-14-goto-school-2/night.sh \
#       >> lab/runs/2026-11-14-goto-school-2/launch.out 2>&1 &
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-14-goto-school-2
echo "$(date +%H:%M:%S) training to $(date -d "$DEADLINE" '+%F %H:%M')"
"$HERE/run.sh" > "$HERE/run.out" 2>&1
echo "$(date +%H:%M:%S) training over; morning.sh"
"$HERE/morning.sh" > "$HERE/morning.out" 2>&1
echo "$(date +%H:%M:%S) done: night"
