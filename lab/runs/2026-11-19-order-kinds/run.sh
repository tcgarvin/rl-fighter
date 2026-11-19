#!/bin/bash
# What go-to and defend orders cost a 3 v 3 deathmatch, against the attack order's cost
# (lab/runs/2026-11-17-order-cost). One pilot flies both sides; the ordered side gets
# each rule of order_rules.py, the other side is the unseen script (orders hidden).
# Same seeds as 2026-11-17 / 2026-11-18 (order_rules.py's default 20261117), so every
# row pairs match by match with `none`. Two chains of THREADS threads each (6 in all by
# default). Run from anywhere:
#   run.sh                      # followers_school_1052, 1,152 matches a rule (--blocks 24)
#   PILOT=f995_701 BLOCKS=12 run.sh
# CKPT_ROOT names the checkout that holds the checkpoints (they are not in git), PY the
# python (default .venv/bin/python).
set -euo pipefail
cd "$(dirname "$0")/../../.."
HERE=lab/runs/2026-11-19-order-kinds
RULES=lab/runs/2026-11-17-order-cost/order_rules.py
CKPT_ROOT=${CKPT_ROOT:-.}
PILOT=${PILOT:-followers_school_1052}
BLOCKS=${BLOCKS:-24}
THREADS=${THREADS:-3}
case $PILOT in
  followers_school_1052)
    CKPT=$CKPT_ROOT/lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt ;;
  f995_701)
    CKPT=$CKPT_ROOT/lab/runs/2026-11-01-fighters-v2/f995/checkpoints/ppo_bc_701.pt ;;
  *) echo "unknown PILOT $PILOT" >&2; exit 2 ;;
esac
mkdir -p "$HERE/out"
run() {
  local r=$1 tag=${PILOT}_k3_$1
  nice -n 19 env PYTHONPATH=. "${PY:-.venv/bin/python}" "$RULES" --rule "$r" --k 3 \
    --blocks "$BLOCKS" --threads "$THREADS" --checkpoint "$CKPT" --name "$PILOT" \
    --out "$HERE/out/$tag.json" > "$HERE/out/$tag.out" 2>&1
}
( for r in none goto_front goto_rally defend_ring; do run $r; done ) &
( for r in nearest goto_front_deadline defend_ward; do run $r; done ) &
wait
grep -h "ordered side" "$HERE"/out/${PILOT}_k3_*.out
