#!/usr/bin/env bash
# Order pilot B2b (plan.md): run 1's w1_400 (2026-10-31-order-pilot) trained on, with
# a script pull on ordered rows, hold points near the action and a bigger presence
# pay. Two PPO arms run concurrently: "pull", and "pull_dagger" (one ordered DAgger
# round first). Then the gate evals on every 50-update checkpoint, and the gates.
#
#   nohup lab/runs/2026-10-31-order-pilot-b2b/run.sh > lab/runs/2026-10-31-order-pilot-b2b/run.out 2>&1 &
#   lab/runs/2026-10-31-order-pilot-b2b/run.sh eval gates     # just these stages
#   SMOKE=1 lab/runs/2026-10-31-order-pilot-b2b/run.sh        # tiny sizes, into smoke/
#
# Stages: baseline ppo eval gates secondary. Every stage skips work whose output
# exists ("secondary" runs the blanked-orders baseline for the candidates that pass,
# then the gates again); PPO arms resume from their latest checkpoint, and the
# DAgger round is skipped once its checkpoint exists. Nothing here deletes a
# checkpoint. Logs: <run>/<stage or arm>.out, PPO's <run>/<arm>/log.jsonl.
#
# Knobs (environment): THREADS (12, evals), ARM_THREADS (6 sim + 6 torch per arm,
# two arms at once), N_UPDATES (300), EVAL_UPDATES (the hundreds, then the fifties),
# ARMS ("pull pull_dagger"), V1 (fleet pilot v1's weights; default: fetched by
# tools.champion), W1 (run 1's w1_400; default: its checkpoint in this checkout),
# KL_COEFF (0.1), DAGGER_ROWS (3000000), PY, RUN, SMOKE.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-10-31-order-pilot-b2b
if [[ -z "${PY:-}" ]]; then
    if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY="uv run python"; fi
fi
# shellcheck disable=SC2206
PY=($PY)
SMOKE=${SMOKE:-0}
V1_ID=2026-10-30-fleet-pilot-v1
W1=${W1:-lab/runs/2026-10-31-order-pilot/w1/checkpoints/ppo_bc_400.pt}

# B2b needs the sim of this branch: SIM_VERSION 5 with the near-action hold points
# (the version number did not change, so check for the B2b trainer instead).
sim_version=$("${PY[@]}" -c "import rlf_sim; print(rlf_sim.SIM_VERSION)")
if (( sim_version < 5 )); then
    echo "this run needs SIM_VERSION 5; rlf_sim is $sim_version:" \
        "uv run maturin develop -m crates/sim-py/Cargo.toml --release" >&2
    exit 2
fi
"${PY[@]}" -c "from spacefight.env.rust_env import RustVecEnv; RustVecEnv.scripted_order_rows" \
    || { echo "spacefight is older than B2b (no scripted_order_rows)" >&2; exit 2; }
if [[ -z "${V1:-}" ]]; then
    V1=$("${PY[@]}" -m tools.champion fetch "$V1_ID" | tail -n 1)
fi
[[ -f $V1 ]] || { echo "fleet pilot v1 not found at $V1 (set V1)" >&2; exit 2; }
[[ -f $W1 ]] || { echo "run 1's w1_400 not found at $W1 (set W1)" >&2; exit 2; }

if [[ $SMOKE == 1 ]]; then
    RUN=${RUN:-$HERE/smoke}
    THREADS=${THREADS:-4}
    ARM_THREADS=${ARM_THREADS:-2}
    N_UPDATES=${N_UPDATES:-4}
    EVAL_UPDATES=${EVAL_UPDATES:-"2 4"}
    N_ORDERS=12
    N_MISSIONS=6
    N_FLEET=2
    DAGGER_ROWS=${DAGGER_ROWS:-20000}
    DAGGER_ENVS=40
    PPO_SIZE=(--n-envs 16 --n-steps 32 --set checkpoint_every=2 --set minibatch=256
        --set critic_warmup_updates=1 --set env_warmup_steps=60
        --set beta_decay_start=1 --set beta_decay_end=4)
else
    RUN=${RUN:-$HERE}
    THREADS=${THREADS:-12}
    ARM_THREADS=${ARM_THREADS:-6}
    N_UPDATES=${N_UPDATES:-300}
    EVAL_UPDATES=${EVAL_UPDATES:-"100 200 300 50 150 250"}
    N_ORDERS=96
    N_MISSIONS=516
    N_FLEET=64
    DAGGER_ROWS=${DAGGER_ROWS:-3000000}
    DAGGER_ENVS=256
    PPO_SIZE=()
fi
ARMS=${ARMS:-"pull pull_dagger"}
KL_COEFF=${KL_COEFF:-0.1}
export RUN THREADS V1 W1 N_ORDERS N_MISSIONS N_FLEET SMOKE
# (start update, scripted, self-play, frozen pool): run 1's bands.
BANDS='[[0,0.5,0.25,0.25],[200,0.4,0.3,0.3]]'
mkdir -p "$RUN"

log() { printf '\n== %s %s\n' "$(date +%H:%M:%S)" "$*"; }

check_arm() {  # check_arm NAME: known arm?
    case $1 in
        pull | pull_dagger) ;;
        *) echo "unknown arm $1 (known: pull pull_dagger)" >&2; exit 2 ;;
    esac
}

stage_baseline() {
    log "baseline: missions (script, v1), v1's / w1_400's / the script's following, v1's deathmatch"
    "$HERE/eval.sh" baseline
}

arm_init() {  # arm_init NAME: the PPO init of an arm (runs the DAgger round first)
    local name=$1
    if [[ $name == pull ]]; then
        echo "$W1"
        return
    fi
    local out=$RUN/$name/dagger
    if [[ ! -f $out/dagger_ordered.pt ]]; then
        "${PY[@]}" -m spacefight.train_spike dagger-ordered --init "$W1" --out "$out" \
            --rows "$DAGGER_ROWS" --n-envs "$DAGGER_ENVS" --threads $((2 * ARM_THREADS)) \
            --seed 1 --epochs 1 --lr 1e-4 --lr-final 1e-5 --heads movement >&2
    fi
    echo "$out/dagger_ordered.pt"
}

ppo_arm() {  # ppo_arm NAME: new run, or resume an existing one
    local name=$1
    local dir=$RUN/$name init
    if [[ -f $dir/config.yaml ]]; then
        "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --resume \
            --n-updates "$N_UPDATES"
        return
    fi
    init=$(arm_init "$name")
    "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --init "$init" \
        --n-updates "$N_UPDATES" --seed 0 \
        --sim-threads "$ARM_THREADS" --torch-threads "$ARM_THREADS" \
        --set rosters=orders_v1 --set critic=fleet --set learner_side=random \
        --set obs_dim=403 --set order_reward_weight=1.0 \
        --set "kl_anchor=$V1" --set "kl_anchor_coeff=$KL_COEFF" \
        --set "pool_seed=[$V1,$W1]" --set pool_seed_p=0.5 \
        --set "opponent_bands=$BANDS" \
        --set beta_start=0.1 --set beta_end=0.0 \
        --set beta_decay_start=30 --set beta_decay_end=300 \
        --set beta_rows=ordered --set beta_heads=movement \
        --set critic_warmup_updates=10 --set checkpoint_every=50 \
        "${PPO_SIZE[@]}"
}

stage_ppo() {
    log "PPO arms ($ARMS) concurrently, $ARM_THREADS sim + $ARM_THREADS torch threads each"
    local pids=() arm
    for arm in $ARMS; do
        check_arm "$arm"
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
