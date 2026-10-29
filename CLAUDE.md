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

# Build the website into dist/: story demo at /, live learned-pilot duel at /duel/
# (release wasm, policy export + sim_version check, lab notes, headless smoke match)
scripts/build_site.sh lab/runs/<run>/ppo_bc/checkpoints/ppo_bc_<N>.pt [eval.json]
python3 -m http.server -d dist 8000   # preview

# Parity of the browser policy with torch, and the headless duel smoke test
uv run python -m pytest tests/test_web_policy.py -v
node tools/web/duel_smoke.mjs dist/duel/pkg dist/duel/policy 3

# Deploy dist/ (rl-fighter.tcgarvin.com); needs NETLIFY_AUTH_TOKEN in .env
scripts/deploy.sh            # or: scripts/deploy.sh <checkpoint.pt> to rebuild first

# M2 site (web/, Vite + TS): data for /notebook/ (from lab/runs) and /hulls/ (from assets/)
scripts/build_pages_data.sh  # = cd web && npm run data; writes web/public/{notebook,hulls}/data/
cd web && npm install && npm run build   # tsc --noEmit + vite build into web/dist/
uv run python -m pytest tests/test_build_notebook.py tests/test_build_catalogue.py -v
```

The project is moving to a Rust sim + three.js web client; `docs/DESIGN.md` is the
source of truth for that direction. The website serves the scripted
story demo in `prototypes/story/` at `/` (draft, then missions; it builds on the art-direction
demo in `prototypes/art-direction/`) and, at `/duel/`, `web/duel/`: a live fighter duel
where the learned spike policy flies in the browser (Rust sim in WASM, MLP inference in
JS, the story's renderer modules imported from the site root). The sections below describe the
original Python/NumPy prototype.

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
