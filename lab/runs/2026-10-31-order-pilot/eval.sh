#!/usr/bin/env bash
# Gate evals of plan.md §5 (sampled actions, SIM_VERSION 5). Skips outputs that exist.
#
#   lab/runs/2026-10-31-order-pilot/eval.sh baseline
#   lab/runs/2026-10-31-order-pilot/eval.sh <name> <checkpoint.pt>
#   lab/runs/2026-10-31-order-pilot/eval.sh <name> <checkpoint.pt> blank
#
# baseline: script vs script and v1 vs v1 in carrier battle + convoy (scripted
# commanders), v1's order following (random + scripted commander, carrier + convoy,
# on obs[:385]), v1 vs the script on the fleet_v1 deathmatch suite.
# <name>: the candidate's following, missions vs v1, deathmatch vs the script and
# vs v1 (the gate evals). With "blank": only its following with the order block
# zeroed (the secondary baseline, run for candidates that pass).
#
# Environment (run.sh sets them): RUN, THREADS (12), V1 (fleet pilot v1's
# checkpoint), N_ORDERS (96 per mission and commander), N_MISSIONS (516 per
# mission), N_FLEET (64 per roster), PY.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
RUN=${RUN:-lab/runs/2026-10-31-order-pilot}
THREADS=${THREADS:-12}
N_ORDERS=${N_ORDERS:-96}
N_MISSIONS=${N_MISSIONS:-516}
N_FLEET=${N_FLEET:-64}
if [[ -z "${PY:-}" ]]; then
    if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY="uv run python"; fi
fi
# shellcheck disable=SC2206
PY=($PY)
[[ -n "${V1:-}" && -f "$V1" ]] || { echo "set V1 to fleet pilot v1's checkpoint" >&2; exit 2; }
OUT=$RUN/eval
mkdir -p "$OUT"

run() {  # run OUT_JSON MODULE ARGS...: one eval, Markdown next to the JSON
    local out=$1 module=$2
    shift 2
    if [[ -f $out ]]; then
        echo "skip: $out exists"
        return
    fi
    "${PY[@]}" -m "$module" --n-threads "$THREADS" --out "$out" "$@" >"${out%.json}.md"
    echo "wrote $out"
}

orders() {  # orders OUT_JSON PILOT
    run "$1" spacefight.eval.orders --a "$2" --b script \
        --n-per-scenario "$N_ORDERS" --seed 400000
}

missions() {  # missions OUT_JSON A B
    run "$1" spacefight.eval.missions --a "$2" --b "$3" --commanders scripted \
        --n-per-mission "$N_MISSIONS" --seed 300000
}

fleet() {  # fleet OUT_JSON A B
    run "$1" spacefight.eval.fleet --a "$2" --b "$3" --suite fleet_v1 \
        --n-per-roster "$N_FLEET" --seed 200000
}

if [[ ${1:-} == baseline ]]; then
    missions "$OUT/script_vs_script_missions.json" script script
    missions "$OUT/v1_vs_v1_missions.json" "$V1" "$V1"
    orders "$OUT/v1_orders.json" "$V1"
    fleet "$OUT/v1_fleet_vs_script.json" "$V1" script
    exit 0
fi

if [[ $# -lt 2 ]]; then
    echo "usage: $0 baseline | <name> <checkpoint.pt> [blank]" >&2
    exit 2
fi
name=$1
ckpt=$2
[[ -f $ckpt ]] || { echo "checkpoint not found: $ckpt" >&2; exit 2; }
if [[ ${3:-} == blank ]]; then
    orders "$OUT/${name}_orders_blank.json" "blank:$ckpt"
    exit 0
fi
orders "$OUT/${name}_orders.json" "$ckpt"
missions "$OUT/${name}_missions_vs_v1.json" "$ckpt" "$V1"
fleet "$OUT/${name}_fleet_vs_script.json" "$ckpt" script
fleet "$OUT/${name}_fleet_vs_v1.json" "$ckpt" "$V1"
echo "done: $name"
