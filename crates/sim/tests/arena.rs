//! WP4 acceptance (SIM_SPEC §14): ship-ship collisions, arena push and drain, and
//! arrival scheduling / jump-in.

mod common;

use common::{
    FIGHTER, GUNSHIP, STRAFER, catalogue_with_static, new_match, new_present_match, test_catalogue,
};
use sim::DT;
use sim::Vec2;
use sim::arrival::{ARRIVAL_LOCK_TICKS, earliest_arrive_tick, latest_arrive_tick};
use sim::collision::deepest_contact;
use sim::data::{Catalogue, HullId};
use sim::math::PI;
use sim::state::{Attach, MAX_SHIPS, Match, ShipIdx};

fn close(a: f32, b: f32, tol: f32) -> bool {
    (a - b).abs() <= tol
}

fn momentum(m: &Match, cat: &Catalogue) -> Vec2 {
    m.ships
        .iter()
        .fold(Vec2::ZERO, |acc, s| acc + s.vel * cat.hull(s.hull).mass)
}

fn mass_centre(m: &Match, cat: &Catalogue) -> Vec2 {
    let total: f32 = m.ships.iter().map(|s| cat.hull(s.hull).mass).sum();
    m.ships
        .iter()
        .fold(Vec2::ZERO, |acc, s| acc + s.pos * cat.hull(s.hull).mass)
        / total
}

/// Ship 0 and ship 1 present, overlapping near the origin and closing head-on.
fn head_on(cat: &Catalogue, team0: HullId, team1: HullId) -> Match {
    let mut m = new_present_match(cat, 1, &[team0], &[team1]);
    m.ships[0].pos = Vec2::new(-3.0, 0.0);
    m.ships[0].heading = 0.0;
    m.ships[0].vel = Vec2::new(10.0, 1.0);
    m.ships[1].pos = Vec2::new(4.5, 0.5);
    m.ships[1].heading = PI;
    m.ships[1].vel = Vec2::new(-4.0, 0.0);
    m
}

#[test]
fn overlapping_ships_separate_and_conserve_momentum() {
    let cat = test_catalogue();
    let mut m = head_on(&cat, FIGHTER, GUNSHIP);
    let (a, b) = (&m.ships[0], &m.ships[1]);
    let before = deepest_contact(a, cat.hull(a.hull), b, cat.hull(b.hull)).expect("overlap");
    let p0 = momentum(&m, &cat);
    let c0 = mass_centre(&m, &cat);
    let gap0 = (m.ships[1].pos - m.ships[0].pos).length();

    m.resolve_collisions(&cat);

    let p1 = momentum(&m, &cat);
    let c1 = mass_centre(&m, &cat);
    assert!(
        close(p0.x, p1.x, 1e-3) && close(p0.y, p1.y, 1e-3),
        "{p0:?} -> {p1:?}"
    );
    assert!(
        close(c0.x, c1.x, 1e-4) && close(c0.y, c1.y, 1e-4),
        "{c0:?} -> {c1:?}"
    );
    assert!((m.ships[1].pos - m.ships[0].pos).length() > gap0);
    // Restitution 0.2: the closing speed along the normal flips to -0.2x.
    let n = before.normal;
    let vn = (m.ships[1].vel - m.ships[0].vel).dot(n);
    assert!(vn > 0.0, "ships still closing: vn {vn}");
    // The resolved circle pair no longer overlaps; repeated passes separate fully.
    for _ in 0..20 {
        m.resolve_collisions(&cat);
    }
    let (a, b) = (&m.ships[0], &m.ships[1]);
    let after = deepest_contact(a, cat.hull(a.hull), b, cat.hull(b.hull));
    assert!(after.is_none_or(|c| c.pen < 1e-4), "{after:?}");
}

#[test]
fn restitution_reverses_a_fifth_of_normal_speed() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 1, &[FIGHTER], &[FIGHTER]);
    // Nose circles (r 2.4, 2 m ahead of centre) are 2 m apart: 2.8 m overlap.
    m.ships[0].pos = Vec2::new(-3.0, 0.0);
    m.ships[0].heading = 0.0;
    m.ships[0].vel = Vec2::new(5.0, 0.0);
    m.ships[1].pos = Vec2::new(3.0, 0.0);
    m.ships[1].heading = PI;
    m.ships[1].vel = Vec2::new(-5.0, 0.0);
    m.resolve_collisions(&cat);
    assert!(close(m.ships[0].vel.x, -1.0, 1e-4), "{:?}", m.ships[0].vel);
    assert!(close(m.ships[1].vel.x, 1.0, 1e-4), "{:?}", m.ships[1].vel);
    // Equal masses split the overlap evenly.
    assert!(close(m.ships[0].pos.x, -4.4, 1e-4), "{:?}", m.ships[0].pos);
    assert!(close(m.ships[1].pos.x, 4.4, 1e-4), "{:?}", m.ships[1].pos);
}

#[test]
fn separating_ships_keep_their_velocity() {
    let cat = test_catalogue();
    let mut m = head_on(&cat, FIGHTER, FIGHTER);
    m.ships[0].vel = Vec2::new(-3.0, 0.0);
    m.ships[1].vel = Vec2::new(3.0, 0.0);
    m.resolve_collisions(&cat);
    assert_eq!(m.ships[0].vel, Vec2::new(-3.0, 0.0));
    assert_eq!(m.ships[1].vel, Vec2::new(3.0, 0.0));
    assert!(
        m.ships[0].pos.x < -3.0,
        "positional correction still applies"
    );
}

#[test]
fn static_hull_does_not_move_in_collisions() {
    let (cat, station) = catalogue_with_static();
    let mut m = new_present_match(&cat, 2, &[station], &[FIGHTER]);
    m.ships[0].pos = Vec2::ZERO;
    m.ships[0].vel = Vec2::ZERO;
    m.ships[1].pos = Vec2::new(12.0, 0.0);
    m.ships[1].heading = PI;
    m.ships[1].vel = Vec2::new(-20.0, 0.0);
    let station_before = m.ships[0].clone();
    m.resolve_collisions(&cat);
    assert_eq!(m.ships[0], station_before);
    let f = &m.ships[1];
    // The fighter takes the whole correction and bounces at 0.2x.
    assert!(close(f.vel.x, 4.0, 1e-4), "{:?}", f.vel);
    let contact = deepest_contact(&m.ships[0], cat.hull(station), f, cat.hull(FIGHTER));
    assert!(contact.is_none_or(|c| c.pen < 1e-4), "{contact:?}");
}

#[test]
fn two_static_hulls_are_left_alone() {
    let (cat, station) = catalogue_with_static();
    let mut m = new_present_match(&cat, 2, &[station], &[station]);
    m.ships[0].pos = Vec2::ZERO;
    m.ships[1].pos = Vec2::new(5.0, 0.0);
    let before = m.ships.clone();
    m.resolve_collisions(&cat);
    assert_eq!(m.ships, before);
}

#[test]
fn parent_child_pairs_do_not_collide() {
    let cat = test_catalogue();
    let mut m = head_on(&cat, FIGHTER, FIGHTER);
    m.ships[1].parent = 0;
    let before = m.ships.clone();
    m.resolve_collisions(&cat);
    assert_eq!(m.ships, before);
}

#[test]
fn outside_arena_is_pushed_back_and_drained() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 3, &[FIGHTER], &[STRAFER]);
    let r = m.cfg.arena_radius;
    m.ships[0].pos = Vec2::new(0.0, r + 10.0);
    m.ships[0].vel = Vec2::ZERO;
    m.ships[1].pos = Vec2::new(r - 10.0, 0.0);
    m.ships[1].vel = Vec2::ZERO;
    m.apply_arena(&cat);

    let s = &m.ships[0];
    assert!(close(s.vel.y, -40.0 * DT, 1e-6), "{:?}", s.vel);
    assert!(close(s.vel.x, 0.0, 1e-6));
    assert!(close(s.hp, 80.0 - 0.02 * 80.0 * DT, 1e-5), "hp {}", s.hp);
    assert_eq!(m.ships[1].vel, Vec2::ZERO, "inside: untouched");
    assert_eq!(m.ships[1].hp, 70.0);
    let mut want = [false; MAX_SHIPS];
    want[0] = true;
    assert_eq!(m.outside_arena, want);

    // Back inside: the flag clears on the next call.
    m.ships[0].pos = Vec2::ZERO;
    m.apply_arena(&cat);
    assert_eq!(m.outside_arena, [false; MAX_SHIPS]);
}

#[test]
fn arena_drain_can_take_hp_to_zero() {
    let cat = test_catalogue();
    let mut m = new_present_match(&cat, 3, &[FIGHTER], &[FIGHTER]);
    let far = Vec2::new(m.cfg.arena_radius * 2.0, 0.0);
    // 2 %/s empties the hull in 50 s; hold the ship outside for a little longer.
    for _ in 0..(51 * 30) {
        m.ships[0].pos = far;
        m.apply_arena(&cat);
    }
    assert!(m.ships[0].hp <= 0.0, "hp {}", m.ships[0].hp);
    assert!(
        m.ships[0].alive,
        "death is resolved by stage 12, not the arena"
    );
}

#[test]
fn static_hull_outside_arena_is_not_pushed_or_drained() {
    let (cat, station) = catalogue_with_static();
    let mut m = new_present_match(&cat, 3, &[station], &[FIGHTER]);
    m.ships[0].pos = Vec2::new(m.cfg.arena_radius + 50.0, 0.0);
    let before = m.ships[0].clone();
    m.apply_arena(&cat);
    assert_eq!(m.ships[0], before);
    assert!(!m.outside_arena[0]);
}

#[test]
fn not_present_ships_are_untouched_by_collision_and_arena() {
    let cat = test_catalogue();
    let mut m = new_match(&cat, 4, &[FIGHTER, FIGHTER], &[FIGHTER]);
    assert!(m.ships.iter().all(|s| !s.present));
    // Ship 0 present, 1 and 2 pending; all piled up outside the arena.
    m.ships[0].present = true;
    let spot = Vec2::new(m.cfg.arena_radius + 20.0, 0.0);
    for (i, s) in m.ships.iter_mut().enumerate() {
        s.pos = spot + Vec2::new(i as f32, 0.0);
        s.vel = Vec2::new(-1.0, 0.0);
    }
    let before = m.ships.clone();
    m.resolve_collisions(&cat);
    m.apply_arena(&cat);
    assert_eq!(&m.ships[1..], &before[1..]);
    assert!(!m.outside_arena[1] && !m.outside_arena[2]);
    // The present ship feels the arena but nothing to collide with.
    assert!(m.outside_arena[0]);
    assert_eq!(m.ships[0].pos, before[0].pos);
}

#[test]
fn dead_ships_are_untouched_by_collision() {
    let cat = test_catalogue();
    let mut m = head_on(&cat, FIGHTER, FIGHTER);
    m.ships[1].alive = false;
    let before = m.ships.clone();
    m.resolve_collisions(&cat);
    assert_eq!(m.ships, before);
}

fn team_slots(m: &Match, team: u8) -> Vec<usize> {
    (0..m.ships.len())
        .filter(|&i| m.ships[i].team == team)
        .collect()
}

#[test]
fn arrival_ticks_within_bounds() {
    let cat = test_catalogue();
    let fleets: [(&[HullId], &[HullId]); 4] = [
        (&[FIGHTER], &[FIGHTER]),
        (&[FIGHTER, STRAFER], &[GUNSHIP, FIGHTER]),
        (&[FIGHTER; 4], &[STRAFER; 4]),
        (&[FIGHTER; 7], &[GUNSHIP]),
    ];
    for (t0, t1) in fleets {
        for seed in 0..200 {
            let m = new_match(&cat, seed, t0, t1);
            for team in 0..2u8 {
                let slots = team_slots(&m, team);
                let hi = latest_arrive_tick(slots.len());
                for &i in &slots {
                    let s = &m.ships[i];
                    assert!(
                        (earliest_arrive_tick()..=hi).contains(&s.arrive_tick),
                        "seed {seed} slot {i}: tick {} not in 30..={hi}",
                        s.arrive_tick
                    );
                    assert!(!s.present);
                    assert_eq!(s.vel, Vec2::ZERO);
                    let side = if team == 0 { -1.0 } else { 1.0 };
                    assert!(s.pos.x * side > 0.0, "team {team} on its own side");
                    assert_eq!(s.heading, if team == 0 { 0.0 } else { PI });
                }
            }
        }
    }
    assert_eq!(earliest_arrive_tick(), 30);
    assert_eq!(latest_arrive_tick(3), 50);
    assert_eq!(latest_arrive_tick(7), 76);
}

#[test]
fn fleets_are_cut_into_squads_of_at_most_three() {
    let cat = test_catalogue();
    for seed in 0..50 {
        let m = new_match(&cat, seed, &[FIGHTER; 7], &[STRAFER; 1]);
        let slots = team_slots(&m, 0);
        let squads: Vec<&[usize]> = slots.chunks(3).collect();
        assert_eq!(
            squads.iter().map(|s| s.len()).collect::<Vec<_>>(),
            [3, 3, 1]
        );
        let mut centres = Vec::new();
        for squad in &squads {
            let ys: Vec<f32> = squad.iter().map(|&i| m.ships[i].pos.y).collect();
            let xs: Vec<f32> = squad.iter().map(|&i| m.ships[i].pos.x).collect();
            // Rows 16 m apart, wing ships 10 m behind the centre ship (team 0: -x).
            for w in ys.windows(2) {
                assert!(close(w[1] - w[0], 16.0, 1e-3), "seed {seed}: {ys:?}");
            }
            if squad.len() == 3 {
                assert!(close(xs[0], xs[1] - 10.0, 1e-3) && close(xs[2], xs[0], 1e-3));
            }
            centres.push(ys.iter().sum::<f32>() / ys.len() as f32);
            // Members of a squad arrive within the 0.08 s jitter of each other.
            let ticks: Vec<u32> = squad.iter().map(|&i| m.ships[i].arrive_tick).collect();
            let spread = ticks.iter().max().unwrap() - ticks.iter().min().unwrap();
            assert!(spread <= 3, "seed {seed}: {ticks:?}");
        }
        // Squad centres 70 m apart, give or take 2 * 15 m of jitter.
        for w in centres.windows(2) {
            assert!(
                (40.0..=100.0).contains(&(w[1] - w[0])),
                "seed {seed}: {centres:?}"
            );
        }
    }
}

/// Advance only the clock and stage 2, collecting arrivals per tick.
fn run_arrivals(m: &mut Match, cat: &Catalogue, ticks: u32) -> Vec<(u32, ShipIdx)> {
    let mut log = Vec::new();
    let mut arrived = Vec::new();
    for _ in 0..ticks {
        m.tick += 1;
        arrived.clear();
        m.process_arrivals(cat, &mut arrived);
        log.extend(arrived.iter().map(|&s| (m.tick, s)));
    }
    log
}

#[test]
fn ships_arrive_on_their_tick_moving_and_locked() {
    let cat = test_catalogue();
    let mut m = new_match(&cat, 9, &[FIGHTER, STRAFER, GUNSHIP, FIGHTER], &[GUNSHIP]);
    let scheduled: Vec<u32> = m.ships.iter().map(|s| s.arrive_tick).collect();
    let log = run_arrivals(&mut m, &cat, 120);
    assert_eq!(log.len(), m.ships.len(), "every ship arrives exactly once");
    for &(tick, slot) in &log {
        let s = &m.ships[slot as usize];
        assert_eq!(tick, scheduled[slot as usize]);
        assert!(s.present);
        assert_eq!(s.control_lock_until, tick + ARRIVAL_LOCK_TICKS);
        assert_eq!(ARRIVAL_LOCK_TICKS, 21);
        let want = Vec2::from_angle(s.heading) * cat.hull(s.hull).arrival_speed;
        assert_eq!(s.vel, want);
        assert!(close(
            s.vel.length(),
            1.4 * cat.hull(s.hull).speed_cap,
            1e-3
        ));
        assert!(s.control_locked(tick + 20) && !s.control_locked(tick + 21));
    }
    // Slot order within a tick.
    for w in log.windows(2) {
        assert!(w[0].0 < w[1].0 || w[0].1 < w[1].1, "{log:?}");
    }
}

#[test]
fn dead_and_attached_ships_do_not_arrive() {
    let cat = test_catalogue();
    let mut m = new_match(&cat, 9, &[FIGHTER, FIGHTER], &[FIGHTER]);
    m.ships[0].alive = false;
    m.ships[1].attach = Attach::Docked;
    let log = run_arrivals(&mut m, &cat, 120);
    assert_eq!(log.iter().map(|&(_, s)| s).collect::<Vec<_>>(), [2]);
    assert!(!m.ships[0].present && !m.ships[1].present);
}

#[test]
fn same_seed_same_arrival_schedule() {
    let cat = test_catalogue();
    let fleets: (&[HullId], &[HullId]) =
        (&[FIGHTER, STRAFER, FIGHTER, GUNSHIP], &[GUNSHIP, FIGHTER]);
    let schedule = |seed| {
        let m = new_match(&cat, seed, fleets.0, fleets.1);
        let ships: Vec<(Vec2, f32, u32)> = m
            .ships
            .iter()
            .map(|s| (s.pos, s.heading, s.arrive_tick))
            .collect();
        (ships, m.state_hash())
    };
    assert_eq!(schedule(21), schedule(21));
    assert_ne!(schedule(21).0, schedule(22).0);
}
