#!/usr/bin/env bash
# The dock-pilot measures (plan.md "Measures") on one checkpoint. Writes into OUT;
# `summary.py eval OUT` prints them, `summary.py report` judges them against the parent.
#
#   CKPT=lab/runs/2026-11-20-dock-pilot/dock600/checkpoints/ppo_bc_1000.pt NAME=dock600_1000 \
#       OUT=lab/runs/2026-11-20-dock-pilot/eval/dock600_1000 lab/runs/2026-11-20-dock-pilot/eval.sh
#   CKPT=lab/runs/2026-11-14-goto-school/followers_school/checkpoints/ppo_bc_600.pt \
#       NAME=parent600 OUT=lab/runs/2026-11-20-dock-pilot/eval/parent600 .../eval.sh
#   SMOKE=1 CKPT=... OUT=/tmp/x .../eval.sh
#
# (a) dock drills, calm and threat (spacefight.eval.drills --kinds dock_calm,dock_threat,
#     with the order-hidden pass): dock.json
# (b) recalls in real matches: the candidate flies every strike craft of both sides of a
#     carrier battle and a station assault, scripted commanders, which recall below half
#     hull (../2026-11-20-dock-repair/dock_eval.py): dockm_carrier.json, dockm_station.json
# (c) no regression: the order drill eval and gate (drills.json), the mission eval against
#     the script (carrier battle, convoy; missions.json) and the fleet_v1 suite against the
#     script (fleet.json)
#
# Env: CKPT (required), NAME (default its stem), OUT (required), THREADS (2), QUICK=1
# (the periodic sizes), SMOKE=1 (tiny sizes), DATA_ROOT (the checkout holding lab/runs
# weights; default this one), PY (default .venv/bin/python), NICE (19). Rerunning skips
# every output that exists.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-20-dock-pilot
DATA_ROOT=${DATA_ROOT:-$ROOT}
[[ -n ${CKPT:-} ]] || { echo "set CKPT" >&2; exit 2; }
[[ -n ${OUT:-} ]] || { echo "set OUT" >&2; exit 2; }
[[ $CKPT = /* || -f $CKPT ]] || CKPT=$DATA_ROOT/$CKPT
[[ -f $CKPT ]] || { echo "missing $CKPT" >&2; exit 2; }
CKPT=$(realpath "$CKPT")
NAME=${NAME:-$(basename "$CKPT" .pt)}
PY=${PY:-.venv/bin/python}
THREADS=${THREADS:-2}
NICE=${NICE:-19}
if [[ ${SMOKE:-0} == 1 ]]; then
    N_DOCK=4 N_DOCKM=4 N_DRILL=4 N_MISSION=12 N_FLEET=2
elif [[ ${QUICK:-0} == 1 ]]; then
    N_DOCK=64 N_DOCKM=96 N_DRILL=32 N_MISSION=96 N_FLEET=8
else
    N_DOCK=128 N_DOCKM=256 N_DRILL=64 N_MISSION=192 N_FLEET=16
fi
mkdir -p "$OUT"
export OMP_NUM_THREADS=$THREADS MKL_NUM_THREADS=$THREADS
"$PY" - "$NAME" "$CKPT" "$OUT/pilot.json" <<'EOF'
import json, sys
pid, ckpt, out = sys.argv[1:]
json.dump({"schema": "rlf.live_pilots/1", "pilots": [{"id": pid, "checkpoint": ckpt}]},
          open(out, "w"), indent=1)
EOF

step() {  # $1 output file, then the command
    local out=$1; shift
    if [[ -s $out ]]; then echo "skip $out"; return; fi
    echo "$(date +%H:%M:%S) $out"
    local t0=$SECONDS
    nice -n "$NICE" "$@" > "$out.log" 2>&1 || { echo "FAILED: $out (see $out.log)" >&2; return 1; }
    echo "  $(( SECONDS - t0 )) s"
}

# (a) Dock drills.
step "$OUT/dock.json" "$PY" -m spacefight.eval.drills --a "$CKPT" --name "$NAME" \
    --kinds dock_calm,dock_threat --n-per-kind $N_DOCK --threads "$THREADS" \
    --out "$OUT/dock.json"
# (b) Recalls in matches, scripted commanders, the candidate on every strike slot.
DE="$PY $HERE/../2026-11-20-dock-repair/dock_eval.py --threads $THREADS --n $N_DOCKM --pilots $OUT/pilot.json --checkpoint-root $DATA_ROOT"
step "$OUT/dockm_carrier.json" $DE --mission carrier_battle --out "$OUT/dockm_carrier.json"
step "$OUT/dockm_station.json" $DE --mission station_assault --out "$OUT/dockm_station.json"
# (c) No regression: order drills, missions and fleets against the script.
step "$OUT/drills.json" "$PY" -m spacefight.eval.drills --a "$CKPT" --name "$NAME" \
    --n-per-kind $N_DRILL --threads "$THREADS" --out "$OUT/drills.json"
step "$OUT/missions.json" "$PY" -m spacefight.eval.missions --a "$CKPT" --b script \
    --n-per-mission $N_MISSION --n-threads "$THREADS" --out "$OUT/missions.json"
step "$OUT/fleet.json" "$PY" -m spacefight.eval.fleet --a "$CKPT" --b script \
    --n-per-roster $N_FLEET --n-threads "$THREADS" --out "$OUT/fleet.json"
echo "$(date +%H:%M:%S) done: $OUT"
"$PY" $HERE/summary.py eval "$OUT"
