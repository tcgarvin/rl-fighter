# M3 — Carriers, convoys and commanders (plan, 2026-10-30)

Status: **agreed in outline** (the user's answers of 2026-10-30 are in §3), not started.
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
