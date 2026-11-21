#!/usr/bin/env bash
# After the dock-pilot night: enter each arm's last checkpoint in the season as a child of
# its parent, record its order drills, then wins above replacement for the live pilots, the
# two parents and the two new pilots, in all four live missions (station assault included,
# where the scripted commander's recalls matter most), and the season report. No gates:
# WAR and the family rules decide what goes live (tools.live_pilots publish --war, on the
# laptop). It archives and publishes nothing. Re-running skips what is finished.
#
#   nohup setsid lab/runs/2026-11-20-dock-pilot/war.sh \
#       > lab/runs/2026-11-20-dock-pilot/war.out 2>&1 &
#
# Env: PHASE (dock-pilot), DATE (today), THREADS (12), N_PER_MISSION (1440, about +-3 wins
# per 100), MEMBERS (default: the live list and the two parents).
# For a rehearsal: SEASON (a copy of the season), N_PER_MISSION=24 OUT_PHASE=smoke.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-20-dock-pilot
PY=.venv/bin/python
SEASON=${SEASON:-lab/population/2026-11-sim6}
PHASE=${PHASE:-dock-pilot}
DATE=${DATE:-$(date +%F)}
THREADS=${THREADS:-12}
N_PER_MISSION=${N_PER_MISSION:-1440}
export OMP_NUM_THREADS=$THREADS
PARENTS="followers_school_600 followers_v8_352"
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
arm_id() {  # The member id of arm $1 at update $2.
    case $1 in
        dock600) echo "followers_dock_$2" ;;
        dock352) echo "followers_dock_v8_$2" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_parent() {
    case $1 in
        dock600) echo "followers_school_600 600" ;;
        dock352) echo "followers_v8_352 352" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
settings='{"sim_version":11,"obs_dim":592,"dock_bonus":1.0,"drill_share":0.55,"drill_dock_share":0.5,"drill_dock_threat_share":0.5}'
arm_note() {
    case $1 in
        dock600) echo "Dock pilot night: followers_school_600 taught to answer a recall home, half its drills dock drills; docks 57 calm drills in 100 where its parent docked 2." ;;
        dock352) echo "Dock pilot night: followers_v8_352 taught to answer a recall home, half its drills dock drills; docks 38 calm drills in 100 where its parent docked 1." ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
final_eval() {  # The arm's final eval directory.
    find "$HERE/eval" -maxdepth 1 -type d -name "$1_final_*" | sort | tail -1
}
drilled() {
    "$PY" -c 'import json, sys
m = json.load(open(sys.argv[1]))
sys.exit(0 if any(d["phase"] == sys.argv[2] for d in m["drills"]) else 1)' \
        "$SEASON/members/$1.json" "$PHASE"
}

new_ids=()
for arm in dock600 dock352; do
    update=$(latest_update "$arm")
    id=$(arm_id "$arm" "$update")
    checkpoint=$HERE/$arm/checkpoints/ppo_bc_${update}.pt
    new_ids+=("$id")
    if [[ -f $SEASON/members/$id.json ]]; then
        echo "have member $id"
    else
        read -r parent fork_update <<<"$(arm_parent "$arm")"
        "$PY" -m spacefight.population add-child --season "$SEASON" --id "$id" \
            --parent "$parent" --fork-update "$fork_update" --checkpoint "$checkpoint" \
            --settings "$settings" --note "$(arm_note "$arm")"
    fi
    drills=$(final_eval "$arm")/drills.json
    if drilled "$id"; then
        echo "have drills for $id in $PHASE"
    elif [[ -f $drills ]]; then
        "$PY" -m spacefight.population record-drills --season "$SEASON" --id "$id" \
            --drills "$drills" --phase "$PHASE" --date "$DATE"
    else
        echo "no final drills for $arm ($drills); not recorded"
    fi
done

war=$SEASON/war/${OUT_PHASE:-$PHASE}
members=$MEMBERS$(printf ',%s' "${new_ids[@]}")
echo "$(date +%H:%M:%S) WAR: $members"
"$PY" -m spacefight.population war --season "$SEASON" --out "$war" \
    --members "$members" --commanders live \
    --n-per-mission "$N_PER_MISSION" --threads "$THREADS"
"$PY" -m spacefight.population report --season "$SEASON" --war "$war/war.json" \
    --phase "$PHASE" --date "$DATE"
echo "$(date +%H:%M:%S) done: war"
