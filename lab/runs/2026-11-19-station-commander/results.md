# Station commander: a learned commander does not find what the hand rules found

Earlier the same night, [hand-written rules](../2026-11-19-station-rules/results.md)
found two decisions in the station assault that win matches, and neither is an order to
a pilot. The station's side does best to keep its reserve of strike craft (the small piloted ships) docked until
the station's hull is down to 60% (the rule `hold_late`). The attacker does best to bring
its carrier in to 170 m of the station once all its strike craft have launched
(`carrier_push`). We trained a commander network on this mission for half a day to see
whether it would find those decisions by trial and error. It did not. It scores the same
as giving no orders at all, and it launches the reserve at once, as the hand-written
commander does.

Verdict: **FAIL**, in both roles, for both arms (the two versions trained side by side,
described below). After about 390 updates (rounds of training; 11.5 hours on the
laptop), each learned commander scores level with the side that gives no orders (−0.06
to +0.04, all within noise) and 0.11 to 0.27 below the best hand rule. Neither learned to
hold the station's reserve: both launch it 2 s into the match, as the scripted commander
does, where `hold_late` waits about 30 s. The arm that started from an earlier commander
(`from_c3`, below) does bring its carrier in when attacking, to about 190 m at 90 s (`carrier_push`: 163 m), but that
gained nothing measurable. `SIM_VERSION` 9 (the ninth version of the game's rules); no
rule of the game changed.

<!-- summary: We trained a commander on the station assault to see whether it would discover the two decisions that hand rules showed are worth winning matches: keeping the station's reserve ships docked until the station is hurt, and bringing the attacker's carrier in close. It did not: after half a day of training both versions launch the reserve at once and score the same as giving no orders at all. The likely reason is that holding back means choosing "don't launch" many times in a row, which a learner exploring at random almost never tries. -->

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network
(a **pilot**) that learned to fly by trial and error. Above the pilots, each side can
have a **commander**, a second network or a script that sees the whole side, gives its
ships orders, decides when the carrier or station launches its docked ships, and steers
the carrier ([how a commander works](/commander/)).

Until this night every commander we had made its side worse than giving no orders, because
ordered pilots fight worse ([the order-cost night](../2026-11-17-order-cost/results.md)
traced why). The best learned
commanders, from [commander 3](../2026-11-15-commander-3/results.md), had simply learned
to give almost no orders. The [station assault](../2026-11-19-station-bomber/results.md),
new that night, was built partly to give commanders something worth deciding. One side
defends a static station, the other attacks it with a carrier, strike craft and bombers.
The hand rules showed it does: launch timing and the carrier's position add 0.13 to 0.19
to a side's share of matches won. The question here was whether a commander can learn them itself.

<div data-figure="diagram" data-name="missions" data-caption="The station assault is bottom right. This entry plays it under rules version 9, with the first station and no dreadnought."></div>

## How it was run

The plan, the two arms and the bars (pass marks set before the run) are in
[plan.md](plan.md). The bars, on the carrier reading (explained below): to **pass**, the
commander had to beat the no-orders side in both roles, with the margin of error clear of
zero, and come within noise of the best hand rule (about +0.19 defending, +0.13
attacking). Beating no orders in both roles by less would be **partial**. Anything else
**fails**. One network learned both roles, defending and attacking, drawn at
random each match. Both arms trained against `unseen` (the scripted commander with its
orders hidden from its own pilots, so in effect a side with no orders) in 3 matches of 4,
and against the scripted commander in 1 of 4. Every strike craft was flown by one of the
live ten (the ten pilots the live page draws from, picked at random ship by ship). They
ran from 02:06 to the 13:30 deadline:

- `fresh`: a new network, to update 390.
- `from_c3`: started from a commander that commander 3's night had trained over the same
  live ten (the arm named `live` there), as saved at its update 197. It had learned to
  keep its ships under an order only 5 to 6% of the time. It reached update 392.

<div data-figure="diagram" data-name="station-layout" data-caption="The two decisions this run hoped a commander would learn, under rules version 9 with no dreadnought. The script launches the reserve about 2 s in. The hand rule hold_late waits about 30 s."></div>

The station assault adds no new inputs to the networks. It reaches them dressed as an
older mission: as a carrier battle for both sides (the **carrier reading**) or as a
convoy escort with the station's side defending (the **convoy reading**). `eval.sh`
played each final checkpoint (saved copy of the network) in both roles against `unseen`
on the hand-rule test's matches: 1,024 a role on the carrier reading, 512 on the convoy.
So every difference is **paired**: each match is the same match (seed, ships and pilot
draws) that the rule test played with no orders (its rule `none`), compared match by
match.

## Scores against no orders

"Score" is the learned commander's share of matches won in that role. The roles are not
even: with no orders on either side, the station's side wins about 0.56 of matches and
the attacker about 0.44. "vs no orders" is the commander's score minus that of the
no-orders side on the same matches, so 0 means it adds nothing. The next two columns are
the best hand rule for that role and its own gain over no orders. "vs the rule" is the
commander's score minus the rule's. The ± is the margin of error (1.96 standard errors of
the paired difference): the true value very likely lies within that range.

| Arm | Reading | Role | Score | vs no orders | Best rule | Rule vs no orders | vs the rule |
|---|---|---|---|---|---|---|---|
| `fresh` 390 | carrier | defender | 0.503 | −0.062 ± 0.040 | `hold_late` | +0.185 ± 0.039 | −0.246 ± 0.039 |
| `fresh` 390 | carrier | attacker | 0.431 | −0.005 ± 0.040 | `carrier_push` | +0.130 ± 0.038 | −0.135 ± 0.041 |
| `fresh` 390 | convoy | defender | 0.510 | −0.064 ± 0.057 | `hold_late` | +0.203 ± 0.053 | −0.268 ± 0.055 |
| `fresh` 390 | convoy | attacker | 0.461 | +0.035 ± 0.058 | `carrier_push` | +0.145 ± 0.054 | −0.109 ± 0.054 |
| `from_c3` 392 | carrier | defender | 0.531 | −0.033 ± 0.040 | `hold_late` | +0.185 ± 0.039 | −0.218 ± 0.038 |
| `from_c3` 392 | carrier | attacker | 0.448 | +0.013 ± 0.042 | `carrier_push` | +0.130 ± 0.038 | −0.117 ± 0.042 |
| `from_c3` 392 | convoy | defender | 0.535 | −0.039 ± 0.058 | `hold_late` | +0.203 ± 0.053 | −0.242 ± 0.055 |
| `from_c3` 392 | convoy | attacker | 0.445 | +0.020 ± 0.055 | `carrier_push` | +0.145 ± 0.054 | −0.125 ± 0.056 |

Full tables with match endings: [eval/fresh_390/summary.md](eval/fresh_390/summary.md),
[eval/from_c3_392/summary.md](eval/from_c3_392/summary.md).

## What the commanders do (carrier reading)

Each row is a commander in one role. "First launch" is the median time of its side's
first launch from the station or carrier, and "Station hull then" the station's hull at
that moment (1.00 is undamaged). "Hangar empty" is when the last docked ship has gone.
"Re-orders / min" counts strike craft given a new order each minute, and "Under an order"
is the share of ship time spent under one. The last column is the attacking carrier's
distance from the station 20, 45 and 90 s into the match. The last three rows are the
scripted commander and the two best hand rules, for comparison.

| Arm | Role | First launch (median) | Station hull then | Hangar empty | Re-orders / min | Under an order | Carrier to station at 20 / 45 / 90 s |
|---|---|---|---|---|---|---|---|
| `fresh` | defender | 2 s | 1.00 | 4 s | 6.2 | 0.12 | |
| `fresh` | attacker | 2 s | | 6 s | 15.6 | 0.21 | 440 / 390 / 225 m |
| `from_c3` | defender | 2 s | 1.00 | 9 s | 6.4 | 0.14 | |
| `from_c3` | attacker | 2 s | | 6 s | 8.8 | 0.11 | 417 / 323 / 191 m |
| script (`none`) | either | 2 s | 1.00 | 4 s | | | patrol 420 to 460 m |
| `hold_late` | defender | about 30 s | below 0.60 | | | | |
| `carrier_push` | attacker | | | | | | 396 / 237 / 163 m |

## Through the night

These are means over 50 updates of the training log. Each update played about 85
matches, so each cell is about 4,000 matches split over both roles and both enemies (`unseen` and the scripted commander). The
win columns are against `unseen`, and "under an order" is the share of ship time under an
order.

| Updates | `fresh` defender vs unseen | `fresh` attacker vs unseen | `fresh` under an order | `from_c3` defender | `from_c3` attacker | `from_c3` under an order |
|---|---|---|---|---|---|---|
| 1–50 | 0.448 | 0.395 | 0.39 | 0.515 | 0.447 | 0.03 |
| 101–150 | 0.472 | 0.391 | 0.27 | 0.516 | 0.462 | 0.04 |
| 201–250 | 0.506 | 0.400 | 0.17 | 0.543 | 0.439 | 0.08 |
| 301–350 | 0.530 | 0.398 | 0.15 | 0.529 | 0.424 | 0.07 |
| 351–end | 0.512 | 0.413 | 0.16 | 0.518 | 0.429 | 0.09 |

`fresh` learned what commander 3 learned: order less (ship time under an order fell from
0.39 to 0.15), and its defence rose about 0.06 as it did. That is all it learned.
`from_c3` started quiet and stayed level. The commander decides launches with a separate
part of its network, its launch head. That head's entropy (how much randomness is left in
its choice; near 0 means it always makes the same one) was already 0.08 (`fresh`) and
0.03 (`from_c3`) in the first 10 updates, and fell to about 0.01. The choice to launch
was settled before training could reward holding back.

## What we learned

- **The hand rules' gain is out of reach by exploration, with the choices set up as they
  are.** A launch is a choice the commander makes at every decision while ships are
  docked. Holding the reserve for 30 s means choosing "don't launch" at every decision
  for 30 s. A commander that launches with any real probability per decision has emptied
  the hangar within seconds, so it never sees what holding is worth. The log fits that
  reading (launch entropy near zero from the start, first launch always at 2 s); we did
  not test it directly.

  <!-- figure-idea: why holding is hard to stumble on: a strip of the commander's successive decisions, each a coin flip "launch / don't", showing how fast a 10% or 30% launch chance empties the hangar against the long unbroken run of "don't" that hold_late needs; one decision "hold until hull < 60%" beside it as the alternative. -->

- **The carrier's position is learnable but was not worth much here.** `from_c3`'s
  carrier closes to 190 m by 90 s, near `carrier_push`'s path, and its attack is level
  with no orders. `carrier_push` waits until the hangar is empty and holds 170 m. The
  learned carrier drifts in from the start. Which of those matters was not tested.
- **What to try next**, if commanders stay the goal: a launch decision the commander
  makes once, as a stance ("launch now / hold until the hull falls below x / hold until
  n attackers are close"), so that holding is one choice, not a run of them. Or start
  the launch head biased to hold and let it learn when to let go.
