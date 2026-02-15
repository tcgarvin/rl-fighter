"""Tests for physics: thrust, turn, speed cap, integration."""

import math

import numpy as np
import pytest

from spacefight.sim.core import DT, DRAG_COEFF, SOFT_CAP_DRAG, reset, step

N_SHIPS = 4


def _no_action(n_envs: int, n_ships: int = N_SHIPS) -> np.ndarray:
    return np.zeros((n_envs, n_ships, 5), dtype=np.int32)


def _make_actions(n_envs: int, n_ships: int = N_SHIPS, **overrides) -> np.ndarray:
    """Helper to build action arrays with specific values."""
    actions = _no_action(n_envs, n_ships)
    for key, val in overrides.items():
        idx = {"turn": 0, "thrust": 1, "brake": 2, "fire": 3, "reload": 4}[key]
        actions[:, :, idx] = val
    return actions


class TestThrust:
    def test_thrust_accelerates_along_heading(self):
        state = reset(n_envs=1, seed=0)
        # Set heading to 0 (rightward)
        state.theta[:] = 0.0
        state.x[:] = 0.0
        state.y[:] = 0.0
        state.vx[:] = 0.0
        state.vy[:] = 0.0

        actions = _make_actions(1, thrust=1)
        # Only thrust for ship 0
        for s in range(1, N_SHIPS):
            actions[:, s, 1] = 0

        state, _, _ = step(state, actions)

        # Ship 0 should have positive vx (heading=0 means rightward)
        assert state.vx[0, 0] > 0.0
        # vy should be near zero (heading=0)
        assert abs(state.vy[0, 0]) < 1e-4
        # Ship 1 should not have moved
        assert state.vx[0, 1] == 0.0

    def test_no_thrust_no_acceleration(self):
        state = reset(n_envs=1, seed=0)
        state.vx[:] = 0.0
        state.vy[:] = 0.0

        actions = _no_action(1)
        state, _, _ = step(state, actions)

        assert np.allclose(state.vx, 0.0, atol=1e-6)
        assert np.allclose(state.vy, 0.0, atol=1e-6)


class TestTurn:
    def test_turn_changes_heading(self):
        state = reset(n_envs=1, seed=0)
        initial_theta = state.theta.copy()

        actions = _make_actions(1, turn=1)
        # Only ship 0 turns
        for s in range(1, N_SHIPS):
            actions[:, s, 0] = 0
        state, _, _ = step(state, actions)

        # Heading should have increased for ship 0
        delta = state.theta[0, 0] - initial_theta[0, 0]
        assert delta > 0.0
        expected = state.turn_rate[0, 0] * DT
        assert abs(delta - expected) < 1e-5

    def test_turn_negative(self):
        state = reset(n_envs=1, seed=0)
        initial_theta = state.theta.copy()

        actions = _make_actions(1, turn=-1)
        for s in range(1, N_SHIPS):
            actions[:, s, 0] = 0
        state, _, _ = step(state, actions)

        delta = state.theta[0, 0] - initial_theta[0, 0]
        assert delta < 0.0


class TestBrake:
    def test_brake_decelerates(self):
        state = reset(n_envs=1, seed=0)
        state.vx[:, 0] = 100.0
        state.vy[:, 0] = 0.0

        actions = _make_actions(1, brake=1)
        for s in range(1, N_SHIPS):
            actions[:, s, :] = 0
        state, _, _ = step(state, actions)

        # Speed should decrease
        assert state.vx[0, 0] < 100.0


class TestSpeedCap:
    def test_soft_speed_cap_applies_drag(self):
        state = reset(n_envs=1, seed=0)
        # Set velocity well above max speed
        state.vx[:, 0] = state.max_speed[0, 0] * 2.0
        state.vy[:, 0] = 0.0

        actions = _no_action(1)
        state, _, _ = step(state, actions)

        # Speed should have decreased toward max
        speed = np.sqrt(state.vx[0, 0] ** 2 + state.vy[0, 0] ** 2)
        assert speed < state.max_speed[0, 0] * 2.0

    def test_below_max_speed_no_cap_drag(self):
        state = reset(n_envs=1, seed=0)
        state.vx[:, 0] = state.max_speed[0, 0] * 0.5
        state.vy[:, 0] = 0.0

        initial_vx = state.vx[0, 0]
        actions = _no_action(1)
        state, _, _ = step(state, actions)

        # Without thrust or brake, velocity should not change below cap
        assert abs(state.vx[0, 0] - initial_vx) < 1e-4


class TestIntegration:
    def test_position_updates_with_velocity(self):
        state = reset(n_envs=1, seed=0)
        state.x[:, 0] = 0.0
        state.y[:, 0] = 0.0
        state.vx[:, 0] = 60.0
        state.vy[:, 0] = 30.0

        actions = _no_action(1)
        state, _, _ = step(state, actions)

        # Position should advance by v*dt
        assert abs(state.x[0, 0] - 60.0 * DT) < 1e-3
        assert abs(state.y[0, 0] - 30.0 * DT) < 1e-3
