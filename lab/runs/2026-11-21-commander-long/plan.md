# The long commander run: one learner, the defaults, for days

Planned 2026-11-21. Runs on Beast's CPUs beside the pilot runs on its GPUs, at low
priority, until 2026-11-28 or until stopped. `SIM_VERSION` 11.

## Why

Every commander phase so far has trained for one night and then been judged:
[commander 3](../2026-11-15-commander-3/results.md), and
[commander 4](../2026-11-21-commander-4/plan.md) the night this plan was written. Commander
4's `kite` and `noattack` were still climbing when their night ended: from 0.33 to 0.47
against the side with no orders, in about 3.5 hours, as they learned to stop giving
orders that cost them fights. Most of what that night added were shortcuts: a launch
prior, forbidden orders, an arm for the station's defender alone. The hold arms showed
their cost. The prior handed the learner a good launch policy it had not found itself, and
training moved away from it.

The owner's reading: more training time and patience, not more shortcuts. So this run is
one learner on the trainer's own defaults (`spacefight.commander.train.TrainConfig`),
given days.

## What it is

| Setting | Value |
|---|---|
| Missions | All four, equal weight: deathmatch, carrier battle, convoy escort, station assault (citadel) |
| Pilots | The live ten (`lab/live_pilots.json`, as it stands when the run starts or resumes) |
| Opponents | The defaults: scripted 0.35, random 0.1, itself 0.3, its snapshots 0.25 |
| Start | A fresh commander: no prior beyond the trainer's default lean to "keep", nothing forbidden |
| Set for the machine only | 128 envs, 5 sim + 5 torch threads, `nice` 10 |
| Stops | 2026-11-28 12:00 (`DEADLINE`), or SIGTERM with a checkpoint; `run.sh` resumes |

## How it is measured

`eval_loop.sh` plays every 100th checkpoint against `unseen`, the scripted commander with
its orders hidden from its own pilots, so the side with no orders. That is 192 matches a
mission, all four missions, over the live ten, at the lowest priority. A commander that
gives no orders, launches and flies its carrier as well as the script scores about 0.50.
Above that, its decisions help its side. The curve, not an endpoint, is the result. A
checkpoint above 0.50 goes into the live stable as a pilot joins the season: measured,
not gated.

## With the pilots

The pilot half of the loop keeps running on Beast's GPUs:
[orderable pilots](../2026-11-21-orderable-pilots/plan.md), then whatever follows it. When
WAR changes the live ten, this run keeps the pilots it started with until it is stopped
and resumed, which changes its pilots in one step that the log can mark. Pairing a
commander with pilots trained to take its orders comes once one order is worth giving.
