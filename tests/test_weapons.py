"""Tests for weapon firing, projectile movement, collision, and magazine/reload."""

import math

import numpy as np
import pytest

from spacefight.sim.weapons import (
    MAX_PROJECTILES,
    advance_projectiles,
    check_hits,
    fire_bullets,
    fire_lasers,
    fire_missiles,
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
        "proj_damage": np.zeros((n, p), dtype=np.float32),
        "proj_type": np.zeros((n, p), dtype=np.int32),
    }


def _per_ship_weapon_arrays(n: int, s: int, speed=500.0, range_=800.0,
                             damage=15.0, fire_rate=5.0, mag=6, reload_t=2.0,
                             shots=1, offset=0.0):
    """Create per-ship weapon config arrays for testing."""
    return {
        "weapon_speed": np.full((n, s), speed, dtype=np.float32),
        "weapon_range": np.full((n, s), range_, dtype=np.float32),
        "weapon_damage": np.full((n, s), damage, dtype=np.float32),
        "fire_interval": np.full((n, s), 1.0 / fire_rate, dtype=np.float32),
        "magazine_size": np.full((n, s), mag, dtype=np.int32),
        "reload_time": np.full((n, s), reload_t, dtype=np.float32),
        "shots_per_fire": np.full((n, s), shots, dtype=np.int32),
        "weapon_offset": np.full((n, s), offset, dtype=np.float32),
    }


class TestFireBullets:
    def test_bullet_spawns_on_fire(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)
        wpn = _per_ship_weapon_arrays(N, S)

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
            **wpn,
        )
        (proj_x, proj_y, proj_vx, proj_vy, proj_alive, proj_owner, proj_ttl,
         proj_damage, proj_type, cd, am, rt) = result

        assert proj_alive[0, 0]
        assert proj_owner[0, 0] == 0
        assert proj_vx[0, 0] > 0  # heading=0, bullet moves right
        assert cd[0, 0] == pytest.approx(0.2)
        assert am[0, 0] == 5  # one shot consumed
        assert proj_damage[0, 0] == pytest.approx(15.0)
        assert proj_type[0, 0] == 0  # bullet type

    def test_cooldown_prevents_firing(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)
        wpn = _per_ship_weapon_arrays(N, S)

        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        cooldown = np.array([[0.1, 0.0, 0.0, 0.0]], dtype=np.float32)

        result = fire_bullets(
            **proj,
            ship_x=np.zeros((N, S), dtype=np.float32),
            ship_y=np.zeros((N, S), dtype=np.float32),
            ship_vx=np.zeros((N, S), dtype=np.float32),
            ship_vy=np.zeros((N, S), dtype=np.float32),
            ship_theta=np.zeros((N, S), dtype=np.float32),
            ship_alive=np.ones((N, S), dtype=np.bool_),
            fire_cmd=fire_cmd, cooldown=cooldown,
            ammo=np.full((N, S), 6, dtype=np.int32),
            reload_timer=np.zeros((N, S), dtype=np.float32),
            **wpn,
        )
        proj_alive = result[4]
        assert not np.any(proj_alive)

    def test_dead_ship_cannot_fire(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)
        wpn = _per_ship_weapon_arrays(N, S)

        ship_alive = np.array([[False, True, True, True]], dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)

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
            ammo=np.full((N, S), 6, dtype=np.int32),
            reload_timer=np.zeros((N, S), dtype=np.float32),
            **wpn,
        )
        proj_alive = result[4]
        assert not np.any(proj_alive)

    def test_empty_magazine_prevents_firing(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)
        wpn = _per_ship_weapon_arrays(N, S)

        ammo = np.zeros((N, S), dtype=np.int32)
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
            ammo=ammo,
            reload_timer=np.zeros((N, S), dtype=np.float32),
            **wpn,
        )
        proj_alive = result[4]
        rt = result[11]
        assert not np.any(proj_alive)
        # Should have started reload
        assert rt[0, 0] == pytest.approx(2.0)

    def test_reload_timer_prevents_firing(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)
        wpn = _per_ship_weapon_arrays(N, S)

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
            ammo=np.full((N, S), 6, dtype=np.int32),
            reload_timer=np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32),
            **wpn,
        )
        proj_alive = result[4]
        assert not np.any(proj_alive)


class TestDoubleGauss:
    def test_double_gauss_spawns_two_projectiles(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)
        wpn = _per_ship_weapon_arrays(N, S, damage=12.0, fire_rate=4.0,
                                       mag=10, reload_t=2.5, shots=2, offset=10.0)

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
            ammo=np.full((N, S), 10, dtype=np.int32),
            reload_timer=np.zeros((N, S), dtype=np.float32),
            **wpn,
        )
        proj_x_out = result[0]
        proj_y_out = result[1]
        proj_vx_out = result[2]
        proj_vy_out = result[3]
        proj_alive = result[4]
        proj_damage = result[7]

        # Should have spawned exactly 2 projectiles
        n_alive = np.sum(proj_alive)
        assert n_alive == 2

        # Both should have damage 12
        alive_indices = np.where(proj_alive[0])[0]
        for idx in alive_indices:
            assert proj_damage[0, idx] == pytest.approx(12.0)

        # The two bullets should have the same velocity (parallel, not spread)
        vx0 = proj_vx_out[0, alive_indices[0]]
        vx1 = proj_vx_out[0, alive_indices[1]]
        vy0 = proj_vy_out[0, alive_indices[0]]
        vy1 = proj_vy_out[0, alive_indices[1]]
        assert vx0 == pytest.approx(vx1)
        assert vy0 == pytest.approx(vy1)

        # The two bullets should have different spawn positions (lateral offset)
        # Ship heading=0 → perpendicular is y-axis, so y positions differ
        y0 = proj_y_out[0, alive_indices[0]]
        y1 = proj_y_out[0, alive_indices[1]]
        assert y0 == pytest.approx(5.0)  # +offset/2
        assert y1 == pytest.approx(-5.0)  # -offset/2

        # Only 1 ammo consumed (not 2)
        ammo_out = result[10]
        assert ammo_out[0, 0] == 9


class TestAdvanceProjectiles:
    def test_projectile_moves(self):
        N, P = 1, 4
        proj_x = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.zeros((N, P), dtype=np.float32)
        proj_vx = np.array([[100.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_vy = np.zeros((N, P), dtype=np.float32)
        proj_alive = np.array([[True, False, False, False]], dtype=np.bool_)
        proj_ttl = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_type = np.zeros((N, P), dtype=np.int32)
        proj_target = np.full((N, P), -1, dtype=np.int32)

        S = 4
        ship_x = np.zeros((N, S), dtype=np.float32)
        ship_y = np.zeros((N, S), dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)

        dt = 1.0 / 30.0
        x, y, vx, vy, ttl, alive = advance_projectiles(
            proj_x, proj_y, proj_vx, proj_vy, proj_alive, proj_ttl,
            proj_type, proj_target,
            ship_x, ship_y, ship_alive,
            missile_turn_rate=0.0, dt=dt,
        )

        assert x[0, 0] == pytest.approx(100.0 * dt, abs=1e-4)
        assert alive[0, 0]
        assert ttl[0, 0] < 1.0

    def test_projectile_expires(self):
        N, P = 1, 4
        proj_alive = np.array([[True, False, False, False]], dtype=np.bool_)
        proj_ttl = np.array([[0.01, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_type = np.zeros((N, P), dtype=np.int32)
        proj_target = np.full((N, P), -1, dtype=np.int32)

        S = 4
        dt = 1.0 / 30.0
        _, _, _, _, ttl, alive = advance_projectiles(
            np.zeros((N, P), dtype=np.float32),
            np.zeros((N, P), dtype=np.float32),
            np.zeros((N, P), dtype=np.float32),
            np.zeros((N, P), dtype=np.float32),
            proj_alive, proj_ttl,
            proj_type, proj_target,
            np.zeros((N, S), dtype=np.float32),
            np.zeros((N, S), dtype=np.float32),
            np.ones((N, S), dtype=np.bool_),
            missile_turn_rate=0.0, dt=dt,
        )
        assert not alive[0, 0]


class TestCheckHits:
    def test_bullet_hits_enemy_ship(self):
        N, S, P = 1, 4, 4

        proj_x = np.array([[50.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_alive = np.array([[True, False, False, False]])
        proj_owner = np.array([[0, -1, -1, -1]], dtype=np.int32)
        proj_ttl = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_damage = np.array([[15.0, 0.0, 0.0, 0.0]], dtype=np.float32)

        ship_x = np.array([[0.0, 10.0, 50.0, -50.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 0.0, 5.0, 0.0]], dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        damage, alive = check_hits(
            proj_x, proj_y, proj_alive, proj_owner, proj_ttl,
            proj_damage,
            ship_x, ship_y, ship_radius, ship_alive, ship_team,
        )

        assert damage[0, 2] == pytest.approx(15.0)  # enemy hit
        assert damage[0, 0] == 0.0  # no self-hit
        assert damage[0, 1] == 0.0  # no friendly fire
        assert not alive[0, 0]  # projectile consumed

    def test_no_friendly_fire(self):
        N, S, P = 1, 4, 4

        proj_x = np.array([[10.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_alive = np.array([[True, False, False, False]])
        proj_owner = np.array([[0, -1, -1, -1]], dtype=np.int32)
        proj_ttl = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_damage = np.array([[15.0, 0.0, 0.0, 0.0]], dtype=np.float32)

        ship_x = np.array([[0.0, 10.0, 100.0, 100.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 2.0, 0.0, 0.0]], dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        damage, alive = check_hits(
            proj_x, proj_y, proj_alive, proj_owner, proj_ttl,
            proj_damage,
            ship_x, ship_y, ship_radius, ship_alive, ship_team,
        )

        assert damage[0, 1] == 0.0
        assert alive[0, 0]

    def test_bullet_misses_distant_ship(self):
        N, S, P = 1, 4, 4

        proj_x = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_alive = np.array([[True, False, False, False]])
        proj_owner = np.array([[0, -1, -1, -1]], dtype=np.int32)
        proj_ttl = np.array([[1.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_damage = np.array([[15.0, 0.0, 0.0, 0.0]], dtype=np.float32)

        ship_x = np.array([[0.0, 10.0, 500.0, 500.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        damage, alive = check_hits(
            proj_x, proj_y, proj_alive, proj_owner, proj_ttl,
            proj_damage,
            ship_x, ship_y, ship_radius, ship_alive, ship_team,
        )

        assert damage[0, 2] == 0.0
        assert alive[0, 0]

    def test_per_projectile_damage(self):
        """Different projectiles deal different damage amounts."""
        N, S, P = 1, 4, 4

        # Two projectiles: one 15 dmg, one 40 dmg, both hitting ship 2
        proj_x = np.array([[50.0, 50.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.array([[0.0, 3.0, 0.0, 0.0]], dtype=np.float32)
        proj_alive = np.array([[True, True, False, False]])
        proj_owner = np.array([[0, 1, -1, -1]], dtype=np.int32)
        proj_ttl = np.array([[1.0, 1.0, 0.0, 0.0]], dtype=np.float32)
        proj_damage = np.array([[15.0, 40.0, 0.0, 0.0]], dtype=np.float32)

        ship_x = np.array([[0.0, 10.0, 50.0, -50.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 0.0, 5.0, 0.0]], dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        damage, alive = check_hits(
            proj_x, proj_y, proj_alive, proj_owner, proj_ttl,
            proj_damage,
            ship_x, ship_y, ship_radius, ship_alive, ship_team,
        )

        assert damage[0, 2] == pytest.approx(55.0)  # 15 + 40


class TestFireLasers:
    def _laser_args(self, N, S):
        """Common laser weapon args."""
        return {
            "ammo": np.full((N, S), 5, dtype=np.int32),
            "reload_timer": np.zeros((N, S), dtype=np.float32),
            "weapon_damage": np.full((N, S), 9.0, dtype=np.float32),
            "weapon_range": np.full((N, S), 500.0, dtype=np.float32),
            "fire_interval": np.full((N, S), 0.125, dtype=np.float32),  # 1/8
            "magazine_size": np.full((N, S), 5, dtype=np.int32),
            "reload_time": np.full((N, S), 3.0, dtype=np.float32),
        }

    def test_laser_hits_enemy(self):
        N, S = 1, 4
        # Ship 0 at origin facing right, enemy ship 2 at (300, 0) radius 18
        ship_x = np.array([[0.0, 10.0, 300.0, -50.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        ship_theta = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        cooldown = np.zeros((N, S), dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        damage, cd_out, ammo_out, _, laser_hits = fire_lasers(
            ship_x, ship_y, ship_theta, ship_alive,
            fire_cmd, cooldown,
            **self._laser_args(N, S),
            ship_radius=ship_radius, ship_team=ship_team,
        )

        assert damage[0, 2] == pytest.approx(9.0)
        assert cd_out[0, 0] == pytest.approx(0.125)
        assert ammo_out[0, 0] == 4  # one shot consumed
        assert len(laser_hits) == 1

    def test_laser_misses_out_of_range(self):
        N, S = 1, 4
        # Enemy at 600, laser range 500
        ship_x = np.array([[0.0, 10.0, 600.0, -50.0]], dtype=np.float32)
        ship_y = np.zeros((N, S), dtype=np.float32)
        ship_theta = np.zeros((N, S), dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        cooldown = np.zeros((N, S), dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        damage, _, _, _, _ = fire_lasers(
            ship_x, ship_y, ship_theta, ship_alive,
            fire_cmd, cooldown,
            **self._laser_args(N, S),
            ship_radius=ship_radius, ship_team=ship_team,
        )

        assert damage[0, 2] == 0.0

    def test_laser_cooldown_prevents_fire(self):
        N, S = 1, 4
        ship_x = np.array([[0.0, 10.0, 300.0, -50.0]], dtype=np.float32)
        ship_y = np.zeros((N, S), dtype=np.float32)
        ship_theta = np.zeros((N, S), dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        cooldown = np.array([[0.1, 0.0, 0.0, 0.0]], dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        damage, _, _, _, laser_hits = fire_lasers(
            ship_x, ship_y, ship_theta, ship_alive,
            fire_cmd, cooldown,
            **self._laser_args(N, S),
            ship_radius=ship_radius, ship_team=ship_team,
        )

        assert damage[0, 2] == 0.0
        assert len(laser_hits) == 0

    def test_laser_empty_magazine_prevents_fire(self):
        N, S = 1, 4
        ship_x = np.array([[0.0, 10.0, 300.0, -50.0]], dtype=np.float32)
        ship_y = np.zeros((N, S), dtype=np.float32)
        ship_theta = np.zeros((N, S), dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        cooldown = np.zeros((N, S), dtype=np.float32)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        args = self._laser_args(N, S)
        args["ammo"] = np.zeros((N, S), dtype=np.int32)  # empty magazine

        damage, _, _, rt_out, laser_hits = fire_lasers(
            ship_x, ship_y, ship_theta, ship_alive,
            fire_cmd, cooldown,
            **args,
            ship_radius=ship_radius, ship_team=ship_team,
        )

        assert damage[0, 2] == 0.0
        assert len(laser_hits) == 0
        # Should have started reload
        assert rt_out[0, 0] == pytest.approx(3.0)

    def test_laser_burst_depletes_magazine(self):
        """Firing 5 times should empty the magazine and trigger reload."""
        N, S = 1, 4
        ship_x = np.array([[0.0, 10.0, 300.0, -50.0]], dtype=np.float32)
        ship_y = np.zeros((N, S), dtype=np.float32)
        ship_theta = np.zeros((N, S), dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        ship_radius = np.array([[12.0, 12.0, 18.0, 18.0]], dtype=np.float32)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        ammo = np.full((N, S), 5, dtype=np.int32)
        cooldown = np.zeros((N, S), dtype=np.float32)
        reload_timer = np.zeros((N, S), dtype=np.float32)
        total_damage = 0.0

        for i in range(5):
            damage, cooldown, ammo, reload_timer, _ = fire_lasers(
                ship_x, ship_y, ship_theta, ship_alive,
                fire_cmd, cooldown,
                ammo=ammo, reload_timer=reload_timer,
                weapon_damage=np.full((N, S), 9.0, dtype=np.float32),
                weapon_range=np.full((N, S), 500.0, dtype=np.float32),
                fire_interval=np.full((N, S), 0.125, dtype=np.float32),
                magazine_size=np.full((N, S), 5, dtype=np.int32),
                reload_time=np.full((N, S), 3.0, dtype=np.float32),
                ship_radius=ship_radius, ship_team=ship_team,
            )
            total_damage += damage[0, 2]
            # Reset cooldown between shots (simulating time passing)
            cooldown[:] = 0.0

        # 5 shots × 9 damage = 45 total
        assert total_damage == pytest.approx(45.0)
        assert ammo[0, 0] == 0
        # Reload should have started
        assert reload_timer[0, 0] == pytest.approx(3.0)


class TestFireMissiles:
    def test_missile_spawns_with_target(self):
        N, S = 1, 4
        proj = _empty_projectiles(N)

        ship_x = np.array([[0.0, 10.0, 300.0, -300.0]], dtype=np.float32)
        ship_y = np.zeros((N, S), dtype=np.float32)
        ship_vx = np.zeros((N, S), dtype=np.float32)
        ship_vy = np.zeros((N, S), dtype=np.float32)
        ship_theta = np.array([[0.0, 0.0, math.pi, math.pi]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        cooldown = np.zeros((N, S), dtype=np.float32)
        ammo = np.full((N, S), 1, dtype=np.int32)
        reload_timer = np.zeros((N, S), dtype=np.float32)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        weapon_speed = np.full((N, S), 250.0, dtype=np.float32)
        weapon_range = np.full((N, S), 1000.0, dtype=np.float32)
        weapon_damage = np.full((N, S), 40.0, dtype=np.float32)
        fire_interval = np.full((N, S), 1.0, dtype=np.float32)
        magazine_size = np.full((N, S), 1, dtype=np.int32)
        reload_time = np.full((N, S), 4.0, dtype=np.float32)

        result = fire_missiles(
            **proj,
            proj_target=np.full((N, MAX_PROJECTILES), -1, dtype=np.int32),
            ship_x=ship_x, ship_y=ship_y,
            ship_vx=ship_vx, ship_vy=ship_vy,
            ship_theta=ship_theta, ship_alive=ship_alive,
            fire_cmd=fire_cmd, cooldown=cooldown,
            ammo=ammo, reload_timer=reload_timer,
            weapon_speed=weapon_speed, weapon_range=weapon_range,
            weapon_damage=weapon_damage, fire_interval=fire_interval,
            magazine_size=magazine_size, reload_time=reload_time,
            ship_team=ship_team,
        )
        proj_alive = result[4]
        proj_damage = result[7]
        proj_type = result[8]
        proj_target = result[9]

        assert np.sum(proj_alive) == 1
        slot = np.where(proj_alive[0])[0][0]
        assert proj_damage[0, slot] == pytest.approx(40.0)
        assert proj_type[0, slot] == 1  # missile
        # Should target ship 2 (nearest enemy in forward arc)
        assert proj_target[0, slot] == 2

    def test_missile_no_target_behind(self):
        """Missile fires straight if all enemies are behind."""
        N, S = 1, 4
        proj = _empty_projectiles(N)

        # Ship 0 facing right, enemies behind at negative x
        ship_x = np.array([[0.0, 10.0, -300.0, -300.0]], dtype=np.float32)
        ship_y = np.zeros((N, S), dtype=np.float32)
        ship_theta = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)
        fire_cmd = np.array([[True, False, False, False]], dtype=np.bool_)
        ship_team = np.array([[0, 0, 1, 1]], dtype=np.int32)

        result = fire_missiles(
            **proj,
            proj_target=np.full((N, MAX_PROJECTILES), -1, dtype=np.int32),
            ship_x=ship_x, ship_y=ship_y,
            ship_vx=np.zeros((N, S), dtype=np.float32),
            ship_vy=np.zeros((N, S), dtype=np.float32),
            ship_theta=ship_theta, ship_alive=ship_alive,
            fire_cmd=fire_cmd,
            cooldown=np.zeros((N, S), dtype=np.float32),
            ammo=np.full((N, S), 1, dtype=np.int32),
            reload_timer=np.zeros((N, S), dtype=np.float32),
            weapon_speed=np.full((N, S), 250.0, dtype=np.float32),
            weapon_range=np.full((N, S), 1000.0, dtype=np.float32),
            weapon_damage=np.full((N, S), 40.0, dtype=np.float32),
            fire_interval=np.full((N, S), 1.0, dtype=np.float32),
            magazine_size=np.full((N, S), 1, dtype=np.int32),
            reload_time=np.full((N, S), 4.0, dtype=np.float32),
            ship_team=ship_team,
        )
        proj_target = result[9]
        proj_alive = result[4]
        slot = np.where(proj_alive[0])[0][0]
        assert proj_target[0, slot] == -1  # no target lock


class TestMissileGuidance:
    def test_missile_turns_toward_target(self):
        """A missile heading right should turn toward a target that's above it."""
        N, P = 1, 4
        S = 4

        # Missile at (0,0) heading right, target at (100, 100)
        proj_x = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_vx = np.array([[250.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_vy = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_alive = np.array([[True, False, False, False]], dtype=np.bool_)
        proj_ttl = np.array([[4.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_type = np.array([[1, 0, 0, 0]], dtype=np.int32)  # missile
        proj_target = np.array([[2, -1, -1, -1]], dtype=np.int32)  # target ship 2

        ship_x = np.array([[0.0, 10.0, 100.0, -50.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 0.0, 100.0, 0.0]], dtype=np.float32)
        ship_alive = np.ones((N, S), dtype=np.bool_)

        dt = 1.0 / 30.0
        missile_turn_rate = math.radians(120.0)

        _, _, vx, vy, _, _ = advance_projectiles(
            proj_x, proj_y, proj_vx, proj_vy, proj_alive, proj_ttl,
            proj_type, proj_target,
            ship_x, ship_y, ship_alive,
            missile_turn_rate=missile_turn_rate, dt=dt,
        )

        # Missile should have gained positive vy (turning up toward target)
        assert vy[0, 0] > 0.0
        # Speed should be preserved
        speed = math.sqrt(float(vx[0, 0])**2 + float(vy[0, 0])**2)
        assert speed == pytest.approx(250.0, abs=1.0)

    def test_missile_loses_guidance_on_target_death(self):
        """Missile should stop guiding when target dies."""
        N, P = 1, 4
        S = 4

        proj_x = np.array([[0.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_y = np.zeros((N, P), dtype=np.float32)
        proj_vx = np.array([[250.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_vy = np.zeros((N, P), dtype=np.float32)
        proj_alive = np.array([[True, False, False, False]], dtype=np.bool_)
        proj_ttl = np.array([[4.0, 0.0, 0.0, 0.0]], dtype=np.float32)
        proj_type = np.array([[1, 0, 0, 0]], dtype=np.int32)
        proj_target = np.array([[2, -1, -1, -1]], dtype=np.int32)

        ship_x = np.array([[0.0, 10.0, 100.0, -50.0]], dtype=np.float32)
        ship_y = np.array([[0.0, 0.0, 100.0, 0.0]], dtype=np.float32)
        ship_alive = np.array([[True, True, False, True]], dtype=np.bool_)  # target dead

        dt = 1.0 / 30.0
        _, _, vx, vy, _, _ = advance_projectiles(
            proj_x, proj_y, proj_vx, proj_vy, proj_alive, proj_ttl,
            proj_type, proj_target,
            ship_x, ship_y, ship_alive,
            missile_turn_rate=math.radians(120.0), dt=dt,
        )

        # Should not have turned — vy stays 0
        assert vy[0, 0] == pytest.approx(0.0)
        # Target should be cleared
        assert proj_target[0, 0] == -1
