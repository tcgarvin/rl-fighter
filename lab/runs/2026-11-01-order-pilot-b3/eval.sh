#!/usr/bin/env bash
# Gate evals of plan.md §5 (sampled actions, SIM_VERSION 6). Skips outputs that exist.
#
#   lab/runs/2026-11-01-order-pilot-b3/eval.sh baseline
#   lab/runs/2026-11-01-order-pilot-b3/eval.sh <name> <checkpoint.pt>
#
# baseline, in this order, before any candidate is evaluated:
#   1. sizing: run 1's w1_400 following, random commander, followed pass, N_SIZE per
#      mission; gates.py size turns its defended ward-minutes into the following
#      eval's n per random-commander scenario (eval/n_orders.txt, plan.md §5);
#   2. the teacher (the order-following scripts) and w1_400 on the following eval;
#   3. gates.py bounds: the teacher-first O bounds (eval/o_bounds.json and .md);
#   4. script vs script and v1 vs v1 missions, v1 vs the script in deathmatch.
# <name>: the candidate's following (random commander followed + hidden, scripted
# commander followed), missions vs v1 and vs w1_400, deathmatch vs the script and
# vs v1.
#
# Environment (run.sh sets them): RUN, THREADS (12), V1, W1_400, N_SIZE (48),
# N_ORDERS_MIN / N_ORDERS_MAX (96 / 480), N_ORDERS_SCRIPTED (96), N_MISSIONS (516),
# N_MISSIONS_W1 (258), N_FLEET (64), PY.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-01-order-pilot-b3
RUN=${RUN:-$HERE}
THREADS=${THREADS:-12}
N_SIZE=${N_SIZE:-48}
N_ORDERS_MIN=${N_ORDERS_MIN:-96}
N_ORDERS_MAX=${N_ORDERS_MAX:-480}
N_ORDERS_SCRIPTED=${N_ORDERS_SCRIPTED:-96}
N_MISSIONS=${N_MISSIONS:-516}
N_MISSIONS_W1=${N_MISSIONS_W1:-258}
N_FLEET=${N_FLEET:-64}
if [[ -z "${PY:-}" ]]; then
    if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY="uv run python"; fi
fi
# shellcheck disable=SC2206
PY=($PY)
[[ -n "${V1:-}" && -f "$V1" ]] || { echo "set V1 to fleet pilot v1's checkpoint" >&2; exit 2; }
[[ -n "${W1_400:-}" && -f "$W1_400" ]] || { echo "set W1_400 to run 1's w1_400" >&2; exit 2; }
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

n_orders() {  # the following eval's n per random-commander scenario (sized first)
    [[ -f $OUT/n_orders.txt ]] || { echo "no $OUT/n_orders.txt: run baseline" >&2; exit 2; }
    cat "$OUT/n_orders.txt"
}

orders() {  # orders OUT_JSON PILOT [ARGS...]
    local out=$1 pilot=$2
    shift 2
    run "$out" spacefight.eval.orders --a "$pilot" --b script \
        --n-per-scenario "$(n_orders)" --n-scripted "$N_ORDERS_SCRIPTED" \
        --seed 400000 "$@"
}

missions() {  # missions OUT_JSON A B N
    run "$1" spacefight.eval.missions --a "$2" --b "$3" --commanders scripted \
        --n-per-mission "$4" --seed 300000
}

fleet() {  # fleet OUT_JSON A B
    run "$1" spacefight.eval.fleet --a "$2" --b "$3" --suite fleet_v1 \
        --n-per-roster "$N_FLEET" --seed 200000
}

if [[ ${1:-} == baseline ]]; then
    run "$OUT/sizing_w1_400_orders.json" spacefight.eval.orders --a "$W1_400" \
        --b script --commanders random --passes followed \
        --n-per-scenario "$N_SIZE" --seed 410000
    if [[ ! -f $OUT/n_orders.txt ]]; then
        "${PY[@]}" "$HERE/gates.py" --run "$RUN" size \
            --low "$N_ORDERS_MIN" --high "$N_ORDERS_MAX" >"$OUT/n_orders.tmp"
        mv "$OUT/n_orders.tmp" "$OUT/n_orders.txt"
    fi
    echo "following eval: $(n_orders) matches per random-commander scenario"
    orders "$OUT/teacher_orders.json" script --passes followed
    orders "$OUT/w1_400_orders.json" "$W1_400"
    "${PY[@]}" "$HERE/gates.py" --run "$RUN" bounds
    missions "$OUT/script_vs_script_missions.json" script script "$N_MISSIONS"
    missions "$OUT/v1_vs_v1_missions.json" "$V1" "$V1" "$N_MISSIONS"
    fleet "$OUT/v1_fleet_vs_script.json" "$V1" script
    exit 0
fi

if [[ $# -lt 2 ]]; then
    echo "usage: $0 baseline | <name> <checkpoint.pt>" >&2
    exit 2
fi
name=$1
ckpt=$2
[[ -f $ckpt ]] || { echo "checkpoint not found: $ckpt" >&2; exit 2; }
[[ -f $OUT/o_bounds.json ]] || { echo "no O bounds yet: run baseline first" >&2; exit 2; }
orders "$OUT/${name}_orders.json" "$ckpt"
missions "$OUT/${name}_missions_vs_v1.json" "$ckpt" "$V1" "$N_MISSIONS"
missions "$OUT/${name}_missions_vs_w1_400.json" "$ckpt" "$W1_400" "$N_MISSIONS_W1"
fleet "$OUT/${name}_fleet_vs_script.json" "$ckpt" script
fleet "$OUT/${name}_fleet_vs_v1.json" "$ckpt" "$V1"
echo "done: $name"
