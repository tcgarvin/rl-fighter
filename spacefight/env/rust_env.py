"""Thin typed wrapper over the Rust batched env ``rlf_sim.VecEnv`` (SIM_SPEC §10.1).

``RustVecEnv`` gives the v1 interface shape, ``reset() -> obs`` and
``step(actions) -> (obs, rewards, dones, info)``, over the zero-copy buffers of the
Rust env.

Views versus copies: by default every array returned by ``reset``/``step`` (``obs``,
``rewards``, ``dones`` and the ``StepInfo`` fields ``winner``, ``episode_count``,
``tick``, ``act_mask``, ``alive``, ``hits``, ``hit_count``, ``order_rewards``) is a
*view* of a buffer
owned by the Rust env, overwritten in place by the next ``step()`` or ``reset()``.
Store them with ``np.copy`` / ``StepInfo.copy()``, or construct the env with
``copy_outputs=True`` to get owned arrays from every call. The ``prev_*`` fields of
``StepInfo`` are always owned snapshots taken before the step.

Fleets. Every match has ``n_ships`` slots (``max_ships``, default the fleet size). A
match with fewer ships pads the remaining slots: team and hull id -1, zero obs,
``act_mask``/``alive`` and every slot mask false. With a ``roster_sampler`` each env
plays a freshly drawn ``Roster`` every episode (the next one is drawn and queued
when a match ends); ``team``, ``hull_id``, the slot masks and ``arena_radius`` then
describe each env's *current* match and change on the step that rebuilds it (for a
done env the step's returned arrays already belong to the new match; ``StepInfo``
carries ``prev_team`` for the finished one). Without a sampler they never change.

Missions and orders (SIM_VERSION 5). A ``Roster`` names its mission and each team's
commander mode (``"random"`` among them); ``set_next_roster`` passes both to the sim,
with the match's clock (``time_limit_s=None``: the mission's default). The env also
exports ``order_rewards`` beside ``rewards``.

SIM_VERSION 6 (orders redesigned: attack, defend, go-to). The obs grows to 583
(``ship_extras``, ``order_ships``; the first 403 floats are v5's); a team can be put
in hidden-order mode (``hide_orders``, per env build or per queued match); the env
exports ``order_transit``, ``ward_threat`` and ``ward_hull_lost`` and
``order_tracks()``. A ``Roster`` can carry ``hide_orders`` too, and
``RustVecEnv.rosters`` always holds what each match really has.

Go-to order pay's shaping term must use the trainer's discount, so ``RustVecEnv`` takes
``order_shaping_gamma`` and applies it to every match of the env (SIM_SPEC §8).

SIM_VERSION 8 (go-to deadlines). A go-to order may carry a deadline, an absolute match
tick (``NO_DEADLINE``, 0, for none): ``OpeningOrder.deadline_tick`` for a roster's
opening orders, ``"deadline"`` in the order dict of ``raw.submit_command`` for an
external commander mid-match. The obs grows to 587 (``order_time``: has_deadline, time
left, urgency, closeness; the first 583 floats are v7's), ``order_tracks()`` adds
``deadline`` and ``missed``, and ``RustVecEnv`` takes the pay for a go-to with a
deadline, ``goto_timed_bonus`` and ``goto_miss_penalty``, for every match of the env.

The learned commander (``docs/COMMANDER.md``): a team whose commander is
``"learned"`` decides every ``LEARNED_COMMAND_TICKS``. ``commander_due(team)`` says
which envs decide before the next step, ``commander_features(team)`` gives every env's
inputs and masks, ``submit_commander_actions(team, env_ids, actions)`` decodes the
decisions in the sim (per env and team hold state, reset with the match) and
``team_values()`` is the shaping potential.

A ``Roster`` can also place its ships (``start_layout``), carry the orders an external
commander opens with (``opening_orders``: the env queues them whenever that match is
built, once a match and only for those matches, and the sim applies them on the first
slow tick), its own clock, and drill rules (``docs/PILOT_TRAINING.md`` §2).

The extension is built with
``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields, replace
from pathlib import Path

import numpy as np
import rlf_sim
from numpy.typing import NDArray

from spacefight.env.rosters import DEATHMATCH, SCRIPTED, Roster, Sampler

SIM_VERSION: int = int(rlf_sim.SIM_VERSION)
OBS_DIM: int = rlf_sim.OBS_DIM
# SIM_VERSION 5: sim version -> the obs width a pilot of that version consumes
# (``obs[..., :width]``; v3/v4 pilots read the 385-float prefix, SIM_SPEC §0.3).
PILOT_OBS_DIMS: dict[int, int] = {
    int(k): int(v) for k, v in rlf_sim.PILOT_OBS_DIMS.items()
}
# Slots a stage B training env pads its rosters to (SIM_SPEC §10.1).
MAX_TRAIN_SHIPS: int = int(rlf_sim.MAX_TRAIN_SHIPS)
ACTION_WIDTH: int = rlf_sim.ACTION_WIDTH
MAX_HITS: int = rlf_sim.MAX_HITS
HIT_FIELDS: int = rlf_sim.HIT_FIELDS
MAX_REACTION_TICKS: int = rlf_sim.MAX_REACTION_TICKS
OBS_LAYOUT: dict[str, tuple[int, int]] = dict(rlf_sim.OBS_LAYOUT)
ACTION_LAYOUT: dict[str, tuple[int, int]] = dict(rlf_sim.ACTION_LAYOUT)
# has_order, the order block's first float (SIM_VERSION 5).
HAS_ORDER_COL: int = OBS_LAYOUT["order"][0]
# The attack one-hot right after has_order (the kind one-hot is ORDER_KINDS' order).
ATTACK_COL: int = HAS_ORDER_COL + 1
# ``order_tracks()["effective_kind"]`` / ``["standing_kind"]`` codes (SIM_VERSION 6).
TRACK_NONE, TRACK_ATTACK, TRACK_DEFEND, TRACK_GOTO = 0, 1, 2, 3
# SIM_VERSION 6: the v5 obs width (the prefix a v5 pilot reads), the per-ship extras
# record, the ships observed round the order point, and the order kinds in the
# obs one-hot's order (kind codes 1, 2, 3; 0 is none).
OBS_DIM_V5: int = int(rlf_sim.OBS_DIM_V5)
# SIM_VERSION 8: the v6 / v7 obs width (the prefix a v6 or v7 pilot reads), and the
# deadline tick of a go-to without a deadline.
OBS_DIM_V7: int = int(rlf_sim.OBS_DIM_V7)
NO_DEADLINE: int = int(rlf_sim.NO_DEADLINE)
SHIP_EXTRA_W: int = int(rlf_sim.SHIP_EXTRA_W)
N_ORDER_SHIPS: int = int(rlf_sim.N_ORDER_SHIPS)
ORDER_KINDS: tuple[str, ...] = tuple(rlf_sim.ORDER_KINDS)

# Number of fixed-width records in each obs block (SIM_SPEC §7.2), from the sim.
OBS_SLOTS: dict[str, int] = dict(rlf_sim.OBS_SLOTS)


# Default reaction delay in ticks (SIM_SPEC §5 stage 3; MatchConfig default).
DEFAULT_REACTION_TICKS = 2
# Default discount of go-to order pay's shaping term (MatchConfig default). A trainer
# passes its own discount instead (SIM_SPEC §8).
DEFAULT_ORDER_SHAPING_GAMMA: float = float(rlf_sim.ORDER_SHAPING_GAMMA)
# Default order pay of a go-to with a deadline (MatchConfig defaults, SIM_VERSION 8):
# for arriving by the deadline tick, and the one-shot charge for missing it.
DEFAULT_GOTO_TIMED_BONUS: float = float(rlf_sim.ORDER_TIMED_ARRIVAL_BONUS)
DEFAULT_GOTO_MISS_PENALTY: float = float(rlf_sim.ORDER_MISS_PENALTY)

# Number of choices of each action head (SIM_SPEC §7.1): values are 0..n-1.
ACTION_HEAD_CHOICES: dict[str, int] = {"throttle": 3, "slew": 3, "fire": 2, "power": 7}

# Largest valid value of each of the ACTION_WIDTH action columns.
ACTION_HIGHS: NDArray[np.int8] = np.concatenate(
    [
        np.full(ACTION_LAYOUT[name][1], ACTION_HEAD_CHOICES[name] - 1, dtype=np.int8)
        for name in ACTION_LAYOUT
    ]
)

# Winner value of a match that has not ended on this step.
WINNER_NONE = -2


def obs_block(
    obs: NDArray[np.float32], name: str, split_slots: bool = False
) -> NDArray[np.float32]:
    """Slice the obs block ``name`` out of ``obs[..., OBS_DIM]`` (a view).

    Args:
        obs: Observations with OBS_DIM as the last axis.
        name: Key of ``OBS_LAYOUT`` (e.g. "self", "ships").
        split_slots: Reshape the block to ``[..., slots, width // slots]``.

    Raises:
        KeyError: Unknown block name.
        ValueError: Last axis is not OBS_DIM.
    """
    if obs.shape[-1] != OBS_DIM:
        raise ValueError(f"obs last axis must be {OBS_DIM}, got {obs.shape}")
    offset, width = OBS_LAYOUT[name]
    block = obs[..., offset : offset + width]
    if split_slots:
        slots = OBS_SLOTS[name]
        return block.reshape(*block.shape[:-1], slots, width // slots)
    return block


def action_block(actions: NDArray[np.int8], name: str) -> NDArray[np.int8]:
    """Slice the action head ``name`` out of ``actions[..., ACTION_WIDTH]`` (a view).

    Raises:
        KeyError: Unknown head name.
        ValueError: Last axis is not ACTION_WIDTH.
    """
    if actions.shape[-1] != ACTION_WIDTH:
        raise ValueError(
            f"actions last axis must be {ACTION_WIDTH}, got {actions.shape}"
        )
    offset, width = ACTION_LAYOUT[name]
    return actions[..., offset : offset + width]


@dataclass(frozen=True)
class StepInfo:
    """Per-step extras of ``RustVecEnv.step`` (shapes for N envs, S ships).

    Fields marked *view* alias env buffers and are overwritten by the next step;
    see the module docstring.

    Attributes:
        winner: [N] i8 view: 0/1 winning team, -1 draw, -2 (WINNER_NONE) still running.
        episode_count: [N] u32 view: episode generation after the step (auto-reset
            increments it on done envs).
        tick: [N] u32 view: tick after the step (0 for an env that just reset).
        act_mask: [N, S] bool view: whether the action chosen from this obs will be
            applied (alive, present, and ``tick + 1 + d >= control_lock_until``,
            SIM_SPEC §7.1). A masked row has no effect at all; exclude it from the
            loss.
        alive: [N, S] bool view, after the step (fresh match for done envs).
        hits: [N, MAX_HITS, HIT_FIELDS] i32 view: (shooter, target, fire_tick,
            damage*1000, shield, decision_tick) rows of hits that landed this step;
            ``decision_tick`` is the post-step tick of the obs the firing action was
            chosen from (``fire_tick - 1 - d``).
        hit_count: [N] i32 view: valid rows of ``hits``.
        collision_damage: [N, S] f32 view: hull damage each ship took from ship-ship
            collisions this step, after impact arcs (SIM_VERSION 3, SIM_SPEC §5.5).
            Collisions make no ``hits`` rows and credit nobody.
        order_rewards: [N, S] f32 view: the order reward of this step (SIM_VERSION 5,
            SIM_SPEC §8), separate from ``rewards``; the trainer weights it.
        thruster_mask: [N, S, 8] bool view, of the current match.
        turret_mask: [N, S, 6] bool view, of the current match.
        fixed_turret: [N, S, 6] bool view, of the current match (slew head
            meaningless).
        prev_tick: [N] u32 owned: tick before the step.
        prev_episode_count: [N] u32 owned: episode_count before the step (the
            episode the step's hits and rewards belong to).
        prev_alive: [N, S] bool owned: alive before the step.
        prev_team: [N, S] i8 owned: team of each slot before the step (the
            finished match's teams for a done env; -1 = padding).
    """

    winner: NDArray[np.int8]
    episode_count: NDArray[np.uint32]
    tick: NDArray[np.uint32]
    act_mask: NDArray[np.bool_]
    alive: NDArray[np.bool_]
    hits: NDArray[np.int32]
    hit_count: NDArray[np.int32]
    collision_damage: NDArray[np.float32]
    order_rewards: NDArray[np.float32]
    thruster_mask: NDArray[np.bool_]
    turret_mask: NDArray[np.bool_]
    fixed_turret: NDArray[np.bool_]
    prev_tick: NDArray[np.uint32]
    prev_episode_count: NDArray[np.uint32]
    prev_alive: NDArray[np.bool_]
    prev_team: NDArray[np.int8]

    def copy(self) -> StepInfo:
        """Return a StepInfo whose arrays are all owned copies."""
        return StepInfo(**{f.name: getattr(self, f.name).copy() for f in fields(self)})


class RustVecEnv:
    """v1-style batched env over ``rlf_sim.VecEnv`` with auto-reset.

    The env is ready on construction (every match at tick 0, episode 0); ``reset()``
    rebuilds all matches with episode_count 0.

    Args:
        assets_dir: Directory holding ``hulls/`` and ``weapons.yaml``.
        n_envs: Number of parallel matches.
        fleets: ``[[team 0 hulls], [team 1 hulls]]``; ship slots are team 0's
            hulls then team 1's. With a ``roster_sampler`` it only sizes the
            constructor's throwaway first build (any valid fleet will do).
        seed: Base seed; match i, episode e uses ``split(seed, i, e)``.
        arena_radius: Arena radius in metres.
        time_limit_s: Match time limit in seconds.
        n_threads: Rayon worker threads (0 = rayon default).
        record_events: Record per-step events (``events()``; debug only).
        reaction_ticks: Ticks between choosing an action and the sim applying it,
            ``0..=MAX_REACTION_TICKS`` (a hull's own value overrides it).
        copy_outputs: Return owned copies instead of buffer views.
        max_ships: Ship slots per match (default: the size of ``fleets``, or the
            sampler's ``max_ships``).
        roster_sampler: Draw every env's roster per episode (module docstring);
            each roster's arena radius is the shared ``arena_radius_for`` rule and
            ``arena_radius`` is ignored.
        commanders: Each team's commander mode of the constructor's first build
            (a queued ``Roster`` names its own).
        hide_orders: Per team, hidden-order mode (SIM_VERSION 6): that team's obs
            shows no order. Holds for every match unless ``set_next_roster`` overrides
            it; a queued ``Roster`` can hide a team on top of it.
        order_shaping_gamma: Discount of go-to order pay's shaping term, in (0, 1],
            for every match of the env, whatever roster is queued. A trainer passes
            its own discount: anything else pays a pilot to stay away from the point
            (SIM_SPEC §8).
        goto_timed_bonus: Order pay for arriving at a go-to with a deadline by its
            deadline tick (SIM_VERSION 8), finite and >= 0, for every match of the env.
        goto_miss_penalty: Order pay charged once, as its negative, when a go-to's
            deadline passes before the ship has arrived, finite and >= 0, for every
            match of the env.

    Raises:
        ValueError: Invalid arguments or assets (from ``rlf_sim``), or a sampled
            roster that does not fit ``max_ships``.
    """

    def __init__(
        self,
        assets_dir: str | Path,
        n_envs: int,
        fleets: Sequence[Sequence[str]],
        seed: int,
        arena_radius: float = 450.0,
        time_limit_s: float = 90.0,
        n_threads: int = 0,
        record_events: bool = False,
        reaction_ticks: int = DEFAULT_REACTION_TICKS,
        copy_outputs: bool = False,
        max_ships: int | None = None,
        roster_sampler: Sampler | None = None,
        commanders: Sequence[str] = (SCRIPTED, SCRIPTED),
        hide_orders: tuple[bool, bool] = (False, False),
        order_shaping_gamma: float = DEFAULT_ORDER_SHAPING_GAMMA,
        goto_timed_bonus: float = DEFAULT_GOTO_TIMED_BONUS,
        goto_miss_penalty: float = DEFAULT_GOTO_MISS_PENALTY,
    ) -> None:
        if max_ships is None and roster_sampler is not None:
            max_ships = roster_sampler.max_ships
        modes = tuple(commanders)
        if len(modes) != 2:
            raise ValueError(f"commanders must name two modes, got {modes}")
        self._env = rlf_sim.VecEnv(
            str(assets_dir),
            n_envs,
            [list(team) for team in fleets],
            seed,
            arena_radius=arena_radius,
            time_limit_s=time_limit_s,
            n_threads=n_threads,
            record_events=record_events,
            reaction_ticks=reaction_ticks,
            max_ships=max_ships,
            commanders=list(modes),
            hide_orders=list(_hide_pair(hide_orders)),
            order_shaping_gamma=order_shaping_gamma,
            goto_timed_bonus=goto_timed_bonus,
            goto_miss_penalty=goto_miss_penalty,
        )
        self.fleets: tuple[tuple[str, ...], ...] = tuple(tuple(t) for t in fleets)
        self.reaction_ticks = reaction_ticks
        self.time_limit_s = time_limit_s
        self.copy_outputs = copy_outputs
        self.roster_sampler = roster_sampler
        self.commanders: tuple[str, str] = (modes[0], modes[1])
        self._default_hide = _hide_pair(hide_orders)
        fixed = Roster.of(
            fleets[0],
            fleets[1],
            commanders=self.commanders,
            hide_orders=self._default_hide,
        )
        # Roster of each env's current match and of its queued next match.
        self.rosters: list[Roster] = [fixed] * n_envs
        self._next: list[Roster] = [fixed] * n_envs
        if roster_sampler is not None:
            for i in range(n_envs):
                self.set_next_roster(i, roster_sampler.sample())
            self.reset()

    # -- static description -------------------------------------------------

    @property
    def raw(self) -> rlf_sim.VecEnv:
        """The wrapped ``rlf_sim.VecEnv`` (render_state, state_hash, buffers)."""
        return self._env

    @property
    def n_envs(self) -> int:
        """Number of parallel matches (N)."""
        return int(self._env.n_envs)

    @property
    def n_ships(self) -> int:
        """Ship slots per match (S)."""
        return int(self._env.n_ships)

    @property
    def dt(self) -> float:
        """Seconds per step."""
        return float(self._env.dt)

    @property
    def order_shaping_gamma(self) -> float:
        """Discount of go-to order pay's shaping term in this env's matches, as the
        sim holds it (f32)."""
        return float(self._env.order_shaping_gamma)

    @property
    def goto_timed_bonus(self) -> float:
        """Order pay for arriving at a go-to with a deadline in time, in this env's
        matches, as the sim holds it (f32)."""
        return float(self._env.goto_timed_bonus)

    @property
    def goto_miss_penalty(self) -> float:
        """Order pay charged once for missing a go-to's deadline, in this env's
        matches, as the sim holds it (f32)."""
        return float(self._env.goto_miss_penalty)

    @property
    def obs_layout(self) -> dict[str, tuple[int, int]]:
        """Obs block name -> (offset, width); a fresh dict."""
        return dict(OBS_LAYOUT)

    @property
    def action_layout(self) -> dict[str, tuple[int, int]]:
        """Action head name -> (offset, width); a fresh dict."""
        return dict(ACTION_LAYOUT)

    @property
    def team(self) -> NDArray[np.int8]:
        """[N, S] team of each slot of the current match, -1 = padding (view)."""
        return self._env.team

    @property
    def hull_id(self) -> NDArray[np.int16]:
        """[N, S] hull id of each slot of the current match, -1 = padding (view)."""
        return self._env.hull_id

    @property
    def thruster_mask(self) -> NDArray[np.bool_]:
        """[N, S, 8] which thruster slots exist (view, current match)."""
        return self._env.thruster_mask

    @property
    def turret_mask(self) -> NDArray[np.bool_]:
        """[N, S, 6] which turret slots exist (view, current match)."""
        return self._env.turret_mask

    @property
    def fixed_turret(self) -> NDArray[np.bool_]:
        """[N, S, 6] turret slots that are fixed guns (view, current match)."""
        return self._env.fixed_turret

    @property
    def arena_radius(self) -> NDArray[np.float32]:
        """[N] arena radius of each env's current match, metres (view)."""
        return self._env.arena_radius

    def set_next_roster(
        self,
        i: int,
        roster: Roster,
        arena_radius: float | None = None,
        time_limit_s: float | None = None,
        hide_orders: tuple[bool, bool] | None = None,
    ) -> None:
        """Queue ``roster`` (teams, mission, commanders, hidden orders) for env
        ``i``'s next match.

        Args:
            i: Env index.
            roster: The match.
            arena_radius: Arena radius in metres; ``None`` uses the shared rule
                (``roster.arena_radius``). Overrides are for surveys only: training
                and the live page use the rule.
            time_limit_s: The match's clock; ``None`` is the roster's own clock if it
                has one, else the mission's default for a mission roster, else the
                env's ``time_limit_s``.
            hide_orders: Per team, hidden-order mode for this match (SIM_VERSION 6).
                ``None``: a team is hidden if the roster or the env hides it, so an
                eval's hidden env stays hidden and a roster's condition still holds.

        Raises:
            ValueError: The roster does not fit ``n_ships`` or its mission, or names
                unknown hulls or commander modes.
            IndexError: ``i`` out of range.
        """
        radius = roster.arena_radius if arena_radius is None else arena_radius
        mission = None if roster.mission == DEATHMATCH else roster.mission
        if hide_orders is None:
            hide = (
                roster.hide_orders[0] or self._default_hide[0],
                roster.hide_orders[1] or self._default_hide[1],
            )
        else:
            hide = _hide_pair(hide_orders)
        if time_limit_s is None and roster.time_limit_s > 0:
            time_limit_s = roster.time_limit_s
        self._env.set_next_roster(
            i,
            roster.fleets(),
            radius,
            mission=mission,
            commanders=list(roster.commanders),
            time_limit_s=time_limit_s,
            hide_orders=list(hide),
            start_layout=[s.row() for s in roster.start_layout] or None,
            drill=roster.drill is not None,
        )
        self._next[i] = (
            roster if hide == roster.hide_orders else replace(roster, hide_orders=hide)
        )

    # -- live buffers ---------------------------------------------------------

    @property
    def obs(self) -> NDArray[np.float32]:
        """[N, S, OBS_DIM] current observations (view)."""
        return self._env.obs

    @property
    def actions(self) -> NDArray[np.int8]:
        """[N, S, ACTION_WIDTH] action buffer read by ``step()`` (view, writable)."""
        return self._env.actions

    @property
    def act_mask(self) -> NDArray[np.bool_]:
        """[N, S] whether each ship's next action counts (view)."""
        return self._env.act_mask

    @property
    def end_reason(self) -> NDArray[np.int8]:
        """[N] ``rlf_sim.END_REASONS`` code of a match that ended on the last step,
        0 while running (view)."""
        return self._env.end_reason

    @property
    def order_rewards(self) -> NDArray[np.float32]:
        """[N, S] order reward of the last step (SIM_SPEC §8, v5; view, or a copy
        with ``copy_outputs``), alongside ``rewards``: the trainer weights it by
        ``w``. ``StepInfo.order_rewards`` is the same buffer."""
        return self._out(self._env.order_rewards)

    @property
    def order_transit(self) -> NDArray[np.bool_]:
        """[N, S] the slot's effective order is a go-to not yet arrived or a defend
        whose ward has no threat (SIM_VERSION 6), as of the current obs (view, or a
        copy with ``copy_outputs``). Raw: the trainer picks the rows to pull."""
        return self._out(self._env.order_transit)

    @property
    def ward_threat(self) -> NDArray[np.bool_]:
        """[N, S, S] ``[i, w, e]``: ship ``e`` was in ship ``w``'s threat set in the
        last step (SIM_VERSION 6; view, or a copy with ``copy_outputs``)."""
        return self._out(self._env.ward_threat)

    @property
    def ward_hull_lost(self) -> NDArray[np.float32]:
        """[N, S] hull fraction each ship lost in the last step (SIM_VERSION 6;
        view, or a copy with ``copy_outputs``)."""
        return self._out(self._env.ward_hull_lost)

    def order_tracks(self) -> dict[str, NDArray]:
        """Every slot's order instance now (SIM_VERSION 6; new arrays):
        ``standing_kind``/``effective_kind`` [N, S] int8 (0 none, 1 attack, 2
        defend, 3 goto), ``target`` [N, S] int16 (-1), ``point`` [N, S, 2] f32,
        ``radius`` [N, S] f32, ``arrived`` [N, S] bool, ``instance_start`` [N, S]
        uint32, and (SIM_VERSION 8) ``deadline`` [N, S] uint32 (the instance's go-to
        deadline tick, ``NO_DEADLINE`` for none) and ``missed`` [N, S] bool (the
        deadline passed before the ship arrived)."""
        return dict(self._env.order_tracks())

    # -- the learned commander (docs/COMMANDER.md) ---------------------------

    def commander_due(self, team: int) -> NDArray[np.bool_]:
        """[N] bool, new: whether each env's next step is ``team``'s slow tick (a
        ``"learned"`` team every ``LEARNED_COMMAND_TICKS``, others every
        ``COMMAND_TICKS``).

        Raises:
            ValueError: ``team`` is not 0 or 1.
        """
        return self._env.commander_due(team)

    def commander_features(self, team: int) -> dict[str, NDArray]:
        """Team ``team``'s commander inputs and masks in every env now (new arrays;
        ``E = MAX_SHIPS`` entities): ``globals`` [N, 53] f32, ``entities`` [N, E, 40]
        f32, ``valid`` [N, E] bool, ``launch_mask`` [N, 3], ``waypoint_mask`` [N, 26],
        ``squad_mask`` [N, E, 6], ``order_mask`` [N, 4, 5], ``target_mask`` [N, E],
        ``ward_mask`` [N, E] (bool).

        Raises:
            ValueError: ``team`` is not 0 or 1.
        """
        return dict(self._env.commander_features(team))

    def submit_commander_actions(
        self,
        team: int,
        env_ids: Sequence[int] | NDArray[np.integer],
        actions: NDArray[np.integer],
    ) -> NDArray[np.int32]:
        """Decode and queue team ``team``'s decisions for the envs ``env_ids``.

        Args:
            team: 0 or 1.
            env_ids: [K] env indices, each due (``commander_due(team)``) and with a
                ``"learned"`` (or ``"external"``) commander on that team.
            actions: [K, ACTION_DIM] integers (``docs/COMMANDER.md`` "Outputs").

        Returns:
            [K] int32: the ships whose order each decision changed.

        Raises:
            ValueError: A shape mismatch, a repeated env, an env not due or whose
                team takes no decisions, or a value outside its head's choices; no
                env is changed then.
            IndexError: An env index out of range.
        """
        ids = np.ascontiguousarray(env_ids, dtype=np.int64).reshape(-1)
        acts = np.ascontiguousarray(actions, dtype=np.int32)
        return self._env.submit_commander_actions(team, ids, acts)

    def commander_locks(self, i: int, team: int) -> dict[str, object]:
        """Team ``team``'s commander hold state in env ``i`` (``decisions``,
        ``squad_hold_left``, ``ship_hold_left``, ``changed_ships``,
        ``last_launch_tick``)."""
        return dict(self._env.commander_locks(i, team))

    def team_values(self) -> NDArray[np.float32]:
        """[N, 2] f32, new: each env's team values now (hull + half shield of every
        ship still in the match)."""
        return self._env.team_values()

    # -- stepping -------------------------------------------------------------

    def reset(self) -> NDArray[np.float32]:
        """Rebuild every match at episode 0 (queued rosters apply) and return the
        first observations. With a sampler every env then queues a fresh draw."""
        self._env.reset()
        self._advance_rosters(range(self.n_envs))
        return self._out(self._env.obs)

    def _advance_rosters(self, envs: Sequence[int] | NDArray[np.integer]) -> None:
        """Envs that were just rebuilt: the queued roster is now current and its
        opening orders go in; with a sampler, draw and queue the next one."""
        for i in envs:
            i = int(i)
            self.rosters[i] = self._next[i]
            for order in self.rosters[i].opening_orders:
                self._env.submit_command(i, order.team, order.command())
            if self.roster_sampler is not None:
                self.set_next_roster(i, self.roster_sampler.sample())

    def step(
        self, actions: NDArray[np.int8] | None = None
    ) -> tuple[NDArray[np.float32], NDArray[np.float32], NDArray[np.bool_], StepInfo]:
        """Advance every match one tick.

        Args:
            actions: int8 ``[N, S, ACTION_WIDTH]`` actions, copied into the action
                buffer; ``None`` steps with what is already in ``self.actions``
                (e.g. after ``scripted_actions()``). Out-of-range values are
                clamped by the sim.

        Returns:
            ``(obs [N,S,OBS_DIM] f32, rewards [N,S] f32, dones [N] bool, info)``.
            For a done env, ``rewards`` include the terminal term and ``obs`` is
            the fresh match's first observation.

        Raises:
            ValueError: Wrong actions shape or dtype (from ``rlf_sim``).
        """
        env = self._env
        prev_tick = env.tick.copy()
        prev_episode = env.episode_count.copy()
        prev_alive = env.alive.copy()
        prev_team = env.team.copy()
        if actions is None:
            env.step()
        else:
            env.step(actions)
        info = StepInfo(
            winner=env.winner,
            episode_count=env.episode_count,
            tick=env.tick,
            act_mask=env.act_mask,
            alive=env.alive,
            hits=env.hits,
            hit_count=env.hit_count,
            collision_damage=env.collision_damage,
            order_rewards=env.order_rewards,
            thruster_mask=env.thruster_mask,
            turret_mask=env.turret_mask,
            fixed_turret=env.fixed_turret,
            prev_tick=prev_tick,
            prev_episode_count=prev_episode,
            prev_alive=prev_alive,
            prev_team=prev_team,
        )
        done_envs = np.flatnonzero(env.dones)
        if done_envs.size:
            self._advance_rosters(done_envs)
        if self.copy_outputs:
            info = info.copy()
        return self._out(env.obs), self._out(env.rewards), self._out(env.dones), info

    def scripted_actions(self, team: int | None = None) -> NDArray[np.int8]:
        """Write the scripted controller's actions into ``self.actions``.

        Args:
            team: 0 or 1 to fill only that team's rows; ``None`` fills every ship.

        Returns:
            The action buffer (a view, or a copy with ``copy_outputs``), e.g. as
            behaviour-cloning targets for the current ``obs``.

        Raises:
            ValueError: ``team`` is not 0, 1 or None.
        """
        if team is None:
            self._env.scripted_actions()
        else:
            self._env.scripted_actions(team=team)
        return self._out(self._env.actions)

    def scripted_order_rows(self) -> NDArray[np.bool_]:
        """[N, S] bool, owned: slots of the current matches whose obs shows an order
        (``has_order``) that the slot's script flies, so ``scripted_actions()`` is an
        order-following label there (``Roster.scripts_follow_orders``: not the
        scripted commander's advisory deathmatch orders). Capital ships' waypoints
        read as holds and count too; callers keep the rows they train."""
        follows = np.asarray(
            [r.scripts_follow_orders() for r in self.rosters], dtype=np.bool_
        )
        team = np.asarray(self._env.team, dtype=np.int64)
        by_slot = np.take_along_axis(follows, np.clip(team, 0, 1), axis=1)
        has_order = self._env.obs[..., HAS_ORDER_COL] > 0.5
        return has_order & by_slot & (team >= 0)

    def order_hidden_rows(self) -> NDArray[np.bool_]:
        """[N, S] bool, owned: slots of the current matches whose team has its orders
        hidden (``Roster.hide_orders``). The sim still computes ``order_rewards`` for
        them (SIM_SPEC §7.2), so a trainer that pays only for orders it shows masks
        these rows out. Padding is never hidden."""
        hidden = np.asarray([r.hide_orders for r in self.rosters], dtype=np.bool_)
        team = np.asarray(self._env.team, dtype=np.int64)
        by_slot = np.take_along_axis(hidden, np.clip(team, 0, 1), axis=1)
        return by_slot & (team >= 0)

    def transit_rows(self) -> NDArray[np.bool_]:
        """[N, S] bool, owned (SIM_VERSION 6): ``order_transit`` slots whose script
        flies the order (``Roster.scripts_follow_orders``), so ``scripted_actions()``
        is the order-following script's transit flying there: the rows of the
        transit-only script pull (``docs/M3_PLAN.md`` "Stage B3"). A hidden team has
        none: its pilots cannot see the order they would be pulled toward. Like the
        obs, it describes the current matches (a done env's new match after a
        step)."""
        follows = np.asarray(
            [r.scripts_follow_orders() for r in self.rosters], dtype=np.bool_
        )
        team = np.asarray(self._env.team, dtype=np.int64)
        by_slot = np.take_along_axis(follows, np.clip(team, 0, 1), axis=1)
        transit = np.asarray(self._env.order_transit, dtype=np.bool_)
        return transit & by_slot & (team >= 0) & ~self.order_hidden_rows()

    def events(self) -> NDArray[np.float32]:
        """Copied ``[E, 9]`` events of the last step (needs ``record_events``)."""
        return self._env.events()

    def _out(self, arr: NDArray) -> NDArray:
        return arr.copy() if self.copy_outputs else arr


def _hide_pair(hide_orders: Sequence[bool]) -> tuple[bool, bool]:
    """``hide_orders`` as two bools.

    Raises:
        ValueError: Not two values.
    """
    pair = tuple(bool(h) for h in hide_orders)
    if len(pair) != 2:
        raise ValueError(f"hide_orders must name two teams, got {hide_orders}")
    return (pair[0], pair[1])
