//! Determinism contract (SIM_SPEC §12): golden hash traces and match independence.
//!
//! The golden files under `tests/golden/` are generated natively and embedded with
//! `include_str!`, so the same test binary run under wasmtime on `wasm32-wasip1`
//! (no filesystem access) checks wasm32 against native bit for bit. Regenerate them
//! with `UPDATE_GOLDEN=1 cargo test -p sim --test determinism` (native only); any
//! change to a golden file is a `SIM_VERSION` bump.
//!
//! Each trace line records, at a sample tick, `state_hash()` plus an auxiliary
//! running digest of every step's outputs (flat events, hit records, rewards and
//! every ship's observation). Those outputs are not part of the state hash, but
//! the browser and the trainer consume them, so they must match across targets too.
//!
//! v4 compatibility (SIM_SPEC §0.2): `v3_compat_*` replay the four v3 scenarios and
//! render them as SIM_VERSION 3 would have — the v3 state hash (v3 hull ids, none of
//! the v4 mission or command state) and the aux digest without the v4 event kinds —
//! and compare with the v3 golden traces kept verbatim under `tests/golden/v3/`. They
//! prove that deathmatch with up to 8 ships is bit-identical to v3 tick by tick
//! (every ship and projectile, every obs, reward, hit and v3 event), which is what
//! lets pilot v1 (trained under v3) fly in v4.

mod common;

use common::asset_catalogue;
use sim::actions::{ACTION_WIDTH, ShipAction};
use sim::data::{Catalogue, HullId};
use sim::events::{EVENT_STRIDE, KIND_COLLISION};
use sim::hash::StateHash;
use sim::mission::{CarrierBattle, ConvoyEscort, EndReason, Mission};
use sim::obs::OBS_DIM;
use sim::rng::Pcg32;
use sim::scripted;
use sim::setup::MatchConfig;
use sim::state::{Match, MatchPhase};
use sim::{SIM_VERSION, StateHasher};

/// Tick budget of the §12 scripted scenarios.
const SCRIPTED_TICKS: u32 = 3000;
/// Sample ticks of the §12 scripted scenarios (those reached before `Over`).
const SCRIPTED_SAMPLES: [u32; 5] = [1, 30, 300, 1000, 3000];

/// Ticks of the random-action scenario: 5 simulated minutes.
const RANDOM_TICKS: u32 = 9000;
/// Sample interval of the random-action scenario.
const RANDOM_SAMPLE_EVERY: u32 = 100;
/// PCG stream of the test's own action generator; differs from the match stream,
/// so the action stream is independent of the match rng.
const ACTION_STREAM: u64 = 0x5eed_ac71_0000_0001;
/// Chance per tick that a ship rolls a new random action row; otherwise it repeats
/// the last one, so ships fly coherent arcs instead of jittering in place.
const REROLL_CHANCE: f32 = 0.125;

fn hull_ids(cat: &Catalogue, names: &[&str]) -> Vec<HullId> {
    names
        .iter()
        .map(|n| cat.hull_id(n).unwrap_or_else(|| panic!("unknown hull {n}")))
        .collect()
}

fn config(cat: &Catalogue, seed: u64, team0: &[&str], team1: &[&str]) -> MatchConfig {
    MatchConfig {
        seed,
        fleets: [hull_ids(cat, team0), hull_ids(cat, team1)],
        ..MatchConfig::default()
    }
}

/// Who chooses each tick's actions.
enum Driver {
    /// `scripted::act` for every ship.
    Scripted,
    /// Sticky uniform random rows from the test's own PCG32.
    Random(RandomActions),
}

/// Uniform random action rows over every head's full range, re-rolled per ship
/// with probability `REROLL_CHANCE` each tick.
struct RandomActions {
    rng: Pcg32,
    rows: Vec<[i8; ACTION_WIDTH]>,
}

impl RandomActions {
    fn new(seed: u64, n_ships: usize) -> Self {
        RandomActions {
            rng: Pcg32::with_stream(seed, ACTION_STREAM),
            rows: vec![[0; ACTION_WIDTH]; n_ships],
        }
    }

    /// Draw in `0..=max`.
    fn draw(&mut self, max: u32) -> i8 {
        (self.rng.next_u32() % (max + 1)) as i8
    }

    /// The next tick's action for every ship, in slot order.
    fn next(&mut self) -> Vec<ShipAction> {
        use sim::actions::{FIRE_MAX, THROTTLE_MAX};
        use sim::actions::{FIRE_OFFSET, POWER_MAX, POWER_OFFSET, SLEW_MAX, SLEW_OFFSET};
        let mut out = Vec::with_capacity(self.rows.len());
        for i in 0..self.rows.len() {
            if self.rng.uniform() < REROLL_CHANCE {
                let mut row = [0i8; ACTION_WIDTH];
                for (k, v) in row.iter_mut().enumerate() {
                    let max = if k < SLEW_OFFSET {
                        THROTTLE_MAX
                    } else if k < FIRE_OFFSET {
                        SLEW_MAX
                    } else if k < POWER_OFFSET {
                        FIRE_MAX
                    } else {
                        POWER_MAX
                    };
                    *v = self.draw(u32::from(max));
                }
                self.rows[i] = row;
            }
            out.push(ShipAction::from_row(&self.rows[i]));
        }
        out
    }
}

/// How a trace renders the state hash and the aux digest.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Flavour {
    /// The current sim version.
    Current,
    /// As SIM_VERSION 3 rendered it (module docs).
    V3,
}

/// The v3 hull ids: the v3 catalogue was fighter, gunship, strafer, sorted by name.
fn v3_hull_id(cat: &Catalogue, hull: HullId) -> u16 {
    match cat.hull(hull).name.as_str() {
        "fighter" => 0,
        "gunship" => 1,
        "strafer" => 2,
        other => panic!("hull {other} did not exist in SIM_VERSION 3"),
    }
}

/// `Match::state_hash` as SIM_VERSION 3 computed it: tick, rng, ships (v3 hull ids;
/// the ship record is unchanged otherwise), projectiles, `proj_next`, phase, winner.
fn v3_state_hash(cat: &Catalogue, m: &Match) -> u64 {
    let mut h = StateHasher::new();
    h.write_u32(m.tick);
    m.rng.hash_into(&mut h);
    for ship in &m.ships {
        let mut s = ship.clone();
        s.hull = v3_hull_id(cat, ship.hull);
        s.hash_into(&mut h);
    }
    m.projectiles.hash_into(&mut h);
    h.write_usize(m.proj_next);
    h.write_u8(m.phase.index());
    h.write_i8(m.winner);
    h.finish()
}

fn state_hash(flavour: Flavour, cat: &Catalogue, m: &Match) -> u64 {
    match flavour {
        Flavour::Current => m.state_hash(),
        Flavour::V3 => v3_state_hash(cat, m),
    }
}

/// Fold one step's outputs into the auxiliary digest (`V3`: v3 event kinds only).
fn digest_outputs(
    aux: &mut StateHasher,
    cat: &Catalogue,
    m: &Match,
    obs: &mut [f32],
    flavour: Flavour,
) {
    let mut flat = Vec::new();
    m.events.encode_into(&mut flat);
    if flavour == Flavour::V3 {
        flat = flat
            .chunks_exact(EVENT_STRIDE)
            .filter(|e| e[0] <= f32::from(KIND_COLLISION))
            .flatten()
            .copied()
            .collect();
    }
    aux.write_u32(flat.len() as u32);
    for &f in &flat {
        aux.write_f32(f);
    }
    aux.write_u32(m.events.dropped);
    aux.write_u32(m.hits().len() as u32);
    for h in m.hits() {
        aux.write_u8(h.shooter);
        aux.write_u8(h.target);
        aux.write_f32(h.damage);
        aux.write_u32(h.fire_tick);
        aux.write_bool(h.shield);
    }
    for &r in m.rewards() {
        aux.write_f32(r);
    }
    for slot in 0..m.ships().len() {
        m.write_obs(cat, slot as u8, obs);
        for &f in obs.iter() {
            aux.write_f32(f);
        }
    }
}

/// Run a scenario and render its trace: a header, `tick state aux` at each sample
/// tick reached, and an `end` line with the final tick, hashes, phase and winner.
fn trace(
    name: &str,
    cfg: &MatchConfig,
    mut driver: Driver,
    ticks: u32,
    sample: impl Fn(u32) -> bool,
    flavour: Flavour,
) -> String {
    let cat = asset_catalogue();
    let mut m = Match::new(&cat, cfg).expect("match setup");
    let mut aux = StateHasher::new();
    let mut obs = vec![0.0f32; OBS_DIM];
    let version = match flavour {
        Flavour::Current => SIM_VERSION,
        Flavour::V3 => 3,
    };
    let mut out = format!(
        "# sim golden trace {name} (SIM_VERSION {version}); regenerate with UPDATE_GOLDEN=1\n\
         # tick state_hash aux_digest; end tick state_hash aux_digest phase winner\n"
    );
    while m.tick() < ticks && m.phase() == MatchPhase::Running {
        let actions: Vec<ShipAction> = match &mut driver {
            Driver::Scripted => (0..m.ships().len())
                .map(|i| scripted::act(&m, &cat, i as u8))
                .collect(),
            Driver::Random(r) => r.next(),
        };
        for (i, a) in actions.into_iter().enumerate() {
            m.set_action(i as u8, a);
        }
        m.step(&cat);
        digest_outputs(&mut aux, &cat, &m, &mut obs, flavour);
        if sample(m.tick()) {
            out += &format!(
                "{} {:016x} {:016x}\n",
                m.tick(),
                state_hash(flavour, &cat, &m),
                aux.finish()
            );
        }
    }
    let phase = match m.phase() {
        MatchPhase::Running => "running",
        MatchPhase::Over => "over",
    };
    out += &format!(
        "end {} {:016x} {:016x} {phase} {}\n",
        m.tick(),
        state_hash(flavour, &cat, &m),
        aux.finish(),
        m.winner()
    );
    if flavour == Flavour::Current && cfg.mission != Mission::Deathmatch {
        out += &format!("reason {}\n", m.mission.end_reason.name());
    }
    out
}

/// Compare `actual` with the embedded golden text, or rewrite the golden file
/// when `UPDATE_GOLDEN=1` (native only: wasip1 tests have no filesystem).
fn check_golden(file: &str, embedded: &str, actual: &str) {
    if std::env::var("UPDATE_GOLDEN").is_ok_and(|v| v == "1") {
        let path = format!("{}/tests/golden/{file}", env!("CARGO_MANIFEST_DIR"));
        std::fs::write(&path, actual).unwrap_or_else(|e| panic!("writing {path}: {e}"));
        return;
    }
    assert!(
        !embedded.trim().is_empty(),
        "golden {file} is empty; generate it with UPDATE_GOLDEN=1 (native)"
    );
    if embedded != actual {
        let first_diff = embedded
            .lines()
            .zip(actual.lines())
            .find(|(g, a)| g != a)
            .map_or_else(
                || "line count differs".to_string(),
                |(g, a)| format!("golden `{g}` vs actual `{a}`"),
            );
        panic!(
            "determinism trace {file} diverged ({first_diff}).\n\
             If the sim change is intended, regenerate with UPDATE_GOLDEN=1 and bump \
             SIM_VERSION.\n--- actual ---\n{actual}"
        );
    }
}

fn scripted_trace(name: &str, cfg: &MatchConfig, flavour: Flavour) -> String {
    trace(
        name,
        cfg,
        Driver::Scripted,
        SCRIPTED_TICKS,
        |t| SCRIPTED_SAMPLES.contains(&t),
        flavour,
    )
}

fn duel_trace(flavour: Flavour) -> String {
    let cat = asset_catalogue();
    let cfg = config(&cat, 7, &["fighter"], &["fighter"]);
    scripted_trace("duel_fighter_s7", &cfg, flavour)
}

fn mixed_2v2_trace(flavour: Flavour) -> String {
    let cat = asset_catalogue();
    let cfg = config(&cat, 11, &["fighter", "strafer"], &["gunship", "fighter"]);
    scripted_trace("2v2_mixed_s11", &cfg, flavour)
}

fn mixed_3v3_trace(flavour: Flavour) -> String {
    let cat = asset_catalogue();
    let cfg = config(
        &cat,
        13,
        &["fighter", "strafer", "gunship"],
        &["gunship", "fighter", "strafer"],
    );
    scripted_trace("3v3_mixed_s13", &cfg, flavour)
}

/// Random actions keep every hull flying, slewing, firing and switching power for
/// the full time limit, so the trace covers far more of the sim than scripted
/// fights that end in a few hundred ticks.
fn random_3v3_trace(flavour: Flavour) -> String {
    let cat = asset_catalogue();
    let mut cfg = config(
        &cat,
        17,
        &["fighter", "strafer", "gunship"],
        &["gunship", "fighter", "strafer"],
    );
    cfg.time_limit_ticks = RANDOM_TICKS;
    let n_ships = cfg.fleets[0].len() + cfg.fleets[1].len();
    let driver = Driver::Random(RandomActions::new(17, n_ships));
    trace(
        "3v3_random_s17",
        &cfg,
        driver,
        RANDOM_TICKS,
        |t| t % RANDOM_SAMPLE_EVERY == 0,
        flavour,
    )
}

#[test]
fn golden_duel_fighter_seed7() {
    check_golden(
        "duel_fighter_s7.txt",
        include_str!("golden/duel_fighter_s7.txt"),
        &duel_trace(Flavour::Current),
    );
}

#[test]
fn golden_2v2_mixed_seed11() {
    check_golden(
        "2v2_mixed_s11.txt",
        include_str!("golden/2v2_mixed_s11.txt"),
        &mixed_2v2_trace(Flavour::Current),
    );
}

#[test]
fn golden_3v3_mixed_seed13() {
    check_golden(
        "3v3_mixed_s13.txt",
        include_str!("golden/3v3_mixed_s13.txt"),
        &mixed_3v3_trace(Flavour::Current),
    );
}

#[test]
fn golden_3v3_random_actions_seed17() {
    check_golden(
        "3v3_random_s17.txt",
        include_str!("golden/3v3_random_s17.txt"),
        &random_3v3_trace(Flavour::Current),
    );
}

/// Compare with a v3 golden file, never rewritten (it is the v3 record).
fn check_v3(embedded: &str, actual: &str) {
    assert_eq!(
        embedded, actual,
        "deathmatch diverged from SIM_VERSION 3 (pilot v1 compatibility, SIM_SPEC §0.2)"
    );
}

#[test]
fn v3_compat_duel_fighter_seed7() {
    check_v3(
        include_str!("golden/v3/duel_fighter_s7.txt"),
        &duel_trace(Flavour::V3),
    );
}

#[test]
fn v3_compat_2v2_mixed_seed11() {
    check_v3(
        include_str!("golden/v3/2v2_mixed_s11.txt"),
        &mixed_2v2_trace(Flavour::V3),
    );
}

#[test]
fn v3_compat_3v3_mixed_seed13() {
    check_v3(
        include_str!("golden/v3/3v3_mixed_s13.txt"),
        &mixed_3v3_trace(Flavour::V3),
    );
}

#[test]
fn v3_compat_3v3_random_actions_seed17() {
    check_v3(
        include_str!("golden/v3/3v3_random_s17.txt"),
        &random_3v3_trace(Flavour::V3),
    );
}

/// Ticks budget of the mission scenarios (both end well before it).
const MISSION_TICKS: u32 = 9000;
/// Sample interval of the mission scenarios.
const MISSION_SAMPLE_EVERY: u32 = 300;

/// Carrier battle, scripted pilots and stub commanders on both sides: carriers,
/// jump-ins, launches from both bays, squad orders, to a carrier kill.
pub fn carrier_battle_config(cat: &Catalogue, seed: u64) -> MatchConfig {
    let wing = [
        "fighter", "strafer", "fighter", "gunship", "fighter", "fighter",
    ];
    let mut team0 = vec!["carrier"];
    team0.extend(wing);
    let mut cfg = config(cat, seed, &team0, &team0);
    cfg.mission = Mission::CarrierBattle(CarrierBattle::default());
    cfg.time_limit_ticks = MISSION_TICKS;
    cfg
}

/// Convoy escort: four freighters and three escorts against six attackers.
pub fn convoy_config(cat: &Catalogue, seed: u64) -> MatchConfig {
    let mut cfg = config(
        cat,
        seed,
        &[
            "freighter",
            "freighter",
            "freighter",
            "freighter",
            "fighter",
            "strafer",
            "fighter",
        ],
        &[
            "fighter", "fighter", "strafer", "gunship", "fighter", "strafer",
        ],
    );
    cfg.mission = Mission::ConvoyEscort(ConvoyEscort::standard(cfg.arena_radius));
    cfg.time_limit_ticks = MISSION_TICKS;
    cfg
}

fn mission_trace(name: &str, cfg: &MatchConfig) -> String {
    trace(
        name,
        cfg,
        Driver::Scripted,
        MISSION_TICKS,
        |t| t % MISSION_SAMPLE_EVERY == 0,
        Flavour::Current,
    )
}

#[test]
fn golden_carrier_battle_seed23() {
    let cat = asset_catalogue();
    let actual = mission_trace("carrier_battle_s23", &carrier_battle_config(&cat, 23));
    check_golden(
        "carrier_battle_s23.txt",
        include_str!("golden/carrier_battle_s23.txt"),
        &actual,
    );
}

#[test]
fn golden_convoy_escort_seed29() {
    let cat = asset_catalogue();
    let actual = mission_trace("convoy_escort_s29", &convoy_config(&cat, 29));
    check_golden(
        "convoy_escort_s29.txt",
        include_str!("golden/convoy_escort_s29.txt"),
        &actual,
    );
}

/// The two mission scenarios end properly (not at the budget) with a reason.
#[test]
fn mission_scenarios_end_with_a_reason() {
    let cat = asset_catalogue();
    for cfg in [carrier_battle_config(&cat, 23), convoy_config(&cat, 29)] {
        let mut m = Match::new(&cat, &cfg).expect("setup");
        while m.phase() == MatchPhase::Running && m.tick() < MISSION_TICKS {
            for i in 0..m.ships().len() {
                let a = scripted::act(&m, &cat, i as u8);
                m.set_action(i as u8, a);
            }
            m.step(&cat);
        }
        assert_eq!(m.phase(), MatchPhase::Over, "{:?}", cfg.mission.kind());
        assert_ne!(m.mission.end_reason, EndReason::NotOver);
        assert_ne!(
            m.mission.end_reason,
            EndReason::TimeLimit,
            "{:?}",
            cfg.mission.kind()
        );
    }
}

/// Two same-seed matches given the same actions stay hash-equal every tick while a
/// third, differently seeded match is stepped between them: no shared state.
#[test]
fn same_seed_matches_are_independent_of_interleaved_match() {
    let cat = asset_catalogue();
    let fleets: (&[&str], &[&str]) = (&["fighter", "strafer"], &["gunship", "fighter"]);
    let mut a = Match::new(&cat, &config(&cat, 21, fleets.0, fleets.1)).expect("setup");
    let mut b = Match::new(&cat, &config(&cat, 21, fleets.0, fleets.1)).expect("setup");
    let mut c = Match::new(&cat, &config(&cat, 22, fleets.0, fleets.1)).expect("setup");
    let mut shared = RandomActions::new(5, 4);
    let mut other = RandomActions::new(6, 4);
    let mut diverged_from_c = false;
    for _ in 0..1500 {
        let acts = shared.next();
        for (i, act) in acts.iter().enumerate() {
            a.set_action(i as u8, *act);
        }
        a.step(&cat);
        for (i, act) in other.next().into_iter().enumerate() {
            c.set_action(i as u8, act);
        }
        c.step(&cat);
        for (i, act) in acts.iter().enumerate() {
            b.set_action(i as u8, *act);
        }
        b.step(&cat);
        assert_eq!(a.state_hash(), b.state_hash(), "tick {}", a.tick());
        diverged_from_c |= a.state_hash() != c.state_hash();
    }
    assert!(diverged_from_c, "the third match should differ");
}
