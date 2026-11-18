#!/bin/bash
# The order-rule batch: even 2v2 and 3v3, four rules, 1,152 matches each (two chains of
# four threads). Run from the repo root.
cd "$(dirname "$0")/../../.."
D=lab/runs/2026-11-17-order-cost
PILOTS=${PILOTS:-lab/runs/2026-11-15-commander-3/pilots_followers.json}
TAG=${TAG:-}
for k in 2 3; do
  (
    for r in scripted nearest focus none; do
      PYTHONPATH=. nice -n 10 .venv/bin/python $D/order_rules.py --rule $r --k $k \
        --blocks ${BLOCKS:-24} --threads 4 --pilots $PILOTS --out $D/out/k${k}_${r}${TAG}.json
    done
  ) &
done
wait
