#!/usr/bin/env bash
# The fight-ablation measures (plan.md "Measures") on one checkpoint. Writes into OUT;
# `summary.py eval OUT` prints them, `summary.py report` sets them beside the parent's.
#
#   CKPT=lab/runs/2026-11-26-fight-ablation/solo/checkpoints/ppo_bc_1000.pt \
#       NAME=solo_1000 OUT=lab/runs/2026-11-26-fight-ablation/eval/solo_1000 \
#       lab/runs/2026-11-26-fight-ablation/eval.sh
#   QUICK=1 CKPT=... OUT=... .../eval.sh     (the periodic subset: (a), (b), (c), the fleet
#                                            suite and the unordered order-cost pass)
#   SMOKE=1 CKPT=... OUT=/tmp/x .../eval.sh  (tiny sizes; with QUICK=1 the subset)
#
# (a) the drill eval, all five kinds (go-to, attack, defend, dock_calm, dock_threat),
#     each flown again with the order hidden: drills.json
# (b) recalls in real matches: the candidate flies every strike craft of both sides of a
#     carrier battle and a station assault, scripted commanders, which recall below half
#     hull (../2026-11-20-dock-repair/dock_eval.py): dockm_carrier.json, dockm_station.json
# (c) the bomber swap (../2026-11-19-station-bomber/swap_eval.py): the same matches
#     twice, side X's first gunship as it is and swapped for a bomber, the candidate on
#     every strike slot; the paired delta and the swapped slot's damage to capital ships
#     and strike craft: swap_dm.json (3 v 3 deathmatch), swap_carrier.json
# (d) wins against the script: the fleet_v1 suite (fleet.json; QUICK too, smaller) and,
#     full evals only, the mission eval (carrier battle, convoy, station assault;
#     missions.json)
# (e) the order cost (../2026-11-17-order-cost/order_rules.py): 3 v 3, the candidate
#     ordered by `nearest` and unordered (`none`) against a free followers_school_1052:
#     oc_base1052_<rule>.json (QUICK: `none` only, fewer blocks)
#
# Env: CKPT (required), NAME (default its stem), OUT (required), THREADS (2), QUICK=1
# (the periodic subset and sizes), SMOKE=1 (tiny sizes), DATA_ROOT (the checkout holding
# lab/runs weights; default this one), PY (default .venv/bin/python), NICE (19).
# Rerunning skips every output that exists.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-26-fight-ablation
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
    N_DRILL=4 N_DOCKM=4 N_SWAP=1 N_MISSION=12 N_FLEET=2 OC_BLOCKS=1
elif [[ $QUICK == 1 ]]; then
    N_DRILL=64 N_DOCKM=96 N_SWAP=8 N_FLEET=8 OC_BLOCKS=6
else
    N_DRILL=128 N_DOCKM=256 N_SWAP=32 N_MISSION=192 N_FLEET=16 OC_BLOCKS=24
fi
BASES=(
    "base1052=lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt"
)
mkdir -p "$OUT"
OUT=$(realpath "$OUT")
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
# (c) The bomber swap, the candidate on every strike slot.
SW="$PY $HERE/../2026-11-19-station-bomber/swap_eval.py --threads $THREADS --n-per-roster $N_SWAP --pilots $OUT/pilot.json --checkpoint-root $DATA_ROOT"
step "$OUT/swap_dm.json" $SW --mission deathmatch --out "$OUT/swap_dm.json"
step "$OUT/swap_carrier.json" $SW --mission carrier_battle --out "$OUT/swap_carrier.json"
# (d) Wins against the script.
if [[ $QUICK != 1 ]]; then
    step "$OUT/missions.json" "$PY" -m spacefight.eval.missions --a "$CKPT" --b script \
        --n-per-mission $N_MISSION --n-threads "$THREADS" --out "$OUT/missions.json"
fi
step "$OUT/fleet.json" "$PY" -m spacefight.eval.fleet --a "$CKPT" --b script \
    --n-per-roster $N_FLEET --n-threads "$THREADS" --out "$OUT/fleet.json"
# (e) The order cost against a free pilot (QUICK: the unordered pass only).
RULES=(nearest none)
[[ $QUICK == 1 ]] && RULES=(none)
for base in "${BASES[@]}"; do
    bname=${base%%=*}
    bckpt=$DATA_ROOT/${base#*=}
    [[ -f $bckpt ]] || { echo "missing $bckpt" >&2; exit 2; }
    for rule in "${RULES[@]}"; do
        step "$OUT/oc_${bname}_$rule.json" "$PY" \
            lab/runs/2026-11-17-order-cost/order_rules.py --rule "$rule" --k 3 \
            --blocks $OC_BLOCKS --threads "$THREADS" --checkpoint "$CKPT" \
            --name "$NAME" --unseen-checkpoint "$bckpt" --unseen-name "$bname" \
            --out "$OUT/oc_${bname}_$rule.json"
    done
done
echo "$(date +%H:%M:%S) done: $OUT"
"$PY" $HERE/summary.py eval "$OUT"
