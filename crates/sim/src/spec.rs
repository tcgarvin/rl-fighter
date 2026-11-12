//! The JSON-shaped interface the bindings share (v4, SIM_SPEC §10.3): mission and
//! command specs parsed with serde (PyO3 passes `json.dumps` of a dict, WASM a JSON
//! string), and serialisable views of the mission and commander state. Hull names,
//! not ids, cross the boundary.

use serde::{Deserialize, Serialize};

use crate::command::{
    CapitalStatus, Command, CommandOutcome, CommanderMode, CommanderObs, MAX_SQUADS, Order,
    Outcome, Waypoint,
};
use crate::data::Catalogue;
use crate::math::Vec2;
use crate::mission::{CarrierBattle, ConvoyEscort, ConvoyStatus, Mission, MissionKind};
use crate::state::{Match, NONE};

/// `{"kind": "deathmatch"}`, `{"kind": "carrier_battle", "jump_in": [2, 2]}`,
/// `{"kind": "convoy_escort", "start": [x, y], "jump_point": [x, y], "jump_radius": 40,
/// "charge_ticks": 60, "start_speed_frac": 0.8}`; every parameter optional (defaults:
/// `Mission::standard` for the arena).
#[derive(Clone, Debug, Deserialize, PartialEq)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum MissionSpec {
    Deathmatch {},
    CarrierBattle {
        #[serde(default)]
        jump_in: Option<[u8; 2]>,
    },
    ConvoyEscort {
        #[serde(default)]
        start: Option<[f32; 2]>,
        #[serde(default)]
        jump_point: Option<[f32; 2]>,
        #[serde(default)]
        jump_radius: Option<f32>,
        #[serde(default)]
        charge_ticks: Option<u32>,
        #[serde(default)]
        start_speed_frac: Option<f32>,
    },
}

fn v([x, y]: [f32; 2]) -> Vec2 {
    Vec2::new(x, y)
}

impl MissionSpec {
    /// The mission, defaults filled for an arena of `arena_radius`.
    pub fn build(&self, arena_radius: f32) -> Mission {
        match self {
            MissionSpec::Deathmatch {} => Mission::Deathmatch,
            MissionSpec::CarrierBattle { jump_in } => {
                let mut cb = CarrierBattle::default();
                if let Some(j) = jump_in {
                    cb.jump_in = *j;
                }
                Mission::CarrierBattle(cb)
            }
            MissionSpec::ConvoyEscort {
                start,
                jump_point,
                jump_radius,
                charge_ticks,
                start_speed_frac,
            } => {
                let mut ce = ConvoyEscort::standard(arena_radius);
                if let Some(p) = start {
                    ce.start = v(*p);
                }
                if let Some(p) = jump_point {
                    ce.jump_point = v(*p);
                }
                if let Some(r) = jump_radius {
                    ce.jump_radius = *r;
                }
                if let Some(t) = charge_ticks {
                    ce.charge_ticks = *t;
                }
                if let Some(f) = start_speed_frac {
                    ce.start_speed_frac = *f;
                }
                Mission::ConvoyEscort(ce)
            }
        }
    }

    /// Parse a JSON mission spec, or a bare kind name (`"carrier_battle"`).
    pub fn parse(text: &str) -> Result<MissionSpec, String> {
        let trimmed = text.trim();
        if let Some(kind) = MissionKind::from_name(trimmed) {
            return Ok(MissionSpec::of_kind(kind));
        }
        serde_json::from_str(trimmed).map_err(|e| format!("mission: {e}"))
    }

    pub fn of_kind(kind: MissionKind) -> MissionSpec {
        match kind {
            MissionKind::Deathmatch => MissionSpec::Deathmatch {},
            MissionKind::CarrierBattle => MissionSpec::CarrierBattle { jump_in: None },
            MissionKind::ConvoyEscort => MissionSpec::ConvoyEscort {
                start: None,
                jump_point: None,
                jump_radius: None,
                charge_ticks: None,
                start_speed_frac: None,
            },
        }
    }
}

/// Parse `["scripted", "external"]`-style commander modes (v5: also `"random"`; the
/// learned commander: `"learned"`).
pub fn parse_commanders(names: &[String]) -> Result<[CommanderMode; 2], String> {
    if names.len() != 2 {
        return Err(format!(
            "commanders must name two modes (team 0, team 1), got {}",
            names.len()
        ));
    }
    let one = |n: &str| {
        CommanderMode::from_name(n).ok_or_else(|| {
            format!("unknown commander mode {n:?} (scripted, external, random, learned)")
        })
    };
    Ok([one(&names[0])?, one(&names[1])?])
}

/// `{"kind": "none"}`, `{"kind": "attack", "target": slot}`, `{"kind": "defend",
/// "ward": slot}`, `{"kind": "goto", "point": [x, y], "radius": r, "deadline": tick}`
/// (v6; v8 adds `deadline`, the match tick to arrive by, 0 or absent for none; views
/// always write it).
#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum OrderSpec {
    None {},
    Attack {
        target: u8,
    },
    Defend {
        ward: u8,
    },
    #[serde(rename = "goto")]
    GoTo {
        point: [f32; 2],
        radius: f32,
        #[serde(default)]
        deadline: u32,
    },
}

impl From<Order> for OrderSpec {
    fn from(o: Order) -> Self {
        match o {
            Order::None => OrderSpec::None {},
            Order::Attack { target } => OrderSpec::Attack { target },
            Order::Defend { ward } => OrderSpec::Defend { ward },
            Order::GoTo {
                point,
                radius,
                deadline,
            } => OrderSpec::GoTo {
                point: [point.x, point.y],
                radius,
                deadline,
            },
        }
    }
}

impl From<OrderSpec> for Order {
    fn from(o: OrderSpec) -> Self {
        match o {
            OrderSpec::None {} => Order::None,
            OrderSpec::Attack { target } => Order::Attack { target },
            OrderSpec::Defend { ward } => Order::Defend { ward },
            OrderSpec::GoTo {
                point,
                radius,
                deadline,
            } => Order::GoTo {
                point: v(point),
                radius,
                deadline,
            },
        }
    }
}

/// `{"kind": "launch", "hull": "fighter" | null, "bay": 0 | null}`,
/// `{"kind": "waypoint", "ship": slot, "pos": [x, y] | null}` (null unsets),
/// `{"kind": "squad", "squad": 0, "members": [slots], "order": {...}}`.
#[derive(Clone, Debug, Deserialize, PartialEq)]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum CommandSpec {
    Launch {
        #[serde(default)]
        hull: Option<String>,
        #[serde(default)]
        bay: Option<u8>,
    },
    Waypoint {
        ship: u8,
        #[serde(default)]
        pos: Option<[f32; 2]>,
    },
    Squad {
        squad: u8,
        members: Vec<u8>,
        order: OrderSpec,
    },
}

impl CommandSpec {
    /// The command, hull names resolved against `cat`. Errors on unknown hulls and
    /// member slots that cannot exist (`>= 32`); everything else is the sim's call.
    pub fn to_command(&self, cat: &Catalogue) -> Result<Command, String> {
        Ok(match self {
            CommandSpec::Launch { hull, bay } => Command::Launch {
                hull: match hull {
                    None => None,
                    Some(name) => Some(
                        cat.hull_id(name)
                            .ok_or_else(|| format!("launch: unknown hull {name:?}"))?,
                    ),
                },
                bay: *bay,
            },
            CommandSpec::Waypoint { ship, pos } => Command::Waypoint {
                ship: *ship,
                waypoint: pos.map_or(Waypoint::Unset, |p| Waypoint::At(v(p))),
            },
            CommandSpec::Squad {
                squad,
                members,
                order,
            } => {
                let mut mask = 0u32;
                for &s in members {
                    if s >= 32 {
                        return Err(format!("squad: member slot {s} out of range"));
                    }
                    mask |= 1 << s;
                }
                Command::Squad {
                    squad: *squad,
                    members: mask,
                    order: (*order).into(),
                }
            }
        })
    }

    /// Parse one command object or a list of them.
    pub fn parse_list(text: &str) -> Result<Vec<CommandSpec>, String> {
        let value: serde_json::Value =
            serde_json::from_str(text).map_err(|e| format!("commands: {e}"))?;
        let items = match value {
            serde_json::Value::Array(items) => items,
            one => vec![one],
        };
        items
            .into_iter()
            .map(|item| serde_json::from_value(item).map_err(|e| format!("command: {e}")))
            .collect()
    }
}

fn members_of(mask: u32) -> Vec<u8> {
    (0..32u8).filter(|&s| mask & (1 << s) != 0).collect()
}

#[derive(Clone, Debug, Serialize)]
pub struct SquadView {
    pub index: u8,
    pub members: Vec<u8>,
    pub order: OrderSpec,
}

#[derive(Clone, Debug, Serialize)]
pub struct CapitalView {
    pub slot: u8,
    pub hull: String,
    pub alive: bool,
    pub hp: f32,
    pub max_hp: f32,
    pub shield: f32,
    pub max_shield: f32,
    pub pos: [f32; 2],
    pub vel: [f32; 2],
    pub heading: f32,
}

impl CapitalView {
    fn of(cat: &Catalogue, c: &CapitalStatus) -> CapitalView {
        CapitalView {
            slot: c.slot,
            hull: cat.hull(c.hull).name.clone(),
            alive: c.alive,
            hp: c.hp,
            max_hp: c.max_hp,
            shield: c.shield,
            max_shield: c.max_shield,
            pos: [c.pos.x, c.pos.y],
            vel: [c.vel.x, c.vel.y],
            heading: c.heading,
        }
    }
}

#[derive(Clone, Debug, Serialize)]
pub struct ConvoyView {
    pub total: u8,
    pub en_route: u8,
    pub charging: u8,
    pub escaped: u8,
    pub destroyed: u8,
    pub to_destroy: u8,
    pub to_escape: u8,
    pub progress: f32,
    pub start: [f32; 2],
    pub jump_point: [f32; 2],
    pub jump_radius: f32,
    pub charge_ticks: u32,
}

fn convoy_view(m: &Match, st: &ConvoyStatus) -> Option<ConvoyView> {
    let Mission::ConvoyEscort(ce) = &m.cfg.mission else {
        return None;
    };
    Some(ConvoyView {
        total: st.total,
        en_route: st.en_route,
        charging: st.charging,
        escaped: st.escaped,
        destroyed: st.destroyed,
        to_destroy: st.to_destroy,
        to_escape: st.to_escape,
        progress: st.progress,
        start: [ce.start.x, ce.start.y],
        jump_point: [ce.jump_point.x, ce.jump_point.y],
        jump_radius: ce.jump_radius,
        charge_ticks: ce.charge_ticks,
    })
}

fn by_hull(cat: &Catalogue, counts: &[u8]) -> std::collections::BTreeMap<String, u8> {
    counts
        .iter()
        .enumerate()
        .filter(|&(_, &n)| n > 0)
        .map(|(h, &n)| (cat.hulls[h].name.clone(), n))
        .collect()
}

/// [`CommanderObs`] with hull names (counts keyed by hull name, zeros left out).
#[derive(Clone, Debug, Serialize)]
pub struct CommanderObsView {
    pub team: u8,
    pub tick: u32,
    pub ticks_left: u32,
    pub mission: &'static str,
    pub in_space: std::collections::BTreeMap<String, u8>,
    pub arriving: std::collections::BTreeMap<String, u8>,
    pub reserves: std::collections::BTreeMap<String, u8>,
    pub enemy_visible: std::collections::BTreeMap<String, u8>,
    pub own_carrier: Option<CapitalView>,
    pub enemy_carrier: Option<CapitalView>,
    pub bays_ready: Vec<bool>,
    pub convoy: Option<ConvoyView>,
    pub transports: Vec<CapitalView>,
    pub squads: Vec<SquadView>,
}

impl CommanderObsView {
    pub fn of(m: &Match, cat: &Catalogue, obs: &CommanderObs) -> CommanderObsView {
        CommanderObsView {
            team: obs.team,
            tick: obs.tick,
            ticks_left: obs.ticks_left,
            mission: obs.mission.name(),
            in_space: by_hull(cat, &obs.in_space),
            arriving: by_hull(cat, &obs.arriving),
            reserves: by_hull(cat, &obs.reserves),
            enemy_visible: by_hull(cat, &obs.enemy_visible),
            own_carrier: obs.own_carrier.as_ref().map(|c| CapitalView::of(cat, c)),
            enemy_carrier: obs.enemy_carrier.as_ref().map(|c| CapitalView::of(cat, c)),
            bays_ready: obs.bays_ready.clone(),
            convoy: convoy_view(m, &obs.convoy),
            transports: obs
                .transports
                .iter()
                .map(|c| CapitalView::of(cat, c))
                .collect(),
            squads: squad_views(&obs.squads),
        }
    }
}

fn squad_views(squads: &[crate::command::Squad; MAX_SQUADS]) -> Vec<SquadView> {
    squads
        .iter()
        .enumerate()
        .map(|(k, s)| SquadView {
            index: k as u8,
            members: members_of(s.members),
            order: s.order.into(),
        })
        .collect()
}

/// One command's outcome: `{"command": "launch", "outcome": "launched", "ship": 3,
/// "bay": 0}` or `{"command": "squad", "outcome": "refused", "reason": "no_such_squad"}`.
#[derive(Clone, Debug, Serialize)]
pub struct OutcomeView {
    pub command: &'static str,
    pub outcome: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ship: Option<u8>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub bay: Option<u8>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub reason: Option<&'static str>,
}

impl OutcomeView {
    pub fn of(o: &CommandOutcome) -> OutcomeView {
        let command = match o.command {
            Command::Launch { .. } => "launch",
            Command::Waypoint { .. } => "waypoint",
            Command::Squad { .. } => "squad",
        };
        let mut view = OutcomeView {
            command,
            outcome: "applied",
            ship: None,
            bay: None,
            reason: None,
        };
        match o.outcome {
            Outcome::Applied => {}
            Outcome::Sanitized => view.outcome = "sanitized",
            Outcome::Launched { ship, bay } => {
                view.outcome = "launched";
                view.ship = Some(ship);
                view.bay = Some(bay);
            }
            Outcome::Refused(r) => {
                view.outcome = "refused";
                view.reason = Some(r.name());
            }
        }
        view
    }
}

/// Per-ship mission fields.
#[derive(Clone, Debug, Serialize)]
pub struct ShipMissionView {
    pub slot: u8,
    pub team: u8,
    pub hull: String,
    pub role: String,
    pub docked: bool,
    /// The carrier a docked ship waits in, or -1.
    pub parent: i16,
    /// `"idle"`, `"charging"`, `"departed"`.
    pub jump: &'static str,
    pub charge_until: Option<u32>,
    pub waypoint: Option<[f32; 2]>,
    /// Squad index in its team, or -1.
    pub squad: i8,
}

/// The whole mission and command state of a match (bindings, debugging, the web).
#[derive(Clone, Debug, Serialize)]
pub struct MissionStateView {
    pub mission: &'static str,
    pub end_reason: &'static str,
    pub tick: u32,
    /// v5: the match clock, ticks.
    pub time_limit_ticks: u32,
    /// v5: each team's commander mode (`"scripted"`, `"external"`, `"random"`,
    /// `"learned"`).
    pub commanders: [&'static str; 2],
    pub command_due: bool,
    /// Per team: carrier slot or -1.
    pub carrier: [i16; 2],
    /// Per team: docked reserves in launch order.
    pub hangar: [Vec<u8>; 2],
    /// Per team: per bay, the tick from which it may launch.
    pub bay_ready: [Vec<u32>; 2],
    pub squads: [Vec<SquadView>; 2],
    pub convoy: Option<ConvoyView>,
    pub ships: Vec<ShipMissionView>,
}

fn slot_or_minus_one(s: u8) -> i16 {
    if s == NONE { -1 } else { i16::from(s) }
}

impl MissionStateView {
    pub fn of(m: &Match, cat: &Catalogue) -> MissionStateView {
        use crate::mission::JumpState;
        let bays = |t: usize| {
            let c = m.mission.carrier[t];
            if c == NONE {
                return Vec::new();
            }
            let n = cat.hull(m.ships[usize::from(c)].hull).bays.len();
            m.mission.bay_ready[t][..n].to_vec()
        };
        let ships = m
            .ships
            .iter()
            .map(|s| {
                let hull = cat.hull(s.hull);
                let (jump, until) = match m.mission.jump[usize::from(s.slot)] {
                    JumpState::Idle => ("idle", None),
                    JumpState::Charging { until } => ("charging", Some(until)),
                    JumpState::Departed => ("departed", None),
                };
                ShipMissionView {
                    slot: s.slot,
                    team: s.team,
                    hull: hull.name.clone(),
                    role: hull.role.clone(),
                    docked: s.attach == crate::state::Attach::Docked,
                    parent: slot_or_minus_one(s.parent),
                    jump,
                    charge_until: until,
                    waypoint: match m.command.waypoints[usize::from(s.slot)] {
                        Waypoint::Unset => None,
                        Waypoint::At(p) => Some([p.x, p.y]),
                    },
                    squad: m.squad_of(s.slot).map_or(-1, |k| k as i8),
                }
            })
            .collect();
        MissionStateView {
            mission: m.cfg.mission.kind().name(),
            end_reason: m.mission.end_reason.name(),
            tick: m.tick,
            time_limit_ticks: m.cfg.time_limit_ticks,
            commanders: m.cfg.commanders.map(|c| c.name()),
            command_due: m.command_due(),
            carrier: [
                slot_or_minus_one(m.mission.carrier[0]),
                slot_or_minus_one(m.mission.carrier[1]),
            ],
            hangar: [m.reserves[0].clone(), m.reserves[1].clone()],
            bay_ready: [bays(0), bays(1)],
            squads: [
                squad_views(&m.command.squads[0]),
                squad_views(&m.command.squads[1]),
            ],
            convoy: convoy_view(m, &m.convoy_status()),
            ships,
        }
    }
}

/// One default roster of a mission (`mission::default_rosters`), for the bindings.
#[derive(Clone, Debug, Serialize, PartialEq)]
pub struct MissionRosterView {
    pub name: &'static str,
    pub mission: &'static str,
    /// Hull names per team, slot order.
    pub fleets: [Vec<&'static str>; 2],
}

/// The default rosters of mission `kind` (empty for deathmatch, whose rosters are
/// budget drafts).
pub fn mission_rosters(kind: MissionKind) -> Vec<MissionRosterView> {
    crate::mission::default_rosters(kind)
        .iter()
        .map(|r| MissionRosterView {
            name: r.name,
            mission: kind.name(),
            fleets: [r.fleets[0].to_vec(), r.fleets[1].to_vec()],
        })
        .collect()
}

/// JSON text of `view` (the views above always serialise).
pub fn to_json<T: Serialize>(view: &T) -> String {
    serde_json::to_string(view).expect("views serialise")
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mission_specs_parse_and_fill_defaults() {
        let m = MissionSpec::parse("carrier_battle").unwrap().build(450.0);
        assert_eq!(m, Mission::CarrierBattle(CarrierBattle::default()));
        let m = MissionSpec::parse(r#"{"kind": "convoy_escort", "jump_radius": 55}"#)
            .unwrap()
            .build(450.0);
        let Mission::ConvoyEscort(ce) = m else {
            panic!()
        };
        assert_eq!(ce.jump_radius, 55.0);
        assert_eq!(ce.start, ConvoyEscort::standard(450.0).start);
        assert!(MissionSpec::parse(r#"{"kind": "convoy_escort", "jump": 1}"#).is_err());
        assert!(MissionSpec::parse("duel").is_err());
    }

    #[test]
    fn command_specs_parse() {
        let cmds = CommandSpec::parse_list(
            r#"[{"kind": "launch", "hull": "fighter"}, {"kind": "waypoint", "ship": 0, "pos": null},
                {"kind": "squad", "squad": 1, "members": [2, 3], "order": {"kind": "goto", "point": [1, 2], "radius": 30}}]"#,
        )
        .unwrap();
        assert_eq!(cmds.len(), 3);
        assert!(CommandSpec::parse_list(r#"{"kind": "launch", "hul": 1}"#).is_err());
        let one = CommandSpec::parse_list(r#"{"kind": "launch"}"#).unwrap();
        assert_eq!(
            one[0],
            CommandSpec::Launch {
                hull: None,
                bay: None
            }
        );
    }
}
