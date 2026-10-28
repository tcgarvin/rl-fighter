//! Catalogue of hull and weapon definitions, DataError, and YAML loading (SIM_SPEC §4).

pub mod hull;
pub mod validate;
pub mod weapon;

pub use hull::{BayDef, Circle, HullDef, ShieldDef, ThrusterDef, TurretDef};
pub use weapon::{WeaponDef, WeaponKind};

/// Index into `Catalogue::hulls`; stable for a loaded catalogue (hulls sorted by name).
pub type HullId = u16;
/// Index into `Catalogue::weapons`, in file order.
pub type WeaponId = u16;

/// Every hull and weapon a match can use. Loading (`from_yaml`, `load_dir`) lands in WP1.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Catalogue {
    pub hulls: Vec<HullDef>,
    pub weapons: Vec<WeaponDef>,
}

impl Catalogue {
    pub fn hull_id(&self, name: &str) -> Option<HullId> {
        self.hulls
            .iter()
            .position(|h| h.name == name)
            .map(|i| i as HullId)
    }

    pub fn hull(&self, id: HullId) -> &HullDef {
        &self.hulls[id as usize]
    }

    pub fn weapon(&self, id: WeaponId) -> &WeaponDef {
        &self.weapons[id as usize]
    }
}
