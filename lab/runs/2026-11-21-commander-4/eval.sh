#!/usr/bin/env bash
# The morning measures of plan.md, for each arm's last checkpoint (or the ones named).
#
#   hold      the citadel defender against unseen, 512 matches, on preflight.sh's seeds and
#             settings (station_rules.py --rule learned, carrier reading), so each cell pairs
#             match by match with preflight/citadel_*: no orders, hold_late, hold_reserve.
#             Also update 0: the same start (commander 3 live 197) with the launch head
#             reset as the trainer did it, to tell what was learned from what the prior gave.
#   kite      spacefight.commander.eval against unseen, 384 a mission, over its own two
#   noattack  pilots and over the live ten; and the scripted commander over the same pilots
#             against unseen, for scale.
#
#   lab/runs/2026-11-21-commander-4/eval.sh            # every arm's latest checkpoint
#   ARMS="hold" lab/runs/2026-11-21-commander-4/eval.sh
#
# Writes eval/<name>/... Finished cells are kept on a rerun. Env: ARMS ("hold kite
# noattack"; hold_quiet too), N (512, hold), N_PER_MISSION (384), THREADS (3 a commander eval), PY.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/../../.." && pwd)"
cd "$ROOT"
PY=${PY:-$ROOT/.venv/bin/python}
ARMS=${ARMS:-"hold hold_quiet kite noattack"}
N=${N:-512}
N_PER_MISSION=${N_PER_MISSION:-384}
THREADS=${THREADS:-3}
RULES=$ROOT/lab/runs/2026-11-19-station-rules
LIVE=$ROOT/lab/live_pilots.json
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p "$HERE/eval"

latest() {  # The latest checkpoint of arm $1.
    find "$HERE/$1/checkpoints" -name 'commander_*.pt' -printf '%f\n' | sort -V | tail -1 \
        | sed "s|^|$HERE/$1/checkpoints/|"
}
pilots_of() {
    case $1 in
        kite) echo "$HERE/pilots_kite.json" ;;
        noattack) echo "$ROOT/lab/runs/2026-11-15-commander-3/pilots_followers.json" ;;
        *) echo "unknown arm $1" >&2; exit 2 ;;
    esac
}
station_cell() {  # <name> <commander.pt>
    local out="$HERE/eval/$1/citadel_defender_learned.json"
    [[ -f $out ]] && { echo "have $out"; return; }
    mkdir -p "$HERE/eval/$1"
    (cd "$RULES" && STATION_ROSTER=citadel nice -n 19 "$PY" station_rules.py --role defender \
        --rule learned --commander "$2" --n "$N" --threads 1 --torch-threads 1 \
        --out "$out.tmp" > "$HERE/eval/$1/citadel_defender.log" 2>&1) && mv "$out.tmp" "$out"
}
commander_cell() {  # <out.json> <a> <pilots.json>
    [[ -f $1 ]] && { echo "have $1"; return; }
    mkdir -p "$(dirname "$1")"
    nice -n 19 "$PY" -m spacefight.commander.eval --a "$2" --b unseen \
        --n-per-mission "$N_PER_MISSION" --threads "$THREADS" --pilots "$3" \
        --out "$1.tmp" > "${1%.json}.md" 2>&1 && mv "$1.tmp" "$1"
}

for arm in $ARMS; do
    ckpt=$(latest "$arm")
    [[ -n $ckpt ]] || { echo "no checkpoint for $arm" >&2; exit 2; }
    name=${arm}_$(basename "$ckpt" .pt | sed 's/^commander_//')
    echo "$(date +%H:%M:%S) $name"
    case $arm in
        hold | hold_quiet)
            zero=$HERE/eval/${arm}_0/commander_0.pt
            if [[ ! -f $zero ]]; then
                mkdir -p "$(dirname "$zero")"
                "$PY" - "$HERE/$arm/config.json" "$zero" <<'EOF'
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
            fi
            station_cell "$name" "$ckpt" &
            station_cell "${arm}_0" "$zero" &
            ;;
        kite | noattack)
            pilots=$(pilots_of "$arm")
            commander_cell "$HERE/eval/$name/own.json" "$ckpt" "$pilots" &
            commander_cell "$HERE/eval/$name/live.json" "$ckpt" "$LIVE" &
            commander_cell "$HERE/eval/scripted_$arm/own.json" scripted "$pilots" &
            ;;
    esac
done
status=0
for job in $(jobs -p); do wait "$job" || status=1; done
echo "$(date +%H:%M:%S) done (status $status)"
exit $status
