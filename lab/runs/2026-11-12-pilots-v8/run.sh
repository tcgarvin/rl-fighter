#!/usr/bin/env bash
# Pilots on SIM_VERSION 8: go-to orders with deadlines (plan.md, docs/PILOT_TRAINING.md).
# Each arm is a new run started from a night-4 pilot, widened from 583 to 587 inputs so it
# can see the deadline (order_time: has a deadline, time left, urgency, closeness). The
# settings are night 4's; what changes is the sim, the go-to drills (three in four carry a
# deadline) and go-to pay at a deadline (goto_timed_bonus, goto_miss_penalty).
# followers_v8_blind is the control: the same start and pay as followers_v8, but it keeps
# its 583 inputs, so it is paid by the deadline without seeing it.
# Stops by SIGTERM at the deadline; each trainer checkpoints cleanly. Re-running resumes.
#
#   DEADLINE="08:00 tomorrow" nohup lab/runs/2026-11-12-pilots-v8/run.sh \
#       > lab/runs/2026-11-12-pilots-v8/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-12-pilots-v8/run.sh     # tiny sizes, into smoke/
#
# Env: ARMS (the four below), N_ENVS (256), N_UPDATES (6000, an upper bound on an arm's
# total updates; the deadline ends the night), DEADLINE (a `date -d` string, required
# outside SMOKE), ARM_THREADS (3 sim + 3 torch), NEW_INPUT_LR (3), TIMED_BONUS (1.0),
# MISS_PENALTY (1.0).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-12-pilots-v8
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
MAIN=/home/timg/code/rl-fighter
FAMILIES=$MAIN/lab/runs/2026-11-01-pilot-families
F995=$MAIN/lab/runs/2026-11-01-fighters-v2/f995/checkpoints/ppo_bc_701.pt
TRANSIT=$MAIN/lab/runs/2026-11-01-order-pilot-b3/transit/checkpoints/ppo_bc_300.pt
R=$MAIN/lab/runs/2026-11-01-order-pilot-b3/reward/checkpoints/ppo_bc_300.pt
W1_400=$MAIN/lab/runs/2026-10-31-order-pilot/w1/checkpoints/ppo_bc_400.pt
V1=$MAIN/lab/runs/2026-10-30-fleet-pilot/arm_warm/checkpoints/ppo_bc_400.pt
F99_696=$MAIN/lab/runs/2026-11-01-fighters-v2/f99/checkpoints/ppo_bc_696.pt
# Tonight's parents.
FOLLOWERS_1793=$FAMILIES/followers/checkpoints/ppo_bc_1793.pt
FIGHTERS_1832=$FAMILIES/fighters/checkpoints/ppo_bc_1832.pt
PAY1_1317=$FAMILIES/fighters_pay1/checkpoints/ppo_bc_1317.pt
# The frozen pool: nights 1 to 3's (POOL3 of the pilot-families run) plus nights 3 and 4's
# six. A new run has no checkpoints of its own yet, so its line's history comes from here.
POOL_FILES=("$F995" "$TRANSIT" "$R" "$W1_400" "$V1"
    "$FAMILIES/fighters/checkpoints/ppo_bc_506.pt"
    "$FAMILIES/followers/checkpoints/ppo_bc_513.pt"
    "$FAMILIES/fighters/checkpoints/ppo_bc_959.pt"
    "$FAMILIES/followers/checkpoints/ppo_bc_955.pt"
    "$FAMILIES/fighters_pay1/checkpoints/ppo_bc_462.pt"
    "$F99_696"
    "$FAMILIES/fighters/checkpoints/ppo_bc_1338.pt"
    "$FAMILIES/followers/checkpoints/ppo_bc_1323.pt"
    "$FAMILIES/fighters_pay1/checkpoints/ppo_bc_849.pt"
    "$FIGHTERS_1832" "$FOLLOWERS_1793" "$PAY1_1317")
for f in "${POOL_FILES[@]}"; do
    [[ -f $f ]] || { echo "missing checkpoint $f" >&2; exit 2; }
done
POOL="[$(IFS=,; echo "${POOL_FILES[*]}")]"

ARMS=${ARMS:-"followers_v8 fighters_v8 fighters_pay1_v8 followers_v8_blind"}
if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    N_UPDATES=${N_UPDATES:-3}
    ARM_THREADS=${ARM_THREADS:-2}
    DEADLINE=${DEADLINE:-"+20 minutes"}
    SIZE=(--n-envs 16 --n-steps 32 --set checkpoint_every=1 --set minibatch=256
        --set critic_warmup_updates=1 --set early_clip_updates=1)
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"08:00 tomorrow\"" >&2; exit 2; }
    RUN=$HERE
    N_UPDATES=${N_UPDATES:-6000}
    ARM_THREADS=${ARM_THREADS:-3}
    SIZE=(--n-envs "${N_ENVS:-256}" --set checkpoint_every=50
        --set critic_warmup_updates=20 --set early_clip_updates=50)
fi
deadline=$(date -d "$DEADLINE" +%s)

# Night 4's settings, shared by every arm.
COMMON="--set opponent_bands=[[0,0.2,0.4,0.4]] --set enemy_sampling=pfsp --set pool_seed=$POOL"
COMMON="$COMMON --set commander_stable=[live] --set extra_fire_cost=0.002 --set value_only_rows=true"
# New on v8: what a go-to with a deadline pays (times the arm's order_reward_weight).
COMMON="$COMMON --set goto_timed_bonus=${TIMED_BONUS:-1.0} --set goto_miss_penalty=${MISS_PENALTY:-1.0}"
# The four new inputs start at zero weight; their first-layer columns step this much faster.
SEES="--set obs_dim=587 --set new_input_lr_mult=${NEW_INPUT_LR:-3}"
BLIND="--set obs_dim=583"
FOLLOWERS_DRILLS='{"drill_share":0.35,"drill_weights":[3,1,1],"commander_p":0.667}'

arm_init() {
    case $1 in
        followers_v8 | followers_v8_blind) echo "$FOLLOWERS_1793" ;;
        fighters_v8) echo "$FIGHTERS_1832" ;;
        fighters_pay1_v8) echo "$PAY1_1317" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_args() {
    case $1 in
        followers_v8) echo "$COMMON $SEES --set order_reward_weight=1.0 --set roster_overrides=$FOLLOWERS_DRILLS" ;;
        followers_v8_blind) echo "$COMMON $BLIND --set order_reward_weight=1.0 --set roster_overrides=$FOLLOWERS_DRILLS" ;;
        fighters_v8) echo "$COMMON $SEES --set order_reward_weight=3.0 --set roster_overrides={\"drill_share\":0.35,\"drill_weights\":[2,1,1],\"commander_p\":0.333}" ;;
        fighters_pay1_v8) echo "$COMMON $SEES --set order_reward_weight=1.0 --set roster_overrides={\"drill_share\":0.25,\"drill_weights\":[2,1,1],\"commander_p\":0.333}" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}

pids=()
for arm in $ARMS; do
    dir=$RUN/$arm
    mkdir -p "$dir"
    if [[ -f $dir/config.yaml ]]; then
        # shellcheck disable=SC2046
        "$PY" -m spacefight.train_spike ppo --run-dir "$dir" --resume --n-updates "$N_UPDATES" \
            --set sim_threads="$ARM_THREADS" --set torch_threads="$ARM_THREADS" \
            $(arm_args "$arm") >>"$RUN/$arm.out" 2>&1 &
    else
        # shellcheck disable=SC2046
        "$PY" -m spacefight.train_spike ppo --run-dir "$dir" --init "$(arm_init "$arm")" \
            --n-updates "$N_UPDATES" --seed 21 \
            --sim-threads "$ARM_THREADS" --torch-threads "$ARM_THREADS" \
            --set rosters=pilots_v1 --set critic=fleet --set learner_side=random \
            --set gamma=0.995 --set lr_decay=false \
            --set beta_start=0.0 --set beta_end=0.0 --set pool_seed_p=0.5 \
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
