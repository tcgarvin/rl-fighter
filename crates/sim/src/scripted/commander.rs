//! The scripted commander (`CommanderMode::Scripted`), run by the sim inside `step`
//! on every slow tick so the browser and training share it (SIM_SPEC §5.9, §11.1).
//!
//! It reads `Match` state and returns the team's commands for this slow tick. Like
//! the pilots it is deterministic (no rng) and stateless: what it remembers between
//! slow ticks is the sim's own command state (squads, orders, waypoints), which is
//! also what gives it hysteresis. An order is changed only for a clearly better one
//! (each change is a line in the web's command log), squad membership only moves
//! when a squad is the wrong size, and a squad command or a waypoint that would not
//! change anything is not sent. The one allocation is the returned `Vec`, once per
//! slow tick.
//!
//! - **Carrier battle.** *Launches*: keep `WING_BASE` strike craft in space or on
//!   the way, one more every `WING_GROWTH_TICKS`, one launch per slow tick; scramble
//!   (one per bay) while enemy strike craft threaten the carrier; empty the hangar
//!   in the last `LATE_TICKS`. *Squads*: squad 0 **defends** the carrier (a third of
//!   the wing, half while it is threatened; new launches join it), squad 1
//!   **strikes**: the enemy carrier, unless the enemy strike craft near it outnumber
//!   the strike squad, in which case it attacks the enemy strike craft nearest
//!   itself. *Carrier waypoint*: patrol its own side (`HOME_FRAC` of the radius out,
//!   switching between `±PATROL_Y` every `PATROL_TICKS`); retreat `RETREAT_STEP`
//!   away from threats; when winning on numbers, or in the last `LATE_TICKS`, close
//!   to `STANDOFF` of the enemy carrier (its flak range); when its wing is spent,
//!   close on the enemy carrier itself.
//! - **Convoy escort, defenders.** Transports fly to the jump point (setup's
//!   waypoint, never changed: the transport is a sitting duck). Squad 0 **defends**
//!   the most threatened transport (the lead one while none is threatened), half
//!   the escort; squad 1 **intercepts** the enemy nearest the convoy, or goes to a
//!   point off the convoy's flank on the attackers' side before they arrive.
//! - **Convoy escort, attackers.** Two **waves**: wave 1 (squad 0, the first half)
//!   attacks the transport that scores highest on route progress plus damage taken
//!   (the lead or the most damaged one); wave 2 (squad 1) goes to a staging point
//!   ahead of the convoy on the attackers' side, and goes in on the same target
//!   once wave 1 is down to half its size, or at `WAVE_TWO_TICKS`.
//! - **Deathmatch.** Two squads (the fleet split in slot order): squad 0 attacks
//!   the enemy nearest it, squad 1 the most damaged enemy within reach. The
//!   scripted pilots do not follow a scripted deathmatch commander
//!   (`scripted::orders`), so these orders are only shown.

use crate::command::{
    BAY_COOLDOWN_TICKS, Command, MAX_SQUADS, NO_DEADLINE, Order, Squad, Waypoint,
};
use crate::data::Catalogue;
use crate::math::Vec2;
use crate::mission::{ConvoyEscort, JumpState, Mission, is_capital_ship};
use crate::state::{Attach, Match, NONE, Ship, ShipIdx};

/// Strike craft a carrier keeps in space or on their way at the start.
pub const WING_BASE: usize = 3;
/// It keeps one more every this many ticks (30 s).
pub const WING_GROWTH_TICKS: u32 = 900;
/// Outside a scramble, launches are at least this many ticks apart (12 s), so a
/// hangar empties over the match rather than in its first seconds.
pub const LAUNCH_INTERVAL_TICKS: u32 = 360;
/// In the last this many ticks (60 s) a carrier empties its hangar and closes on
/// the enemy carrier.
pub const LATE_TICKS: u32 = 1800;
/// Enemy strike craft within this distance of a carrier threaten it (m); at least
/// `THREAT_COUNT` of them make the commander scramble and retreat.
pub const THREAT_RADIUS: f32 = 200.0;
pub const THREAT_COUNT: usize = 2;
/// A threatened carrier's defence stays at half the wing until no enemy strike craft
/// is within this distance (m).
pub const THREAT_CLEAR_RADIUS: f32 = 280.0;
/// Enemy strike craft within this distance of their carrier escort it (m).
pub const ESCORT_RADIUS: f32 = 220.0;
/// A carrier patrols `HOME_FRAC` of the arena radius out on its own side, between
/// `±PATROL_Y` metres, switching every `PATROL_TICKS` (20 s).
pub const HOME_FRAC: f32 = 0.6;
pub const PATROL_Y: f32 = 60.0;
pub const PATROL_TICKS: u32 = 600;
/// A threatened carrier's waypoint lies this far from it, away from the threat (m).
pub const RETREAT_STEP: f32 = 100.0;
/// Carrier waypoints stay inside this fraction of the arena radius.
pub const CARRIER_LIMIT_FRAC: f32 = 0.78;
/// An advancing carrier closes to this distance of the enemy carrier (m), inside
/// its flak range (230 m).
pub const STANDOFF: f32 = 170.0;
/// "Winning on numbers": at least this many times the enemy's strike craft in
/// space, plus `WINNING_MARGIN`.
pub const WINNING_RATIO: usize = 2;
pub const WINNING_MARGIN: usize = 2;
/// Also "winning": the own carrier's hull fraction this much above the enemy's.
pub const WINNING_HULL_MARGIN: f32 = 0.2;
/// A new waypoint is sent only this far (m) from the current one.
pub const WAYPOINT_SLACK: f32 = 20.0;
/// An attack target is kept unless another is nearer than this fraction of its
/// distance, less `STICKY_METRES`.
pub const STICKY_FRAC: f32 = 0.6;
pub const STICKY_METRES: f32 = 30.0;
/// Enemies within this distance of a transport threaten it (m).
pub const CONVOY_THREAT_RADIUS: f32 = 220.0;
/// The defence moves to another transport only if it has this many more threats.
pub const WARD_SWITCH_MARGIN: usize = 2;
/// Before the attackers arrive, the intercept squad goes this far off the lead
/// transport toward the attackers' side (m), within `INTERCEPT_GOTO_RADIUS`.
pub const INTERCEPT_GOTO_OFFSET: f32 = 120.0;
pub const INTERCEPT_GOTO_RADIUS: f32 = 80.0;
/// A go-to point is kept while the one it would now pick is within this (m).
pub const GOTO_SLACK: f32 = 120.0;
/// Attackers' target score: route progress plus this × the hull fraction lost,
/// plus `CHARGING_BONUS` for a transport charging its jump; a new target must beat
/// the current one by `TARGET_SWITCH_MARGIN`.
pub const DAMAGE_WEIGHT: f32 = 1.0;
pub const CHARGING_BONUS: f32 = 0.2;
pub const TARGET_SWITCH_MARGIN: f32 = 0.25;
/// Wave 2 goes in at this tick (30 s) at the latest.
pub const WAVE_TWO_TICKS: u32 = 900;
/// Wave 2 stages this far ahead of the lead transport along the route and this far
/// toward the attackers' side (m), arriving within `STAGING_RADIUS`.
pub const STAGING_AHEAD: f32 = 150.0;
pub const STAGING_SIDE: f32 = 110.0;
pub const STAGING_RADIUS: f32 = 60.0;
/// Deathmatch: squad 1 picks the most damaged enemy within this distance (m).
pub const FOCUS_REACH: f32 = 300.0;
/// Deathmatch: a new focus target must be this much more damaged (fraction).
pub const FOCUS_SWITCH_MARGIN: f32 = 0.2;

const DEFEND: usize = 0;
const STRIKE: usize = 1;
const INTERCEPT: usize = 1;
const WAVE_ONE: usize = 0;
const WAVE_TWO: usize = 1;

/// Slots in `mask`.
fn slots(mask: u32) -> impl Iterator<Item = usize> {
    (0..32).filter(move |&s| mask & (1 << s) != 0)
}

fn count(mask: u32) -> usize {
    mask.count_ones() as usize
}

/// Mask of the slots of `m` passing `keep`.
fn mask_of(m: &Match, keep: impl Fn(usize, &Ship) -> bool) -> u32 {
    let mut mask = 0;
    for (i, s) in m.ships.iter().enumerate() {
        if keep(i, s) {
            mask |= 1 << i;
        }
    }
    mask
}

/// Mean position of the active ships in `mask`.
fn centroid(m: &Match, mask: u32) -> Option<Vec2> {
    let (mut sum, mut n) = (Vec2::ZERO, 0.0f32);
    for s in slots(mask) {
        if m.ships[s].active() {
            sum += m.ships[s].pos;
            n += 1.0;
        }
    }
    (n > 0.0).then(|| sum / n)
}

fn within(m: &Match, mask: u32, p: Vec2, r: f32) -> usize {
    slots(mask)
        .filter(|&s| (m.ships[s].pos - p).length() < r)
        .count()
}

/// The slot in `mask` nearest `p` by `dist` (ties to the lower slot).
fn nearest_by(mask: u32, dist: impl Fn(usize) -> f32) -> Option<usize> {
    let mut best = None;
    let mut best_d = f32::INFINITY;
    for s in slots(mask) {
        let d = dist(s);
        if d < best_d {
            best_d = d;
            best = Some(s);
        }
    }
    best
}

/// The current attack target if it is still in `candidates` and no candidate is
/// clearly nearer by `dist` (module constants), else the nearest candidate.
fn sticky_nearest(current: Order, candidates: u32, dist: impl Fn(usize) -> f32) -> Option<usize> {
    let best = nearest_by(candidates, &dist)?;
    if let Order::Attack { target } = current {
        let t = usize::from(target);
        if candidates & (1 << t) != 0 && dist(best) >= STICKY_FRAC * dist(t) - STICKY_METRES {
            return Some(t);
        }
    }
    Some(best)
}

fn attack(slot: usize) -> Order {
    Order::Attack {
        target: slot as ShipIdx,
    }
}

/// Members of squads `a` and `b` from `pool`, `a` sized `want_a`: members stay in
/// their squad while it is the right size; newcomers fill squad `a` first; a squad
/// that is too big gives up the members with the largest `rank` (squad `a`) or the
/// smallest (squad `b`) to the other.
fn split(
    current: &[Squad; MAX_SQUADS],
    pool: u32,
    (a, b): (usize, usize),
    want_a: usize,
    rank: impl Fn(usize) -> f32,
) -> (u32, u32) {
    let mut in_a = current[a].members & pool;
    let mut in_b = current[b].members & pool & !in_a;
    for s in slots(pool & !(in_a | in_b)) {
        if count(in_a) < want_a {
            in_a |= 1 << s;
        } else {
            in_b |= 1 << s;
        }
    }
    while count(in_a) > want_a {
        let out = slots(in_a)
            .max_by(|&x, &y| rank(x).total_cmp(&rank(y)).then(x.cmp(&y)))
            .expect("non-empty");
        in_a &= !(1 << out);
        in_b |= 1 << out;
    }
    while count(in_a) < want_a && in_b != 0 {
        let take = slots(in_b)
            .min_by(|&x, &y| rank(x).total_cmp(&rank(y)).then(x.cmp(&y)))
            .expect("non-empty");
        in_b &= !(1 << take);
        in_a |= 1 << take;
    }
    (in_a, in_b)
}

/// Push a `Squad` command unless it changes nothing.
fn set_squad(m: &Match, team: u8, k: usize, members: u32, order: Order, out: &mut Vec<Command>) {
    let cur = m.command.squads[usize::from(team)][k];
    if cur.members == members && cur.order == order {
        return;
    }
    out.push(Command::Squad {
        squad: k as u8,
        members,
        order,
    });
}

/// Push a `Waypoint` command unless `ship` already has one within `WAYPOINT_SLACK`.
fn set_waypoint(m: &Match, ship: usize, p: Vec2, out: &mut Vec<Command>) {
    let limit = crate::command::POINT_LIMIT_FRAC * m.cfg.arena_radius;
    let p = clamp_disc(p, limit);
    if let Waypoint::At(cur) = m.command.waypoints[ship]
        && (cur - p).length() <= WAYPOINT_SLACK
    {
        return;
    }
    out.push(Command::Waypoint {
        ship: ship as ShipIdx,
        waypoint: Waypoint::At(p),
    });
}

fn clamp_disc(p: Vec2, r: f32) -> Vec2 {
    let len = p.length();
    if len > r { p * (r / len) } else { p }
}

/// A go-to `want`, or the current go-to order if its point is within `GOTO_SLACK`.
fn sticky_goto(current: Order, want: Vec2, radius: f32) -> Order {
    if let Order::GoTo { point, .. } = current
        && (point - want).length() <= GOTO_SLACK
    {
        return current;
    }
    Order::GoTo {
        point: want,
        radius,
        deadline: NO_DEADLINE,
    }
}

/// The team's commands for this slow tick (module docs).
pub fn commands(m: &Match, cat: &Catalogue, team: u8) -> Vec<Command> {
    let mut out = Vec::new();
    let team = team & 1;
    match &m.cfg.mission {
        Mission::Deathmatch => deathmatch(m, cat, team, &mut out),
        Mission::CarrierBattle(_) => carrier_battle(m, cat, team, &mut out),
        Mission::ConvoyEscort(ce) if team == 0 => convoy_defence(m, cat, ce, &mut out),
        Mission::ConvoyEscort(ce) => convoy_attack(m, cat, ce, &mut out),
    }
    out
}

/// Own strike craft in the match and not docked (on the field or on the way in).
fn own_wing(m: &Match, cat: &Catalogue, team: u8) -> u32 {
    mask_of(m, |i, s| {
        s.team == team
            && m.in_match(i)
            && s.attach == Attach::None
            && !is_capital_ship(cat.hull(s.hull))
    })
}

/// Active enemy strike craft of `team`.
fn enemy_strike(m: &Match, cat: &Catalogue, team: u8) -> u32 {
    mask_of(m, |_, s| {
        s.team != team && s.active() && !is_capital_ship(cat.hull(s.hull))
    })
}

/// Active enemies of `team`.
fn enemies(m: &Match, team: u8) -> u32 {
    mask_of(m, |_, s| s.team != team && s.active())
}

fn deathmatch(m: &Match, cat: &Catalogue, team: u8, out: &mut Vec<Command>) {
    let squads = &m.command.squads[usize::from(team)];
    let pool = own_wing(m, cat, team);
    let foes = enemies(m, team);
    // The fleet split in slot order: the first half is squad 0.
    let first_half = slots(pool)
        .take(count(pool).div_ceil(2))
        .fold(0, |a, s| a | 1 << s);
    let (a, b) = split(squads, pool, (0, 1), count(pool).div_ceil(2), |s| {
        if first_half & (1 << s) != 0 { 0.0 } else { 1.0 }
    });
    let order_a = centroid(m, a).map_or(Order::None, |c| {
        sticky_nearest(squads[0].order, foes, |s| (m.ships[s].pos - c).length())
            .map_or(Order::None, attack)
    });
    let order_b = centroid(m, b).map_or(Order::None, |c| {
        let damage = |s: usize| {
            let ship = &m.ships[s];
            let hull = cat.hull(ship.hull);
            let full = hull.hp + hull.shield.map_or(0.0, |sh| sh.hp);
            1.0 - (ship.hp + ship.shield) / full
        };
        let reach = mask_of(m, |i, _| {
            foes & (1 << i) != 0 && (m.ships[i].pos - c).length() < FOCUS_REACH
        });
        let pick = if reach == 0 { foes } else { reach };
        let best = slots(pick).max_by(|&x, &y| damage(x).total_cmp(&damage(y)).then(y.cmp(&x)));
        let keep = match squads[1].order {
            Order::Attack { target } => {
                let t = usize::from(target);
                (pick & (1 << t) != 0
                    && best.is_some_and(|b| damage(b) < damage(t) + FOCUS_SWITCH_MARGIN))
                .then_some(t)
            }
            _ => None,
        };
        keep.or(best).map_or(Order::None, attack)
    });
    set_squad(m, team, 0, a, order_a, out);
    set_squad(m, team, 1, b, order_b, out);
}

fn carrier_battle(m: &Match, cat: &Catalogue, team: u8, out: &mut Vec<Command>) {
    let t = usize::from(team);
    let own = m.mission.carrier[t];
    let foe = m.mission.carrier[1 - t];
    if own == NONE || !m.ships[usize::from(own)].active() {
        return;
    }
    let carrier = &m.ships[usize::from(own)];
    let side = if team == 0 { -1.0 } else { 1.0 };
    let radius = m.cfg.arena_radius;
    let enemy_strike = enemy_strike(m, cat, team);
    let threats = within(m, enemy_strike, carrier.pos, THREAT_RADIUS);
    let lingering = within(m, enemy_strike, carrier.pos, THREAT_CLEAR_RADIUS);
    let ticks_left = m.cfg.time_limit_ticks.saturating_sub(m.tick);
    let late = ticks_left <= LATE_TICKS;

    // Launches (the sim refuses what the bays cannot do).
    let mut wing = own_wing(m, cat, team);
    let reserves = &m.reserves[t];
    let bays = cat.hull(carrier.hull).bays.len();
    let target = WING_BASE + (m.tick / WING_GROWTH_TICKS) as usize;
    // The last launch: the latest bay cooldown, less the cooldown.
    let last_launch = m.mission.bay_ready[t][..bays]
        .iter()
        .max()
        .map_or(0, |&r| r.saturating_sub(BAY_COOLDOWN_TICKS));
    let paced = m.tick >= last_launch + LAUNCH_INTERVAL_TICKS || last_launch == 0;
    let launches = if late || threats >= THREAT_COUNT {
        bays
    } else if count(wing) < target && paced {
        1
    } else {
        0
    }
    .min(reserves.len());
    for &slot in &reserves[..launches] {
        out.push(Command::Launch {
            hull: None,
            bay: None,
        });
        // The launched ship joins the wing (the defence) this slow tick.
        wing |= 1 << slot;
    }

    // Squads: defend the carrier, strike the enemy.
    let squads = &m.command.squads[t];
    let n = count(wing);
    let defending = count(squads[DEFEND].members & wing);
    let alarmed = threats >= THREAT_COUNT || (lingering > 0 && 2 * defending >= n && n > 1);
    let want_defend = match n {
        0 => 0,
        1 => usize::from(alarmed),
        _ if alarmed => n.div_ceil(2),
        _ => n.div_ceil(3),
    };
    let home_dist = |s: usize| (m.ships[s].pos - carrier.pos).length();
    let (defend, strike) = split(squads, wing, (DEFEND, STRIKE), want_defend, home_dist);
    let defend_order = if defend == 0 {
        Order::None
    } else {
        Order::Defend { ward: own }
    };
    let strike_order = if strike == 0 || foe == NONE || !m.ships[usize::from(foe)].active() {
        Order::None
    } else {
        let enemy_carrier = &m.ships[usize::from(foe)];
        let escort = within(m, enemy_strike, enemy_carrier.pos, ESCORT_RADIUS);
        let on_carrier = squads[STRIKE].order == attack(usize::from(foe));
        let strikers = count(strike);
        let go_carrier = enemy_strike == 0
            || if on_carrier {
                escort <= strikers + 1
            } else {
                2 * escort <= strikers
            };
        if go_carrier {
            attack(usize::from(foe))
        } else {
            let c = centroid(m, strike).unwrap_or(carrier.pos);
            sticky_nearest(squads[STRIKE].order, enemy_strike, |s| {
                (m.ships[s].pos - c).length()
            })
            .map_or(attack(usize::from(foe)), attack)
        }
    };
    set_squad(m, team, DEFEND, defend, defend_order, out);
    set_squad(m, team, STRIKE, strike, strike_order, out);

    // The carrier's waypoint.
    let spent = wing == 0 && m.reserves[t].is_empty();
    let enemy_carrier =
        (foe != NONE && m.ships[usize::from(foe)].active()).then(|| &m.ships[usize::from(foe)]);
    let own_space = count(wing);
    let hull = |c: &Ship| c.hp / cat.hull(c.hull).hp;
    let winning = own_space >= WINNING_RATIO * count(enemy_strike) + WINNING_MARGIN
        || enemy_carrier.is_some_and(|e| hull(carrier) >= hull(e) + WINNING_HULL_MARGIN);
    let limit = CARRIER_LIMIT_FRAC * radius;
    let close = |e: &Ship| {
        let back = (carrier.pos - e.pos).normalized();
        e.pos + back * STANDOFF
    };
    let goal = match enemy_carrier {
        Some(e) if spent => e.pos,
        // Late in the match it closes whatever threatens it: the clock is the
        // greater danger.
        Some(e) if late => close(e),
        _ if threats >= THREAT_COUNT => {
            let from = centroid(m, enemy_strike & threat_mask(m, enemy_strike, carrier.pos))
                .unwrap_or(carrier.pos);
            let away = (carrier.pos - from).normalized();
            clamp_disc(carrier.pos + away * RETREAT_STEP, limit)
        }
        Some(e) if winning => close(e),
        _ => {
            let leg = if (m.tick / PATROL_TICKS) % 2 == 0 {
                1.0
            } else {
                -1.0
            };
            Vec2::new(side * HOME_FRAC * radius, leg * PATROL_Y)
        }
    };
    set_waypoint(m, usize::from(own), goal, out);
}

/// The ships of `mask` within `THREAT_RADIUS` of `p`.
fn threat_mask(m: &Match, mask: u32, p: Vec2) -> u32 {
    mask_of(m, |i, s| {
        mask & (1 << i) != 0 && (s.pos - p).length() < THREAT_RADIUS
    })
}

/// Own transports still on the field (en route or charging).
fn convoy(m: &Match) -> u32 {
    mask_of(m, |i, s| m.mission.transports & (1 << i) != 0 && s.active())
}

/// The transport furthest along the route.
fn lead_transport(m: &Match, ce: &ConvoyEscort, convoy: u32) -> Option<usize> {
    slots(convoy).max_by(|&a, &b| {
        ce.progress(m.ships[a].pos)
            .total_cmp(&ce.progress(m.ships[b].pos))
            .then(b.cmp(&a))
    })
}

/// Unit vector from the route toward the side the attackers jump in on (team 1's
/// side, `+x`), perpendicular to the route.
fn attackers_side(ce: &ConvoyEscort) -> Vec2 {
    let port = ce.route_dir().perp();
    if port.x > 0.0 { port } else { -port }
}

fn convoy_defence(m: &Match, cat: &Catalogue, ce: &ConvoyEscort, out: &mut Vec<Command>) {
    let convoy = convoy(m);
    let Some(lead) = lead_transport(m, ce, convoy) else {
        return;
    };
    let squads = &m.command.squads[0];
    let foes = enemies(m, 0);
    let threat = |s: usize| within(m, foes, m.ships[s].pos, CONVOY_THREAT_RADIUS);
    let charging = |s: usize| matches!(m.mission.jump[s], JumpState::Charging { .. });
    // The most threatened transport that is not leaving; the lead one if none is.
    let most = slots(convoy & !mask_of(m, |i, _| charging(i)))
        .max_by(|&a, &b| threat(a).cmp(&threat(b)).then(b.cmp(&a)))
        .filter(|&s| threat(s) > 0)
        .unwrap_or(lead);
    let ward = match squads[DEFEND].order {
        Order::Defend { ward } => {
            let w = usize::from(ward);
            let ok = convoy & (1 << w) != 0 && !charging(w);
            if ok && threat(most) < threat(w) + WARD_SWITCH_MARGIN {
                w
            } else {
                most
            }
        }
        _ => most,
    };
    let pool = own_wing(m, cat, 0);
    let ward_pos = m.ships[ward].pos;
    let (defend, intercept) = split(
        squads,
        pool,
        (DEFEND, INTERCEPT),
        count(pool).div_ceil(2),
        |s| (m.ships[s].pos - ward_pos).length(),
    );
    let defend_order = if defend == 0 {
        Order::None
    } else {
        Order::Defend {
            ward: ward as ShipIdx,
        }
    };
    let convoy_dist = |s: usize| {
        slots(convoy)
            .map(|c| (m.ships[c].pos - m.ships[s].pos).length())
            .fold(f32::INFINITY, f32::min)
    };
    let intercept_order = if intercept == 0 {
        Order::None
    } else if foes == 0 {
        let at = m.ships[lead].pos + attackers_side(ce) * INTERCEPT_GOTO_OFFSET;
        sticky_goto(squads[INTERCEPT].order, at, INTERCEPT_GOTO_RADIUS)
    } else {
        sticky_nearest(squads[INTERCEPT].order, foes, convoy_dist).map_or(Order::None, attack)
    };
    set_squad(m, 0, DEFEND, defend, defend_order, out);
    set_squad(m, 0, INTERCEPT, intercept, intercept_order, out);
}

fn convoy_attack(m: &Match, cat: &Catalogue, ce: &ConvoyEscort, out: &mut Vec<Command>) {
    let convoy = convoy(m);
    let squads = &m.command.squads[1];
    let pool = own_wing(m, cat, 1);
    let Some(lead) = lead_transport(m, ce, convoy) else {
        return;
    };
    let score = |s: usize| {
        let ship = &m.ships[s];
        let lost = 1.0 - ship.hp / cat.hull(ship.hull).hp;
        let charge = if matches!(m.mission.jump[s], JumpState::Charging { .. }) {
            CHARGING_BONUS
        } else {
            0.0
        };
        ce.progress(ship.pos) + DAMAGE_WEIGHT * lost + charge
    };
    let best = slots(convoy)
        .max_by(|&a, &b| score(a).total_cmp(&score(b)).then(b.cmp(&a)))
        .expect("the convoy has a lead");
    let target = match squads[WAVE_ONE].order {
        Order::Attack { target } => {
            let cur = usize::from(target);
            if convoy & (1 << cur) != 0 && score(best) < score(cur) + TARGET_SWITCH_MARGIN {
                cur
            } else {
                best
            }
        }
        _ => best,
    };
    // Waves: the first half of the attackers (slot order) is wave 1; newcomers and
    // the rest are wave 2.
    let fresh = squads[WAVE_ONE].members == 0 && squads[WAVE_TWO].members == 0;
    let first = if fresh {
        slots(pool)
            .take(count(pool).div_ceil(2))
            .fold(0, |a, s| a | 1 << s)
    } else {
        squads[WAVE_ONE].members & pool
    };
    let one = first;
    let two = pool & !one;
    let committed = matches!(squads[WAVE_TWO].order, Order::Attack { .. });
    let go = committed || m.tick >= WAVE_TWO_TICKS || 2 * count(one) <= count(two);
    let order_one = if one == 0 {
        Order::None
    } else {
        attack(target)
    };
    let order_two = if two == 0 {
        Order::None
    } else if go {
        attack(target)
    } else {
        let at =
            m.ships[lead].pos + ce.route_dir() * STAGING_AHEAD + attackers_side(ce) * STAGING_SIDE;
        sticky_goto(squads[WAVE_TWO].order, at, STAGING_RADIUS)
    };
    set_squad(m, 1, WAVE_ONE, one, order_one, out);
    set_squad(m, 1, WAVE_TWO, two, order_two, out);
}
