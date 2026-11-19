"""The pilot stable a commander commands: every strike craft on both sides is flown by a
pilot drawn at random, ship by ship, from the live list (``lab/live_pilots.json``), as
the live page draws them. Capital ships fly the sim's scripts.

A stable may also put the script pilot in the draw (``include_script``), as the WAR
measurement does: then the script flies a strike craft as often as any other pilot.

The draw mode ``side`` (``PILOT_DRAW_SIDE``) draws one pilot per team instead, and all
that team's strike craft fly it, so each side is one commander and one pilot (the live
page's ``?pairing=side``). A draw may also pin a team's pilot. The default, ``ship``,
draws exactly what it always did.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from spacefight.env.rosters import capital_hull_ids
from spacefight.env.rust_env import RustVecEnv
from spacefight.eval.controllers import Policy

REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_PILOTS = REPO_ROOT / "lab" / "live_pilots.json"
# Draw modes: a pilot per strike craft, or one per team that all its strike craft fly.
PILOT_DRAW_SHIP = "ship"
PILOT_DRAW_SIDE = "side"
PILOT_DRAWS = (PILOT_DRAW_SHIP, PILOT_DRAW_SIDE)
# A team whose pilot is not pinned (``PilotStable.draw``'s ``pinned``).
UNPINNED = -1


def live_pilot_checkpoints(
    path: Path = LIVE_PILOTS, root: Path = REPO_ROOT
) -> list[tuple[str, Path]]:
    """``(id, checkpoint)`` of every pilot on the live list, in its order.

    Raises:
        ValueError: The file is not a live list, or is empty.
        FileNotFoundError: A checkpoint is missing.
    """
    data = json.loads(path.read_text())
    if data.get("schema") != "rlf.live_pilots/1" or not data.get("pilots"):
        raise ValueError(f"{path} is not a non-empty rlf.live_pilots/1 list")
    out = []
    for p in data["pilots"]:
        ckpt = root / p["checkpoint"]
        if not ckpt.is_file():
            raise FileNotFoundError(f"pilot {p['id']}: no checkpoint at {ckpt}")
        out.append((str(p["id"]), ckpt))
    return out


class PilotStable:
    """Frozen pilots, drawn for every strike-craft slot of each match: one per slot
    (``ship``), or one per team (``side``).

    Attributes:
        ids: Pilot ids, index order.
        mode: ``PILOT_DRAW_SHIP`` or ``PILOT_DRAW_SIDE``.
        assign: [N, S] int64: the pilot index flying each slot, or ``script`` (=
            ``len(ids)``) for capital ships and empty slots, and for strike craft the
            script pilot was drawn to fly.
        include_script: Whether the script pilot is in the draw for strike craft.
    """

    def __init__(
        self,
        pilots: Sequence[tuple[str, Path]],
        n_envs: int,
        n_ships: int,
        seed: int,
        assets_dir: Path,
        include_script: bool = False,
        mode: str = PILOT_DRAW_SHIP,
    ) -> None:
        """Load every pilot's policy.

        Args:
            pilots: ``(id, checkpoint)`` of the neural pilots, in index order.
            n_envs: Matches played at once.
            n_ships: Slots per match.
            seed: Seed of the ship-by-ship draw.
            assets_dir: Sim assets, for which hulls are capital ships.
            include_script: Also draw the script pilot for strike craft, uniformly with
                the others. Off, the draw is exactly what it always was.
            mode: ``ship`` draws a pilot per strike craft (as it always did), ``side``
                one per team, flown by all its strike craft.

        Raises:
            ValueError: No neural pilot, or an unknown mode.
        """
        if not pilots:
            raise ValueError("a pilot stable needs at least one pilot")
        if mode not in PILOT_DRAWS:
            raise ValueError(f"pilot draw must be one of {PILOT_DRAWS}, got {mode!r}")
        self.mode = mode
        self.ids = [pid for pid, _ in pilots]
        self.policies = [Policy(path, sample=True) for _, path in pilots]
        self.script = len(self.ids)
        self.include_script = include_script
        self.assign = np.full((n_envs, n_ships), self.script, dtype=np.int64)
        self._capital = np.asarray(capital_hull_ids(assets_dir), dtype=np.int64)
        self._rng = np.random.default_rng(seed)

    def draw(
        self,
        env: RustVecEnv,
        envs: Sequence[int] | NDArray[np.integer],
        pinned: NDArray[np.integer] | None = None,
    ) -> None:
        """Draw a pilot for every strike craft of ``envs``' current matches.

        Args:
            env: The env whose current matches are drawn for (its ``hull_id``, and
                ``team`` in side mode or with pins).
            envs: The envs to draw.
            pinned: Optional ``[len(envs), 2]`` pilot index of each env's team 0 and
                team 1 (an index into ``ids``, or ``script``), or ``UNPINNED`` to draw.
                The draw is made as without pins and then a pinned team's strike craft
                are overwritten, so the unpinned team flies the same pilots it would
                have without them.

        Raises:
            ValueError: ``pinned`` has the wrong shape or an index out of range.
        """
        envs = list(envs)
        if pinned is not None:
            pinned = np.asarray(pinned, dtype=np.int64)
            if pinned.shape != (len(envs), 2):
                raise ValueError(f"pinned must be [{len(envs)}, 2], got {pinned.shape}")
            if pinned.min() < UNPINNED or pinned.max() > self.script:
                raise ValueError(f"pinned pilots must be in -1..{self.script}")
        choices = len(self.ids) + int(self.include_script)
        for k, i in enumerate(envs):
            hull = env.hull_id[int(i)]
            strike = (hull >= 0) & ~np.isin(hull, self._capital)
            row = np.full(hull.shape, self.script, dtype=np.int64)
            if self.mode == PILOT_DRAW_SHIP:
                row[strike] = self._rng.integers(0, choices, int(strike.sum()))
            else:
                side = self._rng.integers(0, choices, 2)
                team = np.asarray(env.team[int(i)])
                for t in (0, 1):
                    row[strike & (team == t)] = side[t]
            if pinned is not None:
                team = np.asarray(env.team[int(i)])
                for t in (0, 1):
                    if pinned[k, t] != UNPINNED:
                        row[strike & (team == t)] = pinned[k, t]
            self.assign[int(i)] = row

    def strike_mask(self, env: RustVecEnv) -> NDArray[np.bool_]:
        """[N, S] strike craft of the current matches: the slots a pilot is drawn for."""
        hull = np.asarray(env.hull_id)
        return (hull >= 0) & ~np.isin(hull, self._capital)

    def actions(self, env: RustVecEnv) -> NDArray[np.int8]:
        """Every ship's action this tick: the scripts', then each pilot's rows."""
        actions = env.scripted_actions().copy()
        for k, policy in enumerate(self.policies):
            rows = self.assign == k
            if rows.any():
                actions[rows] = policy.act(env, rows)
        return actions
