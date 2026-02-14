"""Egocentric observation builder for RL agents (2v2).

Each ship sees the world from its own heading frame: relative vectors
are rotated by -theta so that "forward" is always along the +x axis.

Observation vector (36 features per ship):
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

  Ally (1 ally in 2v2) (7):
    12-13: relative position (x, y) in body frame / 1000
    14-15: relative velocity (x, y) in body frame / 500
    16: distance / 1000
    17: hull fraction
    18: alive flag

  Enemies (2 enemies in 2v2, sorted by distance) (7 each = 14):
    19-25: enemy 0 (nearest): rel pos, rel vel, dist, hull frac, alive
    26-32: enemy 1: rel pos, rel vel, dist, hull frac, alive

  Zone (3):
    33-34: zone direction (x, y) unit vector in body frame
    35: zone margin
"""

from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray

from spacefight.sim.core import TEAM_SIZE, SimState

OBS_DIM = 36


def _rotate_into_body_frame(
    dx: NDArray[np.float32],
    dy: NDArray[np.float32],
    cos_neg_theta: NDArray[np.float32],
    sin_neg_theta: NDArray[np.float32],
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    """Rotate world-frame vectors into the ship's body frame."""
    rx = dx * cos_neg_theta - dy * sin_neg_theta
    ry = dx * sin_neg_theta + dy * cos_neg_theta
    return rx, ry


def _write_other_ship_features(
    obs: NDArray[np.float32],
    col_start: int,
    state: SimState,
    s: int,
    other: NDArray[np.int32],
    cos_t: NDArray[np.float32],
    sin_t: NDArray[np.float32],
) -> None:
    """Write 7 features for another ship (ally or enemy) into obs.

    Args:
        obs: Output array [N, S, 36].
        col_start: Starting column index for this ship's features.
        state: SimState.
        s: Index of the observing ship.
        other: [N] indices of the other ship to observe.
        cos_t: cos(-theta) for ship s, shape [N].
        sin_t: sin(-theta) for ship s, shape [N].
    """
    N = state.n_envs
    n_idx = np.arange(N)

    # Relative position in world frame
    dx = state.x[n_idx, other] - state.x[:, s]
    dy = state.y[n_idx, other] - state.y[:, s]
    # Relative velocity in world frame
    dvx = state.vx[n_idx, other] - state.vx[:, s]
    dvy = state.vy[n_idx, other] - state.vy[:, s]

    rx, ry = _rotate_into_body_frame(dx, dy, cos_t, sin_t)
    rvx, rvy = _rotate_into_body_frame(dvx, dvy, cos_t, sin_t)

    dist = np.sqrt(dx * dx + dy * dy)

    max_hull_other = np.maximum(state.max_hull[n_idx, other], 1e-8)
    hull_frac = state.hull[n_idx, other] / max_hull_other
    alive_flag = state.alive[n_idx, other].astype(np.float32)

    # Zero out features for dead ships
    obs[:, s, col_start + 0] = rx / 1000.0 * alive_flag
    obs[:, s, col_start + 1] = ry / 1000.0 * alive_flag
    obs[:, s, col_start + 2] = rvx / 500.0 * alive_flag
    obs[:, s, col_start + 3] = rvy / 500.0 * alive_flag
    obs[:, s, col_start + 4] = dist / 1000.0 * alive_flag
    obs[:, s, col_start + 5] = hull_frac * alive_flag
    obs[:, s, col_start + 6] = alive_flag


def build_egocentric_obs(state: SimState) -> NDArray[np.float32]:
    """Build egocentric observations for all ships in all environments.

    Args:
        state: Current SimState with shapes [N, S] for ship arrays.

    Returns:
        Observation array of shape [N, S, 36], float32.
    """
    N, S = state.n_envs, state.n_ships

    obs = np.zeros((N, S, OBS_DIM), dtype=np.float32)

    for s in range(S):
        # Rotation by -theta (into ego heading frame)
        cos_t = np.cos(-state.theta[:, s])
        sin_t = np.sin(-state.theta[:, s])

        # --- Self features (8) ---
        speed = np.sqrt(state.vx[:, s] ** 2 + state.vy[:, s] ** 2)
        max_speed_safe = np.maximum(state.max_speed[:, s], 1e-8)
        max_hull_safe = np.maximum(state.max_hull[:, s], 1e-8)
        fire_interval = max(state.fire_interval, 1e-8)
        reload_time = max(state.reload_time, 1e-8)

        fwd_speed = (
            state.vx[:, s] * np.cos(state.theta[:, s])
            + state.vy[:, s] * np.sin(state.theta[:, s])
        )

        obs[:, s, 0] = speed / max_speed_safe
        obs[:, s, 1] = state.hull[:, s] / max_hull_safe
        obs[:, s, 2] = state.cooldown[:, s] / fire_interval
        obs[:, s, 3] = np.sin(state.theta[:, s])
        obs[:, s, 4] = np.cos(state.theta[:, s])
        obs[:, s, 5] = fwd_speed / max_speed_safe
        obs[:, s, 6] = state.ammo[:, s].astype(np.float32) / max(state.magazine_size, 1)
        obs[:, s, 7] = state.reload_timer[:, s] / reload_time

        # --- Ship properties (4) ---
        obs[:, s, 8] = state.max_hull[:, s] / 250.0
        obs[:, s, 9] = state.max_speed[:, s] / 300.0
        obs[:, s, 10] = state.turn_rate[:, s] / math.pi
        obs[:, s, 11] = state.thrust_accel[:, s] / 400.0

        # --- Ally features (7) ---
        own_team = state.team[0, s]
        allies = []
        enemies = []
        for other_s in range(S):
            if other_s == s:
                continue
            if state.team[0, other_s] == own_team:
                allies.append(other_s)
            else:
                enemies.append(other_s)

        # Write ally (expect exactly 1 in 2v2)
        if allies:
            ally_idx = np.full(N, allies[0], dtype=np.int32)
            _write_other_ship_features(obs, 12, state, s, ally_idx, cos_t, sin_t)

        # --- Enemy features (14 = 7 * 2) ---
        # Sort enemies by distance (nearest first)
        if enemies:
            n_idx = np.arange(N)
            enemy_dists = []
            for e in enemies:
                dx = state.x[:, e] - state.x[:, s]
                dy = state.y[:, e] - state.y[:, s]
                enemy_dists.append(np.sqrt(dx * dx + dy * dy))

            # Stack and argsort
            dist_stack = np.stack(enemy_dists, axis=1)  # [N, n_enemies]
            sort_idx = np.argsort(dist_stack, axis=1)   # [N, n_enemies]

            enemy_array = np.array(enemies)
            for rank in range(min(len(enemies), 2)):
                col_start = 19 + rank * 7
                # Per-env sorted enemy index
                sorted_enemy = enemy_array[sort_idx[:, rank]]
                _write_other_ship_features(
                    obs, col_start, state, s, sorted_enemy, cos_t, sin_t
                )

        # --- Zone features (3) ---
        zx = state.zone_cx - state.x[:, s]
        zy = state.zone_cy - state.y[:, s]
        zone_dist = np.sqrt(zx**2 + zy**2)
        safe_zone_dist = np.maximum(zone_dist, 1e-8)
        zx_unit = zx / safe_zone_dist
        zy_unit = zy / safe_zone_dist
        obs[:, s, 33], obs[:, s, 34] = _rotate_into_body_frame(
            zx_unit, zy_unit, cos_t, sin_t
        )
        obs[:, s, 35] = (state.zone_r - zone_dist) / state.zone_r

    return obs
