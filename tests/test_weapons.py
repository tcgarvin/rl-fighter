"""Tests for weapon firing, projectile movement, collision, and magazine/reload."""

import math

import numpy as np
import pytest

from spacefight.sim.weapons import (
    MAX_PROJECTILES,
    advance_projectiles,
    check_hits,
    fire_bullets,
)


def _empty_projectiles(n: int, p: int = MAX_PROJECTILES):
    return {
        "proj_x": np.zeros((n, p), dtype=np.float32),
        "proj_y": np.zeros((n, p), dtype=np.float32),
        "proj_vx": np.zeros((n, p), dtype=np.float32),
        "proj_vy": np.zeros((n, p), dtype=np.float32),
        "proj_alive": np.zeros((n, p), dtype=np.bool_),
        "proj_owner": np.full((n, p), -1, dtype=np.int32),
        "proj_ttl": np.zeros((n, p), dtype=np.float32),
    }


class TestFireBullets:
    def test_bullet_spawns_on_fire(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)

        ship_x = np.array([[0.0, 100.0, -100.0, -200.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        ship_vx = np.zeros((N, S), dtype=np.float32)
        ship_vy = np.zeros((N, S), dtype=np.float32)
        ship_theta = np.array([[0.0, math.pi, 0.0, math.pi]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        cooldown = np.zeros((N, S), dtype=np.float32)
        ammo = np.full((N, S), 6, dtype=np.int32)
        reload_timer = np.zeros((N, S), dtype=np.float32)

        result = fire_bullets(
            **proj,
            ship_x=ship_x, ship_y=ship_y,
            ship_vx=ship_vx, ship_vy=ship_vy,
            ship_theta=ship_theta, ship_alive=ship_alive,
            fire_cmd=fire_cmd, cooldown=cooldown,
            ammo=ammo, reload_timer=reload_timer,
            bullet_speed=500.0, bullet_range=800.0, fire_interval=0.2,
            magazine_size=6, reload_time=2.0,
        )
        proj_x, proj_y, proj_vx, proj_vy, proj_alive, proj_owner, proj_ttl, cd, am, rt = result

        assert proj_alive[0, 0]
        assert proj_owner[0, 0] == 0
        assert proj_vx[0, 0] > 0  # heading=0, bullet moves right
        assert cd[0, 0] == pytest.approx(0.2)
        assert am[0, 0] == 5  # one shot consumed

    def test_cooldown_prevents_firing(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)

        ship_x = np.zeros((N, S), dtype=np.float32)
        ship_y = np.zeros((N, S), dtype=np.float32)
        ship_vx = np.zeros((N, S), dtype=np.float32)
        ship_vy = np.zeros((N, S), dtype=np.float32)
        ship_theta = np.zeros((N, S), dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        cooldown = np.array([[0.1, 0.0, 0.0, 0.0]], dtype=np.float32)
        ammo = np.full((N, S), 6, dtype=np.int32)
        reload_timer = np.zeros((N, S), dtype=np.float32)

        result = fire_bullets(
            **proj,
            ship_x=ship_x, ship_y=ship_y,
            ship_vx=ship_vx, ship_vy=ship_vy,
            ship_theta=ship_theta, ship_alive=ship_alive,
            fire_cmd=fire_cmd, cooldown=cooldown,
            ammo=ammo, reload_timer=reload_timer,
            bullet_speed=500.0, bullet_range=800.0, fire_interval=0.2,
            magazine_size=6, reload_time=2.0,
        )
        _, _, _, _, proj_alive, _, _, _, _, _ = result
        assert not np.any(proj_alive)

    def test_dead_ship_cannot_fire(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)

        ship_alive = np.array([[False, True, True, True]], dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        ammo = np.full((N, S), 6, dtype=np.int32)
        reload_timer = np.zeros((N, S), dtype=np.float32)

        result = fire_bullets(
            **proj,
            ship_x=np.zeros((N, S), dtype=np.float32),
            ship_y=np.zeros((N, S), dtype=np.float32),
            ship_vx=np.zeros((N, S), dtype=np.float32),
            ship_vy=np.zeros((N, S), dtype=np.float32),
            ship_theta=np.zeros((N, S), dtype=np.float32),
            ship_alive=ship_alive,
            fire_cmd=fire_cmd,
            cooldown=np.zeros((N, S), dtype=np.float32),
            ammo=ammo, reload_timer=reload_timer,
            bullet_speed=500.0, bullet_range=800.0, fire_interval=0.2,
            magazine_size=6, reload_time=2.0,
        )
        _, _, _, _, proj_alive, _, _, _, _, _ = result
        assert not np.any(proj_alive)

    def test_empty_magazine_prevents_firing(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)

        ammo = np.zeros((N, S), dtype=np.int32)  # empty magazine
        reload_timer = np.zeros((N, S), dtype=np.float32)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)

        result = fire_bullets(
            **proj,
            ship_x=np.zeros((N, S), dtype=np.float32),
            ship_y=np.zeros((N, S), dtype=np.float32),
            ship_vx=np.zeros((N, S), dtype=np.float32),
            ship_vy=np.zeros((N, S), dtype=np.float32),
            ship_theta=np.zeros((N, S), dtype=np.float32),
            ship_alive=np.ones((N, S), dtype=np.bool_),
            fire_cmd=fire_cmd,
            cooldown=np.zeros((N, S), dtype=np.float32),
            ammo=ammo, reload_timer=reload_timer,
            bullet_speed=500.0, bullet_range=800.0, fire_interval=0.2,
            magazine_size=6, reload_time=2.0,
        )
        _, _, _, _, proj_alive, _, _, _, _, rt = result
        assert not np.any(proj_alive)
        # Should have started reload
        assert rt[0, 0] == pytest.approx(2.0)

    def test_reload_timer_prevents_firing(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)

        ammo = np.full((N, S), 6, dtype=np.int32)
        reload_timer = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)

        result = fire_bullets(
            **proj,
            ship_x=np.zeros((N, S), dtype=np.float32),
            ship_y=np.zeros((N, S), dtype=np.float32),
            ship_vx=np.zeros((N, S), dtype=np.float32),
            ship_vy=np.zeros((N, S), dtype=np.float32),
            ship_theta=np.zeros((N, S), dtype=np.float32),
            ship_alive=np.ones((N, S), dtype=np.bool_),
            fire_cmd=fire_cmd,
            cooldown=np.zeros((N, S), dtype=np.float32),
            ammo=ammo, reload_timer=reload_timer,
            bullet_speed=500.0, bullet_range=800.0, fire_interval=0.2,
            magazine_size=6, reload_time=2.0,
        )
        _, _, _, _, proj_alive, _, _, _, _, _ = result
        assert not np.any(proj_alive)


class TestAdvanceProjectiles:
    def test_projectile_moves(self):
        N, P = 1, 4
        proj_x = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.zeros((N, P), dtype=np.float32)
        proj_vx = np.array([[100.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_vy = np.zeros((N, P), dtype=np.float32)
        proj_alive = np.array([[True, False, False, False]], dtype=np.bool_)
        proj_ttl = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)

        dt = 1.0 / 30.0
        x, y, ttl, alive = advance_projectiles(
            proj_x, proj_y, proj_vx, proj_vy, proj_alive, proj_ttl, dt
        )

        assert x[0, 0] == pytest.approx(100.0 * dt, abs=1e-4)
        assert alive[0, 0]
        assert ttl[0, 0] < 1.0

    def test_projectile_expires(self):
        N, P = 1, 4
        proj_alive = np.array([[True, False, False, False]], dtype=np.bool_)
        proj_ttl = np.array([[0.01, 0.0, 0.0, 0.0]], dtype=np.float32)

        dt = 1.0 / 30.0
        _, _, ttl, alive = advance_projectiles(
            np.zeros((N, P), dtype=np.float32),
            np.zeros((N, P), dtype=np.float32),
            np.zeros((N, P), dtype=np.float32),
            np.zeros((N, P), dtype=np.float32),
            proj_alive, proj_ttl, dt,
        )
        assert not alive[0, 0]


class TestCheckHits:
    def test_bullet_hits_enemy_ship(self):
        N, S, P = 1, 4, 4

        # Projectile at (50, 0) owned by ship 0, ship 2 (enemy) at (50, 5) radius 18
        proj_x = np.array([[50.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_alive = np.array([[True, False, False, False]])
        proj_owner = np.array([[0, -1, -1, -1]], dtype=np.int32)
        proj_ttl = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)

        ship_x = np.array([[0.0, 10.0, 50.0, -50.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 0.0, 5.0, 0.0]], dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        damage, alive = check_hits(
            proj_x, proj_y, proj_alive, proj_owner, proj_ttl,
            ship_x, ship_y, ship_radius, ship_alive, ship_team,
            bullet_damage=15.0,
        )

        assert damage[0, 2] == pytest.approx(15.0)  # enemy hit
        assert damage[0, 0] == 0.0  # no self-hit
        assert damage[0, 1] == 0.0  # no friendly fire
        assert not alive[0, 0]  # projectile consumed

    def test_no_friendly_fire(self):
        """Bullets should not damage ships on the same team."""
        N, S, P = 1, 4, 4

        # Projectile at (10, 0) owned by ship 0, ship 1 (teammate) at (10, 2) radius 12
        proj_x = np.array([[10.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_alive = np.array([[True, False, False, False]])
        proj_owner = np.array([[0, -1, -1, -1]], dtype=np.int32)
        proj_ttl = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)

        ship_x = np.array([[0.0, 10.0, 100.0, 100.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 2.0, 0.0, 0.0]], dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        damage, alive = check_hits(
            proj_x, proj_y, proj_alive, proj_owner, proj_ttl,
            ship_x, ship_y, ship_radius, ship_alive, ship_team,
            bullet_damage=15.0,
        )

        assert damage[0, 1] == 0.0  # no friendly fire
        assert alive[0, 0]  # projectile not consumed by teammate

    def test_bullet_misses_distant_ship(self):
        N, S, P = 1, 4, 4

        proj_x = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_alive = np.array([[True, False, False, False]])
        proj_owner = np.array([[0, -1, -1, -1]], dtype=np.int32)
        proj_ttl = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)

        ship_x = np.array([[0.0, 10.0, 500.0, 500.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        damage, alive = check_hits(
            proj_x, proj_y, proj_alive, proj_owner, proj_ttl,
            ship_x, ship_y, ship_radius, ship_alive, ship_team,
            bullet_damage=15.0,
        )

        assert damage[0, 2] == 0.0
        assert alive[0, 0]  # projectile still alive
