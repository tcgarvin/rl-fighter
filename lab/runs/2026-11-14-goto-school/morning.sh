#!/usr/bin/env bash
# The morning after go-to school (plan.md): for each arm's latest checkpoint the drill eval,
# its member record, the deadline sweep (also with its deadline inputs zeroed, nodeadline:),
# the shooting eval against its parent, then wins above replacement for the live ten, the
# parents and tonight's three, and the report. It archives and publishes nothing.
# Re-running skips what is finished.
#
# The baseline is last night's: the script and the parents (followers_v8_352,
# fighters_v8_362) on the same drills and sweep seeds, in
# lab/runs/2026-11-12-pilots-v8/eval/ and lab/population/2026-11-sim6/sweep/first-v8-night/.
#
#   nohup lab/runs/2026-11-14-goto-school/morning.sh \
#       > lab/runs/2026-11-14-goto-school/morning.out 2>&1 &
#
# Env: PHASE (goto-school), DATE (today), ARMS (the run's three), THREADS (14),
# N_DRILLS (256 per kind), SWEEP_SEEDS (6 per cell), N_SHOOTING (516 per mission),
# N_PER_MISSION (1440, WAR; about +-3 wins per 100), MEMBERS (the pilots already rated).
# For a rehearsal: RUN (the run dir, e.g. its smoke/), SEASON (a copy of the season).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=${RUN:-lab/runs/2026-11-14-goto-school}
PY=.venv/bin/python
SEASON=${SEASON:-lab/population/2026-11-sim6}
PHASE=${PHASE:-goto-school}
DATE=${DATE:-$(date +%F)}
ARMS=${ARMS:-"followers_school followers_pay3 fighters_v8"}
THREADS=${THREADS:-14}
N_DRILLS=${N_DRILLS:-256}
SWEEP_SEEDS=${SWEEP_SEEDS:-6}
N_SHOOTING=${N_SHOOTING:-516}  # carrier battles come in blocks of 6
N_PER_MISSION=${N_PER_MISSION:-1440}
export OMP_NUM_THREADS=$THREADS
# The ten live pilots (lab/live_pilots.json after the first v8 night) and fighters_v8_362,
# a parent that is not live; tonight's arms join them.
RATED=f995_701,fighters_pay1_1317,f99_696,followers_v8_352,fighters_pay1_462
RATED=$RATED,fighters_pay1_849,f995_400,fighters_pay1_v8_351,followers_1323,fighters_1832
RATED=$RATED,fighters_v8_362
MEMBERS=${MEMBERS:-$RATED}

latest_update() {
    local found
    found=$(find "$HERE/$1/checkpoints" -name 'ppo_bc_*.pt' -printf '%f\n' \
        | sed 's/ppo_bc_\([0-9]*\)\.pt/\1/' | sort -n | tail -1)
    [[ -n $found ]] || { echo "no checkpoints for $1" >&2; exit 2; }
    echo "$found"
}

# Parent and its update at the fork, the settings that describe the arm, and its note.
arm_parent() {
    case $1 in
        followers_school | followers_pay3) echo "followers_v8_352 352" ;;
        fighters_v8) echo "fighters_v8_362 362" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_settings() {
    case $1 in
        followers_school) echo '{"sim_version":8,"obs_dim":587,"goto_timed_bonus":3.0,"goto_miss_penalty":3.0,"drill_share":0.7,"drill_weights":[6,1,1]}' ;;
        followers_pay3) echo '{"sim_version":8,"obs_dim":587,"goto_timed_bonus":3.0,"goto_miss_penalty":3.0}' ;;
        fighters_v8) echo '{"sim_version":8,"obs_dim":587,"goto_timed_bonus":1.0,"goto_miss_penalty":1.0}' ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_note() {
    case $1 in
        followers_school) echo "Go-to school: followers_v8_352 one night on with go-to drills as most of its training and a deadline worth 3." ;;
        followers_pay3) echo "Go-to school, pay only: followers_v8_352 one night on with last night's drills and a deadline worth 3." ;;
        fighters_v8) echo "Go-to school, unchanged: fighters_v8_362 a second night on the first v8 night's settings." ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}

member_checkpoint() {  # The checkpoint path in member $1's season record.
    "$PY" -c 'import json, sys
print(json.load(open(sys.argv[1]))["checkpoint"])' "$SEASON/members/$1.json"
}
drilled() {  # Has member $1 a drill record for PHASE?
    "$PY" -c 'import json, sys
m = json.load(open(sys.argv[1]))
sys.exit(0 if any(d["phase"] == sys.argv[2] for d in m["drills"]) else 1)' \
        "$SEASON/members/$1.json" "$PHASE"
}
drills() {  # drills <pilot spec> <name> <out.json>
    if [[ -f $3 ]]; then
        echo "have $3"
    else
        echo "$(date +%H:%M:%S) drills: $2"
        "$PY" -m spacefight.eval.drills --a "$1" --name "$2" \
            --n-per-kind "$N_DRILLS" --threads "$THREADS" --out "$3" >/dev/null
    fi
}
sweep() {  # sweep <pilot spec> <name> <out.json>
    if [[ -f $3 ]]; then
        echo "have $3"
    else
        echo "$(date +%H:%M:%S) sweep: $2"
        "$PY" -m spacefight.eval.goto_sweep --a "$1" --name "$2" \
            --seeds-per-cell "$SWEEP_SEEDS" --threads "$THREADS" --out "$3" >/dev/null
    fi
}

mkdir -p "$HERE/eval"
sweeps=$SEASON/sweep/$PHASE

new_ids=()
for arm in $ARMS; do
    update=$(latest_update "$arm")
    id=${arm}_${update}
    checkpoint=$HERE/$arm/checkpoints/ppo_bc_${update}.pt
    new_ids+=("$id")
    drills "$checkpoint" "$id" "$HERE/eval/drills_$id.json"
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
            --drills "$HERE/eval/drills_$id.json" --phase "$PHASE" --date "$DATE"
    fi
    sweep "$checkpoint" "$id" "$sweeps/$id.json"
    sweep "nodeadline:$checkpoint" "${id}_nodeadline" "$sweeps/${id}_nodeadline.json"
done

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
