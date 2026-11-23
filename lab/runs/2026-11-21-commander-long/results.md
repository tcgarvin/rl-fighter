# The long commander run: level with no orders, by giving none

One commander trained on the trainer's defaults for 7,149 updates (about 50 hours of
training) on Beast, from commander 3's `live` 197. It ends level with the side that gets
no orders, or a little above: 0.523 over 2,304 matches. It beats the scripted commander
0.667. It gets there by almost never giving an order: its ships spend 0.2% of their time
under one. The run is paused, not finished, at update 7149, so the next commander phase
resumes it with whatever pilots are live then. No rule of the game changed
(`SIM_VERSION` 11).

<!-- summary: We trained one commander for about two and a half days instead of one night, starting from the best one we had. It ended level with a side that gives no orders at all, or a little ahead (52 wins in 100), and well ahead of the hand-written commander (67 in 100). It got there by giving almost no orders: its ships are under an order 0.2% of the time. With today's pilots, an order costs a ship more than it gains, so the best commander mostly launches its craft and stays quiet. It now flies on the live page, and the run is paused rather than stopped, so it can carry on once pilots answer orders and come home when recalled. -->

The [plan](plan.md) has the setup, the three trainer fixes made at update 1235 and how to
read the log across them. "Unseen" is the scripted commander with its orders hidden from
its own pilots: the side with no orders. A commander that gives no orders and launches as
well as the script scores about 0.50 against it.

## The curve

`eval_loop.sh`: every 100th checkpoint against unseen, 192 matches a mission over the four
missions and the live ten (768 a checkpoint, about ±0.035). Means over each stretch:

| Updates | Checkpoints | Wins | Deathmatch | Carrier | Convoy | Station | Time under an order |
|---|---|---|---|---|---|---|---|
| 100–1,200 (before the fixes) | 12 | 0.461 | 0.50 | 0.41 | 0.49 | 0.45 | 4.9% |
| 1,300–1,900 | 7 | 0.424 | 0.45 | 0.36 | 0.44 | 0.45 | 28% |
| 2,000–2,900 | 10 | 0.471 | 0.48 | 0.44 | 0.47 | 0.49 | 3.9% |
| 3,000–3,900 | 10 | 0.488 | 0.51 | 0.45 | 0.49 | 0.50 | 1.8% |
| 4,000–4,900 | 10 | 0.488 | 0.49 | 0.46 | 0.49 | 0.51 | 1.4% |
| 5,000–5,900 | 10 | 0.487 | 0.49 | 0.44 | 0.48 | 0.53 | 1.1% |
| 6,000–7,100 | 12 | 0.491 | 0.51 | 0.44 | 0.49 | 0.52 | 0.5% |

- **The fixes cost it first.** Right after update 1235 the run counted the order heads it
  had been ignoring, gave more orders (28% of ship time) and dropped to 0.42. It took
  about 1,000 updates to stop again.
- **From about update 3,000 it is flat.** Forty-four checkpoints between 0.465 and 0.512,
  with no trend. Its training win rate against unseen stayed between 0.47 and 0.50 over
  the same stretch, against the script 0.62 to 0.68, against its own snapshots about 0.50.
- **What it gained came from going quiet.** Time under an order fell from 5% to 0.5%
  across the run, and the score rose by about as much as the orders had been costing.
  The carrier battle stayed its weakest mission (0.44) and the station assault its best
  (0.52 to 0.53).

## The last checkpoint

`final/` on Beast: update 7149, 576 matches a mission (2,304 a row, about ±0.02).

| Against | Wins | Deathmatch | Carrier | Convoy | Station | Its time under an order |
|---|---|---|---|---|---|---|
| Unseen (no orders) | **0.523** | 0.54 | 0.50 | 0.50 | 0.56 | 0.2% |
| Scripted | **0.667** | 0.66 | 0.70 | 0.63 | 0.68 | 0.2% |

The scripted side keeps its ships under an order 91% of the time. That it loses 2 in 3
to a side that gives almost none is the same finding as every phase before: with these
pilots, an order costs more than it brings.

## What it means

The trainer now works as intended (the critic explains about 80% of the variance of the
returns, the order heads that count are the ones the decoder reads), and given days it
finds the best policy these pilots allow, which is close to silence. A commander can only
be worth more than that once a pilot gains from an order: takes an attack order without
losing its fight, and breaks off to come home when recalled. Neither is true yet (see
[orderable pilots](../2026-11-21-orderable-pilots/results.md) and
[dock pilot](../2026-11-20-dock-pilot/results.md)). So the next phase is pilots, and this
run waits for them.

## Paused, to resume

Stopped with SIGTERM at update 7149 on 2026-11-23 (it checkpointed). The state is copied
to `paused-7149/` on Beast: `state.pt` (sha256 `1a992b6f…`), `commander_7149.pt`
(`67bb7b4e…`), the config, log, snapshot pool and `learner.out`; the code was commit
`fd8f401`. To resume, run `run.sh` with a new `DEADLINE` (it passes `--resume` when
`learner/state.pt` exists). A resumed run reads its pilots from its own config, so the
`--set live_pilots=<list>` that moves it to the pilots live then is one step the log can
mark.

## On the live page

Update 7149 joins the live commander stable as `long_7149`, beside the scripted
commander and the three from commander 1.
