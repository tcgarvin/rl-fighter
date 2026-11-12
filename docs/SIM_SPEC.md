# RL Fighter — M1 Simulation Spec (Rust core + Python bindings)

Status: implementation spec for milestone M1, written 2026-10-28; revised the same
day to **SIM_VERSION 2** (§0) after M1 landed, to **SIM_VERSION 3** (§0.1,
collision damage) on 2026-10-29, to **SIM_VERSION 4** (§0.2: missions, carriers,
convoys, the commander layer; M3 stage A, WP-S1) on 2026-10-30, and to **SIM_VERSION
5** (§0.3: orders reach the pilots, the order reward, the random commander; M3 stage
B, WP-B1) the same evening. `docs/DESIGN.md` is the source of
truth for direction; this file pins the decisions implementers need. When the two
disagree, fix this file and note it in the lab journal.

Scope of M1: **M1a** `crates/sim` (three hulls, thrusters, power split, turrets, four
weapon kinds, shields, compound-circle hits, ship collisions, arena, arrival, skirmish
termination, events, obs, rewards, scripted fighter) and **M1b** `crates/sim-py`
(batched VecEnv over N matches, zero-copy numpy buffers, throughput benchmark). The
`crates/sim-wasm` crate must build and pass the native-vs-WASM determinism test, but
has no renderer yet (that is M2).

Not in M1 (but the data model leaves room, see §3.4): bomber, carrier, station, bays,
docking/repair, attached/tethered ships, friendly fire, damage types, ammo/heat,
GLB-derived geometry. (Collision damage was out of M1; v3 adds it, §0.1.)

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
| 9 | Duel balance (data): gauss **5 dmg** / 0.20 s / 220 m / 200 m/s / 1.0° spread; fighter 80 hp. The plan's starting point was 3 dmg; the WP15 sweep moved it to 5 (`lab/runs/2026-10-28-sim-v2/results.md`). | v1 duels end on the first head-on pass (plan §2.1) | §4.1, §4.2 |
| 10 | Scripted fighter extends after a merge and no longer throttles down inside 60 m (WP15) | two sim.js fighters parked nose to nose inside gun range for the whole duel, so v2 nose armour took nearly every hit and there were no passes | §11 |

Also folded in from what WP1–WP10 built (deviations the packages recorded in code
comments; the spec now matches them): hull roles are `fighter` / `skirmisher`
(strafer) / `anchor` (gunship); the scripted turn gain is 10, not 2.5; `Projectile`
carries its `weapon` id; `Match` has `shots_fired`, `outside_arena`, `dropped_hits`;
the VecEnv has `dt`, `step(actions=None)` and `events()`; the determinism suite has
four golden scenarios including a random-action one; the golden traces also digest
every step's events, hits, rewards and obs.

### 0.1 v3 changes (SIM_VERSION 2 → 3)

| # | change | why | sections |
|---|---|---|---|
| 1 | Collision damage: a closing contact faster than `COLLISION_FREE_SPEED = 10` m/s damages both non-static ships by `COLLISION_DAMAGE_PER_J = 0.002` hp per joule of excess normal kinetic energy, through the shield-then-hull rule, scaled per ship by its impact arcs. No `HitRecord`, no credit, never flips `alive`; sets `last_hit_tick`. | The contact survey (`lab/runs/2026-10-29-collision-damage/survey/`) found ship contacts in every duel, 99 % nose to nose at a median ~95 m/s closing, with no consequence beyond a bump: ramming was free | §5 stage 10, §5.5 |
| 2 | Optional hull `impact` arcs (same format and rules as `armour`): fighter and strafer nose (±45°) 1.5×, elsewhere 1×; gunship 0.75× all round | Fighters should be fragile in crashes and most fragile nose first, so pilots learn to turn away; done in physics, not as a reward term | §4.1, §4.4 rule 12 |
| 3 | Reward: collision damage is damage taken (`-0.01` hull, `-0.005` shield) for the damaged ship; nobody is credited. `Match.collision_damage` / `collision_shield_damage` are per-step outputs; the VecEnv exposes `collision_damage [N,S]` | A crash is not a kill shot; crediting the other ship would reward ramming | §8, §10.1 |
| 4 | Event `Collision { a, b, pos, normal, closing }`, kind code 7 (appended after `Arrival`, so codes 0–6 are unchanged) | Renderer spark at the impact; eval crash counts | §9 |
| 5 | Scripted fighter deconflicts (no sim rule change; the scripted golden traces regenerate again): predicts closest approach and sidesteps on RCS / breaks away from a pass that would come within 11 m, stops burning above 40 m/s meeting a target head-on, extends to 0.6 × gun range (was 1.2) | The v2 script rammed through every merge (10.8 contacts per duel); under v3 that made script-vs-script duels 60 % draws, mostly mutual crash kills, ~8 s long. The script is the BC teacher and baseline opponent, so it has to fly passes that miss | §11 |

### 0.2 v4 changes (SIM_VERSION 3 → 4, M3 stage A / WP-S1)

| # | change | why | sections |
|---|---|---|---|
| 1 | `MAX_SHIPS` 8 → 20 (docked reserves count). `obs::N_NEAR_SHIPS` is now its own const, **7**: `OBS_DIM` stays 385 and the obs layout is unchanged (a pilot sees the nearest 7 present ships). `MAX_BAYS = 4`, validation rule 13 | carrier wings and convoys need ~16–20 ships; pilot v1 must keep flying | §3, §4.4, §7.2 |
| 2 | Hulls `carrier` (role `carrier`, two bays) and `freighter` (role `transport`: unarmed, weak heading-hold RCS). Hull ids shift: carrier 0, fighter 1, freighter 2, gunship 3, strafer 4 (nothing keys on raw ids; obs is feature-based) | M3 missions | §4.1 |
| 3 | Missions in `MatchConfig.mission`: `Deathmatch` (default, the v3 match), `CarrierBattle`, `ConvoyEscort`; per-mission setup, termination, winner, time-limit tiebreak and `EndReason` | M3 plan §1 | §5.8, §5.10 |
| 4 | Hangars and launches: docked reserves (`Attach::Docked`, `parent` = carrier, `Match.reserves`), launched from bays with a cooldown | carrier battle | §5.9 |
| 5 | The commander layer: a slow tick every `COMMAND_TICKS = 60` (stage 1b), squads with orders, capital-ship waypoints, launches; `CommanderMode::{Scripted, External}` per team; a coarse `CommanderObs`. Squads, orders and waypoints are hashed state | DESIGN §7 "Hierarchy" | §5 stage 1b, §5.9 |
| 6 | Convoy jump-out (stage 12b): charge inside the jump radius, then leave the field and count as escaped (`JumpState`) | convoy escort | §5.10 |
| 7 | Events `Launch` (8), `Order` (9), `JumpCharge` (10), `JumpOut` (11), `MatchEnd` (12), appended so codes 0–7 are unchanged | the web log, lines and result | §9 |
| 8 | Scripted capital-ship pilots (`carrier`, `transport`) and the scripted commander (WP-S1 stub, replaced in WP-S2: §5.9) | missions playable end to end | §11 |
| 9 | State hash appends reserves, mission state and command state after `winner` | determinism | §12 |
| 10 | `PILOT_COMPAT_VERSIONS = [3, 4]`: pilots trained under v3 fly in v4. Deathmatch with ≤ 8 ships is **bit-identical to v3**, proven by `tests/determinism.rs::v3_compat_*`, which replay the four v3 golden traces (kept verbatim in `tests/golden/v3/`) with the v3 hash (v3 hull ids, no v4 state) and the aux digest without event kinds ≥ 8 | pilot v1 is the live champion | §10, §12 |

Bindings: PyO3 and WASM gain mission selection, end reasons, external commands, the
commander and mission views, and a shared JSON spec (§10.1–10.3). Bundles and the
champion registry accept a pilot whose `sim_version` is in `PILOT_COMPAT_VERSIONS`
(bundle manifest `sim_version` = the wasm's, `pilot_sim_version` = the policy's).

**WP-S2 (still SIM_VERSION 4; stage A's sim was not shipped between WP-S1 and WP-S2).**
The real scripted commander (§5.9), scripted strike craft that follow their squad's
order (§11 "Squad orders"), the carrier pilot's rate profile and RCS hysteresis and
point-defence flak (§11), hull retunes (carrier: hp 1500 → 1000, cap 10 → 8 m/s, mains
7000 → 300 N, RCS 3500 → 450 N; freighter: hp 500 → 400, cap 14 → 10.5 m/s; mounts
unchanged) and the default mission rosters (§10.3, `mission::default_rosters`), all
chosen with the mission survey (`lab/runs/2026-10-30-mission-survey/`). The v4 golden
traces were regenerated: the missions' because their play changed, the deathmatch ones
only because the deathmatch commander now forms two squads (command state is hashed
and `Order` events are in the aux digest). Deathmatch trajectories are unchanged: the
`v3_compat_*` replays still pass untouched, since scripted pilots do not follow a
scripted deathmatch commander.

### 0.3 v5 changes (SIM_VERSION 4 → 5, M3 stage B / WP-B1)

The M3 plan's "Stage B decisions" are the spec; this table is the diff and the reasons.

| # | change | why | sections |
|---|---|---|---|
| 1 | **Order block** appended to the obs: `OBS_DIM` 385 → 403, block `order` (18 floats) at offset 385. The first 385 floats are exactly v4's for the same state (`obs::OBS_DIM_V4`) | pilots must see their order (DESIGN §7 "Hierarchy"); appending keeps every v3/v4 pilot flying on the prefix | §7.2 |
| 2 | A ship's **own order** (`order` module): a strike craft's squad order; a capital ship with a waypoint has it as a hold of 25 m (for stage B′); an attack whose target is no longer active, or a guard whose ward is not on the field, reads as none at once | one notion of "my order" for the obs and the reward; a dead target should not keep pulling the pilot until the next slow tick | §5.9 |
| 3 | **Order instances** per ship (hashed `OrderTrack`: kind, target, point, start tick, arrived, presence ticks, last Φ). A new instance whenever the ship's order kind, target or hold point changes (a radius change alone does not) | the obs's "time since order" feature and the per-instance reward caps need it, and it must be deterministic | §5.9, §8 |
| 4 | **Order reward** in its own buffer `order_rewards[N,S]` (stage 13b): attack damage on the target, guard/hold potential shaping with a reset per instance, a one-shot arrival bonus, capped presence, guard damage near the ward. `rewards` is unchanged | Python weights it (`w = 1`, `w = 0.3` arms); capped because uncapped presence under the scripted carrier guard pays more than winning | §8 |
| 5 | `CommanderMode::Random` (`"random"`): the scripted logistics, random squads and orders, on its own rng streams (one per team, hashed) | training on any order, not just the script's habits; its own streams so a scripted match is untouched | §5.9 |
| 6 | `PILOT_COMPAT_VERSIONS = [3, 4, 5]` and `PILOT_OBS_DIMS = {3: 385, 4: 385, 5: 403}`: a pilot of version `v` reads `obs[..., :PILOT_OBS_DIMS[v]]` | frozen v1 opponents, older bundles on the live page | §10 |
| 7 | `MAX_TRAIN_SHIPS = 12` (`sim::setup`): the slots a stage B training env pads to | carrier battles and convoys with 4–5 strike craft a side | §10.1, §13 |
| 8 | State hash appends the random commander's state, then every slot's order track | determinism | §12 |

**Compatibility.** Under the scripted commander nothing a v4 match does changes: the
`v4_compat_*` replays (`tests/determinism.rs`) run all six v4 golden scenarios (kept
verbatim in `tests/golden/v4/`) and render them as v4 did (the hash without the v5
state, the aux digest over the first 385 obs floats): every trajectory, reward, hit,
event and obs prefix is bit-identical, missions included. The `v3_compat_*` replays
still pass too. So fleet pilot v1 (v3) flies a v5 bundle unchanged on the obs prefix
(tested by the headless live smoke on a v5 bundle).

**Judgement calls** (easy to change; each has its reason):
- *No order → an all-zero block*, mission one-hot and order age included. An order-less
  row is then exactly a v4 obs padded with zeros, which is what the run's KL anchor to
  v1 on `has_order = 0` rows wants; the mission is visible whenever there is an order.
- *Hit credit uses the standing order*, shaping/arrival/presence the effective one: the
  hit that kills an attack target is paid although the effective order is already none.
- *Capital waypoints also earn the order reward* (as holds of 25 m), so the obs and the
  reward agree on what "my order" is for B′. Stage B trains strike rows only, so it
  does not matter there.
- *Random squads are fixed per ship for the match* (drawn once per slot, docked
  reserves included); the orders change, the membership does not. Three squads.
- *A cleared order is redrawn at once* (target dead, ward gone), not at its timer, so a
  random squad does not idle for up to 16 s.
- *Shaping γ = 0.99*, the trainer's PPO γ. (Since made per match: §8,
  `MatchConfig.order_shaping_gamma`.)

### 0.4 v6 changes (SIM_VERSION 5 → 6, M3 stage B3 / WP-B3-sim)

The M3 plan's "Stage B3: orders redesigned" is the spec; this table is the diff and
the reasons (`lab/runs/2026-10-31-order-pilot{,-b2b}/results.md`: run 1 barely
followed orders, B2b followed them and lost its fights).

| # | change | why | sections |
|---|---|---|---|
| 1 | Orders **attack / defend / go-to / none**: `Order::Guard` → `Defend { ward }`, `Order::Hold` → `GoTo { point, radius }` (kind codes 2 and 3 unchanged; JSON `"defend"`, `"goto"`). Capital waypoints read as go-to of 25 m | hold rewarded parking; a defender should fight what threatens its ward, not hold a ring | §5.9, §10.3 |
| 2 | **Go-to completes per ship on arrival**: once inside the radius its *effective* order is none (obs `has_order = 0`, no order reward, the script falls back to its role) while the squad's standing order lasts. A point re-issued within `GOTO_SAME_POINT = 40` m of the instance's first point is the same instance | waves that used to wait at a hold fight on arrival; re-staging a screen cannot farm the arrival bonus | §5.9, §8 |
| 3 | Order instances are keyed on the **standing** order (v5: the valid one): a target or ward that dies does not start an instance; `OrderTrack` loses `presence_ticks` | the trainer's instance bookkeeping (censoring by death) needs the instance to outlive its target | §5.9 |
| 4 | **Threat set** of a ward: enemies within their own longest weapon range + `THREAT_MARGIN = 40` m + the ward's bound radius of it, or that damaged it in the last `RECENT_HIT_TICKS = 150` ticks (`Match.hit_by`, hashed) | no fixed guard ring: reach differs by hull (a torpedo rack would outrange any ring) | §5.9 |
| 5 | **Order reward**: defend pays damage on the ward's threat set, `−0.5 ×` the ward's hull fraction lost per step and `−0.3` on its death, to every defender via its standing order; no location terms. Go-to: shaping as before until arrival, arrival `0.2`, no presence. Attack unchanged | rewards what defending is for; presence paid for parking | §8 |
| 6 | Obs `OBS_DIM` 403 → **583**: `ship_extras` (7 × 10, per `ships` slot: hull-class one-hot, reach, distance to my order point, is my order ship, hit my ward) and `order_ships` (5 × 22: the ships nearest my order point, record + extras). The first 403 floats are v5's | a defender must judge threats round its ward, which may be far from itself | §7.2 |
| 7 | **Hidden-order mode** (`MatchConfig.hide_orders[team]`): that team's obs shows no order (block, `order_ships`, order extras zero), exactly as without one; rewards and scripts unchanged | the order-following gates compare a pilot with its order hidden by the sim, on paired seeds | §7.2, §10 |
| 8 | Scripts: a defender engages its ward's threat set (recent hitters first, then nearest the ward), stations on the ward only with the set empty; a go-to flies to the point (0.9 of its speed cap). Scripted commander: defend for guard, go-to for hold. Random commander: defend wards a capital ship with probability 0.5 when the team has one | the scripts are the order-following teacher | §5.9, §11 |
| 9 | `PILOT_COMPAT_VERSIONS = [3, 4, 5, 6]`, `PILOT_OBS_DIMS = {3: 385, 4: 385, 5: 403, 6: 583}`; bindings: `order_transit`, `ward_threat`, `ward_hull_lost`, `order_tracks()`, `hide_orders` | frozen v1 and v5 pilots fly on their prefix; the trainer's transit-row pull and the eval's defend metrics | §10 |
| 10 | State hash appends `hit_by` (the match's slots, row by row) | determinism | §12 |

**Compatibility.** Under the scripted commander a deathmatch is unchanged: the
`v5_compat_*` replays render the four deathmatch scenarios as v5 did (v5's order
tracks, keyed on the valid order, rebuilt by the test; the aux digest over the first
403 obs floats plus the order rewards) and match the v5 traces kept in
`tests/golden/v5/` bit for bit; `v3_compat_*` and the deathmatch `v4_compat_*` still
pass. The missions change by design (the scripted commander's orders and the
order-following scripts), so the v4 mission traces are no longer replayed. Fleet pilot
v1 flies the missions exactly as before: it does not read orders, and the mission
survey's live mode is bit-identical between v5 and v6.

### 0.5 v7 changes (SIM_VERSION 6 → 7, crash damage by velocity change)

The owner's change (2026-11-09): a small ship that crashes into a big one should pay
for it, since its velocity changes far more. The v3 energy term is unchanged; a second
term is added.

| # | change | why | sections |
|---|---|---|---|
| 1 | Each non-static ship in a damaging contact also takes `CRASH_HULL_PER_DV = 1.25` hull points per m/s of its **own velocity change** `jimp * w_k` above `CRASH_DV_FREE = (1 + e) * COLLISION_FREE_SPEED = 12` m/s, times its impact arc, **past any shield**, into `collision_damage` | the v3 term gave both ships the same damage, so a fighter that hit a carrier lost no more than the carrier; a fighter at full speed into a capital ship now dies at any bearing | §5.5 |
| 2 | Scripted strike craft **avoid crashes with any ship** (`scripted/avoid.rs`), not only a fighter's target | under row 1 the script rammed freighters, its own capital ships and passing strike craft, and died of it | §11 |
| 3 | `PILOT_COMPAT_VERSIONS = [3, 4, 5, 6, 7]`, `PILOT_OBS_DIMS` adds `7: 583` | obs and actions are v6's | §10 |

**Compatibility.** Obs and actions are unchanged, which is what an old pilot needs to
fly. Trajectories change wherever ships crash hard or a scripted strafer or gunship
flies: only the fighter duel is still bit-identical to v3, v4 and v5
(`v3_compat_duel_*`, `v4_compat_duel_*`, `v5_compat_duel_*`); the mixed and
random-actions scenarios are no longer replayed (`tests/golden/v3/`, `v4/`, `v5/` keep
their record). Pilots of v3 to v6 still fly, but were trained when crashes cost a light
ship less and against a script that rammed.

### 0.6 v8 changes (SIM_VERSION 7 → 8, go-to deadlines)

The owner's decision (2026-11-12) after a diagnostic of the go-to drills: pilots read a
go-to but kill enemies first and arrive late, and stop 40 to 60 m short of the circle.
The deadline existed only in the eval; nothing in the order, the pay or the obs
carried it. Now a go-to may carry one, the pilot sees the time left, and the pay is
strict about the deadline but free before it, so an order with time to spare leaves
room to fight on the way. No commander in the sim issues a deadline yet: they come from
external commands (drills first).

| # | change | why | sections |
|---|---|---|---|
| 1 | `Order::GoTo { point, radius, deadline }`: `deadline: u32` is the match tick to be inside the radius by, `NO_DEADLINE = 0` for none (JSON `"deadline"`, default 0). Any value is accepted. The scripted, random and learned commanders and capital waypoints pass `NO_DEADLINE`. Hashed with the order | the order has to say when | §5.9, §10.3 |
| 2 | `OrderTrack` gains `deadline` and `missed` (both hashed). A go-to re-issued with **another deadline is a new instance**, even at the same point | a new deadline is a new thing to do, with its own pay | §5.9 |
| 3 | **Arrival and expiry.** Inside the radius at the end of a step whose tick is ≤ the deadline: arrived in time. At the end of the first step whose tick is > the deadline, a ship of the instance that has not arrived has **missed**: `missed = true` and its effective order is none from then on, as after an arrival (obs shows no order, no shaping, the script flies its role, a drill no longer waits for it, a learned commander's hold on it is spent). The squad's standing order stays. A deadline already past when the order lands is missed on that step | "be there by tick y" has to end at tick y | §5.9, §5.10, §11 |
| 4 | **An instance that starts with the ship on the field and already inside the radius is complete at once and pays no arrival bonus** (every go-to, deadline or not; v7 paid 0.2 on that step) | row 2 would otherwise let a commander farm the bonus by re-issuing deadlines to a ship that is already there | §5.9, §8 |
| 5 | **Pay.** A go-to with a deadline has the no-deadline shaping until arrival or expiry, pays `MatchConfig.goto_timed_bonus` (default `ORDER_TIMED_ARRIVAL_BONUS = 1.0`) instead of 0.2 for arriving in time, and charges `MatchConfig.goto_miss_penalty` (default `ORDER_MISS_PENALTY = 1.0`) once on a miss; a ship that is dead or absent on that step is marked missed but not charged. Nothing is charged for time before the deadline. Both config values are validated (finite, ≥ 0) and, like `order_shaping_gamma`, are not hashed | strict about the deadline, free before it | §8 |
| 6 | Obs `OBS_DIM` 583 → **587**: block `order_time` (4 floats) at offset 583: has_deadline, time left, urgency, closeness. All zero unless the ship sees a go-to. The first 583 floats are v7's | the pilot has to see the clock; and the order block's distance, scaled by the arena radius, moves 0.1 over the last 45 m, which may be too coarse to finish on | §7.2 |
| 7 | `PILOT_COMPAT_VERSIONS = [3, 4, 5, 6, 7, 8]`, `PILOT_OBS_DIMS` adds `8: 587`; v6 and v7 pilots keep reading their 583-float prefix (`OBS_DIM_V7`). Bindings: `goto_timed_bonus` / `goto_miss_penalty` kwargs and getters, `order_tracks()` adds `deadline` and `missed`, `NO_DEADLINE`, `OBS_DIM_V7` | older pilots fly on; the trainer sets the pay | §10 |

Not changed: the `Order` event and the wasm `squads()` view keep their layouts (all
eight event floats are in use, and the web client reads nine floats per squad), so a
deadline is visible in the JSON views (`mission_state`, `commander_obs`) and in
`order_tracks()` only.

**Compatibility.** With no deadline issued, v8 flies exactly as v7. The `v7_compat_*`
replay renders all nine v7 scenarios as v7 did (the state hash without the deadlines
and `missed`; the aux digest over the first 583 obs floats plus the order rewards) and
matches the v7 traces kept in `tests/golden/v7/` bit for bit: every ship and
projectile, obs prefix, reward, hit and event, under the scripted and the random
commander, in every mission. Row 4 is the one rule that reaches such a match. It
changes only the order reward of the step an instance starts on (v7 marked the ship
arrived on that same step, so nothing a ship or a script reads differs); the replay adds
the 0.2 back for those steps and so shows that nothing else about the order reward
moved. It fires 4, 4 and 2 times in the three random-commander scenarios and never
under the scripted commander. `v3_compat_duel_*`, `v4_compat_duel_*` and
`v5_compat_duel_*` still pass.

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
  src/lib.rs               # re-exports; SIM_VERSION (4), PILOT_COMPAT_VERSIONS (v4)
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
  src/mission.rs           # v4: Mission, EndReason, JumpState, MissionState, setup, rules, termination
  src/command.rs           # v4: squads, orders, waypoints, launches, commands, CommanderObs
  src/spec.rs              # v4: JSON specs and views shared by the bindings (§10.3)
  src/step.rs              # Match::step (order in §5), termination, winner
  src/events.rs            # Event enum, EventBuf, flat encoding
  src/obs.rs               # obs layout consts + write_obs (§7)
  src/reward.rs            # per-ship reward + HitRecord accumulation (§8)
  src/scripted/mod.rs      # allocate_thrusters, act(match, ship) dispatch
  src/scripted/fighter.rs  # fighter controller (§11)
  src/scripted/capital.rs  # v4: carrier and transport pilots (§11)
  src/scripted/commander.rs # v4: the scripted commander (WP-S2) (§5.9)
  tests/                   # integration tests per work package (§12)
  tests/golden/            # determinism hash traces (§9)
crates/sim-py/             # pyo3 0.30 + numpy 0.30 + rayon; maturin; module `rlf_sim`
  src/lib.rs               # #[pymodule]; VecEnv class; Catalogue loading; bench
crates/sim-wasm/           # wasm-bindgen; WasmMatch wrapper (one match)
assets/hulls/<name>/hull.yaml   # carrier, fighter, freighter, gunship, strafer (v4)
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
    pub mission: Mission,                            // v4; default Mission::Deathmatch (§5.10)
    pub commanders: [CommanderMode; 2],              // v4; default [Scripted; 2] (§5.9)
    pub hide_orders: [bool; 2],                      // v6; default [false; 2] (§7.2)
    pub order_shaping_gamma: f32,                    // default 0.99; in (0, 1] (§8)
    pub goto_timed_bonus: f32,                       // v8; default 1.0; finite, >= 0 (§8)
    pub goto_miss_penalty: f32,                      // v8; default 1.0; finite, >= 0 (§8)
    pub start_layout: Option<Vec<ShipStart>>,        // default None; where each slot starts (§5.10)
    pub drill: bool,                                 // default false; drill rules (§5.10)
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
pub const MAX_SHIPS: usize = 20;     // per match (both teams, docked reserves included; v4, was 8)
pub const MAX_BAYS: usize = 4;       // v4: bays per hull (rule 13)
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
    // v4: a docked reserve has attach = Docked and parent = its carrier; launch clears
    // both (Mounted and Tethered stay reserved). Included in the hash:
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
    pub reserves: [Vec<ShipIdx>; 2],       // v4: docked slots per team, launch order (hashed)
    pub mission: MissionState,             // v4: end_reason, carrier[2], bay_ready[2][MAX_BAYS],
                                           //     transports bitmask, jump[MAX_SHIPS] (hashed)
    pub command: CommandState,             // v4: squads[2][MAX_SQUADS], waypoints[MAX_SHIPS] (hashed)
    pub inbox: [Vec<Command>; 2],          // v4: External commands for the next slow tick (input, not hashed)
    pub command_results: [Vec<CommandOutcome>; 2], // v4: last slow tick's outcomes (output, not hashed)
}
```

`pending` and `applied` are per-step inputs/outputs, not simulation state, and are
not hashed; `queue` and `thrust_level` are state and are hashed (§12).

### 3.4 Room for later hulls

- `HullDef.static: bool` — skip integration; infinite mass in collisions. Parsed and
  honoured in M1 (tested with a synthetic hull), no shipped static hull.
- `HullDef.bays: Vec<BayDef>` — v4: used for launches (§5.9).
- `Ship.parent / attach` — hit tests and collisions must skip pairs where one is the
  other's parent (`same_entity(a,b)` helper in `damage.rs`, used by every hit path).
  Ships with `attach != None` are `present == false` in M1 semantics.

## 4. Data files

### 4.1 Hull YAML (`assets/hulls/<name>/hull.yaml`)

```yaml
name: fighter            # must equal directory name
role: fighter            # free string; the scripted controller dispatches on it (§11)
hp: 80                   # v2 duel balance (was 60; WP15 sweep)
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
impact:                  # optional (v3); absent or [] → uniform 1×. Collision damage by
  - {from_deg: -180, to_deg: -45, mult: 1.0}    # body-frame bearing of the contact point
  - {from_deg: -45,  to_deg: 45,  mult: 1.5}    # nose crumples
  - {from_deg: 45,   to_deg: 180, mult: 1.0}
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
changes in bold; v4 capital ships at the end):

| hull | role | hp | mass | inertia | speed_cap | shield (hp/regen/delay/radius) | armour (v2) | impact (v3) | collision circles (pos, r) |
|---|---|---|---|---|---|---|---|---|---|
| fighter | fighter | **80** | 10 | 55 | 60 | none | **nose 0.5 / flank 1.0 / engine 1.5** (arcs as above) | nose (±45°) 1.5 / else 1.0 | (2.0,0) 2.4; (-2.2,0) 2.6 |
| strafer | skirmisher | 70 | 11 | 75 | 50 | 40 / 8 / 3 / 7.5 | uniform (absent) | nose (±45°) 1.5 / else 1.0 | (0,0) 3.2; (0,3.6) 2.4; (0,-3.6) 2.4 |
| gunship | anchor | 320 | 60 | 2200 | 24 | 140 / 12 / 4 / 11 | uniform (absent) | 0.75 all round | (4.5,0) 3.6; (0,0) 4.6; (-4.5,0) 3.8 |
| carrier (v4) | carrier | **1000** (WP-S2; was 1500) | 600 | 90000 | **8** (was 10) | 260 / 15 / 5 / 24 | uniform | 0.5 all round | (13,0) 6.5; (0,0) 8.5; (-13,0) 7.5 |
| freighter (v4) | transport | **400** (WP-S2; was 500) | 300 | **40000** | **10.5** (was 14) | 80 / 6 / 5 / 15 | uniform | 0.75 all round | (8,0) 4; (0,0) 4.5; (-8,0) 4.2 |

v4 mounts (the contract with the art agent's models; body frame): **carrier** mains
`thruster.main.l/c/r` at (−19.5, 4.5) / (−20, 0) / (−19.5, −4.5), dir +x, **300 N** (WP-S2; was 7000); RCS
`thruster.rcs.fl/fr/rl/rr` at (15, ±8) / (−14, ±8.5), dir ∓y, **450 N** (was 3500; WP-S2: about 1.5 m/s² from the mains and 0.15 rad/s² of yaw at even power, so it reads as a capital ship); flak turrets
`turret.flak.fore` (12, 0) rest 0 arc 270, `turret.flak.port` (−6, 7) rest 90 arc 200,
`turret.flak.starboard` (−6, −7) rest −90 arc 200, all slew 90; bays `bay.port` (4, 9)
dir (0.5, 0.87) and `bay.starboard` (4, −9) dir (0.5, −0.87); cost 120. **freighter**
(user, 2026-10-30: a sitting duck, never evades): mains `thruster.main.l/r` at
(−13, ±2), dir +x, 3000 N; RCS `thruster.rcs.fl/fr/rl/rr` at (9, ±4.2) / (−9, ±4.4),
**300 N** (heading hold only; its script turns with the RCS alone, ≈ 0.14 rad/s² of
yaw); no turrets, no bays; cost 40. Role `transport` is the mission category, so
another transport-role hull (a medical frigate) needs no sim change.

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

**Impact (v3).** `impact` has exactly the format, storage (`HullDef.impact:
Vec<ArmourArc>`), lookup (`impact_mult(hull, b)`) and validation (rule 12) of
`armour`, but scales **collision** damage (§5.5) instead of weapon damage, at the
bearing of the contact point; armour never applies to collisions and impact never
to hits. Like armour it applies to hull damage only. The strafer's side pods sit at
±90°, so a pod strike counts as flank (1×) and only a strike on the nose cone
within ±45° takes 1.5×; the gunship is uniformly sturdier (a single arc).

Derived on load (stored in `HullDef`): `bound_radius = max(|c.pos| + c.r)`,
`shield_radius = shield.radius` or `bound_radius`, `has_shield`, `n_power_systems`
(3 if shield else 2), `arrival_speed = 1.4 * speed_cap`, `reaction_ticks:
Option<u8>` (None = use the match config).

### 4.2 Weapon YAML (`assets/weapons.yaml`)

```yaml
# gauss: v2 duel balance (SIM_SPEC §0 item 9, chosen by the WP15 sweep in
# lab/runs/2026-10-28-sim-v2/results.md); v1 was speed 240, range 300, damage 6,
# interval 0.16, spread 0.6.
gauss:   {kind: bullet,  speed: 200, range: 220, damage: 5,  interval: 0.20, spread_deg: 1.0}
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
12. (v3) `impact`, if given and non-empty: the same rules as 11.
13. (v4) at most `MAX_BAYS = 4` bays (bay ids share rule 4's uniqueness and `dir` checks).

`Match::new` additionally rejects `cfg.reaction_ticks > MAX_REACTION_TICKS`
(`SetupError::ReactionTooLong`).

Python: `DataError` → `ValueError` with the message. WASM: `JsError`.

## 5. Step order (`Match::step`)

Each stage loops over ships in slot order and over projectiles in pool order.
`active(s) = s.alive && s.present`. Let `P_s, P_e, P_w` be the power multipliers (§5.2).

1. **Clear** `events`, `hits`, `rewards`; `tick += 1`. If `phase == Over` return (the
   VecEnv never calls step on a finished match; WASM may, for an outro).
1b. **Commanders** (v4, §5.9): if `tick % COMMAND_TICKS == 0`, sanitise squads and
   waypoints, gather both teams' commands (scripted or the inbox), apply team 0's then
   team 1's (launches happen here, so a launched ship is active for the rest of the
   step and earns from it), and emit `Order` for every squad whose order changed.
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
10. **Ship–ship collisions** (§5.5), pairs `(i<j)`, both active; v3: closing
    contacts above the free speed apply collision damage and emit `Collision`.
11. **Arena** (§5.7): push and drain, active non-static.
12. **Deaths**: any ship with `hp <= 0 && alive` → `alive=false, present=false, hp=0`,
    `thrust_level` all 0, `queue` all `IDLE`, emit `Death`. (Damage never flips
    `alive` directly; this stage does, so simultaneous kills are symmetric.)
12b. **Mission rules** (v4, §5.10): a carrier battle kills the docked reserves of a
    carrier that died this step (no `Death` events) and empties its hangar; a convoy
    escort starts and completes transport jump charges (`JumpCharge`, `JumpOut`).
13. **Termination** (§5.8, per mission in v4) and terminal rewards; emits `MatchEnd`.
13b. **Orders** (v5, §5.9, §8): refresh every ship's order instance and compute
    `order_rewards` (cleared in stage 1 with `rewards`).
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
No torque transfer.

**Collision damage (v3).** The contact point of the deepest pair is the midpoint of
the two circles' surfaces along the normal, `p = ((ca + n*ra) + (cb - n*rb)) * 0.5`,
from the poses the contact was found in; each ship's bearing
`b_k = wrap(atan2(p - pos_k) - heading_k)` is taken from those same (pre-correction)
poses, with the §5.4 convention (`p == pos` → 0). `vn` above is the pre-impulse
relative normal speed. With `COLLISION_FREE_SPEED = 10.0` m/s and
`COLLISION_DAMAGE_PER_J = 0.002` hp/J (consts in `collision.rs`):

```
excess = max(0, -vn - COLLISION_FREE_SPEED)        # closing speed above the free speed
mu     = 1 / (wi + wj)                             # reduced mass (static partner: the other's mass)
base   = COLLISION_DAMAGE_PER_J * (0.5 * mu * excess * excess)
if base > 0:
    for k in (i, j), in that order, skipping static hulls:
        apply_collision_damage(k, base, b_k)
        dv = CRASH_HULL_PER_DV * max(0, jimp * w_k - CRASH_DV_FREE)   # v7
        apply_crash_hull_damage(k, dv, b_k)
    emit Collision { a: i, b: j, pos: p, normal: n, closing: -vn }

apply_collision_damage(k, amount, b):
  k.last_hit_tick = tick                            # delays shield regen like a hit
  if k.shield > 0:                                  # the §5.4 shield rule, no overflow
      k.shield = max(0, k.shield - amount / (0.7 + 0.3 * P_s(k)))
      collision_shield_damage[k] += amount          # raw, like a shield HitRecord
  else:
      dealt = amount * impact_mult(hull_k, b)       # impact arcs, never armour (§4.1)
      k.hp -= dealt
      collision_damage[k] += dealt

apply_crash_hull_damage(k, amount, b):              # v7; nothing if amount == 0
  k.last_hit_tick = tick
  dealt = amount * impact_mult(hull_k, b)           # past any shield
  k.hp -= dealt
  collision_damage[k] += dealt
```

**Velocity-change damage (v7).** `jimp * w_k` is ship `k`'s own velocity change from
the impulse, at most `(1 + e) * |vn|`, so with `CRASH_DV_FREE = (1 + e) *
COLLISION_FREE_SPEED = 12` m/s the term fires only when `base > 0`. With
`CRASH_HULL_PER_DV = 1.25` hp per m/s: a fighter at 60 m/s into a carrier at rest
changes velocity by 70.8 m/s, 73.5 hp before arcs on top of the 24.6 base, past its 80
at any bearing, while the carrier's 1.2 m/s adds nothing; two fighters closing at
60 m/s nose to nose each take 1.5 * (12.5 + 30) = 63.75.

So a fighter–fighter crash at 95 m/s closing (mu = 5 kg, 18,062 J excess) deals
36.1 hp base, 54.2 nose first (v3; v7 adds 1.25 * 45 * 1.5 = 84.4 more, killing
both). Collision damage records no
`HitRecord` (hit-rate stats and shooter credit see only weapons) and, like all
damage, never flips `alive`: a crash that kills both ships is resolved in stage 12
and is a draw. `collision_damage` and `collision_shield_damage` (`[f32; MAX_SHIPS]`
on `Match`) are per-step outputs, cleared in stage 1 and not hashed. Static hulls
take no collision damage and keep their `last_hit_tick`.

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

`alive_t = count(in_match && team == t)` where `in_match = alive && !jumped out`
(pending arrivals and docked reserves count; v4 adds the jump-out exception).
Deathmatch (and v3):
- `alive_0 == 0 || alive_1 == 0` → Over; winner = surviving team, or -1 if both 0;
  reason `Eliminated`.
- `tick >= time_limit_ticks` → Over; `value_t = Σ_in_match (hp + 0.5*shield)`;
  winner = higher value, or -1 if `|v0 - v1| < 1e-3`; reason `TimeLimit`.

v4 missions (§5.10) have their own rules. Every end sets `Match.mission.end_reason`
(`EndReason`: 0 `NotOver`, 1 `Eliminated`, 2 `TimeLimit`, 3 `CarrierDestroyed`,
4 `ConvoyThrough`, 5 `ConvoyDestroyed`) and emits `MatchEnd { winner, reason }`.

### 5.9 Hangars, launches and the commander layer (v4)

**Hangars.** In a carrier battle the ships that do not jump in start docked:
`attach = Docked`, `parent` = the carrier, `present = false`, at the carrier's
position; `Match.reserves[team]` lists them in launch order (fleet order). Docked
ships are alive (they count for elimination) but never arrive, are never hit and
have zero obs; they die with their carrier (stage 12b).

**Launch** (`Match::launch(cat, team, hull, bay)`, also the `Launch` command): needs
the team's carrier (`NoCarrier`), active (`CarrierLost`), a reserve (`HangarEmpty`),
of the requested hull if any (`NoReserveOfHull`, first such in the hangar), and a
bay: the requested one (`NoSuchBay`, `BayBusy` if `tick < bay_ready`) or else the
ready bay with the smallest `bay_ready` (ties: lower index). The ship becomes present
with `attach = None, parent = NONE`, at `mouth + dir · (bound_radius + 1)` (mouth =
the bay mount in world, dir = bay dir rotated by the carrier's heading, so it clears
the carrier's circles), heading `atan2(dir)`, `vel = carrier.vel + dir · 30`,
`omega = 0`, `control_lock_until = tick + LAUNCH_LOCK_TICKS (15)`, `arrive_tick =
tick`; the bay's `bay_ready = tick + BAY_COOLDOWN_TICKS (45)`; emit `Launch`.
Refusals change nothing.

**Slow tick** (stage 1b, every `COMMAND_TICKS = 60` ticks, first at tick 60;
`Match::command_due()` says whether the next step is one):
1. Clear `command_results`; per team drop squad members that are no longer in the
   match and replace orders that are no longer valid by `Order::None`; unset the
   waypoints of ships no longer in the match.
2. Gather each team's commands: `Scripted` → `scripted::commander::commands(m, cat,
   team)` (both teams read the same state, before either applies); `External` → the
   team's inbox (`Match::submit_command`, then cleared). A `Scripted` team's inbox is
   discarded.
3. Apply team 0's, then team 1's, in order, recording a `CommandOutcome` for each
   (`Applied`, `Sanitized`, `Launched { ship, bay }`, `Refused(Refusal)`).
4. Emit one `Order` per squad whose order differs from the start of the tick.

No commands means the previous orders stand.

**Commands.** `Launch { hull: Option<HullId>, bay: Option<u8> }`; `Waypoint { ship,
waypoint: Unset | At(pos) }` for the team's own carriers and transports in the match
(else `NotOwnShip` / `ShipLost` / `NotCapital`; non-finite → `BadPoint`; clamped into
`0.95 R`); `Squad { squad, members: u32 bitmask, order }` (`NoSuchSquad` past
`MAX_SQUADS = 4`): members are restricted to own strike craft in the match (bits for
other slots, capital ships, dead or departed ships are dropped) and removed from the
team's other squads; the order is sanitised: `Attack { target }` needs an active enemy,
`Defend { ward }` an own ship in the match, `GoTo { point, radius, deadline }` finite
(point clamped into `0.95 R`, radius into `[10, R]`), else `Order::None` (v6; v5's
`Guard` and `Hold`). A go-to's `deadline` (v8; a match tick, `NO_DEADLINE = 0` for none)
is kept as given, whatever its value. Any drop makes the
outcome `Sanitized`.

**State** (hashed): `CommandState { squads: [[Squad { members, order }; 4]; 2],
waypoints: [Waypoint; MAX_SHIPS] }`. Setup sets the carriers' and transports' first
waypoints. Pilots do not see orders in stage A; v5 adds the obs block (below, §7.2).

**A ship's own order (v5, v6; `order.rs`).** The *standing* order of slot `s` is its
waypoint as `GoTo { point, radius: CAPITAL_WAYPOINT_RADIUS = 25 }` (no deadline) if it
has one (capital ships), else its squad's order, else none. The *valid* order is the standing
one with an attack on a target that is not active, or a defend of a ward that is not
active (dead, docked, not yet arrived, jumped out), replaced by none at once, not at
the next slow tick. The *effective* order is the valid one, except that a go-to that
is **over** for the ship, because it arrived during its current instance or (v8)
missed the instance's deadline, is none: the ship
flies its role again while the squad's standing go-to lasts until the commander
changes it. The obs, the go-to shaping and the scripts use the effective order; hit
credit and the defend penalties the standing one. Order geometry: attack → the
target's position, defend → the ward's, go-to → its point; radius 0 for attack and
defend, the go-to radius for go-to.

**Order instances (v5, v6, v8).** `Match.order_tracks[s]` (`OrderTrack`, hashed): the
instance's key `(kind, target, point, deadline)`, its `start_tick`, `arrived`,
`last_phi` and (v8) `missed`.
Stage 13b compares each ship's *standing* order with its key (v6; v5 used the
effective order, so a dead target started an empty instance): a different kind or
target, a go-to point more than `GOTO_SAME_POINT = 40` m from the instance's first
point, or (v8) a different go-to deadline starts a new instance at this tick with Φ
reset to its current value (a radius
change or a smaller move is the same instance, completed or not). Setup starts every
ship's instance at tick 0 (only capital waypoints exist then). v8: an instance that
starts with the ship active after stage 2 (at setup: active) and already inside the
radius starts `arrived`, with no bonus (§8); a ship that is not on the field then is
not marked, and arrives in the usual way once it is.

**Go-to deadlines (v8).** Stage 13b, per ship with a standing go-to, after the instance
check and the shaping, in this order. *Expiry:* if the instance has a deadline, the
step's tick is past it and the ship has neither arrived nor missed, then `missed =
true` (whether or not the ship is on the field; only a ship active after stage 2 is
charged, §8). *Arrival:* a ship active after stage 2, inside the radius, neither
arrived nor missed, has `arrived = true`. So arrival at the end of the step whose tick
equals the deadline is in time, the step after is too late, and an order that lands
with its deadline already past is missed on the step it lands (and charged; it is
still complete with no charge if the ship is inside the radius then). A missed go-to
is over for that ship exactly as an arrived one is: effective order none. A go-to
without a deadline never expires.

**Threat sets and hits (v6).** `Match.hit_by[w][e]` is the tick `e` last damaged `w`
(hull or shield, enemies only; 0 never; hashed over the match's slots), updated at
stage 13b from the step's HitRecords. Ward `w`'s *threat set* among candidate slots:
the enemies `e` of `w` with `|e − w| ≤ reach(e) + THREAT_MARGIN (40 m) + bound(w)`,
`reach` the longest weapon range of `e`'s hull (`Match.ship_reach`, from the
catalogue at setup), or with `tick − hit_by[w][e] < RECENT_HIT_TICKS (150)`. The reward
and `Match.ward_threat` (output) use the ships active after stage 2 as candidates, for
every such ward; the scripts and the transit flag the ships active now.
`Match.hull_lost[s]` (output) is the hull fraction `s` lost in the step, measured
from its hp at the end of the previous step's stage 13b (a death counts the rest of
its hull). `Match::order_transit(s)`: the effective order is a go-to (not arrived, nor
missed), or a defend whose ward's threat set is empty.

**Random commander (v5, `CommanderMode::Random`, `"random"`,
`scripted/random_commander.rs`).** Stage B trains pilots on any order. Per team, on
every slow tick:
- *Logistics*: the scripted commander's commands without its `Squad` ones (launches
  and waypoints exactly as the script would).
- *Squads*: the first time it commands, it draws for each of the team's strike-craft
  slots in slot order (docked reserves too): no squad with probability
  `UNASSIGNED_FRAC = 0.15`, else one of `RANDOM_SQUADS = 3` uniformly. Membership is
  fixed for the match. A squad's members are its own strike craft in the match and
  not docked, plus the reserves this tick's launches will take (the first in the
  hangar), as the scripted commander does.
- *Orders*: a squad with members draws when `tick ≥ next_draw` or when its order was
  cleared (target or ward gone): kind uniform over none / attack / defend / go-to;
  attack → a uniformly drawn active enemy (capital ships included); defend → with
  an active own capital ship and probability `DEFEND_CAPITAL_P = 0.5` (one `uniform`,
  drawn only when the team has one) a uniformly drawn capital ship, else a uniformly
  drawn own active ship not in the squad (capital ships included); go-to → a point
  near the squad's fight (below) and a radius uniform in `[70, 150)` m. A
  kind with no valid target becomes none. Then `next_draw = tick + 60 · (3 + u%6)`
  (3–8 slow ticks). Squads with no members get `Order::None`. A command is sent only
  when membership or order changes, so every `Order` event is a real change.
- *Rng*: `RandomCommander.rng[team] = Pcg32::with_stream(seed,
  RANDOM_COMMAND_STREAMS[team])`, never the match stream; draw order per team:
  assignment (per slot: one `uniform`, then a `next_u32` for the squad unless it
  drew none), then per
  squad in index order: kind, target or point (`uniform` angle, `uniform` radius
  fraction, `range` radius), timer. Team 1's draws do not depend on team 0's mode.
- *Go-to points near the action* (`goto_point`, v6 names; since the order pilot's run B2b, no
  `SIM_VERSION` bump: the obs layout and every scripted-commander match are
  unchanged, only the random commander's draws move). Run 1 drew hold points
  uniformly over the disc of `0.7 R`, usually away from the fight, so a pilot paid
  for following one lost its fight, and ignored holds (`lab/runs/2026-10-31-order-pilot/
  results.md`). Now: `c` = the centroid of the squad's active members (all still
  launching: of the team's active ships), `e` = the centroid of the
  `GOTO_NEAREST_ENEMIES = 2` active enemies nearest `c` (ties to the lower slot); the
  point is `c + f · (e − c) + j`, `f` uniform in `[GOTO_LERP_MIN, GOTO_LERP_MAX) =
  [0.25, 0.75)`, `j` uniform over a disc of `GOTO_JITTER = 60` m, scaled back onto
  the disc of `GOTO_POINT_FRAC · R = 0.7 R` if outside it. With probability
  `GOTO_FAR_P = 0.2`, or with no active own ship or enemy, the point is the old
  uniform draw over the `0.7 R` disc instead (a *far* point): the scripted
  commander's own holds (a convoy's staging and screening points) are not always at
  the fight, and a hold must keep meaning "go to the point", not "go and fight";
  0.2 keeps far holds at about 5 % of all random orders, so following mostly
  coincides with fighting while the habit forms. Draws: one `uniform` (far if `<
  0.2`); far: `uniform` angle, `uniform` radius fraction; near: `range` f, then the
  jitter's `uniform` angle and `uniform` radius fraction; then the hold radius. On
  the training mix with scripted pilots the median squad-to-point distance at the
  draw is 117 m (the old rule on the same states: 261 m). The three random-commander
  golden traces were regenerated; every other trace is unchanged.
  The state (`rng`, `assigned`, `squad`, `next_draw`, `drawn`) is hashed.
Scripted strike pilots follow its orders in every mission, deathmatch included (§11).

**Commander observation** (`Match::commander_obs(cat, team) -> CommanderObs`): tick,
ticks left, mission kind; own ships by hull id `in_space` (active), `arriving`,
`reserves` (docked); `enemy_visible` (active enemies by hull); own and enemy carrier
`CapitalStatus` (slot, hull, alive, hp/max, shield/max, pos, vel, heading; the enemy
one only while active); own bays ready; `ConvoyStatus`; own active transports; own
squads. A learned commander will flatten it.

**Scripted commander** (`scripted/commander.rs`, WP-S2; it replaced WP-S1's stub).
Deterministic, no rng, and stateless: what it remembers between slow ticks is the
command state itself, which is also its hysteresis. An order changes only for a
clearly better one (an attack target is kept unless another is nearer than `0.6 ×`
its distance `− 30 m`; a defended ward unless another transport has 2 more threats; a
go-to point while the new one is within 120 m), squad membership moves only when a
squad is the wrong size (the members furthest from the ward leave first), and a squad
command or waypoint that changes nothing (a waypoint within 20 m of the current one)
is not sent. So every `Order` event is a real change, for the web's command log.
"Strike craft" below are own non-capital ships in the match and not docked; "wing" is
those.

- *Carrier battle.* **Launches** (fleet order, the sim picks the bay): keep
  `WING_BASE = 3` strike craft in space or on the way, one more every 30 s; one
  launch at most every `LAUNCH_INTERVAL_TICKS = 360` (12 s); **scramble** one per bay
  per slow tick while ≥ `THREAT_COUNT = 2` enemy strike craft are within
  `THREAT_RADIUS = 200` m of the carrier; empty the hangar (one per bay per slow tick)
  in the last `LATE_TICKS = 1800` (60 s). A ship launched this slow tick is put in the
  defence at once. **Squads**: squad 0 *defends* the carrier, `⌈n/3⌉` of the wing (`⌈n/2⌉`
  while threatened, until no enemy strike craft is within 280 m); squad 1 *strikes*
  the enemy carrier, unless the enemy strike craft within 220 m of it outnumber the
  strike squad (`2·escort > strikers` to turn away from the carrier, `escort >
  strikers + 1` once on it), in which case it attacks the enemy strike craft nearest
  its centroid. **Carrier waypoint**, first match wins: the wing is spent (no strike
  craft, empty hangar) → the enemy carrier's position (a flak duel, so attrition still
  ends in a kill); the last 60 s → `STANDOFF = 170` m short of the enemy carrier
  (inside flak range); threatened → `RETREAT_STEP = 100` m away from the threats'
  centroid (inside `0.78 R`); winning (own wing ≥ 2 × the enemy strike craft in space
  + 2, or own carrier hull fraction ≥ the enemy's + 0.2) → the standoff point; else
  patrol `(side · 0.6 R, ±60 m)`, switching every 20 s.
- *Convoy escort, defenders.* Transports keep the jump point setup gave them (the
  transport is a sitting duck: never re-routed). Squad 0 *defends* the most threatened
  transport that is not charging (most enemies within 220 m; the lead transport, the
  one furthest along the route, while none is threatened), `⌈n/2⌉` of the escort.
  Squad 1 *intercepts* the enemy nearest any transport; before the attackers arrive it
  *goes to* a point 120 m off the lead transport toward their side (radius 80 m; v6:
  arrived, its ships fly their role).
- *Convoy escort, attackers.* Two **waves**: wave 1 (squad 0, the first `⌈n/2⌉` in slot
  order) attacks the transport scoring highest on route progress + hull fraction lost
  (+ 0.2 while it charges its jump), switching only for a score 0.25 higher; wave 2
  (squad 1) *goes to* a staging point 150 m ahead of the lead transport along the
  route and 110 m toward the attackers' side (radius 60 m), and goes in on the same
  target once wave 1 is down to half wave 2's size, or at 30 s; once in, it stays in.
  v6: a go-to completes on arrival, so an order-following wave 2 fights from the
  staging point on instead of waiting there. The timing was left as it was: the live
  configuration (pilot v1, which does not read orders) is bit-identical to v5, and
  script vs script moved within its noise (WP-B3-sim report).
- *Deathmatch.* The fleet split in slot order into two squads: squad 0 attacks the
  enemy nearest its centroid, squad 1 the most damaged enemy (hull + shield fraction
  lost) within 300 m of its centroid (switching for 0.2 more damage). These orders are
  only shown: scripted pilots do not follow a scripted deathmatch commander (§11).
  v5: learned pilots see them in their obs (advisory orders), as in every mission.

### 5.10 Missions (v4)

`MatchConfig.mission`: `Deathmatch` | `CarrierBattle { jump_in: [u8; 2] }` |
`ConvoyEscort { start, jump_point, jump_radius, charge_ticks, start_speed_frac }`.
`Match::new` validates the roster against the mission (`SetupError::Mission`).
Arena: `mission::arena_radius_for_mission(kind, n)` = 450 m for all three (DESIGN §6).
Default time limits (`MissionKind::default_time_limit_ticks`; callers pass them in
`time_limit_ticks`): 90 s, 150 s, 120 s.

**Deathmatch**: v3 (§5.6, §5.8).

**Start layout** (`MatchConfig.start_layout`, default `None`; a deathmatch only, for order
drills). One `ShipStart { pos, vel, heading }` per slot, team 0 then team 1. Every ship is
present at tick 0 with no jump-in and no control lock, and setup draws nothing from the
rng. `Match::new` refuses (`SetupError::StartLayout`) a wrong length, a non-finite value, a
ship outside the arena radius or over its hull's speed cap, and two ships whose bound
circles overlap. With `None` nothing changes: no `sim_version` bump.

**Drill rules** (`MatchConfig.drill`, default `false`; needs a start layout;
`docs/PILOT_TRAINING.md` §2). The mission stays `Deathmatch`, so the obs's mission one-hot
and the order rules are a deathmatch's (`external` orders are followed; only the scripted
commander's are advisory, §11). Differences: every ship starts under a control lock to tick
`COMMAND_TICKS + 1 + reaction_ticks`, so it coasts and the first action any ship chooses
comes from an obs that shows the orders of the first slow tick. Stage 13 replaces the
deathmatch's: team 0 has no strike craft in the match → over (`Eliminated`); the time limit
→ over (`TimeLimit`); team 1 is gone and no strike craft of team 0 has an effective go-to →
over (`Eliminated`). Killing the last enemy does not cut a go-to short; a go-to whose
deadline was missed (v8) is no longer effective, so it does not keep the drill going. The winner is always
a draw, so the terminal reward (§8) is 0, with the rest of the pay as usual. A freighter
with no waypoint coasts and holds its heading, and does not keep a drill going.

**Carrier battle.** Each team has exactly one `carrier`-role ship and no transports.
Setup draws, per team in order: `y = range(−40, 40)`; the carrier is present at
`(side · 0.72 R, y)` heading 0 / π, `vel` 0.4 × its speed cap forward, waypoint 60 m
ahead. Of the team's other ships (fleet order) the first `min(jump_in[team], wing)`
jump in (§5.6 schedule over those ships only; default `jump_in` 2), the rest dock.
Then the jump-in schedule is drawn for both teams (teams with no jump-in ships draw
nothing). Stage 12b: when a carrier dies its docked reserves die (`alive = false, hp
= 0`, no event) and the hangar empties. Termination: a dead carrier loses
(`CarrierDestroyed`; both → draw). Time limit: the higher carrier hull fraction
`hp/max_hp` if they differ by ≥ 1e-3, else the team value, else draw (`TimeLimit`).

**Convoy escort.** Team 0 fields 1–`MAX_CONVOY` (8) `transport`-role ships (the
convoy; slots in `MissionState.transports`) and any escorts; team 1 none. Standard
layout (`ConvoyEscort::standard(R)`): `start = (0, −0.55 R)`, `jump_point = (0,
+0.75 R)`, `jump_radius = 40`, `charge_ticks = 60`, `start_speed_frac = 0.8`. With
`fwd` the unit route direction and `port = perp(fwd)`: transport `i` at `start − fwd ·
32 i + port · (±12)` (even `i` to port), heading and velocity straight at the jump
point; escort `j` at `start + fwd · (20 − 40 ⌊j/2⌋) + port · (±45)` (even `j` to port)
with heading `fwd`; all at `start_speed_frac` × the slowest transport's cap, present at
tick 0 with no control lock. No rng draws for team 0; then team 1's jump-in schedule.
Stage 12b, for each active transport: `Idle` inside the jump radius →
`Charging { until: tick + charge_ticks }` (`JumpCharge`); `Charging` at `tick >= until`
→ `Departed`: `present = false`, levels 0, queue IDLE, waypoint unset (`JumpOut`). A
departed ship stays `alive` but is out of the match (not counted for elimination or
team value, never arrives again, zero obs, earns nothing). Termination with `n`
transports, `to_destroy = ceil(n / 2)`, `to_escape = n − to_destroy + 1`, in order:
destroyed ≥ `to_destroy` → team 1 (`ConvoyDestroyed`); escaped ≥ `to_escape` → team 0
(`ConvoyThrough`); no team 1 ship in the match → team 0 (`Eliminated`); time limit →
team 1 (`TimeLimit`: the convoy failed to get through). `Match::convoy_status()`
reports total, en route, charging, escaped, destroyed, both thresholds and the mean
route progress of the transports not destroyed (escaped = 1).

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

`OBS_DIM = 587` `f32` (v8; 583 in v6 and v7, 403 in v5, 385 in v2–v4, 204 in v1), body frame of the observing ship (relative
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
137: 84  all other active ships, 7 slots (N_NEAR_SHIPS; v4: no longer MAX_SHIPS − 1) sorted by distance (allies and
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
385: 18  v5 order block (below); 385 = OBS_DIM_V4, the obs of a v3/v4 pilot
403: 70  v6 ship_extras, 7 × 10, one per `ships` slot (below); 403 = OBS_DIM_V5
473: 110 v6 order_ships, 5 × 22 (below)
583: 4   v8 order_time (below); 583 = OBS_DIM_V7, the obs of a v6 or v7 pilot
587 = OBS_DIM
```

**Order block (v5, `write_order`).** The ship's effective order (§5.9), body frame,
clamped like the rest. A ship with no order (v6: or a completed go-to, or on a
hidden-order team; v8: or a go-to whose deadline it missed) gets 18 zeros (mission and age included), so an order-less row is
a v4 obs padded with zeros.

| offset | feature |
|---|---|
| 0 | has_order (1) |
| 1–3 | kind one-hot: attack, defend, go-to (v5: attack, guard, hold) |
| 4–5 | target point − own position, body, / R (attack: the target; defend: the ward; go-to: the point) |
| 6–7 | target point velocity − own velocity, body, / VS (go-to: −own velocity) |
| 8 | (distance − radius) / R: negative inside the radius |
| 9 | radius / R (v6: attack and defend 0; go-to its radius; a capital waypoint 25 m) |
| 10 | target hp / max hp (0 for go-to) |
| 11 | target bound radius / L (0 for go-to) |
| 12–13 | sin, cos of (target heading − own heading) (0 for go-to) |
| 14 | ticks since this ship's order instance started / 300, at most 1 |
| 15–17 | mission one-hot: deathmatch, carrier battle, convoy escort |

Pilots see their order in every mission, the scripted deathmatch commander's advisory
orders included. A pilot of sim version `v` reads `obs[..., :PILOT_OBS_DIMS[v]]`:
385 for v3/v4 (no order block), 403 for v5, 583 for v6 and v7, 587 for v8
(`sim::pilot_obs_dim`).

**Ship extras (v6, `write_ship_extras`).** One 10-float record per `ships` slot, same
order (zero for an empty slot), so a pilot can judge threats:

| offset | feature |
|---|---|
| 0–5 | hull class one-hot: fighter, strafer, gunship, carrier, freighter, spare (from the catalogue role: fighter, skirmisher, anchor, carrier, transport, other; `order::hull_class`) |
| 6 | the ship's longest weapon range / R |
| 7 | the ship's distance to my order point (target, ward or go-to point) / R; 0 without an order |
| 8 | 1 if it is my order's target or ward |
| 9 | 1 if my order is a defend and it damaged my ward in the last 150 ticks |

**Order ships (v6).** The `N_ORDER_SHIPS = 5` active ships nearest my order point,
allies and enemies, excluding me and the order's own ship (already in the order
block), nearest first (ties to the lower slot), each the 12-float `ships` record
(relative to me) followed by its 10 extras. All zero without an order. A second block
rather than re-selecting the 7 `ships` slots by the order point: the v5 prefix stays
exact, and a defender still sees what is near itself.

**Order time (v8, `write_order_time`).** Four floats, all zero unless the order the
ship sees is a go-to (so zero with no order, an attack or a defend, on a hidden-order
team, and once the go-to is over: arrived or missed). `e = max(0, d − radius)` is the
distance to the circle's edge in metres, `left = max(0, deadline − tick)` the ticks
left: the number of steps in which an arrival is still in time.

| offset | feature |
|---|---|
| 0 | has_deadline: 1 if the go-to has a deadline |
| 1 | time left: `left / 900` (30 s), clamped to [0, 2]; 0 without a deadline |
| 2 | urgency: `e / (left / 30 × speed_cap)`, clamped to [0, 2], with the hull's catalogue `speed_cap` (fighter 60, strafer 50, gunship 24 m/s). 1 means a straight line at that speed just makes it. 0 inside the circle and without a deadline; 2 with `left = 0` and `e > 0` |
| 3 | closeness: `1 − min(1, e / 100)`, for any go-to, deadline or not: 0 at 100 m or more outside the circle, 1 at its edge |

On the deadline tick itself `left` is 0: the next step is the one that marks the miss.
The speed cap is the hull's catalogue value, which is the real cap at an even power
split. The cap a ship flies under is `speed_cap × (0.6 + 0.4 P_e)` (§5.1, §5.2): 0.68
of it with the engines starved, up to 1.26 of it with full power to the engines. So
urgency 1 needs at least an even split, and a ship that had to start from rest or turn
first cannot make urgency 1 at an even split; above about 1.26 no power split makes
it.

**Hidden-order mode (v6).** `MatchConfig.hide_orders[team]`: that team's ships see
no order: the order block, `order_ships`, extras 7–9 and (v8) `order_time` are zero,
exactly as for a ship without one. Everything else (rewards, tracks, scripts, the commander) is
unchanged: the order-following eval's control arm on paired seeds.

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
projectiles 8, pending 4, turret_arc 6, turret_range 6; v5 appends `"order"`, 1 record
of 18; WASM `obsLayoutJson()`). Turret `angle` is the
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
| collision (v3) | `-0.01 * collision_damage[s]` (hull, after impact arcs) `- 0.005 * collision_shield_damage[s]` (raw) for the damaged ship; nobody is credited |
| fire cost | `-0.002` per shot actually fired (not per trigger pull on cooldown) |
| arena | `-0.002` per tick while `|pos| > R` |
| terminal | `+1` every ship on the winning team, `-1` losing team (dead ships too); draw 0 (always under drill rules, §5.10) |

Dead or not-yet-present ships get 0 except the terminal term. Precisely: a ship earns
the per-step terms iff it was active after stage 2 of that step, so the killing hit
still penalises its target, while hits from projectiles of an already-dead shooter
credit nobody in `rewards` (the HitRecord keeps the credit). Rewards are not
normalised in the sim. Weights are the named consts in `reward.rs`.

**Order reward (v5, v6, v8; `order_rewards[N, S] f32`, stage 13b).** A separate buffer, so
the trainer weights it (`w`) and `rewards` stays exactly v4's. The same ships earn it
as earn `rewards` (docked reserves earn nothing); per ship and step, summed in this
order:

| term | value |
|---|---|
| attack | `+0.01 ·` hull `+ 0.005 ·` shield damage the ship dealt to its ordered target, when it lands (`HitRecord`s of this step; no retroactive credit: flight time is short next to GAE's horizon) |
| defend, damage | the same weights on damage dealt to the ward's **threat set** (§5.9; candidates: the ships on the field this step, positions after the step) |
| defend, ward hull | `DEFEND_HULL_LOSS_WEIGHT = −0.5 ×` the ward's hull fraction lost this step (`Match.hull_lost`; fractions, so a freighter and a carrier weigh the same) |
| defend, ward death | `DEFEND_WARD_DEATH = −0.3` once, on the step the ward dies |
| go-to: shaping | `γΦ′ − Φ`, `Φ = −K · max(0, d − radius) / R`, `K = 1.0`, `γ = MatchConfig.order_shaping_gamma` (default 0.99), until arrival (v8: or a missed deadline; the step that marks the miss still pays it); on the step an instance starts, 0 (Φ is reset to Φ′: no reward for the jump). The same with and without a deadline |
| go-to without a deadline: arrival | `ORDER_ARRIVAL_BONUS = +0.2` once per instance, the first step inside the radius (`d ≤ radius`); the go-to is then complete for that ship |
| go-to with a deadline: arrival (v8) | `+MatchConfig.goto_timed_bonus` (default `ORDER_TIMED_ARRIVAL_BONUS = 1.0`) once per instance, instead of the 0.2, the first step inside the radius whose tick is ≤ the deadline |
| go-to with a deadline: miss (v8) | `−MatchConfig.goto_miss_penalty` (default `ORDER_MISS_PENALTY = 1.0`) once per instance, on the first step whose tick is > the deadline, if the ship has not arrived. Nothing after it: no shaping, no late bonus |
| go-to: starts inside (v8) | an instance that starts with the ship already inside the radius is complete at once and pays neither bonus (v7 paid the 0.2 on that step) |

**Deadlines (v8).** The pay is strict about the deadline and free before it: no term
charges for time, so a pilot with time to spare loses nothing by fighting on the way,
and the whole difference between making and missing the deadline is `goto_timed_bonus +
goto_miss_penalty` (2.0 by default, the size of a win against a loss). A ship that does
not earn on the step that marks the miss (dead, or absent) is marked missed and not
charged. A deadline already past when the order lands is a miss on that step, charged
like any other, so a commander that issues one costs its pilots the penalty; a new
instance (a point moved more than 40 m, or another deadline) is charged on its own.
Both values are `MatchConfig` fields, finite and ≥ 0 or a `SetupError`
(`InvalidGotoPay`), and like `order_shaping_gamma` they only change `order_rewards`, so
they are not in the state hash.

**Shaping discount.** `MatchConfig.order_shaping_gamma` must be the trainer's discount:
only then does the shaping leave the optimal policy unchanged. Set below the trainer's
discount it pays a pilot to stay away from the point: standing still pays `(γ − 1) Φ′ > 0`
per step, and with shaping at 0.99 under training at 0.995 that outweighs flying there
(`docs/PILOT_TRAINING.md` §3). A value outside (0, 1], or NaN, is a `SetupError`. It only
changes `order_rewards`, which no ship observes and no script reads, so it is not in the
state hash and needs no `SIM_VERSION` bump. The live page reads no rewards and keeps the
default.

`d` is the distance to the go-to point, `radius` its radius (§5.9). Hit credit and both
ward terms use the *standing* order: the hit that kills an attack target is paid, and
every defender of a ward pays the whole of its loss and death (shared, not split),
although the effective order is already none on that tick. Shaping and arrival use
the standing go-to (a go-to is never invalid). Defend has no location term at all, and
no order pays a presence term (v6; v5 paid `0.0009` per step inside for at most 300
steps, which rewarded parking). Consts in `reward.rs`: `ORDER_HULL_WEIGHT`,
`ORDER_SHIELD_WEIGHT`, `DEFEND_HULL_LOSS_WEIGHT`, `DEFEND_WARD_DEATH`,
`ORDER_SHAPING_K`, `ORDER_SHAPING_GAMMA`, `ORDER_ARRIVAL_BONUS`,
`ORDER_TIMED_ARRIVAL_BONUS`, `ORDER_MISS_PENALTY`; in `order.rs`:
`THREAT_MARGIN`, `RECENT_HIT_TICKS`, `GOTO_SAME_POINT`, `CAPITAL_WAYPOINT_RADIUS`; in
`command.rs`: `NO_DEADLINE`.
Capital ships' waypoints are paid as go-to too (they are what their obs shows); stage
B trains strike rows only.

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
`seed = split(base_seed, i, episode_count[i])` and the same roster (or the one queued
with `set_next_roster(i, ...)`, §10.1), and the returned
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
    Collision { a: u8, b: u8, pos: Vec2, normal: Vec2, closing: f32 }, // v3: damaging contacts only
    // v4:
    Launch    { ship: u8, carrier: u8, bay: u8, pos: Vec2, dir: Vec2 },   // pos = bay mouth (world)
    Order     { team: u8, squad: u8, kind: u8, target: u8, point: Vec2, radius: f32 },
    JumpCharge{ ship: u8, pos: Vec2, until: u32 },
    JumpOut   { ship: u8, pos: Vec2, heading: f32 },
    MatchEnd  { winner: i8, reason: EndReason },
}
```

v4 flat encodings (kinds 8–12): `Launch` = `[8, ship, carrier, mouth.x, mouth.y,
dir.x, dir.y, bay]`; `Order` = `[9, team, squad, point.x, point.y, target (−1 none),
radius, kind]` (kind 0 none, 1 attack, 2 defend, 3 go-to (v5: guard, hold); point = the go-to point, or the
target's position when the order was given; v8: a go-to's deadline is not in the event,
whose eight floats are all taken, though a changed deadline alone does emit one), emitted once per changed squad per slow
tick; `JumpCharge` = `[10, ship, 0, x, y, 0, 0, until]`; `JumpOut` = `[11, ship, 0, x,
y, 0, 0, heading]`; `MatchEnd` = `[12, winner (−1 draw), reason, 0, 0, 0, 0, 0]`,
emitted on the step the match ends (every mission, deathmatch too).

`EventBuf` is a `Vec<Event>` with capacity `MAX_EVENTS`, cleared each step. Flat
encoding for FFI: `[f32; 8]` per event = `[kind, a, b, x, y, nx_or_x2, ny_or_y2, extra]`
(kinds 0..7 in the order above; `a,b` = ship/turret or target/shooter, or the two
slots `a < b` of a `Collision`; `extra` = angle / damage / radius / heading /
depleted / closing speed; v3: `Collision` = `[7, a, b, x, y, nx, ny, closing]` with
the contact point and the unit normal from `a` to `b`; `Fire` puts its weapon id in slot 5,
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
                     reaction_ticks: int = 2,                                # v2; 0..MAX_REACTION_TICKS
                     max_ships: int | None = None)                           # S; default the fleet total
env.n_envs, env.n_ships -> int (S = max_ships or fleet total; MAX_SHIPS cap), env.dt -> float
env.set_next_roster(i, fleets, arena_radius)  # env i's next match (next done or reset) and later ones
env.reset()                       # rebuild every match with episode_count = 0
env.step(actions=None)            # reads env.actions (or copies `actions` in first), advances all matches, auto-resets
# zero-copy buffers, owned by the env, overwritten in place on every step():
env.obs      [N,S,385] f32     env.actions   [N,S,21] i8 (write here before step)
env.rewards  [N,S] f32         env.dones     [N] bool        env.winner [N] i8
env.act_mask [N,S] bool        env.thruster_mask [N,S,8] bool  env.turret_mask [N,S,6] bool
env.fixed_turret [N,S,6] bool  env.team [N,S] i8  env.hull_id [N,S] i16  env.alive [N,S] bool
env.tick [N] u32  env.episode_count [N] u32  env.hits [N,64,6] i32  env.hit_count [N] i32
env.collision_damage [N,S] f32  # v3: hull damage each ship took from collisions this step (after impact arcs)
env.arena_radius [N] f32        # radius of each env's current match
env.scripted_actions(team: int | None = None)   # writes the scripted controller's actions into env.actions for the given team (or all ships)
env.state_hash() -> np.ndarray[N] u64           # per match
env.render_state(i) -> dict                     # ships/projectiles of match i (debug); ships carry thrust_level, queue
env.events() -> np.ndarray[E, 9] f32            # record_events only; column 0 = match index
rlf_sim.OBS_LAYOUT, rlf_sim.OBS_SLOTS, rlf_sim.ACTION_LAYOUT, rlf_sim.SIM_VERSION,
rlf_sim.OBS_DIM, rlf_sim.ACTION_WIDTH, rlf_sim.MAX_SHIPS, rlf_sim.MAX_HITS, rlf_sim.HIT_FIELDS,
rlf_sim.HIT_DAMAGE_SCALE, rlf_sim.MAX_REACTION_TICKS
rlf_sim.arena_radius_for(n_ships) -> float      # the shared arena rule (sim::setup::arena_radius_for)
# v4:
VecEnv(..., mission=None | "carrier_battle" | {"kind": ..., ...},   # §10.3 spec; default deathmatch
       commanders=None | ["scripted" | "external", ...])            # default both scripted
env.set_next_roster(i, fleets, arena_radius, mission=None)
env.end_reason [N] i8          # EndReason code of a match that ended this step (0 running)
env.command_due() -> bool[N]   # the next step is a slow tick
env.submit_command(i, team, command | [commands])   # queued for the next slow tick (§10.3)
env.command_results(i, team) -> list[dict]          # {"command", "outcome", "ship"/"bay" | "reason"}
env.commander_obs(i, team) -> dict                  # CommanderObs with hull names
env.mission_state(i) -> dict                        # carriers, hangars, bays, squads, convoy, ships
env.render_state(i): + "mission", "end_reason"; ships + "role", "docked", "escaped"
rlf_sim.PILOT_COMPAT_VERSIONS, N_NEAR_SHIPS, COMMAND_TICKS, MAX_SQUADS, MISSIONS, END_REASONS,
rlf_sim.EVENT_KINDS (name -> code), arena_radius_for_mission(mission, n), mission_time_limit_s(mission),
rlf_sim.pilot_compatible(version)
rlf_sim.mission_rosters(mission) -> list[dict]       # WP-S2: default rosters, [{"name", "mission", "fleets": [[...], [...]]}]
# v5:
VecEnv(..., commanders=["random", "scripted"])      # "scripted" | "external" | "random" per team
env.order_rewards [N,S] f32    # the order reward (§8), zero-copy like rewards; 0 for padding
env.set_next_roster(i, fleets, arena_radius, mission=None, commanders=None, time_limit_s=None)
    # commanders: two modes; None keeps the constructor's.
    # time_limit_s: None = the mission's default (mission_time_limit_s) when a mission
    # is given, else the constructor's time_limit_s. Both stick with the roster like
    # the other fields, so one env mixes 90 s deathmatch, 150 s carrier, 120 s convoy.
env.mission_state(i): + "commanders", "time_limit_ticks"
rlf_sim.OBS_DIM_V4 == 385, OBS_LAYOUT/OBS_SLOTS + "order"
rlf_sim.MAX_TRAIN_SHIPS == 12, rlf_sim.COMMANDER_MODES == ["scripted", "external", "random"]
# v6:
rlf_sim.SIM_VERSION == 6, OBS_DIM == 583, OBS_DIM_V5 == 403
rlf_sim.PILOT_COMPAT_VERSIONS == [3, 4, 5, 6]
rlf_sim.PILOT_OBS_DIMS == {3: 385, 4: 385, 5: 403, 6: 583}   # sim version -> obs width its pilot reads
rlf_sim.OBS_LAYOUT/OBS_SLOTS + "ship_extras" (403, 70; 7) + "order_ships" (473, 110; 5)
rlf_sim.SHIP_EXTRA_W == 10, N_ORDER_SHIPS == 5, ORDER_KINDS == ["attack", "defend", "goto"]
rlf_sim.HULL_CLASSES == ["fighter", "strafer", "gunship", "carrier", "freighter", "spare"]
VecEnv(..., hide_orders=[False, False])   # per team, hidden-order mode (§7.2)
env.set_next_roster(..., hide_orders=None) # None keeps the env's setting
env.set_next_roster(..., start_layout=None, drill=False)
    # start_layout: per slot [x, y, vx, vy, heading], ValueError if the sim refuses it;
    # drill: drill rules (both §5.10). Both stick with the roster through auto-resets.
VecEnv(..., order_shaping_gamma=0.99)     # go-to shaping's discount (§8), in (0, 1]; every
                                          # match of the env, whatever roster is queued
env.order_shaping_gamma                   # f32, as the sim holds it
rlf_sim.ORDER_SHAPING_GAMMA == 0.99       # the default (f32)
env.order_transit  [N,S] bool    # effective order a go-to not yet arrived, or a defend whose
                                 # ward's threat set is empty; as of the obs (rebuilt match)
env.ward_threat    [N,S,S] bool  # [i, w, e]: e in w's threat set in the last step (every w on
                                 # the field; the finished match on a done step, like rewards)
env.ward_hull_lost [N,S] f32     # hull fraction each ship lost in the last step (a death counts)
env.order_tracks() -> dict of new arrays: standing_kind, effective_kind [N,S] int8
    # (0 none, 1 attack, 2 defend, 3 goto), target [N,S] int16 (-1), point [N,S,2] f32,
    # radius [N,S] f32 (the standing go-to's), arrived [N,S] bool, instance_start [N,S] u32
env.mission_state(i)["squads"][t][k]["order"]["kind"] in "none" | "attack" | "defend" | "goto"
# v8:
rlf_sim.SIM_VERSION == 8, OBS_DIM == 587, OBS_DIM_V7 == 583, NO_DEADLINE == 0
rlf_sim.PILOT_COMPAT_VERSIONS == [3, 4, 5, 6, 7, 8]
rlf_sim.PILOT_OBS_DIMS == {3: 385, 4: 385, 5: 403, 6: 583, 7: 583, 8: 587}
rlf_sim.OBS_LAYOUT/OBS_SLOTS + "order_time" (583, 4; 1)
rlf_sim.ORDER_TIME_TICKS == 900.0, CLOSENESS_RANGE == 100.0     # the block's scales (§7.2)
VecEnv(..., goto_timed_bonus=1.0, goto_miss_penalty=1.0)   # pay of a go-to with a deadline
                                          # (§8), finite and >= 0 or ValueError; every match
                                          # of the env, whatever roster is queued
env.goto_timed_bonus, env.goto_miss_penalty                # f32, as the sim holds them
rlf_sim.ORDER_TIMED_ARRIVAL_BONUS == 1.0, ORDER_MISS_PENALTY == 1.0   # the defaults
env.submit_command(i, team, {"kind": "squad", "squad": 0, "members": [0],
    "order": {"kind": "goto", "point": [x, y], "radius": 30, "deadline": tick}})
    # deadline: the match tick to arrive by, a non-negative integer; 0 or absent: none
env.order_tracks(): + deadline [N,S] u32 (the instance's, 0 none), missed [N,S] bool
env.mission_state(i)["squads"][t][k]["order"]: a go-to always has "deadline" (0 none)
```

v8 Python side: `RustVecEnv(..., goto_timed_bonus=, goto_miss_penalty=)` with the sim's
defaults and matching properties; `rosters.OpeningOrder.deadline_tick` (an absolute
match tick, `rosters.NO_DEADLINE = 0` for none; a non-negative int, on go-to orders
only, or `ValueError`) reaches the sim as the order's `"deadline"`;
`spike_policy.PILOT_OBS_DIMS[8] = 587`. A checkpoint records its own `obs_dim` and
every caller cuts the obs to it (`fit_obs`), so a 583-input pilot of v6 or v7 flies a
v8 env unchanged.

v5 Python side: `RustVecEnv` exposes `order_rewards` (property and `StepInfo.order_rewards`,
views) and passes `mission`, `commanders` and `time_limit_s` through
`set_next_roster`; `rust_env.PILOT_OBS_DIMS`, `MAX_TRAIN_SHIPS`. The v1-shaped policy
(`spike_policy`, 385 inputs) reads the prefix: `spike_policy.policy_obs(obs)` =
`obs[..., :385]`, used by PPO, BC and `act_numpy`.

Training is unchanged by default: deathmatch, scripted commanders (they set squad
state no pilot reads yet). `RustVecEnv` with a roster sampler pads to
`rosters.MAX_FLEET_SHIPS = 8`, not `MAX_SHIPS`, and rosters draw fighter, strafer and
gunship only.

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
every call.

**Rosters** (fleet pilot v1, `lab/runs/2026-10-30-fleet-pilot/plan.md`): every match
has `S` slots; a match with `k < S` ships fills slots `0..k` (team 0 then team 1)
and pads the rest: team and hull id -1, zero obs, `act_mask`, `alive` and all slot
masks false, zero rewards; padding never shoots or is hit. `set_next_roster`
validates the roster (known hulls, non-empty teams, at most `S` ships, a valid radius)
and applies it when env `i` is next rebuilt; it then sticks until replaced. `team`,
`hull_id`, the three slot masks and `arena_radius` describe each env's current
match and are rewritten only when that match is rebuilt, so after a done step they
already belong to the new match (`RustVecEnv`'s `StepInfo.prev_team` keeps the
finished one). A fixed-fleet env padded with `max_ships` steps bit-identically to
the unpadded one. `RustVecEnv(roster_sampler=...)` (`spacefight/env/rosters.py`)
queues a fresh seeded draw for every env each time its match ends.

**Arena rule**: `sim::setup::arena_radius_for(n_ships)` is the one place that sizes an
arena for a fleet (450 m for every size today; the reasons are in its doc comment and
the fleet pilot plan §2). Python gets it as `rlf_sim.arena_radius_for`, the browser as
`arenaRadiusFor`; training rosters, the fleet eval and the live page all call it.

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
arenaRadiusFor(n_ships: number): number;  // the shared arena rule (§10.1)
```

v4 additions (add, don't break: the ships view stays stride 29):

```ts
// config_json gains "mission": "carrier_battle" | {kind, ...} (§10.3) and
// "commanders": ["scripted", "external"]; both optional.
ship_ext_ptr(): number; ship_ext_len(): number;  // SHIP_EXT_STRIDE = 10 per ship, ship order:
    // [role (0 strike/other, 1 carrier, 2 transport), docked, parent (-1), jump (0 idle,
    //  1 charging, 2 departed), charge_until, has_waypoint, waypoint.x, waypoint.y,
    //  squad (-1), squad order kind]
mission_kind(): number;     // 0 deathmatch, 1 carrier battle, 2 convoy escort
end_reason(): number;       // EndReason code (§5.8)
command_due(): boolean;
submit_commands(team, json): void;   // one command object or an array (§10.3); throws on bad JSON/hulls
command_results_json(team): string;  // JSON array of outcomes of the last slow tick
commander_obs_json(team): string; mission_state_json(): string;  // the §10.3 views
squads(): Float32Array;     // SQUAD_STRIDE = 9 per squad, team 0's 4 then team 1's:
    // [team, index, n_members, members_mask, order_kind, target (-1), point.x, point.y, radius]
    // (point = go-to point or the target's current position: draw a line to it)
team_state(team): Float32Array;  // TEAM_STRIDE = 8: [carrier_slot (-1), hp, max_hp, shield,
                                 //  max_shield, hangar_count, bays, bays_ready]
hangar_hulls(team): Uint16Array; // docked reserves' hull ids, launch order
convoy(): Float32Array;     // CONVOY_STRIDE = 14 (empty unless convoy): [total, en_route, charging,
    // escaped, destroyed, to_destroy, to_escape, progress, start.x, start.y, jump.x, jump.y,
    // jump_radius, charge_ticks]
// module: pilot_compat_versions(): Uint32Array; pilot_compatible(v); arenaRadiusForMission(m, n);
// missionTimeLimitTicks(m); MAX_SHIPS(); COMMAND_TICKS(); MAX_SQUADS(); SHIP_EXT_STRIDE();
// SQUAD_STRIDE(); TEAM_STRIDE(); CONVOY_STRIDE()
// WP-S2: missionRostersJson(m): string  // default rosters (§10.3), JSON array of
//   {"name", "mission", "fleets": [[hull, ...], [hull, ...]]}; "[]" for deathmatch
```

Web notes: hull ids in the ships view follow the catalogue the page passes (sorted by
name; v4: carrier 0, fighter 1, freighter 2, gunship 3, strafer 4), so map them by
name. Ships with `docked = 1` or `jump = 2` are not on the field (`present = 0`); a
launch is a `Launch` event (mouth and direction for the streak) and the ship's
`present` flipping to 1 that step; `JumpCharge` → `JumpOut` brackets the jump effect.
The policy flies strike craft only (role 0); capital ships take `scripted_action`.
`bundle.ts` checks `manifest.sim_version` against the wasm and the pilot's
`pilot_sim_version` against `pilot_compat_versions()`. v5: it takes the pilot's obs
width from `pilotObsDimsJson()` (`Bundle.pilotObsDim`; the policy manifest's `obs_dim`
must equal it) and `match.ts` feeds the policy `obs(s).subarray(0, pilotObsDim)`;
`policy.js` refuses an obs of any other width. `scripts/build_bundle.sh` passes the
table to `tools/export_policy.py` (`--wasm-pilot-obs-dims`), which checks a
checkpoint's `obs_dim` against its own version's width.

v5 additions:

```ts
// config_json "commanders" also takes "random".
order_rewards(): Float32Array;     // last step's order reward per ship (§8)
// module: pilotObsDim(version): number (throws for a version this build does not fly);
// pilotObsDimsJson(): string  // {"3":385,"4":385,"5":403,"6":583,"7":583,"8":587}
// obsLayoutJson(): string     // {"blocks": [[name, offset, width], ...], "slots": [[name, n], ...]}
// MAX_TRAIN_SHIPS(): number   // 12
```

`config_json` is `MatchConfig` serialised with serde
(`{"seed":..,"arena_radius":..,"time_limit_ticks":..,"reaction_ticks":2,"fleets":[["fighter"],["fighter"]]}`
with hull names resolved on the WASM side; `arena_radius`, `time_limit_ticks` and
(v2) `reaction_ticks` default when absent).

### 10.3 The shared JSON spec (v4, `sim::spec`)

Both bindings parse missions and commands with the same serde structs (PyO3 passes
`json.dumps` of a dict); unknown fields are errors.

```jsonc
// mission: a kind name, or
{"kind": "deathmatch"}
{"kind": "carrier_battle", "jump_in": [2, 2]}                    // optional
{"kind": "convoy_escort", "start": [x, y], "jump_point": [x, y], // all optional:
 "jump_radius": 40, "charge_ticks": 60, "start_speed_frac": 0.8} // ConvoyEscort::standard(R)
// commanders (config_json / VecEnv): ["scripted" | "external" | "random", same]
// commands (one or an array):
{"kind": "launch", "hull": "fighter" | null, "bay": 0 | null}
{"kind": "waypoint", "ship": 0, "pos": [x, y] | null}            // null unsets
{"kind": "squad", "squad": 0, "members": [1, 2, 3],
 "order": {"kind": "none"} | {"kind": "attack", "target": 9} | {"kind": "defend", "ward": 0}
        | {"kind": "goto", "point": [x, y], "radius": 50, "deadline": 0}}
// v8: "deadline" is the match tick to arrive by, a non-negative integer; 0 or absent
// means none. The views (mission_state, commander_obs) always write it.
```

**Default rosters** (WP-S2, `mission::default_rosters(kind)`, as `MissionRosterView`
through `rlf_sim.mission_rosters` / `missionRostersJson`): what the live page drafts
for a mission and the mission survey balances. Slot order matters (a carrier battle's
first `jump_in` strike craft jump in, the rest launch in that order; transports form
their files in order). The first entry is the default.

| mission | name | team 0 | team 1 |
|---|---|---|---|
| carrier_battle | wing of 8 | carrier, F S F G F S F G | the same |
| carrier_battle | wing of 6 | carrier, F F S F S G | the same |
| carrier_battle | wing of 9 | carrier, F S F G F S F G F | the same |
| convoy_escort | 5 freighters | 5 freighters, F S F G | F F S G F S |
| convoy_escort | 6 freighters | 6 freighters, F S F G | F F S G F S |
| convoy_escort | 7 freighters | 7 freighters, F S F G | F F S G F S |

(F fighter, S strafer, G gunship.) Deathmatch has none: its rosters stay budget
drafts of 2–4 strike craft a side. The convoy rosters changed on 2026-11-01 for the
`reward_300` champion, with no rule change and no `SIM_VERSION` bump (rosters are data
the page and the evals read; goldens build their own fleets):
`lab/runs/2026-11-01-fighters-v2/convoy_balance.md`.

Views (serde-serialised): `CommanderObsView` (counts keyed by hull name),
`MissionStateView` (mission, end reason, tick, command_due, carriers, hangars, bay
cooldowns, squads with member lists and orders, convoy, per-ship role / docked /
parent / jump / waypoint / squad), `OutcomeView`.

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
3. `force_body = (1 if |err| < 0.9 else 0.2, 0)`; v3: `(0, 0)` instead while the
   target faces us (`target_aspect < 90°`), `dist < 1.5 × range` and our speed is
   over 40 m/s (a slower pass is a longer firing window). **Extend (v2, WP15):** if
   the target's bearing from our nose and our bearing from the target's nose both
   exceed 90° (backs to each other, i.e. just after a merge) and
   `dist < 0.6 × range` of the primary weapon (v2: 1.2), hold the current heading
   (`aim = heading'`) with `force_body = (1, 0)`. sim.js instead dropped to 0.3
   throttle inside 60 m and always turned straight back, so two scripted fighters
   parked nose to nose at 10–60 m, never left gun range after the first merge, and
   with the v2 nose armour took 93 % of hits at 0.5× (WP15 sweep). A ship with the
   enemy on its tail (pointing at it) still turns to fight. The extend check comes
   first, then deconfliction, then the pursuit above.
   **Deconfliction (v3 script):** with `r = rel_pos`, `v = target.vel − vel`,
   closing `c = −r·v / dist`, `t* = −r·v / |v|²`, `miss = r + v t*`: when `c > 5`
   m/s, `t* < 1.0 + 4 δ` s (`δ = reaction_ticks · DT`) and `|miss| < 11` m, move
   along `away = −miss / |miss|` (`perp(v̂)` if `|miss| ≤ 0.5`, which makes two
   scripted pilots on an exact collision course pass starboard to starboard);
   `side = +1` if `away` points to port (body +y), else −1. If `t* < 0.35 + 2 δ`,
   break: `aim = lead + 1.5 · side`, `force_body = (m, side)` with `m = 1` only once
   the target is more than 1 rad off the nose (before that the main engine would add
   closing speed), else 0. Otherwise sidestep with the nose kept on the lead point
   (the gun still bears): `force_body = (0, side · min(1, (11 − |miss|) / t*² / 19))`
   (each pilot covers half the shortfall at the ≈ 19 m/s² a full two-pod RCS push
   gives at the attack power split).
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

**Squad orders (WP-S2, `scripted/orders.rs`).** A strike-craft pilot whose squad has
an order picks its target from the order instead of the nearest enemy; everything
after target selection (manoeuvre, deconfliction, turrets, power) is unchanged:
- *Attack* `target`: the target; but an enemy strike craft within `0.4 ×` the primary
  gun range is fought first while the target is more than twice that away
  (self-defence on a strike run). A target that died since the slow tick falls back
  to the role's own choice until the commander re-tasks the squad.
- *Defend* `ward` (v6): the ward's threat set among the active ships (§5.9): the
  recent hitters of the ward first, then the others, each nearest the ward first
  (`scripted::orders::defend_target`). With the set empty the pilot keeps station: it
  wants the ward's velocity plus `0.5/s ×` the offset to its station on a ring round
  the ward (bound radius + 45 m; capped at `0.6 ×` its speed cap), at angle `slot ×
  2.4 rad` so a squad spreads; it turns its nose along the missing velocity, burns
  within 0.5 rad of it and coasts under 4 m/s missing.
- *Go-to* `point, radius` (v6): flies to its station at `radius/2` from the point (the
  same ring rule, at most `0.9 ×` its speed cap) without engaging; once it has arrived
  the order is complete and the pilot flies its role (*None*). v8: the script does not
  read the deadline (it flies the same transit with or without one); once the deadline
  is missed the order is over and it flies its role too.
- *None*: exactly the pre-order behaviour.

Pilots follow orders in every mission **except a deathmatch whose team has the
scripted commander**: there the orders are only shown, so the default deathmatch
(the fleet pilot's eval and training opponent, and the `v3_compat_*` traces) is
bit-identical to v3. An external or (v5) random commander's orders are followed in
a deathmatch too (stage B's random orders). Against a capital ship the fighter's deconfliction miss
distance is both bound radii plus 6 m instead of 11 m, and it covers the whole
shortfall itself (a capital ship does not sidestep), so a strafing run does not fly
into the carrier's hull.

**Capital ships (v4, `scripted/capital.rs`).** Both fly their waypoint
(`Match.command.waypoints`) and allocate the mains (thrusters with `dir.x > 0.5`) from
the force request alone and every other thruster from the torque request alone, so
they never turn on an off-axis main (that would add thrust a carrier cannot take back,
and yaw a transport must not have). *Carrier* (WP-S2): a turn-rate profile sized to
its own yaw authority `α` (full RCS, even power): wanted rate `sign(err) · min(√(α ·
e), 0.8 · e, 0.8 · ω_settle)` with `e = |err| − 0.02` rad (the hold band; ω_settle =
`α · DT / (1 − ANGULAR_DRAG)`), torque request `(want − ω) / (0.5 α)`. RCS hysteresis:
with every RCS pod off, a request under `RCS_ON_REQUEST = 0.4` stays 0, and once on a
pod runs until the request falls into the allocator's dead zone (≈ 0.21), so it no
longer chatters while holding heading. Outside `ARRIVE_RADIUS = 25` m it burns the
mains while within 0.6 rad of the waypoint and slower than `want = min(cap, 0.08 ·
(dist − 25))`, coming on below `want − 0.5` m/s once off, and staying lit at cruise
(`want = cap`; the soft cap holds the speed). No reverse thrust: it stops on drag
(≈ 10 v of coast). Inside, or without a waypoint, it holds heading and coasts; the
fighters' arena turn-back; shared power rules (§11 item 7) against the nearest enemy.
Its flak tracks the nearest enemy **strike craft** in reach (1.4 × range), and a
capital ship only when none is (flak cannot hit projectiles; a torpedo is a threat
through its launcher). *Transport* (final, user 2026-10-30): points at its waypoint
(PD `torque = clamp(4·err − 8·omega, ±1)`), mains on while its forward speed is below
`TRANSPORT_CRUISE_FRAC = 0.8` × cap, heading held with the RCS; within 25 m of the
point it cuts the mains and holds heading. It never evades or reacts to threats;
balanced power; no guns.

Roles as shipped: `fighter` (fighter), `skirmisher` (strafer: orbit at 120 m,
`orbit_sign = +1 if slot even else -1`) and `anchor` (gunship: standoff 170 m,
broadside), ported from sim.js in `fighter.rs` / `strafer.rs` / `gunship.rs`; a hull
whose role has no controller returns `IDLE`. The controller reads `Match` state, not
obs, so BC pairs are `(obs_t, act(state_t))`; it is deterministic and allocation-free.
Acceptance for v2 (§14.1 WP11, revised at WP14 for the real armour and balance):
scripted fighter duels (seeds 0..20) end in a kill before the time limit for 20/20 at
`reaction_ticks` 2, and for ≥ 12/20 at 0 and ≥ 18/20 at 4 (measured 14 and 19). At
`d = 0` the two pilots are often exact mirror images and hover nose to nose until the
time limit; the WP15 sweep over 200 seeds: 20 % time limit at `d = 0`, 0 % at 2, 3 %
at 4.
With the v3 deconflicting script the same test measures 19/20 at 0 (one mutual
kill), 20/20 at 2 and 19/20 at 4. Script-vs-script under v3 (duel harness n = 512,
contact survey n = 128, `d = 2`): contacts closing > 30 m/s 0.02 per match (v2
script 8.4), crash deaths in 2 % of matches (unchanged script under v3: 61 %),
draws 0.016, median 1492 ticks, hit rate 0.46, 4.9 passes per match
(`lab/runs/2026-10-29-collision-damage/`).

**Collision avoidance (v7, `avoid.rs`).** Under v7 crash damage the script flew itself
to death: script against script, fighters took 54 (carrier battle) and 71 (convoy) of
their 80 hp from crashes a match, mostly ramming freighters, their own capital ships
and passing strike craft, which the target-only deconfliction never saw. Now, between
the role's plan and the arena override, every strike craft (fighter, strafer, gunship;
on an order's station manoeuvre too) takes the soonest pass, over every other active
ship of either team but a fighter's strike-craft target (the deconfliction above keeps
that one), that closes faster than 8 m/s, comes within both bound radii + 3 m, and is
within `2.5 + 4 d` s (`d` the reaction delay). Early it sidesteps on the RCS away from
the miss, keeps the role's heading and cuts the mains while the other ship is within
1 rad of the nose. Inside `0.9 + 0.05 × (both radii) + 2 d` s it breaks: the nose
swings halfway between the miss direction and straight away, the mains burn once the
other ship is 1 rad off the nose. Measured (script vs script, 48 matches a mission,
`d = 2`): fighter crash damage 15 (carrier) and 30 (convoy) a match, strafers 0.8 and
2.1 (were 20 and 33); hard (> 30 m/s) fighter–freighter contacts in 24 convoys 31
(were 108).

## 12. Determinism contract and test

- `state_hash()`: FNV-1a 64 over, in order: `tick`, rng state (two u64), each ship's
  fields in declaration order (`to_bits()` for f32, raw for ints/bools; v2: `thrust_level`
  in place of `throttle`, then `reaction_ticks` and the `queue` as `4 × 21` u8 after
  `attach`), each projectile pool slot (v2: `decision_tick` after `fire_tick`),
  `proj_next`, `phase`, `winner`. Implemented in-crate (`hash.rs`), no `std::hash`.
  `pending`, `applied`, events, hits and rewards are outputs and are not hashed.
  v4 appends, after `winner`: per team the reserve count (`u64`) then slots; the
  mission state (end reason, carrier slots, `bay_ready` per team, transports bitmask,
  per-slot jump state as `(code, until)`); the command state (per team, per squad:
  members `u32`, order `(kind, target, point, radius)`; per slot: waypoint `(0|1,
  pos)`). `inbox` and `command_results` are not hashed. The v3 hash is reproducible
  from v4 state (`tests/determinism.rs::v3_state_hash`: v3 hull ids, no v4 fields).
  v5 appends the random commander's state (per team its rng `(state, stream)`, the
  `assigned` flags, per slot its squad, per team and squad `next_draw` then `drawn`)
  and then every slot's `OrderTrack` (kind, target, point, start tick, arrived,
  presence ticks, last Φ). `order_rewards` is an output, not hashed. The v4 hash is
  the v5 one without those two (`v4_state_hash`). v6: the `OrderTrack` loses the
  presence counter (kind, target, point, start tick, arrived, last Φ), and `hit_by`
  is appended, the match's slots × slots as `u32` row by row (ward-major).
  `ward_threat`, `hull_lost` and the hp marks are outputs or copies, not hashed. The
  v5 hash is rebuilt by the test (`v5_state_hash` with `V5Tracks`, v5's
  valid-order-keyed instances). v8: an order hashes its go-to deadline after the
  radius (0 for the other kinds), and the `OrderTrack` appends `deadline` and `missed`
  (kind, target, point, start tick, arrived, last Φ, deadline, missed). The v7 hash is
  the v8 one without those three (`v7_state_hash`, `hash_command_v7`), and the nine v7
  traces are replayed against it (`v7_compat_*`, §0.6).
- Native test (`crates/sim/tests/determinism.rs`): four golden scenarios, embedded
  with `include_str!` so the same binary runs under wasmtime:
  v4 adds `carrier_battle_s23` (two carriers with six-ship wings, scripted commanders, to
  a carrier kill) and `convoy_escort_s29` (four freighters and three escorts against
  six attackers, to `convoy_destroyed`; both regenerated by WP-S2 with the real commander), sampled every 300 ticks, with a `reason` line,
  and the `v3_compat_*` replays of `tests/golden/v3/` (§0.2 item 10). v5 adds
  `carrier_battle_random_s31`, `convoy_escort_random_s37` (the random commander on both
  sides) and `3v3_random_commander_s41` (random v scripted in a deathmatch), digests
  `order_rewards` too, and the `v4_compat_*` replays of all six v4 traces kept in
  `tests/golden/v4/` (§0.3; the v3 and v4 flavours digest the first 385 obs floats).
  v6 regenerates every current trace and adds the `v5_compat_*` replays of the four
  deathmatch traces kept in `tests/golden/v5/` (§0.4; the first 403 obs floats and the
  order rewards); the v4 mission replays are retired (v6 changes the missions).
  The node smoke runs `carrier_battle_random_s31` through the wasm-pack bundle. The v3 scenarios:
  `duel_fighter_s7` (1v1 fighter, seed 7), `2v2_mixed_s11` (fighter+strafer vs
  gunship+fighter), `3v3_mixed_s13`, all 3000 ticks with the scripted controller
  on both sides, sampled at ticks `{1, 30, 300, 1000, 3000}` (those reached before
  `Over`); and `3v3_random_s17` (9000 ticks of sticky uniform random action rows from
  the test's own PCG stream, sampled every 100 ticks). Each line carries the state
  hash plus an auxiliary digest of that step's flat events, hit records, rewards and
  every ship's obs, so outputs match across targets too. Regenerate golden only with
  `UPDATE_GOLDEN=1`; a diff in golden is a `SIM_VERSION` bump. v2 regenerates all
  four once (§14.1 WP14), after the balance tuple is final; v3 (collision damage)
  regenerates all four again, and the v3 scripted fighter (§0.1 item 5) the three
  scripted ones once more.
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
| 4v4 mixed (v4: the largest training roster) | ≥ 2,000 steps/s | 1,000 |

Budget reasoning: one 2-ship tick with ~20 projectiles and a 385-float obs is ~3–5 µs
(the v2 obs is 1.9× v1's but mostly zero-filled slots; the threat sort is over ≤ 256
pool entries with an 8-entry insertion list); 256 of them is ~1 ms single-threaded,
so 16 cores plus ~50 µs of PyO3 overhead leaves headroom. The targets above are
unchanged for v2. Measured at WP14 (SIM_VERSION 2, this laptop, idle, load < 1):
1v1 14,008 steps/s (3.6 M match-ticks/s), 2v2 8,114, single-thread 1v1 3,200; the
same run inside `RLF_BENCH=1 scripts/check.sh` right after the builds (load ~7) gave
6,623 / 3,735 / 2,175, still above every floor. The WASM row is not benchmarked yet. At the
target, the 4-hour nightly budget is sim-bound at >2 × 10^10 match-ticks; policy
inference will dominate. v4 (`MAX_SHIPS` 20, this laptop, idle): 1v1 12,598, 2v2 7,384,
single-thread 2,731, 4v4 2,215 steps/s; before the cap change 11,473 / 7,303 / 2,849 /
2,210 (no regression).

v5 adds the stage B training shapes, 12 slots (`MAX_TRAIN_SHIPS`), random v scripted
commander, with `scripted_actions()` every step for the trainer's labels: 4v4 @12
(target 1,200, floor 600), carrier battle (carrier + 5 a side) and convoy (4
freighters + 3 escorts v 5) @12 (target 600, floor 300). Measured 2026-10-30 at
load ≈ 2–4 (other runs shared the machine): 1v1 11,738, 2v2 6,916, single-thread
2,615, 4v4 2,179, 4v4 @12 + labels 1,718, carrier @12 + labels 400–488, convoy @12 +
labels 513–605 steps/s. The mission shapes under random actions are a pessimistic
bound (random flak and fire fill the projectile pool): with every ship flown by its
script they run ≈ 1,060–1,090 steps/s (carrier) and 1,050–1,090 (convoy), ≈ 270 k
match-ticks/s. v4 on the same machine and minute: carrier 490 / 1,117, convoy 622 /
1,118 (labels / scripted play), so the order block, order tracks and order reward
cost within noise.

v6 (583-float obs: five more ship records and seven extras records per observer;
threat sets for every ship each step) measured 2026-10-31, v5 and v6 back to back on
the same minute (the machine was intermittently loaded, so absolute numbers drift by
2×; the paired ratio is the result): 1v1 5,356 → 4,879, single-thread 2,097 → 1,878,
4v4 1,023 → 879, 4v4 @12 + labels 775 → 696, carrier @12 + labels 492 → 425, convoy
@12 + labels 607 → 506 steps/s: 10–17 % slower. In a quiet run v6 gave 1v1 10,281,
2v2 5,919, single-thread 2,446, 4v4 1,829, 4v4 @12 1,447, carrier 880, convoy 527,
every floor met; floors unchanged. The body-frame rotation is computed once per
observer (it was two `sinf`/`cosf` per record), which took the obs from +42 % to
+21 % over v5 in a native profile of carrier battles.

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
