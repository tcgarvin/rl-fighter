#!/usr/bin/env bash
# The morning after a night on SIM_VERSION 8 (plan.md): for each arm's latest checkpoint
# the drill eval (go-to now judged by the order's own deadline, with the split of failures
# into near misses and ships that went for an enemy), its member record, the deadline sweep
# (one ship, set distances, the same starts replayed at each time allowance), the shooting
# eval against its parent, then wins above replacement for the live ten plus tonight's and
# the report. It archives and publishes nothing. Re-running skips what is finished.
#
# The parents and the script are measured on the same v8 drills and sweep as the baseline
# (they cannot see a deadline). A pilot that can see it is also swept with those inputs
# zeroed (nodeadline:), which separates what it learned to read from what it learned to do.
#
#   PHASE=first-v8-night nohup lab/runs/2026-11-12-pilots-v8/morning.sh \
#       > lab/runs/2026-11-12-pilots-v8/morning.out 2>&1 &
#
# Env: PHASE (first-v8-night), DATE (today), ARMS (the run's four), THREADS (14),
# N_DRILLS (256 per kind), SWEEP_SEEDS (6 per cell), N_SHOOTING (516 per mission),
# N_PER_MISSION (1440, WAR; about +-3 wins per 100), MEMBERS (the pilots already rated).
# For a rehearsal: RUN (the run dir, e.g. its smoke/), SEASON (a copy of the season).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=${RUN:-lab/runs/2026-11-12-pilots-v8}
PY=.venv/bin/python
SEASON=${SEASON:-lab/population/2026-11-sim6}
PHASE=${PHASE:-first-v8-night}
DATE=${DATE:-$(date +%F)}
ARMS=${ARMS:-"followers_v8 fighters_v8 fighters_pay1_v8 followers_v8_blind"}
THREADS=${THREADS:-14}
N_DRILLS=${N_DRILLS:-256}
SWEEP_SEEDS=${SWEEP_SEEDS:-6}
N_SHOOTING=${N_SHOOTING:-516}  # carrier battles come in blocks of 6
N_PER_MISSION=${N_PER_MISSION:-1440}
export OMP_NUM_THREADS=$THREADS
# The ten live pilots (lab/live_pilots.json after night 4); tonight's arms join them.
RATED=f99_696,fighters_pay1_1317,fighters_1832,fighters_pay1_462,f995_701,f995_400
RATED=$RATED,followers_1793,fighters_1338,fighters_pay1_849,followers_1323
MEMBERS=${MEMBERS:-$RATED}
PARENTS="followers_1793 fighters_1832 fighters_pay1_1317"

latest_update() {
    local found
    found=$(find "$HERE/$1/checkpoints" -name 'ppo_bc_*.pt' -printf '%f\n' \
        | sed 's/ppo_bc_\([0-9]*\)\.pt/\1/' | sort -n | tail -1)
    [[ -n $found ]] || { echo "no checkpoints for $1" >&2; exit 2; }
    echo "$found"
}

# Parent, its update at the fork, whether the arm sees the deadline, and its note.
arm_parent() {
    case $1 in
        followers_v8 | followers_v8_blind) echo "followers_1793 1793" ;;
        fighters_v8) echo "fighters_1832 1832" ;;
        fighters_pay1_v8) echo "fighters_pay1_1317 1317" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_sees() { [[ $1 != *_blind ]]; }
arm_settings() {
    if arm_sees "$1"; then
        echo '{"sim_version":8,"obs_dim":587,"goto_timed_bonus":1.0,"goto_miss_penalty":1.0}'
    else
        echo '{"sim_version":8,"obs_dim":583,"goto_timed_bonus":1.0,"goto_miss_penalty":1.0}'
    fi
}
arm_note() {
    read -r parent _ <<<"$(arm_parent "$1")"
    if arm_sees "$1"; then
        echo "First v8 night: $parent's line with four new inputs for a go-to's deadline, trained on go-to drills that carry one."
    else
        echo "First v8 night, control: $parent's line paid by go-to deadlines it cannot see (583 inputs)."
    fi
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

# The baseline on v8's drills and sweep: the script and tonight's parents.
drills script script "$HERE/eval/drills_script.json"
sweep script script "$sweeps/script.json"
for parent in $PARENTS; do
    checkpoint=$(member_checkpoint "$parent")
    drills "$checkpoint" "$parent" "$HERE/eval/drills_$parent.json"
    sweep "$checkpoint" "$parent" "$sweeps/$parent.json"
done

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
    if arm_sees "$arm"; then
        sweep "nodeadline:$checkpoint" "${id}_nodeadline" "$sweeps/${id}_nodeadline.json"
    fi
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
