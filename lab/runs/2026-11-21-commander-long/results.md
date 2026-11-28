# The long commander run: level with no orders, by giving none

A commander is the network that sees a whole side and decides when to launch its ships
and what to order them to do. This time one commander trained for 7,149 updates (an
update is one round of playing matches and then adjusting the network), about 50 hours of
training on Beast, the lab's desktop with two graphics cards. It used the trainer's
default settings and started from the best commander we had, commander 3's `live` 197
(the `live` line of the [commander 3 night](../2026-11-15-commander-3/results.md), saved
at update 197). It ends level with the side that gets no orders, or a little above: it
wins 0.523 of 2,304 matches against it. It beats the scripted commander, the hand-written
one, 0.667. It gets there by almost never giving an order: its ships spend 0.2% of their
time under one. The run is paused, not finished, at update 7149, so the next commander
phase resumes it with whatever pilots are live then. No rule of the game changed
(`SIM_VERSION` 11, the eleventh version of the game's rules).

<!-- summary: We trained one commander for about two and a half days instead of one night, starting from the best one we had. It ended level with a side that gives no orders at all, or a little ahead (52 wins in 100), and well ahead of the hand-written commander (67 in 100). It got there by giving almost no orders: its ships are under an order 0.2% of the time. With today's pilots, an order costs a ship more than it gains, so the best commander mostly launches its craft and stays quiet. It now flies on the live page, and the run is paused rather than stopped, so it can carry on once pilots answer orders and come home when recalled. -->

The [plan](plan.md) has the setup, the three trainer fixes made at update 1235 and how to
read the log across them. "Unseen" is the scripted commander with its orders hidden from
its own pilots: the side with no orders. A commander that gives no orders and launches as
well as the script scores about 0.50 against it.

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a pilot, that learned to fly by trial and error. Above the pilots, each side has a
commander: the scripted one, or a learned network (the [commander page](/commander/)
explains how one works). Training alternates between phases for commanders, with the
pilots frozen, and phases for pilots. The [first learned commanders](../2026-11-08-commander-1/results.md)
reached level with the scripted one. Then we found that a side whose pilots get no orders
at all beat every commander we had. In [commander 3](../2026-11-15-commander-3/results.md)
and [commander 4](../2026-11-21-commander-4/results.md) the learned commanders climbed to
about level with that side by learning to give fewer orders, and two of commander 4's
were still climbing when their one night ran out. [The order-cost night](../2026-11-17-order-cost/results.md)
showed why an order costs: an ordered pilot keeps flying at its target and loses the
duel, where a free one falls back and fights on its own terms.

Every commander so far had trained for a single night, often with shortcuts added. The
owner's reading was that patience, not more shortcuts, was what was missing. So this run
asks what one commander finds on the plain defaults if it is given days.

<div data-figure="diagram" data-name="orders" data-caption="The commander trained here is a learned one. It also launches craft from its carrier, which the picture leaves out. By the end of the run its ships spent 0.2% of their time under any of these orders."></div>

## The curve

`eval_loop.sh` played every 100th checkpoint (saved copy of the network) against unseen:
192 matches a mission over the four missions, with every strike craft flown by a pilot
drawn from the live ten, the ten pilots the live page currently uses. That is 768 matches
a checkpoint, about ±0.035 (± is the margin of error: the true value very likely lies
within that range). Each row below is the mean over the checkpoints in one stretch of
updates. "Wins" is the share of matches won against unseen (0.5 is even), and the four
columns after it split that by mission: team deathmatch (small ships only), carrier
battle (destroy the enemy carrier), convoy escort (guard or attack freighters flying to a
jump point) and station assault (attack or defend a static station). "Time under an
order" is the share of its ships' time spent carrying an order.

<div data-figure="diagram" data-name="missions" data-caption="The four mission columns in the table below are these four missions, the ones the live page plays."></div>

| Updates | Checkpoints | Wins | Deathmatch | Carrier | Convoy | Station | Time under an order |
|---|---|---|---|---|---|---|---|
| 100–1,200 (before the fixes) | 12 | 0.461 | 0.50 | 0.41 | 0.49 | 0.45 | 4.9% |
| 1,300–1,900 | 7 | 0.424 | 0.45 | 0.36 | 0.44 | 0.45 | 28% |
| 2,000–2,900 | 10 | 0.471 | 0.48 | 0.44 | 0.47 | 0.49 | 3.9% |
| 3,000–3,900 | 10 | 0.488 | 0.51 | 0.45 | 0.49 | 0.50 | 1.8% |
| 4,000–4,900 | 10 | 0.488 | 0.49 | 0.46 | 0.49 | 0.51 | 1.4% |
| 5,000–5,900 | 10 | 0.487 | 0.49 | 0.44 | 0.48 | 0.53 | 1.1% |
| 6,000–7,100 | 12 | 0.491 | 0.51 | 0.44 | 0.49 | 0.52 | 0.5% |

<!-- figure-idea: a two-line chart over the 7,149 updates: win rate against the no-orders side (with its margin of error) and time under an order, with the fixes at update 1235 marked. It shows at a glance that the score rose as the orders fell away, and the dip after the fixes. -->

- **The fixes cost it first.** A review found three faults in the trainer, fixed at
  update 1235 (the [plan](plan.md) has them in full). The parts of the commander's output
  that pick each squad's order (a squad is a group of its ships, and these parts are its
  "order heads") had counted in training even for squads with no ships in them, where
  they did nothing. The run had never played the no-orders side it is measured against,
  and now does in 0.3 of its matches. And a run started from an older commander now first
  trains its critic alone (the critic is a second network used only in training, which
  predicts how a match will go). That fix did not touch this run, whose critic was
  already trained. Right after update 1235 the run gave more orders (28% of ship time)
  and dropped to 0.42. (The plan noted at the fix that the empty squads' order heads were
  still near random, so a ship moved into an empty squad would probably still draw a
  random order until they relearned.) It took about 1,000 updates to go back to giving
  few orders.
- **From about update 3,000 it is flat.** Forty-four checkpoints between 0.465 and 0.512,
  with no trend. Its training win rate (in the matches it trained on, not the eval)
  against unseen stayed between 0.47 and 0.50 over the same stretch, against the script
  0.62 to 0.68, against its own snapshots (saved earlier copies of itself) about 0.50.
- **What it gained came from going quiet.** Time under an order fell from 5% to 0.5%
  across the run, and the score rose from 0.461 to 0.491, by about as much as the orders
  had been costing.
  The carrier battle stayed its weakest mission (0.44) and the station assault its best
  (0.52 to 0.53).

## The last checkpoint

`final/` on Beast: update 7149, 576 matches a mission (2,304 a row, about ±0.02). Each row
is one opponent. The numbers are the share of matches the long-run commander won, overall
and by mission, and the last column is how much of their time its own ships spent under
an order.

| Against | Wins | Deathmatch | Carrier | Convoy | Station | Its time under an order |
|---|---|---|---|---|---|---|
| Unseen (no orders) | **0.523** | 0.54 | 0.50 | 0.50 | 0.56 | 0.2% |
| Scripted | **0.667** | 0.66 | 0.70 | 0.63 | 0.68 | 0.2% |

The scripted side keeps its ships under an order 91% of the time. That it loses 2 in 3
to a side that gives almost none is the same finding as every phase before: with these
pilots, an order costs more than it brings.

<div data-figure="diagram" data-name="unseen-side" data-caption="The table's two rows are these two sides. The long run's commander won 0.523 against the unseen side and 0.667 against the scripted commander with its orders shown."></div>

## What it means

The trainer now works as intended. The critic's predictions account for about 80% of the
spread in how much reward actually followed, so it is a good guide. And training now
counts only the order heads whose choices actually become orders. Given days, the trainer
finds the best way of commanding these pilots allow, which is close to silence. A
commander can only be worth more than that once a pilot gains from an order: takes an
attack order without losing its fight, and breaks off to come home when recalled for
repair. Neither is true yet (see [orderable
pilots](../2026-11-21-orderable-pilots/results.md), where two pilots were each taught the
skill the other had and neither ended with both, and [dock
pilot](../2026-11-20-dock-pilot/results.md), where pilots learned to dock in practice but
rarely make it home in real matches). So the next phase is pilots, and this run waits for
them.

## Paused, to resume

This section is the record for picking the run up again, and a reader can skip it.
Stopped with SIGTERM (a stop signal the trainer answers by saving first) at update 7149 on
2026-11-23 (it checkpointed). The state is copied to `paused-7149/` on Beast: `state.pt`
(sha256 `1a992b6f…`), `commander_7149.pt` (`67bb7b4e…`), the config, log, snapshot pool
and `learner.out`; the code was commit `fd8f401`. To resume, run `run.sh` with a new
`DEADLINE` (it passes `--resume` when `learner/state.pt` exists). A resumed run reads its
pilots from its own config, so the `--set live_pilots=<list>` that moves it to the pilots
live then is one step the log can mark.

## On the live page

Update 7149 joins the live commander stable (the commanders the live page draws from, one
per side per match) as `long_7149`, beside the scripted commander and the three from
[commander 1](../2026-11-08-commander-1/results.md).
