"""Preset ``pilots_v1`` (``docs/PILOT_TRAINING.md`` §3): live rosters, the same condition
on both sides, order pay only where an order is shown, and the training discount in
go-to shaping (§3, build item 1).

The extension must be built into the venv first:

    uv run maturin develop -m crates/sim-py/Cargo.toml --release
"""

from __future__ import annotations

import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import numpy as np
import pytest

rlf_sim = pytest.importorskip(
    "rlf_sim",
    reason=(
        "rlf_sim extension not built; run "
        "`uv run maturin develop -m crates/sim-py/Cargo.toml --release`"
    ),
)

from spacefight.env.rosters import (  # noqa: E402
    CARRIER_BATTLE,
    CONVOY_ESCORT,
    DEATHMATCH,
    MAX_FLEET_SHIPS,
    MAX_PER_SIDE,
    MAX_SHIPS,
    MAX_TRAIN_SHIPS,
    MISSIONS,
    SCRIPTED,
    OrdersDistribution,
    PilotsDistribution,
    PilotsRosterSampler,
    Roster,
    capital_hull_ids,
    load_hull_costs,
    make_sampler,
    resolve_distribution,
)
from spacefight.env.rust_env import (  # noqa: E402
    DEFAULT_ORDER_SHAPING_GAMMA,
    OBS_LAYOUT,
    RustVecEnv,
)
from spacefight.rl.spike_ppo import (  # noqa: E402
    PPOConfig,
    SpikeTrainer,
    read_config,
    write_config,
)
from tools.build_bundle import (  # noqa: E402
    MIN_PER_SIDE,
    load_catalogue,
    roster_rules,
)

REPO = Path(__file__).resolve().parent.parent
ASSETS = str(REPO / "assets")
THREADS = 2
ORDER_OFF, ORDER_W = OBS_LAYOUT["order"]
ORDER_SHIPS_OFF, ORDER_SHIPS_W = OBS_LAYOUT["order_ships"]
# The order-dependent columns of each ship_extras record (SIM_SPEC §7.2).
EXTRAS_OFF, EXTRAS_W = OBS_LAYOUT["ship_extras"]
EXTRAS_RECORDS = int(rlf_sim.OBS_SLOTS["ship_extras"])
EXTRAS_ORDER_COL = 7
NODE = shutil.which("node")


def live_fleets(mission: str) -> list[tuple[tuple[str, ...], tuple[str, ...]]]:
    """The sim's rosters of ``mission`` as team pairs, default first."""
    return [
        (tuple(r["fleets"][0]), tuple(r["fleets"][1]))
        for r in rlf_sim.mission_rosters(mission)
    ]


def _sampler(seed: int = 0, **overrides: object) -> PilotsRosterSampler:
    return PilotsRosterSampler(PilotsDistribution(**overrides), seed)  # type: ignore[arg-type]


# -- the distribution --------------------------------------------------------


def test_preset_resolves_and_orders_v1_is_unchanged() -> None:
    dist = resolve_distribution("pilots_v1")
    assert isinstance(dist, PilotsDistribution)
    assert isinstance(make_sampler(dist, 0), PilotsRosterSampler)
    orders = resolve_distribution("orders_v1")
    assert isinstance(orders, OrdersDistribution)
    assert orders.max_ships == MAX_TRAIN_SHIPS == 12
    assert make_sampler(orders, 0).max_ships == 12


def test_mission_shares_follow_the_weights() -> None:
    rosters = _sampler().sample_many(6000)
    counts = Counter(r.mission for r in rosters)
    for mission, share in zip(MISSIONS, (0.4, 0.3, 0.3)):
        assert counts[mission] / len(rosters) == pytest.approx(share, abs=0.03)


def test_commander_share_follows_commander_p_in_every_mission() -> None:
    for commander_p in (0.5, 0.25):
        rosters = _sampler(commander_p=commander_p).sample_many(6000)
        for mission in MISSIONS:
            of_mission = [r for r in rosters if r.mission == mission]
            shown = sum(not r.hide_orders[0] for r in of_mission) / len(of_mission)
            assert shown == pytest.approx(commander_p, abs=0.05), mission


def test_condition_is_always_the_same_on_both_sides() -> None:
    for r in _sampler().sample_many(3000):
        assert r.commanders == (SCRIPTED, SCRIPTED)
        assert r.hide_orders[0] == r.hide_orders[1]


@pytest.mark.parametrize("mission", [CARRIER_BATTLE, CONVOY_ESCORT])
def test_mission_rosters_are_live_rosters_with_the_page_s_shares(mission: str) -> None:
    fleets = live_fleets(mission)
    assert len(fleets) >= 2
    rosters = [r for r in _sampler().sample_many(8000) if r.mission == mission]
    counts = Counter(r.teams for r in rosters)
    assert set(counts) <= set(fleets), "drew a roster the sim does not list"
    assert counts[fleets[0]] / len(rosters) == pytest.approx(0.5, abs=0.04)
    for other in fleets[1:]:
        share = 0.5 / (len(fleets) - 1)
        assert counts[other] / len(rosters) == pytest.approx(share, abs=0.04)


def test_rosters_come_from_the_sim_at_run_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    only = [
        {
            "name": "changed",
            "mission": CARRIER_BATTLE,
            "fleets": [["carrier", "fighter"], ["carrier", "strafer"]],
        }
    ]
    real = rlf_sim.mission_rosters
    monkeypatch.setattr(
        rlf_sim,
        "mission_rosters",
        lambda mission: only if mission == CARRIER_BATTLE else real(mission),
    )
    drawn = _sampler(mission_weights=(0.0, 1.0, 0.0)).sample_many(20)
    assert {r.teams for r in drawn} == {
        (("carrier", "fighter"), ("carrier", "strafer"))
    }


def test_drafts_obey_the_page_s_budget_rules() -> None:
    costs = load_hull_costs()
    rosters = [r for r in _sampler().sample_many(3000) if r.mission == DEATHMATCH]
    spent_per_size: Counter[int] = Counter()
    for r in rosters:
        assert all(MIN_PER_SIDE <= len(t) <= MAX_PER_SIDE for t in r.teams)
        spent = r.cost(costs)
        assert max(spent) <= 40.0
        spent_per_size[int(max(spent))] += 1
    # A uniform size of 2, 3 or 4 of the cheapest hull's worth.
    assert set(spent_per_size) == {20, 30, 40}
    # Budget 40 can buy a gunship and a cheap ship against four cheap ones.
    assert any({len(r.teams[0]), len(r.teams[1])} == {2, 4} for r in rosters)


def test_draft_defaults_match_the_bundle_s_roster_rules() -> None:
    d = PilotsDistribution()
    info = load_catalogue(Path(ASSETS))["info"]
    rules = roster_rules(
        list(d.draft_hulls), info, MIN_PER_SIDE, d.draft_max_per_side, None
    )
    assert rules.hulls == d.draft_hulls
    assert rules.min_per_side == d.draft_min_per_side
    assert rules.max_per_side == d.draft_max_per_side
    assert rules.budget == d.draft_budget


@pytest.mark.skipif(NODE is None, reason="node is not on PATH")
def test_draws_match_the_live_page_s_own_code() -> None:
    """The page's ``missionRoster`` (TypeScript, run in Node) and the sampler draw from
    the same rosters, mission by mission, within sampling noise."""
    n = 12000
    info = load_catalogue(Path(ASSETS))["info"]
    d = PilotsDistribution()
    rules = roster_rules(
        list(d.draft_hulls), info, MIN_PER_SIDE, d.draft_max_per_side, None
    )
    payload = {
        "n": n,
        "info": info,
        "rules": {
            "hulls": list(rules.hulls),
            "min_per_side": rules.min_per_side,
            "max_per_side": rules.max_per_side,
            "budget": rules.budget,
        },
        "rosters": {m: rlf_sim.mission_rosters(m) for m in MISSIONS},
    }
    script = """
    import { missionRoster } from "./web/src/live/missions.ts";
    let text = "";
    for await (const chunk of process.stdin) text += chunk;
    const { n, info, rules, rosters } = JSON.parse(text);
    let s = 12345;
    const rng = () => {
      s = (s + 0x6d2b79f5) | 0;
      let t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    const out = {};
    for (const mission of ["deathmatch", "carrier_battle", "convoy_escort"]) {
      out[mission] = {};
      for (let i = 0; i < n; i++) {
        const r = missionRoster(mission, { kind: "draft" }, rules, info, rng, rosters);
        const key = JSON.stringify(r.fleets);
        out[mission][key] = (out[mission][key] ?? 0) + 1;
      }
    }
    console.log(JSON.stringify(out));
    """
    done = subprocess.run(
        [
            str(NODE),
            "--experimental-strip-types",
            "--no-warnings",
            "--input-type=module",
            "-e",
            script,
        ],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=120,
    )
    assert done.returncode == 0, done.stderr
    page = json.loads(done.stdout)
    for index, mission in enumerate(MISSIONS):
        weights = tuple(1.0 if k == index else 0.0 for k in range(3))
        ours = Counter(
            json.dumps([list(t) for t in r.teams], separators=(",", ":"))
            for r in _sampler(seed=3, mission_weights=weights).sample_many(n)
        )
        theirs = Counter({k: v for k, v in page[mission].items()})
        if mission != DEATHMATCH:
            assert set(ours) == set(theirs), mission
            assert _distance(ours, theirs) < 0.03, mission
            continue
        # A draft has 480 team pairs: two samples of the same sampler differ by about
        # 0.09 at this n, so the joint distance only bounds the shape. A real mismatch
        # shows in these views, which have few enough values to be sharp.
        assert _distance(ours, theirs) < 0.13
        assert _distance(_size_pairs(ours), _size_pairs(theirs)) < 0.03
        assert _distance(_sides(ours), _sides(theirs)) < 0.04


def _distance(a: Counter[str], b: Counter[str]) -> float:
    """Total variation distance of two samples."""
    n_a, n_b = sum(a.values()), sum(b.values())
    return 0.5 * sum(abs(a[k] / n_a - b[k] / n_b) for k in set(a) | set(b))


def _size_pairs(rosters: Counter[str]) -> Counter[str]:
    """Roster counts by ``"<team 0 ships>v<team 1 ships>"`` (JSON team-pair keys)."""
    out: Counter[str] = Counter()
    for key, count in rosters.items():
        team0, team1 = json.loads(key)
        out[f"{len(team0)}v{len(team1)}"] += count
    return out


def _sides(rosters: Counter[str]) -> Counter[str]:
    """Counts of every side's hulls in slot order, both teams pooled (JSON keys)."""
    out: Counter[str] = Counter()
    for key, count in rosters.items():
        for team in json.loads(key):
            out[",".join(team)] += count
    return out


@pytest.mark.parametrize(
    "overrides",
    [
        {"commander_p": 1.5},
        {"default_roster_share": -0.1},
        {"mission_weights": (1.0, 1.0)},
        {"mission_weights": (0.0, 0.0, 0.0)},
        {"draft_min_per_side": 5},
        {"draft_hulls": ()},
        {"draft_budget": 0.0},
        {"max_ships": MAX_TRAIN_SHIPS},
        {"max_ships": MAX_SHIPS + 1},
        {"kind": "orders"},
    ],
)
def test_bad_parameters_are_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        PilotsDistribution(**overrides)  # type: ignore[arg-type]


def test_budget_below_the_minimum_side_is_rejected() -> None:
    with pytest.raises(ValueError, match="draft_budget"):
        _sampler(draft_budget=15.0)


def test_max_ships_fits_the_biggest_live_roster_and_only_what_is_played() -> None:
    widest = max(
        len(t0) + len(t1)
        for mission in (CARRIER_BATTLE, CONVOY_ESCORT)
        for t0, t1 in live_fleets(mission)
    )
    assert PilotsDistribution().max_ships == MAX_SHIPS == widest
    # A deathmatch-only family needs no more than two full sides.
    small = PilotsDistribution(
        mission_weights=(1.0, 0.0, 0.0), max_ships=MAX_FLEET_SHIPS
    )
    assert PilotsRosterSampler(small, 0).sample().n_ships <= MAX_FLEET_SHIPS


def test_distribution_round_trips_through_a_plain_dict() -> None:
    dist = PilotsDistribution(commander_p=0.25, mission_weights=(0.5, 0.25, 0.25))
    plain = dist.to_dict()
    assert isinstance(plain["mission_weights"], list)
    assert resolve_distribution(plain) == dist
    assert PilotsDistribution.from_dict(plain) == dist
    with pytest.raises(ValueError, match="unknown"):
        PilotsDistribution.from_dict({**plain, "nonsense": 1})


def test_config_round_trips_with_a_family_s_commander_share(tmp_path: Path) -> None:
    config = PPOConfig.preset(
        "scratch",
        rosters="pilots_v1",
        critic="fleet",
        roster_overrides={"commander_p": 0.3},
    )
    assert config.roster_distribution()["commander_p"] == 0.3
    path = tmp_path / "config.yaml"
    write_config(config, path)
    back = read_config(path)
    assert back == config
    dist = resolve_distribution(back.roster_distribution())
    assert isinstance(dist, PilotsDistribution) and dist.commander_p == 0.3


# -- Roster.hide_orders ------------------------------------------------------


def test_roster_carries_hide_orders_and_old_construction_still_works() -> None:
    plain = Roster.of(["fighter"], ["strafer"])
    assert plain.hide_orders == (False, False)
    assert Roster(plain.teams, DEATHMATCH, (SCRIPTED, SCRIPTED)) == plain
    hidden = Roster.of(["fighter"], ["strafer"], hide_orders=(True, False))
    assert hidden != plain
    assert hidden.swapped().hide_orders == (False, True)
    assert hidden.swapped().swapped() == hidden
    with pytest.raises(ValueError, match="hide_orders"):
        Roster.of(["fighter"], ["strafer"], hide_orders=(True,))  # type: ignore[arg-type]


def _env(sampler_seed: int = 0, n: int = 6, **overrides: object) -> RustVecEnv:
    return RustVecEnv(
        ASSETS,
        n,
        [["fighter"], ["fighter"]],
        sampler_seed,
        n_threads=THREADS,
        roster_sampler=_sampler(sampler_seed, **overrides),
    )


def _run_scripted(env: RustVecEnv, steps: int) -> None:
    for _ in range(steps):
        env.scripted_actions()
        env.step()


def test_env_pads_to_the_biggest_live_roster() -> None:
    env = _env()
    assert env.n_ships == MAX_SHIPS
    for i, roster in enumerate(env.rosters):
        n = roster.n_ships
        assert (env.team[i, :n] >= 0).all() and (env.team[i, n:] == -1).all()


def test_hidden_matches_blank_orders_in_obs_and_shown_ones_do_not() -> None:
    # Half hidden, half shown; carrier battles, whose capital ships always have a
    # waypoint and whose strike craft soon have squad orders.
    env = _env(n=12, mission_weights=(0.0, 1.0, 0.0))
    conditions = {r.hide_orders[0] for r in env.rosters}
    assert conditions == {True, False}, "the seed must give both conditions"
    saw_shown_order = False
    for _ in range(400):
        env.scripted_actions()
        env.step()
        hidden_rows = env.order_hidden_rows()
        for i, roster in enumerate(env.rosters):
            real = env.team[i] >= 0
            np.testing.assert_array_equal(hidden_rows[i], real & roster.hide_orders[0])
        h = env.obs[hidden_rows]
        assert np.all(h[:, ORDER_OFF : ORDER_OFF + ORDER_W] == 0.0)
        assert np.all(h[:, ORDER_SHIPS_OFF : ORDER_SHIPS_OFF + ORDER_SHIPS_W] == 0.0)
        extras = h[:, EXTRAS_OFF : EXTRAS_OFF + EXTRAS_W]
        extras = extras.reshape(len(h), EXTRAS_RECORDS, -1)
        assert np.all(extras[..., EXTRAS_ORDER_COL:] == 0.0)
        shown = (env.team >= 0) & ~hidden_rows
        saw_shown_order |= bool((env.obs[shown][:, ORDER_OFF] == 1.0).any())
    assert saw_shown_order


def test_condition_applies_to_each_match_as_rosters_turn_over() -> None:
    env = _env(n=8, mission_weights=(1.0, 0.0, 0.0))
    start = env.raw.episode_count.copy()
    for _ in range(4000):
        env.scripted_actions()
        env.step()
        if (env.raw.episode_count > start).all():
            break
    assert (env.raw.episode_count > start).all(), "every env must finish a match"
    assert all(r.hide_orders[0] == r.hide_orders[1] for r in env.rosters)
    # The sim's view of the current match agrees with the wrapper's.
    for i, roster in enumerate(env.rosters):
        real = env.team[i] >= 0
        assert env.order_hidden_rows()[i][real].all() == roster.hide_orders[0]


def test_env_hide_default_and_explicit_override_keep_working() -> None:
    """An eval's hidden env stays hidden under any roster; an explicit pair wins."""
    fleets = [["fighter"], ["fighter"]]
    env = RustVecEnv(ASSETS, 2, fleets, 0, n_threads=THREADS, hide_orders=(True, False))
    assert env.rosters[0].hide_orders == (True, False)
    roster = Roster.of(["fighter"], ["strafer"])
    env.set_next_roster(0, roster)
    env.set_next_roster(
        1, Roster.of(["fighter"], ["strafer"], hide_orders=(False, True))
    )
    env.reset()
    assert env.rosters[0].hide_orders == (True, False)
    assert env.rosters[1].hide_orders == (True, True)
    env.set_next_roster(0, roster, hide_orders=(False, False))
    env.reset()
    assert env.rosters[0].hide_orders == (False, False)
    assert env.order_hidden_rows()[0].tolist() == [False, False]


def test_hidden_rows_are_no_transit_rows() -> None:
    env = _env(n=8, mission_weights=(0.0, 0.0, 1.0))
    saw_transit = False
    for _ in range(200):
        env.scripted_actions()
        env.step()
        assert not (env.transit_rows() & env.order_hidden_rows()).any()
        saw_transit |= bool(env.transit_rows().any())
    assert saw_transit


def test_docked_reserves_and_capital_ships_are_not_flown() -> None:
    env = _env(
        n=4,
        mission_weights=(0.0, 1.0, 0.0),
        default_roster_share=1.0,
    )
    capital = capital_hull_ids(Path(ASSETS))
    saw_docked = False
    for _ in range(60):
        env.scripted_actions()
        env.step()
        for i in range(env.n_envs):
            for ship in env.raw.mission_state(i)["ships"]:
                if ship["docked"]:
                    saw_docked = True
                    slot = ship["slot"]
                    assert not env.act_mask[i, slot]
                    assert env.hull_id[i, slot] not in capital
                    assert env.obs[i, slot, 0] == 0.0, "the fleet critic reads present"
    assert saw_docked, "the wing of 8 must keep reserves in the hangar"


# -- the trainer -------------------------------------------------------------


def _config(**overrides: object) -> PPOConfig:
    base: dict[str, object] = {
        "assets_dir": ASSETS,
        "n_envs": 6,
        "n_steps": 16,
        "t_tail": 40,
        "n_updates": 3,
        "minibatch": 128,
        "sim_threads": THREADS,
        "torch_threads": THREADS,
        "env_warmup_steps": 60,
        "rosters": "pilots_v1",
        "critic": "fleet",
        "learner_side": "random",
        "order_reward_weight": 1.0,
    }
    base.update(overrides)
    return PPOConfig.preset("scratch", **base)


def test_trains_end_to_end_and_resumes_on_live_rosters(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    config = _config(gamma=0.995, roster_overrides={"commander_p": 0.5})
    trainer = SpikeTrainer(config, run_dir)
    assert trainer.n_ships == MAX_SHIPS
    capital = capital_hull_ids(Path(ASSETS))

    def check(t: SpikeTrainer, row: dict[str, object]) -> None:
        assert row["samples"] != 0
        assert np.isfinite(float(row["value_loss"]))  # type: ignore[arg-type]
        store = t.storage
        assert not (store.learner & np.isin(store.hull, capital)).any()
        assert not (store.learner & (store.team < 0)).any()
        train = store.train_rows()
        assert store.act_mask[: store.n_steps][train].all()
        # Hidden rows were paid no order reward and shown none.
        hidden = store.order_hidden[: store.filled]
        assert not store.order_reward[: store.filled][hidden].any()
        assert not store.has_order[: store.filled][hidden].any()

    assert trainer.train(check) == 3
    assert trainer.storage.order_hidden.any(), "half the matches should be hidden"
    assert (trainer.storage.team >= 0).any()
    assert read_config(run_dir / "config.yaml") == config
    resumed = SpikeTrainer(
        _config(gamma=0.995, n_updates=4, roster_overrides={"commander_p": 0.5}),
        run_dir,
        resume=True,
    )
    assert resumed.env.order_shaping_gamma == pytest.approx(0.995)
    assert resumed.train(None) == 4


def test_order_pay_is_kept_on_shown_rows_and_dropped_on_hidden_rows(
    tmp_path: Path,
) -> None:
    trainer = SpikeTrainer(_config(n_updates=1, n_envs=8), tmp_path / "run")
    raw_pay: list[np.ndarray] = []
    original = trainer._record_step

    def spy(b, rewards, dones, info) -> None:  # type: ignore[no-untyped-def]
        raw_pay.append(info.order_rewards.reshape(-1).copy())
        original(b, rewards, dones, info)
        store = trainer.storage
        hidden = store.order_hidden[b]
        np.testing.assert_array_equal(
            store.order_reward[b][~hidden], raw_pay[-1][~hidden]
        )
        assert not store.order_reward[b][hidden].any()
        np.testing.assert_allclose(
            store.rewards[b], store.team_reward[b] + store.order_reward[b]
        )

    trainer._record_step = spy  # type: ignore[method-assign]
    trainer.run_update()
    pay = np.stack(raw_pay)
    hidden = trainer.storage.order_hidden[: len(pay)]
    assert pay[hidden].any(), "the sim pays hidden rows: this test needs some"
    assert pay[~hidden].any(), "and shown rows"


def test_gamma_outside_the_range_is_rejected_by_the_config() -> None:
    for gamma in (0.0, -0.5, 1.5, float("nan")):
        with pytest.raises(ValueError, match="gamma"):
            _config(gamma=gamma)


# -- the shaping discount -----------------------------------------------------


@pytest.mark.parametrize("gamma", [0.995, 0.99, 0.9])
def test_a_trainer_s_env_carries_its_gamma(tmp_path: Path, gamma: float) -> None:
    trainer = SpikeTrainer(
        _config(gamma=gamma, n_updates=1, n_envs=2, env_warmup_steps=0),
        tmp_path / "run",
    )
    assert trainer.env.order_shaping_gamma == float(np.float32(gamma))


def test_a_gamma_0_99_trainer_has_exactly_the_old_constant(tmp_path: Path) -> None:
    trainer = SpikeTrainer(
        _config(gamma=0.99, n_updates=1, n_envs=2, env_warmup_steps=0),
        tmp_path / "run",
    )
    assert trainer.env.order_shaping_gamma == DEFAULT_ORDER_SHAPING_GAMMA
    assert DEFAULT_ORDER_SHAPING_GAMMA == float(rlf_sim.ORDER_SHAPING_GAMMA)
    assert DEFAULT_ORDER_SHAPING_GAMMA == float(np.float32(0.99))


@pytest.mark.parametrize("gamma", [0.0, -0.1, 1.01, float("nan"), float("inf")])
def test_env_rejects_a_bad_gamma(gamma: float) -> None:
    with pytest.raises(ValueError, match="order_shaping_gamma"):
        RustVecEnv(
            ASSETS,
            1,
            [["fighter"], ["fighter"]],
            0,
            n_threads=1,
            order_shaping_gamma=gamma,
        )


def test_gamma_changes_only_go_to_pay_and_survives_a_roster_swap() -> None:
    """Same seeds at two discounts: the matches and every other reward are identical;
    go-to rows differ by exactly ``(0.995 - 0.99) * phi`` with ``phi <= 0``."""
    team0 = ["carrier", "fighter", "strafer"]
    team1 = ["carrier", "fighter", "fighter"]
    modes = ("random", "random")

    def build(gamma: float) -> RustVecEnv:
        env = RustVecEnv(
            ASSETS,
            6,
            [["fighter"], ["fighter"]],
            17,
            n_threads=THREADS,
            max_ships=6,
            commanders=modes,
            order_shaping_gamma=gamma,
        )
        for i in range(env.n_envs):
            env.set_next_roster(
                i, Roster.of(team0, team1, mission=CARRIER_BATTLE, commanders=modes)
            )
        env.reset()
        assert env.order_shaping_gamma == float(np.float32(gamma))
        return env

    low, high = build(0.99), build(0.995)
    saw_goto = False
    for _ in range(500):
        for env in (low, high):
            env.scripted_actions()
            env.step()
        np.testing.assert_array_equal(low.raw.state_hash(), high.raw.state_hash())
        np.testing.assert_array_equal(low.raw.rewards, high.raw.rewards)
        difference = high.order_rewards - low.order_rewards
        goto = low.order_tracks()["standing_kind"] == 3
        assert not difference[~goto].any()
        assert (difference <= 1e-6).all(), "phi <= 0, so a higher gamma pays less"
        phi = difference / 0.005
        assert (phi >= -2.5).all(), "phi is at most a couple of arena radii"
        saw_goto |= bool((difference < -1e-6).any())
    assert saw_goto, "the random commander must give some go-to far from its point"
