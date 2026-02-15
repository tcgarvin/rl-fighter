# Reinforcement Learning Setup

This document describes the RL training pipeline: the algorithm, network architecture, observation/action spaces, rollout collection, and training loop.

## Algorithm: MAPPO

The system uses Multi-Agent PPO (MAPPO) — PPO adapted for cooperative multi-agent settings:

- **Decentralized actors**: each ship acts on its own egocentric observation
- **Centralized critic**: the value function sees concatenated teammate observations for reduced variance
- **Parameter sharing**: all 4 ships (2 per team) share the same actor and critic weights

Self-play is implicit — because every ship uses the same policy with egocentric observations, training against yourself produces increasingly capable opponents without explicit opponent sampling.

## Network Architecture

### Actor

The actor is a multi-head MLP that maps a single ship's observation to action distributions:

```
obs [53] → Linear(256) → ReLU → Linear(256) → ReLU → 5 action heads
```

Each head is an independent `Linear → Categorical`:

| Head | Size | Meaning |
|------|------|---------|
| Turn | 3 | {left, none, right} → mapped to {-1, 0, 1} |
| Thrust | 2 | {off, on} |
| Brake | 2 | {off, on} |
| Fire | 2 | {off, on} |
| Reload | 2 | {off, on} |

Actions are sampled independently from each head. The total log-probability is the sum of per-head log-probs; entropy is likewise summed.

### Centralized Critic

The critic sees the agent's own observation concatenated with its teammate's observation (106 features total for 2v2):

```
[own_obs, teammate_obs] [106] → Linear(256) → ReLU → Linear(256) → ReLU → Linear(1)
```

This gives the critic access to team-level information (teammate position, health, ammo) while the actor only sees its own egocentric view. The teammate mapping is fixed: ship 0 ↔ ship 1, ship 2 ↔ ship 3.

## Observations

Each ship receives a **53-feature egocentric observation** built in `spacefight/rl/obs.py`. All spatial quantities are rotated into the ship's body frame (forward = +x axis).

### Feature layout

**Self state (8 features)**

| Index | Feature | Normalization |
|-------|---------|---------------|
| 0 | Speed | / max_speed |
| 1 | Hull fraction | hull / max_hull |
| 2 | Weapon cooldown | / fire_interval |
| 3 | sin(heading) | [-1, 1] |
| 4 | cos(heading) | [-1, 1] |
| 5 | Forward speed | / max_speed |
| 6 | Ammo fraction | ammo / magazine_size |
| 7 | Reload timer | / reload_time |

**Ship properties (4 features)** — lets the policy adapt to the hull it's flying:

| Index | Feature | Normalization |
|-------|---------|---------------|
| 8 | Max hull | / 250 (gunboat HP) |
| 9 | Max speed | / 300 (interceptor speed) |
| 10 | Turn rate | / π |
| 11 | Thrust accel | / 400 (interceptor thrust) |

**Weapon descriptors (5 features)** — weapon identity and ballistic properties:

| Index | Feature | Normalization |
|-------|---------|---------------|
| 12 | Is projectile | 1 for gauss_gun/double_gauss, 0 otherwise |
| 13 | Is hitscan | 1 for laser, 0 otherwise |
| 14 | Is guided | 1 for guided_missile, 0 otherwise |
| 15 | Effective range | / 1500 |
| 16 | Projectile speed | / 500 (0 for hitscan) |

**Ally (7 features)** — one teammate in 2v2:

| Index | Feature | Normalization |
|-------|---------|---------------|
| 17–18 | Relative position (x, y) | / 1000, body frame |
| 19–20 | Relative velocity (x, y) | / 500, body frame |
| 21 | Distance | / 1000 |
| 22 | Hull fraction | [0, 1] |
| 23 | Alive flag | 0 or 1 |

**Enemies (13 features × 2 = 26)** — both enemies, sorted by distance (nearest first):

| Index | Feature | Normalization |
|-------|---------|---------------|
| 24–25 | Relative position (x, y) | / 1000, body frame |
| 26–27 | Relative velocity (x, y) | / 500, body frame |
| 28 | Distance | / 1000 |
| 29 | Hull fraction | [0, 1] |
| 30 | Alive flag | 0 or 1 |
| 31 | Bearing cos | forward component of unit LOS (1 = dead ahead) |
| 32 | Bearing sin | lateral component of unit LOS (0 = on bore) |
| 33 | Radial closing speed | / 500 (positive = closing) |
| 34 | Tangential speed | / 500 |
| 35 | Time-to-target | dist / proj_speed / 5 (0 for hitscan) |
| 36 | Range margin | (weapon_range − dist) / weapon_range |

Enemy 1 occupies indices 37–49 with the same layout. Dead entities have all features zeroed (multiplied by alive flag).

**Engagement zone (3 features)**:

| Index | Feature | Normalization |
|-------|---------|---------------|
| 50–51 | Direction to zone center (x, y) | unit vector, body frame |
| 52 | Zone margin | (zone_r − distance) / zone_r |

### Engagement geometry features

The per-enemy engagement features (indices 31–36) are deterministic transforms of the existing relative position and velocity, designed to reduce sample complexity for fire-control decisions:

- **Bearing cos/sin**: Unit line-of-sight in body frame. When bearing_cos ≈ 1 and bearing_sin ≈ 0, the enemy is directly ahead — the policy can learn a simple threshold for "is a shot plausible?"
- **Radial closing speed**: v_r = −(v_rel · û), positive when closing. Helps predict whether an enemy is entering or leaving weapon range.
- **Tangential speed**: v_t = cross(v_rel, û). Indicates how fast the target is moving across the bore line, relevant for lead angle estimation.
- **Time-to-target**: dist / v_projectile (0 for hitscan). Gives the flight time a projectile would need to reach the enemy's current position.
- **Range margin**: (R_eff − dist) / R_eff. Positive when in weapon range, negative when out. Provides an explicit firing envelope signal.

### Critic observations

The critic input is simply `[own_obs, teammate_obs]` concatenated — 106 features. This is built by `build_critic_obs()` in `spacefight/env/vec_env.py`.

## Rewards

Rewards are per-ship, per-tick. All ships on a team share the same terminal reward.

### Shaping (continuous)

| Signal | Value | Purpose |
|--------|-------|---------|
| Damage dealt to enemies | +0.01 per HP | Encourage aggression |
| Damage taken | −0.01 per HP | Discourage recklessness |
| Fire cost | −0.005 per trigger pull | Penalize wasteful firing |
| Zone violation | quadratic penalty | Force engagement (see [SIMULATION.md](SIMULATION.md)) |

The fire cost is a flat per-trigger-pull penalty applied whenever an alive ship chooses the fire action. At −0.005, a gauss hit (15 HP × 0.01 = +0.15) only requires ~1-in-30 accuracy to break even, so the cost penalizes blind spam without suppressing initiative.

### Terminal

| Outcome | Value |
|---------|-------|
| Team wins (all enemies dead) | +1.0 |
| Team loses (all own ships dead) | −1.0 |

## Rollout Collection

The training loop collects fixed-length rollouts across all parallel environments:

1. For T_STEPS (128) consecutive sim ticks:
   - Build egocentric observations `[N, S, 53]` and critic observations `[N, S, 106]`
   - Forward pass through actor-critic on GPU (batched across all N×S agents)
   - Sample actions, record log-probs and value estimates
   - Step the sim, collect rewards and done flags
   - Store transition in the rollout buffer
2. After the rollout, compute bootstrap values for the final state
3. Compute GAE advantages over the stored transitions

### Buffer layout

The `RolloutBuffer` stores data shaped `[T, N×S, ...]` where T = rollout steps and N×S = total agents across all parallel matches. Stored per timestep:

| Field | Shape | Description |
|-------|-------|-------------|
| `obs` | `[T, N×S, 53]` | Per-agent observations |
| `critic_obs` | `[T, N×S, 106]` | Centralized critic observations |
| `raw_actions` | `[T, N×S, 5]` | Categorical action indices |
| `log_probs` | `[T, N×S]` | Sum of per-head log-probs |
| `values` | `[T, N×S]` | Critic value estimates |
| `rewards` | `[T, N×S]` | Per-agent rewards |
| `dones` | `[T, N×S]` | Episode termination flags |

Done flags are broadcast from per-match `[N]` to per-agent `[N, S]` since all ships in a match end together.

## GAE Computation

Generalized Advantage Estimation with γ = 0.99, λ = 0.95:

```
For t = T-1 down to 0:
    δₜ = rₜ + γ · V(sₜ₊₁) · (1 − doneₜ) − V(sₜ)
    Aₜ = δₜ + γ · λ · (1 − doneₜ) · Aₜ₊₁
```

Returns = advantages + values. Advantages are normalized (zero mean, unit variance) before the PPO update.

## PPO Update

After computing advantages, the PPO update runs K epochs of minibatch gradient descent:

### Procedure

1. Move all rollout data to GPU (single bulk transfer)
2. Normalize advantages globally (mean=0, std=1)
3. For each of K epochs:
   - Randomly shuffle all N×S×T transitions
   - Iterate over minibatches of size BATCH_SIZE
   - For each minibatch:
     - Re-evaluate log-probs and values under the current policy
     - Compute clipped surrogate policy loss
     - Compute MSE value loss against GAE returns
     - Compute entropy bonus
     - Combined loss = `pg_loss + VF_COEFF × vf_loss − ENT_COEFF × entropy`
     - Backprop with gradient clipping

### Clipped surrogate objective

```
ratio = exp(new_log_prob − old_log_prob)
surr1 = ratio × advantage
surr2 = clip(ratio, 1−ε, 1+ε) × advantage
pg_loss = −min(surr1, surr2)
```

## Hyperparameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| N_ENVS | 256 | Parallel matches |
| N_SHIPS | 4 | Ships per match (2v2) |
| T_STEPS | 128 | Rollout steps per update |
| N_UPDATES | 5000 | Total training updates |
| GAMMA | 0.99 | Discount factor |
| LAM | 0.95 | GAE lambda |
| LR | 3e-4 | Adam learning rate |
| CLIP_EPS | 0.2 | PPO clip epsilon |
| K_EPOCHS | 4 | PPO epochs per rollout |
| BATCH_SIZE | 4096 | Minibatch size |
| ENT_COEFF | 0.01 | Entropy bonus coefficient |
| VF_COEFF | 0.5 | Value loss coefficient |
| MAX_GRAD_NORM | 0.5 | Gradient clipping norm |
| CHECKPOINT_INTERVAL | 100 | Save every N updates |

### Derived quantities

- Transitions per rollout: 128 × 256 × 4 = **131,072**
- Minibatches per epoch: 131,072 / 4,096 = **32**
- Gradient steps per update: 4 × 32 = **128**
- Sim ticks per update: 128 (at 30 Hz = 4.27 seconds of game time)
- Total sim ticks: 128 × 5,000 = 640,000 (≈ 5.9 hours of game time)

## Training Loop

The full loop in `train.py`:

```
for update in 1..N_UPDATES:
    # Rollout phase (model.eval, no_grad)
    for t in 1..T_STEPS:
        obs → actor-critic → actions, log_probs, values
        env.step(actions) → next_obs, rewards, dones
        buffer.insert(obs, actions, log_probs, values, rewards, dones)

    # Compute bootstrap values for final state
    # Compute GAE advantages and returns

    # PPO update phase (model.train)
    ppo_update(buffer_data, advantages, returns)

    # Logging every 10 updates
    # Checkpoint every 100 updates
```

### Training metrics

Logged every 10 updates:

| Metric | Description |
|--------|-------------|
| reward | Mean reward per agent-step across the rollout |
| pg_loss | Mean policy gradient loss |
| vf_loss | Mean value function loss |
| entropy | Mean policy entropy (higher = more exploration) |
| episodes | Cumulative episodes completed |
| zone_viol | Fraction of ship-ticks outside the engagement zone |
| first_dmg | Mean tick of first damage in each episode (measures closing speed) |

### Checkpoints

Model weights are saved as `checkpoints/policy_<update>.pt` every 100 updates, plus a final `policy_final.pt`. These are plain `state_dict` files loadable with `torch.load()`.

## Running Training

```bash
# Default settings (256 envs, 5000 updates)
uv run python train.py

# Custom settings
uv run python train.py --n-envs 64 --n-updates 1000 --seed 0
```

Automatically uses CUDA if available, otherwise falls back to CPU.
