"""Drive the learned commanders of a batched env for one tick (docs/COMMANDER.md).

A ``learned`` team decides on its own slow tick (every ``LEARNED_COMMAND_TICKS``). Before
each step, ``decide_learned`` asks the env which envs are due for each team, runs every
learned network on the due envs it commands (one batch per network per team, no
gradient, CPU) and submits the decisions. The commander eval
(``spacefight.commander.eval.play_matches``) and the pilot trainer
(``spacefight.rl.spike_ppo``) both use it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final

import numpy as np
from numpy.typing import NDArray

from spacefight.commander.io import CommanderInputs
from spacefight.commander.policy import CommanderActor, sample_actions
from spacefight.commander.train import FEATURE_KEYS
from spacefight.env.rust_env import RustVecEnv

# ``side_commander`` entry of a team that no commander in the list runs (a drill's
# external commander, a hidden-orders match's script).
NOT_IN_STABLE: Final = -1


def decide_learned(
    env: RustVecEnv,
    side_commander: NDArray[np.int64],
    learned: Sequence[tuple[int, CommanderActor]],
    running: NDArray[np.bool_],
) -> int:
    """Choose and submit every due decision of a learned team, for both teams.

    Each team's features are read once, and only when one of its due envs has a
    learned commander. Teams are visited 0 then 1 and networks in ``learned`` order,
    and decisions are sampled as ``act`` samples them (``sample_actions``), so a
    seeded run draws the same decisions every time.

    Args:
        env: The env, before its next step.
        side_commander: [n_envs, 2] index of each env's team 0 and team 1 commander
            in the caller's list (``NOT_IN_STABLE`` for none).
        learned: ``(index, actor)`` of every learned commander in that list.
        running: [n_envs] envs that may decide (finished eval matches may not).

    Returns:
        The number of decisions submitted.

    Raises:
        ValueError: ``side_commander`` or ``running`` does not have one row per env.
    """
    n = env.n_envs
    if side_commander.shape != (n, 2) or running.shape != (n,):
        raise ValueError(
            f"side_commander must be [{n}, 2] and running [{n}], got "
            f"{side_commander.shape} and {running.shape}"
        )
    submitted = 0
    if not learned:
        return submitted
    for team in (0, 1):
        due = np.asarray(env.raw.commander_due(team), dtype=np.bool_) & running
        if not due.any():
            continue
        feats: Mapping[str, NDArray] | None = None
        for index, actor in learned:
            rows = np.flatnonzero(due & (side_commander[:, team] == index))
            if rows.size == 0:
                continue
            if feats is None:
                feats = env.raw.commander_features(team)
            x = CommanderInputs.from_numpy(
                {key: np.asarray(feats[key])[rows] for key in FEATURE_KEYS}
            )
            actions = sample_actions(actor, x)
            env.raw.submit_commander_actions(
                team, rows.astype(np.int64), actions.numpy().astype(np.int32)
            )
            submitted += int(rows.size)
    return submitted
