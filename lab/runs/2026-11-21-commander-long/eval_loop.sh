#!/usr/bin/env bash
# The long run's curve (plan.md): every EVERY updates, the learner's checkpoint against
# the side with no orders ("unseen"), all four missions, over the live ten, at low
# priority. One eval at a time; finished ones are kept, so a restart picks up where it
# stopped; one that fails is marked .failed and skipped. Runs until the trainer has
# exited and every checkpoint due is measured, so start it after the trainer.
#
#   nohup setsid lab/runs/2026-11-21-commander-long/eval_loop.sh \
#       > lab/runs/2026-11-21-commander-long/eval_loop.out 2>&1 &
#
# Env: EVERY (100), N_PER_MISSION (192), THREADS (2), PY.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-21-commander-long
PY=${PY:-.venv/bin/python}
EVERY=${EVERY:-100}
N_PER_MISSION=${N_PER_MISSION:-192}
THREADS=${THREADS:-2}
mkdir -p "$HERE/eval"

trainer_running() {
    # grep -c reads all of ps's output. With grep -q it closed the pipe at the first
    # match, ps died of SIGPIPE and pipefail called a running trainer stopped: the loop
    # ended at 16:50 on 2026-11-21 with the trainer still running.
    ps -eo args | grep -v grep \
        | grep -c "commander.train --run-dir $HERE/learner" > /dev/null
}
due() {  # Checkpoints at multiples of EVERY not yet measured, oldest first.
    find "$HERE/learner/checkpoints" -name 'commander_*.pt' -printf '%f\n' 2>/dev/null \
        | sed 's/^commander_//; s/\.pt$//' | sort -n | while read -r u; do
            if (( u % EVERY == 0 )) && [[ ! -f $HERE/eval/unseen_$u.json ]] \
                && [[ ! -f $HERE/eval/unseen_$u.failed ]]; then echo "$u"; fi
        done
}

while true; do
    next=$(due | head -n 1 || true)  # head closing the pipe early is not an error
    if [[ -z $next ]]; then
        trainer_running || break
        sleep 600
        continue
    fi
    out=$HERE/eval/unseen_$next.json
    echo "$(date '+%F %H:%M') eval $next"
    if nice -n 19 "$PY" -m spacefight.commander.eval \
        --a "$HERE/learner/checkpoints/commander_$next.pt" --b unseen \
        --n-per-mission "$N_PER_MISSION" --threads "$THREADS" \
        --out "$out.tmp" > "$HERE/eval/unseen_$next.md" 2>&1; then
        mv "$out.tmp" "$out"
    else
        # Marked, so the loop moves on; the .md holds the error.
        echo "$(date '+%F %H:%M') eval $next FAILED (see eval/unseen_$next.md)"
        touch "$HERE/eval/unseen_$next.failed"
    fi
done
echo "$(date '+%F %H:%M') done: trainer exited, every checkpoint due measured"
