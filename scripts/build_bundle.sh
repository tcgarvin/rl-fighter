#!/usr/bin/env bash
# Assemble the live page's champion bundle in web/public/bundle/ (gitignored), which
# Vite copies to /bundle/ in web/dist:
#   pkg/            the sim-wasm build (sim_wasm.js + sim_wasm_bg.wasm)
#   policy/         the exported policy (tools/export_policy.py: manifest.json, weights.bin)
#   catalogue.json  hull + weapon YAMLs and the muster card info
#   manifest.json   rlf.bundle/1 (tools/build_bundle.py): bundle id, sim version,
#                   champion, trained match config, roster rules
# then plays headless N-ship matches from it (tools/web/live_smoke.mjs).
#
# Usage: scripts/build_bundle.sh <checkpoint.pt> <run-id> [eval.json]
#   checkpoint  spike-policy checkpoint for the champion
#   run-id      its lab run (lab/runs/<run-id>), the notebook entry the page links to
#   eval.json   optional rlf.eval.duel JSON of that checkpoint; its summary goes into
#               the manifests
# Env: PYTHON (default: the repo's .venv python), RLF_SKIP_WASM=1 reuses the last
#      wasm-pack build, RLF_CHAMPION_ID / RLF_CHAMPION_NAME / RLF_CHAMPION_HULLS
#      (comma-separated; default: the hulls it trained on) / RLF_ROSTER_BUDGET
#      override the manifest, RLF_SMOKE_MATCHES (default 4).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
export PATH="$HOME/.cargo/bin:$PATH"

if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo "usage: scripts/build_bundle.sh <checkpoint.pt> <run-id> [eval.json]" >&2
    exit 2
fi
CHECKPOINT="$1"
RUN_ID="$2"
EVAL_JSON="${3:-}"
PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python}"
PKG="$REPO_ROOT/target/wasm-pack/sim-wasm-release"
BUNDLE="$REPO_ROOT/web/public/bundle"

step() { printf '\n==> %s\n' "$*"; }

if [[ ! -f "$CHECKPOINT" ]]; then
    echo "Error: checkpoint $CHECKPOINT not found" >&2
    exit 1
fi
if [[ ! -d "lab/runs/$RUN_ID" ]]; then
    echo "Error: lab/runs/$RUN_ID does not exist" >&2
    exit 1
fi

if [[ "${RLF_SKIP_WASM:-0}" == "1" && -f "$PKG/sim_wasm_bg.wasm" ]]; then
    step "reusing $PKG (RLF_SKIP_WASM=1)"
else
    step "wasm-pack build crates/sim-wasm --release --target web"
    wasm-pack --quiet build crates/sim-wasm --release --target web --out-dir "$PKG"
fi

# The policy export checks its checkpoint against the bundle it will run with.
read -r SIM_VERSION OBS_DIM < <(node --input-type=module -e "
import fs from 'node:fs';
const sim = await import('$PKG/sim_wasm.js');
sim.initSync({ module: fs.readFileSync('$PKG/sim_wasm_bg.wasm') });
console.log(sim.sim_version(), sim.OBS_DIM());
")

step "assemble $BUNDLE"
rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/pkg"
cp "$PKG/sim_wasm.js" "$PKG/sim_wasm_bg.wasm" "$BUNDLE/pkg/"

step "export policy: $CHECKPOINT (sim_version $SIM_VERSION, obs_dim $OBS_DIM)"
EXPORT_ARGS=(--checkpoint "$CHECKPOINT" --out "$BUNDLE/policy"
    --wasm-sim-version "$SIM_VERSION" --wasm-obs-dim "$OBS_DIM")
if [[ -n "$EVAL_JSON" ]]; then
    EXPORT_ARGS+=(--eval-json "$EVAL_JSON")
fi
"$PYTHON" -m tools.export_policy "${EXPORT_ARGS[@]}"

step "catalogue + manifest"
BUNDLE_ARGS=(--bundle "$BUNDLE" --run "$RUN_ID" --assets assets)
[[ -n "${RLF_CHAMPION_ID:-}" ]] && BUNDLE_ARGS+=(--champion-id "$RLF_CHAMPION_ID")
[[ -n "${RLF_CHAMPION_NAME:-}" ]] && BUNDLE_ARGS+=(--champion-name "$RLF_CHAMPION_NAME")
[[ -n "${RLF_CHAMPION_HULLS:-}" ]] && BUNDLE_ARGS+=(--hulls "$RLF_CHAMPION_HULLS")
[[ -n "${RLF_ROSTER_BUDGET:-}" ]] && BUNDLE_ARGS+=(--budget "$RLF_ROSTER_BUDGET")
"$PYTHON" -m tools.build_bundle "${BUNDLE_ARGS[@]}"

step "headless smoke: drafted matches from the bundle, every ship flown by the policy"
node --experimental-strip-types --no-warnings tools/web/live_smoke.mjs "$BUNDLE" "${RLF_SMOKE_MATCHES:-4}"

step "built $BUNDLE ($(du -sh "$BUNDLE" | cut -f1))"
