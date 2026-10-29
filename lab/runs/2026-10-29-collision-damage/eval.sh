#!/usr/bin/env bash
# Gate evals of plan.md §4 for one checkpoint, all under SIM_VERSION 3:
# duel vs the script and vs the v2 champion (n=512), contact survey vs the script
# (n=128). Skips outputs that exist.
#
#   lab/runs/2026-10-29-collision-damage/eval.sh <name> <checkpoint.pt>
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
RUN=lab/runs/2026-10-29-collision-damage
CHAMP_V2=lab/runs/2026-10-28-learnability-spike/ppo_bc/checkpoints/ppo_bc_1200.pt
PY=(.venv/bin/python)
THREADS=${THREADS:-12}
name=$1
ckpt=$2
mkdir -p "$RUN/eval"

duel() {  # duel OUT ARGS...
    local out=$1
    shift
    [[ -f $out ]] && return
    "${PY[@]}" -m spacefight.eval.duel --n 512 --seed 100000 --n-threads "$THREADS" \
        --out "$out" "$@" >/dev/null
}

duel "$RUN/eval/${name}_vs_script.json" --a "$ckpt" --b script
duel "$RUN/eval/${name}_vs_champ_v2.json" --a "$ckpt" --b "$CHAMP_V2"
out="$RUN/eval/${name}_survey_vs_script.json"
[[ -f $out ]] || PYTHONPATH=. "${PY[@]}" tools/contact_survey.py --a "$ckpt" \
    --b script --n 128 --out "$out" >/dev/null
echo "done: $name"
