#!/usr/bin/env bash
# The fourth commander phase (plan.md, docs/COMMANDER.md): three ways a commander might
# finally help its side. One PPO learner per arm, pilots frozen and drawn ship by ship from
# the arm's pilot list. Each trainer stops itself at the deadline (or on SIGTERM) with a
# checkpoint. Re-running resumes.
#
#   hold      the station's defender only, the citadel, from commander 3's `live` 197,
#             its launch head reset to launch each hull 3% of decisions (launch_prior),
#             long credit (gamma 0.997, lambda 0.98), no shaping; enemies 3/4 unseen,
#             1/4 scripted; the live ten. Can it learn to hold the reserve?
#   hold_quiet  as hold, its orders forbidden (only launches): started at 05:15 when hold,
#             which may give orders, drifted into giving them and lost ground.
#   kite      a fresh commander over the two kite pilots (orders cost them least), half
#             against unseen, all four missions. Do orders help pilots that can take them?
#   noattack  a fresh commander that cannot give attack orders (forbid_orders), over
#             commander 3's four followers, half against unseen, all four missions.
#
#   DEADLINE="2026-11-21 10:30" nohup setsid lab/runs/2026-11-21-commander-4/run.sh \
#       > lab/runs/2026-11-21-commander-4/run.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-21-commander-4/run.sh     # tiny sizes, into smoke/
#
# Env: ARMS ("hold kite noattack"), N_ENVS (128), DEADLINE (a `date -d` string, required
# outside SMOKE), ARM_THREADS (5 sim + 5 torch).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-21-commander-4
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"hold kite noattack"}
ARM_THREADS=${ARM_THREADS:-5}
FOLLOWERS=lab/runs/2026-11-15-commander-3/pilots_followers.json
KITE=$HERE/pilots_kite.json
LIVE=lab/live_pilots.json
C3_LIVE=lab/runs/2026-11-15-commander-3/live/checkpoints/commander_197.pt
[[ -f $C3_LIVE ]] || { echo "missing $C3_LIVE" >&2; exit 2; }
if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    DEADLINE=${DEADLINE:-"+4 minutes"}
    SIZE=(--smoke --set max_updates=2)
    BIG=()
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"2026-11-21 10:30\"" >&2; exit 2; }
    RUN=$HERE
    SIZE=(--set n_envs="${N_ENVS:-128}" --set minibatch=1024 --set snapshot_every=25
        --set checkpoint_every=10)
    BIG=(--set decisions_per_update=8192)
fi
if (( $(date -d "$DEADLINE" +%s) <= $(date +%s) )); then
    echo "DEADLINE \"$DEADLINE\" is $(date -d "$DEADLINE" '+%F %H:%M'), already past" >&2
    exit 2
fi

arm_args() {
    case $1 in
        hold) echo "--set mission_weights=[0,0,0,1] --set learner_team=0 --set launch_prior=0.03
            --set init=\"$C3_LIVE\" --set opponent_shares=[0.25,0,0,0,0.75]
            --set live_pilots=\"$LIVE\" --set ent_coef=0.002 --set gamma=0.997 --set lam=0.98
            --set shaping=0.0" ;;
        hold_quiet) echo "--set mission_weights=[0,0,0,1] --set learner_team=0 --set launch_prior=0.03
            --set init=\"$C3_LIVE\" --set opponent_shares=[0.25,0,0,0,0.75]
            --set live_pilots=\"$LIVE\" --set ent_coef=0.002 --set gamma=0.997 --set lam=0.98
            --set shaping=0.0 --set forbid_orders=[\"attack\",\"defend\",\"goto\"]" ;;
        kite) echo "--set live_pilots=\"$KITE\" --set opponent_shares=[0,0,0.25,0.25,0.5]
            --set ent_coef=0.002 --set shaping=0.5 --set keep_prior=0.8" ;;
        noattack) echo "--set forbid_orders=[\"attack\"] --set live_pilots=\"$FOLLOWERS\"
            --set opponent_shares=[0,0,0.25,0.25,0.5] --set ent_coef=0.002 --set shaping=0.5
            --set keep_prior=0.8" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_size() {  # hold: half-size updates (station matches are long; more updates a night).
    if [[ $SMOKE == 1 ]]; then return; fi
    case $1 in
        hold | hold_quiet) echo "--set decisions_per_update=4096" ;;
        *) echo "${BIG[@]}" ;;
    esac
}

pids=()
for arm in $ARMS; do
    dir=$RUN/$arm
    mkdir -p "$dir"
    resume=()
    [[ -f $dir/state.pt ]] && resume=(--resume)
    # shellcheck disable=SC2046
    OMP_NUM_THREADS=$ARM_THREADS "$PY" -m spacefight.commander.train --run-dir "$dir" \
        --deadline "$DEADLINE" "${resume[@]}" "${SIZE[@]}" $(arm_size "$arm") \
        --set n_threads="$ARM_THREADS" --set torch_threads="$ARM_THREADS" \
        --set seed=0 --set order_price=0.0 \
        $(arm_args "$arm") > "$RUN/$arm.out" 2>&1 &
    pids+=($!)
    echo "$(date +%H:%M:%S) $arm pid $!"
done
status=0
for pid in "${pids[@]}"; do
    wait "$pid" || status=1
done
echo "$(date +%H:%M:%S) done: commanders (status $status)"
exit $status
