//! Scripted controllers: thruster allocator and per-role dispatch (SIM_SPEC §11).
//!
//! A port of the pilots in `prototypes/story/sim.js` onto the Rust state and action
//! heads. Used as the BC target, the baseline opponent, and in the browser, so it is
//! deterministic and reads only `Match` state (never obs): no rng, no allocation,
//! transcendentals via `libm` only.
//!
//! Every role shares one tick: pick a target, let the role's pilot choose a
//! body-frame force and a desired heading, override both near the arena edge, turn
//! with a PD torque, allocate thrusters, aim and fire each turret, pick a power split.

pub mod fighter;
pub mod gunship;
pub mod strafer;

use crate::DT;
use crate::actions::{SLEW_HOLD, ShipAction};
use crate::data::{Catalogue, HullDef, WeaponDef, WeaponKind};
use crate::math::{Vec2, clamp, wrap_angle};
use crate::power;
use crate::state::{MAX_THRUSTERS, Match, NEVER, Ship, ShipIdx};
use crate::turrets::cooldown_after_tick;

/// Throttle levels of the action head.
const THROTTLE_OFF: u8 = 0;
const THROTTLE_HALF: u8 = 1;
const THROTTLE_FULL: u8 = 2;

/// Allocator score thresholds for full and half throttle (sim.js).
const FULL_SCORE: f32 = 0.6;
const HALF_SCORE: f32 = 0.25;
/// Weight of the torque request against the force request in a thruster's score.
const TORQUE_WEIGHT: f32 = 1.2;

/// PD heading controller gains; the torque request is clamped to `[-1, 1]`.
///
/// sim.js uses a gain of 2.5. The allocator ignores torque requests below
/// `HALF_SCORE / TORQUE_WEIGHT` (≈ 0.21), so at 2.5 the pilot cannot correct heading
/// errors under ≈ 0.083 rad, while a fighter's compound circles (≈ 2.6 m wide head-on;
/// sim.js used one 4.5 m circle) subtend that only inside ≈ 30 m: scripted fighter
/// duels missed every pass and settled into an endless turning circle. At 10 the
/// dead zone is ≈ 0.02 rad, fine enough to hit at gun range.
const TURN_GAIN: f32 = 10.0;
const TURN_DAMPING: f32 = 1.6;

/// Beyond this fraction of the arena radius a pilot turns for the centre at full thrust.
const ARENA_TURN_BACK: f32 = 0.85;

/// Fighters go for bombers within this range before anything else (sim.js).
const FIGHTER_BOMBER_PRIORITY_RANGE: f32 = 260.0;
/// Bullet and flak turrets consider targets out to this multiple of weapon range.
const TURRET_SEARCH_FACTOR: f32 = 1.4;
/// Torpedo racks fall back to non-capital targets only this close (fraction of range).
const TORPEDO_FALLBACK_FACTOR: f32 = 0.5;

/// Fire when the aim error is under this many radians.
const FIXED_GUN_TOLERANCE: f32 = 0.1;
const TURRET_TOLERANCE: f32 = 0.06;
const TORPEDO_TOLERANCE: f32 = 0.35;
/// Turrets hold within this many radians of their goal angle (spec §11 step 6).
const SLEW_DEADBAND: f32 = 0.03;

/// "Under fire": hit within the last 1.2 s.
const UNDER_FIRE_TICKS: u32 = 36;
/// Shield fraction below which a pilot under fire diverts power to shields.
const SHIELD_NERVE: f32 = 0.3;
/// Hull fraction below which a pilot counts as badly hurt.
const HURT_HULL_FRACTION: f32 = 0.45;
/// Beyond this multiple of its longest weapon range a pilot powers its engines.
const PURSUIT_RANGE_FACTOR: f32 = 1.5;

/// Indices into `power::POWER_TARGETS` standing in for sim.js's power modes.
const POWER_BALANCED: u8 = 0;
/// sim.js "defend" (0.6, 0.25, 0.15).
const POWER_DEFEND: u8 = 1;
/// sim.js "pursuit" (0.15, 0.6, 0.25); also "evade" on shieldless hulls (engines-max).
const POWER_PURSUIT: u8 = 2;
/// sim.js "attack" (0.2, 0.2, 0.6).
const POWER_ATTACK: u8 = 3;
/// sim.js "evade" (0.4, 0.6, 0) on shielded hulls: the nearest entry with both S and E up.
const POWER_EVADE_SHIELDED: u8 = 4;

/// Hull roles that have a controller. Any other role gets the idle action.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum Role {
    Fighter,
    Skirmisher,
    Anchor,
}

impl Role {
    fn of(role: &str) -> Option<Role> {
        match role {
            "fighter" => Some(Role::Fighter),
            "skirmisher" => Some(Role::Skirmisher),
            "anchor" => Some(Role::Anchor),
            _ => None,
        }
    }
}

/// Roles torpedo racks prefer (sim.js `CAPITAL_ROLES`).
fn is_capital(role: &str) -> bool {
    matches!(role, "carrier" | "station" | "anchor")
}

/// What a role's pilot wants this tick: body-frame force request (each component in
/// `[-1, 1]`, magnitude scaled to at most 1 by the allocator) and a world heading.
#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct Manoeuvre {
    pub force_body: Vec2,
    pub heading: f32,
}

/// The pilot's view of its target, relative to its own ship.
#[derive(Clone, Copy, Debug)]
pub(crate) struct Engagement {
    /// `target.pos - me.pos`.
    pub rel_pos: Vec2,
    /// `|rel_pos|`, floored at 1 mm.
    pub dist: f32,
    /// World heading to the lead point of the ship's primary weapon.
    pub lead_heading: f32,
}

/// The scripted action for `ship` in its current state.
///
/// Inactive ships, roles without a controller and ships with no active enemy get
/// [`ShipAction::IDLE`]. Panics if `ship` is not a slot of `m`.
pub fn act(m: &Match, cat: &Catalogue, ship: ShipIdx) -> ShipAction {
    let me = &m.ships[ship as usize];
    if !me.active() {
        return ShipAction::IDLE;
    }
    let hull = cat.hull(me.hull);
    let Some(role) = Role::of(&hull.role) else {
        return ShipAction::IDLE;
    };
    let Some(target) = pick_target(m, cat, me, role) else {
        return ShipAction::IDLE;
    };
    let eng = engage(cat, me, hull, target);

    let mut plan = match role {
        Role::Fighter => fighter::manoeuvre(me, &eng),
        Role::Skirmisher => strafer::manoeuvre(me, &eng),
        Role::Anchor => gunship::manoeuvre(&eng),
    };
    if me.pos.length() > ARENA_TURN_BACK * m.cfg.arena_radius {
        plan = Manoeuvre {
            force_body: Vec2::X,
            heading: (-me.pos).angle(),
        };
    }

    let mut action = ShipAction::IDLE;
    action.throttle = allocate_thrusters(hull, plan.force_body, turn_torque(me, plan.heading));
    action.power = choose_power(m, cat, me, hull, eng.dist);
    let p_w = weapons_multiplier_after_slew(me, hull, action.power);
    aim_turrets(m, cat, me, hull, p_w, &mut action);
    action
}

/// The weapons multiplier stage 6 will use this tick if the ship picks power target
/// `power_idx`: stage 4 slews the split toward it before turrets cool down.
fn weapons_multiplier_after_slew(me: &Ship, hull: &HullDef, power_idx: u8) -> f32 {
    let mut split = me.power;
    power::slew(&mut split, power::target_for(hull, usize::from(power_idx)));
    power::multipliers(hull.n_power_systems, split)[power::WEAPONS]
}

/// Greedy thruster allocation (sim.js `allocateThrusters`): each thruster's score is
/// how far its push lies along the requested force (scaled by `min(|f|, 1)`) plus
/// `1.2 * sign(arm) * torque`, where `arm = cross(pos, dir)`; score `> 0.6` is full
/// throttle, `> 0.25` half, else off. `force_body` is body frame; `torque` is a
/// request in `[-1, 1]`, positive CCW. Slots beyond the hull's thrusters are 0.
pub fn allocate_thrusters(hull: &HullDef, force_body: Vec2, torque: f32) -> [u8; MAX_THRUSTERS] {
    let f_mag = force_body.length();
    let f_hat = if f_mag > 1e-6 {
        force_body / f_mag
    } else {
        Vec2::ZERO
    };
    let f_scale = f_mag.min(1.0);
    let mut out = [THROTTLE_OFF; MAX_THRUSTERS];
    for (level, t) in out.iter_mut().zip(&hull.thrusters) {
        let along = t.dir.dot(f_hat) * f_scale;
        let spin = sign(t.pos.cross(t.dir)) * torque;
        let score = along + TORQUE_WEIGHT * spin;
        *level = if score > FULL_SCORE {
            THROTTLE_FULL
        } else if score > HALF_SCORE {
            THROTTLE_HALF
        } else {
            THROTTLE_OFF
        };
    }
    out
}

/// `Math.sign`: 0 for 0 (unlike `f32::signum`, which gives 1 for +0).
fn sign(x: f32) -> f32 {
    if x > 0.0 {
        1.0
    } else if x < 0.0 {
        -1.0
    } else {
        0.0
    }
}

/// PD torque request toward `heading`, in `[-1, 1]`.
fn turn_torque(me: &Ship, heading: f32) -> f32 {
    let err = wrap_angle(heading - me.heading);
    clamp(TURN_GAIN * err - TURN_DAMPING * me.omega, -1.0, 1.0)
}

/// Nearest active enemy of `team` to `from`, strictly closer than `max_range`, whose
/// hull passes `filter`. Ties go to the lower slot.
fn nearest_enemy<'a>(
    m: &'a Match,
    cat: &Catalogue,
    team: u8,
    from: Vec2,
    max_range: f32,
    filter: impl Fn(&HullDef) -> bool,
) -> Option<&'a Ship> {
    let mut best = None;
    let mut best_d = max_range;
    for other in &m.ships {
        if !other.active() || other.team == team || !filter(cat.hull(other.hull)) {
            continue;
        }
        let d = (other.pos - from).length();
        if d < best_d {
            best_d = d;
            best = Some(other);
        }
    }
    best
}

/// The pilot's target (sim.js `pickTarget`): fighters go for a bomber within 260 m
/// first; everyone else takes the nearest active enemy.
fn pick_target<'a>(m: &'a Match, cat: &Catalogue, me: &Ship, role: Role) -> Option<&'a Ship> {
    let any = |_: &HullDef| true;
    if role == Role::Fighter {
        let bomber = nearest_enemy(
            m,
            cat,
            me.team,
            me.pos,
            FIGHTER_BOMBER_PRIORITY_RANGE,
            |h| h.role == "bomber",
        );
        if bomber.is_some() {
            return bomber;
        }
    }
    nearest_enemy(m, cat, me.team, me.pos, f32::INFINITY, any)
}

fn engage(cat: &Catalogue, me: &Ship, hull: &HullDef, target: &Ship) -> Engagement {
    let rel_pos = target.pos - me.pos;
    let dist = rel_pos.length().max(1e-3);
    let lead = match hull.turrets.first() {
        Some(t) => lead_point(cat.weapon(t.weapon), me, target, rel_pos),
        None => rel_pos,
    };
    Engagement {
        rel_pos,
        dist,
        lead_heading: lead.angle(),
    }
}

/// Where to aim `weapon` from a point `rel` away from `target` so the shot meets it,
/// to first order: `rel + v_rel * |rel| / speed`. Bullets and flak inherit the
/// shooter's velocity, torpedoes do not; beams are hitscan (no lead).
fn lead_point(weapon: &WeaponDef, me: &Ship, target: &Ship, rel: Vec2) -> Vec2 {
    if weapon.kind == WeaponKind::Beam || weapon.speed <= 0.0 {
        return rel;
    }
    let v_rel = match weapon.kind {
        WeaponKind::Torpedo => target.vel,
        _ => target.vel - me.vel,
    };
    rel + v_rel * (rel.length() / weapon.speed)
}

/// Slew and fire heads for every turret (sim.js `aimTurrets`, adapted to the
/// left/hold/right slew head and the linear arc clamp of stage 6).
///
/// A turret is ready when its cooldown reaches 0 in this tick's stage 6 (at weapons
/// multiplier `p_w`), since stage 7 fires right after: gating on the cooldown as
/// read now would fire every shot a tick late.
fn aim_turrets(
    m: &Match,
    cat: &Catalogue,
    me: &Ship,
    hull: &HullDef,
    p_w: f32,
    action: &mut ShipAction,
) {
    for (j, turret) in hull.turrets.iter().enumerate() {
        let weapon = cat.weapon(turret.weapon);
        let muzzle = me.to_world(turret.pos);
        let target = if weapon.kind == WeaponKind::Torpedo {
            nearest_enemy(m, cat, me.team, muzzle, weapon.range, |h| {
                is_capital(&h.role)
            })
            .or_else(|| {
                let reach = weapon.range * TORPEDO_FALLBACK_FACTOR;
                nearest_enemy(m, cat, me.team, muzzle, reach, |_| true)
            })
        } else {
            let reach = weapon.range * TURRET_SEARCH_FACTOR;
            nearest_enemy(m, cat, me.team, muzzle, reach, |_| true)
        };
        action.slew[j] = SLEW_HOLD;
        action.fire[j] = 0;
        let Some(target) = target else {
            continue;
        };
        let rel = target.pos - muzzle;
        let aim = wrap_angle(lead_point(weapon, me, target, rel).angle() - me.heading);
        let angle = me.turret_angle[j];
        if turret.arc > 0.0 {
            // Goal angle inside the arc; the turret moves linearly through its arc (no
            // wrap), so the step toward it is the plain difference.
            let half = 0.5 * turret.arc;
            let goal = turret.rest + clamp(wrap_angle(aim - turret.rest), -half, half);
            let delta = goal - angle;
            // A deadband narrower than half a step would chatter around the goal.
            let band = SLEW_DEADBAND.max(0.5 * turret.slew_rate * DT);
            action.slew[j] = if delta > band {
                0 // CCW
            } else if delta < -band {
                2 // CW
            } else {
                SLEW_HOLD
            };
        }
        let tolerance = match (weapon.kind, turret.arc > 0.0) {
            (WeaponKind::Torpedo, _) => TORPEDO_TOLERANCE,
            (_, true) => TURRET_TOLERANCE,
            (_, false) => FIXED_GUN_TOLERANCE,
        };
        let aim_err = wrap_angle(aim - angle).abs();
        let ready = cooldown_after_tick(me.turret_cooldown[j], p_w) == 0.0;
        if aim_err < tolerance && rel.length() < weapon.range && ready {
            action.fire[j] = 1;
        }
    }
}

/// Power head (sim.js `managePower`, mapped onto `POWER_TARGETS`). sim.js holds a
/// mode for 1.4 s before changing it; the controller is stateless, so instead it
/// keeps its current target while the split is still slewing toward it, except
/// when it wants shields or to break off.
fn choose_power(m: &Match, cat: &Catalogue, me: &Ship, hull: &HullDef, dist: f32) -> u8 {
    let range = hull
        .turrets
        .iter()
        .map(|t| cat.weapon(t.weapon).range)
        .fold(0.0, f32::max);
    let under_fire =
        me.last_hit_tick != NEVER && m.tick.saturating_sub(me.last_hit_tick) < UNDER_FIRE_TICKS;
    let hurt = me.hp / hull.hp < HURT_HULL_FRACTION && !hull.is_static;
    let evade = if hull.has_shield() {
        POWER_EVADE_SHIELDED
    } else {
        POWER_PURSUIT
    };
    let (want, urgent) = match hull.shield {
        Some(s) if under_fire && me.shield / s.hp < SHIELD_NERVE => {
            (if hurt { evade } else { POWER_DEFEND }, true)
        }
        None if under_fire && hurt => (evade, true),
        _ if dist < range => (POWER_ATTACK, false),
        _ if !hull.is_static && dist > range * PURSUIT_RANGE_FACTOR => (POWER_PURSUIT, false),
        _ => (POWER_BALANCED, false),
    };
    if urgent || me.power == me.power_target {
        return want;
    }
    current_power_index(hull, me.power_target).unwrap_or(want)
}

/// The table index whose target split is `target` (first match on two-way hulls,
/// where entries repeat).
fn current_power_index(hull: &HullDef, target: [f32; 3]) -> Option<u8> {
    (0..power::N_POWER_TARGETS)
        .find(|&i| power::target_for(hull, i) == target)
        .map(|i| i as u8)
}
