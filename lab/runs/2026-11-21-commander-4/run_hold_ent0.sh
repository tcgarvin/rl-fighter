#!/usr/bin/env bash
# hold_ent0 (plan.md, "08:30"): hold_quiet exactly, with no entropy bonus (ent_coef 0).
# A test of one guess: holding a reserve means choosing "hold" at every decision the
# reserve could launch, and the entropy bonus pushes each toward even odds, while the only
# push back is a win or loss a minute later; so the head learns to launch everything at 2 s.
# Its own launcher, so run.sh (still running kite and noattack) is never edited while it runs.
#
#   DEADLINE="2026-11-21 10:30" nohup setsid lab/runs/2026-11-21-commander-4/run_hold_ent0.sh \
#       > lab/runs/2026-11-21-commander-4/run_hold_ent0.out 2>&1 &
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"
HERE=lab/runs/2026-11-21-commander-4
DIR=$HERE/hold_ent0
THREADS=${ARM_THREADS:-5}
[[ -n ${DEADLINE:-} ]] || { echo "set DEADLINE" >&2; exit 2; }
mkdir -p "$DIR"
resume=()
[[ -f $DIR/state.pt ]] && resume=(--resume)
OMP_NUM_THREADS=$THREADS exec .venv/bin/python -m spacefight.commander.train --run-dir "$DIR" \
    --deadline "$DEADLINE" "${resume[@]}" \
    --set n_envs=128 --set minibatch=1024 --set snapshot_every=25 --set checkpoint_every=10 \
    --set decisions_per_update=4096 \
    --set n_threads="$THREADS" --set torch_threads="$THREADS" --set seed=0 --set order_price=0.0 \
    --set mission_weights=[0,0,0,1] --set learner_team=0 --set launch_prior=0.03 \
    --set init=\""lab/runs/2026-11-15-commander-3/live/checkpoints/commander_197.pt"\" \
    --set opponent_shares=[0.25,0,0,0,0.75] --set live_pilots=\""lab/live_pilots.json"\" \
    --set ent_coef=0.0 --set gamma=0.997 --set lam=0.98 --set shaping=0.0 \
    --set forbid_orders=[\"attack\",\"defend\",\"goto\"] > "$DIR.out" 2>&1
