# <!-- hand:title -->TODO(coordinator): a title that states the finding<!-- /hand:title -->

Date 2026-10-28 · run dir `2026-10-28-learnability-spike` · branch `worktree-agent-a3c8741a8e81ce545` · commit `9108b45` (report) · SIM_VERSION 2 · verdict: **PENDING**

Training: `ppo_bc` 179/1200 (unfinished), `ppo_scratch` 538/1200 (unfinished). Evals present: 3 of 23 matrix pairings.

## What we asked

<!-- hand:asked -->TODO(coordinator): two sentences for a visitor: can a small MLP learn to fly, aim and fire a fighter by driving its thrusters and trigger directly, in one night on a laptop CPU?<!-- /hand:asked -->

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

**PENDING**. missing bc_dagger_vs_script, ppo_bc_final_vs_script.

- **H1** pending (needs BC + DAgger, PPO-BC final and the baseline).
- **H2** pending (needs PPO-BC final and PPO-scratch final).
- **H0** pending (needs PPO-BC final and PPO-scratch final).

PPO-BC best checkpoint so far: update 100 (rollout win vs the script 0.431, 50-update smoothed).

### §1 criteria (sampled actions, n = 512 vs the script, sides swapped)

✓/✗ against the policy's column (BC for BC and BC + DAgger, pass for the PPO policies); 'strong' = every strong cell met; '—' = not evaluated yet.

| policy | column | win rate | draw rate | engagement | hit rate | outside arena | kill endings | engine duty | strong |
|---|---|---|---|---|---|---|---|---|---|
| script (baseline) | — | 0.511 | 0.029 | 0.858 | 0.597 | 0.0000 | 0.998 | 0.850 | — |
| BC | BC | 0.006 ✗ | 0.000 ✓ | 0.927 ✓ | 0.299 ✓ | 0.0021 ✓ | 1.000 ✓ | 0.831 | — |
| BC + DAgger | BC | — | — | — | — | — | — | — | — |
| PPO-BC final | pass | — | — | — | — | — | — | — | — |
| PPO-BC best | pass | — | — | — | — | — | — | — | — |
| PPO-BC 400 | pass | — | — | — | — | — | — | — | — |
| PPO-BC 800 | pass | — | — | — | — | — | — | — | — |
| PPO-scratch final | pass | — | — | — | — | — | — | — | — |

Argmax rows (second row per §6.1, not used for the verdict):

| policy | column | win rate | draw rate | engagement | hit rate | outside arena | kill endings | engine duty | strong |
|---|---|---|---|---|---|---|---|---|---|
| BC (argmax) | BC | 0.005 ✗ | 0.002 ✓ | 0.654 ✓ | 0.422 ✓ | 0.2812 ✗ | 0.963 ✓ | 0.907 | — |
| BC + DAgger (argmax) | BC | — | — | — | — | — | — | — | — |
| PPO-BC final (argmax) | pass | — | — | — | — | — | — | — | — |
| PPO-BC best (argmax) | pass | — | — | — | — | — | — | — | — |
| PPO-BC 400 (argmax) | pass | — | — | — | — | — | — | — | — |
| PPO-BC 800 (argmax) | pass | — | — | — | — | — | — | — | — |
| PPO-scratch final (argmax) | pass | — | — | — | — | — | — | — | — |

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
| BC + DAgger | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| BC + DAgger (argmax) | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC final | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC final (argmax) | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC best | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC best (argmax) | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC 400 | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC 400 (argmax) | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC 800 | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC 800 (argmax) | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-scratch final | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-scratch final (argmax) | script | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC final | BC + DAgger | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC final (argmax) | BC + DAgger | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC final | PPO-BC 400 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC final (argmax) | PPO-BC 400 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC final | PPO-BC 800 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-BC final (argmax) | PPO-BC 800 | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-scratch final | PPO-BC final | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| PPO-scratch final (argmax) | PPO-BC final | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

No NaNs or stuck ships in any eval.

### Learning curves

matplotlib is not installed in the venv, so no PNGs: the per-update curves (rollout win vs the script, raw and 50-update smoothed, and entropy per head group, both runs) are in `learning_curves.csv`. Every 100 updates:

| update | run | samples | win vs script (50-upd) | H throttle | H fire | H power | H mean |
|---|---|---|---|---|---|---|---|
| 100 | ppo_bc | 3,132,389 | 0.431 | 0.159 | 0.113 | 0.649 | 0.222 |
| 100 | ppo_scratch | 3,157,096 | 0.024 | 0.980 | 0.642 | 1.850 | 1.056 |
| 200 | ppo_scratch | 6,361,798 | 0.071 | 0.893 | 0.491 | 1.785 | 0.963 |
| 300 | ppo_scratch | 9,568,438 | 0.062 | 0.828 | 0.095 | 1.679 | 0.845 |
| 400 | ppo_scratch | 13,127,765 | 0.040 | 0.746 | 0.091 | 1.544 | 0.766 |
| 500 | ppo_scratch | 17,296,619 | 0.003 | 0.739 | 0.014 | 1.572 | 0.754 |

## What it looked like

<!-- hand:looked-like -->TODO(coordinator): two or three observations from render_state replays: does it lead its shots, does it turn to re-engage, what does it do at the edge. Do not fill from the numbers alone.<!-- /hand:looked-like -->

## What we learned

<!-- hand:learned -->TODO(coordinator): bullets on which of H1/H2/H0 held, and surprises.<!-- /hand:learned -->

## Next

<!-- hand:next -->TODO(coordinator): the one experiment this result argues for; backlog items added.<!-- /hand:next -->

## Numbers

- `ppo_bc`: 179 / 1200 updates, 5,603,902 learner samples, 0.21 h of update time (4.22 s/update, 7,426 samples/s), threads 6 sim + 6 torch.
- `ppo_scratch`: 538 / 1200 updates, 18,879,919 learner samples, 0.66 h of update time (4.40 s/update, 7,981 samples/s), threads 6 sim + 6 torch.
