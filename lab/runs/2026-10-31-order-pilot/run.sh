#!/usr/bin/env bash
# Order pilot (plan.md): fleet pilot v1 widened to the SIM_VERSION 5 order obs, then
# two PPO arms (order reward weight w = 1 and w = 0.3) over the orders_v1 mission mix,
# run concurrently, then the gate evals on every 50-update checkpoint and the gates.
#
#   nohup lab/runs/2026-10-31-order-pilot/run.sh > lab/runs/2026-10-31-order-pilot/run.out 2>&1 &
#   lab/runs/2026-10-31-order-pilot/run.sh eval gates      # just these stages
#   SMOKE=1 lab/runs/2026-10-31-order-pilot/run.sh         # tiny sizes, into smoke/
#
# Stages: baseline ppo eval gates secondary. Every stage skips work whose output
# exists ("secondary" runs the blanked-orders baseline for the candidates that pass,
# then the gates again); PPO
# arms resume from their latest checkpoint. Nothing here deletes a checkpoint. Logs:
# <run>/<stage or arm>.out, PPO's <run>/<arm>/log.jsonl.
#
# Knobs (environment): THREADS (12, evals), ARM_THREADS (6 sim + 6 torch per arm,
# two arms at once), N_UPDATES (400), EVAL_UPDATES (the hundreds, then the fifties), ARMS
# ("w1 w03"), V1 (fleet pilot v1's weights; default: fetched by tools.champion),
# KL_COEFF (0.1), PY, RUN, SMOKE.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-10-31-order-pilot
if [[ -z "${PY:-}" ]]; then
    if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY="uv run python"; fi
fi
# shellcheck disable=SC2206
PY=($PY)
SMOKE=${SMOKE:-0}
V1_ID=2026-10-30-fleet-pilot-v1

sim_version=$("${PY[@]}" -c "import rlf_sim; print(rlf_sim.SIM_VERSION)")
if (( sim_version < 5 )); then
    echo "this run needs SIM_VERSION 5 (orders in the obs); rlf_sim is $sim_version:" \
        "uv run maturin develop -m crates/sim-py/Cargo.toml --release" >&2
    exit 2
fi
if [[ -z "${V1:-}" ]]; then
    V1=$("${PY[@]}" -m tools.champion fetch "$V1_ID" | tail -n 1)
fi
[[ -f $V1 ]] || { echo "fleet pilot v1 not found at $V1 (set V1)" >&2; exit 2; }

if [[ $SMOKE == 1 ]]; then
    RUN=${RUN:-$HERE/smoke}
    THREADS=${THREADS:-4}
    ARM_THREADS=${ARM_THREADS:-2}
    N_UPDATES=${N_UPDATES:-4}
    EVAL_UPDATES=${EVAL_UPDATES:-"2 4"}
    N_ORDERS=12
    N_MISSIONS=6
    N_FLEET=2
    PPO_SIZE=(--n-envs 16 --n-steps 32 --set checkpoint_every=2 --set minibatch=256
        --set critic_warmup_updates=1 --set env_warmup_steps=60)
else
    RUN=${RUN:-$HERE}
    THREADS=${THREADS:-12}
    ARM_THREADS=${ARM_THREADS:-6}
    N_UPDATES=${N_UPDATES:-400}
    EVAL_UPDATES=${EVAL_UPDATES:-"100 200 300 400 50 150 250 350"}
    N_ORDERS=96
    N_MISSIONS=516
    N_FLEET=64
    PPO_SIZE=()
fi
ARMS=${ARMS:-"w1 w03"}
KL_COEFF=${KL_COEFF:-0.1}
export RUN THREADS V1 N_ORDERS N_MISSIONS N_FLEET SMOKE
# (start update, scripted, self-play, frozen pool): scripts >= 40 % throughout.
BANDS='[[0,0.5,0.25,0.25],[200,0.4,0.3,0.3]]'
mkdir -p "$RUN"

log() { printf '\n== %s %s\n' "$(date +%H:%M:%S)" "$*"; }

arm_weight() {  # arm_weight NAME: the order reward weight w of an arm
    case $1 in
        w1) echo 1.0 ;;
        w03) echo 0.3 ;;
        *) echo "unknown arm $1 (known: w1 w03)" >&2; exit 2 ;;
    esac
}

stage_baseline() {
    log "baseline: script vs script and v1 vs v1 missions, v1's following, v1's deathmatch"
    "$HERE/eval.sh" baseline
}

ppo_arm() {  # ppo_arm NAME: new run, or resume an existing one
    local name=$1
    local dir=$RUN/$name w
    w=$(arm_weight "$name")
    if [[ -f $dir/config.yaml ]]; then
        "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --resume \
            --n-updates "$N_UPDATES"
    else
        "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --init "$V1" \
            --n-updates "$N_UPDATES" --seed 0 \
            --sim-threads "$ARM_THREADS" --torch-threads "$ARM_THREADS" \
            --set rosters=orders_v1 --set critic=fleet --set learner_side=random \
            --set obs_dim=403 \
            --set "order_reward_weight=$w" \
            --set "kl_anchor=$V1" --set "kl_anchor_coeff=$KL_COEFF" \
            --set "pool_seed=[$V1]" --set pool_seed_p=0.5 \
            --set "opponent_bands=$BANDS" --set beta_start=0.0 \
            --set critic_warmup_updates=20 --set checkpoint_every=50 \
            "${PPO_SIZE[@]}"
    fi
}

stage_ppo() {
    log "PPO arms ($ARMS) concurrently, $ARM_THREADS sim + $ARM_THREADS torch threads each"
    local pids=() arm
    for arm in $ARMS; do
        arm_weight "$arm" >/dev/null
        ppo_arm "$arm" >>"$RUN/$arm.out" 2>&1 &
        pids+=($!)
    done
    # SIGTERM / Ctrl-C reach every trainer, which checkpoints after the update.
    trap 'kill -TERM ${pids[*]} 2>/dev/null || true' TERM INT
    local status=0 pid
    for pid in "${pids[@]}"; do
        wait "$pid" || status=$?
    done
    wait # a signal interrupts the waits above; let the trainers finish saving
    trap - TERM INT
    for arm in $ARMS; do tail -n 1 "$RUN/$arm.out"; done
    return "$status"
}

stage_eval() {
    log "gate evals (eval.sh), $THREADS threads"
    local u arm
    for u in $EVAL_UPDATES; do
        for arm in $ARMS; do
            local ckpt=$RUN/$arm/checkpoints/ppo_bc_$u.pt
            if [[ -f $ckpt ]]; then
                "$HERE/eval.sh" "${arm}_$u" "$ckpt"
            else
                echo "skip ${arm}_$u: $ckpt not found"
            fi
        done
    done
}

stage_gates() {
    log "gates (plan.md §5)"
    "${PY[@]}" "$HERE/gates.py" --run "$RUN"
}

stage_secondary() {
    log "secondary baseline (order block zeroed) for the candidates that pass"
    local name
    for name in $("${PY[@]}" -c "
import json, sys
data = json.load(open(sys.argv[1]))
print(' '.join(c['candidate'] for c in data['candidates'] if c['passed']))
" "$RUN/eval/gates.json"); do
        local arm=${name%_*} u=${name##*_}
        "$HERE/eval.sh" "$name" "$RUN/$arm/checkpoints/ppo_bc_$u.pt" blank
    done
    stage_gates
}

STAGES=(baseline ppo eval gates secondary)
if [[ $# -gt 0 ]]; then STAGES=("$@"); fi
for stage in "${STAGES[@]}"; do
    if ! declare -F "stage_$stage" >/dev/null; then
        echo "unknown stage: $stage (known: baseline ppo eval gates secondary)" >&2
        exit 2
    fi
done
for stage in "${STAGES[@]}"; do
    "stage_$stage"
done
log "done: ${STAGES[*]}"
