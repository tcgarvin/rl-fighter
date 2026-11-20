#!/usr/bin/env bash
# Dock drill baselines (plan.md "Baselines"): the script and the ten live pilots
# (lab/live_pilots.json, read at their own widths: 587 floats or fewer, so a dock order
# is a go-to to the bay mouth to them) on the dock eval, calm and threat, N drills a kind
# (each pilot also flies them with the order hidden). Writes baseline/<id>.json and .md;
# rerunning skips what exists. nice 19 (the laptop is shared).
#
#   lab/runs/2026-11-20-dock-pilot/baseline.sh
#   N=16 lab/runs/2026-11-20-dock-pilot/baseline.sh    (a quick look)
#
# Env: N (128), THREADS (2), DATA_ROOT (the checkout holding lab/runs weights; default
# this one), PY (default .venv/bin/python).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-20-dock-pilot
OUT=$HERE/baseline
DATA_ROOT=${DATA_ROOT:-$ROOT}
PY=${PY:-.venv/bin/python}
N=${N:-128}
THREADS=${THREADS:-2}
mkdir -p "$OUT"
export OMP_NUM_THREADS=$THREADS MKL_NUM_THREADS=$THREADS

eval_one() {  # $1 id, $2 checkpoint or "script"
    local out=$OUT/$1.json
    if [[ -s $out ]]; then echo "skip $out"; return; fi
    echo "$(date +%H:%M:%S) $1"
    nice -n 19 "$PY" -m spacefight.eval.drills --a "$2" --name "$1" \
        --kinds dock_calm,dock_threat --n-per-kind "$N" --threads "$THREADS" \
        --out "$out" > "$out.log" 2>&1 || { echo "FAILED: $1 (see $out.log)" >&2; return 1; }
}

eval_one script script
while IFS=$'\t' read -r id ckpt; do
    eval_one "$id" "$DATA_ROOT/$ckpt"
done < <("$PY" -c '
import json
for p in json.load(open("lab/live_pilots.json"))["pilots"]:
    print(p["id"], p["checkpoint"], sep="\t")
')
"$PY" "$HERE/summary.py" baseline "$OUT"
