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
given days. And it builds on what we have rather than starting over (the rule now in
`docs/COMMANDER.md` "Training"). It starts from the best general commander so far,
commander 3's `live` 197, which is level with the no-orders side over the live ten (0.49).
A first launch from a fresh net was stopped after 3 updates for this reason.

## What it is

| Setting | Value |
|---|---|
| Missions | All four, equal weight: deathmatch, carrier battle, convoy escort, station assault (citadel) |
| Pilots | The live ten (`lab/live_pilots.json`, as it stands when the run starts or resumes) |
| Opponents | The defaults: scripted 0.35, random 0.1, itself 0.3, its snapshots 0.25 |
| Start | Commander 3's `live` 197 (`init`; its actor, a new critic). No launch prior, nothing forbidden |
| Entropy bonus | 0.002, the trainer's default since 2026-11-21 (it was 0.01, which commander 3 found kept a commander ordering) |
| Set for the machine | 128 envs, 5 sim + 5 torch threads, `nice` 10 |
| Stops | 2026-11-28 12:00 (`DEADLINE`), or SIGTERM with a checkpoint; `run.sh` resumes |

## How it is measured

`eval_loop.sh` plays every 100th checkpoint against `unseen`, the scripted commander with
its orders hidden from its own pilots, so the side with no orders. That is 192 matches a
mission, all four missions, over the live ten, at the lowest priority. A commander that
gives no orders, launches and flies its carrier as well as the script scores about 0.50.
Above that, its decisions help its side. The curve, not an endpoint, is the result. A
checkpoint above 0.50 goes into the live stable as a pilot joins the season: measured,
not gated.

## So far (2026-11-21, about 140 updates an hour)

`eval/unseen_<update>.json`, 768 matches each, about ±0.035. The start, `live` 197, scored
0.460 over the live ten in commander 4's eval (1,536 matches,
[results](../2026-11-21-commander-4/results.md)).

| Update | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 |
|---|---|---|---|---|---|---|---|---|
| Wins against unseen | 0.43 | 0.48 | 0.46 | 0.42 | 0.44 | 0.45 | 0.48 | 0.45 |
| Time under an order | 8% | 2% | 2% | 3% | 2% | 0.5% | 0.6% | 5% |

Flat so far, within noise of its start, and still giving few orders. That is expected
after six hours; the plan is days.

## The fixes (2026-11-21, from update 1235)

A review of the trainer found three faults. The run was stopped at update 1235 (19:25),
its state copied to `before-fixes-1235/` on Beast (state, config, log, the checkpoint and
the snapshot pool; the code was commit `318728b`), and resumed from that state with the
fixes. It was not restarted: the actor, the critic and their optimiser carry on.

| Fault | What it did | Fix |
|---|---|---|
| The order heads of empty squads counted in the log-probability and the entropy bonus | The decoder gives an empty squad no order, so nothing but the entropy bonus moved those heads. Their entropy rose from 1.3 to 4.8 nats, and a ship that joined a squad drew a near-random order | A squad's order, target, ward and point heads count only when the squad ends the decision with a member (`docs/COMMANDER.md` "Outputs") |
| The run never met the side it is measured against | `opponent_shares` gave unseen 0. Over 1,235 updates its training win rates did not move: 0.65 to 0.62 against the script, 0.56 to 0.58 against random orders, 0.50 against its snapshots | Enemies are now scripted 0.15, random 0.05, itself 0.25, its snapshots 0.25, unseen 0.3 (the trainer's new default, set in `run.sh` because a resumed run reads its own config) |
| A run from `init` moved a trained actor on a new critic's advantages | Suspected of unwinding commander 4's launch prior. It does not touch this resume, whose critic has 1,235 updates behind it | `critic_warmup`, 20 updates of critic alone at the start of a run from `init` |

What carries over from before: the order heads of empty squads are still near even
odds, so a ship put into an empty squad probably still draws a random order. With the
fix those heads learn only from decisions where they did something. How fast that
recovers is one of the things the curve will show. The heads that did count were less
far gone than the old log suggested: in the first three updates after the fix (1236 to
1238), 0.19 to 0.20 of them chose something other than keep, a decision had 0.4 to 0.6
squads with a member, and ships spent 14 to 16% of their time under an order. The
critic explained 0.72 to 0.82 of the returns' variance, so the resume did not start
from a cold critic.

**Reading the log across update 1235.** `entropy_order`, `entropy_target`, `_ward` and
`_point`, and with them `entropy`, now sum only the heads that counted, so they drop at
1236 without the policy having changed. `order_change_rate` and `order_none`,
`_attack`, `_defend`, `_goto` are now shares of the order heads the decoder read, not of
all four. New keys: `order_heads_live`, `explained_variance`, `actor_frozen`, and
`win_unseen` / `n_unseen`.

**The eval loop stopped early.** It ended at 16:50 after update 800, taking a running
trainer for a stopped one (`grep -q` closed the pipe, `ps` died of SIGPIPE, and
`pipefail` reported that as "no trainer"). Fixed; restarted with the trainer, it
measures 900 to 1,200 first and then carries on.

## With the pilots

The pilot half of the loop keeps running on Beast's GPUs:
[orderable pilots](../2026-11-21-orderable-pilots/plan.md), then whatever follows it. When
WAR changes the live ten, this run keeps the pilots it started with until it is stopped
and resumed, which changes its pilots in one step that the log can mark. Pairing a
commander with pilots trained to take its orders comes once one order is worth giving.
