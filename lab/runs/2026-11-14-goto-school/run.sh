#!/usr/bin/env bash
# Go-to school (plan.md): the second night on SIM_VERSION 8. The first night's pilots can
# see a go-to's deadline but did not learn to fly by it: an arm finished about 1,800 go-to
# drills all night, and at order pay 1 a deadline (+1 / -1) is worth about one kill.
# Tonight raises both on the followers line and leaves fighters as it was:
#   followers_school  followers_v8_352 on, go-to drills most of its training (drill share
#                     0.7, go-to weighted 6), a deadline worth 3 (bonus and penalty)
#   followers_pay3    followers_v8_352 on, last night's drills, a deadline worth 3
#   fighters_v8       fighters_v8_362 on, unchanged (its order pay of 3 already makes a
#                     deadline worth 3): a second night of the same
# Each arm continues last night's run: its directory here starts as a copy of that run's
# (config, log, checkpoints with their optimiser state), so update counts carry on from
# about 352 and the four deadline inputs keep their faster step.
# Stops by SIGTERM at the deadline; each trainer checkpoints cleanly. Re-running resumes.
#
#   DEADLINE="07:20" nohup lab/runs/2026-11-14-goto-school/run.sh \
#       > lab/runs/2026-11-14-goto-school/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-14-goto-school/run.sh     # 2 updates per arm, into smoke/
#
# Env: ARMS (the three below), N_UPDATES (6000, an upper bound on an arm's total updates;
# the deadline ends the night), DEADLINE (a `date -d` string, required outside SMOKE),
# ARM_THREADS (5 sim + 5 torch; three arms on 16 cores), GOTO_PAY (3.0), CRITIC_SETTLE (10).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-14-goto-school
LAST=lab/runs/2026-11-12-pilots-v8
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"followers_school followers_pay3 fighters_v8"}
ARM_THREADS=${ARM_THREADS:-5}
GOTO_PAY=${GOTO_PAY:-3.0}
CRITIC_SETTLE=${CRITIC_SETTLE:-10}

if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    DEADLINE=${DEADLINE:-"+20 minutes"}
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"07:20\"" >&2; exit 2; }
    RUN=$HERE
fi
deadline=$(date -d "$DEADLINE" +%s)

# Last night's run each arm continues.
arm_source() {
    case $1 in
        followers_school | followers_pay3) echo "$LAST/followers_v8" ;;
        fighters_v8) echo "$LAST/fighters_v8" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_fork() {  # The update last night's run ended on.
    latest_update "$(arm_source "$1")"
}
# What changes from last night's config (config.yaml keeps the rest).
PAY="--set goto_timed_bonus=$GOTO_PAY --set goto_miss_penalty=$GOTO_PAY"
SCHOOL='{"drill_share":0.7,"drill_weights":[6,1,1],"commander_p":0.667}'
arm_args() {
    case $1 in
        followers_school) echo "$PAY --set roster_overrides=$SCHOOL" ;;
        followers_pay3) echo "$PAY" ;;
        fighters_v8) echo "" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
latest_update() {  # The highest update with a checkpoint in run directory $1.
    local found
    found=$(find "$1/checkpoints" -name 'ppo_bc_*.pt' -printf '%f\n' \
        | sed 's/ppo_bc_\([0-9]*\)\.pt/\1/' | sort -n | tail -1)
    [[ -n $found ]] || { echo "no checkpoints in $1" >&2; exit 2; }
    echo "$found"
}

pids=()
for arm in $ARMS; do
    dir=$RUN/$arm
    if [[ ! -f $dir/config.yaml ]]; then
        source=$(arm_source "$arm")
        [[ -f $source/config.yaml ]] || { echo "missing $source/config.yaml" >&2; exit 2; }
        mkdir -p "$dir"
        cp -r "$source/config.yaml" "$source/log.jsonl" "$source/checkpoints" "$dir/"
        echo "$(date +%H:%M:%S) $arm starts as a copy of $source"
    fi
    n_updates=${N_UPDATES:-6000}
    [[ $SMOKE == 1 ]] && n_updates=$(( $(latest_update "$dir") + 2 ))
    # A deadline worth 3 changes what a go-to row is worth, so the critic gets
    # CRITIC_SETTLE updates past the fork before the actor moves (an absolute update,
    # so a later re-run does not freeze again).
    frozen_until=0
    [[ -n $(arm_args "$arm") ]] && frozen_until=$(( $(arm_fork "$arm") + CRITIC_SETTLE ))
    # shellcheck disable=SC2046
    "$PY" -m spacefight.train_spike ppo --run-dir "$dir" --resume --n-updates "$n_updates" \
        --set sim_threads="$ARM_THREADS" --set torch_threads="$ARM_THREADS" \
        --set actor_frozen_until="$frozen_until" \
        $(arm_args "$arm") >>"$RUN/$arm.out" 2>&1 &
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
