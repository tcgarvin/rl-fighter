//! Loaded weapon definitions (SIM_SPEC §4.2). Runtime units: radians, seconds, ticks.

#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum WeaponKind {
    Bullet,
    Beam,
    Flak,
    Torpedo,
}

impl WeaponKind {
    /// Index for the obs one-hot and the flat event encoding.
    pub fn index(self) -> usize {
        self as usize
    }
}

#[derive(Clone, Debug, PartialEq)]
pub struct WeaponDef {
    pub name: String,
    pub kind: WeaponKind,
    /// m/s; 0 for beams.
    pub speed: f32,
    pub range: f32,
    pub damage: f32,
    /// Seconds between shots at a weapons power multiplier of 1.
    pub interval: f32,
    /// Full spread cone, radians.
    pub spread: f32,
    /// Flak proximity radius, metres; 0 otherwise.
    pub burst_radius: f32,
    /// Flak: fraction of the fuse that may be cut short at random.
    pub fuse_jitter: f32,
    /// Torpedo steering rate, radians per second.
    pub turn_rate: f32,
    /// Torpedo lock cone at spawn (full angle, radians); 0 means no lock.
    pub lock_cone: f32,
    /// Multiplier on projectile lifetime (torpedoes fly past their nominal range).
    pub life_factor: f32,

    // Derived on load.
    /// `round(range / speed * 30 * life_factor)`; 0 for beams.
    pub life_ticks: u32,
}
