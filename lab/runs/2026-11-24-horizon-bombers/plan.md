# Horizon and bombers: a pilot that plans further ahead, flies bombers and fights beside other pilots (plan)

Prepared 2026-11-24 on the laptop. Trains on Beast from about 11:00 until 2026-11-25
06:00, then the final evals, WAR and the write-up; results live by 2026-11-25 17:00.
It follows the [long commander run](../2026-11-21-commander-long/results.md), paused at
update 7149. That commander learned to give almost no orders, because with today's
pilots an order costs more than it brings.

## Questions

1. **Does a longer horizon make a pilot that comes home?** Pilots discount 0.995 a 30 Hz
   tick, with no action repeat: a reward 30 s away weighs 0.011, and the half-life is
   4.6 s. Each ship is paid for its own damage dealt and taken. So a pilot is a
   short-horizon damage maximiser, and breaking off a fight to repair, which pays tens
   of seconds later, is worth almost nothing to it. That would explain why the
   [dock pilots](../2026-11-20-dock-pilot/results.md) dock in drills (a trip home is the
   whole drill) but finish only 3 to 8 recalls in 100 in matches, mostly "never close".
   At 0.999 a reward 30 s away weighs 0.41 and the half-life is 23 s. This is a
   hypothesis from the 2026-11-21 review, untested.
2. **Can pilots learn the bomber?** No pilot has trained on bombers on purpose. A learned
   pilot in a bomber barely fights: 33 damage a deathmatch against 127 as a gunship, and
   the swap costs its side 0.38 of a match
   ([station and bomber](../2026-11-19-station-bomber/results.md)). The pilots read the
   bomber as a slow gunship, but its torpedo rack is fixed and points where the hull
   points.
3. **Does training beside other pilots help?** Until now the learner flew its whole side.
   On the live page and in WAR, pilots are drawn ship by ship, so every pilot's
   teammates are other pilots.

## Arms

One parent, one config; the arms differ only in the discount (and seed).

| Arm | Gamma | Seed | Where |
|---|---|---|---|
| `h999` | 0.999 | 2411 | Beast, `update_device=cuda:0`, 3 + 3 threads |
| `h995` | 0.995, the parent's | 2412 | Beast, `update_device=cuda:1`, 3 + 3 threads |

**Parent: `followers_dock_v8_2676`** (`../2026-11-20-dock-pilot/dock352` update 2676,
592 inputs). It is in the live ten (+11.3 wins per 100 over the script, orderable-pilots
WAR), it follows orders (a follower), and it already docks: 0.38 of calm dock drills,
0.14 under fire. No widening is needed. Both arms start from its weights, the owner's
rule: build on what we have.

So `h999` against `h995` is a one-variable comparison of the horizon. The bombers and
the teammates are in both arms. Their effect shows against the parent, together with
one more night of training: a first look, not a controlled test.

## Config

The parent's own config (`parent_config.yaml`, its `dock352/config.yaml`): order pay 1,
dock bonus 1, go-to deadline pay 3 / 3, extra fire cost 0.002, actor lr 1e-4 with no
decay, 256 envs x 128 steps, fleet critic, PFSP over its 17 pool seeds (`pool_seed_p`
0.5), the commander stable `[live, scripted]`, early clip 50. Set on top:

| Key | Value | Why |
|---|---|---|
| `gamma` | 0.999 / 0.995 | the question |
| `critic_warmup_updates` | 50 (both) | the critic learns the new discount, the bombers and the teammates before the actor moves (the parent's was 20) |
| `bomber_share` | 0.2 | in a deathmatch, carrier battle or convoy, each strike slot of either side is a bomber with this chance |
| `drill_bomber_share` | 0.2 | the same for the pilot slots of attack and defend drills |
| `mission_weights`, `citadel_share` | the `pilots_v1` defaults, (0.3, 0.25, 0.25, 0.2) and 1 | the station assault, with its three attacking bombers, is a fifth of matches, as live. New for this line: the parent trained before it was in the defaults |
| `teammate_share` | 0.3 | in a match, each of the learner side's strike craft is a live pilot with this chance, drawn when the match starts; at least one stays the learner's |
| `teammate_pool` | the live ten (`lab/live_pilots.json`) | the pilots it flies beside on the live page |
| roster overrides otherwise | the parent's: `drill_share` 0.55, `drill_weights` [6, 1, 1], `drill_dock_share` 0.5, `drill_dock_threat_share` 0.5, `commander_p` 0.667, `mixed_p` 0 | |
| `checkpoint_every` | 25 | |

**Mixed teammates** are new trainer code (`PPOConfig.teammate_share`,
`teammate_pool`; `tests/test_teammates_train.py`). A teammate's rows train nothing and
stay out of the learner's figures in the log; `teammate_rows_share` logs their share of
the side's rows.

**A longer horizon changes what the critic predicts.** At 0.999 a return sums about five
times as many ticks, so the parent's critic starts out wrong by that much. Both arms
train the critic alone for their first 50 updates. Advantages are normalised per batch,
so the actor's step size does not change with the discount.

## Measures

`eval.sh` on the parent before training (`eval/parent_dock2676`, at full size), on every
1000th checkpoint while training (`QUICK=1`: the first three below), and on each arm's
last checkpoint at full size. `summary.py report` sets them side by side in `report.md`.

- **Recalls in matches** (`dockm_carrier.json`, `dockm_station.json`): the checkpoint
  flies every strike craft, scripted commanders recall below half hull. Share of recalls
  that end in a dock, and why the rest failed. **The horizon's main measure.**
- **The bomber swap** (`swap_dm.json`, `swap_carrier.json`): the same matches twice, side
  X's first gunship as it is and as a bomber. The paired score change, and the bomber's
  damage to capital ships and strike craft. **The bomber's main measure.**
- **Drills** (`drills.json`): go-to, attack, defend, calm and threat dock drills, each
  flown again with the order hidden.
- **Wins against the script** (full only): the mission eval (carrier battle, convoy,
  station assault) and the fleet_v1 suite.
- **The order cost** (full only): 3 v 3, ordered onto the nearest enemy and unordered,
  against a free `followers_school_1052`; cost is the paired difference.

Then **WAR** (`war.sh`): each arm's last checkpoint joins the season as a child of
`followers_dock_v8_2676`. WAR is played over the live ten, the parent and both arms, in
the four live missions with the live commander stable, and the live ten is published
from it. No gates: WAR and the family rules decide what goes live.

## What would count

- **Horizon:** `h999` finishes more match recalls than `h995` and the parent (3 to 7 in
  100 today; the script finishes 54 to 64), without losing more than noise in wins
  against the script. If both arms climb alike, docking came from the extra training,
  not the horizon.
- **Bombers:** the swap's cost shrinks from the parent's, and the bomber's damage to
  capital ships rises toward the script's (124 in the carrier battle).
- **Teammates:** WAR is the measure, since it plays mixed sides. Read only against the
  parent: an arm that gains WAR gained it from all three changes and the extra night.

## Timeline

| When | What |
|---|---|
| Tue morning | trainer code and tests, the parent's full eval on Beast (from 08:00), a smoke of every stage |
| Tue ~11:00 | both arms start on Beast; periodic evals every 1000 updates |
| Wed 06:00 | training stops; final evals of both arms (about 1.5 h) |
| Wed ~08:00 | WAR (about 2 h at 12 threads) |
| Wed by 17:00 | results.md, the live list from WAR, deploy |
