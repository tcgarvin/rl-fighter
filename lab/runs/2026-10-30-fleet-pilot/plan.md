# Fleet pilot v1: one network flies every hull in mixed fleets

| | |
|---|---|
| Run | `2026-10-30-fleet-pilot` (M2 WP-T, `docs/M2_PLAN.md` §4) |
| Branch | `m2-site` (WP-T worktree) |
| Question | Can the spike's masked multi-head MLP, one network for every ship, fly fighters, strafers and gunships in mixed skirmishes of 1–4 ships a side, beat the scripted pilots, and leave no hull behind? |
| Scenario | rosters from `fleet_v1` (1–4 a side, mixed hulls, uneven sides, budget drafts), arena 450 m, 90 s limit, `reaction_ticks` 2, `SIM_VERSION` 3 |
| Status | **planned**; pipeline smoke-tested (`SMOKE=1 run.sh`), baselines measured (`eval/`), not trained |
| Ships | the promoted pilot replaces the fighter-only duel pilot on the live page, where it flies every ship (M2 §1) |

## 1. Why, and what would count

The live page will show mixed fleets with every ship flown by the champion pilot
(M2 §1); today's pilot only knows 1v1 fighter duels. The obs layout and the action
heads already cover every hull (385 floats, 21 masked heads, SIM_SPEC §7), so one
network can fly all three. This run asks whether the spike's recipe carries over.

- **H1.** BC + DAgger on the three scripted pilots, then PPO with a decaying pull
  toward them, gives a fleet pilot that beats the script team on the fixed fleet
  suite (G1) with every hull at least as useful as its script (G2), healthy (G3),
  and still a strong duellist (G4).
- **H2.** Starting the clone from the v3 duel champion's weights (arm *warm*) beats
  starting it fresh (arm *fresh*) at equal samples.
- **H0.** A shared MLP cannot serve three control schemes: some hull stays below its
  script (G2 fails) however strong the team is. That is the DESIGN §7 "split a hull
  class off" signal and would move the shared-vs-specialist comparison into M3.

## 2. Before training: the teachers, balance, the arena

`tools/fleet_survey.py`, script vs script, suite `survey` (22 rosters × 128
matches, `survey/script_vs_script.{md,json}`), and the gate baseline on the
`fleet_v1` suite (`eval/script_vs_script_fleet.{md,json}`, 16 rosters × 64).

**The scripted strafer and gunship fight sensibly; no script fix.** Pooled over both
sides of the survey:

| hull | dmg / ship (hull + shield) | dmg / cost | survival | hit rate | engagement | outside arena | crash dmg / ship |
|---|---|---|---|---|---|---|---|
| fighter | 64.9 + 40.0 | 10.5 | 0.44 | 0.61 | 0.86 | 0.0000 | 5.0 |
| strafer | 61.8 + 27.5 | 8.9 | 0.31 | 0.32 | 0.86 | 0.0000 | 0.6 |
| gunship | 216.8 + 84.9 | 10.1 | 0.58 | 0.23 | 0.93 | 0.0000 | 1.6 |

Every hull engages, lands hits and stays in the arena; draws are 0.2 %. The gunship's
low hit rate is flak bursts and broadside gauss at range, not missing turrets.

**Balance (report only; the hull YAMLs are not retuned here, that needs a
`SIM_VERSION` bump and the live page's art).** Hull costs are fighter 10,
strafer 10, gunship 30.

| roster (first team v second) | cost | first team wins | time limit |
|---|---|---|---|
| F v S | 10 v 10 | 1.00 | 0.00 |
| FF v SS / FFF v SSS / FFFF v SSSS | equal | 0.84 / 0.97 / 0.96 | 0.00 |
| G v FFF / G v SSS / G v FFS | 30 v 30 | 0.00 / 0.21 / 0.02 | 0.00 |
| GF v FFSS / GS v SSFF | 40 v 40 | 0.27 / 0.11 | 0.00 |
| G v G | 30 v 30 | 0.46 | 0.36 |
| FG v SG / FSG v FSG / FSGF v SSFG | equal | 0.82 / 0.73 / 0.45 | 0.62 / 0.62 / 0.46 |

- **The fighter dominates the strafer at equal cost**: it wins the 1v1 every time,
  and pure-fighter teams beat equal strafer teams at 84–97 %. The strafer's laser
  meets the fighter's 0.5× nose armour because the fighter chases nose-on.
- **The gunship is overpriced**: three lights (30) beat it 79–100 % of the time, and
  a gunship plus a light lose to four lights. Damage per cost is even (≈ 10) but
  the gunship dies to focus fire.
- **Gunship against gunship stalls**: every roster with a gunship on both sides
  hits the 90 s limit 36–62 % of the time (two shields regenerating 12 hp/s
  against the gunship's 0.2 hit rate). The live page decides those on value, but
  they are long and slow to watch.
- Recommended retunes, for a later `SIM_VERSION`: gunship `cost` 30 → 20 (or keep
  30 and raise its hp/shield); strafer laser `damage` 3 → 4 or `hp` 70 → 85; gunship
  `shield.regen_rate` 12 → 6 to end gunship mirrors. Re-survey after each.
- Fair-fight consequence for this run: in the fixed suite every roster is played
  with the pilot on each side equally often, so the script's own win rate is 0.50
  everywhere (baseline 0.499) and lopsided rosters weigh both ways.

**Arena: 450 m for every fleet size** (`sim::setup::arena_radius_for`, exported as
`rlf_sim.arena_radius_for` and the browser's `arenaRadiusFor`; the live page must
call it). A growing radius (+25 m per ship beyond two, 600 m for 4v4) was tried on
the `fleet_v1` suite (`survey/radius_450_vs_rule.md`): engagement 0.91 vs 0.89 and
crash damage 2.5 vs 2.4 per ship, the same; but 4v4 rosters hit the time limit more
(0.28 vs 0.19). The obs scale distances by the radius, so one radius also keeps the
duel pilots' inputs where they trained.

**The v3 duel champion does not fly fighters well in fleets**
(`survey/champion_fighters_vs_script.md`: champion on the fighters, script on
the other hulls, vs the script team): its fighters deal 28 + 21 damage (script
fighters 67 + 30), hit 0.15 of their shots (0.62), survive 0.09 (0.50), and its team
wins 0.29. Flying every hull (`eval/champ_v3_fleet_vs_script.md`) it wins 0.165,
0.495 in 1v1s (it still wins the fighter duel) and ≤ 0.03 in 3v3 and larger. So the
script, not the champion, is the teacher for every hull, and the warm arm tests
only whether the champion's *weights* are a better starting point than random.

## 3. Setup

- **Rosters** (`spacefight/env/rosters.py`, preset `fleet_v1`), drawn per env per
  episode, seeded: a fighter duel 5 %; a budget draft 25 % × 0.95 (budget 20/30/40,
  each side buys uniformly among hulls it can still afford, up to 4 ships, so sides
  can be uneven, e.g. G v FFF); else a skirmish with team 0's size from
  (0.2, 0.3, 0.25, 0.25) for 1–4, the other side ±1 with p = 0.25, a mirror
  composition with p = 0.2, else uniform hulls. Slot order is shuffled, teams are
  swapped with p = ½. Measured over 2000 draws: 1v1 16 %, 2v2 26 %, 3v3 16 %,
  4v4 15 %, uneven 27 %; hulls 37 % fighter, 35 % strafer, 29 % gunship.
- **Env**: `RustVecEnv(roster_sampler=…)`, `max_ships` 8 (padding slots: team -1,
  zero obs, no heads), N = 256, the next roster queued when a match ends
  (`set_next_roster`, zero-copy buffers; `tools/bench_env.py --assert-floors`
  passes: 10.9 k / 6.4 k / 2.4 k steps/s).
- **Policy**: the spike's `SpikeActor` (385 → 256 → 256 → 61, 21 masked heads),
  unchanged; masks come from each ship's own hull, so the gunship's three slewing
  turrets get slew heads and the fixed guns do not.
- **Critic**: `FleetCritic`: the spike critic on the ship's own obs plus a correction
  from mean-pooled 64-d embeddings of its present teammates and of the present
  enemies (and both counts); padding and dead ships are masked out, any team size up
  to 4 a side works. It starts from the init checkpoint's critic with the correction
  at zero. PPO minibatches are whole (step, env) groups so the critic sees each
  row's match.
- **Samples**: every alive ship of the learning team (team 0, plus team 1 in
  self-play envs) with `act_mask` set; labels from `scripted_actions()`, each hull
  its own script.
- **Credit**: `RustCreditAdapter` unchanged; tested with up to 8 shooters per match
  (`tests/test_spike_ppo.py::test_credit_lands_on_decision_step_across_rollouts[fleet]`).

## 4. Method

**Recipe: BC → DAgger → PPO with a decaying script pull, for both arms.** The spike
showed BC alone fails (0.6 % vs the script: compounding error), three DAgger rounds
fix the drift (15 %) and make the init PPO needs, and PPO from scratch never learns
to fire. Fleets add three control schemes and more off-distribution states, so
DAgger matters more, not less.

| stage | arm *fresh* | arm *warm* |
|---|---|---|
| round 0 | BC on 3 M DART rows (p = 0.15), 8 epochs, fresh actor | the v3 champion's actor (no training; its DART rows still join the aggregate) |
| rounds 1–3 | 2 M on-policy rows each (learner flies one whole team vs the script), labelled by the script, aggregated, 2 epochs fine-tune | same |
| best round | highest fleet win vs the script (suite `fleet_v1`, 32 per roster) | same |
| PPO | 600 updates of 256 × 128, from that round | same |

DART and on-policy collection use 128 envs, so each env plays about three matches
per round and late-match states are covered. PPO: the spike's BC preset (actor LR
1e-4, clip 0.1 for 200 updates, 30-update critic warm-up, β 0.1 → 0 over updates
30–300), `critic=fleet`, opponent bands `[[0,1,0,0],[200,0.5,0.3,0.2],[400,0.4,0.3,0.3]]`
(script / self-play / frozen pool), checkpoints every 100. The script stays at
≥ 40 % of envs throughout: it is the only opponent that flies every hull well from
update 0, and G1 is measured against it.

## 5. Gates (fixed before any learned fleet policy was evaluated)

Encoded in `spacefight/eval/fleet_gates.py`; `gates.py` applies them to the JSONs
`eval.sh` writes. Fleet eval: suite `fleet_v1` (1v1 F/S/G mirrors, three 2v2, three
3v3, two uneven 2v3, three drafts, two 4v4), 64 matches per roster, the pilot on
each side half the time, seed 200000, sampled actions. Duel: `spacefight.eval.duel`,
n = 512, seed 100000. "Script baseline" = `eval/script_vs_script_fleet.json`, same
suite, seed and size, both sides pooled.

| gate | check | bound |
|---|---|---|
| **G1 strength** | win vs the script (draws ½), all rosters | ≥ 0.60 |
| | win vs the script in every roster class (1v1, 2v2, 3v3, 2v3, draft, 4v4) | ≥ 0.45 |
| **G2 no hull left behind** | per hull (fighter, strafer, gunship): damage dealt per ship, hull + shield, / the script baseline's | ≥ 0.9 |
| | per hull: survival − the script baseline's | ≥ 0 |
| **G3 health** | engine duty (strongest thruster's level, live ticks) of every hull | 0.15–0.95 |
| | outside-arena share of live ticks, all ships | ≤ 0.02 |
| | draw rate | ≤ 0.05 |
| | matches with a NaN obs or a stuck ship | ≤ 1 % |
| | time-limit rate − the script baseline's (0.121) | ≤ 0.15 |
| **G4 the duel** | fighter duel win vs the v3 champion (`ppo_bc_600`) | ≥ 0.35 |
| | fighter duel win vs the script | ≥ 0.80 |

Baseline values the bounds refer to: script per-ship damage fighter 89.1, strafer
93.2, gunship 299.5; survival 0.37 / 0.35 / 0.65; engine duty 0.39 / 0.43 / 0.53;
the v3 champion wins the duel vs the script 1.000.

Candidates: each arm's DAgger best and PPO checkpoints at 200, 400, 600. **Pick**: the
candidate that passes all of G1–G4 with the highest fleet win vs the script (ties:
duel win vs the champion). If none passes, nothing is promoted; the live page keeps
fighter-only fleets with the v3 champion (M2 §2), and `results.md` says which gate
failed. Reported, not gated: win vs the arm's own DAgger init (`*_fleet_vs_ref`),
per-class win, hit rate, passes and crash contacts per hull, median length.

## 6. Budget and schedule (measured 2026-10-29 on this laptop, otherwise idle)

| stage | measured | estimate |
|---|---|---|
| baseline evals | done: 54 s for all three | 0 |
| fleet DART collection | 1 M rows in 2.2 s (256 envs) | seconds |
| BC / DAgger training | 107 k rows/s at 12 threads | round 0: 23 M rows ≈ 3.5 min; rounds 1–3: 10–18 M rows ≈ 1.5–3 min each |
| DAgger round scoring | fleet eval of 512 matches + duel of 256 | ≈ 1 min per round |
| **DAgger, both arms** (sequential, 12 threads) | | **≈ 35 min** |
| PPO, one arm alone, 6 sim + 6 torch | 8.0 s/update, 60 k samples/update (7.5 k samples/s) | |
| **PPO, two arms at once** | the spike ran 1.9× slower per update with two arms | **≈ 15 s/update → 600 updates ≈ 2.5 h**, 36 M samples per arm |
| **gate evals** (8 candidates × fleet vs script, fleet vs ref, two duels) | baseline fleet eval of 1024 matches < 30 s | **≈ 20 min** |
| **total** | | **≈ 3.5 h** |

If throughput is half the estimate (thermal throttling, as the spike saw), stop PPO
at the 400-update checkpoints (`N_UPDATES=400 EVAL_UPDATES="200 400"`), or drop the
warm arm. Memory: the DAgger aggregate is 9 M rows ≈ 7.5 GB (float16 obs), freed
before PPO; each PPO arm's buffer ≈ 0.6 GB.

## 7. Risks

| risk | signal | response |
|---|---|---|
| one hull lags (H0) | G2 fails for one hull while G1 passes | report it; M3's shared-vs-specialist comparison; a per-hull loss weight in BC |
| the warm arm forgets its duel skill in DAgger | `warm_dagger` duel vs champion ≪ 0.5 | expected; G4 is checked after PPO, not after DAgger |
| gunship mirrors stall under learned play too | time-limit rate > baseline + 0.15 | G3 rejects; recommend the regen retune of §2 |
| PPO collapses fire on shielded hulls (fire cost vs shield hits at half weight) | strafer / gunship fire rate → 0 in `hull_hit_rate`/log | keep β longer (`beta_decay_end` 500) |
| self-play destabilises | vs_scripted_win falls after update 200 | the script share stays ≥ 40 %; pick an earlier checkpoint |
| throughput half the plan | > 20 s/update | stop at 400 updates (§6) |

## 8. Running it

From the repo root of the main checkout (the v3 champion's weights live there):

```
nohup lab/runs/2026-10-30-fleet-pilot/run.sh > lab/runs/2026-10-30-fleet-pilot/run.out 2>&1 &
```

Stages `baseline dagger_fresh dagger_warm ppo eval gates`, each skipping finished
work (PPO resumes from its latest checkpoint; an unfinished DAgger directory is
moved aside, never deleted). `run.sh eval gates` re-runs only those. Logs:
`run.out`, `<stage>.out`, `arm_*/log.jsonl`. `SMOKE=1 run.sh` runs every stage at
tiny sizes into `smoke/` (gitignored) in about two minutes. Afterwards: write
`results.md` from `eval/gates.md`, and promote the pick only if it passes.
