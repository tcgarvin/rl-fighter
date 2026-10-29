#!/usr/bin/env bash
# Learnability spike, as it was actually run (2026-10-28, interactively in the
# evening rather than on the 03:00 schedule of plan.md §5). See results.md
# "Deviations from plan" for why DAgger, 1200 updates and the scaled bands.
#
#   lab/runs/2026-10-28-learnability-spike/run.sh            # every stage in order
#   lab/runs/2026-10-28-learnability-spike/run.sh eval report # just these stages
#
# Stages: baseline bc bc_eval dagger ppo eval report. Every stage skips work whose
# output already exists (PPO resumes from its latest checkpoint), and nothing here
# deletes a checkpoint. Run from anywhere; paths are relative to the repo root, as
# the PPO config.yaml files record them.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
RUN=lab/runs/2026-10-28-learnability-spike
if [[ -z "${PY:-}" ]]; then
    if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python; else PY="uv run python"; fi
fi
# shellcheck disable=SC2206
PY=($PY)
BANDS='[[0,1,0,0],[360,0.5,0.3,0.2],[720,0.3,0.4,0.3]]'  # plan §4.2 bands × 0.6

log() { printf '\n== %s %s\n' "$(date +%H:%M:%S)" "$*"; }

duel() {  # duel OUT_JSON ARGS...: one plan §6.1 eval unless OUT_JSON exists
    local out=$1
    shift
    if [[ -f $out ]]; then
        echo "skip: $out exists"
        return
    fi
    "${PY[@]}" -m spacefight.eval.duel --n 512 --seed 100000 --n-threads 12 \
        --out "$out" "$@"
}

stage_baseline() {
    log "baseline: script vs script (the × script denominators)"
    duel "$RUN/eval/script_vs_script.json" --a script --b script
}

stage_bc() {
    log "BC: 2 M DART rows, 8 epochs, 12 threads"
    if [[ -f $RUN/bc/bc.pt ]]; then
        echo "skip: $RUN/bc/bc.pt exists"
        return
    fi
    "${PY[@]}" -m spacefight.train_spike bc --rows 2000000 --out "$RUN/bc" \
        --seed 0 --threads 12
}

stage_bc_eval() {
    log "BC vs script, sampled and argmax"
    duel "$RUN/eval/bc_vs_script.json" --a "$RUN/bc/bc.pt" --b script
    duel "$RUN/eval/bc_argmax_vs_script.json" --a "$RUN/bc/bc.pt" --b script --argmax
}

stage_dagger() {
    # Added after BC won 0.6 % vs the script (compounding error); not in plan.md.
    log "DAgger: 3 rounds x 2 M on-policy rows on top of bc.pt, 4 threads"
    if [[ -f $RUN/bc_dagger/best.pt ]]; then
        echo "skip: $RUN/bc_dagger/best.pt exists"
        return
    fi
    "${PY[@]}" -m spacefight.train_spike dagger --out "$RUN/bc_dagger" \
        --init "$RUN/bc/bc.pt" --threads 4 --rounds 3 --rows-per-round 2000000 \
        --duel-argmax
}

ppo_run() {  # ppo_run NAME INIT EXTRA_ARGS...: new run, or resume an existing one
    local name=$1 init=$2
    shift 2
    local dir=$RUN/$name
    if [[ -f $dir/config.yaml ]]; then
        "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --resume
    else
        "${PY[@]}" -m spacefight.train_spike ppo --run-dir "$dir" --init "$init" \
            --n-updates 1200 --seed 0 --sim-threads 6 --torch-threads 6 \
            --set "opponent_bands=$BANDS" "$@"
    fi
}

stage_ppo() {
    log "PPO-BC and PPO-scratch concurrently, 6 sim + 6 torch threads each"
    ppo_run ppo_scratch scratch >>"$RUN/ppo_scratch.out" 2>&1 &
    local scratch=$!
    ppo_run ppo_bc "$RUN/bc_dagger/best.pt" --set beta_decay_end=420 \
        >>"$RUN/ppo_bc.out" 2>&1 &
    local bc=$!
    # SIGTERM / Ctrl-C reach both trainers, which checkpoint after the update.
    trap 'kill -TERM $scratch $bc 2>/dev/null || true' TERM INT
    local status=0
    wait "$scratch" || status=$?
    wait "$bc" || status=$?
    wait # a signal interrupts the waits above; let both trainers finish saving
    trap - TERM INT
    tail -n 1 "$RUN/ppo_scratch.out" "$RUN/ppo_bc.out"
    return "$status"
}

stage_eval() {
    log "eval matrix (plan §6.2, adapted) + health (§6.3), 12 threads"
    "${PY[@]}" -m tools.spike_eval_matrix --run-dir "$RUN" --threads 12
}

stage_report() {
    log "results.md"
    "${PY[@]}" -m tools.lab_report --run-dir "$RUN"
}

STAGES=(baseline bc bc_eval dagger ppo eval report)
if [[ $# -gt 0 ]]; then STAGES=("$@"); fi
for stage in "${STAGES[@]}"; do
    if ! declare -F "stage_$stage" >/dev/null; then
        echo "unknown stage: $stage (known: baseline bc bc_eval dagger ppo eval report)" >&2
        exit 2
    fi
done
for stage in "${STAGES[@]}"; do
    "stage_$stage"
done
