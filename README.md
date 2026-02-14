# RL Fighter

A reinforcement learning environment for 1v1 space combat. Ships fight in a 2D arena using thrust, turning, braking, and a gauss gun. Agents are trained via PPO self-play with egocentric observations, so both ships share the same policy.

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

The sim runs at 30 Hz with batched NumPy arrays. Each match has 2 ships with 4 discrete actions per tick:

| Action | Values | Effect |
|--------|--------|--------|
| Turn | -1, 0, 1 | Rotate left/none/right |
| Thrust | 0, 1 | Accelerate along heading |
| Brake | 0, 1 | Apply drag to slow down |
| Fire | 0, 1 | Shoot gauss gun (if off cooldown) |

Ships have hull HP, a speed cap with soft drag, and a shared projectile pool (64 bullets per match). A match ends when any ship reaches 0 HP or after 1800 ticks (60s).

### Observations

Each ship gets a 14-dimensional egocentric observation. All spatial values are rotated into the ship's heading frame so "forward" is always +x:

| # | Feature | Range |
|---|---------|-------|
| 0-1 | Opponent relative position (heading frame) | /1000 |
| 2-3 | Opponent relative velocity (heading frame) | /500 |
| 4 | Distance to opponent | /1000 |
| 5 | Bearing to opponent | /pi |
| 6 | Own speed | /max_speed |
| 7 | Own hull fraction | [0,1] |
| 8 | Opponent hull fraction | [0,1] |
| 9 | Weapon cooldown fraction | /fire_interval |
| 10-11 | sin(heading), cos(heading) | [-1,1] |
| 12 | Opponent alive | 0/1 |
| 13 | Forward speed component | /max_speed |

### Policy

Separate actor and critic MLPs (2 hidden layers, 128 units each, ReLU). The actor has 4 independent categorical heads for each action. Both ships use the same network — self-play is implicit through the egocentric obs.

### Rewards

- **+1.0** for winning (opponent destroyed)
- **-1.0** for losing
- **+0.01** per HP of damage dealt
- **-0.01** per HP of damage taken
