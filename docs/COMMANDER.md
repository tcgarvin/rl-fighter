# The learned commander

Status: **agreed with the owner 2026-11-07; being built.** The Rust side (cadence,
features, masks, decoding, bindings) is in `crates/sim/src/commander_io.rs`; "Rust
implementation" below records how it reads the points this contract leaves open. This
is the interface contract
between the sim (Rust: features, masks, decoding, cadence), training (Python) and the live
page (WASM + JS). Changing a layout below changes the network's shape, so it is a version
bump of the commander interface (`COMMANDER_IO_VERSION`).

## Where it fits

- Commanders and pilots train in alternating phases, the other side frozen
  (`docs/PILOT_TRAINING.md`). The commander phase trains commanders against a stable of
  commanders, with every strike craft on both sides flown by a pilot drawn at random,
  ship by ship, from the live list (`lab/live_pilots.json`), as the live page does.
- The scripted commander is a member of the commander stable until learned ones beat it.
- Transports stay on their scripted route; their waypoint is never the commander's.

## Cadence and the `learned` commander mode

- A new `CommanderMode::Learned`: like `External`, the caller submits commands, but on its
  own cadence, `LEARNED_COMMAND_TICKS = 30` (1 Hz). Scripted, random and external teams keep
  `COMMAND_TICKS = 60`, so their matches are unchanged (no `SIM_VERSION` bump).
- A team's slow tick sanitises that team's squads and waypoints, as now, then applies its
  commands. Per-team cadence: a team's slow tick is `tick % its_command_ticks == 0`.
  A team that is not due keeps its inbox for its own slow tick.
- The commander decides once per its slow tick, before it: `commander_due(team)` is true on
  the step whose tick will be the team's slow tick (`Match::command_due_for(team)`; the
  team-less `command_due` now means either team's).

## Frame

Team frame: the world frame for team 0, rotated 180 degrees for team 1 (`p -> -p`), so
every commander's home side is `-x` and the enemy side `+x`. Positions are divided by the
arena radius `R`, velocities by `VEL_SCALE = 100` m/s.

## Inputs

Entities are indexed by ship slot (`MAX_SHIPS = 20`), so a pointer head's choice is a
slot. An entity is **valid** when the ship is alive and on the field or arriving (not yet
jumped in). Docked reserves are not entities; the globals count them.

**Entity features, `ENTITY_DIM = 40` per slot** (zeros for invalid slots):

| Index | Feature |
|---|---|
| 0 | valid |
| 1 | own team (1) or enemy (0) |
| 2-7 | hull class one-hot (`HULL_CLASSES`: fighter, strafer, gunship, carrier, freighter, spare) |
| 8-9 | position, team frame, / R |
| 10-11 | velocity, team frame, / 100 m/s |
| 12-13 | heading cos, sin, team frame |
| 14 | hull fraction |
| 15 | shield fraction (0 if no shield) |
| 16 | on the field |
| 17 | arriving |
| 18 | charging its jump (transport) |
| 19-23 | own strike craft: squad one-hot (none, 1, 2, 3, 4) |
| 24-27 | own strike craft: effective order kind one-hot (none, attack, defend, go-to) |
| 28-31 | an attack target of my squad k (k = 1..4) |
| 32-35 | the defend ward of my squad k |
| 36 | enemy that threatens one of my capital ships (in its threat set) |
| 37 | distance to my carrier, or to my lead transport, / R (0 if neither) |
| 38 | distance to the enemy carrier, or the enemy lead transport, / R (0 if neither) |
| 39 | own strike craft: squad-move lock left, decisions / `LOCK_DECISIONS` |

**Globals, `GLOBAL_DIM = 53`:**

| Index | Feature |
|---|---|
| 0-3 | role one-hot: deathmatch, carrier battle, convoy defender, convoy attacker |
| 4 | time left / time limit |
| 5 | tick / time limit |
| 6-8 | hangar reserves by strike hull (fighter, strafer, gunship) / 8 |
| 9 | bays ready / `MAX_BAYS` |
| 10 | bays on my carrier / `MAX_BAYS` |
| 11 | my carrier alive (0 if none) |
| 12 | enemy carrier alive (0 if none) |
| 13-17 | convoy: escaped, destroyed, needed to escape, needed to destroy, charging, each / convoy size (0 outside a convoy) |
| 18-49 | per squad k = 1..4, 8 each: size / 8, order kind one-hot (4), lock left / `LOCK_DECISIONS`, go-to point x, y (team frame, / R; 0 unless go-to) |
| 50 | own strike craft on the field / 10 |
| 51 | enemy strike craft on the field / 10 |
| 52 | seconds since my last launch / 20, capped at 1 (1 if never) |

## Outputs

One decision per slow tick, `ACTION_DIM = 40` integers:

| Index | Head | Choices |
|---|---|---|
| 0-2 | launch, per strike hull (fighter, strafer, gunship) | 0 hold, 1 launch one |
| 3 | carrier waypoint | 0 keep, 1-25 map point |
| 4-23 | squad of ship slot s | 0 keep, 1 no squad, 2-5 squad 1-4 |
| 24-27 | order of squad k | 0 keep, 1 none, 2 attack, 3 defend, 4 go-to |
| 28-31 | attack target of squad k | ship slot 0-19 |
| 32-35 | defend ward of squad k | ship slot 0-19 |
| 36-39 | go-to point of squad k | map point 0-24 |

A target, ward or point head is part of the decision only when its squad's order chose
that kind (its log-probability counts only then).

**Map points, `N_POINTS = 25`, team frame:** point 0 is the centre; point `1 + 8 r + b` is
at radius `(0.3, 0.6, 0.85)[r] R` and bearing `45 b` degrees, counter-clockwise from `+x`
(toward the enemy side). Go-to orders use radius `GOTO_RADIUS = 60` m. A carrier waypoint
is the point itself.

**Masks** (a choice is allowed when its mask is true; "keep" and "hold" always are):

- Launch a hull: my carrier alive, a reserve of that hull, a bay ready. Launches go
  fighter, strafer, gunship in that order; the sim picks the bay; one refused for a busy
  bay is reported, not an error.
- Carrier waypoint: points only while my carrier is alive.
- Squad of slot s: only for my strike craft on the field or arriving, and not while its
  squad-move lock lasts.
- Order of squad k: none, attack, defend and go-to only while my team has strike craft
  (on the field or arriving) and not while the squad's order lock lasts. Attack also needs
  an enemy on the field, defend an own ship on the field. Masks are computed before the
  decision, so a squad that ends the decision empty gets no command; its order is moot.
- Attack target: enemy ships on the field. Defend ward: own ships on the field (strike
  craft or capital).

**Locks:** when a squad's order changes (kind, target or ward, or point), its order is
locked to "keep" for `LOCK_DECISIONS = 3` decisions. When a ship moves squad, it is locked
for 3 decisions. Re-issuing the same order is not a change. Launches are never locked.

**Decoding** (Rust, shared by training and the browser): apply the squad moves to get each
squad's members, then each squad's order, then send a `Command::Squad` for every squad whose
members or order changed, then the waypoint, then the launches. The lock state (per team:
decision count, squad lock ends, ship lock ends, last launch tick) lives beside the match,
not in its hashed state, and resets with the match.

## Rust implementation

`sim::commander_io` (constants, `CommanderLocks`, `features`, `masks`, `decode`,
`submit`) is shared by the Python env and the browser. Where the contract above is open,
it reads it so:

- **Entities.** Arriving ships of both teams are entities (as above). Entity features
  19-27 and 39 are zero for capital ships and enemies. 24-27 use the ship's effective
  order (`order::effective_order`). 28-35 mark the target or ward of each squad's
  standing order, whatever the squad's size. 36: the enemy is in the threat set
  (`Match::threat_set`, candidates the ships on the field) of one of my capital ships on
  the field. Heading cos/sin in the team frame is `sign * (cos h, sin h)`.
- **Reference ships (37, 38).** A team's live carrier, else its lead transport: its
  transport on the field furthest along the route (ties to the lower slot). Team 1 in a
  convoy has none, so its 37 is 0.
- **Globals.** 9 and the launch mask count bays ready on the coming slow tick
  (`tick + 1`, when a launch decided now applies). 10 is the carrier's bay count while
  the team has a carrier, alive or not (0 without). 13-17 use `convoy_status`
  (`to_escape`, `to_destroy`). A squad's size (18 + 8k) counts its members that are
  entities; its order kind is its standing order's. A drill reads as a deathmatch.
- **Locks.** `CommanderLocks` keeps a decision count and, per squad and per slot, the
  first decision that is free again: a change decoded at decision `n` locks decisions
  `n + 1 ..= n + 3`. "Lock left" is the locked decisions still to come, counting the next
  one (3, 2, 1, then 0). Python keeps one per env and team and resets it whenever that
  env's match is rebuilt; the browser keeps one per team per `WasmMatch`.
- **Decoding applies the masks itself**, computed from the state before the decision: a
  choice its mask forbids reads as keep (or hold), including an attack or defend whose
  target or ward head names a slot its mask forbids. A value outside its head's choices,
  or a decision that is not 40 values, is an error and changes nothing.
- **A squad that ends the decision empty** takes no new order (and no order lock). If its
  members changed (every member moved out, or to no squad), it still gets a
  `Command::Squad` with no members and its current order, so a move to "no squad" takes
  effect.
- **Waypoints and launches.** A chosen waypoint is always sent (re-sending the same point
  is harmless). A decision with any allowed launch sets the last launch tick to the coming
  slow tick, even if the sim then refuses a second launch for a busy bay. Each launch
  names the hull of the first docked reserve of that class.
- **Submitting** needs the team's commander to take decisions (`learned`, or `external`)
  and its slow tick to be the next step; otherwise the bindings raise and change nothing.

### Bindings

Python (`rlf_sim.VecEnv`; thin wrappers of the same names on `RustVecEnv`), `N` envs,
`E = 20` entity slots whatever `n_ships` is:

- `commander_due(team) -> bool[N]`
- `commander_features(team) -> dict`: `globals` f32 `[N, 53]`, `entities` f32
  `[N, E, 40]`, `valid` bool `[N, E]`, `launch_mask` bool `[N, 3]`, `waypoint_mask` bool
  `[N, 26]`, `squad_mask` bool `[N, E, 6]`, `order_mask` bool `[N, 4, 5]`, `target_mask`
  bool `[N, E]`, `ward_mask` bool `[N, E]`
- `submit_commander_actions(team, env_ids: int64[K], actions: int32[K, 40])` (ValueError
  before any env changes for a wrong dtype or shape, a repeated env, a team that takes no
  decisions, an env not due, or a value out of range; IndexError for a bad env id)
- `commander_locks(i, team) -> dict` (`decisions`, `squad_lock_left`, `ship_lock_left`,
  `last_launch_tick`), `team_values() -> f32 [N, 2]`
- module level: `rlf_sim.commander_io()` (version, dims, scales, action heads as
  `name -> (offset, width, choices)`, entity, global and flat layouts),
  `LEARNED_COMMAND_TICKS`; `"learned"` in `COMMANDER_MODES` (and `spacefight.env.
  rosters.COMMANDER_MODES`), accepted by the constructor and `set_next_roster`.

Browser (`WasmMatch`; `"learned"` accepted in `config_json.commanders`):
`commander_due(team)`, `commander_features(team) -> Float32Array` (1082 floats),
`submit_commander_action(team, Int32Array(40)) -> number of commands` (throws as Python
raises), `team_values()`; module `COMMANDER_IO_VERSION()`, `COMMANDER_FEATURES_LEN()`,
`COMMANDER_ACTION_DIM()`, `LEARNED_COMMAND_TICKS()`, `commanderIoJson()`. The flat
features are, in order (offset, width): globals (0, 53), entities (53, 800: slot-major,
40 each), valid (853, 20), launch mask (873, 3), waypoint mask (876, 26), squad mask
(902, 120: slot-major, 6 each), order mask (1022, 20: squad-major, 5 each), target mask
(1042, 20), ward mask (1062, 20); masks 0/1.

## Reward

Per decision, for the commander's team: `gamma * phi' - phi` (potential-based, so it does
not change which policy is best) with `phi = SHAPING_WEIGHT * (v_own - v_enemy) / v_total0`
(team values as the sim computes them, `v_total0` both teams' value at the start), plus
+1 for a win and -1 for a loss at the end (a draw 0), by each mission's own rules.
`SHAPING_WEIGHT` starts at 0.5.

## Network (Python, exported for the browser)

1. A shared entity encoder: `ENTITY_DIM -> 64 -> 64`, tanh.
2. One self-attention layer over valid entities (4 heads, width 64, residual).
3. A pooled summary: mean of valid entities, joined with the globals, `-> 128`, tanh.
4. Heads:
   - launch (3 × 2) and carrier waypoint (26) from the summary;
   - squad of slot s (6) from that slot's entity vector and the summary;
   - per squad k, a query from a learned squad embedding, the squad's 8 globals and the
     summary: order (5), go-to point (25), and attack and defend pointers, each the dot
     product of a projected query with the projected entity vectors.

The critic is separate and used only in training: the same shape to a value, plus each
entity's pilot identity (which net flies it), which the actor does not see.

## Training

PPO over decisions with GAE (`gamma` 0.99 per decision, `lambda` 0.95). Each match draws
the learner's team at random, the enemy commander from the stable (scripted, random, the
learner itself, its past snapshots; weighted toward the ones it beats least), and every
strike craft's pilot from the live list. Missions and rosters as on the live page.
