#!/bin/bash
# Baseline before training (plan.md): the order-cost measure (nearest, none, scripted;
# 3 v 3, the 2026-11-17 seeds) and the drill eval, on followers_school_1052 alone.
# Run from anywhere; the same script measures an arm's checkpoint with CKPT, NAME, OUT.
set -euo pipefail
cd "$(dirname "$0")/../../.."
HERE=lab/runs/2026-11-18-mixed-orders
CKPT=${CKPT:-lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt}
NAME=${NAME:-followers_school_1052}
OUT=${OUT:-$HERE/eval_before}
mkdir -p "$OUT"
for r in nearest none scripted; do
  PYTHONPATH=. .venv/bin/python lab/runs/2026-11-17-order-cost/order_rules.py --rule $r --k 3 \
    --blocks 24 --threads 4 --checkpoint "$CKPT" --name "$NAME" --out "$OUT/k3_$r.json" &
done
wait
.venv/bin/python -m spacefight.eval.drills --a "$CKPT" --name "$NAME" --n-per-kind 64 \
  --threads 12 --out "$OUT/drills.json"
