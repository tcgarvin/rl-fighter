//! Catalogue of hull and weapon definitions, DataError, and YAML loading (SIM_SPEC §4).

pub mod hull;
mod raw;
pub mod validate;
pub mod weapon;

use core::fmt;

pub use hull::{
    ArmourArc, BayDef, Circle, HullDef, MAX_ARMOUR_ARCS, ShieldDef, ThrusterDef, TurretDef,
    armour_mult, impact_mult,
};
pub use weapon::{WeaponDef, WeaponKind};

use crate::TICK_HZ;
use crate::math::PI;
use raw::{RawArmourArc, RawHull, RawKind, RawWeapon, RawWeapons};
use validate::vec2;

/// Index into `Catalogue::hulls`; stable for a loaded catalogue (hulls sorted by name).
pub type HullId = u16;
/// Index into `Catalogue::weapons`, in file order.
pub type WeaponId = u16;

const DEG_TO_RAD: f32 = PI / 180.0;

/// A data file failed to load. Loading collects every problem before giving up, so a
/// failed load with more than one problem returns `Multiple`.
#[derive(Clone, Debug, PartialEq)]
pub enum DataError {
    /// A file could not be read or is not valid YAML for its schema. `file` is the
    /// path relative to the assets directory, e.g. `hulls/fighter/hull.yaml`.
    Parse { file: String, msg: String },
    /// A parsed definition breaks a §4.4 rule. `hull` is the hull's directory name,
    /// or `weapons.yaml` (`validate::WEAPONS_FILE`) for weapon errors.
    Invalid { hull: String, msg: String },
    /// Two or more of the above; never nested, never fewer than two.
    Multiple(Vec<DataError>),
}

impl DataError {
    /// Every individual problem: the contents of `Multiple`, or just `self`.
    pub fn issues(&self) -> &[DataError] {
        match self {
            DataError::Multiple(all) => all,
            single => core::slice::from_ref(single),
        }
    }

    fn from_list(mut errs: Vec<DataError>) -> DataError {
        assert!(!errs.is_empty(), "from_list needs at least one error");
        if errs.len() == 1 {
            errs.remove(0)
        } else {
            DataError::Multiple(errs)
        }
    }
}

impl fmt::Display for DataError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            DataError::Parse { file, msg } => write!(f, "{file}: {msg}"),
            DataError::Invalid { hull, msg } => write!(f, "{hull}: {msg}"),
            DataError::Multiple(all) => {
                write!(f, "{} data errors:", all.len())?;
                for e in all {
                    write!(f, "\n  {e}")?;
                }
                Ok(())
            }
        }
    }
}

impl std::error::Error for DataError {}

/// `round(range / speed * 30 * life_factor)`; callers handle beams (speed 0).
pub(crate) fn life_ticks(range: f32, speed: f32, life_factor: f32) -> u32 {
    // `as` saturates: negative and NaN become 0, which validation rejects.
    libm::roundf(range / speed * TICK_HZ * life_factor) as u32
}

fn hull_file(name: &str) -> String {
    format!("hulls/{name}/hull.yaml")
}

/// Every hull and weapon a match can use.
#[derive(Clone, Debug, Default, PartialEq)]
pub struct Catalogue {
    pub hulls: Vec<HullDef>,
    pub weapons: Vec<WeaponDef>,
}

impl Catalogue {
    /// Build a catalogue from YAML text: `hulls` is `(directory name, hull.yaml text)`
    /// pairs in any order, `weapons_yaml` the text of `weapons.yaml`. Hulls are sorted
    /// by name, so ids match `load_dir`. Every parse and validation error is reported.
    pub fn from_yaml(hulls: &[(&str, &str)], weapons_yaml: &str) -> Result<Self, DataError> {
        let mut errs = Vec::new();

        let weapons = match serde_saphyr::from_str::<RawWeapons>(weapons_yaml) {
            Ok(RawWeapons(list)) => Some(list),
            Err(e) => {
                errs.push(DataError::Parse {
                    file: validate::WEAPONS_FILE.to_string(),
                    msg: e.to_string(),
                });
                None
            }
        };
        let weapon_names: Option<Vec<String>> = weapons
            .as_ref()
            .map(|list| list.iter().map(|(n, _)| n.clone()).collect());
        if let Some(list) = &weapons {
            for (i, (name, w)) in list.iter().enumerate() {
                if list[..i].iter().any(|(n, _)| n == name) {
                    errs.push(DataError::Invalid {
                        hull: validate::WEAPONS_FILE.to_string(),
                        msg: format!("weapon {name:?} is defined twice"),
                    });
                }
                validate::validate_weapon(name, w, &mut errs);
            }
        }

        let mut sorted: Vec<(&str, &str)> = hulls.to_vec();
        sorted.sort_by(|a, b| a.0.cmp(b.0));
        let mut raw_hulls = Vec::with_capacity(sorted.len());
        for (i, &(name, text)) in sorted.iter().enumerate() {
            if i > 0 && sorted[i - 1].0 == name {
                errs.push(DataError::Invalid {
                    hull: name.to_string(),
                    msg: "hull is defined twice".to_string(),
                });
                continue;
            }
            match serde_saphyr::from_str::<RawHull>(text) {
                Ok(raw) => {
                    validate::validate_hull(name, &raw, weapon_names.as_deref(), &mut errs);
                    raw_hulls.push(raw);
                }
                Err(e) => errs.push(DataError::Parse {
                    file: hull_file(name),
                    msg: e.to_string(),
                }),
            }
        }

        if !errs.is_empty() {
            return Err(DataError::from_list(errs));
        }
        let (Some(weapons), Some(weapon_names)) = (weapons, weapon_names) else {
            unreachable!("weapon parse failures are reported above");
        };
        let hulls = raw_hulls
            .into_iter()
            .map(|raw| convert_hull(raw, &weapon_names))
            .collect();
        let weapons = weapons.into_iter().map(convert_weapon).collect();
        Ok(Catalogue { hulls, weapons })
    }

    /// Read `assets/weapons.yaml` and every `assets/hulls/<name>/hull.yaml`, hulls
    /// sorted by directory name so ids are stable across machines.
    #[cfg(feature = "fs")]
    pub fn load_dir(assets: &std::path::Path) -> Result<Self, DataError> {
        let read = |rel: &str| {
            std::fs::read_to_string(assets.join(rel)).map_err(|e| DataError::Parse {
                file: rel.to_string(),
                msg: format!("cannot read {}: {e}", assets.join(rel).display()),
            })
        };
        let hulls_dir = assets.join("hulls");
        let listing_err = |e: std::io::Error| DataError::Parse {
            file: "hulls".to_string(),
            msg: format!("cannot list {}: {e}", hulls_dir.display()),
        };

        let mut names = Vec::new();
        let mut errs = Vec::new();
        for entry in std::fs::read_dir(&hulls_dir).map_err(listing_err)? {
            let entry = entry.map_err(listing_err)?;
            if !entry.file_type().map_err(listing_err)?.is_dir() {
                continue;
            }
            match entry.file_name().into_string() {
                Ok(name) => names.push(name),
                Err(raw) => errs.push(DataError::Invalid {
                    hull: raw.to_string_lossy().into_owned(),
                    msg: "rule 1: hull directory name is not valid UTF-8".to_string(),
                }),
            }
        }
        names.sort();

        let weapons = read(validate::WEAPONS_FILE);
        let mut texts = Vec::with_capacity(names.len());
        for name in &names {
            match read(&hull_file(name)) {
                Ok(text) => texts.push((name.as_str(), text)),
                Err(e) => errs.push(e),
            }
        }
        let weapons = match weapons {
            Ok(text) => text,
            Err(e) => {
                errs.insert(0, e);
                return Err(DataError::from_list(errs));
            }
        };
        if !errs.is_empty() {
            return Err(DataError::from_list(errs));
        }
        let pairs: Vec<(&str, &str)> = texts.iter().map(|(n, t)| (*n, t.as_str())).collect();
        Catalogue::from_yaml(&pairs, &weapons)
    }

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

/// Only called on validated input: every turret weapon exists.
fn convert_hull(raw: RawHull, weapon_names: &[String]) -> HullDef {
    let weapon_id = |name: &str| {
        let idx = weapon_names
            .iter()
            .position(|n| n == name)
            .expect("turret weapons are validated before conversion");
        idx as WeaponId
    };
    let mut hull = HullDef {
        name: raw.name,
        role: raw.role,
        hp: raw.hp,
        mass: raw.mass,
        inertia: raw.inertia,
        speed_cap: raw.speed_cap,
        is_static: raw.is_static,
        shield: raw.shield.map(|s| ShieldDef {
            hp: s.hp,
            regen_rate: s.regen_rate,
            regen_delay: s.regen_delay,
            radius: s.radius,
        }),
        reaction_ticks: raw.reaction_ticks.map(|d| {
            u8::try_from(d).expect("reaction_ticks is validated (rule 10) before conversion")
        }),
        cost: raw.cost,
        collision: raw
            .collision
            .iter()
            .map(|c| Circle {
                pos: vec2(c.pos),
                r: c.r,
            })
            .collect(),
        thrusters: raw
            .thrusters
            .into_iter()
            .map(|t| ThrusterDef {
                id: t.id,
                pos: vec2(t.pos),
                dir: vec2(t.dir).normalized(),
                max_force: t.max_force,
            })
            .collect(),
        turrets: raw
            .turrets
            .into_iter()
            .map(|t| TurretDef {
                weapon: weapon_id(&t.weapon),
                id: t.id,
                pos: vec2(t.pos),
                rest: t.rest_deg * DEG_TO_RAD,
                arc: t.arc_deg * DEG_TO_RAD,
                slew_rate: t.slew_deg_s * DEG_TO_RAD,
            })
            .collect(),
        bays: raw
            .bays
            .into_iter()
            .map(|b| BayDef {
                id: b.id,
                pos: vec2(b.pos),
                dir: vec2(b.dir).normalized(),
            })
            .collect(),
        armour: convert_armour(&raw.armour),
        impact: convert_armour(&raw.impact),
        bound_radius: 0.0,
        shield_radius: 0.0,
        n_power_systems: 0,
        arrival_speed: 0.0,
    };
    hull.derive();
    hull
}

/// Armour or impact arcs in radians, list order kept (validated to tile [-180, 180]).
fn convert_armour(raw: &[RawArmourArc]) -> Vec<ArmourArc> {
    raw.iter()
        .map(|a| ArmourArc {
            from: a.from_deg * DEG_TO_RAD,
            to: a.to_deg * DEG_TO_RAD,
            mult: a.mult,
        })
        .collect()
}

fn convert_weapon((name, w): (String, RawWeapon)) -> WeaponDef {
    let kind = match w.kind {
        RawKind::Bullet => WeaponKind::Bullet,
        RawKind::Beam => WeaponKind::Beam,
        RawKind::Flak => WeaponKind::Flak,
        RawKind::Torpedo => WeaponKind::Torpedo,
    };
    let life_ticks = match kind {
        WeaponKind::Beam => 0,
        _ => life_ticks(w.range, w.speed, w.life_factor),
    };
    WeaponDef {
        name,
        kind,
        speed: w.speed,
        range: w.range,
        damage: w.damage,
        interval: w.interval,
        spread: w.spread_deg * DEG_TO_RAD,
        burst_radius: w.burst_radius,
        fuse_jitter: w.fuse_jitter,
        turn_rate: w.turn_rate_deg_s * DEG_TO_RAD,
        lock_cone: w.lock_cone_deg * DEG_TO_RAD,
        life_factor: w.life_factor,
        life_ticks,
    }
}
