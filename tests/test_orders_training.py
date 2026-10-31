"""Stage B training (M3, lab/runs/2026-10-31-order-pilot): widening a v1 net to the
order obs, frozen pool entries on the obs prefix, the KL anchor on unordered rows,
the orders_v1 roster mix, and capital ships staying out of the learner's rows."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import numpy as np
import pytest
import torch

from spacefight.env import rust_env
from spacefight.env.rosters import (
    CAPITAL_ROLES,
    CARRIER_BATTLE,
    CONVOY_ESCORT,
    DEATHMATCH,
    FLEET_HULLS,
    MAX_TRAIN_SHIPS,
    RANDOM,
    SCRIPTED,
    OrdersDistribution,
    OrdersRosterSampler,
    Roster,
    capital_hull_ids,
    load_hull_roles,
    make_sampler,
    resolve_distribution,
)
from spacefight.rl.opponents import (
    OpponentAssigner,
    OpponentKind,
    OpponentSchedule,
)
from spacefight.rl.spike_policy import (
    OBS_DIM,
    ORDER_OBS_DIM,
    PILOT_OBS_DIMS,
    FleetCritic,
    HeadMasks,
    SpikeActor,
    SpikeCritic,
    SampleOut,
    fit_obs,
    head_kl,
    load_policy,
    save_policy,
    widen_actor,
    widen_critic,
)
from spacefight.rl.spike_ppo import (
    PPOBatch,
    PPOConfig,
    SpikeTrainer,
    UpdateSettings,
    episode_class,
    ppo_update,
)

ASSETS = str(Path(__file__).resolve().parent.parent / "assets")
THREADS = 2
torch.set_num_threads(THREADS)


def _masks(n: int, seed: int) -> HeadMasks:
    rng = np.random.default_rng(seed)
    turret = rng.random((n, 6)) < 0.6
    return HeadMasks.from_numpy(
        rng.random((n, 8)) < 0.7, turret, turret & (rng.random((n, 6)) < 0.5)
    )


def _order_obs(n: int, seed: int, has_order: float = 1.0) -> torch.Tensor:
    gen = torch.Generator().manual_seed(seed)
    obs = torch.randn(n, ORDER_OBS_DIM, generator=gen)
    obs[:, OBS_DIM] = has_order
    return obs


# ------------------------------------------------------------------ widening


def test_widened_actor_matches_v1_on_any_obs_with_the_same_prefix() -> None:
    torch.manual_seed(0)
    narrow = SpikeActor()
    wide = widen_actor(narrow, ORDER_OBS_DIM)
    obs = _order_obs(64, 1)  # random order block, not zero
    with torch.no_grad():
        # Identical up to float32 summation order (BLAS blocks a 403-long dot
        # product differently from a 385-long one; the extra terms are exact zeros).
        torch.testing.assert_close(
            wide(obs), narrow(obs[:, :OBS_DIM]), rtol=0, atol=1e-5
        )
        masks = _masks(64, 2)
        np.testing.assert_array_equal(
            wide.sample(obs, masks, deterministic=True).actions.numpy(),
            narrow.sample(obs[:, :OBS_DIM], masks, deterministic=True).actions.numpy(),
        )
    assert wide.obs_dim == ORDER_OBS_DIM and narrow.obs_dim == OBS_DIM
    first = wide.net[0]
    assert isinstance(first, torch.nn.Linear)
    assert torch.equal(first.weight[:, OBS_DIM:], torch.zeros(256, 18))


@pytest.mark.parametrize("kind", ["spike", "fleet"])
def test_widened_critic_matches_v1_on_the_prefix(kind: str) -> None:
    torch.manual_seed(1)
    narrow = SpikeCritic() if kind == "spike" else FleetCritic()
    if isinstance(narrow, FleetCritic):  # a correction that is not zero
        last = narrow.mix[-1]
        assert isinstance(last, torch.nn.Linear)
        torch.nn.init.normal_(last.weight)
    wide = widen_critic(narrow, ORDER_OBS_DIM)
    obs = _order_obs(10, 2).reshape(2, 5, ORDER_OBS_DIM)
    obs[..., 0] = 1.0
    team = torch.tensor([[0, 0, 1, 1, -1]] * 2)
    rows = torch.tensor([[0, 0], [0, 2], [1, 1], [1, 3]])
    with torch.no_grad():
        got = wide.forward_set(obs, team, rows)
        want = narrow.forward_set(obs[..., :OBS_DIM].contiguous(), team, rows)
    torch.testing.assert_close(got, want, rtol=0, atol=1e-5)


def test_checkpoints_record_and_restore_the_obs_width(tmp_path: Path) -> None:
    actor = widen_actor(SpikeActor(), ORDER_OBS_DIM)
    critic = widen_critic(FleetCritic(), ORDER_OBS_DIM)
    save_policy(tmp_path / "wide.pt", actor, critic, {"sim_version": 5})
    loaded, loaded_critic, _ = load_policy(tmp_path / "wide.pt")
    assert loaded.obs_dim == ORDER_OBS_DIM == loaded_critic.obs_dim
    obs = _order_obs(4, 3)
    with torch.no_grad():
        torch.testing.assert_close(loaded(obs), actor(obs))
    # A pre-v5 file (no obs_dim key) loads as 385 wide.
    payload = torch.load(tmp_path / "wide.pt", weights_only=True)
    narrow = SpikeActor()
    payload["actor"] = narrow.state_dict()
    payload["critic"] = FleetCritic().state_dict()
    del payload["obs_dim"], payload["critic_obs_dim"]
    torch.save(payload, tmp_path / "old.pt")
    assert load_policy(tmp_path / "old.pt")[0].obs_dim == OBS_DIM


def test_pilot_obs_dims_match_the_sim() -> None:
    assert PILOT_OBS_DIMS[rust_env.SIM_VERSION] == rust_env.OBS_DIM
    for version, dim in rust_env.PILOT_OBS_DIMS.items():
        assert PILOT_OBS_DIMS[version] == dim


def test_narrow_nets_fly_on_the_prefix_and_never_on_a_narrower_obs() -> None:
    obs = _order_obs(3, 4)
    assert fit_obs(obs, OBS_DIM).shape == (3, OBS_DIM)
    assert fit_obs(obs, ORDER_OBS_DIM) is obs
    with pytest.raises(ValueError, match="older sim"):
        fit_obs(obs[:, :OBS_DIM], ORDER_OBS_DIM)


# ------------------------------------------------------------------ KL anchor


def test_head_kl_is_zero_for_the_same_net_and_ignores_masked_heads() -> None:
    torch.manual_seed(2)
    actor = SpikeActor()
    obs = torch.randn(16, OBS_DIM)
    masks = _masks(16, 0)
    valid = masks.head_valid()
    heads = actor.head_log_softmax(obs)
    torch.testing.assert_close(head_kl(heads, heads, valid), torch.zeros(16))
    other = SpikeActor().head_log_softmax(obs)
    kl = head_kl(heads, other, valid)
    assert bool((kl > 0).all())
    none = torch.zeros_like(valid)
    torch.testing.assert_close(head_kl(heads, other, none), torch.zeros(16))


def _anchor_batch(n: int, anchored: torch.Tensor) -> PPOBatch:
    obs = _order_obs(n, 5, has_order=0.0).reshape(n, 1, ORDER_OBS_DIM)
    obs[:, 0, OBS_DIM] = (~anchored).float()
    zeros = torch.zeros(n)
    return PPOBatch(
        obs=obs,
        team=torch.zeros(n, 1, dtype=torch.int64),
        rows=torch.stack([torch.arange(n), torch.zeros(n, dtype=torch.int64)], 1),
        masks=_masks(n, 1),
        actions=torch.ones(n, 21, dtype=torch.int64),
        labels=torch.ones(n, 21, dtype=torch.int64),
        old_log_prob=zeros,
        advantages=zeros,
        returns=zeros,
        anchor_rows=anchored,
        pull_rows=torch.ones(n, dtype=torch.bool),
    )


def _settings(coeff: float) -> UpdateSettings:
    return UpdateSettings(
        clip_eps=0.2,
        beta=0.0,
        actor_frozen=False,
        ent_coeff=0.0,
        vf_coeff=0.0,
        max_grad_norm=1e9,
        epochs=1,
        minibatch=1 << 20,
        entropy_floor=0.0,
        entropy_floor_coeff=0.0,
        kl_anchor_coeff=coeff,
    )


def test_kl_anchor_pulls_only_unordered_rows_toward_the_anchor() -> None:
    """With zero advantages the only actor gradient is the anchor's: rows with an
    order feel none of it, rows without move toward the anchor."""
    torch.manual_seed(3)
    anchor = SpikeActor()  # 385 wide: sees the prefix
    n = 64
    anchored = torch.arange(n) % 2 == 0
    batch = _anchor_batch(n, anchored)
    obs = batch.obs[:, 0]
    actor = widen_actor(SpikeActor(), ORDER_OBS_DIM)
    critic = SpikeCritic(obs_dim=ORDER_OBS_DIM)
    valid = batch.masks.head_valid()

    def kl() -> torch.Tensor:
        with torch.no_grad():
            return head_kl(
                anchor.head_log_softmax(obs[:, :OBS_DIM]),
                actor.head_log_softmax(obs),
                valid,
            )

    before = kl()
    opt = torch.optim.SGD(actor.parameters(), lr=0.05)
    critic_opt = torch.optim.SGD(critic.parameters(), lr=0.0)
    for _ in range(30):
        metrics = ppo_update(
            actor, critic, opt, critic_opt, batch, _settings(1.0), anchor
        )
    after = kl()
    assert after[anchored].mean() < 0.5 * before[anchored].mean()
    assert metrics["kl_anchor_share"] == pytest.approx(0.5)
    assert {"kl_anchor", "kl_anchor_ordered"} <= set(metrics)


def test_kl_anchor_has_no_gradient_without_unordered_rows() -> None:
    torch.manual_seed(4)
    anchor = SpikeActor()
    batch = _anchor_batch(32, torch.zeros(32, dtype=torch.bool))
    actor = widen_actor(SpikeActor(), ORDER_OBS_DIM)
    critic = SpikeCritic(obs_dim=ORDER_OBS_DIM)
    start = [p.detach().clone() for p in actor.parameters()]
    opt = torch.optim.SGD(actor.parameters(), lr=1.0)
    metrics = ppo_update(
        actor,
        critic,
        opt,
        torch.optim.SGD(critic.parameters(), lr=0.0),
        batch,
        _settings(10.0),
        anchor,
    )
    for p, q in zip(actor.parameters(), start):
        torch.testing.assert_close(p, q, rtol=0, atol=0)
    assert metrics["kl_anchor_share"] == 0.0
    assert "kl_anchor" not in metrics


# ------------------------------------------------------------------ the pool


def test_snapshot_draws_keep_the_seed_share_as_the_pool_grows() -> None:
    schedule = OpponentSchedule([[0, 0.0, 0.0, 1.0]])
    assigner = OpponentAssigner(
        4000, schedule, np.random.default_rng(0), n_seeds=1, seed_p=0.5
    )
    assigner.assign_all(0, pool_size=9)  # the seed + 8 periodic checkpoints
    assert (assigner.kinds == OpponentKind.SNAPSHOT).all()
    share = float(np.mean(assigner.snapshot == 0))
    assert share == pytest.approx(0.5, abs=0.03)
    assert set(np.unique(assigner.snapshot)) == set(range(9))
    assigner.assign_all(0, pool_size=1)
    assert (assigner.snapshot == 0).all()


# ------------------------------------------------------------------ rosters


def test_orders_preset_round_trips_and_draws_the_planned_mix() -> None:
    dist = resolve_distribution("orders_v1")
    assert isinstance(dist, OrdersDistribution)
    assert resolve_distribution(dist.to_dict()) == dist
    rosters = OrdersRosterSampler(dist, 0).sample_many(4000)
    missions = Counter(r.mission for r in rosters)
    for mission, share in (
        (DEATHMATCH, 0.4),
        (CARRIER_BATTLE, 0.3),
        (CONVOY_ESCORT, 0.3),
    ):
        assert missions[mission] / 4000 == pytest.approx(share, abs=0.03)
    modes = Counter(c for r in rosters for c in r.commanders)
    assert modes[RANDOM] / (2 * 4000) == pytest.approx(0.5, abs=0.02)
    assert set(modes) == {RANDOM, SCRIPTED}


def test_orders_rosters_have_the_planned_shapes_and_fit_twelve_slots() -> None:
    roles = load_hull_roles()
    for r in OrdersRosterSampler(OrdersDistribution(), 1).sample_many(1500):
        assert r.n_ships <= MAX_TRAIN_SHIPS
        caps = [
            [roles[h] for h in team if roles[h] in CAPITAL_ROLES] for team in r.teams
        ]
        if r.mission == DEATHMATCH:
            assert caps == [[], []]
            assert set(r.teams[0]) | set(r.teams[1]) <= set(FLEET_HULLS)
        elif r.mission == CARRIER_BATTLE:
            assert caps == [["carrier"], ["carrier"]]
            for team in r.teams:
                assert team[0] == "carrier" and 4 <= len(team) - 1 <= 5
        else:
            n_transports = r.teams[0].count("freighter")
            assert caps == [["transport"] * n_transports, []]
            assert 3 <= n_transports <= 4
            assert r.teams[0][:n_transports] == ("freighter",) * n_transports
            assert 2 <= len(r.teams[0]) - n_transports <= 3
            assert 4 <= len(r.teams[1]) <= 5


def test_convoys_cannot_swap_sides_and_classes_name_the_learner_side() -> None:
    convoy = Roster.of(["freighter", "fighter"], ["fighter"], mission=CONVOY_ESCORT)
    with pytest.raises(ValueError, match="convoy"):
        convoy.swapped()
    assert episode_class(convoy, 0) == "convoy_escort/defend"
    assert episode_class(convoy, 1) == "convoy_escort/attack"
    fleet = Roster.of(["fighter"], ["strafer", "gunship"])
    assert episode_class(fleet, 1) == "1v2"


def test_orders_env_pads_mission_rosters_to_twelve_slots() -> None:
    sampler = make_sampler(OrdersDistribution(), 0)
    env = rust_env.RustVecEnv(
        ASSETS,
        12,
        [["fighter"], ["fighter"]],
        0,
        n_threads=THREADS,
        roster_sampler=sampler,
    )
    assert env.n_ships == MAX_TRAIN_SHIPS == rust_env.MAX_TRAIN_SHIPS
    for i, roster in enumerate(env.rosters):
        n = roster.n_ships
        assert (env.team[i, :n] >= 0).all() and (env.team[i, n:] == -1).all()
    # Each roster's own commanders and clock reach the sim: run every env to its
    # end on scripts and check the clock of the ones that timed out.
    assert {c for r in env.rosters for c in r.commanders} == {RANDOM, SCRIPTED}


# ------------------------------------------------------------------ the trainer


def _orders_config(tmp_path: Path, init: str, **overrides: object) -> PPOConfig:
    base: dict[str, object] = {
        "assets_dir": ASSETS,
        "n_envs": 8,
        "n_steps": 16,
        "minibatch": 128,
        "sim_threads": THREADS,
        "torch_threads": THREADS,
        "env_warmup_steps": 60,
        "rosters": "orders_v1",
        "critic": "fleet",
        "learner_side": "random",
        "beta_start": 0.0,
        "critic_warmup_updates": 0,
        "obs_dim": ORDER_OBS_DIM,
    }
    base.update(overrides)
    return PPOConfig.preset(init, **base)


@pytest.fixture
def v1_like(tmp_path: Path) -> Path:
    """A 385-wide checkpoint standing in for fleet pilot v1."""
    torch.manual_seed(5)
    path = tmp_path / "v1.pt"
    save_policy(path, SpikeActor(), SpikeCritic(), {"kind": "test", "sim_version": 3})
    return path


def test_trainer_widens_a_v1_init_to_the_sim_and_starts_as_v1(
    tmp_path: Path, v1_like: Path
) -> None:
    trainer = SpikeTrainer(_orders_config(tmp_path, str(v1_like)), tmp_path / "run")
    assert trainer.actor.obs_dim == rust_env.OBS_DIM
    v1 = load_policy(v1_like)[0]
    obs = torch.from_numpy(trainer.env.obs.reshape(-1, rust_env.OBS_DIM).copy())
    with torch.no_grad():
        torch.testing.assert_close(
            trainer.actor(obs), v1(obs[:, :OBS_DIM]), rtol=0, atol=1e-5
        )


def test_learner_and_snapshot_rows_never_include_capital_ships(
    tmp_path: Path, v1_like: Path
) -> None:
    cfg = _orders_config(
        tmp_path,
        str(v1_like),
        pool_seed=[str(v1_like)],
        pool_seed_p=1.0,
        opponent_bands=[[0, 0.0, 0.5, 0.5]],
        roster_overrides={"mission_weights": [0.0, 0.5, 0.5]},
        n_updates=1,
    )
    trainer = SpikeTrainer(cfg, tmp_path / "run")
    seen: list[np.ndarray] = []
    real_actor = trainer.pool.actor

    def spy(index: int) -> SpikeActor:
        actor = real_actor(index)
        original = actor.sample

        def sample(
            obs: torch.Tensor, masks: HeadMasks, deterministic: bool = False
        ) -> SampleOut:
            seen.append(np.array([obs.shape[1]]))
            return original(obs, masks, deterministic)

        actor.sample = sample  # type: ignore[method-assign]
        return actor

    trainer.pool.actor = spy  # type: ignore[method-assign]
    trainer.run_update()
    store = trainer.storage
    capital = np.isin(store.hull, capital_hull_ids(Path(ASSETS))) & (store.team >= 0)
    assert capital.any()
    assert not (store.learner & capital).any()
    assert not (store.side & capital).any()
    assert seen and all(int(w[0]) == OBS_DIM for w in seen)
    # Capital rows act on their script's labels.
    np.testing.assert_array_equal(store.actions[capital], store.labels[capital])


def test_learner_side_is_drawn_per_episode(tmp_path: Path, v1_like: Path) -> None:
    trainer = SpikeTrainer(
        _orders_config(tmp_path, str(v1_like), n_envs=64), tmp_path / "run"
    )
    assert 0 < int(trainer.learner_team.sum()) < 64
    fixed = SpikeTrainer(
        _orders_config(tmp_path, str(v1_like), learner_side="team0"),
        tmp_path / "run2",
    )
    assert not fixed.learner_team.any()


def test_orders_ppo_logs_both_reward_parts_and_the_anchor(
    tmp_path: Path, v1_like: Path
) -> None:
    cfg = _orders_config(
        tmp_path,
        str(v1_like),
        kl_anchor=str(v1_like),
        kl_anchor_coeff=0.1,
        n_updates=2,
        order_reward_weight=0.3,
    )
    trainer = SpikeTrainer(cfg, tmp_path / "run")
    rows = [trainer.run_update() for _ in range(2)]
    last = rows[-1]
    for key in ("reward_team", "reward_order", "reward_order_weighted", "kl_anchor"):
        assert last[key] is not None, key
    total = float(last["reward_team"]) + float(last["reward_order_weighted"])  # type: ignore[arg-type]
    assert last["reward_mean"] == pytest.approx(total, abs=1e-6)
    assert 0.0 < float(last["has_order_share"]) < 1.0  # type: ignore[arg-type]
    assert float(last["kl_anchor_share"]) == pytest.approx(  # type: ignore[arg-type]
        1.0 - float(last["has_order_share"]), abs=0.05  # type: ignore[arg-type]
    )
