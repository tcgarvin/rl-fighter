//! YAML-facing serde structs (SIM_SPEC §4.1, §4.2). Authored units: degrees, seconds.
//! Converted to the runtime types in `data/mod.rs` after validation.

use core::fmt;
use core::marker::PhantomData;

use serde::Deserialize;
use serde::de::{MapAccess, Visitor};

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RawCircle {
    pub pos: [f32; 2],
    pub r: f32,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RawThruster {
    pub id: String,
    pub pos: [f32; 2],
    pub dir: [f32; 2],
    pub max_force: f32,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RawTurret {
    pub id: String,
    pub pos: [f32; 2],
    pub rest_deg: f32,
    pub arc_deg: f32,
    pub slew_deg_s: f32,
    pub weapon: String,
}

#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RawShield {
    pub hp: f32,
    pub regen_rate: f32,
    pub regen_delay: f32,
    pub radius: f32,
}

/// One armour arc as authored (v2): degrees, half-open `[from_deg, to_deg)`.
#[derive(Clone, Copy, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RawArmourArc {
    pub from_deg: f32,
    pub to_deg: f32,
    pub mult: f32,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RawBay {
    pub id: String,
    pub pos: [f32; 2],
    pub dir: [f32; 2],
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RawHull {
    pub name: String,
    pub role: String,
    pub hp: f32,
    pub mass: f32,
    pub inertia: f32,
    pub speed_cap: f32,
    #[serde(rename = "static", default)]
    pub is_static: bool,
    #[serde(default)]
    pub shield: Option<RawShield>,
    /// v2: overrides `MatchConfig.reaction_ticks`; signed so rule 10 reports negatives.
    #[serde(default)]
    pub reaction_ticks: Option<i64>,
    pub cost: u32,
    pub collision: Vec<RawCircle>,
    pub thrusters: Vec<RawThruster>,
    pub turrets: Vec<RawTurret>,
    #[serde(default)]
    pub bays: Vec<RawBay>,
    /// Optional (v2); absent or `[]` is uniform 1x.
    #[serde(default)]
    pub armour: Vec<RawArmourArc>,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "lowercase")]
pub(crate) enum RawKind {
    Bullet,
    Beam,
    Flak,
    Torpedo,
}

fn one() -> f32 {
    1.0
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RawWeapon {
    pub kind: RawKind,
    pub speed: f32,
    pub range: f32,
    pub damage: f32,
    pub interval: f32,
    pub spread_deg: f32,
    #[serde(default)]
    pub burst_radius: f32,
    #[serde(default)]
    pub fuse_jitter: f32,
    #[serde(default)]
    pub turn_rate_deg_s: f32,
    #[serde(default)]
    pub lock_cone_deg: f32,
    #[serde(default = "one")]
    pub life_factor: f32,
}

/// The weapons file as an ordered list: weapon ids are assigned in file order, which a
/// `BTreeMap` would lose. Duplicate names are rejected by the YAML parser itself.
#[derive(Debug)]
pub(crate) struct RawWeapons(pub Vec<(String, RawWeapon)>);

impl<'de> Deserialize<'de> for RawWeapons {
    fn deserialize<D: serde::Deserializer<'de>>(de: D) -> Result<Self, D::Error> {
        struct OrderedVisitor(PhantomData<RawWeapon>);

        impl<'de> Visitor<'de> for OrderedVisitor {
            type Value = RawWeapons;

            fn expecting(&self, f: &mut fmt::Formatter) -> fmt::Result {
                f.write_str("a mapping of weapon name to weapon definition")
            }

            fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<RawWeapons, A::Error> {
                let mut out = Vec::new();
                while let Some(entry) = map.next_entry::<String, RawWeapon>()? {
                    out.push(entry);
                }
                Ok(RawWeapons(out))
            }
        }

        de.deserialize_map(OrderedVisitor(PhantomData))
    }
}
