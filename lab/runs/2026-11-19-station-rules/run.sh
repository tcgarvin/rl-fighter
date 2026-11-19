#!/usr/bin/env bash
# Hand-written commanders in the station assault (SIM_VERSION 9) against no orders:
# results.md. Live pilots (lab/live_pilots.json, weights from the main checkout's
# lab/runs: CHECKPOINT_ROOT), drawn per slot per match. Six chains of one process each
# (1 sim thread, 1 torch thread; inference is ~90% of the time), nice 19: the laptop is
# shared. Every cell plays the same seeds and pilot draws, so cells pair match by match
# (the torch thread count is fixed for that). Finished cells are kept on a rerun.
# analyze.py prints the tables.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
OUT=out
mkdir -p "$OUT"
N="${N:-1024}"         # carrier reading: the baseline and every rule
NCHECK="${NCHECK:-96}" # rule `none` (external, the script's launches ported) per role
NCONVOY="${NCONVOY:-512}"
ROOT="${CHECKPOINT_ROOT:-/home/timg/code/rl-fighter}"
# The checkout's venv with rlf_sim built into it (maturin develop; `uv run` would sync).
PY="${PY:-$HERE/../../../.venv/bin/python}"
# cell <as> <role> <rule> <n>. The baseline is role "check", rule "unseen": the script
# with its orders hidden on both sides. The rule `none` plays the same matches, so
# analyze.py uses the baseline as `none` for both roles; "checksmall" is the baseline at
# NCHECK matches, which the `none` cells must reproduce match for match (torch's
# sampling stream depends on the batch size, so the check compares equal sizes).
cell() {
    local out="$OUT/$1_$2_$3.json" role="$2"
    [[ -f "$out" ]] && { echo "== have $out"; return; }
    [[ "$role" == check* ]] && role=attacker
    nice -n 19 $PY station_rules.py --station-as "$1" --role "$role" --rule "$3" --n "$4" \
        --threads 1 --torch-threads 1 --checkpoint-root "$ROOT" --out "$out.tmp"
    mv "$out.tmp" "$out"
}
chain() { # <log> <cell args>... (groups of four)
    local log="$OUT/$1.log"; shift
    while (($#)); do cell "$1" "$2" "$3" "$4"; shift 4; done >> "$log" 2>&1
}

chain c1 carrier check unseen "$N"         carrier attacker rally_release "$N" &
chain c2 carrier attacker scripted "$N"    carrier attacker bomber_only "$N" &
chain c3 carrier attacker escort_bombers "$N" carrier attacker carrier_push "$N" &
chain c4 carrier defender scripted "$N"    carrier defender hold_reserve "$N" &
chain c5 carrier defender hold_late "$N"   carrier defender intercept_bombers "$N" &
chain c6 carrier defender hunt_bombers "$N" \
    carrier attacker none "$NCHECK" carrier defender none "$NCHECK" &
wait
# Second round. hold_never was added once the first showed that launch timing matters
# (hold_late), with the size-matched baseline for the identity check. The convoy reading (the station's side reads as a convoy defender): the baseline, the
# script and the best rule of each role on the carrier reading.
BEST_ATTACKER="${BEST_ATTACKER:-carrier_push}"
BEST_DEFENDER="${BEST_DEFENDER:-hold_late}"
chain c7 carrier defender hold_never "$N" carrier checksmall unseen "$NCHECK" &
chain v1 convoy check unseen "$NCONVOY" &
chain v2 convoy attacker scripted "$NCONVOY" &
chain v3 convoy attacker "$BEST_ATTACKER" "$NCONVOY" &
chain v4 convoy defender scripted "$NCONVOY" &
chain v5 convoy defender "$BEST_DEFENDER" "$NCONVOY" &
wait
cat "$OUT"/*.log
$PY analyze.py
