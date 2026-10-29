# Learnability spike: can actuator-level control learn in a night?

| | |
|---|---|
| Run | `2026-10-28-learnability-spike` (first lab run; this file sets the `plan.md` format) |
| Branch | `m1-sim` → `spike/learnability` |
| Question | DESIGN §12 item 3: with a small MLP on a CPU-only laptop, does a fighter learn to fly, aim and fire by driving thrusters and a trigger directly, within ~4 h? |
| Scenario | 1v1 fighter vs fighter, arena 450 m, 90 s limit, `reaction_ticks` 2 (SIM_SPEC §0 item 3), on `SIM_VERSION` 2 |
| Status | planned (update to running / done / aborted); sim v2 block **lifted** 2026-10-28: WP11–15 merged on `m1-sim`, `SIM_VERSION` 2, duel gate passed (`lab/runs/2026-10-28-sim-v2/results.md`) |
| Hands | balance sweep: agent A (= SIM_SPEC WP15); policy + BC: agent B; PPO loop: agent C; eval: agent D (see §8) |

**Sim v2 first.** The sim refinements in SIM_SPEC §0 (lighter damping, throttle ramp,
reaction delay, directional armour, shield-first hits, 385-float obs, exact
`act_mask`, `decision_tick` credit) land as `SIM_VERSION` 2 *before* this run; the
balance change below is tuned on v2, not v1. Numbers in this plan that depend on the
sim (obs size, action semantics, credit tail, memory) are the v2 numbers.

Format for future runs: the table above, then §1 hypothesis, §2 pre-gates, §3 setup,
§4 method, §5 budget and schedule, §6 eval and verdict, §7 risks, §8 work packages.
`results.md` follows the verdict template in §6.4. `config.yaml` holds every number
used, `log.jsonl` the per-update metrics, `checkpoints/` the weights.

## 1. Hypothesis and success criteria

**H1.** Behaviour cloning from the Rust scripted fighter gives a policy that already
flies and fights (not just a prior), and PPO from that start beats the script.
**H2.** PPO from scratch with the same sample budget does *not* reach the same
strength, which tells us the scripted controllers are worth maintaining per hull.
**H0 (null).** Nothing beats the script: the actuator action space is too hard for an
MLP on this budget, and M3 needs the residual-policy or handwired variants first.

Measured on the fixed eval of §6 (N = 512 matches vs the script, sides swapped):

| Metric | BC only | BC + PPO (pass) | BC + PPO (strong) |
|---|---|---|---|
| Win rate vs script (draws count ½) | ≥ 0.35 | ≥ 0.60 | ≥ 0.75 |
| Draw rate | ≤ 0.15 | ≤ 0.10 | ≤ 0.10 |
| Engagement rate (share of live ticks with enemy inside 1.2 × gun range) | ≥ 0.5 × script | ≥ 0.4 | ≥ 0.5 |
| Hit rate (hits / shots) | ≥ 0.5 × script | ≥ 0.6 × script | ≥ script |
| Share of ticks outside the arena | ≤ 0.02 | ≤ 0.02 | ≤ 0.01 |
| Matches ending by kill (not time limit) | ≥ 0.8 | ≥ 0.9 | ≥ 0.95 |
| Mean main-engine thrust level (v2 ramped level in [0, 1], obs thruster feature 6) | report | 0.2–0.9 (neither idle nor pinned) | same |

"Flies on purpose" is the row block engagement / hit rate / outside arena / kill
rate taken together: a policy that wins by sitting still, or by orbiting the edge,
fails those rows even if it wins. The scratch control is reported on the same table;
H2 holds if BC + PPO leads it by ≥ 0.15 win rate at equal samples.

Verdict rules: **PASS** = BC + PPO reaches every "pass" cell. **PARTIAL** = BC only
reaches its column, or PPO wins but fails a watchability row. **FAIL** = BC below its
column or PPO never above 0.5 vs the script. Any verdict with a working pipeline is a
useful result; the journal entry says which.

## 2. Pre-gate: duel balance (after sim v2, before any training)

### 2.1 Problem (measured on v1)

Scripted fighter vs fighter ends in ~150 ticks on the first head-on pass, half of them
mutual kills. Arithmetic: 60 hp / 6 dmg = 10 hits; at the "attack" power split
(`P_w` = 1.48) the gauss cycles every 0.16/0.96 = 0.17 s (6 shots/s); a head-on pass
with 120 m/s closing speed spends 300/120 = 2.5 s inside range, both noses on, so both
land ~10 hits in one pass. Symmetric geometry + one-pass kill = same-tick deaths.
One-pass kills also mean the reward signal is one event per episode, and the fire
head only matters for ~2 s of a 5 s episode.

### 2.2 Change (data only: `assets/weapons.yaml`, `assets/hulls/fighter/hull.yaml`)

The starting tuple is written into the assets by SIM_SPEC WP14 (it is the v2
baseline the golden traces are generated on); this run's sweep (WP15) moves it if a
gate fails.

**Final (WP15, 2026-10-28):** gauss **5 dmg** / 0.20 s / 220 m / 200 m/s / 1.0°,
fighter **80 hp**, armour as designed. That is the start tuple below with `damage` 3 → 5,
plus a scripted-pilot change (extend after a merge; SIM_SPEC §11). With the sim.js
pilot no tuple could pass: the fighters never left gun range after the first merge.
At `reaction_ticks` 2: median 1296 ticks, 1 % mutual kills, 0 % time limit, 3 passes,
32 % hp per pass. Every tried tuple is in `lab/runs/2026-10-28-sim-v2/results.md`.

| Field | v1 | v2 start | why |
|---|---|---|---|
| gauss `damage` | 6 | **3** | 27 hits to kill at 80 hp: a pass takes a third of a ship, not all of it |
| gauss `interval` | 0.16 | **0.20** | max 14 dps at attack power, 10 dps even split |
| gauss `range` | 300 | **220** | shorter in-range window per pass (220/120 = 1.8 s), more passes |
| gauss `speed` | 240 | **200** | lead matters more in turning fights; still 3.3 × ship cap |
| gauss `spread_deg` | 0.6 | **1.0** | mild range fall-off (±1.9 m at 220 m vs a 2.5 m target radius); not a dice roll |
| fighter `hp` | 60 | **80** | with 3 dmg, 27 hits; one perfect head-on pass ≤ 26 dmg (33 %) |

v2 changes the arithmetic in three ways the sweep must expect. **Armour** (nose 0.5×,
flank 1×, engine 1.5×): a head-on pass now does ≤ 13 hull damage (17 %) and a tail
chase 4.5 per hit, so passes count rises and the first tuple to try if duels run
*long* is `damage: 4`, not 2. **Reaction delay** (2 ticks) and the **throttle ramp**
lower the script's hit rate a little (it predicts, SIM_SPEC §11, but the ramp
slows its turn reversals); **lighter damping** lengthens the turn-around between
passes. Expected: a kill needs 4–7 passes at 4–6 s each, so a duel runs 20–45 s.
Same-tick deaths need both ships to take their last hit on the same tick, which the
arrival jitter, spread and asymmetric armour make rare. Gunship/strafer are untouched
(gauss on the gunship's broadsides also gets the change; acceptable, out of scope).
Reward weights stay: 0.01/hp means a kill is worth 0.8 to the shooter in step
rewards plus 1.0 terminal, so the terminal term still dominates. Fire cost stays at
-0.002 (a 3-dmg nose hit is worth 0.015 after armour, a tail hit 0.045; roughly 10 %
of shots must land to break even).

### 2.3 Verification gate (`tools/duel_sweep.py`, ~2 min)

Script vs script, one `VecEnv` with N = 200 (seeds 0..199, one episode each, stop
reading an env after its first `done`), 12 threads, run at `reaction_ticks` 0, 2 and
4 (the gates apply at 2, the default; 0 and 4 are reported for SIM_SPEC §15 q7).
Report median / p10 / p90 match length, draw rate, time-limit rate, passes per match
(count of transitions of `dist < range` from `obs_block(obs, "ships",
split_slots=True)[..., 0, 11]`, per ship), hits per pass, damage per pass as a share
of hp, shots per match, hit rate, share of ticks outside the arena, and the hull-hit
multiplier mix (share of hits with `mult` 0.5 / 1 / 1.5 from `events()`).

| Gate | accept |
|---|---|
| median length | 450–1500 ticks (15–50 s) |
| draw rate (winner = -1 by kill) | < 0.10 |
| time-limit endings | < 0.10 |
| median passes before the kill | ≥ 3 |
| damage per pass | 10–40 % of hp |

If a gate fails, adjust in this order: `damage` (4 if too long, 2 if too short),
then `range` (200/260), then `hp`. Never more than two sweeps; record every tried
tuple in `results.md`. `SIM_VERSION` is already 2 (WP14); if the sweep changes the
assets, regenerate `crates/sim/tests/golden/*` with `UPDATE_GOLDEN=1` (the version
stays 2: the traces were never published under the old tuple), rerun
`scripts/check.sh`, rebuild `rlf_sim`, and update SIM_SPEC §4.1/§4.2.

## 3. Setup

- **Env:** `RustVecEnv` (`spacefight/env/rust_env.py`) over `rlf_sim.VecEnv`,
  `fleets=[["fighter"],["fighter"]]`, `reaction_ticks=2`, N = 256, `n_threads` = 12
  (6 when two runs share the box), seed per run. Learner = team 0 in every env;
  team 1 is the opponent (§4.2). Obs 385-d straight from the sim (SIM_SPEC §7.2:
  already body-frame and scaled, includes the thrust levels and the 2 queued
  actions; no running normalisation), plus masks `act_mask`, `thruster_mask`,
  `turret_mask`, `fixed_turret`.
- **Action semantics (v2):** the 8 throttle heads are rate commands on the
  thruster level (0 = decrease, 1 = hold, 2 = increase, ±1/6 per tick), not levels;
  every head takes effect 3 ticks after the obs it was chosen from (`reaction_ticks`
  2 + 1). The head shapes are unchanged (3/3/2/7), so the policy layout below is as
  planned. `act_mask = 0` now means exactly "this row has no effect" (SIM_SPEC §7.1),
  so masking rows out of the loss is exact.
- **Policy** (`spacefight/rl/spike_policy.py`): MLP 385 → 256 → 256 (tanh) → one
  61-logit layer sliced into heads: 8 throttles × 3, 6 slews × 3, 6 fires × 2,
  1 power × 7. Heads are independent categoricals. Masking: absent thruster/turret
  slots and fixed-gun slew heads contribute zero log-prob and zero entropy (their
  samples are overwritten with `THROTTLE_HOLD` (1) / `SLEW_HOLD` (1)); rows with
  `act_mask = 0` are excluded from every loss. Sampling without 21 `Categorical`
  objects: reshape the 3-way logits to `[B, 14, 3]`, fire to `[B, 6, 2]`, power
  `[B, 7]`, and use `log_softmax` + `multinomial` on the flattened rows. ~180 k
  parameters.
- **Critic:** separate MLP 385 → 256 → 256 → 1 on the ship's own obs. Decision: no
  centralised critic for 1v1. The obs already contains the enemy's relative state,
  there is no teammate to aggregate, and a separate net lets BC train the actor
  alone while the critic warms up on its own (§4.2). The MAPPO critic returns in M3.
- **Credit:** `RustCreditAdapter` (`spacefight/rl/credit.py`) over hits `[N,64,6]`:
  each hit's shooter reward is moved from the landing step to the buffer step
  stamped with the hit's `decision_tick` (SIM_SPEC §8: the obs tick the fire action
  was chosen on, `fire_tick − 1 − reaction_ticks`). `T_TAIL` = 40 ticks (gauss life
  220/200 s = 33 ticks + 3 ticks of reaction delay + margin).
- **Determinism:** torch seed = run seed; env seeds listed in `config.yaml`.

## 4. Method

### 4.1 Phase A: behaviour cloning

- **Dataset** (`spacefight/rl/bc.py:collect`): script on both sides, N = 256,
  labels from `env.scripted_actions()` for every present ship; the executed action is
  the label except that, per ship per tick with p = 0.15, one random head is
  replaced by a uniform draw (DART-style noise, so the data covers recovery states
  the clean script never visits). Keep rows with `act_mask = 1`. Size: **2 M rows**
  (≈ 3.1 GB obs in f32 at 385 floats; ~4 k env steps, under a minute; store as
  float16 or drop to 1.5 M rows if memory is tight). Hold out 5 % by env index.
  Note the labels are rate heads: the script's throttle label depends on the
  queued actions in the obs (SIM_SPEC §11 `projected_levels`), which is why the
  pending-action block must be in the obs for BC to be a function of it.
- **Training:** masked per-head cross-entropy, equal weight per head, Adam 1e-3 with
  cosine decay to 1e-4, batch 4096, **8 epochs** (≈ 4 k minibatches, ~2 min at
  measured 200 k samples/s). Entropy floor: label smoothing 0.02 so PPO starts with
  non-degenerate logits.
- **Eval:** (a) held-out action agreement per head group (throttles, slews on the
  gunship are n/a here, fire, power), plus precision/recall on `fire = 1` (expected
  base rate 5–15 % of ticks); (b) `eval.duel` BC vs script (§6). BC column of the
  §1 table is the gate for Phase B: if BC is below it, Phase B still runs (the
  spike is about the pipeline too) but the verdict notes it.

### 4.2 Phase B: PPO from the BC start, with a decaying pull toward the script

PPO as v1 (`spacefight/rl/ppo.py` logic, re-implemented for the masked heads):

| Hyperparameter | value | note |
|---|---|---|
| N envs × T steps | 256 × 128 | 65,536 ship-samples per update (2 ships; opponent rows dropped unless self-play) |
| γ / λ | 0.99 / 0.95 | v1 |
| clip ε | 0.2 (0.1 for the first 200 updates) | protect the BC init |
| epochs × minibatch | 4 × 4096 | v1 |
| LR | 1e-4 actor, 3e-4 critic, linear decay to 0 | lower than v1's 3e-4 for the actor |
| entropy coeff | 0.005, per head mean | 21 heads: 0.01 summed over heads was v1's scale |
| value coeff / grad norm | 0.5 / 0.5 | v1 |
| critic warm-up | 30 updates, actor frozen | the BC actor has no value function; fresh advantages would wreck it |
| script pull β | 0.1 → 0 linearly over updates 30–700 | aux loss `−β · mean log π(a_script | s)` on the learner's own rollout states; the script is deterministic so this cross-entropy *is* the KL to it (DESIGN §7). Labels are free: call `scripted_actions()` and copy before writing the learner's actions |
| updates | 2000 | ≈ 131 M ship-samples, 33 M env steps, ~45 k matches at ~25 s each |
| checkpoints | every 100 updates + final | `checkpoints/ppo_bc_{u}.pt` |

**Opponent schedule** (per env, resampled when that env's episode resets):

| updates | scripted | self (mirror, same weights, team 1 rows also trained) | frozen snapshot from pool |
|---|---|---|---|
| 0–600 | 100 % | 0 | 0 |
| 600–1200 | 50 % | 30 % | 20 % |
| 1200–2000 | 30 % | 40 % | 30 % |

Pool = every 100-update checkpoint; sample uniformly. Snapshot inference is one extra
forward on the team-1 rows of those envs (≤ +1 ms per step). Self-play rows join the
batch; snapshot and scripted rows do not.

**Control: PPO from scratch.** Same code path, same budget (2000 updates), same
opponent schedule, β = 0, no critic warm-up, random init (orthogonal, small output
gain), LR 3e-4 actor. Runs concurrently with the BC run, 6 threads each (§5).

### 4.3 Logged per update (`log.jsonl`)

update, wall time, samples/s, sim steps/s; reward mean and its components (damage
dealt/taken, fire cost, arena, terminal, injected credit); rollout win/draw/loss vs
each opponent kind; episodes finished and mean length; entropy per head group;
approx KL and clip fraction; value loss and explained variance; aux script NLL and β;
main-engine duty, fire rate, hit rate, outside-arena share; current snapshot pool.

## 5. Compute budget and night schedule

Measured on this laptop (torch 2.10 CPU, H = 256, batch 512 for inference,
4096 for updates): inference 1.4 ms / 512 rows at 12 threads (1.7 at 6); forward +
backward + Adam 200 k rows/s at 12 threads (160 k at 6). Sim: 14 k batched steps/s
at N = 256 (0.07 ms per step, negligible). Budget per update with 6 threads each
and two concurrent runs:

| Stage | per update | note |
|---|---|---|
| rollout, 128 steps | 128 × (1.7 ms learner + 0.5 ms snapshot avg + 0.1 ms sim + ~1 ms Python glue: copies, masks, credit, logging) ≈ 0.45 s | glue is the uncertainty; measure in WP-C's smoke test |
| GAE + credit | ~0.05 s | NumPy |
| PPO, 4 × 65 k rows | 0.26 M rows / 160 k = 1.6 s | dominant |
| **total** | **≈ 2.2 s** → ~30 k ship-samples/s | 2000 updates ≈ 75 min; plan 2 h 15 for both runs, allowing 2× glue overrun |

| Clock | Step | Wall |
|---|---|---|
| 03:00 | branch off `m1-sim` at SIM_VERSION 2 (WP14 merged), build (`maturin develop --release`), `duel_sweep` ×1–2 (WP15), golden regen if the tuple moved, tests | 25 min |
| 03:25 | BC data + train + BC eval (12 threads) | 15 min |
| 03:40 | PPO-from-BC and PPO-from-scratch concurrently, 6 sim + 6 torch threads each | 2 h 15 |
| 05:55 | hard stop of training if still running (the loop checkpoints on SIGTERM) | |
| 05:55 | eval: 3 policies × {script, BC, best previous checkpoint} × 512 matches ≈ 10 runs × 1 min | 15 min |
| 06:10 | `results.md`, journal entry, commit; no promotion (no champion yet, no eval gates file yet) | 30 min |
| 06:40 | slack | 20 min |

Memory: BC dataset ≈ 3.1 GB (f32) or 1.6 GB (f16), rollout buffer 65 k × 385 × 4 B
≈ 100 MB per run, far below 29 GB. Checkpointing: `torch.save` of actor + critic + optimizer + update index +
RNG states every 100 updates and on SIGTERM; a `--resume` flag restarts from the
last one.

## 6. Evaluation protocol

### 6.1 Harness (`spacefight/eval/duel.py`)

`evaluate(a, b, n=512, seed=100_000) -> DuelResult` where `a`, `b` are controllers:
`Scripted()`, `Policy(path, sample=True|False)`. N = 512 envs, each runs exactly one
episode (seeds 100,000 + i, fixed forever for this scenario); 256 envs with `a` on
team 0 and 256 with `a` on team 1, so arrival side bias cancels. Primary numbers use
stochastic sampling (the distribution PPO optimises); argmax is reported as a
second row. Metrics per side: win / draw / loss, match length (median, p10, p90),
ending type (kill / time limit), passes, shots, hits, hit rate, damage dealt,
engagement rate, outside-arena share, main-engine duty, fire rate, mean speed, and
`nan_or_stuck` (any NaN in obs, or a ship with |vel| < 1 for > 10 s while an enemy
lives). Output as JSON next to the checkpoint, plus a one-line Markdown row.

### 6.2 Matrix

| a | b |
|---|---|
| script | script (balance baseline; also gives the script's hit and engagement rates used as denominators) |
| BC | script |
| PPO-BC final, and the best checkpoint by rollout win rate | script, BC, PPO-BC at 500 / 1000 / 1500 |
| PPO-scratch final | script, PPO-BC final |

### 6.3 Health

No NaNs anywhere; no stuck ships; `n_threads` 1 vs 12 give identical `state_hash`
under the new assets (regression on the determinism test).

### 6.4 `results.md` template (also the public journal entry)

```
# <title that states the finding>              e.g. "Cloned pilots fly; PPO makes them win"
Date, run dir, branch, commit, SIM_VERSION, verdict: PASS | PARTIAL | FAIL
## What we asked          (two sentences, for a visitor)
## What we did            (balance change with before/after sweep numbers; BC; PPO; control)
## Results                (the §1 table filled in, one row per policy; the eval matrix; a learning-curve plot: win rate vs script and entropy over updates, both runs)
## What it looked like    (two or three qualitative observations from render_state replays: does it lead, does it turn to re-engage, what it does at the edge)
## What we learned        (bullets: which of H1/H2/H0 held; surprises)
## Next                   (the one experiment this result argues for; backlog items added)
## Numbers                (compute used, samples, wall time, throughput)
```

## 7. Risks and what to try next

| Risk | Signal | Response |
|---|---|---|
| BC collapses the fire head to "never fire" (rare positive class) | fire recall < 0.5 on held-out; BC vs script shots per match ≪ script | reweight fire head loss 1:3 for the positive class, or resample dataset so 30 % of rows have `fire = 1`; check that cooldown (`obs_block(obs, "turrets", True)[..., 0, 5]`) is what the script keys on |
| Throttle heads collapse to "hold" (v2 rate heads: hold is the majority label once a level is reached) | throttle entropy ≈ 0 by update 300 with main-engine level pinned; BC throttle agreement high but level duty outside 0.2–0.9 | per-head entropy floor on the throttle group; weight increase/decrease labels 2:1 in BC; confirm the pending-action block is in the obs (the label is a function of it) |
| Reaction delay makes the script's aim too poor to be a useful BC target | script-vs-script hit rate < 0.5 × its v1 value in the sweep at `reaction_ticks` 2 | run the sweep at 0 and 2; if 2 is unlearnable, train at 0 and report; SIM_SPEC §15 q7 |
| BC flies but cannot recover from off-distribution states (spins, drifts out) | BC outside-arena share > 0.1, stuck ships | raise DART noise to 0.3, add 10 % of rows from a *perturbed* script (random throttle for 0.5 s bursts) |
| PPO destroys the BC policy in the first updates | win rate drops below BC's within 100 updates; KL to BC spikes | longer critic warm-up (60), clip 0.05 early, β floor 0.02 for the whole run |
| Entropy collapse (throttle heads pinned) | per-head entropy < 0.1 nats by update 500 | entropy coeff 0.02; per-head entropy floor loss |
| Edge exploit: the policy learns to make the script chase it out of the arena | high win rate with outside share > 0.02, long matches, time-limit endings | `ARENA_PENALTY` ×5 (sim const; needs a version bump), or shrink the arena to 350 (SIM_SPEC §15 q1) |
| Kiting at max range (strong but boring) | engagement rate < 0.3 with win rate high | shorter `range` (180), or reward time-in-range; this is the watchability gate in action |
| Draws return under learned play (both learn to disengage) | draw / time-limit rate > 0.2 | lower time limit to 60 s; small per-tick cost −0.0005 for both sides |
| Scratch control learns nothing (no shots ever land) | hit rate ~0, flat reward | expected; it is what H2 predicts. Report it, do not rescue it this night |
| Throughput half of plan (glue) | < 15 k samples/s per run | drop to 1200 updates for both runs; keep the comparison at equal samples |
| Self-play destabilises (win rate vs script falls after 600) | | hold scripted share at 100 % and record; league design is M3's job |
| Balance gate never passes in two sweeps | | train on the best tuple anyway and flag the balance as open; the spike is about learnability |

Next experiments this run sets up: residual policy (logits = script one-hot ×
temperature + learned), handwired script compilation, strafer and gunship BC with
turret slew heads, and the attention policy over the same records.

## 8. Work packages

Keep code in `spacefight/` (Python), entry point `spacefight/train_spike.py`, tests
in `tests/`. `RustVecEnv` and the credit adapter at v2 (SIM_SPEC WP10 + WP13) are
assumed present; sim v2 (SIM_SPEC §14.1 WP11–14) must be merged before A starts.
Every package: `black`, `mypy`, `pytest` green.

| WP | agent | scope | files | acceptance | depends / parallel |
|---|---|---|---|---|---|
| A | A | duel sweep tool and the balance gate on sim v2 (= SIM_SPEC WP15; the version bump and first golden regen are WP14's) | `tools/duel_sweep.py`, `tests/test_duel_sweep.py`, `assets/weapons.yaml`, `assets/hulls/fighter/hull.yaml` and `crates/sim/tests/golden/*` only if the tuple moves | `duel_sweep.py --n 200 --reaction-ticks 2` prints the §2.3 table and exits non-zero on a failed gate; pytest runs it on 16 seeds with the gates relaxed to "no draws > 50 %, median > 300"; `scripts/check.sh` green; SIM_SPEC §4.1/§4.2 tables match the assets | after SIM_SPEC WP14; parallel with B, D |
| B | B | masked multi-head policy and critic | `spacefight/rl/spike_policy.py`, `tests/test_spike_policy.py` | `sample(obs, masks)` returns an `[B, 21]` int8 action row the env accepts; masked heads give exactly 0 log-prob and entropy; `log_prob` of a sampled action equals the value returned at sampling; `evaluate` on an all-`act_mask`-false batch returns a zero loss; save/load round-trip | parallel with A, D |
| C | B | behaviour cloning | `spacefight/rl/bc.py`, `spacefight/train_spike.py bc`, `tests/test_bc.py` | collecting 20 k rows yields labels equal to `scripted_actions` where no noise was applied and the noise rate within 0.15 ± 0.02; training on 50 k rows for 2 epochs reaches ≥ 0.9 throttle agreement on held-out (the script is a deterministic function of obs); writes `bc.pt` + `bc_eval.json` | after B; parallel with D, E |
| D | D | eval harness | `spacefight/eval/__init__.py`, `spacefight/eval/duel.py`, `spacefight/eval/controllers.py`, `tests/test_eval_duel.py` | script vs script on 32 seeds is deterministic across two calls and across `n_threads`; sides are swapped exactly half; metrics match a hand-computed count on one rendered episode (passes, shots, hits via `hits`/events); JSON schema fixed | needs B's `Policy` interface only; parallel with A, C |
| E | C | PPO loop with credit, aux script loss, opponents, logging, checkpoints | `spacefight/rl/spike_ppo.py`, `spacefight/rl/opponents.py`, `spacefight/train_spike.py ppo`, `tests/test_spike_ppo.py` | 3 updates on N = 8, T = 16 run end to end from `bc.pt` and from scratch; credit lands on the decision step (`decision_tick`, 3 ticks before the shot at `reaction_ticks` 2; reuse the `test_credit` pattern with the Rust adapter); opponent assignment matches the schedule shares within ±1 env; `--resume` continues the update index; SIGTERM saves a checkpoint; `log.jsonl` rows carry every §4.3 key; smoke test reports measured samples/s (feeds §5) | after B; parallel with C, D |
| F | C | run orchestration and write-up scaffold | `lab/runs/2026-10-28-learnability-spike/{run.sh,config.yaml,results.md}` | `run.sh` performs §5 in order with the thread split, writes `results.md` from the eval JSONs through a small template fill (`tools/lab_report.py`), never deletes checkpoints | after A–E |

Order: A, B, D start together; C and E start when B's interface is merged (B
should publish the `Policy` class signature first, within its first hour); F last.
Critical path: B → E → F. The night run itself is F.
