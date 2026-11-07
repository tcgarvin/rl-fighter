#!/usr/bin/env bash
# The morning after the first commander phase: every arm's last checkpoint against the
# scripted commander, the random-orders commander against the scripted one (how much
# orders matter with these pilots), and the arms against each other. Matches as on the
# live page: pilots drawn ship by ship from lab/live_pilots.json, missions in turn.
# Re-running skips finished evals.
#
#   nohup lab/runs/2026-11-08-commander-1/morning.sh > lab/runs/2026-11-08-commander-1/morning.out 2>&1 &
#
# Env: ARMS ("shaped shaped_s1 outcome"), N (192 per mission), THREADS (8 per eval, two
# at a time), RUN (the run dir, e.g. smoke/ for a rehearsal).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-08-commander-1
RUN=${RUN:-$HERE}
PY=.venv/bin/python
ARMS=${ARMS:-"shaped shaped_s1 outcome"}
N=${N:-192}
THREADS=${THREADS:-8}
mkdir -p "$RUN/eval"

latest() {
    local found
    found=$(find "$RUN/$1/checkpoints" -name 'commander_*.pt' -printf '%f\n' \
        | sed 's/commander_\([0-9]*\)\.pt/\1/' | sort -n | tail -1)
    [[ -n $found ]] || { echo "no checkpoints for $1" >&2; exit 2; }
    echo "$RUN/$1/checkpoints/commander_$found.pt"
}

eval_pair() {  # name a b
    local out=$RUN/eval/$1.json
    if [[ -f $out ]]; then
        echo "have $out"
        return
    fi
    echo "$(date +%H:%M:%S) eval $1"
    OMP_NUM_THREADS=$THREADS "$PY" -m spacefight.commander.eval --a "$2" --b "$3" \
        --n-per-mission "$N" --threads "$THREADS" --out "$out" > "$RUN/eval/$1.out" 2>&1
}

declare -A ckpt
jobs=()
for arm in $ARMS; do
    ckpt[$arm]=$(latest "$arm")
    jobs+=("${arm}_v_scripted ${ckpt[$arm]} scripted")
done
jobs+=("random_v_scripted random scripted")
arms=($ARMS)
for ((i = 0; i < ${#arms[@]}; i++)); do
    for ((j = i + 1; j < ${#arms[@]}; j++)); do
        jobs+=("${arms[i]}_v_${arms[j]} ${ckpt[${arms[i]}]} ${ckpt[${arms[j]}]}")
    done
done
running=0
for job in "${jobs[@]}"; do
    # shellcheck disable=SC2086
    eval_pair $job &
    running=$((running + 1))
    if ((running == 2)); then
        wait -n
        running=$((running - 1))
    fi
done
wait
"$PY" - "$RUN/eval" <<'PYEOF'
import json, sys
from pathlib import Path
for f in sorted(Path(sys.argv[1]).glob("*.json")):
    d = json.loads(f.read_text())
    per = " ".join(f"{k[:7]} {v['score_a']:.2f}" for k, v in d["missions"].items())
    print(f"{d['a']:>24} v {d['b']:<24} {d['score_a']:.3f}  ({per})")
PYEOF
echo "$(date +%H:%M:%S) done: morning"
