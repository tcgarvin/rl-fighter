#!/usr/bin/env bash
# The long commander run (plan.md): one learner on the trainer's defaults, for days,
# building on the best general commander so far (commander 3's `live` 197: its actor; the
# critic starts new). All four missions, the live ten as pilots, no prior, nothing
# forbidden; besides the start, only the sizes and threads are set, for the machine. Stops itself at DEADLINE (or on SIGTERM) with a
# checkpoint; re-running resumes. Low priority, so pilot runs, evals and WAR come first.
#
#   DEADLINE="2026-11-28 12:00" nohup setsid lab/runs/2026-11-21-commander-long/run.sh \
#       > lab/runs/2026-11-21-commander-long/run.out 2>&1 &
#
# Env: DEADLINE (required, a `date -d` string), THREADS (5 sim + 5 torch), N_ENVS (128).
# To change anything mid-run, stop it (SIGTERM), copy this file, and start the copy: never
# edit this file while it runs (bash reads a running script as it goes).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
DIR=lab/runs/2026-11-21-commander-long/learner
INIT=lab/runs/2026-11-15-commander-3/live/checkpoints/commander_197.pt
THREADS=${THREADS:-5}
[[ -f $INIT ]] || { echo "missing $INIT" >&2; exit 2; }
[[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"2026-11-28 12:00\"" >&2; exit 2; }
mkdir -p "$DIR"
resume=()
[[ -f $DIR/state.pt ]] && resume=(--resume)
OMP_NUM_THREADS=$THREADS exec nice -n 10 .venv/bin/python -m spacefight.commander.train \
    --run-dir "$DIR" --deadline "$DEADLINE" "${resume[@]}" \
    --set init=\""$INIT"\" \
    --set n_envs="${N_ENVS:-128}" --set n_threads="$THREADS" --set torch_threads="$THREADS" \
    > "$DIR.out" 2>&1
