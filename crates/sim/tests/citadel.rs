//! SIM_VERSION 10 (SIM_SPEC §0.8): hardpoints, `capital_only` weapons, the dreadnought
//! (role `line`) and the station assault v10 (the citadel against a carrier and a
//! dreadnought). The v9 bit-exactness of everything older is in `determinism.rs`
//! (`v9_compat_*`).

mod common;

use common::asset_catalogue;
use sim::command::{Command, CommanderMode, Outcome, Refusal, Waypoint};
use sim::commander_io::{ACTION_DIM, CommanderLocks, N_ENTITIES, features, masks, submit};
use sim::damage::{Hardpoint, apply_damage, struck_hardpoint};
use sim::data::{Catalogue, HullId, WeaponKind};
use sim::events::{Event, KIND_BAY_DESTROYED, KIND_TURRET_DESTROYED};
use sim::math::{PI, Vec2};
use sim::mission::{
    BIG_STATION_ARENA_RADIUS, CarrierBattle, EndReason, Mission, MissionKind, StationAssault,
    arena_radius_for_mission, default_rosters,
};
use sim::rng::Pcg32;
use sim::scripted;
use sim::setup::{MatchConfig, SetupError, ShipStart};
use sim::state::{ACTION_TURRETS, Match, MatchPhase, NONE, Projectile, ShipIdx};

fn ids(cat: &Catalogue, names: &[&str]) -> Vec<HullId> {
    names.iter().map(|n| cat.hull_id(n).unwrap()).collect()
}

fn scripted_step(m: &mut Match, cat: &Catalogue) {
    for i in 0..m.ships().len() {
        let a = scripted::act(m, cat, i as u8);
        m.set_action(i as u8, a);
    }
    m.step(cat);
}

/// The v10 default roster ("citadel"), scripted on both sides.
pub fn citadel_cfg(cat: &Catalogue, seed: u64) -> MatchConfig {
    let roster = default_rosters(MissionKind::StationAssault)
        .iter()
        .find(|r| r.name == "citadel")
        .expect("the v10 roster");
    let n = roster.fleets[0].len() + roster.fleets[1].len();
    MatchConfig {
        seed,
        fleets: [ids(cat, roster.fleets[0]), ids(cat, roster.fleets[1])],
        mission: Mission::StationAssault(StationAssault::default()),
        arena_radius: arena_radius_for_mission(MissionKind::StationAssault, n),
        time_limit_ticks: MissionKind::StationAssault.default_time_limit_ticks(),
        ..MatchConfig::default()
    }
}

/// Two capital ships alone at rest in a deathmatch, `gap` m apart along x: team 0's
/// `a` at the origin heading +x, team 1's `b` heading -x.
fn duel(cat: &Catalogue, a: &str, b: &str, gap: f32) -> Match {
    let cfg = MatchConfig {
        seed: 1,
        arena_radius: 2000.0,
        fleets: [ids(cat, &[a]), ids(cat, &[b])],
        start_layout: Some(vec![
            ShipStart {
                pos: Vec2::ZERO,
                vel: Vec2::ZERO,
                heading: 0.0,
            },
            ShipStart {
                pos: Vec2::new(gap, 0.0),
                vel: Vec2::ZERO,
                heading: PI,
            },
        ]),
        ..MatchConfig::default()
    };
    Match::new(cat, &cfg).unwrap()
}

/// The dreadnought-against-carrier check (no live mission): a deathmatch in a 450 m
/// arena, team 0 a dreadnought at `(-300, 0)` heading +x, team 1 a carrier about 600 m
/// away with `wing` (strike craft, at rest in a fan 60 m in front of it), all present at
/// tick 0, 150 s on the clock, scripted pilots. The seed jitters the gap and the
/// carrier's `y`.
pub fn capital_clash(cat: &Catalogue, wing: &[&str], seed: u64) -> Match {
    let mut rng = Pcg32::new(seed);
    let carrier = Vec2::new(300.0 + rng.range(-40.0, 40.0), rng.range(-60.0, 60.0));
    let mut starts = vec![
        ShipStart {
            pos: Vec2::new(-300.0, 0.0),
            vel: Vec2::ZERO,
            heading: 0.0,
        },
        ShipStart {
            pos: carrier,
            vel: Vec2::ZERO,
            heading: PI,
        },
    ];
    for (k, _) in wing.iter().enumerate() {
        let off = (k as f32 - (wing.len() as f32 - 1.0) * 0.5) * 0.3;
        starts.push(ShipStart {
            pos: carrier + Vec2::from_angle(PI + off) * 60.0,
            vel: Vec2::ZERO,
            heading: PI,
        });
    }
    let mut team1 = vec!["carrier"];
    team1.extend_from_slice(wing);
    let cfg = MatchConfig {
        seed,
        fleets: [ids(cat, &["dreadnought"]), ids(cat, &team1)],
        start_layout: Some(starts),
        time_limit_ticks: MissionKind::StationAssault.default_time_limit_ticks(),
        ..MatchConfig::default()
    };
    Match::new(cat, &cfg).unwrap()
}

/// The carrier's wing of a carrier battle's "wing of 8" roster.
pub const WING_OF_8: [&str; 8] = [
    "fighter", "strafer", "fighter", "gunship", "fighter", "strafer", "fighter", "gunship",
];

/// Play `capital_clash` to the end; whether the dreadnought won, and the tick.
fn clash(cat: &Catalogue, wing: &[&str], seed: u64) -> (bool, u32, f32) {
    let mut m = capital_clash(cat, wing, seed);
    while m.phase() == MatchPhase::Running {
        scripted_step(&mut m, cat);
    }
    (m.winner() == 0, m.tick(), m.ships[0].hp)
}

#[test]
fn a_dreadnought_beats_a_lone_carrier_and_loses_to_one_with_its_wing() {
    let cat = asset_catalogue();
    let lone = (0..6).filter(|&s| clash(&cat, &[], s).0).count();
    assert_eq!(lone, 6, "the dreadnought outguns a lone carrier");
    let winged = (0..6).filter(|&s| clash(&cat, &WING_OF_8, s).0).count();
    assert!(winged <= 1, "a carrier with its wing beats it: {winged}/6");
}

#[test]
fn a_hull_hit_also_damages_the_nearest_hardpoint_in_reach() {
    let cat = asset_catalogue();
    let mut m = duel(&cat, "citadel", "fighter", 300.0);
    let hull = cat.hull(m.ships[0].hull).clone();
    m.ships[0].shield = 0.0;
    let lance = m.ships[0].to_world(hull.turrets[0].pos);
    // A hit 3 m from the lance mount: the hull and the lance both take it.
    let at = lance + Vec2::new(3.0, 0.0);
    assert_eq!(
        struck_hardpoint(&hull, &m.ships[0], at),
        Some(Hardpoint::Turret(0))
    );
    let hp0 = m.ships[0].hp;
    apply_damage(&mut m, &cat, 0, 40.0, at, 1, 0, 0);
    assert_eq!(m.ships[0].hp, hp0 - 40.0, "the hull takes the full hit");
    assert_eq!(m.ships[0].turret_hp[0], hull.turrets[0].hp - 40.0);
    assert!(
        m.ships[0].turret_hp[1..]
            .iter()
            .zip(&hull.turrets[1..])
            .all(|(h, t)| *h == t.hp)
    );
    // The flak mount 6 m away is nearer to a point between the two.
    let flak = m.ships[0].to_world(hull.turrets[1].pos);
    let near_flak = flak + (lance - flak) * 0.2;
    assert_eq!(
        struck_hardpoint(&hull, &m.ships[0], near_flak),
        Some(Hardpoint::Turret(1))
    );
    // Far from every mount: only the hull.
    let core = m.ships[0].pos + Vec2::new(0.0, -19.9);
    assert_eq!(struck_hardpoint(&hull, &m.ships[0], core), None);
    let before = m.ships[0].turret_hp;
    apply_damage(&mut m, &cat, 0, 40.0, core, 1, 0, 0);
    assert_eq!(m.ships[0].turret_hp, before);
    // A bay mouth (hit radius 7).
    let bay = m.ships[0].to_world(hull.bays[2].pos);
    assert_eq!(
        struck_hardpoint(&hull, &m.ships[0], bay + Vec2::new(-1.0, 0.0)),
        Some(Hardpoint::Bay(2))
    );
}

#[test]
fn a_raised_shield_takes_the_hit_and_no_hardpoint_does() {
    let cat = asset_catalogue();
    let mut m = duel(&cat, "citadel", "fighter", 300.0);
    let hull = cat.hull(m.ships[0].hull).clone();
    assert!(m.ships[0].shield > 0.0);
    let lance = m.ships[0].to_world(hull.turrets[0].pos);
    apply_damage(&mut m, &cat, 0, 40.0, lance, 1, 0, 0);
    assert_eq!(m.ships[0].turret_hp[0], hull.turrets[0].hp);
    assert_eq!(m.ships[0].hp, hull.hp);
}

#[test]
fn a_destroyed_turret_never_slews_or_fires_again() {
    let cat = asset_catalogue();
    let mut m = duel(&cat, "dreadnought", "carrier", 200.0);
    let hull = cat.hull(m.ships[0].hull).clone();
    m.ships[0].shield = 0.0;
    // Destroy the bow gauss (turret 4) with one big hit on its mount.
    let mount = m.ships[0].to_world(hull.turrets[4].pos);
    m.events.clear();
    apply_damage(&mut m, &cat, 0, 1000.0, mount, 1, 0, 0);
    assert!(!m.ships[0].turret_alive(4));
    assert_eq!(m.ships[0].turret_hp[4], 0.0);
    let e: Vec<Event> = m.events().to_vec();
    assert!(e.iter().any(|e| matches!(
        e,
        Event::TurretDestroyed {
            ship: 0,
            turret: 4,
            shooter: 1,
            ..
        }
    )));
    assert_eq!(
        e.last().unwrap().encode()[0],
        f32::from(KIND_TURRET_DESTROYED)
    );
    // A dead hardpoint takes no more damage and is not struck again.
    assert_eq!(struck_hardpoint(&hull, &m.ships[0], mount), None);
    // Ask every turret to slew left and fire, every tick.
    let angle = m.ships[0].turret_angle[4];
    let mut fired = [0u32; 5];
    for _ in 0..90 {
        let mut a = sim::actions::ShipAction::IDLE;
        a.slew[..5].fill(0);
        a.fire[..5].fill(1);
        m.set_action(0, a);
        m.step(&cat);
        for e in m.events() {
            if let Event::Fire {
                ship: 0, turret, ..
            } = e
            {
                fired[usize::from(*turret)] += 1;
            }
        }
    }
    assert_eq!(m.ships[0].turret_angle[4], angle, "a dead turret holds");
    assert_eq!(fired[4], 0, "and never fires");
    assert!(fired[2] > 0 && m.ships[0].turret_angle[2] != hull.turrets[2].rest);
}

#[test]
fn destroyed_bays_never_launch_and_with_every_bay_gone_the_hangar_is_stuck() {
    let cat = asset_catalogue();
    let mut m = Match::new(&cat, &citadel_cfg(&cat, 2)).unwrap();
    m.step(&cat);
    let citadel = usize::from(m.carrier_of(0));
    for b in [0, 1, 3] {
        m.ships[citadel].dead_bays |= 1 << b;
    }
    assert_eq!(m.launch(&cat, 0, None, Some(0)), Err(Refusal::BayDestroyed));
    let (_, bay) = m.launch(&cat, 0, None, None).unwrap();
    assert_eq!(bay, 2, "the one bay left");
    m.ships[citadel].dead_bays |= 1 << 2;
    for _ in 0..60 {
        m.step(&cat);
    }
    assert!(!m.hangar(0).is_empty());
    assert_eq!(m.launch(&cat, 0, None, None), Err(Refusal::BayDestroyed));
    // The commander's view and the learned commander's masks agree: nothing is ready.
    let obs = m.commander_obs(&cat, 0);
    assert!(obs.bays_ready.iter().all(|&r| !r));
    let mk = masks(&m, &cat, 0, &CommanderLocks::default());
    assert!(mk.launch.iter().all(|&l| !l));
    // A launch command is refused with the reason, not dropped silently.
    let mut cfg = citadel_cfg(&cat, 2);
    cfg.commanders[0] = CommanderMode::External;
    let mut m = Match::new(&cat, &cfg).unwrap();
    let citadel = usize::from(m.carrier_of(0));
    m.ships[citadel].dead_bays = 0b1111;
    m.submit_command(
        0,
        Command::Launch {
            hull: None,
            bay: None,
        },
    );
    while !m.command_due() {
        m.step(&cat);
    }
    m.step(&cat);
    assert_eq!(
        m.command_results[0]
            .iter()
            .map(|r| r.outcome)
            .collect::<Vec<_>>(),
        vec![Outcome::Refused(Refusal::BayDestroyed)]
    );
}

#[test]
fn bay_destroyed_events_encode_the_mount() {
    let cat = asset_catalogue();
    let mut m = duel(&cat, "citadel", "dreadnought", 350.0);
    let hull = cat.hull(m.ships[0].hull).clone();
    m.ships[0].shield = 0.0;
    let mouth = m.ships[0].to_world(hull.bays[1].pos);
    m.events.clear();
    apply_damage(&mut m, &cat, 0, 250.0, mouth, 1, 0, 0);
    assert!(!m.ships[0].bay_alive(1));
    let flat = m.events().last().unwrap().encode();
    assert_eq!(flat[0], f32::from(KIND_BAY_DESTROYED));
    assert_eq!(&flat[1..5], &[0.0, 1.0, mouth.x, mouth.y]);
    assert_eq!(flat[7], 1.0, "the shooter");
}

fn shot(
    weapon: u16,
    team: u8,
    owner: ShipIdx,
    pos: Vec2,
    vel: Vec2,
    cat: &Catalogue,
) -> Projectile {
    let w = cat.weapon(weapon);
    Projectile {
        alive: true,
        kind: w.kind,
        weapon,
        team,
        owner,
        pos,
        vel,
        speed: w.speed,
        damage: w.damage,
        life_ticks: w.life_ticks,
        fire_tick: 0,
        decision_tick: 0,
        target: NONE,
    }
}

#[test]
fn capital_only_shots_pass_through_strike_craft() {
    let cat = asset_catalogue();
    let lance = cat.weapons.iter().position(|w| w.name == "lance").unwrap() as u16;
    let gauss = 0u16;
    assert!(cat.weapon(lance).capital_only && cat.weapon(lance).kind == WeaponKind::Bullet);
    // Team 0: a citadel far away; team 1: a fighter at (100, 0) and a carrier at (200, 0).
    let cfg = MatchConfig {
        seed: 3,
        arena_radius: 2000.0,
        fleets: [ids(&cat, &["citadel"]), ids(&cat, &["fighter", "carrier"])],
        start_layout: Some(vec![
            ShipStart {
                pos: Vec2::new(-500.0, 0.0),
                vel: Vec2::ZERO,
                heading: 0.0,
            },
            ShipStart {
                pos: Vec2::new(100.0, 0.0),
                vel: Vec2::ZERO,
                heading: PI,
            },
            ShipStart {
                pos: Vec2::new(200.0, 0.0),
                vel: Vec2::ZERO,
                heading: PI,
            },
        ]),
        ..MatchConfig::default()
    };
    let mut m = Match::new(&cat, &cfg).unwrap();
    let v = Vec2::new(300.0, 0.0);
    m.projectiles[0] = shot(lance, 0, 0, Vec2::new(60.0, 0.0), v, &cat);
    m.projectiles[1] = shot(
        gauss,
        0,
        0,
        Vec2::new(60.0, 0.5),
        Vec2::new(200.0, 0.0),
        &cat,
    );
    let mut hit_fighter = [0u32; 2];
    let mut hit_carrier = 0u32;
    for _ in 0..30 {
        m.step(&cat);
        for h in m.hits() {
            match h.target {
                1 => hit_fighter[usize::from(h.damage > 10.0)] += 1,
                2 => hit_carrier += 1,
                _ => {}
            }
        }
    }
    assert_eq!(
        hit_fighter,
        [1, 0],
        "the gauss round hits the fighter, the lance does not"
    );
    assert_eq!(hit_carrier, 1, "the lance flies on into the carrier");
}

#[test]
fn hardpoint_hp_never_soaks_hull_damage() {
    // The v9 rule for the hull is unchanged: a hull with hardpoints loses exactly what
    // the same hull without them does.
    let cat = asset_catalogue();
    let mut plain = cat.clone();
    let id = usize::from(cat.hull_id("dreadnought").unwrap());
    for t in &mut plain.hulls[id].turrets {
        t.hp = 0.0;
    }
    let hit = |c: &Catalogue| {
        let mut m = duel(c, "dreadnought", "carrier", 320.0);
        m.ships[0].shield = 0.0;
        let hull = c.hull(m.ships[0].hull).clone();
        let mut lost = Vec::new();
        for (j, t) in hull.turrets.iter().enumerate() {
            let at = m.ships[0].to_world(t.pos) + Vec2::new(0.0, 1.5);
            let before = m.ships[0].hp;
            apply_damage(&mut m, c, 0, 90.0, at, 1, 0, 0);
            lost.push((before - m.ships[0].hp, m.ships[0].turret_alive(j)));
        }
        lost
    };
    let with = hit(&cat);
    let without = hit(&plain);
    for ((a, alive), (b, _)) in with.iter().zip(&without) {
        assert_eq!(a, b, "the hull takes the same hit either way");
        assert!(*alive, "90 is under every dreadnought hardpoint's hp");
    }
}

#[test]
fn v10_station_assault_setup_and_arena() {
    let cat = asset_catalogue();
    let cfg = citadel_cfg(&cat, 5);
    assert_eq!(cfg.arena_radius, BIG_STATION_ARENA_RADIUS);
    assert_eq!(
        arena_radius_for_mission(MissionKind::StationAssault, 16),
        450.0
    );
    let m = Match::new(&cat, &cfg).unwrap();
    let citadel = usize::from(m.carrier_of(0));
    assert_eq!(cat.hull(m.ships[citadel].hull).name, "citadel");
    let carrier = usize::from(m.carrier_of(1));
    let dread = (0..m.ships.len())
        .find(|&s| cat.hull(m.ships[s].hull).role == "line")
        .unwrap();
    assert_eq!(m.ships[dread].team, 1);
    let d = &m.ships[dread];
    assert!(d.present && d.alive && d.attach == sim::state::Attach::None);
    assert_eq!(m.command.waypoints[dread], Waypoint::Unset);
    assert!(!m.hangar(1).contains(&(dread as u8)));
    // Beside its carrier, ahead of it, outside the lance's reach.
    let to_citadel = (d.pos - m.ships[citadel].pos).length();
    assert!(
        to_citadel > 430.0,
        "starts outside lance range: {to_citadel}"
    );
    assert!(d.pos.x < m.ships[carrier].pos.x);
    assert!((d.pos - m.ships[carrier].pos).length() < 100.0);
    // Wide ships hash their extra state; v9 hulls are not wide.
    assert!(m.ships[citadel].wide && d.wide && !m.ships[carrier].wide);
}

#[test]
fn v10_station_assault_is_repelled_only_once_the_dreadnought_is_gone() {
    let cat = asset_catalogue();
    let mut m = Match::new(&cat, &citadel_cfg(&cat, 6)).unwrap();
    m.step(&cat);
    let dread = (0..m.ships.len())
        .find(|&s| cat.hull(m.ships[s].hull).role == "line")
        .unwrap();
    for s in 0..m.ships.len() {
        if m.ships[s].team == 1 && s != dread {
            m.ships[s].hp = 0.0;
        }
    }
    m.step(&cat);
    assert_eq!(m.phase(), MatchPhase::Running, "the dreadnought fights on");
    m.ships[dread].hp = 0.0;
    m.step(&cat);
    assert_eq!(
        (m.winner(), m.mission.end_reason),
        (0, EndReason::AssaultRepelled)
    );
    // The citadel falls: the attackers win.
    let mut m = Match::new(&cat, &citadel_cfg(&cat, 6)).unwrap();
    m.step(&cat);
    let citadel = usize::from(m.carrier_of(0));
    m.ships[citadel].hp = 0.0;
    m.step(&cat);
    assert_eq!(
        (m.winner(), m.mission.end_reason),
        (1, EndReason::StationDestroyed)
    );
}

#[test]
fn line_ships_are_validated_by_mission() {
    let cat = asset_catalogue();
    let dread = cat.hull_id("dreadnought").unwrap();
    // Two on the attack, or one on the defence: refused.
    let mut cfg = citadel_cfg(&cat, 1);
    cfg.fleets[1].push(dread);
    assert!(matches!(
        Match::new(&cat, &cfg),
        Err(SetupError::Mission(_))
    ));
    let mut cfg = citadel_cfg(&cat, 1);
    cfg.fleets[0].push(dread);
    assert!(matches!(
        Match::new(&cat, &cfg),
        Err(SetupError::Mission(_))
    ));
    // Not in a carrier battle (no new live mission); fine in a deathmatch.
    let carrier = cat.hull_id("carrier").unwrap();
    let fighter = cat.hull_id("fighter").unwrap();
    let cb = MatchConfig {
        fleets: [vec![carrier, dread, fighter], vec![carrier, fighter]],
        mission: Mission::CarrierBattle(CarrierBattle::default()),
        ..MatchConfig::default()
    };
    assert!(matches!(Match::new(&cat, &cb), Err(SetupError::Mission(_))));
    let dm = MatchConfig {
        fleets: [vec![dread], vec![carrier, fighter]],
        ..MatchConfig::default()
    };
    assert!(Match::new(&cat, &dm).is_ok());
}

#[test]
fn the_scripted_dreadnought_closes_and_holds_the_enemy_off_its_bow() {
    let cat = asset_catalogue();
    // Carrier at 700 m with no waypoint: it holds still.
    let mut m = duel(&cat, "dreadnought", "carrier", 700.0);
    let range = scripted::capital::main_gun_range(&cat, cat.hull(m.ships[0].hull));
    assert_eq!(range, 380.0);
    for _ in 0..30 * 60 {
        scripted_step(&mut m, &cat);
        if m.phase() == MatchPhase::Over {
            break;
        }
    }
    let d = &m.ships[0];
    let c = &m.ships[1];
    let off_bow = sim::math::wrap_angle((c.pos - d.pos).angle() - d.heading).abs();
    assert!(
        c.alive,
        "60 s is too short to sink a carrier at rail damage 22"
    );
    let dist = (c.pos - d.pos).length();
    assert!(dist < 380.0 && dist > 200.0, "at standoff: {dist}");
    assert!((0.5..0.9).contains(&off_bow), "held off the bow: {off_bow}");
}

#[test]
fn rails_go_for_the_lances_first() {
    let cat = asset_catalogue();
    let mut m = duel(&cat, "dreadnought", "citadel", 330.0);
    // Strip the citadel's shield so hits land on the hull (and the hardpoints).
    let mut lance_hits = 0;
    let mut other_hits = 0;
    for _ in 0..30 * 40 {
        m.ships[1].shield = 0.0;
        let before = m.ships[1].turret_hp;
        scripted_step(&mut m, &cat);
        for (j, &was) in before.iter().enumerate() {
            if m.ships[1].turret_hp[j] < was {
                if j == 0 || j == 6 {
                    lance_hits += 1;
                } else {
                    other_hits += 1;
                }
            }
        }
    }
    assert!(lance_hits > 0, "the rails struck a lance");
    assert!(
        !m.ships[1].turret_alive(0) || lance_hits >= other_hits,
        "lances first: {lance_hits} vs {other_hits}"
    );
}

/// A learned commander on the attack, with a dreadnought in its fleet: random valid
/// decisions for a whole match never panic, and never put the dreadnought in a squad.
#[test]
fn a_learned_commander_plays_the_v10_assault_without_touching_the_dreadnought() {
    let cat = asset_catalogue();
    for team in 0..2u8 {
        let mut cfg = citadel_cfg(&cat, 9 + u64::from(team));
        cfg.commanders[usize::from(team)] = CommanderMode::Learned;
        let mut m = Match::new(&cat, &cfg).unwrap();
        let dread = (0..m.ships.len())
            .find(|&s| cat.hull(m.ships[s].hull).role == "line")
            .unwrap();
        let mut locks = CommanderLocks::default();
        let mut rng = Pcg32::new(77);
        while m.phase() == MatchPhase::Running && m.tick() < 3000 {
            if m.command_due_for(team) {
                let f = features(&m, &cat, team, &locks);
                assert!(
                    !f.masks.squad[dread][1..].iter().any(|&a| a),
                    "never in a squad"
                );
                assert_eq!(f.valid.len(), N_ENTITIES);
                let mut action = [0i32; ACTION_DIM];
                for (i, a) in action.iter_mut().enumerate() {
                    let n = sim::commander_io::head_choices(i) as u32;
                    *a = (rng.next_u32() % n) as i32;
                }
                submit(&mut m, &cat, team, &mut locks, &action).unwrap();
            }
            scripted_step(&mut m, &cat);
            for q in &m.command.squads[usize::from(team)] {
                assert!(!q.contains(dread));
            }
        }
    }
}

/// The scripted v10 assault: the turrets and bays do get destroyed, nothing panics, the
/// match ends with a reason. (`station_assault_v10_*` golden traces pin it bit for bit.)
#[test]
fn a_scripted_v10_assault_destroys_hardpoints_and_ends() {
    let cat = asset_catalogue();
    let mut destroyed = 0;
    for seed in 0..3 {
        let mut m = Match::new(&cat, &citadel_cfg(&cat, 20 + seed)).unwrap();
        while m.phase() == MatchPhase::Running {
            scripted_step(&mut m, &cat);
            destroyed += m
                .events()
                .iter()
                .filter(|e| {
                    matches!(
                        e,
                        Event::TurretDestroyed { .. } | Event::BayDestroyed { .. }
                    )
                })
                .count();
        }
        assert_ne!(m.mission.end_reason, EndReason::NotOver);
    }
    assert!(destroyed > 0, "hardpoints were destroyed");
}

#[test]
fn a_citadel_flown_through_action_rows_flies_as_the_script() {
    // The bindings and the web send action rows (six turret slots); stage 0 gives the
    // citadel's other six turrets the script's heads, so a row-driven match is the
    // script-driven one bit for bit.
    let cat = asset_catalogue();
    let cfg = citadel_cfg(&cat, 61);
    let mut whole = Match::new(&cat, &cfg).unwrap();
    let mut rows = Match::new(&cat, &cfg).unwrap();
    let mut row = [0i8; sim::actions::ACTION_WIDTH];
    let mut extra_fired = 0;
    for _ in 0..2400 {
        if whole.phase() != MatchPhase::Running {
            break;
        }
        for i in 0..whole.ships().len() {
            let a = scripted::act(&whole, &cat, i as u8);
            whole.set_action(i as u8, a);
            scripted::act(&rows, &cat, i as u8).to_row(&mut row);
            rows.set_action(i as u8, sim::actions::ShipAction::from_row(&row));
        }
        whole.step(&cat);
        rows.step(&cat);
        assert_eq!(
            whole.state_hash(),
            rows.state_hash(),
            "tick {}",
            whole.tick()
        );
        extra_fired += whole
            .events()
            .iter()
            .filter(|e| matches!(e, Event::Fire { ship: 0, turret, .. } if usize::from(*turret) >= ACTION_TURRETS))
            .count();
    }
    assert!(
        extra_fired > 0,
        "the citadel's turrets past the sixth fired"
    );
}

#[test]
fn the_action_row_keeps_six_turret_slots() {
    assert_eq!(ACTION_TURRETS, 6);
    assert_eq!(sim::actions::ACTION_WIDTH, 21);
    let row = [1i8; 21];
    let a = sim::actions::ShipAction::from_row(&row);
    assert!(
        a.slew[ACTION_TURRETS..]
            .iter()
            .all(|&s| s == sim::actions::SLEW_HOLD)
    );
    assert!(a.fire[ACTION_TURRETS..].iter().all(|&f| f == 0));
}

/// Diagnostic, not a gate: script-vs-script v10 assaults, summed over `RLF_DIAG_N`
/// matches (default 20): attacker wins, end reasons, length, hardpoints destroyed, who
/// damaged the citadel, what the citadel did to the dreadnought, the most live
/// projectiles at once; `RLF_DIAG_VERBOSE=1` adds a line a match, `RLF_ASSETS=<dir>` loads
/// another assets directory (the balance sweep). Run with `cargo test -p sim --release
/// --test citadel diag -- --ignored --nocapture`.
#[cfg(not(target_os = "wasi"))]
#[test]
#[ignore]
fn diag_v10_assault() {
    use std::collections::BTreeMap;
    let cat = match std::env::var("RLF_ASSETS") {
        Ok(dir) => Catalogue::load_dir(std::path::Path::new(&dir)).expect("assets load"),
        Err(_) => asset_catalogue(),
    };
    let n: u64 = std::env::var("RLF_DIAG_N")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(20);
    let verbose = std::env::var("RLF_DIAG_VERBOSE").is_ok_and(|v| v == "1");
    let mut att = 0;
    let mut reasons = BTreeMap::<&str, u32>::new();
    let (mut turrets, mut bays, mut live_max, mut secs) = (0u32, 0u32, 0usize, 0.0f32);
    let mut on_citadel = BTreeMap::<String, f32>::new();
    let (mut on_dread, mut dread_lost, mut dread_deaths) = (0.0f32, 0.0f32, 0u32);
    let mut dread_turrets = 0u32;
    let mut first_kill = BTreeMap::<String, u32>::new();
    for seed in 0..n {
        let mut m = Match::new(&cat, &citadel_cfg(&cat, 1000 + seed)).unwrap();
        let dread = (0..m.ships.len())
            .find(|&s| cat.hull(m.ships[s].hull).role == "line")
            .unwrap();
        let citadel = usize::from(m.carrier_of(0));
        let (mut t, mut b, mut first) = (0, 0, true);
        while m.phase() == MatchPhase::Running {
            scripted_step(&mut m, &cat);
            for h in m.hits() {
                if usize::from(h.target) == citadel {
                    let name = cat.hull(m.ships[usize::from(h.shooter)].hull).name.clone();
                    *on_citadel.entry(name).or_default() += h.damage;
                }
                if usize::from(h.target) == dread && usize::from(h.shooter) == citadel {
                    on_dread += h.damage;
                }
            }
            for e in m.events() {
                let (hit_ship, mount) = match e {
                    Event::TurretDestroyed { ship, turret, .. } => {
                        if usize::from(*ship) == citadel {
                            t += 1;
                        } else {
                            dread_turrets += 1;
                        }
                        let h = cat.hull(m.ships[usize::from(*ship)].hull);
                        (*ship, h.turrets[usize::from(*turret)].id.clone())
                    }
                    Event::BayDestroyed { ship, bay, .. } => {
                        b += 1;
                        let h = cat.hull(m.ships[usize::from(*ship)].hull);
                        (*ship, h.bays[usize::from(*bay)].id.clone())
                    }
                    Event::Death { ship, .. } if usize::from(*ship) == dread => {
                        dread_deaths += 1;
                        continue;
                    }
                    _ => continue,
                };
                if first && usize::from(hit_ship) == citadel {
                    first = false;
                    // "turret.flak.2" -> "flak", "bay.0" -> "bay".
                    let kind = match mount.split('.').collect::<Vec<_>>()[..] {
                        ["turret", kind, ..] => kind.to_string(),
                        [kind, ..] => kind.to_string(),
                        [] => "?".to_string(),
                    };
                    *first_kill.entry(kind).or_default() += 1;
                }
            }
            live_max = live_max.max(m.projectiles().iter().filter(|p| p.alive).count());
        }
        if m.winner() == 1 {
            att += 1;
        }
        *reasons.entry(m.mission.end_reason.name()).or_default() += 1;
        turrets += t;
        bays += b;
        secs += m.tick() as f32 / 30.0;
        dread_lost += 1800.0 - m.ships[dread].hp;
        if verbose {
            let c = &m.ships[citadel];
            println!(
                "seed {seed}: {} at {:.0}s, turrets {t} bays {b}, dread hp {:.0}, citadel hp {:.0}",
                m.mission.end_reason.name(),
                m.tick() as f32 / 30.0,
                m.ships[dread].hp,
                c.hp,
            );
        }
    }
    let nf = n as f32;
    let parts: Vec<String> = on_citadel
        .iter()
        .map(|(k, v)| format!("{k} {:.0}", v / nf))
        .collect();
    println!(
        "attacker win {:.3} ({att}/{n}); ends {reasons:?}; mean {:.0}s",
        att as f32 / nf,
        secs / nf
    );
    println!(
        "citadel hardpoints destroyed a match: turrets {:.2}, bays {:.2}; first kill {first_kill:?}",
        turrets as f32 / nf,
        bays as f32 / nf
    );
    println!("on citadel a match: {}", parts.join(", "));
    println!(
        "citadel on dreadnought {:.0} a match; dreadnought hull lost {:.0}, turrets lost {:.2}, \
         died {dread_deaths}/{n}; live projectiles max {live_max}",
        on_dread / nf,
        dread_lost / nf,
        dread_turrets as f32 / nf
    );
}

/// Diagnostic, not a gate: the dreadnought against a lone carrier, a carrier with half
/// a wing and one with the "wing of 8", `RLF_DIAG_N` seeds each (default 20; also
/// `RLF_ASSETS`, as `diag_v10_assault`).
#[cfg(not(target_os = "wasi"))]
#[test]
#[ignore]
fn diag_dreadnought_vs_carrier() {
    let cat = match std::env::var("RLF_ASSETS") {
        Ok(dir) => Catalogue::load_dir(std::path::Path::new(&dir)).expect("assets load"),
        Err(_) => asset_catalogue(),
    };
    let n: u64 = std::env::var("RLF_DIAG_N")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(20);
    for (name, wing) in [
        ("lone carrier", &[][..]),
        ("carrier + 4", &WING_OF_8[..4]),
        ("carrier + wing of 8", &WING_OF_8[..]),
    ] {
        let (mut wins, mut secs, mut hp) = (0, 0.0f32, 0.0f32);
        for seed in 0..n {
            let (won, tick, left) = clash(&cat, wing, 500 + seed);
            wins += u32::from(won);
            secs += tick as f32 / 30.0;
            hp += left;
        }
        let nf = n as f32;
        println!(
            "dreadnought vs {name}: wins {:.3} ({wins}/{n}), mean {:.0}s, dreadnought hull left {:.0}",
            wins as f32 / nf,
            secs / nf,
            hp / nf
        );
    }
}
