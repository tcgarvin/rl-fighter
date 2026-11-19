# Kite drills: the `kite` arm follows an order at 0.42 to 0.47 against a free 1052

Verdict: **PASS** for `kite`. `kite_pay025` lands between the bars. Ordered onto its nearest
enemy in a 3 v 3 against `followers_school_1052` flying free, `kite` scores 0.474 at
update 2200 and 0.421 at its final 2205. Free, it scores 0.561 and 0.566, and it passes
the drill gate at both (attack_flip 0.969 and 0.938, 1052's is 0.875). Those meet
plan.md's success bars (ordered >= 0.40 at 2200 and the end, free >= 0.55, gate with
attack_flip within 0.05). `kite_pay025` scores 0.325 and 0.330 ordered, which is above the
failure bar (0.30) and below success. Its 2200 checkpoint misses the gate on
defend_more_on_named (0.836, bar 0.85). Each arm is one seed. The rules didn't change
during the run: it trained at `SIM_VERSION` 8 and was measured at 9, and the old missions
play bit-identically at 9.

<!-- summary: We trained pilots on attack drills whose target is a frozen pool pilot that can back away and fight back, to see whether an order would stop costing a fleet fight. One arm (kite) now wins 0.42 to 0.47 of 3 v 3 games against a free 1052 when ordered onto its nearest enemy, against 0.14 for the parent and 0.14 to 0.35 for every earlier arm. It still charges its target as hard as before, but now wins that duel; the arm that also cut match order pay to a quarter did not improve as much (0.33). -->

The plan is in [plan.md](plan.md). Both arms start fresh from `followers_school_1052`
with drill_share 0.4, drill_weights `[4, 3, 1]` and `drill_attack_pool_share` 0.5. Half
of all attack drills are kite drills: no freighters, and the whole enemy team is a frozen
pool pilot whose orders are hidden from it. `kite_pay025` also sets
`match_order_pay_scale` 0.25. Both ran on Beast (cuda:0 and cuda:1, 3 + 3 threads, about
10.5 s an update) from 22:28 until the 05:00 deadline, and stopped at updates **2205**
(`kite`) and **2211** (`kite_pay025`). Update 725 was not measured; the time before the
next run only covered 2200 and the finals.

## The cost, against a free pilot

The measure is `eval.sh` → `order_rules.py --k 3 --blocks 24`: 3 v 3 games of one hull,
1,152 matches a cell on the 2026-11-17 seeds. The checkpoint's side is ordered by
`nearest` (each ship onto its nearest enemy) or by `scripted` (the sim's commander), or
it gets no orders (`none`). The other side is a free pilot whose scripted orders are
hidden from it. The ± is 1.96 standard errors. Cost is nearest minus none, paired match
by match. Earlier rows are from `lab/runs/2026-11-18-mixed-orders/` (the parent's from its
`eval_before/`, 1052 on both sides).

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

| Checkpoint | No orders | Nearest | Scripted commander | Cost (paired) |
|---|---|---|---|---|
| kite 2200 | 0.647 ± 0.028 | 0.465 ± 0.029 | 0.464 ± 0.029 | −0.182 ± 0.036 |
| kite 2205 (final) | 0.631 ± 0.028 | 0.465 ± 0.029 | 0.438 ± 0.029 | −0.166 ± 0.039 |
| kite_pay025 2200 | 0.646 ± 0.028 | **0.641** ± 0.028 | 0.618 ± 0.028 | −0.005 ± 0.039 |
| kite_pay025 2211 (final) | 0.588 ± 0.028 | **0.622** ± 0.028 | 0.596 ± 0.028 | +0.034 ± 0.039 |

No earlier checkpoint was measured against f995_701, so these rows have nothing to
compare with yet.

- **`kite` is the first arm above 0.40 ordered.** 0.474 and 0.421, against 0.136 for the
  parent and 0.14 to 0.35 for all 13 checkpoints of the mixed-orders run. Its free score
  (0.56) sits in the middle of the earlier arms' range (0.36 to 0.83), so the gain did not
  come from a stronger free pilot. The cost against 1052 is −0.09 and −0.15, the smallest
  measured for a pilot that is not weak free.
- **The two arms disagree on which opponent the order costs against.** `kite` keeps a cost
  of about −0.17 against f995_701 (0.47 ordered, 0.63 to 0.65 free). `kite_pay025` follows
  an order for free against f995_701 (0.64 and 0.62 ordered, −0.01 and +0.03 cost), but
  pays −0.24 against 1052. f995_701 is a pool seed of both arms, so either arm may have
  met it as a kite-drill enemy. With one seed per arm, this does not say whether the
  difference comes from the arm's settings or from its seed.
- **The scripted commander's orders cost more than `nearest` for `kite`** (0.34 to 0.37
  against 1052) and less for `kite_pay025` (0.38 to 0.43). Both are above the parent's
  0.200.
- **2200 and the final are 5 to 11 updates apart.** They differ by up to 0.05 on the
  ordered score, which shows how noisy one checkpoint is, not a trend.

## What the ordered side does (first 30 s, 3 v 3, `nearest`, against free 1052)

These come from the JSONs' `sides.ordered`. Lost is ships per match. Arc shares are of a
ship's time alive. Advance is speed toward the enemy fleet's centroid, and "to target" is
speed toward the ship's own target. Damage is per match. "Share on target" is damage
dealt to the target over all damage dealt.

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

`drill_sides`, weighted by episodes over update windows. Pass is any damage on the named
target. Lost is the share of ordered pilots killed. Damage is per drill.

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

Drill success over updates 1501–2200: `kite` goto 0.783 (3,724 drills), `kite_pay025`
0.763 (3,778).

- **Kite drills stay hard and do not get easier.** In both arms about 89% pass, but 88% of
  the ordered pilots die and they take about 1.25 times what they deal to the target. That
  holds from the first 250 updates to the last 700. The enemy is a pool snapshot drawn by
  PFSP, so it gets stronger as the pool grows, and a flat line can still hide learning.
  Even so, the telemetry does not show the gain the cross eval shows.
- **Nobody learned to hang back.** `chose_neither` on kite drills stays at 0.002 to 0.009.
- Standard attack and defend drills look as they do in earlier runs (pass 0.93, 0.85 to
  0.90).

## Drill bars

`spacefight.eval.drills --n-per-kind 64`, bars in `spacefight/eval/drill_bars.yaml`.

| Bar | 1052 | kite 2200 | kite 2205 | kite_pay025 2200 | kite_pay025 2211 |
|---|---|---|---|---|---|
| goto_arrival | 0.851 | 0.859 | 0.835 | 0.810 | 0.857 |
| goto_lift | 0.672 | 0.713 | 0.679 | 0.637 | 0.689 |
| attack_target_hit | 0.961 | 0.977 | 0.961 | 0.969 | 0.945 |
| attack_side | 0.938 | 0.984 | 0.969 | 0.906 | 0.898 |
| attack_flip | 0.875 | 0.969 | 0.938 | 0.844 | 0.828 |
| defend_more_on_named | 0.945 | 0.922 | 0.883 | 0.836 (**missed**) | 0.867 |
| defend_side | 0.961 | 0.969 | 0.977 | 0.898 | 0.906 |
| defend_flip | 0.922 | 0.938 | 0.953 | 0.797 | 0.812 |
| Gate | pass | pass | pass | fail | pass |

`kite` is at or above the parent on every attack bar. `kite_pay025` is the weaker of the
two arms on every attack and defend bar, at both updates. It misses
defend_more_on_named at 2200 by 0.014, inside the noise of 128 drills, and passes at its
final.

## What we learned

- **An attack drill against a pilot that fights back moved the ordered score for the first
  time.** `kite` scores 0.42 and 0.47 ordered against a free 1052, more than three times
  the parent's score and 0.08 to 0.13 above the best of 13 earlier checkpoints (0.345), at a normal free
  strength and with the drill gate passed.
- **It did not do it by stopping pursuit.** `kite` charges its target as hard as 1052 does,
  and still shoots almost only its target. It now wins that exchange: twice the time on
  target and about 1.7 times the damage. The fix for the order's cost may be to make the
  ordered fight winnable, not to stop the chase.
- **The quarter order pay in matches did not help here.** `kite_pay025` scored 0.33
  ordered against 1052 and is weaker on drill bars. It is cost-free against f995_701,
  which `kite` is not. One seed per arm can't separate the setting from the seed.
- **Drill telemetry doesn't track it.** Kite drills stay at about 88% of pilots lost the
  whole run, in both arms, so watch the cross eval, not training logs, for this.
- Not measured: update 725, a second seed of `kite`, a 2 v 2, and a WAR rating. Under the
  plan, `kite` 2200 or 2205 can go into the population's WAR as a candidate.

## Files

- `eval_final/` (updates 2205 and 2211) and `eval_2200/`:
  `<ckpt>_v_{base1052,f995_701}_{nearest,none,scripted}.json|.out` are the cross-pilot
  measure, and `<ckpt>_drills.json|.out` the drill eval. Run on Beast at `SIM_VERSION` 9
  with `THREADS=1`, 14 jobs at once, about 920 s each.
- `eval_final.log`, `eval_2200.log`: the score lines of each eval batch.
- Not in git: the run directories `kite/` and `kite_pay025/` (log.jsonl, config.yaml,
  checkpoints) and the supervisor's `run_beast.out`, all on Beast.
