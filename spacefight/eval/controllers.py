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
    OBS_LAYOUT,
    RustVecEnv,
)

THROTTLE_HOLD = 1
SLEW_HOLD = 1
# make_controller prefix of a policy flown with the obs order block zeroed.
BLANK_ORDERS_PREFIX = "blank:"
# ... with a go-to's deadline zeroed in the ``order_time`` block (SIM_VERSION 8), so
# every go-to reads as one without a deadline, and with the whole block zeroed.
NO_DEADLINE_PREFIX = "nodeadline:"
NO_ORDER_TIME_PREFIX = "notime:"
# What a policy is kept from seeing of the ``order_time`` block.
SEE_ORDER_TIME, HIDE_DEADLINE, HIDE_ORDER_TIME = "", "deadline", "order_time"
ORDER_TIME_HIDES = (SEE_ORDER_TIME, HIDE_DEADLINE, HIDE_ORDER_TIME)
# The block's floats that carry the deadline (has_deadline, time left, urgency); its
# fourth, closeness, any go-to has (SIM_SPEC §7.2).
_DEADLINE_FLOATS = 3


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

    A policy narrower than the sim's obs (fleet pilot v1, 385 floats, in a
    SIM_VERSION 5 sim of 403) flies on the prefix ``obs[..., :actor.obs_dim]``.

    Args:
        path: Checkpoint written by ``spike_policy.save_policy``.
        sample: Sample from the head distributions (the eval's primary numbers);
            ``False`` takes the argmax of every head.
        blank_orders: Zero the obs order block (SIM_VERSION 5) before the policy
            sees it: stage B's "same pilot with orders blanked" baseline.
        hide_order_time: ``HIDE_DEADLINE`` zeroes the deadline's three floats of the
            ``order_time`` block (SIM_VERSION 8), so a go-to with a deadline reads as
            one without: the same pilot blind to the deadline. ``HIDE_ORDER_TIME``
            zeroes the whole block, closeness too. A pilot of 583 inputs or fewer
            never sees the block, so neither changes how it flies.

    Raises:
        FileNotFoundError: ``path`` does not exist.
        ValueError: ``path`` is not a spike-policy checkpoint, or an unknown
            ``hide_order_time``.
    """

    def __init__(
        self,
        path: Path,
        sample: bool = True,
        blank_orders: bool = False,
        hide_order_time: str = SEE_ORDER_TIME,
    ) -> None:
        if not path.is_file():
            raise FileNotFoundError(f"policy checkpoint not found: {path}")
        if hide_order_time not in ORDER_TIME_HIDES:
            raise ValueError(
                f"hide_order_time must be one of {ORDER_TIME_HIDES}, "
                f"got {hide_order_time!r}"
            )
        from spacefight.rl import spike_policy

        self.path = path
        self.sample = sample
        self.blank_orders = blank_orders
        self.hide_order_time = hide_order_time
        self._spike = spike_policy
        actor, _critic, meta = spike_policy.load_policy(path)
        self.actor = actor.eval()
        self.meta = meta

    @property
    def label(self) -> str:
        mode = "" if self.sample else ":argmax"
        blank = ":blank_orders" if self.blank_orders else ""
        hidden = f":no_{self.hide_order_time}" if self.hide_order_time else ""
        return f"policy:{self.path.name}{mode}{blank}{hidden}"

    def reset(self, seed: int) -> None:
        """Seed torch's global RNG, which the actor samples from."""
        import torch

        torch.manual_seed(seed)

    def act(self, env: RustVecEnv, rows: NDArray[np.bool_]) -> NDArray[np.int8]:
        _check_rows(env, rows)
        if not rows.any():
            return np.zeros((0, ACTION_WIDTH), dtype=np.int8)
        obs = np.ascontiguousarray(env.obs[rows], dtype=np.float32)
        if self.blank_orders:
            offset, width = OBS_LAYOUT["order"]
            obs[:, offset : offset + width] = 0.0
        if self.hide_order_time:
            offset, width = OBS_LAYOUT["order_time"]
            if self.hide_order_time == HIDE_DEADLINE:
                width = _DEADLINE_FLOATS
            obs[:, offset : offset + width] = 0.0
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
    """Build a controller from a CLI spec: ``script``, ``random``, a checkpoint path,
    ``blank:<checkpoint>`` (the policy with the obs order block zeroed),
    ``nodeadline:<checkpoint>`` (blind to a go-to's deadline) or ``notime:<checkpoint>``
    (the whole ``order_time`` block zeroed).

    Raises:
        FileNotFoundError: ``spec`` is neither keyword nor an existing file.
    """
    if spec == "script":
        return Scripted()
    if spec == "random":
        return RandomController(seed)
    if spec.startswith(BLANK_ORDERS_PREFIX):
        path = Path(spec.removeprefix(BLANK_ORDERS_PREFIX))
        return Policy(path, sample=sample, blank_orders=True)
    for prefix, hide in (
        (NO_DEADLINE_PREFIX, HIDE_DEADLINE),
        (NO_ORDER_TIME_PREFIX, HIDE_ORDER_TIME),
    ):
        if spec.startswith(prefix):
            path = Path(spec.removeprefix(prefix))
            return Policy(path, sample=sample, hide_order_time=hide)
    return Policy(Path(spec), sample=sample)
