"""The pilot stable a commander commands: every strike craft on both sides is flown by a
pilot drawn at random, ship by ship, from the live list (``lab/live_pilots.json``), as
the live page draws them. Capital ships fly the sim's scripts.
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
    """Frozen pilots, one drawn per strike-craft slot for each match.

    Attributes:
        ids: Pilot ids, index order.
        assign: [N, S] int64: the pilot index flying each slot, or ``script`` (=
            ``len(ids)``) for capital ships and empty slots.
    """

    def __init__(
        self,
        pilots: Sequence[tuple[str, Path]],
        n_envs: int,
        n_ships: int,
        seed: int,
        assets_dir: Path,
    ) -> None:
        if not pilots:
            raise ValueError("a pilot stable needs at least one pilot")
        self.ids = [pid for pid, _ in pilots]
        self.policies = [Policy(path, sample=True) for _, path in pilots]
        self.script = len(self.ids)
        self.assign = np.full((n_envs, n_ships), self.script, dtype=np.int64)
        self._capital = np.asarray(capital_hull_ids(assets_dir), dtype=np.int64)
        self._rng = np.random.default_rng(seed)

    def draw(self, env: RustVecEnv, envs: Sequence[int] | NDArray[np.integer]) -> None:
        """Draw a pilot for every strike craft of ``envs``' current matches."""
        for i in envs:
            hull = env.hull_id[int(i)]
            strike = (hull >= 0) & ~np.isin(hull, self._capital)
            row = np.full(hull.shape, self.script, dtype=np.int64)
            row[strike] = self._rng.integers(0, len(self.ids), int(strike.sum()))
            self.assign[int(i)] = row

    def actions(self, env: RustVecEnv) -> NDArray[np.int8]:
        """Every ship's action this tick: the scripts', then each pilot's rows."""
        actions = env.scripted_actions().copy()
        for k, policy in enumerate(self.policies):
            rows = self.assign == k
            if rows.any():
                actions[rows] = policy.act(env, rows)
        return actions
