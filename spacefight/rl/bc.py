"""Behaviour cloning of the Rust scripted pilot (learnability spike, phase A).

Spec: ``lab/runs/2026-10-28-learnability-spike/plan.md`` §4.1, acceptance §8 row C.

Three steps:

- ``collect``: the script flies both sides; every present ship's scripted action is
  the label. The executed action equals the label except that, per ship per tick
  with probability ``dart_p``, one random *valid* head is replaced by a uniform
  draw (DART-style noise, so the data covers recovery states). Rows with
  ``act_mask`` false (no effect) are dropped. 5 % of envs (by index) are held out.
- ``train``: masked per-head cross-entropy, mean over each row's valid heads, Adam
  with cosine decay. Only the actor is trained; the critic is freshly initialised
  (PPO warms it up, plan §4.2).
- ``bc_eval``: held-out agreement per head group and fire precision / recall.
- ``dagger``: DAgger against compounding error. Round 0 is the ``collect`` dataset;
  each later round ``collect_on_policy`` lets the current actor fly one side
  against the script, labels the actor's own states with ``scripted_actions()``,
  aggregates them with every earlier round (``AggregateDataset``) and retrains.

Labels are only meaningful where ``HeadMasks.head_valid()`` is true; masked slots
of ``scripted_actions()`` hold arbitrary filler, so every comparison is restricted
to valid heads.
"""

from __future__ import annotations

import json
import math
import shutil
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path

import numpy as np
import torch
from numpy.typing import NDArray

from spacefight.env.rust_env import SIM_VERSION, RustVecEnv
from spacefight.eval.controllers import Policy, Scripted
from spacefight.eval.duel import DuelResult, evaluate
from spacefight.rl.spike_policy import (
    ACTION_HIGHS,
    ACTION_WIDTH,
    FIRE_NONE,
    HEAD_GROUPS,
    OBS_DIM,
    THROTTLE_HOLD,
    HeadMasks,
    SpikeActor,
    SpikeCritic,
    act_numpy,
    load_policy,
    save_policy,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ASSETS = REPO_ROOT / "assets"
FIGHTER_DUEL: tuple[tuple[str, ...], ...] = (("fighter",), ("fighter",))
FIRE_SHOOT = 1

CHECKPOINT_NAME = "bc.pt"
EVAL_NAME = "bc_eval.json"
DATASET_NAME = "bc_dataset.npz"
OBS_DTYPES = ("float16", "float32")

_HEAD_HIGHS = np.asarray(ACTION_HIGHS, dtype=np.int64)
_EVAL_BATCH = 16384


@dataclass(frozen=True)
class CollectStats:
    """What ``collect`` actually did.

    Attributes:
        env_steps: Batched env steps taken.
        rows: Rows kept (``act_mask`` true).
        holdout_rows: Kept rows from held-out envs.
        noise_rate: Share of kept rows whose executed action had a head replaced.
        changed_rate: Share of kept rows whose executed action differs from the
            label (a uniform draw can repeat the label).
        fire_rate: Share of kept rows with fire label 1 on the first gun.
        wall_s: Collection wall time in seconds.
    """

    env_steps: int
    rows: int
    holdout_rows: int
    noise_rate: float
    changed_rate: float
    fire_rate: float
    wall_s: float


@dataclass(frozen=True)
class BCDataset:
    """Kept rows of a ``collect`` run (R rows).

    Attributes:
        obs: [R, 385] observations (float16 by default).
        labels: [R, 21] int8 scripted actions (only valid heads meaningful).
        executed: [R, 21] int8 actions actually sent to the env.
        noised: [R] bool, True where a head was replaced by noise.
        thruster: [R, 8] bool slot masks.
        turret: [R, 6] bool slot masks.
        fixed_turret: [R, 6] bool slot masks.
        env_index: [R] int32 env the row came from.
        ship: [R] int8 ship slot.
        step: [R] int32 batched env step the row was observed on.
        holdout: [R] bool, True for rows of held-out envs.
        stats: Collection statistics.
    """

    obs: NDArray[np.floating]
    labels: NDArray[np.int8]
    executed: NDArray[np.int8]
    noised: NDArray[np.bool_]
    thruster: NDArray[np.bool_]
    turret: NDArray[np.bool_]
    fixed_turret: NDArray[np.bool_]
    env_index: NDArray[np.int32]
    ship: NDArray[np.int8]
    step: NDArray[np.int32]
    holdout: NDArray[np.bool_]
    stats: CollectStats

    @property
    def n_rows(self) -> int:
        """Number of rows R."""
        return int(self.labels.shape[0])

    def masks(self, rows: NDArray[np.bool_] | NDArray[np.int64]) -> HeadMasks:
        """Head masks of the selected rows."""
        return HeadMasks.from_numpy(
            self.thruster[rows], self.turret[rows], self.fixed_turret[rows]
        )

    def save(self, path: Path) -> None:
        """Write the arrays and stats to an uncompressed ``.npz``."""
        path.parent.mkdir(parents=True, exist_ok=True)
        arrays = {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "stats"
        }
        np.savez(path, stats=json.dumps(asdict(self.stats)), **arrays)


def valid_heads(
    thruster: NDArray[np.bool_],
    turret: NDArray[np.bool_],
    fixed_turret: NDArray[np.bool_],
) -> NDArray[np.bool_]:
    """[..., 21] bool: meaningful heads (NumPy twin of ``HeadMasks.head_valid``)."""
    slew = turret & ~fixed_turret
    power = np.ones(thruster.shape[:-1] + (1,), dtype=np.bool_)
    return np.concatenate([thruster, slew, turret, power], axis=-1)


def holdout_envs(n_envs: int, holdout_frac: float) -> NDArray[np.bool_]:
    """[N] bool: the last ``ceil(frac · N)`` envs are held out (at least one)."""
    if not 0.0 < holdout_frac < 1.0:
        raise ValueError(f"holdout_frac must be in (0, 1), got {holdout_frac}")
    n_held = max(1, math.ceil(holdout_frac * n_envs))
    if n_held >= n_envs:
        raise ValueError(f"holdout of {n_held} envs leaves none of {n_envs} to train")
    held = np.zeros(n_envs, dtype=np.bool_)
    held[n_envs - n_held :] = True
    return held


def apply_dart_noise(
    labels: NDArray[np.int8],
    head_valid: NDArray[np.bool_],
    dart_p: float,
    rng: np.random.Generator,
) -> tuple[NDArray[np.int8], NDArray[np.bool_]]:
    """Replace one random valid head per selected ship by a uniform draw.

    Args:
        labels: [M, 21] scripted actions (not modified).
        head_valid: [M, 21] valid heads; every row needs at least one.
        dart_p: Probability that a ship's action is perturbed this tick.
        rng: Random source.

    Returns:
        ``(executed [M, 21] int8, noised [M] bool)``.
    """
    if not 0.0 <= dart_p <= 1.0:
        raise ValueError(f"dart_p must be in [0, 1], got {dart_p}")
    n_valid = head_valid.sum(-1)
    if np.any(n_valid == 0):
        raise ValueError("every row needs at least one valid head")
    executed = labels.copy()
    noised = np.less(rng.random(labels.shape[0]), dart_p)
    rows = np.flatnonzero(noised)
    # Pick the k-th valid head of each row, k uniform in [0, n_valid).
    kth = (rng.random(rows.size) * n_valid[rows]).astype(np.int64)
    rank = np.cumsum(head_valid[rows], axis=-1) - 1
    cols = np.argmax(head_valid[rows] & (rank == kth[:, None]), axis=-1)
    draws = (rng.random(rows.size) * (_HEAD_HIGHS[cols] + 1)).astype(np.int8)
    executed[rows, cols] = draws
    return executed, noised


def collect(
    n_rows: int,
    n_envs: int = 256,
    n_threads: int = 0,
    seed: int = 0,
    dart_p: float = 0.15,
    holdout_frac: float = 0.05,
    reaction_ticks: int = 2,
    obs_dtype: str = "float16",
    assets_dir: Path = DEFAULT_ASSETS,
) -> BCDataset:
    """Collect ``n_rows`` scripted-vs-scripted rows with DART noise.

    Args:
        n_rows: Rows to keep (``act_mask`` true); the last step is truncated.
        n_envs: Parallel matches.
        n_threads: Sim threads (0 = rayon default).
        seed: Env seed; the noise RNG is seeded from it too.
        dart_p: Per ship per tick probability of perturbing one valid head.
        holdout_frac: Share of envs (by index) held out for evaluation.
        reaction_ticks: Sim reaction delay.
        obs_dtype: Storage dtype of the observations, one of OBS_DTYPES.
        assets_dir: Asset directory for the sim.

    Returns:
        The dataset with its stats.
    """
    if n_rows <= 0:
        raise ValueError(f"n_rows must be positive, got {n_rows}")
    if obs_dtype not in OBS_DTYPES:
        raise ValueError(f"obs_dtype must be one of {OBS_DTYPES}, got {obs_dtype}")
    start = time.perf_counter()
    env = RustVecEnv(
        assets_dir,
        n_envs,
        [list(team) for team in FIGHTER_DUEL],
        seed,
        n_threads=n_threads,
        reaction_ticks=reaction_ticks,
    )
    rng = np.random.default_rng(seed)
    thruster = env.thruster_mask.copy()
    turret = env.turret_mask.copy()
    fixed = env.fixed_turret.copy()
    head_valid = valid_heads(thruster, turret, fixed).reshape(-1, ACTION_WIDTH)
    held_env = holdout_envs(n_envs, holdout_frac)
    env_of_slot = np.repeat(np.arange(n_envs, dtype=np.int32), env.n_ships)
    ship_of_slot = np.tile(np.arange(env.n_ships, dtype=np.int8), n_envs)
    flat_thruster = thruster.reshape(-1, thruster.shape[-1])
    flat_turret = turret.reshape(-1, turret.shape[-1])
    flat_fixed = fixed.reshape(-1, fixed.shape[-1])

    out = _empty_buffers(n_rows, obs_dtype)
    filled = 0
    step = 0
    while filled < n_rows:
        labels = env.scripted_actions().reshape(-1, ACTION_WIDTH).copy()
        executed, noised = apply_dart_noise(labels, head_valid, dart_p, rng)
        keep = np.flatnonzero(env.act_mask.reshape(-1))[: n_rows - filled]
        rows = slice(filled, filled + keep.size)
        out["obs"][rows] = env.obs.reshape(-1, OBS_DIM)[keep]
        out["labels"][rows] = labels[keep]
        out["executed"][rows] = executed[keep]
        out["noised"][rows] = noised[keep]
        out["thruster"][rows] = flat_thruster[keep]
        out["turret"][rows] = flat_turret[keep]
        out["fixed_turret"][rows] = flat_fixed[keep]
        out["env_index"][rows] = env_of_slot[keep]
        out["ship"][rows] = ship_of_slot[keep]
        out["step"][rows] = step
        filled += keep.size
        env.step(executed.reshape(env.actions.shape))
        step += 1

    holdout = held_env[out["env_index"]]
    changed = np.any(
        (out["executed"] != out["labels"])
        & valid_heads(out["thruster"], out["turret"], out["fixed_turret"]),
        axis=-1,
    )
    stats = CollectStats(
        env_steps=step,
        rows=n_rows,
        holdout_rows=int(holdout.sum()),
        noise_rate=float(out["noised"].mean()),
        changed_rate=float(changed.mean()),
        fire_rate=float((out["labels"][:, HEAD_GROUPS["fire"].start] == 1).mean()),
        wall_s=time.perf_counter() - start,
    )
    return BCDataset(holdout=holdout, stats=stats, **out)


def _empty_buffers(n_rows: int, obs_dtype: str) -> dict[str, np.ndarray]:
    return {
        "obs": np.empty((n_rows, OBS_DIM), dtype=obs_dtype),
        "labels": np.empty((n_rows, ACTION_WIDTH), dtype=np.int8),
        "executed": np.empty((n_rows, ACTION_WIDTH), dtype=np.int8),
        "noised": np.empty(n_rows, dtype=np.bool_),
        "thruster": np.empty((n_rows, 8), dtype=np.bool_),
        "turret": np.empty((n_rows, 6), dtype=np.bool_),
        "fixed_turret": np.empty((n_rows, 6), dtype=np.bool_),
        "env_index": np.empty(n_rows, dtype=np.int32),
        "ship": np.empty(n_rows, dtype=np.int8),
        "step": np.empty(n_rows, dtype=np.int32),
    }


@dataclass(frozen=True)
class TrainConfig:
    """BC optimisation settings (plan §4.1 defaults).

    Attributes:
        epochs: Passes over the training rows.
        batch_size: Rows per minibatch.
        lr: Initial Adam learning rate.
        lr_final: Learning rate at the end of the cosine decay.
        label_smoothing: Target smoothing ε per head.
        fire_pos_weight: Loss weight of fire heads whose label is 1 (§7 mitigation
            for a collapsed fire head; 1.0 = off).
        throttle_change_weight: Loss weight of throttle heads whose label is
            increase/decrease (§7 mitigation for a "hold" collapse; 1.0 = off).
        seed: Torch seed (init and shuffling).
    """

    epochs: int = 8
    batch_size: int = 4096
    lr: float = 1e-3
    lr_final: float = 1e-4
    label_smoothing: float = 0.02
    fire_pos_weight: float = 1.0
    throttle_change_weight: float = 1.0
    seed: int = 0


@dataclass
class TrainLog:
    """Per-epoch training record."""

    epoch_loss: list[float] = field(default_factory=list)
    steps: int = 0
    wall_s: float = 0.0


def head_weights(
    labels: torch.Tensor,
    fire_pos_weight: float,
    throttle_change_weight: float,
) -> torch.Tensor:
    """[B, 21] float loss weight per head from the label values."""
    weights = torch.ones(labels.shape, dtype=torch.float32)
    throttle = HEAD_GROUPS["throttle"]
    fire = HEAD_GROUPS["fire"]
    change = labels[:, throttle] != THROTTLE_HOLD
    weights[:, throttle] = torch.where(change, throttle_change_weight, 1.0)
    weights[:, fire] = torch.where(labels[:, fire] == FIRE_SHOOT, fire_pos_weight, 1.0)
    return weights


def bc_loss(
    actor: SpikeActor,
    obs: torch.Tensor,
    masks: HeadMasks,
    labels: torch.Tensor,
    config: TrainConfig,
) -> torch.Tensor:
    """Mean over rows of the (weighted) per-head CE averaged over valid heads."""
    ce = actor.head_cross_entropy(obs, masks, labels, config.label_smoothing)
    weights = head_weights(
        labels, config.fire_pos_weight, config.throttle_change_weight
    )
    n_valid = masks.head_valid().sum(-1).clamp(min=1)
    return ((ce * weights).sum(-1) / n_valid).mean()


def train(
    dataset: BCDataset, config: TrainConfig, actor: SpikeActor | None = None
) -> tuple[SpikeActor, TrainLog]:
    """Fit an actor to the training (non-held-out) rows of ``dataset``.

    Args:
        dataset: Output of ``collect``.
        config: Optimisation settings.
        actor: Actor to train in place; a fresh one (seeded) if omitted.

    Returns:
        The trained actor and the training log.
    """
    torch.manual_seed(config.seed)
    if actor is None:
        actor = SpikeActor()
    train_rows = np.flatnonzero(~dataset.holdout)
    if train_rows.size == 0:
        raise ValueError("dataset has no training rows")
    steps_per_epoch = math.ceil(train_rows.size / config.batch_size)
    total_steps = steps_per_epoch * config.epochs
    optimiser = torch.optim.Adam(actor.parameters(), lr=config.lr)
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimiser, T_max=total_steps, eta_min=config.lr_final
    )
    masks = dataset.masks(train_rows)
    labels = torch.from_numpy(dataset.labels[train_rows].astype(np.int64))
    generator = torch.Generator().manual_seed(config.seed)
    log = TrainLog()
    start = time.perf_counter()
    actor.train()
    for _ in range(config.epochs):
        order = torch.randperm(train_rows.size, generator=generator)
        total = 0.0
        for batch in order.split(config.batch_size):
            obs = torch.from_numpy(
                dataset.obs[train_rows[batch.numpy()]].astype(np.float32)
            )
            loss = bc_loss(actor, obs, masks.index(batch), labels[batch], config)
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
            schedule.step()
            total += float(loss.detach()) * batch.numel()
            log.steps += 1
        log.epoch_loss.append(total / train_rows.size)
    actor.eval()
    log.wall_s = time.perf_counter() - start
    return actor, log


def predict(actor: SpikeActor, dataset: BCDataset, rows: np.ndarray) -> np.ndarray:
    """[len(rows), 21] int8 argmax actions of ``actor`` on the selected rows."""
    preds = np.empty((rows.size, ACTION_WIDTH), dtype=np.int8)
    for begin in range(0, rows.size, _EVAL_BATCH):
        chunk = rows[begin : begin + _EVAL_BATCH]
        preds[begin : begin + chunk.size] = act_numpy(
            actor,
            dataset.obs[chunk].astype(np.float32),
            dataset.masks(chunk),
            deterministic=True,
        )
    return preds


def bc_eval(actor: SpikeActor, dataset: BCDataset) -> dict[str, object]:
    """Held-out agreement per head group, fire precision / recall, hold shares.

    Only valid heads are compared. A group with no valid head (slew on the
    fighter's fixed gun) reports ``agreement: None`` and ``heads: 0``.
    """
    rows = np.flatnonzero(dataset.holdout)
    if rows.size == 0:
        raise ValueError("dataset has no held-out rows")
    preds = predict(actor, dataset, rows)
    labels = dataset.labels[rows]
    valid = valid_heads(
        dataset.thruster[rows], dataset.turret[rows], dataset.fixed_turret[rows]
    )
    agree = preds == labels
    groups: dict[str, dict[str, object]] = {}
    for name, cols in HEAD_GROUPS.items():
        group_valid = valid[:, cols]
        count = int(group_valid.sum())
        groups[name] = {
            "heads": int(group_valid[0].sum()),
            "samples": count,
            "agreement": (
                float(agree[:, cols][group_valid].mean()) if count > 0 else None
            ),
        }
    throttle = HEAD_GROUPS["throttle"]
    thr_valid = valid[:, throttle]
    thr_labels = labels[:, throttle][thr_valid]
    thr_preds = preds[:, throttle][thr_valid]
    change = thr_labels != THROTTLE_HOLD
    groups["throttle"].update(
        {
            "label_hold_share": float((~change).mean()),
            "pred_hold_share": float((thr_preds == THROTTLE_HOLD).mean()),
            "agreement_on_change_labels": (
                float((thr_preds[change] == thr_labels[change]).mean())
                if change.any()
                else None
            ),
        }
    )
    fire = HEAD_GROUPS["fire"]
    fire_valid = valid[:, fire]
    fire_labels = labels[:, fire][fire_valid] == FIRE_SHOOT
    fire_preds = preds[:, fire][fire_valid] == FIRE_SHOOT
    true_pos = int((fire_labels & fire_preds).sum())
    groups["fire"].update(
        {
            "base_rate": float(fire_labels.mean()),
            "pred_rate": float(fire_preds.mean()),
            "precision": (
                true_pos / int(fire_preds.sum()) if fire_preds.any() else None
            ),
            "recall": true_pos / int(fire_labels.sum()) if fire_labels.any() else None,
        }
    )
    all_agree = np.where(valid, agree, True).all(-1)
    return {
        "holdout_rows": int(rows.size),
        "groups": groups,
        "exact_row_agreement": float(all_agree.mean()),
    }


@dataclass(frozen=True)
class BCRunResult:
    """Paths and numbers of ``run``."""

    checkpoint: Path
    eval_path: Path
    eval: dict[str, object]


def run(
    out_dir: Path,
    n_rows: int,
    seed: int,
    n_threads: int,
    n_envs: int = 256,
    dart_p: float = 0.15,
    obs_dtype: str = "float16",
    config: TrainConfig | None = None,
    save_dataset: bool = False,
) -> BCRunResult:
    """Collect, train, evaluate; write ``bc.pt`` and ``bc_eval.json`` in ``out_dir``.

    The checkpoint holds the trained actor and a freshly initialised critic.
    """
    config = config or TrainConfig(seed=seed)
    if n_threads > 0:
        torch.set_num_threads(n_threads)
    dataset = collect(
        n_rows,
        n_envs=n_envs,
        n_threads=n_threads,
        seed=seed,
        dart_p=dart_p,
        obs_dtype=obs_dtype,
    )
    if save_dataset:
        dataset.save(out_dir / DATASET_NAME)
    actor, log = train(dataset, config)
    eval_start = time.perf_counter()
    result = bc_eval(actor, dataset)
    eval_s = time.perf_counter() - eval_start
    report: dict[str, object] = {
        **result,
        "collect": asdict(dataset.stats),
        "train": {
            "config": asdict(config),
            "epoch_loss": log.epoch_loss,
            "steps": log.steps,
            "wall_s": log.wall_s,
        },
        "eval_wall_s": eval_s,
        "setup": {
            "n_rows": n_rows,
            "n_envs": n_envs,
            "seed": seed,
            "n_threads": n_threads,
            "dart_p": dart_p,
            "obs_dtype": obs_dtype,
            "fleets": [list(team) for team in FIGHTER_DUEL],
            "reaction_ticks": 2,
        },
    }
    torch.manual_seed(config.seed + 1)
    critic = SpikeCritic()
    checkpoint = out_dir / CHECKPOINT_NAME
    save_policy(
        checkpoint,
        actor,
        critic,
        {
            "source": "bc",
            "sim_version": SIM_VERSION,
            "critic": "fresh",
            "bc_eval": json.loads(json.dumps(report)),
        },
    )
    eval_path = out_dir / EVAL_NAME
    eval_path.write_text(json.dumps(report, indent=2) + "\n")
    return BCRunResult(checkpoint=checkpoint, eval_path=eval_path, eval=report)


# ------------------------------------------------------------------------ DAgger


def collect_on_policy(
    actor: SpikeActor,
    n_rows: int,
    n_envs: int = 256,
    n_threads: int = 0,
    seed: int = 1,
    beta: float = 0.0,
    sample: bool = True,
    holdout_frac: float = 0.05,
    reaction_ticks: int = 2,
    obs_dtype: str = "float16",
    assets_dir: Path = DEFAULT_ASSETS,
) -> BCDataset:
    """Collect ``n_rows`` rows of ``actor`` flying against the script (DAgger).

    Env ``i`` puts the learner on team ``i % 2`` (the eval's side split); the other
    team flies the script. Each step the script's actions for every ship are
    fetched *before* the learner's actions are written, so the learner's rows are
    labelled with what the script would do in the learner's own states. With
    probability ``beta`` per learner ship-tick the script's action is executed
    instead of the actor's (beta-DAgger). Only learner rows with ``act_mask`` true
    are kept; storage and holdout follow ``collect``.

    The returned stats reuse ``CollectStats``: ``noise_rate`` is the share of rows
    where the script's action was executed (``noised`` marks them) and
    ``changed_rate`` the share whose executed action differs from the label on a
    valid head (the actor's on-policy disagreement with the script).

    Args:
        actor: The learner; sampled with torch's global RNG, seeded from ``seed``.
        n_rows: Rows to keep; the last step is truncated.
        n_envs: Parallel matches (at least 2, so both sides are covered).
        n_threads: Sim threads (0 = rayon default).
        seed: Env seed; the mixing RNG and torch are seeded from it too.
        beta: Per learner ship-tick probability of executing the script's action.
        sample: Sample the actor's heads (``False``: argmax).
        holdout_frac: Share of envs (by index) held out for evaluation.
        reaction_ticks: Sim reaction delay.
        obs_dtype: Storage dtype of the observations, one of OBS_DTYPES.
        assets_dir: Asset directory for the sim.

    Returns:
        The dataset with its stats.
    """
    if n_rows <= 0:
        raise ValueError(f"n_rows must be positive, got {n_rows}")
    if n_envs < 2:
        raise ValueError(f"n_envs must be >= 2 to alternate sides, got {n_envs}")
    if not 0.0 <= beta <= 1.0:
        raise ValueError(f"beta must be in [0, 1], got {beta}")
    if obs_dtype not in OBS_DTYPES:
        raise ValueError(f"obs_dtype must be one of {OBS_DTYPES}, got {obs_dtype}")
    start = time.perf_counter()
    env = RustVecEnv(
        assets_dir,
        n_envs,
        [list(team) for team in FIGHTER_DUEL],
        seed,
        n_threads=n_threads,
        reaction_ticks=reaction_ticks,
    )
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    learner_team = np.arange(n_envs) % 2
    learner_slot = (env.team == learner_team[:, None]).reshape(-1)
    held_env = holdout_envs(n_envs, holdout_frac)
    env_of_slot = np.repeat(np.arange(n_envs, dtype=np.int32), env.n_ships)
    ship_of_slot = np.tile(np.arange(env.n_ships, dtype=np.int8), n_envs)
    flat_thruster = env.thruster_mask.copy().reshape(-1, 8)
    flat_turret = env.turret_mask.copy().reshape(-1, 6)
    flat_fixed = env.fixed_turret.copy().reshape(-1, 6)

    out = _empty_buffers(n_rows, obs_dtype)
    filled = 0
    step = 0
    actor.eval()
    while filled < n_rows:
        labels = env.scripted_actions().reshape(-1, ACTION_WIDTH).copy()
        learn = np.flatnonzero(learner_slot & env.act_mask.reshape(-1))
        obs = env.obs.reshape(-1, OBS_DIM)[learn]
        policy = act_numpy(
            actor,
            obs,
            HeadMasks.from_numpy(
                flat_thruster[learn], flat_turret[learn], flat_fixed[learn]
            ),
            deterministic=not sample,
        )
        scripted = np.less(rng.random(learn.size), beta)
        executed = labels.copy()
        executed[learn[~scripted]] = policy[~scripted]
        n_keep = min(learn.size, n_rows - filled)
        keep = learn[:n_keep]
        rows = slice(filled, filled + n_keep)
        out["obs"][rows] = obs[:n_keep]
        out["labels"][rows] = labels[keep]
        out["executed"][rows] = executed[keep]
        out["noised"][rows] = scripted[:n_keep]
        out["thruster"][rows] = flat_thruster[keep]
        out["turret"][rows] = flat_turret[keep]
        out["fixed_turret"][rows] = flat_fixed[keep]
        out["env_index"][rows] = env_of_slot[keep]
        out["ship"][rows] = ship_of_slot[keep]
        out["step"][rows] = step
        filled += n_keep
        env.step(executed.reshape(env.actions.shape))
        step += 1

    holdout = held_env[out["env_index"]]
    return BCDataset(holdout=holdout, stats=_stats(out, holdout, step, start), **out)


def _stats(
    out: dict[str, np.ndarray],
    holdout: NDArray[np.bool_],
    env_steps: int,
    start: float,
) -> CollectStats:
    changed = np.any(
        (out["executed"] != out["labels"])
        & valid_heads(out["thruster"], out["turret"], out["fixed_turret"]),
        axis=-1,
    )
    return CollectStats(
        env_steps=env_steps,
        rows=int(out["labels"].shape[0]),
        holdout_rows=int(holdout.sum()),
        noise_rate=float(out["noised"].mean()),
        changed_rate=float(changed.mean()),
        fire_rate=float((out["labels"][:, HEAD_GROUPS["fire"].start] == 1).mean()),
        wall_s=time.perf_counter() - start,
    )


_ROW_FIELDS = (
    "obs",
    "labels",
    "executed",
    "noised",
    "thruster",
    "turret",
    "fixed_turret",
    "env_index",
    "ship",
    "step",
    "holdout",
)


class AggregateDataset:
    """Preallocated row store that DAgger rounds append to (no re-concatenation).

    ``view()`` and ``part()`` return ``BCDataset`` objects whose arrays are views
    into the store; appends never move earlier rows, so the views stay valid.

    Args:
        capacity: Maximum rows over all appends.
        obs_dtype: Storage dtype of the observations, one of OBS_DTYPES.
    """

    def __init__(self, capacity: int, obs_dtype: str = "float16") -> None:
        if capacity <= 0:
            raise ValueError(f"capacity must be positive, got {capacity}")
        if obs_dtype not in OBS_DTYPES:
            raise ValueError(f"obs_dtype must be one of {OBS_DTYPES}, got {obs_dtype}")
        self.capacity = capacity
        self._arrays = _empty_buffers(capacity, obs_dtype)
        self._arrays["holdout"] = np.empty(capacity, dtype=np.bool_)
        self._parts: list[tuple[int, int, CollectStats]] = []
        self.size = 0

    @property
    def n_parts(self) -> int:
        """Number of appended datasets."""
        return len(self._parts)

    def append(self, dataset: BCDataset) -> int:
        """Copy ``dataset``'s rows in; returns the new part's index.

        Raises:
            ValueError: The rows do not fit, or the obs dtype differs.
        """
        if self.size + dataset.n_rows > self.capacity:
            raise ValueError(
                f"{dataset.n_rows} rows do not fit: {self.size} of "
                f"{self.capacity} used"
            )
        if dataset.obs.dtype != self._arrays["obs"].dtype:
            raise ValueError(
                f"obs dtype {dataset.obs.dtype} != store {self._arrays['obs'].dtype}"
            )
        rows = slice(self.size, self.size + dataset.n_rows)
        for name in _ROW_FIELDS:
            self._arrays[name][rows] = getattr(dataset, name)
        self._parts.append((self.size, self.size + dataset.n_rows, dataset.stats))
        self.size += dataset.n_rows
        return len(self._parts) - 1

    def part(self, index: int) -> BCDataset:
        """The rows of the ``index``-th append, with its own stats."""
        begin, end, stats = self._parts[index]
        return self._slice(begin, end, stats)

    def view(self) -> BCDataset:
        """Every row appended so far; stats are summed / row-weighted over parts."""
        if not self._parts:
            raise ValueError("no rows appended")
        stats = [s for _, _, s in self._parts]
        rows = sum(s.rows for s in stats)

        def weighted(name: str) -> float:
            return float(sum(getattr(s, name) * s.rows for s in stats) / rows)

        merged = CollectStats(
            env_steps=sum(s.env_steps for s in stats),
            rows=rows,
            holdout_rows=sum(s.holdout_rows for s in stats),
            noise_rate=weighted("noise_rate"),
            changed_rate=weighted("changed_rate"),
            fire_rate=weighted("fire_rate"),
            wall_s=sum(s.wall_s for s in stats),
        )
        return self._slice(0, self.size, merged)

    def _slice(self, begin: int, end: int, stats: CollectStats) -> BCDataset:
        arrays = {name: self._arrays[name][begin:end] for name in _ROW_FIELDS}
        return BCDataset(stats=stats, **arrays)


DAGGER_MODES = ("finetune", "scratch")


@dataclass(frozen=True)
class DaggerConfig:
    """Settings of a ``dagger`` run.

    Attributes:
        rounds: On-policy rounds after round 0.
        rows_per_round: On-policy rows collected per round.
        base_rows: Round-0 rows (the scripted DART dataset of ``collect``).
        seed: Round-0 collection seed; round ``k`` collects with ``seed + k``.
        n_envs: Parallel matches for every collection.
        dart_p: Round-0 DART noise.
        beta_first: Round-1 mixing probability; later rounds use 0.
        mode: "finetune" (continue from the previous round's actor) or "scratch"
            (fresh actor every round, trained with ``base_train``).
        base_train: Round-0 training (and every round in "scratch" mode).
        finetune_train: Training of rounds >= 1 in "finetune" mode.
        max_rows: Upper bound on the aggregate store (memory guard).
        duel_n: Duels per evaluation (``eval.duel.evaluate``).
        duel_argmax: Also evaluate the argmax policy each round.
        obs_dtype: Storage dtype of the observations.
    """

    rounds: int = 3
    rows_per_round: int = 2_000_000
    base_rows: int = 2_000_000
    seed: int = 0
    n_envs: int = 256
    dart_p: float = 0.15
    beta_first: float = 0.0
    mode: str = "finetune"
    base_train: TrainConfig = field(default_factory=TrainConfig)
    finetune_train: TrainConfig = field(
        default_factory=lambda: TrainConfig(epochs=2, lr=3e-4, lr_final=3e-5)
    )
    max_rows: int = 8_000_000
    duel_n: int = 512
    duel_argmax: bool = False
    obs_dtype: str = "float16"

    def __post_init__(self) -> None:
        if self.mode not in DAGGER_MODES:
            raise ValueError(f"mode must be one of {DAGGER_MODES}, got {self.mode}")
        if self.rounds < 0:
            raise ValueError(f"rounds must be >= 0, got {self.rounds}")
        if self.total_rows > self.max_rows:
            raise ValueError(
                f"{self.total_rows} aggregate rows exceed max_rows {self.max_rows}"
            )

    @property
    def total_rows(self) -> int:
        """Aggregate rows after the last round."""
        return self.base_rows + self.rounds * self.rows_per_round


DAGGER_EVAL_NAME = "dagger_eval.json"
DAGGER_BEST_NAME = "best.pt"


def dagger_checkpoint_name(round_index: int) -> str:
    """File name of round ``round_index``'s checkpoint."""
    return f"bc_dagger_r{round_index}.pt"


def duel_summary(result: DuelResult) -> dict[str, float]:
    """The learner-side (side "a") numbers of the DAgger table, plus the script's."""
    side = result.side_a
    n = result.config.n
    return {
        "win_rate": side.win_rate,
        "draw_rate": side.draws / n,
        "hit_rate": side.hit_rate,
        "engagement_rate": side.engagement_rate,
        "outside_share": side.outside_share,
        "main_engine_duty": side.main_engine_duty,
        "fire_rate": side.fire_rate,
        "shots": side.shots,
        "kill_rate": result.match.kill_rate,
        "script_hit_rate": result.side_b.hit_rate,
        "script_engagement_rate": result.side_b.engagement_rate,
        "script_main_engine_duty": result.side_b.main_engine_duty,
    }


def agreement_summary(report: dict[str, object]) -> dict[str, object]:
    """The headline numbers of a ``bc_eval`` report."""
    groups = report["groups"]
    if not isinstance(groups, dict):
        raise TypeError("bc_eval report has no groups dict")
    return {
        "throttle": groups["throttle"]["agreement"],
        "fire": groups["fire"]["agreement"],
        "fire_recall": groups["fire"]["recall"],
        "fire_precision": groups["fire"]["precision"],
        "power": groups["power"]["agreement"],
        "exact_row": report["exact_row_agreement"],
    }


def _duel(checkpoint: Path, config: DaggerConfig, n_threads: int) -> dict[str, object]:
    out: dict[str, object] = {}
    for sample in (True, False) if config.duel_argmax else (True,):
        start = time.perf_counter()
        result = evaluate(
            Policy(checkpoint, sample=sample),
            Scripted(),
            n=config.duel_n,
            n_threads=n_threads,
        )
        out["sample" if sample else "argmax"] = {
            "summary": duel_summary(result),
            "markdown": result.markdown_row("a"),
            "wall_s": time.perf_counter() - start,
            "result": result.to_dict(),
        }
    return out


@dataclass(frozen=True)
class DaggerResult:
    """Paths and per-round rows of ``dagger``."""

    eval_path: Path
    best: Path
    best_round: int
    rounds: list[dict[str, object]]


def dagger(
    out_dir: Path,
    config: DaggerConfig,
    n_threads: int,
    init: Path | None = None,
    on_round: Callable[[dict[str, object]], None] | None = None,
) -> DaggerResult:
    """DAgger on the scripted fighter: round 0 is BC, then on-policy rounds.

    Round 0 re-collects the scripted DART dataset (``collect`` with
    ``config.seed``) and either trains on it or, with ``init``, takes that
    checkpoint's actor (the original BC run on the same data). Each later round
    collects ``rows_per_round`` on-policy rows with the current actor, appends them
    to the aggregate, trains (fine-tune or from scratch) on every non-held-out row,
    and scores the result on that round's on-policy holdout (with the collecting
    actor and the trained one) and in ``config.duel_n`` sampled duels against the
    script. Each round writes ``bc_dagger_r{k}.pt`` and rewrites
    ``dagger_eval.json``; the round with the best sampled win rate is copied to
    ``best.pt``.

    Args:
        out_dir: Output directory.
        config: Run settings.
        n_threads: Sim and torch threads (also used by the duels).
        init: Optional round-0 checkpoint used instead of training round 0.
        on_round: Called with each round's row as soon as it is complete.
    """
    if n_threads > 0:
        torch.set_num_threads(n_threads)
    out_dir.mkdir(parents=True, exist_ok=True)
    store = AggregateDataset(config.total_rows, config.obs_dtype)
    start = time.perf_counter()
    store.append(
        collect(
            config.base_rows,
            n_envs=config.n_envs,
            n_threads=n_threads,
            seed=config.seed,
            dart_p=config.dart_p,
            obs_dtype=config.obs_dtype,
        )
    )
    round0 = store.part(0)
    if init is None:
        actor, log = train(round0, config.base_train)
        train_report = _train_report(config.base_train, log)
    else:
        actor = load_policy(init)[0]
        train_report = {"init": str(init)}
    rows = [
        _finish_round(0, actor, round0, None, store.size, train_report, config)
        | {"beta": 1.0}
    ]
    _save_round(out_dir, 0, actor, rows, config, n_threads, start, init, on_round)

    for k in range(1, config.rounds + 1):
        start = time.perf_counter()
        beta = config.beta_first if k == 1 else 0.0
        store.append(
            collect_on_policy(
                actor,
                config.rows_per_round,
                n_envs=config.n_envs,
                n_threads=n_threads,
                seed=config.seed + k,
                beta=beta,
                obs_dtype=config.obs_dtype,
            )
        )
        part = store.part(k)
        before = agreement_summary(bc_eval(actor, part))
        if config.mode == "finetune":
            train_config = replace(
                config.finetune_train, seed=config.finetune_train.seed + k
            )
            actor, log = train(store.view(), train_config, actor=actor)
        else:
            train_config = replace(config.base_train, seed=config.base_train.seed + k)
            actor, log = train(store.view(), train_config)
        row = _finish_round(
            k,
            actor,
            part,
            before,
            store.size,
            _train_report(train_config, log),
            config,
        )
        rows.append(row | {"beta": beta})
        _save_round(out_dir, k, actor, rows, config, n_threads, start, init, on_round)

    best_round = max(range(len(rows)), key=lambda i: _win_rate(rows[i]))
    best = out_dir / DAGGER_BEST_NAME
    shutil.copyfile(out_dir / dagger_checkpoint_name(best_round), best)
    eval_path = _write_dagger_eval(out_dir, config, init, rows, best_round)
    return DaggerResult(
        eval_path=eval_path, best=best, best_round=best_round, rounds=rows
    )


def _train_report(config: TrainConfig, log: TrainLog) -> dict[str, object]:
    return {
        "config": asdict(config),
        "epoch_loss": log.epoch_loss,
        "steps": log.steps,
        "wall_s": log.wall_s,
    }


def _win_rate(row: dict[str, object]) -> float:
    duel = row["duel"]
    if not isinstance(duel, dict):
        raise TypeError("round row has no duel dict")
    return float(duel["sample"]["summary"]["win_rate"])


def _finish_round(
    k: int,
    actor: SpikeActor,
    part: BCDataset,
    before: dict[str, object] | None,
    aggregate_rows: int,
    train_report: dict[str, object],
    config: DaggerConfig,
) -> dict[str, object]:
    """Round ``k``'s row without the duel (agreement on its own holdout)."""
    return {
        "round": k,
        "source": "dart_script" if k == 0 else "on_policy",
        "collect": asdict(part.stats),
        "aggregate_rows": aggregate_rows,
        "train": train_report,
        "holdout_agreement_collector": before,
        "holdout_agreement": agreement_summary(bc_eval(actor, part)),
    }


def _save_round(
    out_dir: Path,
    k: int,
    actor: SpikeActor,
    rows: list[dict[str, object]],
    config: DaggerConfig,
    n_threads: int,
    start: float,
    init: Path | None,
    on_round: Callable[[dict[str, object]], None] | None,
) -> None:
    """Write round ``k``'s checkpoint, run its duels and rewrite the eval JSON."""
    row = rows[k]
    checkpoint = out_dir / dagger_checkpoint_name(k)
    torch.manual_seed(config.seed + 1)
    save_policy(
        checkpoint,
        actor,
        SpikeCritic(),
        {
            "source": "bc_dagger",
            "sim_version": SIM_VERSION,
            "critic": "fresh",
            "round": k,
            "holdout_agreement": json.loads(json.dumps(row["holdout_agreement"])),
        },
    )
    row["checkpoint"] = str(checkpoint)
    row["duel"] = _duel(checkpoint, config, n_threads)
    row["wall_s"] = time.perf_counter() - start
    _write_dagger_eval(out_dir, config, init, rows)
    if on_round is not None:
        on_round(row)


def _write_dagger_eval(
    out_dir: Path,
    config: DaggerConfig,
    init: Path | None,
    rows: list[dict[str, object]],
    best_round: int | None = None,
) -> Path:
    report = {
        "config": asdict(config),
        "init": str(init) if init is not None else None,
        "best_round": best_round,
        "rounds": rows,
    }
    path = out_dir / DAGGER_EVAL_NAME
    path.write_text(json.dumps(report, indent=2) + "\n")
    return path
