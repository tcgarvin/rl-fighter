# Order pilot: fleet pilot v1 learns to fly its commander's orders

| | |
|---|---|
| Run | `2026-10-31-order-pilot` (M3 stage B, WP-B2; `docs/M3_PLAN.md` "Stage B decisions") |
| Branch | `m3-orders-run` (merged after WP-B1's `m3-orders-sim`, SIM_VERSION 5) |
| Question | Starting from fleet pilot v1 with the new order inputs zeroed, does PPO with a small order reward teach the pilot to fly attack, guard and hold orders (from a random and from the scripted commander), without losing what v1 wins? Which order reward weight, 1 or 0.3? |
| Scenario | rosters `orders_v1`: deathmatch 0.4 (`fleet_v1` draws) / carrier battle 0.3 / convoy 0.3, each team's commander scripted or random with p = ½, padded to 12 ships; arena 450 m; clocks 90 / 150 / 120 s; `reaction_ticks` 2; `SIM_VERSION` 5 |
| Status | **planned**: gates fixed below before any eval of an order pilot |
| Ships | the pick replaces fleet pilot v1 on the live page, where the stage B page draws the commander's orders and shows the ships flying them |

## 1. Why, and what would count

Stage A put carriers, convoys and a commander on the live page. The commander's
orders are drawn behind "Show commands", but pilot v1 cannot see them: it fights the
nearest enemy. Stage B (SIM_VERSION 5) appends an 18-float order block to the pilot
obs (`OBS_DIM` 385 → 403, the first 385 floats unchanged) and an order reward
buffer, `order_rewards[N, S]` (attack damage on the target; guard and hold
potential shaping, a one-shot arrival bonus and capped presence; guard damage near
the ward). This run teaches the pilot to use them.

- **H1.** v1 widened with zero order columns, PPO on the team reward plus `w ×` the
  order reward, with a KL anchor to v1 on rows without an order, follows orders
  measurably better than v1 does by accident (gate O), under both commanders, while
  it still wins carrier battles and convoys against v1 pilots (M), fights
  deathmatches as well (D), and stays healthy (H).
- **H2.** `w = 1` follows better than `w = 0.3` (O), and `w = 0.3` keeps more of v1's
  strength (M, D). If both pass, the pick rule decides by mission strength.
- **H0.** The order reward is too small next to the team reward, or the anchor too
  strong: the candidates follow no better than v1 or than themselves with the
  block zeroed (O fails; the secondary baseline shows the block is unused).

## 2. Before training: baselines (the `baseline` stage, measured first)

All on SIM_VERSION 5, sampled actions, the evals of §5:

- **script vs script** and **v1 vs v1** in carrier battle and convoy (scripted
  commanders, live default rosters, n = 516 per mission): win rates per side,
  end reasons, **time-limit and stalemate rates** (H's reference);
- **v1's order following** on `obs[:385]` (`spacefight.eval.orders`): carrier +
  convoy under the random and the scripted commander, n = 96 per scenario, the
  script on the other side (O's primary reference);
- **v1 vs the script** on the `fleet_v1` deathmatch suite (H's deathmatch
  time-limit reference).

The same evals on SIM_VERSION 4 (no orders there), run 2026-10-30 on this branch to
size the run and sanity-check the evals. The v5 baseline replaces them and is what
the gates read (v5 keeps v4's first 385 obs floats, so v1's numbers should repeat):

| eval (v4, seeds as §5) | carrier battle | convoy |
|---|---|---|
| v1 vs v1: win of side a / time limit / stalemate / median length | 0.496 / 0.019 / 0.000 / 115 s | 0.502 / 0.000 / 0.000 / 68 s |
| script vs script: win of side a / time limit / stalemate / median length | 0.443 / 0.174 / 0.000 / 134 s | 0.496 / 0.000 / 0.000 / 68 s |

Deathmatch (`fleet_v1`, 64 per roster): v1 vs the script 0.889 (time limit 0.001,
as in the fleet run), v1 vs v1 0.485. Script vs script is the same controller on both
sides, so its side-a win rate measures only seed luck: 0.443 at seed 300000, 0.532
at seed 12345 (n = 516). That spread (±0.05) is why M below bounds each mission at
0.47 and asks more only of the mean of the two.

## 3. Setup

- **Sim**: SIM_VERSION 5. Order block (`OBS_LAYOUT["order"]`, offset 385): has_order,
  kind one-hot, target point relative position and velocity (body frame), signed
  distance outside the radius, radius, target hp, bound, relative heading, ticks
  since the order changed, mission one-hot. Pilots see their squad's order in every
  mission, including the advisory deathmatch orders the scripts ignore.
- **Rosters** (`spacefight/env/rosters.py`, preset `orders_v1`, drawn per env per
  episode): mission deathmatch 0.4 / carrier battle 0.3 / convoy 0.3; each team's
  commander `random` with p = ½, else `scripted`. Deathmatch draws are `fleet_v1`'s
  (1–4 a side). Carrier battle: a carrier plus 4–5 strike craft a side (hulls
  uniform over fighter, strafer, gunship; team 1 mirrors team 0's wing with p =
  0.25; 2 jump in, the rest launch). Convoy: 3–4 freighters and 2–3 escorts (team
  0) v 4–5 attackers. Every match pads to `MAX_TRAIN_SHIPS` = 12 slots. The sim's
  per-roster clock is the mission's default.
- **Who flies what**: the learner flies strike craft only. Carriers and freighters
  keep their scripts' actions (they are never learner, self-play or snapshot rows;
  tested). The learner's team is drawn per episode (`learner_side = random`), so
  it defends and attacks convoys equally often.
- **Opponents** (team bands, start update / scripted / self-play / frozen pool):
  `[[0, 0.5, 0.25, 0.25], [200, 0.4, 0.3, 0.3]]`: scripts ≥ 40 % throughout. The
  pool is frozen v1 (a `pool_seed`, flying on `obs[..., :385]`) plus the run's own
  50-update checkpoints; a pool env plays v1 with p = ½ (`pool_seed_p`), so v1 keeps
  its share as the pool grows. Scripted opponents follow orders under the random
  commander and in missions, as the sim's scripts do.
- **Policy and critic**: v1's `SpikeActor` and `FleetCritic`, widened to 403 inputs
  with the 18 new first-layer columns zero (`widen_actor`, `widen_critic`): at update
  0 the pilot is v1 (tested to float32 round-off on any obs whose first 385 floats
  match). Checkpoints record `obs_dim` 403 and `sim_version` 5.
- **Reward**: team reward (SIM_SPEC §8, unchanged) `+ w × order_rewards`; credit and
  GAE on the sum; `reward_team`, `reward_order` (unweighted) and
  `reward_order_weighted` are logged apart.
- **KL anchor**: `+ 0.1 × KL(v1 ‖ π)` (summed over the row's valid heads, mean over
  the minibatch's rows with `has_order = 0`). Why 0.1: it is the weight the fleet
  run's PPO trained under with its script pull (β = 0.1 on a joint NLL, updates
  0–100) without stalling, and per-update `approx_kl` there was ≈ 0.005, so the
  anchor binds once the unordered behaviour has drifted ≈ 0.05–0.2 nats from v1,
  long before 400 updates of drift would add up. It never touches rows with an
  order. `kl_anchor` (unordered rows) and `kl_anchor_ordered` (ordered rows, not
  penalised) are logged every update; ordered rows should drift, unordered not.
- **Samples**: 256 envs × 128 steps (≈ 110 k learner rows per update, measured on v4);
  credit adapter, tail and minibatches of whole matches as in the fleet run.

## 4. Method

One stage: PPO from widened v1, two arms run concurrently with the same seed and
everything else equal:

| arm | order reward weight `w` |
|---|---|
| `w1` | 1.0 |
| `w03` | 0.3 |

PPO: the fleet run's BC preset (actor LR 1e-4 decaying linearly to 0 at update 400,
clip 0.1 for 200 updates then 0.2, entropy 0.005, 4 epochs, minibatch 4096) with
**no script pull** (β = 0) and a **20-update critic warm-up** (the critic must learn
the order reward and the longer missions before the actor moves; the fleet run used
30, but its critic started from a BC critic on a smaller change). 400 updates,
checkpoints every 50, each one a candidate.

## 5. Gates (fixed before any order pilot is evaluated)

Encoded in `spacefight/eval/order_gates.py`; `gates.py` applies them to the JSONs
`eval.sh` writes. Sampled actions throughout.

- **Following eval** (`spacefight.eval.orders`, schema `rlf.eval.orders/1`): carrier
  battle and convoy, each under the random and under the scripted commander, the
  live default rosters (`rlf_sim.mission_rosters`), the candidate flying one side's
  strike craft (each side of each roster equally often), the script the other
  side's, n = 96 per scenario (a carrier battle under the random commander gives each
  ship an order change every 3–8 slow ticks, so thousands of instances), seed
  400000. Pooled over both missions per commander mode. Order
  instance: from a change of a ship's order (kind, target or point) to the next.
  Attack: *ticks to gun range* (median over instances whose target started under
  250 m, never-reached counted as last) and *damage share on the target* (pooled
  damage to the ordered target / all damage dealt under attack orders). Guard: *time
  within* 90 m + the ward's bound (share of live instance ticks). Hold: *time
  inside* the radius. *Response*: ticks to the nose within 30° of the target point,
  for instances that start outside the radius. Primary baseline: v1 on
  `obs[:385]`; secondary (reported): the candidate with the block zeroed.
- **Mission eval** (`spacefight.eval.missions`, `rlf.eval.mission/1`): the candidate
  vs v1 pilots, scripted commanders, capital ships by script, the live default
  rosters, the pilot on each side of each roster equally often, n = 516 per mission
  (a multiple of 2 × 3 rosters), seed 300000. *Stalemate*: a time-limit ending with
  no damage landed by anyone in the last 30 s.
- **Deathmatch**: `spacefight.eval.fleet`, suite `fleet_v1`, 64 per roster, seed
  200000, vs the script and vs v1.

| gate | check | bound |
|---|---|---|
| **O following, random commander** | attack / guard / hold instances | ≥ 30 each |
| | attack: median ticks to gun range (targets < 250 m) | ≤ 150 |
| | attack: damage share on the target | ≥ v1's + 0.10 |
| | guard: time within | ≥ max(0.50, v1's + 0.15) |
| | hold: time inside | ≥ max(0.40, v1's + 0.15) |
| | response: median ticks, all kinds | ≤ 90 |
| **O following, scripted commander** | attack / guard / hold instances | ≥ 30 each |
| | attack: damage share on the target | ≥ v1's + 0.05 |
| | guard: time within | ≥ v1's + 0.10 |
| | hold: time inside | ≥ v1's + 0.10 |
| | response: median ticks, all kinds | ≤ 90 |
| **M missions vs v1** | carrier battle win (draws ½) | ≥ 0.47 |
| | convoy win | ≥ 0.47 |
| | mean of the two | ≥ 0.52 |
| **D deathmatch** | `fleet_v1` win vs the script | ≥ 0.85 |
| | `fleet_v1` win vs v1 | ≥ 0.45 |
| **H health** | per mission: time-limit rate | ≤ v1 vs v1's + 0.10 |
| | per mission: stalemate rate | ≤ v1 vs v1's + 0.05 |
| | per mission and deathmatch: NaN or stuck matches (share) | ≤ 0.01 |
| | per mission and deathmatch: outside-arena share | ≤ 0.02 |
| | deathmatch time-limit rate | ≤ v1 vs script's + 0.10 |

Why these numbers. The ticks-to-close (150, 5 s) and response (90, 3 s) bounds are
the M3 decisions'. M's 0.47 per mission is parity less ≈ 1.4 standard errors at n =
516 (a candidate not detectably worse than v1 in either mission), and the 0.52 mean
asks that following orders win something somewhere. The scripted commander's margins
are smaller than the random one's because its orders are sensible ones that v1
partly follows by accident (attack the nearest, guard the carrier it fights near).
D is the decisions' (the advisory deathmatch orders may cost a little; 0.45 vs v1
names it). H's margins are relative to v1 vs v1 because the candidate replaces v1 in
exactly that matchup. Engine duty is reported per hull and per order kind (the direct
readout of farming a presence reward by parking), not gated; so are passes, lengths,
end reasons and the secondary baseline. There are no duel gates.

**Pick**: among candidates (both arms, updates 50–400) that pass every gate, the
highest mean mission win vs v1; ties by the deathmatch win vs v1. If none passes,
nothing is promoted, the live page keeps v1, and `results.md` names the failed
checks.

## 6. Budget (measured on this laptop, 16 cores, no GPU, otherwise idle)

Measured 2026-10-30 on SIM_VERSION 4 with this branch's code and the `orders_v1`
mix minus the random commander (not in v4) and with one clock per env; the order
block adds 18 floats per row, and the random commander is the same script with a
different order source, so v5 should cost the same. **Re-measure on v5** with
`SMOKE=1` then the first 10 updates of the real run, and amend this table.

| stage | measured | estimate |
|---|---|---|
| PPO, one arm alone, 6 sim + 6 torch | 17–21 s/update, ≈ 110 k samples (rollout 2.8 s, PPO 14 s) | |
| **PPO, two arms at once** (6 + 6 each) | **29 s/update** mean of updates 2–8, ≈ 112 k samples, PPO ≈ 22 s | 400 updates ≈ **3.2 h** (the first 20 critic-only updates are faster; samples per update grew 1.9× over the fleet run, so allow 3.5 h) |
| baseline (v4 timings) | missions v1 vs v1 4.5 min, script vs script 1.5 min, `fleet_v1` 0.9 min; following not runnable on v4 (≈ 1.5 min estimated) | **≈ 9 min** |
| gate evals per candidate (12 threads) | missions vs v1 (1032 matches) 4.5 min, fleet vs script 0.9 min, fleet vs v1 1.05 min, following ≈ 1.5 min (estimate) | **≈ 8 min**; 16 candidates ≈ 2.1 h, the 8 hundreds ≈ 1.1 h |
| secondary (blanked following, passing candidates only) | ≈ 1.5 min each | ≤ 25 min |
| **total** | | **≈ 5.7 h** (PPO 3.3 h + evals 2.1 h + baseline and secondary), at the edge of a 6 h night |

The eval stage runs the 100-update checkpoints first (`EVAL_UPDATES` "100 200 300
400 50 150 250 350"), so if the night runs short the gates can already pick among
the even hundreds, and the rest are resumable (`run.sh eval gates`).
**The cut, if the v5 re-measure is slower**: above 33 s/update, evaluate the hundreds
on the night (`EVAL_UPDATES="100 200 300 400"`, ≈ 1.1 h, total ≈ 4.8 h) and the
fifties the next day; above 40 s/update, also stop at 300 updates (`N_UPDATES=300`,
checkpoints and gates unchanged). Dropping an arm is not proposed: the two arms run
in parallel, so one arm alone saves only ≈ 40 % of the PPO wall time.

Memory: two arms ≈ 3 GB each (403-wide obs over 12 slots × 256 envs × 168 steps ≈
0.8 GB per arm plus the buffers), well inside 29 GB.

## 7. Risks

| risk | signal | response |
|---|---|---|
| presence farming: pilots park on hold or guard points instead of fighting | engine duty under hold/guard ≪ under none; M or D fails while O passes | the presence term is capped per instance; pick `w03`; lower `w` |
| the order reward is too weak to matter (H0) | `reward_order_weighted` ≪ `reward_team` in the log, O fails, with ≈ blank | a later arm with `w` 3 |
| the anchor stops unordered learning, or does not hold | `kl_anchor` ≈ 0 with D falling, or `kl_anchor` > 0.5 | change `KL_COEFF` (0.03 / 0.3) in a rerun |
| the critic cannot value long missions | explained variance < 0.5 after warm-up | longer warm-up; it is logged per update |
| mixed clocks per batch | carrier matches 150 s next to 90 s deathmatches | GAE is per row, so only the sample mix changes; logged per class (`episodes_by_class`) |
| self-play destabilises | `vs_scripted_win` falls after update 200 | scripts stay ≥ 40 %; an earlier checkpoint |
| throughput below the plan | > 40 s/update | stop at 300 (`N_UPDATES=300`), evaluate the hundreds |

## 8. Running it

From the repo root of the main checkout, after `m3-orders-sim` and this branch are
merged and the SIM_VERSION 5 extension is built (`uv run maturin develop -m
crates/sim-py/Cargo.toml --release`); `run.sh` refuses an older `rlf_sim` and fetches
fleet pilot v1's weights with `tools.champion fetch` (or `V1=path`):

```
SMOKE=1 lab/runs/2026-10-31-order-pilot/run.sh      # every stage at tiny sizes, smoke/ (gitignored)
nohup lab/runs/2026-10-31-order-pilot/run.sh > lab/runs/2026-10-31-order-pilot/run.out 2>&1 &
```

Stages `baseline ppo eval gates secondary`, each skipping finished work (PPO
resumes from the latest checkpoint; SIGTERM checkpoints after the current update;
`secondary` runs the blanked-orders following eval for the candidates that pass and
redoes the gate table). `run.sh eval gates` re-runs only those. Logs: `run.out`, `w1.out`, `w03.out`, `<arm>/log.jsonl`.
Afterwards write `results.md` from `eval/gates.md`, and promote the pick only if
it passes.
