#!/usr/bin/env bash
# Gate evals of plan.md §5 for one checkpoint (sampled actions, SIM_VERSION 3):
# fleet eval vs the script (suite fleet_v1, N_EVAL matches per roster, seed 200000),
# fighter duel vs the v3 champion and vs the script (DUEL_N, seed 100000), and the
# fleet eval vs a reference checkpoint when one is given. Skips outputs that exist.
#
#   lab/runs/2026-10-30-fleet-pilot/eval.sh baseline
#   lab/runs/2026-10-30-fleet-pilot/eval.sh <name> <checkpoint.pt> [<reference.pt>]
#
# Environment (run.sh sets them): RUN, THREADS (12), N_EVAL (64), DUEL_N (512),
# CHAMP_V3, PY.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
RUN=${RUN:-lab/runs/2026-10-30-fleet-pilot}
THREADS=${THREADS:-12}
N_EVAL=${N_EVAL:-64}
DUEL_N=${DUEL_N:-512}
CHAMP_V3=${CHAMP_V3:-lab/runs/2026-10-29-collision-damage/arm_a_rl/checkpoints/ppo_bc_600.pt}
if [[ -z "${PY:-}" ]]; then
    if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY="uv run python"; fi
fi
# shellcheck disable=SC2206
PY=($PY)
OUT=$RUN/eval
mkdir -p "$OUT"

fleet() {  # fleet OUT_JSON ARGS...: one fleet eval (Markdown next to the JSON)
    local out=$1
    shift
    if [[ -f $out ]]; then
        echo "skip: $out exists"
        return
    fi
    "${PY[@]}" -m spacefight.eval.fleet --suite fleet_v1 --n-per-roster "$N_EVAL" \
        --seed 200000 --n-threads "$THREADS" --out "$out" "$@" >"${out%.json}.md"
    echo "wrote $out"
}

duel() {  # duel OUT_JSON ARGS...: one fighter duel eval
    local out=$1
    shift
    if [[ -f $out ]]; then
        echo "skip: $out exists"
        return
    fi
    "${PY[@]}" -m spacefight.eval.duel --n "$DUEL_N" --seed 100000 \
        --n-threads "$THREADS" --out "$out" "$@" >"${out%.json}.md"
    echo "wrote $out"
}

if [[ ${1:-} == baseline ]]; then
    fleet "$OUT/script_vs_script_fleet.json" --a script --b script
    duel "$OUT/champ_v3_duel_vs_script.json" --a "$CHAMP_V3" --b script
    fleet "$OUT/champ_v3_fleet_vs_script.json" --a "$CHAMP_V3" --b script
    exit 0
fi

if [[ $# -lt 2 ]]; then
    echo "usage: $0 baseline | <name> <checkpoint.pt> [<reference.pt>]" >&2
    exit 2
fi
name=$1
ckpt=$2
ref=${3:-}
[[ -f $ckpt ]] || { echo "checkpoint not found: $ckpt" >&2; exit 2; }
fleet "$OUT/${name}_fleet_vs_script.json" --a "$ckpt" --b script
duel "$OUT/${name}_duel_vs_champ_v3.json" --a "$ckpt" --b "$CHAMP_V3"
duel "$OUT/${name}_duel_vs_script.json" --a "$ckpt" --b script
if [[ -n $ref ]]; then
    fleet "$OUT/${name}_fleet_vs_ref.json" --a "$ckpt" --b "$ref"
fi
echo "done: $name"
