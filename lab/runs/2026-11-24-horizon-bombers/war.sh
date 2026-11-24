#!/usr/bin/env bash
# After the horizon-bombers night: enter each arm's last checkpoint in the season as a
# child of followers_dock_v8_2676, record its final drills, then wins above replacement
# for the live ten (the parent among them) and the two new members, in all four live
# missions (WAR's default), with the live commander stable, and the season report. No
# gates: WAR and the family rules decide what goes live (tools.live_pilots publish
# --war, on the laptop). It archives and publishes nothing. Re-running skips what is
# finished.
#
#   nohup setsid lab/runs/2026-11-24-horizon-bombers/war.sh \
#       > lab/runs/2026-11-24-horizon-bombers/war.out 2>&1 &
#
# Env: PHASE (horizon-bombers), DATE (today), THREADS (12), N_PER_MISSION (1440, about
# +-3 wins per 100), MEMBERS (default: the live list; the new members are always
# added), CHECKPOINT_ROOT (the checkout holding the weights; default this one), RUN (the
# run directory holding the arms' checkpoints and eval/; default this directory). For a
# rehearsal: SEASON (a copy of the season), RUN=lab/runs/2026-11-24-horizon-bombers/smoke,
# N_PER_MISSION=24, OUT_PHASE=smoke.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-24-horizon-bombers
RUN=${RUN:-$HERE}
PY=${PY:-.venv/bin/python}
export PYTHONPATH=$ROOT
CHECKPOINT_ROOT=${CHECKPOINT_ROOT:-$ROOT}
SEASON=${SEASON:-lab/population/2026-11-sim6}
PHASE=${PHASE:-horizon-bombers}
DATE=${DATE:-$(date +%F)}
THREADS=${THREADS:-12}
N_PER_MISSION=${N_PER_MISSION:-1440}
export OMP_NUM_THREADS=$THREADS

latest_update() {
    local found
    found=$(find "$RUN/$1/checkpoints" -name 'ppo_bc_*.pt' -printf '%f\n' \
        | sed 's/ppo_bc_\([0-9]*\)\.pt/\1/' | sort -n | tail -1)
    [[ -n $found ]] || { echo "no checkpoints for $1" >&2; exit 2; }
    echo "$found"
}
have() { [[ -f $SEASON/members/$1.json ]]; }
drilled() {
    "$PY" -c 'import json, sys
m = json.load(open(sys.argv[1]))
sys.exit(0 if any(d["phase"] == sys.argv[2] for d in m["drills"]) else 1)' \
        "$SEASON/members/$1.json" "$PHASE"
}
add_child() {  # id parent fork_update checkpoint settings note
    if have "$1"; then
        echo "have member $1"
        return
    fi
    [[ -f $CHECKPOINT_ROOT/$4 ]] || { echo "missing $CHECKPOINT_ROOT/$4 (the weights of $1)" >&2; exit 2; }
    "$PY" -m spacefight.population add-child --season "$SEASON" --id "$1" \
        --parent "$2" --fork-update "$3" --checkpoint "$4" \
        --checkpoint-root "$CHECKPOINT_ROOT" --settings "$5" --note "$6"
}
record() {  # id drills.json
    if drilled "$1"; then
        echo "have drills for $1 in $PHASE"
    elif [[ -f $2 ]]; then
        "$PY" -m spacefight.population record-drills --season "$SEASON" --id "$1" \
            --drills "$2" --phase "$PHASE" --date "$DATE"
    else
        echo "no final drills for $1 ($2); not recorded"
    fi
}
final_eval() {  # The arm's final eval directory (empty when there is none).
    find "$RUN/eval" -maxdepth 1 -type d -name "$1_final_*" 2>/dev/null | sort | tail -1
}

arm_id() {  # The member id of arm $1 at update $2.
    case $1 in
        h999) echo "dock_h999_$2" ;;
        h995) echo "dock_h995_$2" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_gamma() {
    case $1 in
        h999) echo 0.999 ;;
        h995) echo 0.995 ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_note() {
    case $1 in
        h999) echo "Horizon and bombers night: followers_dock_v8_2676 with a longer horizon (gamma 0.999), bombers in its matches and drills, and live pilots as a third of its teammates." ;;
        h995) echo "Horizon and bombers night: followers_dock_v8_2676 on its own horizon (gamma 0.995), with bombers in its matches and drills and live pilots as a third of its teammates." ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
new_ids=()
for arm in h999 h995; do
    update=$(latest_update "$arm")
    id=$(arm_id "$arm" "$update")
    settings="{\"sim_version\":11,\"obs_dim\":592,\"gamma\":$(arm_gamma "$arm"),\"bomber_share\":0.2,\"drill_bomber_share\":0.2,\"teammate_share\":0.3,\"dock_bonus\":1.0,\"drill_share\":0.55,\"drill_dock_share\":0.5,\"drill_dock_threat_share\":0.5}"
    add_child "$id" followers_dock_v8_2676 2676 "$RUN/$arm/checkpoints/ppo_bc_${update}.pt" \
        "$settings" "$(arm_note "$arm")"
    new_ids+=("$id")
    final=$(final_eval "$arm")
    record "$id" "${final:-$RUN/eval/${arm}_final_missing}/drills.json"
done

rated() {  # The live list (followers_dock_v8_2676, both arms' parent, is on it).
    "$PY" -c 'import json
print(",".join(p["id"] for p in json.load(open("lab/live_pilots.json"))["pilots"]))'
}
MEMBERS=${MEMBERS:-$(rated)}
war=$SEASON/war/${OUT_PHASE:-$PHASE}
members=$MEMBERS$(printf ',%s' "${new_ids[@]}")
echo "$(date +%H:%M:%S) WAR: $members"
"$PY" -m spacefight.population war --season "$SEASON" --out "$war" \
    --members "$members" --commanders live --checkpoint-root "$CHECKPOINT_ROOT" \
    --n-per-mission "$N_PER_MISSION" --threads "$THREADS"
"$PY" -m spacefight.population report --season "$SEASON" --war "$war/war.json" \
    --phase "$PHASE" --date "$DATE"
echo "$(date +%H:%M:%S) done: war"
