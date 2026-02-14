"""Bullet projectile system with magazine-based reload.

Manages a fixed-size pool of point projectiles per match.
"""

import numpy as np
from numpy.typing import NDArray

# Maximum projectiles tracked per match
MAX_PROJECTILES = 128


def fire_bullets(
    proj_x: NDArray[np.float32],
    proj_y: NDArray[np.float32],
    proj_vx: NDArray[np.float32],
    proj_vy: NDArray[np.float32],
    proj_alive: NDArray[np.bool_],
    proj_owner: NDArray[np.int32],
    proj_ttl: NDArray[np.float32],
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
    bullet_speed: float,
    bullet_range: float,
    fire_interval: float,
    magazine_size: int,
    reload_time: float,
) -> tuple[
    NDArray[np.float32],
    NDArray[np.float32],
    NDArray[np.float32],
    NDArray[np.float32],
    NDArray[np.bool_],
    NDArray[np.int32],
    NDArray[np.float32],
    NDArray[np.float32],
    NDArray[np.int32],
    NDArray[np.float32],
]:
    """Spawn new bullets for ships that fire, with magazine/reload mechanics.

    Args:
        proj_*: Projectile pool arrays, shape [N, P].
        ship_*: Ship state arrays, shape [N, S].
        fire_cmd: Fire command per ship, shape [N, S].
        cooldown: Time remaining before ship can fire again, shape [N, S].
        ammo: Shots remaining in current magazine, shape [N, S].
        reload_timer: Time remaining on reload, shape [N, S].
        bullet_speed: Speed of bullet relative to ship.
        bullet_range: Max travel distance of bullet.
        fire_interval: Minimum time between shots (1/fire_rate).
        magazine_size: Shots per magazine.
        reload_time: Seconds to reload empty magazine.

    Returns:
        Updated projectile arrays, cooldown, ammo, and reload_timer.
    """
    N, S = fire_cmd.shape
    P = proj_alive.shape[1]

    can_fire = fire_cmd & ship_alive & (cooldown <= 0.0) & (ammo > 0) & (reload_timer <= 0.0)
    ttl = bullet_range / bullet_speed

    for s in range(S):
        batch_mask = can_fire[:, s]
        if not np.any(batch_mask):
            continue

        firing_indices = np.where(batch_mask)[0]

        cos_t = np.cos(ship_theta[firing_indices, s])
        sin_t = np.sin(ship_theta[firing_indices, s])
        bvx = ship_vx[firing_indices, s] + bullet_speed * cos_t
        bvy = ship_vy[firing_indices, s] + bullet_speed * sin_t

        for i, n in enumerate(firing_indices):
            # Find first dead slot; if none, recycle oldest (lowest TTL)
            dead_slots = np.where(~proj_alive[n])[0]
            if len(dead_slots) > 0:
                slot = dead_slots[0]
            else:
                slot = int(np.argmin(proj_ttl[n]))

            proj_x[n, slot] = ship_x[n, s]
            proj_y[n, slot] = ship_y[n, s]
            proj_vx[n, slot] = bvx[i]
            proj_vy[n, slot] = bvy[i]
            proj_alive[n, slot] = True
            proj_owner[n, slot] = s
            proj_ttl[n, slot] = ttl

        cooldown[firing_indices, s] = fire_interval
        ammo[firing_indices, s] -= 1

    # Auto-reload when magazine is empty
    empty_mag = (ammo <= 0) & (reload_timer <= 0.0) & ship_alive
    reload_timer = np.where(empty_mag, reload_time, reload_timer)

    return (
        proj_x, proj_y, proj_vx, proj_vy, proj_alive, proj_owner, proj_ttl,
        cooldown, ammo, reload_timer,
    )


def advance_projectiles(
    proj_x: NDArray[np.float32],
    proj_y: NDArray[np.float32],
    proj_vx: NDArray[np.float32],
    proj_vy: NDArray[np.float32],
    proj_alive: NDArray[np.bool_],
    proj_ttl: NDArray[np.float32],
    dt: float,
) -> tuple[
    NDArray[np.float32],
    NDArray[np.float32],
    NDArray[np.float32],
    NDArray[np.bool_],
]:
    """Move projectiles and expire those past their TTL.

    Returns:
        Updated (proj_x, proj_y, proj_ttl, proj_alive).
    """
    alive_mask = proj_alive.astype(np.float32)
    proj_x = proj_x + proj_vx * dt * alive_mask
    proj_y = proj_y + proj_vy * dt * alive_mask
    proj_ttl = proj_ttl - dt * alive_mask
    proj_alive = proj_alive & (proj_ttl > 0.0)
    return proj_x, proj_y, proj_ttl, proj_alive


def check_hits(
    proj_x: NDArray[np.float32],
    proj_y: NDArray[np.float32],
    proj_alive: NDArray[np.bool_],
    proj_owner: NDArray[np.int32],
    proj_ttl: NDArray[np.float32],
    ship_x: NDArray[np.float32],
    ship_y: NDArray[np.float32],
    ship_radius: NDArray[np.float32],
    ship_alive: NDArray[np.bool_],
    ship_team: NDArray[np.int32],
    bullet_damage: float,
) -> tuple[NDArray[np.float32], NDArray[np.bool_]]:
    """Check for bullet-ship collisions with team-based friendly fire prevention.

    A bullet hits a ship if within ship_radius and the ship is on a different
    team than the projectile owner.

    Args:
        proj_*: Projectile arrays, shape [N, P].
        ship_*: Ship arrays, shape [N, S].
        ship_team: Team assignment per ship, shape [N, S].
        bullet_damage: Damage per hit.

    Returns:
        (damage_per_ship [N, S], updated proj_alive [N, P]).
    """
    N, S = ship_x.shape
    P = proj_x.shape[1]

    # Expand for broadcasting: [N, P, 1] vs [N, 1, S]
    px = proj_x[:, :, np.newaxis]  # [N, P, 1]
    py = proj_y[:, :, np.newaxis]
    sx = ship_x[:, np.newaxis, :]  # [N, 1, S]
    sy = ship_y[:, np.newaxis, :]

    # ship_radius is [N, S] — expand to [N, 1, S]
    sr = ship_radius[:, np.newaxis, :]  # [N, 1, S]

    dx = px - sx
    dy = py - sy
    dist_sq = dx * dx + dy * dy
    radius_sq = sr * sr

    in_range = dist_sq < radius_sq  # [N, P, S]

    # Mask: projectile alive, ship alive, not same team
    p_alive = proj_alive[:, :, np.newaxis]  # [N, P, 1]
    s_alive = ship_alive[:, np.newaxis, :]  # [N, 1, S]

    # Team-based friendly fire prevention: proj_owner -> owner's team
    owner_expanded = proj_owner[:, :, np.newaxis]  # [N, P, 1]
    # Gather team of projectile owner: team[n, owner[n, p]]
    # owner can be -1 for unowned projectiles, clamp to 0 for indexing
    safe_owner = np.maximum(owner_expanded, 0)
    # Build owner team array [N, P, 1]
    owner_team = np.take_along_axis(
        ship_team[:, np.newaxis, :],  # [N, 1, S]
        safe_owner,  # [N, P, 1] used as index into axis=2
        axis=2,
    )  # [N, P, 1]
    ship_team_expanded = ship_team[:, np.newaxis, :]  # [N, 1, S]
    not_same_team = owner_team != ship_team_expanded  # [N, P, S]

    # Also exclude unowned projectiles (owner == -1)
    valid_owner = proj_owner[:, :, np.newaxis] >= 0  # [N, P, 1]

    hit_mask = in_range & p_alive & s_alive & not_same_team & valid_owner  # [N, P, S]

    # Any hit kills the projectile
    proj_hit = np.any(hit_mask, axis=2)  # [N, P]
    proj_alive = proj_alive & ~proj_hit

    # Accumulate damage per ship
    damage = np.sum(hit_mask.astype(np.float32), axis=1) * bullet_damage  # [N, S]

    return damage, proj_alive
