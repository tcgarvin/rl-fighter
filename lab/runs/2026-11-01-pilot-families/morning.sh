#!/usr/bin/env bash
# The morning after a night of pilot families: drill evals on each arm's latest
# checkpoint (a report; the gate archives nobody since 2026-11-08), the members' records and
# drill results, then wins above replacement (WAR) in live-like matches for every pilot the
# live page can pick plus tonight's three, and the report with WAR shadow culls. It
# archives nothing. Re-running skips finished drill evals, members, drill records and WAR
# chunks. Nights 1 and 2 played a round robin here instead (see git history).
#
#   PHASE=third-night nohup lab/runs/2026-11-01-pilot-families/morning.sh \
#       > lab/runs/2026-11-01-pilot-families/morning.out 2>&1 &
#
# Env: PHASE (required), DATE (today), ARMS (fighters followers fighters_pay1), THREADS
# (14), N_DRILLS (256 per kind), N_PER_MISSION (1440, WAR; about +-3 wins per 100),
# MEMBERS (the pilots already rated; tonight's arms join them). For a rehearsal: RUN (the
# run dir, e.g. its smoke/), SEASON (a copy of the season).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=${RUN:-lab/runs/2026-11-01-pilot-families}
PY=.venv/bin/python
SEASON=${SEASON:-lab/population/2026-11-sim6}
PHASE=${PHASE:?set PHASE, e.g. PHASE=second-night}
DATE=${DATE:-$(date +%F)}
ARMS=${ARMS:-"fighters followers fighters_pay1"}
THREADS=${THREADS:-14}
N_DRILLS=${N_DRILLS:-256}
N_PER_MISSION=${N_PER_MISSION:-1440}
export OMP_NUM_THREADS=$THREADS
# The ten live pilots and transit_300 (WAR 2026-11-08-live-eleven); tonight's arms join them.
RATED=f995_701,fighters_506,fighters_959,fighters_pay1_462,followers_513,followers_955
RATED=$RATED,transit_300,f99_696,f995_400,hide_644,reward_300
MEMBERS=${MEMBERS:-$RATED}

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
        fighters) echo "fighters_959 959" ;;
        followers) echo "followers_955 955" ;;
        fighters_pay1) echo "fighters_pay1_462 462" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_settings() {
    local added='"pool_seed_added":["fighters_959","followers_955","fighters_pay1_462","f99_696"],"commander_stable":["live"]'
    case $1 in
        fighters) echo "{\"drill_share\":0.35,\"drill_weights\":[2,1,1],$added}" ;;
        followers) echo "{\"drill_share\":0.35,\"drill_weights\":[3,1,1],$added}" ;;
        fighters_pay1) echo "{\"drill_share\":0.25,\"drill_weights\":[2,1,1],$added}" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_note() {
    case $1 in
        fighters) echo "Night 3: fighters_959's line under the learned commanders, drills 0.35 weighted to go-to." ;;
        followers) echo "Night 3: followers_955's line under the learned commanders, drills 0.35, go-to three times the others." ;;
        fighters_pay1) echo "Night 3: fighters_pay1_462's line under the learned commanders, drills 0.25 weighted to go-to." ;;
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

war=$SEASON/war/$PHASE
members=$MEMBERS$(printf ',%s' "${new_ids[@]}")
echo "$(date +%H:%M:%S) WAR: $members"
"$PY" -m spacefight.population war --season "$SEASON" --out "$war" \
    --members "$members" --commanders live --n-per-mission "$N_PER_MISSION" \
    --threads "$THREADS"
"$PY" -m spacefight.population report --season "$SEASON" --war "$war/war.json" \
    --phase "$PHASE" --date "$DATE"
echo "$(date +%H:%M:%S) done: morning"
