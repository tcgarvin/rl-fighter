# Station commander: a learned commander does not find the hand rules' gains

Verdict: **FAIL**, in both roles, for both arms. After about 390 updates (11.5 hours on
the laptop), each learned commander scores level with the side that gives no orders
(−0.06 to +0.04, all within noise) and 0.11 to 0.27 below the best hand rule. Neither
learned to hold the station's reserve: both launch it at 2 s, as the script does, where
`hold_late` waits about 30 s. The attacker from commander 3 does bring its carrier in,
to about 190 m at 90 s (`carrier_push`: 163 m), but that gained nothing measurable.
`SIM_VERSION` 9; no rule of the game changed.

<!-- summary: We trained a commander on the station assault to see whether it would discover the two decisions that hand rules showed are worth winning matches: keeping the station's reserve ships docked until the station is hurt, and bringing the attacker's carrier in close. It did not: after half a day of training both versions launch the reserve at once and score the same as giving no orders at all. The likely reason is that holding back means choosing "don't launch" many times in a row, which a learner exploring at random almost never tries. -->

The plan, arms and bars are in [plan.md](plan.md). The hand rules are in
[station-rules](../2026-11-19-station-rules/results.md). Both arms trained against
`unseen` (the script, its orders hidden from its own pilots) 3 matches in 4 and the
script 1 in 4, over the live ten pilots, from 02:06 to the 13:30 deadline: `fresh`
(a new net) to update 390 and `from_c3` (commander 3's `live` line, update 197) to 392.
`eval.sh` played each final checkpoint in both roles against `unseen` on the hand-rule
eval's matches (1,024 a role on the carrier reading, 512 on the convoy), so every delta
is paired with the rule test's `none`.

## Scores against no orders

The ± is 1.96 standard errors of the paired difference.

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

Means over 50 updates of the training log (about 85 matches an update, so each cell is
about 4,000 matches split over both roles and both enemies):

| Updates | `fresh` defender vs unseen | `fresh` attacker vs unseen | `fresh` under an order | `from_c3` defender | `from_c3` attacker | `from_c3` under an order |
|---|---|---|---|---|---|---|
| 1–50 | 0.448 | 0.395 | 0.39 | 0.515 | 0.447 | 0.03 |
| 101–150 | 0.472 | 0.391 | 0.27 | 0.516 | 0.462 | 0.04 |
| 201–250 | 0.506 | 0.400 | 0.17 | 0.543 | 0.439 | 0.08 |
| 301–350 | 0.530 | 0.398 | 0.15 | 0.529 | 0.424 | 0.07 |
| 351–end | 0.512 | 0.413 | 0.16 | 0.518 | 0.429 | 0.09 |

`fresh` learned what commander 3 learned: order less (ship time under an order fell from
0.39 to 0.15), and its defence rose about 0.06 as it did. That is all it learned.
`from_c3` started quiet and stayed level. The launch head's entropy was already 0.08
(`fresh`) and 0.03 (`from_c3`) in the first 10 updates and fell to about 0.01: the
choice to launch was settled before training could reward holding back.

## What we learned

- **The hand rules' gain is out of reach of this action space by exploration.** A launch
  is a choice made at every decision while ships are docked. Holding the reserve for
  30 s means choosing "don't launch" at every decision for 30 s. A policy that launches
  with any real probability per decision has emptied the hangar within seconds, so it
  never sees what holding is worth. The log fits that reading (launch entropy near
  zero from the start, first launch always at 2 s); we did not test it directly.
- **The carrier waypoint is learnable but was not worth much here.** `from_c3`'s carrier
  closes to 190 m by 90 s, near `carrier_push`'s path, and its attack is level with no
  orders. `carrier_push` waits until the hangar is empty and holds 170 m; the learned
  carrier drifts in from the start. Which of those matters was not tested.
- **What to try next**, if commanders stay the goal: a launch decision the commander
  makes once, as a stance ("launch now / hold until the hull falls below x / hold until
  n attackers are close"), so that holding is one choice, not a run of them; or start
  the launch head biased to hold and let it learn when to let go.
