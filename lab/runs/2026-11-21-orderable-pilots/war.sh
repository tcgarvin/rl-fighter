#!/usr/bin/env bash
# After the orderable-pilots night: enter the kite-drills pilots (kite_2205,
# kite_pay025_2211, children of followers_school_1052) and each arm's last checkpoint in
# the season, as children of their parents, record drills where a final drills.json
# exists, then wins above replacement for the live pilots, the two dock pilots, the
# parents and the new members, in all four live missions (WAR's default), with the live
# commander stable, and the season report. No gates: WAR and the family rules decide
# what goes live (tools.live_pilots publish --war, on the laptop). It archives and
# publishes nothing. Re-running skips what is finished.
#
#   nohup setsid lab/runs/2026-11-21-orderable-pilots/war.sh \
#       > lab/runs/2026-11-21-orderable-pilots/war.out 2>&1 &
#
# The dock pilots (followers_dock_2624, followers_dock_v8_2676) joined the season in the
# dock-pilot WAR step (../2026-11-20-dock-pilot/war.sh); a checkout without their
# records enters them here the same way, since dockkite's member is a child of
# followers_dock_2624.
#
# Env: PHASE (orderable-pilots), DATE (today), THREADS (12), N_PER_MISSION (1440, about
# +-3 wins per 100), MEMBERS (default: the live list and the two dock pilots; the new
# members are always added), CHECKPOINT_ROOT (the checkout holding the weights;
# default this one), RUN (the run directory holding the arms'
# checkpoints and eval/; default this directory). For a rehearsal: SEASON (a copy of the
# season), RUN=lab/runs/2026-11-21-orderable-pilots/smoke, N_PER_MISSION=24
# OUT_PHASE=smoke (members hold paths relative to CHECKPOINT_ROOT, so from a worktree
# the smoke arms' checkpoints must also sit at that path under CHECKPOINT_ROOT;
# rehearsed so on the laptop 2026-11-21: six members added, 96 matches, exit 0).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-21-orderable-pilots
RUN=${RUN:-$HERE}
PY=${PY:-.venv/bin/python}
export PYTHONPATH=$ROOT
CHECKPOINT_ROOT=${CHECKPOINT_ROOT:-$ROOT}
SEASON=${SEASON:-lab/population/2026-11-sim6}
PHASE=${PHASE:-orderable-pilots}
DATE=${DATE:-$(date +%F)}
THREADS=${THREADS:-12}
N_PER_MISSION=${N_PER_MISSION:-1440}
export OMP_NUM_THREADS=$THREADS
KITE=lab/runs/2026-11-18-kite-drills
DOCK=lab/runs/2026-11-20-dock-pilot

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

# The dock pilots, if this season copy lacks them (as ../2026-11-20-dock-pilot/war.sh).
dock_settings='{"sim_version":11,"obs_dim":592,"dock_bonus":1.0,"drill_share":0.55,"drill_dock_share":0.5,"drill_dock_threat_share":0.5}'
add_child followers_dock_2624 followers_school_600 600 \
    "$DOCK/dock600/checkpoints/ppo_bc_2624.pt" "$dock_settings" \
    "Dock pilot night: followers_school_600 taught to answer a recall home, half its drills dock drills; docks 57 calm drills in 100 where its parent docked 2."
add_child followers_dock_v8_2676 followers_v8_352 352 \
    "$DOCK/dock352/checkpoints/ppo_bc_2676.pt" "$dock_settings" \
    "Dock pilot night: followers_v8_352 taught to answer a recall home, half its drills dock drills; docks 38 calm drills in 100 where its parent docked 1."

# The kite-drills pilots, children of followers_school_1052, and their final drills
# (the drill eval at 64 a kind, SIM_VERSION 9: order drills only).
kite_settings='{"sim_version":8,"obs_dim":587,"drill_share":0.4,"drill_weights":[4,3,1],"drill_attack_pool_share":0.5,"commander_p":0.667,"mixed_p":0.0}'
add_child kite_2205 followers_school_1052 1052 "$KITE/kite/checkpoints/ppo_bc_2205.pt" \
    "$kite_settings" \
    "Kite drills: followers_school_1052 trained on attack drills against a frozen pool pilot that falls back; ordered onto its nearest enemy it wins 0.42 of 3 v 3s against a free 1052, where its parent won 0.14."
record kite_2205 "$KITE/eval_final/kite_2205_drills.json"
add_child kite_pay025_2211 followers_school_1052 1052 \
    "$KITE/kite_pay025/checkpoints/ppo_bc_2211.pt" \
    '{"sim_version":8,"obs_dim":587,"drill_share":0.4,"drill_weights":[4,3,1],"drill_attack_pool_share":0.5,"commander_p":0.667,"mixed_p":0.0,"match_order_pay_scale":0.25}' \
    "Kite drills with a quarter of the order pay in matches: ordered onto its nearest enemy it wins 0.33 of 3 v 3s against a free 1052 (its parent 0.14), and pays no cost against f995_701."
record kite_pay025_2211 "$KITE/eval_final/kite_pay025_2211_drills.json"

# Tonight's arms.
arm_id() {  # The member id of arm $1 at update $2.
    case $1 in
        kitedock) echo "kite_dock_$2" ;;
        dockkite) echo "followers_dockkite_$2" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_parent() {
    case $1 in
        kitedock) echo "kite_2205 2205" ;;
        dockkite) echo "followers_dock_2624 2624" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_note() {
    case $1 in
        kitedock) echo "Orderable pilots night: kite_2205 (orderable) widened to 592 inputs and taught to dock, with kite drills kept in its mix." ;;
        dockkite) echo "Orderable pilots night: followers_dock_2624 (dockable) given kite drills, with dock drills kept in its mix." ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
settings='{"sim_version":11,"obs_dim":592,"dock_bonus":1.0,"goto_timed_bonus":3.0,"goto_miss_penalty":3.0,"drill_share":0.55,"drill_weights":[4,3,1],"drill_attack_pool_share":0.5,"drill_dock_share":0.4,"drill_dock_threat_share":0.5,"commander_p":0.667,"mixed_p":0.0}'
new_ids=(kite_2205 kite_pay025_2211)
for arm in kitedock dockkite; do
    update=$(latest_update "$arm")
    id=$(arm_id "$arm" "$update")
    read -r parent fork_update <<<"$(arm_parent "$arm")"
    add_child "$id" "$parent" "$fork_update" "$RUN/$arm/checkpoints/ppo_bc_${update}.pt" \
        "$settings" "$(arm_note "$arm")"
    new_ids+=("$id")
    final=$(final_eval "$arm")
    record "$id" "${final:-$RUN/eval/${arm}_final_missing}/drills.json"
done

rated() {  # The live list, then the dock pilots not on it (followers_dock_2624 is
    # dockkite's parent; kite_2205, kitedock's, is among the new members).
    "$PY" -c 'import json, sys
ids = [p["id"] for p in json.load(open("lab/live_pilots.json"))["pilots"]]
ids += [p for p in sys.argv[1:] if p not in ids]
print(",".join(ids))' followers_dock_2624 followers_dock_v8_2676
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
