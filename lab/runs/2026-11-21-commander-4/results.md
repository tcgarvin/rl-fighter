# Commander 4: learned commanders still help most by giving few orders

Three ideas for a commander that helps its side, one night on the laptop, `SIM_VERSION` 11.
None of them beat the side that gets no orders. `kite` and `noattack` climbed from 0.33
to level with it by giving fewer orders, as commander 3 did. The station's defender,
started from a launch prior close to the best hand rule, trained that prior away in every
run, with or without an entropy bonus. No rule of the game changed.

<!-- summary: Three commanders trained for a night. Two of them, one over the kite-drilled pilots and one that could not give attack orders, climbed from 0.33 to level with the side that gets no orders by giving almost none. The third, the station's defender, started from a launch habit close to the best hand rule (attacker wins 0.16 against 0.32 with no orders) and in four runs trained it away, toward launching the whole hangar at 2 s (0.38 to 0.42). Removing the entropy bonus did not stop it. Measured on the same matches, no commander 4 checkpoint beats commander 3's live 197 clearly enough to replace it as the start of the long commander run. -->

The [plan](plan.md) has the arms, the reasons for each, and the notes written during the
night. "Unseen" is the scripted commander with its orders hidden from its own pilots: the
side with no orders. A commander that gives no orders scores about 0.50 against it.

## `kite` and `noattack`: level with no orders, by going quiet

`spacefight.commander.eval` against unseen, 384 matches a mission over the four missions
(1,536 a row, about ±0.025). "Own pilots" is each arm's training list: the two kite
pilots for `kite`, commander 3's four followers for `noattack`.

| Commander | Pilots | Wins | Deathmatch | Carrier | Convoy | Station | Time under an order |
|---|---|---|---|---|---|---|---|
| `kite` 190 | own | **0.496** | 0.49 | 0.52 | 0.49 | 0.49 | 10% |
| `kite` 190 | live ten | 0.465 | 0.52 | 0.38 | 0.50 | 0.45 | 10% |
| `noattack` 174 | own | 0.453 | 0.48 | 0.41 | 0.52 | 0.40 | 0.4% |
| `noattack` 174 | live ten | **0.489** | 0.53 | 0.50 | 0.49 | 0.43 | 0.3% |
| Commander 3 `live` 197 | live ten | 0.460 | 0.52 | 0.39 | 0.51 | 0.42 | 5% |
| Scripted | `kite`'s two | 0.371 | 0.42 | 0.27 | 0.44 | 0.36 | 92% |
| Scripted | the four followers | 0.280 | 0.35 | 0.10 | 0.22 | 0.45 | |

- **Both climbed by ordering less.** Over the night `kite`'s ship time under an order fell
  from 49% to 10%, and its trainer's win rate against unseen rose from 0.32 to about 0.5.
  `noattack` fell from 41% to almost nothing and rose from 0.33 to about 0.47.
- **The kite pilots make orders cheaper, not worth giving.** The scripted commander loses
  less over the kite pilots (0.37) than over the followers (0.28), so an order costs them
  less. But `kite` still did best by giving few. In its last updates, a change of order
  was "no order" three times in four, and most of the rest were attack orders.
- **Without attack orders there was nothing left to give.** `noattack` could still order
  go-to and defend, and it learned to give neither.
- **None is clearly ahead of commander 3's `live` 197 over the live ten.** `noattack` is
  0.03 above, mostly in the carrier battle, but its attack ban is built into its weights
  (a fixed −30 on that choice). A run started from it could never learn attack orders. So
  the [long commander run](../2026-11-21-commander-long/plan.md) keeps `live` 197 as its
  start.

## The station's defender: every run trained away a good launch habit

Four runs on the citadel, always the defender, started from commander 3's `live` 197 with
its launch head reset to launch each hull class on 3% of decisions: `hold` (twice, the
second by accident, see below), `hold_quiet` (orders forbidden, launch timing only), and
`hold_ent0` (`hold_quiet` with no entropy bonus). Each cell is 512 matches on the
preflight's seeds, paired with the hand rules' cells. The table shows the attacker's wins,
so lower is better for the defender (± 1.96 standard errors).

| Defender | Attacker wins | First launch, median | Hangar empty, median |
|---|---|---|---|
| No orders (the script's launches) | 0.322 ± 0.041 | 3 s | 7 s |
| `hold_late` (hand rule) | **0.133** ± 0.029 | 57 s | 59 s |
| Update 0 (the launch prior alone) | **0.158** ± 0.032 | 9 s | 76 s |
| `hold_quiet` 10 / 30 / 57 | 0.191 / 0.283 / 0.404 | 5 / 2 / 2 s | 36 / 15 / 5 s |
| `hold`, second run, 10 / 56 | 0.191 / 0.422 | 4 / 2 s | 32 / 7 s |
| `hold`, first run, 68 | 0.383 | 2 s | 9 s |
| `hold_ent0` 10 / 30 / 108 | 0.213 / 0.277 / 0.381 | 4 / 3 / 2 s | 33 / 18 / 7 s |

- **The prior was nearly as good as the best hand rule**, and every run moved away from
  it, toward launching the whole hangar at 2 s. By the end each was worse than no orders.
- **The entropy bonus was not the cause.** `hold_ent0` had none and slid the same way, on
  the same curve. The night's guess about the bonus (plan, "08:25") is wrong.
- **What is left is the signal.** An update sees about 25 station matches. Each is won or
  lost a minute after the launches that decided it, and that one result is shared by
  every decision in the match. A policy that starts near the best rule then mostly takes
  noisy steps, and from near the top most steps lead down. Holding is a choice made at
  many decisions in a row, so it is also the easiest habit for noise to wear away.
  Untested fixes: choose a hold time once per hull class, or play far more matches an
  update. Both are shortcuts of the kind the owner asked to set aside for long runs on
  the defaults, so neither is scheduled.

## What went wrong in the night

Editing `run.sh` at 05:10, while two copies of it were running, made bash read the
edited file part-way through. At 05:10 the copy that started `hold` launched it again
from update 1. That second run overwrote the first run's checkpoints 10 to 50 and ran as
an unplanned fourth trainer until 07:55. At 10:30 the other copy, when `kite` and
`noattack` stopped, started `noattack` again. That overwrote its resume state and log
before it was stopped. Its final weights (174) and training log were not affected. Run
scripts are no longer edited while running, and new launchers end in `exec`.

## What goes live

Nothing changes on the live page. A commander level with no orders adds no measured
gain to the live stable. The long commander run on Beast takes it from here: one learner
on the trainer's defaults, for days, from `live` 197.
