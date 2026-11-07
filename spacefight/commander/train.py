"""PPO for the commander (docs/COMMANDER.md "Training").

One step is one decision of a ``learned`` team (every 30 ticks). Pilots are frozen and
drawn per ship from the live list. Each match draws the learner's team, the enemy
commander (scripted, random, the learner itself, or one of its snapshots, weighted toward
the ones it beats least), the mission (uniform, as the live page rotates) and a live
roster.

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
    CommanderInputs,
    check_sim_layout,
)
from spacefight.commander.pilots import LIVE_PILOTS, PilotStable, live_pilot_checkpoints
from spacefight.commander.policy import (
    CommanderActor,
    CommanderCritic,
    act,
    evaluate,
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
    PilotsDistribution,
    Roster,
    make_sampler,
)
from spacefight.env.rust_env import RustVecEnv
from spacefight.eval.missions import default_rosters

REPO_ROOT = Path(__file__).resolve().parents[2]
ASSETS = REPO_ROOT / "assets"
LEARNED: Final = "learned"
MISSIONS: Final = (DEATHMATCH, CARRIER_BATTLE, CONVOY_ESCORT)
WINNER_DRAW: Final = -1

# Enemy commander kinds.
OPP_SCRIPTED, OPP_RANDOM, OPP_SELF, OPP_SNAPSHOT = range(4)
OPP_NAMES: Final = ("scripted", "random", "self", "snapshot")
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
    ent_coef: float = 0.01
    vf_coef: float = 0.5
    max_grad_norm: float = 0.5
    gamma: float = 0.99
    lam: float = 0.95
    shaping: float = 0.5
    # Enemy commander shares: scripted, random, self, snapshots (snapshots' share goes to
    # self until the first snapshot exists).
    opponent_shares: tuple[float, float, float, float] = (0.35, 0.1, 0.3, 0.25)
    pfsp_power: float = 1.0
    pfsp_floor: float = 0.1
    snapshot_every: int = 20
    max_snapshots: int = 10
    checkpoint_every: int = 10
    mission_weights: tuple[float, float, float] = (1.0, 1.0, 1.0)
    live_pilots: str = str(LIVE_PILOTS)
    max_updates: int = 1_000_000

    def __post_init__(self) -> None:
        if len(self.opponent_shares) != 4 or min(self.opponent_shares) < 0:
            raise ValueError("opponent_shares needs four non-negative shares")
        if self.decisions_per_update < self.minibatch:
            raise ValueError("decisions_per_update must be at least one minibatch")


@dataclass
class Assignment:
    """Who commands what in one match."""

    learner_team: int
    opponent: int  # OPP_*
    snapshot: int = -1  # pool index for OPP_SNAPSHOT
    mission: str = DEATHMATCH
    roster: str = ""

    def controllers(self) -> tuple[int, int]:
        enemy = {
            OPP_SCRIPTED: NOT_LEARNED,
            OPP_RANDOM: NOT_LEARNED,
            OPP_SELF: LEARNER,
            OPP_SNAPSHOT: 2 + self.snapshot,
        }[self.opponent]
        c = [enemy, enemy]
        c[self.learner_team] = LEARNER
        return c[0], c[1]

    def modes(self) -> tuple[str, str]:
        enemy = {OPP_SCRIPTED: SCRIPTED, OPP_RANDOM: RANDOM}.get(self.opponent, LEARNED)
        m = [enemy, enemy]
        m[self.learner_team] = LEARNED
        return m[0], m[1]


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
        check_sim_layout(rlf_sim.commander_io())
        self.actor = CommanderActor()
        pilots = live_pilot_checkpoints(Path(cfg.live_pilots))
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
        self.mission_rosters = {m: default_rosters(m) for m in MISSIONS[1:]}
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
            pilots, cfg.n_envs, self.env.n_ships, cfg.seed + 11, ASSETS
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
        opp = int(self.rng.choice(4, p=shares / shares.sum()))
        snap = -1
        if opp == OPP_SNAPSHOT:
            rates = np.array([self.results.rate(self._snap_name(k)) for k in range(len(self.pool))])
            w = (1.0 - rates) ** cfg.pfsp_power + cfg.pfsp_floor
            snap = int(self.rng.choice(len(self.pool), p=w / w.sum()))
        mw = np.asarray(cfg.mission_weights, dtype=np.float64)
        mission = MISSIONS[int(self.rng.choice(3, p=mw / mw.sum()))]
        return Assignment(
            learner_team=int(self.rng.integers(0, 2)),
            opponent=opp,
            snapshot=snap,
            mission=mission,
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
        return Roster(teams, a.mission, a.modes())

    def _queue(self, i: int, a: Assignment, store: bool = True) -> None:
        roster = self._roster(a)
        self.env.set_next_roster(
            i,
            roster,
            time_limit_s=float(rlf_sim.mission_time_limit_s(a.mission)),
            hide_orders=(False, False),
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
                self.env.raw.submit_commander_actions(
                    team, rows.astype(np.int64), actions.numpy().astype(np.int32)
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
                        prev.reward = self.cfg.gamma * phi - prev.phi
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
                    )
                self._behaviour(actions)

    def _behaviour(self, actions: torch.Tensor) -> None:
        a = actions.numpy()
        s = self.match_stats
        s["decisions"] += a.shape[0]
        s["launch_orders"] += float((a[:, LAUNCH] == 1).sum())
        order = a[:, ORDER]
        s["order_heads"] += order.size
        s["order_changes"] += float((order != ORDER_KEEP).sum())
        for k, name in enumerate(("keep", "none", "attack", "defend", "goto")):
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
                    prev.reward = outcome - prev.phi
                    prev.done = True
                    self.completed.append(prev)
                if team == a.learner_team and a.opponent != OPP_SELF:
                    score = 0.5 if w == WINNER_DRAW else float(w == team)
                    self.results.record(self._opp_name(a), score)
                    self.match_stats[f"n_{OPP_NAMES[a.opponent]}"] += 1
                    self.match_stats[f"won_{OPP_NAMES[a.opponent]}"] += score
                    self.match_stats[f"n_{a.mission}"] += 1
                    self.match_stats[f"won_{a.mission}"] += score
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
        state = torch.load(self.run_dir / "state.pt", map_location="cpu", weights_only=False)
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
        for name in (*OPP_NAMES, *MISSIONS):
            if s[f"n_{name}"]:
                out[f"win_{name}"] = round(s[f"won_{name}"] / s[f"n_{name}"], 3)
                out[f"n_{name}"] = s[f"n_{name}"]
        if s["decisions"]:
            out["launch_per_decision"] = round(s["launch_orders"] / s["decisions"], 3)
            out["order_change_rate"] = round(s["order_changes"] / s["order_heads"], 3)
            for name in ("none", "attack", "defend", "goto"):
                out[f"order_{name}"] = round(s[f"order_{name}"] / s["order_heads"], 3)
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
        base |= {"n_envs": 8, "decisions_per_update": 512, "minibatch": 128,
                 "snapshot_every": 2, "checkpoint_every": 2}
    known = {f.name for f in fields(TrainConfig)}
    for item in args.set:
        key, _, value = item.partition("=")
        if key not in known:
            raise SystemExit(f"unknown setting {key!r}")
        base[key] = json.loads(value)
    for key in ("opponent_shares", "mission_weights"):
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
