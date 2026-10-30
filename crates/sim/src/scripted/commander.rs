//! The scripted commander (`CommanderMode::Scripted`), run by the sim inside `step`
//! on every slow tick so the browser and training share it (SIM_SPEC §5.9).
//!
//! **Stub (WP-S1)**, enough to play every mission end to end; WP-S2 replaces the body
//! of [`commands`] with the real script (guard and strike squads, launch timing,
//! steering the carrier):
//!
//! 1. Launch: while the team has fewer than `STUB_WING_IN_SPACE` strike craft on the
//!    field or on their way in, ask for one launch per carrier bay (any hull, any
//!    bay; the sim refuses what it cannot do).
//! 2. One squad (index 0) of every strike craft still in the match, docked reserves
//!    included, ordered to attack the enemy capital ship nearest the team's anchor
//!    (its carrier, else its lead transport, else the centroid of its ships on the
//!    field), else the nearest enemy ship; no order with no enemy in sight.
//! 3. Waypoints: transports to the convoy's jump point (setup already set it; the
//!    stub reasserts it). The carrier keeps the hold point setup gave it until its
//!    wing is spent (no strike craft left in space, on the way in or in the hangar);
//!    then it closes on the enemy carrier for a flak duel, so a battle of attrition
//!    still ends in a carrier kill rather than the clock.

use crate::command::{Command, Order, Waypoint};
use crate::data::Catalogue;
use crate::math::Vec2;
use crate::mission::{Mission, is_capital_ship, is_transport};
use crate::state::{Attach, Match, NONE, ShipIdx};

/// Strike craft the stub keeps in space before it launches more.
pub const STUB_WING_IN_SPACE: usize = 6;

/// The point the team measures "nearest" from.
fn anchor(m: &Match, cat: &Catalogue, team: u8) -> Vec2 {
    let carrier = m.mission.carrier[usize::from(team)];
    if carrier != NONE && m.ships[usize::from(carrier)].active() {
        return m.ships[usize::from(carrier)].pos;
    }
    if let Some(lead) = m
        .ships
        .iter()
        .find(|s| s.team == team && s.active() && is_transport(cat.hull(s.hull)))
    {
        return lead.pos;
    }
    let (mut sum, mut n) = (Vec2::ZERO, 0.0f32);
    for s in m.ships.iter().filter(|s| s.team == team && s.active()) {
        sum += s.pos;
        n += 1.0;
    }
    if n > 0.0 { sum / n } else { Vec2::ZERO }
}

/// Nearest active enemy of `team` to `from` that passes `filter`; ties to the lower
/// slot.
fn nearest(
    m: &Match,
    cat: &Catalogue,
    team: u8,
    from: Vec2,
    capital_only: bool,
) -> Option<ShipIdx> {
    let mut best = None;
    let mut best_d = f32::INFINITY;
    for s in &m.ships {
        if s.team == team || !s.active() || (capital_only && !is_capital_ship(cat.hull(s.hull))) {
            continue;
        }
        let d = (s.pos - from).length();
        if d < best_d {
            best_d = d;
            best = Some(s.slot);
        }
    }
    best
}

/// The commands of `team` for this slow tick (module docs).
pub fn commands(m: &Match, cat: &Catalogue, team: u8) -> Vec<Command> {
    let mut out = Vec::new();
    let t = usize::from(team);

    let carrier = m.mission.carrier[t];
    if carrier != NONE && m.ships[usize::from(carrier)].active() {
        let wing = m
            .ships
            .iter()
            .enumerate()
            .filter(|(i, s)| {
                s.team == team
                    && m.in_match(*i)
                    && s.attach == Attach::None
                    && !is_capital_ship(cat.hull(s.hull))
            })
            .count();
        let bays = cat.hull(m.ships[usize::from(carrier)].hull).bays.len();
        let want = STUB_WING_IN_SPACE
            .saturating_sub(wing)
            .min(m.reserves[t].len())
            .min(bays);
        for _ in 0..want {
            out.push(Command::Launch {
                hull: None,
                bay: None,
            });
        }
        let enemy = m.mission.carrier[1 - t];
        if wing == 0 && m.reserves[t].is_empty() && enemy != NONE {
            let e = &m.ships[usize::from(enemy)];
            if e.active() {
                out.push(Command::Waypoint {
                    ship: carrier,
                    waypoint: Waypoint::At(e.pos),
                });
            }
        }
    }

    if let Mission::ConvoyEscort(ce) = &m.cfg.mission {
        for (i, s) in m.ships.iter().enumerate() {
            if s.team == team && m.mission.transports & (1 << i) != 0 && m.in_match(i) {
                out.push(Command::Waypoint {
                    ship: s.slot,
                    waypoint: Waypoint::At(ce.jump_point),
                });
            }
        }
    }

    let mut members = 0u32;
    for (i, s) in m.ships.iter().enumerate() {
        if s.team == team && m.in_match(i) && !is_capital_ship(cat.hull(s.hull)) {
            members |= 1 << i;
        }
    }
    let from = anchor(m, cat, team);
    let order = nearest(m, cat, team, from, true)
        .or_else(|| nearest(m, cat, team, from, false))
        .map_or(Order::None, |target| Order::Attack { target });
    out.push(Command::Squad {
        squad: 0,
        members,
        order,
    });
    out
}
