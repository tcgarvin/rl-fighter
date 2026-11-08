# First commander phase

Planned 2026-11-07 with the owner. The design is `docs/COMMANDER.md`; the page is
`/commander/`. Launched 2026-11-08 02:08 when the owner said the machine was free until 18:00; training
stops at 11:00 (nine hours, not the planned five), then `morning.sh`.

## Why now

The loop is commanders, then pilots, then commanders. Pilots frozen tonight; tomorrow's
pilot phase trains under the commanders this one makes, with more go-to drills, and culls
by wins above replacement in matches like the live page's.

## What we measured before training

Matches as on the live page (pilots drawn ship by ship from the live ten, missions in
turn), 96 per mission, so about ±0.05:

| Commander | Against scripted | Deathmatch | Carrier | Convoy |
|---|---|---|---|---|
| Random orders (scripted logistics) | 0.53 | 0.46 | 0.57 | 0.56 |
| Untrained learned commander | 0.46 | 0.43 | 0.44 | 0.50 |

**With these pilots the scripted commander's orders are no better than random ones.** Most
of the live ten ignore orders, so a commander's leverage tonight is mostly logistics:
launches and where the carrier goes. Orders pay off only on ships a follower flies
(`followers_513`, `followers_955`, about one ship in five). Expect a small, noisy signal; it
grows as pilots learn to follow, which is the point of the loop.

## Arms

All: PPO per decision (1 Hz), 128 envs, 8192 decisions an update, minibatch 1024, 4 epochs,
LR 3e-4, entropy 0.01, gamma 0.99, lambda 0.95. Enemy commanders: scripted 0.35, random
0.1, itself 0.3, its snapshots 0.25 (every 25 updates, last 10, weighted toward the ones it
beats least). Missions uniform. 4 sim + 4 torch threads each.

| Arm | Shaping | Seed | Question |
|---|---|---|---|
| `shaped` | 0.5 | 0 | The design |
| `shaped_s1` | 0.5 | 1 | How much two seeds differ |
| `outcome` | 0 | 0 | Does the value-balance shaping help? |

Speed: 4096 decisions in about 12 s of rollout at 128 envs alone; three at once will be
slower. About 300 updates an hour alone.

## Morning (`morning.sh`, about 20 minutes)

Each arm's last checkpoint against the scripted commander, random against scripted, and the
arms against each other, 192 matches per mission. Then: the best arm (and any other that is
not clearly worse) joins `lab/live_commanders.json` beside the scripted commander, the live
page draws a commander per side from it, and the logbook gets an entry.

```bash
cd ~/code/rl-fighter && DEADLINE="07:30" nohup setsid bash -c \
  'lab/runs/2026-11-08-commander-1/run.sh >> lab/runs/2026-11-08-commander-1/run.out 2>&1 &&
   lab/runs/2026-11-08-commander-1/morning.sh > lab/runs/2026-11-08-commander-1/morning.out 2>&1' \
  > /dev/null 2>&1 &
```

Checked before launch: `SMOKE=1 run.sh` (all three arms train, snapshot and checkpoint),
`morning.sh` rehearsed on the smoke checkpoints, full pytest (746 passed), `scripts/check.sh`.

## Outcome (2026-11-08)

About 325 updates each by 11:00. Against the scripted commander (576 matches, ±0.04):
`shaped` 0.56, `outcome` 0.55, `shaped_s1` 0.53, random orders 0.54; the arms are even
with each other. All three joined the live stable as `c1_shaped`, `c1_outcome`,
`c1_shaped_s1` and were deployed at about 12:30. Write-up: `results.md`.
