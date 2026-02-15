"""Lightweight vectorized environment wrapper around the sim."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from spacefight.rl.obs import OBS_DIM, build_egocentric_obs
from spacefight.sim.core import TEAM_SIZE, SimState, load_hulls, reset, step


_TEAMMATE_MAP_4 = np.array([1, 0, 3, 2], dtype=np.int32)


def build_critic_obs(obs: NDArray[np.float32], n_ships: int) -> NDArray[np.float32]:
    """Build centralized critic observations by concatenating teammate obs.

    For each agent, the critic sees [own_obs, teammate_obs].

    Args:
        obs: Per-agent observations, shape [N, S, obs_dim].
        n_ships: Number of ships per match.

    Returns:
        Critic observations, shape [N, S, obs_dim * 2].
    """
    N, S, D = obs.shape
    teammate_idx = _TEAMMATE_MAP_4[:S]
    return np.concatenate([obs, obs[:, teammate_idx]], axis=2)


class VecEnv:
    """Batched environment for N parallel 2v2 matches.

    Wraps sim.core.reset/step with a standard RL interface:
    reset() -> obs, step(actions) -> (obs, rewards, dones, infos).
    """

    def __init__(
        self,
        n_envs: int = 256,
        hull_names: list[str] | None = None,
        seed: int | None = None,
        max_steps: int = 2700,  # 90 seconds at 30 Hz
        n_ships: int = 4,
        randomize_hulls: bool = False,
    ) -> None:
        self.n_envs = n_envs
        self.hull_names = hull_names
        self.seed = seed
        self.max_steps = max_steps
        self.n_ships = n_ships
        self.randomize_hulls = randomize_hulls
        self._state: SimState | None = None
        self._rng = np.random.default_rng(seed)
        self._hull_types: list[str] = list(load_hulls().keys())

    @property
    def state(self) -> SimState:
        if self._state is None:
            raise RuntimeError("Environment not reset. Call reset() first.")
        return self._state

    def _pick_hull_names(self) -> list[str] | None:
        """Select hull names for a reset, optionally randomizing."""
        if self.hull_names is not None:
            return self.hull_names
        if self.randomize_hulls:
            return [
                self._rng.choice(self._hull_types)
                for _ in range(self.n_ships)
            ]
        return None  # defaults to all fighters

    def reset(self) -> NDArray[np.float32]:
        """Reset all environments and return initial observations."""
        episode_seed = int(self._rng.integers(0, 2**31))
        hull_names = self._pick_hull_names()
        self._state = reset(
            n_envs=self.n_envs,
            hull_names=hull_names,
            seed=episode_seed,
            n_ships=self.n_ships,
        )
        return self._observe()

    def step(
        self, actions: NDArray[np.int32]
    ) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.bool_], dict]:
        """Step all environments.

        Args:
            actions: [N, S, 4] int32 array (turn, thrust, brake, fire).

        Returns:
            (obs, rewards, dones, infos) tuple.
        """
        state = self.state
        self._state, rewards, dones = step(state, actions)

        # Time limit
        time_done = self._state.tick >= self.max_steps
        dones = dones | time_done
        self._state.done = dones

        infos = {
            "tick": self._state.tick.copy(),
            "hull": self._state.hull.copy(),
            "alive": self._state.alive.copy(),
        }

        # Snapshot dones before auto-reset mutates state.done
        dones_out = dones.copy()

        # Auto-reset done environments
        done_indices = np.where(dones)[0]
        if len(done_indices) > 0:
            self._auto_reset(done_indices)

        obs = self._observe()
        return obs, rewards, dones_out, infos

    def _auto_reset(self, indices: NDArray[np.intp]) -> None:
        """Reset specific environments that are done."""
        n_reset = len(indices)
        hull_names = self._pick_hull_names()
        fresh = reset(
            n_envs=n_reset,
            hull_names=hull_names,
            seed=int(self._rng.integers(0, 2**31)),
            n_ships=self.state.n_ships,
        )
        state = self._state
        assert state is not None

        # Copy fresh state into the done slots
        for attr in [
            "x", "y", "vx", "vy", "theta", "hull", "alive",
            "max_hull", "radius", "max_speed", "turn_rate", "thrust_accel",
            "team", "cooldown", "ammo", "reload_timer",
            "proj_x", "proj_y", "proj_vx", "proj_vy",
            "proj_alive", "proj_owner", "proj_ttl",
            "zone_cx", "zone_cy", "zone_r", "t_since_damage",
        ]:
            getattr(state, attr)[indices] = getattr(fresh, attr)

        state.done[indices] = False
        state.tick[indices] = 0

    def _observe(self) -> NDArray[np.float32]:
        """Build egocentric observation array.

        Each ship sees the world from its own heading frame.
        Shape: [N, S, OBS_DIM].
        """
        return build_egocentric_obs(self.state)
