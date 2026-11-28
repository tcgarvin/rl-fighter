# <!-- hand:title -->Cloned, corrected, then trained: a learned pilot beats the script in 512 of 512 duels<!-- /hand:title -->

Date 2026-10-28 · run dir `2026-10-28-learnability-spike` · branch `spike/learnability` · commit `272e7e1` (report) · SIM_VERSION 2 · verdict: **PASS**

Training: `ppo_bc` 1200/1200, `ppo_scratch` 1200/1200. Evals present: 24 of 23 matrix pairings.

(That line is written by the report tool: the run holds 24 test results for the 23 test pairings in the eval matrix below, the extra one being a separate test of update 500.)

<!-- summary: The project's first training run asked whether a small neural network can learn to fly a fighter by driving its thrusters and trigger directly, with no autopilot, in one night on a laptop. It can. Copying our hand-written pilot gave a network that lost almost every duel, a correction step helped a little, and trial-and-error training from that start then beat the hand-written pilot in all 512 test duels. Trial and error from nothing, on the same budget, never learned to shoot. -->

## What we asked

<!-- hand:asked -->Can a small neural network learn to fly a fighter by driving its thrusters and trigger directly, with no autopilot, in one night on a laptop CPU? We tested three routes: copy a hand-written pilot, copy it and then train by trial and error, or train by trial and error from nothing.

"No autopilot" means the network sets each thruster, the trigger and the ship's power split itself, many times a second. Nothing steers for it, so chasing, aiming and dodging all have to be learned. The hand-written pilot is the script: a pilot written as rules, which is also the opponent every learned pilot is measured against.

The answer is yes, by the second route. The copy alone won 0.6 % of its duels against the script, and 15 % after a correction step. Trial-and-error training from that copy won 0.994 of its duels against the script after about 400 updates (roughly 35 minutes), and all 512 duels of the final test at the end. Trial and error from nothing, on the same budget, never learned to shoot.<!-- /hand:asked -->

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network. The game runs in a simulation, a program that plays thousands of matches at once, far faster than real time, so a network can practise. This was the project's first training run, and it tested what the design called the project's biggest risk: whether a network can learn to fly at this low level at all, on a laptop's processor, in a night.

The run had been waiting on [the version 2 rules](../2026-10-28-sim-v2/results.md), finished the same day. They made duels last about 43 seconds, with three or four attacking runs (passes) each, instead of ending on the first head-on meeting. Those rules also changed the script so that after each pass it extends, flying straight out of gun range before it turns back, instead of staying in a brawl after the merge (the moment the two ships meet and cross). That made it a better pilot to copy.

<div data-figure="diagram" data-name="pilot" data-caption="This first run trained the network on the fighter alone, in duels against the script. Orders, the bomber and one network for every hull all came later."></div>

## What we did

The run had three stages, and the rest of the entry uses their short names.

- **Behaviour cloning (BC).** The network is trained to copy the script. We recorded 2 million moments of script-against-script duels and trained the network to pick the script's action in each. A little random noise was added to the script's actions while recording (the DART method), so the recording also shows the script recovering from small mistakes.
- **DAgger.** A correction step. The copy flies, the script says what it would have done in the situations the copy actually gets into, and the copy is trained on those answers too. We ran three rounds.
- **PPO, trial-and-error training.** The pilot plays many duels, earns points (reward) for damage dealt and for a win, loses points for damage taken and a little for each shot fired (holding the trigger while the gun recharges between shots costs nothing), and is adjusted to do more of what earned points. One round of play and adjustment is an update. Two PPO runs went side by side: `ppo_bc` started from the corrected copy, `ppo_scratch` from random weights. `ppo_bc` also had a script pull, an extra training term that pulls the pilot's choices toward the script's, faded from full strength at update 30 to nothing at update 420.

<div data-figure="diagram" data-name="training-methods" data-caption="The main arm here used all three steps in order: copying, three rounds of correction, then trial and error. Its script pull acted on every moment and faded from full strength at update 30 to nothing at update 420. The other arm used trial and error alone, from random weights."></div>

The list below is the run's exact settings, written out from its configuration, followed by the ways the run departed from its plan. It is the record, and a reader can skip to Results. Terms that matter later: "held-out agreement" is how often the copy chose what the script chose, on recorded moments it had not trained on; "256 × 128" is 256 duels played at once for 128 ticks (a tick is 1/30 of a second) per update; β is the strength of the script pull; the critic is a second network, used only in training, that predicts how well things will go, and "warm-up" means it trained alone first; opponent bands give, from a starting update, the shares of duels against the script, against a copy of the pilot itself, and against frozen earlier versions of it.

- **Balance (pre-gate, plan §2):** gauss (the fighter's gun) 5 dmg / 0.20 s / 220 m / 200 m/s / 1.0°, fighter 80 hp, plus the scripted pilot extending after a merge; every tried tuple and the before/after sweep is in `lab/runs/2026-10-28-sim-v2/results.md`.
- **BC:** 2,000,000 DART rows (p = 0.15); held-out agreement throttle 0.958, fire 0.968, power 0.722; fire precision 0.853 / recall 0.682.
- **DAgger:** 3 rounds × 2,000,000 on-policy rows labelled by the script; sampled win rate vs the script per round: r0 0.006; r1 0.029; r2 0.080; r3 0.154; best round 3 → `bc_dagger/best.pt` (PPO-BC's init).
- **ppo_bc:** init `lab/runs/2026-10-28-learnability-spike/bc_dagger/best.pt`, 1200 updates of 256 × 128, actor LR 0.0001, β 0.1 → 0.0 over 30–420, critic warm-up 30, opponent bands `[[0, 1, 0, 0], [360, 0.5, 0.3, 0.2], [720, 0.3, 0.4, 0.3]]`.
- **ppo_scratch:** init `scratch`, 1200 updates of 256 × 128, actor LR 0.0003, β 0.0 → 0.0 over 30–700, critic warm-up 0, opponent bands `[[0, 1, 0, 0], [360, 0.5, 0.3, 0.2], [720, 0.3, 0.4, 0.3]]`.

### Deviations from plan

Where the run differed from [the plan](plan.md), and why.

- **Ran interactively in the evening**, not on the 03:00 night schedule of §5.
- **DAgger added** between BC and PPO (not in the plan): BC alone won 0.6 % vs the
  script (compounding error off the expert's state distribution), so three DAgger
  rounds of 2 M on-policy rows each were run on top of `bc/bc.pt`; round 3 (sampled
  win 0.154) is `bc_dagger/best.pt` and the PPO-BC init. The verdict's "BC" stage is
  BC + DAgger; plain BC is still reported.
- **1200 PPO updates instead of 2000** for both runs, per the §7 throughput row:
  thermal throttling, ~2.8 s/update measured with one run alone. The comparison
  stays at equal updates.
- **Opponent bands scaled × 0.6** to the shorter run:
  `[[0,1,0,0],[360,0.5,0.3,0.2],[720,0.3,0.4,0.3]]`.
- **β decay end 420** (700 × 0.6) for PPO-BC.
- **Engine-duty band top 0.95** instead of 0.9 (the script runs at 0.85; changed
  before any learned policy was evaluated, §1).
- **Thread split:** both PPO runs concurrently at 6 sim + 6 torch threads.
- **Matrix adapted (§6.2):** PPO-BC at 400 / 800 instead of 500 / 1000 / 1500;
  PPO-BC final also plays BC + DAgger (its init) instead of BC; the best checkpoint
  is the 100-update checkpoint with the highest rollout `vs_scripted_win`
  (episode-weighted over the 50 updates up to it).

## Results

### Verdict

Before the run, [the plan](plan.md) (§1) set pass marks for each stage (the table at the end of the next section: the "BC" column holds the marks for the copy, "pass" and "strong" those for the trained pilot) and three hypotheses. **H1**: copying alone already gives a pilot that flies and fights, and PPO from that start beats the script. **H2**: PPO from scratch, on the same budget, does not get as strong. **H0**, the null: nothing beats the script, because driving the thrusters directly is too hard for a small network on this budget. Below, "PPO-BC" is the `ppo_bc` run and "PPO-scratch" the `ppo_scratch` run; "final" is the network after update 1200, "400" and "800" are checkpoints (saved copies) from those updates, and "best" is the checkpoint with the highest win rate in its own training matches.

**PASS**. BC + DAgger misses the BC column on win; PPO-BC final reaches every pass cell.

- **H1** does not hold as stated, because only its second half came true: BC + DAgger misses the BC column (win 0.154), so copying alone did not give a pilot that fights; PPO-BC final beats the script (win 1.000).
- **H2** holds: BC + PPO leads scratch by +0.976 win rate vs the script at equal updates (rule: ≥ 0.15).
- **H0** is rejected (the null hypothesis, that nothing beats the script, turned out false): best learned policy vs the script is PPO-BC final at 1.000 (sampled).

PPO-BC best checkpoint: update 500 (rollout win vs the script 1.000, 50-update smoothed).

### §1 criteria (sampled actions, n = 512 vs the script, sides swapped)

Each row is one pilot playing 512 duels against the script, on each side half the time. The columns are the plan's measures. Win rate counts a draw as half, and 0.5 is an even fight. Engagement is the share of time the enemy is within 1.2 times gun range. Hit rate is hits per shot. Outside arena is the share of time spent outside the arena. Kill endings is the share of duels that end in a kill rather than at the time limit. Engine duty is the main engine's average thrust level, from 0 (off) to 1 (full); its marks (0.2–0.95) rule out a pilot that idles or one that holds the throttle flat out all the time. "Sampled" means the pilot picks each action at random, in proportion to how much it favours it, as it does in training. The marks each column is checked against are in the third table, where "0.5 × script" means at least half the script's own value. Together the engagement, hit rate, outside-arena and kill rows check that a pilot flies on purpose, rather than winning by sitting still or circling the edge.

✓/✗ against the policy's column (BC for BC and BC + DAgger, pass for the PPO policies); 'strong' = every strong cell met; '—' = not evaluated yet.

| policy | column | win rate | draw rate | engagement | hit rate | outside arena | kill endings | engine duty | strong |
|---|---|---|---|---|---|---|---|---|---|
| script (baseline) | — | 0.511 | 0.029 | 0.858 | 0.597 | 0.0000 | 0.998 | 0.850 | — |
| BC | BC | 0.006 ✗ | 0.000 ✓ | 0.927 ✓ | 0.299 ✓ | 0.0021 ✓ | 1.000 ✓ | 0.831 | — |
| BC + DAgger | BC | 0.154 ✗ | 0.004 ✓ | 0.877 ✓ | 0.387 ✓ | 0.0014 ✓ | 0.998 ✓ | 0.847 | — |
| PPO-BC final | pass | 1.000 ✓ | 0.000 ✓ | 0.839 ✓ | 0.668 ✓ | 0.0000 ✓ | 1.000 ✓ | 0.922 ✓ | yes |
| PPO-BC best | pass | 1.000 ✓ | 0.000 ✓ | 0.897 ✓ | 0.618 ✓ | 0.0000 ✓ | 1.000 ✓ | 0.874 ✓ | yes |
| PPO-BC 400 | pass | 0.994 ✓ | 0.000 ✓ | 0.906 ✓ | 0.621 ✓ | 0.0001 ✓ | 1.000 ✓ | 0.841 ✓ | yes |
| PPO-BC 800 | pass | 1.000 ✓ | 0.000 ✓ | 0.848 ✓ | 0.668 ✓ | 0.0000 ✓ | 1.000 ✓ | 0.898 ✓ | yes |
| PPO-scratch final | pass | 0.024 ✗ | 0.049 ✓ | 0.980 ✓ | 0.000 ✗ | 0.0000 ✓ | 0.000 ✗ | 0.984 ✗ | no |

Argmax rows (second row per §6.1, not used for the verdict). Here the pilot always takes its single favourite action instead of sampling:

| policy | column | win rate | draw rate | engagement | hit rate | outside arena | kill endings | engine duty | strong |
|---|---|---|---|---|---|---|---|---|---|
| BC (argmax) | BC | 0.005 ✗ | 0.002 ✓ | 0.654 ✓ | 0.422 ✓ | 0.2812 ✗ | 0.963 ✓ | 0.907 | — |
| BC + DAgger (argmax) | BC | 0.065 ✗ | 0.002 ✓ | 0.876 ✓ | 0.604 ✓ | 0.0003 ✓ | 1.000 ✓ | 0.839 | — |
| PPO-BC final (argmax) | pass | 1.000 ✓ | 0.000 ✓ | 0.828 ✓ | 0.723 ✓ | 0.0000 ✓ | 1.000 ✓ | 0.922 ✓ | yes |
| PPO-BC best (argmax) | pass | 1.000 ✓ | 0.000 ✓ | 0.896 ✓ | 0.707 ✓ | 0.0000 ✓ | 1.000 ✓ | 0.895 ✓ | yes |
| PPO-BC 400 (argmax) | pass | 0.996 ✓ | 0.000 ✓ | 0.904 ✓ | 0.733 ✓ | 0.0000 ✓ | 1.000 ✓ | 0.838 ✓ | yes |
| PPO-BC 800 (argmax) | pass | 1.000 ✓ | 0.000 ✓ | 0.843 ✓ | 0.710 ✓ | 0.0000 ✓ | 1.000 ✓ | 0.911 ✓ | yes |
| PPO-scratch final (argmax) | pass | 0.006 ✗ | 0.012 ✓ | 0.980 ✓ | 0.000 ✗ | 0.0006 ✓ | 0.035 ✗ | 0.982 ✗ | no |

| column | win rate | draw rate | engagement | hit rate | outside arena | kill endings | engine duty |
|---|---|---|---|---|---|---|---|
| BC | ≥ 0.35 | ≤ 0.15 | ≥ 0.5 × script | ≥ 0.5 × script | ≤ 0.02 | ≥ 0.8 | report |
| pass | ≥ 0.6 | ≤ 0.1 | ≥ 0.4 | ≥ 0.6 × script | ≤ 0.02 | ≥ 0.9 | 0.2–0.95 |
| strong | ≥ 0.75 | ≤ 0.1 | ≥ 0.5 | ≥ 1 × script | ≤ 0.01 | ≥ 0.95 | 0.2–0.95 |

### Eval matrix

Every test pairing. Each row is 512 duels of pilot a against pilot b, with a's numbers: win, draw and loss shares; duel length in ticks (30 a second), the median with the 10th to 90th percentile range; the share ending in a kill; passes, shots, hits and damage dealt per duel; and, as above, hit rate, engagement, outside arena and engine duty. Fire is the share of decisions with the trigger held, speed is in m/s, and nan/stuck counts broken or stuck ships (a health check).

Side a's numbers; '(argmax)' rows have both sides take the argmax.

| a | b | n | win | draw | loss | length med (p10–p90) | kill | passes | shots | hits | hit rate | dmg | engage | outside | engine | fire | speed | nan/stuck |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| script | script | 512 | 0.511 | 0.029 | 0.475 | 1312 (1054–1673) | 0.998 | 2.93 | 45.7 | 27.3 | 0.597 | 75.2 | 0.858 | 0.0000 | 0.850 | 0.085 | 39.1 | 0 |
| BC | script | 512 | 0.006 | 0.000 | 0.994 | 1254 (1011–1536) | 1.000 | 1.74 | 51.9 | 15.5 | 0.299 | 44.7 | 0.927 | 0.0021 | 0.831 | 0.088 | 42.5 | 0 |
| BC (argmax) | script | 512 | 0.005 | 0.002 | 0.994 | 1130 (343–1784) | 0.963 | 1.08 | 15.5 | 6.6 | 0.422 | 17.8 | 0.654 | 0.2812 | 0.907 | 0.041 | 48.9 | 0 |
| BC + DAgger | script | 512 | 0.154 | 0.004 | 0.844 | 1414 (1138–1763) | 0.998 | 2.73 | 56.3 | 21.8 | 0.387 | 62.4 | 0.877 | 0.0014 | 0.847 | 0.075 | 44.7 | 0 |
| BC + DAgger (argmax) | script | 512 | 0.065 | 0.002 | 0.934 | 1281 (1031–1553) | 1.000 | 2.45 | 35.1 | 21.2 | 0.604 | 57.9 | 0.876 | 0.0003 | 0.839 | 0.065 | 40.9 | 0 |
| PPO-BC final | script | 512 | 1.000 | 0.000 | 0.000 | 365 (306–437) | 1.000 | 1.00 | 42.0 | 28.0 | 0.668 | 80.4 | 0.839 | 0.0000 | 0.922 | 0.762 | 36.0 | 0 |
| PPO-BC final (argmax) | script | 512 | 1.000 | 0.000 | 0.000 | 347 (292–409) | 1.000 | 1.00 | 39.3 | 28.4 | 0.723 | 80.3 | 0.828 | 0.0000 | 0.922 | 0.777 | 36.4 | 0 |
| PPO-BC best | script | 512 | 1.000 | 0.000 | 0.000 | 559 (459–666) | 1.000 | 1.03 | 44.9 | 27.8 | 0.618 | 80.5 | 0.897 | 0.0000 | 0.874 | 0.256 | 34.9 | 0 |
| PPO-BC best (argmax) | script | 512 | 1.000 | 0.000 | 0.000 | 561 (474–646) | 1.000 | 1.03 | 40.3 | 28.5 | 0.707 | 80.5 | 0.896 | 0.0000 | 0.895 | 0.225 | 34.9 | 0 |
| PPO-BC 400 | script | 512 | 0.994 | 0.000 | 0.006 | 796 (681–981) | 1.000 | 1.35 | 45.8 | 28.4 | 0.621 | 80.5 | 0.906 | 0.0001 | 0.841 | 0.140 | 36.8 | 0 |
| PPO-BC 400 (argmax) | script | 512 | 0.996 | 0.000 | 0.004 | 790 (666–968) | 1.000 | 1.36 | 39.6 | 29.1 | 0.733 | 80.4 | 0.904 | 0.0000 | 0.838 | 0.125 | 35.7 | 0 |
| PPO-BC 800 | script | 512 | 1.000 | 0.000 | 0.000 | 377 (318–475) | 1.000 | 1.00 | 41.9 | 28.0 | 0.668 | 80.4 | 0.848 | 0.0000 | 0.898 | 0.611 | 35.0 | 0 |
| PPO-BC 800 (argmax) | script | 512 | 1.000 | 0.000 | 0.000 | 362 (310–466) | 1.000 | 1.00 | 40.2 | 28.5 | 0.710 | 80.4 | 0.843 | 0.0000 | 0.911 | 0.631 | 34.9 | 0 |
| PPO-scratch final | script | 512 | 0.024 | 0.049 | 0.951 | 2700 (2700–2700) | 0.000 | 1.05 | 0.1 | 0.0 | 0.000 | 0.0 | 0.980 | 0.0000 | 0.984 | 0.000 | 63.0 | 0 |
| PPO-scratch final (argmax) | script | 512 | 0.006 | 0.012 | 0.988 | 2700 (2700–2700) | 0.035 | 1.12 | 0.0 | 0.0 | 0.000 | 0.0 | 0.980 | 0.0006 | 0.982 | 0.000 | 64.6 | 0 |
| PPO-BC final | BC + DAgger | 512 | 1.000 | 0.000 | 0.000 | 398 (332–486) | 1.000 | 1.00 | 45.7 | 28.0 | 0.612 | 80.3 | 0.854 | 0.0000 | 0.918 | 0.725 | 36.8 | 0 |
| PPO-BC final (argmax) | BC + DAgger | 512 | 1.000 | 0.000 | 0.000 | 360 (311–423) | 1.000 | 1.00 | 41.0 | 27.7 | 0.677 | 80.4 | 0.837 | 0.0000 | 0.924 | 0.769 | 37.8 | 0 |
| PPO-BC final | PPO-BC 400 | 512 | 1.000 | 0.000 | 0.000 | 366 (306–429) | 1.000 | 1.00 | 41.2 | 28.4 | 0.689 | 80.5 | 0.834 | 0.0000 | 0.908 | 0.751 | 36.1 | 0 |
| PPO-BC final (argmax) | PPO-BC 400 | 512 | 1.000 | 0.000 | 0.000 | 332 (294–376) | 1.000 | 1.00 | 37.3 | 28.3 | 0.761 | 80.4 | 0.819 | 0.0000 | 0.916 | 0.776 | 37.4 | 0 |
| PPO-BC final | PPO-BC 800 | 512 | 0.806 | 0.014 | 0.188 | 316 (282–388) | 1.000 | 1.00 | 35.8 | 27.2 | 0.761 | 79.0 | 0.804 | 0.0000 | 0.890 | 0.744 | 35.8 | 0 |
| PPO-BC final (argmax) | PPO-BC 800 | 512 | 0.817 | 0.010 | 0.178 | 325 (269–385) | 1.000 | 1.00 | 35.0 | 27.2 | 0.776 | 79.2 | 0.805 | 0.0000 | 0.880 | 0.759 | 35.0 | 0 |
| PPO-scratch final | PPO-BC final | 512 | 0.000 | 0.000 | 1.000 | 465 (376–565) | 1.000 | 1.02 | 0.0 | 0.0 | 0.000 | 0.0 | 0.872 | 0.0000 | 0.935 | 0.000 | 65.2 | 0 |
| PPO-scratch final (argmax) | PPO-BC final | 512 | 0.000 | 0.000 | 1.000 | 576 (466–706) | 1.000 | 1.03 | 0.0 | 0.0 | 0.000 | 0.0 | 0.899 | 0.0000 | 0.953 | 0.000 | 66.6 | 0 |

No NaNs or stuck ships in any eval.

### Learning curves

How the two PPO runs progressed. "Samples" is the number of pilot decisions trained on so far, and "win vs script (50-upd)" the win rate in the training duels against the script, averaged over the last 50 updates. The H columns are entropy: how much randomness the pilot keeps in a choice, where 0 means it always makes the same one. They are given for the throttle outputs, the fire output, the power output (how the ship splits its power between shields, engines and weapons) and the mean over all outputs.

matplotlib is not installed in the venv, so no PNGs: the per-update curves (rollout win vs the script, raw and 50-update smoothed, and entropy per head group, both runs) are in `learning_curves.csv`. Every 100 updates:

| update | run | samples | win vs script (50-upd) | H throttle | H fire | H power | H mean |
|---|---|---|---|---|---|---|---|
| 100 | ppo_bc | 3,132,389 | 0.431 | 0.159 | 0.113 | 0.649 | 0.222 |
| 200 | ppo_bc | 6,260,695 | 0.654 | 0.147 | 0.113 | 0.520 | 0.195 |
| 300 | ppo_bc | 9,370,060 | 0.916 | 0.149 | 0.125 | 0.418 | 0.184 |
| 400 | ppo_bc | 12,781,295 | 0.993 | 0.173 | 0.154 | 0.427 | 0.207 |
| 500 | ppo_bc | 16,668,139 | 1.000 | 0.237 | 0.262 | 0.533 | 0.283 |
| 600 | ppo_bc | 20,444,278 | 1.000 | 0.342 | 0.323 | 0.492 | 0.361 |
| 700 | ppo_bc | 24,124,862 | 1.000 | 0.360 | 0.320 | 0.441 | 0.366 |
| 800 | ppo_bc | 27,960,611 | 1.000 | 0.349 | 0.275 | 0.428 | 0.350 |
| 900 | ppo_bc | 31,809,512 | 1.000 | 0.360 | 0.233 | 0.366 | 0.342 |
| 1000 | ppo_bc | 35,636,386 | 1.000 | 0.365 | 0.211 | 0.310 | 0.335 |
| 1100 | ppo_bc | 39,423,068 | 1.000 | 0.368 | 0.195 | 0.325 | 0.337 |
| 1200 | ppo_bc | 43,201,008 | 1.000 | 0.364 | 0.187 | 0.361 | 0.339 |
| 100 | ppo_scratch | 3,157,096 | 0.024 | 0.980 | 0.642 | 1.850 | 1.056 |
| 200 | ppo_scratch | 6,361,798 | 0.071 | 0.893 | 0.491 | 1.785 | 0.963 |
| 300 | ppo_scratch | 9,568,438 | 0.062 | 0.828 | 0.095 | 1.679 | 0.845 |
| 400 | ppo_scratch | 13,127,765 | 0.040 | 0.746 | 0.091 | 1.544 | 0.766 |
| 500 | ppo_scratch | 17,296,619 | 0.003 | 0.739 | 0.014 | 1.572 | 0.754 |
| 600 | ppo_scratch | 21,465,284 | 0.000 | 0.719 | 0.007 | 1.501 | 0.729 |
| 700 | ppo_scratch | 25,636,651 | 0.000 | 0.749 | 0.002 | 1.456 | 0.744 |
| 800 | ppo_scratch | 30,027,964 | 0.000 | 0.705 | 0.004 | 1.469 | 0.714 |
| 900 | ppo_scratch | 34,510,487 | 0.000 | 0.662 | 0.002 | 1.452 | 0.681 |
| 1000 | ppo_scratch | 38,992,553 | 0.000 | 0.648 | 0.000 | 1.481 | 0.674 |
| 1100 | ppo_scratch | 43,477,897 | 0.000 | 0.610 | 0.001 | 1.409 | 0.637 |
| 1200 | ppo_scratch | 47,962,307 | 0.000 | 0.661 | 0.000 | 1.339 | 0.663 |

## What it looked like

<!-- hand:looked-like -->Read from a trajectory trace of six champion-vs-script matches (the champion is the final PPO-BC pilot) (seed 777; distance, nose angle to the enemy, HP and speed every second), not from the summary metrics:

- **It aims on the way in.** From 450 m down to about 100 m the learned pilot keeps its nose within 1–2° of the enemy, while the script's nose swings 10–27° off as it closes. The learned pilot is already 10–20 hp up before the ships meet.
- **It approaches slower.** It holds about 50 m/s on the approach, where the script runs up to 60–70, so it arrives in a steady firing position.
- **There is no second pass, but a brawl.** After the merge both ships slow to 15–30 m/s and fight a close turning fight at 10–70 m. The script keeps trying to extend (short bursts to 60–70 m/s). The learned pilot stays on it at low speed with its nose usually 5–15° off, while the script's is often 20–90° off. That is why the eval counts one "pass" per match: the ships never leave gun range again.
- **No edge behaviour seen.** Every traced fight stayed near the centre; outside-arena share is 0 in the eval too.<!-- /hand:looked-like -->

<!-- figure-idea: overhead tracks of one champion-vs-script duel: the learned pilot's steady approach with its nose on the enemy against the script's swinging nose, then the close turning brawl after the merge. It would show why the eval counts one pass per duel. -->

## What we learned

<!-- hand:learned -->- **H0 rejected, H2 holds by a mile.** BC + DAgger + PPO beat the script in 512 of 512 duels (sampled and argmax), with a hit rate of 0.67 against the script's 0.60. PPO from scratch on the same budget never learned to shoot (win 0.02, 0 hits).
- **H1 only half held** (so, as stated, it does not hold). Cloning alone did not give a fighter. It matched the script's choices 96 % of the time on the script's own states, yet won 0.6 % of duels. Compounding error was the cause (small mistakes take the copy into situations the script never flew into, where it has nothing to copy, so the mistakes pile up): on its own states it agreed only 78 % of the time, and its argmax play (always its favourite action) left the arena 28 % of the time. Three DAgger rounds (label the clone's own states with the script) fixed the drift and raised the win rate to 15 %. PPO did the rest in about 400 updates (13 M samples, roughly 35 minutes).
- **Scratch PPO found "never fire".** Each shot fired costs a little and random aim never hits, so the fire head (the network's trigger output) collapsed to 0 (entropy 0.66 → 0.00 by update 1000). As planned, we report this rather than rescue it. It is a reward-design finding as much as a learnability one.
- **Strong, but short.** The champion kills in a median 12 s (the script mirror takes 44 s), in one approach and one brawl. It holds the trigger on 76 % of decisions, which costs nothing while the gun is cycling (recharging between shots). Every watchability cell (the checks that it flies on purpose) passes, but the duel no longer has the multi-pass rhythm [the balance sweep](../2026-10-28-sim-v2/results.md) tuned for. Watch this as opponents get stronger.
- **Throughput ran at a quarter of the plan.** The CPU throttles under sustained load (about 2 GHz), and two concurrent runs got about 6.7 k samples/s each, not 30 k. The night budget should assume this.<!-- /hand:learned -->

## Next

<!-- hand:next -->**Next experiment:** run the same recipe (BC → DAgger → PPO with a decaying script pull) on the strafer and the gunship, the other two ship types (hulls), whose turret slew heads (the outputs that turn a turret) this spike never exercised. Then move it onto the M3 attention policy (a different network design, planned at the time for the third milestone), so that one network flies all three hulls. The question is whether the recipe transfers to other hulls, or whether the fighter's result depended on its simple controls.

Backlog added:
- Make DAgger a standard step of the BC pipeline (it is cheap: about 5 minutes a round).
- Add a duel-length / passes watchability signal to the eval gates, so one-pass brawls are visible at promotion time (when a pilot is chosen to fly on the site).
- Revisit the fire cost for from-scratch learning (for example no cost while the gun is cycling, or a short warm-up without it).
- Budget nightly runs at the measured throttled throughput.
- The live page now shows this champion (update 1200) at `/duel/`.<!-- /hand:next -->

## Numbers

Computing used, for the record.

- `ppo_bc`: 1200 / 1200 updates, 43,201,008 learner samples, 1.78 h of update time (5.34 s/update, 6,738 samples/s), threads 6 sim + 6 torch.
- `ppo_scratch`: 1200 / 1200 updates, 47,962,307 learner samples, 1.97 h of update time (5.90 s/update, 6,778 samples/s), threads 6 sim + 6 torch.
