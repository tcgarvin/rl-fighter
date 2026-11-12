//! The random commander (`CommanderMode::Random`, v5; SIM_SPEC §5.9): stage B trains
//! pilots to follow *any* order, not just the ones the scripted commander tends to
//! give, so this commander keeps the script's logistics and draws the orders.
//!
//! - **Logistics** are the scripted commander's: its launches and waypoints
//!   (`scripted::commander::commands` without its squad commands), so carriers and
//!   transports fly and hangars empty exactly as under the script.
//! - **Squads.** The first time it commands, it draws, for each of the team's strike
//!   craft slots in slot order (docked reserves too, so they have a squad when they
//!   launch), a squad among the first `RANDOM_SQUADS`, or none with probability
//!   `UNASSIGNED_FRAC`. A ship keeps that squad for the match. Members are the own
//!   strike craft in the match and not docked, plus the reserves launched this slow
//!   tick (as the scripted commander does).
//! - **Orders.** A squad with members draws a new order when its timer runs out (every
//!   `REDRAW_MIN_SLOW_TICKS..=REDRAW_MAX_SLOW_TICKS` slow ticks, drawn each time) or
//!   when its order was cleared because its target or ward is gone: a kind uniform
//!   over none / attack / defend / go-to (v6; v5's guard and hold), then a valid
//!   target. Attack: a uniformly drawn active enemy (capital ships included). Defend:
//!   when the team has an active capital ship, with probability
//!   `DEFEND_CAPITAL_P` a uniformly drawn one of those; otherwise a uniformly drawn
//!   own active ship that is not in the squad (capital ships included). Go-to: a
//!   point near the squad's fight ([`goto_point`]) and a radius in
//!   `[GOTO_RADIUS_MIN, GOTO_RADIUS_MAX)`. A kind with no valid target becomes none.
//! - **Go-to points near the action** (B2b, after the order pilot's run 1, whose holds
//!   were uniform over the disc of `GOTO_POINT_FRAC` R: usually away from the fight, so
//!   following one cost the pilot its fight and was rationally ignored). The point
//!   lies between the squad's centroid and its `GOTO_NEAREST_ENEMIES` nearest enemies,
//!   a fraction in `[GOTO_LERP_MIN, GOTO_LERP_MAX)` of the way, plus a jitter uniform
//!   over a disc of `GOTO_JITTER` m, clamped into the disc of `GOTO_POINT_FRAC` R.
//!   (A squad whose members are all still launching uses its team's active ships.)
//!   With probability `GOTO_FAR_P` (or with no active own ship or enemy) it is
//!   the old uniform draw over that disc instead: the scripted commander's own go-to
//!   points (a convoy's staging and screening points) are not always at the fight,
//!   and a go-to must keep meaning "go to the point", not "go and fight".
//!
//! Its rng is its own: one PCG32 stream per team, seeded from the match seed on
//! streams that differ from the match stream (`RANDOM_COMMAND_STREAMS`), so drawing
//! orders never moves the match rng, and team 1's draws do not depend on whether team
//! 0 is random. Its streams and memory are hashed. Scripted strike pilots follow its
//! orders, as they follow an external commander's (`scripted::orders`).

use crate::command::{Command, MAX_SQUADS, NO_DEADLINE, Order, Squad};
use crate::data::Catalogue;
use crate::hash::{StateHash, StateHasher};
use crate::math::{TAU, Vec2};
use crate::mission::is_capital_ship;
use crate::rng::Pcg32;
use crate::state::{Attach, MAX_SHIPS, Match, NONE, ShipIdx};

use super::commander;

/// Squads the random commander uses (of `MAX_SQUADS`).
pub const RANDOM_SQUADS: usize = 3;
/// Chance that a strike craft is in no squad (no order all match).
pub const UNASSIGNED_FRAC: f32 = 0.15;
/// A squad's order lasts this many slow ticks (inclusive range, drawn per order).
pub const REDRAW_MIN_SLOW_TICKS: u32 = 3;
pub const REDRAW_MAX_SLOW_TICKS: u32 = 8;
/// Go-to points lie within this fraction of the arena radius.
pub const GOTO_POINT_FRAC: f32 = 0.7;
/// Chance that a go-to point is drawn uniformly over the disc of `GOTO_POINT_FRAC` R
/// (a far point) instead of near the squad's fight (module docs).
pub const GOTO_FAR_P: f32 = 0.2;
/// A near go-to point lies this fraction of the way from the squad's centroid to its
/// nearest enemies (uniform in `[MIN, MAX)`).
pub const GOTO_LERP_MIN: f32 = 0.25;
pub const GOTO_LERP_MAX: f32 = 0.75;
/// Jitter of a near go-to point: uniform over a disc of this radius, metres.
pub const GOTO_JITTER: f32 = 60.0;
/// A near go-to point aims at the centroid of this many enemies nearest the squad.
pub const GOTO_NEAREST_ENEMIES: usize = 2;
/// Go-to radius range, metres.
pub const GOTO_RADIUS_MIN: f32 = 70.0;
pub const GOTO_RADIUS_MAX: f32 = 150.0;
/// v6: a defend order wards one of the team's capital ships with this probability
/// when it has one on the field.
pub const DEFEND_CAPITAL_P: f32 = 0.5;
/// PCG stream selectors of team 0's and team 1's draws (not `rng::MATCH_STREAM`).
pub const RANDOM_COMMAND_STREAMS: [u64; 2] = [0x0c0d_e5a1_7e00_0001, 0x0c0d_e5a1_7e00_0002];

const _: () = assert!(RANDOM_SQUADS <= MAX_SQUADS);

/// The random commander's state on `Match` (hashed in field order).
#[derive(Clone, Debug, PartialEq)]
pub struct RandomCommander {
    /// Per team, its own stream.
    pub rng: [Pcg32; 2],
    /// Per team: squads have been drawn.
    pub assigned: [bool; 2],
    /// Per slot: its squad, `NONE` for none (meaningful once its team is assigned).
    pub squad: [u8; MAX_SHIPS],
    /// Per team and squad: the tick from which it draws a new order.
    pub next_draw: [[u32; MAX_SQUADS]; 2],
    /// Per team and squad: the kind it last drew (to notice a cleared order).
    pub drawn: [[u8; MAX_SQUADS]; 2],
}

impl RandomCommander {
    /// The state of a match seeded with `seed`: nothing drawn yet.
    pub fn new(seed: u64) -> RandomCommander {
        RandomCommander {
            rng: RANDOM_COMMAND_STREAMS.map(|stream| Pcg32::with_stream(seed, stream)),
            assigned: [false; 2],
            squad: [NONE; MAX_SHIPS],
            next_draw: [[0; MAX_SQUADS]; 2],
            drawn: [[0; MAX_SQUADS]; 2],
        }
    }
}

impl StateHash for RandomCommander {
    fn hash_into(&self, h: &mut StateHasher) {
        self.rng.hash_into(h);
        self.assigned.hash_into(h);
        self.squad.hash_into(h);
        for team in &self.next_draw {
            team.hash_into(h);
        }
        for team in &self.drawn {
            team.hash_into(h);
        }
    }
}

/// Draw in `0..n` (`n > 0`).
fn below(rng: &mut Pcg32, n: usize) -> usize {
    (rng.next_u32() % n as u32) as usize
}

/// A uniformly drawn slot of `mask`, or `None` if it is empty (no draw then).
fn pick(rng: &mut Pcg32, mask: u32) -> Option<ShipIdx> {
    let n = mask.count_ones() as usize;
    if n == 0 {
        return None;
    }
    let k = below(rng, n);
    (0..32)
        .filter(|&s| mask & (1 << s) != 0)
        .nth(k)
        .map(|s| s as ShipIdx)
}

fn mask_of(m: &Match, keep: impl Fn(usize) -> bool) -> u32 {
    (0..m.ships.len())
        .filter(|&s| keep(s))
        .fold(0, |a, s| a | 1 << s)
}

/// A point uniform over the disc of radius `r` (one `uniform` angle, then one
/// `uniform` radius fraction).
fn uniform_in_disc(rng: &mut Pcg32, r: f32) -> Vec2 {
    let angle = rng.uniform() * TAU;
    Vec2::from_angle(angle) * (r * libm::sqrtf(rng.uniform()))
}

/// Mean position of the active ships of `mask`, `None` if none is active.
fn active_centroid(m: &Match, mask: u32) -> Option<Vec2> {
    let (mut sum, mut n) = (Vec2::ZERO, 0.0f32);
    for (s, ship) in m.ships.iter().enumerate() {
        if mask & (1 << s) != 0 && ship.active() {
            sum += ship.pos;
            n += 1.0;
        }
    }
    (n > 0.0).then(|| sum / n)
}

/// Centroid of the (at most) `GOTO_NEAREST_ENEMIES` active enemies of `team`
/// nearest `from` (ties to the lower slot), `None` with no active enemy.
fn nearest_enemies_centroid(m: &Match, team: u8, from: Vec2) -> Option<Vec2> {
    let mut best: [(f32, usize); GOTO_NEAREST_ENEMIES] = [(f32::INFINITY, 0); GOTO_NEAREST_ENEMIES];
    for (s, ship) in m.ships.iter().enumerate() {
        if ship.team == team || !ship.active() {
            continue;
        }
        let d = (ship.pos - from).length();
        if let Some(k) = best.iter().position(|&(bd, _)| d < bd) {
            best.copy_within(k..GOTO_NEAREST_ENEMIES - 1, k + 1);
            best[k] = (d, s);
        }
    }
    let mask = best
        .iter()
        .filter(|(d, _)| d.is_finite())
        .fold(0u32, |a, &(_, s)| a | 1 << s);
    active_centroid(m, mask)
}

/// A go-to point for a squad of `team` with members `members` (module docs). Draws,
/// in order: one `uniform` (far or near); far: [`uniform_in_disc`]; near: the lerp
/// fraction, then the jitter's [`uniform_in_disc`].
pub fn goto_point(m: &Match, team: u8, members: u32, rng: &mut Pcg32) -> Vec2 {
    let reach = GOTO_POINT_FRAC * m.cfg.arena_radius;
    let far = rng.uniform() < GOTO_FAR_P;
    // Reserves launching this tick are not active yet: the team's ships stand in.
    let own = mask_of(m, |s| m.ships[s].team == team);
    let fight = active_centroid(m, members)
        .or_else(|| active_centroid(m, own))
        .and_then(|squad| nearest_enemies_centroid(m, team, squad).map(|foes| (squad, foes)));
    let Some((squad, foes)) = fight.filter(|_| !far) else {
        return uniform_in_disc(rng, reach);
    };
    let along = rng.range(GOTO_LERP_MIN, GOTO_LERP_MAX);
    let point = squad + (foes - squad) * along + uniform_in_disc(rng, GOTO_JITTER);
    let r = point.length();
    if r > reach {
        point * (reach / r)
    } else {
        point
    }
}

/// A random order for a squad of `team` with members `members` (module docs).
fn draw_order(m: &Match, cat: &Catalogue, team: u8, members: u32, rng: &mut Pcg32) -> Order {
    match below(rng, 4) {
        1 => {
            let foes = mask_of(m, |s| m.ships[s].team != team && m.ships[s].active());
            pick(rng, foes).map_or(Order::None, |target| Order::Attack { target })
        }
        2 => {
            let own = mask_of(m, |s| {
                m.ships[s].team == team && m.ships[s].active() && members & (1 << s) == 0
            });
            let capital = mask_of(m, |s| {
                own & (1 << s) != 0 && is_capital_ship(cat.hull(m.ships[s].hull))
            });
            let pool = if capital != 0 && rng.uniform() < DEFEND_CAPITAL_P {
                capital
            } else {
                own
            };
            pick(rng, pool).map_or(Order::None, |ward| Order::Defend { ward })
        }
        3 => {
            let point = goto_point(m, team, members, rng);
            let radius = rng.range(GOTO_RADIUS_MIN, GOTO_RADIUS_MAX);
            Order::GoTo {
                point,
                radius,
                deadline: NO_DEADLINE,
            }
        }
        _ => Order::None,
    }
}

/// `team`'s commands for this slow tick (module docs). Draws only from `st`, never
/// from the match rng.
pub fn commands(m: &Match, cat: &Catalogue, team: u8, st: &mut RandomCommander) -> Vec<Command> {
    let team = team & 1;
    let t = usize::from(team);
    let mut out: Vec<Command> = commander::commands(m, cat, team)
        .into_iter()
        .filter(|c| !matches!(c, Command::Squad { .. }))
        .collect();
    let strike = |s: usize| m.ships[s].team == team && !is_capital_ship(cat.hull(m.ships[s].hull));
    if !st.assigned[t] {
        for s in 0..m.ships.len() {
            if !strike(s) {
                continue;
            }
            st.squad[s] = if st.rng[t].uniform() < UNASSIGNED_FRAC {
                NONE
            } else {
                below(&mut st.rng[t], RANDOM_SQUADS) as u8
            };
        }
        st.assigned[t] = true;
    }
    // The wing: strike craft in the match and not docked, plus this tick's launches
    // (the first reserves in the hangar, as the scripted commander launches them).
    let launches = out
        .iter()
        .filter(|c| matches!(c, Command::Launch { .. }))
        .count();
    let launched = m.reserves[t]
        .iter()
        .take(launches)
        .fold(0u32, |a, &s| a | 1 << s);
    let wing = mask_of(m, |s| {
        strike(s) && m.in_match(s) && m.ships[s].attach == Attach::None
    }) | launched;
    let current: [Squad; MAX_SQUADS] = m.command.squads[t];
    for (k, cur) in current.iter().enumerate().take(RANDOM_SQUADS) {
        let members = mask_of(m, |s| wing & (1 << s) != 0 && usize::from(st.squad[s]) == k);
        let order = if members == 0 {
            st.drawn[t][k] = 0;
            Order::None
        } else if m.tick >= st.next_draw[t][k] || (st.drawn[t][k] != 0 && cur.order == Order::None)
        {
            let rng = &mut st.rng[t];
            let order = draw_order(m, cat, team, members, rng);
            let span = (REDRAW_MAX_SLOW_TICKS - REDRAW_MIN_SLOW_TICKS + 1) as usize;
            let slow_ticks = REDRAW_MIN_SLOW_TICKS + below(rng, span) as u32;
            st.next_draw[t][k] = m.tick + slow_ticks * crate::command::COMMAND_TICKS;
            st.drawn[t][k] = order.kind();
            order
        } else {
            cur.order
        };
        if members != cur.members || order != cur.order {
            out.push(Command::Squad {
                squad: k as u8,
                members,
                order,
            });
        }
    }
    out
}
