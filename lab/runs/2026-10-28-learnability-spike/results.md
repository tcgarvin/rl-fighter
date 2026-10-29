# <!-- hand:title -->Cloned, corrected, then trained: a learned pilot beats the script in 512 of 512 duels<!-- /hand:title -->

Date 2026-10-28 · run dir `2026-10-28-learnability-spike` · branch `spike/learnability` · commit `272e7e1` (report) · SIM_VERSION 2 · verdict: **PASS**

Training: `ppo_bc` 1200/1200, `ppo_scratch` 1200/1200. Evals present: 24 of 23 matrix pairings.

## What we asked

<!-- hand:asked -->Can a small neural network learn to fly a fighter by driving its thrusters and trigger directly, with no autopilot, in one night on a laptop CPU? We tested three routes: copy a hand-written pilot, copy it and then train by trial and error, or train by trial and error from nothing.<!-- /hand:asked -->

## What we did

- **Balance (pre-gate, plan §2):** gauss 5 dmg / 0.20 s / 220 m / 200 m/s / 1.0°, fighter 80 hp, plus the scripted pilot extending after a merge; every tried tuple and the before/after sweep is in `lab/runs/2026-10-28-sim-v2/results.md`.
- **BC:** 2,000,000 DART rows (p = 0.15); held-out agreement throttle 0.958, fire 0.968, power 0.722; fire precision 0.853 / recall 0.682.
- **DAgger:** 3 rounds × 2,000,000 on-policy rows labelled by the script; sampled win rate vs the script per round: r0 0.006; r1 0.029; r2 0.080; r3 0.154; best round 3 → `bc_dagger/best.pt` (PPO-BC's init).
- **ppo_bc:** init `lab/runs/2026-10-28-learnability-spike/bc_dagger/best.pt`, 1200 updates of 256 × 128, actor LR 0.0001, β 0.1 → 0.0 over 30–420, critic warm-up 30, opponent bands `[[0, 1, 0, 0], [360, 0.5, 0.3, 0.2], [720, 0.3, 0.4, 0.3]]`.
- **ppo_scratch:** init `scratch`, 1200 updates of 256 × 128, actor LR 0.0003, β 0.0 → 0.0 over 30–700, critic warm-up 0, opponent bands `[[0, 1, 0, 0], [360, 0.5, 0.3, 0.2], [720, 0.3, 0.4, 0.3]]`.

### Deviations from plan

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

**PASS**. BC + DAgger misses the BC column on win; PPO-BC final reaches every pass cell.

- **H1** does not hold: BC + DAgger misses the BC column (win 0.154); PPO-BC final beats the script (win 1.000).
- **H2** holds: BC + PPO leads scratch by +0.976 win rate vs the script at equal updates (rule: ≥ 0.15).
- **H0** is rejected: best learned policy vs the script is PPO-BC final at 1.000 (sampled).

PPO-BC best checkpoint so far: update 500 (rollout win vs the script 1.000, 50-update smoothed).

### §1 criteria (sampled actions, n = 512 vs the script, sides swapped)

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

Argmax rows (second row per §6.1, not used for the verdict):

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

<!-- hand:looked-like -->Read from a trajectory trace of six champion-vs-script matches (seed 777; distance, nose angle to the enemy, HP and speed every second), not from the summary metrics:

- **It aims on the way in.** From 450 m down to about 100 m the learned pilot keeps its nose within 1–2° of the enemy, while the script's nose swings 10–27° off as it closes. The learned pilot is already 10–20 hp up before the ships meet.
- **It approaches slower.** It holds about 50 m/s on the approach, where the script runs up to 60–70, so it arrives in a steady firing position.
- **There is no second pass, but a brawl.** After the merge both ships slow to 15–30 m/s and fight a close turning fight at 10–70 m. The script keeps trying to extend (short bursts to 60–70 m/s). The learned pilot stays on it at low speed with its nose usually 5–15° off, while the script's is often 20–90° off. That is why the eval counts one "pass" per match: the ships never leave gun range again.
- **No edge behaviour seen.** Every traced fight stayed near the centre; outside-arena share is 0 in the eval too.<!-- /hand:looked-like -->

## What we learned

<!-- hand:learned -->- **H0 rejected, H2 holds by a mile.** BC + DAgger + PPO beat the script in 512 of 512 duels (sampled and argmax), with a hit rate of 0.67 against the script's 0.60. PPO from scratch on the same budget never learned to shoot (win 0.02, 0 hits).
- **H1 only half held.** Cloning alone did not give a fighter. It matched the script's choices 96 % of the time on the script's own states, yet won 0.6 % of duels. Compounding error was the cause: on its own states it agreed only 78 % of the time, and its argmax play left the arena 28 % of the time. Three DAgger rounds (label the clone's own states with the script) fixed the drift and raised the win rate to 15 %. PPO did the rest in about 400 updates (13 M samples, roughly 35 minutes).
- **Scratch PPO found "never fire".** Each trigger pull costs a little and random aim never hits, so the fire head collapsed to 0 (entropy 0.66 → 0.00 by update 1000). As planned, we report this rather than rescue it. It is a reward-design finding as much as a learnability one.
- **Strong, but short.** The champion kills in a median 12 s (the script mirror takes 44 s), in one approach and one brawl. It holds the trigger on 76 % of decisions, which costs nothing while the gun is cycling. Every watchability cell passes, but the duel no longer has the multi-pass rhythm the balance sweep tuned for. Watch this as opponents get stronger.
- **Throughput ran at a quarter of the plan.** The CPU throttles under sustained load (about 2 GHz), and two concurrent runs got about 6.7 k samples/s each, not 30 k. The night budget should assume this.<!-- /hand:learned -->

## Next

<!-- hand:next -->**Next experiment:** run the same recipe (BC → DAgger → PPO with a decaying script pull) on the strafer and the gunship, whose turret slew heads this spike never exercised. Then move it onto the M3 attention policy, so that one network flies all three hulls. The question is whether the recipe transfers to other hulls, or whether the fighter's result depended on its simple controls.

Backlog added:
- Make DAgger a standard step of the BC pipeline (it is cheap: about 5 minutes a round).
- Add a duel-length / passes watchability signal to the eval gates, so one-pass brawls are visible at promotion time.
- Revisit the fire cost for from-scratch learning (for example no cost while the gun is cycling, or a short warm-up without it).
- Budget nightly runs at the measured throttled throughput.
- The live page now shows this champion (update 1200) at `/duel/`.<!-- /hand:next -->

## Numbers

- `ppo_bc`: 1200 / 1200 updates, 43,201,008 learner samples, 1.78 h of update time (5.34 s/update, 6,738 samples/s), threads 6 sim + 6 torch.
- `ppo_scratch`: 1200 / 1200 updates, 47,962,307 learner samples, 1.97 h of update time (5.90 s/update, 6,778 samples/s), threads 6 sim + 6 torch.
