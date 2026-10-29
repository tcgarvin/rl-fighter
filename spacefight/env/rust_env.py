"""Thin typed wrapper over the Rust batched env ``rlf_sim.VecEnv`` (SIM_SPEC §10.1).

``RustVecEnv`` gives the v1 interface shape, ``reset() -> obs`` and
``step(actions) -> (obs, rewards, dones, info)``, over the zero-copy buffers of the
Rust env.

Views versus copies: by default every array returned by ``reset``/``step`` (``obs``,
``rewards``, ``dones`` and the ``StepInfo`` fields ``winner``, ``episode_count``,
``tick``, ``act_mask``, ``alive``, ``hits``, ``hit_count``) is a *view* of a buffer
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

The extension is built with
``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, fields
from pathlib import Path

import numpy as np
import rlf_sim
from numpy.typing import NDArray

from spacefight.env.rosters import Roster, RosterSampler

SIM_VERSION: int = int(rlf_sim.SIM_VERSION)
OBS_DIM: int = rlf_sim.OBS_DIM
ACTION_WIDTH: int = rlf_sim.ACTION_WIDTH
MAX_HITS: int = rlf_sim.MAX_HITS
HIT_FIELDS: int = rlf_sim.HIT_FIELDS
MAX_REACTION_TICKS: int = rlf_sim.MAX_REACTION_TICKS
OBS_LAYOUT: dict[str, tuple[int, int]] = dict(rlf_sim.OBS_LAYOUT)
ACTION_LAYOUT: dict[str, tuple[int, int]] = dict(rlf_sim.ACTION_LAYOUT)

# Number of fixed-width records in each obs block (SIM_SPEC §7.2), from the sim.
OBS_SLOTS: dict[str, int] = dict(rlf_sim.OBS_SLOTS)

# Default reaction delay in ticks (SIM_SPEC §5 stage 3; MatchConfig default).
DEFAULT_REACTION_TICKS = 2

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
        max_ships: Ship slots per match (default: the size of ``fleets``, or
            ``MAX_SHIPS`` with a sampler).
        roster_sampler: Draw every env's roster per episode (module docstring);
            each roster's arena radius is the shared ``arena_radius_for`` rule and
            ``arena_radius`` is ignored.

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
        roster_sampler: RosterSampler | None = None,
    ) -> None:
        if max_ships is None and roster_sampler is not None:
            max_ships = int(rlf_sim.MAX_SHIPS)
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
        )
        self.fleets: tuple[tuple[str, ...], ...] = tuple(tuple(t) for t in fleets)
        self.reaction_ticks = reaction_ticks
        self.copy_outputs = copy_outputs
        self.roster_sampler = roster_sampler
        fixed = Roster.of(fleets[0], fleets[1])
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

    def set_next_roster(self, i: int, roster: Roster) -> None:
        """Queue ``roster`` (arena from the shared rule) for env ``i``'s next match.

        Raises:
            ValueError: The roster does not fit ``n_ships`` or names unknown hulls.
            IndexError: ``i`` out of range.
        """
        self._env.set_next_roster(i, roster.fleets(), roster.arena_radius)
        self._next[i] = roster

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

    # -- stepping -------------------------------------------------------------

    def reset(self) -> NDArray[np.float32]:
        """Rebuild every match at episode 0 (queued rosters apply) and return the
        first observations. With a sampler every env then queues a fresh draw."""
        self._env.reset()
        self._advance_rosters(range(self.n_envs))
        return self._out(self._env.obs)

    def _advance_rosters(self, envs: Sequence[int] | NDArray[np.integer]) -> None:
        """Envs that were just rebuilt: the queued roster is now current; with a
        sampler, draw and queue the next one."""
        for i in envs:
            i = int(i)
            self.rosters[i] = self._next[i]
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

    def events(self) -> NDArray[np.float32]:
        """Copied ``[E, 9]`` events of the last step (needs ``record_events``)."""
        return self._env.events()

    def _out(self, arr: NDArray) -> NDArray:
        return arr.copy() if self.copy_outputs else arr
