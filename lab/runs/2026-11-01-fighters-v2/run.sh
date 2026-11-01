#!/usr/bin/env bash
# Fighters v2 (plan.md): three plain-RL arms from run B3's reward_300, no script pull,
# constant LR. Stops by SIGTERM at the deadline; each trainer checkpoints cleanly.
#
#   nohup lab/runs/2026-11-01-fighters-v2/run.sh > lab/runs/2026-11-01-fighters-v2/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-01-fighters-v2/run.sh     # tiny sizes, into smoke/
#
# Env: ARMS ("f99 f995 hide"), N_UPDATES (1200, an upper bound; the deadline ends it),
# DEADLINE (a `date -d` string, "05:30 tomorrow"), ARM_THREADS (4 sim + 4 torch).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-01-fighters-v2
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
MAIN=/home/timg/code/rl-fighter
V1=$MAIN/lab/runs/2026-10-30-fleet-pilot/arm_warm/checkpoints/ppo_bc_400.pt
W1_400=$MAIN/lab/runs/2026-10-31-order-pilot/w1/checkpoints/ppo_bc_400.pt
R=$MAIN/lab/runs/2026-11-01-order-pilot-b3/reward/checkpoints/ppo_bc_300.pt
for f in "$V1" "$W1_400" "$R"; do
    [[ -f $f ]] || { echo "missing checkpoint $f" >&2; exit 2; }
done

ARMS=${ARMS:-"f99 f995 hide"}
if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    N_UPDATES=${N_UPDATES:-3}
    ARM_THREADS=${ARM_THREADS:-2}
    DEADLINE=${DEADLINE:-"+20 minutes"}
    SIZE=(--n-envs 16 --n-steps 32 --set checkpoint_every=1 --set minibatch=256
        --set critic_warmup_updates=1 --set early_clip_updates=1)
else
    RUN=$HERE
    N_UPDATES=${N_UPDATES:-1200}
    ARM_THREADS=${ARM_THREADS:-4}
    DEADLINE=${DEADLINE:-"05:30 tomorrow"}
    SIZE=(--set checkpoint_every=50 --set critic_warmup_updates=20 --set early_clip_updates=50)
fi
deadline=$(date -d "$DEADLINE" +%s)
BANDS='[[0,0.2,0.4,0.4]]'

arm_args() {
    case $1 in
        f99) echo "--set gamma=0.99 --set order_reward_weight=0.0" ;;
        f995) echo "--set gamma=0.995 --set order_reward_weight=0.0" ;;
        hide) echo "--set gamma=0.99 --set order_reward_weight=1.0 --set hide_damage_when_ordered=true --set kl_anchor=$R --set kl_anchor_coeff=0.1" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}

pids=()
for arm in $ARMS; do
    dir=$RUN/$arm
    mkdir -p "$dir"
    if [[ -f $dir/config.yaml ]]; then
        "$PY" -m spacefight.train_spike ppo --run-dir "$dir" --resume --n-updates "$N_UPDATES" \
            >>"$RUN/$arm.out" 2>&1 &
    else
        # shellcheck disable=SC2046
        "$PY" -m spacefight.train_spike ppo --run-dir "$dir" --init "$R" \
            --n-updates "$N_UPDATES" --seed 11 \
            --sim-threads "$ARM_THREADS" --torch-threads "$ARM_THREADS" \
            --set rosters=orders_v1 --set critic=fleet --set learner_side=random \
            --set obs_dim=583 --set lr_decay=false --set beta_start=0.0 --set beta_end=0.0 \
            --set "pool_seed=[$V1,$W1_400,$R]" --set pool_seed_p=0.5 \
            --set "opponent_bands=$BANDS" \
            $(arm_args "$arm") "${SIZE[@]}" >>"$RUN/$arm.out" 2>&1 &
    fi
    pids+=($!)
    echo "$(date +%H:%M:%S) $arm pid ${pids[-1]}"
done

# SIGTERM reaches every trainer, which checkpoints after its update.
stop() { kill -TERM "${pids[@]}" 2>/dev/null || true; }
trap stop TERM INT
while (( $(date +%s) < deadline )); do
    alive=0
    for pid in "${pids[@]}"; do kill -0 "$pid" 2>/dev/null && alive=1; done
    (( alive )) || break
    sleep 20 &
    wait $! || true
done
stop
wait || true
echo "$(date +%H:%M:%S) done: PPO"
