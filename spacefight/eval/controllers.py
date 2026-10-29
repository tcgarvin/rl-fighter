"""Controllers the eval harness pits against each other (spike plan §6.1).

A controller chooses the action rows for a subset of ship slots of a ``RustVecEnv``
from the env's current observations:

    rows = np.zeros((env.n_envs, env.n_ships), dtype=bool)   # which slots to drive
    rows[:, 0] = True
    controller.reset(seed=0)                                 # once per evaluation
    actions = controller.act(env, rows)                      # [rows.sum(), 21] int8
    env.actions[rows] = actions

``act`` returns one row per ``True`` entry of ``rows``, in the row-major order of
``env.obs[rows]``. Controllers may overwrite ``env.actions`` (the scripted one
does), so callers pass the assembled actions to ``env.step(actions)`` explicitly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

import numpy as np
from numpy.typing import NDArray

from spacefight.env.rust_env import (
    ACTION_HIGHS,
    ACTION_LAYOUT,
    ACTION_WIDTH,
    RustVecEnv,
)

THROTTLE_HOLD = 1
SLEW_HOLD = 1


def idle_actions(n_rows: int) -> NDArray[np.int8]:
    """``[n_rows, ACTION_WIDTH]`` rows of ``ShipAction::IDLE`` (hold, no fire, power 0)."""
    rows = np.zeros((n_rows, ACTION_WIDTH), dtype=np.int8)
    for head, hold in (("throttle", THROTTLE_HOLD), ("slew", SLEW_HOLD)):
        offset, width = ACTION_LAYOUT[head]
        rows[:, offset : offset + width] = hold
    return rows


class Controller(Protocol):
    """Chooses actions for selected ship slots of a ``RustVecEnv``."""

    @property
    def label(self) -> str:
        """Short name for tables and JSON (e.g. "script", "policy:bc.pt")."""
        ...

    def reset(self, seed: int) -> None:
        """Reseed any randomness; called once at the start of every evaluation."""
        ...

    def act(self, env: RustVecEnv, rows: NDArray[np.bool_]) -> NDArray[np.int8]:
        """Actions for the slots where ``rows`` (``[N, S]`` bool) is true.

        Returns:
            ``[rows.sum(), ACTION_WIDTH]`` int8, ordered like ``env.obs[rows]``.
        """
        ...


def _check_rows(env: RustVecEnv, rows: NDArray[np.bool_]) -> None:
    expected = (env.n_envs, env.n_ships)
    if rows.shape != expected or rows.dtype != np.bool_:
        raise ValueError(f"rows must be bool {expected}, got {rows.dtype} {rows.shape}")


class Scripted:
    """The Rust scripted controller (``env.scripted_actions()``, SIM_SPEC §11)."""

    @property
    def label(self) -> str:
        return "script"

    def reset(self, seed: int) -> None:
        """Nothing to reseed: the script is a deterministic function of the obs."""

    def act(self, env: RustVecEnv, rows: NDArray[np.bool_]) -> NDArray[np.int8]:
        _check_rows(env, rows)
        return np.array(env.scripted_actions()[rows], dtype=np.int8)


class RandomController:
    """Uniform random value on every action head (a sanity floor for the eval).

    Args:
        seed: Base seed; ``reset(seed)`` reseeds from ``(self.seed, seed)``.
    """

    def __init__(self, seed: int = 0) -> None:
        self.seed = seed
        self._rng = np.random.default_rng([seed, 0])

    @property
    def label(self) -> str:
        return "random"

    def reset(self, seed: int) -> None:
        self._rng = np.random.default_rng([self.seed, seed])

    def act(self, env: RustVecEnv, rows: NDArray[np.bool_]) -> NDArray[np.int8]:
        _check_rows(env, rows)
        n_rows = int(rows.sum())
        highs = ACTION_HIGHS.astype(np.int64) + 1
        return self._rng.integers(0, highs, size=(n_rows, ACTION_WIDTH)).astype(np.int8)


class Policy:
    """A trained spike actor (``spacefight.rl.spike_policy``, plan WP-B).

    torch and the policy module are imported on construction, not with this module,
    so the scripted and random controllers work without loading torch.

    Args:
        path: Checkpoint written by ``spike_policy.save_policy``.
        sample: Sample from the head distributions (the eval's primary numbers);
            ``False`` takes the argmax of every head.

    Raises:
        FileNotFoundError: ``path`` does not exist.
        ValueError: ``path`` is not a spike-policy checkpoint.
    """

    def __init__(self, path: Path, sample: bool = True) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"policy checkpoint not found: {path}")
        from spacefight.rl import spike_policy

        self.path = path
        self.sample = sample
        self._spike = spike_policy
        actor, _critic, meta = spike_policy.load_policy(path)
        self.actor = actor.eval()
        self.meta = meta

    @property
    def label(self) -> str:
        mode = "" if self.sample else ":argmax"
        return f"policy:{self.path.name}{mode}"

    def reset(self, seed: int) -> None:
        """Seed torch's global RNG, which the actor samples from."""
        import torch

        torch.manual_seed(seed)

    def act(self, env: RustVecEnv, rows: NDArray[np.bool_]) -> NDArray[np.int8]:
        _check_rows(env, rows)
        if not rows.any():
            return np.zeros((0, ACTION_WIDTH), dtype=np.int8)
        obs = np.ascontiguousarray(env.obs[rows], dtype=np.float32)
        masks = self._spike.HeadMasks.from_numpy(
            env.thruster_mask[rows], env.turret_mask[rows], env.fixed_turret[rows]
        )
        actions = self._spike.act_numpy(
            self.actor, obs, masks, deterministic=not self.sample
        )
        out = np.asarray(actions, dtype=np.int8)
        if out.shape != (obs.shape[0], ACTION_WIDTH):
            raise ValueError(
                f"act_numpy returned {out.shape}, expected "
                f"({obs.shape[0]}, {ACTION_WIDTH})"
            )
        return out


class PerHull:
    """Routes each ship to a controller by its hull (e.g. a duel champion flying
    the fighters of a team whose other hulls fly the script).

    Args:
        default: Controller for hulls without an override.
        overrides: Hull id -> controller.
        names: Hull id -> name, for the label.
    """

    def __init__(
        self,
        default: Controller,
        overrides: dict[int, Controller],
        names: dict[int, str],
    ) -> None:
        self.default = default
        self.overrides = dict(overrides)
        self.names = dict(names)

    @property
    def label(self) -> str:
        parts = [
            f"{self.names[h]}={c.label}" for h, c in sorted(self.overrides.items())
        ]
        return f"{self.default.label}+" + ",".join(parts)

    def reset(self, seed: int) -> None:
        self.default.reset(seed)
        for k, ctrl in enumerate(self.overrides.values()):
            ctrl.reset(seed + 1000 * (k + 1))

    def act(self, env: RustVecEnv, rows: NDArray[np.bool_]) -> NDArray[np.int8]:
        _check_rows(env, rows)
        out = np.zeros((int(rows.sum()), ACTION_WIDTH), dtype=np.int8)
        hull = env.hull_id[rows]
        routed = np.zeros(hull.shape, dtype=np.bool_)
        for hid, ctrl in self.overrides.items():
            sel = rows & (env.hull_id == hid)
            if sel.any():
                out[hull == hid] = ctrl.act(env, sel)
            routed |= hull == hid
        rest = rows & ~np.isin(env.hull_id, list(self.overrides))
        if rest.any():
            out[~routed] = self.default.act(env, rest)
        return out


def make_controller(spec: str, sample: bool = True, seed: int = 0) -> Controller:
    """Build a controller from a CLI spec: ``script``, ``random`` or a checkpoint path.

    Raises:
        FileNotFoundError: ``spec`` is neither keyword nor an existing file.
    """
    if spec == "script":
        return Scripted()
    if spec == "random":
        return RandomController(seed)
    return Policy(Path(spec), sample=sample)
