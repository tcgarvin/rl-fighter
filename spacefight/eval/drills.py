"""Order drill eval and gate (``docs/PILOT_TRAINING.md`` §2): did the pilot understand what
it was told?

Fixed seeds, separate from training. For a checkpoint or ``script``, per kind and overall,
with counts and standard errors:

- **go-to**: each ship's arrival by its deadline (``spacefight.env.drills``), shown and
  with the orders hidden from the obs on the same seeds. A ship killed before its
  deadline without arriving is *censored*, not failed: fighting on the way is allowed.
  The script flies orders it cannot see, so its hidden pass would prove nothing and is
  skipped.
- **attack**: damage on the named target (does any land, and how much per pilot), the side
  chosen, and the swap test. Damage on other enemies is reported and judged in no way.
- **defend**: damage on the named ward's attackers against the other's, the side chosen,
  and the swap test. Whether the ward survives is not measured.

**The side chosen** is measured from where the pilots themselves go, so it survives enemies
flying at them. From the tick the order lands, a pilot has *committed* to a side the first
time it is ``COMMIT_M`` metres along the line between the sides from where it was on that
tick. The squad's choice is the side most of its committed pilots took (a tie, or nobody
committing, is no choice).

**The swap test** plays every attack and defend drill twice: the same start and match seed,
with the other side named. It *flips* if both times the squad chose the side it was told.
``same_side`` is the share of pairs that chose one side both times, whatever was named:
that is the smart pilot who would have done the same with no order.

The gate reads its bars from one small YAML (``DEFAULT_BARS``). An unset bar is not a pass:
with any bar unset and none failed the verdict is ``report_only``, stated plainly. A pilot
named in ``exempt`` is ``exempt`` whatever the numbers say. Bars get their values in step
6 of the plan, after measuring the script and the founders.

    python -m spacefight.eval.drills --a ckpt.pt --name f995_701 --out drills.json
    python -m spacefight.eval.drills --a script --n-per-kind 64 --out script.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import rlf_sim
import yaml  # type: ignore[import-untyped]
from numpy.typing import NDArray

from spacefight.env.drills import ORDER_TICK, DrillGenerator, DrillLedger, DrillSpec
from spacefight.env.rosters import (
    DEFAULT_ASSETS,
    DRILL_ATTACK,
    DRILL_DEFEND,
    DRILL_GOTO,
    EXTERNAL,
    capital_hull_ids,
)
from spacefight.env.rust_env import (
    TRACK_ATTACK,
    TRACK_DEFEND,
    TRACK_GOTO,
    RustVecEnv,
)
from spacefight.eval.controllers import (
    Controller,
    Scripted,
    idle_actions,
    make_controller,
)

SCHEMA = "rlf.eval.drills/1"
DEFAULT_SEED = 500_000
DEFAULT_BARS = Path(__file__).with_name("drill_bars.yaml")
# Metres along the line between the sides that commit a pilot to a side, at a 450 m arena.
COMMIT_M = 80.0
REFERENCE_RADIUS = 450.0
# Ticks between reads of positions for the side chosen.
POLL_TICKS = 3
# Kinds' seeds are this far apart, so no two kinds share a generator stream by accident.
KIND_SEED_STRIDE = 1_000_000
CHOSE_NAMED, CHOSE_OTHER, NO_CHOICE = "named", "other", "none"
_ORDER_CODES = {
    DRILL_ATTACK: TRACK_ATTACK,
    DRILL_DEFEND: TRACK_DEFEND,
    DRILL_GOTO: TRACK_GOTO,
}

PASS, FAIL, REPORT_ONLY, EXEMPT = "pass", "fail", "report_only", "exempt"
# Every bar the gate knows: a lower bound on the number at this path of the summary.
BAR_PATHS: dict[str, tuple[str, ...]] = {
    "goto_arrival": ("goto", "shown", "rate"),
    "goto_lift": ("goto", "lift"),
    "attack_target_hit": ("attack", "target_hit", "rate"),
    "attack_side": ("attack", "chose_named", "rate"),
    "attack_flip": ("attack", "flip", "rate"),
    "defend_more_on_named": ("defend", "more_on_named", "rate"),
    "defend_side": ("defend", "chose_named", "rate"),
    "defend_flip": ("defend", "flip", "rate"),
}


@dataclass(frozen=True)
class Rate:
    """A share with its count and binomial standard error."""

    successes: int
    n: int
    rate: float
    se: float

    @classmethod
    def of(cls, successes: int, n: int) -> Rate:
        """``successes`` of ``n``; rate and error 0 with ``n`` 0."""
        if n == 0:
            return cls(0, 0, 0.0, 0.0)
        p = successes / n
        return cls(int(successes), int(n), p, math.sqrt(p * (1.0 - p) / n))

    def text(self) -> str:
        """``0.75 +/- 0.05 (12/16)``."""
        return f"{self.rate:.2f} +/- {self.se:.2f} ({self.successes}/{self.n})"


@dataclass(frozen=True)
class Mean:
    """A mean with its count and standard error."""

    n: int
    mean: float
    se: float

    @classmethod
    def of(cls, values: Sequence[float]) -> Mean:
        """Mean of ``values``; 0 for none."""
        if not values:
            return cls(0, 0.0, 0.0)
        arr = np.asarray(values, dtype=np.float64)
        se = float(arr.std(ddof=1) / math.sqrt(arr.size)) if arr.size > 1 else 0.0
        return cls(int(arr.size), float(arr.mean()), se)

    def text(self) -> str:
        """``12.3 +/- 1.0 (n=16)``."""
        return f"{self.mean:.1f} +/- {self.se:.1f} (n={self.n})"


@dataclass
class ShipRun:
    """One pilot in one played go-to."""

    deadline: int
    arrived_tick: int = -1
    gone_tick: int = -1

    def outcome(self) -> str:
        """``arrived``, ``late`` or ``censored``: it was killed before its deadline, or
        the match ended before it for want of pilots (module docstring)."""
        if 0 <= self.arrived_tick <= self.deadline:
            return "arrived"
        if 0 <= self.gone_tick < self.deadline:
            return "censored"
        return "late"


@dataclass
class DrillRecord:
    """One played drill: what the pilots did, in the terms the summaries use."""

    spec: DrillSpec
    target_damage: float = 0.0
    named_group_damage: float = 0.0
    other_group_damage: float = 0.0
    total_damage: float = 0.0
    choice: str = NO_CHOICE
    ships: list[ShipRun] = field(default_factory=list)

    @property
    def per_pilot(self) -> float:
        """1 / squad size, for damage per pilot."""
        return 1.0 / len(self.spec.pilots)


def _commit_signs(
    positions: NDArray[np.float64],
    origin: NDArray[np.float64],
    axis: NDArray[np.float64],
) -> NDArray[np.int64]:
    """Per pilot, +1 or -1 if it is past ``COMMIT_M`` toward side 1 or side 0, else 0."""
    along = (positions - origin) @ axis
    out = np.zeros(along.shape, dtype=np.int64)
    out[along >= COMMIT_M] = 1
    out[along <= -COMMIT_M] = -1
    return out


class _SideWatch:
    """Which side each pilot of one attack or defend drill committed to."""

    def __init__(self, spec: DrillSpec) -> None:
        self.spec = spec
        scale = REFERENCE_RADIUS / spec.arena_radius
        # Positions scale to the reference arena, so COMMIT_M stays one number.
        self.scale = scale
        self.axis = np.asarray(spec.side_axis, dtype=np.float64)
        self.origin: NDArray[np.float64] = np.zeros((len(spec.pilots), 2))
        self.started = False
        self.signs = np.zeros(len(spec.pilots), dtype=np.int64)

    @property
    def settled(self) -> bool:
        """Every pilot has committed: nothing more to read."""
        return bool(np.all(self.signs != 0))

    def see(self, ships: Sequence[Mapping[str, Any]]) -> None:
        """Read the pilots' positions (``render_state``'s ship list)."""
        at = (
            np.array([ships[s]["pos"] for s in self.spec.pilots], dtype=np.float64)
            * self.scale
        )
        alive = np.array([bool(ships[s]["alive"]) for s in self.spec.pilots])
        if not self.started:
            self.origin = at
            self.started = True
            return
        fresh = _commit_signs(at, self.origin, self.axis)
        take = (self.signs == 0) & alive
        self.signs[take] = fresh[take]

    def choice(self) -> str:
        """The squad's choice (module docstring)."""
        total = int(self.signs.sum())
        if total == 0:
            return NO_CHOICE
        toward_side = 1 if total > 0 else 0
        return CHOSE_NAMED if toward_side == self.spec.named_side else CHOSE_OTHER


def run_pass(
    controller: Controller,
    specs: Sequence[DrillSpec],
    seed: int,
    n_threads: int = 2,
    hidden: bool = False,
    assets_dir: Path = DEFAULT_ASSETS,
) -> list[DrillRecord]:
    """Play each drill once, ``controller`` flying its pilots and scripts the rest.

    Env ``i`` plays ``specs[i]`` with match seed ``split(seed, i, 0)``, so two passes with
    the same ``seed`` and order of specs play the same matches.

    Args:
        controller: Flies team 0's strike craft.
        specs: The drills.
        seed: Base seed.
        n_threads: Sim threads.
        hidden: Hide the orders from the pilots' obs.
        assets_dir: Hull and weapon YAML.

    Returns:
        One record per spec, in order.

    Raises:
        RuntimeError: A match did not end on its clock, or a pilot never got its order.
        ValueError: No specs.
    """
    if not specs:
        raise ValueError("run_pass needs at least one drill")
    first = specs[0].roster()
    env = RustVecEnv(
        assets_dir,
        len(specs),
        first.fleets(),
        seed,
        n_threads=n_threads,
        max_ships=max(s.roster().n_ships for s in specs),
        commanders=(EXTERNAL, EXTERNAL),
    )
    for i, spec in enumerate(specs):
        env.set_next_roster(i, spec.roster(hidden=hidden))
    env.reset()
    n, s = env.n_envs, env.n_ships
    capital = np.isin(env.hull_id, capital_hull_ids(assets_dir))
    team = env.team.astype(np.int64).copy()
    pilots = (team == 0) & ~capital
    scripted = (team >= 0) & ~pilots
    ledger = DrillLedger(n, s)
    records = [DrillRecord(spec) for spec in specs]
    watches: dict[int, _SideWatch] = {}
    for i, spec in enumerate(specs):
        ledger.begin(i, env.rosters[i].drill)
        if spec.has_sides:
            watches[i] = _SideWatch(spec)
        else:
            records[i].ships = [ShipRun(d) for d in spec.deadlines]
    running = np.ones(n, dtype=np.bool_)
    controller.reset(seed)
    max_steps = max(spec.clock_ticks for spec in specs) + 2
    arrived_tick = np.full((n, s), -1, dtype=np.int64)
    gone_tick = np.full((n, s), -1, dtype=np.int64)
    for tick in range(max_steps):
        if tick == ORDER_TICK + 1:
            _check_orders_landed(env, specs, running)
        if ledger.any_goto_running():
            _note_goto_ticks(env, ledger, running, arrived_tick, gone_tick, tick)
        if tick >= ORDER_TICK and tick % POLL_TICKS == 0:
            for i, watch in watches.items():
                if running[i] and not watch.settled:
                    watch.see(env.raw.render_state(i)["ships"])
        decide = running[:, None] & env.act_mask
        actions = idle_actions(n * s).reshape(n, s, -1)
        rows = decide & scripted
        if rows.any():
            actions[rows] = env.scripted_actions()[rows]
        rows = decide & pilots
        if rows.any():
            actions[rows] = controller.act(env, rows)
        _, _, dones, info = env.step(actions)
        ledger.add_hits(info.hits, info.hit_count)
        ending = running & dones
        for env_id in np.flatnonzero(ending):
            ledger.finish(int(env_id))
            # Whoever had not arrived or died by now: the last pilot's death ended it.
            open_now = (gone_tick[env_id] < 0) & (arrived_tick[env_id] < 0)
            gone_tick[env_id, open_now] = tick + 1
        running &= ~dones
        if not running.any():
            break
    else:
        raise RuntimeError("drills did not end on their clocks")
    for i, record in enumerate(records):
        record.target_damage = float(ledger.target_damage[i])
        record.named_group_damage = float(ledger.group_damage[i, 0])
        record.other_group_damage = float(ledger.group_damage[i, 1])
        record.total_damage = float(ledger.total_damage[i])
        if i in watches:
            record.choice = watches[i].choice()
        for ship, slot in zip(record.ships, record.spec.pilots):
            ship.arrived_tick = int(arrived_tick[i, slot])
            ship.gone_tick = int(gone_tick[i, slot])
    return records


def _note_goto_ticks(
    env: RustVecEnv,
    ledger: DrillLedger,
    running: NDArray[np.bool_],
    arrived_tick: NDArray[np.int64],
    gone_tick: NDArray[np.int64],
    tick: int,
) -> None:
    """Note the first tick each go-to pilot shows as arrived, and as dead."""
    arrived = np.asarray(env.order_tracks()["arrived"], dtype=np.bool_)
    open_rows = ledger.pilot & running[:, None] & ledger.goto[:, None]
    arrived_tick[open_rows & arrived & (arrived_tick < 0)] = tick
    alive = np.asarray(env.raw.alive, dtype=np.bool_)
    gone_tick[open_rows & ~alive & (gone_tick < 0)] = tick


def _check_orders_landed(
    env: RustVecEnv, specs: Sequence[DrillSpec], running: NDArray[np.bool_]
) -> None:
    """Raise unless every live pilot has its order: a refused or mangled command would
    otherwise read as a pilot that ignored its order."""
    standing = env.order_tracks()["standing_kind"]
    alive = np.asarray(env.raw.alive, dtype=np.bool_)
    for i, spec in enumerate(specs):
        if not running[i]:
            continue
        want = _ORDER_CODES[spec.kind]
        for slot in spec.pilots:
            if alive[i, slot] and int(standing[i, slot]) != want:
                raise RuntimeError(
                    f"drill {spec.kind}/{spec.seed}: pilot {slot} holds order code "
                    f"{int(standing[i, slot])} after tick {ORDER_TICK}, wanted {want}"
                )


# -- summaries --------------------------------------------------------------------------


def summarise_goto(
    shown: Sequence[DrillRecord], hidden: Sequence[DrillRecord]
) -> dict[str, Any]:
    """Arrival by deadline, shown and hidden, near and far, ship by ship (ships of one
    squad are not independent, so the errors are a little small)."""

    def count(records: Sequence[DrillRecord]) -> dict[str, Any]:
        outcomes = [ship.outcome() for r in records for ship in r.ships]
        arrived = outcomes.count("arrived")
        late = outcomes.count("late")
        rate = Rate.of(arrived, arrived + late)
        return {
            "rate": rate.rate,
            "se": rate.se,
            "arrived": arrived,
            "late": late,
            "censored": outcomes.count("censored"),
            "n": arrived + late,
        }

    near = [r for r in shown if not r.spec.far]
    far = [r for r in shown if r.spec.far]
    around = [r for r in shown if r.spec.enemies_around]
    out: dict[str, Any] = {
        "n_drills": len(shown),
        "shown": count(shown),
        "shown_near": count(near),
        "shown_far": count(far),
        "shown_enemies_around": count(around),
        "hidden": count(hidden) if hidden else None,
        "lift": None,
    }
    if hidden:
        out["lift"] = out["shown"]["rate"] - out["hidden"]["rate"]
    return out


def _sides_summary(
    records: Sequence[DrillRecord], partners: Sequence[DrillRecord]
) -> dict[str, Any]:
    """The side chosen over both passes, and the swap test over the pairs."""
    every = [*records, *partners]
    pairs = list(zip(records, partners, strict=True))
    choices = [r.choice for r in every]
    flips = sum(a.choice == CHOSE_NAMED and b.choice == CHOSE_NAMED for a, b in pairs)
    # The partners name opposite sides, so one side both times is one named, one other.
    same = sum({a.choice, b.choice} == {CHOSE_NAMED, CHOSE_OTHER} for a, b in pairs)
    return {
        "n_pairs": len(pairs),
        "chose_named": asdict(Rate.of(choices.count(CHOSE_NAMED), len(choices))),
        "chose_other": asdict(Rate.of(choices.count(CHOSE_OTHER), len(choices))),
        "no_choice": asdict(Rate.of(choices.count(NO_CHOICE), len(choices))),
        "flip": asdict(Rate.of(flips, len(pairs))),
        "same_side": asdict(Rate.of(same, len(pairs))),
    }


def summarise_attack(
    records: Sequence[DrillRecord], partners: Sequence[DrillRecord]
) -> dict[str, Any]:
    """Named-target damage, the side chosen, the swap test. Damage on other enemies is
    reported, never judged."""
    every = [*records, *partners]
    hit = sum(r.target_damage > 0.0 for r in every)
    target = [r.target_damage * r.per_pilot for r in every]
    other = [(r.total_damage - r.target_damage) * r.per_pilot for r in every]
    charging = [
        (a, b) for a, b in zip(records, partners, strict=True) if a.spec.charging
    ]
    busy = [
        (a, b) for a, b in zip(records, partners, strict=True) if not a.spec.charging
    ]

    def sides_of(pairs: Sequence[tuple[DrillRecord, DrillRecord]]) -> dict[str, Any]:
        return _sides_summary([a for a, _ in pairs], [b for _, b in pairs])

    return {
        "n_drills": len(every),
        "target_hit": asdict(Rate.of(hit, len(every))),
        "target_damage_per_pilot": asdict(Mean.of(target)),
        "other_damage_per_pilot": asdict(Mean.of(other)),
        "enemies_busy": sides_of(busy),
        "enemies_charging": sides_of(charging),
        **_sides_summary(records, partners),
    }


def summarise_defend(
    records: Sequence[DrillRecord], partners: Sequence[DrillRecord]
) -> dict[str, Any]:
    """Damage on the named ward's attackers against the other's, the side chosen, the swap
    test. Whether the ward survives is not looked at."""
    every = [*records, *partners]
    more = sum(r.named_group_damage > r.other_group_damage for r in every)
    named = [r.named_group_damage * r.per_pilot for r in every]
    other = [r.other_group_damage * r.per_pilot for r in every]
    return {
        "n_drills": len(every),
        "more_on_named": asdict(Rate.of(more, len(every))),
        "named_attackers_damage_per_pilot": asdict(Mean.of(named)),
        "other_attackers_damage_per_pilot": asdict(Mean.of(other)),
        **_sides_summary(records, partners),
    }


def summarise_overall(summary: Mapping[str, Any]) -> dict[str, Any]:
    """The core check of each kind, pooled: go-to arrivals (shown) and swap-test flips."""
    goto = summary["goto"]["shown"]
    flips = [summary[k]["flip"] for k in (DRILL_ATTACK, DRILL_DEFEND)]
    successes = goto["arrived"] + sum(f["successes"] for f in flips)
    n = goto["n"] + sum(f["n"] for f in flips)
    return {
        "core": asdict(Rate.of(successes, n)),
        "core_is": "go-to arrivals (shown) and attack and defend swap-test flips",
    }


# -- the gate ---------------------------------------------------------------------------


def load_bars(path: Path = DEFAULT_BARS) -> dict[str, float | None]:
    """The bars: every name of ``BAR_PATHS``, ``None`` where unset or missing.

    Raises:
        FileNotFoundError: No file at ``path``.
        ValueError: A name the gate does not know, or a bar that is not a number.
    """
    raw = yaml.safe_load(path.read_text())
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must hold a mapping of bars")
    return parse_bars(raw)


def parse_bars(raw: Mapping[str, object]) -> dict[str, float | None]:
    """``raw`` checked and completed; see ``load_bars``."""
    unknown = set(raw) - set(BAR_PATHS)
    if unknown:
        raise ValueError(
            f"unknown drill bars {sorted(unknown)}; known: {sorted(BAR_PATHS)}"
        )
    bars: dict[str, float | None] = dict.fromkeys(BAR_PATHS)
    for name, value in raw.items():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"bar {name} must be a number or unset, got {value!r}")
        bars[name] = float(value)
    return bars


@dataclass(frozen=True)
class GateResult:
    """The gate's verdict.

    Attributes:
        verdict: ``pass``, ``fail``, ``report_only`` or ``exempt``.
        statement: The verdict in a plain sentence.
        unset: Bars with no value.
        failed: Bars set and not met.
        met: Bars set and met.
        measured: Each bar's number in this eval (``None`` where there is none, e.g. the
            script's go-to lift).
    """

    verdict: str
    statement: str
    unset: tuple[str, ...]
    failed: tuple[str, ...]
    met: tuple[str, ...]
    measured: dict[str, float | None]


def _measure(summary: Mapping[str, Any], path: tuple[str, ...]) -> float | None:
    node: Any = summary
    for key in path:
        if node is None:
            return None
        node = node[key]
    return None if node is None else float(node)


def apply_gate(
    summary: Mapping[str, Any],
    bars: Mapping[str, float | None],
    name: str,
    exempt: Sequence[str] = (),
) -> GateResult:
    """Judge one pilot's ``summary`` against ``bars``.

    A failed bar fails the pilot. Otherwise any unset bar, or a set bar with nothing to
    measure, means ``report_only``: never a pass. Only a pilot that meets every bar
    passes. An exempt pilot (the founders; the member list that decides that comes later)
    gets ``exempt``, with the same numbers shown.

    Args:
        summary: ``evaluate``'s kinds.
        bars: ``parse_bars`` output.
        name: The pilot's name, as ``exempt`` lists it.
        exempt: Names the gate does not judge.
    """
    measured = {bar: _measure(summary, path) for bar, path in BAR_PATHS.items()}
    unset, failed, met = [], [], []
    for bar in BAR_PATHS:
        value, floor = measured[bar], bars.get(bar)
        if floor is None or value is None:
            unset.append(bar)
        elif value < floor:
            failed.append(bar)
        else:
            met.append(bar)
    if name in exempt:
        verdict = EXEMPT
        statement = f"{name} is exempt: the gate does not judge it."
    elif failed:
        verdict = FAIL
        statement = f"{name} failed the drill gate: {', '.join(failed)}."
    elif unset:
        verdict = REPORT_ONLY
        statement = (
            f"Report only, not a pass: {len(unset)} of {len(BAR_PATHS)} bars are unset "
            f"or have nothing to measure ({', '.join(unset)})."
        )
    else:
        verdict = PASS
        statement = f"{name} passed the drill gate: every bar met."
    return GateResult(
        verdict, statement, tuple(unset), tuple(failed), tuple(met), measured
    )


# -- the eval ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DrillEvalConfig:
    """One drill evaluation.

    Attributes:
        n_per_kind: Go-to drills, and attack and defend swap pairs (two matches each).
        seed: Base of the drills' and the matches' seeds.
        hidden_goto: Run the go-to's hidden pass (never for the script, module docstring).
    """

    n_per_kind: int = 256
    seed: int = DEFAULT_SEED
    hidden_goto: bool = True
    sim_version: int = int(rlf_sim.SIM_VERSION)


@dataclass(frozen=True)
class DrillResult:
    """Outcome of ``evaluate``; JSON schema ``SCHEMA``."""

    pilot: str
    name: str
    config: DrillEvalConfig
    kinds: dict[str, Any]
    overall: dict[str, Any]
    gate: GateResult
    schema: str = SCHEMA

    def to_dict(self) -> dict[str, Any]:
        """Plain JSON-ready dict."""
        return asdict(self)

    def to_json(self) -> str:
        """Indented JSON text."""
        return json.dumps(self.to_dict(), indent=1)

    def to_markdown(self) -> str:
        """A plain report."""
        return report_markdown(self)


def report_markdown(result: DrillResult) -> str:
    """The result as plain Markdown."""
    goto, attack, defend = (
        result.kinds[DRILL_GOTO],
        result.kinds[DRILL_ATTACK],
        result.kinds[DRILL_DEFEND],
    )

    def rate(raw: Mapping[str, Any]) -> str:
        return Rate(**raw).text()

    def mean(raw: Mapping[str, Any]) -> str:
        return Mean(**raw).text()

    def arrival(raw: Mapping[str, Any]) -> str:
        return (
            f"{raw['rate']:.2f} +/- {raw['se']:.2f} ({raw['arrived']}/{raw['n']}; "
            f"{raw['censored']} killed first, not counted)"
        )

    lines = [
        f"# Order drills: {result.name}",
        "",
        f"**Gate: {result.gate.verdict}.** {result.gate.statement}",
        "",
        f"Pilot `{result.pilot}`, seed {result.config.seed}, sim version "
        f"{result.config.sim_version}. Overall: {rate(result.overall['core'])} "
        f"({result.overall['core_is']}).",
        "",
        f"## Go-to ({goto['n_drills']} drills, ship by ship)",
        "",
        f"- Arrival by the deadline, order shown: {arrival(goto['shown'])}",
    ]
    if goto["hidden"] is not None:
        lines += [
            f"- Same seeds, order hidden: {arrival(goto['hidden'])}",
            f"- Lift from seeing the order: {goto['lift']:+.2f}",
        ]
    else:
        lines.append("- Hidden pass not run (the script flies orders it cannot see).")
    lines += [
        f"- Near: {arrival(goto['shown_near'])}",
        f"- Far: {arrival(goto['shown_far'])}",
        f"- Enemies around the route: {arrival(goto['shown_enemies_around'])}",
    ]
    for label, part in (("Attack", attack), ("Defend", defend)):
        lines += ["", f"## {label} ({part['n_pairs']} swap pairs)", ""]
        if label == "Attack":
            lines += [
                f"- Any damage on the named target: {rate(part['target_hit'])}",
                "- Swap test, flipped, groups busy with a freighter: "
                f"{rate(part['enemies_busy']['flip'])}",
                "- Swap test, flipped, groups flying at the pilots: "
                f"{rate(part['enemies_charging']['flip'])}",
                "- Damage on the named target per pilot: "
                f"{mean(part['target_damage_per_pilot'])}",
                "- On other enemies per pilot (not judged): "
                f"{mean(part['other_damage_per_pilot'])}",
            ]
        else:
            lines += [
                "- Named ward's attackers took more than the other's: "
                f"{rate(part['more_on_named'])}",
                "- On the named ward's attackers per pilot: "
                f"{mean(part['named_attackers_damage_per_pilot'])}",
                "- On the other's per pilot: "
                f"{mean(part['other_attackers_damage_per_pilot'])}",
            ]
        lines += [
            f"- Chose the named side: {rate(part['chose_named'])}",
            f"- Chose the other side: {rate(part['chose_other'])}",
            f"- Chose neither: {rate(part['no_choice'])}",
            f"- Swap test, flipped with the order: {rate(part['flip'])}",
            f"- Swap test, one side whatever was named: {rate(part['same_side'])}",
        ]
    lines += ["", "## Bars", "", "| Bar | Measured | Bar value |", "|---|---|---|"]
    bars = result.gate
    for bar, value in bars.measured.items():
        shown = "n/a" if value is None else f"{value:.3f}"
        status = (
            "unset"
            if bar in bars.unset
            else ("failed" if bar in bars.failed else "met")
        )
        lines.append(f"| {bar} | {shown} | {status} |")
    return "\n".join(lines) + "\n"


def evaluate(
    controller: Controller,
    name: str,
    cfg: DrillEvalConfig | None = None,
    bars: Mapping[str, float | None] | None = None,
    exempt: Sequence[str] = (),
    n_threads: int = 2,
    assets_dir: Path = DEFAULT_ASSETS,
) -> DrillResult:
    """Play every drill of ``cfg`` and judge the result.

    Args:
        controller: The pilot.
        name: The pilot's name in the report and for ``exempt``.
        cfg: The drills (default ``DrillEvalConfig()``).
        bars: The gate's bars (default: ``DEFAULT_BARS``).
        exempt: Pilots the gate does not judge.
        n_threads: Sim threads.
        assets_dir: Hull and weapon YAML.
    """
    cfg = cfg or DrillEvalConfig()
    bars = load_bars() if bars is None else parse_bars(bars)
    gen = DrillGenerator(assets_dir)
    kinds: dict[str, Any] = {}

    goto = gen.generate_many(DRILL_GOTO, cfg.n_per_kind, cfg.seed)
    shown = run_pass(controller, goto, cfg.seed, n_threads, False, assets_dir)
    hidden: list[DrillRecord] = []
    if cfg.hidden_goto and not isinstance(controller, Scripted):
        hidden = run_pass(controller, goto, cfg.seed, n_threads, True, assets_dir)
    kinds[DRILL_GOTO] = summarise_goto(shown, hidden)

    summarisers = {DRILL_ATTACK: summarise_attack, DRILL_DEFEND: summarise_defend}
    for k, (kind, summarise) in enumerate(summarisers.items(), start=1):
        base = cfg.seed + k * KIND_SEED_STRIDE
        specs = gen.generate_many(kind, cfg.n_per_kind, base)
        partners = [spec.swapped() for spec in specs]
        first = run_pass(controller, specs, base, n_threads, False, assets_dir)
        second = run_pass(controller, partners, base, n_threads, False, assets_dir)
        kinds[kind] = summarise(first, second)

    return DrillResult(
        pilot=controller.label,
        name=name,
        config=cfg,
        kinds=kinds,
        overall=summarise_overall(kinds),
        gate=apply_gate(kinds, bars, name, exempt),
    )


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--a", required=True, help="A checkpoint path, or script")
    parser.add_argument(
        "--name", default="", help="The pilot's name (default: from --a)"
    )
    parser.add_argument("--n-per-kind", type=int, default=DrillEvalConfig.n_per_kind)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--bars", type=Path, default=DEFAULT_BARS)
    parser.add_argument(
        "--exempt", default="", help="Comma-separated pilots the gate does not judge"
    )
    parser.add_argument("--no-hidden", action="store_true")
    parser.add_argument("--out", type=Path, help="JSON path; the report goes beside it")
    args = parser.parse_args(argv)
    controller = make_controller(args.a, sample=True, seed=args.seed)
    name = args.name or Path(args.a).stem
    result = evaluate(
        controller,
        name,
        DrillEvalConfig(args.n_per_kind, args.seed, not args.no_hidden),
        load_bars(args.bars),
        [e for e in args.exempt.split(",") if e],
        args.threads,
    )
    report = result.to_markdown()
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(result.to_json())
        args.out.with_suffix(".md").write_text(report)
    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
