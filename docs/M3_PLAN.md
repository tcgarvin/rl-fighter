# M3 — Carriers, convoys and commanders (plan, 2026-10-30)

Status: **stage A done and live; stage B run 1 failed its order gate, run B2b passed it but failed missions and deathmatch (`lab/runs/2026-10-31-order-pilot{,-b2b}/results.md`); nothing promoted; order redesign (attack / defend / go-to) next** (decisions under "Stage B decisions"; the user's answers of 2026-10-30 are in §3).
Asked for by the user on 2026-10-30, after fleet pilot v1: team deathmatch works, duels
are dull, and the story needs the carrier and the layered ("feudal") AI on the live
page, with matches that have different goals, escort among them. A scripted or stub
commander is fine. This pulls DESIGN §12's M5 (flagships, bays, a scripted commander,
goal-conditioned orders) ahead of the attention policy, the league and the nightly lab,
which move back one milestone each.

Deferred on purpose (user, 2026-10-30): pilot diversity (several policies or styles on
one hull type). Two identical commanders may well produce the same symmetry problem the
duels had; we deal with that when we see it.

## 1. Done when

The live page rotates through three missions, every one readable without explanation:

- **Team deathmatch.** As today, 2–4 ships a side (no duels since 2026-10-30).
- **Carrier battle.** Each side has a carrier that launches its air wing from its bays
  over the match. Losing your carrier loses the match.
- **Convoy escort.** The scene opens on a convoy of 3–5 transports **already under way**
  toward a jump point, with the defending fleet flying in formation with it. The
  attackers **jump in**.
  - When a transport reaches the jump point, it **jumps out** and counts as escaped.
  - When the convoy is through, the defenders jump out too, for the look of it.
  - The attackers win by destroying enough of the convoy before it gets through.

A **commander** per side decides on a slow tick (every 2 s): what to launch and when,
where the carrier or the convoy goes, and an **order for each squad** (attack a target,
guard a ship, hold a point). Pilots see their order and fly to it (stage B). The page
shows:
- the mission brief at muster;
- carrier HP and convoy progress in the HUD;
- a result that says why the match ended;
- behind a **"show commands" toggle** (like "technical details"), the commander layer:
  - faint lines from each squad to its target, and markers at hold and jump points;
  - a small scrolling **command log**, a computer readout of commander activity
    ("EMBER CMD › launch 3 fighters · bay port", "AZURE CMD › strike squad → transport
    2"). It is ambient, not something you're meant to read, and tapping it opens it to
    be read.

## 2. Stages (each one ships to the live page)

### Stage A: missions on screen (scripted commander, scripted capital ships, pilot v1)

Common sim work, SIM_VERSION 4:
- **Missions** in `MatchConfig` (deathmatch, carrier battle, convoy escort), each with
  its own setup, termination, winner and time-limit tiebreak.
- **The commander interface.** On the slow tick the sim exposes a coarse commander
  observation and takes commander actions: launches, waypoints for the carrier or
  convoy, and squad orders. Orders are sim state, so they are hashed and
  deterministic.
- **Command events** for the log and the lines.
- **A higher ship cap.** Today `MAX_SHIPS` is 8; a convoy plus two fleets, or two
  carriers with wings, needs about 16–20. Browser inference is about 0.4 ms per ship,
  well inside the 33 ms tick.

The scripted commander lives in the sim crate (Rust), so the browser and training run
the same code, as with the scripted pilots. Capital ships are flown by scripts:
actuator-level like every script, with no autopilot action. The learned pilot keeps
flying the strike craft. The bundle maps carrier and transport → script.

**A1, carrier battle.**
1. **Carrier hull.** `assets/hulls/carrier/` (model.glb from Codex/sol, co-designed
   mounts per DESIGN §5). It's slow and big, with flak for point defence and two bays.
   A starting point is the story demo's carrier in `prototypes/story/hulls.js`.
2. **Hangars and launches.** A carrier holds a queue of ships that are not present yet.
   A launch makes one present at the bay mouth, moving along the bay's direction, with
   its controls locked briefly. This is the jump-in arrival path started from a bay.
3. **Scripted carrier pilot.** It flies to the commander's waypoint, and its flak
   tracks the nearest threat.
4. **Commander script.**
   - It launches reserves as the wing in space thins.
   - It splits the wing into a guard squad and a strike squad.
   - It strikes the enemy carrier, or the nearest enemy squad while the enemy escort
     is strong.

**A2, convoy escort.**
1. **Transport hull.** `assets/hulls/transport/`: unarmed or lightly armed, slow and
   tough, also from Codex/sol. Convoys are 3–5 of them.
2. **Under-way setup.** The convoy and its escort start present and moving, in
   formation along the route. The attackers use the existing jump-in arrival.
   Formation is only where they start. After that, escorts fly their own pilots, and
   stage A's pilots will peel off to fight.
3. **Jump-out.** It is a mission rule, not a pilot action. A transport that reaches the
   jump point charges briefly, then leaves the field and counts as escaped (an event).
   The defenders' jump-out at the end is drawn by the renderer when the match ends; the
   sim only needs the end event.
4. **Scripted transport pilot.** It flies the commander's route.
5. **Commander script.** The defenders get a guard squad on the convoy and an
   intercept squad. The attackers send waves, aimed at the lead or most-damaged
   transport.
6. **Win rule and clock.** The attackers win if at least half the convoy dies. The
   distance and the clock are tuned with the survey; the user leaves both open.

**Both:**
- **Web.** Render the new hulls; draw bay launches, the under-way opening and
  jump-outs; rotate missions. Add the mission brief, the HUD state, the result reason,
  and the "show commands" toggle with lines and the command log.
- **Balance.** A script-vs-script mission survey, as `tools/fleet_survey.py` does for
  fleets, for win rates, match length and time-limit rates per mission.

Pilot v1's obs has no order inputs; carriers and transports are just large ships to
it. In stage A the commander's orders steer only the scripted capital ships and the
launches, but they are logged and drawn, so the layer is visible from day one.

#### WP-S1, the stage A sim (landed on `m3-sim`, SIM_VERSION 4)

What it decided; `docs/SIM_SPEC.md` §0.2, §5.9, §5.10 and §10.3 have the detail.

- **Ship cap 8 → 20, obs unchanged.** `OBS_DIM` stays 385: a pilot sees the nearest
  7 present ships (`N_NEAR_SHIPS`, no longer `MAX_SHIPS − 1`). Training rosters pad
  to `MAX_FLEET_SHIPS = 8`, so training buffers and throughput are unchanged (4v4
  bench 2,215 steps/s before and after).
- **Pilot v1 keeps flying.** Deathmatch with up to 8 ships is bit-identical to v3:
  `v3_compat_*` replays the four v3 golden traces (kept under
  `crates/sim/tests/golden/v3/`) tick for tick. `PILOT_COMPAT_VERSIONS = [3, 4]` is
  exported to Python and WASM; the bundle (manifest `sim_version` = the wasm's,
  `pilot_sim_version` = the policy's), `export_policy`, the live page and
  `tools/champion.py watchable` accept a pilot whose version is in it. A v4 bundle of
  fleet pilot v1 passes the headless live smoke.
- **Hulls.** `carrier` (role `carrier`; story-demo numbers, collision circles
  along the spine, impact 0.5, two bays) and **`freighter`** (role `transport`).
  The user's change of 2026-10-30: the transport is a sitting duck, so the hull
  is named `freighter` (role `transport` stays the mission category, so a later
  "medical frigate" is just another transport-role hull). It is unarmed, with two
  mains and 300 N heading-hold RCS (not 1400). Its inertia is raised to 40,000 so
  that it barely turns, about 0.14 rad/s² of yaw authority. The art agent has the
  same spec. Hull ids shift (carrier sorts first); nothing keys on raw ids.
- **Missions** in `MatchConfig.mission`, with end reasons `eliminated`,
  `time_limit`, `carrier_destroyed`, `convoy_through`, `convoy_destroyed`:
  - *Deathmatch*: as v3.
  - *Carrier battle*: one carrier per team, present at tick 0 at `0.72 R`, under way at
    0.4 × its cap toward a hold point 60 m ahead; the first `jump_in` (default 2) of the
    other ships jump in, the rest start docked. Losing the carrier loses (docked ships
    die with it); time limit (default 150 s) → the higher carrier hull fraction, then
    team value, then draw.
  - *Convoy escort*: team 0's transports (1–8) start present, in two files, pointed at
    the jump point and moving at their cruise speed (0.8 × cap), with the escorts in
    pairs 45 m either side; team 1 jumps in. The route is straight, `(0, −0.55 R)` →
    `(0, +0.75 R)` (bottom to top on a phone; the attackers hit its flank), jump radius
    40 m, charge 2 s. Attackers win at `ceil(n/2)` destroyed; defenders once enough
    escaped that this cannot happen, or if every attacker is dead; at the time limit
    (default 120 s) the convoy has failed and the attackers win.
  - **Arena**: 450 m for every mission (`arena_radius_for_mission`), so pilot v1's
    obs scale is the one it trained on; both layouts fit. WP-S2 may change it there.
- **Commander layer.** Every 60 ticks: squads (at most 4 per team, a member bitmask
  over 20 slots, strike craft only) with orders `none / attack / guard / hold`,
  waypoints for carriers and transports, and launches (one reserve, from a chosen or
  the longest-ready bay; 30 m/s out of the bay mouth plus the carrier's velocity,
  0.5 s control lock, 1.5 s bay cooldown). It is all hashed. Invalid members and orders
  are sanitised; impossible launches and waypoints are refused, never panic, with every
  outcome reported. `CommanderMode::Scripted` (default) runs
  `scripted::commander::commands` inside `step`; `External` takes the caller's queued
  commands. The commander observation is a typed struct (`CommanderObs`).
- **Events** 8–12: `Launch`, `Order` (once per change per slow tick), `JumpCharge`,
  `JumpOut`, `MatchEnd`.
- **Scripts.** The **transport script is final**: it cruises the mains at 0.8 × cap
  toward the waypoint and holds heading with the RCS. It never evades and never reacts,
  and it cuts the mains within 25 m of the point. The carrier script is a first cut: it
  turns to the waypoint and burns while facing it below an approach speed that it can
  coast down from on drag (no reverse thrust). Capital ships fire their mains only for
  thrust, never to turn. Its flak uses the shared turret aim. The **stub commander**
  keeps 6 strike craft in space (one launch per bay per slow tick) and gives one squad
  of every strike craft an order to attack the nearest enemy capital ship, else the
  nearest enemy. It points transports at the jump point. Once its wing is spent, it
  sends the carrier at the enemy carrier, so a battle of attrition ends in a kill
  rather than at the clock.

Left for **WP-S2**: the real commander script (guard and strike squads, launch
timing, convoy waves), the carrier pilot's refinement (its RCS chatters while it
holds heading), the mission survey (arena, route length, clocks, `jump_in`, hangar
sizes), and any hull retune. Left for the **web**: rendering carrier and freighter,
launch streaks, the under-way opening, jump charge and jump-out, the mission rotation,
HUD and result reasons, and the commands toggle and log. The WASM API note is
SIM_SPEC §10.2.

#### WP-S2, the commander, the carrier pilot and the mission survey (`m3-sim2`)

What it decided; SIM_SPEC §0.2 ("WP-S2"), §5.9, §10.3 and §11 have the detail, and
`lab/runs/2026-10-30-mission-survey/` the numbers.

- **Still SIM_VERSION 4.** Stage A's sim had not shipped, so WP-S2 regenerated the v4
  golden traces instead of bumping: the missions' (their play changed) and the
  deathmatch ones (only the hashed command state and `Order` events changed). The
  `v3_compat_*` replays pass untouched, so pilot v1's deathmatch is still bit-identical
  to v3.
- **The scripted commander** (`scripted/commander.rs`) is stateless and uses the
  command state as its memory and hysteresis: orders change only for a clearly better
  one, squad membership only when a squad is the wrong size, and unchanged commands
  are not sent, so each `Order` event is a real change (tested: at most one order
  change per squad per three slow ticks). Carrier battle: paced launches (3 in space
  + 1 per 30 s, at most one per 12 s; scramble per bay when threatened; empty the
  hangar in the last 60 s), a **guard** squad (⅓ of the wing, ½ when threatened) and
  a **strike** squad (the enemy carrier, or the nearest enemy strike craft while the
  carrier's escort outnumbers it); carrier waypoint: patrol its own side, retreat from
  threats, close to 170 m (flak range) when winning or in the last 60 s, the enemy
  carrier itself when its wing is spent. Convoy: defenders **guard** the most threatened transport
  and **intercept** the enemy nearest the convoy; attackers send **two waves** at the
  transport scoring highest on progress + damage, wave 2 staging ahead of the convoy
  until wave 1 is halved or 30 s. Deathmatch: two squads (nearest, most damaged).
- **Scripted strike craft follow orders** (`scripted/orders.rs`: attack with
  self-defence, guard and hold with station keeping), except under a *scripted*
  deathmatch commander, whose orders are only shown. Decision: that keeps the default
  deathmatch (fleet pilot v1's eval opponent and training teacher) and the v3 traces
  unchanged, while an external commander's orders are followed in every mission, as
  stage B's random-order training needs.
- **Carrier pilot.** Hull retune without moving a mount: mains 7000 → 300 N, RCS 3500
  → 450 N, cap 10 → 8 m/s (≈ 1.5 m/s² and 0.15 rad/s², a 90° turn in ≈ 20 s), hp 1500
  → 1000. It brakes on drag only (no flip-and-burn: at its turn rate a flip takes
  longer than coasting down). A turn-rate profile plus an RCS on/off hysteresis band
  replaced the PD, so it no longer chatters holding heading (tested: ≤ 3 burns and
  ≥ 15 ticks between them after a knock). Its flak tracks the nearest enemy strike
  craft before any capital ship.
- **Balance** (live configuration: pilot v1 on every strike craft, scripts on the
  capital ships). Freighter hp 500 → 400 and cap 14 → 10.5 m/s (the route takes
  ≈ 68 s instead of 54: with the old numbers the convoy got through 95 % of the time);
  arena (450 m), route, clocks (150 s, 120 s) and `jump_in` (2) unchanged. Default
  rosters (`mission::default_rosters`, SIM_SPEC §10.3; PyO3 `rlf_sim.mission_rosters`,
  WASM `missionRostersJson`): carrier + 8, 6 or 9 strike craft a side; 4 freighters +
  3 escorts v 6, 3 + 4 v 5, 5 + 4 v 8.
- **Left open.** The script-vs-script convoy is lopsided per roster (the scripted
  escorts lose the 4-freighter roster every time and win the 3-freighter one), which
  matters only when the scripts teach stage B; carrier launches are front-loaded
  (median ≈ 28 s, p90 ≈ 60 s) because pilot v1's dogfights burn through a wing fast.

#### WP-W, the live page (`m3-web`)

- **Rotation and rosters** (`web/src/live/missions.ts`): deathmatch → carrier battle →
  convoy, by match seed; `?mission=deathmatch|carrier|convoy` pins one (`?fleets=`
  implies deathmatch). Mission rosters are the sim's (`missionRostersJson`): the
  default half the time, an alternative otherwise; strike craft an older champion
  cannot fly are swapped for one it can. Mission parameters (arena, clock, route,
  thresholds) are read back from the sim, never set by the page.
- **Who flies what.** The policy flies role-0 ships; carriers and freighters take
  `scripted_action`. The commanders run inside `step`.
- **Effects.** `Launch` → `fx.bayLaunch` (the launched ship's real length and
  velocity), `JumpCharge` → `fx.jumpCharge` (cancelled on death), `JumpOut` →
  `fx.jumpOut` and the hull is pulled out and hidden; when the escort wins a convoy
  its remaining ships `fx.jumpOutQuick`, staggered, freighters first. Docked ships
  are not drawn and not framed.
- **Camera.** It looks along the match's main axis: sim +x as before, or the convoy's
  route, so the route runs up a phone's long side and left to right on desktop. The
  convoy's camera looks 110 m down the route ahead of the lead freighter and takes in
  the jump point once the lead is within 230 m.
- **The jump point is always marked** in a convoy (ring and a DOM "JUMP POINT" label,
  which survives a bright backdrop planet); the squad lines, attack/guard/hold
  markers, carrier waypoints and the line from the convoy to the jump point are behind
  "Show commands" (localStorage `rlf.live.showCommands`, `?commands=1|0`).
- **HUD.** Objective-first muster (headline, brief, cards grouped by hull when a side
  has more than four ships); a mission panel (each carrier's hull and hangar; the
  convoy's pips, escaped against the sim's `to_escape`, kills against `to_destroy`,
  metres to the jump); the result line says why ("Ember's carrier destroyed",
  "Convoy through — 3 of 4 escaped", "Time limit — …"). Command log: three faint
  lines collapsed, tap for the full log with times and squad sizes.
- **Renderer numbers.** The bundle catalogue now carries each hull's YAML geometry
  (`info[hull].geometry`); the live page lays it over `render/hulls.js` (mounts, bays,
  collision radius, shield radius, hp, cap), and `hulls.js` itself was aligned with
  the YAML for the hull turntable and the art preview.

### Stage B: orders reach the pilots (the feudal layer)

1. **Order block in the pilot obs:** order kind (none, attack, guard, hold) and the
   target's relative position and velocity, in the body frame. `OBS_DIM` 385 → about
   397. This needs a new obs layout, so a new sim season.
2. **Warm start with zero-initialised order inputs.** At update 0 the new pilot is
   exactly fleet pilot v1.
3. **Order reward**, small next to the team reward (DESIGN §7):
   - attack: damage dealt to the target;
   - guard: staying within range of the ward, plus damage to ships near it;
   - hold: time inside the hold radius.
4. **Training on random orders** as well as the scripted commander's, so pilots follow
   any order, across all three missions.
5. **The learned pilot takes over the carrier** (user's choice), and the transports if
   the run supports it. The scripts stay as their teachers and as the fallback.
6. **Gates, fixed in the run's plan before any eval:**
   - order-following per order kind, against the same pilot with orders blanked;
   - mission win rate against v1 pilots under the same commander;
   - no loss of deathmatch strength;
   - time-limit and stalemate rates.

   Engine duty is reported, not gated. There are no duel gates.

#### Stage B decisions (team lead with Fable as design partner, 2026-10-30 evening)

The outline above stands except where this list changes it. Two work packages run in
parallel against the interface below; the run follows.

- **Split: stage B is strike craft only; the learned carrier moves to stage B′.** It is a
  separate short run (BC on capital rows from their scripts, a KL anchor to the stage B
  pilot on strike rows; it decides shared net vs a small capital net with data). Why: the
  carrier's control timescales are 50–100× a fighter's, a wobbling carrier is the
  biggest thing on screen, it would confound the mission gates, and a policy carrier
  that follows waypoints looks the same as the script. The user's choice (a learned
  carrier) is kept, just one run later. Item 5 above moves to B′.
- **SIM_VERSION 5, order block appended at the end of the obs.** `OBS_DIM` 385 → 403;
  the first 385 floats are exactly v4's, so v3/v4 pilots run on `obs[..., :385]` (frozen
  v1 opponents, older bundles on the live page). Block `order`, 18 floats, body frame,
  clamped like the rest:
  `0` has_order · `1–3` kind one-hot attack/guard/hold · `4–5` target point rel pos / R
  (attack: the target; guard: the ward; hold: the point) · `6–7` target point vel −
  own vel, body, / VS (hold: −own vel) · `8` signed (dist − radius) / R · `9` radius / R ·
  `10` target hp fraction (0 for hold) · `11` target bound radius / L (0 for hold) ·
  `12–13` sin/cos of the target's heading relative to own (0 for hold) · `14` ticks
  since this ship's order last changed / 300, clamped to 1 · `15–17` mission one-hot
  (deathmatch, carrier battle, convoy). Radii: hold = its order radius; guard =
  `GUARD_PRESENCE = 90 m` + the ward's bound radius; attack = 0. Capital ships' obs get
  their waypoint as a hold (radius 25 m) for B′. Pilots see their squad's order in
  every mission, including the advisory deathmatch orders the scripts ignore.
- **Order reward, a separate buffer `order_rewards[N,S]`** (Python weights it by `w`),
  named consts in `reward.rs`. An *order instance* starts whenever a ship's order kind,
  target or point changes (per ship, hashed state: start tick, arrived flag, presence
  ticks used, last Φ):
  - attack: `+0.01·hull + 0.005·shield` damage dealt to the ordered target, at landing
    (no retroactive credit: flight time is short next to GAE's horizon);
  - guard and hold: potential shaping `γΦ′ − Φ`, `Φ = −K·max(0, d − radius)/R`, `K =
    1.0`, Φ reset at a new instance (no reward for the jump); a one-shot **arrival
    bonus** `+0.1` the first time inside the radius per instance; **capped presence**
    `+0.0003`/tick inside, for at most 300 ticks per instance (≤ 0.09);
  - guard also `+0.01·hull + 0.005·shield` damage dealt to enemies within
    `GUARD_RADIUS` (180 m) + bound of the ward.
  Why capped: an uncapped presence term under the scripted commander's carrier guard
  pays more than winning, and v1 already coasts.
- **`CommanderMode::Random`** (Rust, its own rng stream): the script's logistics
  (launches, waypoints), random squads and orders: every 3–8 slow ticks a squad draws
  a kind uniformly from none/attack/guard/hold and a valid target (an active enemy; an
  own ship, capitals included; a point within 0.7 R, radius 70–150 m); about 15 % of
  strike craft unassigned. Scripted pilots follow it, like an external commander.
- **Training rosters pad to 12 ships** (`MAX_TRAIN_SHIPS`; live rosters go to 18).
  Training missions: carrier + 4–5 strike craft a side (2 jump in); convoy 3–4
  freighters + 2–3 escorts v 4–5. Evals also run the live default rosters.
- **The run:** init = v1 with the 18 new input columns (actor and critic) zeroed, so
  update 0 is exactly v1. 400 PPO updates, checkpoints every 50 with gate evals on
  each. Env mix deathmatch 0.4 / carrier 0.3 / convoy 0.3; commander scripted 0.5 /
  random 0.5 per team. Opponents: order-following scripts ≥ 40 %, self-play, frozen v1
  on `obs[..., :385]`. No β pull toward strike scripts; a **KL anchor to v1 on rows with
  `has_order = 0`** keeps unordered behaviour. **Arms: `w = 1` and `w = 0.3`.**
- **Gates** (the run's plan fixes the numbers before any eval; baselines measured
  first: v1 and script-vs-script time-limit and stalemate rates per mission):
  - following, per kind, against **v1 on `obs[:385]`** (primary) and the pilot with the
    block zeroed (secondary), under the random commander *and* the scripted one in
    missions: attack — time to close (order to inside gun range, median ≤ 150 ticks for
    targets under 250 m) and damage share on the target; guard — time within 90 m +
    bound of the ward; hold — time inside the radius; **order-change response time**
    (order to the nose within 30° of the target point, median ≤ 90 ticks);
  - missions: win vs v1 pilots under the scripted commander (n ≥ 512 per mission);
  - deathmatch: `fleet_v1` win vs script ≥ 0.85 and vs v1 ≥ 0.45 (advisory orders
    may cost a little: named, not excused);
  - health: time-limit and stalemate rates against the measured baselines, NaN or stuck
    ≤ 1 %, outside arena ≤ 0.02. Reported: engine duty per hull *and per order kind*
    (the direct readout of farming), passes, length.

#### Stage B3: orders redesigned (user, team lead and Fable, 2026-10-31)

Run 1 (`lab/runs/2026-10-31-order-pilot/results.md`) made a strong mission pilot that
barely followed orders; B2b (`…-b2b/results.md`) followed them at the teacher's level
and lost every carrier battle, because the script pull overwrote combat flying. The
review that followed changes the orders, the obs and the recipe. Where this list and
"Stage B decisions" disagree, this list wins.

**Orders (SIM_VERSION 6): attack, defend, go-to, none.** Hold is gone; return to carrier
waits for docking (Later).
- *Attack* `target`: unchanged. Damage to the target pays `0.01·hull + 0.005·shield` on
  top of the team reward.
- *Defend* `ward` (was guard): **no location reward.** Pays `0.01·hull + 0.005·shield`
  for damage dealt to the ward's **threat set**, and every defender of the ward pays
  `−0.5 ×` the ward's hull fraction lost each tick, and `−0.3` once if it dies (shared,
  not split; fractions, so a freighter and a carrier weigh the same). Threat set: enemies
  within *their own* longest weapon range + 40 m + the ward's bound radius of the ward,
  or that damaged the ward in the last 150 ticks (a per-ship "last hit by" record,
  hashed). No fixed guard radius: a gunship's torpedo (340 m) outranges the old 180 m.
  Both ward terms use each defender's *standing* order on the step the damage lands (the
  effective order is already none on the tick the ward dies). Docked reserves are not
  earning and pay nothing.
- *Go-to* `point` (replaces hold): potential shaping as now (nets zero), arrival bonus
  `0.2`, no presence term. **Completes per ship on arrival** (inside the radius): from
  then on that ship's effective order is none (obs `has_order = 0`, no order reward),
  while the squad's standing order lasts until the commander changes it. A re-issued
  point within 40 m of the last go-to point is the same instance and pays nothing twice
  (else re-staging a screen farms 0.2 a slow tick); gates.md reports arrivals per minute. Capital ships' waypoints
  read as go-to (radius 25 m), completing per waypoint.
- Order block layout unchanged (18 floats), kind one-hot read as attack/defend/go-to.
  Feature 9 (radius) is 0 for attack and defend, the arrival radius for go-to.

**Obs: what a pilot needs to judge threats.** The first 403 floats stay exactly v5's
(frozen v1 runs on `[:385]`, run 1's w1_400 on `[:403]`, both exact). Two tail blocks:
- `ship_extras`, one record per existing ship slot (the 7 nearest self, same order):
  hull-class one-hot (fixed order, 6 slots: fighter, strafer, gunship, carrier,
  freighter, spare), longest weapon range / R, distance from that ship to my order point
  (target, ward or go-to point) / R (0 without an order), is my order's target or ward,
  damaged my ward in the last 150 ticks. 10 floats × 7.
- `order_ships`: the **5 ships nearest my order point** (ward, attack target or go-to
  point; allies and enemies; excluding self and the order's own ship, already in the
  order block), each as the 12-float ship record (relative to self) + the 10
  extras. All zero without an order. 22 floats × 5. Why a second block and not
  re-selecting the 7 slots by the ward: the v5 prefix stays exact for every pilot, and a
  defender still sees what is near itself.
- `OBS_DIM` 403 → 583. The browser actor's first layer grows to 583 × 256; fine on a
  phone (WP checks the JS inference time at 18 ships).

**Teachers (`scripted/orders.rs`).** The scripted defender engages its ward's threat
set (recent hitters of the ward first, then nearest the ward), and stations near the
ward only when the set is empty. Go-to: fly to the point; after arrival the script falls
back to its role. The **scripted commander** issues go-to where it issued hold (convoy
flank screen, attacker wave 2's staging point) and defend where it issued guard. Waves
that used to wait at a hold now fight on arrival, so the mission balance must be
re-measured (survey: carrier battles 98 % carrier kill and about 50/50, convoy attackers
win 52–62 % on every default roster); the WP retunes the commander's timing (e.g. issue
wave 2's go-to later) if it drifts out.

**Random commander:** kinds none/attack/defend/go-to; go-to points drawn near the
action as in B2b (20 % far); defend wards: a capital ship when the team has one, 50 %,
else any own ship.

**The run (`lab/runs/2026-11-01-order-pilot-b3`):**
- Init: run 1's **w1_400** (the best mission pilot), first-layer columns for the 180
  new inputs zeroed, so update 0 is exactly w1_400.
- KL anchor on `has_order = 0` rows to **w1_400** on `obs[:403]` (it is stronger than v1
  in missions and plays v1's deathmatch); frozen pool: v1 and w1_400.
- **The script pull only on transit rows**: a go-to not yet arrived, or a defend whose
  threat set is empty. **Attack rows are never pulled** (closing through an enemy's guns
  is where v1's evasive flying lives, and it is what B2b destroyed; attack already
  closes in 92–100 ticks). Never on combat rows. Movement heads only.
- **The new first-layer columns (actor and critic) get their own parameter group at
  10× the LR**, in both arms: run 1 showed 400 updates at 1e-4 barely move zeroed
  columns. The fleet critic reads all 583 inputs, its new columns zeroed too.
- **Arms: `transit` (β 0.05 → 0 over updates 30–300) and `reward` (β 0).** The second
  says whether the new rewards and inputs are enough on their own. 300–400 updates,
  checkpoints every 50.
- Order reward weight `w = 1`.

**Gates (the run's plan fixes the numbers before any eval; per order, on the same
definitions as the reward):**
- O, under the random commander, against the same pilot **with its order hidden by the
  sim** (no order block, no `order_ships`, no order extras; not zeroed floats only): a
  per-team obs flag in the match config, so followed and hidden runs are the same
  matches with paired seeds, each pilot evaluated as both teams. Instances cut short by
  death, a new order or the match end are censored (excluded), not counted either way.
  Go-to near and far draws are reported separately (only far ones test following against
  the fight). Defend needs ≥ 300 defended ward-minutes per candidate (one torpedo volley
  is 55 hp). Expect the defend threat-set share to saturate late in carrier battles
  (380 m reach in a 450 m arena); the teacher-first rule below covers it.
  attack: median time to gun range ≤ 150 ticks (targets under 250 m out), damage share
  on target ≥ hidden + 0.05; defend: ward hull lost per defended minute ≤ 0.8 × hidden,
  and share of the defender's damage on the threat set ≥ hidden + 0.05; go-to: ≥ 0.7 of
  instances arrive within 1.5 × (straight-line distance / speed cap + 60 ticks). The
  teacher is measured first; a bound it cannot meet is set from it before any candidate
  is evaluated, and the plan says so.
- M: mission win vs v1 as now (each ≥ 0.47, mean ≥ 0.52) **and** mean vs w1_400 ≥ 0.45.
- D and H as in run 1.
- Pick: among candidates that pass everything, the highest mean mission win vs v1.

**Work packages.** WP-B3-sim (Rust, bindings, goldens with v5 compat, SIM_SPEC, scripted
commander and teachers, mission balance re-measure, web overlay labels, a transit-row
mask for Python) and WP-B3-train (widening to 583, anchor on `[:403]`, transit-row pull,
the eval's hidden-order mode and defend/go-to metrics, gates, run dir), in parallel
against the interface above; the run follows.

### Later (not M3)

- Docking and repair, flown by the pilot (the story demo's return-to-bay).
- A supply economy.
- Retreat as an order.
- A learned commander (its own PPO at the slow tick).
- Commander and pilot diversity.

## 3. Decisions (user, 2026-10-30)

1. **The escort protects a convoy of 3–5 transports**, not the carrier: a new
   transport hull.
2. **The carrier is scripted in stage A, and learned in stage B.**
3. **Commands are shown behind a toggle:** light lines plus a small scrolling command
   log, ambient, that can be tapped to read.
4. **The escort is point to point**, opening with the convoy under way and its escort
   in formation. The attackers jump in, and the convoy and then the defenders jump out
   at the end. Length and clock are to be tuned. Parts of the opening and the jump-out
   may be postponed if they prove costly, but this is the target.

## 4. Order of work

1. In parallel: the carrier and transport hulls (Codex/sol art, co-designed YAML).
2. In parallel: the stage A sim (missions, the commander interface, launches, the
   under-way setup, jump-out, the ship cap, both scripts and the commander script,
   with Rust tests and golden traces).
3. Bindings (PyO3 and WASM).
4. Mission survey and balance.
5. Web: hulls, effects, HUD, the commands toggle and log.
6. Deploy A1 (carrier battle) as soon as it stands, then A2 (convoy escort).
7. Then the stage B plan for the run, the training run, gates, promotion and deploy.
