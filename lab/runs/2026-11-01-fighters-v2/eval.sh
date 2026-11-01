#!/usr/bin/env bash
# Evals of plan.md §4, run after PPO has stopped. Skips outputs that exist.
#
#   eval.sh screen       every arm at updates 200, 400 and its last: missions vs R
#   eval.sh gate NAME    gate F evals of NAME = <arm>_<update> (f99 / f995)
#   eval.sh hide NAME    gate H evals of NAME = hide_<update>, with B3's eval.sh into
#                        hide_gates/eval, whose baselines this stage refreshes
#
# Env: THREADS (14), N_SCREEN (258), N_GATE (1032), N_FLEET (64).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-01-fighters-v2
B3=lab/runs/2026-11-01-order-pilot-b3
PY=.venv/bin/python
THREADS=${THREADS:-14}
N_SCREEN=${N_SCREEN:-258}
N_GATE=${N_GATE:-1032}
N_FLEET=${N_FLEET:-64}
MAIN=/home/timg/code/rl-fighter
V1=$MAIN/lab/runs/2026-10-30-fleet-pilot/arm_warm/checkpoints/ppo_bc_400.pt
W1_400=$MAIN/lab/runs/2026-10-31-order-pilot/w1/checkpoints/ppo_bc_400.pt
R=$MAIN/$B3/reward/checkpoints/ppo_bc_300.pt
OUT=${OUT:-$HERE/eval}
mkdir -p "$OUT"

run() {  # run OUT_JSON MODULE ARGS...
    local out=$1 module=$2
    shift 2
    if [[ -f $out ]]; then echo "skip: $out exists"; return; fi
    "$PY" -m "$module" --n-threads "$THREADS" --out "$out" "$@" >"${out%.json}.md"
    echo "$(date +%H:%M:%S) wrote $out"
}

checkpoint() {  # checkpoint ARM UPDATE
    echo "$HERE/$1/checkpoints/ppo_bc_$2.pt"
}

case ${1:-} in
screen)
    for arm in ${ARMS:-f99 f995 hide}; do
        last=$(ls "$HERE/$arm/checkpoints" | sed -E 's/ppo_bc_([0-9]+)\.pt/\1/' | sort -n | tail -n 1)
        for u in ${SCREEN_UPDATES:-200 400} "$last"; do
            ckpt=$(checkpoint "$arm" "$u")
            [[ -f $ckpt ]] || { echo "no $ckpt"; continue; }
            run "$OUT/screen_${arm}_$u.json" spacefight.eval.missions --a "$ckpt" --b "$R" \
                --commanders scripted --n-per-mission "$N_SCREEN" --seed 300000
        done
    done
    ;;
gate)
    name=$2
    arm=${name%_*}
    ckpt=$(checkpoint "$arm" "${name##*_}")
    run "$OUT/${name}_missions_vs_R.json" spacefight.eval.missions --a "$ckpt" --b "$R" \
        --commanders scripted --n-per-mission "$N_GATE" --seed 310000
    run "$OUT/${name}_fleet_vs_R.json" spacefight.eval.fleet --a "$ckpt" --b "$R" \
        --suite fleet_v1 --n-per-roster "$N_FLEET" --seed 210000
    run "$OUT/${name}_fleet_vs_script.json" spacefight.eval.fleet --a "$ckpt" --b script \
        --suite fleet_v1 --n-per-roster "$N_FLEET" --seed 210000
    ;;
hide)
    name=$2
    RUN=$HERE/hide_gates
    mkdir -p "$RUN/eval"
    # B3's bounds and following references stay: gate H is B3's, unchanged.
    for f in o_bounds.json o_bounds.md n_orders.txt teacher_orders.json \
        w1_400_orders.json sizing_w1_400_orders.json; do
        [[ -f $RUN/eval/$f ]] || cp "$B3/eval/$f" "$RUN/eval/$f"
    done
    # Baselines against the current default rosters.
    OUT=$RUN/eval
    run "$OUT/script_vs_script_missions.json" spacefight.eval.missions --a script --b script \
        --commanders scripted --n-per-mission 516 --seed 300000
    run "$OUT/v1_vs_v1_missions.json" spacefight.eval.missions --a "$V1" --b "$V1" \
        --commanders scripted --n-per-mission 516 --seed 300000
    run "$OUT/v1_fleet_vs_script.json" spacefight.eval.fleet --a "$V1" --b script \
        --suite fleet_v1 --n-per-roster "$N_FLEET" --seed 200000
    RUN=$RUN THREADS=$THREADS V1=$V1 W1_400=$W1_400 PY=$PY \
        "$B3/eval.sh" "$name" "$(checkpoint hide "${name##*_}")"
    "$PY" "$B3/gates.py" --run "$RUN" gates
    ;;
*)
    echo "usage: $0 screen | gate NAME | hide NAME" >&2
    exit 2
    ;;
esac
