#!/usr/bin/env bash
# Preflight for commander 4's hold arm: do the station-rules defender hand rules
# still beat no orders at SIM_VERSION 11 (recalls and relaunches), on the v9 station
# ("strike of 8", where they were measured) and on the citadel the live page plays?
# Six cells, one process each, nice 19; cells of one roster pair match by match.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
RULES="$HERE/../2026-11-19-station-rules"
PY="$HERE/../../../.venv/bin/python"
N="${N:-512}"
OUT="$HERE/preflight"
mkdir -p "$OUT"
cell() { # <roster> <role> <rule>
    local out="$OUT/$1_$2_$3.json" role="$2"
    [[ -f "$out" ]] && { echo "have $out"; return; }
    [[ "$role" == check ]] && role=attacker
    (cd "$RULES" && STATION_ROSTER="$1" nice -n 19 "$PY" station_rules.py --role "$role" \
        --rule "$3" --n "$N" --threads 1 --torch-threads 1 --out "$out.tmp" \
        > "$OUT/$1_$2_$3.log" 2>&1) && mv "$out.tmp" "$out"
}
for roster in "strike of 8" citadel; do
    cell "$roster" check unseen &
    cell "$roster" defender hold_late &
    cell "$roster" defender hold_reserve &
done
wait
echo done
