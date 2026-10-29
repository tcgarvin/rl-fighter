# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RL Fighter is a reinforcement learning environment for 2v2 space combat. It uses batched NumPy simulation (256 parallel matches), PPO self-play training with PyTorch, and Pygame visualization. Python 3.13+, managed with `uv`.

## Commands

```bash
# Install dependencies
uv sync --extra dev

# Run tests
uv run python -m pytest tests/ -v

# Run a single test file
uv run python -m pytest tests/test_physics.py -v

# Run a single test
uv run python -m pytest tests/test_physics.py::test_thrust -v

# Train
uv run python train.py
uv run python train.py --n-envs 64 --n-updates 1000 --seed 0

# Visualize
uv run python -m vis.pygame_vis
uv run python -m vis.pygame_vis --checkpoint checkpoints/policy_500.pt

# Rust sim workspace (crates/): fmt, clippy, native + wasm32-wasip1 tests, wasm-pack build
# Needs: rustup target wasm32-wasip1, wasmtime (~/.wasmtime/bin), wasm-pack (~/.cargo/bin)
# Plain cargo on crates/sim-py needs PYO3_PYTHON=$(uv python find '>=3.13') (check.sh sets it)
scripts/check.sh

# Build the Rust sim's Python extension (rlf_sim) into the venv, test, benchmark
uv run maturin develop -m crates/sim-py/Cargo.toml --release
uv run python -m pytest tests/test_rust_env.py -v
uv run python tools/bench_env.py --assert-floors

# Rust gate (fmt, clippy, native + wasip1 tests, wasm-pack, rlf_sim build + tests)
scripts/check.sh

# Champion bundle for the live page into web/public/bundle/ (release wasm, policy export
# + sim_version check, catalogue, manifest.json rlf.bundle/1, headless N-ship smoke)
scripts/build_bundle.sh <checkpoint.pt> <run-id> [eval.json]
# Web client (web/: Vite + TS). npm run build typechecks; preview serves web/dist
cd web && npm install && npm run build && npx vite preview --port 4173

# Build the website into dist/: live page at /, story demo at /story/ (bundle + web build)
scripts/build_site.sh lab/runs/<run>/<arm>/checkpoints/ppo_bc_<N>.pt <run-id> [eval.json]

# Parity of the browser policy with torch; the headless live-match smoke test
uv run python -m pytest tests/test_web_policy.py -v
node --experimental-strip-types tools/web/live_smoke.mjs web/public/bundle 4 [--hulls fighter,strafer,gunship]
# Screenshots (390x844, 1440x900) into web/shots/live/, and a 10-minute heap/GPU soak,
# against a running preview / web/dist; RLF_GPU=1 uses the host GPU instead of SwiftShader
node tools/web/live_shots.mjs http://localhost:4173
node tools/web/live_soak.mjs 10 8

# Fleets (1-4 ships a side, mixed hulls): fleet eval (schema rlf.eval.fleet/1), the
# script-vs-script fleet survey, and the fleet pilot v1 run (BC -> DAgger -> PPO;
# SMOKE=1 runs every stage at tiny sizes into the run's gitignored smoke/ dir)
uv run python -m spacefight.eval.fleet --a <checkpoint.pt> --b script --out fleet.json
PYTHONPATH=. uv run python tools/fleet_survey.py --n-per-roster 128
nohup lab/runs/2026-10-30-fleet-pilot/run.sh > lab/runs/2026-10-30-fleet-pilot/run.out 2>&1 &

# Deploy dist/ (rl-fighter.tcgarvin.com); needs NETLIFY_AUTH_TOKEN in .env
scripts/deploy.sh            # or: scripts/deploy.sh <checkpoint.pt> <run-id> to rebuild first

# Data for /notebook/ (from lab/runs) and /hulls/ (from assets/) into web/public/{notebook,hulls}/data/
scripts/build_pages_data.sh  # = cd web && npm run data
uv run python -m pytest tests/test_build_notebook.py tests/test_build_catalogue.py -v
```

The project is moving to a Rust sim + three.js web client; `docs/DESIGN.md` is the
source of truth for that direction. The website (`web/`, Vite + TypeScript) serves the
live page at `/`: matches that loop forever, every ship flown by the champion policy
(Rust sim in WASM, MLP inference in JS, `web/src/live/`, renderer modules in
`web/src/render/`), loaded from the champion bundle at `/bundle/`. `/duel/` redirects to a
1v1 fighter roster. The scripted story demo in `prototypes/story/` (draft, then missions;
it builds on the art-direction demo in `prototypes/art-direction/`) is served at `/story/`.
The sections below describe the original Python/NumPy prototype.

## Architecture

### Simulation (`spacefight/sim/`)
Headless, vectorized NumPy physics engine. **SimState** is a dataclass of batched arrays shaped `[N, S]` (N=parallel matches, S=4 ships). Runs at 30 Hz. `core.py` handles physics (thrust/turn/brake with soft speed cap), `weapons.py` handles projectile spawning/advancement/hit detection (point-in-circle, team-aware), `damage.py` applies hull damage.

### Environment (`spacefight/env/vec_env.py`)
**VecEnv** wraps the sim into a standard RL interface: `reset() → obs`, `step(actions) → (obs, rewards, dones, infos)`. Auto-resets finished episodes. 4 ships per match (2v2), 2700-step episode limit (90s). Rewards: +/- 0.01 per HP dealt/taken, zone penalty for idle/out-of-bounds, +/-1.0 win/loss terminal.

### RL (`spacefight/rl/`)
- **obs.py**: Builds 36-feature egocentric observations per ship (body-frame rotation so forward=+x). Features: self state, hull properties, 1 ally, 2 nearest enemies (sorted by distance), engagement zone.
- **policy.py**: `ActorCritic` with decentralized actor (2×256 MLP → 4 categorical heads: turn/thrust/brake/fire) and centralized critic (concatenated team obs → scalar value).
- **ppo.py**: PPO clipped objective update (clip ε=0.2, entropy coeff 0.01, value coeff 0.5).
- **rollout_buffer.py**: Fixed-size buffer with GAE advantage computation (γ=0.99, λ=0.95).

### Data (`data/`)
YAML-driven hull and weapon definitions. 4 hull types (interceptor/fighter/gunboat/bomber) with different HP/speed/turn/thrust trade-offs. Gauss gun: 15 dmg, 6-shot magazine, 2s reload.

### Visualization (`vis/pygame_vis.py`)
Pygame match viewer. Ships as hull-specific colored polygons, bullets, HP bars. Controls: Space=pause, R=reset, Q=quit.

### Key Design Decisions
- Same policy plays all ships (egocentric obs enables implicit self-play)
- MAPPO-style: decentralized actors + centralized critic
- Deterministic sim (reproducible with seed)
- Projectile pool of 128 per match with oldest-overwrite recycling
