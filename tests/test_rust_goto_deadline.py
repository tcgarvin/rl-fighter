"""SIM_VERSION 8 through the bindings: a go-to order with a deadline.

The pay kwargs (``goto_timed_bonus``, ``goto_miss_penalty``), ``OpeningOrder``'s
``deadline_tick`` and an external commander's ``"deadline"`` reaching the sim, the
``order_time`` obs block, ``order_tracks()``'s ``deadline`` and ``missed``, and a
583-input pilot of SIM_VERSION 7 flying the 587-float sim on its prefix
(``docs/SIM_SPEC.md`` §0.6).
"""

from __future__ import annotations

import math
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

from spacefight.env import rosters, rust_env  # noqa: E402
from spacefight.env.rosters import (  # noqa: E402
    DRILL_ATTACK,
    DRILL_GOTO,
    EXTERNAL,
    DrillTag,
    OpeningOrder,
    Roster,
    ShipStart,
)
from spacefight.env.rust_env import RustVecEnv  # noqa: E402
from spacefight.eval.controllers import Policy  # noqa: E402
from spacefight.rl.spike_policy import (  # noqa: E402
    PILOT_OBS_DIMS,
    V6_OBS_DIM,
    V8_OBS_DIM,
    HeadMasks,
    SpikeActor,
    SpikeCritic,
    act_numpy,
    load_policy,
    save_policy,
)

ASSETS = Path(__file__).resolve().parents[1] / "assets"
# The first slow tick: opening orders land here.
ORDER_TICK = int(rlf_sim.COMMAND_TICKS)
ORDER_TIME_OFF, ORDER_TIME_W = rust_env.OBS_LAYOUT["order_time"]
HAS_DEADLINE, TIME_LEFT, URGENCY, CLOSENESS = range(4)
GOTO = rust_env.TRACK_GOTO
FIGHTER_SPEED_CAP = 60.0


def goto_drill(
    deadline_tick: int,
    point: tuple[float, float] = (-100.0, 0.0),
    radius: float = 30.0,
) -> Roster:
    """A go-to drill: one fighter at rest at (-300, 0) facing +x with a go-to, and an
    enemy fighter far away with no order."""
    return Roster(
        (("fighter",), ("fighter",)),
        commanders=(EXTERNAL, EXTERNAL),
        start_layout=(
            ShipStart(-300.0, 0.0, 0.0, 0.0, 0.0),
            ShipStart(300.0, 300.0, 0.0, 0.0, math.pi),
        ),
        opening_orders=(
            OpeningOrder(
                0,
                0,
                (0,),
                DRILL_GOTO,
                point=point,
                radius=radius,
                deadline_tick=deadline_tick,
            ),
        ),
        time_limit_s=40.0,
        drill=DrillTag(DRILL_GOTO, (0,)),
    )


def play(
    roster: Roster,
    seed: int = 3,
    goto_timed_bonus: float = rust_env.DEFAULT_GOTO_TIMED_BONUS,
    goto_miss_penalty: float = rust_env.DEFAULT_GOTO_MISS_PENALTY,
) -> RustVecEnv:
    """An env of one match of ``roster`` at tick 0."""
    env = RustVecEnv(
        ASSETS,
        1,
        roster.fleets(),
        seed,
        n_threads=1,
        commanders=(EXTERNAL, EXTERNAL),
        goto_timed_bonus=goto_timed_bonus,
        goto_miss_penalty=goto_miss_penalty,
    )
    env.set_next_roster(0, roster)
    env.reset()
    return env


def step_scripted(env: RustVecEnv) -> float:
    """One step flown by the scripts; ship 0's order reward."""
    env.scripted_actions()
    env.step()
    return float(env.order_rewards[0, 0])


def step_idle(env: RustVecEnv) -> float:
    """One step with every thruster held and no fire; ship 0's order reward."""
    actions = np.zeros_like(env.actions)
    actions[..., :8] = 1
    env.step(actions)
    return float(env.order_rewards[0, 0])


def tick_of(env: RustVecEnv) -> int:
    return int(env.raw.tick[0])


def order_time(env: RustVecEnv, slot: int = 0) -> np.ndarray:
    return env.obs[0, slot, ORDER_TIME_OFF : ORDER_TIME_OFF + ORDER_TIME_W].copy()


# -- constants and kwargs ---------------------------------------------------------------


def test_the_obs_is_587_wide_with_the_order_time_block_last() -> None:
    assert rust_env.SIM_VERSION == 8
    assert (rust_env.OBS_DIM, rust_env.OBS_DIM_V7) == (587, 583)
    assert (ORDER_TIME_OFF, ORDER_TIME_W) == (583, 4)
    assert list(rust_env.OBS_LAYOUT)[-1] == "order_time"
    assert rust_env.OBS_SLOTS["order_time"] == 1
    assert rust_env.PILOT_OBS_DIMS == {3: 385, 4: 385, 5: 403, 6: 583, 7: 583, 8: 587}
    assert PILOT_OBS_DIMS[8] == V8_OBS_DIM == rust_env.OBS_DIM
    assert PILOT_OBS_DIMS[6] == PILOT_OBS_DIMS[7] == V6_OBS_DIM == rust_env.OBS_DIM_V7
    assert rust_env.NO_DEADLINE == rosters.NO_DEADLINE == 0
    env = play(goto_drill(rosters.NO_DEADLINE))
    assert env.obs.shape == (1, 2, 587)


def test_goto_pay_defaults_to_the_sim_s_constants() -> None:
    assert rust_env.DEFAULT_GOTO_TIMED_BONUS == rlf_sim.ORDER_TIMED_ARRIVAL_BONUS == 1.0
    assert rust_env.DEFAULT_GOTO_MISS_PENALTY == rlf_sim.ORDER_MISS_PENALTY == 1.0
    env = RustVecEnv(ASSETS, 2, [["fighter"], ["fighter"]], 0, n_threads=1)
    assert (env.goto_timed_bonus, env.goto_miss_penalty) == (1.0, 1.0)
    raw = rlf_sim.VecEnv(str(ASSETS), 2, [["fighter"], ["fighter"]], 0)
    assert (raw.goto_timed_bonus, raw.goto_miss_penalty) == (1.0, 1.0)


def test_goto_pay_kwargs_hold_through_a_queued_roster() -> None:
    env = play(goto_drill(500), goto_timed_bonus=0.75, goto_miss_penalty=0.25)
    assert (env.goto_timed_bonus, env.goto_miss_penalty) == (0.75, 0.25)
    raw = rlf_sim.VecEnv(
        str(ASSETS),
        1,
        [["fighter"], ["fighter"]],
        0,
        goto_timed_bonus=2.5,
        goto_miss_penalty=0.0,
    )
    assert (raw.goto_timed_bonus, raw.goto_miss_penalty) == (2.5, 0.0)


@pytest.mark.parametrize("bad", [-0.1, float("nan"), float("inf"), float("-inf")])
def test_goto_pay_must_be_finite_and_not_negative(bad: float) -> None:
    fleets = [["fighter"], ["fighter"]]
    with pytest.raises(ValueError, match="goto_timed_bonus"):
        RustVecEnv(ASSETS, 1, fleets, 0, goto_timed_bonus=bad)
    with pytest.raises(ValueError, match="goto_miss_penalty"):
        RustVecEnv(ASSETS, 1, fleets, 0, goto_miss_penalty=bad)
    with pytest.raises(ValueError, match="goto_timed_bonus"):
        rlf_sim.VecEnv(str(ASSETS), 1, fleets, 0, goto_timed_bonus=bad)
    with pytest.raises(ValueError, match="goto_miss_penalty"):
        rlf_sim.VecEnv(str(ASSETS), 1, fleets, 0, goto_miss_penalty=bad)


# -- OpeningOrder ------------------------------------------------------------------------


def test_an_opening_order_has_no_deadline_unless_given_one() -> None:
    plain = OpeningOrder(0, 0, (0,), DRILL_GOTO, point=(10.0, 20.0), radius=30.0)
    assert plain.deadline_tick == rosters.NO_DEADLINE
    assert plain.command()["order"] == {
        "kind": "goto",
        "point": [10.0, 20.0],
        "radius": 30.0,
        "deadline": 0,
    }
    timed = OpeningOrder(
        0, 0, (0,), DRILL_GOTO, point=(10.0, 20.0), radius=30.0, deadline_tick=450
    )
    assert timed.command()["order"] == {
        "kind": "goto",
        "point": [10.0, 20.0],
        "radius": 30.0,
        "deadline": 450,
    }
    attack = OpeningOrder(0, 0, (0,), DRILL_ATTACK, target=1)
    assert attack.command()["order"] == {"kind": "attack", "target": 1}


@pytest.mark.parametrize("bad", [-1, 2**32, 1.5, "90", True, None])
def test_an_opening_order_refuses_a_deadline_that_is_not_a_tick(bad: object) -> None:
    with pytest.raises(ValueError, match="deadline_tick"):
        OpeningOrder(0, 0, (0,), DRILL_GOTO, radius=30.0, deadline_tick=bad)  # type: ignore[arg-type]


def test_only_a_goto_opening_order_takes_a_deadline() -> None:
    with pytest.raises(ValueError, match="only a go-to takes a deadline"):
        OpeningOrder(0, 0, (0,), DRILL_ATTACK, target=1, deadline_tick=300)


# -- the deadline in the sim --------------------------------------------------------------


def test_an_opening_order_s_deadline_reaches_the_sim() -> None:
    env = play(goto_drill(400, point=(-100.0, 0.0), radius=30.0))
    for _ in range(ORDER_TICK - 1):
        step_idle(env)
    assert not env.order_tracks()["deadline"].any(), "not before the first slow tick"
    assert not order_time(env).any()
    step_idle(env)
    assert tick_of(env) == ORDER_TICK
    tracks = env.order_tracks()
    assert tracks["standing_kind"][0, 0] == GOTO
    assert tracks["effective_kind"][0, 0] == GOTO
    assert tracks["deadline"][0, 0] == 400
    assert tracks["instance_start"][0, 0] == ORDER_TICK
    assert not tracks["missed"].any() and not tracks["arrived"].any()
    assert tracks["deadline"][0, 1] == 0, "the enemy has no order"
    order = env.raw.mission_state(0)["squads"][0][0]["order"]
    assert (order["kind"], order["deadline"]) == ("goto", 400)
    # The pilot sees it: 170 m to the circle's edge, 340 ticks left.
    block = order_time(env)
    left_ticks = 400 - ORDER_TICK
    assert block[HAS_DEADLINE] == 1.0
    assert block[TIME_LEFT] == pytest.approx(left_ticks / 900.0)
    assert block[URGENCY] == pytest.approx(
        170.0 / (left_ticks / 30.0 * FIGHTER_SPEED_CAP), rel=1e-4
    )
    assert block[CLOSENESS] == 0.0
    assert not order_time(env, 1).any(), "nor does the enemy see one"


def test_a_missed_deadline_is_charged_once_and_the_order_is_over() -> None:
    deadline = ORDER_TICK + 15
    env = play(goto_drill(deadline, point=(100.0, 0.0)), goto_miss_penalty=0.5)
    paid: dict[int, float] = {}
    while tick_of(env) < deadline + 30:
        reward = step_idle(env)
        paid[tick_of(env)] = reward
        tracks = env.order_tracks()
        late = tick_of(env) > deadline
        assert bool(tracks["missed"][0, 0]) == late
        if ORDER_TICK <= tick_of(env) <= deadline:
            assert tracks["effective_kind"][0, 0] == GOTO
            assert order_time(env)[HAS_DEADLINE] == 1.0
    charged = [t for t, r in paid.items() if r < -0.25]
    assert charged == [deadline + 1]
    assert paid[deadline + 1] == pytest.approx(-0.5, abs=0.02)
    assert all(r == 0.0 for t, r in paid.items() if t > deadline + 1)
    tracks = env.order_tracks()
    assert tracks["standing_kind"][0, 0] == GOTO, "the squad's order stands"
    assert tracks["effective_kind"][0, 0] == rust_env.TRACK_NONE
    assert tracks["deadline"][0, 0] == deadline and not tracks["arrived"][0, 0]
    # The obs is that of a ship without an order.
    order_off, order_w = rust_env.OBS_LAYOUT["order"]
    assert not env.obs[0, 0, order_off : order_off + order_w].any()
    assert not order_time(env).any()
    assert not env.order_transit[0, 0]


def test_arriving_by_the_deadline_pays_the_timed_bonus_once() -> None:
    env = play(goto_drill(900, point=(-150.0, 0.0), radius=40.0), goto_timed_bonus=0.75)
    bonuses = []
    closeness = []
    while tick_of(env) < 600 and not env.order_tracks()["arrived"][0, 0]:
        reward = step_scripted(env)
        closeness.append(float(order_time(env)[CLOSENESS]))
        if reward > 0.5:
            bonuses.append(reward)
    tracks = env.order_tracks()
    assert tracks["arrived"][0, 0] and not tracks["missed"][0, 0]
    assert len(bonuses) == 1 and bonuses[0] == pytest.approx(0.75, abs=0.05)
    assert tracks["effective_kind"][0, 0] == rust_env.TRACK_NONE
    # Closeness rose from 0 to nearly 1 on the way in, then the block went dark.
    assert closeness[ORDER_TICK] == 0.0 and max(closeness) > 0.9
    assert not order_time(env).any()
    for _ in range(60):
        assert step_scripted(env) == 0.0


def test_a_deadline_that_is_not_missed_changes_nothing_in_the_first_583_floats() -> (
    None
):
    plain = play(goto_drill(rosters.NO_DEADLINE, point=(100.0, 100.0)))
    timed = play(goto_drill(1100, point=(100.0, 100.0)))
    differed = False
    for _ in range(240):
        step_scripted(plain)
        step_scripted(timed)
        np.testing.assert_array_equal(
            plain.obs[..., : rust_env.OBS_DIM_V7], timed.obs[..., : rust_env.OBS_DIM_V7]
        )
        differed |= bool(
            (plain.obs[..., ORDER_TIME_OFF:] != timed.obs[..., ORDER_TIME_OFF:]).any()
        )
    assert differed, "the order_time block shows the deadline"
    assert tick_of(plain) == tick_of(timed) == 240


# -- an external commander, mid-match -----------------------------------------------------


def external_duel() -> RustVecEnv:
    """A plain fighter duel whose commanders are both external."""
    return RustVecEnv(
        ASSETS,
        1,
        [["fighter"], ["fighter"]],
        5,
        n_threads=1,
        commanders=(EXTERNAL, EXTERNAL),
    )


def goto_command(deadline: object) -> dict[str, object]:
    return {
        "kind": "squad",
        "squad": 0,
        "members": [0],
        "order": {
            "kind": "goto",
            "point": [50.0, -120.0],
            "radius": 35.0,
            "deadline": deadline,
        },
    }


def test_an_external_commander_gives_a_goto_a_deadline_mid_match() -> None:
    env = external_duel()
    for _ in range(100):
        step_scripted(env)
    while not env.raw.command_due()[0]:
        step_scripted(env)
    deadline = tick_of(env) + 400
    env.raw.submit_command(0, 0, goto_command(deadline))
    step_scripted(env)
    tracks = env.order_tracks()
    assert tracks["standing_kind"][0, 0] == GOTO
    assert tracks["deadline"][0, 0] == deadline
    assert tracks["instance_start"][0, 0] == tick_of(env)
    assert order_time(env)[HAS_DEADLINE] == 1.0
    # The same go-to with another deadline is a new instance.
    while not env.raw.command_due()[0]:
        step_scripted(env)
    env.raw.submit_command(0, 0, goto_command(deadline + 300))
    step_scripted(env)
    tracks = env.order_tracks()
    assert tracks["deadline"][0, 0] == deadline + 300
    assert tracks["instance_start"][0, 0] == tick_of(env)


def test_a_goto_command_without_a_deadline_has_none() -> None:
    env = external_duel()
    command = goto_command(0)
    del command["order"]["deadline"]  # type: ignore[attr-defined]
    env.raw.submit_command(0, 0, command)
    for _ in range(ORDER_TICK):
        step_scripted(env)
    tracks = env.order_tracks()
    assert tracks["standing_kind"][0, 0] == GOTO
    assert tracks["deadline"][0, 0] == rosters.NO_DEADLINE
    block = order_time(env)
    assert (block[HAS_DEADLINE], block[TIME_LEFT], block[URGENCY]) == (0.0, 0.0, 0.0)


@pytest.mark.parametrize("bad", [-1, 1.5, "soon", None, 2**32])
def test_a_command_s_deadline_must_be_a_tick(bad: object) -> None:
    env = external_duel()
    with pytest.raises(ValueError, match="command"):
        env.raw.submit_command(0, 0, goto_command(bad))


# -- older pilots -------------------------------------------------------------------------


def test_a_583_input_pilot_loads_and_flies_the_587_float_sim(tmp_path: Path) -> None:
    path = tmp_path / "v7_pilot.pt"
    width = PILOT_OBS_DIMS[7]
    save_policy(
        path,
        SpikeActor(obs_dim=width),
        SpikeCritic(obs_dim=width),
        {"kind": "test", "sim_version": 7},
    )
    actor, critic, meta = load_policy(path)
    assert actor.obs_dim == critic.obs_dim == 583 and meta["sim_version"] == 7
    assert rust_env.PILOT_OBS_DIMS[int(meta["sim_version"])] == actor.obs_dim  # type: ignore[call-overload]

    env = play(goto_drill(500, point=(0.0, 0.0)))
    pilot = Policy(path, sample=False)
    rows = env.team >= 0
    for _ in range(ORDER_TICK + 30):
        acts = pilot.act(env, rows)
        assert acts.shape == (2, rust_env.ACTION_WIDTH) and acts.dtype == np.int8
        actions = np.zeros_like(env.actions)
        actions[rows] = acts
        env.step(actions)
    assert env.obs.shape[-1] == 587 and order_time(env)[HAS_DEADLINE] == 1.0
    # It read exactly the 583-float prefix: the deadline block does not reach it.
    masks = HeadMasks.from_numpy(
        env.thruster_mask[rows], env.turret_mask[rows], env.fixed_turret[rows]
    )
    seen = np.ascontiguousarray(env.obs[rows])
    blanked = seen.copy()
    blanked[:, ORDER_TIME_OFF:] = 0.0
    np.testing.assert_array_equal(
        act_numpy(actor, seen, masks, deterministic=True),
        act_numpy(actor, blanked[:, :width], masks, deterministic=True),
    )
    np.testing.assert_array_equal(
        pilot.act(env, rows), act_numpy(actor, seen, masks, deterministic=True)
    )
