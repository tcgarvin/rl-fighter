//! The learned commander's interface (`docs/COMMANDER.md`, `COMMANDER_IO_VERSION` 1):
//! what one team's commander sees ([`features`]: globals, per-slot entities and every
//! choice mask) and how one decision of `ACTION_DIM` integers becomes [`Command`]s
//! ([`decode`]). Training (the Python env) and the browser (the WASM bridge) share this
//! code, so a network sees and acts on exactly the same thing in both.
//!
//! - **Team frame**: the world frame for team 0, rotated 180 degrees for team 1
//!   (`p -> -p`), so every commander's home side is `-x`. Positions are divided by the
//!   arena radius, velocities by `VEL_SCALE`.
//! - **Entities** are indexed by ship slot (`MAX_SHIPS`); a slot is valid when its ship
//!   is alive and on the field or arriving (not docked, not jumped out).
//! - **Holds** ([`CommanderLocks`]) live beside the match, not in its hashed state, and
//!   reset with the match. A ship whose order a decision changed (through its squad's
//!   order or by moving squad) keeps that order for `HOLD_DECISIONS` decisions: it
//!   cannot move squad, and its squad's order cannot change, until the hold ends. A
//!   hold ends early when its order is spent ([`ship_hold_left`]): the attack target
//!   or the ward is gone, or the ship has arrived at its go-to point.
//! - **Masks** are computed from the state before the decision. [`decode`] applies them
//!   itself: a choice its mask forbids reads as "keep" (or "hold"), so a decision can
//!   never do what its masks do not allow. A value outside its head's range is an
//!   error ([`DecodeError`]).
//!
//! Nothing here changes the match; a learned team's commands reach it through
//! `Match::submit_command` and apply on the team's slow tick (`LEARNED_COMMAND_TICKS`).

use crate::TICK_HZ;
use crate::command::{Command, MAX_SQUADS, NO_DEADLINE, Order, Waypoint};
use crate::data::{Catalogue, HullId};
use crate::math::{PI, Vec2};
use crate::mission::{JumpState, Mission, MissionKind, is_capital_ship};
use crate::order::{N_HULL_CLASSES, effective_order};
use crate::state::{Attach, MAX_BAYS, MAX_SHIPS, Match, NONE, ShipIdx};

/// Version of this interface: any change to a layout below bumps it.
pub const COMMANDER_IO_VERSION: u32 = 1;
/// Entities, one per ship slot.
pub const N_ENTITIES: usize = MAX_SHIPS;
/// Floats per entity.
pub const ENTITY_DIM: usize = 40;
/// Floats of globals.
pub const GLOBAL_DIM: usize = 53;
/// Integers in one decision.
pub const ACTION_DIM: usize = 40;
/// Map points (go-to points and carrier waypoints).
pub const N_POINTS: usize = 25;
/// Decisions from one change of a ship's order to the next one allowed: a ship keeps
/// an order for at least this many decisions (5 s at the learned cadence) unless the
/// order is spent first.
pub const HOLD_DECISIONS: u32 = 5;
/// Radius of a go-to order (m).
pub const GOTO_RADIUS: f32 = 60.0;
/// Velocities are divided by this (m/s).
pub const VEL_SCALE: f32 = 100.0;
/// Map point radii as fractions of the arena radius (ring `r` of points `1 + 8 r + b`).
pub const POINT_RADII: [f32; 3] = [0.3, 0.6, 0.85];
/// Bearings per ring, `45` degrees apart, counter-clockwise from `+x`.
pub const POINT_BEARINGS: usize = 8;
/// Strike hulls with a launch head: the first three `HULL_CLASSES` (fighter, strafer,
/// gunship).
pub const N_LAUNCH_HULLS: usize = 3;
/// Carrier waypoint choices: keep, then each map point.
pub const N_WAYPOINT_CHOICES: usize = 1 + N_POINTS;
/// Squad choices of a ship: keep, no squad, squads 1-4.
pub const N_SQUAD_CHOICES: usize = 2 + MAX_SQUADS;
/// Order choices of a squad: keep, none, attack, defend, go-to.
pub const N_ORDER_CHOICES: usize = 5;
/// Globals per squad.
pub const SQUAD_GLOBALS: usize = 8;
/// Scales of the counts in the globals.
pub const RESERVE_SCALE: f32 = 8.0;
pub const SQUAD_SIZE_SCALE: f32 = 8.0;
pub const STRIKE_COUNT_SCALE: f32 = 10.0;
/// Seconds since the last launch are divided by this and capped at 1.
pub const LAUNCH_AGE_SCALE_S: f32 = 20.0;

const _: () = assert!(1 + POINT_RADII.len() * POINT_BEARINGS == N_POINTS);
const _: () = assert!(N_LAUNCH_HULLS <= N_HULL_CLASSES);

/// Offsets of the action heads (`docs/COMMANDER.md` "Outputs").
pub mod act {
    use super::{MAX_SQUADS, N_ENTITIES, N_LAUNCH_HULLS};
    /// Launch per strike hull: 0 hold, 1 launch one.
    pub const LAUNCH: usize = 0;
    /// Carrier waypoint: 0 keep, 1-25 map point.
    pub const WAYPOINT: usize = LAUNCH + N_LAUNCH_HULLS;
    /// Squad of slot s: 0 keep, 1 no squad, 2-5 squad 1-4.
    pub const SQUAD: usize = WAYPOINT + 1;
    /// Order of squad k: 0 keep, 1 none, 2 attack, 3 defend, 4 go-to.
    pub const ORDER: usize = SQUAD + N_ENTITIES;
    /// Attack target of squad k: a ship slot.
    pub const TARGET: usize = ORDER + MAX_SQUADS;
    /// Defend ward of squad k: a ship slot.
    pub const WARD: usize = TARGET + MAX_SQUADS;
    /// Go-to point of squad k: a map point.
    pub const POINT: usize = WARD + MAX_SQUADS;
    pub const END: usize = POINT + MAX_SQUADS;
}
const _: () = assert!(act::END == ACTION_DIM);

/// Offsets within an entity (`docs/COMMANDER.md` "Entity features").
pub mod ent {
    pub const VALID: usize = 0;
    pub const OWN: usize = 1;
    /// Hull class one-hot (`HULL_CLASSES`), 6.
    pub const CLASS: usize = 2;
    pub const POS: usize = 8;
    pub const VEL: usize = 10;
    pub const HEADING: usize = 12;
    pub const HULL: usize = 14;
    pub const SHIELD: usize = 15;
    pub const ON_FIELD: usize = 16;
    pub const ARRIVING: usize = 17;
    pub const CHARGING: usize = 18;
    /// Own strike craft: squad one-hot (none, 1-4), 5.
    pub const SQUAD: usize = 19;
    /// Own strike craft: effective order kind one-hot (none, attack, defend, go-to), 4.
    pub const ORDER: usize = 24;
    /// Attack target of my squad k, 4.
    pub const TARGET_OF: usize = 28;
    /// Defend ward of my squad k, 4.
    pub const WARD_OF: usize = 32;
    pub const THREAT: usize = 36;
    pub const DIST_OWN: usize = 37;
    pub const DIST_ENEMY: usize = 38;
    pub const SHIP_HOLD: usize = 39;
}
const _: () = assert!(ent::SHIP_HOLD + 1 == ENTITY_DIM);

/// Offsets within the globals (`docs/COMMANDER.md` "Globals").
pub mod glob {
    /// Role one-hot: deathmatch, carrier battle, convoy defender, convoy attacker.
    pub const ROLE: usize = 0;
    pub const TIME_LEFT: usize = 4;
    pub const TICK: usize = 5;
    /// Hangar reserves by strike hull, 3.
    pub const RESERVES: usize = 6;
    pub const BAYS_READY: usize = 9;
    pub const BAYS: usize = 10;
    pub const CARRIER: usize = 11;
    pub const ENEMY_CARRIER: usize = 12;
    /// Convoy: escaped, destroyed, needed to escape, needed to destroy, charging.
    pub const CONVOY: usize = 13;
    /// Per squad, `SQUAD_GLOBALS` each: size, order kind one-hot (4), hold left,
    /// go-to point x, y.
    pub const SQUADS: usize = 18;
    pub const OWN_STRIKE: usize = 50;
    pub const ENEMY_STRIKE: usize = 51;
    pub const LAUNCH_AGE: usize = 52;
}
const _: () = assert!(glob::SQUADS + MAX_SQUADS * SQUAD_GLOBALS == glob::OWN_STRIKE);
const _: () = assert!(glob::LAUNCH_AGE + 1 == GLOBAL_DIM);

/// The flat layout of [`CommanderFeatures::write_flat`] (the browser's
/// `commander_features`): `(name, offset, width)` in order. Masks are 0/1.
pub const FLAT_LAYOUT: [(&str, usize, usize); 9] = [
    ("globals", 0, GLOBAL_DIM),
    ("entities", GLOBAL_DIM, N_ENTITIES * ENTITY_DIM),
    ("valid", GLOBAL_DIM + N_ENTITIES * ENTITY_DIM, N_ENTITIES),
    ("launch_mask", FLAT_LAUNCH, N_LAUNCH_HULLS),
    (
        "waypoint_mask",
        FLAT_LAUNCH + N_LAUNCH_HULLS,
        N_WAYPOINT_CHOICES,
    ),
    ("squad_mask", FLAT_SQUAD, N_ENTITIES * N_SQUAD_CHOICES),
    ("order_mask", FLAT_ORDER, MAX_SQUADS * N_ORDER_CHOICES),
    (
        "target_mask",
        FLAT_ORDER + MAX_SQUADS * N_ORDER_CHOICES,
        N_ENTITIES,
    ),
    ("ward_mask", FLAT_DIM - N_ENTITIES, N_ENTITIES),
];
const FLAT_LAUNCH: usize = GLOBAL_DIM + N_ENTITIES * ENTITY_DIM + N_ENTITIES;
const FLAT_SQUAD: usize = FLAT_LAUNCH + N_LAUNCH_HULLS + N_WAYPOINT_CHOICES;
const FLAT_ORDER: usize = FLAT_SQUAD + N_ENTITIES * N_SQUAD_CHOICES;
/// Floats of [`CommanderFeatures::write_flat`].
pub const FLAT_DIM: usize = FLAT_ORDER + MAX_SQUADS * N_ORDER_CHOICES + 2 * N_ENTITIES;
const _: () = assert!(FLAT_DIM == 1082);

/// One team's hold state (module docs): kept beside the match, not hashed, reset with
/// the match. Hold ends count decisions: a hold set while decoding decision `n` lasts
/// through decisions `n + 1 ..= n + HOLD_DECISIONS - 1`, so the ship's order may change
/// again at decision `n + HOLD_DECISIONS`.
#[derive(Clone, Debug, Default, PartialEq, Eq)]
pub struct CommanderLocks {
    /// Decisions decoded so far this match.
    pub decisions: u32,
    /// Per slot: the first decision the ship's order may change again.
    pub ship_hold_end: [u32; MAX_SHIPS],
    /// Per slot: `Order::kind` of the order the hold was set with (0 none).
    pub ship_hold_kind: [u8; MAX_SHIPS],
    /// Per slot: the match tick the hold was set at (the decision's, one before the
    /// slow tick that applies it).
    pub ship_hold_tick: [u32; MAX_SHIPS],
    /// Ships whose order the last decoded decision changed.
    pub changed_ships: u32,
    /// The slow tick of the team's last launch decision, `None` before the first.
    pub last_launch_tick: Option<u32>,
}

/// Decisions until slot `s`'s order may change again (0: it may now), counting the
/// next one. A hold whose order is spent is over: once the decision that set it has
/// applied, a ship given an attack, defend or go-to order whose effective order is
/// none (the target or ward is gone, it has arrived, or, v8, it has missed the go-to's
/// deadline) is free at once.
pub fn ship_hold_left(m: &Match, locks: &CommanderLocks, s: usize) -> u32 {
    let left = locks.ship_hold_end[s].saturating_sub(locks.decisions);
    if left == 0 || s >= m.ships.len() {
        return 0;
    }
    let spent = locks.ship_hold_kind[s] != 0
        && m.tick > locks.ship_hold_tick[s]
        && effective_order(m, s).kind() == 0;
    if spent { 0 } else { left }
}

/// `team`'s strike craft in the match, as a slot mask: the ships a squad can hold.
fn strike_mask(m: &Match, cat: &Catalogue, team: u8) -> u32 {
    (0..m.ships.len())
        .filter(|&s| m.ships[s].team == team && m.in_match(s) && is_strike(m, cat, s))
        .fold(0u32, |acc, s| acc | 1 << s)
}

/// Decisions until squad `k` of `team` may take a new order (0: it may now): the
/// longest hold left among its members.
pub fn squad_hold_left(
    m: &Match,
    cat: &Catalogue,
    team: u8,
    locks: &CommanderLocks,
    k: usize,
) -> u32 {
    let team = team & 1;
    let members = m.command.squads[usize::from(team)][k].members & strike_mask(m, cat, team);
    (0..m.ships.len())
        .filter(|&s| members & (1 << s) != 0)
        .map(|s| ship_hold_left(m, locks, s))
        .max()
        .unwrap_or(0)
}

/// Which choice of each head is allowed (`docs/COMMANDER.md` "Masks"). "Keep" and
/// "hold" (choice 0) are always allowed.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CommanderMasks {
    /// Per strike hull: a launch is allowed (hold always is).
    pub launch: [bool; N_LAUNCH_HULLS],
    pub waypoint: [bool; N_WAYPOINT_CHOICES],
    pub squad: [[bool; N_SQUAD_CHOICES]; N_ENTITIES],
    pub order: [[bool; N_ORDER_CHOICES]; MAX_SQUADS],
    pub target: [bool; N_ENTITIES],
    pub ward: [bool; N_ENTITIES],
}

/// One team's commander inputs (module docs).
#[derive(Clone, Debug, PartialEq)]
pub struct CommanderFeatures {
    pub globals: [f32; GLOBAL_DIM],
    pub entities: [[f32; ENTITY_DIM]; N_ENTITIES],
    pub valid: [bool; N_ENTITIES],
    pub masks: CommanderMasks,
}

impl CommanderFeatures {
    /// Append the [`FLAT_LAYOUT`] encoding (`FLAT_DIM` floats, masks 0/1) to `out`.
    pub fn write_flat(&self, out: &mut Vec<f32>) {
        let b = |v: bool| if v { 1.0 } else { 0.0 };
        out.reserve(FLAT_DIM);
        out.extend_from_slice(&self.globals);
        for e in &self.entities {
            out.extend_from_slice(e);
        }
        let k = &self.masks;
        out.extend(self.valid.iter().map(|&v| b(v)));
        out.extend(k.launch.iter().map(|&v| b(v)));
        out.extend(k.waypoint.iter().map(|&v| b(v)));
        out.extend(k.squad.iter().flatten().map(|&v| b(v)));
        out.extend(k.order.iter().flatten().map(|&v| b(v)));
        out.extend(k.target.iter().map(|&v| b(v)));
        out.extend(k.ward.iter().map(|&v| b(v)));
    }
}

/// Why a decision could not be decoded.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum DecodeError {
    /// The decision does not have `ACTION_DIM` values.
    Length { len: usize },
    /// `action[index]` is outside its head's choices `0..choices`.
    OutOfRange {
        index: usize,
        value: i32,
        choices: usize,
    },
}

impl std::fmt::Display for DecodeError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match *self {
            DecodeError::Length { len } => {
                write!(f, "a commander decision has {ACTION_DIM} values, got {len}")
            }
            DecodeError::OutOfRange {
                index,
                value,
                choices,
            } => write!(
                f,
                "commander action[{index}] = {value} is outside 0..{choices}"
            ),
        }
    }
}

impl std::error::Error for DecodeError {}

/// Choices of head `index` of a decision.
pub fn head_choices(index: usize) -> usize {
    match index {
        i if i < act::WAYPOINT => 2,
        i if i < act::SQUAD => N_WAYPOINT_CHOICES,
        i if i < act::ORDER => N_SQUAD_CHOICES,
        i if i < act::TARGET => N_ORDER_CHOICES,
        i if i < act::POINT => N_ENTITIES,
        _ => N_POINTS,
    }
}

/// Check that `action` has `ACTION_DIM` values, each within its head's choices.
pub fn validate_action(action: &[i32]) -> Result<(), DecodeError> {
    if action.len() != ACTION_DIM {
        return Err(DecodeError::Length { len: action.len() });
    }
    for (index, &value) in action.iter().enumerate() {
        let choices = head_choices(index);
        if !(0..choices as i32).contains(&value) {
            return Err(DecodeError::OutOfRange {
                index,
                value,
                choices,
            });
        }
    }
    Ok(())
}

/// `+1` for team 0, `-1` for team 1: the team frame is `p -> sign * p`.
pub fn frame_sign(team: u8) -> f32 {
    if team & 1 == 0 { 1.0 } else { -1.0 }
}

/// Map point `k` (`0..N_POINTS`) in the team frame, as a fraction of the arena radius:
/// 0 the centre, `1 + 8 r + b` at radius `POINT_RADII[r]` and bearing `45 b` degrees.
pub fn map_point_unit(k: usize) -> Vec2 {
    if k == 0 {
        return Vec2::ZERO;
    }
    let (r, b) = ((k - 1) / POINT_BEARINGS, (k - 1) % POINT_BEARINGS);
    Vec2::from_angle(b as f32 * (PI / 4.0)) * POINT_RADII[r]
}

/// Map point `k` of `team` in the world frame, metres.
pub fn map_point(team: u8, k: usize, arena_radius: f32) -> Vec2 {
    map_point_unit(k) * (frame_sign(team) * arena_radius)
}

/// A slot that is an entity: alive and on the field or arriving.
fn is_entity(m: &Match, s: usize) -> bool {
    m.in_match(s) && m.ships[s].attach != Attach::Docked
}

fn is_strike(m: &Match, cat: &Catalogue, s: usize) -> bool {
    !is_capital_ship(cat.hull(m.ships[s].hull))
}

/// `team`'s carrier slot if it is alive.
fn live_carrier(m: &Match, team: u8) -> Option<usize> {
    let c = m.mission.carrier[usize::from(team & 1)];
    (c != NONE && m.ships[usize::from(c)].active()).then_some(usize::from(c))
}

/// `team`'s transport furthest along the route (ties to the lower slot), on the field.
fn lead_transport(m: &Match, team: u8) -> Option<usize> {
    let Mission::ConvoyEscort(ce) = &m.cfg.mission else {
        return None;
    };
    (0..m.ships.len())
        .filter(|&s| {
            m.mission.transports & (1 << s) != 0
                && m.ships[s].team == team & 1
                && m.ships[s].active()
        })
        .max_by(|&a, &b| {
            ce.progress(m.ships[a].pos)
                .total_cmp(&ce.progress(m.ships[b].pos))
                .then(b.cmp(&a))
        })
}

/// What distances in entity features 37 and 38 are measured to for `team`: its live
/// carrier, else its lead transport.
fn reference_ship(m: &Match, team: u8) -> Option<usize> {
    live_carrier(m, team).or_else(|| lead_transport(m, team))
}

/// Bays of `team`'s live carrier ready on the coming slow tick (`tick + 1`, when a
/// launch decided now applies), and its bay count (0 without a carrier).
fn bays(m: &Match, cat: &Catalogue, team: u8) -> (usize, usize) {
    let t = usize::from(team & 1);
    let c = m.mission.carrier[t];
    if c == NONE {
        return (0, 0);
    }
    let n = cat.hull(m.ships[usize::from(c)].hull).bays.len();
    if live_carrier(m, team).is_none() {
        return (0, n);
    }
    let ready = (0..n)
        .filter(|&b| m.tick + 1 >= m.mission.bay_ready[t][b])
        .count();
    (ready, n)
}

/// `team`'s docked reserves by obs hull class (launch order kept within a class).
fn reserve_counts(m: &Match, team: u8) -> [usize; N_HULL_CLASSES] {
    let mut out = [0; N_HULL_CLASSES];
    for &s in m.hangar(team) {
        out[usize::from(m.ship_class[usize::from(s)])] += 1;
    }
    out
}

/// The masks of `team`'s next decision (`docs/COMMANDER.md` "Masks").
pub fn masks(m: &Match, cat: &Catalogue, team: u8, locks: &CommanderLocks) -> CommanderMasks {
    let team = team & 1;
    let n = m.ships.len();
    let carrier_up = live_carrier(m, team).is_some();
    let (ready, _) = bays(m, cat, team);
    let reserves = reserve_counts(m, team);
    let mut out = CommanderMasks {
        launch: [false; N_LAUNCH_HULLS],
        waypoint: [carrier_up; N_WAYPOINT_CHOICES],
        squad: [[false; N_SQUAD_CHOICES]; N_ENTITIES],
        order: [[false; N_ORDER_CHOICES]; MAX_SQUADS],
        target: [false; N_ENTITIES],
        ward: [false; N_ENTITIES],
    };
    out.waypoint[0] = true;
    for (h, allowed) in out.launch.iter_mut().enumerate() {
        *allowed = carrier_up && ready > 0 && reserves[h] > 0;
    }
    let mut any_strike = false;
    for s in 0..N_ENTITIES {
        out.squad[s][0] = true;
        if s >= n {
            continue;
        }
        let ship = &m.ships[s];
        if ship.team == team && is_entity(m, s) && is_strike(m, cat, s) {
            any_strike = true;
            if ship_hold_left(m, locks, s) == 0 {
                out.squad[s] = [true; N_SQUAD_CHOICES];
            }
        }
        if ship.active() {
            out.target[s] = ship.team != team;
            out.ward[s] = ship.team == team;
        }
    }
    let enemy_on_field = out.target.iter().any(|&t| t);
    let own_on_field = out.ward.iter().any(|&w| w);
    for (k, row) in out.order.iter_mut().enumerate() {
        row[0] = true;
        if any_strike && squad_hold_left(m, cat, team, locks, k) == 0 {
            row[1] = true;
            row[2] = enemy_on_field;
            row[3] = own_on_field;
            row[4] = true;
        }
    }
    out
}

/// `team`'s commander inputs now (`docs/COMMANDER.md` "Inputs"), with the masks of its
/// next decision.
pub fn features(m: &Match, cat: &Catalogue, team: u8, locks: &CommanderLocks) -> CommanderFeatures {
    let team = team & 1;
    let t = usize::from(team);
    let sign = frame_sign(team);
    let radius = m.cfg.arena_radius;
    let n = m.ships.len();
    let squads = &m.command.squads[t];
    let mut out = CommanderFeatures {
        globals: [0.0; GLOBAL_DIM],
        entities: [[0.0; ENTITY_DIM]; N_ENTITIES],
        valid: [false; N_ENTITIES],
        masks: masks(m, cat, team, locks),
    };

    // Enemies in the threat set of any of my capital ships on the field.
    let active = m.active_mask();
    let threats = (0..n)
        .filter(|&s| m.ships[s].team == team && m.ships[s].active() && !is_strike(m, cat, s))
        .fold(0u32, |acc, c| acc | m.threat_set(cat, c, active));
    let own_ref = reference_ship(m, team).map(|s| m.ships[s].pos);
    let enemy_ref = reference_ship(m, 1 - team).map(|s| m.ships[s].pos);
    let dist = |p: Vec2, r: Option<Vec2>| r.map_or(0.0, |q| (p - q).length() / radius);

    for s in 0..n {
        if !is_entity(m, s) {
            continue;
        }
        let ship = &m.ships[s];
        let hull = cat.hull(ship.hull);
        let own = ship.team == team;
        let e = &mut out.entities[s];
        out.valid[s] = true;
        e[ent::VALID] = 1.0;
        e[ent::OWN] = if own { 1.0 } else { 0.0 };
        e[ent::CLASS + usize::from(m.ship_class[s])] = 1.0;
        let pos = ship.pos * (sign / radius);
        let vel = ship.vel * (sign / VEL_SCALE);
        let heading = Vec2::from_angle(ship.heading) * sign;
        e[ent::POS] = pos.x;
        e[ent::POS + 1] = pos.y;
        e[ent::VEL] = vel.x;
        e[ent::VEL + 1] = vel.y;
        e[ent::HEADING] = heading.x;
        e[ent::HEADING + 1] = heading.y;
        e[ent::HULL] = ship.hp / hull.hp;
        e[ent::SHIELD] = hull.shield.map_or(0.0, |sh| {
            if sh.hp > 0.0 {
                ship.shield / sh.hp
            } else {
                0.0
            }
        });
        e[ent::ON_FIELD] = if ship.present { 1.0 } else { 0.0 };
        e[ent::ARRIVING] = if ship.present { 0.0 } else { 1.0 };
        e[ent::CHARGING] = if matches!(m.mission.jump[s], JumpState::Charging { .. }) {
            1.0
        } else {
            0.0
        };
        if own && is_strike(m, cat, s) {
            let squad = squads
                .iter()
                .position(|q| q.contains(s))
                .map_or(0, |k| k + 1);
            e[ent::SQUAD + squad] = 1.0;
            e[ent::ORDER + usize::from(effective_order(m, s).kind())] = 1.0;
            e[ent::SHIP_HOLD] = ship_hold_left(m, locks, s) as f32 / HOLD_DECISIONS as f32;
        }
        for (k, q) in squads.iter().enumerate() {
            match q.order {
                Order::Attack { target } if usize::from(target) == s => {
                    e[ent::TARGET_OF + k] = 1.0;
                }
                Order::Defend { ward } if usize::from(ward) == s => e[ent::WARD_OF + k] = 1.0,
                _ => {}
            }
        }
        if !own && threats & (1 << s) != 0 {
            e[ent::THREAT] = 1.0;
        }
        e[ent::DIST_OWN] = dist(ship.pos, own_ref);
        e[ent::DIST_ENEMY] = dist(ship.pos, enemy_ref);
    }

    let g = &mut out.globals;
    let role = match m.cfg.mission.kind() {
        MissionKind::Deathmatch => 0,
        MissionKind::CarrierBattle => 1,
        MissionKind::ConvoyEscort => 2 + t,
    };
    g[glob::ROLE + role] = 1.0;
    let limit = m.cfg.time_limit_ticks as f32;
    g[glob::TIME_LEFT] = m.cfg.time_limit_ticks.saturating_sub(m.tick) as f32 / limit;
    g[glob::TICK] = m.tick as f32 / limit;
    let reserves = reserve_counts(m, team);
    for h in 0..N_LAUNCH_HULLS {
        g[glob::RESERVES + h] = reserves[h] as f32 / RESERVE_SCALE;
    }
    let (ready, n_bays) = bays(m, cat, team);
    g[glob::BAYS_READY] = ready as f32 / MAX_BAYS as f32;
    g[glob::BAYS] = n_bays as f32 / MAX_BAYS as f32;
    g[glob::CARRIER] = if live_carrier(m, team).is_some() {
        1.0
    } else {
        0.0
    };
    g[glob::ENEMY_CARRIER] = if live_carrier(m, 1 - team).is_some() {
        1.0
    } else {
        0.0
    };
    let c = m.convoy_status();
    if c.total > 0 {
        let total = f32::from(c.total);
        let counts = [
            c.escaped,
            c.destroyed,
            c.to_escape,
            c.to_destroy,
            c.charging,
        ];
        for (i, &v) in counts.iter().enumerate() {
            g[glob::CONVOY + i] = f32::from(v) / total;
        }
    }
    for (k, q) in squads.iter().enumerate() {
        let base = glob::SQUADS + k * SQUAD_GLOBALS;
        let size = (0..n).filter(|&s| q.contains(s) && is_entity(m, s)).count();
        g[base] = size as f32 / SQUAD_SIZE_SCALE;
        g[base + 1 + usize::from(q.order.kind())] = 1.0;
        g[base + 5] = squad_hold_left(m, cat, team, locks, k) as f32 / HOLD_DECISIONS as f32;
        if let Order::GoTo { point, .. } = q.order {
            let p = point * (sign / radius);
            g[base + 6] = p.x;
            g[base + 7] = p.y;
        }
    }
    let strike_on_field = |own: bool| {
        (0..n)
            .filter(|&s| {
                (m.ships[s].team == team) == own && m.ships[s].active() && is_strike(m, cat, s)
            })
            .count() as f32
            / STRIKE_COUNT_SCALE
    };
    g[glob::OWN_STRIKE] = strike_on_field(true);
    g[glob::ENEMY_STRIKE] = strike_on_field(false);
    g[glob::LAUNCH_AGE] = locks.last_launch_tick.map_or(1.0, |at| {
        let secs = m.tick.saturating_sub(at) as f32 / TICK_HZ;
        (secs / LAUNCH_AGE_SCALE_S).min(1.0)
    });
    out
}

/// The hull of `team`'s first docked reserve of obs class `class`.
fn reserve_hull(m: &Match, team: u8, class: usize) -> Option<HullId> {
    m.hangar(team)
        .iter()
        .find(|&&s| usize::from(m.ship_class[usize::from(s)]) == class)
        .map(|&s| m.ships[usize::from(s)].hull)
}

/// Turn `team`'s decision `action` (`ACTION_DIM` values) into commands and update its
/// `locks` (`docs/COMMANDER.md` "Decoding"): apply the squad moves to get each squad's
/// members, then each squad's order, then a `Command::Squad` for every squad whose
/// members or order changed (in squad order), then the carrier waypoint, then the
/// launches (fighter, strafer, gunship). The masks are those of the state now: a choice
/// they forbid reads as keep or hold. A squad that ends the decision empty takes no new
/// order. Every ship whose order the decision changed (its squad's order before against
/// after, none without a squad) starts a hold of `HOLD_DECISIONS`, and
/// `locks.changed_ships` counts them. Re-issuing a squad's current order, or moving a
/// ship between squads with the same order, changes no ship's order and sets no hold.
/// A decision with any launch sets `locks.last_launch_tick` to the coming slow tick
/// (`tick + 1`). The commands apply when submitted (`Match::submit_command`) before the
/// team's slow tick.
pub fn decode(
    m: &Match,
    cat: &Catalogue,
    team: u8,
    locks: &mut CommanderLocks,
    action: &[i32],
) -> Result<Vec<Command>, DecodeError> {
    validate_action(action)?;
    let team = team & 1;
    let t = usize::from(team);
    let n = m.ships.len();
    let allowed = masks(m, cat, team, locks);
    let choice = |i: usize| action[i] as usize;

    // Squad members now, without the ships the slow tick will drop anyway.
    let eligible = strike_mask(m, cat, team);
    let squads = &m.command.squads[t];
    let before: [u32; MAX_SQUADS] = std::array::from_fn(|k| squads[k].members & eligible);
    let mut members = before;
    for s in 0..N_ENTITIES {
        let c = choice(act::SQUAD + s);
        if c == 0 || !allowed.squad[s][c] {
            continue;
        }
        let now = members.iter().position(|&q| q & (1 << s) != 0);
        let next = c.checked_sub(2);
        if now == next {
            continue;
        }
        for q in members.iter_mut() {
            *q &= !(1 << s);
        }
        if let Some(k) = next {
            members[k] |= 1 << s;
        }
    }

    let radius = m.cfg.arena_radius;
    let mut orders: [Order; MAX_SQUADS] = std::array::from_fn(|k| squads[k].order);
    let mut order_changed = [false; MAX_SQUADS];
    for k in 0..MAX_SQUADS {
        let c = choice(act::ORDER + k);
        if c == 0 || !allowed.order[k][c] || members[k] == 0 {
            continue;
        }
        let order = match c {
            1 => Order::None,
            2 => {
                let target = choice(act::TARGET + k);
                if !allowed.target[target] {
                    continue;
                }
                Order::Attack {
                    target: target as ShipIdx,
                }
            }
            3 => {
                let ward = choice(act::WARD + k);
                if !allowed.ward[ward] {
                    continue;
                }
                Order::Defend {
                    ward: ward as ShipIdx,
                }
            }
            _ => Order::GoTo {
                point: map_point(team, choice(act::POINT + k), radius),
                radius: GOTO_RADIUS,
                deadline: NO_DEADLINE,
            },
        };
        if order == orders[k] {
            continue;
        }
        orders[k] = order;
        order_changed[k] = true;
    }

    // Hold every ship whose own order this decision changed.
    let order_of = |sets: &[u32; MAX_SQUADS], of: &dyn Fn(usize) -> Order, s: usize| {
        sets.iter()
            .position(|&q| q & (1 << s) != 0)
            .map_or(Order::None, of)
    };
    locks.changed_ships = 0;
    for s in (0..n).filter(|&s| eligible & (1 << s) != 0) {
        let old = order_of(&before, &|k| squads[k].order, s);
        let new = order_of(&members, &|k| orders[k], s);
        if old == new {
            continue;
        }
        locks.ship_hold_end[s] = locks.decisions + HOLD_DECISIONS;
        locks.ship_hold_kind[s] = new.kind();
        locks.ship_hold_tick[s] = m.tick;
        locks.changed_ships += 1;
    }

    let mut out = Vec::new();
    for k in 0..MAX_SQUADS {
        if members[k] != before[k] || order_changed[k] {
            out.push(Command::Squad {
                squad: k as u8,
                members: members[k],
                order: orders[k],
            });
        }
    }
    let wp = choice(act::WAYPOINT);
    if wp != 0 && allowed.waypoint[wp] {
        let carrier = m.mission.carrier[t];
        out.push(Command::Waypoint {
            ship: carrier,
            waypoint: Waypoint::At(map_point(team, wp - 1, radius)),
        });
    }
    let mut launched = false;
    for h in 0..N_LAUNCH_HULLS {
        if choice(act::LAUNCH + h) == 1 && allowed.launch[h] {
            let hull = reserve_hull(m, team, h);
            debug_assert!(hull.is_some(), "the launch mask needs a reserve");
            out.push(Command::Launch { hull, bay: None });
            launched = true;
        }
    }
    if launched {
        locks.last_launch_tick = Some(m.tick + 1);
    }
    locks.decisions += 1;
    Ok(out)
}

/// [`decode`] `action` and queue its commands for `team`'s next slow tick; returns how
/// many were queued.
pub fn submit(
    m: &mut Match,
    cat: &Catalogue,
    team: u8,
    locks: &mut CommanderLocks,
    action: &[i32],
) -> Result<usize, DecodeError> {
    let cmds = decode(m, cat, team, locks, action)?;
    for &c in &cmds {
        m.submit_command(team, c);
    }
    Ok(cmds.len())
}
