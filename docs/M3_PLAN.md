# M3 — Carriers and commanders (plan, 2026-10-30, draft for review)

Status: **draft**. Asked for by the user on 2026-10-30, after fleet pilot v1: team
deathmatch works, duels are dull, and the story needs the carrier and the layered
("feudal") AI on the live page, with matches that have different goals, escort among
them. A scripted or stub commander is fine. This pulls DESIGN §12's M5 (flagships, bays,
a scripted commander, goal-conditioned orders) ahead of the attention policy, the league
and the nightly lab, which move back one milestone each.

Deferred on purpose (user, 2026-10-30): pilot diversity (several policies or styles on
one hull type). Two identical commanders may well produce the same symmetry problem the
duels had; we deal with that when we see it.

## 1. Done when

The live page rotates through three missions, every one readable without explanation:

- **Team deathmatch.** As today, 2–4 ships a side (no duels).
- **Carrier battle.** Each side has a carrier that launches its air wing from its bays
  over the match. Losing your carrier loses the match.
- **Escort.** One side's carrier must reach a jump point across the arena and jump
  out. Its wing escorts it. The other side has no carrier, but a larger strike force
  that arrives in waves, and wins by killing the carrier or running out the clock.

A **commander** per side decides on a slow tick (every 2 s): what to launch and when,
where the carrier goes, and an **order for each squad** (attack a target, guard a ship,
hold a point). Pilots see their order and fly to it. The page shows the layer:
- the mission brief at muster;
- the orders as lines and markers, kept light;
- carrier HP and escort progress in the HUD;
- a result that says why the match ended.

## 2. Stages (each one ships to the live page)

### Stage A: the carrier on screen (scripted commander, today's pilots)

1. **Carrier hull.** `assets/hulls/carrier/` (model.glb from Codex/sol, co-designed
   mounts per DESIGN §5). It's slow and big, with flak turrets for point defence and
   two bays. A starting point is the story demo's carrier in
   `prototypes/story/hulls.js`.
2. **Sim, SIM_VERSION 4:**
   - **Hangars and launches.** A carrier holds a queue of ships that are not present
     yet. A launch makes one present at the bay mouth, already moving along the bay's
     direction, with its controls locked briefly. This is the arrival path that
     already exists, started from a bay instead of a jump-in.
   - **A flagship flag**, and **missions** in `MatchConfig`: deathmatch, carrier
     battle, and escort (jump point, radius, hold time). Each sets its own termination,
     winner and time-limit tiebreak.
   - **The commander interface.** On the slow tick the sim exposes a coarse commander
     observation and takes commander actions: launches, the carrier's waypoint and
     squad orders. Orders are sim state, so they are hashed and deterministic.
3. **Scripted carrier pilot (Rust).** It's actuator-level like every script, with no
   autopilot action. It flies the carrier to the commander's waypoint and its flak
   tracks the nearest threat. The learned pilot does not fly carriers, so the bundle
   maps carrier → script.
4. **Scripted commander (Rust, in the sim crate).** The browser and training run the
   same code, as with the scripted pilots:
   - It launches reserves when the wing in space thins out.
   - It splits the wing into a guard squad on the carrier and a strike squad.
   - It sends the strike squad at the enemy carrier, or at the nearest enemy squad when
     the carrier's escort is strong.
   - In escort it steers the carrier toward the jump point.

   In stage A, orders change only launches and the carrier's course. Pilots don't see
   them yet and fight the nearest enemy, as today.
5. **Web.** Render the carrier and bay launches (a short streak out of the bay mouth),
   and rotate missions. Add the mission brief to the muster, carrier and escort state
   to the HUD, and the reason to the result screen.
6. **Balance.** A script-vs-script mission survey, as `tools/fleet_survey.py` does for
   fleets, so neither escort side wins nearly always.

The stage A live page has carriers, launches and three missions, with pilot v1 flying
the strike craft unchanged. Pilot v1's obs has no order or carrier-specific inputs; a
carrier is just a big enemy ship to it.

### Stage B: orders reach the pilots (the feudal layer)

1. **Order block in the pilot obs:** order kind (none, attack, guard, hold) and the
   target's relative position and velocity, in the body frame. `OBS_DIM` 385 → about
   397.
2. **Warm start with zero-initialised order inputs.** At update 0 the new pilot is
   exactly fleet pilot v1, so the run starts from a pilot that already fights well.
3. **Order reward**, small next to the team reward (DESIGN §7):
   - attack: damage dealt to the target;
   - guard: staying within range of the ward, plus damage to ships near it;
   - hold: time inside the hold radius.
4. **Training missions.** Pilots train on random orders as well as the scripted
   commander's, so they follow any order. Training uses all three missions.
5. **Gates, fixed in the run's plan before any eval:**
   - order-following per order kind, against the same pilot with orders blanked;
   - mission win rate against v1 pilots under the same commander;
   - no loss of deathmatch strength;
   - time-limit and stalemate rates.

   Engine duty is reported, not gated. There are no duel gates.

The stage B live page draws the commander's orders and shows the ships obeying them.

### Later (not M3)

- Docking and repair, flown by the pilot (the story demo's return-to-bay).
- A supply economy.
- Retreat as an order.
- A learned commander (its own PPO at the slow tick).
- Commander diversity.

## 3. Decisions for review

1. **Escort shape.** The proposal escorts the carrier itself, so one new hull serves
   both new missions, and the attackers have no carrier. The alternative is a separate
   unarmed transport, which means more art and a fourth hull.
2. **Who flies the carrier.** The proposal is a script for now. The learned pilot
   would need a carrier block in its obs and training to fly something that slow and
   heavy.
3. **How much of the commander to draw.** The proposal is a thin line from each squad
   to its target and a marker at hold points, with a toggle to hide them.
   DESIGN §13 leaves this open.
4. **Arena and clock for escort.** At the story carrier's 10 m/s, crossing 900 m
   takes 90 s. The proposal is a larger arena for carrier missions with a 150 s
   limit. That makes episodes longer, so training costs more per sample.

## 4. Order of work

Stage A sim (bays, missions, the commander interface, both scripts, with Rust tests and
golden traces) → the carrier hull and art, in parallel with the sim → bindings (PyO3 and
WASM) → mission survey and balance → web → deploy. Then the stage B plan for the run,
the training run, gates, promotion and deploy.
