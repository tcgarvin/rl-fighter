#!/usr/bin/env bash
# Fleet pilot v1 (plan.md): fleet DAgger for two inits, then two PPO arms over
# mixed 1-4-a-side fleets run concurrently, then the gate evals.
#
#   nohup lab/runs/2026-10-30-fleet-pilot/run.sh > lab/runs/2026-10-30-fleet-pilot/run.out 2>&1 &
#   lab/runs/2026-10-30-fleet-pilot/run.sh eval gates     # just these stages
#   SMOKE=1 lab/runs/2026-10-30-fleet-pilot/run.sh        # tiny sizes, into smoke/
#
# Stages: baseline dagger_fresh dagger_warm ppo eval gates. Every stage skips work
# whose output exists; PPO arms resume from their latest checkpoint; an unfinished
# DAgger directory is moved aside (never deleted) and redone. Nothing here deletes
# a checkpoint. Logs: <run>/<stage or arm>.out, PPO's <run>/<arm>/log.jsonl.
#
# Knobs (environment): THREADS (12, DAgger / evals), ARM_THREADS (6 sim + 6 torch
# per PPO arm, two arms at once), N_UPDATES (600), EVAL_UPDATES ("200 400 600"),
# CHAMP_V3 (the v3 duel champion), PY, RUN, SMOKE.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-10-30-fleet-pilot
if [[ -z "${PY:-}" ]]; then
    if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY="uv run python"; fi
fi
# shellcheck disable=SC2206
PY=($PY)
CHAMP_V3=${CHAMP_V3:-lab/runs/2026-10-29-collision-damage/arm_a_rl/checkpoints/ppo_bc_600.pt}
SMOKE=${SMOKE:-0}

if [[ $SMOKE == 1 ]]; then
    RUN=${RUN:-$HERE/smoke}
    THREADS=${THREADS:-4}
    ARM_THREADS=${ARM_THREADS:-2}
    N_UPDATES=${N_UPDATES:-4}
    EVAL_UPDATES=${EVAL_UPDATES:-"2 4"}
    N_EVAL=2
    DUEL_N=16
    DAGGER_ARGS=(--base-rows 30000 --rounds 1 --rows-per-round 30000 --max-rows 60000
        --epochs 1 --finetune-epochs 1 --n-envs 32 --fleet-n-per-roster 2 --duel-n 16)
    PPO_SIZE=(--n-envs 16 --n-steps 32 --set checkpoint_every=2 --set minibatch=256
        --set critic_warmup_updates=1 --set env_warmup_steps=60)
else
    RUN=${RUN:-$HERE}
    THREADS=${THREADS:-12}
    ARM_THREADS=${ARM_THREADS:-6}
    N_UPDATES=${N_UPDATES:-600}
    EVAL_UPDATES=${EVAL_UPDATES:-"200 400 600"}
    N_EVAL=64
    DUEL_N=512
    # 3 M DART rows + 3 rounds x 2 M on-policy rows (about 7.5 GB of float16 obs).
    DAGGER_ARGS=(--base-rows 3000000 --rounds 3 --rows-per-round 2000000
        --max-rows 9000000 --n-envs 128 --fleet-n-per-roster 32 --duel-n 256)
    PPO_SIZE=()
fi
export RUN THREADS N_EVAL DUEL_N CHAMP_V3 SMOKE
BANDS='[[0,1,0,0],[200,0.5,0.3,0.2],[400,0.4,0.3,0.3]]'
mkdir -p "$RUN"

log() { printf '\n== %s %s\n' "$(date +%H:%M:%S)" "$*"; }

need_champion() {
    if [[ ! -f $CHAMP_V3 ]]; then
        echo "v3 champion not found at $CHAMP_V3 (set CHAMP_V3)" >&2
        exit 2
    fi
}

stage_baseline() {
    log "baseline: script vs script on the fleet suite; the v3 champion's duel and fleets"
    need_champion
    "$HERE/eval.sh" baseline
}

dagger_run() {  # dagger_run NAME EXTRA_ARGS...: one fleet DAgger, skipped if done
    local name=$1
    shift
    local dir=$RUN/$name
    if [[ -f $dir/best.pt ]]; then
        echo "skip: $dir/best.pt exists"
        return
    fi
    if [[ -d $dir ]]; then
        local aside
        aside="$dir.partial-$(date +%Y%m%d-%H%M%S)"
        echo "moving the unfinished $dir aside to $aside"
        mv "$dir" "$aside"
    fi
    "${PY[@]}" -m spacefight.train_spike dagger --out "$dir" --rosters fleet_v1 \
        --seed 0 --threads "$THREADS" "${DAGGER_ARGS[@]}" "$@" >>"$RUN/$name.out" 2>&1
    tail -n 1 "$RUN/$name.out"
}

stage_dagger_fresh() {
    log "DAgger from fresh BC on fleet DART rows ($THREADS threads)"
    dagger_run dagger_fresh
}

stage_dagger_warm() {
    log "DAgger from the v3 duel champion ($THREADS threads)"
    need_champion
    dagger_run dagger_warm --init "$CHAMP_V3"
}

ppo_arm() {  # ppo_arm NAME INIT: new run, or resume an existing one
    local name=$1 init=$2
    local dir=$RUN/$name
    if [[ -f $dir/config.yaml ]]; then
        "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --resume \
            --n-updates "$N_UPDATES"
    else
        "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --init "$init" \
            --n-updates "$N_UPDATES" --seed 0 \
            --sim-threads "$ARM_THREADS" --torch-threads "$ARM_THREADS" \
            --set rosters=fleet_v1 --set critic=fleet \
            --set "opponent_bands=$BANDS" --set beta_decay_end=300 \
            "${PPO_SIZE[@]}"
    fi
}

stage_ppo() {
    log "PPO arm_fresh and arm_warm concurrently, $ARM_THREADS sim + $ARM_THREADS torch threads each"
    local init
    for init in "$RUN/dagger_fresh/best.pt" "$RUN/dagger_warm/best.pt"; do
        [[ -f $init ]] || { echo "missing $init: run the dagger stages first" >&2; exit 2; }
    done
    ppo_arm arm_fresh "$RUN/dagger_fresh/best.pt" >>"$RUN/arm_fresh.out" 2>&1 &
    local fresh=$!
    ppo_arm arm_warm "$RUN/dagger_warm/best.pt" >>"$RUN/arm_warm.out" 2>&1 &
    local warm=$!
    # SIGTERM / Ctrl-C reach both trainers, which checkpoint after the update.
    trap 'kill -TERM $fresh $warm 2>/dev/null || true' TERM INT
    local status=0
    wait "$fresh" || status=$?
    wait "$warm" || status=$?
    wait # a signal interrupts the waits above; let both trainers finish saving
    trap - TERM INT
    tail -n 1 "$RUN/arm_fresh.out" "$RUN/arm_warm.out"
    return "$status"
}

stage_eval() {
    log "gate evals (eval.sh), $THREADS threads"
    "$HERE/eval.sh" fresh_dagger "$RUN/dagger_fresh/best.pt"
    "$HERE/eval.sh" warm_dagger "$RUN/dagger_warm/best.pt"
    local u arm
    for u in $EVAL_UPDATES; do
        for arm in fresh warm; do
            local ckpt=$RUN/arm_$arm/checkpoints/ppo_bc_$u.pt
            if [[ -f $ckpt ]]; then
                "$HERE/eval.sh" "${arm}_$u" "$ckpt" "$RUN/dagger_$arm/best.pt"
            else
                echo "skip ${arm}_$u: $ckpt not found"
            fi
        done
    done
}

stage_gates() {
    log "gates (plan.md §5)"
    "${PY[@]}" "$HERE/gates.py" --run "$RUN"
}

STAGES=(baseline dagger_fresh dagger_warm ppo eval gates)
if [[ $# -gt 0 ]]; then STAGES=("$@"); fi
for stage in "${STAGES[@]}"; do
    if ! declare -F "stage_$stage" >/dev/null; then
        echo "unknown stage: $stage (known: baseline dagger_fresh dagger_warm ppo eval gates)" >&2
        exit 2
    fi
done
for stage in "${STAGES[@]}"; do
    "stage_$stage"
done
log "done: ${STAGES[*]}"
