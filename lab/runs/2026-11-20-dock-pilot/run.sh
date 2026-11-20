#!/usr/bin/env bash
# Teach learned pilots to dock (plan.md). Two arms, one config, each widening a live
# pilot from 587 to 592 inputs (the dock block) with --init:
#   dock600  followers_school_600  seed 2011  cuda:0
#   dock352  followers_v8_352      seed 2012  cuda:1
# Config: followers_school's (lab/runs/2026-11-14-goto-school/followers_school) with
#   obs_dim 592, new_input_lr_mult 3          the dock block, zero columns at 3x the step
#   dock_bonus 1.0                            the order pay on docking (the sim's is 0.2)
#   commander_stable [live, scripted] [1, 1]  scripted commanders on 0.625 of the
#                                             commanded sides: they recall, learned ones
#                                             never do
#   roster_overrides: drill_share 0.55, drill_dock_share 0.5 (dock drills 0.275 of the
#     draws, calm and threat half each), drill_weights [6, 1, 1] (the other 0.275),
#     commander_p 0.667, mixed_p 0, the parent's mission weights (no station assault in
#     matches: docking at a station is in the drills)
#   checkpoint_every 25
# Then periodic evals (eval.sh QUICK=1, nice 19) on every EVAL_EVERY-th update of each arm
# while it trains, and after the deadline the full evals of each arm's last checkpoint
# and of both parents, and report.md (summary.py report).
#
# Needs a venv with rlf_sim built from this tree (SIM_VERSION 11 with the dock drills:
# rlf_sim.DOCK["bonus"]). An arm that dies before the deadline is started again from its
# last checkpoint (or from the init if it had none), up to MAX_RESTARTS times. Stops by
# SIGTERM at the deadline; each trainer checkpoints after its update. Re-running resumes
# training and skips finished evals.
#
#   Beast:  DEADLINE="2026-11-21 06:30" nohup setsid lab/runs/2026-11-20-dock-pilot/run.sh \
#               > lab/runs/2026-11-20-dock-pilot/run_beast.out 2>&1 &
#   SMOKE=1 nice -n 19 lab/runs/2026-11-20-dock-pilot/run.sh
#       (every stage at tiny sizes into smoke/: 2 updates an arm, CPU, the periodic and
#       final evals and the report; from a worktree add DATA_ROOT=/home/timg/code/rl-fighter
#       for the init weights)
#
# Env: ARMS (default "dock600 dock352"), DEADLINE (a `date -d` string, required outside
# SMOKE), N_UPDATES (6000, an upper bound; the deadline ends the run), SIM_THREADS and
# TORCH_THREADS (3 each; per arm SIM_THREADS_<arm>, TORCH_THREADS_<arm>), DEVICE_<arm>
# (update_device; defaults dock600=cuda:0, dock352=cuda:1; SMOKE: cpu), MAX_RESTARTS (3),
# EVAL_EVERY (500 updates; 0 turns the periodic evals off), EVAL_THREADS (2), DATA_ROOT
# (the checkout holding the init and pool checkpoints; default this one), FINAL (1: run
# the final evals and the report after training; 0 skips them).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-20-dock-pilot
SOURCE=lab/runs/2026-11-14-goto-school/followers_school
DATA_ROOT=${DATA_ROOT:-$ROOT}
PY=.venv/bin/python
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"dock600 dock352"}
MAX_RESTARTS=${MAX_RESTARTS:-3}
EVAL_THREADS=${EVAL_THREADS:-2}
FINAL=${FINAL:-1}
[[ -f $SOURCE/config.yaml ]] || { echo "missing $SOURCE/config.yaml" >&2; exit 2; }
"$PY" -c 'import rlf_sim, sys; sys.exit(0 if rlf_sim.SIM_VERSION >= 11 and "bonus" in rlf_sim.DOCK else 1)' \
    || { echo "rlf_sim lacks the dock drills (SIM_VERSION 11, DOCK['bonus']); rebuild it:" \
              "uv run maturin develop -m crates/sim-py/Cargo.toml --release" >&2; exit 2; }

arm_init() {  # The parent checkpoint (relative to DATA_ROOT) and its eval name.
    case $1 in
        dock600) echo "lab/runs/2026-11-14-goto-school/followers_school/checkpoints/ppo_bc_600.pt" ;;
        dock352) echo "lab/runs/2026-11-12-pilots-v8/followers_v8/checkpoints/ppo_bc_352.pt" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_parent() {
    case $1 in
        dock600) echo parent600 ;;
        dock352) echo parent352 ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_seed() {
    case $1 in
        dock600) echo 2011 ;;
        dock352) echo 2012 ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_device() {
    local var="DEVICE_$1" default
    case $1 in
        dock600) default=cuda:0 ;;
        dock352) default=cuda:1 ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
    [[ $SMOKE == 1 ]] && default=cpu
    echo "${!var:-$default}"
}
arm_threads() {  # $1 arm, $2 SIM or TORCH
    local var="${2}_THREADS_$1" base="${2}_THREADS" fallback=3
    [[ $SMOKE == 1 ]] && fallback=1
    echo "${!var:-${!base:-$fallback}}"
}
latest_update() {  # The highest update with a checkpoint in run directory $1, or empty.
    [[ -d $1/checkpoints ]] || return 0
    find "$1/checkpoints" -name 'ppo_bc_*.pt' -printf '%f\n' \
        | sed 's/ppo_bc_\([0-9]*\)\.pt/\1/' | sort -n | tail -1
}

for arm in $ARMS; do
    init=$DATA_ROOT/$(arm_init "$arm")
    [[ -f $init ]] || { echo "missing $init (rsync the parent's weights)" >&2; exit 2; }
done

if [[ $SMOKE == 1 ]]; then
    RUN=$HERE/smoke
    DEADLINE=${DEADLINE:-"+40 minutes"}
    EVAL_EVERY=${EVAL_EVERY:-2}
    EVAL_ENV=(SMOKE=1)
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"2026-11-21 06:30\"" >&2; exit 2; }
    RUN=$HERE
    EVAL_EVERY=${EVAL_EVERY:-500}
    EVAL_ENV=(QUICK=1)
fi
deadline=$(date -d "$DEADLINE" +%s)
(( deadline > $(date +%s) )) || { echo "DEADLINE $DEADLINE is already past" >&2; exit 2; }

OVERRIDES='{"drill_share":0.55,"drill_dock_share":0.5,"drill_dock_threat_share":0.5,'
OVERRIDES+='"drill_weights":[6,1,1],"commander_p":0.667,"mixed_p":0.0}'

# followers_school's config as --set KEY=JSON pairs (JSON is YAML), minus what this run
# sets itself: init and tag come from --init, the rest is listed below.
source_sets() {
    "$PY" - "$SOURCE/config.yaml" <<'EOF'
import json, sys, yaml
skip = {"init", "tag", "seed", "roster_overrides", "checkpoint_every", "n_updates",
        "sim_threads", "torch_threads", "update_device", "actor_frozen_until",
        "obs_dim", "new_input_lr_mult", "commander_stable", "commander_weights",
        "dock_bonus"}
for key, value in yaml.safe_load(open(sys.argv[1])).items():
    if key not in skip:
        print(f"{key}={json.dumps(value)}")
EOF
}

declare -A pid_of restarts n_updates
start_arm() {
    local arm=$1 dir=$RUN/$1 seed device sim torch init
    seed=$(arm_seed "$arm")
    device=$(arm_device "$arm")
    sim=$(arm_threads "$arm" SIM)
    torch=$(arm_threads "$arm" TORCH)
    init=$DATA_ROOT/$(arm_init "$arm")
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
        "$PY" -m spacefight.train_spike ppo --run-dir "$dir" --init "$init" \
            "${sets[@]}" --set seed="$seed" --set roster_overrides="$OVERRIDES" \
            --set obs_dim=592 --set new_input_lr_mult=3 --set dock_bonus=1.0 \
            --set 'commander_stable=[live, scripted]' --set 'commander_weights=[1, 1]' \
            "${args[@]}" >>"$RUN/$arm.out" 2>&1 &
    fi
    pid_of[$arm]=$!
    echo "$(date +%H:%M:%S) $arm pid ${pid_of[$arm]} (seed $seed, $device, $sim+$torch threads)"
}

# One checkpoint's evals (eval.sh), into $RUN/eval/<name>; $1 checkpoint, $2 name, then
# extra env for eval.sh (QUICK=1 or SMOKE=1).
eval_ckpt() {
    local ckpt=$1 name=$2; shift 2
    env "$@" CKPT="$ckpt" NAME="$name" OUT="$RUN/eval/$name" THREADS="$EVAL_THREADS" \
        DATA_ROOT="$DATA_ROOT" "$HERE/eval.sh" >>"$RUN/eval.out" 2>&1 \
        || echo "$(date +%H:%M:%S) eval of $name failed (see $RUN/eval.out)"
}

# The periodic evals: every EVAL_EVERY-th checkpoint of each arm, one at a time, while
# training runs (nice 19, EVAL_THREADS threads). Each is tried once (its directory's
# .tried); a touched eval/.stop makes the loop take one last look and end.
eval_loop() {
    local last_pass=0 arm path u
    while :; do
        [[ -f $RUN/eval/.stop ]] && last_pass=1
        for arm in $ARMS; do
            [[ -d $RUN/$arm/checkpoints ]] || continue
            for path in "$RUN/$arm"/checkpoints/ppo_bc_*.pt; do
                [[ -f $path ]] || continue
                u=$(basename "$path" .pt); u=${u#ppo_bc_}
                (( u > 0 && u % EVAL_EVERY == 0 )) || continue
                [[ -e $RUN/eval/${arm}_$u/.tried ]] && continue
                mkdir -p "$RUN/eval/${arm}_$u"
                touch "$RUN/eval/${arm}_$u/.tried"
                echo "$(date +%H:%M:%S) periodic eval ${arm}_$u"
                eval_ckpt "$path" "${arm}_$u" "${EVAL_ENV[@]}"
            done
        done
        (( last_pass )) && break
        sleep 60 &
        wait $! || true
    done
}

mkdir -p "$RUN/eval"
rm -f "$RUN/eval/.stop"
for arm in $ARMS; do
    n_updates[$arm]=${N_UPDATES:-6000}
    if [[ $SMOKE == 1 ]]; then
        done_so_far=$(latest_update "$RUN/$arm")
        n_updates[$arm]=$(( ${done_so_far:-0} + 2 ))
    fi
    restarts[$arm]=0
    start_arm "$arm"
done
eval_pid=
if (( EVAL_EVERY > 0 )); then
    eval_loop &
    eval_pid=$!
fi

stopping=0
signalled=0
stop() {
    stopping=1
    kill -TERM "${pid_of[@]}" 2>/dev/null || true
}
# A signal stops the trainers (each checkpoints after its update) and skips the final
# evals; the deadline does not. Re-running resumes, and with an arm's update count
# reached it goes straight to the evals.
on_signal() {
    signalled=1
    stop
}
trap on_signal TERM INT
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
for arm in $ARMS; do wait "${pid_of[$arm]}" 2>/dev/null || true; done
echo "$(date +%H:%M:%S) done: PPO"
# The periodic evals take a last look (the newest checkpoints) and end; on a signal they
# stop at once.
if [[ -n $eval_pid ]]; then
    if (( signalled )); then
        pkill -TERM -P "$eval_pid" 2>/dev/null || true
        kill -TERM "$eval_pid" 2>/dev/null || true
    else
        touch "$RUN/eval/.stop"
    fi
    wait "$eval_pid" 2>/dev/null || true
    rm -f "$RUN/eval/.stop"
fi
(( FINAL && ! signalled )) || exit 0

# The final evals at full size (SMOKE: tiny): each arm's last checkpoint and both
# parents, then the report.
FINAL_ENV=()
[[ $SMOKE == 1 ]] && FINAL_ENV=(SMOKE=1)
for arm in $ARMS; do
    parent=$(arm_parent "$arm")
    eval_ckpt "$DATA_ROOT/$(arm_init "$arm")" "$parent" "${FINAL_ENV[@]}"
    last=$(latest_update "$RUN/$arm")
    [[ -n $last ]] || { echo "$arm has no checkpoint"; continue; }
    eval_ckpt "$RUN/$arm/checkpoints/ppo_bc_$last.pt" "${arm}_final_$last" "${FINAL_ENV[@]}"
done
"$PY" "$HERE/summary.py" report "$RUN" --arms $ARMS | tee "$RUN/report.md"
echo "$(date +%H:%M:%S) done: report $RUN/report.md"
