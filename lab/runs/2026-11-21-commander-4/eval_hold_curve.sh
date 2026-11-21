#!/usr/bin/env bash
# The citadel defender along the hold arms' training, on preflight.sh's seeds and settings
# (512 matches a cell, station_rules.py --rule learned), so every cell pairs match by match
# with preflight/citadel_*: no orders, hold_late, hold_reserve. Written at 08:00 after all
# three hold runs slid from about 0.85 to 0.62 in training, to see the slide in paired
# matches and what it did to launch timing.
#
#   hold_quiet   0 (the start: commander 3 live 197, launch head reset), 10, 30, final
#   hold         0, and the second run's 10 and final (see plan.md: the first run's 10 to 50
#                were overwritten when run.sh restarted it), and the first run's 68
#
# Writes eval/<arm>_<update>/citadel_defender_learned.json, as eval.sh does; finished cells
# are kept. Env: N (512), PY.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
cd "$ROOT"
PY=${PY:-$ROOT/.venv/bin/python}
N=${N:-512}
RULES=$ROOT/lab/runs/2026-11-19-station-rules
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

station_cell() {  # <name> <commander.pt>
    local out="$HERE/eval/$1/citadel_defender_learned.json"
    [[ -f $out ]] && { echo "have $out"; return; }
    mkdir -p "$HERE/eval/$1"
    (cd "$RULES" && STATION_ROSTER=citadel nice -n 19 "$PY" station_rules.py --role defender \
        --rule learned --commander "$2" --n "$N" --threads 1 --torch-threads 1 \
        --out "$out.tmp" > "$HERE/eval/$1/citadel_defender.log" 2>&1) && mv "$out.tmp" "$out"
}
zero() {  # <arm>: update 0 of the arm, its launch head reset as the trainer did it.
    local out=$HERE/eval/${1}_0/commander_0.pt
    [[ -f $out ]] && { echo "$out"; return; }
    mkdir -p "$(dirname "$out")"
    "$PY" - "$HERE/$1/config.json" "$out" <<'EOF'
import json, sys
from pathlib import Path

from spacefight.commander.policy import load_commander, save_commander
from spacefight.commander.train import TrainConfig, initial_actor

config = json.loads(Path(sys.argv[1]).read_text())
fields = TrainConfig.__dataclass_fields__
cfg = TrainConfig(**{k: (tuple(v) if isinstance(v, list) else v)
                     for k, v in config.items() if k in fields})
_, meta = load_commander(Path(cfg.init))
save_commander(Path(sys.argv[2]), initial_actor(cfg), {**meta, "update": 0})
EOF
    echo "$out"
}
last() {  # The last checkpoint of arm $1.
    find "$HERE/$1/checkpoints" -name 'commander_*.pt' -newer "$HERE/$1/config.json" \
        -printf '%f\n' | sort -V | tail -1 | sed 's/^commander_//; s/\.pt$//'
}

CK=$HERE/hold_quiet/checkpoints
HK=$HERE/hold/checkpoints
q_last=$(last hold_quiet)
h_last=$(last hold)
cells=(
    "hold_quiet_0 $(zero hold_quiet)"
    "hold_quiet_10 $CK/commander_10.pt"
    "hold_quiet_30 $CK/commander_30.pt"
    "hold_quiet_$q_last $CK/commander_$q_last.pt"
    "hold_0 $(zero hold)"
    "hold_run2_10 $HK/commander_10.pt"
    "hold_run2_$h_last $HK/commander_$h_last.pt"
    "hold_run1_68 $HK/commander_68.pt"
)
echo "$(date +%H:%M:%S) ${#cells[@]} cells"
for cell in "${cells[@]}"; do
    # shellcheck disable=SC2086
    station_cell $cell &
done
status=0
for job in $(jobs -p); do wait "$job" || status=1; done
echo "$(date +%H:%M:%S) done (status $status)"
exit $status
