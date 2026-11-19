#!/usr/bin/env bash
# The pairing grid: is a side flown by one commander and one pilot worth more than the
# sum of its parts? Side a is a commander (row) and a pilot flying all its strike craft
# (column), or the per-ship draw (column "mixed"); side b is always the scripted
# commander with every strike craft's pilot drawn ship by ship from the live ten, the
# live page's default side. Then pilot pairs with no commander (unseen v unseen), one
# pilot a side, against what the season's WAR predicts. Every cell of a mission has the
# same seed, so rosters, sides and b's pilots are the same match by match.
# Re-running skips finished cells.
#
#   nohup lab/runs/2026-11-19-pairing/run.sh > lab/runs/2026-11-19-pairing/run.out 2>&1 &
#
# Env: N (96 a mission), N_PAIRS (96), THREADS (8), ROOT_CKPT (the checkout holding the
# weights; default the main checkout of this worktree), PY, SMOKE=1 (tiny sizes into
# smoke/).
#
# Sizing (2026-11-18, the laptop shared with two other evals, load ~20 on 16 cores): a
# cell (one row, one column, three missions) took about 9 minutes at 144 matches a
# mission, so the planned 6 pilots x 4 commanders at 144 would have taken over 4 hours.
# The first column (f995_701) ran at 144; the rest at 96. analyze.py uses each cell's
# first 96 matches of a mission, which are the same rosters, sides and side-b pilots in
# every cell (the draw is made in env order).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
cd "$REPO"
MAIN="$(git worktree list --porcelain | awk '/^worktree /{print $2; exit}')"
ROOT_CKPT=${ROOT_CKPT:-$MAIN}
PY=${PY:-$ROOT_CKPT/.venv/bin/python}
THREADS=${THREADS:-8}
N=${N:-96}
N_PAIRS=${N_PAIRS:-96}
OUT=$HERE/cells
if [[ "${SMOKE:-0}" == 1 ]]; then
  N=48
  N_PAIRS=48
  OUT=$HERE/smoke/cells
fi
C1=$ROOT_CKPT/lab/runs/2026-11-08-commander-1
declare -A COMMANDERS=(
  [scripted]=scripted
  [unseen]=unseen
  [c1_shaped]=$C1/shaped/checkpoints/commander_327.pt
  [c1_outcome]=$C1/outcome/checkpoints/commander_328.pt
)
ROWS=(scripted unseen c1_shaped c1_outcome)
# Four of the live ten (lab/live_pilots.json "follows"): the two best rated, which
# mostly ignore orders (f995_701 follows 11-22% of drills, fighters_pay1_v8_351 26-33%),
# and two that follow them (followers_school_600 70-89%, followers_v8_352 51-76%).
PILOTS=(f995_701 fighters_pay1_v8_351 followers_school_600 followers_v8_352)
MISSIONS=(deathmatch carrier_battle convoy_escort)
# No commander on either side: one pilot a side, a then b.
PAIRS=("f995_701 followers_v8_352" "followers_school_600 followers_v8_352")

cell() { # name a pilot_a b pilot_b n
  local name=$1 a=$2 pa=$3 b=$4 pb=$5 n=$6
  for m in "${MISSIONS[@]}"; do
    local out=$OUT/$m/$name.json
    [[ -f $out ]] && continue
    PYTHONPATH=. nice -n 19 "$PY" "$HERE/grid.py" --mission "$m" --a "$a" --pilot-a "$pa" \
      --b "$b" --pilot-b "$pb" --n "$n" --threads "$THREADS" \
      --checkpoint-root "$ROOT_CKPT" --out "$out" 2>&1 | grep -v Warning || true
    [[ -f $out ]] || { echo "cell $m/$name failed" >&2; exit 1; }
  done
}

echo "start $(date -Is) N=$N N_PAIRS=$N_PAIRS THREADS=$THREADS"
for p in "${PILOTS[@]}"; do
  for c in "${ROWS[@]}"; do
    cell "grid__${c}__${p}" "${COMMANDERS[$c]}" "$p" scripted draw "$N"
  done
done
for c in "${ROWS[@]}"; do
  cell "grid__${c}__mixed" "${COMMANDERS[$c]}" draw scripted draw "$N"
done
for pair in "${PAIRS[@]}"; do
  read -r pa pb <<<"$pair"
  cell "pair__${pa}__${pb}" unseen "$pa" unseen "$pb" "$N_PAIRS"
done
echo "done $(date -Is)"
