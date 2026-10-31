# Order pilot B3: orders redesigned, threats in the obs, a pull only in transit

| | |
|---|---|
| Run | `2026-11-01-order-pilot-b3` (M3 stage B3, `docs/M3_PLAN.md` "Stage B3: orders redesigned") |
| Branch | `m3-b3-train` (WP-B3-train), on top of `m3-b3-sim` (WP-B3-sim, SIM_VERSION 6) |
| Question | Starting from run 1's `w1_400` widened to the SIM_VERSION 6 obs, do attack, defend and go-to orders, with threat and order-point context in the obs, get followed at the teacher's level (gate O, against the same pilot with its orders hidden by the sim) while the pilot keeps `w1_400`'s mission strength (M, D, H)? Is a script pull limited to transit rows needed, or are the new rewards and inputs enough? |
| Scenario | rosters `orders_v1` (deathmatch 0.4 / carrier battle 0.3 / convoy 0.3, each team's commander scripted or random with p = ½), padded to 12 ships, arena 450 m, clocks 90 / 150 / 120 s, `reaction_ticks` 2; SIM_VERSION 6 (orders attack / defend / go-to) |
| Status | **planned**: gates, the teacher-first rule, the eval sizing rule and the pick rule fixed below before any eval; `SMOKE=1` to be run once SIM_VERSION 6 is merged |
| Ships | the pick replaces fleet pilot v1 on the live page |

## 1. What runs 1 and B2b showed, and what changed

- **Run 1** (`../2026-10-31-order-pilot/results.md`): PPO from v1 with the order block
  zeroed made a much stronger mission pilot (`w1_400`: 0.79 of carrier battles and
  0.74 of convoys won against v1) that barely followed orders. Holds were ignored,
  guards stayed near where v1 would have flown.
- **B2b** (`../2026-10-31-order-pilot-b2b/results.md`): a script pull on every ordered
  row taught following at the teacher's level and destroyed combat flying by update
  50 (carrier battle win vs v1 0.00–0.04). The pull covered 0.67–0.70 of all rows,
  mostly ships in a fight.

The review that followed (user, team lead and Fable, `docs/M3_PLAN.md` "Stage B3")
changes the orders, the obs and the recipe:

1. **Orders (SIM_VERSION 6): attack, defend, go-to.** Defend pays for damage to the
   ward's *threat set* (enemies within their own weapon range + 40 m + the ward's
   bound of the ward, or that hit it in the last 150 ticks) and costs every defender
   `0.5 ×` the ward's hull fraction lost and `0.3` if it dies: no location reward.
   Go-to replaces hold: shaping, arrival bonus 0.2, no presence; it completes per
   ship on arrival (`has_order = 0` from then on).
2. **Obs 403 → 583**: `ship_extras` (hull class, weapon range, distance to my order
   point, is my target or ward, hit my ward recently; 10 × 7) and `order_ships` (the
   5 ships nearest my order point; 22 × 5). The first 403 floats are v5's exactly.
3. **The script pull only on transit rows**: a go-to not yet reached, or a defend
   whose threat set is empty (`env.order_transit`). Never on attack rows, never in a
   fight. Movement heads only.
4. **The new inputs learn 10× faster**: their first-layer columns (actor, and the
   fleet critic's base and encoder) step 10× as far as the rest.

Hypotheses:
- **H1.** The `transit` arm passes O, M, D and H.
- **H2.** The `reward` arm (no pull) follows less than `transit` at every
  checkpoint (go-to in time and defend hull lost), and keeps at least as much
  mission strength.
- **H0.** Neither follows: O fails with the hidden pass close to the followed one
  (the new inputs are unused), or the pilot follows and loses missions as in B2b
  (`transit` only: the pull still reaches combat flying).

## 2. Before training: the baseline stage (run first, in this order)

All on SIM_VERSION 6, sampled actions, the evals of §5.

1. **Sizing.** `w1_400` on the following eval, random commander, followed pass,
   48 matches per mission (seed 410000). Its defended ward-minutes per match set the
   following eval's n (§5, "Sizing").
2. **The teacher** (the order-following scripts, `--a script`, followed pass only: a
   script flies orders it cannot see) and **`w1_400`** (followed and hidden) on the
   following eval at that n.
3. **The O bounds** (§5, "Teacher-first rule"): `gates.py bounds` writes
   `eval/o_bounds.json` and `eval/o_bounds.md` and logs them to `run.out`. Nothing
   changes them once a candidate is evaluated (`gates.py` refuses).
4. **Missions**: script vs script and v1 vs v1 (scripted commanders, live default
   rosters, n = 516 per mission; H's reference), and v1 vs the script on the
   `fleet_v1` deathmatch suite (64 per roster).

The v6 sim re-balances the missions (waves fight on arrival; `M3_PLAN` "Teachers"),
so v1 vs v1 and script vs script are re-measured, not copied from run 1.

## 3. Setup

- **Init**: run 1's `w1_400`
  (`/home/timg/code/rl-fighter/lab/runs/2026-10-31-order-pilot/w1/checkpoints/ppo_bc_400.pt`,
  `W1_400`), actor and fleet critic, widened 403 → 583 with the 180 new first-layer
  columns zero (`widen_actor`, `widen_critic`), so update 0 is exactly `w1_400` on
  the v5 prefix (tested). Fresh optimisers.
- **New inputs at 10× step size** (`new_input_lr_mult: 10`, both arms): Adam's step
  is elementwise, so `NewInputAdam` scales the step of columns 403–582 of the
  actor's first layer and of the fleet critic's base and encoder first layers by
  10 after each Adam step. That is exactly a separate parameter group at 10× the LR
  for those columns (tested against a two-group Adam), while the first layer stays
  one tensor (checkpoints, `load_policy` and the web export unchanged). Run 1
  showed that 400 updates at 1e-4 barely move zeroed columns. The log has
  `new_input_lr`.
- **Reward**: team reward + `1.0 ×` the v6 order reward (`order_rewards`); credit and
  GAE on the sum; both parts logged.
- **KL anchor**: `0.1 × KL(w1_400 ‖ π)` on rows with `has_order = 0` (no order, or a
  go-to already reached), on `obs[..., :403]` (`fit_obs`), cached at rollout time
  as in B2b. `w1_400` is stronger than v1 in missions and plays v1's deathmatch.
- **Script pull** (`transit` arm): `beta_rows: transit`, `beta_heads: movement`; β
  0.05 to update 30, linear to 0 at update 300. Transit rows are
  `env.order_transit` slots whose script flies the order (not the scripted
  commander's advisory deathmatch orders), learner rows only; the rollout raises if
  a transit row ever shows an attack order. The `reward` arm computes the same rows
  (β = 0), so `beta_rows_share` is logged in both.
- **Opponents**: run 1's bands `[[0, 0.5, 0.25, 0.25], [200, 0.4, 0.3, 0.3]]`
  (scripts ≥ 40 %); the frozen pool seeds are **v1** (on `obs[:385]`) and
  **`w1_400`** (on `obs[:403]`), `pool_seed_p` 0.5, plus the run's own 50-update
  checkpoints (583 wide). Scripted opponents follow orders as the v6 teachers do.
- **PPO**: the BC preset (actor LR 1e-4 decaying linearly to 0 at update 300, clip
  0.1 for 200 updates then 0.2, entropy 0.005, 4 epochs, minibatch 4096, γ 0.99, λ
  0.95), **critic warm-up 20 updates** (run 1's: the critic meets 180 new inputs and
  the new defend and go-to rewards). Checkpoints record `obs_dim` 583 and
  `sim_version` 6.
- **Samples**: 256 envs × 128 steps, ≈ 110–120 k learner rows per update.

## 4. Method

Two arms, run concurrently with the same seed (0), 300 updates each, checkpoints
every 50 (each a candidate), 6 sim + 6 torch threads each:

| arm | script pull |
|---|---|
| `transit` | β 0.05 → 0 over updates 30–300, transit rows, movement heads |
| `reward` | none (β 0) |

## 5. Gates and pick (fixed 2026-10-31, before any eval)

Encoded in `spacefight/eval/order_gates_b3.py`; `gates.py` applies them to the JSONs
`eval.sh` writes. Sampled actions throughout.

**Following eval** (`spacefight.eval.orders`, schema `rlf.eval.orders/2`): carrier
battle and convoy, live default rosters, the candidate flying one side's strike craft
(each side of each roster equally often), the script the other side's, capital ships
by script, seed 400000. Random commander: two passes on the same matches (the same
seed per scenario), **followed** and **hidden** (the sim hides the candidate's
orders: no order block, no `order_ships`, no order extras; orders, rewards and
scripts unchanged), n per mission from the sizing rule. Scripted commander: followed
only, 96 per mission, reported. Pooled over both missions. Definitions (the reward's,
from the sim's `order_tracks()`, `ward_threat`, `ward_hull_lost`; module docstring of
`spacefight/eval/orders.py`):

- an *instance* is one effective order of one ship; it *ends* when the target or ward
  is gone, *completes* (go-to) on arrival, and is *censored* when the ship dies, a
  new order arrives, or the match ends;
- attack: median ticks to gun range for targets 0–250 m outside it at the start
  (censored before closing: excluded; target died first: never); damage share on the
  target (pooled);
- defend: ward hull fraction lost per defended ward-minute (a ward is defended on a
  tick when at least one measured ship defends it; minutes counted per ward, not per
  defender); share of the defenders' damage on the ward's threat set at landing;
  distance to the ward reported;
- go-to: share of judged instances arriving within `1.5 × (d / speed cap + 60
  ticks)`, `d` the distance to the arrival circle at the first live tick; censored
  before the deadline: excluded, censored after it: a failure. Near and far (`d >
  200 m`) reported apart (the sim does not export which draw a point came from, so
  "far" is by distance); arrivals per ship-minute reported;
- engine duty per hull and per order kind, reported.

Per-tick pooled metrics (the shares, hull lost per minute, distance) count censored
instances' ticks too: censoring cuts a rate's numerator and denominator together.

**Sizing** (before the teacher is measured): n per random-commander scenario is the
smallest multiple of 6 (twice the 3 default rosters) at which the sizing run's
defended ward-minutes per match give `1.3 × 300` ward-minutes, clamped to 96–384
(`order_gates_b3.orders_n`; `eval/n_orders.txt`).

**Teacher-first rule.** The teacher is measured first. Every O bound it cannot meet
is replaced, before any candidate is evaluated, by one set from the teacher:
`teacher − 0.05` for a `≥` bound, `teacher × 1.05` for a `≤` bound (an absolute
bound then). A relative bound ("hidden + 0.05", "0.8 × hidden") is judged for the
teacher against `w1_400` with its orders hidden, because a script cannot be hidden.
A teacher that never closes on attack targets (median "never") keeps the plan's 150.
`eval/o_bounds.md` lists each bound, the teacher's value, what it was judged against
and whether it was replaced.

| gate | check | bound |
|---|---|---|
| **O following, random commander** | attack / defend / judged go-to instances | ≥ 30 each |
| | defended ward-minutes, followed and hidden | ≥ 300 each |
| | attack: median ticks to gun range (targets 0–250 m outside it) | ≤ 150 |
| | attack: damage share on target | ≥ hidden + 0.05 |
| | defend: ward hull lost per defended ward-minute | ≤ 0.8 × hidden |
| | defend: share of the defender's damage on the threat set | ≥ hidden + 0.05 |
| | go-to: share arriving within the deadline | ≥ 0.7 |
| **M missions** (scripted commanders, live default rosters) | carrier battle win vs v1 (draws ½), n = 516 | ≥ 0.47 |
| | convoy win vs v1, n = 516 | ≥ 0.47 |
| | mean of the two vs v1 | ≥ 0.52 |
| | mean mission win vs `w1_400`, n = 258 per mission | ≥ 0.45 |
| **D deathmatch** (`fleet_v1`, 64 per roster) | win vs the script | ≥ 0.85 |
| | win vs v1 | ≥ 0.45 |
| **H health** | per mission: time-limit rate | ≤ v1 vs v1's + 0.10 |
| | per mission: stalemate rate | ≤ v1 vs v1's + 0.05 |
| | per mission and deathmatch: NaN or stuck matches (share) | ≤ 0.01 |
| | per mission and deathmatch: outside-arena share | ≤ 0.02 |
| | deathmatch time-limit rate | ≤ v1 vs script's + 0.10 |

"hidden" is the candidate's own hidden pass on the same matches. Expect the defend
threat-set share to saturate late in carrier battles (a 380 m reach in a 450 m
arena); the teacher-first rule covers it. The scripted commander's following, the
near / far go-to split, arrivals per minute, distance to the ward and engine duty
per hull and order kind are reported in `gates.md`, not gated. There are no duel
gates.

**Pick**: among candidates (both arms, updates 50–300) that pass every gate, the
highest mean mission win vs v1; ties by the deathmatch win vs v1. If none passes,
nothing is promoted, the live page keeps its champion, and `results.md` names the
failed checks.

## 6. Budget (16 cores, no GPU; estimated, to be checked in the SMOKE run and the first updates)

| stage | basis | estimate |
|---|---|---|
| baseline | sizing ≈ 15 s; teacher (followed only) ≈ 1.5 min; `w1_400` ≈ 3.5 min; script vs script ≈ 1.5 min, v1 vs v1 ≈ 3.4 min, v1 deathmatch ≈ 1 min (run 1's rates) | **≈ 12 min** |
| **PPO, two arms at once** (6 sim + 6 torch each) | B2b: 21 s/update with the anchor cache (403 wide); 583 inputs add ≈ 2 % to a minibatch's forward + backward (measured, actor + fleet critic); allow 10 % for the wider buffers and the transit flag | 300 updates at ≈ 23 s ≈ **1.9 h**, allow **2.2 h** |
| gate evals per candidate (12 threads) | following at n = 240 (two passes) + 96 scripted: 1 152 matches ≈ 3.3 min (run 1: 384 matches in 57 s, + 15 % for positions); missions vs v1 3.4 min, vs `w1_400` 1.7 min; deathmatch ≈ 2 min | **≈ 10.5 min** (12 min at n = 384); the 6 hundreds ≈ 1.1 h, all 12 ≈ 2.1–2.4 h |
| **total** | | **≈ 4.5–4.8 h** |

`EVAL_UPDATES` runs the hundreds first ("100 200 300 50 150 250"): about 3.5 h into
the night the gates can already pick among them, and the rest is resumable
(`run.sh eval gates`). Above 30 s/update (1.3 × the estimate) set `N_UPDATES=250`;
above 35 s/update, `N_UPDATES=200` and `EVAL_UPDATES="100 200 50 150"`. Memory: two
arms ≈ 4 GB each (583-wide obs over 12 slots × 256 envs × 168 steps ≈ 1.2 GB per arm
plus the buffers), inside 29 GB.

## 7. Risks

| risk | signal | response |
|---|---|---|
| the pull reaches combat flying again (B2b) | `beta_rows_share` > 0.3; M vs `w1_400` well below ½ at update 50; `vs_scripted_win` drops | the transit flag is the sim's; β is 0.05 (B2b: 0.1); the `reward` arm is the control |
| the 10× columns blow up | `approx_kl` > 0.05 or `kl_anchor` > 0.5 after the warm-up; explained variance falls | a rerun at `NEW_INPUT_LR_MULT=3` |
| defend never pays against winning | defend hull lost ≈ hidden in both arms | the teacher-first bound shows what the teacher reaches; reported per arm |
| too few defended ward-minutes | O "defended ward-minutes" fails | the sizing rule (1.3 × 300) should prevent it; rerun the eval with `N_ORDERS_MAX` higher |
| go-to farming by re-staging | arrivals per minute ≫ the teacher's (gates.md) | the sim pays a point within 40 m once |
| self-play destabilises | `vs_scripted_win` falls after update 200 | scripts stay ≥ 40 %; an earlier checkpoint |
| throughput below the plan | > 30 s/update | §6 |

## 8. Running it

From the repo root of the main checkout, after `m3-b3-sim` and this branch are merged
and the SIM_VERSION 6 extension is built (`uv run maturin develop -m
crates/sim-py/Cargo.toml --release`; `run.sh` refuses an older `rlf_sim`). Needs
fleet pilot v1 (`V1`, default
`/home/timg/code/rl-fighter/lab/runs/2026-10-30-fleet-pilot/arm_warm/checkpoints/ppo_bc_400.pt`)
and run 1's `w1_400` (`W1_400`, default as in §3):

```
SMOKE=1 lab/runs/2026-11-01-order-pilot-b3/run.sh      # every stage at tiny sizes, smoke/ (gitignored)
nohup lab/runs/2026-11-01-order-pilot-b3/run.sh > lab/runs/2026-11-01-order-pilot-b3/run.out 2>&1 &
```

Stages `baseline ppo eval gates`, each skipping finished work (PPO resumes from the
latest checkpoint; SIGTERM checkpoints after the current update). `run.sh eval gates`
re-runs only those. Logs: `run.out`, `transit.out`, `reward.out`,
`<arm>/log.jsonl`; `eval/o_bounds.md` (fixed before the candidates),
`eval/n_orders.txt`, `eval/gates.md`. Afterwards write `results.md` from
`eval/gates.md`, and promote the pick only if it passes.
