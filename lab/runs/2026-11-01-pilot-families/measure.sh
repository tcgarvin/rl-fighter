#!/usr/bin/env bash
# Before the first night (plan.md steps 1 and 2): drills on the script and founders, to set
# the bars, then the round robin across existing pilots. Needs the machine. Re-running skips
# finished drill evals and finished round-robin pairs.
#
#   nohup lab/runs/2026-11-01-pilot-families/measure.sh \
#       > lab/runs/2026-11-01-pilot-families/measure.out 2>&1 &
#
# Env: THREADS (8), N_DRILLS (256 per kind), N_PER_MISSION (240), DEATHMATCH_ROSTERS (24).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-01-pilot-families
PY=.venv/bin/python
SEASON=lab/population/2026-11-sim6
THREADS=${THREADS:-8}
N_DRILLS=${N_DRILLS:-256}
N_PER_MISSION=${N_PER_MISSION:-240}
DEATHMATCH_ROSTERS=${DEATHMATCH_ROSTERS:-24}
MAIN=/home/timg/code/rl-fighter
export OMP_NUM_THREADS=$THREADS

drills() {
    local name=$1 checkpoint=$2 out=$HERE/eval/drills_$1.json
    [[ -f $out ]] && { echo "have $out"; return; }
    echo "$(date +%H:%M:%S) drills: $name"
    "$PY" -m spacefight.eval.drills --a "$checkpoint" --name "$name" \
        --n-per-kind "$N_DRILLS" --threads "$THREADS" --out "$out"
}

mkdir -p "$HERE/eval"
drills script script
drills f995_701 "$MAIN/lab/runs/2026-11-01-fighters-v2/f995/checkpoints/ppo_bc_701.pt"
drills transit_300 "$MAIN/lab/runs/2026-11-01-order-pilot-b3/transit/checkpoints/ppo_bc_300.pt"
drills reward_300 "$MAIN/lab/runs/2026-11-01-order-pilot-b3/reward/checkpoints/ppo_bc_300.pt"
drills hide_644 "$MAIN/lab/runs/2026-11-01-fighters-v2/hide/checkpoints/ppo_bc_644.pt"

echo "$(date +%H:%M:%S) round robin"
"$PY" -m spacefight.population round-robin --season "$SEASON" \
    --out "$SEASON/round_robin/existing-pilots" \
    --members script,f995_701,f995_400,f99_696,reward_300,transit_300,hide_644,v1,w1_400 \
    --n-per-mission "$N_PER_MISSION" --deathmatch-rosters "$DEATHMATCH_ROSTERS" \
    --n-threads "$THREADS"
"$PY" -m spacefight.population report --season "$SEASON" \
    --results "$SEASON/round_robin/existing-pilots" \
    --phase existing-pilots --date "$(date +%F)"
echo "$(date +%H:%M:%S) done: measure"
