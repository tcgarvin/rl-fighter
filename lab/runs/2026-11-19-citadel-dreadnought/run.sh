#!/usr/bin/env bash
# Citadel and dreadnought measurements (SIM_VERSION 10), results.md. At most 8 threads,
# nice 19 (the laptop is shared). Live pilots: lab/live_pilots.json, weights from the
# main checkout's lab/runs (CHECKPOINT_ROOT). Needs rlf_sim built from this tree
# (uv run maturin develop -m crates/sim-py/Cargo.toml --release).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
cd "$HERE"
OUT=out
mkdir -p "$OUT" "$OUT/v9_rerun"
PILOTS="$REPO/lab/live_pilots.json"
ROOT="${CHECKPOINT_ROOT:-/home/timg/code/rl-fighter}"
THREADS="${THREADS:-8}"
run() { echo "== $*"; nice -n 19 uv run python "$@" > /dev/null; }

# 1. Balance, script against script, the citadel roster, both obs mappings (the script
# reads no obs, so they should agree up to the commander's reading).
run citadel_eval.py --n 512 --threads "$THREADS" --out "$OUT/balance_script_carrier.json"
run citadel_eval.py --n 512 --threads "$THREADS" --station-as convoy \
    --out "$OUT/balance_script_convoy.json"

# 2. Old missions unchanged: the v9 entry's script-vs-script evals re-run under v10 must
# match its committed files exactly (station roster of v9, carrier battle, deathmatch).
V9="$REPO/lab/runs/2026-11-19-station-bomber"
run "$V9/station_eval.py" --n 512 --out "$OUT/v9_rerun/balance_script_carrier.json"
run "$V9/station_eval.py" --n 512 --station-as convoy \
    --out "$OUT/v9_rerun/balance_script_convoy.json"
run "$V9/swap_eval.py" --mission deathmatch --n-per-roster 16 \
    --out "$OUT/v9_rerun/swap_dm_script.json"
run "$V9/swap_eval.py" --mission carrier_battle --n-per-roster 86 \
    --out "$OUT/v9_rerun/swap_carrier_script.json"
uv run python compare_v9.py --old "$V9/out" --new "$OUT/v9_rerun" | tee "$OUT/v9_compare.txt"

# 3. Dreadnought against a carrier, gun to gun (the Rust harness, no live mission):
# alone, with 4 strike craft, with 8; 40 starts each.
(cd "$REPO" && RLF_DIAG_N=40 nice -n 19 cargo test -q --release -p sim --test citadel \
    diag_dreadnought_vs_carrier -- --ignored --nocapture) \
    | grep '^dreadnought vs' | tee "$OUT/dreadnought_vs_carrier.txt"

# 4. Live pilots zero-shot on both sides of the citadel roster, scripted commanders,
# each mapping: do they engage the dreadnought (obs class spare)?
for as in carrier convoy; do
    run citadel_eval.py --n 512 --threads "$THREADS" --station-as "$as" \
        --pilots "$PILOTS" --checkpoint-root "$ROOT" --out "$OUT/pilots_$as.json"
done

# 5. Does the lance hold off the capitals? The Rust harness's v10 assault (128 starts,
# seeds 1000+), with the shipped assets and with a copy whose lance does 1 damage.
diag() {
    (cd "$REPO" && RLF_DIAG_N=128 nice -n 19 cargo test -q --release -p sim --test citadel \
        diag_v10_assault -- --ignored --nocapture) | grep -E '^(attacker|citadel|on citadel)'
}
diag | tee "$OUT/diag_shipped.txt"
ABL="$(mktemp -d)"
cp -r "$REPO/assets/." "$ABL/"
sed -i 's/^\(lance: .*\)damage: 130,/\1damage: 1,/' "$ABL/weapons.yaml"
grep -q 'damage: 1, interval: 2.2' "$ABL/weapons.yaml"
RLF_ASSETS="$ABL" diag | tee "$OUT/diag_lance_1.txt"
rm -rf "$ABL"
echo "== done"
