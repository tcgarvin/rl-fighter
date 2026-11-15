#!/usr/bin/env bash
# The morning after the third commander phase. Every arm's last checkpoint, flown over
# the pilots it trained with, against three sides: "unseen" (the script's launches and no
# orders: is the commander worth more than no commander?), random orders and the scripted
# commander. Then over the other pilot list against unseen, and the first arm against
# each of the others. The same seeds and sizes as before.sh, whose results in
# eval_before/ are the baselines. Re-running skips finished evals.
#
#   nohup nice -n 19 lab/runs/2026-11-15-commander-3/morning.sh \
#       > lab/runs/2026-11-15-commander-3/morning.out 2>&1 &
#
# Env: ARMS ("followers followers_ent01 live"), N (384 per mission), THREADS (8 per eval,
# two at a time), RUN (the run dir, e.g. smoke/ for a rehearsal).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-15-commander-3
RUN=${RUN:-$HERE}
PY=.venv/bin/python
ARMS=${ARMS:-"followers followers_ent01 live"}
N=${N:-384}
THREADS=${THREADS:-8}

latest() {
    local found
    found=$(find "$RUN/$1/checkpoints" -name 'commander_*.pt' -printf '%f\n' \
        | sed 's/commander_\([0-9]*\)\.pt/\1/' | sort -n | tail -1)
    [[ -n $found ]] || { echo "no checkpoints for $1" >&2; exit 2; }
    echo "$RUN/$1/checkpoints/commander_$found.pt"
}
pool_file() {
    case $1 in
        live) echo lab/live_pilots.json ;;
        followers) echo "$HERE/pilots_followers.json" ;;
        *) echo "unknown pool $1" >&2; exit 2 ;;
    esac
}
# The pilots an arm trained over, and the other list.
home_pool() { [[ $1 == live ]] && echo live || echo followers; }
away_pool() { [[ $1 == live ]] && echo followers || echo live; }

eval_pair() {  # pool name a b
    local out=$RUN/eval/$1/$2.json
    if [[ -f $out ]]; then
        echo "have $out"
        return
    fi
    mkdir -p "$(dirname "$out")"
    echo "$(date +%H:%M:%S) eval $1 $2"
    OMP_NUM_THREADS=$THREADS "$PY" -m spacefight.commander.eval --a "$3" --b "$4" \
        --pilots "$(pool_file "$1")" --n-per-mission "$N" --threads "$THREADS" \
        --out "$out" > "${out%.json}.out" 2>&1
}

declare -A ckpt
arms=($ARMS)
for arm in "${arms[@]}"; do
    ckpt[$arm]=$(latest "$arm")
    echo "$arm: ${ckpt[$arm]}"
done
# The order is the order of need: a morning cut short still has the first answers.
jobs=()
for arm in "${arms[@]}"; do
    jobs+=("$(home_pool "$arm") ${arm}_v_unseen ${ckpt[$arm]} unseen")
done
for arm in "${arms[@]}"; do
    jobs+=("$(home_pool "$arm") ${arm}_v_random ${ckpt[$arm]} random")
    jobs+=("$(home_pool "$arm") ${arm}_v_scripted ${ckpt[$arm]} scripted")
done
for arm in "${arms[@]}"; do
    jobs+=("$(away_pool "$arm") ${arm}_v_unseen ${ckpt[$arm]} unseen")
done
# The first arm is the main line: against each other arm, over both arms' pilots.
a=${arms[0]}
for b in "${arms[@]:1}"; do
    jobs+=("$(home_pool "$a") ${a}_v_${b} ${ckpt[$a]} ${ckpt[$b]}")
    if [[ $(home_pool "$a") != $(home_pool "$b") ]]; then
        jobs+=("$(home_pool "$b") ${a}_v_${b} ${ckpt[$a]} ${ckpt[$b]}")
    fi
done
running=0
status=0
for job in "${jobs[@]}"; do
    # shellcheck disable=SC2086
    eval_pair $job &
    running=$((running + 1))
    if ((running == 2)); then
        wait -n || status=1
        running=$((running - 1))
    fi
done
while ((running > 0)); do
    wait -n || status=1
    running=$((running - 1))
done
"$PY" "$HERE/summary.py" "$RUN/eval"
echo "$(date +%H:%M:%S) done: morning (status $status)"
exit $status
