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
| 39 | own strike craft: order hold left, decisions / `HOLD_DECISIONS` |

**Globals, `GLOBAL_DIM = 53`:**

| Index | Feature |
|---|---|
| 0-3 | role one-hot: deathmatch, carrier battle, convoy defender, convoy attacker (v9: a station assault reads as its `reads_as`, see below) |
| 4 | time left / time limit |
| 5 | tick / time limit |
| 6-8 | hangar reserves by strike hull (fighter, strafer, gunship) / 8 |
| 9 | bays ready / `MAX_BAYS` |
| 10 | bays on my carrier / `MAX_BAYS` |
| 11 | my carrier alive (0 if none) |
| 12 | enemy carrier alive (0 if none) |
| 13-17 | convoy: escaped, destroyed, needed to escape, needed to destroy, charging, each / convoy size (0 outside a convoy) |
| 18-49 | per squad k = 1..4, 8 each: size / 8, order kind one-hot (4), hold left / `HOLD_DECISIONS` (the longest among its members), go-to point x, y (team frame, / R; 0 unless go-to) |
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
(toward the enemy side). Go-to orders use radius `GOTO_RADIUS = 60` m and carry no
deadline (SIM_VERSION 8 lets a go-to carry one, `docs/SIM_SPEC.md` §0.6; so far only an
external commander's orders do). A carrier waypoint is the point itself.

**Station assault (SIM_VERSION 9).** No input changed (`COMMANDER_IO_VERSION` stays
1). The station is team 0's carrier: its slot is the carrier entity, its bays launch the
garrison (the launch heads and reserves work as on a carrier), "my carrier alive" is the
station's. The role one-hot reads the mission's `reads_as` (`{"kind":
"station_assault", "as": ...}`): `carrier` sets index 1 for both teams (the symmetric
reading), `convoy` sets 2 for the defender (team 0) and 3 for the attacker, the
asymmetric reading, with the convoy globals (13-17) at 0 since there are no
transports. A bomber is an `anchor`, so the gunship launch head launches it (the first
docked anchor in fleet order) and it counts in the gunship reserves. The decisions that
should matter here are timing and concentration (`lab/runs/2026-11-19-station-bomber`):
when the attacker sends its wing (all at once or piecemeal into the turrets), whether
its escorts defend the bombers, and for the defender which attackers it intercepts
(bombers first) and when it launches.

**Citadel and dreadnought (SIM_VERSION 10).** No input changed. The citadel is team 0's
carrier as the station was; a bay destroyed (`docs/SIM_SPEC.md` §0.8) is neither ready
nor counted in "bays", so the launch mask closes when every bay is gone and a launch
through a dead bay is refused (`bay_destroyed`). The attacker's dreadnought (role
`line`) is a capital ship: never in a squad, never given an order, not counted as a
strike craft (the scripted commander holds it at a staging point until the strike
goes; a learned commander leaves it to its own script). It does count toward "repelled": the assault fails only when the
carrier, the dreadnought and every strike craft are gone.

**Dock and repair (SIM_VERSION 11).** No input or output changed (`COMMANDER_IO_VERSION`
1), so the learned commander cannot order a recall: its craft never go home until a
commander is trained to send them (stage 4 of `lab/runs/2026-11-20-dock-repair/plan.md`,
a new output). There is no sim-side stand-in (owner's call, 2026-11-20). The scripted
commander does recall (`docs/SIM_SPEC.md` §5.11): every own strike craft below half its
hull, unless it is finishing a kill or under an enemy capital ship's guns, and the random
commander keeps those recalls with the scripted launches. So a learned commander's
opponent recalls, and its entity inputs see it: a ship flying home holds a dock order of
its own, which wins over its squad's (it is taken out of its squad when recalled), and
its entity's order one-hot reads it as a go-to (a v8 to v10 pilot reads it so too; a v11
pilot also sees the obs's dock block). A returned ship
waits in the hangar ("reserves" counts it) and may launch 4 s after docking; the launch
mask needs a reserve that may launch, so a hangar holding only returned ships inside
their turnaround closes it. The eval's order timings (`orders_a` / `orders_b`) count
squad orders only, not dock orders.

**Masks** (a choice is allowed when its mask is true; "keep" and "hold" always are):

- Launch a hull: my carrier alive, a reserve of that hull, a bay ready. Launches go
  fighter, strafer, gunship in that order; the sim picks the bay; one refused for a busy
  bay is reported, not an error.
- Carrier waypoint: points only while my carrier is alive and can move (SIM_VERSION 9:
  a station, a static carrier, only keeps).
- Squad of slot s: only for my strike craft on the field or arriving, and not while the
  ship is held.
- Order of squad k: none, attack, defend and go-to only while my team has strike craft
  (on the field or arriving) and not while any of the squad's members is held. Attack
  also needs an enemy on the field, defend an own ship on the field. Masks are computed
  before the decision, so a squad that ends the decision empty gets no command; its order
  is moot.
- Attack target: enemy ships on the field. Defend ward: own ships on the field (strike
  craft or capital).

**Holds:** a ship whose own order a decision changed keeps that order: it cannot move
squad, and its squad's order cannot change, until `HOLD_DECISIONS = 5` decisions (5
seconds) after the change. A change at decision n leaves decisions n+1 to n+4 able only to
keep; the ship is free again at decision n+5. So a ship's order changes at most once every
5 seconds.

- A ship's order is its squad's order (kind, target or ward, or point), or none without a
  squad. It changes when its squad's order changes, when the ship moves to a squad with a
  different order, or when it joins or leaves a squad and that changes its order.
- A squad's order is held while any of its members is held: its hold left is the longest
  among them.
- A hold ends early when the order is spent: the attack target or the defend ward is gone
  (dead, or jumped out), or the ship has arrived at its go-to point, or it has missed the
  go-to's deadline. The ship can then be re-ordered at once.
- Moving a ship between squads that have the same order, or from no squad into a squad
  with no order, changes nobody's order and sets no hold. Re-issuing the same order is not
  a change.
- Launches and the carrier waypoint are never held.

The first rule (to 2026-11-10) locked a squad's order for 3 decisions after it changed
and, separately, a ship for 3 decisions after it moved squad; the two did not see each
other, so a ship could be re-ordered every second through squad moves. The `c1_*`
commanders were trained under it. The layouts did not change, so `COMMANDER_IO_VERSION`
stays 1. The owner's reason for the change: commanders "change orders far too often,
sometimes giving ships changing orders every second".

**Decoding** (Rust, shared by training and the browser): apply the squad moves to get each
squad's members, then each squad's order, then send a `Command::Squad` for every squad whose
members or order changed, then the waypoint, then the launches. Every ship whose order
the decision changed starts a hold. The hold state (per team: decision count, each ship's
hold, the number of ships the last decision changed, last launch tick) lives beside the
match, not in its hashed state, and resets with the match.

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
- **Holds.** `CommanderLocks` (the name is from the first rule) keeps a decision count
  and, per slot, the first decision at which the ship's order may change again, the kind
  of the order the hold was set with, and the tick it was set at: a change decoded at
  decision `n` holds decisions `n + 1 ..= n + 4`, and the ship is free at `n + 5`. "Hold
  left" (`ship_hold_left`) is the held decisions still to come, counting the next one (4,
  3, 2, 1, then 0), so feature 39 is at most 0.8. A squad's hold left
  (`squad_hold_left`) is the longest among its members, read from the match's squads
  now; a ship that joins a squad with a different order is held, and so holds that
  squad's order too. Python keeps one `CommanderLocks` per env and team and resets it
  whenever that env's match is rebuilt; the browser keeps one per team per `WasmMatch`.
- **Whose order changed.** For each of the team's strike craft, decoding compares the
  whole order of its squad before the decision with that of its squad after (none
  without a squad). Every ship for which they differ starts a hold, and the count is kept
  as `changed_ships`. That covers a ship that loses its order (moved to no squad, or its
  squad's order set to none): it is held too.
- **A spent order.** A hold set with an attack, defend or go-to order is over as soon as
  the ship's effective order (`order::effective_order`) is none: the target or ward is
  not on the field, the ship has arrived at the go-to point, or (SIM_VERSION 8) the
  go-to had a deadline and the ship missed it. The decoder gives its go-tos no deadline,
  so the last case needs an order that came from somewhere else. This is read only once the
  decision that set the hold has applied (a later tick), so the ship's old order cannot
  end the new hold. A hold set with no order runs its full length. When one member of a
  squad arrives, that ship can be moved at once, but the squad's order stays held while
  another member is.
- **Decoding applies the masks itself**, computed from the state before the decision: a
  choice its mask forbids reads as keep (or hold), including an attack or defend whose
  target or ward head names a slot its mask forbids. A value outside its head's choices,
  or a decision that is not 40 values, is an error and changes nothing.
- **A squad that ends the decision empty** takes no new order. If its members changed
  (every member moved out, or to no squad), it still gets a `Command::Squad` with no
  members and its current order, so a move to "no squad" takes effect.
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
- `submit_commander_actions(team, env_ids: int64[K], actions: int32[K, 40]) -> int32[K]`:
  the number of ships whose order each decision changed (ValueError before any env
  changes for a wrong dtype or shape, a repeated env, a team that takes no decisions, an
  env not due, or a value out of range; IndexError for a bad env id)
- `commander_locks(i, team) -> dict`: `decisions`, `squad_hold_left` (per squad) and
  `ship_hold_left` (per slot) as the next decision would see them (0 is free now),
  `changed_ships` (by the last decision), `last_launch_tick`
- `team_values() -> f32 [N, 2]`
- module level: `rlf_sim.commander_io()` (lowercase keys: `version`, dims, scales,
  `hold_decisions`, `command_ticks` (the learned cadence), action heads as
  `name -> (offset, width, choices)`, entity, global and flat layouts; entity feature 39
  is `ship_hold`),
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

**The price of an order** (`TrainConfig.order_price`, default 0.0): each decision's reward
is reduced by `order_price` times the number of ships whose order that decision changed
(what `submit_commander_actions` returns). It is not potential-based: it is meant to
change which policy is best, as the price of a shot does for the pilots. At the default
it does nothing.

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

**The unseen enemy** (the fifth of `TrainConfig.opponent_shares`, default 0): the
scripted commander with its orders hidden from its own pilots, so a side that launches
as the script does and is otherwise not commanded. On 2026-11-15 that side beat the
scripted commander 0.75 to 0.25 over pilots that follow orders, and every learned
commander we had. A learner that beats it gives orders worth more than no orders. In the
third phase none did: with half their matches against it, two fresh commanders learned to
keep ships under an order only 3 to 6% of the time and ended level with it; one with
`ent_coef` 0.01 kept ordering about half the time and lost 0.34 to 0.66
(`lab/runs/2026-11-15-commander-3/results.md`). So `TrainConfig.ent_coef` defaults to
0.002 since 2026-11-21, the value every run since has used.

**Build on what we have.** A commander run starts from the best commander checkpoint
that fits (`init`), not from a fresh net. Today that is commander 3's `live` 197
(`lab/runs/2026-11-15-commander-3/live/checkpoints/commander_197.pt`), level with the
no-orders side over the live ten. Start fresh only on purpose: when the inputs or outputs
changed so that no checkpoint loads, or as a deliberate unrelated line for comparison.
The plan says which, and why. Pilots do the same: a new pilot is a child of a member
(`docs/PILOT_TRAINING.md` "The plan in short").

**Keep prior** (`TrainConfig.keep_prior`, default 0.8): a fresh actor's order and squad
heads start with a bias toward "keep", so an untrained commander keeps with about that
probability when every choice is allowed, not 1 time in 5 (order) or 1 in 6 (squad). It
applies to a new network only.

The training log (`log.jsonl` in the run directory) also records, per update,
`order_seconds` (the mean seconds a ship goes between changes of its order) and
`ordered_share` (the share of ship-seconds spent with an order).

**Station assault** (`TrainConfig.mission_weights`' fourth weight, default 1 since 2026-11-21, so a commander trains on all four live missions equally; the citadel roster on SIM_VERSION >= 10;
`station_convoy_share`, default 0, the chance a station assault reads as a convoy escort,
else as a carrier battle). The log scores each enemy per station role
(`win_unseen_defender`, `win_unseen_attacker`, ...). **A start** (`TrainConfig.init`,
default none): a commander checkpoint the actor starts from instead of a fresh net (the
critic starts fresh). `pilot_root` names the checkout holding the pilots' weights, for a
run from a worktree. First used by `lab/runs/2026-11-19-station-commander`.

**Settings for one-sided and narrowed runs** (2026-11-21; each defaults to the old
behaviour):

- `launch_prior` (default 0, off): after any `init` load (or on a fresh net), the launch
  head restarts with small weights and biases such that each hull class launches with
  this probability per decision (`policy.lean_to_hold`: hold's bias is
  log((1 − p)/p) above launch's; the head's six outputs read as `[hull, hold|launch]`).
  A head near even odds empties the hangar in about 4 s, so a learner never tries
  holding a reserve, which the hand rules found worth +0.14 to +0.19 to the station
  defender (`lab/runs/2026-11-19-station-rules`). At 0.03 a hull class launches about
  once per 33 decisions (about 33 s).
- `learner_team` (default −1, either side, drawn per match): 0 or 1 pins the learner to
  that team in every match (a station assault's team 0 defends). The draw is still made
  and discarded, so a pinned run's other draws are an unpinned run's. A pinned learner
  must have self and snapshot shares of 0: self-play would train it on the other side
  too, and its snapshots never played that side.
- `station_roster` (default "", the live default: `spacefight.eval.missions.
  default_rosters`, the citadel from SIM_VERSION 10): a roster name from
  `rlf_sim.mission_rosters("station_assault")`, for example "strike of 8" (7 against 9
  ships, one carrier attacking) or "citadel" (8 against 11: the citadel, and a carrier
  and a dreadnought attacking). An unknown name raises `ValueError` at config time.
- `forbid_orders` (default none): order kinds ("none", "attack", "defend", "goto") the
  learner never picks (`policy.forbid_orders`, after any `init` load). Each one's weight
  row in the order head is zeroed and −30 added to its bias, so it has about 1e-13 of
  the probability in every state. It is only weights, so eval and the browser export
  need nothing new, and snapshots (and so self-play enemies) inherit it. Training does
  not undo it: a choice never sampled gets a gradient of about its probability, which
  Adam (epsilon 1e-8) turns into steps of about 1e-9, so a bias rather than a mask in the
  trainer is enough (`tests/test_commander_policy.py` runs PPO-like updates against it).

**The pilots a commander trains over** (`TrainConfig.live_pilots`, default the live
list): a file of the same schema naming other pilots, for example only those that follow
orders (`lab/runs/2026-11-15-commander-3/pilots_followers.json`). The critic has one
identity per pilot in the file, so a run keeps the file it started with.

## Eval

`spacefight.commander.eval` plays commander `--a` against `--b` (JSON
`rlf.eval.commander/1`): each live mission's rosters in turn (deathmatch, carrier battle,
convoy escort and, since 2026-11-21, the station assault, the citadel only), `a` on each side half the
time, pilots drawn ship by ship with a fixed seed. A side is a checkpoint or one of:

- `scripted`: the sim's scripted commander.
- `random`: the script's launches with random squads and orders.
- `unseen`: the scripted commander with its orders hidden from its own pilots (the sim's
  hidden-order mode). It launches as the script does and its pilots fly as if nobody
  commanded them, so it is the "no orders" side. A commander's orders are worth something
  only if it beats this. The order counts the eval reports for it are the script's, which
  no pilot saw.

`--pilots <list.json>` draws both sides' pilots from another list of the live list's
schema. The eval also times every ship's orders (`orders_a`, `orders_b`).

`--checkpoint-root` names the checkout the list's checkpoints are under, for a worktree.

Drawing one pilot per side instead (each side one commander and one pilot) made no
difference (`lab/runs/2026-11-19-pairing/results.md`), so the option was removed.
