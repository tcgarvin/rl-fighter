#!/bin/bash
# The order-cost measure with different pilots on the two sides (order_rules.py
# --unseen-checkpoint): each arm's checkpoint ordered (nearest) and unordered (none)
# against followers_school_1052 flying free, and 1052 ordered against each arm free.
# Separates "the ordered pilot got better" from "the free pilot got better at
# punishing ordered ones", which the same-pilot measure mixes.
#   eval_cross.sh <out-dir> <name>=<ckpt> [<name>=<ckpt> ...]
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUT=$1; shift
BASE=lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt
THREADS=${THREADS:-2}
mkdir -p "$OUT"
run() {  # rule ordered-name ordered-ckpt unseen-name unseen-ckpt
  nice -n 19 env PYTHONPATH=. .venv/bin/python lab/runs/2026-11-17-order-cost/order_rules.py \
    --rule "$1" --k 3 --blocks 24 --threads "$THREADS" \
    --checkpoint "$3" --name "$2" --unseen-checkpoint "$5" --unseen-name "$4" \
    --out "$OUT/${2}_v_${4}_$1.json" > "$OUT/${2}_v_${4}_$1.out" 2>&1
}
for spec in "$@"; do
  name=${spec%%=*}; ckpt=${spec#*=}
  run nearest "$name" "$ckpt" base1052 "$BASE" &
  run none "$name" "$ckpt" base1052 "$BASE" &
  [[ ${SKIP_REVERSE:-0} == 1 ]] || run nearest base1052 "$BASE" "$name" "$ckpt" &
done
wait
grep -h "ordered side" "$OUT"/*.out
