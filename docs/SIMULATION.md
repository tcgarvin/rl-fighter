# Simulation Overview

This document describes how the RL Fighter simulation works — the physics, weapons, damage model, environment wrapper, observations, and reward structure.

## Architecture

The simulation lives in `spacefight/sim/` and is a headless, vectorized NumPy engine. It runs N parallel matches simultaneously with no Python loops over ships or matches. The key files:

- **`core.py`** — Physics integration, spawn logic, engagement zone, reward computation, top-level `step()`
- **`weapons.py`** — Projectile spawning, advancement, hit detection, magazine/reload system
- **`damage.py`** — Hull damage application and alive-status bookkeeping

The sim has no dependency on PyTorch or any rendering library.

## SimState

All state is stored in a single `SimState` dataclass of batched NumPy arrays. Most arrays are shaped `[N, S]` where N = number of parallel matches and S = 4 ships (2 per team in 2v2).

### Ship state (dynamic, updated each tick)

| Field | Shape | Description |
|-------|-------|-------------|
| `x`, `y` | `[N, S]` | World position |
| `vx`, `vy` | `[N, S]` | Velocity |
| `theta` | `[N, S]` | Heading (radians) |
| `hull` | `[N, S]` | Current HP |
| `alive` | `[N, S]` | Whether the ship is alive |

### Ship properties (constant within an episode)

| Field | Shape | Description |
|-------|-------|-------------|
| `max_hull` | `[N, S]` | Maximum HP |
| `radius` | `[N, S]` | Collision radius |
| `max_speed` | `[N, S]` | Soft speed cap |
| `turn_rate` | `[N, S]` | Turn rate (rad/s) |
| `thrust_accel` | `[N, S]` | Thrust acceleration |
| `team` | `[N, S]` | Team index (0 or 1) |

### Weapon state

| Field | Shape | Description |
|-------|-------|-------------|
| `cooldown` | `[N, S]` | Time until ship can fire again |
| `ammo` | `[N, S]` | Shots remaining in magazine |
| `reload_timer` | `[N, S]` | Time remaining on reload |

### Projectile pool (fixed size, oldest-overwrite recycling)

| Field | Shape | Description |
|-------|-------|-------------|
| `proj_x`, `proj_y` | `[N, 128]` | Projectile positions |
| `proj_vx`, `proj_vy` | `[N, 128]` | Projectile velocities |
| `proj_alive` | `[N, 128]` | Active flag |
| `proj_owner` | `[N, 128]` | Ship index that fired (-1 = unowned) |
| `proj_ttl` | `[N, 128]` | Time-to-live (seconds) |

### Episode tracking

| Field | Shape | Description |
|-------|-------|-------------|
| `zone_cx`, `zone_cy` | `[N]` | Engagement zone center |
| `zone_r` | `[N]` | Engagement zone radius |
| `t_since_damage` | `[N]` | Ticks since last damage event |
| `done` | `[N]` | Episode-done flag |
| `tick` | `[N]` | Current tick counter |

### Weapon config (scalar, same for all ships)

| Parameter | Value |
|-----------|-------|
| `bullet_speed` | 500.0 units/s |
| `bullet_range` | 800.0 units |
| `bullet_damage` | 15.0 HP |
| `fire_interval` | 0.2s (5 shots/s within magazine) |
| `magazine_size` | 6 shots |
| `reload_time` | 2.0s |

## Physics

The sim runs at **30 Hz** (`DT = 1/30`). Each tick applies the following per ship, all vectorized across N matches and S ships:

### 1. Turn

```
omega = turn_cmd * turn_rate       # turn_cmd ∈ {-1, 0, 1}
theta += omega * DT * alive
```

### 2. Thrust

```
ax = thrust_cmd * thrust_accel * cos(theta)
ay = thrust_cmd * thrust_accel * sin(theta)
```

### 3. Brake (viscous drag)

```
ax -= brake_cmd * DRAG_COEFF * vx      # DRAG_COEFF = 0.5
ay -= brake_cmd * DRAG_COEFF * vy
```

### 4. Soft speed cap

Rather than hard-clamping velocity, extra drag kicks in above `max_speed`:

```
over = max(speed - max_speed, 0)
drag = SOFT_CAP_DRAG * over / speed     # SOFT_CAP_DRAG = 2.0
ax -= drag * vx
ay -= drag * vy
```

This produces smooth, arcade-style movement without velocity discontinuities.

### 5. Integration

```
vx += ax * DT * alive
vy += ay * DT * alive
x  += vx * DT * alive
y  += vy * DT * alive
```

Dead ships freeze in place (multiplied by `alive`).

## Weapons

Currently one weapon type: the **gauss gun**.

### Magazine system

- Ships start with a full magazine (6 shots)
- Fire condition: `fire_cmd AND alive AND cooldown <= 0 AND ammo > 0 AND reload_timer <= 0`
- On fire: spawn projectile, set `cooldown = fire_interval`, decrement `ammo`
- When magazine empties (`ammo <= 0`): auto-reload begins (`reload_timer = reload_time`)
- When reload completes: `ammo` refilled to `magazine_size`

### Projectile spawning

- Bullet velocity = ship velocity + `bullet_speed` along ship heading
- TTL = `bullet_range / bullet_speed` = 1.6 seconds
- Spawns into the first dead slot in the 128-slot pool; if full, overwrites the projectile with the lowest remaining TTL

### Projectile advancement

Each tick:
```
proj_x += proj_vx * DT * proj_alive
proj_y += proj_vy * DT * proj_alive
proj_ttl -= DT * proj_alive
proj_alive &= (proj_ttl > 0)
```

### Hit detection

Point-in-circle: `distance² < ship_radius²` for each projectile against each ship. Team-aware — projectiles only hit enemies (different team than the firing ship). On hit, the projectile is killed and damage is applied.

## Damage

```
hull -= damage * alive
hull = max(hull, 0)
alive &= (hull > 0)
```

No shields, armor, or resistances in the current implementation. Damage is pure kinetic HP reduction.

## Spawning

Teams spawn on opposite sides of the engagement zone center:

- **Per-team distance from center**: 520–720 units (randomized), so teams start 1040–1440 units apart
- **Lateral offset**: ±120 units (spreads teammates)
- **Position jitter**: ±30 units on the forward axis
- **Heading**: fully random (0 to 2π), so ships must orient before engaging

Since weapon range is 800 units, teams always spawn outside firing range and must maneuver to engage.

## Engagement zone

Each episode gets a randomized engagement zone:

- **Center**: within ±60 units of origin
- **Radius**: 800–1000 units (uniform random)

Ships outside the zone receive a quadratic penalty based on how far they've strayed:

```
margin = (zone_r - distance_to_center) / zone_r
penalty = -ZONE_K * max(-margin, 0)²          # ZONE_K = 0.1
```

The penalty scales up from 10% to 100% strength after 150 ticks (5 seconds) without any damage being dealt in the match, discouraging passive play.

## Hulls

Four hull types defined in `data/hulls.yaml`:

| Hull | HP | Radius | Speed | Turn Rate (°/s) | Thrust | Character |
|------|-----|--------|-------|-----------------|--------|-----------|
| Interceptor | 80 | 12.0 | 300.0 | 180 | 400.0 | Fast, fragile, agile |
| Fighter | 150 | 18.0 | 220.0 | 120 | 300.0 | Balanced all-rounder |
| Gunboat | 250 | 25.0 | 160.0 | 80 | 200.0 | Slow, tough, hard to turn |
| Bomber | 120 | 16.0 | 200.0 | 100 | 350.0 | Quick but fragile, high thrust |

By default all ships are fighters. Hull randomization is available but off by default.

## Environment wrapper (VecEnv)

`spacefight/env/vec_env.py` wraps the sim into a standard RL interface:

- `reset() → obs` — resets all matches, returns initial observations
- `step(actions) → (obs, rewards, dones, infos)` — advances one tick

### Episode termination

- **Team elimination**: all ships on one team dead
- **Time limit**: 2700 ticks (90 seconds at 30 Hz)

Finished episodes auto-reset in-place, keeping the vectorized batch running continuously.

### Defaults

- 256 parallel matches
- 4 ships per match (2v2)
- 2700-step episode limit

## Observations

Each ship receives a **36-feature egocentric observation** (built in `spacefight/rl/obs.py`). All spatial quantities are rotated into the ship's body frame so that forward is always +x.

### Feature layout

| Features | Count | Description |
|----------|-------|-------------|
| Self state | 8 | speed, hull fraction, cooldown, sin/cos heading, forward speed, ammo fraction, reload timer |
| Ship properties | 4 | max_hull, max_speed, turn_rate, thrust_accel (each normalized) |
| Ally | 7 | relative position, relative velocity, distance, hull fraction, alive flag |
| Enemy 0 (nearest) | 7 | relative position, relative velocity, distance, hull fraction, alive flag |
| Enemy 1 | 7 | relative position, relative velocity, distance, hull fraction, alive flag |
| Zone | 3 | direction to zone center (body frame), margin |
| **Total** | **36** | |

Enemies are sorted by distance (nearest first). Normalization constants: positions /1000, velocities /500, hull stats /250, speed /300, turn rate /π, thrust /400.

## Rewards

### Per-tick shaping

| Signal | Value | Purpose |
|--------|-------|---------|
| Damage dealt to enemies | +0.01 per HP | Encourage aggression |
| Damage taken | -0.01 per HP | Discourage recklessness |
| Zone violation | quadratic penalty | Force engagement |

### Terminal

| Outcome | Value |
|---------|-------|
| Team wins (all enemies dead) | +1.0 |
| Team loses (all own ships dead) | -1.0 |

All surviving ships on the winning team get the win reward; all ships on the losing team get the loss reward.

## Actions

4 discrete action heads per ship:

| Action | Values | Effect |
|--------|--------|--------|
| Turn | {-1, 0, 1} | Rotate left / none / right |
| Thrust | {0, 1} | Accelerate along heading |
| Brake | {0, 1} | Apply viscous drag |
| Fire | {0, 1} | Fire gauss gun (if able) |

## Determinism

The sim is fully deterministic given a seed. The RNG (`np.random.Generator` with `PCG64`) is used only at reset for spawn positions, zone parameters, and hull selection. Within an episode, the physics are deterministic — same actions always produce the same outcome.
