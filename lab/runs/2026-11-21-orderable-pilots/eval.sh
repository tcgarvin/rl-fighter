#!/usr/bin/env bash
# The orderable-pilots measures (plan.md "Measures") on one checkpoint. Writes into OUT;
# `summary.py eval OUT` prints them, `summary.py report` sets them beside the parent's.
#
#   CKPT=lab/runs/2026-11-21-orderable-pilots/kitedock/checkpoints/ppo_bc_1000.pt \
#       NAME=kitedock_1000 OUT=lab/runs/2026-11-21-orderable-pilots/eval/kitedock_1000 \
#       lab/runs/2026-11-21-orderable-pilots/eval.sh
#   QUICK=1 CKPT=... OUT=... .../eval.sh     (the periodic subset, (a) and (b))
#   SMOKE=1 CKPT=... OUT=/tmp/x .../eval.sh  (tiny sizes; with QUICK=1 the subset)
#
# (a) the drill eval, all five kinds (go-to, attack, defend, dock_calm, dock_threat; the
#     default since 2026-11-21), each flown again with the order hidden: drills.json
# (b) recalls in real matches: the candidate flies every strike craft of both sides of a
#     carrier battle and a station assault, scripted commanders, which recall below half
#     hull (../2026-11-20-dock-repair/dock_eval.py): dockm_carrier.json, dockm_station.json
# Full evals only (not QUICK):
# (c) wins against the script: the mission eval (carrier battle, convoy, station assault;
#     missions.json) and the fleet_v1 suite (fleet.json)
# (d) the order cost (../2026-11-17-order-cost/order_rules.py, as the kite drills measured
#     it): 3 v 3, 24 blocks (1,152 matches a row), the candidate ordered by `nearest`, by
#     `scripted` and unordered (`none`), against a free followers_school_1052 (base1052)
#     and a free f995_701: oc_<base>_<rule>.json
#
# Env: CKPT (required), NAME (default its stem), OUT (required), THREADS (2), QUICK=1
# (the periodic subset and sizes), SMOKE=1 (tiny sizes), DATA_ROOT (the checkout holding
# lab/runs weights; default this one), PY (default .venv/bin/python), NICE (19).
# Rerunning skips every output that exists.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-21-orderable-pilots
DATA_ROOT=${DATA_ROOT:-$ROOT}
export PYTHONPATH=$ROOT
[[ -n ${CKPT:-} ]] || { echo "set CKPT" >&2; exit 2; }
[[ -n ${OUT:-} ]] || { echo "set OUT" >&2; exit 2; }
[[ $CKPT = /* || -f $CKPT ]] || CKPT=$DATA_ROOT/$CKPT
[[ -f $CKPT ]] || { echo "missing $CKPT" >&2; exit 2; }
CKPT=$(realpath "$CKPT")
NAME=${NAME:-$(basename "$CKPT" .pt)}
PY=${PY:-.venv/bin/python}
THREADS=${THREADS:-2}
NICE=${NICE:-19}
QUICK=${QUICK:-0}
if [[ ${SMOKE:-0} == 1 ]]; then
    N_DRILL=4 N_DOCKM=4 N_MISSION=12 N_FLEET=2 OC_BLOCKS=1
elif [[ $QUICK == 1 ]]; then
    N_DRILL=64 N_DOCKM=96
else
    N_DRILL=128 N_DOCKM=256 N_MISSION=192 N_FLEET=16 OC_BLOCKS=24
fi
BASES=(
    "base1052=lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt"
    "f995_701=lab/runs/2026-11-01-fighters-v2/f995/checkpoints/ppo_bc_701.pt"
)
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

# (a) The drill eval, order and dock drills.
step "$OUT/drills.json" "$PY" -m spacefight.eval.drills --a "$CKPT" --name "$NAME" \
    --n-per-kind $N_DRILL --threads "$THREADS" --out "$OUT/drills.json"
# (b) Recalls in matches, scripted commanders, the candidate on every strike slot.
DE="$PY $HERE/../2026-11-20-dock-repair/dock_eval.py --threads $THREADS --n $N_DOCKM --pilots $OUT/pilot.json --checkpoint-root $DATA_ROOT"
step "$OUT/dockm_carrier.json" $DE --mission carrier_battle --out "$OUT/dockm_carrier.json"
step "$OUT/dockm_station.json" $DE --mission station_assault --out "$OUT/dockm_station.json"
if [[ $QUICK != 1 ]]; then
    # (c) Wins against the script.
    step "$OUT/missions.json" "$PY" -m spacefight.eval.missions --a "$CKPT" --b script \
        --n-per-mission $N_MISSION --n-threads "$THREADS" --out "$OUT/missions.json"
    step "$OUT/fleet.json" "$PY" -m spacefight.eval.fleet --a "$CKPT" --b script \
        --n-per-roster $N_FLEET --n-threads "$THREADS" --out "$OUT/fleet.json"
    # (d) The order cost against two free pilots.
    for base in "${BASES[@]}"; do
        bname=${base%%=*}
        bckpt=$DATA_ROOT/${base#*=}
        [[ -f $bckpt ]] || { echo "missing $bckpt" >&2; exit 2; }
        for rule in nearest none scripted; do
            step "$OUT/oc_${bname}_$rule.json" "$PY" \
                lab/runs/2026-11-17-order-cost/order_rules.py --rule "$rule" --k 3 \
                --blocks $OC_BLOCKS --threads "$THREADS" --checkpoint "$CKPT" \
                --name "$NAME" --unseen-checkpoint "$bckpt" --unseen-name "$bname" \
                --out "$OUT/oc_${bname}_$rule.json"
        done
    done
fi
echo "$(date +%H:%M:%S) done: $OUT"
"$PY" $HERE/summary.py eval "$OUT"
