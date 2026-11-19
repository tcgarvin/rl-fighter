#!/usr/bin/env bash
# A learned commander in the station assault at the hand-rule eval's settings
# (../2026-11-19-station-rules: the default "strike of 8", live pilots per slot, the
# other side `unseen`, seed 1119000, one sim and one torch thread a cell), in both roles
# and both readings, then summary.py's table against the hand rules and the verdict.
#
#   lab/runs/2026-11-19-station-commander/eval.sh <commander.pt> [name]
#
# Writes eval/<name>/<as>_<role>_learned.json and eval/<name>/summary.md (name defaults
# to <arm>_<update> from the checkpoint path). Four cells at once under nice 19 (carrier
# 1,024 matches a role, about 30 min a cell on an idle core; convoy 512). Finished cells
# are kept on a rerun. Env: N (1024), NCONVOY (512), PY, CHECKPOINT_ROOT (the checkout
# holding the pilots' weights).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
[[ $# -ge 1 ]] || { echo "usage: $0 <commander.pt> [name]" >&2; exit 2; }
CKPT="$(realpath "$1")"
[[ -f $CKPT ]] || { echo "no commander at $CKPT" >&2; exit 2; }
if [[ $# -ge 2 ]]; then
    NAME=$2
else
    NAME="$(basename "$(dirname "$(dirname "$CKPT")")")_$(basename "$CKPT" .pt | sed 's/^commander_//')"
fi
N=${N:-1024}
NCONVOY=${NCONVOY:-512}
PY=${PY:-/home/timg/code/rl-fighter/.venv/bin/python}
CHECKPOINT_ROOT=${CHECKPOINT_ROOT:-/home/timg/code/rl-fighter}
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
RULES="$ROOT/lab/runs/2026-11-19-station-rules/station_rules.py"
OUT="$HERE/eval/$NAME"
mkdir -p "$OUT"
echo "$CKPT" > "$OUT/commander.txt"

cell() { # <as> <role> <n>
    local out="$OUT/$1_$2_learned.json"
    [[ -f $out ]] && { echo "== have $out"; return; }
    nice -n 19 "$PY" "$RULES" --station-as "$1" --role "$2" --rule learned \
        --commander "$CKPT" --n "$3" --threads 1 --torch-threads 1 \
        --checkpoint-root "$CHECKPOINT_ROOT" --out "$out.tmp" > "$OUT/$1_$2.log" 2>&1
    mv "$out.tmp" "$out"
    cat "$OUT/$1_$2.log"
}
cell carrier defender "$N" &
cell carrier attacker "$N" &
cell convoy defender "$NCONVOY" &
cell convoy attacker "$NCONVOY" &
status=0
for job in $(jobs -p); do wait "$job" || status=1; done
"$PY" "$HERE/summary.py" "$OUT" | tee "$OUT/summary.md"
exit $status
