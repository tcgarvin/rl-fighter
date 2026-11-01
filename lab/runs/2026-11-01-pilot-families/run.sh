#!/usr/bin/env bash
# First night of pilot families (plan.md, docs/PILOT_TRAINING.md). One learner per family.
# Stops by SIGTERM at the deadline; each trainer checkpoints cleanly. Re-running resumes.
#
#   DEADLINE="06:00 tomorrow" nohup lab/runs/2026-11-01-pilot-families/run.sh \
#       > lab/runs/2026-11-01-pilot-families/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-01-pilot-families/run.sh     # tiny sizes, into smoke/
#
# Env: ARMS ("fighters followers scratch"), N_ENVS (256), N_UPDATES (1500, an upper bound;
# the deadline ends it), DEADLINE (a `date -d` string, required outside SMOKE),
# ARM_THREADS (4 sim + 4 torch).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-01-pilot-families
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
MAIN=/home/timg/code/rl-fighter
F995=$MAIN/lab/runs/2026-11-01-fighters-v2/f995/checkpoints/ppo_bc_701.pt
TRANSIT=$MAIN/lab/runs/2026-11-01-order-pilot-b3/transit/checkpoints/ppo_bc_300.pt
R=$MAIN/lab/runs/2026-11-01-order-pilot-b3/reward/checkpoints/ppo_bc_300.pt
W1_400=$MAIN/lab/runs/2026-10-31-order-pilot/w1/checkpoints/ppo_bc_400.pt
V1=$MAIN/lab/runs/2026-10-30-fleet-pilot/arm_warm/checkpoints/ppo_bc_400.pt
for f in "$F995" "$TRANSIT" "$R" "$W1_400" "$V1"; do
    [[ -f $f ]] || { echo "missing checkpoint $f" >&2; exit 2; }
done

ARMS=${ARMS:-"fighters followers scratch"}
if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    N_UPDATES=${N_UPDATES:-3}
    ARM_THREADS=${ARM_THREADS:-2}
    DEADLINE=${DEADLINE:-"+20 minutes"}
    SIZE=(--n-envs 16 --n-steps 32 --set checkpoint_every=1 --set minibatch=256
        --set critic_warmup_updates=1 --set early_clip_updates=1)
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"06:00 tomorrow\"" >&2; exit 2; }
    RUN=$HERE
    N_UPDATES=${N_UPDATES:-1500}
    ARM_THREADS=${ARM_THREADS:-4}
    SIZE=(--n-envs "${N_ENVS:-256}" --set checkpoint_every=50
        --set critic_warmup_updates=20 --set early_clip_updates=50)
fi
deadline=$(date -d "$DEADLINE" +%s)
POOL="[$F995,$TRANSIT,$R,$W1_400,$V1]"
MIXED_BANDS='[[0,0.2,0.4,0.4]]'
SCRATCH_BANDS='[[0,0.5,0.5,0.0]]'

# Shares of section 4: commander_p splits what is left after drills.
arm_init() {
    case $1 in
        fighters) echo "$F995" ;;
        followers) echo "$TRANSIT" ;;
        scratch) echo scratch ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_args() {
    case $1 in
        fighters) echo "--set order_reward_weight=3.0 --set opponent_bands=$MIXED_BANDS --set enemy_sampling=pfsp --set roster_overrides={\"drill_share\":0.1,\"commander_p\":0.333}" ;;
        followers) echo "--set order_reward_weight=1.0 --set opponent_bands=$MIXED_BANDS --set enemy_sampling=pfsp --set roster_overrides={\"drill_share\":0.25,\"commander_p\":0.667}" ;;
        scratch) echo "--set order_reward_weight=1.0 --set actor_lr=0.0003 --set opponent_bands=$SCRATCH_BANDS --set roster_overrides={\"drill_share\":0.1,\"commander_p\":0.333}" ;;
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
        "$PY" -m spacefight.train_spike ppo --run-dir "$dir" --init "$(arm_init "$arm")" \
            --n-updates "$N_UPDATES" --seed 21 \
            --sim-threads "$ARM_THREADS" --torch-threads "$ARM_THREADS" \
            --set rosters=pilots_v1 --set critic=fleet --set learner_side=random \
            --set obs_dim=583 --set gamma=0.995 --set lr_decay=false \
            --set beta_start=0.0 --set beta_end=0.0 \
            --set "pool_seed=$POOL" --set pool_seed_p=0.5 \
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
