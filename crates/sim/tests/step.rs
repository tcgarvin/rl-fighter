//! WP5 acceptance (SIM_SPEC §14): `Match::step` in the §5 order, deaths, termination
//! and winner (§5.8), rewards (§8), plus the scripted-match tests handed over from WP7.

mod common;

use common::{FIGHTER, GUNSHIP, STRAFER, config, new_match, new_present_match, test_catalogue};
use sim::DT;
use sim::actions::{ShipAction, THROTTLE_INCREASE};
use sim::data::Catalogue;
use sim::events::Event;
use sim::math::{PI, Vec2, wrap_angle};
use sim::reward::{ARENA_PENALTY, FIRE_COST, HULL_DAMAGE_WEIGHT, SHIELD_DAMAGE_WEIGHT, WIN_REWARD};
use sim::scripted::act;
use sim::state::{
    MAX_REACTION_TICKS, Match, MatchPhase, Projectile, ShipIdx, WINNER_DRAW, WINNER_NONE,
};

const EPS: f32 = 1e-6;

fn close(a: f32, b: f32, tol: f32) -> bool {
    (a - b).abs() <= tol
}

fn place(m: &mut Match, slot: usize, pos: Vec2, heading: f32) {
    let s = &mut m.ships[slot];
    s.pos = pos;
    s.heading = heading;
    s.vel = Vec2::ZERO;
    s.omega = 0.0;
}

fn fire_nose() -> ShipAction {
    let mut a = ShipAction::IDLE;
    a.fire[0] = 1;
    a
}

/// A live projectile of `owner` placed so it hits the ship at `target_pos` this tick.
fn bullet_at(m: &Match, owner: ShipIdx, target_pos: Vec2, damage: f32) -> Projectile {
    Projectile {
        alive: true,
        team: m.ships[owner as usize].team,
        owner,
        pos: target_pos - Vec2::new(3.0, 0.0),
        vel: Vec2::new(240.0, 0.0),
        speed: 240.0,
        damage,
        life_ticks: 10,
        fire_tick: m.tick,
        ..Projectile::DEAD
    }
}

/// Step with the scripted controller driving every ship until `Over` or `max_ticks`.
fn run_scripted(m: &mut Match, cat: &Catalogue, max_ticks: u32) {
    while m.phase() == MatchPhase::Running && m.tick() < max_ticks {
        for s in 0..m.ships.len() as ShipIdx {
            let a = act(m, cat, s);
            m.set_action(s, a);
        }
        m.step(cat);
    }
}

#[test]
fn shooter_beats_a_ship_that_never_fires() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 3, &[FIGHTER], &[FIGHTER]);
    place(&mut m, 0, Vec2::new(-50.0, 0.0), 0.0);
    place(&mut m, 1, Vec2::new(50.0, 0.0), PI);
    let mut ticks = 0;
    while m.phase() == MatchPhase::Running {
        m.set_action(0, fire_nose());
        m.set_action(1, ShipAction::IDLE);
        m.step(&cat);
        ticks += 1;
        assert!(ticks < 600, "the target should die well within 20 s");
    }
    assert_eq!(m.winner(), 0);
    assert!(m.ships[0].alive);
    assert!(!m.ships[1].alive && !m.ships[1].present);
    assert_eq!(m.ships[1].hp, 0.0);
    assert!(
        m.events()
            .iter()
            .any(|e| matches!(e, Event::Death { ship: 1, .. }))
    );
    // Terminal term on the last step.
    assert!(m.rewards()[0] > WIN_REWARD - 0.1);
    assert!(m.rewards()[1] < -WIN_REWARD);
}

#[test]
fn time_limit_uses_value_tiebreak() {
    let cat = test_catalogue();
    let mut cfg = config(4, &[FIGHTER], &[STRAFER]);
    cfg.time_limit_ticks = 5;
    let mut m = Match::new(&cat, &cfg).unwrap();
    common::make_all_present(&mut m);
    // Fighter 60 hp vs strafer 50 hp + 0.5 * 40 shield = 70: the strafer wins...
    m.ships[1].hp = 50.0;
    for _ in 0..4 {
        m.step(&cat);
        assert_eq!(m.phase(), MatchPhase::Running);
        assert_eq!(m.winner(), WINNER_NONE);
    }
    m.step(&cat);
    assert_eq!(m.tick(), 5);
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), 1);
    assert!(close(m.rewards()[0], -WIN_REWARD, EPS));
    assert!(close(m.rewards()[1], WIN_REWARD, EPS));

    // ...and with equal value it is a draw with no terminal reward.
    let mut m = Match::new(&cat, &cfg).unwrap();
    common::make_all_present(&mut m);
    m.ships[1].hp = 40.0;
    for _ in 0..5 {
        m.step(&cat);
    }
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), WINNER_DRAW);
    assert_eq!(m.rewards(), &[0.0, 0.0]);
}

#[test]
fn time_limit_value_counts_pending_ships() {
    let cat = test_catalogue();
    let mut cfg = config(4, &[FIGHTER, FIGHTER], &[FIGHTER]);
    cfg.time_limit_ticks = 1;
    let mut m = Match::new(&cat, &cfg).unwrap();
    // Nobody has arrived at tick 1; team 0 has two fighters of value, team 1 one.
    m.step(&cat);
    assert!(m.ships.iter().all(|s| !s.present));
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), 0);
}

#[test]
fn simultaneous_death_is_a_draw() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 5, &[FIGHTER], &[FIGHTER]);
    place(&mut m, 0, Vec2::new(-50.0, 0.0), 0.0);
    place(&mut m, 1, Vec2::new(50.0, 0.0), PI);
    m.ships[0].hp = 3.0;
    m.ships[1].hp = 3.0;
    // Ship 0's bullet hits ship 1 first (pool order); ship 1 must still die in the
    // same tick from its own bullet on ship 0.
    m.projectiles[0] = bullet_at(&m, 0, m.ships[1].pos, 6.0);
    m.projectiles[1] = bullet_at(&m, 1, m.ships[0].pos, 6.0);
    m.step(&cat);
    assert!(!m.ships[0].alive && !m.ships[1].alive);
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), WINNER_DRAW);
    let deaths = m
        .events()
        .iter()
        .filter(|e| matches!(e, Event::Death { .. }))
        .count();
    assert_eq!(deaths, 2);
    // Damage terms cancel (each dealt and took 6 hull); no terminal term on a draw.
    for r in m.rewards() {
        assert!(close(*r, 0.0, EPS), "reward {r}");
    }
}

#[test]
fn reward_terms_sum_as_spec() {
    let cat = test_catalogue();
    // Slot 0 fighter, slot 1 strafer (shielded), slot 2 fighter (team 1, ally of 1).
    let mut m = new_present_match(&cat, 6, &[FIGHTER], &[STRAFER, FIGHTER]);
    place(&mut m, 0, Vec2::new(0.0, 0.0), 0.0);
    place(&mut m, 1, Vec2::new(100.0, 0.0), PI);
    // Ship 2 outside the arena, facing away, idle.
    place(&mut m, 2, Vec2::new(0.0, 460.0), 0.0);
    // Ship 0 fires its nose gun (one shot, a miss this tick: the bullet is in flight).
    m.set_action(0, fire_nose());
    // A bullet of ship 0 hits the strafer's shield; one of ship 1 hits fighter 0's hull.
    m.projectiles[10] = bullet_at(&m, 0, m.ships[1].pos, 6.0);
    m.projectiles[11] = bullet_at(&m, 1, m.ships[0].pos, 4.0);
    m.step(&cat);

    assert_eq!(m.shots_fired[0], 1);
    assert_eq!(m.hits().len(), 2);
    assert!(m.hits()[0].shield && !m.hits()[1].shield);
    assert!(m.outside_arena[2]);
    let r = m.rewards();
    let want0 = SHIELD_DAMAGE_WEIGHT * 6.0 - HULL_DAMAGE_WEIGHT * 4.0 + FIRE_COST;
    let want1 = -SHIELD_DAMAGE_WEIGHT * 6.0 + HULL_DAMAGE_WEIGHT * 4.0;
    let want2 = ARENA_PENALTY;
    assert!(close(r[0], want0, EPS), "r0 {} want {want0}", r[0]);
    assert!(close(r[1], want1, EPS), "r1 {} want {want1}", r[1]);
    assert!(close(r[2], want2, EPS), "r2 {} want {want2}", r[2]);
    // Concrete numbers, in case a weight changes silently.
    assert!(close(r[0], 0.03 - 0.04 - 0.002, EPS));
    assert!(close(r[2], -0.002, EPS));
}

#[test]
fn trigger_pull_on_cooldown_costs_nothing() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 7, &[FIGHTER], &[FIGHTER]);
    place(&mut m, 0, Vec2::new(0.0, 0.0), PI / 2.0);
    place(&mut m, 1, Vec2::new(0.0, -200.0), 0.0);
    m.set_action(0, fire_nose());
    m.step(&cat);
    assert!(close(m.rewards()[0], FIRE_COST, EPS));
    m.set_action(0, fire_nose());
    m.step(&cat);
    assert_eq!(m.shots_fired[0], 0, "gun is cooling down");
    assert_eq!(m.rewards()[0], 0.0);
}

#[test]
fn step_after_over_is_a_noop() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 8, &[FIGHTER], &[FIGHTER]);
    place(&mut m, 1, Vec2::new(0.0, 0.0), 0.0);
    m.ships[1].hp = 0.0;
    m.projectiles[0] = bullet_at(&m, 0, Vec2::new(0.0, 300.0), 6.0);
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), 0);
    let ships = m.ships.clone();
    let projectiles = m.projectiles;
    let rng = m.rng.clone();
    let tick = m.tick();
    for k in 1..=3 {
        m.set_action(0, fire_nose());
        m.step(&cat);
        assert_eq!(m.tick(), tick + k, "stage 1 still advances the clock");
        assert_eq!(m.ships, ships);
        assert_eq!(m.projectiles, projectiles);
        assert_eq!(m.rng, rng);
        assert_eq!(m.phase(), MatchPhase::Over);
        assert_eq!(m.winner(), 0);
        assert!(m.events().is_empty() && m.hits().is_empty());
        assert_eq!(m.rewards(), &[0.0, 0.0]);
    }
}

#[test]
fn arrival_events_once_per_ship() {
    let cat = test_catalogue();
    let mut m = new_match(&cat, 9, &[FIGHTER, STRAFER, FIGHTER, GUNSHIP], &[GUNSHIP]);
    let n = m.ships.len();
    let mut seen = vec![0u32; n];
    for _ in 0..120 {
        m.step(&cat);
        for e in m.events() {
            if let Event::Arrival { ship, pos, heading } = *e {
                let s = &m.ships[ship as usize];
                seen[ship as usize] += 1;
                assert_eq!(m.tick(), s.arrive_tick);
                assert!(s.present);
                assert!(wrap_angle(heading - s.heading).abs() < 1e-5);
                // Position is recorded at arrival, before this tick's motion.
                let step = cat.hull(s.hull).arrival_speed * DT;
                assert!((pos + s.vel * DT - s.pos).length() < 1e-3 * step.max(1.0));
            }
        }
    }
    assert_eq!(seen, vec![1; n]);
}

#[test]
fn dead_ships_get_only_the_terminal_term() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 10, &[FIGHTER, FIGHTER], &[FIGHTER]);
    place(&mut m, 0, Vec2::new(-100.0, 0.0), 0.0);
    place(&mut m, 1, Vec2::new(-100.0, 50.0), 0.0);
    place(&mut m, 2, Vec2::new(100.0, 0.0), PI);
    // Kill slot 1 on the first step via a hit from slot 2.
    m.ships[1].hp = 1.0;
    m.projectiles[0] = bullet_at(&m, 2, m.ships[1].pos, 6.0);
    m.step(&cat);
    assert!(!m.ships[1].alive);
    // It took the killing hit while alive, so it is penalised for it.
    assert!(close(m.rewards()[1], -HULL_DAMAGE_WEIGHT * 6.0, EPS));
    assert_eq!(m.phase(), MatchPhase::Running);

    // Now a bullet the dead ship fired hits slot 2: slot 2 is penalised, the dead
    // shooter earns nothing (its credit stays in the HitRecord); its fire is ignored.
    m.projectiles[1] = bullet_at(&m, 1, m.ships[2].pos, 6.0);
    m.set_action(1, fire_nose());
    m.step(&cat);
    assert_eq!(m.hits().len(), 1);
    assert_eq!(m.hits()[0].shooter, 1);
    assert_eq!(m.rewards()[1], 0.0);
    assert!(close(m.rewards()[2], -HULL_DAMAGE_WEIGHT * 6.0, EPS));

    // Finish slot 2: the whole of team 0, the dead slot included, gets +1.
    m.ships[2].hp = 1.0;
    m.projectiles[2] = bullet_at(&m, 0, m.ships[2].pos, 6.0);
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Over);
    assert_eq!(m.winner(), 0);
    assert!(close(m.rewards()[1], WIN_REWARD, EPS));
    assert!(close(
        m.rewards()[0],
        WIN_REWARD + HULL_DAMAGE_WEIGHT * 6.0,
        EPS
    ));
    assert!(close(
        m.rewards()[2],
        -WIN_REWARD - HULL_DAMAGE_WEIGHT * 6.0,
        EPS
    ));
}

#[test]
fn pending_ships_count_as_alive() {
    let cat = test_catalogue();
    let mut m = new_match(&cat, 12, &[FIGHTER], &[FIGHTER]);
    // Before anyone arrives the match keeps running, and a pending ship's team
    // is not eliminated.
    m.step(&cat);
    assert!(m.ships.iter().all(|s| !s.present));
    assert_eq!(m.phase(), MatchPhase::Running);
}

#[test]
fn deaths_clear_levels_and_queue_and_emit_death() {
    let cat = test_catalogue();
    let mut cfg = config(13, &[FIGHTER, FIGHTER], &[FIGHTER]);
    cfg.reaction_ticks = 3;
    let mut m = Match::new(&cat, &cfg).unwrap();
    common::make_all_present(&mut m);
    let mut a = ShipAction::IDLE;
    a.throttle[0] = THROTTLE_INCREASE;
    a.fire[0] = 1;
    for _ in 0..8 {
        m.set_action(0, a);
        m.step(&cat);
    }
    assert!(m.ships[0].thrust_level[0] > 0.0);
    assert!(m.ships[0].queue[..3].iter().all(|q| *q == a));
    m.ships[0].hp = -1.0;
    m.set_action(0, a);
    m.step(&cat);
    let s = &m.ships[0];
    assert!(!s.alive && !s.present);
    assert_eq!(s.hp, 0.0);
    assert_eq!(s.thrust_level, [0.0; 8]);
    assert_eq!(s.queue, [ShipAction::IDLE; MAX_REACTION_TICKS]);
    assert!(
        m.events()
            .iter()
            .any(|e| matches!(e, Event::Death { ship: 0, pos } if *pos == s.pos))
    );
    // Dead ships skip stage 3: nothing is enqueued any more.
    let dead = s.clone();
    m.set_action(0, a);
    m.step(&cat);
    assert_eq!(m.ships[0], dead);
}

#[test]
fn hit_record_decision_tick_is_fire_tick_minus_one_minus_d() {
    let cat = test_catalogue();
    for d in 0..=MAX_REACTION_TICKS as u8 {
        // Fighter (gauss bullets) and strafer (laser beam) on team 0, a fighter
        // target dead ahead of both on team 1.
        let mut cfg = config(14, &[FIGHTER, STRAFER], &[FIGHTER]);
        cfg.reaction_ticks = d;
        let mut m = Match::new(&cat, &cfg).unwrap();
        common::make_all_present(&mut m);
        place(&mut m, 0, Vec2::new(-60.0, 0.0), 0.0);
        place(&mut m, 1, Vec2::new(-40.0, 30.0), 0.0);
        place(&mut m, 2, Vec2::new(0.0, 0.0), 0.0);
        m.ships[2].hp = 1.0e6;
        // Aim the strafer's nose exactly at the target.
        let rel = m.ships[2].pos - m.ships[1].pos;
        m.ships[1].heading = rel.angle();
        let mut seen = [false; 2];
        for _ in 0..40 {
            m.set_action(0, fire_nose());
            m.set_action(1, fire_nose());
            m.step(&cat);
            for p in m.projectiles().iter().filter(|p| p.alive) {
                assert_eq!(p.decision_tick, p.fire_tick - 1 - u32::from(d), "d {d}");
            }
            for h in m.hits() {
                assert_eq!(h.decision_tick, h.fire_tick - 1 - u32::from(d), "d {d}");
                seen[h.shooter as usize] = true;
            }
        }
        assert_eq!(seen, [true, true], "d {d}: bullet and beam both landed");
    }
}

/// Scripted fighter 1v1 from the real jump-in for seeds 0..20 at reaction delay `d`:
/// every duel must end in a kill before the time limit. Returns the
/// (team 0 wins, team 1 wins, draws) split and the sorted lengths in ticks.
fn scripted_duels(d: u8) -> ([u32; 3], Vec<u32>) {
    let cat = test_catalogue();
    let mut split = [0u32; 3];
    let mut lengths = Vec::new();
    for seed in 0..20 {
        let mut cfg = config(seed, &[FIGHTER], &[FIGHTER]);
        cfg.reaction_ticks = d;
        let mut m = Match::new(&cat, &cfg).unwrap();
        let limit = m.cfg.time_limit_ticks;
        run_scripted(&mut m, &cat, limit);
        assert_eq!(m.phase(), MatchPhase::Over, "d {d} seed {seed}");
        let dead = m.ships.iter().filter(|s| !s.alive).count();
        assert!(
            m.tick() < limit && dead >= 1,
            "d {d} seed {seed}: no kill before the time limit (tick {}, hp {:?})",
            m.tick(),
            m.ships.iter().map(|s| s.hp).collect::<Vec<_>>()
        );
        split[if m.winner() >= 0 {
            m.winner() as usize
        } else {
            2
        }] += 1;
        lengths.push(m.tick());
    }
    lengths.sort_unstable();
    println!(
        "scripted fighter 1v1, d = {d}: wins/wins/draws {split:?}, median length {} ticks, \
         range {}..{}",
        lengths[lengths.len() / 2],
        lengths[0],
        lengths[lengths.len() - 1]
    );
    (split, lengths)
}

#[test]
fn scripted_fighter_duel_ends_in_a_kill_without_delay() {
    scripted_duels(0);
}

#[test]
fn scripted_fighter_duel_ends_in_a_kill_at_default_delay() {
    scripted_duels(2);
}

#[test]
fn scripted_fighter_duel_ends_in_a_kill_at_max_delay() {
    scripted_duels(MAX_REACTION_TICKS as u8);
}

#[test]
fn scripted_mixed_2v2_smoke() {
    let cat = test_catalogue();
    for seed in [11, 12, 13] {
        let mut m = new_match(&cat, seed, &[FIGHTER, STRAFER], &[GUNSHIP, FIGHTER]);
        let mut damage_taken = false;
        let limit = m.cfg.time_limit_ticks;
        while m.phase() == MatchPhase::Running {
            for s in 0..m.ships.len() as ShipIdx {
                let a = act(&m, &cat, s);
                m.set_action(s, a);
            }
            m.step(&cat);
            damage_taken |= !m.hits().is_empty();
            for s in &m.ships {
                let finite = [s.pos.x, s.pos.y, s.vel.x, s.vel.y, s.heading, s.omega]
                    .iter()
                    .chain(&[s.hp, s.shield])
                    .all(|v| v.is_finite());
                assert!(
                    finite,
                    "seed {seed} tick {}: non-finite ship {s:?}",
                    m.tick()
                );
            }
            assert!(m.rewards().iter().all(|r| r.is_finite()));
            assert!(m.tick() <= limit);
        }
        assert!(damage_taken, "seed {seed}: nobody took damage");
        println!(
            "2v2 seed {seed}: winner {} at tick {}",
            m.winner(),
            m.tick()
        );
    }
}
