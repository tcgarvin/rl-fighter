//! The learned commander's interface (`docs/COMMANDER.md`, `sim::commander_io`) and its
//! cadence (`CommanderMode::Learned`, `LEARNED_COMMAND_TICKS`).

mod common;

use common::asset_catalogue;
use sim::command::{
    COMMAND_TICKS, Command, CommanderMode, LEARNED_COMMAND_TICKS, Order, Squad, Waypoint,
};
use sim::commander_io::{
    ACTION_DIM, CommanderFeatures, CommanderLocks, DecodeError, ENTITY_DIM, FLAT_DIM, FLAT_LAYOUT,
    GLOBAL_DIM, GOTO_RADIUS, HOLD_DECISIONS, N_ENTITIES, N_POINTS, act, decode, ent, features,
    glob, map_point, masks, ship_hold_left, squad_hold_left, submit,
};
use sim::data::{Catalogue, HullId};
use sim::math::{PI, Vec2};
use sim::mission::{CarrierBattle, ConvoyEscort, Mission};
use sim::scripted;
use sim::setup::{MatchConfig, ShipStart};
use sim::state::{Attach, MAX_SHIPS, Match};

const R: f32 = 450.0;

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

const WING: [&str; 3] = ["fighter", "strafer", "gunship"];

/// A deathmatch of `WING` vs `WING`, team 1 placed as team 0's point mirror.
fn mirrored_deathmatch(cat: &Catalogue, commanders: [CommanderMode; 2]) -> Match {
    let starts = [
        (Vec2::new(-200.0, 40.0), Vec2::new(10.0, -3.0), 0.4),
        (Vec2::new(-150.0, -90.0), Vec2::new(0.0, 12.0), -1.1),
        (Vec2::new(-260.0, 120.0), Vec2::new(-4.0, 5.0), 2.6),
    ];
    let mut layout: Vec<ShipStart> = starts
        .iter()
        .map(|&(pos, vel, heading)| ShipStart { pos, vel, heading })
        .collect();
    let mirrored: Vec<ShipStart> = layout
        .iter()
        .map(|s| ShipStart {
            pos: -s.pos,
            vel: -s.vel,
            heading: s.heading + PI,
        })
        .collect();
    layout.extend(mirrored);
    let cfg = MatchConfig {
        seed: 5,
        arena_radius: R,
        fleets: [ids(cat, &WING), ids(cat, &WING)],
        commanders,
        start_layout: Some(layout),
        ..MatchConfig::default()
    };
    Match::new(cat, &cfg).unwrap()
}

fn carrier_cfg(cat: &Catalogue, commanders: [CommanderMode; 2]) -> MatchConfig {
    let team = [
        "carrier", "fighter", "strafer", "fighter", "gunship", "fighter", "fighter",
    ];
    MatchConfig {
        seed: 2,
        arena_radius: R,
        fleets: [ids(cat, &team), ids(cat, &team)],
        mission: Mission::CarrierBattle(CarrierBattle::default()),
        time_limit_ticks: 9000,
        commanders,
        ..MatchConfig::default()
    }
}

fn convoy_cfg(cat: &Catalogue, commanders: [CommanderMode; 2]) -> MatchConfig {
    let t0 = ["freighter", "freighter", "fighter", "strafer"];
    let t1 = ["fighter", "fighter", "gunship"];
    MatchConfig {
        seed: 4,
        arena_radius: R,
        fleets: [ids(cat, &t0), ids(cat, &t1)],
        mission: Mission::ConvoyEscort(ConvoyEscort::standard(R)),
        commanders,
        ..MatchConfig::default()
    }
}

/// Overwrite team 1 of a match whose teams have the same fleet with the point mirror
/// of team 0 (slot `s` of team 0 is slot `s + half` of team 1).
fn mirror_team_one(m: &mut Match) {
    let half = m.ships.len() / 2;
    for s in 0..half {
        let a = m.ships[s].clone();
        let b = &mut m.ships[s + half];
        b.pos = -a.pos;
        b.vel = -a.vel;
        b.heading = a.heading + PI;
        b.hp = a.hp;
        b.shield = a.shield;
        b.present = a.present;
        b.alive = a.alive;
    }
}

/// Team 1's features with its slots renumbered as team 0's (slot `s` <-> `s + half`).
fn assert_mirror(f0: &CommanderFeatures, f1: &CommanderFeatures, n: usize) {
    let half = n / 2;
    let swap = |s: usize| if s < half { s + half } else { s - half };
    for (i, (a, b)) in f0.globals.iter().zip(&f1.globals).enumerate() {
        assert!((a - b).abs() < 1e-5, "global {i}: {a} vs {b}");
    }
    for s in 0..N_ENTITIES {
        let t = if s < n { swap(s) } else { s };
        for i in 0..ENTITY_DIM {
            let (a, b) = (f0.entities[s][i], f1.entities[t][i]);
            assert!((a - b).abs() < 1e-5, "slot {s} feature {i}: {a} vs {b}");
        }
        assert_eq!(f0.valid[s], f1.valid[t]);
        assert_eq!(f0.masks.squad[s], f1.masks.squad[t]);
        assert_eq!(f0.masks.target[s], f1.masks.target[t]);
        assert_eq!(f0.masks.ward[s], f1.masks.ward[t]);
    }
    assert_eq!(f0.masks.launch, f1.masks.launch);
    assert_eq!(f0.masks.waypoint, f1.masks.waypoint);
    assert_eq!(f0.masks.order, f1.masks.order);
}

#[test]
fn a_mirrored_deathmatch_looks_the_same_to_both_teams() {
    let cat = asset_catalogue();
    let mut m = mirrored_deathmatch(&cat, [CommanderMode::Learned; 2]);
    // Mirrored squads and orders: squad 0 attacks the enemy gunship, squad 1 goes to
    // map point 3 (each team's own frame).
    for team in 0..2usize {
        let o = 3 * team;
        let e = 3 * (1 - team);
        m.command.squads[team][0] = Squad {
            members: 0b11 << o,
            order: Order::Attack {
                target: (e + 2) as u8,
            },
        };
        m.command.squads[team][1] = Squad {
            members: 1 << (o + 2),
            order: Order::GoTo {
                point: map_point(team as u8, 3, R),
                radius: GOTO_RADIUS,
            },
        };
        m.ships[o + 1].hp *= 0.5;
    }
    let locks = CommanderLocks::default();
    let f0 = features(&m, &cat, 0, &locks);
    let f1 = features(&m, &cat, 1, &locks);
    assert_mirror(&f0, &f1, 6);
    // Spot checks in team 0's frame: its ship 0 is on its home side, the enemy's
    // mirror on the far side; the gunship is squad 0's attack target.
    assert!(f0.entities[0][ent::POS] < 0.0 && f0.entities[3][ent::POS] > 0.0);
    assert!((f1.entities[3][ent::POS] - f0.entities[0][ent::POS]).abs() < 1e-6);
    assert_eq!(f0.entities[5][ent::TARGET_OF], 1.0);
    assert_eq!(f0.entities[0][ent::SQUAD + 1], 1.0);
    assert_eq!(f0.entities[2][ent::SQUAD + 2], 1.0);
    assert_eq!(f0.entities[3][ent::SQUAD], 0.0, "enemies show no squad");
    assert!(
        (f0.globals[glob::SQUADS + 8 + 7] - 0.3).abs() < 1e-6,
        "point 3 is +y"
    );
    assert_eq!(f0.globals[glob::ROLE], 1.0);
}

#[test]
fn a_mirrored_carrier_battle_looks_the_same_to_both_teams() {
    let cat = asset_catalogue();
    let mut m = Match::new(&cat, &carrier_cfg(&cat, [CommanderMode::Learned; 2])).unwrap();
    for _ in 0..90 {
        scripted_step(&mut m, &cat);
    }
    mirror_team_one(&mut m);
    // Same bay cooldowns and hangars on both sides.
    m.mission.bay_ready[1] = m.mission.bay_ready[0];
    assert_eq!(m.hangar(0).len(), m.hangar(1).len());
    let locks = CommanderLocks::default();
    let f0 = features(&m, &cat, 0, &locks);
    let f1 = features(&m, &cat, 1, &locks);
    assert_mirror(&f0, &f1, m.ships.len());
    let carrier = usize::from(m.carrier_of(0));
    assert_eq!(f0.entities[carrier][ent::CLASS + 3], 1.0);
    assert_eq!(f0.entities[carrier][ent::DIST_OWN], 0.0);
    assert!(f0.entities[carrier][ent::DIST_ENEMY] > 1.0);
    assert_eq!(f0.globals[glob::ROLE + 1], 1.0);
    assert_eq!(f0.globals[glob::CARRIER], 1.0);
    assert_eq!(f0.globals[glob::ENEMY_CARRIER], 1.0);
    // Docked reserves are not entities.
    for &s in m.hangar(0) {
        assert!(!f0.valid[usize::from(s)]);
        assert!(f0.entities[usize::from(s)].iter().all(|&x| x == 0.0));
    }
}

#[test]
fn convoy_roles_and_reference_ships() {
    let cat = asset_catalogue();
    let m = Match::new(&cat, &convoy_cfg(&cat, [CommanderMode::Learned; 2])).unwrap();
    let locks = CommanderLocks::default();
    let f0 = features(&m, &cat, 0, &locks);
    let f1 = features(&m, &cat, 1, &locks);
    assert_eq!(f0.globals[glob::ROLE + 2], 1.0, "defender");
    assert_eq!(f1.globals[glob::ROLE + 3], 1.0, "attacker");
    // Needed to escape (2) and to destroy (1), of a convoy of 2.
    assert_eq!(f0.globals[glob::CONVOY + 2], 1.0);
    assert_eq!(f0.globals[glob::CONVOY + 3], 0.5);
    assert_eq!(
        f0.globals[glob::CONVOY..glob::CONVOY + 5],
        f1.globals[glob::CONVOY..glob::CONVOY + 5]
    );
    // A transport measures 0 to the lead transport only if it is the lead; escorts
    // measure to it; the attackers have no reference ship of their own.
    let leads = (0..2)
        .filter(|&s| f0.entities[s][ent::DIST_OWN] == 0.0)
        .count();
    assert_eq!(leads, 1);
    assert!(f0.entities[2][ent::DIST_OWN] > 0.0);
    assert_eq!(f1.entities[2][ent::DIST_OWN], 0.0);
    assert!(f1.entities[2][ent::DIST_ENEMY] > 0.0);
    assert!(
        f0.masks.launch.iter().all(|&l| !l),
        "no carrier, no launches"
    );
    assert!(f0.masks.waypoint[1..].iter().all(|&w| !w));
}

#[test]
fn masks_follow_the_carrier_reserves_and_the_field() {
    let cat = asset_catalogue();
    let mut m = Match::new(&cat, &carrier_cfg(&cat, [CommanderMode::Learned; 2])).unwrap();
    let locks = CommanderLocks::default();
    let k = masks(&m, &cat, 0, &locks);
    // Hangar: fighter, gunship, fighter, fighter; no strafer.
    assert_eq!(k.launch, [true, false, true]);
    assert!(k.waypoint.iter().all(|&w| w));
    // Tick 0: the jump-ins are arriving, only the carriers are on the field.
    let carrier = usize::from(m.carrier_of(0));
    let enemy = usize::from(m.carrier_of(1));
    for s in 0..MAX_SHIPS {
        assert_eq!(k.target[s], s == enemy, "slot {s}");
        assert_eq!(k.ward[s], s == carrier, "slot {s}");
    }
    let arriving: Vec<usize> = (0..m.ships.len())
        .filter(|&s| {
            m.ships[s].team == 0 && !m.ships[s].present && m.ships[s].attach == Attach::None
        })
        .collect();
    assert_eq!(arriving.len(), 2);
    for s in 0..MAX_SHIPS {
        let movable = arriving.contains(&s);
        assert_eq!(
            k.squad[s],
            [true, movable, movable, movable, movable, movable],
            "slot {s}"
        );
    }
    assert!(k.order.iter().all(|row| *row == [true; 5]));

    // Busy bays: no launches; the hold is still there.
    m.mission.bay_ready[0] = [u32::MAX; 4];
    assert_eq!(masks(&m, &cat, 0, &locks).launch, [false; 3]);
    let f = features(&m, &cat, 0, &locks);
    assert_eq!(f.globals[glob::BAYS_READY], 0.0);
    assert!(f.globals[glob::BAYS] > 0.0);

    // No carrier: no launches, no waypoints.
    m.ships[carrier].alive = false;
    m.ships[carrier].present = false;
    let k = masks(&m, &cat, 0, &locks);
    assert_eq!(k.launch, [false; 3]);
    assert!(k.waypoint[0]);
    assert!(k.waypoint[1..].iter().all(|&w| !w));
    assert!(!k.ward[carrier]);
    // No own ship on the field: defend is masked, none/attack/go-to are not.
    assert!(
        k.order
            .iter()
            .all(|row| *row == [true, true, true, false, true])
    );

    // No strike craft at all: only keep.
    for s in arriving {
        m.ships[s].alive = false;
    }
    let k = masks(&m, &cat, 0, &locks);
    assert!(
        k.order
            .iter()
            .all(|row| *row == [true, false, false, false, false])
    );
}

#[test]
fn a_deathmatch_has_no_carrier_heads_and_needs_ships_on_the_field_to_attack() {
    let cat = asset_catalogue();
    let cfg = MatchConfig {
        seed: 1,
        fleets: [ids(&cat, &WING), ids(&cat, &WING)],
        commanders: [CommanderMode::Learned; 2],
        ..MatchConfig::default()
    };
    let m = Match::new(&cat, &cfg).unwrap();
    let f = features(&m, &cat, 0, &CommanderLocks::default());
    assert_eq!(f.masks.launch, [false; 3]);
    assert!(f.masks.waypoint[1..].iter().all(|&w| !w));
    // Everyone is still jumping in.
    assert!(f.valid[..6].iter().all(|&v| v));
    assert!(f.entities[..6].iter().all(|e| e[ent::ARRIVING] == 1.0));
    assert!(
        f.masks
            .order
            .iter()
            .all(|row| *row == [true, true, false, false, true])
    );
    assert_eq!(f.globals[glob::LAUNCH_AGE], 1.0, "never launched");
    assert_eq!(f.globals[glob::OWN_STRIKE], 0.0);
}

fn keep() -> [i32; ACTION_DIM] {
    [0; ACTION_DIM]
}

/// Step (scripted pilots) until `team`'s decision is due.
fn until_due(m: &mut Match, cat: &Catalogue, team: u8) {
    while !m.command_due_for(team) {
        scripted_step(m, cat);
    }
}

/// Decode and submit `action` for `team` once due, then step onto the slow tick.
fn decide(
    m: &mut Match,
    cat: &Catalogue,
    team: u8,
    locks: &mut CommanderLocks,
    action: &[i32],
) -> usize {
    until_due(m, cat, team);
    let n = submit(m, cat, team, locks, action).unwrap();
    scripted_step(m, cat);
    n
}

/// A deathmatch with every ship on the field (learned team 0).
fn present_deathmatch(cat: &Catalogue) -> Match {
    mirrored_deathmatch(cat, [CommanderMode::Learned, CommanderMode::External])
}

#[test]
fn map_points_are_in_the_team_frame() {
    let p = |team: u8, k: usize| map_point(team, k, R);
    assert_eq!(p(0, 0), Vec2::ZERO);
    let close = |a: Vec2, b: Vec2| (a - b).length() < 1e-3;
    assert!(close(p(0, 1), Vec2::new(0.3 * R, 0.0)));
    assert!(close(p(0, 3), Vec2::new(0.0, 0.3 * R)));
    assert!(close(p(0, 5), Vec2::new(-0.3 * R, 0.0)));
    assert!(close(p(0, 9), Vec2::new(0.6 * R, 0.0)));
    assert!(close(p(0, 17), Vec2::new(0.85 * R, 0.0)));
    let diag = 0.85 * R / 2f32.sqrt();
    assert!(close(p(0, 24), Vec2::new(diag, -diag)));
    for k in 0..N_POINTS {
        assert!(close(p(1, k), -p(0, k)), "team 1's point {k} is the mirror");
    }
}

#[test]
fn decode_moves_ships_sets_orders_and_keeps() {
    let cat = asset_catalogue();
    let mut m = present_deathmatch(&cat);
    let mut locks = CommanderLocks::default();
    assert!(decode(&m, &cat, 0, &mut locks, &keep()).unwrap().is_empty());
    assert_eq!(locks.decisions, 1, "a keep is still a decision");

    let mut a = keep();
    a[act::SQUAD] = 2; // slot 0 -> squad 1
    a[act::SQUAD + 1] = 2; // slot 1 -> squad 1
    a[act::SQUAD + 2] = 3; // slot 2 -> squad 2
    a[act::ORDER] = 2; // squad 1 attacks
    a[act::TARGET] = 4;
    a[act::ORDER + 1] = 4; // squad 2 goes to point 9
    a[act::POINT + 1] = 9;
    a[act::ORDER + 2] = 2; // squad 3 is empty: no order
    a[act::TARGET + 2] = 3;
    let cmds = decode(&m, &cat, 0, &mut locks, &a).unwrap();
    assert_eq!(
        cmds,
        vec![
            Command::Squad {
                squad: 0,
                members: 0b011,
                order: Order::Attack { target: 4 },
            },
            Command::Squad {
                squad: 1,
                members: 0b100,
                order: Order::GoTo {
                    point: map_point(0, 9, R),
                    radius: GOTO_RADIUS,
                },
            },
        ]
    );
    let end = 1 + HOLD_DECISIONS;
    assert_eq!(&locks.ship_hold_end[..4], &[end, end, end, 0]);
    assert_eq!(&locks.ship_hold_kind[..3], &[1, 1, 3]);
    assert_eq!(locks.changed_ships, 3);

    // Team 1 decodes the same go-to in its own frame.
    let mut l1 = CommanderLocks::default();
    let mut b = keep();
    b[act::SQUAD + 3] = 2;
    b[act::ORDER] = 4;
    b[act::POINT] = 9;
    let cmds = decode(&m, &cat, 1, &mut l1, &b).unwrap();
    let [
        Command::Squad {
            squad: 0,
            members: 0b1000,
            order: Order::GoTo { point, radius },
        },
    ] = cmds[..]
    else {
        panic!("one go-to squad command, got {cmds:?}");
    };
    assert!(
        (point - Vec2::new(-0.6 * R, 0.0)).length() < 1e-3,
        "{point:?}"
    );
    assert_eq!(radius, GOTO_RADIUS);

    // Masked choices read as keep: attack an own ship, defend an enemy, move an enemy.
    m.command.squads[0][0] = Squad {
        members: 0b11,
        order: Order::None,
    };
    let mut locks = CommanderLocks::default();
    let mut c = keep();
    c[act::ORDER] = 2;
    c[act::TARGET] = 1;
    c[act::ORDER + 1] = 3;
    c[act::WARD + 1] = 4;
    c[act::SQUAD + 4] = 2;
    c[act::LAUNCH] = 1;
    c[act::WAYPOINT] = 3;
    assert!(decode(&m, &cat, 0, &mut locks, &c).unwrap().is_empty());
    assert_eq!(locks.ship_hold_end, [0; MAX_SHIPS]);
    assert_eq!(locks.changed_ships, 0);
    assert_eq!(locks.last_launch_tick, None);
}

#[test]
fn moving_every_member_out_empties_the_squad() {
    let cat = asset_catalogue();
    let mut m = present_deathmatch(&cat);
    m.command.squads[0][2] = Squad {
        members: 0b1,
        order: Order::Attack { target: 3 },
    };
    let mut locks = CommanderLocks::default();
    let mut a = keep();
    a[act::SQUAD] = 1; // slot 0 -> no squad
    a[act::ORDER + 2] = 3; // an order for a squad that ends empty is moot
    a[act::WARD + 2] = 1;
    let cmds = decode(&m, &cat, 0, &mut locks, &a).unwrap();
    assert_eq!(
        cmds,
        vec![Command::Squad {
            squad: 2,
            members: 0,
            order: Order::Attack { target: 3 },
        }]
    );
    assert_eq!(locks.changed_ships, 1, "slot 0 lost its attack order");
    assert_eq!(locks.ship_hold_kind[0], 0);
    assert_eq!(squad_hold_left(&m, &cat, 0, &locks, 2), HOLD_DECISIONS - 1);
}

#[test]
fn a_changed_order_holds_five_decisions_and_reissues_are_not_changes() {
    let cat = asset_catalogue();
    let mut m = present_deathmatch(&cat);
    let mut locks = CommanderLocks::default();
    let mut a = keep();
    a[act::SQUAD] = 2;
    a[act::SQUAD + 1] = 2;
    a[act::ORDER] = 4;
    a[act::POINT] = 17; // far: nobody arrives during the test
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &a), 1);
    assert_eq!(m.command.squads[0][0].members, 0b11);
    let goto = m.command.squads[0][0].order;
    assert_eq!(goto.kind(), 3);
    assert_eq!(locks.changed_ships, 2);

    // The same decision again is no change: no commands, no new hold.
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &a), 0);
    assert_eq!(locks.ship_hold_end[0], HOLD_DECISIONS);
    assert_eq!(locks.changed_ships, 0);

    // A different order or move is refused (read as keep) while the hold lasts:
    // decisions 2, 3 and 4 after the change at decision 0.
    let mut b = keep();
    b[act::ORDER] = 1;
    b[act::SQUAD] = 1;
    for left in [3, 2, 1] {
        let f = features(&m, &cat, 0, &locks);
        assert_eq!(f.masks.order[0], [true, false, false, false, false]);
        assert_eq!(f.masks.squad[0], [true, false, false, false, false, false]);
        assert!(f.masks.squad[2][1], "slot 2 never moved");
        assert!(f.masks.order[1][1], "squad 2 never changed");
        let want = left as f32 / HOLD_DECISIONS as f32;
        assert_eq!(f.entities[0][ent::SHIP_HOLD], want);
        assert_eq!(f.globals[glob::SQUADS + 5], want);
        assert_eq!(decide(&mut m, &cat, 0, &mut locks, &b), 0, "{left} left");
        assert_eq!(m.command.squads[0][0].order, goto);
    }
    // Decision 5, five seconds after the change: free again.
    assert_eq!(locks.decisions, HOLD_DECISIONS);
    let f = features(&m, &cat, 0, &locks);
    assert_eq!(f.masks.order[0], [true; 5]);
    assert_eq!(f.entities[0][ent::SHIP_HOLD], 0.0);
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &b), 1);
    assert_eq!(m.command.squads[0][0].members, 0b10);
    assert_eq!(m.command.squads[0][0].order, Order::None);
    assert_eq!(locks.changed_ships, 2, "both ships lost the go-to");
    assert_eq!(locks.ship_hold_end[1], 2 * HOLD_DECISIONS);
}

/// The gap the first rules left: a ship could take a new order through its squad one
/// second, move squad the next, and have that squad's order change the second after.
#[test]
fn a_ship_cannot_be_re_ordered_through_another_squad() {
    let cat = asset_catalogue();
    let mut m = present_deathmatch(&cat);
    let mut locks = CommanderLocks::default();
    let mut a = keep();
    a[act::SQUAD] = 2; // slot 0 -> squad 1, which attacks
    a[act::ORDER] = 2;
    a[act::TARGET] = 4;
    a[act::SQUAD + 1] = 3; // slot 1 -> squad 2, which defends
    a[act::ORDER + 1] = 3;
    a[act::WARD + 1] = 2;
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &a), 2);

    // Slot 0 may not follow its new order into squad 2.
    let mut b = keep();
    b[act::SQUAD] = 3;
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &b), 0);
    assert_eq!(m.command.squads[0][0].members, 0b1);

    // Slot 2, never ordered, joins squad 1: its order changes, so it is held, and
    // squad 1 cannot take a new order until that hold ends too.
    let mut c = keep();
    c[act::SQUAD + 2] = 2;
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &c), 1);
    assert_eq!(locks.changed_ships, 1);
    assert_eq!(ship_hold_left(&m, &locks, 0), HOLD_DECISIONS - 3);
    assert_eq!(ship_hold_left(&m, &locks, 2), HOLD_DECISIONS - 1);
    assert_eq!(squad_hold_left(&m, &cat, 0, &locks, 0), HOLD_DECISIONS - 1);
    let mut d = keep();
    d[act::ORDER] = 1;
    for _ in 0..HOLD_DECISIONS - 1 {
        assert!(!masks(&m, &cat, 0, &locks).order[0][1]);
        assert_eq!(decide(&mut m, &cat, 0, &mut locks, &d), 0);
    }
    assert!(masks(&m, &cat, 0, &locks).order[0][1]);
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &d), 1);
    assert_eq!(locks.changed_ships, 2);
}

#[test]
fn moving_between_squads_with_the_same_order_is_not_a_change() {
    let cat = asset_catalogue();
    let mut m = present_deathmatch(&cat);
    let mut locks = CommanderLocks::default();
    // Slot 0 from no squad into squad 1, which has no order: still no order.
    let mut a = keep();
    a[act::SQUAD] = 2;
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &a), 1);
    assert_eq!(locks.changed_ships, 0);
    assert_eq!(ship_hold_left(&m, &locks, 0), 0);
    // So the squad can be ordered on the very next decision.
    let mut b = keep();
    b[act::ORDER] = 2;
    b[act::TARGET] = 3;
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &b), 1);
    assert_eq!(locks.changed_ships, 1);
    assert_eq!(ship_hold_left(&m, &locks, 0), HOLD_DECISIONS - 1);
}

#[test]
fn a_spent_order_ends_its_hold_at_once() {
    let cat = asset_catalogue();
    let mut m = present_deathmatch(&cat);
    let mut locks = CommanderLocks::default();
    let mut a = keep();
    a[act::SQUAD] = 2; // slot 0 attacks slot 4
    a[act::ORDER] = 2;
    a[act::TARGET] = 4;
    a[act::SQUAD + 1] = 3; // slot 1 goes to point 5
    a[act::ORDER + 1] = 4;
    a[act::POINT + 1] = 5;
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &a), 2);
    assert_eq!(ship_hold_left(&m, &locks, 0), HOLD_DECISIONS - 1);
    assert_eq!(ship_hold_left(&m, &locks, 1), HOLD_DECISIONS - 1);

    // The target dies: the attack cannot be followed, so the squad is free before
    // the slow tick has even cleared the order.
    m.ships[4].hp = 0.0;
    scripted_step(&mut m, &cat);
    assert_eq!(m.command.squads[0][0].order, Order::Attack { target: 4 });
    assert_eq!(ship_hold_left(&m, &locks, 0), 0);
    let f = features(&m, &cat, 0, &locks);
    assert_eq!(f.entities[0][ent::SHIP_HOLD], 0.0);
    assert!(f.masks.order[0][2] && f.masks.squad[0][3]);
    assert!(!f.masks.order[1][1], "squad 2's go-to still holds");

    // The go-to ship arrives: its order is done, so it is free too.
    let Order::GoTo { point, .. } = m.command.squads[0][1].order else {
        panic!("squad 2 has a go-to");
    };
    m.ships[1].pos = point;
    scripted_step(&mut m, &cat);
    assert_eq!(ship_hold_left(&m, &locks, 1), 0);
    assert!(masks(&m, &cat, 0, &locks).order[1][1]);

    // A new order starts a new hold.
    let mut b = keep();
    b[act::ORDER] = 2;
    b[act::TARGET] = 3;
    assert_eq!(decide(&mut m, &cat, 0, &mut locks, &b), 1);
    assert_eq!(ship_hold_left(&m, &locks, 0), HOLD_DECISIONS - 1);
}

/// A hold reads its order's state only once the decision has applied: straight after
/// decoding, the ship still shows the order it had before.
#[test]
fn a_hold_is_not_spent_before_its_decision_applies() {
    let cat = asset_catalogue();
    let mut m = present_deathmatch(&cat);
    let mut locks = CommanderLocks::default();
    let mut a = keep();
    a[act::SQUAD] = 2;
    a[act::ORDER] = 2;
    a[act::TARGET] = 4;
    until_due(&mut m, &cat, 0);
    submit(&mut m, &cat, 0, &mut locks, &a).unwrap();
    assert_eq!(ship_hold_left(&m, &locks, 0), HOLD_DECISIONS - 1);
}

#[test]
fn decode_launches_and_waypoints_from_the_carrier() {
    let cat = asset_catalogue();
    let mut m = Match::new(
        &cat,
        &carrier_cfg(&cat, [CommanderMode::Learned, CommanderMode::Scripted]),
    )
    .unwrap();
    let mut locks = CommanderLocks::default();
    let fighter = cat.hull_id("fighter").unwrap();
    let gunship = cat.hull_id("gunship").unwrap();
    let carrier = m.carrier_of(0);
    let mut a = keep();
    a[act::LAUNCH] = 1;
    a[act::LAUNCH + 1] = 1; // no strafer in the hangar: hold
    a[act::LAUNCH + 2] = 1;
    a[act::WAYPOINT] = 1 + 10;
    until_due(&mut m, &cat, 0);
    let cmds = decode(&m, &cat, 0, &mut locks, &a).unwrap();
    assert_eq!(
        cmds,
        vec![
            Command::Waypoint {
                ship: carrier,
                waypoint: Waypoint::At(map_point(0, 10, R)),
            },
            Command::Launch {
                hull: Some(fighter),
                bay: None,
            },
            Command::Launch {
                hull: Some(gunship),
                bay: None,
            },
        ]
    );
    assert_eq!(m.tick() + 1, LEARNED_COMMAND_TICKS);
    assert_eq!(locks.last_launch_tick, Some(LEARNED_COMMAND_TICKS));
    for c in cmds {
        m.submit_command(0, c);
    }
    scripted_step(&mut m, &cat);
    let launched = m
        .command_results(0)
        .iter()
        .filter(|o| matches!(o.outcome, sim::command::Outcome::Launched { .. }))
        .count();
    assert!(launched >= 1);
    assert_eq!(
        m.command.waypoints[usize::from(carrier)],
        Waypoint::At(map_point(0, 10, R))
    );
    for _ in 0..15 * 30 {
        scripted_step(&mut m, &cat);
    }
    let f = features(&m, &cat, 0, &locks);
    let want = (15.0 * 30.0 / 30.0) / 20.0;
    assert!((f.globals[glob::LAUNCH_AGE] - want).abs() < 1e-5);
}

#[test]
fn out_of_range_values_are_errors_and_change_nothing() {
    let cat = asset_catalogue();
    let m = present_deathmatch(&cat);
    let mut locks = CommanderLocks::default();
    let mut a = keep();
    a[act::SQUAD] = 2;
    a[act::ORDER] = 5;
    assert_eq!(
        decode(&m, &cat, 0, &mut locks, &a),
        Err(DecodeError::OutOfRange {
            index: act::ORDER,
            value: 5,
            choices: 5
        })
    );
    a[act::ORDER] = 0;
    a[act::POINT] = 25;
    assert!(decode(&m, &cat, 0, &mut locks, &a).is_err());
    a[act::POINT] = 0;
    a[act::TARGET] = -1;
    assert!(decode(&m, &cat, 0, &mut locks, &a).is_err());
    assert_eq!(
        decode(&m, &cat, 0, &mut locks, &a[..39]),
        Err(DecodeError::Length { len: 39 })
    );
    assert_eq!(locks, CommanderLocks::default());
}

#[test]
fn a_learned_team_decides_every_30_ticks_the_other_every_60() {
    let cat = asset_catalogue();
    let mut m = present_deathmatch(&cat);
    let mut due = [Vec::new(), Vec::new()];
    for _ in 0..240 {
        for team in 0..2u8 {
            if m.command_due_for(team) {
                due[usize::from(team)].push(m.tick() + 1);
            }
        }
        assert_eq!(
            m.command_due(),
            m.command_due_for(0) || m.command_due_for(1)
        );
        m.step(&cat);
    }
    assert_eq!(due[0], vec![30, 60, 90, 120, 150, 180, 210, 240]);
    assert_eq!(due[1], vec![60, 120, 180, 240]);

    // Team 1's commands wait for its own slow tick; team 0's apply on its next.
    let mut m = present_deathmatch(&cat);
    while m.tick() < LEARNED_COMMAND_TICKS - 1 {
        m.step(&cat);
    }
    let squad = |members: u32| Command::Squad {
        squad: 0,
        members,
        order: Order::None,
    };
    m.submit_command(0, squad(0b1));
    m.submit_command(1, squad(0b1000));
    m.step(&cat);
    assert_eq!(m.command.squads[0][0].members, 0b1);
    assert_eq!(m.command.squads[1][0].members, 0);
    assert_eq!(m.command_results(0).len(), 1);
    assert!(m.command_results(1).is_empty());
    while m.tick() < COMMAND_TICKS {
        m.step(&cat);
    }
    assert_eq!(m.command.squads[1][0].members, 0b1000);
    assert!(m.command_results(0).is_empty(), "team 0 sent nothing at 60");
    assert_eq!(m.command_results(1).len(), 1);
}

#[test]
fn a_learned_team_that_sends_nothing_plays_like_an_external_one() {
    let cat = asset_catalogue();
    for cfg in [
        carrier_cfg(&cat, [CommanderMode::Scripted, CommanderMode::External]),
        convoy_cfg(&cat, [CommanderMode::External, CommanderMode::Scripted]),
    ] {
        let mut learned = cfg.clone();
        for c in learned.commanders.iter_mut() {
            if *c == CommanderMode::External {
                *c = CommanderMode::Learned;
            }
        }
        let mut a = Match::new(&cat, &cfg).unwrap();
        let mut b = Match::new(&cat, &learned).unwrap();
        for _ in 0..600 {
            scripted_step(&mut a, &cat);
            scripted_step(&mut b, &cat);
            assert_eq!(a.state_hash(), b.state_hash(), "tick {}", a.tick());
        }
    }
}

#[test]
fn default_matches_keep_the_60_tick_cadence() {
    let cat = asset_catalogue();
    for modes in [
        [CommanderMode::Scripted; 2],
        [CommanderMode::External, CommanderMode::Random],
    ] {
        let mut m = Match::new(&cat, &carrier_cfg(&cat, modes)).unwrap();
        for _ in 0..200 {
            let want = (m.tick() + 1) % COMMAND_TICKS == 0;
            assert_eq!(m.command_due(), want);
            assert_eq!(m.command_due_for(0), want);
            assert_eq!(m.command_due_for(1), want);
            scripted_step(&mut m, &cat);
        }
    }
    assert_eq!(
        CommanderMode::from_name("learned"),
        Some(CommanderMode::Learned)
    );
    assert_eq!(CommanderMode::Learned.name(), "learned");
}

#[test]
fn the_flat_layout_covers_every_feature_once() {
    let cat = asset_catalogue();
    let m = Match::new(&cat, &carrier_cfg(&cat, [CommanderMode::Learned; 2])).unwrap();
    let f = features(&m, &cat, 1, &CommanderLocks::default());
    let mut flat = Vec::new();
    f.write_flat(&mut flat);
    assert_eq!(flat.len(), FLAT_DIM);
    let mut at = 0;
    for (_, offset, width) in FLAT_LAYOUT {
        assert_eq!(offset, at);
        at += width;
    }
    assert_eq!(at, FLAT_DIM);
    assert_eq!(&flat[..GLOBAL_DIM], &f.globals);
    let (_, off, _) = FLAT_LAYOUT[5];
    for s in 0..N_ENTITIES {
        for c in 0..6 {
            let want = if f.masks.squad[s][c] { 1.0 } else { 0.0 };
            assert_eq!(flat[off + s * 6 + c], want);
        }
    }
    let (_, off, _) = FLAT_LAYOUT[8];
    for s in 0..N_ENTITIES {
        assert_eq!(flat[off + s], if f.masks.ward[s] { 1.0 } else { 0.0 });
    }
}
