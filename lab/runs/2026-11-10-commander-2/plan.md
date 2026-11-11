# Second commander phase: orders that last

Planned 2026-11-10 with the owner. The design is `docs/COMMANDER.md`; the page is
`/commander/`.

## Why now

By the loop it is the commanders' turn, against the ten pilots of the
[fourth night](../2026-11-10-fourth-night/) under `SIM_VERSION` 7. And the owner, watching
the live page: the commanders "change orders far too often, sometimes giving ships changing
orders every second".

## What was wrong

- **The locks had a gap.** A squad's order was locked for 3 decisions after it changed, and
  a ship for 3 decisions after it moved squad, but neither saw the other. A ship could get a
  new order through its squad, be moved to another squad a second later, and have that
  squad's order change the second after.
- **Changing an order cost nothing.** The reward is the win and the balance of ships. Most
  pilots ignore orders, so the order choices got almost no signal, and the entropy bonus
  pushed them toward even odds. At the end of phase 1, 52% of squad order choices were
  something other than "keep".
- **"Keep" started as one choice in five** (one in six for a ship's squad).

## What changed (2026-11-10)

- **A hold on each ship's order** (`HOLD_DECISIONS = 5`, `crates/sim/src/commander_io.rs`).
  A ship whose order a decision changed, by either route, keeps that order for 5 seconds:
  it cannot move squad, and its squad's order cannot change, until then. Owner's choice of
  5 seconds.
- **A spent order ends its hold at once**: the attack target or the ward is gone, or the
  ship has arrived at its go-to point. Owner: "if an order becomes invalid (say, target is
  destroyed), new orders can be issued sooner".
- **A price on orders** in training (`order_price`): each decision pays that much for every
  ship whose order it changed. Off by default; two of tonight's lines set it.
- **A start that leans to "keep"** (`keep_prior` 0.8).
- The trainer logs `order_seconds` and `ordered_share`; the commander eval times every
  ship's orders (`orders_a`, `orders_b` in its JSON).
- The layouts are unchanged, so `COMMANDER_IO_VERSION` stays 1 and the `c1_*` commanders
  still load. The sim's own rules did not change (the scripted and random commanders are
  not held), so `SIM_VERSION` stays 7 and script against script is as it was this morning.

## What we measured before training

`c1_shaped` (phase 1's design line) against the scripted commander, 48 matches a mission,
the same matches under both rules. An order here is a ship's order as the sim tracks it:
it starts when the ship's standing order changes kind or target, or its go-to point moves.

| Commander, rule | Orders a ship-minute | Median order | Orders under 5 s | Time under an order |
|---|---|---|---|---|
| `c1_shaped`, old 3-second locks | 10.1 | 3.0 s | 96% | 45% |
| `c1_shaped`, 5-second hold | 6.8 | 5.0 s | 7% | 52% |
| Scripted commander (not held) | 5.1 | 8.0 s | 32% | 99% |

- Under the old locks nearly every order `c1_shaped` gave ended inside 5 seconds.
- Under the hold the 7% that end early are spent orders. But the median is exactly the
  hold: it re-orders the moment it is allowed. The hold alone caps the churn; it does not
  teach the commander to let an order run. That is what the price is for.
- `c1_shaped` scored 0.54 against the script under both rules (144 matches, so about
  ±0.08): the hold cost it nothing we can see.
- **The scripted commander re-orders too**: a third of its orders end inside 5 seconds. It
  decides every 2 seconds and retargets freely. It is not held by the new rule. Whether it
  should be is the owner's call: it would be a sim rule change (`SIM_VERSION` 8), and the
  script is the pilots' teacher and the commander every learned one is compared with.

## Arms

All start fresh (the rules changed): PPO per decision (1 Hz), 128 envs, 8192 decisions an
update, minibatch 1024, 4 epochs, LR 3e-4, entropy 0.01, gamma 0.99, lambda 0.95, shaping
0.5, seed 0, `keep_prior` 0.8. Enemy commanders as in phase 1: scripted 0.35, random 0.1,
itself 0.3, its snapshots 0.25. Missions uniform. 4 sim + 4 torch threads each.

| Arm | Price of an order, per ship | Question |
|---|---|---|
| `hold` | 0 | What does the hold alone give? |
| `price2` | 0.002 | Does a small price make orders last? |
| `price5` | 0.005 | How far can the price go before the commander stops giving orders? |

For scale: a win is +1 and a loss −1. A side of six ships re-ordered every 5 seconds for
100 seconds is 120 changes, which is −0.24 at 0.002 and −0.6 at 0.005. With pilots that
mostly ignore orders an order is worth little, so the risk at any price is a commander
that gives none. `ordered_share` in the log shows that if it happens.

Speed in phase 1: about 36 updates an hour with three arms.

## Morning (`morning.sh`, about 30 minutes)

Each arm's last checkpoint against the scripted commander, random orders and `c1_shaped`
(under the hold) against it too, and the arms against each other, 192 matches a mission.
Each line of the summary carries how long that commander's orders lasted. Then:

- A line joins `lab/live_commanders.json` if it is not clearly worse than the script
  **and** its orders last (median well over 5 seconds, time under an order not collapsed).
- The `c1_*` commanders leave the stable once a new one is in: they were trained under the
  old locks.
- A logbook entry, and the live page rebuilt with the hold in its WASM.

## Launch

`launch_when_idle.sh` waits for midnight, then starts `run.sh` once the owner's session
has been idle 15 minutes with no game running (checked every 10 minutes), with a deadline
of 08:00, and runs `morning.sh` after it.

```bash
cd ~/code/rl-fighter && nohup setsid lab/runs/2026-11-10-commander-2/launch_when_idle.sh \
    > lab/runs/2026-11-10-commander-2/launch.out 2>&1 &
```

**Launched 2026-11-10 23:03 by hand**, not by the watcher: the owner said the machine is
free until noon. Training stops at 10:45, then `morning.sh`:

```bash
cd ~/code/rl-fighter && DEADLINE="10:45 tomorrow" nohup setsid bash -c \
  'lab/runs/2026-11-10-commander-2/run.sh >> lab/runs/2026-11-10-commander-2/run.out 2>&1 &&
   lab/runs/2026-11-10-commander-2/morning.sh > lab/runs/2026-11-10-commander-2/morning.out 2>&1' \
  > /dev/null 2>&1 &
```

Checked before launch: `scripts/check.sh`, the full pytest, `SMOKE=1 run.sh` (all three
arms train, snapshot and checkpoint), `morning.sh` rehearsed on the smoke checkpoints.
