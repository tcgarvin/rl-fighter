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
uv run python -m pytest tests/test_rust_missions.py -v   # v4 missions + commander API, v5 orders/random commander
uv run python -m pytest tests/test_rust_orders_v6.py -v  # v6 orders: defend / go-to, hidden orders, transit, threat sets
# Mission timeline diagnostic (carrier battle, convoy escort, stub commanders)
cargo test -p sim --test missions timeline -- --ignored --nocapture
uv run python tools/bench_env.py --assert-floors   # v5: + 12-slot carrier/convoy training shapes

# Rust gate (fmt, clippy, native + wasip1 tests, wasm-pack, rlf_sim build + tests)
scripts/check.sh

# Champion bundle for the live page into web/public/bundle/ (release wasm, policy export
# + sim_version check, catalogue, manifest.json rlf.bundle/1, headless N-ship smoke)
scripts/build_bundle.sh <checkpoint.pt> <run-id> [eval.json]
# Web client (web/: Vite + TS). npm run build typechecks; preview serves web/dist
cd web && npm install && npm run build && npx vite preview --port 4173
# List / stop stray vite servers of this repo and its worktrees (never other projects')
scripts/kill_stale_vite.sh [PID... | --older-than MIN]

# Build the website into dist/: live page at /, story demo at /story/ (bundle + web build)
scripts/build_site.sh            # from the current champion (lab/champions)
scripts/build_site.sh lab/runs/<run>/<arm>/checkpoints/ppo_bc_<N>.pt <run-id> [eval.json]

# Champion registry: lab/champions/<id>/champion.json (rlf.champion/1) is committed; the
# weights live in gs://storage.tcgarvin.com/rl-fighter/champions/<id>/<sha256>.pt, served
# at https://storage.tcgarvin.com (upload uses gcloud --configuration=tcgarvin-com; fetch
# is plain HTTPS into ~/.cache/rl-fighter/weights, sha256-checked)
uv run python -m tools.champion promote --id YYYY-MM-DD-name --name "..." --run <run-id> \
    --checkpoint <ckpt.pt> --hulls fighter,strafer,gunship --eval-json <eval.json> [--parent <id>]
uv run python -m tools.champion list | fetch [<id>] | env [<id>]
# /pilot/ states the current champion's facts, so promote before scripts/build_site.sh and
# tests/test_pilot_page.py agree with a page written for a new champion. RLF_CHAMPIONS_DIR
# points every registry reader at a copy, to rehearse with a record not yet promoted.

# Parity of the browser policy with torch; the headless live-match smoke test
uv run python -m pytest tests/test_web_policy.py -v
node --experimental-strip-types tools/web/live_smoke.mjs web/public/bundle 4 [--hulls fighter,strafer,gunship]
# Screenshots (390x844, 1440x900) into web/shots/live/, and a 10-minute heap/GPU soak,
# against a running preview / web/dist; RLF_GPU=1 uses the host GPU instead of SwiftShader
node tools/web/live_shots.mjs http://localhost:4173
node tools/web/live_soak.mjs 10 8
# M3 art preview without the sim (carrier, freighter, bay launch, jump charge/out, orders):
# dev-only page web/dev/m3-art.html?scene=lineup|detail|convoy|launch|jump|quick|orders[&t=s]
# on the Vite dev server; screenshots into web/shots/m3-art/
cd web && npx vite --port 5179 --strictPort   # then, from the repo root:
node tools/web/art_shots.mjs http://localhost:5179
# Art agent (DESIGN §11): Codex, gpt-6.1-sol only, always at high reasoning effort (the
# default is none); -i attaches screenshots for review
codex exec -m gpt-6.1-sol -c model_reasoning_effort='"high"' -s workspace-write -C . -i shot.png "..."

# Fleets (1-4 ships a side, mixed hulls): fleet eval (schema rlf.eval.fleet/1), the
# script-vs-script fleet survey, and the fleet pilot v1 run (BC -> DAgger -> PPO;
# SMOKE=1 runs every stage at tiny sizes into the run's gitignored smoke/ dir)
uv run python -m spacefight.eval.fleet --a <checkpoint.pt> --b script --out fleet.json
PYTHONPATH=. uv run python tools/fleet_survey.py --n-per-roster 128
nohup lab/runs/2026-10-30-fleet-pilot/run.sh > lab/runs/2026-10-30-fleet-pilot/run.out 2>&1 &

# Stage B (orders, SIM_VERSION 5): mission eval (rlf.eval.mission/1; carrier + convoy,
# live default rosters, capital ships by script), the v5 order-following eval
# (spacefight.eval.orders_v1, rlf.eval.orders/1, runs 1 and B2b; v5 sim only), and the
# order pilot run (rosters orders_v1, arms w1 / w03; SMOKE=1 for tiny sizes into smoke/)
uv run python -m spacefight.eval.missions --a <checkpoint.pt> --b <v1.pt> --out missions.json
nohup lab/runs/2026-10-31-order-pilot/run.sh > lab/runs/2026-10-31-order-pilot/run.out 2>&1 &

# Stage B3 (orders attack / defend / go-to, SIM_VERSION 6, OBS_DIM 583): order eval
# (rlf.eval.orders/2: followed and hidden-by-the-sim passes on the same matches; the
# teacher with --a script --passes followed), gates in spacefight/eval/order_gates_b3.py,
# and run B3 (w1_400 widened to 583, arms transit / reward; SMOKE=1 tiny sizes).
# v6 pilots export with 583 inputs and sim_version 6: tools/export_policy.py
# --wasm-sim-version 6 --wasm-obs-dim 583 --wasm-pilot-compat 3,4,5,6
uv run python -m spacefight.eval.orders --a <checkpoint.pt> --out orders.json
nohup lab/runs/2026-11-01-order-pilot-b3/run.sh > lab/runs/2026-11-01-order-pilot-b3/run.out 2>&1 &

# Order drills (docs/PILOT_TRAINING.md section 2): start layouts + drill rules in the sim,
# spacefight/env/drills.py, drill_share in pilots_v1 (roster_overrides), and the drill eval
# and gate (JSON rlf.eval.drills/1, report beside it; bars in spacefight/eval/drill_bars.yaml;
# the script has no hidden go-to pass, so its gate says report_only)
uv run python -m spacefight.eval.drills --a <checkpoint.pt|script> --name <pilot> \
    --n-per-kind 64 --threads 2 --out drills.json [--exempt f995_701,transit_300] [--bars <yaml>]
uv run python -m pytest tests/test_drills.py -v
cargo test -p sim --test drills

# Pilot population (docs/PILOT_TRAINING.md sections 4-6): records in lab/population/<season>/
# members/ (rlf.population.member/1; weights stay out of git), all-pairs no-commander round
# robin (resumable; tiny sizes by default), combat rating, shadow culls (a report only, it
# changes no status), phone-readable report.md. --checkpoint-root names the checkout that
# holds lab/runs, needed from a worktree.
uv run python -m spacefight.population list --season lab/population/2026-11-sim6
uv run python -m spacefight.population add-founder --season lab/population/2026-11-sim6 \
    --id <id> --family <family> --checkpoint <path.pt> [--parent <id> --fork-update <N>]
uv run python -m spacefight.population round-robin --season lab/population/2026-11-sim6 \
    --out lab/population/2026-11-sim6/round_robin/existing-pilots \
    --members script,f995_701,f995_400,f99_696,reward_300,transit_300,hide_644,v1,w1_400 \
    --n-per-mission 240 --deathmatch-rosters 24 --n-threads 4
uv run python -m spacefight.population report --season lab/population/2026-11-sim6 \
    --results lab/population/2026-11-sim6/round_robin/existing-pilots \
    --phase existing-pilots --date YYYY-MM-DD [--record]
uv run python -m pytest tests/test_population_records.py tests/test_population_rating.py \
    tests/test_population_culling.py tests/test_round_robin.py tests/test_opponents_weighted.py -v

# Deploy dist/ (rl-fighter.tcgarvin.com); needs NETLIFY_AUTH_TOKEN in .env
scripts/deploy.sh            # or --build (current champion) / <checkpoint.pt> <run-id> to rebuild first

# Data for /notebook/ (from lab/runs) and /hulls/ (from assets/) into web/public/{notebook,hulls}/data/,
# and the check that the static /pilot/ page (web/pilot/index.html, "How the pilot works")
# still matches the sim, policy code, hulls and champion (tools/pilot_facts.py)
scripts/build_pages_data.sh  # = cd web && npm run data
uv run python -m pytest tests/test_build_notebook.py tests/test_build_catalogue.py tests/test_pilot_page.py -v
```

How pilots train (scenarios, order drills, families, what earns a place): `docs/PILOT_TRAINING.md`.
Keep it current when training scenarios change.

The project is moving to a Rust sim + three.js web client; `docs/DESIGN.md` is the
source of truth for that direction. The website (`web/`, Vite + TypeScript) serves the
live page at `/`: matches that loop forever, rotating team deathmatch, carrier battle
and convoy escort (`web/src/live/missions.ts`: rotation, rosters, briefs; `?mission=
deathmatch|carrier|convoy` pins one, `?commands=1` shows the commander layer), every
strike craft flown by the champion policy and capital ships by the sim's scripts (Rust
sim in WASM, MLP inference in JS, `web/src/live/`, renderer modules in
`web/src/render/`), loaded from the champion bundle at `/bundle/`. The renderer takes
hull mounts from the bundle catalogue (the YAML), not `render/hulls.js`. `/duel/`
redirects to a 1v1 fighter roster. The scripted story demo in `prototypes/story/` (draft, then missions;
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
