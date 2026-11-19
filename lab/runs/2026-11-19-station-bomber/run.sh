#!/usr/bin/env bash
# Station assault and bomber measurements (SIM_VERSION 9), results.md. At most 8
# threads, nice 19 (the laptop is shared). Live pilots: lab/live_pilots.json, weights
# from the main checkout's lab/runs (CHECKPOINT_ROOT).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
OUT=out
mkdir -p "$OUT"
PILOTS="$HERE/../../live_pilots.json"
ROOT="${CHECKPOINT_ROOT:-/home/timg/code/rl-fighter}"
run() { echo "== $*"; nice -n 19 uv run python "$@" > /dev/null; }

# 1. Station balance, script against script, both obs mappings (the script reads no obs).
run station_eval.py --n 512 --out "$OUT/balance_script_carrier.json"
run station_eval.py --n 512 --station-as convoy --out "$OUT/balance_script_convoy.json"

# 2. Live pilots zero-shot on both sides, scripted commanders, each mapping; then the
# scripted commander against `unseen` (one side's orders hidden from its pilots).
for as in carrier convoy; do
    run station_eval.py --n 512 --station-as "$as" --pilots "$PILOTS" \
        --checkpoint-root "$ROOT" --out "$OUT/pilots_$as.json"
done
run station_eval.py --n 512 --pilots "$PILOTS" --checkpoint-root "$ROOT" \
    --commanders scripted unseen --out "$OUT/pilots_carrier_attacker_unseen.json"
run station_eval.py --n 512 --pilots "$PILOTS" --checkpoint-root "$ROOT" \
    --commanders unseen scripted --out "$OUT/pilots_carrier_defender_unseen.json"

# 3. Bomber paired swap: script first (replacement level), then live pilots.
run swap_eval.py --mission deathmatch --n-per-roster 16 --out "$OUT/swap_dm_script.json"
run swap_eval.py --mission carrier_battle --n-per-roster 86 --out "$OUT/swap_carrier_script.json"
run swap_eval.py --mission deathmatch --n-per-roster 16 --pilots "$PILOTS" \
    --checkpoint-root "$ROOT" --out "$OUT/swap_dm_pilots.json"
run swap_eval.py --mission carrier_battle --n-per-roster 86 --pilots "$PILOTS" \
    --checkpoint-root "$ROOT" --out "$OUT/swap_carrier_pilots.json"
echo "== done"
