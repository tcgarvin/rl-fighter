"""Tests for egocentric observation builder (2v2, 53 features)."""

import numpy as np

from spacefight.rl.obs import OBS_DIM, build_egocentric_obs
from spacefight.sim.core import SimState, reset


class TestEgocentricObs:
    def test_shape_and_dtype(self):
        state = reset(n_envs=4, seed=0, n_ships=4)
        obs = build_egocentric_obs(state)
        assert obs.shape == (4, 4, OBS_DIM)
        assert obs.dtype == np.float32

    def test_hull_fraction_at_reset(self):
        """At reset, hull fraction should be 1.0 for all ships."""
        state = reset(n_envs=8, seed=42, n_ships=4)
        obs = build_egocentric_obs(state)
        # obs[:, :, 1] is own hull fraction
        np.testing.assert_allclose(obs[:, :, 1], 1.0, atol=1e-6)

    def test_ally_alive_at_reset(self):
        """At reset, ally alive flag should be 1.0."""
        state = reset(n_envs=4, seed=0, n_ships=4)
        obs = build_egocentric_obs(state)
        # obs[:, :, 23] is ally alive flag
        np.testing.assert_array_equal(obs[:, :, 23], 1.0)

    def test_enemies_alive_at_reset(self):
        """At reset, both enemy alive flags should be 1.0."""
        state = reset(n_envs=4, seed=0, n_ships=4)
        obs = build_egocentric_obs(state)
        # obs[:, :, 30] is enemy 0 alive, obs[:, :, 43] is enemy 1 alive
        np.testing.assert_array_equal(obs[:, :, 30], 1.0)
        np.testing.assert_array_equal(obs[:, :, 43], 1.0)

    def test_dead_ally_reflected(self):
        """When ally dies, ally alive flag should be 0."""
        state = reset(n_envs=2, seed=0, n_ships=4)
        state.alive[0, 1] = False  # kill ship 1 (ally of ship 0)
        obs = build_egocentric_obs(state)
        # Ship 0 sees ally (ship 1) as dead
        assert obs[0, 0, 23] == 0.0

    def test_ammo_fraction_at_reset(self):
        """At reset, ammo fraction should be 1.0."""
        state = reset(n_envs=4, seed=0, n_ships=4)
        obs = build_egocentric_obs(state)
        # obs[:, :, 6] is ammo fraction
        np.testing.assert_allclose(obs[:, :, 6], 1.0, atol=1e-6)

    def test_reload_fraction_at_reset(self):
        """At reset, reload fraction should be 0.0."""
        state = reset(n_envs=4, seed=0, n_ships=4)
        obs = build_egocentric_obs(state)
        # obs[:, :, 7] is reload fraction
        np.testing.assert_allclose(obs[:, :, 7], 0.0, atol=1e-6)

    def test_ship_properties_present(self):
        """Hull stats should be non-zero at reset."""
        state = reset(n_envs=4, seed=0, n_ships=4)
        obs = build_egocentric_obs(state)
        # obs[:, :, 8] is max_hull / 250
        assert np.all(obs[:, :, 8] > 0)
        # obs[:, :, 9] is max_speed / 300
        assert np.all(obs[:, :, 9] > 0)

    def test_cooldown_zero_at_reset(self):
        """Cooldown should be 0 at reset."""
        state = reset(n_envs=4, seed=0, n_ships=4)
        obs = build_egocentric_obs(state)
        # obs[:, :, 2] is cooldown fraction
        np.testing.assert_allclose(obs[:, :, 2], 0.0, atol=1e-6)

    def test_no_nans(self):
        """Observations should never contain NaN."""
        state = reset(n_envs=16, seed=0, n_ships=4)
        obs = build_egocentric_obs(state)
        assert not np.any(np.isnan(obs))

    def test_zone_margin_present(self):
        """Zone margin should be present and finite."""
        state = reset(n_envs=4, seed=0, n_ships=4)
        obs = build_egocentric_obs(state)
        # obs[:, :, 52] is zone margin
        assert np.all(np.isfinite(obs[:, :, 52]))

    def test_enemy_distance_sorting(self):
        """Nearest enemy should be in slots 24-36, farthest in 37-49."""
        state = reset(n_envs=1, seed=0, n_ships=4)
        # Place ship 0 at origin
        state.x[0, 0] = 0.0
        state.y[0, 0] = 0.0
        state.theta[0, 0] = 0.0
        state.vx[0, :] = 0.0
        state.vy[0, :] = 0.0
        # Ship 1 (ally) nearby
        state.x[0, 1] = 10.0
        state.y[0, 1] = 0.0
        # Ship 2 (enemy) far
        state.x[0, 2] = 200.0
        state.y[0, 2] = 0.0
        # Ship 3 (enemy) close
        state.x[0, 3] = 50.0
        state.y[0, 3] = 0.0

        obs = build_egocentric_obs(state)
        # For ship 0: enemy nearest (ship 3 at 50) should be in 24-36
        # enemy far (ship 2 at 200) should be in 37-49
        nearest_dist = obs[0, 0, 28]   # distance / 1000 for nearest
        farthest_dist = obs[0, 0, 41]  # distance / 1000 for farthest
        assert nearest_dist < farthest_dist

    def test_weapon_descriptors(self):
        """Weapon descriptors should reflect the hull's weapon type."""
        # Default hull_names=None → all fighters → gauss_gun (bullet type)
        state = reset(n_envs=2, seed=0, n_ships=4)
        obs = build_egocentric_obs(state)
        # Fighter uses gauss_gun: is_projectile=1, is_hitscan=0, is_guided=0
        np.testing.assert_array_equal(obs[:, :, 12], 1.0)  # is_projectile
        np.testing.assert_array_equal(obs[:, :, 13], 0.0)  # is_hitscan
        np.testing.assert_array_equal(obs[:, :, 14], 0.0)  # is_guided
        # Range = 800 / 1500
        np.testing.assert_allclose(obs[:, :, 15], 800.0 / 1500.0, atol=1e-6)
        # Speed = 500 / 500
        np.testing.assert_allclose(obs[:, :, 16], 500.0 / 500.0, atol=1e-6)

    def test_bearing_dead_ahead(self):
        """When enemy is dead ahead, bearing_cos ≈ 1, bearing_sin ≈ 0."""
        state = reset(n_envs=1, seed=0, n_ships=4)
        state.x[0, 0] = 0.0
        state.y[0, 0] = 0.0
        state.theta[0, 0] = 0.0  # facing +x
        state.vx[0, :] = 0.0
        state.vy[0, :] = 0.0
        # Place nearest enemy (ship 2) dead ahead
        state.x[0, 2] = 100.0
        state.y[0, 2] = 0.0
        # Place other enemy (ship 3) far away
        state.x[0, 3] = 500.0
        state.y[0, 3] = 0.0

        obs = build_egocentric_obs(state)
        # Nearest enemy bearing for ship 0
        bearing_cos = obs[0, 0, 31]
        bearing_sin = obs[0, 0, 32]
        np.testing.assert_allclose(bearing_cos, 1.0, atol=1e-5)
        np.testing.assert_allclose(bearing_sin, 0.0, atol=1e-5)

    def test_range_margin_positive_in_range(self):
        """Range margin should be positive when enemy is within weapon range."""
        state = reset(n_envs=1, seed=0, n_ships=4)
        state.x[0, 0] = 0.0
        state.y[0, 0] = 0.0
        state.vx[0, :] = 0.0
        state.vy[0, :] = 0.0
        # Place nearest enemy within gauss range (800)
        state.x[0, 2] = 400.0
        state.y[0, 2] = 0.0
        state.x[0, 3] = 600.0
        state.y[0, 3] = 0.0

        obs = build_egocentric_obs(state)
        # Range margin for nearest enemy (ship 2 at 400, weapon range 800)
        range_margin = obs[0, 0, 36]
        assert range_margin > 0.0
        np.testing.assert_allclose(range_margin, (800.0 - 400.0) / 800.0, atol=1e-4)

    def test_range_margin_negative_out_of_range(self):
        """Range margin should be negative when enemy is beyond weapon range."""
        state = reset(n_envs=1, seed=0, n_ships=4)
        state.x[0, 0] = 0.0
        state.y[0, 0] = 0.0
        state.vx[0, :] = 0.0
        state.vy[0, :] = 0.0
        # Place nearest enemy beyond gauss range (800)
        state.x[0, 2] = 1000.0
        state.y[0, 2] = 0.0
        state.x[0, 3] = 1200.0
        state.y[0, 3] = 0.0

        obs = build_egocentric_obs(state)
        range_margin = obs[0, 0, 36]
        assert range_margin < 0.0

    def test_closing_speed_positive_when_approaching(self):
        """Radial closing speed should be positive when enemy approaches."""
        state = reset(n_envs=1, seed=0, n_ships=4)
        state.x[0, 0] = 0.0
        state.y[0, 0] = 0.0
        state.theta[0, 0] = 0.0
        state.vx[0, 0] = 0.0
        state.vy[0, 0] = 0.0
        # Enemy approaching from ahead
        state.x[0, 2] = 200.0
        state.y[0, 2] = 0.0
        state.vx[0, 2] = -100.0  # moving toward ship 0
        state.vy[0, 2] = 0.0
        state.x[0, 3] = 500.0
        state.y[0, 3] = 0.0
        state.vx[0, 3] = 0.0
        state.vy[0, 3] = 0.0

        obs = build_egocentric_obs(state)
        radial_speed = obs[0, 0, 33]
        assert radial_speed > 0.0  # positive = closing
