#!/usr/bin/env bash
# Order pilot B3 (plan.md): run 1's w1_400 widened to the SIM_VERSION 6 obs (583
# inputs, the new columns zero and at 10x step size), then two PPO arms run
# concurrently: "transit" (script pull on transit rows only, beta 0.05 -> 0 over
# updates 30-300) and "reward" (no pull). Then the gate evals on every 50-update
# checkpoint, and the gates.
#
#   nohup lab/runs/2026-11-01-order-pilot-b3/run.sh > lab/runs/2026-11-01-order-pilot-b3/run.out 2>&1 &
#   lab/runs/2026-11-01-order-pilot-b3/run.sh eval gates      # just these stages
#   SMOKE=1 lab/runs/2026-11-01-order-pilot-b3/run.sh         # tiny sizes, into smoke/
#
# Stages: baseline ppo eval gates. Every stage skips work whose output exists; PPO
# arms resume from their latest checkpoint. The baseline stage sizes the following
# eval and fixes the teacher-first O bounds before any candidate is evaluated.
# Nothing here deletes a checkpoint. Logs: <run>/<stage or arm>.out, PPO's
# <run>/<arm>/log.jsonl.
#
# Knobs (environment): THREADS (12, evals), ARM_THREADS (6 sim + 6 torch per arm,
# two arms at once), N_UPDATES (300), EVAL_UPDATES (the hundreds, then the fifties),
# ARMS ("transit reward"), V1 (fleet pilot v1), W1_400 (run 1's w1_400), KL_COEFF
# (0.1), NEW_INPUT_LR_MULT (10), PY, RUN, SMOKE.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-01-order-pilot-b3
if [[ -z "${PY:-}" ]]; then
    if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY="uv run python"; fi
fi
# shellcheck disable=SC2206
PY=($PY)
SMOKE=${SMOKE:-0}
MAIN=/home/timg/code/rl-fighter
V1=${V1:-$MAIN/lab/runs/2026-10-30-fleet-pilot/arm_warm/checkpoints/ppo_bc_400.pt}
W1_400=${W1_400:-$MAIN/lab/runs/2026-10-31-order-pilot/w1/checkpoints/ppo_bc_400.pt}

sim_version=$("${PY[@]}" -c "import rlf_sim; print(rlf_sim.SIM_VERSION)")
if (( sim_version < 6 )); then
    echo "this run needs SIM_VERSION 6 (orders redesigned); rlf_sim is $sim_version:" \
        "uv run maturin develop -m crates/sim-py/Cargo.toml --release" >&2
    exit 2
fi
[[ -f $V1 ]] || { echo "fleet pilot v1 not found at $V1 (set V1)" >&2; exit 2; }
[[ -f $W1_400 ]] || { echo "run 1's w1_400 not found at $W1_400 (set W1_400)" >&2; exit 2; }
OBS_DIM=$("${PY[@]}" -c "import rlf_sim; print(rlf_sim.OBS_DIM)")

if [[ $SMOKE == 1 ]]; then
    RUN=${RUN:-$HERE/smoke}
    THREADS=${THREADS:-4}
    ARM_THREADS=${ARM_THREADS:-2}
    N_UPDATES=${N_UPDATES:-4}
    EVAL_UPDATES=${EVAL_UPDATES:-"2 4"}
    N_SIZE=6
    N_ORDERS_MIN=6
    N_ORDERS_MAX=12
    N_ORDERS_SCRIPTED=6
    N_MISSIONS=6
    N_MISSIONS_W1=6
    N_FLEET=2
    PPO_SIZE=(--n-envs 16 --n-steps 32 --set checkpoint_every=2 --set minibatch=256
        --set critic_warmup_updates=1 --set env_warmup_steps=60)
    BETA_SCHEDULE=(--set beta_decay_start=1 --set beta_decay_end=4)
else
    RUN=${RUN:-$HERE}
    THREADS=${THREADS:-12}
    ARM_THREADS=${ARM_THREADS:-6}
    N_UPDATES=${N_UPDATES:-300}
    EVAL_UPDATES=${EVAL_UPDATES:-"100 200 300 50 150 250"}
    N_SIZE=48
    N_ORDERS_MIN=96
    N_ORDERS_MAX=480
    N_ORDERS_SCRIPTED=96
    N_MISSIONS=516
    N_MISSIONS_W1=258
    N_FLEET=64
    PPO_SIZE=(--set critic_warmup_updates=20)
    BETA_SCHEDULE=(--set beta_decay_start=30 --set beta_decay_end=300)
fi
ARMS=${ARMS:-"transit reward"}
KL_COEFF=${KL_COEFF:-0.1}
NEW_INPUT_LR_MULT=${NEW_INPUT_LR_MULT:-10}
export RUN THREADS V1 W1_400 N_SIZE N_ORDERS_MIN N_ORDERS_MAX N_ORDERS_SCRIPTED \
    N_MISSIONS N_MISSIONS_W1 N_FLEET SMOKE
# (start update, scripted, self-play, frozen pool): run 1's bands.
BANDS='[[0,0.5,0.25,0.25],[200,0.4,0.3,0.3]]'
mkdir -p "$RUN"

log() { printf '\n== %s %s\n' "$(date +%H:%M:%S)" "$*"; }

arm_pull() {  # arm_pull NAME: the script-pull settings of an arm
    case $1 in
        transit) echo "--set beta_start=0.05 --set beta_rows=transit" ;;
        reward) echo "--set beta_start=0.0 --set beta_rows=transit" ;;
        *) echo "unknown arm $1 (known: transit reward)" >&2; exit 2 ;;
    esac
}

stage_baseline() {
    log "baseline: sizing, the teacher's and w1_400's following, O bounds, missions, deathmatch"
    "$HERE/eval.sh" baseline
}

ppo_arm() {  # ppo_arm NAME: new run, or resume an existing one
    local name=$1
    local dir=$RUN/$name pull
    if [[ -f $dir/config.yaml ]]; then
        "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --resume \
            --n-updates "$N_UPDATES"
        return
    fi
    # shellcheck disable=SC2207
    pull=($(arm_pull "$name"))
    "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --init "$W1_400" \
        --n-updates "$N_UPDATES" --seed 0 \
        --sim-threads "$ARM_THREADS" --torch-threads "$ARM_THREADS" \
        --set rosters=orders_v1 --set critic=fleet --set learner_side=random \
        --set "obs_dim=$OBS_DIM" --set "new_input_lr_mult=$NEW_INPUT_LR_MULT" \
        --set order_reward_weight=1.0 \
        --set "kl_anchor=$W1_400" --set "kl_anchor_coeff=$KL_COEFF" \
        --set "pool_seed=[$V1,$W1_400]" --set pool_seed_p=0.5 \
        --set "opponent_bands=$BANDS" \
        "${pull[@]}" --set beta_end=0.0 --set beta_heads=movement \
        "${BETA_SCHEDULE[@]}" --set checkpoint_every=50 \
        "${PPO_SIZE[@]}"
}

stage_ppo() {
    log "PPO arms ($ARMS) concurrently, $ARM_THREADS sim + $ARM_THREADS torch threads each"
    local pids=() arm
    for arm in $ARMS; do
        arm_pull "$arm" >/dev/null
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
    "${PY[@]}" "$HERE/gates.py" --run "$RUN" gates
}

STAGES=(baseline ppo eval gates)
if [[ $# -gt 0 ]]; then STAGES=("$@"); fi
for stage in "${STAGES[@]}"; do
    if ! declare -F "stage_$stage" >/dev/null; then
        echo "unknown stage: $stage (known: baseline ppo eval gates)" >&2
        exit 2
    fi
done
for stage in "${STAGES[@]}"; do
    "stage_$stage"
done
log "done: ${STAGES[*]}"
