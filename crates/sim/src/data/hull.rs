//! Loaded hull definitions (SIM_SPEC §4.1).
//!
//! These are the resolved runtime types every other module reads: angles are in
//! radians, durations in seconds, directions normalised, and the derived fields
//! already filled in. The YAML-facing serde structs live with the loader, so the
//! file format can change without touching the sim.

use crate::data::WeaponId;
use crate::math::Vec2;

/// One circle of a hull's compound collision shape, in the body frame.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Circle {
    pub pos: Vec2,
    pub r: f32,
}

#[derive(Clone, Debug, PartialEq)]
pub struct ThrusterDef {
    /// Mount id, e.g. `thruster.rcs.fl`; matches a named empty in the hull model.
    pub id: String,
    pub pos: Vec2,
    /// Unit vector: the direction the force pushes the ship (exhaust points opposite).
    pub dir: Vec2,
    pub max_force: f32,
}

#[derive(Clone, Debug, PartialEq)]
pub struct TurretDef {
    pub id: String,
    pub pos: Vec2,
    /// Body-frame rest angle, radians.
    pub rest: f32,
    /// Full firing arc, radians; 0 is a fixed gun.
    pub arc: f32,
    /// Radians per second; 0 for fixed guns.
    pub slew_rate: f32,
    pub weapon: WeaponId,
    /// v10: hardpoint hit points; 0 is not a hardpoint (it cannot be destroyed). Only
    /// capital hulls may set it (validation rule 14, SIM_SPEC §5.4).
    pub hp: f32,
    /// v10: a hull hit within this distance (m) of the mount damages the hardpoint.
    pub hit_radius: f32,
}

impl TurretDef {
    /// v10: the turret has its own hit points and can be destroyed.
    pub fn is_hardpoint(&self) -> bool {
        self.hp > 0.0
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ShieldDef {
    pub hp: f32,
    /// Shield HP per second at a power multiplier of 1.
    pub regen_rate: f32,
    /// Seconds without hits before regen starts, at a power multiplier of 1.
    pub regen_delay: f32,
    pub radius: f32,
}

/// Rule 11: most armour arcs a hull may declare.
pub const MAX_ARMOUR_ARCS: usize = 8;

/// One directional armour arc (SIM_SPEC §4.1, v2): hull damage landing at a
/// body-frame bearing in `[from, to)` (radians, CCW from the nose) is scaled by
/// `mult`. A hull's arcs tile `[-PI, PI]` in order.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ArmourArc {
    pub from: f32,
    pub to: f32,
    pub mult: f32,
}

/// A launch bay (v4, SIM_SPEC §5.9): launched ships leave the mouth at `pos` along `dir`.
#[derive(Clone, Debug, PartialEq)]
pub struct BayDef {
    pub id: String,
    pub pos: Vec2,
    /// Unit launch direction in the body frame.
    pub dir: Vec2,
    /// v10: hardpoint hit points; 0 is not a hardpoint (as for turrets).
    pub hp: f32,
    /// v10: a hull hit within this distance (m) of the mouth damages the bay.
    pub hit_radius: f32,
}

impl BayDef {
    /// v10: the bay has its own hit points and can be destroyed.
    pub fn is_hardpoint(&self) -> bool {
        self.hp > 0.0
    }
}

/// v10: default `hit_radius` of a turret or bay hardpoint, metres.
pub const DEFAULT_HARDPOINT_HIT_RADIUS: f32 = 8.0;

/// Hull roles of capital ships (v10 adds `line`, the dreadnought): flown by the
/// capital-ship scripts, never in squads, and the only hulls whose turrets and bays may
/// be hardpoints (any `static` hull too).
pub const ROLE_CARRIER: &str = "carrier";
pub const ROLE_TRANSPORT: &str = "transport";
pub const ROLE_LINE: &str = "line";

/// Whether a hull of `role` (and `is_static`) is a capital ship for the hardpoint rule
/// (SIM_SPEC §5.4, v10).
pub fn is_capital_role(role: &str, is_static: bool) -> bool {
    is_static || matches!(role, ROLE_CARRIER | ROLE_TRANSPORT | ROLE_LINE)
}

#[derive(Clone, Debug, PartialEq)]
pub struct HullDef {
    pub name: String,
    pub role: String,
    pub hp: f32,
    pub mass: f32,
    pub inertia: f32,
    pub speed_cap: f32,
    /// Immobile hull: never integrated, infinite mass in collisions.
    pub is_static: bool,
    pub shield: Option<ShieldDef>,
    /// v2: reaction delay override in ticks; `None` uses `MatchConfig.reaction_ticks`.
    pub reaction_ticks: Option<u8>,
    pub cost: u32,
    pub collision: Vec<Circle>,
    pub thrusters: Vec<ThrusterDef>,
    pub turrets: Vec<TurretDef>,
    pub bays: Vec<BayDef>,
    /// Directional armour arcs in list order; empty means uniform 1x (SIM_SPEC §4.1).
    pub armour: Vec<ArmourArc>,
    /// v3: directional collision-damage arcs (same layout as `armour`); empty means
    /// uniform 1x (SIM_SPEC §4.1, §5.5).
    pub impact: Vec<ArmourArc>,

    // Derived on load.
    /// `max(|c.pos| + c.r)` over collision circles.
    pub bound_radius: f32,
    /// The shield's radius, or `bound_radius` for shieldless hulls.
    pub shield_radius: f32,
    /// 3 with a shield (shields, engines, weapons), else 2.
    pub n_power_systems: u8,
    /// `1.4 * speed_cap`: ships jump in already moving.
    pub arrival_speed: f32,
}

impl HullDef {
    pub fn has_shield(&self) -> bool {
        self.shield.is_some()
    }

    /// v10: a capital ship for the hardpoint rule and `capital_only` weapons: role
    /// `carrier`, `transport` or `line`, or any static hull ([`is_capital_role`]).
    pub fn is_capital(&self) -> bool {
        is_capital_role(&self.role, self.is_static)
    }

    /// v10: any turret or bay of the hull is a hardpoint.
    pub fn has_hardpoints(&self) -> bool {
        self.turrets.iter().any(TurretDef::is_hardpoint)
            || self.bays.iter().any(BayDef::is_hardpoint)
    }

    /// Fill the derived fields from the authored ones. The loader calls this; tests
    /// that build a `HullDef` by hand should too.
    pub fn derive(&mut self) {
        self.bound_radius = self
            .collision
            .iter()
            .map(|c| c.pos.length() + c.r)
            .fold(0.0, f32::max);
        self.shield_radius = match self.shield {
            Some(s) => s.radius,
            None => self.bound_radius,
        };
        self.n_power_systems = if self.shield.is_some() { 3 } else { 2 };
        self.arrival_speed = 1.4 * self.speed_cap;
    }
}

/// Hull damage multiplier at body-frame `bearing` (radians, as `wrap_angle` returns)
/// (SIM_SPEC §4.1). Arcs are half-open `[from, to)` and validated to tile
/// `[-PI, PI]` in order, so the lookup is the first arc whose `to` lies above the
/// bearing; anything past the last `to` (only `+PI`, or a hair below `-PI`'s
/// rounding on the other end) takes the last arc. 1.0 without armour.
pub fn armour_mult(hull: &HullDef, bearing: f32) -> f32 {
    arc_mult(&hull.armour, bearing)
}

/// Collision damage multiplier at body-frame `bearing` (v3, SIM_SPEC §4.1, §5.5):
/// the same lookup as [`armour_mult`] over the hull's `impact` arcs. 1.0 without
/// impact arcs.
pub fn impact_mult(hull: &HullDef, bearing: f32) -> f32 {
    arc_mult(&hull.impact, bearing)
}

/// First arc whose `to` lies above `bearing`, else the last arc, else 1.0.
fn arc_mult(arcs: &[ArmourArc], bearing: f32) -> f32 {
    match arcs.iter().find(|a| bearing < a.to) {
        Some(a) => a.mult,
        None => arcs.last().map_or(1.0, |a| a.mult),
    }
}
