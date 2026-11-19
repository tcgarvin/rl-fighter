# Mixed-condition matches and order pay: an order still costs a fleet fight

Verdict: **FAIL.** No arm made an attack order cheap to follow. Against
`followers_school_1052` flying free, every checkpoint we measured scores between 0.14 and
0.35 in a 3 v 3 with each ship ordered onto its nearest enemy. Flying free against the same
opponent, the same checkpoints score 0.36 to 0.83. The best ordered score was pay025 at
update 725 (0.345). Training on did not keep it: 0.248 at 2200, 0.220 at the final 3478.
Every ordered pilot still puts 98% to 100% of its damage on its target. Each arm is one
seed, and a pilot's free strength drifts by ±0.2 from one checkpoint to the next, so the
cost (ordered minus free) is noisy. The scores are not. No rule of the game changed
(`SIM_VERSION` 8).

<!-- summary: We trained pilots in matches where only one side sees its orders, and with less or no pay for following an order outside drills, to see whether an order would stop costing a fleet fight. It did not: ordered onto their nearest enemy, every checkpoint scores 0.14 to 0.35 against a free opponent, and they still shoot almost only their target. A quarter of the order pay looked like it helped at update 725 (0.35), but the effect was gone by the end of the run. -->

The plan is in [plan.md](plan.md). Part 1 has the arms `control`, `mixed` and `mixed_all`
(`mixed_p` 0, 0.5 and 1). Part 2 has `pay0` and `pay025` (`mixed_all` with
`match_order_pay_scale` 0 and 0.25). All of them start fresh from `followers_school_1052`.
`control` ran on the laptop and was measured only at 725. Both mixed arms stopped at
2459 and 2548, and both pay arms at 3494 and 3478 (SIGTERM at 17:56).

## The cost, against a free 1052

The measure is `eval_cross.sh` → `order_rules.py --k 3 --blocks 24`: 3 v 3 games of one
hull (fighter, strafer, gunship), the checkpoint on one side and `followers_school_1052`
on the other. The 1052 side's orders come from the scripted commander and are hidden from
it. The checkpoint's side gets `nearest` (each ship on its own nearest enemy, chosen again
every 2 s) or `none` (no orders, the control). Each cell is 1,152 matches on the 2026-11-17
seeds, so the two columns pair match by match. The ± is 1.96 standard errors, paired for
the cost. "1052 ordered" is the reverse: 1052 under `nearest` against the checkpoint
flying free. It was run only for the laptop's checkpoints; the finals were measured with
`SKIP_REVERSE=1`. The parent's row is from `eval_before/`, with 1052 on both sides.

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
- **Part 1's bar: not met.** At 725, mixed's cost (−0.30) and mixed_all's (−0.37) against
  the control's (−0.40) are within about 0.1. Halving the gap would have needed about −0.20.
- **1052, ordered, is crushed by every arm** (0.04 to 0.10). Against these pilots,
  ordering a side is close to a certain loss.

### 2 v 2, pay025 final

The same measure at `--k 2` (`*_k2.json`), pay025 3478 against a free 1052: no orders
0.352 ± 0.027, nearest 0.340 ± 0.027, cost −0.012 ± 0.036. In a 2 v 2 the order costs this
pilot nothing measurable. It is also a weak 2 v 2 pilot (0.35 free). No other checkpoint
has a cross-pilot 2 v 2 to compare with. On 2026-11-17 the four followers, the same pilots
on both sides, paid −0.09 ± 0.04.

## What the ordered side does (first 30 s, 3 v 3, `nearest`)

These are from the JSONs' `sides.ordered`, with the free side for the parent and the
finals. Lost is per match. Shares are of a ship's time alive. Damage is per match. Advance
is speed toward the enemy fleet's centroid. "Share on target" is damage dealt to the
target over all damage dealt.

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
  0.25 or 0 makes no difference here. Drills alone, or the order input itself, are
  enough to fix "shoot only the target".
- **The charge faded in some arms, and the duel was still lost.** At the end, mixed_all
  advances at +3.0 m/s and pay025 at −0.8, against +13.5 for the parent. Either the fights
  are later or nobody presses: far less damage happens in the first 30 s on both sides,
  and fewer ships are lost. pay025 final still takes more from its target than it deals
  to it (52 and 33), and still scores 0.22. Not charging was not enough.
- **mixed 2459 still charges** (+10.7) and loses the exchange with its target (116 dealt,
  132 taken). Its 0.26 ordered score is about the parent's at 725, so the small cost
  comes from its weak free play.

## Training telemetry

From `log.jsonl` (`win_mixed_ordered` and `win_mixed_hidden`, the learner's score in mixed
matches against pool snapshots, by side), means over the first 100 and the last 200 updates:

| Arm | ordered, first 100 | ordered, last 200 | hidden, first 100 | hidden, last 200 |
|---|---|---|---|---|
| mixed | 0.48 | 0.44 | 0.82 | 0.75 |
| mixed_all | 0.42 | 0.45 | 0.75 | 0.79 |
| pay0 | 0.44 | 0.43 | 0.80 | 0.77 |
| pay025 | 0.41 | 0.42 | 0.74 | 0.73 |

The plan's third bar fails in every arm: the hidden side stays far above 0.5 for the
whole run, and the ordered side's score never climbs. Over 2,500 to 3,500 updates the
learner never learns to win the mixed match from the ordered side.

## Drill bars

`spacefight.eval.drills --n-per-kind 64`. Bars are in `spacefight/eval/drill_bars.yaml`
(attack_flip 0.70, defend_more_on_named 0.85, defend_side 0.85, defend_flip 0.75).

| Bar | 1052 | control 725 | mixed_all 725 | pay025 725 | pay0 3494 | pay025 3478 |
|---|---|---|---|---|---|---|
| goto_arrival | 0.851 | 0.844 | 0.854 | 0.839 | 0.854 | 0.855 |
| goto_lift | 0.672 | 0.659 | 0.684 | 0.653 | 0.718 | 0.661 |
| attack_target_hit | 0.961 | 0.969 | 0.953 | 0.992 | 0.930 | 0.992 |
| attack_side | 0.938 | 0.961 | 0.953 | 0.930 | 0.875 | 0.945 |
| attack_flip | 0.875 | 0.922 | 0.906 | 0.859 | 0.766 | 0.922 |
| defend_more_on_named | 0.945 | 0.898 | 0.859 | 0.836 (**missed**) | 0.852 | 0.914 |
| defend_side | 0.961 | 0.922 | 0.953 | 0.906 | 0.859 | 0.953 |
| defend_flip | 0.922 | 0.844 | 0.906 | 0.812 | 0.719 (**missed**) | 0.922 |
| Gate | pass | pass | pass | fail | fail | pass |

Go-to held in every arm, within 0.02 of the parent's. pay0's final checkpoint fails the
gate, and its attack and defend swap tests fell furthest (attack_flip 0.77, defend_flip
0.72): with no order pay in matches it slowly unlearns what an order means, even though
drills still pay. pay025 725 misses defend_more_on_named by 0.014, which is inside the
noise of 128 drills. Its final checkpoint passes every bar. The mixed and mixed_all
finals did not get a drill eval.

## What we learned

- **Mixed matches do not teach an ordered pilot to win.** That holds with the order paid
  in full, at a quarter, or not at all, over 2,500 to 3,500 updates. The learner's ordered
  side stays at about 0.43 in training, and the cross-pilot score stays at 0.14 to 0.35.
- **Ordered pilots shoot only their target, whatever the match pays.** That comes from
  the drills (their pass rule and pay) or from what the order input means to the net, not
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

The kite-drill run (`lab/runs/2026-11-18-kite-drills/plan.md`, prepared, not yet
launched): attack drills whose enemy team is a frozen pool pilot with its orders hidden.
In those drills the target falls back and fights back, so chasing it and shooting only it
is paid what it is worth. Measure it the same way: `eval_cross.sh` against free 1052,
with the ordered score as the headline, drills, and a 2 v 2.

## Files

- `eval_cross/<ckpt>_v_base1052_{nearest,none}.json|.out`: the cross-pilot measure.
  Finals: `pay0_3494`, `pay025_3478`, `mixed_2459`, `mixedall_2548`, run on Beast with
  `THREADS=1 SKIP_REVERSE=1`, about 590 s each with 8 at once. `_k2` is the 2 v 2 for
  pay025 3478. `base1052_v_<ckpt>_nearest` is the reverse (laptop checkpoints only).
- `eval_drills/<ckpt>.json|.md|.out`: drill evals (pay0 3494, pay025 3478 and pay025 725
  are new here).
- `eval_before/`: the parent, 1052 on both sides. `eval_725/`: same-pilot measures at 725.
