#!/usr/bin/env bash
# The morning after go-to school's second night (plan.md): for each arm's latest
# checkpoint the drill eval, its member record, the deadline sweep (also with its deadline
# inputs zeroed, nodeadline:), the shooting eval against its parent, then wins above
# replacement for the live pilots, the parents and tonight's three, and the report. It
# archives and publishes nothing. Re-running skips what is finished.
#
# The baselines are the parents on the same drills and sweep seeds: followers_school_600
# in lab/runs/2026-11-14-goto-school/eval/ and lab/population/2026-11-sim6/sweep/goto-school/,
# fighters_pay1_v8_351 in lab/runs/2026-11-12-pilots-v8/eval/ and .../sweep/first-v8-night/.
#
#   nohup lab/runs/2026-11-14-goto-school-2/morning.sh \
#       > lab/runs/2026-11-14-goto-school-2/morning.out 2>&1 &
#
# Env: PHASE (goto-school-2), DATE (today), ARMS (the run's three), THREADS (14),
# N_DRILLS (256 per kind), SWEEP_SEEDS (6 per cell), N_SHOOTING (516 per mission),
# N_PER_MISSION (1440, WAR; about +-3 wins per 100), MEMBERS (the pilots already rated:
# by default the live list as it stands, and the two parents).
# For a rehearsal: RUN (the run dir, e.g. its smoke/), SEASON (a copy of the season).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=${RUN:-lab/runs/2026-11-14-goto-school-2}
PY=.venv/bin/python
SEASON=${SEASON:-lab/population/2026-11-sim6}
PHASE=${PHASE:-goto-school-2}
DATE=${DATE:-$(date +%F)}
ARMS=${ARMS:-"followers_school followers_solo fighters_pay1_school"}
THREADS=${THREADS:-14}
N_DRILLS=${N_DRILLS:-256}
SWEEP_SEEDS=${SWEEP_SEEDS:-6}
N_SHOOTING=${N_SHOOTING:-516}  # carrier battles come in blocks of 6
N_PER_MISSION=${N_PER_MISSION:-1440}
export OMP_NUM_THREADS=$THREADS
# The live pilots (lab/live_pilots.json as it stands this morning) and tonight's two
# parents, live or not; tonight's arms join them.
PARENTS="followers_school_600 fighters_pay1_v8_351"
rated() {
    "$PY" -c 'import json, sys
ids = [p["id"] for p in json.load(open("lab/live_pilots.json"))["pilots"]]
ids += [p for p in sys.argv[1:] if p not in ids]
print(",".join(ids))' $PARENTS
}
MEMBERS=${MEMBERS:-$(rated)}

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
        followers_school | followers_solo) echo "followers_school_600 600" ;;
        fighters_pay1_school) echo "fighters_pay1_v8_351 351" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_settings() {
    case $1 in
        followers_school) echo '{"sim_version":8,"obs_dim":587,"goto_timed_bonus":3.0,"goto_miss_penalty":3.0,"drill_share":0.7,"drill_weights":[6,1,1]}' ;;
        followers_solo) echo '{"sim_version":8,"obs_dim":587,"goto_timed_bonus":3.0,"goto_miss_penalty":3.0,"drill_share":0.7,"drill_weights":[6,1,1],"drill_goto_solo_share":0.6}' ;;
        fighters_pay1_school) echo '{"sim_version":8,"obs_dim":587,"goto_timed_bonus":3.0,"goto_miss_penalty":3.0,"drill_share":0.7,"drill_weights":[6,1,1]}' ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_note() {
    case $1 in
        followers_school) echo "Go-to school, second night: followers_school_600 a night on, unchanged." ;;
        followers_solo) echo "Go-to school, second night: followers_school_600 a night on with 7 go-to drills in 10 flown by one ship alone." ;;
        fighters_pay1_school) echo "Go-to school, second night: fighters_pay1_v8_351 a night on with go-to drills as most of its training and a deadline worth 3." ;;
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
