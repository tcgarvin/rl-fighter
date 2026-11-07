#!/usr/bin/env bash
# The first commander phase (plan.md, docs/COMMANDER.md): one PPO learner per arm, pilots
# frozen and drawn ship by ship from lab/live_pilots.json. Each trainer stops itself at
# the deadline (or on SIGTERM) with a checkpoint. Re-running resumes.
#
#   DEADLINE="07:30" nohup lab/runs/2026-11-08-commander-1/run.sh \
#       > lab/runs/2026-11-08-commander-1/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-08-commander-1/run.sh     # tiny sizes, into smoke/
#
# Env: ARMS ("shaped shaped_s1 outcome"), N_ENVS (128), DEADLINE (a `date -d` string,
# required outside SMOKE), ARM_THREADS (4 sim + 4 torch).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-08-commander-1
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"shaped shaped_s1 outcome"}
ARM_THREADS=${ARM_THREADS:-4}
if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    DEADLINE=${DEADLINE:-"+3 minutes"}
    SIZE=(--smoke --set max_updates=3)
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"07:30\"" >&2; exit 2; }
    RUN=$HERE
    SIZE=(--set n_envs="${N_ENVS:-128}" --set decisions_per_update=8192
        --set minibatch=1024 --set snapshot_every=25 --set checkpoint_every=25)
fi

arm_args() {
    case $1 in
        shaped) echo "--set seed=0 --set shaping=0.5" ;;
        shaped_s1) echo "--set seed=1 --set shaping=0.5" ;;
        outcome) echo "--set seed=0 --set shaping=0.0" ;;
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
