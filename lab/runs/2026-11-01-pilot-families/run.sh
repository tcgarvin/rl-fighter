#!/usr/bin/env bash
# Pilot families, one learner per arm (plan.md, docs/PILOT_TRAINING.md). Stops by SIGTERM
# at the deadline; each trainer checkpoints cleanly. Re-running resumes, and a resumed arm
# takes the settings below (the trainer keeps the old config as config_before_<N>.yaml).
#
# Night 1 (2026-11-01): fighters, followers, scratch. Night 2: fighters resumes with drills
# 0.25, followers resumes unchanged, both with fighters_506 and followers_513 added to the
# pool; fighters_pay1 replays night 1's fighters at order pay 1. scratch is retired.
# Night 3 (2026-11-08): all three resume under the live commander stable (the script and
# the three learned commanders), with more drills weighted to go-to, and night 2's three
# and f99_696 (top by WAR) added to the pool.
# Night 4 (2026-11-09): the price of a shot. Every line resumes unchanged but for
# extra_fire_cost 0.002 (twice the sim's FIRE_COST per shot fired), and fighters_fire4, a
# copy of fighters at update 1338 made before any arm starts, pays 0.006 (four times).
# Four arms, so 3 sim + 3 torch threads each (was 4 + 4 for three).
#
#   DEADLINE="05:15 tomorrow" nohup lab/runs/2026-11-01-pilot-families/run.sh \
#       > lab/runs/2026-11-01-pilot-families/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-01-pilot-families/run.sh     # tiny sizes, into smoke/
#
# Env: ARMS ("fighters followers fighters_pay1 fighters_fire4"), N_ENVS (256), N_UPDATES
# (1500, an upper bound; the deadline ends it), DEADLINE (a `date -d` string, required
# outside SMOKE), ARM_THREADS (3 sim + 3 torch).
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
FIGHTERS_506=$MAIN/$HERE/fighters/checkpoints/ppo_bc_506.pt
FOLLOWERS_513=$MAIN/$HERE/followers/checkpoints/ppo_bc_513.pt
FIGHTERS_959=$MAIN/$HERE/fighters/checkpoints/ppo_bc_959.pt
FOLLOWERS_955=$MAIN/$HERE/followers/checkpoints/ppo_bc_955.pt
PAY1_462=$MAIN/$HERE/fighters_pay1/checkpoints/ppo_bc_462.pt
F99_696=$MAIN/lab/runs/2026-11-01-fighters-v2/f99/checkpoints/ppo_bc_696.pt
for f in "$F995" "$TRANSIT" "$R" "$W1_400" "$V1" "$FIGHTERS_506" "$FOLLOWERS_513" \
    "$FIGHTERS_959" "$FOLLOWERS_955" "$PAY1_462" "$F99_696"; do
    [[ -f $f ]] || { echo "missing checkpoint $f" >&2; exit 2; }
done

ARMS=${ARMS:-"fighters followers fighters_pay1 fighters_fire4"}
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
    ARM_THREADS=${ARM_THREADS:-3}
    SIZE=(--n-envs "${N_ENVS:-256}" --set checkpoint_every=50
        --set critic_warmup_updates=20 --set early_clip_updates=50)
fi
deadline=$(date -d "$DEADLINE" +%s)
# Night 1's pool, and night 2's with the first night's two survivors. fighters_pay1 keeps
# night 1's so that order pay is the only difference from night 1's fighters.
POOL1="[$F995,$TRANSIT,$R,$W1_400,$V1]"
POOL2="[$F995,$TRANSIT,$R,$W1_400,$V1,$FIGHTERS_506,$FOLLOWERS_513]"
POOL3="[$F995,$TRANSIT,$R,$W1_400,$V1,$FIGHTERS_506,$FOLLOWERS_513,$FIGHTERS_959,$FOLLOWERS_955,$PAY1_462,$F99_696]"
# Night 3: every match that shows orders draws each side's commander from the live stable.
LIVE_CMD="--set commander_stable=[live]"
MIXED_BANDS='[[0,0.2,0.4,0.4]]'
# Night 4: shaping per shot fired, on top of the sim's FIRE_COST of 0.002.
FIRE2="--set extra_fire_cost=0.002"
FIRE4="--set extra_fire_cost=0.006"
FIGHTERS_ARGS="--set order_reward_weight=3.0 --set opponent_bands=$MIXED_BANDS --set enemy_sampling=pfsp --set pool_seed=$POOL3 $LIVE_CMD --set roster_overrides={\"drill_share\":0.35,\"drill_weights\":[2,1,1],\"commander_p\":0.333}"
SCRATCH_BANDS='[[0,0.5,0.5,0.0]]'

# Shares of section 4: commander_p splits what is left after drills.
arm_init() {
    case $1 in
        # fighters_fire4 starts from F995 only in SMOKE; for real it is a copy of fighters.
        fighters | fighters_pay1 | fighters_fire4) echo "$F995" ;;
        followers) echo "$TRANSIT" ;;
        scratch) echo scratch ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_args() {
    case $1 in
        # Night 4: night 3's settings plus the fire cost. Earlier nights' settings are in
        # plan.md and config_before_<N>.yaml.
        fighters) echo "$FIGHTERS_ARGS $FIRE2" ;;
        fighters_fire4) echo "$FIGHTERS_ARGS $FIRE4" ;;
        followers) echo "--set order_reward_weight=1.0 --set opponent_bands=$MIXED_BANDS --set enemy_sampling=pfsp --set pool_seed=$POOL3 $LIVE_CMD --set roster_overrides={\"drill_share\":0.35,\"drill_weights\":[3,1,1],\"commander_p\":0.667} $FIRE2" ;;
        fighters_pay1) echo "--set order_reward_weight=1.0 --set opponent_bands=$MIXED_BANDS --set enemy_sampling=pfsp --set pool_seed=$POOL3 $LIVE_CMD --set roster_overrides={\"drill_share\":0.25,\"drill_weights\":[2,1,1],\"commander_p\":0.333} $FIRE2" ;;
        # Night 1 only.
        scratch) echo "--set order_reward_weight=1.0 --set actor_lr=0.0003 --set opponent_bands=$SCRATCH_BANDS --set pool_seed=$POOL1 --set roster_overrides={\"drill_share\":0.1,\"commander_p\":0.333}" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}

# Night 4's fork, before any arm runs (a resumed fighters rewrites its config at once):
# fighters_fire4 is fighters' run dir as of update 1338, checkpoints, optimiser and rng
# state included, so it resumes where fighters does and differs only in its fire cost.
FORK_UPDATE=1338
if [[ $SMOKE != 1 && " $ARMS " == *" fighters_fire4 "* && ! -d $RUN/fighters_fire4 ]]; then
    last=$(find "$RUN/fighters/checkpoints" -name 'ppo_bc_*.pt' -printf '%f\n' \
        | sed 's/ppo_bc_\([0-9]*\)\.pt/\1/' | sort -n | tail -1)
    [[ $last == "$FORK_UPDATE" ]] || {
        echo "fighters is at update $last, not $FORK_UPDATE: not forking" >&2; exit 2; }
    cp -r "$RUN/fighters" "$RUN/fighters_fire4"
    echo "$(date +%H:%M:%S) fighters_fire4 forked from fighters at $FORK_UPDATE"
fi

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
            --set obs_dim=583 --set gamma=0.995 --set lr_decay=false \
            --set beta_start=0.0 --set beta_end=0.0 \
            --set pool_seed_p=0.5 \
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
