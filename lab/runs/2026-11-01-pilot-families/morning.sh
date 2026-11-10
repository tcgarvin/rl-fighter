#!/usr/bin/env bash
# The morning after a night of pilot families: drill evals on each arm's latest
# checkpoint (a report; the gate archives nobody since 2026-11-08), the members' records and
# drill results, then wins above replacement (WAR) in live-like matches for every pilot the
# live page can pick plus tonight's three, and the report with WAR shadow culls. It
# archives nothing. Re-running skips finished drill evals, members, drill records and WAR
# chunks. Nights 1 and 2 played a round robin here instead (see git history).
# Night 4 (the price of a shot) adds a shooting eval before WAR: each new pilot against its
# parent in carrier battles and convoys, both sides in the same matches, for hit rate, shots
# and trigger share by hull (eval/shooting_<id>.{json,md}).
#
#   PHASE=third-night nohup lab/runs/2026-11-01-pilot-families/morning.sh \
#       > lab/runs/2026-11-01-pilot-families/morning.out 2>&1 &
#
# Env: PHASE (required), DATE (today), ARMS (fighters followers fighters_pay1), THREADS (14), N_DRILLS (256 per kind), N_SHOOTING (516 per mission),
# N_PER_MISSION (1440, WAR; about +-3 wins per 100),
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
N_SHOOTING=${N_SHOOTING:-516}  # carrier battles come in blocks of 6
N_PER_MISSION=${N_PER_MISSION:-1440}
export OMP_NUM_THREADS=$THREADS
# The ten live pilots (lab/live_pilots.json after night 3) and transit_300; tonight's arms
# join them.
RATED=f99_696,f995_701,f995_400,fighters_pay1_462,fighters_1338,followers_1323
RATED=$RATED,fighters_pay1_849,fighters_506,fighters_959,followers_955,transit_300
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
        fighters | fighters_fire4) echo "fighters_1338 1338" ;;
        followers) echo "followers_1323 1323" ;;
        fighters_pay1) echo "fighters_pay1_849 849" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_settings() {
    # Night 4 changes only the price of a shot (extra_fire_cost, on top of the sim's 0.002).
    case $1 in
        fighters | followers | fighters_pay1) echo '{"extra_fire_cost":0.002}' ;;
        fighters_fire4) echo '{"extra_fire_cost":0.006}' ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_note() {
    case $1 in
        fighters) echo "Night 4: fighters_1338's line with each shot costing twice as much." ;;
        fighters_fire4) echo "Night 4: a copy of fighters_1338's line with each shot costing four times as much." ;;
        followers) echo "Night 4: followers_1323's line with each shot costing twice as much." ;;
        fighters_pay1) echo "Night 4: fighters_pay1_849's line with each shot costing twice as much." ;;
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

member_checkpoint() {  # The checkpoint path in member $1's season record.
    "$PY" -c 'import json, sys
print(json.load(open(sys.argv[1]))["checkpoint"])' "$SEASON/members/$1.json"
}

# Shooting: each new pilot (a) against its parent (b), in the same matches.
for arm in $ARMS; do
    update=$(latest_update "$arm")
    id=${arm}_${update}
    read -r parent _ <<<"$(arm_parent "$arm")"
    out=$HERE/eval/shooting_$id
    if [[ -f $out.json ]]; then
        echo "have $out.json"
    else
        echo "$(date +%H:%M:%S) shooting: $id vs $parent"
        "$PY" -m spacefight.eval.missions --a "$HERE/$arm/checkpoints/ppo_bc_${update}.pt" \
            --b "$(member_checkpoint "$parent")" \
            --n-per-mission "$N_SHOOTING" --n-threads "$THREADS" --out "$out.json" >"$out.md"
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
