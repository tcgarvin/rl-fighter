# RL Fighter — M1 Simulation Spec (Rust core + Python bindings)

Status: implementation spec for milestone M1, written 2026-10-28; revised the same
day to **SIM_VERSION 2** (§0) after M1 landed. `docs/DESIGN.md` is the source of
truth for direction; this file pins the decisions implementers need. When the two
disagree, fix this file and note it in the lab journal.

Scope of M1: **M1a** `crates/sim` (three hulls, thrusters, power split, turrets, four
weapon kinds, shields, compound-circle hits, ship collisions, arena, arrival, skirmish
termination, events, obs, rewards, scripted fighter) and **M1b** `crates/sim-py`
(batched VecEnv over N matches, zero-copy numpy buffers, throughput benchmark). The
`crates/sim-wasm` crate must build and pass the native-vs-WASM determinism test, but
has no renderer yet (that is M2).

Not in M1 (but the data model leaves room, see §3.4): bomber, carrier, station, bays,
docking/repair, attached/tethered ships, friendly fire, damage types, collision
damage, ammo/heat, GLB-derived geometry.

---

## 0. v2 changes (SIM_VERSION 1 → 2)

Agreed after M1 (WP0–WP10) landed and before the learnability spike
(`lab/runs/2026-10-28-learnability-spike/plan.md`). Everything below lands together
as one version bump, so the golden traces regenerate once. The sections that follow
are already written for v2; this table is the diff and the reasons.

| # | change | why | sections |
|---|---|---|---|
| 1 | Damping a third lighter: linear `vel *= 0.99667` per tick (was 0.995), angular `omega *= 0.96` (was 0.94). Soft speed cap unchanged. Global consts, not hull data. | v1 ships stopped and stopped turning too eagerly; coasting and rotational momentum should matter | §5.1 |
| 2 | Throttle ramp: each thruster holds a continuous level in `[0, 1]` that the action nudges down/holds/up at 5 /s (0 → full in 6 ticks). Force = `max_force · level · P_e`. Levels are state (hashed) and in the obs. | Removes the on/off bang-bang look; turning (RCS) ramps for free; the policy's throttle heads become rate commands, which BC from a script still reproduces | §3, §5.1, §7.1, §7.2, §11 |
| 3 | Reaction delay: an action takes effect `reaction_ticks` after it is chosen (default 2 ticks ≈ 67 ms), through a per-ship FIFO. `MatchConfig.reaction_ticks`, optional hull override. The queued actions are in the obs so the state stays Markov. | Pilots, not servos: instantaneous reaction makes jitter-aiming optimal and looks robotic; the lab sweeps 0/2/4 | §2.1, §3, §4.1, §5 stage 3, §7.1, §7.2, §8, §11 |
| 4 | Directional armour: optional hull `armour` arcs by body-frame bearing of the impact point; hull damage only. Fighter: nose 0.5×, flank 1×, engine 1.5×. | Makes geometry matter (head-on passes are not the whole fight; getting on the tail pays); the renderer can show glancing hits | §4.1, §4.4, §5.4, §8, §9 |
| 5 | Shield-first hit testing: while `shield > 0`, projectiles, beams and flak test against the shield circle, not the hull circles. A projectile's hit point is where its segment first enters the target shape (as beams), so armour bearings and bubble normals are where the shot crossed. | A shield that is only tested on hull contact is a hit-point pool, not a bubble; the `ShieldHit` point/normal now lie where the shot really crossed | §5.3, §6 |
| 6 | Vision: all other ships (7 slots by distance) and 8 hostile projectiles sorted by a threat score, plus thruster levels and the pending-action queue in the obs. `OBS_DIM` 204 → 385. | Nearest-3/4 truncation hid teammates and incoming fire in 2v2+; the extra blocks are what items 2 and 3 need for Markov obs | §7.2, §10.1 |
| 7 | `act_mask` semantics fixed (WP10 found the gap): a masked row is ignored entirely, including slew and power, and the mask is computed for the tick the action will apply on (after the reaction delay). | PPO log-prob masking is only correct when "masked" and "had no effect" coincide; v1 masked the last locked tick wrongly and let slew/power leak through the lock | §5 stage 3, §7.1 |
| 8 | Credit: `HitRecord` and the hits buffer carry `decision_tick` (the obs tick on which the firing action was chosen) alongside `fire_tick`. | With a reaction delay the fire step is `reaction_ticks + 1` before the shot; the Python adapter maps credit to the decision step | §5.3, §8, §10.1 |
| 9 | Balance starting point for the spike's duel sweep (data only): gauss 3 dmg / 0.20 s / 220 m / 200 m/s / 1.0° spread; fighter 80 hp. The sweep (plan §2.3) may move these; the tables in §4 are updated when it does. | v1 duels end on the first head-on pass (plan §2.1) | §4.1, §4.2 |

Also folded in from what WP1–WP10 built (deviations the packages recorded in code
comments; the spec now matches them): hull roles are `fighter` / `skirmisher`
(strafer) / `anchor` (gunship); the scripted turn gain is 10, not 2.5; `Projectile`
carries its `weapon` id; `Match` has `shots_fired`, `outside_arena`, `dropped_hits`;
the VecEnv has `dt`, `step(actions=None)` and `events()`; the determinism suite has
four golden scenarios including a random-action one; the golden traces also digest
every step's events, hits, rewards and obs.

---

## 1. Conventions

- Units: metres, kilograms, seconds, radians. World frame: +x right, +y up, angles CCW
  from +x. Body frame: +x forward, +y port (left). `to_world(p) = R(heading)·p + pos`.
- Fixed step `DT = 1/30 s`. All sim arithmetic is `f32`. Transcendentals only via
  `libm` (`sinf, cosf, atan2f, sqrtf, hypotf, expf`); never `f32::sin` etc., never
  `mul_add`. Sums are in fixed order; no parallelism inside a match.
- Times stored as ticks (`u32`); durations in YAML are seconds, converted to ticks on
  load with `ticks = (s * 30).round()`.
- RNG: PCG32 (`rand_pcg::Pcg32`, `rand_core` only; no `thread_rng`), one stream per
  match, seeded as `Pcg32::new(seed, 0xda3e39cb94b95bdb)`. Uniform floats via
  `(next_u32() >> 8) as f32 * 2^-24`.
- Indices: `ShipIdx = u8` (slot within a match), `NONE = u8::MAX`. `HullId = u16`,
  `WeaponId = u16` (indices into the catalogue, stable for a loaded catalogue).

## 2. Workspace layout

```
Cargo.toml                 # [workspace] members = crates/*; resolver = "2"
crates/sim/                # no I/O by default; `fs` feature adds directory loading
  Cargo.toml               # deps: libm, serde, serde-saphyr, rand_core, rand_pcg
  src/lib.rs               # re-exports; pub const SIM_VERSION: u32 = 2
  src/math.rs              # Vec2, wrap_angle, rot, clamp, cross
  src/rng.rs               # Pcg32 wrapper: uniform(), range(lo,hi), split(seed,i,k)
  src/hash.rs              # FNV-1a 64 over f32/int bit patterns (StateHasher)
  src/data/mod.rs          # Catalogue, DataError, load from YAML text (+ load_dir under `fs`)
  src/data/hull.rs         # HullDef, ThrusterDef, TurretDef, ShieldDef, ArmourArc, BayDef, Circle
  src/data/raw.rs          # serde structs for the YAML (degrees, seconds)
  src/data/weapon.rs       # WeaponDef, WeaponKind
  src/data/validate.rs     # validation rules (§4.4)
  src/state.rs             # Match, Ship, Projectile, MatchPhase, consts MAX_*
  src/actions.rs           # ShipAction, ACTION_WIDTH, decode from i8 row, reaction queue, masks
  src/power.rs             # POWER_TARGETS table, slew, multipliers
  src/physics.rs           # throttle ramp, thruster forces, integration, drag, soft cap
  src/turrets.rs           # slew, fire gating, muzzle pose
  src/weapons.rs           # spawn bullet/flak/torpedo, resolve beam
  src/projectiles.rs       # advance, torpedo steer, swept circle tests (shield or hull), flak burst
  src/damage.rs            # apply_damage (shield → armour → hull), same_entity, regen
  src/collision.rs         # ship–ship compound circle impulse
  src/arena.rs             # boundary push + drain
  src/arrival.rs           # schedule_arrivals, process_arrivals
  src/setup.rs             # MatchConfig, Fleet, Match::new
  src/step.rs              # Match::step (order in §5), termination, winner
  src/events.rs            # Event enum, EventBuf, flat encoding
  src/obs.rs               # obs layout consts + write_obs (§7)
  src/reward.rs            # per-ship reward + HitRecord accumulation (§8)
  src/scripted/mod.rs      # allocate_thrusters, act(match, ship) dispatch
  src/scripted/fighter.rs  # fighter controller (§11)
  tests/                   # integration tests per work package (§12)
  tests/golden/            # determinism hash traces (§9)
crates/sim-py/             # pyo3 0.30 + numpy 0.30 + rayon; maturin; module `rlf_sim`
  src/lib.rs               # #[pymodule]; VecEnv class; Catalogue loading; bench
crates/sim-wasm/           # wasm-bindgen; WasmMatch wrapper (one match)
assets/hulls/<name>/hull.yaml   # fighter, strafer, gunship
assets/weapons.yaml
spacefight/env/rust_env.py # thin Python wrapper over rlf_sim.VecEnv (WP10)
tools/bench_env.py         # throughput benchmark (WP9)
```

`crates/sim` compiles for `x86_64`, `wasm32-wasip1` (tests under wasmtime) and
`wasm32-unknown-unknown` (via sim-wasm). It must not use `std::time`, `std::fs`
(outside `fs` feature), `HashMap` with random state (use `BTreeMap` or sorted `Vec`),
or floats from `std` math.

### 2.1 Key public types (crates/sim)

```rust
pub struct Catalogue { pub hulls: Vec<HullDef>, pub weapons: Vec<WeaponDef> }
impl Catalogue {
    pub fn from_yaml(hulls: &[(&str, &str)], weapons_yaml: &str) -> Result<Self, DataError>;
    #[cfg(feature = "fs")] pub fn load_dir(assets: &Path) -> Result<Self, DataError>;
    pub fn hull_id(&self, name: &str) -> Option<HullId>;
}
pub struct MatchConfig {
    pub seed: u64, pub arena_radius: f32,            // default 450.0
    pub time_limit_ticks: u32,                       // default 2700 (90 s)
    pub reaction_ticks: u8,                          // default 2; ≤ MAX_REACTION_TICKS (v2, §5 stage 3)
    pub fleets: [Vec<HullId>; 2],                    // team 0, team 1; ≤ MAX_SHIPS total
}
pub struct Match { /* §3 */ }
impl Match {
    pub fn new(cat: &Catalogue, cfg: &MatchConfig) -> Result<Match, SetupError>;
    pub fn set_action(&mut self, ship: ShipIdx, a: ShipAction);   // the action chosen now (enqueued next step)
    pub fn step(&mut self, cat: &Catalogue);         // one tick; fills events + step stats
    pub fn tick(&self) -> u32;  pub fn phase(&self) -> MatchPhase;  pub fn winner(&self) -> i8;
    pub fn ships(&self) -> &[Ship];  pub fn projectiles(&self) -> &[Projectile];
    pub fn events(&self) -> &[Event];                // events of the last step
    pub fn hits(&self) -> &[HitRecord];              // hits landed during the last step
    pub fn write_obs(&self, cat: &Catalogue, ship: ShipIdx, out: &mut [f32]); // len OBS_DIM
    pub fn rewards(&self) -> &[f32];                 // len n_ships, for the last step
    pub fn act_mask(&self, ship: ShipIdx) -> bool;   // §7.1: will the action chosen now be applied?
    pub fn state_hash(&self) -> u64;
}
pub enum MatchPhase { Running, Over }
```

## 3. State

Design choice: **AoS per match, rayon over matches.** Each match has 1–8 ships and a
few dozen projectiles; the hot loop is a short per-match tick, identical in native
and WASM. SoA across matches (the v1 layout) forces every match to the same ship
count and splits the code path between WASM (one match) and native. Obs, actions and
rewards are written into flat batched numpy buffers by the bindings (§10), which is
where SoA matters.

```rust
pub const MAX_SHIPS: usize = 8;      // per match (both teams)
pub const MAX_THRUSTERS: usize = 8;  // carrier has 7
pub const MAX_TURRETS: usize = 6;    // station has 6
pub const MAX_PROJECTILES: usize = 256; // pool per match, oldest overwritten
pub const MAX_EVENTS: usize = 512;   // per step; excess dropped (counted)
pub const MAX_HITS: usize = 64;      // HitRecords per step
pub const MAX_REACTION_TICKS: usize = 4; // reaction queue capacity (v2); lab sweeps 0/2/4

pub struct Ship {
    pub hull: HullId, pub team: u8, pub slot: ShipIdx,
    pub pos: Vec2, pub vel: Vec2, pub heading: f32, pub omega: f32,
    pub hp: f32, pub shield: f32, pub last_hit_tick: u32,   // u32::MAX = never
    pub alive: bool, pub present: bool,
    pub arrive_tick: u32, pub control_lock_until: u32,
    pub thrust_level: [f32; MAX_THRUSTERS],                 // v2: continuous [0,1], ramped by the action (§5.1)
    pub turret_angle: [f32; MAX_TURRETS],                   // body-frame, radians
    pub turret_cooldown: [f32; MAX_TURRETS],                // seconds remaining
    pub power: [f32; 3], pub power_target: [f32; 3],        // shields, engines, weapons
    pub reaction_ticks: u8,                                 // v2: effective delay d (hull override or cfg)
    pub queue: [ShipAction; MAX_REACTION_TICKS],            // v2: FIFO, queue[0] applies next; slots ≥ d are IDLE
    // Reserved for M5+ (always NONE / None in M1; included in the hash):
    pub parent: ShipIdx, pub attach: Attach,                // Attach::{None, Docked, Mounted, Tethered}
}
pub struct Projectile {
    pub alive: bool, pub kind: WeaponKind, pub weapon: WeaponId, pub team: u8, pub owner: ShipIdx,
    pub pos: Vec2, pub vel: Vec2, pub speed: f32, pub damage: f32,
    pub life_ticks: u32, pub fire_tick: u32,
    pub decision_tick: u32,                // v2: obs tick on which the firing action was chosen (§8)
    pub target: ShipIdx,                   // torpedo only
}
pub struct Match {
    pub cfg: MatchConfig, pub tick: u32, pub rng: Pcg32, pub phase: MatchPhase,
    pub winner: i8,                        // -1 draw, 0/1 team, -2 not over
    pub ships: Vec<Ship>,                  // team 0 slots first, then team 1
    pub projectiles: [Projectile; MAX_PROJECTILES], pub proj_next: usize,
    pub pending: [ShipAction; MAX_SHIPS],  // set_action input: chosen now, enqueued in the next step's stage 3
    pub applied: [ShipAction; MAX_SHIPS],  // v2: the action stages 5–7 use this tick (dequeued + sanitised), not hashed
    pub events: EventBuf, pub hits: Vec<HitRecord>, pub rewards: [f32; MAX_SHIPS],
    pub shots_fired: [u16; MAX_SHIPS], pub outside_arena: [bool; MAX_SHIPS], pub dropped_hits: u32,
    pub reserves: [Vec<ShipIdx>; 2],       // reserved for bays (empty in M1)
}
```

`pending` and `applied` are per-step inputs/outputs, not simulation state, and are
not hashed; `queue` and `thrust_level` are state and are hashed (§12).

### 3.4 Room for later hulls

- `HullDef.static: bool` — skip integration; infinite mass in collisions. Parsed and
  honoured in M1 (tested with a synthetic hull), no shipped static hull.
- `HullDef.bays: Vec<BayDef>` — parsed, validated, unused. `Match.reserves` exists.
- `Ship.parent / attach` — hit tests and collisions must skip pairs where one is the
  other's parent (`same_entity(a,b)` helper in `damage.rs`, used by every hit path).
  Ships with `attach != None` are `present == false` in M1 semantics.

## 4. Data files

### 4.1 Hull YAML (`assets/hulls/<name>/hull.yaml`)

```yaml
name: fighter            # must equal directory name
role: fighter            # free string; the scripted controller dispatches on it (§11)
hp: 80                   # v2 balance starting point (was 60); the spike sweep may move it
mass: 10.0
inertia: 55.0            # explicit in M1; derived from GLB footprint later
speed_cap: 60.0
static: false            # optional, default false
shield: null             # or {hp, regen_rate, regen_delay, radius}
reaction_ticks: null     # optional (v2); an integer overrides MatchConfig.reaction_ticks for this hull
armour:                  # optional (v2); absent or [] → uniform 1×. Arcs by body-frame bearing of
  - {from_deg: -180, to_deg: -135, mult: 1.5}   # the impact point: engine
  - {from_deg: -135, to_deg: -45,  mult: 1.0}   # starboard flank
  - {from_deg: -45,  to_deg: 45,   mult: 0.5}   # nose
  - {from_deg: 45,   to_deg: 135,  mult: 1.0}   # port flank
  - {from_deg: 135,  to_deg: 180,  mult: 1.5}   # engine
cost: 10                 # supply cost; unused in M1
collision:               # body frame; ≥1 circle
  - {pos: [2.0, 0.0], r: 2.4}
  - {pos: [-2.2, 0.0], r: 2.6}
thrusters:               # dir = direction the force pushes the ship (unit, body frame)
  - {id: thruster.main.0, pos: [-4.6, 0.0], dir: [1, 0], max_force: 900}
  - {id: thruster.rcs.fl, pos: [2.2, 2.3],  dir: [0, -1], max_force: 160}
  - {id: thruster.rcs.fr, pos: [2.2, -2.3], dir: [0, 1],  max_force: 160}
  - {id: thruster.rcs.rl, pos: [-2.8, 2.3], dir: [0, -1], max_force: 160}
  - {id: thruster.rcs.rr, pos: [-2.8, -2.3],dir: [0, 1],  max_force: 160}
turrets:                 # arc_deg 0 = fixed gun (slew ignored)
  - {id: turret.nose, pos: [3.8, 0.0], rest_deg: 0, arc_deg: 0, slew_deg_s: 0, weapon: gauss}
bays: []                 # [{id, pos, dir}], parsed, unused in M1
```

M1 hull values (from `prototypes/story/hulls.js`; collision circles are new; v2
changes in bold):

| hull | role | hp | mass | inertia | speed_cap | shield (hp/regen/delay/radius) | armour (v2) | collision circles (pos, r) |
|---|---|---|---|---|---|---|---|---|
| fighter | fighter | **80** | 10 | 55 | 60 | none | **nose 0.5 / flank 1.0 / engine 1.5** (arcs as above) | (2.0,0) 2.4; (-2.2,0) 2.6 |
| strafer | skirmisher | 70 | 11 | 75 | 50 | 40 / 8 / 3 / 7.5 | uniform (absent) | (0,0) 3.2; (0,3.6) 2.4; (0,-3.6) 2.4 |
| gunship | anchor | 320 | 60 | 2200 | 24 | 140 / 12 / 4 / 11 | uniform (absent) | (4.5,0) 3.6; (0,0) 4.6; (-4.5,0) 3.8 |

Thrusters and turrets are copied verbatim from `hulls.js` (`force` → `max_force`,
`rest/arc/slew` → `rest_deg/arc_deg/slew_deg_s`; drop `size`/`height`, they are
render-only). Strafer: main 380 + four laterals 420, nose laser. Gunship: two mains
1700, four RCS 500; turrets fore flak (rest 0, arc 240, slew 120), port gauss (90,
220, 90), starboard gauss (-90, 220, 90). No hull sets `reaction_ticks` in v2 (all
use the match default).

**Armour (v2).** `armour` is a list of arcs `{from_deg, to_deg, mult}` over the
body-frame bearing `b = wrap(atan2(point − ship.pos) − heading)` of the impact point
(§5.4). Stored as `HullDef.armour: Vec<ArmourArc { from: f32, to: f32, mult: f32 }>`
in radians, in list order; empty means uniform 1×. Lookup: the arc with
`from <= b < to`; `b == +π` (the only bearing no half-open arc covers) uses the last
arc. Multipliers apply to hull damage only, never to shields.

Derived on load (stored in `HullDef`): `bound_radius = max(|c.pos| + c.r)`,
`shield_radius = shield.radius` or `bound_radius`, `has_shield`, `n_power_systems`
(3 if shield else 2), `arrival_speed = 1.4 * speed_cap`, `reaction_ticks:
Option<u8>` (None = use the match config).

### 4.2 Weapon YAML (`assets/weapons.yaml`)

```yaml
# gauss is the v2 balance starting point for the spike's duel sweep (plan §2.3);
# v1 was speed 240, range 300, damage 6, interval 0.16, spread 0.6.
gauss:   {kind: bullet,  speed: 200, range: 220, damage: 3,  interval: 0.20, spread_deg: 1.0}
laser:   {kind: beam,    speed: 0,   range: 180, damage: 3,  interval: 0.10, spread_deg: 0.6}
flak:    {kind: flak,    speed: 180, range: 230, damage: 4,  interval: 0.09, spread_deg: 3.5,
          burst_radius: 14, fuse_jitter: 0.4}
torpedo: {kind: torpedo, speed: 95,  range: 340, damage: 55, interval: 3.2,  spread_deg: 0,
          turn_rate_deg_s: 40, lock_cone_deg: 30, life_factor: 1.3}
```

Optional keys default to 0 (`burst_radius`, `fuse_jitter`, `turn_rate_deg_s`,
`lock_cone_deg`) or 1 (`life_factor`). `magazine`/`reload` are **not** in M1 (§6).
Weapon ids are assigned in file order.

### 4.3 Loading

`Catalogue::from_yaml` takes `(name, yaml_text)` pairs plus the weapons text, so the
WASM bundle can hand over the same strings. Under the `fs` feature,
`Catalogue::load_dir(assets)` reads `assets/weapons.yaml` and every
`assets/hulls/*/hull.yaml`, sorted by directory name (hull ids are stable across
machines). Parsing uses `serde-saphyr` (`serde_saphyr::from_str`; pure Rust, maintained; `serde_yaml` is deprecated) with `#[serde(deny_unknown_fields)]`.

### 4.4 Validation (all errors, never warnings; `DataError::{Parse, Invalid{hull, msg}}`)

1. `name` equals the directory name (fs loader) and is `[a-z0-9_]+`.
2. `hp > 0`, `mass > 0`, `inertia > 0`, `speed_cap >= 0`; `speed_cap == 0` only if `static`.
3. ≥ 1 collision circle, all `r > 0`; `bound_radius <= 60`.
4. `len(thrusters) <= MAX_THRUSTERS`, `len(turrets) <= MAX_TURRETS`; ids unique within
   the hull; `|dir| ∈ [0.99, 1.01]` (renormalised on load); `max_force > 0`.
5. Every turret `weapon` exists; `arc_deg ∈ [0, 360]`; `slew_deg_s > 0` if `arc_deg > 0`.
6. Shield: `hp > 0`, `regen_rate >= 0`, `regen_delay >= 0`, `radius >= bound_radius`.
7. Non-static hulls need ≥ 1 thruster. Thrusters must be able to produce net +x force
   and torque in both directions (sum over thrusters of positive/negative torque arm
   contributions); failure is an error in M1 (DESIGN says warning; the lab can relax
   this when a hull that wants it exists).
8. Weapons: `damage > 0`, `interval > 0`, `range > 0`; `speed > 0` unless `kind: beam`.
9. `life_ticks = round(range/speed * 30) >= 1` for projectile kinds.
10. (v2) `reaction_ticks`, if given, is an integer in `[0, MAX_REACTION_TICKS]`.
11. (v2) `armour`, if given and non-empty: at most `MAX_ARMOUR_ARCS = 8` arcs; every
    `from_deg < to_deg`, both in `[-180, 180]`; the first `from_deg == -180`, the last
    `to_deg == 180`, and each `from_deg` equals the previous `to_deg` (so the arcs
    cover 360° exactly with no gap or overlap, in order); every `mult` finite and
    `> 0`. A single arc `[-180, 180]` with `mult: 1` is valid and equals absent.

`Match::new` additionally rejects `cfg.reaction_ticks > MAX_REACTION_TICKS`
(`SetupError::ReactionTooLong`).

Python: `DataError` → `ValueError` with the message. WASM: `JsError`.

## 5. Step order (`Match::step`)

Each stage loops over ships in slot order and over projectiles in pool order.
`active(s) = s.alive && s.present`. Let `P_s, P_e, P_w` be the power multipliers (§5.2).

1. **Clear** `events`, `hits`, `rewards`; `tick += 1`. If `phase == Over` return (the
   VecEnv never calls step on a finished match; WASM may, for an outro).
2. **Arrivals** (§5.6): ships with `!present && alive && tick >= arrive_tick` become
   present with `vel = heading_dir * arrival_speed`, `control_lock_until = tick + 21`
   (0.7 s), emit `Arrival`.
3. **Actions** (v2: reaction queue, lock, ramp). For every **alive** ship `s` with
   delay `d = s.reaction_ticks`, in slot order:
   1. *Dequeue.* `a = if d == 0 { pending[s] } else { queue[0] }`; if `d > 0`, shift
      the queue down one slot and write the newly chosen action into `queue[d-1]`
      **sanitised at enqueue**: `pending[s].sanitized(hull)` (heads clamped, slots
      beyond the hull's thrusters/turrets zeroed / `SLEW_HOLD`) if
      `s.active() && tick + d >= control_lock_until`, else `ShipAction::IDLE`. For
      `d == 0` the same sanitisation applies to `a` directly (with
      `tick >= control_lock_until` as the condition). So an action chosen while the
      ship is not present, or that would land inside the control lock, never enters
      the state: this is what makes `act_mask` (§7.1) exact.
   2. *Lock.* `locked = tick < control_lock_until || hull.is_static || !s.active()`.
      If `locked`, `a = ShipAction::LOCKED` (every throttle head `DECREASE`, slews
      `HOLD`, fire 0, power head = "keep": `power_target` unchanged). Otherwise set
      `power_target` from `a.power`.
   3. *Ramp.* For each thruster `i`: `thrust_level[i] = clamp(thrust_level[i] +
      (a.throttle[i] as i8 − 1) * RAMP_RATE * DT, 0, 1)` with `RAMP_RATE = 5.0` /s
      (one step is `1/6`; 0 → 1 in 6 ticks = 200 ms). Slots beyond the hull's
      thrusters stay 0.
   4. `applied[s] = a` (what stages 6–7 read). Not-present ships still advance their
      queue (always with IDLE entries) so the "chosen at obs tick t, applied at tick
      t + 1 + d" rule holds from arrival; dead ships skip this stage entirely.
4. **Power slew**: `gap = max_k |target_k - power_k|`; `k = min(1, 0.45*DT/gap)`
   (0 if `gap == 0`); `power_k += (target_k - power_k) * k`. Shares stay summed to 1.
5. **Physics** (non-static, active): see §5.1.
6. **Turrets** (active): for each turret with `arc_deg > 0`:
   `angle += slew(applied) * slew_rate * DT`, clamped to `[rest - arc/2, rest + arc/2]`.
   `cooldown = max(0, cooldown - DT * 0.65 * P_w)`. A locked ship's `applied` slews
   are `HOLD`, so turrets do not move during the lock (v1 let them).
7. **Fire** (active): for each turret with `applied.fire == 1` and `cooldown == 0`:
   `cooldown = interval`; spawn per §6 with `fire_tick = tick`,
   `decision_tick = tick − 1 − d` (saturating); emit `Fire`; add fire cost.
   Muzzle pose: `pos_w = to_world(turret.pos)`, `angle_w = heading + turret_angle + spread`,
   `spread = rng.range(-1, 1) * spread_deg/2` in radians. (Locked ships have
   `applied.fire == 0`, so no separate lock check.)
8. **Projectiles** (§5.3): torpedo steer, advance, swept hit test against the shield
   bubble or the hull circles, flak burst, expiry. Hits call `apply_damage` (§5.4)
   immediately, in pool order.
9. **Shield regen** (active with shield): if `tick - last_hit_tick >= round(regen_delay*30 / P_s)`:
   `shield = min(max, shield + regen_rate * P_s * DT)`.
10. **Ship–ship collisions** (§5.5), pairs `(i<j)`, both active.
11. **Arena** (§5.7): push and drain, active non-static.
12. **Deaths**: any ship with `hp <= 0 && alive` → `alive=false, present=false, hp=0`,
    `thrust_level` all 0, `queue` all `IDLE`, emit `Death`. (Damage never flips
    `alive` directly; this stage does, so simultaneous kills are symmetric.)
13. **Termination** (§5.8) and terminal rewards.
14. `rewards` finalised (§8).

### 5.1 Physics

For each thruster `i` with level `l = thrust_level[i] ∈ [0, 1]` (ramped in stage 3):
`f = max_force * l * P_e`; body force `F_b = dir * f`; `τ += cross(pos, F_b)`;
`F_w += rot(heading) * F_b`. Then semi-implicit Euler:

```
vel   += F_w / mass * DT;   omega += τ / inertia * DT
vel   *= LINEAR_DRAG;       omega *= ANGULAR_DRAG     # per-tick damping at 30 Hz
cap    = speed_cap * (0.6 + 0.4 * P_e)
if |vel| > cap: vel *= 1 - min(0.08, (|vel| - cap) / |vel|)   # soft cap
pos   += vel * DT;          heading = wrap(heading + omega * DT)
```

v2 damping is a third lighter than v1: `LINEAR_DRAG = 1 − 0.005 · 2/3 = 0.996_666_7`
(v1 0.995) and `ANGULAR_DRAG = 0.96` (v1 0.94; `1 − 0.06·2/3`). Both are global
consts in `physics.rs`, written as those literals; not hull data (a hull that needs
its own damping is a later data change, not a sim change). Time constants: linear
`≈ 10 s`, angular `≈ 0.8 s`; a fighter's RCS pair (2 × 160 N at 2.3 m) still
settles to ≈ 2.5 rad/s.

Throttle ramp consts live in `physics.rs` too: `RAMP_RATE = 5.0` /s and
`RAMP_STEP = RAMP_RATE * DT` (`1/6` per tick). Because the ramp is applied in stage
3 before stage 5, the tick on which an action is applied already feels its first
`1/6` of thrust.

### 5.2 Power

`power` is `[shields, engines, weapons]`. Shieldless hulls keep `power[0] == 0`.
Multiplier for system `k`: `P_k = 0.2 + 0.8 * n_systems * power_k` (n_systems 3 or 2).
Even split → 1.0; the cap (0.6 / 0.8) → 1.64 / 1.48; zero share → 0.2.

**Power action = one head selecting a target split from a fixed table** (decision:
a menu of targets rather than per-system nudges). Reasons: the slew already makes
commitments slow and a nudge head would make the target a hidden state the policy
must infer; a 7-way categorical is cheap for PPO, trivially mask-free, and BC from a
script that picks a target is exact. It is not a mode: the sim only slews toward the
split; nothing else changes.

| idx | three-way (S,E,W) | two-way (E,W) = drop S, renormalise, clamp to 0.8 |
|---|---|---|
| 0 | 1/3, 1/3, 1/3 | 0.5, 0.5 |
| 1 | 0.6, 0.2, 0.2 | 0.5, 0.5 |
| 2 | 0.2, 0.6, 0.2 | 0.75, 0.25 |
| 3 | 0.2, 0.2, 0.6 | 0.25, 0.75 |
| 4 | 0.4, 0.4, 0.2 | 0.667, 0.333 |
| 5 | 0.4, 0.2, 0.4 | 0.333, 0.667 |
| 6 | 0.2, 0.4, 0.4 | 0.5, 0.5 |

Duplicates on two-way hulls are allowed (no mask); the table lives in `power.rs` as
`POWER_TARGETS: [[f32;3]; 7]` and `two_way_target(idx)`. Initial split = idx 0.

### 5.3 Projectiles and hits

Pool: `proj_next` cycles through `MAX_PROJECTILES`; spawning overwrites that slot
whether or not it is alive (oldest-first recycling, as v1).

- Torpedo steer (before advance): if `target` is active:
  `want = atan2(target.pos - pos)`, `have = atan2(vel)`,
  `have += clamp(wrap(want - have), ±turn_rate*DT)`, `vel = speed * dir(have)`.
- Advance: `next = pos + vel*DT`; `life_ticks -= 1`.
- **Target shape (v2, shield-first).** A ship's hit shape depends on its shield at
  the moment of the test: `shield > 0` → one circle `(ship.pos, shield_radius)`;
  `shield == 0` (or no shield) → the hull's compound collision circles in world
  space. `hit_radius(ship) = shield_radius if shield > 0 else bound_radius` is the
  broad-phase radius. Because hits apply immediately in pool order, the projectile
  that drops a shield to 0 is the last one that tests the bubble on that tick; the
  next one tests the hull.
- Swept test against every enemy active ship whose `same_entity` is false:
  broad phase `segment_dist(pos, next, ship.pos) < hit_radius + 0.5`, then narrow
  phase against the target shape (`segment_hits_circle`, as in sim.js). First hit in
  slot order consumes the projectile; hit point = the segment's first entry into the
  target shape (the earliest `segment_circle_entry` over the circles it hits, or its
  start if it starts inside), the same rule as beams. (v2: not the closest point to
  the circle's centre, which for a segment through a circle is the centre itself and
  would collapse armour bearings onto circle centres and leave a bubble hit through
  the centre without a normal.) `apply_damage` projects shield hits onto the bubble
  for the event. Torpedo hits also emit
  `Burst`.
- Flak: on `life_ticks == 0` without a hit → burst: every enemy active ship with
  `|ship.pos - next| < burst_radius + hit_radius(ship)` takes full damage at point
  `next`; emit `Burst`. Flak life is `life_ticks * (1 - fuse_jitter * rng.uniform())`
  at spawn.
- Expiry: `life_ticks == 0` → dead (bullets/torpedoes silently).
- Beams never enter the pool: resolved at fire time (§6), against the same target
  shapes.

Hit attribution: every damage application records
`HitRecord { shooter: ShipIdx, target: ShipIdx, damage: f32, fire_tick: u32,
decision_tick: u32, shield: bool }` into `Match.hits` (capped at `MAX_HITS`;
overflow counted in `Match.dropped_hits`). `damage` is the amount actually applied:
the raw weapon damage for a shield hit, the armour-scaled amount for a hull hit
(§5.4). `decision_tick` is copied from the projectile (`tick − 1 − d_shooter` for
beams).

### 5.4 Damage and shields

```
apply_damage(target, amount, point, shooter, fire_tick, decision_tick):
  target.last_hit_tick = tick
  if target.shield > 0:
      absorbed = amount / (0.7 + 0.3 * P_s(target))
      target.shield = max(0, target.shield - absorbed)
      n = normalize(point - target.pos)  (or (1,0) if zero)
      emit ShieldHit { target, pos: target.pos + n*shield_radius, normal: n, depleted: shield==0 }
      record HitRecord { shield: true, damage: amount, fire_tick, decision_tick }
  else:
      b    = wrap(atan2(point - target.pos) - target.heading)      # body-frame bearing of the impact
      mult = armour_mult(hull, b)                                   # 1.0 for hulls without armour (§4.1)
      dealt = amount * mult
      target.hp -= dealt
      emit Hit { target, shooter, pos: point, damage: dealt, mult }
      record HitRecord { shield: false, damage: dealt, fire_tick, decision_tick }
```

No overflow from shield to hull within one hit (as sim.js). Armour never applies to
shields. `point == target.pos` (bearing undefined) counts as bearing 0 (nose).
Death is resolved in stage 12. The time-limit tiebreak (§5.8) and the obs use `hp`
as stored, so armour is already included.

### 5.5 Ship–ship collisions

Broad phase: `|pi - pj| < bound_i + bound_j`. Narrow: for each circle pair `(a, b)` in
world space with `d = |ca - cb| < ra + rb`, take the deepest pair only. Resolve:
`n = (cb - ca)/d`, `pen = ra + rb - d`; inverse masses `wi = 1/mass` (0 if static);
positional correction `pos_i -= n * pen * wi/(wi+wj)`, `pos_j += n * pen * wj/(wi+wj)`;
relative normal speed `vn = dot(vel_j - vel_i, n)`; if `vn < 0`:
`jimp = -(1 + 0.2) * vn / (wi + wj)`, `vel_i -= n*jimp*wi`, `vel_j += n*jimp*wj`.
No torque transfer, no collision damage in M1. Emit nothing.

### 5.6 Arrival (jump-in)

At `Match::new`, team `t` side `s = -1 (t=0) / +1 (t=1)`, heading `0 / π`. The fleet
list is cut into squads of ≤ 3 in order. Squad `k` of `K`:
`cy = (k - (K-1)/2) * 70 + rng.range(-15, 15)`, `cx = s * (0.5*R + rng.range(0, 30))`
(ships beyond the arena are fine: they coast in). Ship `i` in the squad with
`row = i - (n-1)/2`: `pos = (cx + |row| * s * 10, cy + row * 16)`.
Times: `team_offset = rng.range(0, 0.6)` per team (both teams, independently — unlike
the demo, neither side is systematically late);
`squad_time = 1.0 + team_offset + k * 0.3 * rng.range(0.6, 1.4)`;
`arrive_tick = round((squad_time + rng.range(0, 0.08)) * 30)`.
Until present a ship is invisible to hits, obs, collisions and the arena; actions
chosen for it are discarded (stage 3 enqueues `IDLE`). Arrival sets
`vel = 1.4 * speed_cap` forward and locks control for `ARRIVAL_LOCK_TICKS = 21`.
At `Match::new` every ship has `thrust_level = 0`, `queue = [IDLE; 4]` and
`reaction_ticks = hull.reaction_ticks.unwrap_or(cfg.reaction_ticks)`; nothing
changes those at arrival. During the lock stage 3 applies `LOCKED` (levels ramp
toward 0, turrets hold, no fire, power target kept), and since the lock (21 ticks)
is longer than any delay (≤ 4), a ship always leaves the lock with every level at 0
and a queue holding only the actions chosen in its last `d` locked ticks that land
after the lock (those are unmasked, §7.1).

### 5.7 Arena

`r = |pos|`; if `r > R`: `vel -= pos/r * 40 * DT` (acceleration 40 m/s² inward, after
integration) and `hp -= 0.02 * max_hp * DT` (drain 2 %/s; it can kill). Reward
penalty in §8.

### 5.8 Termination

`alive_t = count(alive && team == t)` (pending arrivals count as alive).
- `alive_0 == 0 || alive_1 == 0` → Over; winner = surviving team, or -1 if both 0.
- `tick >= time_limit_ticks` → Over; `value_t = Σ_alive (hp + 0.5*shield)`;
  winner = higher value, or -1 if `|v0 - v1| < 1e-3`.

## 6. Weapons

| kind | spawn | hit | notes |
|---|---|---|---|
| bullet (gauss) | pool entry; `vel = ship.vel + speed*dir(angle)`; `life = range/speed` | swept circle vs the target shape (§5.3) | the spike's weapon |
| beam (laser) | none | hitscan: segment `muzzle → muzzle + range*dir` vs each enemy's target shape (shield bubble if up, else hull circles), nearest entry; emit `Beam{from,to}` | damage applied at fire time; `decision_tick = tick − 1 − d` |
| flak | pool; `vel = ship.vel + speed*dir`; jittered fuse | swept circle **or** proximity burst at fuse end (`burst_radius + hit_radius`) | "spread bullet with a fuse"; burst radius 14 |
| torpedo | pool; `vel = speed*dir` (does **not** inherit ship velocity); `life *= life_factor` | swept circle vs the target shape; `Burst` on hit | target chosen at spawn: active enemy within `range` and within `lock_cone_deg/2` of the muzzle line, smallest angular error; none → flies straight |

Decisions: **no magazine/reload in M1** (cooldown only; the power split already
modulates fire rate; v1 showed reload as an action is a learning tax). Fields are
reserved. **Fixed cooldown**, no ±15 % jitter (keeps credit assignment clean).
**No friendly fire** (team filter on every hit path). Torpedo target lock is weapon
mechanics, not an autopilot action: the policy still points the rack and pulls the
trigger.

## 7. Actions and observations

### 7.1 Action encoding

Per ship slot, a row of `ACTION_WIDTH = 21` `int8` (layout unchanged from v1; the
throttle head's meaning changed):

```
[0..8)   thruster throttle   ∈ {0,1,2}     (v2: 0 = DECREASE level, 1 = HOLD, 2 = INCREASE; ±1/6 per tick, §5.1)
[8..14)  turret slew         ∈ {0,1,2}     (0 = left, 1 = hold, 2 = right)
[14..20) turret fire         ∈ {0,1}
[20]     power target        ∈ {0..6}
```

The throttle head is a rate command on `thrust_level`, with the same 0/1/2 shape as
slew (1 = no change), so a policy head and a BC label look exactly as in v1.
`ShipAction::IDLE` = all `HOLD`, no fire, power 0; `ShipAction::LOCKED` (sim-internal,
stage 3) = all `DECREASE`, slews hold, no fire, power "keep".

Batched: `actions[N, S, 21] int8`. Unused slots (beyond the hull's thruster/turret
count) are ignored by the sim; masks tell the policy which heads matter:
`thruster_mask[N,S,8] bool`, `turret_mask[N,S,6] bool`, `fixed_turret[N,S,6] bool`
(arc 0 → slew head meaningless). Values out of range are clamped, not errors.

**`act_mask[N,S] bool` (v2 definition).** Written with the obs at post-step tick `t`
for the action the policy chooses from that obs, which the sim applies at tick
`t + 1 + d` (stage 3): 

```
act_mask = ship.alive && ship.present && (t + 1 + d >= ship.control_lock_until)
```

Contract: **if `act_mask` is false, the chosen row has no effect whatsoever on the
simulation state** (stage 3 enqueues/applies `IDLE` instead: no throttle, slew, fire
or power leaks, and the queue in the obs shows `IDLE`). If `act_mask` is true the row
is applied in full unless the ship dies first (unpredictable; the row is then
dropped with the ship, like the last action before any terminal state). This is the
definition that keeps PPO log-prob masking simple and exact: rows with
`act_mask = 0` are excluded from the loss, every other row is a real decision.
v1's `active && !locked(t)` was wrong on the last locked tick and let slew/power act
during the lock (the `xfail` in `tests/test_rust_env_wrapper.py` records it; v2
turns that test green).

`ShipAction { throttle: [u8;8], slew: [u8;6], fire: [u8;6], power: u8 }` with
`ShipAction::from_row(&[i8]) / to_row(&mut [i8])`, `sanitized(hull)` (clamp heads,
zero unused slots), and the consts `THROTTLE_DECREASE = 0`, `THROTTLE_HOLD = 1`,
`THROTTLE_INCREASE = 2`, `SLEW_HOLD = 1`.

### 7.2 Observation (fixed vector for the spike)

`OBS_DIM = 385` `f32` (v2; v1 was 204), body frame of the observing ship (relative
vectors rotated by `-heading`, so forward = +x). Scales: `R` = arena radius,
`VS = 100` m/s, `OM = 4` rad/s, `L = 20` m, `A = 100` m/s², `HP = 400`, `DMG = 60`,
`T_H = 2.0` s (threat horizon). Values are clamped to `[-5, 5]` after scaling. Absent
entities/slots are all-zero with `present = 0`. Blocks (offset: width — features):

```
0:   21  self + arena
       0 present            1 lock_left = max(0, lock_until − tick)/21   2 speed/VS   3 fwd_speed/VS
       4 lat_speed/VS       5 omega/OM            6 hp/max_hp          7 shield/max_shield (0 if none)
       8 time_left = (time_limit - tick)/time_limit                    9 has_shield
       10-12 power S,E,W    13 mass/100           14 speed_cap/VS      15 bound_radius/L
       16 max_hp/HP         17-18 dir_to_centre (body, unit)           19 (R - |pos|)/R
       20 reaction_ticks/MAX_REACTION_TICKS
21:  56  thrusters, 8 slots × 7: present, pos.x/L, pos.y/L, dir.x, dir.y, (max_force/mass)/A,
         thrust_level
77:  60  turrets, 6 slots × 10: present, pos.x/L, pos.y/L, sin(angle), cos(angle),
         cooldown/interval, kind one-hot[4] (bullet, beam, flak, torpedo)
137: 84  all other active ships, 7 slots (MAX_SHIPS − 1) sorted by distance (allies and
         enemies), × 12: present, is_enemy, rel_pos.x/R, rel_pos.y/R, rel_vel.x/VS,
         rel_vel.y/VS, sin(rel_heading), cos(rel_heading), hp/max_hp, shield/max_shield,
         bound_radius/L, dist/R
221: 64  8 hostile live projectiles sorted by threat score (see below), × 8: present,
         rel_pos.x/R, rel_pos.y/R, rel_vel.x/VS, rel_vel.y/VS, damage/DMG,
         t_ca/T_H, miss/L
285: 88  pending actions, 4 slots (MAX_REACTION_TICKS) × 22: slot k = queue[k] (k = 0
         applies on the next tick); slots k >= d are all-zero. Record: present,
         throttle[8] as −1/0/+1, slew[6] as −1/0/+1 (left = +1, CCW), fire[6] as 0/1,
         power_index/6
373: 6   turret slot j: arc/(2π)  (0 for fixed guns)
379: 6   turret slot j: weapon range/R
385 = OBS_DIM
```

**Threat score (projectile ordering).** For a live projectile with `team !=
observer.team` (own and allied shots are not listed; the ship knows its own fire from
its cooldowns), with `r = p.pos − me.pos`, `v = p.vel − me.vel` (world frame):
`t_ca = clamp(−dot(r, v) / |v|², 0, T_H)` (0 if `|v|² == 0`), `miss = |r + v · t_ca|`,
`score = miss + L · t_ca` (metres; one length scale per second of warning). Lower
score = more threatening; ties keep the lower pool index. A shot flying away has
`t_ca = 0` and `miss = |r|`, so it sorts behind anything converging. `t_ca` and
`miss` are also written into the record so the policy need not recompute them.

Pending-action slot `k` shows the action that will be applied at tick `t + 1 + k`
(the next step for `k = 0`); the action chosen from this obs will become slot `d − 1`
after the next step. With the levels in the thruster block this makes the obs
Markov under the delay. The record encodes heads as signed deltas so "hold" is 0 and
an absent slot (all zeros, `present = 0`) is distinguishable from a queued `IDLE`
(`present = 1`, power 0).

`write_obs` lives in `obs.rs` with `pub const` offsets for every block so Python can
slice by name (`rlf_sim.OBS_LAYOUT` dict exported by sim-py; v2 adds the
`"pending"` block and `OBS_SLOTS` per block: self 1, thrusters 8, turrets 6, ships 7,
projectiles 8, pending 4, turret_arc 6, turret_range 6). Turret `angle` is the
current body-frame angle; `rel_heading = other.heading - self.heading`. Per-record
writers: `write_self`, `write_thruster(hull, t, level, out)`, `write_turret`,
`write_turret_extras`, `write_ship`, `write_projectile(observer, p, score parts,
out)`, `write_pending(action, out)`.

Generalisation to DESIGN §7 tokens: every block above is already a fixed-width
record of one entity (self, thruster, turret, ship, projectile). The token form is the
same records written as `[N, S, T, D_max]` with a type column and a mask, with no
nearest-K truncation. `obs.rs` keeps per-record writers (`write_self`, `write_thruster`,
…) so the token writer is a second assembler over the same functions, not new
features. `sim_version` bumps when either layout changes.

## 8. Rewards, termination, credit

Per ship per step (`rewards[N, S] f32`), accumulated in stages 7–13:

| term | value |
|---|---|
| damage dealt | `+0.01 * damage` to hull (after armour, i.e. `HitRecord.damage`), `+0.005 * damage` to shields (raw) (shooter) |
| damage taken | `-0.01 * hull damage` (after armour), `-0.005 * shield damage` (target) |
| fire cost | `-0.002` per shot actually fired (not per trigger pull on cooldown) |
| arena | `-0.002` per tick while `|pos| > R` |
| terminal | `+1` every ship on the winning team, `-1` losing team (dead ships too); draw 0 |

Dead or not-yet-present ships get 0 except the terminal term. Precisely: a ship earns
the per-step terms iff it was active after stage 2 of that step, so the killing hit
still penalises its target, while hits from projectiles of an already-dead shooter
credit nobody in `rewards` (the HitRecord keeps the credit). Rewards are not
normalised in the sim. Weights are the named consts in `reward.rs`.

**Retroactive projectile credit**: the sim attributes every hit to `owner` and records
`fire_tick` and `decision_tick` (projectiles carry all three). `decision_tick` is
the post-step tick of the obs from which the firing action was chosen:
`decision_tick = fire_tick − 1 − d_shooter` (so with `d = 0` it is `fire_tick − 1`,
exactly the pre-step tick stamp v1's adapter matched on). The VecEnv exposes per step
`hits[N, MAX_HITS, 6] int32` = `(shooter, target, fire_tick, damage*1000, shield,
decision_tick)` (v2 appends column 5; `HIT_FIELDS = 6`) and `hit_count[N] int32`.
The Python `RustCreditAdapter` (`spacefight/rl/credit.py`) *moves* the shooter's
hit reward from the landing buffer step to the buffer step whose pre-step
`tick` stamp equals `decision_tick` in the same episode (`fire_step = buf_step −
(tick_before − decision_tick)`), leaving the sum unchanged; hits whose decision step
is before the retained buffer stay where they landed. The sim does not inject credit.
Shots fired by a ship that has since died still carry their `decision_tick`; the
adapter's `credit_dead_shooters` option decides whether to add that credit.

**VecEnv episode semantics**: `done[i]` is true on the step where match `i` reaches
`Over`; rewards for that step include the terminal term; `winner[i] ∈ {-1,0,1}`
(`-2` otherwise). The env then immediately rebuilds match `i` with
`seed = split(base_seed, i, episode_count[i])` and the same fleets, and the returned
obs row is the fresh match's first observation (ships not present yet → obs ≈ zeros
with `present = 0`). Episode generation `episode_count[i]` is exposed for credit.

## 9. Events

```rust
pub enum Event {
    Fire      { ship: u8, turret: u8, weapon: u16, pos: Vec2, angle: f32 },
    Beam      { ship: u8, from: Vec2, to: Vec2, hit: bool },
    Hit       { target: u8, shooter: u8, pos: Vec2, damage: f32, mult: f32 }, // v2: armour multiplier (1.0 uniform)
    ShieldHit { target: u8, shooter: u8, pos: Vec2, normal: Vec2, depleted: bool },
    Burst     { team: u8, pos: Vec2, radius: f32 },      // flak fuse, torpedo impact
    Death     { ship: u8, pos: Vec2 },
    Arrival   { ship: u8, pos: Vec2, heading: f32 },
}
```

`EventBuf` is a `Vec<Event>` with capacity `MAX_EVENTS`, cleared each step. Flat
encoding for FFI: `[f32; 8]` per event = `[kind, a, b, x, y, nx_or_x2, ny_or_y2, extra]`
(kinds 0..6 in the order above; `a,b` = ship/turret or target/shooter; `extra` =
angle / damage / radius / heading / depleted; `Fire` puts its weapon id in slot 5,
`Beam` its `to` in 5–6 and `hit` in `extra`; v2: `Hit` puts `mult` in slot 5, so a
renderer can show glancing (`< 1`) and raking (`> 1`) hits). WASM:
`WasmMatch.events_ptr() -> *const f32`,
`events_len() -> usize`, read as a `Float32Array` view on `memory.buffer` after each
`step()`. Python: `VecEnv(record_events=False)`; when true, `events()` returns a copied
`[E, 9] f32` array with a leading match index column (debug/visualisation only).

## 10. Bindings

### 10.1 sim-py (`rlf_sim`)

```python
env = rlf_sim.VecEnv(assets_dir: str, n_envs: int, fleets: list[list[str]],  # [[team0 hulls],[team1 hulls]]
                     seed: int, arena_radius: float = 450.0, time_limit_s: float = 90.0,
                     n_threads: int = 0, record_events: bool = False,
                     reaction_ticks: int = 2)                                # v2; 0..MAX_REACTION_TICKS
env.n_envs, env.n_ships -> int (S = fleet total; MAX_SHIPS cap), env.dt -> float
env.reset()                       # rebuild every match with episode_count = 0
env.step(actions=None)            # reads env.actions (or copies `actions` in first), advances all matches, auto-resets
# zero-copy buffers, owned by the env, overwritten in place on every step():
env.obs      [N,S,385] f32     env.actions   [N,S,21] i8 (write here before step)
env.rewards  [N,S] f32         env.dones     [N] bool        env.winner [N] i8
env.act_mask [N,S] bool        env.thruster_mask [N,S,8] bool  env.turret_mask [N,S,6] bool
env.fixed_turret [N,S,6] bool  env.team [N,S] i8  env.hull_id [N,S] i16  env.alive [N,S] bool
env.tick [N] u32  env.episode_count [N] u32  env.hits [N,64,6] i32  env.hit_count [N] i32
env.scripted_actions(team: int | None = None)   # writes the scripted controller's actions into env.actions for the given team (or all ships)
env.state_hash() -> np.ndarray[N] u64           # per match
env.render_state(i) -> dict                     # ships/projectiles of match i (debug); ships carry thrust_level, queue
env.events() -> np.ndarray[E, 9] f32            # record_events only; column 0 = match index
rlf_sim.OBS_LAYOUT, rlf_sim.OBS_SLOTS, rlf_sim.ACTION_LAYOUT, rlf_sim.SIM_VERSION,
rlf_sim.OBS_DIM, rlf_sim.ACTION_WIDTH, rlf_sim.MAX_SHIPS, rlf_sim.MAX_HITS, rlf_sim.HIT_FIELDS,
rlf_sim.HIT_DAMAGE_SCALE, rlf_sim.MAX_REACTION_TICKS
```

`act_mask` is written with the obs after each step/reset and follows the §7.1
definition for the action the caller is about to write. `spacefight/env/rust_env.py`
(`RustVecEnv`, `StepInfo`) wraps this with v1's `reset() → obs`,
`step(actions) → (obs, rewards, dones, info)` shape; `StepInfo.hits` is `[N, 64, 6]`
and `StepInfo` keeps the pre-step `prev_tick / prev_episode_count / prev_alive`
snapshots the credit adapter stamps with.

Buffers are numpy arrays allocated once in `__new__` (`PyArray::zeros`) and held as
`Py<PyArray>`; `step()` takes `&mut` slices under the GIL, then releases the GIL
(`py.allow_threads`) and runs `rayon` `par_iter_mut` over matches, each writing its
own obs/reward rows (disjoint `chunks_mut`). The rayon pool is built once with
`n_threads` (0 = rayon default). The property getters return the same array objects
every call. Fleets are fixed per env; heterogeneous fleets per match are M3.

### 10.2 sim-wasm

```ts
class WasmMatch {
  constructor(hull_yamls: Array<[string,string]>, weapons_yaml: string, config_json: string);
  step(): void;                       // one tick
  set_action(ship: number, row: Int8Array): void;  // length 21
  scripted_action(ship: number): Int8Array;
  ships_ptr(): number; ships_len(): number;        // flat f32, SHIP_STRIDE = 29 per ship (pos, vel, heading, omega, hp, shield, alive, present, team, hull, thrust_level[8] (v2: floats in [0,1]; v1 wrote 0/1/2), turret_angles[6], power[3])
  projectiles_ptr(): number; projectiles_len(): number;  // flat f32 stride 8: pool_slot, kind, team, owner, pos, vel
  events_ptr(): number; events_len(): number;
  obs(ship: number): Float32Array;    // for in-browser inference (M2); OBS_DIM floats
  tick(): number; phase(): number; winner(): number; state_hash_hex(): string;
}
```

`config_json` is `MatchConfig` serialised with serde
(`{"seed":..,"arena_radius":..,"time_limit_ticks":..,"reaction_ticks":2,"fleets":[["fighter"],["fighter"]]}`
with hull names resolved on the WASM side; `arena_radius`, `time_limit_ticks` and
(v2) `reaction_ticks` default when absent).

## 11. Scripted controller (Rust, `scripted/`)

Lives in Rust (decision): usable as BC target, baseline opponent, and in the browser
without a second implementation. Interface:

```rust
pub fn act(m: &Match, cat: &Catalogue, ship: ShipIdx) -> ShipAction;  // deterministic, reads state
pub fn allocate_thrusters(hull: &HullDef, force_body: Vec2, torque: f32) -> [u8; MAX_THRUSTERS];
```

`allocate_thrusters` is the sim.js greedy allocator: `along = dot(dir, f̂) * min(|f|,1)`,
`arm = cross(pos, dir)`, `score = along + 1.2 * sign(arm) * torque`; `> 0.6 → 2`,
`> 0.25 → 1`, else 0. In v2 its output is a **target level** per thruster
(`0, 0.5, 1`), which `levels_to_throttle_heads` turns into the rate heads of §7.1:
`INCREASE` if `projected_level < target − RAMP_STEP/2`, `DECREASE` if
`projected_level > target + RAMP_STEP/2`, else `HOLD`. `projected_level` is the
level the thruster will have when this action is applied: the current
`thrust_level` with the ship's queued throttle heads (`queue[0..d]`) applied in
order, clamped (`scripted::projected_levels(ship)`). With `d = 0` that is the
current level.

**Acting through the delay (v2).** The controller chooses the action that will be
applied at tick `t + 1 + d`, so it evaluates geometry at the predicted state
`τ = (d + 1) · DT` ahead: `pos' = pos + vel·τ`, `heading' = wrap(heading + omega·τ)`
for itself and `pos' = pos + vel·τ` for the target (no thrust prediction; the
error is a fraction of a tick's acceleration). Fire readiness is
`cooldown − (d + 1) · DT · 0.65 · P_w <= 0` (`turrets::cooldown_after_ticks(cooldown,
p_w, d + 1)` generalises `cooldown_after_tick`), and the PD torque uses the
predicted heading error and the current `omega`. The arena check uses `pos'`.

Fighter (`role == "fighter"`), per tick (all quantities predicted as above):
1. Target = nearest active enemy (`dist`), else coast (`IDLE`).
2. Lead: `t = dist / speed`; `aim = atan2(rel_pos + rel_vel * t)`; `err = wrap(aim - heading')`.
3. `go = 1 if dist > 60 || |err| > 1.2 else 0.3`; `force_body = (go * (1 if |err| < 0.9 else 0.2), 0)`.
4. Arena: if `|pos'| > 0.85 R` → `aim = atan2(-pos')`, `force_body = (1, 0)`.
5. `torque = clamp(10 * err - 1.6 * omega, -1, 1)`; target levels = allocator; throttle
   heads = `levels_to_throttle_heads`. (sim.js uses gain 2.5; with the allocator's
   ≈ 0.21 torque dead zone that cannot null aim errors under ≈ 0.08 rad, too coarse
   for the compound-circle fighter, and scripted duels never landed a kill. Changed
   in WP5/WP7.)
6. Turrets: fixed gun fires if `|err| < 0.1 && dist < range` and the weapon is ready at
   the application tick; turreted guns slew toward `wrap(bearing - angle)` (left/right
   by sign, hold within `max(0.03, slew_rate·DT/2)` rad) and fire when `|aim_err| < 0.06`.
7. Power: `3` (weapons) if `dist < range`, `2` (engines) if `dist > 1.5 range`, else 0;
   `1` (shields) if `tick - last_hit_tick < 36 && shield/max < 0.3` (shielded hulls).

Roles as shipped: `fighter` (fighter), `skirmisher` (strafer: orbit at 120 m,
`orbit_sign = +1 if slot even else -1`) and `anchor` (gunship: standoff 170 m,
broadside), ported from sim.js in `fighter.rs` / `strafer.rs` / `gunship.rs`; a hull
whose role has no controller returns `IDLE`. The controller reads `Match` state, not
obs, so BC pairs are `(obs_t, act(state_t))`; it is deterministic and allocation-free.
Acceptance for v2 (§14.1 WP11): scripted fighter duels end in a kill before the time
limit for 20/20 seeds at every `reaction_ticks ∈ {0, 2, 4}`.

## 12. Determinism contract and test

- `state_hash()`: FNV-1a 64 over, in order: `tick`, rng state (two u64), each ship's
  fields in declaration order (`to_bits()` for f32, raw for ints/bools; v2: `thrust_level`
  in place of `throttle`, then `reaction_ticks` and the `queue` as `4 × 21` u8 after
  `attach`), each projectile pool slot (v2: `decision_tick` after `fire_tick`),
  `proj_next`, `phase`, `winner`. Implemented in-crate (`hash.rs`), no `std::hash`.
  `pending`, `applied`, events, hits and rewards are outputs and are not hashed.
- Native test (`crates/sim/tests/determinism.rs`): four golden scenarios, embedded
  with `include_str!` so the same binary runs under wasmtime:
  `duel_fighter_s7` (1v1 fighter, seed 7), `2v2_mixed_s11` (fighter+strafer vs
  gunship+fighter), `3v3_mixed_s13`, all 3000 ticks with the scripted controller
  on both sides, sampled at ticks `{1, 30, 300, 1000, 3000}` (those reached before
  `Over`); and `3v3_random_s17` (9000 ticks of sticky uniform random action rows from
  the test's own PCG stream, sampled every 100 ticks). Each line carries the state
  hash plus an auxiliary digest of that step's flat events, hit records, rewards and
  every ship's obs, so outputs match across targets too. Regenerate golden only with
  `UPDATE_GOLDEN=1`; a diff in golden is a `SIM_VERSION` bump. v2 regenerates all
  four once (§14.1 WP14), after the balance tuple is final.
- WASM: the same test binary runs under **wasmtime** on `wasm32-wasip1`
  (`cargo test -p sim --target wasm32-wasip1`, with
  `CARGO_TARGET_WASM32_WASIP1_RUNNER=wasmtime` in `.cargo/config.toml`). This exercises
  the exact sim code the browser build uses, with no JS harness. Tooling:
  `rustup target add wasm32-wasip1 wasm32-unknown-unknown`, `wasmtime` CLI, `wasm-pack`
  (only to check `sim-wasm` builds). Node is not required in M1.
- Also: two `Match`es with the same seed stepped with the same actions, interleaved
  with a third, hash-equal every tick (no shared state). The VecEnv with
  `n_threads=1` and `n_threads=16` gives identical `state_hash()` arrays.
- Rust defaults do not fuse multiply-adds; `.cargo/config.toml` sets no
  `target-cpu=native`. The hash test is the guard.

## 13. Performance target

Measured by `tools/bench_env.py` (random valid actions, obs on, events off, 16
threads, N = 256, 2000 steps after 100 warm-up), reported as batched env steps/s
(one step = all 256 matches advance one tick):

| scenario | target | floor (fail CI below) |
|---|---|---|
| 1v1 fighter | ≥ 6,000 steps/s (1.5 M match-ticks/s) | 3,000 |
| 2v2 (fighter+strafer each side) | ≥ 4,000 steps/s | 2,000 |
| single-thread 1v1 | ≥ 600 steps/s | 300 |
| WASM single match 2v2 (wasmtime, no obs) | ≥ 20,000 ticks/s | 10,000 |

Budget reasoning: one 2-ship tick with ~20 projectiles and a 385-float obs is ~3–5 µs
(the v2 obs is 1.9× v1's but mostly zero-filled slots; the threat sort is over ≤ 256
pool entries with an 8-entry insertion list); 256 of them is ~1 ms single-threaded,
so 16 cores plus ~50 µs of PyO3 overhead leaves headroom. The targets above are
unchanged for v2; WP14 re-measures and records the number in the lab journal. At the
target, the 4-hour nightly budget is sim-bound at >2 × 10^10 match-ticks; policy
inference will dominate.

## 14. Work packages

Each package is one agent, one sitting. "Parallel" means no file overlap with the
other package. Every package ends with `cargo fmt`, `cargo clippy -D warnings`, tests green.

| WP | scope | files | depends on | parallel with | acceptance |
|---|---|---|---|---|---|
| 0 | Workspace scaffold, `math`, `rng`, `hash`, `.cargo/config.toml`, CI script (`scripts/check.sh`: fmt, clippy, test native + wasip1) | `Cargo.toml`, `crates/*/Cargo.toml`, `sim/src/{lib,math,rng,hash}.rs` | — | — | `cargo test` passes on native and wasip1; `rng` golden vector test; `wrap_angle`/`rot` unit tests; sim-py and sim-wasm crates build empty |
| 1 | Data model, YAML parsing, validation, the three hull files and `weapons.yaml` | `sim/src/data/*`, `assets/**` | 0 | 2 | `tests/data.rs`: load_dir succeeds, every rule in §4.4 has a failing fixture, hull ids sorted by name, derived fields correct |
| 2 | State, actions, power, physics, setup (no weapons, arrival stub placing ships present at t=0) | `state,actions,power,physics,setup`.rs | 0 | 1 (uses a hand-built `HullDef` in tests until 1 lands) | `tests/physics.rs`: main thruster accelerates +x; RCS pair pivots; drag settles; soft cap; power slew reaches target in `gap/0.45` s; multipliers table; action row round-trip and clamping |
| 3 | Turrets, weapons, projectiles, damage/shields, events, hits | `turrets,weapons,projectiles,damage,events`.rs | 1, 2 | 4, 6, 7 | `tests/weapons.rs`: bullet swept hit on a fast ship; beam nearest-hit; flak burst damages within radius; torpedo turns at rate and locks in cone; shield absorbs then regens after delay; ShieldHit normal is unit and points outward; HitRecord has owner + fire_tick; pool recycles oldest |
| 4 | Collisions, arena, arrival | `collision,arena,arrival`.rs | 2 | 3, 6, 7 | `tests/arena.rs`: overlapping ships separate with momentum conserved; static hull does not move; outside arena → pushed back and drained; arrival ticks within bounds, squads ≤ 3, control lock 21 ticks, pending ships untargetable |
| 5 | `Match::step` assembly in the §5 order, termination, winner, rewards | `step,reward`.rs | 3, 4 | 6, 7 | `tests/step.rs`: 1v1 where one side never fires ends with the shooter winning; time limit → value tiebreak; simultaneous death → draw; reward terms sum as §8; `step` after `Over` is a no-op |
| 6 | Observation builder | `obs.rs` | 2 | 3, 4, 5, 7 | `tests/obs.rs`: offsets match §7.2; body-frame rotation (enemy dead ahead → rel_pos.y = 0); nearest-K ordering; absent slots zero; values within [-5,5]; `OBS_LAYOUT` export list |
| 7 | Scripted fighter + allocator (7b: strafer, gunship) | `scripted/*` | 2 | 3, 4, 5, 6 | `tests/scripted.rs`: allocator reproduces sim.js on 6 fixed cases; fighter turns toward a target and fires within tolerance; scripted 1v1 fighter ends in a kill before the time limit for 20/20 seeds (needs WP5 for the last test) |
| 8 | Determinism: golden traces, wasip1 run, `sim-wasm` crate with `WasmMatch` | `tests/determinism.rs`, `tests/golden/*`, `sim-wasm/src/*` | 5, 7 | 9 | §12 tests green natively and under wasmtime; `wasm-pack build crates/sim-wasm` succeeds; a node-free smoke check that `WasmMatch` exports exist (`wasm-bindgen` CLI `--target web` output inspected) |
| 9 | `sim-py` VecEnv, zero-copy buffers, rayon, auto-reset, hits, `bench_env.py` | `sim-py/src/*`, `tools/bench_env.py`, `pyproject` for maturin | 5, 6, 7 | 8 | `tests/test_rust_env.py`: shapes/dtypes exactly as §10.1; same array objects across steps; `dones` and auto-reset obs; `n_threads` 1 vs 16 hash-equal; `hits` fields; benchmark prints and asserts the floors in §13 |
| 10 | Python wrapper `spacefight/env/rust_env.py`, credit adapter to `fire_tick`, BC dataset check | `spacefight/env/rust_env.py`, `spacefight/rl/credit.py` (adapter only), `tests/test_rust_env_wrapper.py` | 9 | — | pytest: gym-style `reset/step` returns `(obs, rew, done, info)`; `CreditAssigner` credits a hit to the fire step; 10k steps of `scripted_actions` produce (obs, action) pairs with the documented masks and no NaN |

Critical path: 0 → 1/2 → 3 → 5 → 8/9 → 10. Maximum concurrency: after WP2, four
agents (3, 4, 6, 7) at once; after WP5, two (8, 9). All ten landed on `m1-sim`
(SIM_VERSION 1).

### 14.1 v2 work packages

Same rules: one agent, one sitting, separate git worktree off `m1-sim`, ends with
`cargo fmt`, `cargo clippy -D warnings`, `scripts/check.sh` green (native + wasip1)
and, where Python is touched, `black`, `mypy`, `pytest`. "Shared" lists every file a
package touches that another v2 package also touches; a package that lands second
rebases onto the first before merging. Until WP14 lands, `SIM_VERSION` stays 1 and
the golden tests are expected to fail on every v2 branch (run them with
`UPDATE_GOLDEN=1` locally to see the trace, never commit the result before WP14).

| WP | scope | files (owned) | shared with | depends on | parallel with | acceptance |
|---|---|---|---|---|---|---|
| 11 | **Control & physics (v2 items 1, 2, 3, 7, 8-sim-side):** damping consts; `thrust_level` ramp; `MatchConfig.reaction_ticks` + hull `reaction_ticks` override + rule 10 + `SetupError::ReactionTooLong`; `Ship.queue` / `applied` / `LOCKED` / enqueue sanitisation (§5 stage 3); deaths clear levels + queue; hash update; `act_mask` per §7.1 (`Match::act_mask`, `actions::act_mask(ship, tick)` with the `t + 1 + d` rule); `Projectile.decision_tick` + `HitRecord.decision_tick` plumbing (`spawn_projectile`, `fire_beam`, `apply_damage` signature); stage 6/7 read `applied`; WASM `config_json.reaction_ticks`; scripted controller: levels → rate heads, `projected_levels`, prediction by `(d+1)·DT`, `cooldown_after_ticks` | `sim/src/{physics,actions,state,setup,step,arrival,turrets,hash}.rs`, `sim/src/scripted/*`, `sim-wasm/src/bridge.rs`, `sim/tests/{physics,step,scripted,arena}.rs` | `sim/src/{weapons,damage,events}.rs`, `sim/src/data/{raw,hull,validate}.rs`, `sim/tests/data.rs`, `sim/tests/common/mod.rs` (with WP12) | — | 12 | `tests/physics.rs`: level ramps 0 → 1 in exactly 6 ticks and clamps; `HOLD` keeps a level across 100 ticks bit-exact; force = `max_force·level·P_e`; drag constants as §5.1 literals (a coasting ship keeps `0.99667^30` of its speed after 1 s); with `d = 2` an action set at obs tick `t` first changes `thrust_level` on the step that ends at tick `t + 3`, and the queue in `render_state`/`Ship.queue` shows it in between; `d = 0` applies next step; `d = 5` rejected by `Match::new` and `reaction_ticks: 5` by the validator; locked ship: levels decay to 0, turrets do not move, no fire, `power_target` unchanged, for all `d`; the §7.1 contract holds — patching any row with `act_mask = 0` leaves `state_hash` identical over 3000 ticks of a 2v2 (the Rust twin of the wrapper's `xfail`), and rows with `act_mask = 1` on a locked ship's last ticks *do* change it; death clears levels and queue; `HitRecord.decision_tick == fire_tick − 1 − d` for bullets and beams; `tests/scripted.rs`: fighter duel ends in a kill ≤ time limit for 20/20 seeds at `d ∈ {0, 2, 4}`; allocator cases as before on target levels; `levels_to_throttle_heads` hold band |
| 12 | **Armour & shield-first (v2 items 4, 5):** `ArmourArc`, hull YAML `armour`, rule 11, `armour_mult(hull, bearing)`; `apply_damage` scales hull damage, `Hit.mult`, flat encoding slot 5; `hit_radius`/target-shape helper; swept test (hit point = first entry into the shape), beam entry test and flak proximity against the shield bubble when `shield > 0`; fighter YAML armour block; `common/mod.rs` fixture catalogue updated to match | `sim/src/{damage,projectiles,weapons,events}.rs`, `sim/src/data/{raw,hull,validate}.rs`, `assets/hulls/fighter/hull.yaml`, `sim/tests/{weapons,data}.rs`, `sim/tests/common/mod.rs`, `sim/tests/fixtures_match_assets.rs` | `sim/src/{weapons,damage,events}.rs`, `sim/src/data/*`, `sim/tests/data.rs`, `sim/tests/common/mod.rs` (with WP11); `assets/hulls/fighter/hull.yaml` (with WP14 balance edit) | — (rebase onto 11 before merge; it adds the `decision_tick` argument WP11 introduces) | 11, 13 | `tests/data.rs`: every rule-11 failure mode has a fixture (gap, overlap, wrong ends, `mult <= 0`, > 8 arcs); `[-180,180] mult 1` loads; `tests/weapons.rs`: a bullet into the fighter's nose does 0.5× and `Hit.mult == 0.5`, from astern 1.5×, abeam 1.0×; bearing exactly `+π` resolves to the last arc; shields ignore armour; a bullet whose segment crosses the shield bubble but not the hull circles hits a shielded-up strafer, and the same segment misses once the shield is 0; the ShieldHit `pos` lies on the bubble and `normal` is unit/outward; a beam stops at the bubble entry point; flak bursts within `burst_radius + shield_radius` of a shielded ship and only within `burst_radius + bound_radius` of a bare one; `HitRecord.damage` is the post-armour amount and the reward uses it |
| 13 | **Observation v2 & bindings (item 6, 8-python-side):** `obs.rs` layout (§7.2), threat score, pending-action records, `OBS_SLOTS`, `OBS_LAYOUT`; `sim-py`: `reaction_ticks` kwarg, `HIT_FIELDS = 6`, new module constants, `render_state` ships gain `thrust_level`/`queue`; `rust_env.py` (`OBS_SLOTS`, `StepInfo` docs); `credit.py` `RustCreditAdapter` maps on `decision_tick` (column 5); `tests/test_rust_env_wrapper.py` `xfail` removed; `tools/bench_env.py` unchanged but rerun | `sim/src/obs.rs`, `sim/tests/obs.rs`, `sim-py/src/*`, `spacefight/env/rust_env.py`, `spacefight/rl/credit.py`, `tests/{test_rust_env,test_rust_env_wrapper,test_credit}.py` | none with 11/12 (reads `thrust_level`, `queue`, `reaction_ticks`, `decision_tick` as WP11 defines them) | 11 | 12 | `tests/obs.rs`: offsets equal §7.2 (const assert `OBS_DIM == 385`); seven ship slots filled in a 4v4 and sorted by distance; projectile ordering matches a hand-computed threat score on three staged shots (converging, passing, receding) and own shots are absent; `t_ca`/`miss` features agree with the score; pending slot `k` equals `queue[k]` encoded as −1/0/+1 and slots `>= d` are zero; thrust levels appear in the thruster records; `lock_left` counts down 21 → 0; values within `[-5, 5]`; `pytest`: buffer shapes/dtypes as §10.1 (`hits [N,64,6]`); `act_mask` from the env matches `Match::act_mask`; with `reaction_ticks=2` a scripted hit's credit lands on the buffer step stamped `decision_tick` (three ticks before the shot's landing-step stamp minus flight); `reaction_ticks=0` reproduces v1 credit placement; `test_masked_ships_actions_are_fully_ignored` passes without `xfail`; 10k steps of `scripted_actions` at `d = 2` give no NaN |
| 14 | **Integration:** `SIM_VERSION = 2`; balance starting tuple into `assets/weapons.yaml` and the fighter YAML (§0 item 9, `hp: 80`); `common/mod.rs` fixture values; `UPDATE_GOLDEN=1` regeneration of all four traces; `scripts/check.sh` native + wasip1; `wasm-pack build`; `maturin develop --release`; `tools/bench_env.py` numbers into the lab journal; §4 tables and §13 note in this file updated with what was measured | `sim/src/lib.rs`, `assets/weapons.yaml`, `assets/hulls/fighter/hull.yaml`, `sim/tests/golden/*`, `sim/tests/common/mod.rs`, `docs/SIM_SPEC.md`, lab journal | `assets/hulls/fighter/hull.yaml`, `sim/tests/common/mod.rs` (with WP12) | 11, 12, 13 merged | — | `scripts/check.sh` green natively and under wasmtime; golden files carry `SIM_VERSION 2` headers; `rlf_sim.SIM_VERSION == 2`, `rlf_sim.OBS_DIM == 385`; `n_threads` 1 vs 16 hash-equal; bench ≥ the §13 floors (targets reported) |
| 15 | **Duel sweep** (the spike plan's §2.3 gate; was its WP A): `tools/duel_sweep.py`, sweep `reaction_ticks ∈ {0, 2, 4}` × the balance knobs, pick the tuple, write it to the assets, regenerate golden if it changed, record every tuple in the run's `results.md` | `tools/duel_sweep.py`, `tests/test_duel_sweep.py`, `assets/weapons.yaml`, `assets/hulls/fighter/hull.yaml`, `sim/tests/golden/*` | assets + golden (with WP14; strictly after it) | 14 | spike WP B, D | plan §2.3 gates; `scripts/check.sh` green after any regen; SIM_SPEC §4 tables match the assets |

Critical path: 11 → 13 → 14 → 15, with 12 alongside 11/13. Two agents can start at
once (11, 12); 13 starts when 11 merges; 14 is a single short integration sitting
once 12 and 13 are both in.

## 15. Open questions (recommended defaults)

1. **Arena radius for the 1v1 spike.** Default 450 m (fighter crosses in ~8 s at
   cap). If kiting dominates, drop to 350 before touching rewards.
2. **Shield damage reward weight** (0.005 vs 0.01). Default half weight; shields
   regenerate so full credit over-rewards chip damage. Revisit with the strafer spike.
3. **Fire cost** (`-0.002`). Default on; set to 0 if the BC-initialised policy stops
   firing. It only exists to stop spraying at nothing.
4. **Validation rule 7** (thrusters must produce both torque directions) is an error
   in M1, a warning in DESIGN. Default: error until a hull that needs it exists, then
   relax in the validator, not the sim.
5. **Torpedo lock at spawn** uses a 30° cone. Default as specified; if bombers later
   need "dumb-fire", add `lock_cone_deg: 0` meaning no lock, which the data already allows.
6. (v2) **Threat score weight** `score = miss + L · t_ca` with `L = 20` m/s of
   warning. Default as specified; if the policy ignores far-but-converging shots,
   try `miss + 2L · t_ca`. The ordering only matters once more than 8 hostile
   projectiles are in flight (never in the 1v1 spike).
7. (v2) **Reaction delay default 2.** The lab sweeps 0/2/4 (WP15); if 4 is as
   learnable as 2 and looks better on the phone, make 4 the default. Per-hull
   overrides exist in the data but no shipped hull uses one.
8. (v2) **Armour on strafer and gunship** is uniform for now. Once the fighter's arcs
   are tuned, the gunship is the natural next candidate (broadside-heavy, thick nose).
9. (v2) **Own projectiles in the obs** are dropped from the vector form. The token
   form (DESIGN §7) can list them as a separate type; the vector form stays hostile-only
   unless the spike shows the policy mis-timing its own shots.
10. (v2) **Damping as hull data.** The consts are global; make them optional hull
    fields the first time a hull wants a different feel (the carrier, probably).
