#!/usr/bin/env bash
# The third commander phase (plan.md, docs/COMMANDER.md): can a commander's orders be
# worth more than no orders? One PPO learner per arm, started fresh, pilots frozen and
# drawn ship by ship from the arm's pilot list, half its matches against the "unseen"
# side (the script's launches, no orders). Each trainer stops itself at the deadline (or
# on SIGTERM) with a checkpoint. Re-running resumes.
#
#   DEADLINE="tomorrow 07:00" nohup lab/runs/2026-11-15-commander-3/run.sh \
#       > lab/runs/2026-11-15-commander-3/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-15-commander-3/run.sh     # tiny sizes, into smoke/
#
# Env: ARMS ("followers followers_ent01 live"), N_ENVS (128), DEADLINE (a `date -d`
# string, required outside SMOKE; in the evening "07:30" is already past, say
# "tomorrow 07:00"), ARM_THREADS (5 sim + 5 torch).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-15-commander-3
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"followers followers_ent01 live"}
ARM_THREADS=${ARM_THREADS:-5}
FOLLOWERS=$HERE/pilots_followers.json
LIVE=lab/live_pilots.json
if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    DEADLINE=${DEADLINE:-"+3 minutes"}
    SIZE=(--smoke --set max_updates=3)
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"tomorrow 07:00\"" >&2; exit 2; }
    RUN=$HERE
    SIZE=(--set n_envs="${N_ENVS:-128}" --set decisions_per_update=8192
        --set minibatch=1024 --set snapshot_every=25 --set checkpoint_every=25)
fi
# A trainer handed a deadline already past saves an untrained commander and exits clean.
if (( $(date -d "$DEADLINE" +%s) <= $(date +%s) )); then
    echo "DEADLINE \"$DEADLINE\" is $(date -d "$DEADLINE" '+%F %H:%M'), already past" >&2
    exit 2
fi

# Every arm: last phase's sizes, shaping, seed and start (keep 4 times in 5), no price on
# orders, and the same enemies: unseen in half its matches, itself and its snapshots in
# the rest (shares: scripted, random, self, snapshots, unseen). They differ in the pilots
# that fly and in the entropy bonus (last phase's was 0.01).
ENEMIES="[0,0,0.25,0.25,0.5]"
arm_args() {
    case $1 in
        followers) echo "--set live_pilots=\"$FOLLOWERS\" --set ent_coef=0.002" ;;
        followers_ent01) echo "--set live_pilots=\"$FOLLOWERS\" --set ent_coef=0.01" ;;
        live) echo "--set live_pilots=\"$LIVE\" --set ent_coef=0.002" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}

pids=()
for arm in $ARMS; do
    dir=$RUN/$arm
    mkdir -p "$dir"
    resume=()
    [[ -f $dir/state.pt ]] && resume=(--resume)
    # shellcheck disable=SC2046
    OMP_NUM_THREADS=$ARM_THREADS "$PY" -m spacefight.commander.train --run-dir "$dir" \
        --deadline "$DEADLINE" "${resume[@]}" "${SIZE[@]}" \
        --set n_threads="$ARM_THREADS" --set torch_threads="$ARM_THREADS" \
        --set seed=0 --set shaping=0.5 --set keep_prior=0.8 --set order_price=0.0 \
        --set opponent_shares="$ENEMIES" \
        $(arm_args "$arm") > "$RUN/$arm.out" 2>&1 &
    pids+=($!)
    echo "$(date +%H:%M:%S) $arm pid $!"
done
status=0
for pid in "${pids[@]}"; do
    wait "$pid" || status=1
done
echo "$(date +%H:%M:%S) done: commanders (status $status)"
exit $status
