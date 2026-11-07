#!/usr/bin/env bash
# The morning after a night of pilot families (plan.md step 5): drill evals on each arm's
# latest checkpoint, the members' records and drill results, a round robin seeded with the
# previous phase's pairs (only new pairs are played), and the report with shadow culls.
# It archives nothing: who is archived for failing the gate is decided when reading the
# report. Re-running skips finished drill evals, members, drill records and pairs.
#
#   PHASE=second-night nohup lab/runs/2026-11-01-pilot-families/morning.sh \
#       > lab/runs/2026-11-01-pilot-families/morning.out 2>&1 &
#
# Env: PHASE (required), PREV (first-night; empty starts the round robin afresh), DATE
# (today), ARMS (fighters followers fighters_pay1), THREADS (12), N_DRILLS (256 per kind),
# N_PER_MISSION (240), DEATHMATCH_ROSTERS (24). The sizes must match PREV's config.json for
# its pairs to count. For a rehearsal: RUN (the run dir, e.g. its smoke/), SEASON (a copy
# of the season), MEMBERS (PREV's members, which tonight's arms join).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=${RUN:-lab/runs/2026-11-01-pilot-families}
PY=.venv/bin/python
SEASON=${SEASON:-lab/population/2026-11-sim6}
PHASE=${PHASE:?set PHASE, e.g. PHASE=second-night}
PREV=${PREV-first-night}
DATE=${DATE:-$(date +%F)}
ARMS=${ARMS:-"fighters followers fighters_pay1"}
THREADS=${THREADS:-12}
N_DRILLS=${N_DRILLS:-256}
N_PER_MISSION=${N_PER_MISSION:-240}
DEATHMATCH_ROSTERS=${DEATHMATCH_ROSTERS:-24}
export OMP_NUM_THREADS=$THREADS
# The members of PREV's round robin; tonight's arms join them.
FIRST_NIGHT=script,f995_701,f995_400,f99_696,fighters_506,followers_513,hide_644
FIRST_NIGHT=$FIRST_NIGHT,reward_300,scratch_417,transit_300,v1,w1_400
MEMBERS=${MEMBERS:-$FIRST_NIGHT}

latest_update() {
    local found
    found=$(find "$HERE/$1/checkpoints" -name 'ppo_bc_*.pt' -printf '%f\n' \
        | sed 's/ppo_bc_\([0-9]*\)\.pt/\1/' | sort -n | tail -1)
    [[ -n $found ]] || { echo "no checkpoints for $1" >&2; exit 2; }
    echo "$found"
}

# Parent, its update at the fork, and the settings changed from it, per arm.
arm_parent() {
    case $1 in
        fighters) echo "fighters_506 506" ;;
        followers) echo "followers_513 513" ;;
        fighters_pay1) echo "f995_701 701" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_settings() {
    local added='"pool_seed_added":["fighters_506","followers_513"]'
    case $1 in
        fighters) echo "{\"drill_share\":0.25,$added}" ;;
        followers) echo "{$added}" ;;
        fighters_pay1) echo '{"rosters":"pilots_v1","gamma":0.995,"lr_decay":false,"beta_start":0.0,"beta_end":0.0,"order_reward_weight":1.0,"drill_share":0.1,"commander_p":0.333,"enemy_sampling":"pfsp"}' ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_note() {
    case $1 in
        fighters) echo "Night 2: fighters_506's line continued with drills 0.25." ;;
        followers) echo "Night 2: followers_513's line continued, the first night's two in the pool." ;;
        fighters_pay1) echo "Night 2: night 1's fighters replayed at order pay 1." ;;
    esac
}

drilled() {  # Has member $1 a drill record for PHASE?
    "$PY" -c 'import json, sys
m = json.load(open(sys.argv[1]))
sys.exit(0 if any(d["phase"] == sys.argv[2] for d in m["drills"]) else 1)' \
        "$SEASON/members/$1.json" "$PHASE"
}

mkdir -p "$HERE/eval"
new_ids=()
for arm in $ARMS; do
    update=$(latest_update "$arm")
    id=${arm}_${update}
    checkpoint=$HERE/$arm/checkpoints/ppo_bc_${update}.pt
    new_ids+=("$id")
    out=$HERE/eval/drills_$id.json
    if [[ -f $out ]]; then
        echo "have $out"
    else
        echo "$(date +%H:%M:%S) drills: $id"
        "$PY" -m spacefight.eval.drills --a "$checkpoint" --name "$id" \
            --n-per-kind "$N_DRILLS" --threads "$THREADS" --out "$out"
    fi
    if [[ -f $SEASON/members/$id.json ]]; then
        echo "have member $id"
    else
        read -r parent fork_update <<<"$(arm_parent "$arm")"
        "$PY" -m spacefight.population add-child --season "$SEASON" --id "$id" \
            --parent "$parent" --fork-update "$fork_update" --checkpoint "$checkpoint" \
            --settings "$(arm_settings "$arm")" --note "$(arm_note "$arm")"
    fi
    if drilled "$id"; then
        echo "have drills for $id in $PHASE"
    else
        "$PY" -m spacefight.population record-drills --season "$SEASON" --id "$id" \
            --drills "$out" --phase "$PHASE" --date "$DATE"
    fi
done

results=$SEASON/round_robin/$PHASE
if [[ ! -d $results && -n $PREV ]]; then
    mkdir -p "$results/pairs"
    cp "$SEASON/round_robin/$PREV/config.json" "$results/"
    cp "$SEASON/round_robin/$PREV/pairs/"*.json "$results/pairs/"
fi
members=$MEMBERS$(printf ',%s' "${new_ids[@]}")
echo "$(date +%H:%M:%S) round robin: $members"
"$PY" -m spacefight.population round-robin --season "$SEASON" --out "$results" \
    --members "$members" --n-per-mission "$N_PER_MISSION" \
    --deathmatch-rosters "$DEATHMATCH_ROSTERS" --n-threads "$THREADS"

if [[ -f $results/.recorded ]]; then
    echo "ratings for $PHASE already recorded"
else
    "$PY" -m spacefight.population report --season "$SEASON" --results "$results" \
        --phase "$PHASE" --date "$DATE" --record
    touch "$results/.recorded"
fi
echo "$(date +%H:%M:%S) done: morning"
