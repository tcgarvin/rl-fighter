"""Weapon systems: bullet, laser (hitscan), missile (guided), with magazine-based reload.

Manages a fixed-size pool of point projectiles per match.
"""

import math

import numpy as np
from numpy.typing import NDArray

# Maximum projectiles tracked per match
MAX_PROJECTILES = 128


def _find_slot(proj_alive: NDArray[np.bool_], proj_ttl: NDArray[np.float32], n: int) -> int:
    """Find a free projectile slot for environment n, or recycle the oldest."""
    dead_slots = np.where(~proj_alive[n])[0]
    if len(dead_slots) > 0:
        return int(dead_slots[0])
    return int(np.argmin(proj_ttl[n]))


def fire_bullets(
    proj_x: NDArray[np.float32],
    proj_y: NDArray[np.float32],
    proj_vx: NDArray[np.float32],
    proj_vy: NDArray[np.float32],
    proj_alive: NDArray[np.bool_],
    proj_owner: NDArray[np.int32],
    proj_ttl: NDArray[np.float32],
    proj_damage: NDArray[np.float32],
    proj_type: NDArray[np.int32],
    ship_x: NDArray[np.float32],
    ship_y: NDArray[np.float32],
    ship_vx: NDArray[np.float32],
    ship_vy: NDArray[np.float32],
    ship_theta: NDArray[np.float32],
    ship_alive: NDArray[np.bool_],
    fire_cmd: NDArray[np.bool_],
    cooldown: NDArray[np.float32],
    ammo: NDArray[np.int32],
    reload_timer: NDArray[np.float32],
    weapon_speed: NDArray[np.float32],    # [N, S]
    weapon_range: NDArray[np.float32],    # [N, S]
    weapon_damage: NDArray[np.float32],   # [N, S]
    fire_interval: NDArray[np.float32],   # [N, S]
    magazine_size: NDArray[np.int32],     # [N, S]
    reload_time: NDArray[np.float32],     # [N, S]
    shots_per_fire: NDArray[np.int32],    # [N, S]
    weapon_offset: NDArray[np.float32],   # [N, S] lateral offset in world units
    proj_fire_step: NDArray[np.int32] | None = None,  # [N, P]
    rollout_step: int = -1,
) -> tuple[
    NDArray[np.float32], NDArray[np.float32],
    NDArray[np.float32], NDArray[np.float32],
    NDArray[np.bool_], NDArray[np.int32],
    NDArray[np.float32], NDArray[np.float32],
    NDArray[np.int32],
    NDArray[np.float32], NDArray[np.int32],
    NDArray[np.float32],
]:
    """Spawn new bullets for ships that fire (gauss_gun and double_gauss).

    Returns:
        Updated projectile arrays, cooldown, ammo, and reload_timer.
    """
    N, S = fire_cmd.shape

    can_fire = fire_cmd & ship_alive & (cooldown <= 0.0) & (ammo > 0) & (reload_timer <= 0.0)

    for s in range(S):
        batch_mask = can_fire[:, s]
        if not np.any(batch_mask):
            continue

        firing_indices = np.where(batch_mask)[0]
        fi0 = firing_indices[0]  # representative firing env
        n_shots = int(shots_per_fire[fi0, s])
        lateral = float(weapon_offset[fi0, s])
        b_speed = float(weapon_speed[fi0, s])
        b_range = float(weapon_range[fi0, s])
        b_damage = float(weapon_damage[fi0, s])
        ttl = b_range / b_speed

        # Compute lateral offsets for each shot (perpendicular to heading)
        if n_shots == 1:
            lat_offsets = [0.0]
        else:
            lat_offsets = [lateral / 2, -lateral / 2]

        for lat_off in lat_offsets:
            # All shots fire parallel (same heading), offset perpendicular
            theta_s = ship_theta[firing_indices, s]
            cos_t = np.cos(theta_s)
            sin_t = np.sin(theta_s)
            # Perpendicular direction: rotate heading 90° CCW → (-sin, cos)
            spawn_x = ship_x[firing_indices, s] + (-sin_t) * lat_off
            spawn_y = ship_y[firing_indices, s] + cos_t * lat_off
            bvx = ship_vx[firing_indices, s] + b_speed * cos_t
            bvy = ship_vy[firing_indices, s] + b_speed * sin_t

            for i, n in enumerate(firing_indices):
                slot = _find_slot(proj_alive, proj_ttl, n)
                proj_x[n, slot] = spawn_x[i]
                proj_y[n, slot] = spawn_y[i]
                proj_vx[n, slot] = bvx[i]
                proj_vy[n, slot] = bvy[i]
                proj_alive[n, slot] = True
                proj_owner[n, slot] = s
                proj_ttl[n, slot] = ttl
                proj_damage[n, slot] = b_damage
                proj_type[n, slot] = 0  # bullet
                if proj_fire_step is not None:
                    proj_fire_step[n, slot] = rollout_step

        cooldown[firing_indices, s] = fire_interval[fi0, s]
        ammo[firing_indices, s] -= 1

    return (
        proj_x, proj_y, proj_vx, proj_vy, proj_alive, proj_owner, proj_ttl,
        proj_damage, proj_type,
        cooldown, ammo, reload_timer,
    )


def fire_lasers(
    ship_x: NDArray[np.float32],
    ship_y: NDArray[np.float32],
    ship_theta: NDArray[np.float32],
    ship_alive: NDArray[np.bool_],
    fire_cmd: NDArray[np.bool_],
    cooldown: NDArray[np.float32],
    ammo: NDArray[np.int32],
    reload_timer: NDArray[np.float32],
    weapon_damage: NDArray[np.float32],   # [N, S]
    weapon_range: NDArray[np.float32],    # [N, S]
    fire_interval: NDArray[np.float32],   # [N, S]
    magazine_size: NDArray[np.int32],     # [N, S]
    reload_time: NDArray[np.float32],     # [N, S]
    ship_radius: NDArray[np.float32],     # [N, S]
    ship_team: NDArray[np.int32],         # [N, S]
) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.int32], NDArray[np.float32], list]:
    """Fire hitscan lasers: instant raycast along heading, damage first enemy hit.

    Returns:
        (damage [N, S], updated cooldown [N, S], ammo [N, S], reload_timer [N, S], laser_hits list).
        laser_hits: list of (env_idx, ship_idx, hit_x, hit_y, end_x, end_y) for visualization.
    """
    N, S = fire_cmd.shape
    damage = np.zeros((N, S), dtype=np.float32)
    laser_hits: list[tuple[int, int, float, float, float, float]] = []

    can_fire = fire_cmd & ship_alive & (cooldown <= 0.0) & (ammo > 0) & (reload_timer <= 0.0)

    for s in range(S):
        batch_mask = can_fire[:, s]
        if not np.any(batch_mask):
            continue

        firing_indices = np.where(batch_mask)[0]
        fi0 = firing_indices[0]  # representative firing env
        l_range = float(weapon_range[fi0, s])
        l_damage = float(weapon_damage[fi0, s])

        for n in firing_indices:
            sx = float(ship_x[n, s])
            sy = float(ship_y[n, s])
            theta = float(ship_theta[n, s])
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            own_team = int(ship_team[n, s])

            # Ray endpoint
            end_x = sx + l_range * cos_t
            end_y = sy + l_range * sin_t

            # Check intersection with each enemy ship (closest first)
            best_t = l_range + 1.0
            best_target = -1

            for e in range(S):
                if int(ship_team[n, e]) == own_team:
                    continue
                if not ship_alive[n, e]:
                    continue

                # Point-on-line closest approach
                ex = float(ship_x[n, e])
                ey = float(ship_y[n, e])
                r = float(ship_radius[n, e])

                # Vector from ray origin to circle center
                dx = ex - sx
                dy = ey - sy

                # Project onto ray direction
                proj = dx * cos_t + dy * sin_t
                if proj < 0 or proj > l_range:
                    continue

                # Perpendicular distance
                perp = abs(dx * sin_t - dy * cos_t)
                if perp < r and proj < best_t:
                    best_t = proj
                    best_target = e

            if best_target >= 0:
                hit_x = sx + best_t * cos_t
                hit_y = sy + best_t * sin_t
                damage[n, best_target] += l_damage
                laser_hits.append((int(n), s, hit_x, hit_y, hit_x, hit_y))
            else:
                laser_hits.append((int(n), s, end_x, end_y, end_x, end_y))

            cooldown[n, s] = float(fire_interval[n, s])
            ammo[n, s] -= 1

    return damage, cooldown, ammo, reload_timer, laser_hits


def fire_missiles(
    proj_x: NDArray[np.float32],
    proj_y: NDArray[np.float32],
    proj_vx: NDArray[np.float32],
    proj_vy: NDArray[np.float32],
    proj_alive: NDArray[np.bool_],
    proj_owner: NDArray[np.int32],
    proj_ttl: NDArray[np.float32],
    proj_damage: NDArray[np.float32],
    proj_type: NDArray[np.int32],
    proj_target: NDArray[np.int32],
    ship_x: NDArray[np.float32],
    ship_y: NDArray[np.float32],
    ship_vx: NDArray[np.float32],
    ship_vy: NDArray[np.float32],
    ship_theta: NDArray[np.float32],
    ship_alive: NDArray[np.bool_],
    fire_cmd: NDArray[np.bool_],
    cooldown: NDArray[np.float32],
    ammo: NDArray[np.int32],
    reload_timer: NDArray[np.float32],
    weapon_speed: NDArray[np.float32],    # [N, S]
    weapon_range: NDArray[np.float32],    # [N, S]
    weapon_damage: NDArray[np.float32],   # [N, S]
    fire_interval: NDArray[np.float32],   # [N, S]
    magazine_size: NDArray[np.int32],     # [N, S]
    reload_time: NDArray[np.float32],     # [N, S]
    ship_team: NDArray[np.int32],         # [N, S]
    proj_fire_step: NDArray[np.int32] | None = None,  # [N, P]
    rollout_step: int = -1,
) -> tuple[
    NDArray[np.float32], NDArray[np.float32],
    NDArray[np.float32], NDArray[np.float32],
    NDArray[np.bool_], NDArray[np.int32],
    NDArray[np.float32], NDArray[np.float32],
    NDArray[np.int32], NDArray[np.int32],
    NDArray[np.float32], NDArray[np.int32],
    NDArray[np.float32],
]:
    """Spawn guided missiles with target lock on nearest forward-arc enemy.

    Returns:
        Updated projectile arrays + proj_target, cooldown, ammo, reload_timer.
    """
    N, S = fire_cmd.shape

    can_fire = fire_cmd & ship_alive & (cooldown <= 0.0) & (ammo > 0) & (reload_timer <= 0.0)

    for s in range(S):
        batch_mask = can_fire[:, s]
        if not np.any(batch_mask):
            continue

        firing_indices = np.where(batch_mask)[0]
        fi0 = firing_indices[0]  # representative firing env
        m_speed = float(weapon_speed[fi0, s])
        m_range = float(weapon_range[fi0, s])
        m_damage = float(weapon_damage[fi0, s])
        ttl = m_range / m_speed

        for n in firing_indices:
            sx = float(ship_x[n, s])
            sy = float(ship_y[n, s])
            theta = float(ship_theta[n, s])
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)
            own_team = int(ship_team[n, s])

            # Find nearest enemy in forward 180° arc
            best_dist = float("inf")
            best_target = -1
            for e in range(S):
                if int(ship_team[n, e]) == own_team:
                    continue
                if not ship_alive[n, e]:
                    continue
                dx = float(ship_x[n, e]) - sx
                dy = float(ship_y[n, e]) - sy
                # Forward dot product: positive means in front
                fwd_dot = dx * cos_t + dy * sin_t
                if fwd_dot <= 0:
                    continue
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < best_dist:
                    best_dist = dist
                    best_target = e

            slot = _find_slot(proj_alive, proj_ttl, n)
            proj_x[n, slot] = sx
            proj_y[n, slot] = sy
            proj_vx[n, slot] = float(ship_vx[n, s]) + m_speed * cos_t
            proj_vy[n, slot] = float(ship_vy[n, s]) + m_speed * sin_t
            proj_alive[n, slot] = True
            proj_owner[n, slot] = s
            proj_ttl[n, slot] = ttl
            proj_damage[n, slot] = m_damage
            proj_type[n, slot] = 1  # missile
            proj_target[n, slot] = best_target
            if proj_fire_step is not None:
                proj_fire_step[n, slot] = rollout_step

        cooldown[firing_indices, s] = float(fire_interval[fi0, s])
        ammo[firing_indices, s] -= 1

    return (
        proj_x, proj_y, proj_vx, proj_vy, proj_alive, proj_owner, proj_ttl,
        proj_damage, proj_type, proj_target,
        cooldown, ammo, reload_timer,
    )


def advance_projectiles(
    proj_x: NDArray[np.float32],
    proj_y: NDArray[np.float32],
    proj_vx: NDArray[np.float32],
    proj_vy: NDArray[np.float32],
    proj_alive: NDArray[np.bool_],
    proj_ttl: NDArray[np.float32],
    proj_type: NDArray[np.int32],
    proj_target: NDArray[np.int32],
    ship_x: NDArray[np.float32],
    ship_y: NDArray[np.float32],
    ship_alive: NDArray[np.bool_],
    missile_turn_rate: float,
    dt: float,
) -> tuple[
    NDArray[np.float32], NDArray[np.float32],
    NDArray[np.float32], NDArray[np.float32],
    NDArray[np.float32], NDArray[np.bool_],
]:
    """Move projectiles, apply missile guidance, and expire those past TTL.

    Returns:
        Updated (proj_x, proj_y, proj_vx, proj_vy, proj_ttl, proj_alive).
    """
    alive_mask = proj_alive.astype(np.float32)
    proj_x = proj_x + proj_vx * dt * alive_mask
    proj_y = proj_y + proj_vy * dt * alive_mask
    proj_ttl = proj_ttl - dt * alive_mask
    proj_alive = proj_alive & (proj_ttl > 0.0)

    # --- Missile guidance ---
    if missile_turn_rate > 0.0:
        N, P = proj_alive.shape
        S = ship_x.shape[1]

        # Find missiles that are alive with valid targets
        is_missile = (proj_type == 1) & proj_alive
        has_target = proj_target >= 0

        guided = is_missile & has_target
        if np.any(guided):
            guided_indices = np.where(guided)
            for idx in range(len(guided_indices[0])):
                n = guided_indices[0][idx]
                p = guided_indices[1][idx]
                t = int(proj_target[n, p])

                # If target is dead, clear guidance
                if t >= S or not ship_alive[n, t]:
                    proj_target[n, p] = -1
                    continue

                # Current velocity direction
                vx = float(proj_vx[n, p])
                vy = float(proj_vy[n, p])
                speed = math.sqrt(vx * vx + vy * vy)
                if speed < 1e-8:
                    continue

                # Desired direction toward target
                dx = float(ship_x[n, t]) - float(proj_x[n, p])
                dy = float(ship_y[n, t]) - float(proj_y[n, p])
                dist = math.sqrt(dx * dx + dy * dy)
                if dist < 1e-8:
                    continue

                # Current heading angle
                cur_angle = math.atan2(vy, vx)
                # Desired heading angle
                des_angle = math.atan2(dy, dx)

                # Angular difference (wrapped to [-pi, pi])
                diff = des_angle - cur_angle
                while diff > math.pi:
                    diff -= 2 * math.pi
                while diff < -math.pi:
                    diff += 2 * math.pi

                # Clamp turn
                max_turn = missile_turn_rate * dt
                turn = max(-max_turn, min(max_turn, diff))
                new_angle = cur_angle + turn

                proj_vx[n, p] = speed * math.cos(new_angle)
                proj_vy[n, p] = speed * math.sin(new_angle)

    return proj_x, proj_y, proj_vx, proj_vy, proj_ttl, proj_alive


def check_hits(
    proj_x: NDArray[np.float32],
    proj_y: NDArray[np.float32],
    proj_alive: NDArray[np.bool_],
    proj_owner: NDArray[np.int32],
    proj_ttl: NDArray[np.float32],
    proj_damage: NDArray[np.float32],  # [N, P] per-projectile damage
    ship_x: NDArray[np.float32],
    ship_y: NDArray[np.float32],
    ship_radius: NDArray[np.float32],
    ship_alive: NDArray[np.bool_],
    ship_team: NDArray[np.int32],
) -> tuple[NDArray[np.float32], NDArray[np.bool_], NDArray[np.bool_]]:
    """Check for projectile-ship collisions with team-based friendly fire prevention.

    Uses per-projectile damage instead of a scalar bullet_damage.

    Returns:
        (damage_per_ship [N, S], updated proj_alive [N, P], proj_hit [N, P]).
    """
    N, S = ship_x.shape
    P = proj_x.shape[1]

    # Expand for broadcasting: [N, P, 1] vs [N, 1, S]
    px = proj_x[:, :, np.newaxis]  # [N, P, 1]
    py = proj_y[:, :, np.newaxis]
    sx = ship_x[:, np.newaxis, :]  # [N, 1, S]
    sy = ship_y[:, np.newaxis, :]

    sr = ship_radius[:, np.newaxis, :]  # [N, 1, S]

    dx = px - sx
    dy = py - sy
    dist_sq = dx * dx + dy * dy
    radius_sq = sr * sr

    in_range = dist_sq < radius_sq  # [N, P, S]

    p_alive = proj_alive[:, :, np.newaxis]  # [N, P, 1]
    s_alive = ship_alive[:, np.newaxis, :]  # [N, 1, S]

    # Team-based friendly fire prevention
    owner_expanded = proj_owner[:, :, np.newaxis]  # [N, P, 1]
    safe_owner = np.maximum(owner_expanded, 0)
    owner_team = np.take_along_axis(
        ship_team[:, np.newaxis, :],
        safe_owner,
        axis=2,
    )  # [N, P, 1]
    ship_team_expanded = ship_team[:, np.newaxis, :]  # [N, 1, S]
    not_same_team = owner_team != ship_team_expanded  # [N, P, S]

    valid_owner = proj_owner[:, :, np.newaxis] >= 0  # [N, P, 1]

    hit_mask = in_range & p_alive & s_alive & not_same_team & valid_owner  # [N, P, S]

    # Any hit kills the projectile
    proj_hit = np.any(hit_mask, axis=2)  # [N, P]
    proj_alive = proj_alive & ~proj_hit

    # Accumulate per-projectile damage per ship
    # hit_mask is [N, P, S], proj_damage is [N, P]
    # Multiply hit_mask by proj_damage expanded to [N, P, 1]
    pd = proj_damage[:, :, np.newaxis]  # [N, P, 1]
    damage = np.sum(hit_mask.astype(np.float32) * pd, axis=1)  # [N, S]

    return damage, proj_alive, proj_hit
