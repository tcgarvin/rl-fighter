#!/bin/bash
# Third pass: nearest and none, 3v3, again with the retreat measures (same seeds, so the
# scores repeat). Run from the repo root.
cd "$(dirname "$0")/../../.."
D=lab/runs/2026-11-17-order-cost
for r in nearest none; do
  PYTHONPATH=. nice -n 10 .venv/bin/python $D/order_rules.py --rule $r --k 3 --blocks 24 \
    --threads 4 --out $D/out/k3_${r}.json &
done
wait
