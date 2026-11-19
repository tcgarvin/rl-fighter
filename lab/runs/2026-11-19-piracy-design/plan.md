# Piracy: a mission about stealing cargo

Nothing here is built. This note proposes a fifth mission, piracy, in which one side
steals cargo instead of destroying ships. Pirates shoot a freighter until
it stops, keep a ship beside it long enough to take the cargo, then fly the cargo out
through a jump point. The aim is a mission where a commander's orders are worth giving.
This week's measurements say a fleet fight is not one: an attack order costs a side 0.37
of a 3 v 3 ([order kinds](../2026-11-19-order-kinds/results.md)), and no commander we
have gains anything over giving no orders ([pairing](../2026-11-19-pairing/results.md)).
The same measurements say a go-to is nearly free. Piracy is built out of go-tos.

<!-- summary: A design for a fifth mission, piracy: pirates stop a freighter, hold a ship beside it to take its cargo, and fly the cargo out through a jump point. It is built from go-to orders, which we measured to be cheap, and it gives a commander facts its pilots cannot see. Nothing is built yet. -->

## The rules

Team 0 hauls and team 1 raids. The arena is 450 m and the clock 120 s.

- **Lanes.** Three freighters, each on its own lane to its own jump point, about 50 s
  to cross. Lanes are 260 m apart, further than any gun reaches (230 m), so a ship
  covers one lane. Four escorts (F S F G) face five pirates (F F S G F).
- **Disabled.** A freighter whose hull falls to 35% is disabled. Its script brakes it to
  rest, it cannot jump, and it takes no more damage. Freighters are never destroyed.
- **Boarding.** A pirate strike craft that stays within 60 m of a disabled freighter for
  5 s takes its cargo. The count stops while an escort is inside the same 60 m, and
  resets if the pirate leaves.
- **Cargo is mass.** The ship carrying it has 50% more mass and 0.75 of its speed cap.
- **Escape.** Two exits on the pirates' edge. A loaded ship inside an exit's 40 m circle
  charges for 2 s and jumps out, by the convoy's jump rule. That cargo is stolen. If
  the ship is killed first, the cargo is saved.
- **Ends.** Pirates win at 2 cargoes stolen (`CargoStolen`). Haulers win at 2 saved (a
  freighter jumped out, or its cargo's carrier killed: `RaidRepelled`), with every
  pirate dead, or on the clock. The clock is the haulers', as it is the station's.

No rule moves a ship. Boarding is where a pilot's own thrusters keep it for 5 s.

## Why orders should pay here

In a fleet fight an attack order tells a pilot nothing it could not see, and makes it
charge. Here an order carries facts the pilot does not have.

- **A pilot sees its 7 nearest ships.** The other lanes are outside its view, and so
  are the hull to board and the exit. The commander sees all 20 slots, and a go-to puts
  the point in the pilot's order block.
- **The verbs are the cheap ones.** A go-to cost 0.08, a deadline added nothing, and
  the pilot is free on arrival. Blocking a boarding is presence, and holding back wins
  gunship fights by 0.17 to 0.29 and loses fighter fights by 0.34 to 0.47. So the
  gunship sits on the stopped freighter and the fighters go forward.
- **One attack order may be worth giving:** on the loaded ship. It is slow and running,
  so charging it is right.
- **The decision is allocation.** Three lanes, and escorts enough to hold two. Pirates
  choose where to concentrate and which exit. Haulers choose which lane to give up, and
  whether to contest the hull or block the exit.

## What a pilot has to learn

- **Hold.** A go-to ends on arrival and the pilot then flies free, which in a fight means
  falling back. Defenders sit 130 to 180 m from their ward, and a fighter crosses the
  ring in 2 s. Five seconds inside 60 m, under fire, is new.
- **Escape.** A go-to with a deadline is already drilled (SIM_VERSION 8), but alone and
  light. This one is heavy and chased.

## How it maps onto the inputs

No input changes for stages 1 to 3. The mission reads as a convoy escort, as the station
assault can. `OBS_DIM` stays 587 and `COMMANDER_IO_VERSION` 1.

| Fact | Where the nets read it |
|---|---|
| Mission | Pilot one-hot index 2; commander role 2 (haulers), 3 (pirates) |
| Score | Commander globals 13-17: saved, stolen, needed of each, charging |
| Disabled | A freighter at rest with hull 0.35 (ship record; entity 14) |
| I carry cargo | Own mass and speed cap (self 13, 14) |
| Who carries | It stays in its freighter's threat set: entity 36; pilot extras 9 under a defend on that freighter |
| Board here, exit there | The go-to point. Exits sit on commander map points |

**The gap.** The learned commander's go-to names one of 25 map points, and a stopped
freighter can be anywhere. Its only way to say "board that one" is an attack order on
the freighter. Whether a pilot under that order stays within 60 m is a stage 2 question.
Hand rules use the external commander, which takes any point.

**What a bump would cost.** For pilots, about four floats appended (carrying, boarding
progress, bearing to the exit): `OBS_DIM` 591. Old pilots would still fly on their
prefix, as the 583-input ones do today, but blind to the new facts. Each of the ten
needs a widening fine-tune, a new export and a parity check. For commanders there is no
prefix: every `c1_*` retrains from nothing. That is the cheaper loss, since none of them
earns its orders. Decide at stage 4, knowing what pilots failed to learn blind.

## Sim pieces (SIM_VERSION 10)

- **Mission** kind 4, `piracy`, with the numbers above as its fields.
- **State**, hashed only in a piracy match so every v9 trace replays: per freighter,
  disabled and where its cargo is (aboard, carried by a slot, stolen, saved); per
  pirate, boarding ticks.
- **Events:** `Disabled`, `Boarded`, `CargoSaved`; `JumpCharge` and `JumpOut` reused.
  End reasons 8 and 9.
- **Scripts.** A scripted pilot sent to a stopped hull holds inside the ring, and a
  loaded one flies to its exit. Commander arms: pirates take the lanes with fewest
  escorts; haulers park the gunship and attack the carrier.
- **Bindings:** a fifth `mission_weights` entry (0 by default), drill kinds `board` and
  `run`, WASM.

## Stages and bars

1. **Sim and script balance.** 512 matches, script against script. Bars: pirates win
   0.45 to 0.55; under 10% end on the clock; a "concentrate" pirate arm differs from a
   "split" one by 0.10. If allocation does not matter to the script, there is nothing
   to command.
2. **Pilots zero-shot.** The live ten under the scripted commander, and with each side's
   orders hidden. No bar: this is the baseline. Record disables, time in the ring
   (after a go-to, and under an attack order on the hull), boardings and escapes.
   Prediction: pirates with no orders steal under 0.1 cargoes a match.
3. **Hand-rule commander.** Rules in Python through the external commander: go-tos and
   the one attack. 576 paired matches a row (± 0.04), with `followers_school_1052` and
   with the live draw. Bars, for each role: the rules beat no orders by 0.10, and beat
   **naive orders** (a random lane, a random exit) by 0.10. `f995_701`, which ignores
   orders, should gain nothing. If the bars fail, fix the rules or the pilots. Do not
   train a commander on it.
4. **Training.** Pilots first: board and run drills, mission weight 0.15 to 0.2, two
   seeds an arm. Bars: board drill 0.7; the old missions and the `nearest` against `none`
   test no worse than noise. Then a commander phase: the learned commander matches the
   hand rules. Then the live page.

## Risks

- **Won by construction.** A pilot with no orders cannot know where the exit is, so
  "orders beat none" is partly a rule. The naive-orders bar is the real test.
- **Holding may not emerge.** SIM_VERSION 5 paid for presence and got parking. Pay for
  the cargo, never for time in the ring. The levers are ring size and boarding time.
- **It turns into a deathmatch.** Pirates kill the escorts, then loot. The 50 s crossing
  is the guard. Measure the share of cargoes taken while escorts live.
- **The convoy reading leaks.** Convoy attackers learned to destroy freighters. Watch
  convoy scores during the fine-tune.
- **Mass is a faint signal** that a ship is loaded.
