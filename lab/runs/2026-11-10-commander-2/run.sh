#!/usr/bin/env bash
# The second commander phase (plan.md, docs/COMMANDER.md): orders that last. One PPO
# learner per arm, started fresh under the 5-second order hold, pilots frozen and drawn
# ship by ship from lab/live_pilots.json. Each trainer stops itself at the deadline (or
# on SIGTERM) with a checkpoint. Re-running resumes.
#
#   DEADLINE="08:00" nohup lab/runs/2026-11-10-commander-2/run.sh \
#       > lab/runs/2026-11-10-commander-2/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-10-commander-2/run.sh     # tiny sizes, into smoke/
#
# Env: ARMS ("hold price2 price5"), N_ENVS (128), DEADLINE (a `date -d` string,
# required outside SMOKE), ARM_THREADS (4 sim + 4 torch).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-10-commander-2
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"hold price2 price5"}
ARM_THREADS=${ARM_THREADS:-4}
if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    DEADLINE=${DEADLINE:-"+3 minutes"}
    SIZE=(--smoke --set max_updates=3)
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"08:00\"" >&2; exit 2; }
    RUN=$HERE
    SIZE=(--set n_envs="${N_ENVS:-128}" --set decisions_per_update=8192
        --set minibatch=1024 --set snapshot_every=25 --set checkpoint_every=25)
fi

# Every arm: the design's shaping, the same seed, a start that keeps 4 times in 5.
# They differ only in the price of an order (per ship whose order a decision changes).
arm_args() {
    case $1 in
        hold) echo "--set order_price=0.0" ;;
        price2) echo "--set order_price=0.002" ;;
        price5) echo "--set order_price=0.005" ;;
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
        --set seed=0 --set shaping=0.5 --set keep_prior=0.8 \
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
