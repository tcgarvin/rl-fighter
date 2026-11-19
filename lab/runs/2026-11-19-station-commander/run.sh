#!/usr/bin/env bash
# Station commander (plan.md): can a learned commander find what the hand rules found in
# the station assault (launch timing, the carrier's push)? One PPO learner per arm, every
# match a station assault (half read as a carrier battle, half as a convoy escort), the
# learner on either side, against the "unseen" side (the script, orders hidden from its
# pilots) in 3 matches of 4 and the script in 1. Pilots frozen, drawn ship by ship from
# the live ten. Each trainer stops itself at the deadline (or on SIGTERM to it or to this
# script) with a checkpoint; a trainer that dies early is restarted with --resume (up to
# RESTARTS times). Re-running resumes.
#
#   DEADLINE="2026-11-19 13:30" nohup setsid lab/runs/2026-11-19-station-commander/run.sh \
#       > lab/runs/2026-11-19-station-commander/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-19-station-commander/run.sh     # tiny sizes, into smoke/
#
# Env: ARMS ("fresh from_c3"), N_ENVS (128), DEADLINE (a `date -d` string, required
# outside SMOKE), ARM_THREADS (6: 6 sim + 6 torch threads an arm; they take turns, so
# about 6 cores an arm), RESTARTS (3), PY (the main checkout's venv: a worktree has
# none), PILOT_ROOT (the checkout holding the pilots' weights).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-19-station-commander
PY=${PY:-/home/timg/code/rl-fighter/.venv/bin/python}
PILOT_ROOT=${PILOT_ROOT:-/home/timg/code/rl-fighter}
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"fresh from_c3"}
ARM_THREADS=${ARM_THREADS:-6}
RESTARTS=${RESTARTS:-3}
LIVE=lab/live_pilots.json
# from_c3: commander 3's `live` line (update 197), trained over the live ten against the
# unseen side, where it ended level (0.49) by giving almost no orders (plan.md).
C3_LIVE=${C3_LIVE:-$PILOT_ROOT/lab/runs/2026-11-15-commander-3/live/checkpoints/commander_197.pt}

# The trainer must be this checkout's (the venv may also see the main checkout's).
src=$("$PY" -c 'import spacefight, sys; sys.stdout.write(spacefight.__file__)')
[[ $src == "$ROOT"/* ]] || { echo "spacefight comes from $src, not $ROOT" >&2; exit 2; }

if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    DEADLINE=${DEADLINE:-"+4 minutes"}
    SIZE=(--smoke --set max_updates=3)
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"2026-11-19 13:30\"" >&2; exit 2; }
    RUN=$HERE
    SIZE=(--set n_envs="${N_ENVS:-128}" --set decisions_per_update=8192
        --set minibatch=1024 --set snapshot_every=25 --set checkpoint_every=10)
fi
deadline_at=$(date -d "$DEADLINE" +%s)
# A trainer handed a deadline already past saves an untrained commander and exits clean.
if (( deadline_at <= $(date +%s) )); then
    echo "DEADLINE \"$DEADLINE\" is $(date -d "@$deadline_at" '+%F %H:%M'), already past" >&2
    exit 2
fi
DEADLINE_ABS="@$deadline_at"

# Every arm: station assault only, half of it read as a convoy; enemies (shares:
# scripted, random, self, snapshots, unseen) the unseen side 3 in 4, the script 1 in 4;
# commander 3's shaping, seed, entropy bonus (0.002) and price (none). The arms differ
# in where the actor starts.
ENEMIES="[0.25,0,0,0,0.75]"
arm_args() {
    case $1 in
        fresh) echo "--set keep_prior=0.8" ;;
        from_c3) echo "--set init=\"$C3_LIVE\"" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}

# run_arm <arm>: the trainer, restarted with --resume if it dies before the deadline.
run_arm() {
    local arm=$1 dir=$RUN/$1 tries=0 status
    mkdir -p "$dir"
    while :; do
        local resume=()
        [[ -f $dir/state.pt ]] && resume=(--resume)
        # shellcheck disable=SC2046
        OMP_NUM_THREADS=$ARM_THREADS "$PY" -m spacefight.commander.train --run-dir "$dir" \
            --deadline "$DEADLINE_ABS" "${resume[@]}" "${SIZE[@]}" \
            --set n_threads="$ARM_THREADS" --set torch_threads="$ARM_THREADS" \
            --set seed=0 --set shaping=0.5 --set order_price=0.0 --set ent_coef=0.002 \
            --set opponent_shares="$ENEMIES" --set mission_weights="[0,0,0,1]" \
            --set station_convoy_share=0.5 --set live_pilots="\"$LIVE\"" \
            --set pilot_root="\"$PILOT_ROOT\"" \
            $(arm_args "$arm") >> "$RUN/$arm.out" 2>&1 &
        local pid=$!
        echo "$pid" > "$RUN/$arm.pid"
        echo "$(date +%H:%M:%S) $arm pid $pid${resume:+ (resume)}"
        status=0
        wait "$pid" || status=$?
        # A wait cut short by our own TERM trap: wait for the trainer's checkpoint.
        while kill -0 "$pid" 2>/dev/null; do wait "$pid" || status=$?; done
        if (( status == 0 )) || [[ -f $RUN/.stop ]] || (( $(date +%s) >= deadline_at )); then
            echo "$(date +%H:%M:%S) $arm ended (status $status)"
            return "$status"
        fi
        tries=$((tries + 1))
        if (( tries > RESTARTS )); then
            echo "$(date +%H:%M:%S) $arm failed $tries times, giving up (status $status)"
            return "$status"
        fi
        echo "$(date +%H:%M:%S) $arm died (status $status), restart $tries of $RESTARTS"
        sleep 20
    done
}

rm -f "$RUN/.stop"
mkdir -p "$RUN"
# SIGTERM/SIGINT here: no restarts, and each trainer stops after its current update with
# a checkpoint.
stop() {
    touch "$RUN/.stop"
    for arm in $ARMS; do
        [[ -f $RUN/$arm.pid ]] && kill -TERM "$(cat "$RUN/$arm.pid")" 2>/dev/null || true
    done
}
trap stop TERM INT

pids=()
for arm in $ARMS; do
    run_arm "$arm" &
    pids+=($!)
done
status=0
for pid in "${pids[@]}"; do
    while :; do
        wait "$pid" && break
        rc=$?
        kill -0 "$pid" 2>/dev/null && continue  # the wait was cut short by the trap
        status=$rc
        break
    done
done
echo "$(date +%H:%M:%S) done: station commanders (status $status)"
exit $status
