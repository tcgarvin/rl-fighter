"""Egocentric observation builder for RL agents (2v2).

Each ship sees the world from its own heading frame: relative vectors
are rotated by -theta so that "forward" is always along the +x axis.

Observation vector (53 features per ship):
  Self features (8):
    0: speed / max_speed
    1: hull fraction
    2: weapon cooldown / fire_interval
    3: sin(theta)
    4: cos(theta)
    5: forward speed / max_speed
    6: ammo fraction (ammo / magazine_size)
    7: reload fraction (reload_timer / reload_time)

  Ship properties (4) — hull stats so agent knows what it's flying:
    8:  max_hull / 250 (normalized by gunboat HP)
    9:  max_speed / 300 (normalized by interceptor speed)
    10: turn_rate / pi
    11: thrust_accel / 400 (normalized by interceptor thrust)

  Weapon descriptors (5) — weapon identity and ballistic properties:
    12: is_projectile (bullet or double_gauss)
    13: is_hitscan (laser)
    14: is_guided (missile)
    15: effective_range / 1500
    16: projectile_speed / 500 (0 for hitscan)

  Ally (1 ally in 2v2) (7):
    17-18: relative position (x, y) in body frame / 1000
    19-20: relative velocity (x, y) in body frame / 500
    21: distance / 1000
    22: hull fraction
    23: alive flag

  Enemies (2 enemies in 2v2, sorted by distance) (13 each = 26):
    24-36: enemy 0 (nearest):
      24-25: rel pos (x, y) body frame / 1000
      26-27: rel vel (x, y) body frame / 500
      28: distance / 1000
      29: hull fraction
      30: alive
      31: bearing cos — forward component of unit LOS (1 = dead ahead)
      32: bearing sin — lateral component of unit LOS (0 = on bore)
      33: radial closing speed / 500 (positive = closing)
      34: tangential speed / 500
      35: time-to-target / 5 (dist / proj_speed; 0 for hitscan)
      36: range margin (weapon_range - dist) / weapon_range

    37-49: enemy 1 (same layout)

  Zone (3):
    50-51: zone direction (x, y) unit vector in body frame
    52: zone margin
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from spacefight.sim.core import TEAM_SIZE, SimState

OBS_DIM = 53

# Precomputed relationship tables for 2v2 (4 ships: 0,1 on team 0; 2,3 on team 1)
# ally_map[s] = index of s's teammate
_ALLY_MAP_4 = np.array([1, 0, 3, 2], dtype=np.int32)
# enemy_map[s] = [enemy_0, enemy_1] (fixed order, sorted by distance at runtime)
_ENEMY_MAP_4 = np.array([[2, 3], [2, 3], [0, 1], [0, 1]], dtype=np.int32)

# Weapon type constants (mirror core.py)
_WEAPON_TYPE_BULLET = 0
_WEAPON_TYPE_HITSCAN = 1
_WEAPON_TYPE_MISSILE = 2
_WEAPON_TYPE_DOUBLE = 3


def build_egocentric_obs(state: SimState) -> NDArray[np.float32]:
    """Build egocentric observations for all ships in all environments.

    Fully vectorized: no Python loops over ships.

    Args:
        state: Current SimState with shapes [N, S] for ship arrays.

    Returns:
        Observation array of shape [N, S, 53], float32.
    """
    N, S = state.n_envs, state.n_ships

    obs = np.zeros((N, S, OBS_DIM), dtype=np.float32)

    # Precompute trig for all ships [N, S]
    cos_theta = np.cos(state.theta)
    sin_theta = np.sin(state.theta)
    cos_neg = cos_theta    # cos(-t) = cos(t)
    sin_neg = -sin_theta   # sin(-t) = -sin(t)

    # --- Self features (8) --- all [N, S]
    speed = np.sqrt(state.vx ** 2 + state.vy ** 2)
    max_speed_safe = np.maximum(state.max_speed, 1e-8)
    max_hull_safe = np.maximum(state.max_hull, 1e-8)
    fire_interval = np.maximum(state.fire_interval, 1e-8)  # [N, S]
    reload_time = np.maximum(state.reload_time, 1e-8)      # [N, S]
    mag_size_safe = np.maximum(state.magazine_size, 1)      # [N, S]

    fwd_speed = state.vx * cos_theta + state.vy * sin_theta

    obs[:, :, 0] = speed / max_speed_safe
    obs[:, :, 1] = state.hull / max_hull_safe
    obs[:, :, 2] = state.cooldown / fire_interval
    obs[:, :, 3] = sin_theta
    obs[:, :, 4] = cos_theta
    obs[:, :, 5] = fwd_speed / max_speed_safe
    obs[:, :, 6] = state.ammo.astype(np.float32) / mag_size_safe
    obs[:, :, 7] = state.reload_timer / reload_time

    # --- Ship properties (4) ---
    obs[:, :, 8] = state.max_hull / 250.0
    obs[:, :, 9] = state.max_speed / 300.0
    obs[:, :, 10] = state.turn_rate / math.pi
    obs[:, :, 11] = state.thrust_accel / 400.0

    # --- Weapon descriptors (5) ---
    wtype = state.weapon_type  # [N, S]
    obs[:, :, 12] = ((wtype == _WEAPON_TYPE_BULLET) | (wtype == _WEAPON_TYPE_DOUBLE)).astype(np.float32)
    obs[:, :, 13] = (wtype == _WEAPON_TYPE_HITSCAN).astype(np.float32)
    obs[:, :, 14] = (wtype == _WEAPON_TYPE_MISSILE).astype(np.float32)
    obs[:, :, 15] = state.weapon_range / 1500.0
    obs[:, :, 16] = state.weapon_speed / 500.0  # 0 for hitscan (speed=0 in data)

    # Precompute weapon ballistic info for time-to-target [N, S]
    is_hitscan = wtype == _WEAPON_TYPE_HITSCAN
    weapon_speed_safe = np.where(is_hitscan, 1.0, np.maximum(state.weapon_speed, 1e-8))
    ttt_mask = (~is_hitscan).astype(np.float32)  # zero out TTT for hitscan

    # --- Ally features (7) ---
    ally_idx = _ALLY_MAP_4[:S]  # [S]

    # Relative position: [N, S] for each of x, y
    ally_dx = state.x[:, ally_idx] - state.x
    ally_dy = state.y[:, ally_idx] - state.y
    ally_dvx = state.vx[:, ally_idx] - state.vx
    ally_dvy = state.vy[:, ally_idx] - state.vy

    # Rotate into body frame [N, S]
    ally_rx = ally_dx * cos_neg - ally_dy * sin_neg
    ally_ry = ally_dx * sin_neg + ally_dy * cos_neg
    ally_rvx = ally_dvx * cos_neg - ally_dvy * sin_neg
    ally_rvy = ally_dvx * sin_neg + ally_dvy * cos_neg

    ally_dist = np.sqrt(ally_dx ** 2 + ally_dy ** 2)
    ally_hull_frac = state.hull[:, ally_idx] / np.maximum(state.max_hull[:, ally_idx], 1e-8)
    ally_alive = state.alive[:, ally_idx].astype(np.float32)

    obs[:, :, 17] = ally_rx / 1000.0 * ally_alive
    obs[:, :, 18] = ally_ry / 1000.0 * ally_alive
    obs[:, :, 19] = ally_rvx / 500.0 * ally_alive
    obs[:, :, 20] = ally_rvy / 500.0 * ally_alive
    obs[:, :, 21] = ally_dist / 1000.0 * ally_alive
    obs[:, :, 22] = ally_hull_frac * ally_alive
    obs[:, :, 23] = ally_alive

    # --- Enemy features (13 * 2 = 26) ---
    enemy_map = _ENEMY_MAP_4[:S]  # [S, 2]

    # Gather enemy positions for both enemies: [N, S, 2]
    enemy_x = state.x[:, enemy_map]    # [N, S, 2]
    enemy_y = state.y[:, enemy_map]
    enemy_vx = state.vx[:, enemy_map]
    enemy_vy = state.vy[:, enemy_map]

    # Relative positions [N, S, 2]
    edx = enemy_x - state.x[:, :, np.newaxis]
    edy = enemy_y - state.y[:, :, np.newaxis]
    edvx = enemy_vx - state.vx[:, :, np.newaxis]
    edvy = enemy_vy - state.vy[:, :, np.newaxis]

    # Distance for sorting [N, S, 2]
    enemy_dist = np.sqrt(edx ** 2 + edy ** 2)

    # Sort by distance: argsort along last axis [N, S, 2]
    sort_idx = np.argsort(enemy_dist, axis=2)  # [N, S, 2]

    # Use advanced indexing to reorder all enemy arrays by distance
    n_idx = np.arange(N)[:, np.newaxis, np.newaxis]  # [N, 1, 1]
    s_idx = np.arange(S)[np.newaxis, :, np.newaxis]  # [1, S, 1]
    edx = edx[n_idx, s_idx, sort_idx]
    edy = edy[n_idx, s_idx, sort_idx]
    edvx = edvx[n_idx, s_idx, sort_idx]
    edvy = edvy[n_idx, s_idx, sort_idx]
    enemy_dist = enemy_dist[n_idx, s_idx, sort_idx]

    # Gather hull/alive for sorted enemies
    sorted_enemy_ships = np.take_along_axis(
        np.broadcast_to(enemy_map[np.newaxis, :, :], (N, S, 2)),
        sort_idx, axis=2
    )  # [N, S, 2]
    enemy_hull_frac = np.zeros((N, S, 2), dtype=np.float32)
    enemy_alive = np.zeros((N, S, 2), dtype=np.float32)
    for rank in range(2):
        e_ships = sorted_enemy_ships[:, :, rank]  # [N, S]
        n_flat = np.arange(N)[:, np.newaxis]
        enemy_hull_frac[:, :, rank] = (
            state.hull[n_flat, e_ships]
            / np.maximum(state.max_hull[n_flat, e_ships], 1e-8)
        )
        enemy_alive[:, :, rank] = state.alive[n_flat, e_ships].astype(np.float32)

    # Rotate into body frame [N, S, 2]
    cos_neg_3d = cos_neg[:, :, np.newaxis]
    sin_neg_3d = sin_neg[:, :, np.newaxis]
    erx = edx * cos_neg_3d - edy * sin_neg_3d
    ery = edx * sin_neg_3d + edy * cos_neg_3d
    ervx = edvx * cos_neg_3d - edvy * sin_neg_3d
    ervy = edvx * sin_neg_3d + edvy * cos_neg_3d

    # --- Engagement geometry (computed in body frame) ---
    safe_dist = np.maximum(enemy_dist, 1e-8)  # [N, S, 2]

    # Unit line-of-sight in body frame
    bearing_cos = erx / safe_dist  # 1 = dead ahead, -1 = behind
    bearing_sin = ery / safe_dist  # 0 = on bore, ±1 = perpendicular

    # Radial closing speed: -(v_rel · unit_LOS)
    # In body frame: -(ervx * bearing_cos + ervy * bearing_sin)
    # But bearing is computed from body-frame rel pos, and rel vel is also in body frame
    radial_speed = -(ervx * bearing_cos + ervy * bearing_sin)  # positive = closing

    # Tangential speed: cross(v_rel, unit_LOS) = ervx * bearing_sin - ervy * bearing_cos
    tangential_speed = ervx * bearing_sin - ervy * bearing_cos

    # Time-to-target: dist / weapon_speed (0 for hitscan)
    # weapon_speed_safe and ttt_mask are [N, S], need to broadcast to [N, S, 2]
    ttt = enemy_dist * ttt_mask[:, :, np.newaxis] / weapon_speed_safe[:, :, np.newaxis] / 5.0

    # Range margin: (weapon_range - dist) / weapon_range
    weapon_range_safe = np.maximum(state.weapon_range, 1e-8)  # [N, S]
    range_margin = (state.weapon_range[:, :, np.newaxis] - enemy_dist) / weapon_range_safe[:, :, np.newaxis]

    # Write enemy features for rank 0 (nearest) and rank 1
    for rank in range(2):
        col = 24 + rank * 13
        alive_r = enemy_alive[:, :, rank]
        obs[:, :, col + 0] = erx[:, :, rank] / 1000.0 * alive_r
        obs[:, :, col + 1] = ery[:, :, rank] / 1000.0 * alive_r
        obs[:, :, col + 2] = ervx[:, :, rank] / 500.0 * alive_r
        obs[:, :, col + 3] = ervy[:, :, rank] / 500.0 * alive_r
        obs[:, :, col + 4] = enemy_dist[:, :, rank] / 1000.0 * alive_r
        obs[:, :, col + 5] = enemy_hull_frac[:, :, rank] * alive_r
        obs[:, :, col + 6] = alive_r
        # Engagement geometry
        obs[:, :, col + 7] = bearing_cos[:, :, rank] * alive_r
        obs[:, :, col + 8] = bearing_sin[:, :, rank] * alive_r
        obs[:, :, col + 9] = radial_speed[:, :, rank] / 500.0 * alive_r
        obs[:, :, col + 10] = tangential_speed[:, :, rank] / 500.0 * alive_r
        obs[:, :, col + 11] = ttt[:, :, rank] * alive_r
        obs[:, :, col + 12] = range_margin[:, :, rank] * alive_r

    # --- Zone features (3) ---
    zx = state.zone_cx[:, np.newaxis] - state.x
    zy = state.zone_cy[:, np.newaxis] - state.y
    zone_dist = np.sqrt(zx ** 2 + zy ** 2)
    safe_zone_dist = np.maximum(zone_dist, 1e-8)
    zx_unit = zx / safe_zone_dist
    zy_unit = zy / safe_zone_dist
    obs[:, :, 50] = zx_unit * cos_neg - zy_unit * sin_neg
    obs[:, :, 51] = zx_unit * sin_neg + zy_unit * cos_neg
    obs[:, :, 52] = (state.zone_r[:, np.newaxis] - zone_dist) / state.zone_r[:, np.newaxis]

    return obs
