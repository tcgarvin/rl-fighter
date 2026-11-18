# Mixed-condition matches

Prepared 2026-11-18, 00:20, on Beast. The laptop session chose the run; the owner is
asleep. Training stops at 15:00.

## Question

Does training in matches where one side sees its orders and the other does not make an
order cheap to follow?

The order-cost measure (`lab/runs/2026-11-17-order-cost`) found that ordering every ship
of a 3 v 3 onto its own nearest enemy drops it to 0.22 against the same pilots with their
orders hidden, the same cost as the script's orders (0.24). Every training match so far
gives both sides the same condition (`docs/PILOT_TRAINING.md` §3). So no ordered pilot
has met a free side that falls back and picks its shots, and no free pilot has met an
ordered one.

## The new key

`mixed_p` in `pilots_v1`'s `roster_overrides`, an experiment, default 0
(`docs/PILOT_TRAINING.md` §3). Of the matches `commander_p` shows on both sides, a share
`mixed_p` hides one side's orders instead, the side drawn at random. The learner plays
either side, the match result is paid, and order pay goes only to the side that sees its
orders. No eval, round robin or rating changes: they keep both sides on one condition.

## Arms

All three are fresh runs from `followers_school_1052`
(`lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt`), with
`--init`. They use followers_school's config (pool seeds, rates, pay, deadline pay 3,
stable `[live]`), changing only:

| Arm | drill_share | commander_p | mixed_p | Where |
|---|---|---|---|---|
| `control` | 0.3 | 0.667 | 0.0 | the laptop, CPU, 6 + 6 threads |
| `mixed` | 0.3 | 0.667 | 0.5 | Beast, `update_device=cuda:0`, 3 + 3 threads |
| `mixed_all` | 0.3 | 0.667 | 1.0 | Beast, `update_device=cuda:1`, 3 + 3 threads |

Checkpoints every 25 updates. Drill weights stay `[6, 1, 1]`. followers_school ran a drill
share of 0.7. All three arms drop it to 0.3 on purpose, so more training rows carry orders
in real matches. The control is there to tell the effect of that change apart from the
effect of `mixed_p`.

Of the non-drill matches: `control` is 2/3 shown on both sides and 1/3 hidden on both;
`mixed` is 1/3 shown, 1/3 mixed, 1/3 hidden; `mixed_all` is 2/3 mixed and 1/3 hidden, so
it never sees both sides ordered.

A fresh run starts a fresh Adam state and snapshot pool, with the copied config's critic
warm-up (20 updates) and early clip (50 updates). The three arms share them, so they
compare like for like. They do not continue followers_school's update count.

## Measures

Before (`eval_before/`, `eval_before.sh`, on `followers_school_1052`):

- The order-cost measure, `order_rules.py --k 3 --blocks 24` with `--checkpoint`, one
  pilot flying both sides: `nearest`, `none` (the control, about 0.50) and `scripted`.
  1,152 matches each on the 2026-11-17 seeds, so the scores pair match by match with
  every later checkpoint.
- The drill eval (`spacefight.eval.drills`, 64 a kind) and its gate.

Measured 2026-11-18, 00:20, with `followers_school_1052` flying both sides: `nearest`
**0.136** ± 0.020, `none` 0.503 ± 0.029, `scripted` 0.200 ± 0.023. Paired against `none`,
`nearest` is −0.367 ± 0.035 and `scripted` −0.303 ± 0.037. That is worse than the four
followers together on 2026-11-17 (0.22). The drill gate passes on every bar (go-to arrival
0.851, lift 0.672; attack target hit 0.961; defend 0.945).

During (log.jsonl): `win_mixed_ordered` and `win_mixed_hidden` (the learner's score in
mixed matches, by its side), `win_by_condition`, drill success, `drill_goto_missed`.

After: the same two measures on each arm's last checkpoint (`CKPT=... NAME=... OUT=...
eval_before.sh`).

## Bars

- **The cost.** `nearest` k3, paired against `none` k3 on the same checkpoint. The parent
  scores 0.22 against 0.52 on the 2026-11-17 pilot list (its own number is in
  `eval_before/`). A `mixed` arm that halves the gap to `none` against `control` has
  answered yes. A gap inside ±0.05 of the control's has answered no.
- **No regression in drills.** The drill gate still passes. Go-to in time stays within
  0.05 of the parent's.
- **The hidden side does not just win.** If `win_mixed_hidden` stays far above 0.5 all
  run and the cost does not move, the ordered side is not learning from losing. That
  shows in `win_mixed_ordered`.
- Not tested here: a rating. If an arm passes, it goes into the population's WAR like
  any other member.

## Part 2: order pay in matches

Prepared 2026-11-18, 07:45, on Beast. The laptop session chose it; training stops at 19:00.

**Why.** The laptop's cross-pilot measure (`eval_cross/`, each checkpoint against
`followers_school_1052` flying free, 3 v 3, 1,152 matches) found mixed matches did not
make an order cheap: with nearest orders control 725 scored 0.28, mixed 725 0.21,
mixed_all 725 0.16, mixed 2250 0.19, mixed_all 2250 0.18. `mixed` and `mixed_all` were
stopped at updates 2459 and 2548.

**Question.** Does order pay in matches (under an attack order a hit on the target pays
double a hit on anyone else) keep an ordered pilot dueling its target? Drills keep their
order pay: it is what fixes what an order means.

**The new key.** `match_order_pay_scale` (trainer, default 1.0, `docs/PILOT_TRAINING.md`
§3): order pay on the rows of matches that are not drills is multiplied by it; drill rows
are unchanged. Go-to shaping is part of the sim's order pay, so it scales too. Logs
`reward_order_drill` and `reward_order_match`.

| Arm | drill_share | commander_p | mixed_p | match_order_pay_scale | Where |
|---|---|---|---|---|---|
| `pay0` | 0.3 | 0.667 | 1.0 | 0.0 | Beast, `update_device=cuda:0`, 3 + 3 threads |
| `pay025` | 0.3 | 0.667 | 1.0 | 0.25 | Beast, `update_device=cuda:1`, 3 + 3 threads |

Fresh from `followers_school_1052` with `--init`, everything else as `mixed_all`. The
comparison is `mixed_all` (pay 1.0) at the same update.

**Measures and bars.** As part 1, plus the cross-pilot measure (`eval_cross.sh`): an
arm that lifts its nearest-orders score against free `followers_school_1052` clearly
above `mixed_all`'s at the same update has answered yes; the drill gate must still pass.
