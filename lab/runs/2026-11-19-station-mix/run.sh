#!/usr/bin/env bash
# Station assault and bombers in the pilot mix (plan.md). Two arms, one config on two
# seeds, both fresh from followers_school_1052 (--init) with followers_school's config
# and the mixed-orders `control` arm's changes (drill_share 0.3, drill_weights [6,1,1],
# commander_p 0.667, mixed_p 0), plus the SIM_VERSION 9 keys:
#   mission_weights [0.3, 0.225, 0.225, 0.25]  (station assault a quarter of matches)
#   station_as_convoy_share 0.5                (both readings half each)
#   bomber_share 0.2, drill_bomber_share 0.2   (a fifth of strike / drill pilot slots)
#   mix_s1   seed 191, cuda:0, 3+3 threads
#   mix_s2   seed 192, cuda:1, 3+3 threads
# plus checkpoint_every 25 and n_updates. Needs a venv with rlf_sim at SIM_VERSION 9.
# An arm that dies before the deadline is started again from its last checkpoint (or
# from scratch, from the init, if it had none yet), up to MAX_RESTARTS times. Stops by
# SIGTERM at the deadline; each trainer checkpoints after its update. Re-running resumes.
#
#   Beast:  DEADLINE="2026-11-19 19:00" nohup setsid \
#               lab/runs/2026-11-19-station-mix/run.sh \
#               > lab/runs/2026-11-19-station-mix/run_beast.out 2>&1 &
#   SMOKE=1 lab/runs/2026-11-19-station-mix/run.sh
#       (tiny sizes, 2 updates a checkpoint, into smoke/; from a worktree add
#       DATA_ROOT=/home/timg/code/rl-fighter for the init weights)
#
# Env: ARMS (default "mix_s1 mix_s2"), DEADLINE (a `date -d` string, required outside
# SMOKE), N_UPDATES (6000, an upper bound; the deadline ends the run), SIM_THREADS and
# TORCH_THREADS (3 each; per arm SIM_THREADS_<arm>, TORCH_THREADS_<arm>), DEVICE_<arm>
# (update_device; defaults mix_s1=cuda:0, mix_s2=cuda:1), MAX_RESTARTS (3), DATA_ROOT
# (the checkout holding the init checkpoint; default this one).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-19-station-mix
SOURCE=lab/runs/2026-11-14-goto-school-2/followers_school
DATA_ROOT=${DATA_ROOT:-$ROOT}
INIT=$DATA_ROOT/$SOURCE/checkpoints/ppo_bc_1052.pt
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"mix_s1 mix_s2"}
MAX_RESTARTS=${MAX_RESTARTS:-3}
[[ -f $INIT ]] || { echo "missing $INIT" >&2; exit 2; }
[[ -f $SOURCE/config.yaml ]] || { echo "missing $SOURCE/config.yaml" >&2; exit 2; }
sim_version=$("$PY" -c 'import rlf_sim; print(rlf_sim.SIM_VERSION)')
(( sim_version >= 9 )) || { echo "rlf_sim is SIM_VERSION $sim_version; rebuild it (needs 9)" >&2; exit 2; }

if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    DEADLINE=${DEADLINE:-"+20 minutes"}
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"2026-11-19 19:00\"" >&2; exit 2; }
    RUN=$HERE
fi
deadline=$(date -d "$DEADLINE" +%s)
(( deadline > $(date +%s) )) || { echo "DEADLINE $DEADLINE is already past" >&2; exit 2; }

OVERRIDES='{"drill_share":0.3,"drill_weights":[6,1,1],"commander_p":0.667,"mixed_p":0.0,'
OVERRIDES+='"mission_weights":[0.3,0.225,0.225,0.25],"station_as_convoy_share":0.5,'
OVERRIDES+='"bomber_share":0.2,"drill_bomber_share":0.2}'

arm_seed() {
    case $1 in
        mix_s1) echo 191 ;;
        mix_s2) echo 192 ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_device() {
    local var="DEVICE_$1" default
    case $1 in
        mix_s1) default=cuda:0 ;;
        mix_s2) default=cuda:1 ;;
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
skip = {"init", "tag", "seed", "roster_overrides", "checkpoint_every", "n_updates",
        "sim_threads", "torch_threads", "update_device", "actor_frozen_until"}
for key, value in yaml.safe_load(open(sys.argv[1])).items():
    if key not in skip:
        print(f"{key}={json.dumps(value)}")
EOF
}

declare -A pid_of restarts n_updates
start_arm() {
    local arm=$1 dir=$RUN/$1 seed device sim torch
    seed=$(arm_seed "$arm")
    device=$(arm_device "$arm")
    sim=$(arm_threads "$arm" SIM)
    torch=$(arm_threads "$arm" TORCH)
    local -a args=(
        --n-updates "${n_updates[$arm]}"
        --set sim_threads="$sim" --set torch_threads="$torch"
        --set update_device="$device"
    )
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
            "${sets[@]}" --set seed="$seed" --set roster_overrides="$OVERRIDES" \
            "${args[@]}" >>"$RUN/$arm.out" 2>&1 &
    fi
    pid_of[$arm]=$!
    echo "$(date +%H:%M:%S) $arm pid ${pid_of[$arm]} (seed $seed, $device, $sim+$torch threads)"
}

mkdir -p "$RUN"
for arm in $ARMS; do
    arm_seed "$arm" >/dev/null
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
