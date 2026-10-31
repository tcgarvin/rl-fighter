"""Run B3's trainer (lab/runs/2026-11-01-order-pilot-b3): the 403 -> 583 warm start,
the new inputs' larger step size, the transit-only script pull, and the env's
SIM_VERSION 6 order bindings. Tests that need the v6 sim skip on an older rlf_sim."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from spacefight.env import rust_env
from spacefight.env.rosters import (
    CARRIER_BATTLE,
    DEATHMATCH,
    RANDOM,
    SCRIPTED,
    Roster,
)
from spacefight.rl.spike_policy import (
    OBS_DIM,
    ORDER_OBS_DIM,
    PILOT_OBS_DIMS,
    V6_OBS_DIM,
    FleetCritic,
    SpikeActor,
    SpikeCritic,
    fit_obs,
    load_policy,
    save_policy,
    widen_actor,
    widen_critic,
)
from spacefight.rl.spike_ppo import (
    NewInputAdam,
    PPOBatch,
    PPOConfig,
    SpikeTrainer,
    first_layer_weights,
    transit_rows,
)
from tools.export_policy import ExportError, export

ASSETS = str(Path(__file__).resolve().parent.parent / "assets")
THREADS = 2
torch.set_num_threads(THREADS)
needs_v6 = pytest.mark.skipif(
    rust_env.SIM_VERSION < 6, reason="needs the SIM_VERSION 6 sim (orders redesigned)"
)


# ------------------------------------------------------------------ widths


def test_v6_pilot_width_is_v5_plus_the_two_tail_blocks() -> None:
    assert V6_OBS_DIM == 583 == ORDER_OBS_DIM + 7 * 10 + 5 * 22
    assert PILOT_OBS_DIMS[6] == V6_OBS_DIM and PILOT_OBS_DIMS[5] == ORDER_OBS_DIM


def test_fit_obs_gives_each_frozen_pilot_its_own_prefix() -> None:
    obs = torch.randn(5, V6_OBS_DIM)
    assert torch.equal(fit_obs(obs, ORDER_OBS_DIM), obs[:, :ORDER_OBS_DIM])
    assert torch.equal(fit_obs(obs, OBS_DIM), obs[:, :OBS_DIM])
    assert fit_obs(obs, V6_OBS_DIM) is obs


def test_widening_w1_to_583_keeps_actor_and_fleet_critic_exact() -> None:
    torch.manual_seed(3)
    actor = widen_actor(SpikeActor(), ORDER_OBS_DIM)
    with torch.no_grad():  # a trained 403-wide net: its order columns are not zero
        first_layer_weights(actor)[0].normal_()
    critic = FleetCritic.from_spike(SpikeCritic(obs_dim=ORDER_OBS_DIM))
    wide_actor = widen_actor(actor, V6_OBS_DIM)
    wide_critic = widen_critic(critic, V6_OBS_DIM)
    obs = torch.randn(3, 4, V6_OBS_DIM)
    team = torch.tensor([[0, 0, 1, 1]] * 3)
    rows = torch.tensor([[0, 0], [1, 2], [2, 3]])
    with torch.no_grad():
        torch.testing.assert_close(
            wide_actor(obs[:, 0]), actor(obs[:, 0, :ORDER_OBS_DIM]), rtol=0, atol=1e-5
        )
        torch.testing.assert_close(
            wide_critic.forward_set(obs, team, rows),
            critic.forward_set(obs[..., :ORDER_OBS_DIM], team, rows),
            rtol=0,
            atol=1e-5,
        )
    assert isinstance(wide_critic, FleetCritic)
    for weight in first_layer_weights(wide_critic) + first_layer_weights(wide_actor):
        assert weight.shape[1] == V6_OBS_DIM
        assert not weight[:, ORDER_OBS_DIM:].any()


# ------------------------------------------------------------------ new inputs


def _grads(steps: int, shape: tuple[int, int]) -> list[torch.Tensor]:
    gen = torch.Generator().manual_seed(1)
    return [torch.randn(shape, generator=gen) for _ in range(steps)]


def test_new_input_columns_step_like_their_own_param_group_at_mult_lr() -> None:
    """NewInputAdam equals plain Adam with the new columns in a second parameter
    group at 10x the LR, step for step."""
    start, mult, lr = 4, 10.0, 1e-3
    torch.manual_seed(0)
    weight = torch.nn.Parameter(torch.randn(3, 7))
    old = torch.nn.Parameter(weight.detach()[:, :start].clone())
    new = torch.nn.Parameter(weight.detach()[:, start:].clone())
    boosted = NewInputAdam([weight], lr=lr, boosted=[weight], start=start, mult=mult)
    param_groups: list[dict[str, object]] = [
        {"params": [old]},
        {"params": [new], "lr": lr * mult},
    ]
    groups = torch.optim.Adam(param_groups, lr=lr, eps=1e-5)  # type: ignore[arg-type]
    for grad in _grads(5, (3, 7)):
        weight.grad = grad.clone()
        old.grad = grad[:, :start].clone()
        new.grad = grad[:, start:].clone()
        boosted.step()
        groups.step()
        torch.testing.assert_close(weight.detach()[:, :start], old.detach())
        torch.testing.assert_close(weight.detach()[:, start:], new.detach())


def test_new_input_adam_without_a_boost_is_plain_adam() -> None:
    torch.manual_seed(0)
    a = torch.nn.Parameter(torch.randn(3, 7))
    b = torch.nn.Parameter(a.detach().clone())
    mine = NewInputAdam([a], lr=1e-2, boosted=[a], start=4, mult=1.0)
    plain = torch.optim.Adam([b], lr=1e-2, eps=1e-5)
    for grad in _grads(3, (3, 7)):
        a.grad, b.grad = grad.clone(), grad.clone()
        mine.step()
        plain.step()
    torch.testing.assert_close(a.detach(), b.detach(), rtol=0, atol=0)
    with pytest.raises(ValueError, match="cannot boost"):
        NewInputAdam([a], lr=1e-2, boosted=[a], start=7, mult=10.0)


def test_new_input_lr_mult_must_be_positive(v1_like: Path) -> None:
    with pytest.raises(ValueError, match="new_input_lr_mult"):
        _config(str(v1_like), new_input_lr_mult=0.0)


# ------------------------------------------------------------------ transit rows


class _FakeRaw:
    def __init__(self, team: np.ndarray, transit: np.ndarray) -> None:
        self.team = team
        self.order_transit = transit


def _fake_env(rosters: list[Roster], team: np.ndarray, transit: np.ndarray):  # type: ignore[no-untyped-def]
    env = object.__new__(rust_env.RustVecEnv)
    env._env = _FakeRaw(team, transit)  # type: ignore[assignment]
    env.rosters = rosters
    return env


def test_transit_rows_skip_padding_and_advisory_deathmatch_orders() -> None:
    team = np.array([[0, 1, -1], [0, 1, -1], [0, 1, 1]], dtype=np.int8)
    transit = np.ones((3, 3), dtype=bool)
    rosters = [
        Roster.of(["fighter"], ["fighter"], commanders=(SCRIPTED, RANDOM)),
        Roster.of(["fighter"], ["fighter"], commanders=(RANDOM, SCRIPTED)),
        Roster.of(
            ["carrier"], ["carrier", "fighter"], CARRIER_BATTLE, (SCRIPTED, SCRIPTED)
        ),
    ]
    assert rosters[0].mission == DEATHMATCH
    rows = _fake_env(rosters, team, transit).transit_rows()
    np.testing.assert_array_equal(
        rows,
        [[False, True, False], [True, False, False], [True, True, True]],
    )


def test_transit_pull_refuses_rows_that_show_an_attack_order() -> None:
    obs = np.zeros((2, rust_env.OBS_DIM), dtype=np.float32)
    env = SimpleNamespace(transit_rows=lambda: np.array([[True, False]]))
    np.testing.assert_array_equal(transit_rows(env, obs), [True, False])  # type: ignore[arg-type]
    obs[0, rust_env.ATTACK_COL] = 1.0
    with pytest.raises(RuntimeError, match="attack"):
        transit_rows(env, obs)  # type: ignore[arg-type]
    obs[0, rust_env.ATTACK_COL] = 0.0
    obs[1, rust_env.ATTACK_COL] = 1.0  # an attack row outside transit is fine
    transit_rows(env, obs)  # type: ignore[arg-type]


@pytest.mark.skipif(
    rust_env.SIM_VERSION >= 6, reason="v6 accepts hide_orders; the guard is for v5"
)
def test_hiding_orders_needs_the_v6_sim() -> None:
    with pytest.raises(ValueError, match="SIM_VERSION"):
        rust_env.RustVecEnv(
            ASSETS, 1, [["fighter"], ["fighter"]], 0, hide_orders=(True, False)
        )


def test_hide_orders_names_two_teams() -> None:
    with pytest.raises(ValueError, match="two teams"):
        rust_env._hide_pair((True,))


# ------------------------------------------------------------------ the trainer


@pytest.fixture
def v1_like(tmp_path: Path) -> Path:
    """A 385-wide checkpoint (v1's width)."""
    torch.manual_seed(5)
    path = tmp_path / "v1.pt"
    save_policy(path, SpikeActor(), SpikeCritic(), {"kind": "test", "sim_version": 3})
    return path


@pytest.fixture
def w1_like(tmp_path: Path) -> Path:
    """A 403-wide checkpoint with non-zero order columns (w1_400's width)."""
    torch.manual_seed(6)
    actor = widen_actor(SpikeActor(), ORDER_OBS_DIM)
    with torch.no_grad():
        first_layer_weights(actor)[0][:, OBS_DIM:].normal_(0.0, 0.1)
    critic = FleetCritic.from_spike(SpikeCritic(obs_dim=ORDER_OBS_DIM))
    path = tmp_path / "w1.pt"
    save_policy(path, actor, critic, {"kind": "test", "sim_version": 5})
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
        "beta_start": 0.05,
        "beta_end": 0.0,
        "beta_decay_start": 30,
        "beta_decay_end": 300,
        "beta_heads": "movement",
        "critic_warmup_updates": 0,
        "obs_dim": rust_env.OBS_DIM,
        "new_input_lr_mult": 10.0,
    }
    base.update(overrides)
    return PPOConfig.preset(init, **base)


def _narrow_init(v1_like: Path, w1_like: Path) -> Path:
    """The init one step narrower than the installed sim (v5: v1, v6: w1_400)."""
    return w1_like if rust_env.OBS_DIM == V6_OBS_DIM else v1_like


def test_trainer_widens_and_boosts_only_the_new_columns(
    tmp_path: Path, v1_like: Path, w1_like: Path
) -> None:
    init = _narrow_init(v1_like, w1_like)
    width = load_policy(init)[0].obs_dim
    trainer = SpikeTrainer(_config(str(init), n_updates=1), tmp_path / "run")
    assert trainer.new_input_start == width
    assert isinstance(trainer.actor_opt, NewInputAdam)
    assert len(trainer.actor_opt.boosted) == 1
    assert len(trainer.critic_opt.boosted) == 2  # fleet critic: base + encoder
    before = [w.detach().clone() for w in first_layer_weights(trainer.actor)]
    row = trainer.run_update()
    assert row["new_input_lr"] == pytest.approx(10.0 * float(row["actor_lr"]))  # type: ignore[arg-type]
    after = first_layer_weights(trainer.actor)[0].detach()
    moved_old = (after[:, :width] - before[0][:, :width]).abs().mean()
    moved_new = (after[:, width:] - before[0][:, width:]).abs().mean()
    assert float(moved_new) > 0.0
    # Adam's steps are ~lr per element: the boosted columns move several times more.
    assert float(moved_new) > 3.0 * float(moved_old)


def test_resume_keeps_the_boosted_columns(
    tmp_path: Path, v1_like: Path, w1_like: Path
) -> None:
    init = _narrow_init(v1_like, w1_like)
    width = load_policy(init)[0].obs_dim
    run = tmp_path / "run"
    cfg = _config(str(init), n_updates=1, checkpoint_every=1)
    SpikeTrainer(cfg, run).train(None)
    resumed = SpikeTrainer(
        _config(str(init), n_updates=2, checkpoint_every=1), run, True
    )
    assert resumed.new_input_start == width
    assert resumed.actor_opt.boosted and resumed.actor_opt.start == width


def test_trainer_pulls_exactly_the_transit_rows(
    tmp_path: Path, v1_like: Path, w1_like: Path
) -> None:
    """``beta_rows: transit`` pulls the rows the env flags (here a stand-in flag on
    an older sim; ``test_trainer_on_v6_pulls_transit_rows_only`` uses the sim's)."""
    init = _narrow_init(v1_like, w1_like)
    trainer = SpikeTrainer(
        _config(str(init), n_updates=1, beta_rows="transit"), tmp_path / "run"
    )
    env = trainer.env
    goto_col = rust_env.HAS_ORDER_COL + 3

    def stand_in() -> np.ndarray:
        return (env.obs[..., goto_col] > 0.5) & (env.team >= 0)

    if rust_env.SIM_VERSION < 6:
        env.transit_rows = stand_in  # type: ignore[method-assign]
    batches: list[PPOBatch] = []
    expected_rows: list[np.ndarray] = []
    original = trainer._prepare_batch

    def spy() -> tuple[PPOBatch, dict[str, object]]:
        batch, stats = original()
        batches.append(batch)
        store = trainer.storage
        train = np.flatnonzero(store.train_rows().reshape(-1))
        flags = store.transit[: trainer.config.n_steps].reshape(-1)
        expected_rows.append(flags[train].copy())
        return batch, stats

    trainer._prepare_batch = spy  # type: ignore[method-assign]
    row = trainer.run_update()
    batch, expected = batches[0], expected_rows[0]
    assert expected.any() and not expected.all()
    np.testing.assert_array_equal(batch.pull_rows.numpy(), expected)
    assert row["beta_rows_share"] == pytest.approx(float(expected.mean()))


@needs_v6
def test_trainer_on_v6_pulls_transit_rows_only(tmp_path: Path, w1_like: Path) -> None:
    cfg = _config(
        str(w1_like),
        n_updates=2,
        beta_rows="transit",
        kl_anchor=str(w1_like),
        kl_anchor_coeff=0.1,
        pool_seed=[str(w1_like)],
    )
    trainer = SpikeTrainer(cfg, tmp_path / "run")
    assert trainer.actor.obs_dim == V6_OBS_DIM and trainer.new_input_start == 403
    rows = [trainer.run_update() for _ in range(2)]
    store = trainer.storage
    obs = store.obs[..., rust_env.ATTACK_COL] > 0.5
    assert not (store.transit & obs).any()
    assert not (store.transit & ~store.scripted_order).any()
    share = float(rows[-1]["beta_rows_share"])  # type: ignore[arg-type]
    assert 0.0 < share < float(rows[-1]["has_order_share"])  # type: ignore[arg-type]


@needs_v6
def test_v6_env_exports_the_order_bindings() -> None:
    env = rust_env.RustVecEnv(
        ASSETS,
        2,
        [["carrier", "fighter", "fighter"], ["carrier", "fighter", "fighter"]],
        0,
        commanders=(RANDOM, RANDOM),
    )
    n, s = env.n_envs, env.n_ships
    assert env.order_transit.shape == (n, s)
    assert env.ward_threat.shape == (n, s, s)
    assert env.ward_hull_lost.shape == (n, s)
    tracks = env.order_tracks()
    for key in ("standing_kind", "effective_kind", "target", "radius", "arrived"):
        assert np.asarray(tracks[key]).shape == (n, s), key
    assert np.asarray(tracks["point"]).shape == (n, s, 2)


# ------------------------------------------------------------------ export


def test_export_takes_a_583_wide_v6_pilot_into_a_v6_build_only(tmp_path: Path) -> None:
    actor = widen_actor(SpikeActor(), V6_OBS_DIM)
    path = tmp_path / "b3.pt"
    save_policy(path, actor, SpikeCritic(obs_dim=V6_OBS_DIM), {"sim_version": 6})
    manifest = export(
        path,
        tmp_path / "out",
        wasm_sim_version=6,
        wasm_obs_dim=V6_OBS_DIM,
        wasm_pilot_compat=[3, 4, 5, 6],
        wasm_pilot_obs_dims=PILOT_OBS_DIMS,
    )
    assert manifest["obs_dim"] == V6_OBS_DIM and manifest["sim_version"] == 6
    assert manifest["layers"][0]["in"] == V6_OBS_DIM
    with pytest.raises(ExportError):  # a v6 pilot in a v5 build
        export(
            path,
            tmp_path / "o2",
            wasm_sim_version=5,
            wasm_obs_dim=ORDER_OBS_DIM,
            wasm_pilot_compat=[3, 4, 5],
            wasm_pilot_obs_dims=PILOT_OBS_DIMS,
        )
    # A v5 pilot (w1_400's width) still exports into a v6 build, on its prefix.
    v5 = tmp_path / "w1.pt"
    narrow = widen_actor(SpikeActor(), ORDER_OBS_DIM)
    save_policy(v5, narrow, SpikeCritic(obs_dim=ORDER_OBS_DIM), {"sim_version": 5})
    manifest = export(
        v5,
        tmp_path / "o3",
        wasm_sim_version=6,
        wasm_obs_dim=V6_OBS_DIM,
        wasm_pilot_compat=[3, 4, 5, 6],
        wasm_pilot_obs_dims=PILOT_OBS_DIMS,
    )
    assert manifest["obs_dim"] == ORDER_OBS_DIM
