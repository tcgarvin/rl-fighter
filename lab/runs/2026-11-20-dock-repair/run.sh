#!/usr/bin/env bash
# Dock and repair measurements (SIM_VERSION 11), results.md. At most 8 threads, nice 19
# (the laptop is shared). Live pilots: lab/live_pilots.json, weights from the main
# checkout's lab/runs (CHECKPOINT_ROOT). Needs rlf_sim built from this tree
# (uv run maturin develop -m crates/sim-py/Cargo.toml --release).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
cd "$HERE"
OUT=out
mkdir -p "$OUT"
PILOTS="$REPO/lab/live_pilots.json"
ROOT="${CHECKPOINT_ROOT:-/home/timg/code/rl-fighter}"
THREADS="${THREADS:-8}"
N="${N:-512}"
run() { echo "== $*"; nice -n 19 uv run python "$@" > /dev/null; }

# 1. Script against script, every mission, the dock rules off (v10) and on (v11).
for mission in deathmatch carrier_battle convoy_escort station_assault citadel; do
    for docking in off on; do
        run dock_eval.py --mission "$mission" --docking "$docking" --n "$N" \
            --threads "$THREADS" --out "$OUT/script_${mission}_${docking}.json"
    done
done

# 2. The live pilots zero-shot under the scripted commanders, which recall them:
# do they fly to the bay and dock? (Both sides, every strike slot, the missions with a
# carrier.)
for mission in carrier_battle station_assault citadel; do
    run dock_eval.py --mission "$mission" --docking on --n "$N" --threads "$THREADS" \
        --pilots "$PILOTS" --checkpoint-root "$ROOT" --out "$OUT/pilots_${mission}_on.json"
    run dock_eval.py --mission "$mission" --docking off --n "$N" --threads "$THREADS" \
        --pilots "$PILOTS" --checkpoint-root "$ROOT" --out "$OUT/pilots_${mission}_off.json"
done

# 3. The Rust harness: the script's dock statistics by roster (seeds 1000 on).
(cd "$REPO" && RLF_DIAG_N=128 nice -n 19 cargo test -q --release -p sim --test dock \
    diag_dock_stats -- --ignored --nocapture) | grep -E '^(carrier|station|  )' \
    | tee "$OUT/diag_dock_stats.txt"

uv run python summary.py "$OUT" | tee "$OUT/summary.txt"
echo "== done"
