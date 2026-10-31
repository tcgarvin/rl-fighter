# Order pilot B2b: show the pilot how to follow, and make following pay

| | |
|---|---|
| Run | `2026-10-31-order-pilot-b2b` (M3 stage B, follow-up to `2026-10-31-order-pilot`) |
| Branch | `m3-orders-b2b` |
| Question | Starting from run 1's `w1_400`, does a script pull on ordered rows (and, in one arm, a short ordered DAgger round first), with hold points near the action and a held order paying on the scale of a kill, get the pilot to fly its orders (gate O) without losing run 1's mission gains (M, D, H)? |
| Scenario | as run 1: rosters `orders_v1` (deathmatch 0.4 / carrier battle 0.3 / convoy 0.3, each team's commander scripted or random with p = ½), padded to 12 ships, arena 450 m, clocks 90 / 150 / 120 s, `reaction_ticks` 2; SIM_VERSION 5 **as changed on this branch** (random hold points, presence pay; the version number is unchanged) |
| Status | **planned**: gates and the pick rule fixed below before any B2b candidate is evaluated; `SMOKE=1` passes every stage |
| Ships | the pick replaces fleet pilot v1 on the live page |

## 1. Run 1 failed; what this run changes, and why

**Run 1 failed its question.** No candidate of either arm passed gate O (order
following); nothing was promoted and v1 stays the champion
(`../2026-10-31-order-pilot/results.md`). Its pilots read the order block a little
(attack targets closed twice as fast as with the block zeroed, guards a little
closer) but ignored holds, and guard and hold time stayed far below the bounds. As a
side result, training on the missions made a much better mission pilot: `w1_400`
wins 0.79 of carrier battles and 0.74 of convoys against v1.

B2b changes four things, each aimed at one cause in run 1's "Why, probably":

1. **A script pull on ordered rows** ("nothing shows the pilot *how* to follow").
   The β term of the fleet run (NLL of the script's action) now averages over
   *ordered* rows only (`beta_rows: ordered`): rows whose obs shows an order that the
   ship's script flies (`RustVecEnv.scripted_order_rows`). Their label from
   `scripted_actions()` is then the order-following script's action for that ship.
   The scripts follow every order of a random commander and of the scripted
   commander in carrier battles and convoys, but not the scripted commander's
   advisory deathmatch orders, which the obs still shows (`has_order = 1`); those
   rows are excluded from the pull (and, as in run 1, get no KL anchor). Unordered
   rows keep the KL anchor to v1 (0.1). β is 0.1 to update 30, then falls linearly
   to 0 at update 300.
   - **Movement heads only** (`beta_heads: movement`: the 8 thrusters and the power
     split; not turret slew or fire). An order says where to fly; the pilot already
     aims and fires better than the script (v1 beats it 0.89 in deathmatch), and the
     script's fire labels are not order-following. Probe (one 100 k-row ordered
     DAgger round from `w1_400`, all heads): the fire head's agreement with the
     script rose 0.64 → 0.93 and its recall fell 0.81 → 0.23, i.e. the pilot learned
     to fire like the script. Movement heads only: 0.64 → 0.83.
2. **Hold points near the action** (the random commander, `SIM_SPEC` §5.9): "a
   random hold point is usually away from the fight". Now between the squad's
   centroid and its two nearest enemies (25–75 % of the way, 60 m jitter, clamped
   into 0.7 R); 20 % stay far, uniform over the 0.7 R disc as before, so a hold still
   means "go to the point". Median squad-to-point distance at the draw: 117 m, against
   261 m for run 1's rule on the same states. Holding and fighting now mostly
   coincide.
3. **Presence on the scale of a kill** (`SIM_SPEC` §8): `+0.0009` per step inside
   (was `0.0003`), still for at most 300 steps per instance: a held order pays up to
   0.27 + the 0.1 arrival bonus, about half a fighter kill. The rate rises rather
   than the cap because random orders last 180–480 steps and ships stay inside more
   than 300 steps in under 10 % of instances, so a longer cap at the old rate would
   pay almost nothing more; under γ = 0.99 per step it is the rate the critic values.
4. **Arm `pull_dagger`: one ordered DAgger round before PPO**: `w1_400` flies one
   side of the mission mix against the script, 3 M ordered rows are labelled by the
   script, and the actor is fine-tuned on their movement heads (1 epoch, Adam LR
   1e-4 → 1e-5, label smoothing 0.02); the critic is kept. It is the recipe that
   taught v1 to fire (BC from a script), given here a direct start instead of a
   decaying auxiliary term. ≈ 1.5 min.

Also: both arms start from `w1_400` (not v1), to keep its mission gains; the KL
anchor's log-probs are cached per sample at rollout time instead of being recomputed
in every minibatch and epoch (the loss is the same, tested); there is no widening,
`w1_400` is already 403 wide.

Hypotheses:
- **H1.** The `pull` arm passes O, and M, D, H as run 1's candidates did.
- **H2.** `pull_dagger` follows better than `pull` at every checkpoint up to 150
  (where β is still ≥ 0.05) and loses no more than `pull` in M and D.
- **H0.** The pilot moves toward its teacher but O still fails; see the teacher's
  own numbers in §2 before reading a failure.

## 2. Before training: baselines, and what the teacher scores

The baseline stage re-runs run 1's baselines on this branch's sim, with run 1's
seeds: script vs script and v1 vs v1 missions (scripted commanders: unchanged by
this branch, so these repeat run 1's numbers bit for bit, a check), v1's following
(random commander: **changed**, the holds moved), v1 vs the script in deathmatch.
Reported beside them: run 1's `w1_400` and **the script** on the same following eval.

Measured 2026-10-31 on this branch while sizing the run (`spacefight.eval.orders`,
n = 96 per scenario, seed 400000; the baseline stage repeats them):

| pilot | commander | attack close (median ticks) | attack share | guard within | hold inside | response |
|---|---|---|---|---|---|---|
| v1 | random | 270 (0.56 reached) | 0.399 | 0.163 | 0.258 | 30 |
| script | random | 95 (0.84) | 0.473 | 0.386 | 0.436 | 17 |
| v1 | scripted | 370 (0.70) | 0.455 | 0.203 | 0.002 | 26 |
| script | scripted | 78 (0.85) | 0.525 | 0.684 | 0.138 | 14 |

v1 under the scripted commander is run 1's number exactly (unchanged sim). Under the
random commander v1's hold time rose 0.101 → 0.258 with no training: part of run 1's
hold failure was where the points were.

**The teacher does not pass gate O.** Under the random commander the order-following
script spends 0.386 of a guard instance within 90 m + bound of its ward (the bound is
0.50; it leaves its ward to engage enemies out to 180 m + bound) and its attack
damage share is v1's + 0.074 (the margin is + 0.10). Everything else it passes. So a
pilot that imitated the script perfectly would fail those two checks, and passing
them asks the pilot to guard closer than its teacher (the presence pay, inside 90 m
+ bound, pushes that way; the pull does not). The gates stay run 1's, as decided; a
failure of only those two checks should be read as "the gate asks more than the
teacher does", for the user to judge.

## 3. Setup (run 1's, except as listed)

- **Init**: `pull`: `lab/runs/2026-10-31-order-pilot/w1/checkpoints/ppo_bc_400.pt`
  (actor and fleet critic, 403 wide). `pull_dagger`: the same after the DAgger round
  (its critic unchanged). Fresh optimisers.
- **Reward**: team reward + `1.0 ×` order reward (run 1's winning `w`), with this
  branch's presence pay.
- **Script pull**: β 0.1 (updates 0–30) → 0 (update 300), `beta_rows: ordered`,
  `beta_heads: movement`. Logged: `aux_script_nll` (all rows, all heads, as before),
  `aux_script_nll_pulled` (the loss term), `beta_rows_share` (≈ 0.6 of training
  rows in the slice; `has_order_share` ≈ 0.8).
- **KL anchor**: `0.1 × KL(v1 ‖ π)` on `has_order = 0` rows, as run 1 (cached).
- **Opponents**: run 1's bands `[[0, 0.5, 0.25, 0.25], [200, 0.4, 0.3, 0.3]]`; the
  frozen pool seeds are **v1 and `w1_400`** (`pool_seed_p` 0.5), plus the run's own
  50-update checkpoints.
- **PPO**: actor LR 1e-4 decaying linearly to 0 at update 300, clip 0.1 for 200
  updates then 0.2, entropy 0.005, 4 epochs, minibatch 4096, γ 0.99, λ 0.95;
  **critic warm-up 10 updates** (run 1: 20 from a widened v1 critic; this critic
  already knows the order reward and needs only the new presence pay and holds).
- **Samples**: 256 envs × 128 steps, ≈ 120 k learner rows per update.

## 4. Method

Two arms, run concurrently with the same seed (0), 300 updates each, checkpoints
every 50, each one a candidate:

| arm | before PPO | PPO |
|---|---|---|
| `pull` | – | §3 |
| `pull_dagger` | one ordered DAgger round (§1 item 4, 3 M rows, seed 1) | §3 |

## 5. Gates and pick (fixed 2026-10-31, before any B2b candidate is evaluated)

**Identical to run 1's** (`../2026-10-31-order-pilot/plan.md` §5,
`spacefight/eval/order_gates.py`, unchanged; `gates.py` here applies them), the same
evals and seeds, against the baselines of §2 measured on this branch:

| gate | check | bound |
|---|---|---|
| **O following, random commander** | attack / guard / hold instances | ≥ 30 each |
| | attack: median ticks to gun range (targets 0–250 m outside it) | ≤ 150 |
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

**Amended 2026-10-31 04:55 by the team lead, before any B2b candidate was evaluated.**
Two random-commander bounds are set from the teacher's §2 scores instead of run 1's:
guard time within ≥ **max(0.35, v1's + 0.15)** (the script scores 0.386: it leaves its
ward to fight within 180 m + bound, which a viewer reads as guarding) and attack damage
share ≥ **v1's + 0.05** (the script: + 0.074). A bound the teacher cannot reach would
only measure noise around the teacher. Every other bound is run 1's. Run 1 fails even
the amended bounds (its best guard was 0.23), so its verdict stands. `gates.py` sets
the two constants; the user may restore 0.50 / 0.10.

Before the amendment, with §2's v1, the random-commander bounds came to: attack share ≥ 0.499, guard ≥
0.50, hold ≥ 0.408; scripted: attack share ≥ 0.505, guard ≥ 0.303, hold ≥ 0.102.

**M is also measured against `w1_400`** (`<name>_missions_vs_w1_400.json`, the same
eval with `w1_400` on the other side): reported in `gates.md`, not gated. It answers
"did the pull cost run 1's mission gains?"; the gate stays on v1, the champion.

**Pick** (unchanged from run 1): among the candidates of both arms, updates 50–300,
that pass every gate, the highest mean mission win vs v1; ties by the deathmatch win
vs v1. If none passes, nothing is promoted, the live page keeps v1, and `results.md`
names the failed checks and, per candidate, its following beside v1's, `w1_400`'s
and the script's (`gates.md` prints that table).

## 6. Budget (measured on this laptop, 16 threads, no GPU)

Measured 2026-10-31 at 04:25–04:36 on this branch, the machine otherwise quiet, kept
to 8 threads (another job was not to be disturbed), so the PPO number below is a
*ratio* applied to run 1's measured two-arm time, not a two-arm measurement.

Timing slice: one arm, the run's exact config and sizes (256 envs × 128 steps, from
`w1_400`, actor training from update 0, no warm-up), 4 sim + 4 torch threads, 7
updates, updates 2–7 averaged; the same with run 1's settings (β 0, the anchor
recomputed per minibatch) for the ratio:

| variant (one arm, 4 + 4 threads) | s/update | rollout | PPO | samples |
|---|---|---|---|---|
| run 1's settings | 13.4 | 2.8 | 10.2 | 113 k |
| **B2b** (pull on ordered rows, anchor cached) | **10.9** | 2.6 | 8.0 | 114 k |

The anchor cache saves ≈ 20 % of the PPO step (the pull costs nothing extra: the
labels' log-probs come from the same forward pass). Run 1 ran two arms at 6 + 6
threads each at 22–24 s/update; × 0.81 gives **≈ 19 s/update for B2b's two arms**.

| stage | measured | estimate |
|---|---|---|
| ordered DAgger round (`pull_dagger` only, before its PPO) | 3 M rows: 83 s at 8 threads (collect ≈ 60 s, 1 epoch ≈ 20 s), 3.8 GB | ≈ 1.5 min (12 threads, beside the other arm's PPO) |
| **PPO, two arms at once** | ≈ 19 s/update (above) | 300 updates ≈ **1.6 h**; samples per update grew in run 1, allow **2 h** |
| baseline | run 1's ≈ 7 min; plus `w1_400`'s following ≈ 1 min and the script's 18 s (8 threads) | **≈ 9 min** |
| gate evals per candidate (12 threads) | run 1's ≈ 6.5 min (following 57 s, missions vs v1 203 s, deathmatch ≈ 2 min) + missions vs `w1_400` ≈ 3.4 min | **≈ 10 min**; 12 candidates ≈ **2 h**, the 6 hundreds ≈ 1 h |
| secondary (blanked following, passing candidates only) | ≈ 1 min each | ≤ 12 min |
| **total** | | **≈ 4–4.5 h**: fits a 6 h night |

`EVAL_UPDATES` runs the hundreds first ("100 200 300 50 150 250"), so a short night
can already pick among them; the rest is resumable (`run.sh eval gates secondary`).
Above 28 s/update (a loaded machine, 1.5 × the estimate) set `N_UPDATES=200`.
Memory: two arms ≈ 3 GB each plus the DAgger round's 3.8 GB at the start, inside
29 GB.

What the slice showed (not an eval): the pull moves the policy much more per update
than run 1's PPO did (`approx_kl` 0.028 against 0.005; the movement-head NLL to the
script stays ≈ 5.6 over the 6 updates while `kl_anchor` on unordered rows rises
0.04 → 0.12 against 0.035), `beta_rows_share` 0.64 of training rows
(`has_order_share` 0.80: the rest are advisory deathmatch orders), explained
variance 0.94. Watch `approx_kl` and `kl_anchor` in the first 30 updates after the
warm-up (§7).

## 7. Risks

| risk | signal | response |
|---|---|---|
| the pull makes the pilot fly like the script and lose mission strength | M vs `w1_400` falls well below ½; `vs_scripted_win` drops in the log | β is gone by 300; pick an earlier/later checkpoint; a rerun with β 0.03 |
| the DAgger round overwrites too much (fire, aim drift through the shared trunk) | `pull_dagger` M or D below `pull` from update 50 | the arm comparison is the answer; next time fewer rows or a lower LR |
| presence farming (parking on holds and guards) | engine duty under hold/guard ≪ under none (gates.md), time-limit or stalemate rates up (H) | presence is capped per instance; the scripted deathmatch commander gives attack orders only, so deathmatches cannot farm it |
| guard within stays under 0.50 (the teacher's 0.386) | O fails on guard only | reported as such (§2); the user decides on the bound |
| the critic mis-values the tripled presence pay | explained variance < 0.5 after warm-up | longer warm-up in a rerun |
| the pull dominates the early updates | `approx_kl` > 0.05 or `kl_anchor` > 0.5 after the warm-up | a rerun with β 0.03; the slice saw 0.028 and 0.12 (§6) |
| self-play destabilises | `vs_scripted_win` falls after update 200 | scripts stay ≥ 40 %; an earlier checkpoint |
| throughput below the plan | > 28 s/update (1.5 × §6) | stop at 200 (`N_UPDATES=200`), evaluate the hundreds |

## 8. Running it

From the repo root of the main checkout, after this branch is merged and the
extension is rebuilt from it (`uv run maturin develop -m crates/sim-py/Cargo.toml
--release`: the hold points and presence pay live in the sim; `run.sh` refuses a
`spacefight` without `scripted_order_rows`, but cannot see an old `rlf_sim` because
`SIM_VERSION` did not change, so rebuild). Needs run 1's `w1_400` at
`lab/runs/2026-10-31-order-pilot/w1/checkpoints/ppo_bc_400.pt` (or `W1=path`) and
fleet pilot v1 (fetched by `tools.champion`, or `V1=path`):

```
SMOKE=1 lab/runs/2026-10-31-order-pilot-b2b/run.sh      # every stage at tiny sizes, smoke/ (gitignored)
nohup lab/runs/2026-10-31-order-pilot-b2b/run.sh > lab/runs/2026-10-31-order-pilot-b2b/run.out 2>&1 &
```

Stages `baseline ppo eval gates secondary`, each skipping finished work (the DAgger
round once its checkpoint exists; PPO resumes from the latest checkpoint; SIGTERM
checkpoints after the current update). `run.sh eval gates` re-runs only those. Logs:
`run.out`, `pull.out`, `pull_dagger.out` (the DAgger round's summary is its first
line), `<arm>/log.jsonl`, `pull_dagger/dagger/dagger_ordered.json`. Afterwards write
`results.md` from `eval/gates.md`, and promote the pick only if it passes.
