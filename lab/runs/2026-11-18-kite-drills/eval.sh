#!/bin/bash
# The measures of plan.md for checkpoints of this run: the order-cost measure with
# different pilots on the two sides (order_rules.py --unseen-checkpoint, 3 v 3, 24 blocks
# = 1,152 matches a row), the checkpoint ordered (nearest, scripted) and unordered (none)
# against two free pilots: followers_school_1052 (its parent) and f995_701 (a fighter,
# not of its family); and the drill eval (64 a kind) with its gate.
#   eval.sh <out-dir> <name>=<ckpt> [<name>=<ckpt> ...]
# Env: THREADS (2 a job), CKPT_ROOT (checkout holding the checkpoints, default this one),
# PY (default .venv/bin/python), SKIP_DRILLS=1.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=$1; shift
CKPT_ROOT=${CKPT_ROOT:-.}
PY=${PY:-.venv/bin/python}
BASES=(
  "base1052=$CKPT_ROOT/lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt"
  "f995_701=$CKPT_ROOT/lab/runs/2026-11-01-fighters-v2/f995/checkpoints/ppo_bc_701.pt"
)
THREADS=${THREADS:-2}
mkdir -p "$OUT"
run() {  # rule ordered-name ordered-ckpt unseen-name unseen-ckpt
  nice -n 19 env PYTHONPATH=. "$PY" lab/runs/2026-11-17-order-cost/order_rules.py \
    --rule "$1" --k 3 --blocks 24 --threads "$THREADS" \
    --checkpoint "$3" --name "$2" --unseen-checkpoint "$5" --unseen-name "$4" \
    --out "$OUT/${2}_v_${4}_$1.json" > "$OUT/${2}_v_${4}_$1.out" 2>&1
}
for spec in "$@"; do
  name=${spec%%=*}; ckpt=${spec#*=}
  for base in "${BASES[@]}"; do
    for rule in nearest none scripted; do
      run "$rule" "$name" "$ckpt" "${base%%=*}" "${base#*=}" &
    done
  done
  if [[ ${SKIP_DRILLS:-0} != 1 ]]; then
    nice -n 19 env PYTHONPATH=. "$PY" -m spacefight.eval.drills --a "$ckpt" --name "$name" \
      --n-per-kind 64 --threads "$THREADS" --out "$OUT/${name}_drills.json" \
      > "$OUT/${name}_drills.out" 2>&1 &
  fi
done
wait
grep -h "ordered side" "$OUT"/*.out || true
