#!/usr/bin/env bash
# Horizon and bombers (plan.md). Two arms from one parent, followers_dock_v8_2676
# (lab/runs/2026-11-20-dock-pilot/dock352 update 2676, 592 inputs, in the live ten), on
# one config that differs only in the discount:
#   h999  gamma 0.999 (a reward 30 s away weighs 0.41; at the parent's 0.995, 0.011)
#                                                          seed 2411  cuda:0
#   h995  gamma 0.995 (the parent's)                       seed 2412  cuda:1
# Config: the parent's own (parent_config.yaml, its dock352 config.yaml), with
#   roster_overrides: the parent's (drill_share 0.55, drill_weights [6, 1, 1],
#     drill_dock_share 0.5, drill_dock_threat_share 0.5, commander_p 0.667, mixed_p 0)
#     plus bomber_share 0.2 and drill_bomber_share 0.2; mission_weights and
#     citadel_share at the pilots_v1 defaults (station assault, with its three bombers,
#     a fifth of matches)
#   teammate_share 0.3, teammate_pool the live ten (lab/live_pilots.json): in matches,
#     each of the learner side's strike craft is a live pilot with chance 0.3
#   critic_warmup_updates 50 (both arms: the critic learns the new discount, the
#     bombers and the teammates before the actor moves)
#   checkpoint_every 25
# Then periodic evals (eval.sh QUICK=1, nice 19) on every EVAL_EVERY-th update of each arm
# while it trains, and after the deadline the full evals of each arm's last checkpoint
# and report.md (summary.py report). The parent's full eval (eval/parent_dock2676) ran
# before training. The report gives measurements only; nothing in this run passes or
# fails a pilot.
#
# An arm that dies before the deadline is started again from its last checkpoint (or
# from the init if it had none), up to MAX_RESTARTS times. Stops by SIGTERM at the
# deadline; each trainer checkpoints after its update. Re-running resumes training and
# skips finished evals.
#
#   Beast:  DEADLINE="2026-11-25 06:00" nohup setsid lab/runs/2026-11-24-horizon-bombers/run.sh \
#               > lab/runs/2026-11-24-horizon-bombers/run_beast.out 2>&1 &
#   SMOKE=1 nice -n 19 lab/runs/2026-11-24-horizon-bombers/run.sh
#       (every stage at tiny sizes into smoke/: 2 updates an arm, CPU, the periodic and
#       final evals, the parent's eval and the report)
#
# Env: ARMS (default "h999 h995"), DEADLINE (a `date -d` string, required outside
# SMOKE), N_UPDATES (20000, an upper bound; the deadline ends the run), SIM_THREADS and
# TORCH_THREADS (3 each; per arm SIM_THREADS_<arm>, TORCH_THREADS_<arm>), DEVICE_<arm>
# (update_device; defaults h999=cuda:0, h995=cuda:1; SMOKE: cpu), MAX_RESTARTS (3),
# EVAL_EVERY (1000 updates; 0 turns the periodic evals off), EVAL_THREADS (2, the
# periodic evals), FINAL_THREADS (5 per final eval; two run at once), DATA_ROOT (the
# checkout holding the init, pool, teammate and base checkpoints; default this one), PY
# (the venv's python; default this checkout's .venv), FINAL (1: run the final evals and
# the report after training; 0 skips them).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-24-horizon-bombers
SOURCE_CONFIG=$HERE/parent_config.yaml
PARENT=lab/runs/2026-11-20-dock-pilot/dock352/checkpoints/ppo_bc_2676.pt
DATA_ROOT=${DATA_ROOT:-$ROOT}
PY=${PY:-.venv/bin/python}
export PYTHONPATH=$ROOT
SMOKE=${SMOKE:-0}
ARMS=${ARMS:-"h999 h995"}
MAX_RESTARTS=${MAX_RESTARTS:-3}
EVAL_THREADS=${EVAL_THREADS:-2}
FINAL=${FINAL:-1}
[[ -f $SOURCE_CONFIG ]] || { echo "missing $SOURCE_CONFIG" >&2; exit 2; }
"$PY" -c 'import rlf_sim, sys; sys.exit(0 if rlf_sim.SIM_VERSION >= 11 and "bonus" in rlf_sim.DOCK else 1)' \
    || { echo "rlf_sim lacks the dock drills (SIM_VERSION 11, DOCK['bonus']); rebuild it:" \
              "uv run maturin develop -m crates/sim-py/Cargo.toml --release" >&2; exit 2; }

arm_init() {  # The parent checkpoint (relative to DATA_ROOT); both arms share it.
    case $1 in
        h999 | h995) echo "$PARENT" ;;
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
arm_seed() {
    case $1 in
        h999) echo 2411 ;;
        h995) echo 2412 ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
arm_device() {
    local var="DEVICE_$1" default
    case $1 in
        h999) default=cuda:0 ;;
        h995) default=cuda:1 ;;
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
    DEADLINE=${DEADLINE:-"+60 minutes"}
    EVAL_EVERY=${EVAL_EVERY:-2}
    EVAL_ENV=(SMOKE=1 QUICK=1)
    FINAL_THREADS=${FINAL_THREADS:-1}
else
    [[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE, e.g. DEADLINE=\"2026-11-22 06:00\"" >&2; exit 2; }
    RUN=$HERE
    EVAL_EVERY=${EVAL_EVERY:-1000}
    EVAL_ENV=(QUICK=1)
    FINAL_THREADS=${FINAL_THREADS:-5}
fi
deadline=$(date -d "$DEADLINE" +%s)
(( deadline > $(date +%s) )) || { echo "DEADLINE $DEADLINE is already past" >&2; exit 2; }

# The parent's roster overrides plus the bombers.
OVERRIDES=$("$PY" - "$SOURCE_CONFIG" <<'EOF'
import json, sys, yaml
overrides = yaml.safe_load(open(sys.argv[1]))["roster_overrides"]
overrides.update({"bomber_share": 0.2, "drill_bomber_share": 0.2})
print(json.dumps(overrides))
EOF
)
# The live ten's checkpoints under DATA_ROOT, as a JSON list: the teammate pool.
TEAMMATES=$("$PY" - "$DATA_ROOT" <<'EOF'
import json, sys
from pathlib import Path
from spacefight.commander.pilots import live_pilot_checkpoints
pilots = live_pilot_checkpoints(Path("lab/live_pilots.json"), Path(sys.argv[1]))
print(json.dumps([str(path) for _, path in pilots]))
EOF
)

# The parent's config as --set KEY=JSON pairs (JSON is YAML), minus what this run sets
# itself: init and tag come from --init, the rest is listed below.
source_sets() {
    "$PY" - "$SOURCE_CONFIG" <<'EOF'
import json, sys, yaml
skip = {"init", "tag", "seed", "roster_overrides", "checkpoint_every", "n_updates",
        "sim_threads", "torch_threads", "update_device", "actor_frozen_until", "gamma",
        "critic_warmup_updates", "teammate_pool", "teammate_share"}
for key, value in yaml.safe_load(open(sys.argv[1])).items():
    if key not in skip:
        print(f"{key}={json.dumps(value)}")
EOF
}

declare -A pid_of restarts n_updates
start_arm() {
    local arm=$1 dir=$RUN/$1 seed device sim torch init gamma
    seed=$(arm_seed "$arm")
    gamma=$(arm_gamma "$arm")
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
            --set gamma="$gamma" --set critic_warmup_updates=50 \
            --set teammate_share=0.3 --set teammate_pool="$TEAMMATES" \
            "${args[@]}" >>"$RUN/$arm.out" 2>&1 &
    fi
    pid_of[$arm]=$!
    echo "$(date +%H:%M:%S) $arm pid ${pid_of[$arm]} (seed $seed, $device, $sim+$torch threads)"
}

# One checkpoint's evals (eval.sh), into $RUN/eval/<name>; $1 checkpoint, $2 name, $3
# threads, then extra env for eval.sh (QUICK=1 and/or SMOKE=1).
eval_ckpt() {
    local ckpt=$1 name=$2 threads=$3; shift 3
    mkdir -p "$RUN/eval/$name"
    env "$@" CKPT="$ckpt" NAME="$name" OUT="$RUN/eval/$name" THREADS="$threads" \
        DATA_ROOT="$DATA_ROOT" PY="$PY" "$HERE/eval.sh" >>"$RUN/eval/$name/eval.out" 2>&1 \
        || echo "$(date +%H:%M:%S) eval of $name failed (see $RUN/eval/$name/eval.out)"
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
                eval_ckpt "$path" "${arm}_$u" "$EVAL_THREADS" "${EVAL_ENV[@]}"
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
    n_updates[$arm]=${N_UPDATES:-20000}
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

# The final evals at full size (SMOKE: tiny): each arm's last checkpoint, side by side
# (FINAL_THREADS each; training is over, so the machine is theirs), then the report.
# The parent's full eval (eval/parent_dock2676) ran before training; a smoke measures
# it here at its tiny sizes.
FINAL_ENV=()
[[ $SMOKE == 1 ]] && FINAL_ENV=(SMOKE=1)
final_pids=()
if [[ $SMOKE == 1 ]]; then
    eval_ckpt "$DATA_ROOT/$PARENT" parent_dock2676 "$FINAL_THREADS" "${FINAL_ENV[@]}" &
    final_pids+=($!)
fi
for arm in $ARMS; do
    last=$(latest_update "$RUN/$arm")
    [[ -n $last ]] || { echo "$arm has no checkpoint"; continue; }
    eval_ckpt "$RUN/$arm/checkpoints/ppo_bc_$last.pt" "${arm}_final_$last" \
        "$FINAL_THREADS" "${FINAL_ENV[@]}" &
    final_pids+=($!)
done
echo "$(date +%H:%M:%S) final evals: ${#final_pids[@]} at once"
for p in "${final_pids[@]}"; do wait "$p" || true; done
"$PY" "$HERE/summary.py" report "$RUN" --arms $ARMS | tee "$RUN/report.md"
echo "$(date +%H:%M:%S) done: report $RUN/report.md"
