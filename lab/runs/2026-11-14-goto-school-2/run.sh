#!/usr/bin/env bash
# Go-to school, second night (plan.md). The first night taught squads to make a go-to
# deadline (drills in time 0.51 to 0.70) and left a ship alone where it was (0.12 in time
# at an allowance of 2). Two of its three arms also stopped early on a drill-generator
# fault, fixed since. Tonight:
#   followers_school  followers_school_600 on, unchanged: does it keep climbing
#   followers_solo    followers_school_600 on, 6 go-to drills in 10 forced to one ship
#                     alone (drill_goto_solo_share 0.6; with those drawn alone, 7 in 10)
#   fighters_pay1_school  fighters_pay1_v8_351 on, given what followers_school got on its
#                     first night: the school's drills (drill share 0.7, go-to weighted 6)
#                     and a deadline worth 3
# Each arm continues last night's run: its directory here starts as a copy of that run's
# (config, checkpoints with their optimiser state, and the log up to the last checkpoint),
# so update counts carry on. An arm that dies before the deadline is started again from
# its last checkpoint, up to MAX_RESTARTS times.
# Stops by SIGTERM at the deadline; each trainer checkpoints cleanly. Re-running resumes.
#
#   DEADLINE="tomorrow 06:30" nohup lab/runs/2026-11-14-goto-school-2/run.sh \
#       > lab/runs/2026-11-14-goto-school-2/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-14-goto-school-2/run.sh     # 2 updates per arm, into smoke/
#
# Env: ARMS (the three below), N_UPDATES (6000, an upper bound on an arm's total updates;
# the deadline ends the night), DEADLINE (a `date -d` string, required outside SMOKE),
# ARM_THREADS (5 sim + 5 torch; three arms on 16 cores), GOTO_PAY (3.0),
# CRITIC_SETTLE (10), MAX_RESTARTS (3).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-14-goto-school-2
LAST=lab/runs/2026-11-14-goto-school
FIRST=lab/runs/2026-11-12-pilots-v8
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"followers_school followers_solo fighters_pay1_school"}
ARM_THREADS=${ARM_THREADS:-5}
GOTO_PAY=${GOTO_PAY:-3.0}
CRITIC_SETTLE=${CRITIC_SETTLE:-10}
MAX_RESTARTS=${MAX_RESTARTS:-3}

if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    DEADLINE=${DEADLINE:-"+20 minutes"}
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"tomorrow 06:30\"" >&2; exit 2; }
    RUN=$HERE
fi
deadline=$(date -d "$DEADLINE" +%s)
# "06:30" said in the evening is this morning's: the night would end as it began.
(( deadline > $(date +%s) )) || { echo "DEADLINE $DEADLINE is already past; say \"tomorrow 06:30\"" >&2; exit 2; }

# The run each arm continues: last night's, or the first v8 night's.
arm_source() {
    case $1 in
        followers_school | followers_solo) echo "$LAST/followers_school" ;;
        fighters_pay1_school) echo "$FIRST/fighters_pay1_v8" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
# What changes from last night's config (config.yaml keeps the rest). The followers
# line's commander share is 0.667 of its matches, the fighters line's 0.333, as before.
SOLO='{"drill_share":0.7,"drill_weights":[6,1,1],"commander_p":0.667,"drill_goto_solo_share":0.6}'
SCHOOL='{"drill_share":0.7,"drill_weights":[6,1,1],"commander_p":0.333}'
PAY="--set goto_timed_bonus=$GOTO_PAY --set goto_miss_penalty=$GOTO_PAY"
arm_args() {
    case $1 in
        followers_school) echo "" ;;
        followers_solo) echo "--set roster_overrides=$SOLO" ;;
        fighters_pay1_school) echo "$PAY --set roster_overrides=$SCHOOL" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
# Updates the actor waits past the fork while the critic learns what a go-to row is
# worth now: only where the pay and the mix of rows change.
arm_settle() {
    case $1 in
        fighters_pay1_school) echo "$CRITIC_SETTLE" ;;
        *) echo 0 ;;
    esac
}
latest_update() {  # The highest update with a checkpoint in run directory $1.
    local found
    found=$(find "$1/checkpoints" -name 'ppo_bc_*.pt' -printf '%f\n' \
        | sed 's/ppo_bc_\([0-9]*\)\.pt/\1/' | sort -n | tail -1)
    [[ -n $found ]] || { echo "no checkpoints in $1" >&2; exit 2; }
    echo "$found"
}

declare -A frozen_until n_updates pid_of restarts
start_arm() {
    local arm=$1 dir=$RUN/$1
    # shellcheck disable=SC2046
    "$PY" -m spacefight.train_spike ppo --run-dir "$dir" --resume \
        --n-updates "${n_updates[$arm]}" \
        --set sim_threads="$ARM_THREADS" --set torch_threads="$ARM_THREADS" \
        --set actor_frozen_until="${frozen_until[$arm]}" \
        $(arm_args "$arm") >>"$RUN/$arm.out" 2>&1 &
    pid_of[$arm]=$!
    echo "$(date +%H:%M:%S) $arm pid ${pid_of[$arm]}"
}

for arm in $ARMS; do
    dir=$RUN/$arm
    if [[ ! -f $dir/config.yaml ]]; then
        source=$(arm_source "$arm")
        [[ -f $source/config.yaml ]] || { echo "missing $source/config.yaml" >&2; exit 2; }
        mkdir -p "$dir"
        cp -r "$source/config.yaml" "$source/checkpoints" "$dir/"
        # A run that died between checkpoints logged updates it will fly again.
        fork=$(latest_update "$source")
        "$PY" -c 'import json, sys
fork = int(sys.argv[1])
for line in open(sys.argv[2]):
    if json.loads(line)["update"] <= fork:
        sys.stdout.write(line)' "$fork" "$source/log.jsonl" >"$dir/log.jsonl"
        echo "$fork" >"$dir/fork_update"
        echo "$(date +%H:%M:%S) $arm starts as a copy of $source at update $fork"
    fi
    n_updates[$arm]=${N_UPDATES:-6000}
    [[ $SMOKE == 1 ]] && n_updates[$arm]=$(( $(latest_update "$dir") + 2 ))
    # An absolute update, so a restart or a later re-run does not freeze again.
    frozen_until[$arm]=0
    settle=$(arm_settle "$arm")
    (( settle > 0 )) && frozen_until[$arm]=$(( $(cat "$dir/fork_update") + settle ))
    restarts[$arm]=0
    start_arm "$arm"
done

# SIGTERM reaches every trainer, which checkpoints after its update.
stopping=0
stop() {
    stopping=1
    kill -TERM "${pid_of[@]}" 2>/dev/null || true
}
trap stop TERM INT
declare -A over
while (( $(date +%s) < deadline && ! stopping )); do
    alive=0
    for arm in $ARMS; do
        [[ -n ${over[$arm]:-} ]] && continue
        if kill -0 "${pid_of[$arm]}" 2>/dev/null; then
            alive=1
            continue
        fi
        # Finished (SMOKE, or N_UPDATES reached) or died: only a death is started again.
        status=0
        wait "${pid_of[$arm]}" || status=$?
        (( stopping )) && break
        if (( status != 0 && restarts[$arm] < MAX_RESTARTS && $(date +%s) < deadline - 600 )); then
            restarts[$arm]=$(( restarts[$arm] + 1 ))
            echo "$(date +%H:%M:%S) $arm died ($status); restart ${restarts[$arm]} from update $(latest_update "$RUN/$arm")"
            start_arm "$arm"
            alive=1
        else
            echo "$(date +%H:%M:%S) $arm over (exit $status)"
            over[$arm]=1
        fi
    done
    (( alive )) || break
    sleep 20 &
    wait $! || true
done
stop
wait || true
echo "$(date +%H:%M:%S) done: PPO"
