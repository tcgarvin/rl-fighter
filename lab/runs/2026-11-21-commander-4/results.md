# Commander 4: learned commanders still help most by giving few orders

A commander is the network (or script) that sees a whole side and decides when to launch
its ships and what to order them to do. We have yet to train one that makes its side win
more than the same pilots given no orders at all. This night on the laptop, at
`SIM_VERSION` 11 (the eleventh version of the game's rules), tried three ideas, one
commander each: `kite`, over pilots drilled so that an attack order costs them less;
`noattack`, which cannot give attack orders at all; and a defender of the citadel (the
big space station) started with a habit of keeping its reserve ships in the hangar, the
one commander decision that hand-written rules had shown to win. None of them beat the
side that gets no orders. `kite` and `noattack` climbed from winning 0.33 of their
matches against that side to level with it, by giving fewer orders, as
[commander 3](../2026-11-15-commander-3/results.md) did. The station's defender, started
from a launch habit close to the best hand rule, trained that habit away in every run, with or without an entropy bonus (a reward for keeping some
randomness in its choices while it learns). No rule of the game changed.

<!-- summary: Three commanders trained for a night. Two of them, one over the kite-drilled pilots and one that could not give attack orders, climbed from 0.33 to level with the side that gets no orders by giving almost none. The third, the station's defender, started from a launch habit close to the best hand rule (attacker wins 0.16 against 0.32 with no orders) and in four runs trained it away, toward launching the whole hangar at 2 s (0.38 to 0.42). Removing the entropy bonus did not stop it. Measured on the same matches, no commander 4 checkpoint beats commander 3's best (`live` 197) clearly enough to replace it as the start of the long commander run. -->

## Where this fits

RL Fighter is a space-combat game in which every small ship is flown by a neural network,
a pilot, that learned to fly by trial and error. Above the pilots each side has a
commander (the [commander page](/commander/) explains how one works). Orders can be
attack (a named enemy), defend (stay near a friendly ship), go-to (fly to a point) or
none. The nights before this one set up three leads:

- [Commander 3](../2026-11-15-commander-3/results.md): given the choice, commanders
  learned to stop giving orders and ended level with a side that gets none.
- [The order-cost night](../2026-11-17-order-cost/results.md) and
  [order kinds](../2026-11-19-order-kinds/results.md) found why. An attack order cuts a
  side's win rate in a 3 v 3 fight (three ships a side) by about 0.3, because an ordered
  pilot charges its target and shoots nothing else. A go-to costs little, and defend depends on the
  hull. [Kite drills](../2026-11-18-kite-drills/results.md) then made an attack order much
  cheaper for one pilot, `kite_2205`.
- [Station rules](../2026-11-19-station-rules/results.md) found the only commander
  decision measured to win: the station's defender holding its reserve in the hangar
  instead of launching it at once. A learned
  [station commander](../2026-11-19-station-commander/results.md) did not find it.

So each arm of this night (one version of the experiment, here one commander in
training) follows one lead. On Beast, the lab's desktop with two graphics cards, the
same night [orderable pilots](../2026-11-21-orderable-pilots/results.md) trained the other half: a
pilot that both takes an attack order cheaply and comes home when recalled.

<div data-figure="diagram" data-name="orders" data-caption="Each arm of this night trains a learned commander. Besides its orders it decides which reserve ships launch, which the picture leaves out. It cannot send the dock order, which only the scripted commander gives."></div>

The [plan](plan.md) has the arms, the reasons for each, and the notes written during the
night. "Unseen" is the scripted commander (the hand-written one) with its orders hidden
from its own pilots: the side with no orders. A commander that gives no orders scores
about 0.50 against it. The ± in this entry is the margin of error: the true value very
likely lies within that range. A commander's name is its arm followed by the update (one
round of training) it was saved at.

## `kite` and `noattack`: level with no orders, by going quiet

`spacefight.commander.eval` against unseen, 384 matches a mission over the four missions
(1,536 a row, about ±0.025). The four missions are team deathmatch (small ships only,
last side standing), carrier battle (each side has a carrier, and a side wins by
destroying the other's), convoy escort (one side guards freighters, the other attacks
them) and station assault (one side defends the citadel, the other attacks it with a
carrier, bombers and a dreadnought, a heavy warship). Each number is the share of matches the commander's side won
against unseen, overall and by mission. "Time under an order" is the share of its ships'
time spent under an order. "Own pilots" is each arm's training list: the two kite pilots
for `kite` (`kite_2205` and `kite_pay025_2211`, from the kite drills), commander 3's four
followers (the four pilots that followed orders best) for `noattack`. "Live ten" is the
ten pilots that fly on the website's front page. Commander 3's `live` 197 is that night's
arm trained over the live ten, saved at update 197; the name is the arm's, and it did not
fly on the live page.

<div data-figure="diagram" data-name="unseen-side" data-caption="Every number in the table below is a share of matches won against this side."></div>

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
  from 49% to 10%, and its win rate against unseen in training rose from 0.32 to about 0.5.
  `noattack` fell from 41% to almost nothing and rose from 0.33 to about 0.47.
- **The kite pilots make orders cheaper, not worth giving.** The scripted commander loses
  less over the kite pilots (0.37) than over the followers (0.28), so an order costs them
  less. But `kite` still did best by giving few. In its last updates, a change of order
  was "no order" three times in four, and most of the rest were attack orders.
- **Without attack orders there was nothing left to give.** `noattack` could still order
  go-to and defend, and it learned to give neither.
- **None is clearly ahead of commander 3's `live` 197 over the live ten.** `noattack` is
  0.03 above, mostly in the carrier battle, but its attack ban is built into its weights
  (a large fixed penalty on that choice's score, so the network never picks it). A run started from it could never learn attack orders. So
  the [long commander run](../2026-11-21-commander-long/results.md) keeps `live` 197 as
  its start.

## The station's defender: every run trained away a good launch habit

Four runs played the citadel's station assault, always as the defender. Each started
from commander 3's `live` 197 with its launch head (the part of the network that decides
launches) reset. A learned commander decides once a second, and the reset head launches
each hull class (type of ship) at only 3% of those decisions, so a reserve waits about
33 s on average and holding it back is what the commander tries first. The runs were
`hold` (twice, the second by accident, see below), `hold_quiet` (orders forbidden, launch
timing only), and `hold_ent0` (`hold_quiet` with no entropy bonus). The yardstick is
`hold_late`, the best hand rule from the station-rules night: launch nothing until the
station's hull is below 60%, then launch everything. Each cell is 512 matches, and every
row uses the same 512 starting layouts, so rows compare match for match. The table shows
the attacker's wins, so lower is better for the defender (± 1.96 standard errors). "First
launch" is when the defender first launched a reserve ship, and "hangar empty" when its
last one left, in seconds from the start. A row such as `hold_quiet` 10 / 30 / 57 gives
the checkpoints (saved copies of the network) at updates 10, 30 and 57.

<!-- figure-idea: a launch timeline for the citadel's defender: the script empties its hangar by 7 s, hold_late waits until about 57 s, the update-0 habit launches a first ship at 9 s and keeps part of the reserve past a minute, and the trained runs end up launching everything at 2 s, each with its attacker win rate beside it. -->

| Defender | Attacker wins | First launch, median | Hangar empty, median |
|---|---|---|---|
| No orders (the script's launches) | 0.322 ± 0.041 | 3 s | 7 s |
| `hold_late` (hand rule) | **0.133** ± 0.029 | 57 s | 59 s |
| Update 0 (the launch prior alone) | **0.158** ± 0.032 | 9 s | 76 s |
| `hold_quiet` 10 / 30 / 57 | 0.191 / 0.283 / 0.404 | 5 / 2 / 2 s | 36 / 15 / 5 s |
| `hold`, second run, 10 / 56 | 0.191 / 0.422 | 4 / 2 s | 32 / 7 s |
| `hold`, first run, 68 | 0.383 | 2 s | 9 s |
| `hold_ent0` 10 / 30 / 108 | 0.213 / 0.277 / 0.381 | 4 / 3 / 2 s | 33 / 18 / 7 s |

("The launch prior" is the starting habit from the 3% reset, before any training.)

- **The prior was nearly as good as the best hand rule**, and every run moved away from
  it, toward launching the whole hangar at 2 s. By the end each was worse than no orders.
- **The entropy bonus was not the cause.** `hold_ent0` had none and slid the same way, on
  the same curve. The night's guess ([plan](plan.md), "08:25") was that the
  bonus, which pushes every "hold" choice toward even odds, wore the holding away. That
  guess is wrong.
- **What is left is the signal.** An update sees about 25 station matches. Each is won or
  lost a minute after the launches that decided it, and that one result is shared by
  every decision in the match. A policy that starts near the best rule then mostly takes
  noisy steps, and from near the top most steps lead down. Holding is a choice made at
  many decisions in a row, so it is also the easiest habit for noise to wear away.
  Untested fixes: choose a hold time once per hull class, or play far more matches an
  update. Both would mean building special measures for this one problem (a new
  kind of choice in the commander, or a training batch many times the usual size). The
  owner asked to set such measures aside in favour of long runs on the trainer's default
  settings, so neither is scheduled.

<!-- figure-idea: shared: why a late result is a weak signal: one win or loss at the end of a match, spread back over the hundreds of decisions a commander made in it, with the few that mattered (the launches in the first minute) lost among them. -->

## What went wrong in the night

Editing `run.sh` at 05:10, while two copies of it were running, made bash (the shell
running the script, which reads it as it goes) read the edited file part-way through. At
05:10 the copy that started `hold` launched it again from update 1. That second run
overwrote the first run's checkpoints 10 to 50 and ran as an unplanned fourth trainer
until 07:55. At 10:30 the other copy, when `kite` and `noattack` stopped, started
`noattack` again. That overwrote its resume state and log before it was stopped. Its
final weights (174) and training log were not affected. Run scripts are no longer edited
while running, and new launchers end in `exec`.

## What goes live

Nothing changes on the live page. A commander level with no orders adds no measured
gain to the live stable (the commanders the live page draws from). The long commander run
on Beast takes it from here: one learner on
the trainer's defaults, for days, from `live` 197.
