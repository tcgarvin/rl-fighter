#!/bin/bash
# Follow-up: the near250 rule (2v2, 3v3), and scripted / nearest / none 3v3 over the
# ignorers. Run from the repo root.
cd "$(dirname "$0")/../../.."
D=lab/runs/2026-11-17-order-cost
IGN=lab/runs/2026-11-15-commander-3/pilots_ignorers.json
run() { PYTHONPATH=. nice -n 10 .venv/bin/python $D/order_rules.py --blocks 24 --threads 4 "$@"; }
( run --rule near250 --k 2 --out $D/out/k2_near250.json
  run --rule near250 --k 3 --out $D/out/k3_near250.json ) &
( run --rule scripted --k 3 --pilots $IGN --out $D/out/k3_scripted_ign.json
  run --rule nearest --k 3 --pilots $IGN --out $D/out/k3_nearest_ign.json
  run --rule none --k 3 --pilots $IGN --out $D/out/k3_none_ign.json ) &
wait
