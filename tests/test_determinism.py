"""Tests for simulation determinism: same seed produces identical results."""

import numpy as np

from spacefight.sim.core import reset, step

N_SHIPS = 4


def _run_episode(seed: int, n_envs: int = 4, n_steps: int = 100) -> dict:
    """Run a short episode and return final state snapshots."""
    rng = np.random.default_rng(seed + 1000)
    state = reset(n_envs=n_envs, seed=seed, n_ships=N_SHIPS)

    for _ in range(n_steps):
        actions = rng.integers(0, 2, size=(n_envs, N_SHIPS, 5)).astype(np.int32)
        actions[:, :, 0] = rng.integers(-1, 2, size=(n_envs, N_SHIPS)).astype(np.int32)
        state, _, _ = step(state, actions)

    return {
        "x": state.x.copy(),
        "y": state.y.copy(),
        "vx": state.vx.copy(),
        "vy": state.vy.copy(),
        "theta": state.theta.copy(),
        "hull": state.hull.copy(),
        "alive": state.alive.copy(),
        "proj_alive": state.proj_alive.copy(),
        "ammo": state.ammo.copy(),
        "reload_timer": state.reload_timer.copy(),
    }


class TestDeterminism:
    def test_same_seed_same_result(self):
        result_a = _run_episode(seed=42)
        result_b = _run_episode(seed=42)

        for key in result_a:
            np.testing.assert_array_equal(
                result_a[key], result_b[key],
                err_msg=f"Mismatch in {key}",
            )

    def test_different_seed_different_result(self):
        result_a = _run_episode(seed=42)
        result_b = _run_episode(seed=99)

        # At least positions should differ
        assert not np.array_equal(result_a["x"], result_b["x"])
