# Kite drills

Prepared 2026-11-18, 14:50, on Beast. The laptop session chose the run, with a second
opinion; the owner is asleep. The laptop launches it.

## Question

Does training on attack drills whose target falls back make an order cheap to follow in a
fleet fight?

The working diagnosis (`lab/runs/2026-11-17-order-cost/results.md`, and the mixed-orders
run's `eval_cross/`): what an order costs is **pursuit**. An ordered pilot keeps closing
on a side that backs away (+8 to +14 m/s toward it, where free pilots fall back) and loses
the exchange with its target, taking 1 to 2.3 times what it deals to it. Training never
punishes this. Every drill enemy is the script, and the script does not fall back. In most
attack drills the target is busy with a freighter. Attack drills are a few percent of
episodes, and the match result is heavily discounted 30 s out. Mixed-condition matches did
not fix it (`mixed_all` 2250, nearest 0.18 against free 1052), and neither did order pay
in matches cut to 0 or a quarter (`pay0` 2200 0.22, `pay025` 2200 0.25, at 0.61 and 0.45
free).

## The new key

`drill_attack_pool_share` in `pilots_v1`'s `roster_overrides`, default 0
(`docs/PILOT_TRAINING.md` §2, "Kite drills"): the share of attack drills that are **kite
drills**. A kite drill is the attack drill's `charging` layout: no freighters, two groups
of 1 to 3 on opposite sides 260 to 340 m out, one member of one group named, so the target
has no task and room to fall back. The clock is 60 s instead of 30 s. The whole enemy team
is flown by one frozen pool entry, drawn as a snapshot match's enemy is (`pool_seed_p`
0.5, PFSP), with its orders hidden. The order, the pass rule (any damage on the named
target) and the pay are the standard attack drill's, and death is not newly charged. So a
pilot that charges a kiting pilot and dies is paid less only because it deals less and
takes more, which is what a match would do to it. The drill eval and gate do not play kite
drills.

## Arms

Both are fresh runs from `followers_school_1052`
(`lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt`), with
`--init`. They use followers_school's config (pool seeds, rates, pay, deadline pay 3,
stable `[live]`) with the mixed-orders `control` arm's overrides (drill_share 0.3,
drill_weights `[6, 1, 1]`, commander_p 0.667, mixed_p 0), changing only:

| Arm | drill_share | drill_weights | drill_attack_pool_share | match_order_pay_scale | Where |
|---|---|---|---|---|---|
| `kite` | 0.4 | `[4, 3, 1]` | 0.5 | 1.0 | Beast, `update_device=cuda:0`, 3 + 3 threads |
| `kite_pay025` | 0.4 | `[4, 3, 1]` | 0.5 | 0.25 | Beast, `update_device=cuda:1`, 3 + 3 threads |

Checkpoints every 25 updates. Attack drills go from 1/8 of 0.3 (3.75% of draws) to 3/8 of
0.4 (15%), half of them kite drills (7.5% of draws, and more of the rollout, since their
clock is twice as long). Go-to drills go from 22.5% to 20% of draws.

The comparison for `kite` is the mixed-orders `control` (725: nearest 0.276, none 0.680
against free 1052), and for `kite_pay025` it is `pay025` (2200: 0.25 and 0.45). Those two
had mixed_p 1.0, so `kite_pay025` against `pay025` also differs in mixed_p and the drill
mix. Neither comparison is clean; the bars below are absolute.

## Measures

`eval.sh <out-dir> <name>=<ckpt> ...` on each arm at updates **725, 2200 and the last**:

- **eval_cross** (`order_rules.py --unseen-checkpoint`, 3 v 3, 24 blocks = 1,152 matches a
  row, the 2026-11-17 seeds): the checkpoint ordered by `nearest`, by `scripted` (the
  sim's commander), and unordered (`none`), against **followers_school_1052** flying free,
  and the same three against **f995_701**, a pilot of another family
  (`lab/live_pilots.json`). f995_701 is also a pool seed of both arms, so it may fly kite
  drills' enemies in training.
- **The drill eval** (`spacefight.eval.drills`, 64 a kind) and its gate.
- **Mechanism check**, from the eval_cross JSON (`sides.<side>`, the first 30 s): the
  ordered side's speed toward its target and the enemy fleet, damage dealt to and taken
  from its target, and ships lost. On 2026-11-17 (the four followers, `nearest`, 3 v 3):
  +16.2 m/s toward the target, 127 taken from it against 101 dealt, 0.93 ships lost.
- **During** (`log.jsonl`): `drill_success["attack_kite"]` against `["attack"]`, and
  `drill_sides`: per standard attack, kite and defend drill, pass rate, `pilots_lost`,
  `target_damage`, `damage_from_target`, and `chose_neither`. Watch `chose_neither` on
  kite drills: a pilot that learns to hang back and not engage at all shows there before
  it shows in the gate.

## Bars

- **Success:** ordered (`nearest`, against free 1052) **>= 0.40** at both 2200 and the
  end; free (`none`) **>= 0.55**; and the standard drill gate passes with attack flip
  within 0.05 of 1052's (0.875).
- **Failure:** both arms ordered **< 0.30**. Then the conclusion is to stop working on
  order cost for now.
- Between the two: report it, with the mechanism check, and the laptop decides.
- The same rows against f995_701 say whether a gain is about 1052 or about free pilots.
  Not tested here: a rating. An arm that passes goes into the population's WAR like any
  other member.

## Launch

The laptop runs it (Beast is free after task 06's evals):

```
DEADLINE="<when>" nohup setsid lab/runs/2026-11-18-kite-drills/run.sh \
    > lab/runs/2026-11-18-kite-drills/run_beast.out 2>&1 &
```

`SMOKE=1 ARMS=kite` runs tiny sizes into `smoke/`.
