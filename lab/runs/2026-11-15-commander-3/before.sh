#!/usr/bin/env bash
# Before the third commander phase: what is a commander worth over pilots that follow?
# Random orders, last phase's commanders and the first phase's c1_shaped, each against
# the scripted commander, twice on the same seeds: with every strike craft flown by the
# live ten (most of whom mostly ignore orders) and by the follower pool
# (pilots_followers.json). Then the controls the first pass asked for: "unseen" is the
# scripted commander with its orders hidden from its own pilots, so a side with no orders.
# Is the script better than no orders, are random orders, is last phase's best commander,
# and does that commander beat random orders directly? Re-running skips finished evals.
#
#   nohup nice -n 19 lab/runs/2026-11-15-commander-3/before.sh \
#       > lab/runs/2026-11-15-commander-3/before.out 2>&1 &
#
# Env: N (384 per mission), THREADS (8 per eval, two at a time), POOLS ("followers live";
# "ignorers" is pilots_ignorers.json, three pilots that mostly ignore orders, of which
# only unseen_v_scripted and random_v_unseen were run), ONLY (a regex of eval names).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-15-commander-3
PY=.venv/bin/python
N=${N:-384}
THREADS=${THREADS:-8}
POOLS=${POOLS:-"followers live"}
C1=lab/runs/2026-11-08-commander-1/shaped/checkpoints/commander_327.pt
HOLD=lab/runs/2026-11-10-commander-2/hold/checkpoints/commander_412.pt
PRICE5=lab/runs/2026-11-10-commander-2/price5/checkpoints/commander_417.pt

pool_file() {
    case $1 in
        live) echo lab/live_pilots.json ;;
        followers) echo "$HERE/pilots_followers.json" ;;
        ignorers) echo "$HERE/pilots_ignorers.json" ;;
        *) echo "unknown pool $1" >&2; exit 2 ;;
    esac
}
eval_pair() {  # pool name a b
    local out=$HERE/eval_before/$1/$2.json
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

jobs=()
for pool in $POOLS; do
    jobs+=("$pool random_v_scripted random scripted")
    jobs+=("$pool price5_v_scripted $PRICE5 scripted")
    jobs+=("$pool hold_v_scripted $HOLD scripted")
    jobs+=("$pool c1_shaped_v_scripted $C1 scripted")
done
for pool in $POOLS; do
    jobs+=("$pool unseen_v_scripted unseen scripted")
done
for pool in $POOLS; do
    jobs+=("$pool price5_v_unseen $PRICE5 unseen")
    jobs+=("$pool random_v_unseen random unseen")
    jobs+=("$pool price5_v_random $PRICE5 random")
done
running=0
status=0
for job in "${jobs[@]}"; do
    [[ $(cut -d' ' -f2 <<< "$job") =~ ^(${ONLY:-.*})$ ]] || continue
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
"$PY" - "$HERE/eval_before" <<'PYEOF'
import json, sys
from pathlib import Path


def orders(o):
    if not o["orders_ended"]:
        return "no orders ended"
    return (
        f"{o['orders_per_ship_min']:.1f}/ship-min, median {o['order_seconds_median']:.1f} s, "
        f"ordered {o['ordered_share']:.0%}"
    )


for pool in sorted(Path(sys.argv[1]).iterdir()):
    print(f"pilots: {pool.name}")
    for f in sorted(pool.glob("*.json")):
        d = json.loads(f.read_text())
        n = sum(m["n"] for m in d["missions"].values())
        per = " ".join(f"{k[:7]} {v['score_a']:.2f}" for k, v in d["missions"].items())
        print(f"{d['a']:>24} v {d['b']:<10} {d['score_a']:.3f} over {n}  ({per})")
        print(f"{'':>24}   a orders: {orders(d['orders_a'])}")
        print(f"{'':>24}   b orders: {orders(d['orders_b'])}")
PYEOF
echo "$(date +%H:%M:%S) done: before (status $status)"
exit $status
