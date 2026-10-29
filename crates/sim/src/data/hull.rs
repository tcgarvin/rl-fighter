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

/// Parsed and validated but unused in M1; reserved for flagships (M5).
#[derive(Clone, Debug, PartialEq)]
pub struct BayDef {
    pub id: String,
    pub pos: Vec2,
    /// Unit launch direction in the body frame.
    pub dir: Vec2,
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
