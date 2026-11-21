"""PPO for the commander (docs/COMMANDER.md "Training").

One step is one decision of a ``learned`` team (every 30 ticks). Pilots are frozen and
drawn per ship from the live list. Each match draws the learner's team, the enemy
commander (scripted, random, the learner itself, one of its snapshots, weighted toward
the ones it beats least, or "unseen": the script with its orders hidden from its own
pilots, so a side nobody commands), the mission (uniform, as the live page rotates) and a
live roster.

    uv run python -m spacefight.commander.train --run-dir lab/runs/<id>/<arm> \
        --deadline "07:30" [--n-envs 64] [--smoke]
"""

from __future__ import annotations

import argparse
import copy
import json
import signal
import subprocess
import sys
import time
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any, Final

import numpy as np
import rlf_sim
import torch
from numpy.typing import NDArray

from spacefight.commander.io import (
    LAUNCH,
    MASK_SHAPES,
    ORDER,
    ORDER_KEEP,
    ORDER_NAMES,
    CommanderInputs,
    check_sim_layout,
)
from spacefight.commander.pilots import (
    LIVE_PILOTS,
    REPO_ROOT as PILOTS_ROOT,
    PilotStable,
    live_pilot_checkpoints,
)
from spacefight.commander.policy import (
    CommanderActor,
    CommanderCritic,
    act,
    evaluate,
    forbid_orders,
    lean_to_hold,
    lean_to_keep,
    load_commander,
    n_params,
    save_commander,
)
from spacefight.env.rosters import (
    CARRIER_BATTLE,
    CONVOY_ESCORT,
    DEATHMATCH,
    RANDOM,
    SCRIPTED,
    STATION_AS_CARRIER,
    STATION_AS_CONVOY,
    STATION_ASSAULT,
    PilotsDistribution,
    Roster,
    make_sampler,
)
from spacefight.env.rust_env import RustVecEnv
from spacefight.eval.missions import default_rosters, named_roster

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS = REPO_ROOT / "assets"
LEARNED: Final = "learned"
# The missions the commander evals and the WAR matches play by default.
MISSIONS: Final = (DEATHMATCH, CARRIER_BATTLE, CONVOY_ESCORT)
# The missions ``TrainConfig.mission_weights`` draws from (SIM_VERSION 9 adds the
# station assault, weight 0 by default: three weights mean exactly the old draws).
TRAIN_MISSIONS: Final = (*MISSIONS, STATION_ASSAULT)
WINNER_DRAW: Final = -1
# A station assault's team 0 defends the station; the log scores each enemy per role.
STATION_ROLES: Final = ("defender", "attacker")
TICK_HZ: Final = 30

# Enemy commander kinds.
OPP_SCRIPTED, OPP_RANDOM, OPP_SELF, OPP_SNAPSHOT, OPP_UNSEEN = range(5)
OPP_NAMES: Final = ("scripted", "random", "self", "snapshot", "unseen")
STATION_SIDES: Final = tuple(f"{o}_{r}" for o in OPP_NAMES for r in STATION_ROLES)
# The controller of a team in a match: not learned, the learner, or snapshot k (>= 2).
NOT_LEARNED, LEARNER = 0, 1
FEATURE_KEYS: Final = ("globals", "entities", "valid", *MASK_SHAPES)


@dataclass
class TrainConfig:
    """Everything a run needs; written to ``config.json`` in the run dir."""

    n_envs: int = 64
    n_threads: int = 4
    torch_threads: int = 4
    seed: int = 0
    decisions_per_update: int = 4096
    epochs: int = 4
    minibatch: int = 512
    lr: float = 3e-4
    clip: float = 0.2
    # 0.002 since 2026-11-21: at 0.01 a commander-3 arm kept ordering half the time and
    # lost 0.34 to 0.66; every run since has used 0.002 (docs/COMMANDER.md "Training").
    ent_coef: float = 0.002
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    gamma: float = 0.99
    lam: float = 0.95
    shaping: float = 0.5
    # The price of an order: each decision's reward drops by this for every ship whose
    # order it changed. Not potential-based; it is meant to change what is best.
    order_price: float = 0.0
    # A fresh actor's odds of "keep" on its order and squad heads (policy.lean_to_keep).
    keep_prior: float = 0.8
    # Enemy commander shares: scripted, random, self, snapshots (snapshots' share goes to
    # self until the first snapshot exists), unseen (the scripted commander with its
    # orders hidden from its own pilots: the side with no orders). Four shares, as configs
    # from before the unseen enemy have, mean none of it.
    opponent_shares: tuple[float, ...] = (0.35, 0.1, 0.3, 0.25, 0.0)
    pfsp_power: float = 1.0
    pfsp_floor: float = 0.1
    snapshot_every: int = 20
    max_snapshots: int = 10
    checkpoint_every: int = 10
    # One weight per ``TRAIN_MISSIONS``; a three-weight tuple (configs from before
    # SIM_VERSION 9) gets a station weight of 0, which draws exactly as before. The
    # default plays every live mission equally, as the live page rotates them (station
    # assault included since 2026-11-21).
    mission_weights: tuple[float, ...] = (1.0, 1.0, 1.0, 1.0)
    live_pilots: str = str(LIVE_PILOTS)
    # The chance a station assault reads to the nets as a convoy escort (station side
    # the convoy defender), else as a carrier battle. 0 draws exactly as before.
    station_convoy_share: float = 0.0
    # A commander checkpoint (``save_commander``) the actor starts from instead of a
    # fresh net (``keep_prior`` then does nothing); the critic starts fresh. "": none.
    init: str = ""
    # Per hull class, the chance the launch head launches each decision
    # (policy.lean_to_hold), set after any ``init`` load. 0: the head as it is.
    launch_prior: float = 0.0
    # The learner's team in every match (a station assault's team 0 defends); -1 draws
    # it per match. A pinned learner needs no self or snapshot enemy.
    learner_team: int = -1
    # The sim's station-assault roster the station draws play
    # (``rlf_sim.mission_rosters("station_assault")``, e.g. "strike of 8"). "": the
    # live default (``spacefight.eval.missions.default_rosters``, the citadel).
    station_roster: str = ""
    # Order kinds the learner never picks (policy.forbid_orders, a bias set after any
    # ``init`` load), e.g. ("attack",).
    forbid_orders: tuple[str, ...] = ()
    # The checkout that holds the pilots' checkpoints (``live_pilots`` paths resolve
    # against it; a worktree has no weights). "": this checkout.
    pilot_root: str = ""
    max_updates: int = 1_000_000

    def __post_init__(self) -> None:
        shares = tuple(float(x) for x in self.opponent_shares)
        if len(shares) == len(OPP_NAMES) - 1:
            shares = (*shares, 0.0)
        if len(shares) != len(OPP_NAMES) or min(shares) < 0 or sum(shares) <= 0:
            raise ValueError(
                f"opponent_shares needs {len(OPP_NAMES)} non-negative shares "
                f"({', '.join(OPP_NAMES)}), not all zero; got {self.opponent_shares}"
            )
        self.opponent_shares = shares
        weights = tuple(float(x) for x in self.mission_weights)
        if len(weights) == len(TRAIN_MISSIONS) - 1:
            weights = (*weights, 0.0)
        if len(weights) != len(TRAIN_MISSIONS) or min(weights) < 0 or sum(weights) <= 0:
            raise ValueError(
                f"mission_weights needs {len(TRAIN_MISSIONS)} non-negative weights "
                f"({', '.join(TRAIN_MISSIONS)}), not all zero; got {self.mission_weights}"
            )
        self.mission_weights = weights
        if self.decisions_per_update < self.minibatch:
            raise ValueError("decisions_per_update must be at least one minibatch")
        if self.order_price < 0:
            raise ValueError(
                f"order_price must not be negative, got {self.order_price}"
            )
        if not 0.0 <= self.station_convoy_share <= 1.0:
            raise ValueError(
                "station_convoy_share must be in [0, 1], "
                f"got {self.station_convoy_share}"
            )
        if not 0.0 <= self.launch_prior < 1.0:
            raise ValueError(f"launch_prior must be in [0, 1), got {self.launch_prior}")
        if self.learner_team not in (-1, 0, 1):
            raise ValueError(
                f"learner_team must be -1 (either) or 0 or 1, got {self.learner_team}"
            )
        if self.learner_team >= 0 and (
            shares[OPP_SELF] > 0 or shares[OPP_SNAPSHOT] > 0
        ):
            # Self-play would train the learner on the other side too, and its
            # snapshots never played that side.
            raise ValueError(
                "a pinned learner_team needs self and snapshot opponent_shares of 0, "
                f"got {self.opponent_shares}"
            )
        if self.station_roster:
            named_roster(STATION_ASSAULT, self.station_roster)
        self.forbid_orders = tuple(str(o) for o in self.forbid_orders)
        for order in self.forbid_orders:
            if order not in ORDER_NAMES[1:]:
                raise ValueError(
                    f"forbid_orders names {order!r}; choose from {ORDER_NAMES[1:]}"
                )


def initial_actor(cfg: TrainConfig) -> CommanderActor:
    """The actor a new run starts from: ``cfg.init``'s weights if it names a commander
    checkpoint, else a fresh net leaning to "keep" (``cfg.keep_prior``); then, on
    either, the launch head re-set to ``cfg.launch_prior`` (if > 0) and the orders of
    ``cfg.forbid_orders`` forbidden.

    Raises:
        ValueError: ``cfg.init`` is not a commander file of this io version.
    """
    actor = CommanderActor()
    lean_to_keep(actor, cfg.keep_prior)
    if cfg.init:
        start, _ = load_commander(Path(cfg.init))
        actor.load_state_dict(start.state_dict())
    if cfg.launch_prior > 0:
        lean_to_hold(actor, cfg.launch_prior)
    forbid_orders(actor, cfg.forbid_orders)
    return actor


def train_rosters(cfg: TrainConfig) -> dict[str, list[tuple[str, Roster]]]:
    """Per mission other than the deathmatch, the ``(name, roster)`` options a match
    draws from: the live defaults, the station assault's ``cfg.station_roster`` if set.

    Raises:
        ValueError: The sim has no station-assault roster ``cfg.station_roster``.
    """
    rosters = {m: default_rosters(m) for m in TRAIN_MISSIONS[1:]}
    if cfg.station_roster:
        rosters[STATION_ASSAULT] = [named_roster(STATION_ASSAULT, cfg.station_roster)]
    return rosters


@dataclass
class Assignment:
    """Who commands what in one match."""

    learner_team: int
    opponent: int  # OPP_*
    snapshot: int = -1  # pool index for OPP_SNAPSHOT
    mission: str = DEATHMATCH
    roster: str = ""
    # What a station assault reads as to the nets (ignored by the other missions).
    station_as: str = STATION_AS_CARRIER

    def controllers(self) -> tuple[int, int]:
        enemy = {
            OPP_SCRIPTED: NOT_LEARNED,
            OPP_RANDOM: NOT_LEARNED,
            OPP_SELF: LEARNER,
            OPP_SNAPSHOT: 2 + self.snapshot,
            OPP_UNSEEN: NOT_LEARNED,
        }[self.opponent]
        c = [enemy, enemy]
        c[self.learner_team] = LEARNER
        return c[0], c[1]

    def modes(self) -> tuple[str, str]:
        enemy = {
            OPP_SCRIPTED: SCRIPTED,
            OPP_RANDOM: RANDOM,
            OPP_UNSEEN: SCRIPTED,
        }.get(self.opponent, LEARNED)
        m = [enemy, enemy]
        m[self.learner_team] = LEARNED
        return m[0], m[1]

    def hide_orders(self) -> tuple[bool, bool]:
        """Per team, whether its pilots are kept from seeing their orders: the enemy's
        under an unseen commander, nobody's otherwise."""
        hide = [self.opponent == OPP_UNSEEN] * 2
        hide[self.learner_team] = False
        return hide[0], hide[1]


@dataclass
class Transition:
    """One learner decision; reward and next value fill in at the next decision or the
    end of the match."""

    key: tuple[int, int, int]  # env, team, match serial
    features: dict[str, NDArray]
    pilot: NDArray[np.int64]
    action: NDArray[np.int64]
    logp: float
    value: float
    phi: float
    # What this decision's order changes cost (``order_price`` a ship).
    cost: float = 0.0
    reward: float = 0.0
    done: bool = False
    next_value: float = 0.0


class Results:
    """Learner's score against each enemy commander (1 win, 0.5 draw, 0 loss)."""

    def __init__(self) -> None:
        self.score: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])

    def record(self, name: str, score: float) -> None:
        s = self.score[name]
        s[0] += score
        s[1] += 1.0

    def rate(self, name: str) -> float:
        s = self.score.get(name)
        return 0.5 if not s or s[1] == 0 else s[0] / s[1]


class Trainer:
    def __init__(self, run_dir: Path, cfg: TrainConfig, resume: bool = False) -> None:
        self.run_dir = run_dir
        self.cfg = cfg
        torch.set_num_threads(cfg.torch_threads)
        torch.manual_seed(cfg.seed)
        self.rng = np.random.default_rng(cfg.seed)
        sim_io = rlf_sim.commander_io()
        check_sim_layout(sim_io)
        self.decision_s = float(sim_io["command_ticks"]) / TICK_HZ
        entity = sim_io["entity_layout"]
        own, cls, order = entity["own"][0], entity["class"][0], entity["order"][0]
        # Entity columns: own team, the three strike hull classes, an order other than none.
        self.own_col = int(own)
        self.strike_cols = slice(int(cls), int(cls) + 3)
        self.ordered_cols = slice(int(order) + 1, int(order) + 4)
        self.actor = initial_actor(cfg)
        pilots = live_pilot_checkpoints(
            Path(cfg.live_pilots),
            Path(cfg.pilot_root) if cfg.pilot_root else PILOTS_ROOT,
        )
        self.critic = CommanderCritic(n_pilots=len(pilots))
        self.opt = torch.optim.Adam(
            list(self.actor.parameters()) + list(self.critic.parameters()), lr=cfg.lr
        )
        self.update = 0
        self.pool: list[tuple[int, Path]] = []
        self.pool_actors: list[CommanderActor] = []
        self.results = Results()
        if resume:
            self._load_state()
        self.dm_sampler = make_sampler(
            PilotsDistribution(mission_weights=(1.0, 0.0, 0.0)), cfg.seed + 7
        )
        self.mission_rosters = train_rosters(cfg)
        first = self._draw_assignment()
        roster = self._roster(first)
        self.env = RustVecEnv(
            ASSETS,
            cfg.n_envs,
            roster.fleets(),
            cfg.seed,
            n_threads=cfg.n_threads,
            reaction_ticks=2,
            max_ships=20,
            commanders=(SCRIPTED, SCRIPTED),
        )
        self.stable = PilotStable(
            pilots,
            cfg.n_envs,
            self.env.n_ships,
            cfg.seed + 11,
            ASSETS,
        )
        self.current: list[Assignment] = [first] * cfg.n_envs
        self.queued: list[Assignment] = []
        for i in range(cfg.n_envs):
            a = self._draw_assignment()
            self._queue(i, a)
        self.env.reset()
        self.current = list(self.queued)
        self.queued = [self._draw_assignment() for _ in range(cfg.n_envs)]
        for i, a in enumerate(self.queued):
            self._queue(i, a, store=False)
        self.serial = np.zeros(cfg.n_envs, dtype=np.int64)
        self.stable.draw(self.env, range(cfg.n_envs))
        self.v_total0 = np.maximum(self.env.team_values().sum(axis=1), 1.0)
        self.pending: dict[tuple[int, int], Transition] = {}
        self.completed: list[Transition] = []
        self.match_stats: dict[str, float] = defaultdict(float)

    # -- assignments ---------------------------------------------------------

    def _draw_assignment(self) -> Assignment:
        cfg = self.cfg
        shares = np.asarray(cfg.opponent_shares, dtype=np.float64)
        if not self.pool:
            shares[OPP_SELF] += shares[OPP_SNAPSHOT]
            shares[OPP_SNAPSHOT] = 0.0
        opp = int(self.rng.choice(len(shares), p=shares / shares.sum()))
        snap = -1
        if opp == OPP_SNAPSHOT:
            rates = np.array(
                [self.results.rate(self._snap_name(k)) for k in range(len(self.pool))]
            )
            w = (1.0 - rates) ** cfg.pfsp_power + cfg.pfsp_floor
            snap = int(self.rng.choice(len(self.pool), p=w / w.sum()))
        mw = np.asarray(cfg.mission_weights, dtype=np.float64)
        # A trailing zero weight leaves the draw exactly as with three missions.
        mission = TRAIN_MISSIONS[int(self.rng.choice(len(mw), p=mw / mw.sum()))]
        # Drawn even when pinned, so a pinned run's other draws are an unpinned one's.
        learner_team = int(self.rng.integers(0, 2))
        if cfg.learner_team >= 0:
            learner_team = cfg.learner_team
        station_as = STATION_AS_CARRIER
        # Drawn only when it can be convoy, so a share of 0 draws exactly as before.
        if mission == STATION_ASSAULT and cfg.station_convoy_share > 0:
            if self.rng.random() < cfg.station_convoy_share:
                station_as = STATION_AS_CONVOY
        return Assignment(
            learner_team=learner_team,
            opponent=opp,
            snapshot=snap,
            mission=mission,
            station_as=station_as,
        )

    def _snap_name(self, k: int) -> str:
        return f"snapshot_{self.pool[k][0]}"

    def _opp_name(self, a: Assignment) -> str:
        if a.opponent == OPP_SNAPSHOT:
            return self._snap_name(a.snapshot)
        return OPP_NAMES[a.opponent]

    def _roster(self, a: Assignment) -> Roster:
        if a.mission == DEATHMATCH:
            teams = self.dm_sampler.sample().teams
            a.roster = "draft"
        else:
            options = self.mission_rosters[a.mission]
            name, r = options[int(self.rng.integers(0, len(options)))]
            teams, a.roster = r.teams, name
        return Roster(teams, a.mission, a.modes(), station_as=a.station_as)

    def _queue(self, i: int, a: Assignment, store: bool = True) -> None:
        roster = self._roster(a)
        self.env.set_next_roster(
            i,
            roster,
            time_limit_s=float(rlf_sim.mission_time_limit_s(a.mission)),
            hide_orders=a.hide_orders(),
        )
        if store:
            self.queued.append(a)

    # -- rollout -------------------------------------------------------------

    def _phi(self, i: int, team: int, values: NDArray) -> float:
        own, enemy = values[i, team], values[i, 1 - team]
        return self.cfg.shaping * float(own - enemy) / float(self.v_total0[i])

    def _decide(self) -> None:
        """Every learned team due to decide: choose, submit, record the learner's."""
        values: NDArray | None = None
        for team in (0, 1):
            due = np.asarray(self.env.raw.commander_due(team), dtype=bool)
            ctrl = np.array([a.controllers()[team] for a in self.current])
            due &= ctrl != NOT_LEARNED
            if not due.any():
                continue
            feats = self.env.raw.commander_features(team)
            if values is None:
                values = np.asarray(self.env.raw.team_values())
            for c in np.unique(ctrl[due]):
                rows = np.flatnonzero(due & (ctrl == c))
                sub = {k: np.asarray(feats[k])[rows] for k in FEATURE_KEYS}
                x = CommanderInputs.from_numpy(sub)
                model = self.actor if c == LEARNER else self.pool_actors[int(c) - 2]
                actions, logp = act(model, x)
                changed = np.asarray(
                    self.env.raw.submit_commander_actions(
                        team, rows.astype(np.int64), actions.numpy().astype(np.int32)
                    )
                )
                if c != LEARNER:
                    continue
                pilot = self.stable.assign[rows]
                with torch.no_grad():
                    v = self.critic(x, torch.from_numpy(pilot)).numpy()
                for j, i in enumerate(rows):
                    i = int(i)
                    phi = self._phi(i, team, values)
                    prev = self.pending.pop((i, team), None)
                    if prev is not None:
                        prev.reward = self.cfg.gamma * phi - prev.phi - prev.cost
                        prev.next_value = float(v[j])
                        self.completed.append(prev)
                    self.pending[(i, team)] = Transition(
                        key=(i, team, int(self.serial[i])),
                        features={k: sub[k][j] for k in FEATURE_KEYS},
                        pilot=pilot[j],
                        action=actions[j].numpy(),
                        logp=float(logp[j]),
                        value=float(v[j]),
                        phi=phi,
                        cost=self.cfg.order_price * float(changed[j]),
                    )
                self._behaviour(actions, sub["entities"], changed)

    def _behaviour(
        self, actions: torch.Tensor, entities: NDArray, changed: NDArray
    ) -> None:
        """Count what the learner's decisions did. ``entities`` [K, E, ENTITY_DIM] are
        the inputs they were made from, ``changed`` [K] the ships each re-ordered."""
        a = actions.numpy()
        s = self.match_stats
        strike = (entities[:, :, self.own_col] > 0) & (
            entities[:, :, self.strike_cols].sum(axis=-1) > 0
        )
        ordered = strike & (entities[:, :, self.ordered_cols].sum(axis=-1) > 0)
        s["ship_decisions"] += float(strike.sum())
        s["ships_ordered"] += float(ordered.sum())
        s["ships_changed"] += float(changed.sum())
        s["decisions"] += a.shape[0]
        s["launch_orders"] += float((a[:, LAUNCH] == 1).sum())
        order = a[:, ORDER]
        s["order_heads"] += order.size
        s["order_changes"] += float((order != ORDER_KEEP).sum())
        for k, name in enumerate(ORDER_NAMES):
            s[f"order_{name}"] += float((order == k).sum())

    def _finish(self, done_envs: NDArray, winner: NDArray) -> None:
        for i in done_envs:
            i = int(i)
            a = self.current[i]
            ctrl = a.controllers()
            for team in (0, 1):
                if ctrl[team] != LEARNER:
                    continue
                w = int(winner[i])
                if w not in (0, 1, WINNER_DRAW):
                    raise RuntimeError(f"env {i} ended with winner code {w}")
                outcome = 0.0 if w == WINNER_DRAW else (1.0 if w == team else -1.0)
                prev = self.pending.pop((i, team), None)
                if prev is not None:
                    prev.reward = outcome - prev.phi - prev.cost
                    prev.done = True
                    self.completed.append(prev)
                if team == a.learner_team and a.opponent != OPP_SELF:
                    score = 0.5 if w == WINNER_DRAW else float(w == team)
                    self.results.record(self._opp_name(a), score)
                    self.match_stats[f"n_{OPP_NAMES[a.opponent]}"] += 1
                    self.match_stats[f"won_{OPP_NAMES[a.opponent]}"] += score
                    self.match_stats[f"n_{a.mission}"] += 1
                    self.match_stats[f"won_{a.mission}"] += score
                    if a.mission == STATION_ASSAULT:
                        side = f"{OPP_NAMES[a.opponent]}_{STATION_ROLES[team]}"
                        self.match_stats[f"n_{side}"] += 1
                        self.match_stats[f"won_{side}"] += score
            self.match_stats["matches"] += 1
            self.serial[i] += 1
            self.current[i] = self.queued[i]
            self.queued[i] = self._draw_assignment()
            self._queue(i, self.queued[i], store=False)
        if done_envs.size:
            self.stable.draw(self.env, done_envs)
            totals = np.asarray(self.env.raw.team_values()).sum(axis=1)
            self.v_total0[done_envs] = np.maximum(totals[done_envs], 1.0)

    def rollout(self) -> None:
        """Step until ``decisions_per_update`` decisions are complete."""
        while len(self.completed) < self.cfg.decisions_per_update:
            self._decide()
            actions = self.stable.actions(self.env)
            _, _, dones, info = self.env.step(actions)
            done_envs = np.flatnonzero(dones)
            if done_envs.size:
                self._finish(done_envs, np.asarray(info.winner).copy())

    # -- update --------------------------------------------------------------

    def _advantages(self, batch: list[Transition]) -> tuple[NDArray, NDArray]:
        cfg = self.cfg
        adv = np.zeros(len(batch), dtype=np.float32)
        by_key: dict[tuple[int, int, int], list[int]] = defaultdict(list)
        for n, t in enumerate(batch):
            by_key[t.key].append(n)
        for idx in by_key.values():
            nxt = 0.0
            for n in reversed(idx):
                t = batch[n]
                nonterminal = 0.0 if t.done else 1.0
                delta = t.reward + cfg.gamma * t.next_value * nonterminal - t.value
                nxt = delta + cfg.gamma * cfg.lam * nonterminal * nxt
                adv[n] = nxt
        values = np.array([t.value for t in batch], dtype=np.float32)
        return adv, adv + values

    def learn(self) -> dict[str, float]:
        cfg = self.cfg
        batch, self.completed = self.completed, []
        adv, returns = self._advantages(batch)
        x = CommanderInputs.from_numpy(
            {k: np.stack([t.features[k] for t in batch]) for k in FEATURE_KEYS}
        )
        actions = torch.from_numpy(np.stack([t.action for t in batch]))
        pilot = torch.from_numpy(np.stack([t.pilot for t in batch]))
        old_logp = torch.tensor([t.logp for t in batch])
        adv_t = torch.from_numpy(adv)
        adv_t = (adv_t - adv_t.mean()) / (adv_t.std() + 1e-8)
        ret_t = torch.from_numpy(returns)
        n = len(batch)
        stats: dict[str, list[float]] = defaultdict(list)
        params = list(self.actor.parameters()) + list(self.critic.parameters())
        for _ in range(cfg.epochs):
            perm = torch.randperm(n)
            for start in range(0, n, cfg.minibatch):
                mb = perm[start : start + cfg.minibatch]
                xb = x.index(mb)
                logp, entropy, per_head = evaluate(self.actor, xb, actions[mb])
                ratio = (logp - old_logp[mb]).exp()
                a = adv_t[mb]
                pg = -torch.min(
                    ratio * a, ratio.clamp(1 - cfg.clip, 1 + cfg.clip) * a
                ).mean()
                v = self.critic(xb, pilot[mb])
                vf = 0.5 * (v - ret_t[mb]).pow(2).mean()
                ent = entropy.mean()
                loss = pg + cfg.vf_coef * vf - cfg.ent_coef * ent
                self.opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, cfg.max_grad_norm)
                self.opt.step()
                with torch.no_grad():
                    stats["policy_loss"].append(float(pg))
                    stats["value_loss"].append(float(vf))
                    stats["entropy"].append(float(ent))
                    stats["approx_kl"].append(float((old_logp[mb] - logp).mean()))
                    stats["clip_frac"].append(
                        float(((ratio - 1).abs() > cfg.clip).float().mean())
                    )
                    for name, e in per_head.items():
                        e = e.sum(dim=-1) if e.dim() > 1 else e
                        stats[f"entropy_{name}"].append(float(e.mean()))
        out = {k: float(np.mean(v)) for k, v in stats.items()}
        out["decisions"] = float(n)
        out["mean_reward"] = float(np.mean([t.reward for t in batch]))
        out["value_mean"] = float(np.mean([t.value for t in batch]))
        out["return_mean"] = float(returns.mean())
        return out

    # -- snapshots, checkpoints ----------------------------------------------

    def _snapshot(self) -> None:
        path = self.run_dir / "snapshots" / f"commander_{self.update}.pt"
        save_commander(path, self.actor, {"update": self.update})
        self.pool.append((self.update, path))
        self.pool_actors.append(copy.deepcopy(self.actor).eval())
        if len(self.pool) > self.cfg.max_snapshots:
            self.pool.pop(0)
            self.pool_actors.pop(0)
            # Matches already assigned to a dropped snapshot index shift; rebuild
            # their assignment so they point at a live entry.
            for lst in (self.current, self.queued):
                for a in lst:
                    if a.opponent == OPP_SNAPSHOT:
                        a.snapshot = max(a.snapshot - 1, 0)

    def checkpoint(self) -> None:
        ckpt = self.run_dir / "checkpoints" / f"commander_{self.update}.pt"
        save_commander(ckpt, self.actor, {"update": self.update})
        state = {
            "actor": self.actor.state_dict(),
            "critic": self.critic.state_dict(),
            "opt": self.opt.state_dict(),
            "update": self.update,
            "pool": [(u, str(p)) for u, p in self.pool],
            "results": {k: list(v) for k, v in self.results.score.items()},
        }
        tmp = self.run_dir / "state.tmp"
        torch.save(state, tmp)
        tmp.replace(self.run_dir / "state.pt")

    def _load_state(self) -> None:
        state = torch.load(
            self.run_dir / "state.pt", map_location="cpu", weights_only=False
        )
        self.actor.load_state_dict(state["actor"])
        self.critic.load_state_dict(state["critic"])
        self.opt.load_state_dict(state["opt"])
        self.update = int(state["update"])
        for u, p in state["pool"]:
            actor, _ = load_commander(Path(p))
            self.pool.append((int(u), Path(p)))
            self.pool_actors.append(actor)
        for k, v in state["results"].items():
            self.results.score[k] = [float(v[0]), float(v[1])]

    # -- main loop -----------------------------------------------------------

    def train(self, deadline: float) -> None:
        log = (self.run_dir / "log.jsonl").open("a")
        start = time.time()
        stop = {"requested": False}

        def request_stop(signum: int, frame: object) -> None:
            stop["requested"] = True

        # SIGTERM ends the run after the current update, with a checkpoint.
        signal.signal(signal.SIGTERM, request_stop)
        while (
            self.update < self.cfg.max_updates
            and time.time() < deadline
            and not stop["requested"]
        ):
            t0 = time.time()
            self.match_stats = defaultdict(float)
            self.rollout()
            t1 = time.time()
            stats = self.learn()
            self.update += 1
            row: dict[str, Any] = {
                "update": self.update,
                "wall": round(time.time() - start, 1),
                "rollout_s": round(t1 - t0, 1),
                "learn_s": round(time.time() - t1, 1),
            }
            row |= {k: round(v, 5) for k, v in stats.items()}
            row |= self._summarise_matches()
            row["pool"] = [u for u, _ in self.pool]
            log.write(json.dumps(row) + "\n")
            log.flush()
            if self.update % self.cfg.snapshot_every == 0:
                self._snapshot()
            if self.update % self.cfg.checkpoint_every == 0:
                self.checkpoint()
        self.checkpoint()
        log.close()

    def _summarise_matches(self) -> dict[str, float]:
        s = self.match_stats
        out: dict[str, float] = {"matches": s["matches"]}
        for name in (*OPP_NAMES, *TRAIN_MISSIONS, *STATION_SIDES):
            if s[f"n_{name}"]:
                out[f"win_{name}"] = round(s[f"won_{name}"] / s[f"n_{name}"], 3)
                out[f"n_{name}"] = s[f"n_{name}"]
        if s["decisions"]:
            out["launch_per_decision"] = round(s["launch_orders"] / s["decisions"], 3)
            out["order_change_rate"] = round(s["order_changes"] / s["order_heads"], 3)
            for name in ("none", "attack", "defend", "goto"):
                out[f"order_{name}"] = round(s[f"order_{name}"] / s["order_heads"], 3)
        if s["ship_decisions"]:
            # Mean seconds a strike craft goes between changes of its order (absent if
            # no order changed), and the share of its time it has an order.
            if s["ships_changed"]:
                out["order_seconds"] = round(
                    self.decision_s * s["ship_decisions"] / s["ships_changed"], 2
                )
            out["ordered_share"] = round(s["ships_ordered"] / s["ship_decisions"], 3)
        return out


def _deadline(spec: str) -> float:
    out = subprocess.run(
        ["date", "-d", spec, "+%s"], capture_output=True, text=True, check=True
    )
    return float(out.stdout.strip())


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--run-dir", type=Path, required=True)
    p.add_argument("--deadline", required=True, help="a `date -d` string")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--set", action="append", default=[], help="key=value (JSON value)")
    p.add_argument("--smoke", action="store_true", help="tiny sizes")
    args = p.parse_args(argv)
    cfg_path = args.run_dir / "config.json"
    if args.resume:
        base = json.loads(cfg_path.read_text())
    else:
        base = {}
    if args.smoke:
        base |= {
            "n_envs": 8,
            "decisions_per_update": 512,
            "minibatch": 128,
            "snapshot_every": 2,
            "checkpoint_every": 2,
        }
    known = {f.name for f in fields(TrainConfig)}
    for item in args.set:
        key, _, value = item.partition("=")
        if key not in known:
            raise SystemExit(f"unknown setting {key!r}")
        base[key] = json.loads(value)
    for key in ("opponent_shares", "mission_weights", "forbid_orders"):
        if key in base:
            base[key] = tuple(base[key])
    cfg = TrainConfig(**base)
    args.run_dir.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps(asdict(cfg), indent=1) + "\n")
    trainer = Trainer(args.run_dir, cfg, resume=args.resume)
    print(
        f"commander {n_params(trainer.actor)} params, critic "
        f"{n_params(trainer.critic)}; {cfg.n_envs} envs; pilots {trainer.stable.ids}",
        flush=True,
    )
    trainer.train(_deadline(args.deadline))
    print(f"done at update {trainer.update}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
