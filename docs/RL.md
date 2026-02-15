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
obs [36] → Linear(256) → ReLU → Linear(256) → ReLU → 4 action heads
```

Each head is an independent `Linear → Categorical`:

| Head | Size | Meaning |
|------|------|---------|
| Turn | 3 | {left, none, right} → mapped to {-1, 0, 1} |
| Thrust | 2 | {off, on} |
| Brake | 2 | {off, on} |
| Fire | 2 | {off, on} |

Actions are sampled independently from each head. The total log-probability is the sum of per-head log-probs; entropy is likewise summed.

### Centralized Critic

The critic sees the agent's own observation concatenated with its teammate's observation (72 features total for 2v2):

```
[own_obs, teammate_obs] [72] → Linear(256) → ReLU → Linear(256) → ReLU → Linear(1)
```

This gives the critic access to team-level information (teammate position, health, ammo) while the actor only sees its own egocentric view. The teammate mapping is fixed: ship 0 ↔ ship 1, ship 2 ↔ ship 3.

## Observations

Each ship receives a **36-feature egocentric observation** built in `spacefight/rl/obs.py`. All spatial quantities are rotated into the ship's body frame (forward = +x axis).

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

**Ally (7 features)** — one teammate in 2v2:

| Index | Feature | Normalization |
|-------|---------|---------------|
| 12–13 | Relative position (x, y) | / 1000, body frame |
| 14–15 | Relative velocity (x, y) | / 500, body frame |
| 16 | Distance | / 1000 |
| 17 | Hull fraction | [0, 1] |
| 18 | Alive flag | 0 or 1 |

**Enemies (7 features × 2 = 14)** — both enemies, sorted by distance (nearest first):

| Index | Feature | Normalization |
|-------|---------|---------------|
| 19–25 | Enemy 0 (nearest) | same layout as ally |
| 26–32 | Enemy 1 | same layout as ally |

**Engagement zone (3 features)**:

| Index | Feature | Normalization |
|-------|---------|---------------|
| 33–34 | Direction to zone center (x, y) | unit vector, body frame |
| 35 | Zone margin | (zone_r − distance) / zone_r |

Dead entities have all features zeroed (multiplied by alive flag).

### Critic observations

The critic input is simply `[own_obs, teammate_obs]` concatenated — 72 features. This is built by `build_critic_obs()` in `spacefight/env/vec_env.py`.

## Rewards

Rewards are per-ship, per-tick. All ships on a team share the same terminal reward.

### Shaping (continuous)

| Signal | Value | Purpose |
|--------|-------|---------|
| Damage dealt to enemies | +0.01 per HP | Encourage aggression |
| Damage taken | −0.01 per HP | Discourage recklessness |
| Zone violation | quadratic penalty | Force engagement (see [SIMULATION.md](SIMULATION.md)) |

### Terminal

| Outcome | Value |
|---------|-------|
| Team wins (all enemies dead) | +1.0 |
| Team loses (all own ships dead) | −1.0 |

## Rollout Collection

The training loop collects fixed-length rollouts across all parallel environments:

1. For T_STEPS (128) consecutive sim ticks:
   - Build egocentric observations `[N, S, 36]` and critic observations `[N, S, 72]`
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
| `obs` | `[T, N×S, 36]` | Per-agent observations |
| `critic_obs` | `[T, N×S, 72]` | Centralized critic observations |
| `raw_actions` | `[T, N×S, 4]` | Categorical action indices |
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
