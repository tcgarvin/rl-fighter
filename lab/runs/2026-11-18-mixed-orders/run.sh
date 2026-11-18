#!/usr/bin/env bash
# Mixed-condition matches (plan.md). Three arms, all fresh runs from followers_school_1052
# (--init), with followers_school's config and only these changes:
#   control    drill_share 0.3, commander_p 0.667, mixed_p 0.0
#   mixed      drill_share 0.3, commander_p 0.667, mixed_p 0.5
#   mixed_all  drill_share 0.3, commander_p 0.667, mixed_p 1.0
# Part 2 (plan.md "Part 2: order pay in matches"), as mixed_all except the pay scale:
#   pay0       mixed_all + match_order_pay_scale 0.0
#   pay025     mixed_all + match_order_pay_scale 0.25
# plus checkpoint_every 25, the thread counts and update_device below, and n_updates.
# An arm that dies before the deadline is started again from its last checkpoint (or
# from scratch, from the init, if it had none yet), up to MAX_RESTARTS times. Stops by
# SIGTERM at the deadline; each trainer checkpoints after its update. Re-running resumes.
#
#   Beast:  ARMS="mixed mixed_all" DEADLINE="2026-11-18 15:00" nohup setsid \
#               lab/runs/2026-11-18-mixed-orders/run.sh \
#               > lab/runs/2026-11-18-mixed-orders/run_beast.out 2>&1 &
#   Laptop: ARMS=control SIM_THREADS=6 TORCH_THREADS=6 DEADLINE="2026-11-18 15:00" \
#               nohup setsid lab/runs/2026-11-18-mixed-orders/run.sh \
#               > lab/runs/2026-11-18-mixed-orders/run_laptop.out 2>&1 &
#   Beast, part 2: ARMS="pay0 pay025" DEADLINE="2026-11-18 19:00" nohup setsid \
#               lab/runs/2026-11-18-mixed-orders/run.sh \
#               > lab/runs/2026-11-18-mixed-orders/run_beast2.out 2>&1 &
#   SMOKE=1 ARMS="control mixed mixed_all" lab/runs/2026-11-18-mixed-orders/run.sh
#       (tiny sizes, 2 updates a checkpoint, into smoke/)
#
# Env: ARMS (default "mixed mixed_all"), DEADLINE (a `date -d` string, required outside
# SMOKE), N_UPDATES (6000, an upper bound; the deadline ends the run), SIM_THREADS and
# TORCH_THREADS (3 each; per arm SIM_THREADS_<arm>, TORCH_THREADS_<arm>), DEVICE_<arm>
# (update_device; defaults control=cpu, mixed=cuda:0, mixed_all=cuda:1, pay0=cuda:0,
# pay025=cuda:1), MAX_RESTARTS (3).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-18-mixed-orders
SOURCE=lab/runs/2026-11-14-goto-school-2/followers_school
INIT=$ROOT/$SOURCE/checkpoints/ppo_bc_1052.pt
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"mixed mixed_all"}
MAX_RESTARTS=${MAX_RESTARTS:-3}
[[ -f $INIT ]] || { echo "missing $INIT" >&2; exit 2; }
[[ -f $SOURCE/config.yaml ]] || { echo "missing $SOURCE/config.yaml" >&2; exit 2; }

if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    DEADLINE=${DEADLINE:-"+20 minutes"}
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"2026-11-18 15:00\"" >&2; exit 2; }
    RUN=$HERE
fi
deadline=$(date -d "$DEADLINE" +%s)
(( deadline > $(date +%s) )) || { echo "DEADLINE $DEADLINE is already past" >&2; exit 2; }

arm_mixed_p() {
    case $1 in
        control) echo 0.0 ;;
        mixed) echo 0.5 ;;
        mixed_all|pay0|pay025) echo 1.0 ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_pay_scale() {  # match_order_pay_scale; empty = the default (1.0, not set)
    case $1 in
        pay0) echo 0.0 ;;
        pay025) echo 0.25 ;;
        *) echo "" ;;
    esac
}
arm_device() {
    local var="DEVICE_$1" default
    case $1 in
        control) default=cpu ;;
        mixed) default=cuda:0 ;;
        mixed_all) default=cuda:1 ;;
        pay0) default=cuda:0 ;;
        pay025) default=cuda:1 ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
    echo "${!var:-$default}"
}
arm_threads() {  # $1 arm, $2 SIM or TORCH
    local var="${2}_THREADS_$1" base="${2}_THREADS"
    echo "${!var:-${!base:-3}}"
}
latest_update() {  # The highest update with a checkpoint in run directory $1, or empty.
    [[ -d $1/checkpoints ]] || return 0
    find "$1/checkpoints" -name 'ppo_bc_*.pt' -printf '%f\n' \
        | sed 's/ppo_bc_\([0-9]*\)\.pt/\1/' | sort -n | tail -1
}

# followers_school's config as --set KEY=JSON pairs (JSON is YAML), minus what this run
# sets itself: init and tag come from --init, the rest is listed below.
source_sets() {
    "$PY" - "$SOURCE/config.yaml" <<'EOF'
import json, sys, yaml
skip = {"init", "tag", "roster_overrides", "checkpoint_every", "n_updates",
        "sim_threads", "torch_threads", "update_device", "actor_frozen_until"}
for key, value in yaml.safe_load(open(sys.argv[1])).items():
    if key not in skip:
        print(f"{key}={json.dumps(value)}")
EOF
}

declare -A pid_of restarts n_updates
start_arm() {
    local arm=$1 dir=$RUN/$1 mixed_p pay_scale device sim torch overrides
    mixed_p=$(arm_mixed_p "$arm")
    pay_scale=$(arm_pay_scale "$arm")
    device=$(arm_device "$arm")
    sim=$(arm_threads "$arm" SIM)
    torch=$(arm_threads "$arm" TORCH)
    overrides="{\"drill_share\":0.3,\"drill_weights\":[6,1,1],\"commander_p\":0.667,\"mixed_p\":$mixed_p}"
    local -a args=(
        --n-updates "${n_updates[$arm]}"
        --set sim_threads="$sim" --set torch_threads="$torch"
        --set update_device="$device"
        --set roster_overrides="$overrides"
    )
    if [[ -n $pay_scale ]]; then
        args+=(--set match_order_pay_scale="$pay_scale")
    fi
    if [[ $SMOKE == 1 ]]; then
        args+=(--set n_envs=8 --set n_steps=32 --set minibatch=256 --set checkpoint_every=2)
    else
        args+=(--set checkpoint_every=25)
    fi
    if [[ -n $(latest_update "$dir") ]]; then
        "$PY" -m spacefight.train_spike ppo --run-dir "$dir" --resume "${args[@]}" \
            >>"$RUN/$arm.out" 2>&1 &
    else
        # Nothing to resume from: a fresh run from the init (a death before the first
        # checkpoint leaves a config and a log behind; start them again).
        rm -f "$dir/config.yaml" "$dir/log.jsonl"
        mkdir -p "$dir"
        local -a sets=()
        while IFS= read -r line; do sets+=(--set "$line"); done < <(source_sets)
        "$PY" -m spacefight.train_spike ppo --run-dir "$dir" --init "$INIT" \
            "${sets[@]}" "${args[@]}" >>"$RUN/$arm.out" 2>&1 &
    fi
    pid_of[$arm]=$!
    echo "$(date +%H:%M:%S) $arm pid ${pid_of[$arm]} (mixed_p $mixed_p${pay_scale:+, match pay $pay_scale}, $device, $sim+$torch threads)"
}

mkdir -p "$RUN"
for arm in $ARMS; do
    arm_mixed_p "$arm" >/dev/null
    n_updates[$arm]=${N_UPDATES:-6000}
    if [[ $SMOKE == 1 ]]; then
        done_so_far=$(latest_update "$RUN/$arm")
        n_updates[$arm]=$(( ${done_so_far:-0} + 2 ))
    fi
    restarts[$arm]=0
    start_arm "$arm"
done

stopping=0
stop() {
    stopping=1
    kill -TERM "${pid_of[@]}" 2>/dev/null || true
}
trap stop TERM INT
declare -A over
while (( $(date +%s) < deadline && ! stopping )); do
    alive=0
    for arm in $ARMS; do
        [[ -n ${over[$arm]:-} ]] && continue
        if kill -0 "${pid_of[$arm]}" 2>/dev/null; then
            alive=1
            continue
        fi
        status=0
        wait "${pid_of[$arm]}" || status=$?
        (( stopping )) && break
        if (( status != 0 && restarts[$arm] < MAX_RESTARTS && $(date +%s) < deadline - 600 )); then
            restarts[$arm]=$(( restarts[$arm] + 1 ))
            echo "$(date +%H:%M:%S) $arm died ($status); restart ${restarts[$arm]} from update $(latest_update "$RUN/$arm")"
            start_arm "$arm"
            alive=1
        else
            echo "$(date +%H:%M:%S) $arm over (exit $status)"
            over[$arm]=1
        fi
    done
    (( alive )) || break
    sleep 20 &
    wait $! || true
done
stop
wait || true
echo "$(date +%H:%M:%S) done: PPO"
