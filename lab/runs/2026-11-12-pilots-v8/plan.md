# Pilots on v8: go-to orders with a deadline

Prepared 2026-11-12. The pilots' turn in the loop, and the first night on `SIM_VERSION` 8.

## Why

Commander training is stuck because orders do not change who wins: most pilots do not
follow them. Go-to is the worst (night 4: `followers_1793` arrives in time 0.39,
`fighters_1832` 0.26), and more of the same drill has not moved it since night 2.

## What a diagnostic found (2026-11-12 morning)

256 go-to drills per pilot, every ship's path traced, the clock run 20 s past the
deadline to see late arrivals. Ships not killed before their deadline:

| Pilot | In time | Near miss | At the enemy instead |
|---|---|---|---|
| Script | 0.98 | 0.01 | 0.01 |
| `transit_300` | 0.64 | 0.26 | 0.10 |
| `followers_513` | 0.56 | 0.31 | 0.12 |
| `followers_1793` | 0.32 | 0.35 | 0.31 |
| `fighters_1832` | 0.28 | 0.25 | 0.46 |
| `fighters_pay1_1317` | 0.16 | 0.23 | 0.59 |
| `f995_701` | 0.20 | 0.23 | 0.57 |

Near miss: within 60 m of the circle before the deadline, not inside in time. At the
enemy instead: never that close, and within 150 m of an enemy or all of them dead.

- **Pilots read the order.** In the first 5 s `followers_1793` closes 66 m on the point
  with the order shown and −3 m with it hidden (script 96 m). `f995_701` does not react
  (39 m against 35 m); its child `fighters_1832` does (46 m against −15 m).
- **No learned pilot finishes reliably**, `transit_300` included. With one idle enemy
  parked far away, `followers_1793` ships that got within 60 m entered a 15 to 35 m
  circle in time 38% of the time and a 60 to 80 m one 65% (script 99%).
- **The `followers` decline is kill-first:** "at the enemy instead" rose 0.12 to 0.31
  from `followers_513` to `followers_1793`; near misses stayed flat. A lone pilot flies
  about 500 m to a harmless parked enemy, kills it, then flies straight to the point at
  top speed (alone: in time 0.14; in a squad 0.44).
- **Being shot at is not the cause:** in time 0.32 with hostile enemies, 0.37 with the
  same enemies idle, 0.42 with one parked far away.

Read from the pay code, not tested: a fighter kill pays 0.8 and arriving 0.2; go-to pay
is the same whenever the ship goes, so nothing paid for being prompt; the deadline was
only in the eval. Pilots can see the match's time left, and the drill's clock ended one
second after the deadline, so they may have timed themselves by it (222 in-time arrivals
fell to 194 with 20 s more clock; one run, within noise).

## What changed (owner's decision, 2026-11-12)

A go-to can carry a deadline, the pilot sees the time left, and pay is strict at the
deadline and free before it, so a low-urgency order leaves time to land hits on the way.
Details in `docs/SIM_SPEC.md` (v8) and `docs/PILOT_TRAINING.md` section 2.

- **Sim v8.** The order carries a deadline tick (none allowed). In time pays 1.0 (0.2
  without a deadline), a miss costs 1.0 once and the order is then spent. Four new
  inputs, 583 to 587: has a deadline, time left, urgency, closeness over the last 100 m.
  With no deadline issued v8 flies exactly as v7. No commander issues one yet.
- **Go-to drills.** Three in four carry a deadline, at 2 to 8 times the squad's
  straight-line time plus 3 s (1.5 was more than a lone script ship could make a quarter
  of the time). The drill's clock ends 1 to 20 s after the deadline, so the match clock
  no longer marks it; a weaker hint remains (the share of the match left when the
  deadline falls is 0.21 at the median).
- **Deadline sweep** (`spacefight.eval.goto_sweep`): one ship, set distances, each hull,
  three levels of opposition, the same starts replayed at each time allowance under the
  same clock, so only the order tells the levels apart.

## Baseline on the sweep (2026-11-12)

One ship alone, 324 starts. In time, of ships alive at the deadline. These pilots cannot
see the deadline; the script flies straight there.

| Pilot | Slack 1.5 | 2 | 3 | 5 | 8 | No deadline |
|---|---|---|---|---|---|---|
| Script | 0.76 | 0.96 | 1.00 | 1.00 | 1.00 | 1.00 |
| `followers_1793` | 0.05 | 0.08 | 0.21 | 0.46 | 0.66 | 0.23 |
| `fighters_1832` | 0.01 | 0.03 | 0.11 | 0.20 | 0.40 | 0.11 |
| `fighters_pay1_1317` | 0.01 | 0.03 | 0.04 | 0.15 | 0.22 | 0.05 |

- A lone trained pilot mostly does not go until the fight is over. Against one idle
  enemy parked on the rim, `followers_1793` with no deadline is in time 0.04 and deals
  the parked ship 45 damage.
- Their share inside the circle early is the same at slack 1.5 and at 8 (0.05 and 0.03
  for `followers_1793`): they fly the same way whatever the allowance. A pilot that
  reads it should be in time at 2 and over, and at 8 arrive later having dealt more.

## Arms

Each is a new run from a night-4 pilot with night 4's settings. Update counts restart at 0.

| Arm | From | Inputs | Order pay | Drills |
|---|---|---|---|---|
| `followers_v8` | `followers_1793` | 587 | 1 | 0.35, go-to weighted 3 |
| `fighters_v8` | `fighters_1832` | 587 | 3 | 0.35, go-to weighted 2 |
| `fighters_pay1_v8` | `fighters_pay1_1317` | 587 | 1 | 0.25, go-to weighted 2 |
| `followers_v8_blind` | `followers_1793` | 583 | 1 | as `followers_v8` |

- **`followers_v8_blind` is the control:** paid by deadlines it cannot see. If seeing
  the deadline matters, `followers_v8` should use a long allowance to fight and still
  arrive, and the blind one can only hurry every time.
- The new inputs' first-layer weights start at zero and step 3 times faster than the
  rest (`new_input_lr_mult`, as B3's widening did).
- Bonus 1.0 and penalty 1.0 are first guesses; `fighters_v8` at order pay 3 has them at 3.
- The frozen pool adds nights 3 and 4's six pilots, since a new run has no checkpoints
  of its own.

## What the morning reads

1. **Sweep, child against parent and against itself with the deadline inputs zeroed.**
   In time at an allowance of 1.5 or more; arrival time at 8 over 1.5 (1 means it ignores
   the allowance); hits bought by a long allowance.
2. **Drills:** in time, near miss, at the enemy instead, by tight, medium and loose
   deadlines and with none. Do near misses fall (the closeness input and the larger
   bonus)? Does kill-first fall?
3. **Seeing against blind** (`followers_v8` against `followers_v8_blind`) on both.
4. **WAR** for the live ten plus tonight's four: did combat hold?
5. Attack and defend flips: did they move while go-to was the subject?

Nothing is published or archived by the morning script.
