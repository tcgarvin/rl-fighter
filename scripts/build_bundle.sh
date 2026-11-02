#!/usr/bin/env bash
# Assemble the live page's champion bundle in web/public/bundle/ (gitignored), which
# Vite copies to /bundle/ in web/dist:
#   pkg/            the sim-wasm build (sim_wasm.js + sim_wasm_bg.wasm)
#   policy/         the exported policy (tools/export_policy.py: manifest.json, weights.bin)
#   catalogue.json  hull + weapon YAMLs and the muster card info
#   manifest.json   rlf.bundle/1 (tools/build_bundle.py): bundle id, sim version,
#                   champion, trained match config, roster rules
# then plays headless matches from it, every mission included (tools/web/live_smoke.mjs).
#
# Usage: scripts/build_bundle.sh <checkpoint.pt> <run-id> [eval.json]
#   checkpoint  spike-policy checkpoint for the champion
#   run-id      its lab run (lab/runs/<run-id>), the notebook entry the page links to
#   eval.json   optional rlf.eval.duel JSON of that checkpoint; its summary goes into
#               the manifests
# Env: PYTHON (default: the repo's .venv python), RLF_SKIP_WASM=1 reuses the last
#      wasm-pack build, RLF_CHAMPION_ID / RLF_CHAMPION_NAME / RLF_CHAMPION_HULLS
#      (comma-separated; default: the hulls it trained on) / RLF_ROSTER_BUDGET
#      override the manifest, RLF_SMOKE_MATCHES (default 4), RLF_BUNDLE_DIR writes the
#      bundle somewhere else (scripts/build_site.sh: past champions' bundles),
#      RLF_LIVE_PILOTS names a registry (lab/live_pilots.json) of pilots to fly ship by
#      ship; without it the champion flies every strike craft.
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
BUNDLE="${RLF_BUNDLE_DIR:-$REPO_ROOT/web/public/bundle}"

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
# SIM_VERSION 4+: the build also flies pilots of the versions in pilot_compat_versions().
# SIM_VERSION 5+: a pilot reads the obs prefix of its own version (pilotObsDimsJson():
# a v3/v4 pilot the first 385 floats of the v5 obs).
read -r SIM_VERSION OBS_DIM PILOT_COMPAT PILOT_OBS_DIMS < <(node --input-type=module -e "
import fs from 'node:fs';
const sim = await import('$PKG/sim_wasm.js');
sim.initSync({ module: fs.readFileSync('$PKG/sim_wasm_bg.wasm') });
const compat = sim.pilot_compat_versions ? Array.from(sim.pilot_compat_versions()) : [sim.sim_version()];
const dims = sim.pilotObsDimsJson ? sim.pilotObsDimsJson() : JSON.stringify(Object.fromEntries(compat.map((v) => [v, sim.OBS_DIM()])));
console.log(sim.sim_version(), sim.OBS_DIM(), compat.join(','), dims);
")

step "assemble $BUNDLE"
rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/pkg"
cp "$PKG/sim_wasm.js" "$PKG/sim_wasm_bg.wasm" "$BUNDLE/pkg/"

step "export policy: $CHECKPOINT (sim_version $SIM_VERSION, obs_dim $OBS_DIM)"
EXPORT_ARGS=(--checkpoint "$CHECKPOINT" --out "$BUNDLE/policy"
    --wasm-sim-version "$SIM_VERSION" --wasm-obs-dim "$OBS_DIM" --wasm-pilot-compat "$PILOT_COMPAT"
    --wasm-pilot-obs-dims "$PILOT_OBS_DIMS")
if [[ -n "$EVAL_JSON" ]]; then
    EXPORT_ARGS+=(--eval-json "$EVAL_JSON")
fi
"$PYTHON" -m tools.export_policy "${EXPORT_ARGS[@]}"

if [[ -n "${RLF_LIVE_PILOTS:-}" ]]; then
    step "export live pilots: $RLF_LIVE_PILOTS"
    "$PYTHON" -m tools.live_pilots export --registry "$RLF_LIVE_PILOTS" --bundle "$BUNDLE" \
        --wasm-sim-version "$SIM_VERSION" --wasm-obs-dim "$OBS_DIM" \
        --wasm-pilot-compat "$PILOT_COMPAT" --wasm-pilot-obs-dims "$PILOT_OBS_DIMS"
fi

step "catalogue + manifest"
BUNDLE_ARGS=(--bundle "$BUNDLE" --run "$RUN_ID" --assets assets
    --sim-version "$SIM_VERSION" --pilot-compat "$PILOT_COMPAT")
[[ -n "${RLF_CHAMPION_ID:-}" ]] && BUNDLE_ARGS+=(--champion-id "$RLF_CHAMPION_ID")
[[ -n "${RLF_CHAMPION_NAME:-}" ]] && BUNDLE_ARGS+=(--champion-name "$RLF_CHAMPION_NAME")
[[ -n "${RLF_CHAMPION_HULLS:-}" ]] && BUNDLE_ARGS+=(--hulls "$RLF_CHAMPION_HULLS")
[[ -n "${RLF_ROSTER_BUDGET:-}" ]] && BUNDLE_ARGS+=(--budget "$RLF_ROSTER_BUDGET")
"$PYTHON" -m tools.build_bundle "${BUNDLE_ARGS[@]}"

step "headless smoke: missions and drafted matches from the bundle (strike craft flown by the policy)"
node --experimental-strip-types --no-warnings tools/web/live_smoke.mjs "$BUNDLE" "${RLF_SMOKE_MATCHES:-4}"

step "built $BUNDLE ($(du -sh "$BUNDLE" | cut -f1))"
