"""Run B2b (lab/runs/2026-10-31-order-pilot-b2b): the script pull on ordered rows, the
rollout cache of the KL anchor, the ordered DAgger round, and the random commander's
hold points near the squad's fight."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import torch

from spacefight.env import rust_env
from spacefight.env.rosters import (
    CARRIER_BATTLE,
    CONVOY_ESCORT,
    DEATHMATCH,
    RANDOM,
    SCRIPTED,
    OrdersDistribution,
    Roster,
    capital_hull_ids,
    make_sampler,
)
from spacefight.rl import bc
from spacefight.rl.spike_policy import (
    N_LOGITS,
    OBS_DIM,
    ORDER_OBS_DIM,
    HeadLogSoftmax,
    HeadMasks,
    SpikeActor,
    SpikeCritic,
    fit_obs,
    head_set_columns,
    load_policy,
    save_policy,
    widen_actor,
)
from spacefight.rl.spike_ppo import (
    PPOBatch,
    PPOConfig,
    SpikeTrainer,
    UpdateSettings,
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


def _batch(
    n: int,
    pull: torch.Tensor,
    anchored: torch.Tensor | None = None,
    reference: torch.Tensor | None = None,
    seed: int = 5,
) -> PPOBatch:
    gen = torch.Generator().manual_seed(seed)
    obs = torch.randn(n, 1, ORDER_OBS_DIM, generator=gen)
    labels = torch.randint(0, 2, (n, 21), generator=gen)
    zeros = torch.zeros(n)
    return PPOBatch(
        obs=obs,
        team=torch.zeros(n, 1, dtype=torch.int64),
        rows=torch.stack([torch.arange(n), torch.zeros(n, dtype=torch.int64)], 1),
        masks=_masks(n, 1),
        actions=torch.ones(n, 21, dtype=torch.int64),
        labels=labels,
        old_log_prob=zeros,
        advantages=zeros,
        returns=zeros,
        anchor_rows=(
            torch.zeros(n, dtype=torch.bool) if anchored is None else anchored
        ),
        pull_rows=pull,
        anchor_reference=reference,
    )


def _settings(
    beta: float, kl: float = 0.0, heads: str = "all", epochs: int = 1
) -> UpdateSettings:
    return UpdateSettings(
        clip_eps=0.2,
        beta=beta,
        actor_frozen=False,
        ent_coeff=0.0,
        vf_coeff=0.0,
        max_grad_norm=1e9,
        epochs=epochs,
        minibatch=1 << 20,
        entropy_floor=0.0,
        entropy_floor_coeff=0.0,
        kl_anchor_coeff=kl,
        beta_heads=heads,
    )


def _nets(seed: int) -> tuple[SpikeActor, SpikeCritic]:
    torch.manual_seed(seed)
    return widen_actor(SpikeActor(), ORDER_OBS_DIM), SpikeCritic(obs_dim=ORDER_OBS_DIM)


def _update(
    actor: SpikeActor,
    critic: SpikeCritic,
    batch: PPOBatch,
    settings: UpdateSettings,
    anchor: SpikeActor | None = None,
    lr: float = 0.05,
) -> dict[str, float]:
    return ppo_update(
        actor,
        critic,
        torch.optim.SGD(actor.parameters(), lr=lr),
        torch.optim.SGD(critic.parameters(), lr=0.0),
        batch,
        settings,
        anchor,
    )


def _label_nll(actor: SpikeActor, batch: PPOBatch) -> torch.Tensor:
    with torch.no_grad():
        _, _, label_lp = actor.evaluate_heads_and_labels(
            batch.obs[:, 0], batch.masks, batch.actions, batch.labels
        )
    return -label_lp.sum(-1)


# ------------------------------------------------------------ β on ordered rows


def test_pull_on_no_rows_moves_nothing() -> None:
    """With zero advantages the pull is the only actor gradient; no pulled row in
    the batch means no step at all, whatever beta is."""
    actor, critic = _nets(0)
    start = [p.detach().clone() for p in actor.parameters()]
    metrics = _update(
        actor, critic, _batch(32, torch.zeros(32, dtype=torch.bool)), _settings(10.0)
    )
    for p, q in zip(actor.parameters(), start):
        torch.testing.assert_close(p, q, rtol=0, atol=0)
    assert "aux_script_nll" in metrics and "aux_script_nll_pulled" not in metrics


def test_pull_averages_over_the_pulled_rows_only() -> None:
    n = 64
    pull = torch.arange(n) % 3 == 0
    actor, critic = _nets(1)
    batch = _batch(n, pull)
    nll = _label_nll(actor, batch)
    metrics = _update(actor, critic, batch, _settings(0.0))
    assert metrics["aux_script_nll_pulled"] == pytest.approx(
        float(nll[pull].mean()), rel=1e-5
    )
    assert metrics["aux_script_nll"] == pytest.approx(float(nll.mean()), rel=1e-5)
    # Pulling lowers the pulled rows' NLL.
    actor, critic = _nets(1)
    for _ in range(20):
        _update(actor, critic, batch, _settings(1.0))
    after = _label_nll(actor, batch)
    assert after[pull].mean() < 0.8 * nll[pull].mean()


def test_pull_on_all_rows_is_the_fleet_runs_loss() -> None:
    """beta_rows "all" (every row pulled, every head) takes exactly the step the
    pre-B2b loss (mean script NLL over the batch) took."""
    n = 48
    batch = _batch(n, torch.ones(n, dtype=torch.bool))
    a1, c1 = _nets(2)
    _update(a1, c1, batch, _settings(0.5))
    a2, _ = _nets(2)
    opt = torch.optim.SGD(a2.parameters(), lr=0.05)
    heads = a2.evaluate_with_heads(
        batch.obs[:, 0], batch.masks, batch.actions, batch.labels
    )
    log_ratio = heads[0].sum(-1) - batch.old_log_prob
    pg = -(log_ratio.exp() * 0.0).mean()
    loss = pg + 0.5 * (-heads[2].sum(-1).mean())
    opt.zero_grad()
    loss.backward()
    opt.step()
    for p, q in zip(a1.parameters(), a2.parameters()):
        torch.testing.assert_close(p, q, rtol=0, atol=1e-7)


def test_movement_pull_leaves_aim_and_fire_labels_out() -> None:
    cols = head_set_columns("movement")
    assert cols[:8].all() and cols[20] and not cols[8:20].any()
    n = 32
    batch = _batch(n, torch.ones(n, dtype=torch.bool))
    actor, critic = _nets(3)
    with torch.no_grad():
        _, _, label_lp = actor.evaluate_heads_and_labels(
            batch.obs[:, 0], batch.masks, batch.actions, batch.labels
        )
    metrics = _update(actor, critic, batch, _settings(0.0, heads="movement"))
    expected = float(-label_lp[:, cols].sum(-1).mean())
    assert metrics["aux_script_nll_pulled"] == pytest.approx(expected, rel=1e-5)


def test_scripts_follow_orders_except_scripted_deathmatch_ones() -> None:
    dm = Roster.of(["fighter"], ["fighter"], commanders=(SCRIPTED, RANDOM))
    assert dm.scripts_follow_orders() == (False, True)
    carrier = Roster.of(
        ["carrier", "fighter"], ["carrier", "fighter"], mission=CARRIER_BATTLE
    )
    assert carrier.scripts_follow_orders() == (True, True)
    convoy = Roster.of(
        ["freighter", "fighter"],
        ["fighter"],
        mission=CONVOY_ESCORT,
        commanders=(RANDOM, SCRIPTED),
    )
    assert convoy.scripts_follow_orders() == (True, True)
    assert Roster.of(
        ["fighter"], ["fighter"], mission=DEATHMATCH
    ).scripts_follow_orders() == (False, False)


def test_scripted_order_rows_skip_advisory_deathmatch_orders() -> None:
    """Advisory (scripted deathmatch) orders show in the obs but are not script
    labels; a random commander's and a mission commander's are."""
    rosters = [
        Roster.of(["fighter", "strafer"], ["fighter", "gunship"]),
        Roster.of(
            ["fighter", "strafer"],
            ["fighter", "gunship"],
            commanders=(RANDOM, SCRIPTED),
        ),
        Roster.of(
            ["carrier", "fighter", "fighter", "strafer"],
            ["carrier", "fighter", "gunship", "fighter"],
            mission=CARRIER_BATTLE,
        ),
    ]
    env = rust_env.RustVecEnv(
        ASSETS, 3, [["fighter"], ["fighter"]], 3, n_threads=THREADS, max_ships=8
    )
    for i, r in enumerate(rosters):
        env.set_next_roster(i, r)
    env.reset()
    seen_order = np.zeros((3, 8), dtype=np.bool_)
    seen_rows = np.zeros((3, 8), dtype=np.bool_)
    for _ in range(600):
        env.scripted_actions()
        env.step()
        has = env.obs[..., rust_env.HAS_ORDER_COL] > 0.5
        rows = env.scripted_order_rows()
        assert not (rows & ~has).any()
        seen_order |= has
        seen_rows |= rows
    team = env.team
    assert seen_order[0].any() and not seen_rows[0].any()  # advisory only
    assert seen_rows[1][team[1] == 0].any() and not seen_rows[1][team[1] == 1].any()
    assert seen_rows[2].any()


# ------------------------------------------------------------ the anchor cache


def test_head_log_softmax_flat_round_trips_exactly() -> None:
    torch.manual_seed(4)
    heads = SpikeActor().head_log_softmax(torch.randn(9, OBS_DIM))
    flat = heads.flat()
    assert flat.shape == (9, N_LOGITS)
    back = HeadLogSoftmax.from_flat(flat)
    for name in ("ternary", "fire", "power"):
        torch.testing.assert_close(
            getattr(back, name), getattr(heads, name), rtol=0, atol=0
        )


@pytest.mark.parametrize("minibatch", [1 << 20, 32])
def test_cached_anchor_gives_the_same_loss_and_step(minibatch: int) -> None:
    """The anchor's log-softmax cached once per sample: the same KL, metrics and
    parameter steps over 3 epochs as running the anchor net in every minibatch.
    Bit for bit when the cache was computed on the same batch shape (one
    minibatch); to float round-off when the minibatches are smaller than the
    batch the cache saw (the anchor's matmuls then block differently)."""
    torch.manual_seed(6)
    anchor = SpikeActor()  # v1-wide: sees the prefix
    n = 96
    anchored = torch.arange(n) % 2 == 0
    plain = _batch(n, ~anchored, anchored)
    with torch.no_grad():
        cache = anchor.head_log_softmax(fit_obs(plain.obs[:, 0], OBS_DIM)).flat()
    cached = replace(plain, anchor_reference=cache)
    settings = replace(_settings(0.1, kl=0.5, epochs=3), minibatch=minibatch)
    results = []
    for batch in (plain, cached):
        actor, critic = _nets(7)
        torch.manual_seed(8)
        metrics = _update(actor, critic, batch, settings, anchor)
        results.append((metrics, [p.detach().clone() for p in actor.parameters()]))
    (m1, p1), (m2, p2) = results
    assert m1.keys() == m2.keys() and "kl_anchor" in m1
    exact = minibatch >= n
    for key in m1:
        if exact:
            assert m1[key] == m2[key], key
        else:
            assert m1[key] == pytest.approx(m2[key], rel=1e-4, abs=1e-7), key
    for a, b in zip(p1, p2):
        torch.testing.assert_close(a, b, rtol=0, atol=0 if exact else 1e-6)


# ------------------------------------------------------------ the trainer


@pytest.fixture
def v1_like(tmp_path: Path) -> Path:
    torch.manual_seed(5)
    path = tmp_path / "v1.pt"
    save_policy(path, SpikeActor(), SpikeCritic(), {"kind": "test", "sim_version": 3})
    return path


def _config(init: str, **overrides: object) -> PPOConfig:
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
        "beta_start": 0.1,
        "beta_end": 0.0,
        "beta_decay_start": 30,
        "beta_decay_end": 300,
        "critic_warmup_updates": 0,
        "obs_dim": ORDER_OBS_DIM,
    }
    base.update(overrides)
    return PPOConfig.preset(init, **base)


def test_trainer_pulls_ordered_rows_and_caches_the_anchor(
    tmp_path: Path, v1_like: Path
) -> None:
    cfg = _config(
        str(v1_like),
        kl_anchor=str(v1_like),
        kl_anchor_coeff=0.1,
        beta_rows="ordered",
        beta_heads="movement",
        n_updates=2,
    )
    trainer = SpikeTrainer(cfg, tmp_path / "run")
    batches: list[PPOBatch] = []
    has_orders: list[torch.Tensor] = []
    lives: list[torch.Tensor] = []
    original = trainer._prepare_batch

    def spy() -> tuple[PPOBatch, dict[str, object]]:
        # The batch's obs are views of the rollout buffer: read them now, before
        # the update shifts the tail over them.
        batch, stats = original()
        batches.append(batch)
        obs = batch.obs[batch.rows[:, 0], batch.rows[:, 1]].clone()
        has_orders.append(obs[:, OBS_DIM] > 0.5)
        with torch.no_grad():
            lives.append(trainer.anchor.head_log_softmax(fit_obs(obs, OBS_DIM)).flat())  # type: ignore[union-attr]
        return batch, stats

    trainer._prepare_batch = spy  # type: ignore[method-assign]
    row = trainer.run_update()
    batch = batches[0]
    # Pulled rows show an order; anchored rows do not; the two never overlap.
    has_order = has_orders[0]
    assert not (batch.pull_rows & ~has_order).any()
    assert not (batch.pull_rows & batch.anchor_rows).any()
    assert 0.0 < float(row["beta_rows_share"]) <= float(row["has_order_share"])  # type: ignore[arg-type]
    assert row["aux_script_nll_pulled"] is not None and row["beta"] == 0.1
    # The cache is the anchor on each training row's obs prefix.
    assert batch.anchor_reference is not None
    torch.testing.assert_close(batch.anchor_reference, lives[0], rtol=0, atol=1e-5)
    # The tail carried into the next rollout keeps its cache.
    trainer.run_update()
    torch.testing.assert_close(batches[1].anchor_reference, lives[1], rtol=0, atol=1e-5)


def test_trainer_without_an_anchor_keeps_no_cache(
    tmp_path: Path, v1_like: Path
) -> None:
    trainer = SpikeTrainer(_config(str(v1_like), n_updates=1), tmp_path / "run")
    assert trainer.storage.anchor_logp.shape[1] == 0
    row = trainer.run_update()
    assert row["beta_rows_share"] == 1.0
    assert row["kl_anchor"] is None


def test_bad_beta_rows_or_heads_are_rejected(v1_like: Path) -> None:
    with pytest.raises(ValueError, match="beta_rows"):
        _config(str(v1_like), beta_rows="some")
    with pytest.raises(ValueError, match="beta_heads"):
        _config(str(v1_like), beta_heads="fire")


# ------------------------------------------------------------ ordered DAgger


def test_ordered_dagger_keeps_ordered_strike_rows_and_the_critic(
    tmp_path: Path, v1_like: Path
) -> None:
    actor, critic, _ = load_policy(v1_like)
    init = tmp_path / "wide.pt"
    save_policy(init, widen_actor(actor, ORDER_OBS_DIM), critic, {"kind": "test"})
    data = bc.collect_on_policy(
        load_policy(init)[0],
        3000,
        n_envs=8,
        n_threads=THREADS,
        seed=2,
        rosters="orders_v1",
        keep="ordered",
    )
    assert data.obs.shape[1] == ORDER_OBS_DIM
    assert (data.obs[:, OBS_DIM] > 0.5).all()  # every row shows an order
    capital = np.isin(data.hull, capital_hull_ids(Path(ASSETS)))
    assert not capital.any()
    result = bc.ordered_dagger_round(
        init,
        tmp_path / "dagger",
        20000,
        bc.TrainConfig(epochs=1, batch_size=512, lr=1e-4, heads="movement"),
        n_threads=THREADS,
        n_envs=40,
    )
    new_actor, new_critic, meta = load_policy(result.checkpoint)
    assert new_actor.obs_dim == ORDER_OBS_DIM and meta["source"] == "bc_dagger_ordered"
    for p, q in zip(new_critic.state_dict().values(), critic.state_dict().values()):
        torch.testing.assert_close(p, q, rtol=0, atol=0)
    assert result.report["holdout_agreement_after"] is not None


# ------------------------------------------------------------ hold points


# The random commander's point order: hold (SIM_VERSION 5), go-to from v6 on (the
# same near-action draw, docs/M3_PLAN.md "Stage B3").
_POINT = "goto" if rust_env.SIM_VERSION >= 6 else "hold"


def _hold_draw_distances(
    n_envs: int, steps: int, seed: int
) -> tuple[np.ndarray, np.ndarray]:
    """At every new random-commander hold order: the distance from the squad's
    active members' centroid to the point, and to a point drawn by run 1's rule
    (uniform over the 0.7 R disc) on the same state."""
    dist = replace(OrdersDistribution(), random_commander_p=1.0)
    env = rust_env.RustVecEnv(
        ASSETS,
        n_envs,
        [["fighter"], ["fighter"]],
        seed,
        n_threads=THREADS,
        roster_sampler=make_sampler(dist, seed),
    )
    rng = np.random.default_rng(seed)
    last: dict[tuple[int, int, int], tuple[float, float] | None] = {}
    new, uniform = [], []
    for _ in range(steps):
        due = np.asarray(env.raw.command_due()).copy()
        env.scripted_actions()
        env.step()
        for e in np.flatnonzero(due):
            state = env.raw.mission_state(int(e))
            ships = None
            for team, squads in enumerate(state["squads"]):
                for q in squads:
                    order = q["order"]
                    key = (int(e), team, int(q["index"]))
                    point = tuple(order["point"]) if order["kind"] == _POINT else None
                    if point is not None and last.get(key) != point:
                        ships = ships or env.raw.render_state(int(e))
                        pos = [
                            s["pos"]
                            for s in ships["ships"]
                            if s["slot"] in q["members"]
                            and s["alive"]
                            and s["present"]
                            and not s["docked"]
                        ]
                        if pos:
                            c = np.mean(np.asarray(pos), axis=0)
                            new.append(float(np.linalg.norm(np.asarray(point) - c)))
                            reach = 0.7 * ships["arena_radius"]
                            a = rng.uniform(0.0, 2.0 * np.pi)
                            u = (
                                np.array([np.cos(a), np.sin(a)])
                                * reach
                                * np.sqrt(rng.uniform())
                            )
                            uniform.append(float(np.linalg.norm(u - c)))
                    last[key] = point
    return np.asarray(new), np.asarray(uniform)


def test_random_hold_points_are_drawn_near_the_squad() -> None:
    """The median distance from the squad to its new hold point is well below what
    run 1's uniform draw gives on the same states (measured on the training mix:
    117 m against 261 m)."""
    new, uniform = _hold_draw_distances(n_envs=24, steps=2400, seed=11)
    assert new.size >= 60, new.size
    assert np.median(new) < 0.6 * np.median(uniform), (
        np.median(new),
        np.median(uniform),
    )
    assert np.median(new) < 160.0
