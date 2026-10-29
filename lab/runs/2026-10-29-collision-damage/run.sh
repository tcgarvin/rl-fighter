#!/usr/bin/env bash
# Collision-damage fine-tune (plan.md §3): two PPO arms from the spike champion
# under SIM_VERSION 3, run concurrently. Resumes an arm whose config.yaml exists.
#
#   lab/runs/2026-10-29-collision-damage/run.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
RUN=lab/runs/2026-10-29-collision-damage
INIT=lab/runs/2026-10-28-learnability-spike/ppo_bc/checkpoints/ppo_bc_1200.pt
if [[ -z "${PY:-}" ]]; then
    if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY="uv run python"; fi
fi
# shellcheck disable=SC2206
PY=($PY)
BANDS='[[0,0.5,0.3,0.2],[200,0.3,0.4,0.3]]'

ppo_run() {  # ppo_run NAME EXTRA_SET_ARGS...
    local name=$1
    shift
    local dir=$RUN/$name
    if [[ -f $dir/config.yaml ]]; then
        "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --resume
    else
        "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --init "$INIT" \
            --n-updates 800 --seed 0 --sim-threads 6 --torch-threads 6 \
            --set "opponent_bands=$BANDS" "$@"
    fi
}

ppo_run arm_a_rl --set beta_start=0.0 >>"$RUN/arm_a_rl.out" 2>&1 &
a=$!
ppo_run arm_b_pull --set beta_decay_end=400 >>"$RUN/arm_b_pull.out" 2>&1 &
b=$!
trap 'kill -TERM $a $b 2>/dev/null || true' TERM INT
status=0
wait "$a" || status=$?
wait "$b" || status=$?
wait
trap - TERM INT
tail -n 1 "$RUN/arm_a_rl.out" "$RUN/arm_b_pull.out"
exit "$status"
