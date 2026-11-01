# First pilot families

Planned 2026-11-01, before any of this was trained. The full plan is
`docs/PILOT_TRAINING.md`. This file is the exact run. **Nothing starts until the owner says
the machine is free.**

## Steps

1. **Check the whole repo:** `scripts/check.sh` and the full pytest suite, which have not
   run on the merged code, including the wasm build.
2. **Measure (`measure.sh`):** drills on the script, founders, `reward_300` and `hide_644`,
   then the round robin across 9 existing pilots. Set the bars in
   `spacefight/eval/drill_bars.yaml` from the drill results.
3. **Speed and memory check:** `run.sh` for about 10 minutes, all arms. Read update time
   and memory. Each learner's rollout obs buffer is about 2 GB at 256 envs and 20 slots,
   and the machine has 29 GB. If memory is tight, set `N_ENVS` lower for all arms.
4. **First night (`run.sh`):** resumes from step 3.
5. **Morning:** drill evals on each arm's latest checkpoint, add those that train usefully
   to the population, round robin into a new results directory, report with shadow culls.

## Arms

All arms: preset `pilots_v1`, discount 0.995 with order pay following it, no script pull,
no KL anchor, constant LR, 4 sim + 4 torch threads, checkpoints every 50 updates.

| Arm | Starts from | Drills | Commander | No commander | Order pay | Enemies |
|---|---|---|---|---|---|---|
| `fighters` | `f995_701` | 0.10 | 0.30 | 0.60 | 3 | 0.2 script, 0.4 self, 0.4 pool (weighted) |
| `followers` | `transit_300` | 0.25 | 0.50 | 0.25 | 1 | same |
| `scratch` | Random weights | 0.10 | 0.30 | 0.60 | 1 | 0.5 script, 0.5 self |

Pool: `f995_701`, `transit_300`, `reward_300`, `w1_400`, v1 for half of draws, this run's
checkpoints for the rest.

**Why these settings:**

- **`fighters` at order pay 3:** this is the plan's first question. Can a small share of
  drills give a strong fighter some following while it keeps its combat? Pay of 3 gives
  the question a real chance. If combat falls badly, the next try is 1.
- **`followers` at order pay 1:** it already follows and needs combat, so team reward
  should dominate. Its script pull ends here.
- **`scratch`:** actor LR 3e-4 rather than 1e-4, since it starts from nothing, and no
  frozen pool at first, since strong enemies would give it nothing to learn from.

## What each morning reads

| Question | Measure |
|---|---|
| Does `fighters` learn orders? | Drill flip rates and go-to lift against `f995_701` |
| Does `fighters` keep combat? | No-commander matches against `f995_701` |
| Does `followers` gain combat? | No-commander matches against `transit_300` |
| Does `followers` keep following? | Its drill results against `transit_300`'s |
| Is `scratch` alive? | Deathmatch against the script. If it can't beat the script by morning, its slot goes to another family |

**Fighters' fallback:** if following does not improve, raise the drill share. If that fails,
move to separate skill networks (`docs/PILOT_TRAINING.md` section 4).

`f995_701` stays live throughout. Nothing here deploys.
