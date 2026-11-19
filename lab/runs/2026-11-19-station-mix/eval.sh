#!/usr/bin/env bash
# The station-mix measures (plan.md "Measures") on one checkpoint, against the parent
# followers_school_1052. Writes into OUT; summary.py prints the table and the bars.
#
#   CKPT=lab/runs/2026-11-19-station-mix/mix_s1/checkpoints/ppo_bc_725.pt NAME=s1_725 \
#       OUT=lab/runs/2026-11-19-station-mix/eval/s1_725 \
#       lab/runs/2026-11-19-station-mix/eval.sh
#   NAME=parent_1052 OUT=lab/runs/2026-11-19-station-mix/eval_before \
#       lab/runs/2026-11-19-station-mix/eval.sh            # CKPT defaults to the parent
#   SMOKE=1 OUT=/tmp/station-mix-eval lab/runs/2026-11-19-station-mix/eval.sh
#
# Env: CKPT (default the parent), NAME, OUT (required), THREADS (2), N_STATION (256 a
# reading and a pairing, so 512 a pairing), DATA_ROOT (the checkout holding lab/runs
# weights; default this checkout), SMOKE=1 (tiny sizes), PY (default .venv/bin/python).
# Rerunning skips every output that exists.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-19-station-mix
DATA_ROOT=${DATA_ROOT:-$ROOT}
PARENT=$DATA_ROOT/lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt
CKPT=${CKPT:-$PARENT}
[[ $CKPT = /* ]] || CKPT=$DATA_ROOT/$CKPT
NAME=${NAME:-$(basename "$CKPT" .pt)}
PY=${PY:-.venv/bin/python}
THREADS=${THREADS:-2}
SMOKE=${SMOKE:-0}
[[ -n ${OUT:-} ]] || { echo "set OUT" >&2; exit 2; }
[[ -f $CKPT ]] || { echo "missing $CKPT" >&2; exit 2; }
[[ -f $PARENT ]] || { echo "missing $PARENT" >&2; exit 2; }
if [[ $SMOKE == 1 ]]; then
    N_STATION=8 SWAP_DM=1 SWAP_CARRIER=2 N_MISSION=12 N_FLEET=2 N_DRILL=4
else
    N_STATION=${N_STATION:-256} SWAP_DM=16 SWAP_CARRIER=86 N_MISSION=192 N_FLEET=16 N_DRILL=64
fi
mkdir -p "$OUT"
export OMP_NUM_THREADS=$THREADS MKL_NUM_THREADS=$THREADS

# One-pilot rlf.live_pilots/1 lists (absolute checkpoints, so the root is ignored).
pilot_list() {  # $1 id, $2 checkpoint, $3 out
    "$PY" - "$1" "$2" "$3" <<'EOF'
import json, sys
pid, ckpt, out = sys.argv[1:]
json.dump({"schema": "rlf.live_pilots/1", "pilots": [{"id": pid, "checkpoint": ckpt}]},
          open(out, "w"), indent=1)
EOF
}
pilot_list "$NAME" "$CKPT" "$OUT/pilot_cand.json"
pilot_list parent_1052 "$PARENT" "$OUT/pilot_parent.json"
same=0
[[ $(realpath "$CKPT") == $(realpath "$PARENT") ]] && same=1

step() {  # $1 output file, then the command
    local out=$1; shift
    if [[ -s $out ]]; then echo "skip $out"; return; fi
    echo "$(date +%H:%M:%S) $out"
    local t0=$SECONDS
    "$@" > "$out.log" 2>&1 || { echo "FAILED: $out (see $out.log)" >&2; return 1; }
    echo "  $(( SECONDS - t0 )) s"
}
SE="$PY $HERE/../2026-11-19-station-bomber/station_eval.py --threads $THREADS --n $N_STATION --checkpoint-root $DATA_ROOT"

# (a) Station assault, scripted commanders, both readings: the candidate attacking 1052,
# defending against it, and flying both sides. Bomber damage to capital ships is in
# damage_dealt_per_ship.attacker.bomber_vs_capital.
for as in carrier convoy; do
    step "$OUT/station_self_$as.json" $SE --station-as "$as" \
        --pilots "$OUT/pilot_cand.json" --out "$OUT/station_self_$as.json"
    (( same )) && continue
    step "$OUT/station_attack_$as.json" $SE --station-as "$as" \
        --pilots "$OUT/pilot_cand.json" --pilots-team 1 \
        --pilots-other "$OUT/pilot_parent.json" --out "$OUT/station_attack_$as.json"
    step "$OUT/station_defend_$as.json" $SE --station-as "$as" \
        --pilots "$OUT/pilot_cand.json" --pilots-team 0 \
        --pilots-other "$OUT/pilot_parent.json" --out "$OUT/station_defend_$as.json"
done

# (b) The bomber in place of a gunship, the candidate flying every strike craft.
SW="$PY $HERE/../2026-11-19-station-bomber/swap_eval.py --threads $THREADS --checkpoint-root $DATA_ROOT --pilots $OUT/pilot_cand.json"
step "$OUT/swap_dm.json" $SW --mission deathmatch --n-per-roster $SWAP_DM --out "$OUT/swap_dm.json"
step "$OUT/swap_carrier.json" $SW --mission carrier_battle --n-per-roster $SWAP_CARRIER \
    --out "$OUT/swap_carrier.json"
# Drills with the pilots in bombers, beside the same drills as drawn.
step "$OUT/bomber_drills.json" "$PY" $HERE/bomber_drills.py --a "$CKPT" \
    --n-per-kind $N_DRILL --threads $THREADS --out "$OUT/bomber_drills.json"

# (c) Old missions against 1052, the 3 v 3 fleet eval, and the drill gate.
if (( ! same )); then
    step "$OUT/missions.json" "$PY" -m spacefight.eval.missions --a "$CKPT" --b "$PARENT" \
        --n-per-mission $N_MISSION --n-threads $THREADS --out "$OUT/missions.json"
    step "$OUT/fleet.json" "$PY" -m spacefight.eval.fleet --a "$CKPT" --b "$PARENT" \
        --n-per-roster $N_FLEET --n-threads $THREADS --out "$OUT/fleet.json"
fi
step "$OUT/drills.json" "$PY" -m spacefight.eval.drills --a "$CKPT" --name "$NAME" \
    --n-per-kind $N_DRILL --threads $THREADS --out "$OUT/drills.json"
echo "$(date +%H:%M:%S) done: $OUT"
"$PY" $HERE/summary.py "$OUT"
