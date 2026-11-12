//! v8 (SIM_SPEC §0.6): a go-to order may carry a deadline tick. Arrival and expiry
//! (§5.9), the pay (§8), the `order_time` obs block (§7.2), and what a missed go-to
//! means to the script, a drill's end and the commands' JSON.

mod common;

use common::{FIGHTER, asset_catalogue, config, test_catalogue};
use sim::command::{Command, CommanderMode, NO_DEADLINE, Order, Squad};
use sim::data::{Catalogue, HullId};
use sim::math::{PI, Vec2};
use sim::obs::*;
use sim::order::{effective_order, standing_order};
use sim::reward::{
    ORDER_ARRIVAL_BONUS, ORDER_MISS_PENALTY, ORDER_SHAPING_GAMMA, ORDER_TIMED_ARRIVAL_BONUS,
};
use sim::scripted;
use sim::setup::{MatchConfig, SetupError};
use sim::spec::CommandSpec;
use sim::state::{MAX_PROJECTILES, MAX_SHIPS, Match, Projectile};

const EPS: f32 = 1e-5;
const R: f32 = 450.0;
const ALL: [bool; MAX_SHIPS] = [true; MAX_SHIPS];
/// The tick the refresh-driven tests start at.
const T0: u32 = 100;

fn close(a: f32, b: f32) -> bool {
    (a - b).abs() < EPS
}

/// A fighter duel under external commanders at tick `T0`: ship 0 at rest `dist` metres
/// from the origin along +x, the enemy far off, and no orders yet.
fn duel(cat: &Catalogue, hull: HullId, dist: f32) -> Match {
    let mut cfg = config(3, &[hull], &[hull]);
    cfg.commanders = [CommanderMode::External; 2];
    let mut m = Match::new(cat, &cfg).unwrap();
    for (s, &(x, y, h)) in m
        .ships
        .iter_mut()
        .zip(&[(dist, 0.0, 0.0), (0.0, 400.0, PI)])
    {
        s.pos = Vec2::new(x, y);
        s.heading = h;
        s.vel = Vec2::ZERO;
        s.omega = 0.0;
        s.present = true;
        s.alive = true;
        s.control_lock_until = 0;
    }
    m.projectiles = [Projectile::DEAD; MAX_PROJECTILES];
    m.tick = T0;
    m
}

/// A go-to at the origin.
fn goto(radius: f32, deadline: u32) -> Order {
    Order::GoTo {
        point: Vec2::ZERO,
        radius,
        deadline,
    }
}

fn order_ship0(m: &mut Match, order: Order) {
    m.command.squads[0][0] = Squad { members: 1, order };
}

/// Ship 0 of [`duel`] with a go-to of `radius` at the origin due by `deadline`, its
/// instance started at `T0`.
fn goto_duel(cat: &Catalogue, dist: f32, radius: f32, deadline: u32) -> Match {
    let mut m = duel(cat, FIGHTER, dist);
    order_ship0(&mut m, goto(radius, deadline));
    assert_eq!(refresh(&mut m, cat), 0.0, "the start step pays nothing");
    m
}

/// Refresh the order tracks without moving anything; ship 0's order reward.
fn refresh(m: &mut Match, cat: &Catalogue) -> f32 {
    m.compute_order_rewards(cat, &ALL);
    m.order_rewards[0]
}

/// One tick later, refreshed: ship 0's order reward.
fn tick(m: &mut Match, cat: &Catalogue) -> f32 {
    m.tick += 1;
    refresh(m, cat)
}

fn obs(m: &Match, cat: &Catalogue, ship: u8) -> Vec<f32> {
    let mut out = vec![f32::NAN; OBS_DIM];
    m.write_obs(cat, ship, &mut out);
    out
}

fn order_time(m: &Match, cat: &Catalogue, ship: u8) -> [f32; ORDER_TIME_W] {
    obs(m, cat, ship)[ORDER_TIME_OFF..ORDER_TIME_OFF + ORDER_TIME_WIDTH]
        .try_into()
        .unwrap()
}

#[test]
fn a_deadline_goto_reached_in_time_pays_the_timed_bonus_once() {
    let cat = test_catalogue();
    let mut m = goto_duel(&cat, 100.0, 50.0, T0 + 300);
    assert_eq!(m.order_track(0).deadline, T0 + 300);
    // Shaping on the way is the no-deadline shaping.
    let phi = -50.0 / R;
    m.ships[0].pos.x = 80.0;
    let phi2 = -30.0 / R;
    assert!(close(tick(&mut m, &cat), ORDER_SHAPING_GAMMA * phi2 - phi));
    // Inside the circle well before the deadline: the timed bonus, not 0.2.
    m.ships[0].pos.x = 30.0;
    let arrival = tick(&mut m, &cat);
    assert!(
        close(arrival, -phi2 + ORDER_TIMED_ARRIVAL_BONUS),
        "{arrival}"
    );
    let track = *m.order_track(0);
    assert!(track.arrived && !track.missed);
    assert_eq!(effective_order(&m, 0), Order::None);
    assert!(matches!(standing_order(&m, 0), Order::GoTo { .. }));
    // Nothing more: parked, past the deadline, out and back.
    let later: f32 = (0..400).map(|_| tick(&mut m, &cat)).sum();
    assert_eq!(later, 0.0);
    assert!(m.tick > T0 + 300 && !m.order_track(0).missed);
    m.ships[0].pos.x = 300.0;
    assert_eq!(tick(&mut m, &cat), 0.0);
}

#[test]
fn arriving_on_the_deadline_tick_itself_is_in_time() {
    let cat = test_catalogue();
    let mut m = goto_duel(&cat, 100.0, 50.0, T0 + 10);
    m.tick = T0 + 9;
    refresh(&mut m, &cat);
    m.ships[0].pos.x = 50.0;
    let paid = tick(&mut m, &cat);
    assert_eq!(m.tick, T0 + 10);
    assert!(close(paid, 50.0 / R + ORDER_TIMED_ARRIVAL_BONUS), "{paid}");
    assert!(m.order_track(0).arrived && !m.order_track(0).missed);
    assert_eq!(tick(&mut m, &cat), 0.0, "no miss after an arrival");
}

#[test]
fn a_missed_deadline_pays_the_penalty_once_and_the_order_reads_as_none() {
    let cat = test_catalogue();
    let mut m = goto_duel(&cat, 200.0, 50.0, T0 + 10);
    let phi = -150.0 / R;
    let drift = (ORDER_SHAPING_GAMMA - 1.0) * phi;
    // Up to and on the deadline tick: still the order, still only shaping.
    for _ in 0..10 {
        assert!(close(tick(&mut m, &cat), drift));
        assert!(matches!(effective_order(&m, 0), Order::GoTo { .. }));
    }
    assert_eq!(m.tick, T0 + 10);
    assert_eq!(order_time(&m, &cat, 0)[order_time_f::HAS_DEADLINE], 1.0);
    // The first step past it: missed, charged once, with that step's shaping.
    let paid = tick(&mut m, &cat);
    assert!(close(paid, drift - ORDER_MISS_PENALTY), "{paid}");
    let track = *m.order_track(0);
    assert!(track.missed && !track.arrived);
    assert_eq!(effective_order(&m, 0), Order::None);
    assert!(
        matches!(standing_order(&m, 0), Order::GoTo { .. }),
        "the squad's order stands until the commander changes it"
    );
    assert!(!m.order_transit(&cat, 0));
    let o = obs(&m, &cat, 0);
    for (name, off, width) in [
        ("order", ORDER_OFF, ORDER_WIDTH),
        ("order_ships", ORDER_SHIPS_OFF, ORDER_SHIPS_WIDTH),
        ("order_time", ORDER_TIME_OFF, ORDER_TIME_WIDTH),
    ] {
        assert!(o[off..off + width].iter().all(|&x| x == 0.0), "{name}");
    }
    let mut none = m.clone();
    order_ship0(&mut none, Order::None);
    assert_eq!(o, obs(&none, &cat, 0), "the obs of a ship without an order");
    // Late arrival earns nothing and nothing is charged again.
    assert_eq!(tick(&mut m, &cat), 0.0);
    m.ships[0].pos.x = 0.0;
    assert_eq!(tick(&mut m, &cat), 0.0);
    assert!(!m.order_track(0).arrived);
}

#[test]
fn a_goto_without_a_deadline_pays_exactly_what_v7_paid() {
    let cat = test_catalogue();
    let mut m = goto_duel(&cat, 100.0, 50.0, NO_DEADLINE);
    let track = *m.order_track(0);
    assert!(!track.has_deadline() && !track.missed);
    let phi = -50.0 / R;
    // Bit for bit v7's terms: γΦ′ − Φ on the way, then −Φ + 0.2 on arrival.
    m.ships[0].pos.x = 80.0;
    let phi2 = -30.0 / R;
    assert_eq!(tick(&mut m, &cat), ORDER_SHAPING_GAMMA * phi2 - phi);
    m.ships[0].pos.x = 30.0;
    let phi3 = 0.0f32;
    assert_eq!(
        tick(&mut m, &cat),
        ORDER_SHAPING_GAMMA * phi3 - phi2 + ORDER_ARRIVAL_BONUS
    );
    // It never expires.
    let mut far = goto_duel(&cat, 200.0, 50.0, NO_DEADLINE);
    far.tick = 1_000_000;
    refresh(&mut far, &cat);
    assert!(!far.order_track(0).missed);
    assert!(matches!(effective_order(&far, 0), Order::GoTo { .. }));
}

#[test]
fn an_instance_that_starts_inside_the_radius_is_complete_and_pays_no_bonus() {
    let cat = test_catalogue();
    for deadline in [NO_DEADLINE, T0 + 300, T0 - 50] {
        let mut m = duel(&cat, FIGHTER, 20.0);
        order_ship0(&mut m, goto(50.0, deadline));
        assert_eq!(refresh(&mut m, &cat), 0.0, "deadline {deadline}");
        let track = *m.order_track(0);
        assert!(track.arrived && !track.missed, "deadline {deadline}");
        assert_eq!(effective_order(&m, 0), Order::None);
        let later: f32 = (0..400).map(|_| tick(&mut m, &cat)).sum();
        assert_eq!(later, 0.0, "deadline {deadline}");
    }
}

/// The farm the "starts inside" rule closes: a go-to to the same point with a new
/// deadline is a new instance, and a ship already there earns nothing from it.
#[test]
fn a_reissued_goto_with_a_new_deadline_is_a_new_instance() {
    let cat = test_catalogue();
    let mut m = goto_duel(&cat, 200.0, 50.0, T0 + 300);
    let first = *m.order_track(0);
    // Same point, same deadline, another radius: the same instance.
    m.tick += 5;
    order_ship0(&mut m, goto(60.0, T0 + 300));
    refresh(&mut m, &cat);
    assert_eq!(m.order_track(0).start_tick, first.start_tick);
    // A new deadline: a new instance from this tick, and no pay for the switch.
    order_ship0(&mut m, goto(50.0, T0 + 600));
    assert_eq!(tick(&mut m, &cat), 0.0);
    let second = *m.order_track(0);
    assert_eq!(second.start_tick, m.tick);
    assert_eq!(second.deadline, T0 + 600);
    // Arrive, then be re-issued the point with yet another deadline while inside.
    m.ships[0].pos.x = 10.0;
    assert!(tick(&mut m, &cat) > ORDER_TIMED_ARRIVAL_BONUS);
    for k in 1..=5 {
        order_ship0(&mut m, goto(50.0, T0 + 600 + 100 * k));
        assert_eq!(tick(&mut m, &cat), 0.0, "re-issue {k} pays nothing");
        assert_eq!(m.order_track(0).start_tick, m.tick);
        assert!(m.order_track(0).arrived);
        assert_eq!(effective_order(&m, 0), Order::None);
    }
    // Dropping the deadline is a new instance too, as is a missed one re-issued.
    order_ship0(&mut m, goto(50.0, NO_DEADLINE));
    assert_eq!(tick(&mut m, &cat), 0.0);
    assert_eq!(m.order_track(0).deadline, NO_DEADLINE);
    let mut late = goto_duel(&cat, 200.0, 50.0, T0 + 1);
    late.tick = T0 + 2;
    refresh(&mut late, &cat);
    assert!(late.order_track(0).missed);
    order_ship0(&mut late, goto(50.0, T0 + 500));
    assert_eq!(tick(&mut late, &cat), 0.0);
    assert!(!late.order_track(0).missed);
    assert!(matches!(effective_order(&late, 0), Order::GoTo { .. }));
}

#[test]
fn a_deadline_already_past_expires_on_the_step_the_order_lands() {
    let cat = test_catalogue();
    let mut m = duel(&cat, FIGHTER, 200.0);
    order_ship0(&mut m, goto(50.0, T0 - 1));
    let paid = refresh(&mut m, &cat);
    assert_eq!(paid, -ORDER_MISS_PENALTY);
    assert!(m.order_track(0).missed);
    assert_eq!(effective_order(&m, 0), Order::None);
    assert_eq!(tick(&mut m, &cat), 0.0);
}

#[test]
fn a_dead_or_absent_ship_is_marked_missed_but_not_charged() {
    let cat = test_catalogue();
    let mut m = goto_duel(&cat, 200.0, 50.0, T0 + 10);
    let mut earning = ALL;
    earning[0] = false;
    m.tick = T0 + 11;
    m.compute_order_rewards(&cat, &earning);
    assert_eq!(m.order_rewards[0], 0.0);
    assert!(m.order_track(0).missed);
    // Back on the field: no charge later either, and the order is over.
    assert_eq!(tick(&mut m, &cat), 0.0);
    assert_eq!(effective_order(&m, 0), Order::None);
}

#[test]
fn order_time_block_at_known_states() {
    let cat = test_catalogue();
    assert_eq!(cat.hull(FIGHTER).speed_cap, 60.0);
    // 200 m outside the circle, 300 ticks (10 s) left: 600 m of reach at 60 m/s.
    let m = goto_duel(&cat, 250.0, 50.0, T0 + 300);
    let b = order_time(&m, &cat, 0);
    assert_eq!(b[order_time_f::HAS_DEADLINE], 1.0);
    assert!(close(b[order_time_f::TIME_LEFT], 300.0 / 900.0));
    assert!(close(b[order_time_f::URGENCY], 200.0 / 600.0));
    assert_eq!(b[order_time_f::CLOSENESS], 0.0);
    // 50 m outside: closeness one half, urgency 50 / 600.
    let m = goto_duel(&cat, 100.0, 50.0, T0 + 300);
    let b = order_time(&m, &cat, 0);
    assert!(close(b[order_time_f::CLOSENESS], 0.5));
    assert!(close(b[order_time_f::URGENCY], 50.0 / 600.0));
    // Exactly makeable flat out: 200 m in 100 ticks at 60 m/s reads 1.
    let m = goto_duel(&cat, 250.0, 50.0, T0 + 100);
    assert!(close(order_time(&m, &cat, 0)[order_time_f::URGENCY], 1.0));
    // Out of reach, and a long deadline: both clamp at 2.
    let m = goto_duel(&cat, 250.0, 50.0, T0 + 30);
    assert_eq!(order_time(&m, &cat, 0)[order_time_f::URGENCY], 2.0);
    let m = goto_duel(&cat, 250.0, 50.0, T0 + 3000);
    assert_eq!(order_time(&m, &cat, 0)[order_time_f::TIME_LEFT], 2.0);
    // On the deadline tick, still outside: no time left, urgency at its ceiling.
    let mut m = goto_duel(&cat, 250.0, 50.0, T0 + 30);
    m.tick = T0 + 30;
    refresh(&mut m, &cat);
    let b = order_time(&m, &cat, 0);
    assert_eq!(
        (
            b[order_time_f::HAS_DEADLINE],
            b[order_time_f::TIME_LEFT],
            b[order_time_f::URGENCY]
        ),
        (1.0, 0.0, 2.0)
    );
    // No deadline: only closeness.
    let m = goto_duel(&cat, 75.0, 50.0, NO_DEADLINE);
    assert_eq!(order_time(&m, &cat, 0), [0.0, 0.0, 0.0, 0.75]);
    let m = goto_duel(&cat, 400.0, 50.0, NO_DEADLINE);
    assert_eq!(order_time(&m, &cat, 0), [0.0; 4]);
}

#[test]
fn order_time_urgency_uses_each_hull_s_catalogue_speed_cap() {
    let cat = asset_catalogue();
    for (name, cap) in [("fighter", 60.0), ("strafer", 50.0), ("gunship", 24.0)] {
        let hull = cat.hull_id(name).unwrap();
        assert_eq!(cat.hull(hull).speed_cap, cap, "{name}");
        let mut m = duel(&cat, hull, 170.0);
        order_ship0(&mut m, goto(50.0, T0 + 300));
        refresh(&mut m, &cat);
        let urgency = order_time(&m, &cat, 0)[order_time_f::URGENCY];
        assert!(close(urgency, 120.0 / (10.0 * cap)), "{name}: {urgency}");
    }
}

#[test]
fn order_time_is_zero_without_a_goto_the_ship_can_see() {
    let cat = test_catalogue();
    // No order, an attack, a defend.
    let mut m = duel(&cat, FIGHTER, 60.0);
    assert_eq!(order_time(&m, &cat, 0), [0.0; 4]);
    order_ship0(&mut m, Order::Attack { target: 1 });
    refresh(&mut m, &cat);
    assert_eq!(order_time(&m, &cat, 0), [0.0; 4]);
    // A hidden order: the whole obs is that of a ship without one.
    let shown = goto_duel(&cat, 100.0, 50.0, T0 + 300);
    let mut hidden = shown.clone();
    hidden.cfg.hide_orders = [true, false];
    let mut none = shown.clone();
    order_ship0(&mut none, Order::None);
    assert_ne!(order_time(&shown, &cat, 0), [0.0; 4]);
    assert_eq!(order_time(&hidden, &cat, 0), [0.0; 4]);
    assert_eq!(obs(&hidden, &cat, 0), obs(&none, &cat, 0));
    // The enemy never sees it.
    assert_eq!(order_time(&shown, &cat, 1), [0.0; 4]);
    // Arrived: over.
    let mut m = shown.clone();
    m.ships[0].pos.x = 10.0;
    tick(&mut m, &cat);
    assert_eq!(order_time(&m, &cat, 0), [0.0; 4]);
}

#[test]
fn a_deadline_changes_nothing_in_the_first_583_obs_floats() {
    let cat = test_catalogue();
    let plain = goto_duel(&cat, 120.0, 50.0, NO_DEADLINE);
    let timed = goto_duel(&cat, 120.0, 50.0, T0 + 200);
    let (a, b) = (obs(&plain, &cat, 0), obs(&timed, &cat, 0));
    assert_eq!(a[..OBS_DIM_V7], b[..OBS_DIM_V7]);
    assert_eq!(a[ORDER_OFF + order_f::HAS_ORDER], 1.0);
    assert_ne!(a[OBS_DIM_V7..], b[OBS_DIM_V7..]);
    // And the enemy's whole obs is the same.
    assert_eq!(obs(&plain, &cat, 1), obs(&timed, &cat, 1));
}

#[test]
fn the_goto_pay_is_the_match_config_s_and_is_validated() {
    let cat = test_catalogue();
    let defaults = MatchConfig::default();
    assert_eq!(defaults.goto_timed_bonus, ORDER_TIMED_ARRIVAL_BONUS);
    assert_eq!(defaults.goto_miss_penalty, ORDER_MISS_PENALTY);
    assert_eq!((ORDER_TIMED_ARRIVAL_BONUS, ORDER_MISS_PENALTY), (1.0, 1.0));

    let mut m = goto_duel(&cat, 100.0, 50.0, T0 + 10);
    m.cfg.goto_timed_bonus = 0.6;
    m.ships[0].pos.x = 50.0;
    assert!(close(tick(&mut m, &cat), 50.0 / R + 0.6));
    let mut m = goto_duel(&cat, 50.0 + R, 50.0, T0 + 1);
    m.cfg.goto_miss_penalty = 0.25;
    m.tick = T0 + 2;
    // Φ = −1 exactly one arena radius outside the circle.
    let phi = -1.0;
    let drift = (ORDER_SHAPING_GAMMA - 1.0) * phi;
    assert!(close(refresh(&mut m, &cat), drift - 0.25));

    let cfg = |bonus: f32, penalty: f32| MatchConfig {
        fleets: [vec![FIGHTER], vec![FIGHTER]],
        goto_timed_bonus: bonus,
        goto_miss_penalty: penalty,
        ..MatchConfig::default()
    };
    for bad in [-0.1, f32::NAN, f32::INFINITY, f32::NEG_INFINITY] {
        assert!(
            matches!(
                cfg(bad, 1.0).validate(&cat),
                Err(SetupError::InvalidGotoPay {
                    name: "goto_timed_bonus",
                    ..
                })
            ),
            "bonus {bad}"
        );
        assert!(
            matches!(
                cfg(1.0, bad).validate(&cat),
                Err(SetupError::InvalidGotoPay {
                    name: "goto_miss_penalty",
                    ..
                })
            ),
            "penalty {bad}"
        );
    }
    assert_eq!(cfg(0.0, 0.0).validate(&cat), Ok(()));
    assert_eq!(cfg(3.5, 2.0).validate(&cat), Ok(()));
}

/// A deathmatch duel 600 m apart with ship 0 under an external commander.
fn stepped_duel(cat: &Catalogue) -> Match {
    let ids =
        |names: &[&str]| -> Vec<HullId> { names.iter().map(|n| cat.hull_id(n).unwrap()).collect() };
    let cfg = MatchConfig {
        seed: 5,
        fleets: [ids(&["fighter"]), ids(&["fighter"])],
        commanders: [CommanderMode::External, CommanderMode::Scripted],
        ..MatchConfig::default()
    };
    let mut m = Match::new(cat, &cfg).unwrap();
    for (s, x) in m.ships.iter_mut().zip([-300.0, 300.0]) {
        s.pos = Vec2::new(x, 0.0);
        s.vel = Vec2::ZERO;
        s.heading = 0.0;
        s.present = true;
        s.arrive_tick = 0;
        s.control_lock_until = 0;
    }
    m
}

/// Step with ship 0 flown by the script and the enemy idle; ship 0's order reward.
fn step_ship0(m: &mut Match, cat: &Catalogue) -> f32 {
    let a = scripted::act(m, cat, 0);
    m.set_action(0, a);
    m.step(cat);
    m.order_rewards()[0]
}

fn squad_goto(point: Vec2, radius: f32, deadline: u32) -> Command {
    Command::Squad {
        squad: 0,
        members: 1,
        order: Order::GoTo {
            point,
            radius,
            deadline,
        },
    }
}

#[test]
fn the_scripted_pilot_makes_a_fair_deadline_and_is_paid_the_timed_bonus() {
    let cat = asset_catalogue();
    let mut m = stepped_duel(&cat);
    let point = Vec2::new(-250.0, -200.0);
    m.submit_command(0, squad_goto(point, 40.0, 900));
    let mut bonuses = 0;
    let mut total = 0.0;
    while m.tick() < 900 {
        let r = step_ship0(&mut m, &cat);
        total += r;
        if r > 0.5 * ORDER_TIMED_ARRIVAL_BONUS {
            bonuses += 1;
            assert!((m.ships[0].pos - point).length() <= 40.0);
        }
    }
    let track = *m.order_track(0);
    assert!(track.arrived && !track.missed, "{track:?}");
    assert_eq!(track.deadline, 900);
    assert_eq!(bonuses, 1);
    assert!(total > ORDER_TIMED_ARRIVAL_BONUS, "{total}");
    assert!(matches!(m.command.squads[0][0].order, Order::GoTo { .. }));
}

/// A go-to the ship cannot make: on the miss it is charged once, and the script, with
/// no order to follow any more, turns to its role and closes on the enemy.
#[test]
fn the_scripted_pilot_falls_back_to_its_role_after_a_miss() {
    let cat = asset_catalogue();
    let mut m = stepped_duel(&cat);
    let point = Vec2::new(-300.0, -250.0);
    let deadline = 45;
    // Ordered from the first tick (as if the last slow tick had set it); the point is
    // inside the arena's point limit, so the slow tick's sanitising leaves it alone.
    m.command.squads[0][0] = Squad {
        members: 1,
        order: Order::GoTo {
            point,
            radius: 20.0,
            deadline,
        },
    };
    let enemy = |m: &Match| (m.ships[1].pos - m.ships[0].pos).length();
    let mut charges = 0;
    while m.tick() <= deadline {
        let r = step_ship0(&mut m, &cat);
        charges += u32::from(r < -0.5 * ORDER_MISS_PENALTY);
    }
    assert_eq!(charges, 1, "charged on the first step past the deadline");
    assert_eq!(m.tick(), deadline + 1);
    assert!(m.order_track(0).missed);
    assert_eq!(effective_order(&m, 0), Order::None);
    let to_point = (point - m.ships[0].pos).length();
    assert!(
        to_point < 240.0 && enemy(&m) > 590.0,
        "it flew for the point, not the enemy: {to_point} m to go, enemy at {}",
        enemy(&m)
    );
    let before = enemy(&m);
    for _ in 0..240 {
        let r = step_ship0(&mut m, &cat);
        assert_eq!(r, 0.0, "a missed go-to pays nothing more");
    }
    assert!(enemy(&m) < before - 100.0, "{} -> {}", before, enemy(&m));
    assert!(matches!(m.command.squads[0][0].order, Order::GoTo { .. }));
}

#[test]
fn commands_json_takes_an_optional_deadline() {
    let cat = asset_catalogue();
    let parse = |text: &str| -> Command {
        CommandSpec::parse_list(text).unwrap()[0]
            .to_command(&cat)
            .unwrap()
    };
    let old = r#"{"kind": "squad", "squad": 0, "members": [0],
        "order": {"kind": "goto", "point": [10.0, -20.0], "radius": 30.0}}"#;
    let Command::Squad { order, .. } = parse(old) else {
        panic!("a squad command");
    };
    assert_eq!(
        order,
        Order::GoTo {
            point: Vec2::new(10.0, -20.0),
            radius: 30.0,
            deadline: NO_DEADLINE,
        }
    );
    let timed = r#"{"kind": "squad", "squad": 0, "members": [0],
        "order": {"kind": "goto", "point": [10.0, -20.0], "radius": 30.0, "deadline": 450}}"#;
    let Command::Squad { order, .. } = parse(timed) else {
        panic!("a squad command");
    };
    assert_eq!(order.deadline(), 450);
    for bad in ["-1", "1.5", "\"soon\"", "null"] {
        let text = timed.replace("450", bad);
        assert!(CommandSpec::parse_list(&text).is_err(), "deadline {bad}");
    }
    // The views write it back.
    let spec = sim::spec::OrderSpec::from(order);
    assert!(sim::spec::to_json(&spec).contains("\"deadline\":450"));
}
