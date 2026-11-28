# Kite drills: practice against a target that backs away cuts the cost of an order

Our trained pilots lose fleet fights (battles between small ships, with no big ships on
the field) when they are given orders: told to attack an enemy,
a pilot charges it and loses the duel. We asked whether practising attacks on a target
that backs away and shoots back would change that. For one of two trained copies it did.
Ordered to attack the enemy nearest it, the `kite` copy now wins 0.42 to 0.47 of
three-a-side fights against its parent flying with no orders, where the parent, ordered
the same way, won 0.14. It still charges as hard as before. What changed is that it now
wins the duel the order sends it into.

Verdict: **PASS** for `kite`, which met every mark the plan set in advance. The other
copy, `kite_pay025`, landed between the marks for success and failure. Each copy is a
single training run, so luck and the setting being tested can't be told apart.

<!-- summary: Our pilots lose fleet fights when given orders, because an ordered pilot charges its target and loses the duel. We trained two copies of a pilot on attack drills whose target is an earlier learned pilot that backs away and shoots back. Ordered to attack its nearest enemy, one copy now wins 0.42 to 0.47 of three-a-side fights against its parent flying with no orders, where the parent won 0.14 and no earlier attempt beat 0.35. It still charges as hard as before but now wins that duel. The copy that also cut the pay for following orders in matches reached only 0.33. -->

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a pilot, that learned to fly by trial and error. A second network or a hand-written
script, the commander, can give each ship orders: attack this enemy, go to that point,
defend that ship. A commander is only worth having if following its orders doesn't lose
the fight. A fleet fight has small ships only, 1 to 4 a side: a side wins by destroying
every enemy, or at the 90 s time limit by having more hull and shields left.
[The order-cost night](../2026-11-17-order-cost/results.md) found that a side ordered to attack loses most 3 v 3 fights against the same pilots with
no orders. The ordered pilots keep flying at their targets while the free side falls back,
then shoot only their targets and lose those duels. [The mixed-orders run](../2026-11-18-mixed-orders/results.md),
the same day as this one, trained pilots in matches with one side ordered and the other
not, and with less pay for following orders. Neither helped.

One gap remained. In the practice scenarios (drills) where pilots learn what an attack
order means, every enemy was the script, our hand-written rule-based pilot, which never
backs away, and most targets were busy attacking a freighter (a slow cargo ship). No pilot had practised on a
target that falls back and fights. This night added that, as **kite drills** (to kite is
to fall back while shooting).

<div data-figure="diagram" data-name="orders" data-caption="This entry turns on the attack order. Kite drills practise it against a target that backs away and fights back."></div>

## What we did

The plan is in [plan.md](plan.md). Two versions of the experiment (arms) trained side by
side. Both start fresh from `followers_school_1052`, a pilot of the followers family (the
line bred to fight and to follow orders), saved at update 1052 of [its go-to school](../2026-11-14-goto-school-2/results.md),
training that was mostly drills. A pilot's name is its training line followed by the
update (one round of training) it was saved at, and "1052" below is short for this one.
Both arms use drill_share 0.4 (40% of training is drills), drill_weights `[4, 3, 1]`
(go-to, attack and defend drills in that ratio) and `drill_attack_pool_share` 0.5, which
makes half of all attack drills kite drills. A kite drill has no freighters, and the
whole enemy team is a frozen pool pilot (a saved pilot that no longer learns, drawn from
the run's pool of training opponents: a few fixed older pilots and this run's own
checkpoints) whose orders are hidden from it. `kite_pay025` also sets
`match_order_pay_scale` 0.25: in ordinary matches, as opposed to drills, the extra pay
for hitting an ordered target is cut to a quarter.

Both ran on Beast (the lab's desktop with two graphics cards: cuda:0 and cuda:1, 3 + 3
threads, about 10.5 s an update) from 22:28 until the 05:00 deadline, and stopped at
updates **2205** (`kite`) and **2211** (`kite_pay025`). Update 725, where the earlier
run's arms were compared, was not measured; the time before the next run only covered
2200 and the finals. The arms trained under `SIM_VERSION` 8 (the version number of the
game's rules) and were measured under 9. Version 9 added a new mission and left the old
missions playing bit-identically, so this does not affect the results.

<!-- figure-idea: a kite drill from above: the learner's squad in the middle, two enemy groups on opposite sides, one enemy named as the target, and that target backing away while firing, against a standard drill whose target is busy with a freighter. Helps because "kite drill" is the night's one new idea. -->

## The cost, against a free pilot

The test is the one from the order-cost night: 3 v 3 games (three ships a side) in which
all six ships are one hull, or ship type: fighter, strafer or gunship. Fighters and
strafers have guns fixed to the nose, so they must point at a target to shoot. The
gunship is slower, with turrets that aim on their own. The checkpoint's side is ordered
by `nearest` (each ship onto its nearest enemy, chosen again every 2 s) or by `scripted`
(the sim's hand-written commander), or it gets no orders (`none`). The other side is a
free pilot, flying on its own judgment: the scripted commander runs underneath it, as it
does for any side without a commander, but its pilots never see its orders. There are
1,152 matches a cell, on the same starting setups as that night, so every cell pairs
with every other match by match. (Command: `eval.sh` → `order_rules.py --k 3 --blocks 24`
on the 2026-11-17 seeds.)

Each number is the checkpoint side's score, the share of matches won with draws counting
half, so 0.5 is even. The ± is the margin of error (1.96 standard errors): the true value
very likely lies within that range. Cost is nearest minus none, paired match by match:
the change in the share of matches won that the order causes, so negative means the
order loses matches. A checkpoint is named by arm and update: "kite 2200" is the `kite` arm at update 2200.
Earlier rows are from [the mixed-orders run](../2026-11-18-mixed-orders/results.md) (the
parent's from its `eval_before/`, 1052 on both sides). There, `control` trained like this
night's arms but with fewer drills and no kite drills, and `pay025` cut match order pay to
a quarter in matches where one side was ordered and the other not.

### Against followers_school_1052

| Checkpoint | No orders | Nearest | Scripted commander | Cost (paired) |
|---|---|---|---|---|
| followers_school_1052 (parent) | 0.503 ± 0.029 | 0.136 ± 0.020 | 0.200 ± 0.023 | −0.367 ± 0.035 |
| control 725 (mixed-orders) | 0.680 ± 0.027 | 0.276 ± 0.026 | | −0.404 ± 0.038 |
| pay025 2200 (mixed-orders) | 0.454 ± 0.029 | 0.248 ± 0.025 | | −0.207 ± 0.038 |
| pay025 3478 (mixed-orders, final) | 0.425 ± 0.029 | 0.220 ± 0.024 | | −0.205 ± 0.035 |
| **kite 2200** | 0.561 ± 0.029 | **0.474** ± 0.029 | 0.365 ± 0.028 | **−0.087** ± 0.039 |
| **kite 2205 (final)** | 0.566 ± 0.029 | **0.421** ± 0.028 | 0.342 ± 0.027 | −0.145 ± 0.039 |
| kite_pay025 2200 | 0.562 ± 0.029 | 0.325 ± 0.027 | 0.378 ± 0.028 | −0.237 ± 0.037 |
| kite_pay025 2211 (final) | 0.565 ± 0.029 | 0.330 ± 0.027 | 0.426 ± 0.029 | −0.235 ± 0.036 |

### Against f995_701 (a fighter of another family)

`f995_701` is the founder of another family, the fighters line: a strong fighter that
ignores orders, from [the Fighters v2 night](../2026-11-01-fighters-v2/results.md). The
table reads the same way, with `f995_701` flying the free side.

| Checkpoint | No orders | Nearest | Scripted commander | Cost (paired) |
|---|---|---|---|---|
| kite 2200 | 0.647 ± 0.028 | 0.465 ± 0.029 | 0.464 ± 0.029 | −0.182 ± 0.036 |
| kite 2205 (final) | 0.631 ± 0.028 | 0.465 ± 0.029 | 0.438 ± 0.029 | −0.166 ± 0.039 |
| kite_pay025 2200 | 0.646 ± 0.028 | **0.641** ± 0.028 | 0.618 ± 0.028 | −0.005 ± 0.039 |
| kite_pay025 2211 (final) | 0.588 ± 0.028 | **0.622** ± 0.028 | 0.596 ± 0.028 | +0.034 ± 0.039 |

No earlier checkpoint was measured against f995_701, so these rows have nothing to
compare with yet.

- **`kite` is the first arm above 0.40 ordered.** 0.474 and 0.421, against 0.136 for the
  parent and 0.14 to 0.35 for all 13 checkpoints of
  [the mixed-orders run](../2026-11-18-mixed-orders/results.md). Its free score (0.56) sits
  in the middle of the earlier arms' range (0.36 to 0.83), so the gain did not come from a
  stronger free pilot. The cost against 1052 is −0.09 and −0.15, the smallest
  measured for a pilot that is not weak when free.
- **The two arms disagree on which opponent the order costs against.** `kite` keeps a cost
  of about −0.17 against f995_701 (0.47 ordered, 0.63 to 0.65 free). `kite_pay025` follows
  an order at no cost against f995_701 (0.64 and 0.62 ordered, −0.01 and +0.03 cost), but
  pays −0.24 against 1052. f995_701 is one of the fixed older pilots in both arms' pool of
  training opponents, so either arm may have met it as a kite-drill enemy.
  With one seed per arm, this does not say whether the difference comes from the arm's
  settings or from its seed.
- **The scripted commander's orders cost more than `nearest` for `kite`** (0.34 to 0.37
  against 1052) and less for `kite_pay025` (0.38 to 0.43). Both are above the parent's
  0.200.
- **2200 and the final are 5 to 11 updates apart.** They differ by up to 0.05 on the
  ordered score, which shows how noisy one checkpoint is, not a trend.

## What the ordered side does (first 30 s, 3 v 3, `nearest`, against free 1052)

This table shows how the ordered side flew in the first 30 seconds of the same matches,
which is where the order-cost night found the cost. These come from the JSONs'
`sides.ordered`. Lost is ships per match. "Target in arc" is the share of a ship's time
alive with its target in its gun arc (for the fighter and strafer, the fixed nose gun
pointing within 10° of it, in range; for the gunship, whose turrets reach nearly all
round, the target within 230 m). Advance is speed toward the enemy fleet's centre (its
centroid), and "to target" is speed toward the ship's own target. Damage is per match.
"Share on target" is damage dealt to the target over all damage dealt.

<!-- figure-idea: shared: the charge and the duel. Two three-ship fleets over the first 30 seconds: the ordered side flying straight at its targets, the free side falling back and taking shots at whoever crosses its nose, with a damage tally for each duel. Helps here because the table's columns (advance, target in arc, dealt to and taken from target) are hard to picture, and several entries on order cost could use it. -->

| Side | Lost | Target in arc | Advance (m/s) | To target (m/s) | Dealt to target | Taken from target | Taken from others | Share on target |
|---|---|---|---|---|---|---|---|---|
| 1052 (parent) | 1.00 | 0.109 | +13.5 | +17.0 | 88 | 118 | 32 | 0.98 |
| control 725 | 0.86 | 0.078 | +11.9 | +15.0 | 88 | 122 | 21 | 0.98 |
| pay025 2200 | 0.53 | 0.110 | +7.9 | +10.9 | 86 | 100 | 10 | 1.00 |
| **kite 2200** | 0.83 | **0.257** | +14.1 | +16.9 | **153** | 145 | 22 | 0.97 |
| **kite 2205** | 0.84 | **0.251** | +13.5 | +16.2 | **146** | 139 | 21 | 0.97 |
| kite_pay025 2200 | 0.46 | 0.082 | +7.5 | +8.3 | 64 | 80 | 14 | 0.98 |
| kite_pay025 2211 | 0.38 | 0.071 | +6.8 | +7.3 | 56 | 74 | 12 | 0.98 |

- **`kite` still charges, and now wins the duel.** It closes on its target at +16 to
  +17 m/s, the same as the parent. What changed is that it keeps the target in its arc
  more than twice as often (0.25 against 0.11) and deals 146 to 153 to it, against 88.
  It deals its target about what the target deals back (146 dealt, 139 taken), where the
  parent, control 725 and pay025 2200 took 1.16 to 1.39 times what they dealt. (Some
  mixed-orders finals also broke even, but they fought far less: 59 dealt or fewer.)
  The plan's diagnosis was that the cost is pursuit. For this arm, pursuit stayed and the
  cost shrank anyway: it got better at the fight the order sends it into.
- **`kite_pay025` looks like the earlier pay025 arm.** It charges less (+7 to +8 m/s),
  fights less in the first 30 s, still takes more from its target than it deals (74 and
  56), and scores about what pay025 did (0.33 against 0.25).
- **Ordered pilots still shoot almost only their target** (0.97 to 0.98). Kite drills did
  not change that.

## Training telemetry (`log.jsonl`)

These are numbers logged during training from the drills the arms actually flew
(`drill_sides`), averaged over windows of updates and weighted by episodes (drills
flown). `attack_kite` is the kite drill, "attack (standard)" the usual attack drill
against script enemies. Pass means the pilots landed some damage on the named target,
which is the drill's check that they understood the order. It says nothing about
surviving, so a drill can pass while the pilot dies. Pilots lost is the share of ordered
pilots killed. Damage is per drill. "Chose neither" is the share of drills in
which the pilots hit neither enemy group: a pilot that hangs back.

| Arm | Drill | Updates | Episodes | Pass | Pilots lost | Dealt to target | Taken from target | Chose neither |
|---|---|---|---|---|---|---|---|---|
| kite | attack_kite | 1–250 | 491 | 0.898 | 0.888 | 128 | 159 | 0.002 |
| kite | attack_kite | 251–725 | 942 | 0.904 | 0.891 | 125 | 159 | 0.003 |
| kite | attack_kite | 726–1500 | 1,641 | 0.903 | 0.885 | 126 | 160 | 0.004 |
| kite | attack_kite | 1501–2200 | 1,348 | 0.885 | 0.877 | 120 | 158 | 0.005 |
| kite | attack (standard) | 1501–2200 | 1,457 | 0.927 | 0.199 | 140 | 63 | 0.027 |
| kite | defend | 1501–2200 | 942 | 0.897 | 0.083 | | | 0.041 |
| kite_pay025 | attack_kite | 1–250 | 498 | 0.916 | 0.896 | 126 | 170 | 0.002 |
| kite_pay025 | attack_kite | 251–725 | 939 | 0.913 | 0.888 | 123 | 164 | 0.009 |
| kite_pay025 | attack_kite | 726–1500 | 1,635 | 0.888 | 0.883 | 126 | 161 | 0.004 |
| kite_pay025 | attack_kite | 1501–2200 | 1,365 | 0.896 | 0.886 | 126 | 156 | 0.004 |
| kite_pay025 | attack (standard) | 1501–2200 | 1,467 | 0.938 | 0.176 | 142 | 61 | 0.014 |
| kite_pay025 | defend | 1501–2200 | 955 | 0.850 | 0.079 | | | 0.029 |

Go-to drill success over updates 1501–2200: `kite` goto 0.783 (3,724 drills),
`kite_pay025` 0.763 (3,778).

- **Kite drills stay hard and do not get easier.** In both arms about 89% pass, but 88% of
  the ordered pilots die and they take about 1.25 times what they deal to the target. That
  holds from the first 250 updates to the last 700. A flat line need not mean nothing was
  learned. The kite-drill enemy is drawn from the pool, which keeps adding this run's own
  newer checkpoints, and the draw (PFSP, prioritized fictitious self-play) favours the
  opponents that beat the learner. So the enemy gets stronger as the learner does. Even so, the telemetry does not show the gain that the test against a free 1052 shows.
- **Nobody learned to hang back.** `chose_neither` on kite drills stays at 0.002 to 0.009.
- Standard attack and defend drills look as they do in earlier runs (pass 0.93, 0.85 to
  0.90).

## Drill bars

`spacefight.eval.drills --n-per-kind 64`, bars in `spacefight/eval/drill_bars.yaml`. The
drill test plays standard drills against script enemies (no kite drills) and checks that a
pilot still does what each order says. Each row is a share of drills, and the gate passes
when every row clears its bar. goto_arrival is the share of ships that reach a go-to
point by its deadline, and goto_lift that share minus the share with the order hidden.
attack_target_hit is any damage on the named target. attack_side and defend_side: the
squad went to the named side. attack_flip and defend_flip are the swap test: the same
start with the other side named, and the squad chose the named side both times.
defend_more_on_named: in a defend drill, where two friendly ships (wards) are under attack
and one is named, the named ward's attackers took more damage than the other ward's.

| Bar | Pass mark | 1052 | kite 2200 | kite 2205 | kite_pay025 2200 | kite_pay025 2211 |
|---|---|---|---|---|---|---|
| goto_arrival | 0.60 | 0.851 | 0.859 | 0.835 | 0.810 | 0.857 |
| goto_lift | 0.40 | 0.672 | 0.713 | 0.679 | 0.637 | 0.689 |
| attack_target_hit | 0.90 | 0.961 | 0.977 | 0.961 | 0.969 | 0.945 |
| attack_side | 0.75 | 0.938 | 0.984 | 0.969 | 0.906 | 0.898 |
| attack_flip | 0.70 | 0.875 | 0.969 | 0.938 | 0.844 | 0.828 |
| defend_more_on_named | 0.85 | 0.945 | 0.922 | 0.883 | 0.836 (**missed**) | 0.867 |
| defend_side | 0.85 | 0.961 | 0.969 | 0.977 | 0.898 | 0.906 |
| defend_flip | 0.75 | 0.922 | 0.938 | 0.953 | 0.797 | 0.812 |
| Gate | | pass | pass | pass | fail | pass |

`kite` is at or above the parent on every attack bar. `kite_pay025` is the weaker of the
two arms on every attack and defend bar, at both updates. It misses
defend_more_on_named at 2200 by 0.014, inside the noise of 128 drills, and passes at its
final.

## Verdict in detail

The plan set its marks before the run. Success: ordered (`nearest`, against a free 1052)
**>= 0.40** at both 2200 and the end; free (`none`) **>= 0.55**; and the drill gate passed,
with attack_flip within 0.05 of 1052's (0.875). Failure: both arms ordered **< 0.30**.

`kite` meets every success mark. Ordered, it scores 0.474 at update 2200 and 0.421 at its
final 2205. Free, it scores 0.561 and 0.566. It passes the drill gate at both, with
attack_flip 0.969 and 0.938. `kite_pay025` scores 0.325 and 0.330 ordered, which is above
the failure mark (0.30) and below success. Its 2200 checkpoint misses the gate on
defend_more_on_named (0.836, bar 0.85).

## What we learned

- **An attack drill against a pilot that fights back moved the ordered score for the first
  time.** `kite` scores 0.42 and 0.47 ordered against a free 1052, more than three times
  the parent's score and 0.08 to 0.13 above the best of 13 mixed-orders checkpoints
  (0.345), at a normal free strength and with the drill gate passed.
- **It did not do it by stopping pursuit.** `kite` charges its target as hard as 1052 does,
  and still shoots almost only its target. It now wins that exchange: twice the time on
  target and about 1.7 times the damage. The fix for the order's cost may be to make the
  ordered fight winnable, not to stop the chase.
- **The quarter order pay in matches did not help here.** `kite_pay025` scored 0.33
  ordered against 1052 and is weaker on drill bars. It is cost-free against f995_701,
  which `kite` is not. One seed per arm can't separate the setting from the seed.
- **Drill telemetry doesn't track it.** Kite drills stay at about 88% of pilots lost the
  whole run, in both arms, so watch the test against a
  free pilot, not training logs, for this.
- Not measured: update 725, a second seed of `kite`, a 2 v 2, and a WAR rating (wins
  above replacement: how many more matches in 100 a side wins with this pilot flying
  instead of the script). Under the plan, `kite` 2200 or 2205 can go into the population's
  WAR as a candidate (the population is the record of every pilot trained under these
  rules).

## Files

Where the raw results are, for anyone reproducing them.

- `eval_final/` (updates 2205 and 2211) and `eval_2200/`:
  `<ckpt>_v_{base1052,f995_701}_{nearest,none,scripted}.json|.out` are the cross-pilot
  measure, and `<ckpt>_drills.json|.out` the drill eval. Run on Beast at `SIM_VERSION` 9
  with `THREADS=1`, 14 jobs at once, about 920 s each.
- `eval_final.log`, `eval_2200.log`: the score lines of each eval batch.
- Not in git: the run directories `kite/` and `kite_pay025/` (log.jsonl, config.yaml,
  checkpoints) and the supervisor's `run_beast.out`, all on Beast.
