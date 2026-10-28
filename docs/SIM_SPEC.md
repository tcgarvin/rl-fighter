# RL Fighter — M1 Simulation Spec (Rust core + Python bindings)

Status: implementation spec for milestone M1, written 2026-10-28. `docs/DESIGN.md` is
the source of truth for direction; this file pins the decisions implementers need.
When the two disagree, fix this file and note it in the lab journal.

Scope of M1: **M1a** `crates/sim` (three hulls, thrusters, power split, turrets, four
weapon kinds, shields, compound-circle hits, ship collisions, arena, arrival, skirmish
termination, events, obs, rewards, scripted fighter) and **M1b** `crates/sim-py`
(batched VecEnv over N matches, zero-copy numpy buffers, throughput benchmark). The
`crates/sim-wasm` crate must build and pass the native-vs-WASM determinism test, but
has no renderer yet (that is M2).

Not in M1 (but the data model leaves room, see §3.4): bomber, carrier, station, bays,
docking/repair, attached/tethered ships, friendly fire, armour/damage types.

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
  src/lib.rs               # re-exports; pub const SIM_VERSION: u32 = 1
  src/math.rs              # Vec2, wrap_angle, rot, clamp, cross
  src/rng.rs               # Pcg32 wrapper: uniform(), range(lo,hi), split(seed,i,k)
  src/hash.rs              # FNV-1a 64 over f32/int bit patterns (StateHasher)
  src/data/mod.rs          # Catalogue, DataError, load from YAML text (+ load_dir under `fs`)
  src/data/hull.rs         # HullDef, ThrusterDef, TurretDef, ShieldDef, BayDef, Circle
  src/data/weapon.rs       # WeaponDef, WeaponKind
  src/data/validate.rs     # validation rules (§4.4)
  src/state.rs             # Match, Ship, Projectile, MatchPhase, consts MAX_*
  src/actions.rs           # ShipAction, ACTION_WIDTH, decode from i8 row, masks
  src/power.rs             # POWER_TARGETS table, slew, multipliers
  src/physics.rs           # thruster forces, integration, drag, soft cap
  src/turrets.rs           # slew, fire gating, muzzle pose
  src/weapons.rs           # spawn bullet/flak/torpedo, resolve beam
  src/projectiles.rs       # advance, torpedo steer, swept circle tests, flak burst
  src/damage.rs            # apply_damage (shield → hull), death
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
    pub fleets: [Vec<HullId>; 2],                    // team 0, team 1; ≤ MAX_SHIPS total
}
pub struct Match { /* §3 */ }
impl Match {
    pub fn new(cat: &Catalogue, cfg: &MatchConfig) -> Result<Match, SetupError>;
    pub fn set_action(&mut self, ship: ShipIdx, a: ShipAction);
    pub fn step(&mut self, cat: &Catalogue);         // one tick; fills events + step stats
    pub fn tick(&self) -> u32;  pub fn phase(&self) -> MatchPhase;  pub fn winner(&self) -> i8;
    pub fn ships(&self) -> &[Ship];  pub fn projectiles(&self) -> &[Projectile];
    pub fn events(&self) -> &[Event];                // events of the last step
    pub fn hits(&self) -> &[HitRecord];              // hits landed during the last step
    pub fn write_obs(&self, cat: &Catalogue, ship: ShipIdx, out: &mut [f32]); // len OBS_DIM
    pub fn rewards(&self) -> &[f32];                 // len n_ships, for the last step
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

pub struct Ship {
    pub hull: HullId, pub team: u8, pub slot: ShipIdx,
    pub pos: Vec2, pub vel: Vec2, pub heading: f32, pub omega: f32,
    pub hp: f32, pub shield: f32, pub last_hit_tick: u32,   // u32::MAX = never
    pub alive: bool, pub present: bool,
    pub arrive_tick: u32, pub control_lock_until: u32,
    pub throttle: [u8; MAX_THRUSTERS],                      // 0,1,2 → 0, ½, 1
    pub turret_angle: [f32; MAX_TURRETS],                   // body-frame, radians
    pub turret_cooldown: [f32; MAX_TURRETS],                // seconds remaining
    pub power: [f32; 3], pub power_target: [f32; 3],        // shields, engines, weapons
    // Reserved for M5+ (always NONE / None in M1; included in the hash):
    pub parent: ShipIdx, pub attach: Attach,                // Attach::{None, Docked, Mounted, Tethered}
}
pub struct Projectile {
    pub alive: bool, pub kind: WeaponKind, pub team: u8, pub owner: ShipIdx,
    pub pos: Vec2, pub vel: Vec2, pub speed: f32, pub damage: f32,
    pub life_ticks: u32, pub fire_tick: u32, pub target: ShipIdx, // torpedo only
}
pub struct Match {
    pub cfg: MatchConfig, pub tick: u32, pub rng: Pcg32, pub phase: MatchPhase,
    pub winner: i8,                        // -1 draw, 0/1 team, -2 not over
    pub ships: Vec<Ship>,                  // team 0 slots first, then team 1
    pub projectiles: [Projectile; MAX_PROJECTILES], pub proj_next: usize,
    pub pending: [ShipAction; MAX_SHIPS],
    pub events: EventBuf, pub hits: Vec<HitRecord>, pub rewards: [f32; MAX_SHIPS],
    pub reserves: [Vec<ShipIdx>; 2],       // reserved for bays (empty in M1)
}
```

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
role: fighter            # free string; the scripted controller dispatches on it
hp: 60
mass: 10.0
inertia: 55.0            # explicit in M1; derived from GLB footprint later
speed_cap: 60.0
static: false            # optional, default false
shield: null             # or {hp, regen_rate, regen_delay, radius}
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

M1 hull values (from `prototypes/story/hulls.js`; collision circles are new):

| hull | hp | mass | inertia | speed_cap | shield (hp/regen/delay/radius) | collision circles (pos, r) |
|---|---|---|---|---|---|---|
| fighter | 60 | 10 | 55 | 60 | none | (2.0,0) 2.4; (-2.2,0) 2.6 |
| strafer | 70 | 11 | 75 | 50 | 40 / 8 / 3 / 7.5 | (0,0) 3.2; (0,3.6) 2.4; (0,-3.6) 2.4 |
| gunship | 320 | 60 | 2200 | 24 | 140 / 12 / 4 / 11 | (4.5,0) 3.6; (0,0) 4.6; (-4.5,0) 3.8 |

Thrusters and turrets are copied verbatim from `hulls.js` (`force` → `max_force`,
`rest/arc/slew` → `rest_deg/arc_deg/slew_deg_s`; drop `size`/`height`, they are
render-only). Strafer: main 380 + four laterals 420, nose laser. Gunship: two mains
1700, four RCS 500; turrets fore flak (rest 0, arc 240, slew 120), port gauss (90,
220, 90), starboard gauss (-90, 220, 90).

Derived on load (stored in `HullDef`): `bound_radius = max(|c.pos| + c.r)`,
`shield_radius = shield.radius` or `bound_radius`, `has_shield`, `n_power_systems`
(3 if shield else 2), `arrival_speed = 1.4 * speed_cap`.

### 4.2 Weapon YAML (`assets/weapons.yaml`)

```yaml
gauss:   {kind: bullet,  speed: 240, range: 300, damage: 6,  interval: 0.16, spread_deg: 0.6}
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

Python: `DataError` → `ValueError` with the message. WASM: `JsError`.

## 5. Step order (`Match::step`)

Each stage loops over ships in slot order and over projectiles in pool order.
`active(s) = s.alive && s.present`. Let `P_s, P_e, P_w` be the power multipliers (§5.2).

1. **Clear** `events`, `hits`, `rewards`; `tick += 1`. If `phase == Over` return (the
   VecEnv never calls step on a finished match; WASM may, for an outro).
2. **Arrivals** (§5.6): ships with `!present && alive && tick >= arrive_tick` become
   present with `vel = heading_dir * arrival_speed`, `control_lock_until = tick + 21`
   (0.7 s), emit `Arrival`.
3. **Actions**: for each active ship, if `tick < control_lock_until` or `static`
   the pending action's throttles are forced to 0 and fire to 0 (power target still
   applies). Copy `throttle` from the action. Set `power_target` from the power head.
4. **Power slew**: `gap = max_k |target_k - power_k|`; `k = min(1, 0.45*DT/gap)`
   (0 if `gap == 0`); `power_k += (target_k - power_k) * k`. Shares stay summed to 1.
5. **Physics** (non-static, active): see §5.1.
6. **Turrets** (active): for each turret with `arc_deg > 0`:
   `angle += slew_action * slew_rate * DT`, clamped to `[rest - arc/2, rest + arc/2]`.
   `cooldown = max(0, cooldown - DT * 0.65 * P_w)`.
7. **Fire** (active, not control-locked): for each turret with fire action 1 and
   `cooldown == 0`: `cooldown = interval`; spawn per §6; emit `Fire`; add fire cost.
   Muzzle pose: `pos_w = to_world(turret.pos)`, `angle_w = heading + turret_angle + spread`,
   `spread = rng.range(-1, 1) * spread_deg/2` in radians.
8. **Projectiles** (§5.3): torpedo steer, advance, swept hit test, flak burst, expiry.
   Hits call `apply_damage` (§5.4) immediately, in pool order.
9. **Shield regen** (active with shield): if `tick - last_hit_tick >= round(regen_delay*30 / P_s)`:
   `shield = min(max, shield + regen_rate * P_s * DT)`.
10. **Ship–ship collisions** (§5.5), pairs `(i<j)`, both active.
11. **Arena** (§5.7): push and drain, active non-static.
12. **Deaths**: any ship with `hp <= 0 && alive` → `alive=false, present=false, hp=0`,
    throttles 0, emit `Death`. (Damage never flips `alive` directly; this stage does,
    so simultaneous kills are symmetric.)
13. **Termination** (§5.8) and terminal rewards.
14. `rewards` finalised (§8).

### 5.1 Physics

For each thruster `i` with throttle level `l ∈ {0,1,2}`:
`f = max_force * (l/2) * P_e`; body force `F_b = dir * f`; `τ += cross(pos, F_b)`;
`F_w += rot(heading) * F_b`. Then semi-implicit Euler:

```
vel   += F_w / mass * DT;   omega += τ / inertia * DT
vel   *= 0.995;             omega *= 0.94            # per-tick drag at 30 Hz
cap    = speed_cap * (0.6 + 0.4 * P_e)
if |vel| > cap: vel *= 1 - min(0.08, (|vel| - cap) / |vel|)   # soft cap
pos   += vel * DT;          heading = wrap(heading + omega * DT)
```

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
- Swept test against every enemy active ship whose `same_entity` is false:
  broad phase `segment_dist(pos, next, ship.pos) < bound_radius + 0.5`, then narrow
  phase against each collision circle in world space (`segment_hits_circle`, as in
  sim.js). First hit in slot order consumes the projectile; hit point = `next`
  clamped to the circle (closest point on the segment). Torpedo hits also emit `Burst`.
- Flak: on `life_ticks == 0` without a hit → burst: every enemy active ship with
  `|ship.pos - next| < burst_radius + bound_radius` takes full damage; emit `Burst`.
  Flak life is `life_ticks * (1 - fuse_jitter * rng.uniform())` at spawn.
- Expiry: `life_ticks == 0` → dead (bullets/torpedoes silently).
- Beams never enter the pool: resolved at fire time (§6).

Hit attribution: every damage application records
`HitRecord { shooter: ShipIdx, target: ShipIdx, damage: f32, fire_tick: u32, shield: bool }`
into `Match.hits` (capped at `MAX_HITS`; overflow counted in `Match.dropped_hits`).

### 5.4 Damage and shields

```
apply_damage(target, amount, point, shooter):
  target.last_hit_tick = tick
  if target.shield > 0:
      absorbed = amount / (0.7 + 0.3 * P_s(target))
      target.shield = max(0, target.shield - absorbed)
      n = normalize(point - target.pos)  (or (1,0) if zero)
      emit ShieldHit { target, pos: target.pos + n*shield_radius, normal: n, depleted: shield==0 }
      record HitRecord { shield: true, damage: amount }
  else:
      target.hp -= amount; emit Hit { target, pos: point, shooter }; record HitRecord { shield: false }
```

No overflow from shield to hull within one hit (as sim.js). Death is resolved in stage 12.

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
Until present a ship is invisible to hits, obs, collisions and the arena; its
throttle/fire are ignored. Arrival sets `vel = 1.4 * speed_cap` forward and locks
control for 21 ticks.

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
| bullet (gauss) | pool entry; `vel = ship.vel + speed*dir(angle)`; `life = range/speed` | swept circle | the spike's weapon |
| beam (laser) | none | hitscan: segment `muzzle → muzzle + range*dir` vs enemy circles, nearest hit; emit `Beam{from,to}` | damage applied at fire time |
| flak | pool; `vel = ship.vel + speed*dir`; jittered fuse | swept circle **or** proximity burst at fuse end | "spread bullet with a fuse"; burst radius 14 |
| torpedo | pool; `vel = speed*dir` (does **not** inherit ship velocity); `life *= life_factor` | swept circle; `Burst` on hit | target chosen at spawn: active enemy within `range` and within `lock_cone_deg/2` of the muzzle line, smallest angular error; none → flies straight |

Decisions: **no magazine/reload in M1** (cooldown only; the power split already
modulates fire rate; v1 showed reload as an action is a learning tax). Fields are
reserved. **Fixed cooldown**, no ±15 % jitter (keeps credit assignment clean).
**No friendly fire** (team filter on every hit path). Torpedo target lock is weapon
mechanics, not an autopilot action: the policy still points the rack and pulls the
trigger.

## 7. Actions and observations

### 7.1 Action encoding

Per ship slot, a row of `ACTION_WIDTH = 21` `int8`:

```
[0..8)   thruster throttle   ∈ {0,1,2}     (0 = off, 1 = ½, 2 = full)
[8..14)  turret slew         ∈ {0,1,2}     (0 = left, 1 = hold, 2 = right)
[14..20) turret fire         ∈ {0,1}
[20]     power target        ∈ {0..6}
```

Batched: `actions[N, S, 21] int8`. Unused slots (beyond the hull's thruster/turret
count) are ignored by the sim; masks tell the policy which heads matter:
`thruster_mask[N,S,8] bool`, `turret_mask[N,S,6] bool`, `fixed_turret[N,S,6] bool`
(arc 0 → slew head meaningless), `act_mask[N,S] bool` = present && alive &&
!control-locked (actions of masked ships are ignored; their log-probs should be
excluded from the PPO loss). Values out of range are clamped, not errors.

`ShipAction { throttle: [u8;8], slew: [u8;6], fire: [u8;6], power: u8 }` with
`ShipAction::from_row(&[i8]) / to_row(&mut [i8])`.

### 7.2 Observation (fixed vector for the spike)

`OBS_DIM = 204` `f32`, body frame of the observing ship (relative vectors rotated by
`-heading`, so forward = +x). Scales: `R` = arena radius, `VS = 100` m/s, `OM = 4`
rad/s, `L = 20` m, `A = 100` m/s², `HP = 400`, `DMG = 60`. Values are clamped to
`[-5, 5]` after scaling. Absent entities/slots are all-zero with `present = 0`.
Blocks (offset: width — features):

```
0:   20  self + arena
       0 present            1 control_locked      2 speed/VS           3 fwd_speed/VS
       4 lat_speed/VS       5 omega/OM            6 hp/max_hp          7 shield/max_shield (0 if none)
       8 time_left = (time_limit - tick)/time_limit                    9 has_shield
       10-12 power S,E,W    13 mass/100           14 speed_cap/VS      15 bound_radius/L
       16 max_hp/HP         17-18 dir_to_centre (body, unit)           19 (R - |pos|)/R
20:  48  thrusters, 8 slots × 6: present, pos.x/L, pos.y/L, dir.x, dir.y, (max_force/mass)/A
68:  60  turrets, 6 slots × 10: present, pos.x/L, pos.y/L, sin(angle), cos(angle),
         cooldown/interval, kind one-hot[4] (bullet, beam, flak, torpedo)
128: 36  nearest 3 active ships by distance (allies and enemies), × 12: present, is_enemy,
         rel_pos.x/R, rel_pos.y/R, rel_vel.x/VS, rel_vel.y/VS, sin(rel_heading),
         cos(rel_heading), hp/max_hp, shield/max_shield, bound_radius/L, dist/R
164: 28  nearest 4 live projectiles by distance (hostile and own), × 7: present, hostile,
         rel_pos.x/R, rel_pos.y/R, rel_vel.x/VS, rel_vel.y/VS, damage/DMG
192: 6   turret slot j: arc/(2π)  (0 for fixed guns)
198: 6   turret slot j: weapon range/R
204 = OBS_DIM
```

`write_obs` lives in `obs.rs` with `pub const` offsets for every block so Python can
slice by name (`rlf_sim.OBS_LAYOUT` dict exported by sim-py). Turret `angle` is the
current body-frame angle; `rel_heading = other.heading - self.heading`.

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
| damage dealt | `+0.01 * damage` to hull, `+0.005 * damage` to shields (shooter) |
| damage taken | `-0.01 * hull damage`, `-0.005 * shield damage` (target) |
| fire cost | `-0.002` per shot actually fired (not per trigger pull on cooldown) |
| arena | `-0.002` per tick while `|pos| > R` |
| terminal | `+1` every ship on the winning team, `-1` losing team (dead ships too); draw 0 |

Dead or not-yet-present ships get 0 except the terminal term. Rewards are not
normalised in the sim.

**Retroactive projectile credit**: the sim attributes every hit to `owner` and records
`fire_tick` (projectiles carry both). The VecEnv exposes per step
`hits[N, MAX_HITS, 5] int32` = `(shooter, target, fire_tick, damage*1000, shield)` and
`hit_count[N] int32`; the Python `CreditAssigner` (v1 `spacefight/rl/credit.py`)
converts `fire_tick` to a rollout buffer step with the env's `tick` at rollout start
and the episode generation counter, exactly as v1. The sim does not inject credit.

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
    Hit       { target: u8, shooter: u8, pos: Vec2, damage: f32 },
    ShieldHit { target: u8, shooter: u8, pos: Vec2, normal: Vec2, depleted: bool },
    Burst     { team: u8, pos: Vec2, radius: f32 },      // flak fuse, torpedo impact
    Death     { ship: u8, pos: Vec2 },
    Arrival   { ship: u8, pos: Vec2, heading: f32 },
}
```

`EventBuf` is a `Vec<Event>` with capacity `MAX_EVENTS`, cleared each step. Flat
encoding for FFI: `[f32; 8]` per event = `[kind, a, b, x, y, nx_or_x2, ny_or_y2, extra]`
(kinds 0..6 in the order above; `a,b` = ship/turret or target/shooter; `extra` =
angle / damage / radius / heading / depleted). WASM: `WasmMatch.events_ptr() -> *const f32`,
`events_len() -> usize`, read as a `Float32Array` view on `memory.buffer` after each
`step()`. Python: `VecEnv(record_events=False)`; when true, `events()` returns a copied
`[E, 9] f32` array with a leading match index column (debug/visualisation only).

## 10. Bindings

### 10.1 sim-py (`rlf_sim`)

```python
env = rlf_sim.VecEnv(assets_dir: str, n_envs: int, fleets: list[list[str]],  # [[team0 hulls],[team1 hulls]]
                     seed: int, arena_radius: float = 450.0, time_limit_s: float = 90.0,
                     n_threads: int = 0, record_events: bool = False)
env.n_ships -> int (S, padded to the fleet total; MAX_SHIPS cap)
env.reset()                       # rebuild every match with episode_count = 0
env.step()                        # reads env.actions, advances all matches, auto-resets
# zero-copy buffers, owned by the env, overwritten in place on every step():
env.obs      [N,S,204] f32     env.actions   [N,S,21] i8 (write here before step)
env.rewards  [N,S] f32         env.dones     [N] bool        env.winner [N] i8
env.act_mask [N,S] bool        env.thruster_mask [N,S,8] bool  env.turret_mask [N,S,6] bool
env.fixed_turret [N,S,6] bool  env.team [N,S] i8  env.hull_id [N,S] i16  env.alive [N,S] bool
env.tick [N] u32  env.episode_count [N] u32  env.hits [N,64,5] i32  env.hit_count [N] i32
env.scripted_actions(team: int | None = None)   # writes the scripted controller's actions into env.actions for the given team (or all ships)
env.state_hash() -> np.ndarray[N] u64           # per match
env.render_state(i) -> dict                     # ships/projectiles of match i (debug)
rlf_sim.OBS_LAYOUT, rlf_sim.ACTION_LAYOUT, rlf_sim.SIM_VERSION
```

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
  ships_ptr(): number; ships_len(): number;        // flat f32, SHIP_STRIDE per ship (pos, vel, heading, omega, hp, shield, alive, present, team, hull, throttles[8], turret_angles[6], power[3])
  projectiles_ptr(): number; projectiles_len(): number;  // flat f32 stride 8
  events_ptr(): number; events_len(): number;
  obs(ship: number): Float32Array;    // for in-browser inference (M2)
  tick(): number; phase(): number; winner(): number; state_hash_hex(): string;
}
```

`config_json` is `MatchConfig` serialised with serde (`{"seed":..,"arena_radius":..,"time_limit_ticks":..,"fleets":[["fighter"],["fighter"]]}`
with hull names resolved on the WASM side).

## 11. Scripted controller (Rust, `scripted/`)

Lives in Rust (decision): usable as BC target, baseline opponent, and in the browser
without a second implementation. Interface:

```rust
pub fn act(m: &Match, cat: &Catalogue, ship: ShipIdx) -> ShipAction;  // deterministic, reads state
pub fn allocate_thrusters(hull: &HullDef, force_body: Vec2, torque: f32) -> [u8; MAX_THRUSTERS];
```

`allocate_thrusters` is the sim.js greedy allocator: `along = dot(dir, f̂) * min(|f|,1)`,
`arm = cross(pos, dir)`, `score = along + 1.2 * sign(arm) * torque`; `> 0.6 → 2`,
`> 0.25 → 1`, else 0.

Fighter (`role == "fighter"`), per tick:
1. Target = nearest active enemy (`dist`), else coast (all zero, power 0).
2. Lead: `t = dist / 240`; `aim = atan2(rel_pos + rel_vel * t)`; `err = wrap(aim - heading)`.
3. `go = 1 if dist > 60 || |err| > 1.2 else 0.3`; `force_body = (go * (1 if |err| < 0.9 else 0.2), 0)`.
4. Arena: if `|pos| > 0.85 R` → `aim = atan2(-pos)`, `force_body = (1, 0)`.
5. `torque = clamp(2.5 * err - 1.6 * omega, -1, 1)`; throttles = allocator.
6. Turrets: fixed gun fires if `|err| < 0.1 && dist < range && cooldown == 0`; turreted
   guns slew toward `wrap(bearing - angle)` (left/right by sign, hold within 0.03 rad)
   and fire when `|aim_err| < 0.06`.
7. Power: `3` (weapons) if `dist < range`, `2` (engines) if `dist > 1.5 range`, else 0;
   `1` (shields) if `tick - last_hit_tick < 36 && shield/max < 0.3` (shielded hulls).

Strafer (orbit at 120 m, `orbit_sign = +1 if slot even else -1`) and gunship (standoff
170 m, broadside) are ported from sim.js as `strafer.rs` / `gunship.rs` in WP7b; a
hull whose role has no controller returns the all-zero action. The controller reads
`Match` state, not obs, so BC pairs are `(obs_t, act(state_t))`.

## 12. Determinism contract and test

- `state_hash()`: FNV-1a 64 over, in order: `tick`, rng state (two u64), each ship's
  fields (`to_bits()` for f32, raw for ints/bools), each projectile pool slot, `proj_next`,
  `phase`, `winner`. Implemented in-crate (`hash.rs`), no `std::hash`.
- Native test (`crates/sim/tests/determinism.rs`): for each scenario in
  `{1v1 fighter seed 7, 2v2 fighter+strafer vs gunship+fighter seed 11, 3v3 mixed seed 13}`,
  run 3000 ticks with the scripted controller on both sides; assert the hash at ticks
  `{1, 30, 300, 1000, 3000}` equals `tests/golden/<scenario>.txt`. Regenerate golden
  only with `UPDATE_GOLDEN=1`; a diff in golden is a `sim_version` bump.
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

Budget reasoning: one 2-ship tick with ~20 projectiles and a 204-float obs is ~2–4 µs;
256 of them is ~0.7 ms single-threaded, so 16 cores plus ~50 µs of PyO3 overhead
leaves headroom. At the target, the 4-hour nightly budget is sim-bound at >2 × 10^10
match-ticks; policy inference will dominate.

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
agents (3, 4, 6, 7) at once; after WP5, two (8, 9).

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
