#!/usr/bin/env bash
# Assemble the static site in dist/ (gitignored) for scripts/deploy.sh:
#   /        prototypes/story/ (the scripted story demo)
#   /duel/   web/duel/ + the sim-wasm bundle (pkg/), the exported policy (policy/),
#            the hull/weapon catalogue (assets/catalogue.json) and the lab notes
#            (notes.html, rendered from the run's results.md)
#
# Usage: scripts/build_site.sh <checkpoint.pt> [eval.json]
#   checkpoint  spike-policy checkpoint for the learned pilot (tools/export_policy.py)
#   eval.json   optional rlf.eval.duel/1 or /2 JSON of that checkpoint vs the script; its
#               summary goes into the policy manifest
# Env: PYTHON (default: the repo's .venv python), RLF_NOTES_MD (default: the spike
#      run's results.md), RLF_SKIP_WASM=1 reuses the last wasm-pack build.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"
export PATH="$HOME/.cargo/bin:$PATH"

if [[ $# -lt 1 || $# -gt 2 ]]; then
    echo "usage: scripts/build_site.sh <checkpoint.pt> [eval.json]" >&2
    exit 2
fi
CHECKPOINT="$1"
EVAL_JSON="${2:-}"
PYTHON="${PYTHON:-$REPO_ROOT/.venv/bin/python}"
NOTES_MD="${RLF_NOTES_MD:-$REPO_ROOT/lab/runs/2026-10-28-learnability-spike/results.md}"
PKG="$REPO_ROOT/target/wasm-pack/sim-wasm-release"
DIST="$REPO_ROOT/dist"

step() { printf '\n==> %s\n' "$*"; }

if [[ ! -f "$CHECKPOINT" ]]; then
    echo "Error: checkpoint $CHECKPOINT not found" >&2
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

step "assemble $DIST (story at /, duel at /duel/)"
rm -rf "$DIST"
mkdir -p "$DIST"
cp -R prototypes/story/. "$DIST/"
rm -f "$DIST/README.md"
mkdir -p "$DIST/duel/pkg" "$DIST/duel/assets"
cp web/duel/index.html web/duel/main.js web/duel/duel.js web/duel/policy.js "$DIST/duel/"
cp "$PKG/sim_wasm.js" "$PKG/sim_wasm_bg.wasm" "$DIST/duel/pkg/"

step "catalogue: assets/hulls/*/hull.yaml + assets/weapons.yaml"
node --input-type=module -e "
import fs from 'node:fs';
const names = fs.readdirSync('assets/hulls').filter((n) => fs.existsSync('assets/hulls/' + n + '/hull.yaml')).sort();
const out = { hulls: names.map((n) => [n, fs.readFileSync('assets/hulls/' + n + '/hull.yaml', 'utf8')]), weapons: fs.readFileSync('assets/weapons.yaml', 'utf8') };
fs.writeFileSync('$DIST/duel/assets/catalogue.json', JSON.stringify(out));
console.log('hulls: ' + names.join(', '));
"

step "export policy: $CHECKPOINT (sim_version $SIM_VERSION, obs_dim $OBS_DIM)"
EXPORT_ARGS=(--checkpoint "$CHECKPOINT" --out "$DIST/duel/policy"
    --wasm-sim-version "$SIM_VERSION" --wasm-obs-dim "$OBS_DIM")
if [[ -n "$EVAL_JSON" ]]; then
    EXPORT_ARGS+=(--eval-json "$EVAL_JSON")
fi
"$PYTHON" -m tools.export_policy "${EXPORT_ARGS[@]}"

step "lab notes: $NOTES_MD"
"$PYTHON" -m tools.render_notes --md "$NOTES_MD" --out "$DIST/duel/notes.html"

step "headless smoke: one learned-vs-script match from dist/"
node tools/web/duel_smoke.mjs "$DIST/duel/pkg" "$DIST/duel/policy" 1

step "built $DIST ($(du -sh "$DIST" | cut -f1)); preview: python3 -m http.server -d dist 8000"
