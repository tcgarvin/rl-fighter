"""Kite drills (``docs/PILOT_TRAINING.md`` §2): the attack drill's training variant whose
enemies are pool pilots with their orders hidden (``drill_attack_pool_share``).

Needs the extension: ``uv run maturin develop -m crates/sim-py/Cargo.toml --release``.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch

rlf_sim = pytest.importorskip("rlf_sim", reason="rlf_sim extension not built")

from spacefight.env.drills import (  # noqa: E402
    DRILL_ATTACK_KITE,
    KITE_CLOCK_TICKS,
    SIDE_CLOCK_TICKS,
    WARD_HULL,
    DrillGenerator,
    DrillLedger,
    DrillOutcome,
)
from spacefight.env.rosters import (  # noqa: E402
    DRILL_ATTACK,
    DRILL_DEFEND,
    DRILL_GOTO,
    EXTERNAL,
    MAX_SHIPS,
    DrillTag,
    PilotsDistribution,
    PilotsRosterSampler,
)
from spacefight.rl.opponents import (  # noqa: E402
    OpponentAssigner,
    OpponentKind,
    OpponentSchedule,
)
from spacefight.rl.spike_policy import SpikeActor, SpikeCritic, save_policy  # noqa: E402
from spacefight.rl.spike_ppo import PPOConfig, SpikeTrainer  # noqa: E402

ASSETS = Path(__file__).resolve().parents[1] / "assets"
GEN = DrillGenerator()


def _charging_seed() -> int:
    """A seed whose standard attack drill is a charging one."""
    for seed in range(200):
        if GEN.generate(DRILL_ATTACK, seed).charging:
            return seed
    raise AssertionError("no charging attack drill in 200 seeds")


# -- the drill ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(12))
def test_a_kite_drill_is_a_charging_attack_with_a_longer_clock(seed: int) -> None:
    spec = GEN.generate(DRILL_ATTACK, seed, kite=True)
    assert spec.kite and spec.charging
    assert spec.clock_ticks == KITE_CLOCK_TICKS
    assert WARD_HULL not in spec.teams[0], "no freighter holds the target"
    assert spec.enemy_orders == ()
    roster = spec.roster()
    assert roster.hide_orders == (False, True), "the enemy's orders are hidden"
    assert roster.drill is not None and roster.drill.kite
    assert roster.drill.kind == DRILL_ATTACK
    assert roster.time_limit_s == pytest.approx(60.0)
    # The swap partner is a kite drill too.
    assert spec.swapped().roster().drill.kite  # type: ignore[union-attr]


def test_a_kite_drill_is_the_standard_charging_drill_of_its_seed_but_the_clock() -> None:
    seed = _charging_seed()
    standard = GEN.generate(DRILL_ATTACK, seed)
    kite = GEN.generate(DRILL_ATTACK, seed, kite=True)
    assert replace(kite, kite=False, clock_ticks=SIDE_CLOCK_TICKS) == standard
    # The same order on the same target: the pass rule and the pay are the attack's.
    assert kite.order() == standard.order()
    tag, plain = kite.roster().drill, standard.roster().drill
    assert replace(tag, kite=False) == plain  # type: ignore[arg-type]


def test_the_standard_drills_are_unchanged_and_only_an_attack_has_a_kite() -> None:
    for kind in (DRILL_GOTO, DRILL_ATTACK, DRILL_DEFEND):
        spec = GEN.generate(kind, 9)
        assert not spec.kite
        assert spec.roster().hide_orders == (False, False)
        assert spec.roster().drill is not None
        assert not spec.roster().drill.kite  # type: ignore[union-attr]
    for kind in (DRILL_GOTO, DRILL_DEFEND):
        with pytest.raises(ValueError, match="kite"):
            GEN.generate(kind, 9, kite=True)


def test_a_kite_drill_hides_the_enemy_s_orders_in_the_sim() -> None:
    from spacefight.env.rust_env import RustVecEnv

    roster = GEN.generate(DRILL_ATTACK, 4, kite=True).roster()
    env = RustVecEnv(
        ASSETS,
        1,
        roster.fleets(),
        0,
        max_ships=20,
        n_threads=1,
        commanders=(EXTERNAL, EXTERNAL),
    )
    env.set_next_roster(0, roster)
    env.reset()
    hidden = np.asarray(env.order_hidden_rows())[0]
    team = np.asarray(env.team)[0]
    assert hidden[team == 1].all()
    assert not hidden[team == 0].any()


# -- the sampler ---------------------------------------------------------------------------


@pytest.mark.parametrize("weights", [(1.0, 1.0, 1.0), (4.0, 3.0, 1.0)])
def test_share_zero_leaves_every_draw_and_the_generator_as_they_were(
    weights: tuple[float, ...],
) -> None:
    extra = {"drill_share": 0.4, "drill_weights": weights, "max_ships": MAX_SHIPS}
    plain = PilotsRosterSampler(PilotsDistribution(commander_p=0.667, **extra), 5)
    zero = PilotsRosterSampler(
        PilotsDistribution(commander_p=0.667, drill_attack_pool_share=0.0, **extra), 5
    )
    assert plain.sample_many(400) == zero.sample_many(400)
    assert plain.rng.bit_generator.state == zero.rng.bit_generator.state


def test_the_share_of_attack_drills_that_are_kite_drills_follows_the_setting() -> None:
    only_attack = {"drill_share": 1.0, "drill_weights": (0.0, 1.0, 0.0)}
    every = PilotsRosterSampler(
        PilotsDistribution(drill_attack_pool_share=1.0, **only_attack), 6
    ).sample_many(40)
    assert all(r.drill is not None and r.drill.kite for r in every)
    assert all(r.hide_orders == (False, True) for r in every)
    half = PilotsRosterSampler(
        PilotsDistribution(drill_attack_pool_share=0.5, **only_attack), 7
    ).sample_many(600)
    kite = sum(bool(r.drill and r.drill.kite) for r in half)
    assert kite / len(half) == pytest.approx(0.5, abs=0.06)
    # Go-to and defend drills never are.
    mixed = PilotsRosterSampler(
        PilotsDistribution(drill_share=1.0, drill_attack_pool_share=1.0), 8
    ).sample_many(300)
    for r in mixed:
        assert r.drill is not None
        assert r.drill.kite == (r.drill.kind == DRILL_ATTACK)


def test_a_bad_share_is_rejected_and_the_trainer_needs_a_pool() -> None:
    with pytest.raises(ValueError, match="drill_attack_pool_share"):
        PilotsDistribution(drill_attack_pool_share=1.5)
    with pytest.raises(ValueError, match="pool_seed"):
        PPOConfig.preset(
            "scratch",
            tag="x",
            rosters="pilots_v1",
            roster_overrides={"drill_share": 0.2, "drill_attack_pool_share": 0.5},
            order_reward_weight=1.0,
        )


# -- the ledger ------------------------------------------------------------------------------


def _kite_tag() -> DrillTag:
    return DrillTag(
        DRILL_ATTACK, (0, 1), named_slot=2, named_group=(2,), other_group=(3,), kite=True
    )


def test_a_kite_drill_passes_by_the_attack_rule_and_is_logged_apart() -> None:
    ledger = DrillLedger(1, 4)
    ledger.begin(0, _kite_tag())
    hits = np.zeros((1, 4, 6), dtype=np.int32)
    hits[0, 0] = (0, 2, 0, 4000, 0, 0)  # a pilot on the target
    hits[0, 1] = (2, 1, 0, 7000, 0, 0)  # the target on a pilot
    hits[0, 2] = (3, 0, 0, 3000, 0, 0)  # the other group on a pilot: not the target's
    hits[0, 3] = (2, 3, 0, 1000, 0, 0)  # the target on its own side's ship: no pilot
    ledger.add_hits(hits, np.array([4], dtype=np.int32))
    out = ledger.finish(0)
    assert out == DrillOutcome(
        DRILL_ATTACK_KITE,
        1,
        1,
        pilots=2,
        target_damage=pytest.approx(4.0),  # type: ignore[arg-type]
        damage_from_target=pytest.approx(7.0),  # type: ignore[arg-type]
    )
    # Nothing on the target: a fail, and "chose neither" with nothing on either group.
    ledger.begin(0, _kite_tag())
    assert ledger.finish(0) == DrillOutcome(
        DRILL_ATTACK_KITE, 0, 1, pilots=2, chose_neither=True
    )
    # A standard attack drill keeps its kind.
    ledger.begin(0, replace(_kite_tag(), kite=False))
    assert ledger.finish(0).kind == DRILL_ATTACK


def _see(
    ledger: DrillLedger,
    prev_alive: list[bool],
    alive: list[bool],
    done: bool = False,
    eliminated: bool = False,
    hurt: tuple[int, ...] = (),
) -> None:
    hits = np.zeros((1, 4, 6), dtype=np.int32)
    for k, slot in enumerate(hurt):
        hits[0, k] = (9, slot, 0, 1000, 0, 0)
    ledger.see_deaths(
        np.array([prev_alive]),
        np.array([alive]),
        np.array([done]),
        np.array([eliminated]),
        hits,
        np.array([len(hurt)], dtype=np.int32),
        np.zeros((1, 4), dtype=np.float32),
    )


def test_the_ledger_counts_pilots_killed_during_a_drill_and_on_its_last_step() -> None:
    ledger = DrillLedger(1, 4)
    ledger.begin(0, _kite_tag())
    _see(ledger, [True] * 4, [True, False, True, True])
    _see(ledger, [True, False, True, True], [True, False, True, True])
    assert ledger.finish(0).pilots_lost == 1
    # The last pilot is wiped out on the step that ends it: hurt, the enemies not.
    ledger.begin(0, _kite_tag())
    _see(ledger, [True, False, True, True], [True] * 4, True, True, hurt=(0,))
    _see(ledger, [True] * 4, [True, False, True, True])  # an earlier step's loss
    assert ledger.finish(0).pilots_lost == 2
    # The enemies were the ones wiped out: the pilots left are not counted.
    ledger.begin(0, _kite_tag())
    _see(ledger, [True, True, True, False], [True] * 4, True, True, hurt=(2,))
    assert ledger.finish(0).pilots_lost == 0
    # Ended on the clock: nobody is counted from the last step.
    ledger.begin(0, _kite_tag())
    _see(ledger, [True] * 4, [True] * 4, True, False, hurt=(0, 1))
    assert ledger.finish(0).pilots_lost == 0


# -- the opponents ---------------------------------------------------------------------------


def test_a_kite_env_fights_a_pool_entry_outside_the_quota_and_is_not_recorded() -> None:
    schedule = OpponentSchedule([[0, 0.5, 0.5, 0.0]])
    assigner = OpponentAssigner(
        8, schedule, np.random.default_rng(0), enemy_sampling="pfsp"
    )
    assigner.assign_all(0, 3, forced_scripted=np.array([0, 1, 2]))
    assigner.force_snapshot([1, 2], 3)
    assert assigner.kinds[:3].tolist() == [
        OpponentKind.SCRIPTED,
        OpponentKind.SNAPSHOT,
        OpponentKind.SNAPSHOT,
    ]
    assert assigner.forced[:3].all()
    assert 0 <= assigner.snapshot[1] < 3 and 0 <= assigner.snapshot[2] < 3
    assert assigner.counts() == {"scripted": 3, "self": 2, "snapshot": 0}
    assigner.record_results(
        np.array([1, 2]), np.full(8, -1, dtype=np.int8), np.zeros(8, dtype=np.int8)
    )
    assert assigner.results.state() == [], "a drill's draw says nothing of the enemy"
    assigner.assign(np.array([1]), 0, 3)
    assert not assigner.forced[1]
    with pytest.raises(ValueError, match="pool"):
        assigner.force_snapshot([0], 0)


# -- training ----------------------------------------------------------------------------------


def _kite_config(seed_ckpt: Path, **overrides: object) -> PPOConfig:
    settings: dict[str, object] = {
        "tag": "kite",
        "seed": 3,
        "assets_dir": str(ASSETS),
        "n_envs": 6,
        "n_steps": 48,
        "t_tail": 40,
        "n_updates": 2,
        "minibatch": 256,
        "epochs": 1,
        "sim_threads": 2,
        "torch_threads": 2,
        "rosters": "pilots_v1",
        "roster_overrides": {
            "drill_share": 1.0,
            "drill_weights": [0.0, 1.0, 0.0],
            "drill_attack_pool_share": 1.0,
        },
        "critic": "fleet",
        "learner_side": "random",
        "opponent_bands": [[0, 0.5, 0.5, 0.0]],
        "order_reward_weight": 1.0,
        "pool_seed": [str(seed_ckpt)],
        "checkpoint_every": 100,
    }
    settings.update(overrides)
    return PPOConfig.preset("scratch", **settings)


def test_training_flies_a_kite_drill_s_enemies_from_the_pool_and_logs_it_apart(
    tmp_path: Path,
) -> None:
    torch.manual_seed(0)
    seed_ckpt = tmp_path / "seed.pt"
    save_policy(seed_ckpt, SpikeActor(), SpikeCritic(), {"kind": "test"})
    trainer = SpikeTrainer(_kite_config(seed_ckpt), tmp_path / "run")
    for env_id in range(trainer.n_envs):
        assert trainer.env.rosters[env_id].drill.kite  # type: ignore[union-attr]
        assert trainer.opponents.kinds[env_id] == OpponentKind.SNAPSHOT
        assert trainer.opponents.forced[env_id]
        assert trainer.learner_team[env_id] == 0
    # Hold the drills to a short clock so that they end inside one rollout.
    for i in range(trainer.n_envs):
        roster = trainer.env.rosters[i]
        trainer.env.set_next_roster(i, replace(roster, time_limit_s=1.0))
    trainer.env.reset()
    tally, _ = trainer._collect(0)
    store = trainer.storage
    # Only team 0 learns; team 1's pilots act, flown by the pool entry.
    assert not (store.learner & (store.team == 1)).any()
    assert (store.learner & (store.team == 0)).any()
    fields: dict[str, Any] = tally.log_fields()
    assert fields["drill_episodes"].get(DRILL_ATTACK_KITE, 0) > 0
    assert DRILL_ATTACK not in fields["drill_episodes"]
    assert fields["episodes"] == 0, "drills are not in the match tallies"
    side = fields["drill_sides"][DRILL_ATTACK_KITE]
    assert set(side) == {
        "episodes",
        "pass",
        "pilots_lost",
        "target_damage",
        "damage_from_target",
        "chose_neither",
    }
    assert side["episodes"] == fields["drill_episodes"][DRILL_ATTACK_KITE]
    # New matches drawn after the reset are kite drills on the pool again.
    for env_id in range(trainer.n_envs):
        assert trainer.opponents.kinds[env_id] == OpponentKind.SNAPSHOT
        assert trainer.opponents.forced[env_id]
    assert trainer.opponents.results.state() == []
    rows: list[dict[str, Any]] = []
    trainer.train(lambda _t, row: rows.append(row))
    assert "drill_sides" in rows[-1]
