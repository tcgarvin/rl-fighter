"""Batched space combat simulation core.

All state is stored as NumPy arrays shaped [N, ...] where N is batch size.
Ships are indexed along axis 1 as [N, S, ...] where S=max ships per match.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from numpy.typing import NDArray

from spacefight.sim.damage import apply_damage
from spacefight.sim.weapons import (
    MAX_PROJECTILES,
    advance_projectiles,
    check_hits,
    fire_bullets,
)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DT = 1.0 / 30.0  # 30 Hz tick
DRAG_COEFF = 0.5  # viscous drag for braking
SOFT_CAP_DRAG = 2.0  # extra drag above v_max

# Reward shaping coefficients
REWARD_WIN = 1.0
REWARD_LOSE = -1.0
REWARD_DAMAGE_DEALT = 0.01
REWARD_DAMAGE_TAKEN = -0.01

# Engagement zone shaping
ZONE_K = 0.1  # quadratic penalty scale outside zone
T_IDLE_TICKS = 150  # 5 seconds at 30 Hz before full penalty
ZONE_R_MIN = 500.0
ZONE_R_MAX = 700.0
ZONE_CENTER_RANGE = 60.0  # randomize center within [-60, 60]

# Team configuration
TEAM_SIZE = 2  # ships per team


def load_hulls() -> dict[str, dict[str, Any]]:
    """Load hull definitions from YAML."""
    with open(DATA_DIR / "hulls.yaml") as f:
        return yaml.safe_load(f)["hulls"]


def load_weapons() -> dict[str, dict[str, Any]]:
    """Load weapon definitions from YAML."""
    with open(DATA_DIR / "weapons.yaml") as f:
        return yaml.safe_load(f)["weapons"]


@dataclass
class SimState:
    """Complete batched simulation state.

    All arrays use float32 unless otherwise noted.
    N = batch size, S = max ships per match (4 for 2v2), P = max projectiles.
    """

    n_envs: int
    n_ships: int  # S, ships per match

    # Ship state [N, S]
    x: NDArray[np.float32] = field(repr=False)
    y: NDArray[np.float32] = field(repr=False)
    vx: NDArray[np.float32] = field(repr=False)
    vy: NDArray[np.float32] = field(repr=False)
    theta: NDArray[np.float32] = field(repr=False)  # heading in radians
    hull: NDArray[np.float32] = field(repr=False)
    alive: NDArray[np.bool_] = field(repr=False)

    # Ship properties (constant per episode) [N, S]
    max_hull: NDArray[np.float32] = field(repr=False)
    radius: NDArray[np.float32] = field(repr=False)
    max_speed: NDArray[np.float32] = field(repr=False)
    turn_rate: NDArray[np.float32] = field(repr=False)  # rad/s
    thrust_accel: NDArray[np.float32] = field(repr=False)

    # Team assignment [N, S] int32 (constant per episode)
    team: NDArray[np.int32] = field(repr=False)

    # Weapon state [N, S]
    cooldown: NDArray[np.float32] = field(repr=False)
    ammo: NDArray[np.int32] = field(repr=False)
    reload_timer: NDArray[np.float32] = field(repr=False)

    # Projectile pool [N, P]
    proj_x: NDArray[np.float32] = field(repr=False)
    proj_y: NDArray[np.float32] = field(repr=False)
    proj_vx: NDArray[np.float32] = field(repr=False)
    proj_vy: NDArray[np.float32] = field(repr=False)
    proj_alive: NDArray[np.bool_] = field(repr=False)
    proj_owner: NDArray[np.int32] = field(repr=False)
    proj_ttl: NDArray[np.float32] = field(repr=False)

    # Engagement zone (per episode, constant after reset) [N]
    zone_cx: NDArray[np.float32] = field(repr=False)
    zone_cy: NDArray[np.float32] = field(repr=False)
    zone_r: NDArray[np.float32] = field(repr=False)

    # Idleness tracker [N]
    t_since_damage: NDArray[np.int32] = field(repr=False)

    # Per-ship hull type name (non-array, length S)
    hull_names: list[str] = field(repr=False)

    # Episode tracking
    done: NDArray[np.bool_] = field(repr=False)  # [N]
    tick: NDArray[np.int32] = field(repr=False)  # [N]

    # Weapon config (scalar, same for all)
    bullet_speed: float = 500.0
    bullet_range: float = 800.0
    bullet_damage: float = 15.0
    fire_interval: float = 0.2  # 1/fire_rate
    magazine_size: int = 6
    reload_time: float = 2.0


def reset(
    n_envs: int,
    hull_names: list[str] | None = None,
    seed: int | None = None,
    n_ships: int = 4,
) -> SimState:
    """Create a fresh batch of environments.

    Args:
        n_envs: Number of parallel matches (N).
        hull_names: List of hull types to use, one per ship slot.
                    If None, all ships use "fighter".
        seed: Random seed for reproducibility.
        n_ships: Ships per match (default 4 for 2v2).

    Returns:
        Initialized SimState.
    """
    rng = np.random.default_rng(seed)
    hulls_data = load_hulls()
    weapons_data = load_weapons()
    weapon = weapons_data["gauss_gun"]

    if hull_names is None:
        hull_names = ["fighter"] * n_ships

    N, S, P = n_envs, n_ships, MAX_PROJECTILES

    # Build ship property arrays from hull data
    max_hull = np.zeros((N, S), dtype=np.float32)
    radius = np.zeros((N, S), dtype=np.float32)
    max_speed = np.zeros((N, S), dtype=np.float32)
    turn_rate = np.zeros((N, S), dtype=np.float32)
    thrust_accel = np.zeros((N, S), dtype=np.float32)

    for s_idx in range(S):
        h = hulls_data[hull_names[s_idx]]
        max_hull[:, s_idx] = h["hp"]
        radius[:, s_idx] = h["radius"]
        max_speed[:, s_idx] = h["speed"]
        turn_rate[:, s_idx] = math.radians(h["turn_rate"])
        thrust_accel[:, s_idx] = h["thrust"]

    # Team assignment: first half team 0, second half team 1
    team = np.zeros((N, S), dtype=np.int32)
    for s_idx in range(S):
        team[:, s_idx] = s_idx // TEAM_SIZE

    # Spawn positions: teams on opposing sides
    spawn_dist = 350.0
    x = np.zeros((N, S), dtype=np.float32)
    y = np.zeros((N, S), dtype=np.float32)
    theta = np.zeros((N, S), dtype=np.float32)

    angle_jitter = rng.uniform(-0.3, 0.3, size=(N, S)).astype(np.float32)
    pos_jitter_x = rng.uniform(-30.0, 30.0, size=(N, S)).astype(np.float32)
    pos_jitter_y = rng.uniform(-30.0, 30.0, size=(N, S)).astype(np.float32)

    for s_idx in range(S):
        team_id = s_idx // TEAM_SIZE
        teammate_idx = s_idx % TEAM_SIZE  # 0 or 1 within team
        sign = 1.0 if team_id == 0 else -1.0
        # Offset teammates vertically so they don't stack
        y_team_offset = (teammate_idx - 0.5) * 60.0
        x[:, s_idx] = sign * spawn_dist + pos_jitter_x[:, s_idx]
        y[:, s_idx] = y_team_offset + pos_jitter_y[:, s_idx]
        # Face toward center
        theta[:, s_idx] = (math.pi if sign > 0 else 0.0) + angle_jitter[:, s_idx]

    # Engagement zone: randomize center and radius per episode
    zone_cx = rng.uniform(
        -ZONE_CENTER_RANGE, ZONE_CENTER_RANGE, size=N
    ).astype(np.float32)
    zone_cy = rng.uniform(
        -ZONE_CENTER_RANGE, ZONE_CENTER_RANGE, size=N
    ).astype(np.float32)
    zone_r = rng.uniform(ZONE_R_MIN, ZONE_R_MAX, size=N).astype(np.float32)

    magazine_size = weapon.get("magazine_size", 6)
    reload_time = weapon.get("reload_time", 2.0)

    return SimState(
        n_envs=N,
        n_ships=S,
        x=x,
        y=y,
        vx=np.zeros((N, S), dtype=np.float32),
        vy=np.zeros((N, S), dtype=np.float32),
        theta=theta,
        hull=max_hull.copy(),
        alive=np.ones((N, S), dtype=np.bool_),
        max_hull=max_hull,
        radius=radius,
        max_speed=max_speed,
        turn_rate=turn_rate,
        thrust_accel=thrust_accel,
        team=team,
        cooldown=np.zeros((N, S), dtype=np.float32),
        ammo=np.full((N, S), magazine_size, dtype=np.int32),
        reload_timer=np.zeros((N, S), dtype=np.float32),
        proj_x=np.zeros((N, P), dtype=np.float32),
        proj_y=np.zeros((N, P), dtype=np.float32),
        proj_vx=np.zeros((N, P), dtype=np.float32),
        proj_vy=np.zeros((N, P), dtype=np.float32),
        proj_alive=np.zeros((N, P), dtype=np.bool_),
        proj_owner=np.full((N, P), -1, dtype=np.int32),
        proj_ttl=np.zeros((N, P), dtype=np.float32),
        zone_cx=zone_cx,
        zone_cy=zone_cy,
        zone_r=zone_r,
        hull_names=hull_names,
        t_since_damage=np.zeros(N, dtype=np.int32),
        done=np.zeros(N, dtype=np.bool_),
        tick=np.zeros(N, dtype=np.int32),
        bullet_speed=weapon["speed"],
        bullet_range=weapon["range"],
        bullet_damage=weapon["damage"],
        fire_interval=1.0 / weapon["fire_rate"],
        magazine_size=magazine_size,
        reload_time=reload_time,
    )


def step(
    state: SimState,
    actions: NDArray[np.int32],
) -> tuple[SimState, NDArray[np.float32], NDArray[np.bool_]]:
    """Advance simulation by one tick.

    Args:
        state: Current SimState.
        actions: Action array [N, S, 4] where the 4 action heads are:
                 [turn(-1/0/1), thrust(0/1), brake(0/1), fire(0/1)]

    Returns:
        (state, rewards [N, S], dones [N]).
    """
    N, S = state.n_envs, state.n_ships
    dt = DT

    # Parse actions
    turn_cmd = actions[:, :, 0].astype(np.float32)   # -1, 0, 1
    thrust_cmd = actions[:, :, 1].astype(np.float32)  # 0 or 1
    brake_cmd = actions[:, :, 2].astype(np.float32)   # 0 or 1
    fire_cmd = actions[:, :, 3].astype(np.bool_)

    alive_f = state.alive.astype(np.float32)

    # --- Physics ---
    # Turn
    omega = turn_cmd * state.turn_rate  # rad/s
    state.theta = state.theta + omega * dt * alive_f

    # Thrust acceleration along heading
    cos_t = np.cos(state.theta)
    sin_t = np.sin(state.theta)
    ax = thrust_cmd * state.thrust_accel * cos_t
    ay = thrust_cmd * state.thrust_accel * sin_t

    # Brake: viscous drag
    ax = ax - brake_cmd * DRAG_COEFF * state.vx
    ay = ay - brake_cmd * DRAG_COEFF * state.vy

    # Soft speed cap: extra drag above v_max
    speed = np.sqrt(state.vx**2 + state.vy**2)
    over_speed = np.maximum(speed - state.max_speed, 0.0)
    # Direction of velocity for drag (avoid division by zero)
    safe_speed = np.maximum(speed, 1e-8)
    drag_factor = SOFT_CAP_DRAG * over_speed / safe_speed
    ax = ax - drag_factor * state.vx
    ay = ay - drag_factor * state.vy

    # Integrate velocity and position (only for alive ships)
    state.vx = state.vx + ax * dt * alive_f
    state.vy = state.vy + ay * dt * alive_f
    state.x = state.x + state.vx * dt * alive_f
    state.y = state.y + state.vy * dt * alive_f

    # Decrease weapon cooldown
    state.cooldown = np.maximum(state.cooldown - dt, 0.0)

    # --- Reload timer ---
    reloading = state.reload_timer > 0.0
    state.reload_timer = np.maximum(state.reload_timer - dt, 0.0)
    # Reload complete: refill ammo
    just_reloaded = reloading & (state.reload_timer <= 0.0)
    state.ammo = np.where(just_reloaded, state.magazine_size, state.ammo)

    # --- Weapons ---
    (
        state.proj_x,
        state.proj_y,
        state.proj_vx,
        state.proj_vy,
        state.proj_alive,
        state.proj_owner,
        state.proj_ttl,
        state.cooldown,
        state.ammo,
        state.reload_timer,
    ) = fire_bullets(
        state.proj_x,
        state.proj_y,
        state.proj_vx,
        state.proj_vy,
        state.proj_alive,
        state.proj_owner,
        state.proj_ttl,
        state.x,
        state.y,
        state.vx,
        state.vy,
        state.theta,
        state.alive,
        fire_cmd,
        state.cooldown,
        state.ammo,
        state.reload_timer,
        state.bullet_speed,
        state.bullet_range,
        state.fire_interval,
        state.magazine_size,
        state.reload_time,
    )

    state.proj_x, state.proj_y, state.proj_ttl, state.proj_alive = advance_projectiles(
        state.proj_x,
        state.proj_y,
        state.proj_vx,
        state.proj_vy,
        state.proj_alive,
        state.proj_ttl,
        dt,
    )

    # Per-ship radius for hit detection
    # radius is [N, S]; check_hits needs [N, S] now for per-env hull types
    damage, state.proj_alive = check_hits(
        state.proj_x,
        state.proj_y,
        state.proj_alive,
        state.proj_owner,
        state.proj_ttl,
        state.x,
        state.y,
        state.radius,
        state.alive,
        state.team,
        state.bullet_damage,
    )

    # --- Damage ---
    state.hull, state.alive = apply_damage(state.hull, damage, state.alive)

    # --- Idleness tracker ---
    any_damage = damage.sum(axis=1) > 0  # [N]
    state.t_since_damage = np.where(any_damage, 0, state.t_since_damage + 1)

    # --- Rewards ---
    rewards = np.zeros((N, S), dtype=np.float32)
    # Damage dealt to enemies and damage taken
    for s_idx in range(S):
        own_team = state.team[0, s_idx]
        # Sum damage dealt to all enemies by this ship's projectiles
        for e_idx in range(S):
            if state.team[0, e_idx] != own_team:
                rewards[:, s_idx] += REWARD_DAMAGE_DEALT * damage[:, e_idx]
        # Penalty for own damage taken
        rewards[:, s_idx] += REWARD_DAMAGE_TAKEN * damage[:, s_idx]

    # --- Zone penalty ---
    # Distance from each ship to zone center [N, S]
    dx_zone = state.x - state.zone_cx[:, None]
    dy_zone = state.y - state.zone_cy[:, None]
    dist_to_center = np.sqrt(dx_zone**2 + dy_zone**2)
    margin = (state.zone_r[:, None] - dist_to_center) / state.zone_r[:, None]
    raw_penalty = ZONE_K * np.maximum(-margin, 0.0) ** 2
    idle_scale = np.where(
        state.t_since_damage > T_IDLE_TICKS, 1.0, 0.1
    ).astype(np.float32)
    rewards -= idle_scale[:, None] * raw_penalty

    # --- Win/loss check (team-based) ---
    # For each team, check if all members are dead
    team_0_alive = np.zeros(N, dtype=np.bool_)
    team_1_alive = np.zeros(N, dtype=np.bool_)
    for s_idx in range(S):
        if state.team[0, s_idx] == 0:
            team_0_alive |= state.alive[:, s_idx]
        else:
            team_1_alive |= state.alive[:, s_idx]

    # Episode done when an entire team is eliminated
    team_eliminated = (~team_0_alive | ~team_1_alive)
    newly_done = team_eliminated & ~state.done  # [N]

    # Assign win/loss rewards for newly done episodes
    for s_idx in range(S):
        own_team = state.team[0, s_idx]
        if own_team == 0:
            own_team_alive = team_0_alive
            enemy_team_alive = team_1_alive
        else:
            own_team_alive = team_1_alive
            enemy_team_alive = team_0_alive

        win_mask = newly_done & own_team_alive & ~enemy_team_alive
        lose_mask = newly_done & ~own_team_alive & enemy_team_alive
        rewards[win_mask, s_idx] += REWARD_WIN
        rewards[lose_mask, s_idx] += REWARD_LOSE

    state.done = state.done | newly_done
    state.tick = state.tick + 1

    return state, rewards, state.done
