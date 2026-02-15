# RL Fighter

A reinforcement learning environment for 2v2 space combat. Ships fight in a 2D arena using thrust, turning, braking, and a gauss gun. Agents are trained via PPO self-play with egocentric observations — all four ships share the same policy.

## Setup

Requires Python 3.13+. Install with [uv](https://docs.astral.sh/uv/):

```bash
uv sync --extra dev
```

## Project Structure

```
spacefight/
  sim/           # Batched NumPy simulation (physics, weapons, damage)
  env/           # VecEnv RL wrapper with auto-reset
  rl/            # PPO training components (obs, policy, buffer, update)
vis/             # Pygame match viewer
data/            # YAML definitions for hulls and weapons
docs/            # Design spec and simulation overview
tests/           # pytest suite
train.py         # Training entry point
```

## Training

Train agents with PPO self-play:

```bash
uv run python train.py
```

Defaults: 256 parallel envs, 128 rollout steps, 5000 updates. Checkpoints save to `checkpoints/` every 100 updates.

Override settings:

```bash
uv run python train.py --n-envs 64 --n-updates 1000 --seed 0
```

Training logs print every 10 updates with mean reward, policy loss, value loss, and entropy.

## Visualization

Watch a match with random actions:

```bash
uv run python -m vis.pygame_vis
```

Watch a trained agent play:

```bash
uv run python -m vis.pygame_vis --checkpoint checkpoints/policy_500.pt
```

Controls:
- **Space** — pause/unpause
- **R** — reset match
- **Q** — quit

## Tests

```bash
uv run python -m pytest tests/ -v
```

## How It Works

### Simulation

The sim runs at 30 Hz with batched NumPy arrays. Each match has 4 ships (2v2) with 4 discrete actions per tick:

| Action | Values | Effect |
|--------|--------|--------|
| Turn | -1, 0, 1 | Rotate left/none/right |
| Thrust | 0, 1 | Accelerate along heading |
| Brake | 0, 1 | Apply drag to slow down |
| Fire | 0, 1 | Shoot gauss gun (if off cooldown) |

Ships have hull HP, a speed cap with soft drag, and a shared projectile pool (128 bullets per match). The gauss gun has a 6-shot magazine with 2-second reload. A match ends when an entire team is eliminated or after 2700 ticks (90s).

Teams spawn 1040–1440 units apart (outside the 800-unit weapon range) and must maneuver to engage. An engagement zone penalizes ships that stray too far or avoid combat.

### Hulls

Four hull types with different trade-offs (all fighters by default, randomization available):

| Hull | HP | Speed | Turn (°/s) | Character |
|------|-----|-------|-----------|-----------|
| Interceptor | 80 | 300 | 180 | Fast, fragile, agile |
| Fighter | 150 | 220 | 120 | Balanced all-rounder |
| Gunboat | 250 | 160 | 80 | Slow and tough |
| Bomber | 120 | 200 | 100 | Quick, high thrust |

### Observations

Each ship gets a 36-dimensional egocentric observation rotated into its body frame (forward = +x). Features include self state (speed, hull, ammo, cooldown), ship properties, 1 ally, 2 enemies sorted by distance, and engagement zone info.

### Policy

MAPPO-style architecture: decentralized actor (2x256 MLP with 4 categorical action heads) and centralized critic (sees own + teammate observations). All ships share the same network — self-play is implicit through the egocentric observations.

### Rewards

- **+1.0** for team win (all enemies eliminated)
- **-1.0** for team loss
- **+0.01** per HP of damage dealt
- **-0.01** per HP of damage taken
- Quadratic zone penalty for straying from the engagement area

See [docs/SIMULATION.md](docs/SIMULATION.md) for full details.
