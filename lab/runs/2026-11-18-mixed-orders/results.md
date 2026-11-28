# Matches against unordered sides, and less pay for orders: an order still costs a fleet fight

Our trained pilots lose fleet fights (battles between small ships, with no big ships on
the field) when they are given orders. We tried two changes to their training to fix
that. First, matches in which one side sees its orders and the other does not, a matchup
no pilot had trained in. Second, less or no extra pay in matches for hitting the enemy a
pilot was ordered onto. Neither worked. Ordered to attack the enemy nearest it, every
trained pilot we measured still wins only 0.14 to 0.35 of three-a-side fights against
its parent flying with no orders, and still shoots almost nothing but its target.

Verdict: **FAIL.** No version of the experiment made an attack order cheap to follow. Each
version is a single training run, so luck and the setting being tested can't be told
apart, but none came close.

<!-- summary: Our pilots lose fleet fights when they are given orders, and no pilot had ever trained in a match where one side is ordered and the other is not. We trained pilots in such matches, and with less or no pay for following an order outside practice drills, to see whether an order would stop costing a fleet fight. It did not: ordered to attack their nearest enemy, every pilot we measured wins only 0.14 to 0.35 of three-a-side fights against an opponent with no orders, and they still shoot almost only their target. A quarter of the order pay looked like it helped at one point (0.35), but the effect was gone by the end of the run. -->

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a pilot, that learned to fly by trial and error. A commander (a second network, or a
hand-written script) can give each ship orders, such as "attack that enemy". This entry is
about fleet fights: small ships only, 1 to 4 a side, where a side wins by destroying every
enemy, or at the 90 s time limit by having more hull and shields left. The night before,
[the order-cost night](../2026-11-17-order-cost/results.md) found that following an
attack order loses a fleet fight whichever enemy it names. Ordered pilots keep flying
at their targets while pilots with no orders fall back, then shoot only their targets and
lose those duels. That night also noticed that every training match gave both sides
orders or neither, so an ordered pilot had never met a side that falls back and picks its
shots. A commander is useless if obeying it loses, so this was the obvious thing to fix
next. This run (two parts, one day) tested whether training in that matchup, or paying
less for the order, fixes it. [The kite-drill run](../2026-11-18-kite-drills/results.md)
tried a third idea the same day.

## What we did

The plan is in [plan.md](plan.md). Every arm (version of the experiment) starts fresh
from `followers_school_1052`, a pilot of the followers family (the line bred to fight and
to follow orders), saved at update 1052 of [its go-to school](../2026-11-14-goto-school-2/results.md). A pilot's name is its training
line followed by the update (one round of training) it was saved at, and "1052" below is
short for this pilot. A checkpoint is named by arm and update: "pay025 725" is the
`pay025` arm at update 725.

- **Part 1, mixed matches:** the arms `control`, `mixed` and `mixed_all`. In every arm a
  third of the non-drill matches hide orders from both sides, and the other two thirds
  show them. The setting `mixed_p` (0, 0.5 and 1) is the share of those two thirds in
  which one side's orders are hidden instead. So `control` has no mixed matches, `mixed`
  has them in a third of its non-drill matches (half of two thirds), and `mixed_all` in
  two thirds. All three cut drills (practice scenarios) to 30% of training from the
  parent's 70%, so `control` tells that change apart from the mixed matches.
- **Part 2, order pay:** `pay0` and `pay025` (`mixed_all` with `match_order_pay_scale` 0
  and 0.25). Under an attack order a hit on the target normally pays double a hit on
  anyone else. These arms cut that extra pay in matches to nothing or to a quarter, and
  keep it in drills.

The plan set three checks. First, the cost: a `mixed` arm should halve the gap between
its ordered and free scores, compared with `control`. Second, no loss in drills: the drill
test (a check that the pilot still does what each kind of order says) still passes, with
go-to arrival (reaching a point it was sent to, by the deadline) within 0.05 of the
parent's. Third, the side with
hidden orders should not simply keep winning the mixed matches in training.

`control` ran on the laptop and was measured only at 725. Both mixed arms stopped at
updates 2459 and 2548, and both pay arms at 3494 and 3478 (sent a stop signal, SIGTERM,
at 17:56). No rule of the game changed (`SIM_VERSION` 8, the version number of the game's
rules).

<div data-figure="diagram" data-name="training-night" data-caption="Here one parent, followers_school_1052, was copied into five arms in two parts, and they trained on through the next day. This run had no WAR round: the arms were measured on the order cost and the practice drills."></div>

## The cost, against a free 1052

This section's main test, which we call the cross-pilot measure, is the one from the
order-cost night. Each match is a 3 v 3 (three ships a side) in which all six ships are
one hull, or ship type: fighter, strafer or gunship. Fighters and strafers have guns
fixed to the nose, so they must point at a target to shoot. The gunship is slower, with
turrets that aim on their own. The checkpoint flies one side and `followers_school_1052`
the other. The 1052 side flies free, on its own judgment: the scripted commander runs
underneath it, as it does for any side without a commander, but its pilots never see its
orders. The checkpoint's side gets `nearest` (each ship ordered onto its own nearest
enemy, chosen again every 2 s) or `none` (no orders, the control).

Each number is the checkpoint side's score, the share of matches won with draws counting
half, so 0.5 is even. Each cell is 1,152 matches on the same starting setups as the
order-cost night, so the two columns pair match by match. The cost is nearest minus
none: the change in the share of matches won that the order causes, so negative means
the order loses matches. The ± is the margin of error: the true value very likely lies
within that range. The last column is the reverse test, 1052 ordered by `nearest`
against the checkpoint flying free. It was run only for the checkpoints measured on the
laptop. The parent's row has 1052 on both sides. (Commands: `eval_cross.sh` →
`order_rules.py --k 3 --blocks 24` on the 2026-11-17 seeds; ± is 1.96 standard errors,
paired for the cost; the finals ran with `SKIP_REVERSE=1`; the parent's row is from
`eval_before/`.)

| Checkpoint | No orders | Nearest orders | Cost (paired) | 1052 ordered vs it free |
|---|---|---|---|---|
| followers_school_1052 (parent) | 0.503 ± 0.029 | 0.136 ± 0.020 | −0.367 ± 0.035 | |
| control 725 | 0.680 ± 0.027 | 0.276 ± 0.026 | −0.404 ± 0.038 | 0.050 ± 0.013 |
| mixed 725 | 0.515 ± 0.029 | 0.213 ± 0.024 | −0.302 ± 0.037 | 0.044 ± 0.012 |
| mixed_all 725 | 0.534 ± 0.029 | 0.164 ± 0.021 | −0.370 ± 0.034 | 0.097 ± 0.017 |
| pay0 725 | 0.553 ± 0.029 | 0.234 ± 0.024 | −0.319 ± 0.036 | |
| pay025 725 | 0.590 ± 0.028 | **0.345** ± 0.027 | −0.245 ± 0.043 | |
| mixed 2250 | 0.497 ± 0.029 | 0.186 ± 0.022 | −0.311 ± 0.036 | 0.053 ± 0.013 |
| mixed_all 2250 | 0.737 ± 0.025 | 0.175 ± 0.022 | −0.562 ± 0.034 | 0.088 ± 0.016 |
| pay0 2200 | 0.605 ± 0.028 | 0.220 ± 0.024 | −0.385 ± 0.033 | |
| pay025 2200 | 0.454 ± 0.029 | 0.248 ± 0.025 | −0.207 ± 0.038 | |
| mixed 2459 (final) | 0.360 ± 0.028 | 0.257 ± 0.025 | −0.103 ± 0.036 | |
| mixed_all 2548 (final) | 0.764 ± 0.024 | 0.285 ± 0.026 | −0.479 ± 0.035 | |
| pay0 3494 (final) | 0.826 ± 0.022 | 0.138 ± 0.020 | **−0.688** ± 0.028 | |
| pay025 3478 (final) | 0.425 ± 0.029 | 0.220 ± 0.024 | −0.205 ± 0.035 | |

- **The ordered score barely moves.** Across 13 checkpoints of five arms it stays between
  0.14 and 0.35. The free score ranges from 0.36 to 0.83. The cost column follows the free
  score more than anything else: the arms with the smallest costs (mixed final −0.10,
  pay025 −0.21) are the ones that got *weaker* free. They did not get stronger ordered.
- **pay025 at 725 is the one sign, and it did not hold.** Its 0.345 is the best ordered
  score in the table, 0.18 above mixed_all at the same update. By 2200 the lead over
  mixed_all was 0.07. At the end it was 0.220 against mixed_all's 0.285, though the two
  finals are 900 updates apart.
- **pay0 got strong and no better at orders.** At the end it is the strongest free pilot
  measured (0.83 against 1052), and ordered it scores the parent's 0.14. Removing order
  pay from matches made it a better free fighter. It did not make it a better ordered one.
- **Part 1's first check: not met.** The plan's mark for success was a `mixed` arm that
  halves the gap between ordered and free, compared with `control`. At 725, mixed's cost
  (−0.30) and mixed_all's (−0.37) against the control's (−0.40) are within about 0.1. Halving the gap would have needed about −0.20.
- **1052, ordered, is crushed by every arm** (0.04 to 0.10). Against these pilots,
  ordering a side is close to a certain loss.

### 2 v 2, pay025 final

The same measure in 2 v 2 fights (`--k 2`, `*_k2.json`), pay025 3478 against a free 1052: no orders
0.352 ± 0.027, nearest 0.340 ± 0.027, cost −0.012 ± 0.036. In a 2 v 2 the order costs this
pilot nothing measurable. It is also a weak 2 v 2 pilot (0.35 free). No other checkpoint
has a cross-pilot 2 v 2 to compare with. The closest comparison is from [the order-cost
night](../2026-11-17-order-cost/results.md), where a pool of four order-following pilots
flew both sides of 2 v 2 fights. There, ordering one side onto its nearest enemies cost
it −0.09 ± 0.04.

## What the ordered side does (first 30 s, 3 v 3, `nearest`)

This table shows how each side flew in the first 30 seconds of the same matches (all
with `nearest` orders), which is where the order-cost night found the cost. Each row is a
checkpoint's ordered side, except the rows marked "free side" or "free 1052": those are
the opposing 1052 side in the same matches, shown for the parent and the finals. (From
the JSONs' `sides`.) Lost is ships lost per match. "In arc" shares are of a ship's time alive with its target, or another enemy, in its gun arc
(roughly, where its guns can hit). Damage is per match. Advance is speed toward the enemy
fleet's centre (its centroid). "Share on target" is damage dealt to the target over all
damage dealt.

<!-- figure-idea: shared: the charge and the duel. Two three-ship fleets over the first 30 seconds: the ordered side flying straight at its targets, the free side falling back and taking shots at whoever crosses its nose, with a damage tally for each duel. Helps here because "advance", "in arc" and "share on target" are hard to picture from a table, and several entries on order cost could use it. -->

| Side | Lost | Target in arc | Other in arc | Advance (m/s) | Dealt to target | Dealt to others | Taken from target | Taken from others | Share on target |
|---|---|---|---|---|---|---|---|---|---|
| 1052 (parent), ordered | 1.00 | 0.109 | 0.003 | +13.5 | 88 | 2 | 118 | 32 | 0.98 |
| 1052 (parent), free side | 0.41 | 0.081 | 0.030 | −4.5 | 120 | 30 | 71 | 19 | 0.80 |
| control 725 | 0.86 | 0.078 | 0.002 | +11.9 | 88 | 2 | 122 | 21 | 0.98 |
| mixed 725 | 0.85 | 0.197 | 0.019 | +14.1 | 107 | 2 | 139 | 23 | 0.99 |
| mixed_all 725 | 0.70 | 0.085 | 0.001 | +8.7 | 66 | 1 | 89 | 22 | 0.99 |
| pay0 725 | 0.73 | 0.113 | 0.002 | +7.6 | 91 | 1 | 95 | 21 | 0.99 |
| pay025 725 | 0.87 | 0.153 | 0.018 | +10.9 | 107 | 1 | 136 | 17 | 0.99 |
| mixed 2250 | 0.95 | 0.151 | 0.007 | +13.6 | 113 | 1 | 142 | 22 | 0.99 |
| mixed_all 2250 | 0.54 | 0.067 | 0.001 | +7.8 | 54 | 0 | 74 | 18 | 0.99 |
| pay0 2200 | 0.35 | 0.202 | 0.086 | +10.4 | 55 | 4 | 125 | 18 | 0.93 |
| pay025 2200 | 0.53 | 0.110 | 0.003 | +7.9 | 86 | 0 | 100 | 10 | 1.00 |
| mixed 2459, ordered | 0.91 | 0.128 | 0.007 | +10.7 | 116 | 1 | 132 | 23 | 0.99 |
| mixed 2459, free 1052 | 0.61 | 0.094 | 0.051 | −3.0 | 108 | 47 | 81 | 36 | 0.70 |
| mixed_all 2548, ordered | 0.38 | 0.045 | 0.001 | +3.0 | 59 | 0 | 57 | 11 | 0.99 |
| mixed_all 2548, free 1052 | 0.26 | 0.032 | 0.016 | +1.0 | 48 | 20 | 41 | 19 | 0.70 |
| pay0 3494, ordered | 0.14 | 0.069 | 0.010 | +7.3 | 22 | 1 | 37 | 4 | 0.98 |
| pay0 3494, free 1052 | 0.07 | 0.028 | 0.044 | −1.4 | 20 | 22 | 10 | 12 | 0.48 |
| pay025 3478, ordered | 0.23 | 0.040 | 0.001 | −0.8 | 33 | 0 | 52 | 6 | 0.99 |
| pay025 3478, free 1052 | 0.16 | 0.024 | 0.014 | +3.8 | 36 | 21 | 20 | 14 | 0.63 |

- **Only the target is ever shot.** Every ordered side, in every arm and at every update,
  puts 0.93 to 1.00 of its damage on its target and 0 to 4 a match on others. The free
  1052 puts 0.48 to 0.80 on its target. Pay for hits on the target in matches at 1.0,
  0.25 or 0 makes no difference here. Drills alone, or the order input itself (the order
  as one of the things the pilot sees), are enough to set "shoot only the target".
- **The charge faded in some arms, and the duel was still lost.** At the end, mixed_all
  advances at +3.0 m/s and pay025 at −0.8, against +13.5 for the parent. Either the fights
  are later or nobody presses: far less damage happens in the first 30 s on both sides,
  and fewer ships are lost. pay025 final still takes more from its target than it deals
  to it (52 and 33), and still scores 0.22. Not charging was not enough.
- **mixed 2459 still charges** (+10.7) and loses the exchange with its target (116 dealt,
  132 taken). Its 0.26 ordered score is in the range of the other checkpoints (0.14 to
  0.35), so its small cost comes from its weak free play (0.36).

## Training telemetry

These are numbers logged during training, from `log.jsonl` (`win_mixed_ordered` and
`win_mixed_hidden`): the learner's score in mixed matches against pool snapshots (frozen
earlier pilots used as training opponents), by side. "Ordered" is the learner on the side
that sees its orders, "hidden" the learner on the side whose orders are hidden. The
numbers are means over the first 100 and the last 200 updates:

| Arm | ordered, first 100 | ordered, last 200 | hidden, first 100 | hidden, last 200 |
|---|---|---|---|---|
| mixed | 0.48 | 0.44 | 0.82 | 0.75 |
| mixed_all | 0.42 | 0.45 | 0.75 | 0.79 |
| pay0 | 0.44 | 0.43 | 0.80 | 0.77 |
| pay025 | 0.41 | 0.42 | 0.74 | 0.73 |

The plan's third check (that the hidden side should not simply keep winning) fails in
every arm: the hidden side stays far above 0.5 for the whole run, and the ordered side's
score never climbs. Over 2,500 to 3,500 updates the learner never learns to win the mixed match from the ordered side.

## Drill bars

`spacefight.eval.drills --n-per-kind 64`. Bars (pass marks, in the second column) are in
`spacefight/eval/drill_bars.yaml`. The drill test plays standard drills against script enemies and checks that a pilot still
does what each order says. The gate passes when every row clears its bar. Each row is a
share of drills. goto_arrival is the share of ships that reach a go-to point by its
deadline, and goto_lift that share minus the share with the order hidden.
attack_target_hit is any damage on the named target. attack_side and defend_side: the
squad went to the named side. attack_flip and defend_flip are the swap test: the same
start with the other side named, and the squad chose the named side both times.
defend_more_on_named: in a defend drill, where two friendly ships (wards) are under attack
and one is named, the named ward's attackers took more damage than the other ward's.

| Bar | Pass mark | 1052 | control 725 | mixed_all 725 | pay025 725 | pay0 3494 | pay025 3478 |
|---|---|---|---|---|---|---|---|
| goto_arrival | 0.60 | 0.851 | 0.844 | 0.854 | 0.839 | 0.854 | 0.855 |
| goto_lift | 0.40 | 0.672 | 0.659 | 0.684 | 0.653 | 0.718 | 0.661 |
| attack_target_hit | 0.90 | 0.961 | 0.969 | 0.953 | 0.992 | 0.930 | 0.992 |
| attack_side | 0.75 | 0.938 | 0.961 | 0.953 | 0.930 | 0.875 | 0.945 |
| attack_flip | 0.70 | 0.875 | 0.922 | 0.906 | 0.859 | 0.766 | 0.922 |
| defend_more_on_named | 0.85 | 0.945 | 0.898 | 0.859 | 0.836 (**missed**) | 0.852 | 0.914 |
| defend_side | 0.85 | 0.961 | 0.922 | 0.953 | 0.906 | 0.859 | 0.953 |
| defend_flip | 0.75 | 0.922 | 0.844 | 0.906 | 0.812 | 0.719 (**missed**) | 0.922 |
| Gate | | pass | pass | pass | fail | fail | pass |

Go-to held in every arm: arrival within 0.02 of the parent's, and goto_lift within 0.05.
pay0's final checkpoint fails the gate, and its attack and defend swap tests fell furthest (attack_flip 0.77, defend_flip
0.72): with no order pay in matches it slowly unlearns what an order means, even though
drills still pay. pay025 725 misses defend_more_on_named by 0.014, which is inside the
noise of 128 drills. Its final checkpoint passes every bar. The mixed and mixed_all
finals did not get a drill eval.

## Verdict in detail

Against `followers_school_1052` flying free, every checkpoint we measured scores between
0.14 and 0.35 in a 3 v 3 with each ship ordered onto its nearest enemy. Flying free
against the same opponent, the same checkpoints score 0.36 to 0.83. The best ordered score
was pay025 at update 725 (0.345). Training on did not keep it: 0.248 at 2200, 0.220 at the
final 3478. Every ordered pilot still puts 93% to 100% of its damage on its target (98% to
100% for all but pay0 at 2200). A pilot's free strength drifts by ±0.2 from one checkpoint
to the next, so the cost (ordered minus free) is noisy. The scores themselves are not.

## What we learned

- **Mixed matches do not teach an ordered pilot to win.** That holds with the order paid
  in full, at a quarter, or not at all, over 2,500 to 3,500 updates. The learner's ordered
  side stays at about 0.43 in training, and the cross-pilot score stays at 0.14 to 0.35.
- **Ordered pilots shoot only their target, whatever the match pays.** That comes from
  the drills (their pass rule and pay) or from what the order input means to the network, not
  from match order pay. It is the part of the cost nothing in this run touched.
- **The cost (ordered minus free) is a poor single number** while free strength drifts
  this much: pay0 final pays −0.69 because it is a strong free pilot. The ordered score
  against a fixed free opponent is the steadier measure, and it barely moved.
- **Cutting order pay in matches to 0 costs drill discipline** (pay0's final fails the
  gate). A quarter (pay025) keeps it.
- **One seed per arm.** The differences between arms at one update are at most 0.18, and
  checkpoints 300 to 1,500 updates apart in one arm differ by 0.1. Nothing here ranks one
  arm above another with confidence.

## Next

The kite-drill run ([its plan](../2026-11-18-kite-drills/plan.md), prepared, not yet
launched when this was written; [its results](../2026-11-18-kite-drills/results.md)):
attack drills whose enemy team is a frozen pool pilot with its orders hidden.
In those drills the target falls back and fights back, so chasing it and shooting only it
is paid what it is worth. Measure it the same way: `eval_cross.sh` against free 1052,
with the ordered score as the headline, drills, and a 2 v 2.

## Files

Where the raw results are, for anyone reproducing them.

- `eval_cross/<ckpt>_v_base1052_{nearest,none}.json|.out`: the cross-pilot measure.
  Finals: `pay0_3494`, `pay025_3478`, `mixed_2459`, `mixedall_2548`, run on Beast (the lab's
  desktop with two graphics cards) with
  `THREADS=1 SKIP_REVERSE=1`, about 590 s each with 8 at once. `_k2` is the 2 v 2 for
  pay025 3478. `base1052_v_<ckpt>_nearest` is the reverse (laptop checkpoints only).
- `eval_drills/<ckpt>.json|.md|.out`: drill evals (pay0 3494, pay025 3478 and pay025 725
  are new here).
- `eval_before/`: the parent, 1052 on both sides. `eval_725/`: same-pilot measures at 725.
