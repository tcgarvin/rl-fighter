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
    fire_lasers,
    fire_missiles,
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
ZONE_R_MIN = 800.0
ZONE_R_MAX = 1000.0
ZONE_CENTER_RANGE = 60.0  # randomize center within [-60, 60]

# Team configuration
TEAM_SIZE = 2  # ships per team

# Weapon type constants
WEAPON_TYPE_BULLET = 0   # gauss_gun
WEAPON_TYPE_HITSCAN = 1  # laser
WEAPON_TYPE_MISSILE = 2  # guided_missile
WEAPON_TYPE_DOUBLE = 3   # double_gauss (bullet subtype with spread)

# Map from YAML weapon type string to integer
_WEAPON_TYPE_MAP = {
    "gauss_gun": WEAPON_TYPE_BULLET,
    "laser": WEAPON_TYPE_HITSCAN,
    "guided_missile": WEAPON_TYPE_MISSILE,
    "double_gauss": WEAPON_TYPE_DOUBLE,
}


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

    # Per-ship weapon config [N, S] (constant per episode)
    weapon_type: NDArray[np.int32] = field(repr=False)
    weapon_damage: NDArray[np.float32] = field(repr=False)
    weapon_speed: NDArray[np.float32] = field(repr=False)
    weapon_range: NDArray[np.float32] = field(repr=False)
    fire_interval: NDArray[np.float32] = field(repr=False)
    magazine_size: NDArray[np.int32] = field(repr=False)
    reload_time: NDArray[np.float32] = field(repr=False)
    shots_per_fire: NDArray[np.int32] = field(repr=False)
    weapon_offset: NDArray[np.float32] = field(repr=False)  # lateral offset in world units

    # Projectile pool [N, P]
    proj_x: NDArray[np.float32] = field(repr=False)
    proj_y: NDArray[np.float32] = field(repr=False)
    proj_vx: NDArray[np.float32] = field(repr=False)
    proj_vy: NDArray[np.float32] = field(repr=False)
    proj_alive: NDArray[np.bool_] = field(repr=False)
    proj_owner: NDArray[np.int32] = field(repr=False)
    proj_ttl: NDArray[np.float32] = field(repr=False)
    proj_damage: NDArray[np.float32] = field(repr=False)
    proj_type: NDArray[np.int32] = field(repr=False)   # 0=bullet, 1=missile
    proj_target: NDArray[np.int32] = field(repr=False)  # target ship index, -1=none

    # Engagement zone (per episode, constant after reset) [N]
    zone_cx: NDArray[np.float32] = field(repr=False)
    zone_cy: NDArray[np.float32] = field(repr=False)
    zone_r: NDArray[np.float32] = field(repr=False)

    # Idleness tracker [N]
    t_since_damage: NDArray[np.int32] = field(repr=False)

    # Per-ship hull type name (non-array, length S)
    hull_names: list[str] = field(repr=False)
    # Per-ship weapon name (non-array, length S)
    weapon_names: list[str] = field(repr=False)

    # Episode tracking
    done: NDArray[np.bool_] = field(repr=False)  # [N]
    tick: NDArray[np.int32] = field(repr=False)  # [N]

    # Missile guidance config (scalar)
    missile_turn_rate: float = 0.0  # rad/s

    # Laser hit info for visualizer (set each tick, not persistent)
    laser_hits: list | None = field(default=None, repr=False)


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

    if hull_names is None:
        hull_names = ["fighter"] * n_ships

    N, S, P = n_envs, n_ships, MAX_PROJECTILES

    # Build ship property arrays from hull data
    max_hull = np.zeros((N, S), dtype=np.float32)
    radius = np.zeros((N, S), dtype=np.float32)
    max_speed = np.zeros((N, S), dtype=np.float32)
    turn_rate = np.zeros((N, S), dtype=np.float32)
    thrust_accel = np.zeros((N, S), dtype=np.float32)

    # Per-ship weapon config arrays
    weapon_type_arr = np.zeros((N, S), dtype=np.int32)
    weapon_damage = np.zeros((N, S), dtype=np.float32)
    weapon_speed = np.zeros((N, S), dtype=np.float32)
    weapon_range = np.zeros((N, S), dtype=np.float32)
    fire_interval = np.zeros((N, S), dtype=np.float32)
    magazine_size = np.zeros((N, S), dtype=np.int32)
    reload_time_arr = np.zeros((N, S), dtype=np.float32)
    shots_per_fire = np.ones((N, S), dtype=np.int32)
    weapon_offset = np.zeros((N, S), dtype=np.float32)

    weapon_names: list[str] = []
    missile_turn_rate = 0.0

    for s_idx in range(S):
        h = hulls_data[hull_names[s_idx]]
        max_hull[:, s_idx] = h["hp"]
        radius[:, s_idx] = h["radius"]
        max_speed[:, s_idx] = h["speed"]
        turn_rate[:, s_idx] = math.radians(h["turn_rate"])
        thrust_accel[:, s_idx] = h["thrust"]

        # Weapon config for this hull
        wname = h.get("weapon", "gauss_gun")
        weapon_names.append(wname)
        w = weapons_data[wname]

        weapon_type_arr[:, s_idx] = _WEAPON_TYPE_MAP[wname]
        weapon_damage[:, s_idx] = w["damage"]
        weapon_speed[:, s_idx] = w.get("speed", 0.0)
        weapon_range[:, s_idx] = w["range"]
        fire_interval[:, s_idx] = 1.0 / w["fire_rate"]
        magazine_size[:, s_idx] = w.get("magazine_size", 0)
        reload_time_arr[:, s_idx] = w.get("reload_time", 0.0)
        shots_per_fire[:, s_idx] = w.get("shots_per_fire", 1)
        weapon_offset[:, s_idx] = w.get("offset", 0.0)

        if wname == "guided_missile":
            missile_turn_rate = math.radians(w.get("turn_rate", 120.0))

    # Team assignment: first half team 0, second half team 1
    team = np.zeros((N, S), dtype=np.int32)
    for s_idx in range(S):
        team[:, s_idx] = s_idx // TEAM_SIZE

    # Spawn positions: teams on opposing sides, outside optimal weapon range.
    spawn_dist_min = 520.0
    spawn_dist_max = 720.0
    x = np.zeros((N, S), dtype=np.float32)
    y = np.zeros((N, S), dtype=np.float32)
    theta = np.zeros((N, S), dtype=np.float32)

    spawn_dist = rng.uniform(spawn_dist_min, spawn_dist_max, size=N).astype(
        np.float32
    )
    heading = rng.uniform(0.0, 2.0 * math.pi, size=(N, S)).astype(np.float32)
    lateral_offset = rng.uniform(-120.0, 120.0, size=(N, S)).astype(np.float32)
    pos_jitter_x = rng.uniform(-30.0, 30.0, size=(N, S)).astype(np.float32)

    for s_idx in range(S):
        team_id = s_idx // TEAM_SIZE
        sign = 1.0 if team_id == 0 else -1.0
        x[:, s_idx] = sign * spawn_dist + pos_jitter_x[:, s_idx]
        y[:, s_idx] = lateral_offset[:, s_idx]
        theta[:, s_idx] = heading[:, s_idx]

    # Engagement zone
    zone_cx = rng.uniform(
        -ZONE_CENTER_RANGE, ZONE_CENTER_RANGE, size=N
    ).astype(np.float32)
    zone_cy = rng.uniform(
        -ZONE_CENTER_RANGE, ZONE_CENTER_RANGE, size=N
    ).astype(np.float32)
    zone_r = rng.uniform(ZONE_R_MIN, ZONE_R_MAX, size=N).astype(np.float32)

    # Initialize ammo from magazine size (all weapon types use magazines now)
    ammo = magazine_size.copy()

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
        ammo=ammo,
        reload_timer=np.zeros((N, S), dtype=np.float32),
        weapon_type=weapon_type_arr,
        weapon_damage=weapon_damage,
        weapon_speed=weapon_speed,
        weapon_range=weapon_range,
        fire_interval=fire_interval,
        magazine_size=magazine_size,
        reload_time=reload_time_arr,
        shots_per_fire=shots_per_fire,
        weapon_offset=weapon_offset,
        proj_x=np.zeros((N, P), dtype=np.float32),
        proj_y=np.zeros((N, P), dtype=np.float32),
        proj_vx=np.zeros((N, P), dtype=np.float32),
        proj_vy=np.zeros((N, P), dtype=np.float32),
        proj_alive=np.zeros((N, P), dtype=np.bool_),
        proj_owner=np.full((N, P), -1, dtype=np.int32),
        proj_ttl=np.zeros((N, P), dtype=np.float32),
        proj_damage=np.zeros((N, P), dtype=np.float32),
        proj_type=np.zeros((N, P), dtype=np.int32),
        proj_target=np.full((N, P), -1, dtype=np.int32),
        zone_cx=zone_cx,
        zone_cy=zone_cy,
        zone_r=zone_r,
        hull_names=hull_names,
        weapon_names=weapon_names,
        t_since_damage=np.zeros(N, dtype=np.int32),
        done=np.zeros(N, dtype=np.bool_),
        tick=np.zeros(N, dtype=np.int32),
        missile_turn_rate=missile_turn_rate,
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

    # --- Reload timer (all weapon types use magazines now) ---
    reloading = state.reload_timer > 0.0
    state.reload_timer = np.maximum(state.reload_timer - dt, 0.0)
    just_reloaded = reloading & (state.reload_timer <= 0.0)
    state.ammo = np.where(just_reloaded, state.magazine_size, state.ammo)

    # --- Weapons ---
    # Clear laser hits from previous tick
    state.laser_hits = None

    # Determine which weapon system each ship uses
    is_bullet = (state.weapon_type == WEAPON_TYPE_BULLET) | (state.weapon_type == WEAPON_TYPE_DOUBLE)
    is_laser = state.weapon_type == WEAPON_TYPE_HITSCAN
    is_missile = state.weapon_type == WEAPON_TYPE_MISSILE

    # --- Fire bullets (gauss_gun and double_gauss) ---
    bullet_fire_cmd = fire_cmd & is_bullet
    if np.any(bullet_fire_cmd):
        (
            state.proj_x,
            state.proj_y,
            state.proj_vx,
            state.proj_vy,
            state.proj_alive,
            state.proj_owner,
            state.proj_ttl,
            state.proj_damage,
            state.proj_type,
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
            state.proj_damage,
            state.proj_type,
            state.x,
            state.y,
            state.vx,
            state.vy,
            state.theta,
            state.alive,
            bullet_fire_cmd,
            state.cooldown,
            state.ammo,
            state.reload_timer,
            state.weapon_speed,
            state.weapon_range,
            state.weapon_damage,
            state.fire_interval,
            state.magazine_size,
            state.reload_time,
            state.shots_per_fire,
            state.weapon_offset,
        )

    # --- Fire lasers ---
    laser_fire_cmd = fire_cmd & is_laser
    laser_damage = np.zeros((N, S), dtype=np.float32)
    if np.any(laser_fire_cmd):
        laser_damage, state.cooldown, state.ammo, state.reload_timer, state.laser_hits = fire_lasers(
            state.x,
            state.y,
            state.theta,
            state.alive,
            laser_fire_cmd,
            state.cooldown,
            state.ammo,
            state.reload_timer,
            state.weapon_damage,
            state.weapon_range,
            state.fire_interval,
            state.magazine_size,
            state.reload_time,
            state.radius,
            state.team,
        )

    # --- Fire missiles ---
    missile_fire_cmd = fire_cmd & is_missile
    if np.any(missile_fire_cmd):
        (
            state.proj_x,
            state.proj_y,
            state.proj_vx,
            state.proj_vy,
            state.proj_alive,
            state.proj_owner,
            state.proj_ttl,
            state.proj_damage,
            state.proj_type,
            state.proj_target,
            state.cooldown,
            state.ammo,
            state.reload_timer,
        ) = fire_missiles(
            state.proj_x,
            state.proj_y,
            state.proj_vx,
            state.proj_vy,
            state.proj_alive,
            state.proj_owner,
            state.proj_ttl,
            state.proj_damage,
            state.proj_type,
            state.proj_target,
            state.x,
            state.y,
            state.vx,
            state.vy,
            state.theta,
            state.alive,
            missile_fire_cmd,
            state.cooldown,
            state.ammo,
            state.reload_timer,
            state.weapon_speed,
            state.weapon_range,
            state.weapon_damage,
            state.fire_interval,
            state.magazine_size,
            state.reload_time,
            state.team,
        )

    # Advance projectiles (includes missile guidance)
    (
        state.proj_x,
        state.proj_y,
        state.proj_vx,
        state.proj_vy,
        state.proj_ttl,
        state.proj_alive,
    ) = advance_projectiles(
        state.proj_x,
        state.proj_y,
        state.proj_vx,
        state.proj_vy,
        state.proj_alive,
        state.proj_ttl,
        state.proj_type,
        state.proj_target,
        state.x,
        state.y,
        state.alive,
        state.missile_turn_rate,
        dt,
    )

    # Per-projectile damage for hit detection
    damage, state.proj_alive = check_hits(
        state.proj_x,
        state.proj_y,
        state.proj_alive,
        state.proj_owner,
        state.proj_ttl,
        state.proj_damage,
        state.x,
        state.y,
        state.radius,
        state.alive,
        state.team,
    )

    # Add laser damage
    damage = damage + laser_damage

    # --- Damage ---
    state.hull, state.alive = apply_damage(state.hull, damage, state.alive)

    # --- Idleness tracker ---
    any_damage = damage.sum(axis=1) > 0  # [N]
    state.t_since_damage = np.where(any_damage, 0, state.t_since_damage + 1)

    # --- Rewards ---
    rewards = np.zeros((N, S), dtype=np.float32)
    for s_idx in range(S):
        own_team = state.team[0, s_idx]
        for e_idx in range(S):
            if state.team[0, e_idx] != own_team:
                rewards[:, s_idx] += REWARD_DAMAGE_DEALT * damage[:, e_idx]
        rewards[:, s_idx] += REWARD_DAMAGE_TAKEN * damage[:, s_idx]

    # --- Zone penalty ---
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
    team_0_alive = np.zeros(N, dtype=np.bool_)
    team_1_alive = np.zeros(N, dtype=np.bool_)
    for s_idx in range(S):
        if state.team[0, s_idx] == 0:
            team_0_alive |= state.alive[:, s_idx]
        else:
            team_1_alive |= state.alive[:, s_idx]

    team_eliminated = (~team_0_alive | ~team_1_alive)
    newly_done = team_eliminated & ~state.done

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
