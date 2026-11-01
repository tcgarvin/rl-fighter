"""PPO training loop for the learnability spike (masked heads, credit, opponents).

Spec: ``lab/runs/2026-10-28-learnability-spike/plan.md`` §3 (credit, critic), §4.2
(hyperparameters, critic warm-up, script pull, opponent schedule, scratch control),
§4.3 (log keys) and §5 (budget). Entry point: ``python -m spacefight.train_spike ppo``.

Rollout layout. The learner is team 0 in every env; team 1 is the opponent of that
env (``spacefight.rl.opponents``). Every step stores all ``R = N * S`` ship rows; a
row joins the PPO batch iff it is a learner row (team 0, or team 1 of a self-play
env) and its ``act_mask`` is set (SIM_SPEC §7.1: a masked row has no effect).

Fleets (``rosters`` set): every env draws a roster of 1-4 ships a side per episode
(``spacefight.env.rosters``) in ``max_ships`` padded slots, so each step also stores
every slot's team, hull and head masks (they change when a match is rebuilt). Every
alive ship of the learning team(s) is a sample, each labelled by its own hull's
script. A ``fleet`` critic values a ship from its own obs plus pooled embeddings of
its teammates and of the enemies in the same match (``FleetCritic``), so PPO
minibatches are drawn as whole (step, env) groups: every training row of a group
lands in the same minibatch, together with the obs of its match.

Credit and the rollout boundary. ``RustCreditAdapter`` moves each hit's shooter
reward from the landing step to the step stamped with its ``decision_tick``. A shot
lands up to ~36 ticks after it was chosen, so the last ``t_tail`` (40) steps of a
rollout are not final when the rollout ends. The buffer holds ``n_steps + t_tail``
rows: the first rollout fills all of them, later rollouts keep the previous
rollout's last ``t_tail`` rows at the front and collect ``n_steps`` new rows after
them. Each update trains on rows ``[0, n_steps)``, every one of which has at least
``t_tail`` steps after it in the buffer, so its credit is complete and GAE
bootstraps through real rewards. The cost is that the carried rows were sampled by
the previous update's actor; PPO's ratio uses their stored behaviour log-probs, and
their values are recomputed with the current critic before GAE.

Missions and orders (M3 stage B, ``lab/runs/2026-10-31-order-pilot/plan.md``). With
the ``orders_v1`` rosters an env plays deathmatches, carrier battles and convoys, each
team under a scripted or random commander. Capital ships (carriers, freighters) are
never learner or snapshot rows: they keep their script's actions. With
``learner_side = "random"`` the learner's team is drawn per episode (a convoy's
transports are always team 0, so a fixed side would only ever defend); every
"team 0" above then means "the learner's team of that env". The step reward is the
team reward plus ``order_reward_weight * env.order_rewards`` (SIM_VERSION 5); GAE
runs on the sum and both parts are logged. The env's go-to shaping uses ``gamma``, so
the two discounts cannot disagree (``order_shaping_gamma``, SIM_SPEC §8). With orders
hidden (``Roster.hide_orders``, preset ``pilots_v1``) the sim still computes order pay;
those rows earn none, since a pilot is only paid for an order it was shown. A frozen
``kl_anchor`` actor (fleet pilot v1) adds ``kl_anchor_coeff * KL(anchor || pi)`` on the rows whose obs has no order
(``has_order = 0``), so unordered behaviour stays v1's.

Obs width. Every net sees ``fit_obs(obs, net.obs_dim)``: the learner, the anchor and
each snapshot (a 385-wide v1 in the 403-wide SIM_VERSION 5 obs reads the prefix).
The learner trains at ``config.obs_dim``; 0 keeps the init's width (a fleet run from
v1 stays 385 wide and never sees orders), a wider value widens the init with zero
input columns (``widen_actor``), so update 0 is the init exactly.

Script labels. ``env.scripted_actions()`` is called every step before the learner's
actions overwrite the action buffer, so team-1 scripted rows are already in place
and the labels of every row are stored for the auxiliary loss
``beta * mean(-log pi(a_script | s))`` (joint over the row's valid heads) on the
batch rows. The script NLL is logged every update, also when ``beta`` is 0.

Ordered rows (run B2b, ``lab/runs/2026-10-31-order-pilot-b2b/plan.md``). With
``beta_rows = "ordered"`` the pull's mean runs over the *pulled* rows only: rows whose
obs shows an order that the row's script flies (``RustVecEnv.scripted_order_rows``:
``has_order`` and not the scripted commander's advisory deathmatch orders), so the
label is the order-following script's action for that ship. ``"all"`` is every batch
row (the fleet run). Rows with an advisory deathmatch order get neither the pull nor
the KL anchor (which stays on ``has_order = 0`` rows). ``beta_heads = "movement"``
restricts the pull to the thruster and power heads: an order says where to fly, and
the pilot already aims and fires better than the script does.

Transit rows and new inputs (run B3, ``lab/runs/2026-11-01-order-pilot-b3/plan.md``,
SIM_VERSION 6). With ``beta_rows = "transit"`` the pull averages over the rows whose
effective order is a go-to not yet reached or a defend with an empty threat set
(``RustVecEnv.transit_rows``: ``env.order_transit`` where the row's script flies the
order); attack rows are never transit, which the rollout asserts. When the init is
widened (403 -> 583), the first-layer columns of the new inputs (actor, and the
critic's base and encoder) step ``new_input_lr_mult`` times as far as the rest
(``NewInputAdam``): run 1 showed that zero columns barely move at the base LR.

Reward hiding (run ``lab/runs/2026-11-01-fighters-v2``). With
``hide_damage_when_ordered`` a shot chosen under an order earns no team damage reward
(``RustCreditAdapter.record_step``'s ``unpaid_rows``), only what the order reward pays.

Order drills (``docs/PILOT_TRAINING.md`` section 2). With ``drill_share`` in the
``pilots_v1`` distribution, some envs play drills (``spacefight.env.drills``). The env
queues a drill's orders when its match is built. The trainer holds such an env out of the
opponent quota and has the script fly its enemies (``OpponentAssigner.force_scripted``),
with the learner on the ordered team, team 0, and logs it apart: drills are not in the
episode tallies. Drill pay is match pay plus order pay; the sim's drill rules end a drill
as a draw, so no match result is in it. With ``drill_share`` 0 none of this runs and the
random draws are unchanged.

Anchor cache. The frozen anchor's per-head log-softmax is computed once per sample
at rollout time (learner rows, ``[rows, N_LOGITS]`` float32) and read back in every
minibatch of every epoch, instead of running the anchor net each time; the loss is
the same up to float round-off between batch shapes (tested).
"""

from __future__ import annotations

import dataclasses
import json
import os
import time
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml  # type: ignore[import-untyped]
from numpy.typing import NDArray

from spacefight.env.drills import DrillLedger
from spacefight.env.rosters import (
    CONVOY_ESCORT,
    Roster,
    capital_hull_ids,
    hull_names_by_id,
    make_sampler,
    resolve_distribution,
)
from spacefight.env.rust_env import (
    ATTACK_COL,
    HAS_ORDER_COL,
    OBS_DIM,
    OBS_LAYOUT,
    SIM_VERSION,
    RustVecEnv,
    StepInfo,
)
from spacefight.rl.credit import (
    HIT_DAMAGE_MILLI,
    HIT_DAMAGE_SCALE,
    HIT_SHIELD,
    HIT_SHOOTER,
    HIT_TARGET,
    HULL_DAMAGE_WEIGHT,
    SHIELD_DAMAGE_WEIGHT,
    RustCreditAdapter,
)
from spacefight.rl.opponents import (
    DEFAULT_BANDS,
    DEFAULT_PFSP_FLOOR,
    DEFAULT_PFSP_POWER,
    ENEMY_SAMPLINGS,
    KIND_NAMES,
    SAMPLING_UNIFORM,
    OpponentAssigner,
    OpponentKind,
    OpponentSchedule,
    SnapshotPool,
    check_pfsp_settings,
    snapshot_groups,
)
from spacefight.rl.spike_policy import (
    ACTION_WIDTH,
    CRITIC_KINDS,
    CRITIC_SPIKE,
    HEAD_GROUPS,
    HEAD_SETS,
    N_LOGITS,
    N_THRUSTERS,
    N_TURRETS,
    Critic,
    FleetCritic,
    HeadLogSoftmax,
    HeadMasks,
    SpikeActor,
    SpikeCritic,
    as_critic_kind,
    critic_kind,
    fit_obs,
    head_kl,
    head_set_columns,
    load_policy,
    mean_head_entropy,
    save_policy,
    widen_actor,
    widen_critic,
)

# Reward weights mirrored from crates/sim/src/reward.rs (rlf_sim does not export
# them); tests/test_spike_ppo.py asserts they match the Rust source. Used only to
# split the step reward into logged components.
FIRE_COST = -0.002
ARENA_PENALTY = -0.002

# Obs columns used for logged stats (SIM_SPEC §7.2): self (R - |pos|)/R, and the
# thrust level of thruster slot 0 (the fighter's main engine, first in hull.yaml).
_ARENA_MARGIN_COL = OBS_LAYOUT["self"][0] + 19
_MAIN_ENGINE_LEVEL_COL = OBS_LAYOUT["thrusters"][0] + 6
_FIRE_COL = HEAD_GROUPS["fire"].start
LEARNER_SIDES = ("team0", "random")
# Rows the script pull applies to (module docstring, "Ordered rows", "Transit rows").
BETA_ROWS = ("all", "ordered", "transit")

INIT_SCRATCH = "scratch"
_CHECKPOINT_PREFIX = "ppo"
_TRAIN_STATE_FORMAT = "spike_ppo/1"
# Env seed of a training segment starting at update u: seed + u * this (a resume
# must not replay the episodes the run already trained on).
ENV_SEED_STRIDE = 1_000_003

# Every key of a log.jsonl row (plan §4.3). Rates without data (no episode against
# an opponent kind this update) are null.
LOG_KEYS: tuple[str, ...] = (
    "update",
    "wall_time",
    "update_seconds",
    "rollout_seconds",
    "gae_credit_seconds",
    "ppo_seconds",
    "samples",
    "samples_per_s",
    "sim_steps_per_s",
    "env_seed",
    "reward_mean",
    "reward_team",
    "reward_order",
    "reward_order_weighted",
    "order_reward_weight",
    "has_order_share",
    "beta_rows_share",
    "reward_damage_dealt",
    "reward_damage_taken",
    "reward_fire_cost",
    "reward_arena",
    "reward_terminal",
    "reward_shaping",
    "reward_credit_moved",
    "credit_hits_moved",
    "credit_hits_kept",
    "vs_scripted_win",
    "vs_scripted_draw",
    "vs_scripted_loss",
    "vs_scripted_episodes",
    "vs_self_win",
    "vs_self_draw",
    "vs_self_loss",
    "vs_self_episodes",
    "vs_snapshot_win",
    "vs_snapshot_draw",
    "vs_snapshot_loss",
    "vs_snapshot_episodes",
    "episodes",
    "episode_length_mean",
    "entropy_throttle",
    "entropy_slew",
    "entropy_fire",
    "entropy_power",
    "entropy_mean",
    "approx_kl",
    "clip_fraction",
    "clip_eps",
    "pg_loss",
    "value_loss",
    "explained_variance",
    "aux_script_nll",
    "aux_script_nll_pulled",
    "kl_anchor",
    "kl_anchor_ordered",
    "kl_anchor_share",
    "kl_anchor_coeff",
    "beta",
    "actor_lr",
    "critic_lr",
    "new_input_lr",
    "actor_frozen",
    "main_engine_duty",
    "fire_rate",
    "shots",
    "hits",
    "hit_rate",
    "outside_arena_share",
    "opponents_scripted",
    "opponents_self",
    "opponents_snapshot",
    "snapshot_pool",
    "ships_per_match",
    "vs_scripted_win_by_class",
    "win_by_class",
    "episodes_by_class",
    "drill_rows_share",
    "drill_episodes",
    "drill_success",
    "hull_samples",
    "hull_hit_rate",
    "hull_damage_dealt",
)


# Rollout steps between reads of the sim's order tracks for the drill log's go-to arrivals.
# Under the drill clock's margin, so an arrival on a deadline is seen.
DRILL_TRACK_EVERY = 15

# Diagnostics returned by ``ppo_update`` (null in the log when it is skipped).
PPO_METRIC_KEYS: tuple[str, ...] = (
    "pg_loss",
    "value_loss",
    "approx_kl",
    "clip_fraction",
    "aux_script_nll",
    "aux_script_nll_pulled",
    "kl_anchor",
    "kl_anchor_ordered",
    "kl_anchor_share",
    "entropy_mean",
) + tuple(f"entropy_{name}" for name in HEAD_GROUPS)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------


@dataclass
class PPOConfig:
    """Every number of a spike PPO run (dumped to ``config.yaml``).

    Build with ``PPOConfig.preset(init)``: ``init`` is ``"scratch"`` or the path of
    a ``save_policy`` checkpoint (``bc.pt``); the preset sets the init-dependent
    values of plan §4.2 (BC: actor LR 1e-4, clip 0.1 for 200 updates, 30-update
    critic warm-up, beta 0.1 -> 0 over updates 30-700; scratch: actor LR 3e-4,
    clip 0.2 throughout, no warm-up, beta 0). Fields after the preset are the §7
    risk responses, off by default.
    """

    init: str
    tag: str
    seed: int = 0
    # Env (plan §3).
    assets_dir: str = "assets"
    fleets: list[list[str]] = field(default_factory=lambda: [["fighter"], ["fighter"]])
    n_envs: int = 256
    reaction_ticks: int = 2
    arena_radius: float = 450.0
    time_limit_s: float = 90.0
    sim_threads: int = 6
    torch_threads: int = 6
    # Rollout.
    n_steps: int = 128
    t_tail: int = 40
    n_updates: int = 2000
    gamma: float = 0.99
    gae_lambda: float = 0.95
    credit_dead_shooters: bool = False
    # PPO.
    epochs: int = 4
    minibatch: int = 4096
    clip_eps: float = 0.2
    early_clip_eps: float = 0.1
    early_clip_updates: int = 0
    actor_lr: float = 3e-4
    critic_lr: float = 3e-4
    lr_decay: bool = True
    ent_coeff: float = 0.005
    vf_coeff: float = 0.5
    max_grad_norm: float = 0.5
    critic_warmup_updates: int = 0
    # Script pull: beta_start until beta_decay_start, linear to beta_end at
    # beta_decay_end, then beta_end; never below beta_floor.
    beta_start: float = 0.0
    beta_end: float = 0.0
    beta_decay_start: int = 30
    beta_decay_end: int = 700
    beta_floor: float = 0.0
    # Which batch rows the pull averages over: "all", or "ordered" (rows whose obs
    # shows an order their script flies; module docstring), and which heads it
    # covers: "all", or "movement" (thrusters and power, not aim and fire).
    beta_rows: str = "all"
    beta_heads: str = "all"
    # Opponents: (start_update, scripted, self, snapshot) rows.
    opponent_bands: list[list[float]] = field(
        default_factory=lambda: [list(band) for band in DEFAULT_BANDS]
    )
    checkpoint_every: int = 100
    # Fleets: a roster preset of spacefight.env.rosters ("" = the fixed ``fleets``),
    # field overrides on it, and slots per match (0 = the sampler's ``max_ships`` with
    # rosters, else the fleet size).
    rosters: str = ""
    roster_overrides: dict[str, object] = field(default_factory=dict)
    max_ships: int = 0
    # "spike" (own-obs critic) or "fleet" (centralised over the match's team set).
    critic: str = CRITIC_SPIKE
    # Frozen checkpoints in the snapshot pool from update 0 (paths).
    pool_seed: list[str] = field(default_factory=list)
    # Scripted steps on both sides before the first rollout of a segment, so short
    # test rollouts start past the arrival + control lock (0 for real runs).
    env_warmup_steps: int = 0
    # Stage B (module docstring). learner_side: "team0" (the learner is team 0) or
    # "random" (drawn per episode). pool_seed_p: a snapshot env plays a pool_seed
    # entry with this probability (0 = uniform over the whole pool).
    learner_side: str = "team0"
    pool_seed_p: float = 0.0
    # How frozen-pool draws pick an entry: "uniform", or "pfsp", weighted toward those
    # that beat the learner, with a floor so none drop out (spacefight/rl/opponents.py).
    enemy_sampling: str = SAMPLING_UNIFORM
    enemy_pfsp_power: float = DEFAULT_PFSP_POWER
    enemy_pfsp_floor: float = DEFAULT_PFSP_FLOOR
    # Step reward = team reward + order_reward_weight * order_rewards (SIM_VERSION 5).
    order_reward_weight: float = 0.0
    # Reward hiding (run 2026-11-01-fighters-v2): a shot chosen on a row with an order
    # pays nothing from the team reward; the order reward pays what the order wants
    # (damage to its target or threat set). Damage taken, fire cost, arena and the
    # terminal stay. Rows without an order are paid as usual.
    hide_damage_when_ordered: bool = False
    # Frozen actor (a checkpoint path, "" = none) and the weight of
    # KL(anchor || pi) on rows without an order (has_order = 0).
    kl_anchor: str = ""
    kl_anchor_coeff: float = 0.0
    # The learner's obs width: 0 = the init's (scratch: the sim's OBS_DIM); wider
    # than the init widens it with zero input columns (stage B: 403, B3: 583).
    obs_dim: int = 0
    # Step size of the widened inputs' first-layer columns relative to the rest
    # (actor and critic; ``NewInputAdam``). 1 = no difference; no effect without a
    # widening.
    new_input_lr_mult: float = 1.0
    # §7 risk responses (all off by default).
    entropy_floor: float = 0.0
    entropy_floor_coeff: float = 0.0
    tick_cost: float = 0.0
    extra_arena_penalty: float = 0.0

    @classmethod
    def preset(cls, init: str, **overrides: object) -> PPOConfig:
        """The plan §4.2 config for ``init`` ("scratch" or a policy path)."""
        if init == INIT_SCRATCH:
            base: dict[str, object] = {"init": init, "tag": "scratch"}
        else:
            base = {
                "init": init,
                "tag": "bc",
                "actor_lr": 1e-4,
                "early_clip_updates": 200,
                "critic_warmup_updates": 30,
                "beta_start": 0.1,
            }
        base.update(overrides)
        return cls(**base)  # type: ignore[arg-type]

    def __post_init__(self) -> None:
        positive = {
            "n_envs": self.n_envs,
            "n_steps": self.n_steps,
            "n_updates": self.n_updates,
            "epochs": self.epochs,
            "minibatch": self.minibatch,
            "checkpoint_every": self.checkpoint_every,
        }
        for name, value in positive.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive, got {value}")
        if self.t_tail < 0:
            raise ValueError(f"t_tail must be >= 0, got {self.t_tail}")
        if not 0.0 < self.gamma <= 1.0:
            raise ValueError(f"gamma must be in (0, 1], got {self.gamma}")
        if len(self.fleets) != 2:
            raise ValueError(f"fleets must have two teams, got {self.fleets}")
        if self.beta_decay_end < self.beta_decay_start:
            raise ValueError("beta_decay_end must be >= beta_decay_start")
        if self.sim_threads < 0 or self.torch_threads <= 0:
            raise ValueError("sim_threads must be >= 0 and torch_threads > 0")
        if self.critic not in CRITIC_KINDS:
            raise ValueError(f"critic must be one of {CRITIC_KINDS}, got {self.critic}")
        if self.max_ships < 0:
            raise ValueError(f"max_ships must be >= 0, got {self.max_ships}")
        if self.rosters:
            self.roster_distribution()
        elif self.roster_overrides:
            raise ValueError("roster_overrides needs a rosters preset")
        if self.drill_share > 0.0:
            if self.order_reward_weight <= 0.0:
                raise ValueError(
                    "drills need order_reward_weight > 0: order pay is what they teach"
                )
            if self.hide_damage_when_ordered:
                raise ValueError(
                    "drills cannot run with hide_damage_when_ordered: a hit on another "
                    "enemy must pay what it always does"
                )
        OpponentSchedule(self.opponent_bands)
        if self.learner_side not in LEARNER_SIDES:
            raise ValueError(
                f"learner_side must be one of {LEARNER_SIDES}, got {self.learner_side}"
            )
        if not 0.0 <= self.pool_seed_p <= 1.0:
            raise ValueError(f"pool_seed_p must be in [0, 1], got {self.pool_seed_p}")
        if self.enemy_sampling not in ENEMY_SAMPLINGS:
            raise ValueError(
                f"enemy_sampling must be one of {ENEMY_SAMPLINGS}, "
                f"got {self.enemy_sampling}"
            )
        check_pfsp_settings(self.enemy_pfsp_power, self.enemy_pfsp_floor)
        if self.kl_anchor_coeff < 0.0 or (
            self.kl_anchor_coeff > 0 and not self.kl_anchor
        ):
            raise ValueError("kl_anchor_coeff must be >= 0 and needs a kl_anchor")
        if not 0 <= self.obs_dim <= OBS_DIM:
            raise ValueError(f"obs_dim must be in 0..={OBS_DIM}, got {self.obs_dim}")
        if self.beta_rows not in BETA_ROWS:
            raise ValueError(
                f"beta_rows must be one of {BETA_ROWS}, got {self.beta_rows}"
            )
        if self.new_input_lr_mult <= 0.0:
            raise ValueError(
                f"new_input_lr_mult must be positive, got {self.new_input_lr_mult}"
            )
        if self.beta_heads not in HEAD_SETS:
            raise ValueError(
                f"beta_heads must be one of {tuple(HEAD_SETS)}, got {self.beta_heads}"
            )

    @property
    def drill_share(self) -> float:
        """The share of drills in the roster distribution; 0 without one."""
        if not self.rosters:
            return 0.0
        share = self.roster_distribution().get("drill_share", 0.0)
        if not isinstance(share, (int, float)):
            raise ValueError(f"drill_share must be a number, got {share!r}")
        return float(share)

    def roster_distribution(self) -> dict[str, object]:
        """The roster distribution (preset + overrides) as a plain dict.

        Raises:
            KeyError: Unknown preset.
            ValueError: Bad overrides, or no ``rosters`` preset set.
        """
        if not self.rosters:
            raise ValueError("this config has fixed fleets, not rosters")
        base = resolve_distribution(self.rosters).to_dict()
        base.update(self.roster_overrides)
        return resolve_distribution(base).to_dict()

    def to_dict(self) -> dict[str, object]:
        """Plain-type dict (yaml / checkpoint meta)."""
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PPOConfig:
        """Inverse of ``to_dict``.

        Raises:
            ValueError: Unknown keys.
        """
        known = {f.name for f in dataclasses.fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown config keys: {sorted(unknown)}")
        return cls(**data)  # type: ignore[arg-type]

    def beta(self, update: int) -> float:
        """Script-pull weight at ``update``."""
        if update <= self.beta_decay_start:
            value = self.beta_start
        elif update >= self.beta_decay_end:
            value = self.beta_end
        else:
            frac = (update - self.beta_decay_start) / (
                self.beta_decay_end - self.beta_decay_start
            )
            value = self.beta_start + frac * (self.beta_end - self.beta_start)
        return max(value, self.beta_floor)

    def clip(self, update: int) -> float:
        """Clip epsilon at ``update``."""
        return (
            self.early_clip_eps if update < self.early_clip_updates else self.clip_eps
        )

    def lr_scale(self, update: int) -> float:
        """Linear decay factor from 1 at update 0 to 0 at ``n_updates``."""
        if not self.lr_decay:
            return 1.0
        return max(0.0, 1.0 - update / self.n_updates)

    def actor_frozen(self, update: int) -> bool:
        """Whether the actor is frozen (critic warm-up) at ``update``."""
        return update < self.critic_warmup_updates


def write_config(config: PPOConfig, path: Path) -> None:
    """Dump ``config`` as YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(config.to_dict(), sort_keys=False))


def read_config(path: Path) -> PPOConfig:
    """Load a config written by ``write_config``."""
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path} does not hold a config mapping")
    return PPOConfig.from_dict(data)


# ---------------------------------------------------------------------------
# GAE
# ---------------------------------------------------------------------------


def compute_gae(
    rewards: NDArray[np.float32],
    values: NDArray[np.float32],
    dones: NDArray[np.bool_],
    last_values: NDArray[np.float32],
    gamma: float,
    lam: float,
) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
    """GAE advantages and returns over a ``[L, R]`` buffer.

    Args:
        rewards: [L, R] step rewards.
        values: [L, R] value of the obs each step's action was chosen from.
        dones: [L, R] episode ended on that step (next obs is a fresh match).
        last_values: [R] value of the obs after the last step.
        gamma: Discount.
        lam: GAE lambda.

    Returns:
        ``(advantages [L, R], returns [L, R])``.
    """
    length = rewards.shape[0]
    advantages = np.zeros_like(rewards)
    last_gae = np.zeros(rewards.shape[1], dtype=np.float32)
    next_values = last_values.astype(np.float32)
    for t in reversed(range(length)):
        nonterminal = 1.0 - dones[t].astype(np.float32)
        delta = rewards[t] + gamma * next_values * nonterminal - values[t]
        last_gae = delta + gamma * lam * nonterminal * last_gae
        advantages[t] = last_gae
        next_values = values[t]
    return advantages, advantages + values


# ---------------------------------------------------------------------------
# PPO update
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PPOBatch:
    """Training rows of one update, plus the matches they belong to.

    A *group* is one (buffer step, env): the S slots of one match at one step. The
    critic needs a row's whole group (``FleetCritic``), so rows are addressed as
    ``(group, slot)`` into ``obs`` / ``team``, which hold every group of the update
    (views of the rollout buffer, not copies).
    """

    obs: torch.Tensor  # [G, S, D] every group of the update
    team: torch.Tensor  # [G, S] int64, -1 = padding
    rows: torch.Tensor  # [B, 2] int64 (group, slot) of each training row
    masks: HeadMasks  # B rows
    actions: torch.Tensor  # [B, 21] int64
    labels: torch.Tensor  # [B, 21] int64, script actions
    old_log_prob: torch.Tensor  # [B]
    advantages: torch.Tensor  # [B]
    returns: torch.Tensor  # [B]
    anchor_rows: torch.Tensor  # [B] bool: no order in the obs (KL anchor applies)
    pull_rows: torch.Tensor  # [B] bool: rows the script pull averages over
    # [B, N_LOGITS] the anchor's per-head log-softmax cached at rollout time; None:
    # not cached, ``ppo_update`` runs the anchor net on each minibatch.
    anchor_reference: torch.Tensor | None = None

    @property
    def size(self) -> int:
        """Number of training rows B."""
        return int(self.rows.shape[0])

    def minibatches(self, minibatch: int) -> list[torch.Tensor]:
        """Row indices of ``ceil(B / minibatch)`` minibatches of whole groups, in a
        fresh random order (torch's global RNG)."""
        groups = torch.unique(self.rows[:, 0])
        n_chunks = max(1, min(int(groups.numel()), -(-self.size // minibatch)))
        member = torch.zeros(self.obs.shape[0], dtype=torch.bool)
        out = []
        for chunk in groups[torch.randperm(groups.numel())].tensor_split(n_chunks):
            member[:] = False
            member[chunk] = True
            out.append(torch.nonzero(member[self.rows[:, 0]]).squeeze(1))
        return out

    def group_view(
        self, idx: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """``(obs [U, S, D], team [U, S], rows [K, 2])`` for the rows ``idx``,
        re-indexed into the U groups they touch."""
        rows = self.rows[idx]
        groups, local = torch.unique(rows[:, 0], return_inverse=True)
        local_rows = torch.stack([local, rows[:, 1]], dim=1)
        return self.obs[groups], self.team[groups], local_rows


@dataclass(frozen=True)
class UpdateSettings:
    """Per-update PPO coefficients (scheduled values resolved for this update)."""

    clip_eps: float
    beta: float
    actor_frozen: bool
    ent_coeff: float
    vf_coeff: float
    max_grad_norm: float
    epochs: int
    minibatch: int
    entropy_floor: float
    entropy_floor_coeff: float
    kl_anchor_coeff: float = 0.0
    # Head set of the script pull (``HEAD_SETS``).
    beta_heads: str = "all"


def ppo_update(
    actor: SpikeActor,
    critic: Critic,
    actor_opt: torch.optim.Optimizer,
    critic_opt: torch.optim.Optimizer,
    batch: PPOBatch,
    settings: UpdateSettings,
    anchor: SpikeActor | None = None,
) -> dict[str, float]:
    """Run the clipped PPO epochs on ``batch`` (minibatches of whole groups).

    With ``actor_frozen`` only the critic is trained; the actor's diagnostics
    (entropy, script NLL) are computed without gradient on the first epoch. With an
    ``anchor`` actor, ``settings.kl_anchor_coeff * KL(anchor || actor)`` (mean over
    the minibatch's ``anchor_rows``) joins the actor loss.

    Returns:
        Mean diagnostics: pg_loss, value_loss, approx_kl, clip_fraction,
        aux_script_nll, entropy_mean and entropy_<group>; with an anchor also
        kl_anchor (on anchor rows), kl_anchor_ordered (on the other rows) and
        kl_anchor_share.
    """
    if batch.size == 0:
        raise ValueError("PPO batch is empty (no unmasked learner rows)")
    adv = batch.advantages
    adv = (adv - adv.mean()) / (adv.std(unbiased=False) + 1e-8)
    sums: dict[str, float] = {}
    counts: dict[str, int] = {}

    def add(name: str, value: float) -> None:
        sums[name] = sums.get(name, 0.0) + value
        counts[name] = counts.get(name, 0) + 1

    for epoch in range(settings.epochs):
        for idx in batch.minibatches(settings.minibatch):
            group_obs, group_team, local_rows = batch.group_view(idx)
            obs = group_obs[local_rows[:, 0], local_rows[:, 1]]
            masks = batch.masks.index(idx)
            values = critic.forward_set(group_obs, group_team, local_rows)
            value_loss = nn.functional.mse_loss(values, batch.returns[idx])
            add("value_loss", float(value_loss.detach()))
            if settings.actor_frozen:
                critic_opt.zero_grad(set_to_none=True)
                (settings.vf_coeff * value_loss).backward()
                nn.utils.clip_grad_norm_(critic.parameters(), settings.max_grad_norm)
                critic_opt.step()
                if epoch == 0:
                    with torch.no_grad():
                        _actor_terms(
                            actor, obs, masks, batch, idx, adv, settings, add, anchor
                        )
                continue
            actor_loss = _actor_terms(
                actor, obs, masks, batch, idx, adv, settings, add, anchor
            )
            loss = actor_loss + settings.vf_coeff * value_loss
            actor_opt.zero_grad(set_to_none=True)
            critic_opt.zero_grad(set_to_none=True)
            loss.backward()
            nn.utils.clip_grad_norm_(actor.parameters(), settings.max_grad_norm)
            nn.utils.clip_grad_norm_(critic.parameters(), settings.max_grad_norm)
            actor_opt.step()
            critic_opt.step()
    return {name: sums[name] / counts[name] for name in sums}


def _actor_terms(
    actor: SpikeActor,
    obs: torch.Tensor,
    masks: HeadMasks,
    batch: PPOBatch,
    idx: torch.Tensor,
    adv: torch.Tensor,
    settings: UpdateSettings,
    add: Callable[[str, float], None],
    anchor: SpikeActor | None = None,
) -> torch.Tensor:
    """Actor loss of one minibatch; records its diagnostics through ``add``."""
    head_lp, head_ent, label_lp, heads = actor.evaluate_with_heads(
        obs, masks, batch.actions[idx], batch.labels[idx]
    )
    valid = masks.head_valid()
    log_ratio = head_lp.sum(-1) - batch.old_log_prob[idx]
    ratio = log_ratio.exp()
    mb_adv = adv[idx]
    clip = settings.clip_eps
    pg_loss = -torch.min(ratio * mb_adv, ratio.clamp(1.0 - clip, 1.0 + clip) * mb_adv)
    pg_loss = pg_loss.mean()
    entropy = mean_head_entropy(head_ent, valid).mean()
    row_nll = -label_lp.sum(-1)
    pulled = batch.pull_rows[idx]
    n_pulled = int(pulled.sum())
    pull_nll = -label_lp[:, head_set_columns(settings.beta_heads)].sum(-1)
    script_nll = pull_nll[pulled].mean() if n_pulled else pull_nll.sum() * 0.0
    loss = pg_loss - settings.ent_coeff * entropy + settings.beta * script_nll
    if settings.entropy_floor_coeff > 0.0:
        # Hinge on each valid head's batch-mean entropy (plan §7 entropy floor).
        per_head = head_ent.sum(0) / valid.sum(0).clamp(min=1)
        shortfall = (settings.entropy_floor - per_head).clamp(min=0.0)
        loss = loss + settings.entropy_floor_coeff * shortfall[valid.any(0)].sum()
    if anchor is not None:
        loss = loss + _anchor_term(anchor, obs, heads, valid, batch, idx, settings, add)
    with torch.no_grad():
        add("pg_loss", float(pg_loss))
        add("approx_kl", float(((ratio - 1.0) - log_ratio).mean()))
        add("clip_fraction", float(((ratio - 1.0).abs() > clip).float().mean()))
        add("aux_script_nll", float(row_nll.mean()))
        if n_pulled:
            add("aux_script_nll_pulled", float(script_nll))
        add("entropy_mean", float(entropy))
        for name, cols in HEAD_GROUPS.items():
            group_valid = valid[:, cols]
            total = torch.where(group_valid, head_ent[:, cols], 0.0).sum()
            add(f"entropy_{name}", float(total / group_valid.sum().clamp(min=1)))
    return loss


def _anchor_term(
    anchor: SpikeActor,
    obs: torch.Tensor,
    heads: object,
    valid: torch.Tensor,
    batch: PPOBatch,
    idx: torch.Tensor,
    settings: UpdateSettings,
    add: Callable[[str, float], None],
) -> torch.Tensor:
    """``kl_anchor_coeff * mean KL(anchor || actor)`` over the minibatch's anchor
    rows (0 when it has none); logs the KL on both row sets. The anchor's heads come
    from ``batch.anchor_reference`` when the rollout cached them."""
    if batch.anchor_reference is not None:
        reference = HeadLogSoftmax.from_flat(batch.anchor_reference[idx])
    else:
        with torch.no_grad():
            reference = anchor.head_log_softmax(fit_obs(obs, anchor.obs_dim))
    kl = head_kl(reference, heads, valid)  # type: ignore[arg-type]
    rows = batch.anchor_rows[idx]
    n_rows = int(rows.sum())
    anchored = kl[rows].mean() if n_rows else kl.sum() * 0.0
    with torch.no_grad():
        add("kl_anchor_share", n_rows / max(int(rows.numel()), 1))
        if n_rows:
            add("kl_anchor", float(anchored))
        if n_rows < rows.numel():
            add("kl_anchor_ordered", float(kl[~rows].mean()))
    return settings.kl_anchor_coeff * anchored


# ---------------------------------------------------------------------------
# Rollout storage
# ---------------------------------------------------------------------------


class RolloutStorage:
    """``[n_steps + t_tail, R]`` buffers; see the module docstring for the tail."""

    def __init__(
        self,
        n_steps: int,
        t_tail: int,
        n_envs: int,
        n_ships: int,
        obs_dim: int = OBS_DIM,
        anchor_cache: bool = False,
    ) -> None:
        self.n_steps = n_steps
        self.t_tail = t_tail
        self.length = n_steps + t_tail
        rows = n_envs * n_ships
        length = self.length
        self.obs = np.zeros((length, rows, obs_dim), dtype=np.float32)
        self.actions = np.zeros((length, rows, ACTION_WIDTH), dtype=np.int8)
        self.labels = np.zeros((length, rows, ACTION_WIDTH), dtype=np.int8)
        self.log_prob = np.zeros((length, rows), dtype=np.float32)
        self.values = np.zeros((length, rows), dtype=np.float32)
        self.rewards = np.zeros((length, rows), dtype=np.float32)
        self.dones = np.zeros((length, rows), dtype=np.bool_)
        self.act_mask = np.zeros((length, rows), dtype=np.bool_)
        self.learner = np.zeros((length, rows), dtype=np.bool_)
        # The env obs showed an order (has_order; the KL anchor skips these rows).
        self.has_order = np.zeros((length, rows), dtype=np.bool_)
        # ... that the row's script flies (the "ordered" script pull's rows).
        self.scripted_order = np.zeros((length, rows), dtype=np.bool_)
        # Transit rows whose script flies the order (the "transit" pull's rows).
        self.transit = np.zeros((length, rows), dtype=np.bool_)
        # The row's team has its orders hidden: it earns no order pay.
        self.order_hidden = np.zeros((length, rows), dtype=np.bool_)
        # The frozen anchor's per-head log-softmax of each learner row (rollout
        # cache; zero rows wide without an anchor).
        self.anchor_logp = np.zeros(
            (length, rows if anchor_cache else 0, N_LOGITS), dtype=np.float32
        )
        # Strike craft on the learner's side of their env (logged stats).
        self.side = np.zeros((length, rows), dtype=np.bool_)
        # Each slot's match before the step (rosters change at resets): team (-1 =
        # padding), hull id and head masks.
        self.team = np.zeros((length, rows), dtype=np.int8)
        self.hull = np.zeros((length, rows), dtype=np.int16)
        self.thruster = np.zeros((length, rows, N_THRUSTERS), dtype=np.bool_)
        self.turret = np.zeros((length, rows, N_TURRETS), dtype=np.bool_)
        self.fixed = np.zeros((length, rows, N_TURRETS), dtype=np.bool_)
        # Logged reward components and counts of each step.
        self.dealt = np.zeros((length, rows), dtype=np.float32)
        self.taken = np.zeros((length, rows), dtype=np.float32)
        self.terminal = np.zeros((length, rows), dtype=np.float32)
        self.fire_cost = np.zeros((length, rows), dtype=np.float32)
        self.arena = np.zeros((length, rows), dtype=np.float32)
        self.shaping = np.zeros((length, rows), dtype=np.float32)
        self.team_reward = np.zeros((length, rows), dtype=np.float32)
        self.order_reward = np.zeros((length, rows), dtype=np.float32)
        self.shots = np.zeros((length, rows), dtype=np.int32)
        self.hits = np.zeros((length, rows), dtype=np.int32)
        self.outside = np.zeros((length, rows), dtype=np.bool_)
        # Rows [0, filled) hold data; the first rollout fills the whole buffer.
        self.filled = 0

    def _arrays(self) -> list[NDArray[np.generic]]:
        return [value for value in vars(self).values() if isinstance(value, np.ndarray)]

    def collect_range(self) -> range:
        """Buffer rows the next rollout writes."""
        return range(self.filled, self.length)

    def train_rows(self) -> NDArray[np.bool_]:
        """[n_steps, R] rows that join the loss: learner rows with ``act_mask``."""
        return self.learner[: self.n_steps] & self.act_mask[: self.n_steps]

    def masks(self, steps: slice, flat: NDArray[np.int64] | None = None) -> HeadMasks:
        """Head masks of buffer rows ``steps`` (flattened), optionally only the
        flat indices ``flat`` of those."""
        thruster = self.thruster[steps].reshape(-1, N_THRUSTERS)
        turret = self.turret[steps].reshape(-1, N_TURRETS)
        fixed = self.fixed[steps].reshape(-1, N_TURRETS)
        if flat is not None:
            thruster, turret, fixed = thruster[flat], turret[flat], fixed[flat]
        return HeadMasks.from_numpy(thruster, turret, fixed)

    def shift_tail(self) -> None:
        """Move the last ``t_tail`` rows to the front after an update."""
        for arr in self._arrays():
            arr[: self.t_tail] = arr[self.n_steps :].copy()
        self.filled = self.t_tail


# ---------------------------------------------------------------------------
# Trainer
# ---------------------------------------------------------------------------


@dataclass
class EpisodeTally:
    """Episode outcomes of one rollout, per opponent kind (learner's view)."""

    outcomes: dict[str, list[int]] = field(
        default_factory=lambda: {name: [0, 0, 0] for name in KIND_NAMES.values()}
    )
    lengths: list[int] = field(default_factory=list)
    ships: list[int] = field(default_factory=list)
    # Roster size class -> [wins, draws, losses] against the script.
    scripted_by_class: dict[str, list[int]] = field(default_factory=dict)
    # Class -> [wins, draws, losses] against every opponent.
    by_class: dict[str, list[int]] = field(default_factory=dict)
    # Drill kind -> [successes, trials, episodes] (``DrillLedger.finish``); drills are
    # not in any count above.
    drills: dict[str, list[int]] = field(default_factory=dict)
    # Rows on the learner's side, and how many of them were in drills.
    side_rows: int = 0
    drill_rows: int = 0

    def add(
        self,
        kind: int,
        winner: int,
        length: int,
        size_class: str,
        n_ships: int,
        learner_team: int = 0,
    ) -> None:
        """Record one finished episode; winner is the sim's (0, 1, -1 draw) and
        ``learner_team`` the learner's side of it."""
        name = KIND_NAMES[OpponentKind(kind)]
        slot = 0 if winner == learner_team else (1 if winner == -1 else 2)
        self.outcomes[name][slot] += 1
        self.lengths.append(length)
        self.ships.append(n_ships)
        self.by_class.setdefault(size_class, [0, 0, 0])[slot] += 1
        if kind == OpponentKind.SCRIPTED:
            self.scripted_by_class.setdefault(size_class, [0, 0, 0])[slot] += 1

    def add_drill(self, kind: str, successes: int, trials: int) -> None:
        """Record one finished drill (``DrillLedger.finish``)."""
        tally = self.drills.setdefault(kind, [0, 0, 0])
        tally[0] += successes
        tally[1] += trials
        tally[2] += 1

    def log_fields(self) -> dict[str, object]:
        """``vs_<kind>_{win,draw,loss,episodes}``, ``episodes``, mean length, mean
        ships per match, and the win rate (draws ½) against the script per roster
        size class; the drills' share of the rollout, and their episodes and success
        rate per kind."""
        out: dict[str, object] = {}
        out["drill_rows_share"] = (
            self.drill_rows / self.side_rows if self.side_rows else 0.0
        )
        out["drill_episodes"] = {
            kind: counts[2] for kind, counts in sorted(self.drills.items())
        }
        out["drill_success"] = {
            kind: counts[0] / counts[1] if counts[1] else None
            for kind, counts in sorted(self.drills.items())
        }
        for name, (win, draw, loss) in self.outcomes.items():
            total = win + draw + loss
            out[f"vs_{name}_win"] = win / total if total else None
            out[f"vs_{name}_draw"] = draw / total if total else None
            out[f"vs_{name}_loss"] = loss / total if total else None
            out[f"vs_{name}_episodes"] = total
        out["episodes"] = len(self.lengths)
        out["episode_length_mean"] = (
            float(np.mean(self.lengths)) if self.lengths else None
        )
        out["ships_per_match"] = float(np.mean(self.ships)) if self.ships else None
        out["vs_scripted_win_by_class"] = {
            klass: (win + 0.5 * draw) / (win + draw + loss)
            for klass, (win, draw, loss) in sorted(self.scripted_by_class.items())
        }
        out["win_by_class"] = {
            klass: (win + 0.5 * draw) / (win + draw + loss)
            for klass, (win, draw, loss) in sorted(self.by_class.items())
        }
        out["episodes_by_class"] = {
            klass: sum(counts) for klass, counts in sorted(self.by_class.items())
        }
        return out


def episode_class(roster: Roster, learner_team: int) -> str:
    """The class an episode is tallied under: the roster's class, with the
    learner's side for a convoy (``convoy_escort/defend`` or ``/attack``)."""
    if roster.mission == CONVOY_ESCORT:
        return f"{roster.klass}/{'defend' if learner_team == 0 else 'attack'}"
    return roster.klass


def checkpoint_path(run_dir: Path, tag: str, update: int) -> Path:
    """``<run_dir>/checkpoints/ppo_<tag>_<update>.pt``."""
    return run_dir / "checkpoints" / f"{_CHECKPOINT_PREFIX}_{tag}_{update}.pt"


def latest_checkpoint(run_dir: Path, tag: str) -> Path:
    """The numbered checkpoint with the highest update in ``run_dir``.

    Raises:
        FileNotFoundError: No checkpoint.
    """
    best: tuple[int, Path] | None = None
    for path in (run_dir / "checkpoints").glob(f"{_CHECKPOINT_PREFIX}_{tag}_*.pt"):
        suffix = path.stem.rsplit("_", 1)[-1]
        if suffix.isdigit() and (best is None or int(suffix) > best[0]):
            best = (int(suffix), path)
    if best is None:
        raise FileNotFoundError(f"no {_CHECKPOINT_PREFIX}_{tag}_<u>.pt in {run_dir}")
    return best[1]


class SpikeTrainer:
    """PPO for the spike: owns the env, nets, optimisers, buffers, pool and logs.

    Args:
        config: Run config.
        run_dir: Output directory (``config.yaml``, ``log.jsonl``,
            ``checkpoints/``).
        resume: Continue from the latest checkpoint in ``run_dir``.

    Raises:
        FileNotFoundError: ``resume`` without a checkpoint, or a missing init file.
    """

    def __init__(self, config: PPOConfig, run_dir: Path, resume: bool = False) -> None:
        self.config = config
        self.run_dir = run_dir
        self._stop_requested = False
        torch.set_num_threads(config.torch_threads)
        torch.set_flush_denormal(True)
        torch.manual_seed(config.seed)
        self.rng = np.random.default_rng(config.seed)
        self.pool = SnapshotPool([(-1, path) for path in config.pool_seed])
        for _, path in self.pool.entries:
            if not Path(path).is_file():
                raise FileNotFoundError(f"pool_seed checkpoint {path} not found")
        self.anchor = self._load_anchor(config.kl_anchor)
        self.next_update = 0
        self.elapsed = 0.0
        self._resumed_enemy_results: list[list[float]] = []
        # First new input column of a widened init (0: not widened).
        self.new_input_start = 0
        self.actor: SpikeActor
        self.critic: Critic
        if resume:
            self._load_checkpoint(latest_checkpoint(run_dir, config.tag))
            self._record_resumed_config()
        else:
            self.actor, self.critic = self._initial_nets()
            self._make_optimisers()
            write_config(config, run_dir / "config.yaml")
        self.env_seed = config.seed + ENV_SEED_STRIDE * self.next_update
        sampler = None
        if config.rosters:
            sampler = make_sampler(
                resolve_distribution(config.roster_distribution()), self.env_seed
            )
        self.env = RustVecEnv(
            config.assets_dir,
            config.n_envs,
            config.fleets,
            self.env_seed,
            arena_radius=config.arena_radius,
            time_limit_s=config.time_limit_s,
            n_threads=config.sim_threads,
            reaction_ticks=config.reaction_ticks,
            max_ships=config.max_ships or None,
            roster_sampler=sampler,
            order_shaping_gamma=config.gamma,
        )
        self.n_envs, self.n_ships = self.env.n_envs, self.env.n_ships
        self.rows = self.n_envs * self.n_ships
        self.hull_names = hull_names_by_id(Path(config.assets_dir))
        self.capital_ids = np.asarray(
            capital_hull_ids(Path(config.assets_dir)), dtype=np.int64
        )
        self.obs_dim = self.actor.obs_dim
        if self.critic.obs_dim != self.obs_dim or self.obs_dim > OBS_DIM:
            raise ValueError(
                f"nets take {self.actor.obs_dim} / {self.critic.obs_dim} obs floats, "
                f"the sim gives {OBS_DIM}"
            )
        self.storage = RolloutStorage(
            config.n_steps,
            config.t_tail,
            self.n_envs,
            self.n_ships,
            self.obs_dim,
            anchor_cache=self.anchor is not None,
        )
        self.credit = RustCreditAdapter(
            self.n_envs,
            self.n_ships,
            self.storage.length,
            credit_dead_shooters=config.credit_dead_shooters,
        )
        self.schedule = OpponentSchedule(config.opponent_bands)
        self.opponents = OpponentAssigner(
            self.n_envs,
            self.schedule,
            self.rng,
            n_seeds=len(config.pool_seed),
            seed_p=config.pool_seed_p,
            enemy_sampling=config.enemy_sampling,
            pfsp_power=config.enemy_pfsp_power,
            pfsp_floor=config.enemy_pfsp_floor,
        )
        self.opponents.results.load_state(self._resumed_enemy_results)
        # The learner's team in each env's current match (module docstring).
        self.learner_team = np.zeros(self.n_envs, dtype=np.int8)
        self.drills_on = config.drill_share > 0.0
        self.drill_ledger = DrillLedger(self.n_envs, self.n_ships)
        if self.drills_on:
            drill_envs, match_envs = self._split_drills(np.arange(self.n_envs))
            self.opponents.assign_all(self.next_update, len(self.pool), drill_envs)
            self._draw_learner_sides(match_envs)
            self._note_new_matches(np.arange(self.n_envs))
        else:
            self.opponents.assign_all(self.next_update, len(self.pool))
            self._draw_learner_sides(np.arange(self.n_envs))
        self.log_path = run_dir / "log.jsonl"
        self._collected = range(0)
        for _ in range(config.env_warmup_steps):
            self.env.scripted_actions()
            self.env.step()

    @property
    def team(self) -> NDArray[np.int8]:
        """[R] team of each slot of the env's current matches (-1 = padding)."""
        return np.asarray(self.env.team, dtype=np.int8).reshape(self.rows)

    # -- setup ---------------------------------------------------------------

    def _initial_nets(self) -> tuple[SpikeActor, Critic]:
        """Actor and critic of a new run; a spike critic from the init checkpoint
        becomes the base of a fleet critic when ``config.critic`` is "fleet". An
        init narrower than the sim's obs is widened with zero input columns, so it
        acts and values exactly as the init on the obs prefix."""
        width = self.config.obs_dim
        if self.config.init == INIT_SCRATCH:
            width = width or OBS_DIM
            fresh: Critic = SpikeCritic(obs_dim=width)
            return SpikeActor(obs_dim=width), as_critic_kind(fresh, self.config.critic)
        path = Path(self.config.init)
        if not path.is_file():
            raise FileNotFoundError(f"init policy {path} not found")
        actor, critic, _ = load_policy(path)
        width = width or actor.obs_dim
        if width < actor.obs_dim:
            raise ValueError(f"init {path} is {actor.obs_dim} wide, obs_dim {width}")
        if actor.obs_dim < width:
            print(
                f"init {path.name}: widening the actor and critic from "
                f"{actor.obs_dim} to {width} obs floats (new columns zero, "
                f"{self.config.new_input_lr_mult}x step size)",
                flush=True,
            )
            self.new_input_start = actor.obs_dim
            actor = widen_actor(actor, width)
            critic = widen_critic(critic, width)
        return actor, as_critic_kind(critic, self.config.critic)

    @staticmethod
    def _load_anchor(path: str) -> SpikeActor | None:
        """The frozen KL-anchor actor, or None without one.

        Raises:
            FileNotFoundError: ``path`` is set but missing.
        """
        if not path:
            return None
        if not Path(path).is_file():
            raise FileNotFoundError(f"kl_anchor checkpoint {path} not found")
        anchor, _, _ = load_policy(Path(path))
        anchor.eval()
        for param in anchor.parameters():
            param.requires_grad_(False)
        return anchor

    def _draw_learner_sides(self, envs: NDArray[np.integer]) -> None:
        """The learner's team for ``envs``' next episode (``config.learner_side``)."""
        if self.config.learner_side == "random" and len(envs):
            self.learner_team[envs] = self.rng.integers(0, 2, size=len(envs))

    def _split_drills(
        self, envs: NDArray[np.integer]
    ) -> tuple[NDArray[np.integer], NDArray[np.integer]]:
        """``envs`` whose current match is a drill, and the others."""
        rosters = self.env.rosters
        is_drill = np.fromiter(
            (rosters[int(i)].drill is not None for i in envs),
            dtype=np.bool_,
            count=len(envs),
        )
        return envs[is_drill], envs[~is_drill]

    def _note_new_matches(self, envs: NDArray[np.integer]) -> None:
        """Open ``envs``' new matches in the drill ledger."""
        for i in envs:
            self.drill_ledger.begin(int(i), self.env.rosters[int(i)].drill)

    def _start_new_matches_with_drills(
        self, envs: NDArray[np.integer], update: int
    ) -> None:
        """Opponents and learner sides for ``envs``' new matches: a drill fights the
        script with the learner on the ordered team, outside the quota."""
        drill_envs, match_envs = self._split_drills(envs)
        self.opponents.force_scripted(drill_envs)
        self.opponents.assign(match_envs, update, len(self.pool))
        self._draw_learner_sides(match_envs)
        self.learner_team[drill_envs] = 0
        self._note_new_matches(envs)

    def _make_optimisers(self) -> None:
        start, mult = self.new_input_start, self.config.new_input_lr_mult
        self.actor_opt = NewInputAdam(
            self.actor.parameters(),
            lr=self.config.actor_lr,
            boosted=first_layer_weights(self.actor) if start else [],
            start=start,
            mult=mult,
        )
        self.critic_opt = NewInputAdam(
            self.critic.parameters(),
            lr=self.config.critic_lr,
            boosted=first_layer_weights(self.critic) if start else [],
            start=start,
            mult=mult,
        )

    def request_stop(self) -> None:
        """Ask the loop to checkpoint and return after the current update
        (SIGTERM / SIGINT handlers call this)."""
        self._stop_requested = True

    # -- checkpoints ---------------------------------------------------------

    def save_checkpoint(self, path: Path) -> None:
        """Write a ``load_policy``-compatible checkpoint plus the train state.

        The file is written to a temporary name and renamed, so a kill during the
        write never leaves a truncated checkpoint.
        """
        tmp = path.with_suffix(".tmp")
        meta = {
            "kind": "spike_ppo",
            "sim_version": SIM_VERSION,
            "obs_dim": self.actor.obs_dim,
            "update": self.next_update,
            "config": self.config.to_dict(),
        }
        save_policy(tmp, self.actor, self.critic, meta)
        payload = torch.load(tmp, map_location="cpu", weights_only=True)
        payload["train"] = {
            "format": _TRAIN_STATE_FORMAT,
            "next_update": self.next_update,
            "elapsed": self.elapsed,
            "new_input_start": self.new_input_start,
            "actor_opt": self.actor_opt.state_dict(),
            "critic_opt": self.critic_opt.state_dict(),
            "torch_rng": torch.get_rng_state(),
            "numpy_rng": self.rng.bit_generator.state,
            "pool": [[u, _pool_name(p, path.parent)] for u, p in self.pool.entries],
        }
        if self.config.enemy_sampling != SAMPLING_UNIFORM:
            payload["train"]["enemy_results"] = self.opponents.results.state()
        torch.save(payload, tmp)
        os.replace(tmp, path)

    def _load_checkpoint(self, path: Path) -> None:
        payload = torch.load(path, map_location="cpu", weights_only=True)
        train = payload.get("train")
        if not isinstance(train, dict) or train.get("format") != _TRAIN_STATE_FORMAT:
            raise ValueError(f"{path} has no {_TRAIN_STATE_FORMAT} train state")
        self.actor, self.critic, _ = load_policy(path)
        if critic_kind(self.critic) != self.config.critic:
            raise ValueError(
                f"{path} has a {critic_kind(self.critic)} critic but the config asks "
                f"for {self.config.critic}"
            )
        self.new_input_start = int(train.get("new_input_start", 0))
        self._make_optimisers()
        self.actor_opt.load_state_dict(train["actor_opt"])
        self.critic_opt.load_state_dict(train["critic_opt"])
        torch.set_rng_state(train["torch_rng"])
        self.rng.bit_generator.state = train["numpy_rng"]
        self.next_update = int(train["next_update"])
        self.elapsed = float(train["elapsed"])
        self._resumed_enemy_results = list(train.get("enemy_results", []))
        ckpt_dir = path.parent
        self.pool = SnapshotPool(
            [(int(u), _pool_path(str(n), ckpt_dir)) for u, n in train["pool"]]
        )

    def _record_resumed_config(self) -> None:
        """Rewrite ``config.yaml`` if the resume changed the config, keeping the
        previous one as ``config_before_<update>.yaml``."""
        path = self.run_dir / "config.yaml"
        previous = read_config(path)
        if previous != self.config:
            os.replace(path, self.run_dir / f"config_before_{self.next_update}.yaml")
            write_config(self.config, path)

    # -- main loop -----------------------------------------------------------

    def train(
        self, on_update_end: Callable[[SpikeTrainer, dict[str, object]], None] | None
    ) -> int:
        """Run updates until ``n_updates`` or a stop request.

        Args:
            on_update_end: Called after each update with the trainer and its log
                row (tests use it to request a stop).

        Returns:
            The next update index (== ``n_updates`` when finished).
        """
        cfg = self.config
        while self.next_update < cfg.n_updates:
            row = self.run_update()
            if on_update_end is not None:
                on_update_end(self, row)
            done_updates = self.next_update
            periodic = done_updates % cfg.checkpoint_every == 0
            final = done_updates == cfg.n_updates
            if periodic or final or self._stop_requested:
                path = checkpoint_path(self.run_dir, cfg.tag, done_updates)
                path.parent.mkdir(parents=True, exist_ok=True)
                if periodic:
                    self.pool.add(done_updates, path)
                self.save_checkpoint(path)
            if self._stop_requested:
                break
        return self.next_update

    def run_update(self) -> dict[str, object]:
        """Collect one rollout, run PPO on it, append and return its log row."""
        cfg = self.config
        update = self.next_update
        t0 = time.perf_counter()
        tally, steps = self._collect(update)
        t1 = time.perf_counter()
        batch, reward_stats = self._prepare_batch()
        t2 = time.perf_counter()
        lr_scale = cfg.lr_scale(update)
        for group in self.actor_opt.param_groups:
            group["lr"] = cfg.actor_lr * lr_scale
        for group in self.critic_opt.param_groups:
            group["lr"] = cfg.critic_lr * lr_scale
        settings = UpdateSettings(
            clip_eps=cfg.clip(update),
            beta=cfg.beta(update),
            actor_frozen=cfg.actor_frozen(update),
            ent_coeff=cfg.ent_coeff,
            vf_coeff=cfg.vf_coeff,
            max_grad_norm=cfg.max_grad_norm,
            epochs=cfg.epochs,
            minibatch=cfg.minibatch,
            entropy_floor=cfg.entropy_floor,
            entropy_floor_coeff=cfg.entropy_floor_coeff,
            kl_anchor_coeff=cfg.kl_anchor_coeff,
            beta_heads=cfg.beta_heads,
        )
        metrics: dict[str, float | None] = dict.fromkeys(PPO_METRIC_KEYS)
        if batch.size:
            metrics.update(
                ppo_update(
                    self.actor,
                    self.critic,
                    self.actor_opt,
                    self.critic_opt,
                    batch,
                    settings,
                    self.anchor,
                )
            )
        else:
            # Every row masked (only possible when n_steps is shorter than the
            # arrival + control lock at episode start): no gradient step, the
            # PPO metrics of this row stay null.
            print(f"update {update}: no unmasked learner rows, PPO step skipped")
        t3 = time.perf_counter()
        self.storage.shift_tail()
        self.credit.shift_tail(cfg.n_steps)
        self.next_update += 1
        self.elapsed += t3 - t0
        row: dict[str, object] = {
            "update": self.next_update,
            "wall_time": self.elapsed,
            "update_seconds": t3 - t0,
            "rollout_seconds": t1 - t0,
            "gae_credit_seconds": t2 - t1,
            "ppo_seconds": t3 - t2,
            "samples": batch.size,
            "samples_per_s": batch.size / (t3 - t0),
            "sim_steps_per_s": steps * self.n_envs / (t1 - t0),
            "env_seed": self.env_seed,
            "clip_eps": settings.clip_eps,
            "beta": settings.beta,
            "actor_lr": cfg.actor_lr * lr_scale,
            "critic_lr": cfg.critic_lr * lr_scale,
            "new_input_lr": (
                cfg.actor_lr * lr_scale * cfg.new_input_lr_mult
                if self.new_input_start
                else None
            ),
            "actor_frozen": settings.actor_frozen,
            "snapshot_pool": self.pool.updates(),
            "order_reward_weight": cfg.order_reward_weight,
            "kl_anchor_coeff": cfg.kl_anchor_coeff,
        }
        row.update(reward_stats)
        row.update(tally.log_fields())
        row.update(metrics)
        if settings.actor_frozen and batch.size:
            row.update({"pg_loss": 0.0, "approx_kl": 0.0, "clip_fraction": 0.0})
        for name, count in self.opponents.counts().items():
            row[f"opponents_{name}"] = count
        missing = set(LOG_KEYS) - set(row)
        if missing:
            raise RuntimeError(f"log row is missing keys {sorted(missing)}")
        ordered = {key: row[key] for key in LOG_KEYS}
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a") as handle:
            handle.write(json.dumps(ordered) + "\n")
        return ordered

    # -- rollout -------------------------------------------------------------

    def _collect(self, update: int) -> tuple[EpisodeTally, int]:
        """Fill the storage's collect range; returns episode tally and steps."""
        env, store = self.env, self.storage
        rows, n_ships, n_envs = self.rows, self.n_ships, self.n_envs
        tally = EpisodeTally()
        collect = store.collect_range()
        self.actor.eval()
        for b in collect:
            kinds = self.opponents.kinds
            team = env.team.reshape(rows)
            hull = env.hull_id.reshape(rows)
            store.team[b] = team
            store.hull[b] = hull
            store.thruster[b] = env.thruster_mask.reshape(rows, N_THRUSTERS)
            store.turret[b] = env.turret_mask.reshape(rows, N_TURRETS)
            store.fixed[b] = env.fixed_turret.reshape(rows, N_TURRETS)
            masks = store.masks(slice(b, b + 1))
            self_play_env = np.repeat(kinds == OpponentKind.SELF, n_ships)
            side = np.repeat(self.learner_team, n_ships)
            # Strike craft only: capital ships keep their script's actions.
            pilot = (team >= 0) & ~np.isin(hull, self.capital_ids)
            own = pilot & (team == side)
            learner = own | (pilot & (team == 1 - side) & self_play_env)
            store.learner[b] = learner
            store.side[b] = own
            if self.drills_on:
                drill_rows = np.repeat(self.drill_ledger.running, n_ships)
                tally.side_rows += int(own.sum())
                tally.drill_rows += int((own & drill_rows).sum())
                if b % DRILL_TRACK_EVERY == 0 and self.drill_ledger.any_goto_running():
                    self.drill_ledger.see_arrivals(
                        np.asarray(env.order_tracks()["arrived"], dtype=np.bool_)
                    )
            policy_np = np.flatnonzero(learner)
            policy_rows = torch.from_numpy(policy_np)
            env_obs = env.obs.reshape(rows, OBS_DIM)
            store.has_order[b] = env_obs[:, HAS_ORDER_COL] > 0.5
            store.scripted_order[b] = env.scripted_order_rows().reshape(rows)
            store.order_hidden[b] = env.order_hidden_rows().reshape(rows)
            if self.config.beta_rows == "transit":
                store.transit[b] = transit_rows(env, env_obs)
            store.obs[b] = fit_obs(env_obs, self.obs_dim)
            store.act_mask[b] = env.act_mask.reshape(rows)
            # Script labels for every row (each hull's own script); team-1 scripted
            # rows keep them as their actions.
            store.labels[b] = env.scripted_actions().reshape(rows, ACTION_WIDTH)
            actions = store.actions[b]
            actions[:] = store.labels[b]
            obs_t = torch.from_numpy(store.obs[b])
            with torch.no_grad():
                out = self.actor.sample(obs_t[policy_rows], masks.index(policy_rows))
                values = self.critic.forward_set(
                    obs_t.reshape(n_envs, n_ships, self.obs_dim),
                    torch.from_numpy(team.astype(np.int64)).reshape(n_envs, n_ships),
                    _pairs(policy_np, n_ships),
                )
                actions[policy_np] = out.actions.to(torch.int8).numpy()
                if self.anchor is not None:
                    reference = self.anchor.head_log_softmax(
                        fit_obs(obs_t[policy_rows], self.anchor.obs_dim)
                    )
                    store.anchor_logp[b] = 0.0
                    store.anchor_logp[b, policy_np] = reference.flat().numpy()
                for index, envs in snapshot_groups(
                    kinds, self.opponents.snapshot
                ).items():
                    snap_np = _team_rows(
                        envs, team, n_ships, 1 - self.learner_team[envs]
                    )
                    snap_np = snap_np[pilot[snap_np]]
                    snap_rows = torch.from_numpy(snap_np)
                    snap_actor = self.pool.actor(index)
                    snap = snap_actor.sample(
                        fit_obs(obs_t[snap_rows], snap_actor.obs_dim),
                        masks.index(snap_rows),
                    )
                    actions[snap_np] = snap.actions.to(torch.int8).numpy()
            store.log_prob[b] = 0.0
            store.values[b] = 0.0
            store.log_prob[b, policy_np] = out.log_prob.numpy()
            store.values[b, policy_np] = values.numpy()
            env.actions[...] = actions.reshape(n_envs, n_ships, ACTION_WIDTH)
            rosters = list(env.rosters)
            _, rewards, dones, info = env.step()
            self.credit.record_step(
                b,
                info.prev_tick,
                info.prev_episode_count,
                info.prev_alive,
                info.hits,
                info.hit_count,
                unpaid_rows=(
                    store.has_order if self.config.hide_damage_when_ordered else None
                ),
            )
            self._record_step(b, rewards, dones, info)
            if self.drills_on:
                self.drill_ledger.add_hits(info.hits, info.hit_count)
            done_envs = np.flatnonzero(dones)
            if done_envs.size:
                lengths = info.prev_tick[done_envs].astype(np.int64) + 1
                for env_id, length in zip(done_envs, lengths):
                    roster = rosters[int(env_id)]
                    if roster.drill is not None:
                        tally.add_drill(*self.drill_ledger.finish(int(env_id)))
                        continue
                    learner_team = int(self.learner_team[env_id])
                    tally.add(
                        int(kinds[env_id]),
                        int(info.winner[env_id]),
                        int(length),
                        episode_class(roster, learner_team),
                        roster.n_ships,
                        learner_team,
                    )
                self.opponents.record_results(done_envs, info.winner, self.learner_team)
                if self.drills_on:
                    self._start_new_matches_with_drills(done_envs, update)
                else:
                    self.opponents.assign(done_envs, update, len(self.pool))
                    self._draw_learner_sides(done_envs)
        store.filled = store.length
        self._collected = collect
        return tally, len(collect)

    def _record_step(
        self,
        b: int,
        rewards: NDArray[np.float32],
        dones: NDArray[np.bool_],
        info: StepInfo,
    ) -> None:
        """Store rewards, dones and the logged reward split of buffer row ``b``."""
        store, cfg = self.storage, self.config
        rows, n_ships = self.rows, self.n_ships
        hits, hit_count, winner = info.hits, info.hit_count, info.winner
        prev_alive = info.prev_alive.reshape(rows)
        raw = rewards.reshape(rows).astype(np.float32)
        done_rows = np.repeat(dones, n_ships)
        store.dones[b] = done_rows

        dealt = store.dealt[b]
        taken = store.taken[b]
        n_hits = store.hits[b]
        dealt[:] = 0.0
        taken[:] = 0.0
        n_hits[:] = 0
        if hit_count.any():
            env_ids, k = np.nonzero(np.arange(hits.shape[1]) < hit_count[:, None])
            rec = hits[env_ids, k]
            weight = np.where(
                rec[:, HIT_SHIELD] != 0, SHIELD_DAMAGE_WEIGHT, HULL_DAMAGE_WEIGHT
            )
            amount = (weight * rec[:, HIT_DAMAGE_MILLI] / HIT_DAMAGE_SCALE).astype(
                np.float32
            )
            shooter = env_ids * n_ships + rec[:, HIT_SHOOTER]
            target = env_ids * n_ships + rec[:, HIT_TARGET]
            paid = prev_alive[shooter]
            np.add.at(dealt, shooter[paid], amount[paid])
            np.add.at(n_hits, shooter[paid], 1)
            hurt = prev_alive[target]
            np.add.at(taken, target[hurt], amount[hurt])

        terminal = store.terminal[b]
        terminal[:] = 0.0
        if dones.any():
            # The finished match's teams (the env already holds the next match's).
            team = store.team[b]
            win_rows = np.repeat(winner.astype(np.int64), n_ships)
            decided = done_rows & (win_rows >= 0) & (team >= 0)
            terminal[decided] = np.where(team[decided] == win_rows[decided], 1, -1)

        next_obs = self.env.obs.reshape(rows, OBS_DIM)
        outside = (next_obs[:, _ARENA_MARGIN_COL] < 0.0) & prev_alive & ~done_rows
        store.outside[b] = outside
        store.arena[b] = ARENA_PENALTY * outside
        # v3 collision hull damage is in the raw reward too; shield collision damage
        # is not exported, so it can add a few phantom shots on shielded hulls.
        crash = HULL_DAMAGE_WEIGHT * info.collision_damage.reshape(rows) * prev_alive
        residual = raw - dealt + taken - terminal - store.arena[b] + crash
        shots = np.maximum(np.rint(residual / FIRE_COST), 0).astype(np.int32)
        store.shots[b] = shots
        store.fire_cost[b] = FIRE_COST * shots

        shaping = store.shaping[b]
        shaping[:] = 0.0
        if cfg.tick_cost:
            shaping -= cfg.tick_cost * prev_alive
        if cfg.extra_arena_penalty:
            shaping -= cfg.extra_arena_penalty * outside
        store.team_reward[b] = raw + shaping
        order = store.order_reward[b]
        order[:] = info.order_rewards.reshape(rows)
        order[store.order_hidden[b]] = 0.0
        store.rewards[b] = store.team_reward[b] + cfg.order_reward_weight * order

    # -- GAE + batch ---------------------------------------------------------

    def _prepare_batch(self) -> tuple[PPOBatch, dict[str, object]]:
        """Credit, tail values, GAE and the batch; plus reward stats."""
        cfg, store = self.config, self.storage
        n_envs, n_ships = self.n_envs, self.n_ships
        new = slice(self._collected.start, self._collected.stop)
        stats = self._rollout_stats(new)
        self.credit.inject_into_rewards(store.rewards, 0, store.length)
        with torch.no_grad():
            if self._collected.start > 0:
                # Carried rows: re-value with the current critic.
                tail = slice(0, store.t_tail)
                flat = np.flatnonzero(store.learner[tail].reshape(-1))
                values = np.zeros(store.t_tail * self.rows, dtype=np.float32)
                values[flat] = self._values(
                    store.obs[tail], store.team[tail], flat
                ).numpy()
                store.values[tail] = values.reshape(store.t_tail, self.rows)
            team_now = np.asarray(self.env.team).reshape(1, self.rows)
            real = np.flatnonzero(team_now.reshape(-1) >= 0)
            last_values = np.zeros(self.rows, dtype=np.float32)
            last_values[real] = self._values(
                fit_obs(self.env.obs, self.obs_dim).reshape(1, self.rows, self.obs_dim),
                team_now,
                real,
            ).numpy()
        advantages, returns = compute_gae(
            store.rewards,
            store.values,
            store.dones,
            last_values,
            cfg.gamma,
            cfg.gae_lambda,
        )
        train = store.train_rows()
        flat = np.flatnonzero(train.reshape(-1))
        n = cfg.n_steps
        values = store.values[:n].reshape(-1)[flat]
        rets = returns[:n].reshape(-1)[flat]
        var = float(np.var(rets))
        stats["explained_variance"] = (
            float(1.0 - np.var(rets - values) / var) if var > 0 else 0.0
        )
        anchor_rows = ~store.has_order[:n].reshape(-1)[flat]
        stats["has_order_share"] = (
            float(1.0 - anchor_rows.mean()) if flat.size else None
        )
        if cfg.beta_rows == "ordered":
            pull_rows = store.scripted_order[:n].reshape(-1)[flat]
        elif cfg.beta_rows == "transit":
            pull_rows = store.transit[:n].reshape(-1)[flat]
        else:
            pull_rows = np.ones(flat.size, dtype=np.bool_)
        stats["beta_rows_share"] = float(pull_rows.mean()) if flat.size else None
        anchor_reference = None
        if self.anchor is not None:
            anchor_reference = torch.from_numpy(
                store.anchor_logp[:n].reshape(-1, N_LOGITS)[flat]
            )
        batch = PPOBatch(
            obs=torch.from_numpy(
                store.obs[:n].reshape(n * n_envs, n_ships, self.obs_dim)
            ),
            team=torch.from_numpy(
                store.team[:n].reshape(n * n_envs, n_ships).astype(np.int64)
            ),
            rows=_pairs(flat, n_ships),
            masks=store.masks(slice(0, n), flat),
            actions=torch.from_numpy(
                store.actions[:n].reshape(-1, ACTION_WIDTH)[flat].astype(np.int64)
            ),
            labels=torch.from_numpy(
                store.labels[:n].reshape(-1, ACTION_WIDTH)[flat].astype(np.int64)
            ),
            old_log_prob=torch.from_numpy(store.log_prob[:n].reshape(-1)[flat]),
            advantages=torch.from_numpy(advantages[:n].reshape(-1)[flat]),
            returns=torch.from_numpy(rets),
            anchor_rows=torch.from_numpy(anchor_rows),
            pull_rows=torch.from_numpy(pull_rows),
            anchor_reference=anchor_reference,
        )
        return batch, stats

    def _values(
        self,
        obs: NDArray[np.float32],
        team: NDArray[np.int8],
        flat: NDArray[np.int64],
    ) -> torch.Tensor:
        """Critic values of the flat rows ``flat`` of ``[L, R]`` buffer rows."""
        length = obs.shape[0]
        groups = length * self.n_envs
        return self.critic.forward_set(
            torch.from_numpy(obs).reshape(groups, self.n_ships, self.obs_dim),
            torch.from_numpy(team.astype(np.int64)).reshape(groups, self.n_ships),
            _pairs(flat, self.n_ships),
        )

    def _rollout_stats(self, new: slice) -> dict[str, object]:
        """Reward split and behaviour stats over the learner's team-0 rows of the
        newly collected steps (before credit is injected), overall and per hull."""
        store = self.storage
        team0 = store.side[new]
        active = store.act_mask[new] & team0
        samples = max(int(team0.sum()), 1)

        def mean(arr: NDArray[np.generic]) -> float:
            return float(arr[new][team0].sum()) / samples

        credit = self.credit.credit[store.side]
        shots = int(store.shots[new][team0].sum())
        hits = int(store.hits[new][team0].sum())
        n_active = max(int(active.sum()), 1)
        obs = store.obs[new]
        actions = store.actions[new]
        hull = store.hull[new]
        hull_samples: dict[str, int] = {}
        hull_hit_rate: dict[str, float | None] = {}
        hull_dealt: dict[str, float | None] = {}
        for hid, name in enumerate(self.hull_names):
            sel = active & (hull == hid)
            count = int(sel.sum())
            if not (team0 & (hull == hid)).any():
                continue
            hull_samples[name] = count
            h_shots = int(store.shots[new][team0 & (hull == hid)].sum())
            h_hits = int(store.hits[new][team0 & (hull == hid)].sum())
            hull_hit_rate[name] = h_hits / h_shots if h_shots else None
            hull_dealt[name] = (
                float(store.dealt[new][sel].sum()) / count if count else None
            )
        return {
            "reward_mean": mean(store.rewards),
            "reward_team": mean(store.team_reward),
            "reward_order": mean(store.order_reward),
            "reward_order_weighted": self.config.order_reward_weight
            * mean(store.order_reward),
            "reward_damage_dealt": mean(store.dealt),
            "reward_damage_taken": -mean(store.taken),
            "reward_fire_cost": mean(store.fire_cost),
            "reward_arena": mean(store.arena),
            "reward_terminal": mean(store.terminal),
            "reward_shaping": mean(store.shaping),
            "reward_credit_moved": float(np.clip(credit, 0.0, None).sum()) / samples,
            "credit_hits_moved": self.credit.n_moved,
            "credit_hits_kept": self.credit.n_kept,
            "main_engine_duty": float(obs[..., _MAIN_ENGINE_LEVEL_COL][active].sum())
            / n_active,
            "fire_rate": float((actions[..., _FIRE_COL][active] == 1).sum()) / n_active,
            "shots": shots,
            "hits": hits,
            "hit_rate": hits / shots if shots else None,
            "outside_arena_share": float(store.outside[new][team0].sum()) / n_active,
            "hull_samples": hull_samples,
            "hull_hit_rate": hull_hit_rate,
            "hull_damage_dealt": hull_dealt,
        }


def transit_rows(env: RustVecEnv, env_obs: NDArray[np.float32]) -> NDArray[np.bool_]:
    """[R] the env's transit rows (``RustVecEnv.transit_rows``), flat.

    Args:
        env: The env (SIM_VERSION 6).
        env_obs: [R, OBS_DIM] its current obs (the attack check reads them).

    Raises:
        RuntimeError: A transit row shows an attack order: the sim's transit flag
            must never cover attack rows (the pull would overwrite combat flying).
    """
    transit = env.transit_rows().reshape(-1)
    attacking = transit & (env_obs[:, ATTACK_COL] > 0.5)
    if attacking.any():
        raise RuntimeError(
            f"{int(attacking.sum())} transit rows show an attack order; the "
            "transit pull never applies to attack rows"
        )
    return transit


def first_layer_weights(module: SpikeActor | Critic) -> list[torch.Tensor]:
    """The weights that take the obs as input: the actor's first layer, a spike
    critic's first layer, or a fleet critic's base and encoder first layers."""
    if isinstance(module, FleetCritic):
        layers = [module.base.net[0], module.encoder[0]]
    else:
        layers = [module.net[0]]
    weights = []
    for layer in layers:
        if not isinstance(layer, nn.Linear):
            raise TypeError(f"first layer is {type(layer).__name__}, not Linear")
        weights.append(layer.weight)
    return weights


class NewInputAdam(torch.optim.Adam):
    """Adam whose steps on the input columns ``start:`` of ``boosted`` weights are
    ``mult`` times as large as the rest (run B3's 10x step size for the new inputs).

    Adam's step is elementwise ``-lr * m_hat / (sqrt(v_hat) + eps)`` (no weight
    decay here), so scaling those columns' step after each ``step()`` is exactly a
    separate parameter group at ``mult * lr`` for them, while the first-layer weight
    stays one tensor (checkpoints, ``load_policy`` and the web export are unchanged).
    The moment estimates and the state dict are plain Adam's.

    Args:
        params: Every parameter (as ``torch.optim.Adam``).
        lr: Base learning rate.
        boosted: First-layer weights ``[out, in]`` whose new columns are boosted.
        start: First boosted input column (the init's width).
        mult: Step-size multiple of the boosted columns.
        eps: Adam's epsilon.

    Raises:
        ValueError: A boosted weight is not 2-d or has no column ``start``.
    """

    def __init__(
        self,
        params: Iterable[nn.Parameter],
        lr: float,
        boosted: Sequence[torch.Tensor] = (),
        start: int = 0,
        mult: float = 1.0,
        eps: float = 1e-5,
    ) -> None:
        super().__init__(params, lr=lr, eps=eps)
        for weight in boosted:
            if weight.dim() != 2 or not 0 < start < weight.shape[1]:
                raise ValueError(
                    f"cannot boost columns {start}: of a {tuple(weight.shape)} weight"
                )
        self.boosted = list(boosted) if mult != 1.0 else []
        self.start = start
        self.mult = mult

    @torch.no_grad()
    def step(  # type: ignore[override]
        self, closure: Callable[[], float] | None = None
    ) -> float | None:
        """One Adam step, then the boosted columns' step scaled by ``mult``."""
        before = [w[:, self.start :].clone() for w in self.boosted]
        loss = super().step(closure)
        for weight, old in zip(self.boosted, before):
            new = weight[:, self.start :]
            new.copy_(old + self.mult * (new - old))
        return loss


def _pairs(flat: NDArray[np.int64], n_ships: int) -> torch.Tensor:
    """[K, 2] int64 ``(group, slot)`` of flat ``group * n_ships + slot`` indices."""
    flat64 = np.asarray(flat, dtype=np.int64)
    return torch.from_numpy(np.stack([flat64 // n_ships, flat64 % n_ships], axis=1))


def _team_rows(
    envs: NDArray[np.int64],
    team: NDArray[np.int8],
    n_ships: int,
    which: int | NDArray[np.integer],
) -> NDArray[np.int64]:
    """Flat rows of every ship of team ``which`` in ``envs`` (``team`` is [N * S];
    ``which`` is one team or one per env)."""
    rows = (envs[:, None] * n_ships + np.arange(n_ships)[None, :]).reshape(-1)
    wanted = np.repeat(np.broadcast_to(np.asarray(which), envs.shape), n_ships)
    return rows[team[rows] == wanted]


def _pool_name(path: str, ckpt_dir: Path) -> str:
    """How the train state records a pool entry: the bare name of a checkpoint of
    this run, else the path as given (a ``pool_seed`` entry)."""
    p = Path(path)
    return p.name if p.parent == ckpt_dir else path


def _pool_path(name: str, ckpt_dir: Path) -> str:
    """Inverse of ``_pool_name``."""
    return name if len(Path(name).parts) > 1 else str(ckpt_dir / name)
