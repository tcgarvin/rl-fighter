# Orderable pilots: one pilot that follows an attack order and answers a recall (plan)

Prepared 2026-11-21 on the laptop. Started on Beast at 04:22, about 8.5 s an update an
arm; training stops at 11:30, then the final evals and report.md (about 13:00). It runs
beside [commander 4](../2026-11-21-commander-4/plan.md): pilots that can take orders, and
commanders that might make orders worth giving.

## Question

Can one pilot be both **orderable** and **dockable**?

- *Orderable*: an attack order no longer costs it a fleet fight. The kite drills did that
  (`../2026-11-18-kite-drills/results.md`): ordered onto its nearest enemy in a 3 v 3
  against a free `followers_school_1052`, `kite` 2205 wins 0.42 (its parent 0.14), and the
  order's cost (nearest minus no orders, paired) fell from −0.37 to −0.15 (−0.09 at 2200).
- *Dockable*: it answers a recall and lands. The dock drills did that
  (`../2026-11-20-dock-pilot/report.md`): `dock600` 2624 docks 0.57 of calm dock drills
  and 0.27 of threat drills, where its parent docked 0.02.

Today each skill lives in a different pilot. A commander is only worth something if its
pilots can do both: it orders them onto targets and it recalls them. Each arm starts from
one of the two pilots and learns the other skill, with the first skill's training kept
in the mix so it is not lost.

## Arms

One shared config (below), two parents.

| Arm | Init | Inputs | Seed | Where |
|---|---|---|---|---|
| `kitedock` | `kite` 2205 (`../2026-11-18-kite-drills/kite/checkpoints/ppo_bc_2205.pt`, 587 inputs) | widened to 592 with `--set obs_dim=592 --set new_input_lr_mult=3`, as in the dock pilot run | 2111 | Beast, `update_device=cuda:0`, 3 + 3 threads |
| `dockkite` | `dock600` 2624 (`../2026-11-20-dock-pilot/dock600/checkpoints/ppo_bc_2624.pt`, already 592) | `obs_dim` 592 (no new columns, so `new_input_lr_mult` does nothing) | 2112 | Beast, `update_device=cuda:1`, 3 + 3 threads |

Both parents are followers of one line: `kite` 2205 is a child of `followers_school_1052`,
which is `followers_school_600` a night on; `dock600` 2624 is a child of
`followers_school_600`. So the arms differ by their starting weights and seed, not by
family.

## Config

`followers_school`'s config (`../2026-11-14-goto-school/followers_school/config.yaml`, as
the dock pilot run used): order pay 1, extra fire cost 0.002, gamma 0.995, actor lr
1e-4, 256 envs x 128 steps, PFSP over its 17 pool seeds (`pool_seed_p` 0.5), critic
warm-up 20, early clip 50. The kite run's config (`kite/config.yaml` on Beast and the
laptop) is the same file with its own overrides: nothing in it is kite-specific beyond
`drill_attack_pool_share`, and the kite drills' enemies come from those same pool seeds.
Set on top:

| Key | Value | Why |
|---|---|---|
| `obs_dim`, `new_input_lr_mult` | 592, 3 | the dock block; widens `kite` 2205 |
| `dock_bonus` | 1.0 | the dock pilot run's pay (the sim's is 0.2) |
| `goto_timed_bonus`, `goto_miss_penalty` | 3, 3 | as both parents |
| `commander_stable` | `[live, scripted]`, weights `[1, 1]` | 0.625 of commanded sides scripted, which recall; learned commanders never do |
| `drill_share` | 0.55 | as the dock pilot run |
| `drill_weights` | [4, 3, 1] | the kite drills' order mix (go-to, attack, defend) |
| `drill_attack_pool_share` | 0.5 | half the attack drills are kite drills |
| `drill_dock_share` | 0.4 | dock drills, between the default 0.25 and the dock pilot run's 0.5 |
| `drill_dock_threat_share` | 0.5 | calm and threat half each |
| `commander_p`, `mixed_p` | 0.667, 0 | as both parents |
| `mission_weights`, `citadel_share` | the `pilots_v1` defaults, (0.3, 0.25, 0.25, 0.2) and 1 | station assault a fifth of matches, always the citadel, as live (since 2026-11-21) |
| `checkpoint_every` | 25 | |

**The mix as the trainer resolves it** (share of draws):

| | This run | `kite` 2205 trained on | `dock600` 2624 trained on |
|---|---|---|---|
| Dock drills, calm / threat | 0.110 / 0.110 | 0 | 0.1375 / 0.1375 |
| Go-to drills | 0.165 | 0.200 | 0.206 |
| Attack drills, standard / kite | 0.062 / 0.062 | 0.075 / 0.075 | 0.034 / 0 |
| Defend drills | 0.041 | 0.050 | 0.034 |
| Deathmatch | 0.135 | 0.240 | 0.180 |
| Carrier battle | 0.1125 | 0.180 | 0.135 |
| Convoy escort | 0.1125 | 0.180 | 0.135 |
| Station assault (citadel) | 0.090 | 0 | 0 |

Matches show orders on both sides 0.667 of the time and hide them from both otherwise.
So `kitedock` keeps 0.83 of its attack drills and gains dock drills and the citadel;
`dockkite` keeps 0.8 of its dock drills and gets 3.6 times its attack drills, half of
them kite drills. A kite drill runs 60 s and a dock drill 20 to 60 s, so their share of
the rollout rows differs from their share of draws (`drill_rows_share` in the log).

## Measures

`eval.sh` on a checkpoint writes into `eval/<name>/` (`summary.py eval <dir>` prints it):

- (a) **The drill eval**, all five kinds (go-to, attack, defend, `dock_calm`,
  `dock_threat`; the default since 2026-11-21), each flown again with the order hidden:
  the order drill bars and the dock drills' docked, shot down, docked of survivors and
  lift.
- (b) **Recalls in matches**: the candidate on every strike slot of both sides of carrier
  battles and station assaults, scripted commanders, which recall below half hull
  (`../2026-11-20-dock-repair/dock_eval.py`): recall completion.
- (c) **Wins against the script**: the mission eval (carrier battle, convoy, station
  assault; 192 a mission) and the fleet_v1 suite (16 a roster).
- (d) **The order cost**, as the kite drills measured it
  (`../2026-11-17-order-cost/order_rules.py`): 3 v 3, 24 blocks (1,152 matches a row),
  the candidate ordered by `nearest`, by `scripted` and unordered (`none`), against a free
  `followers_school_1052` and a free `f995_701`. Cost is nearest minus none, paired match
  by match. From the `nearest` rows also what the ordered side did in the first 30 s:
  target in arc, ships lost, damage dealt to and taken from its target.

**Periodic**, every 500 updates of each arm while it trains, at the quick sizes (nice 19,
2 threads): (a) at 64 a kind and (b) at 96 matches a mission.

**Final**, after the deadline, for each arm's last checkpoint and both parents
(`eval/parent_kite2205`, `eval/parent_dock2624`), the four side by side at 3 threads
each: (a) at 128 a kind, (b) at 256 a mission, (c) and (d).

`summary.py report` writes `report.md`: every measure by checkpoint, each arm beside its
parent, and the training telemetry from `log.jsonl` (dock drills docked, calm and threat;
carrier-battle recalls and docks a match; kite drills' pass rate, pilots lost and damage
dealt to and taken from the target; standard attack pass rate; drill rows share). It
reports measurements only. What goes live is WAR's and the family rules' call
(`docs/PILOT_TRAINING.md` §5, §6), in the morning's WAR step.

What to read in it: for `kitedock`, whether the dock rows climb as `dock600`'s did while
the order cost stays near its parent's −0.15; for `dockkite`, whether its order cost
moves from its parent's (measured here for the first time) towards `kite`'s while its dock
rows hold. Each arm is one seed.

## The morning's WAR step

`war.sh` (after the run; reads the arms' last checkpoints and final drills):

- `kite_2205` and `kite_pay025_2211` are **not yet season members**. They are children of
  `followers_school_1052` (fork update 1052, from `../2026-11-18-kite-drills/`), and
  joining the season is part of this step: `war.sh` adds both and records their final
  drills (`../2026-11-18-kite-drills/eval_final/*_drills.json`).
- It adds `followers_dock_2624` and `followers_dock_v8_2676` if the season copy lacks
  them (they joined in the dock pilot WAR step on Beast).
- Tonight's members:
  - `kite_dock_<update>`, parent `kite_2205`, fork update 2205;
  - `followers_dockkite_<update>`, parent `followers_dock_2624`, fork update 2624;
  where `<update>` is the arm's last checkpoint. Their final `drills.json` is recorded
  under phase `orderable-pilots`.
- WAR on its default missions (all four, the station assault the citadel), `--commanders
  live`, 1,440 matches a mission, over the live list, `followers_dock_2624`,
  `followers_dock_v8_2676`, `kite_2205`, `kite_pay025_2211` and the two new members;
  then the season report. It archives and publishes nothing.

```bash
nohup setsid lab/runs/2026-11-21-orderable-pilots/war.sh \
    > lab/runs/2026-11-21-orderable-pilots/war.out 2>&1 &
```

## Budget

At the dock pilot and kite runs' 10.5 to 12.5 s an update (two arms, one a GPU, 3 + 3
threads), 6.5 hours is about 1,900 to 2,200 updates an arm, so four periodic evals an
arm. The final evals: about 1 to 1.5 hours with the four side by side (the order cost is
six rows of 1,152 matches each; the kite run's took about 15 minutes a row at 1 thread
with 14 jobs at once). Suggested: `DEADLINE` 6.5 hours after the start, so the report is
ready about 8 hours in. WAR is about an hour at 12 threads.

## Beast-side setup

- Pull this branch and rebuild the extension in the checkout's venv:
  `uv run maturin develop -m crates/sim-py/Cargo.toml --release` (run.sh refuses an
  `rlf_sim` without the dock drills).
- The weights under the checkout, all already there from the kite and dock pilot runs:
  `lab/runs/2026-11-18-kite-drills/kite/checkpoints/ppo_bc_2205.pt`,
  `lab/runs/2026-11-20-dock-pilot/dock600/checkpoints/ppo_bc_2624.pt`, the order cost's
  bases (`lab/runs/2026-11-14-goto-school-2/followers_school/checkpoints/ppo_bc_1052.pt`,
  `lab/runs/2026-11-01-fighters-v2/f995/checkpoints/ppo_bc_701.pt`) and the pool seeds
  `followers_school`'s config lists.
- The live stable's learned commanders are fetched by HTTPS into
  `~/.cache/rl-fighter/weights` (already there).

```bash
DEADLINE="2026-11-21 11:30" nohup setsid lab/runs/2026-11-21-orderable-pilots/run.sh \
    > lab/runs/2026-11-21-orderable-pilots/run_beast.out 2>&1 &
```

## Smoke (laptop, 2026-11-21)

`SMOKE=1 DATA_ROOT=/home/timg/code/rl-fighter PY=/home/timg/code/rl-fighter/.venv/bin/python
nice -n 19 run.sh` (from a worktree; CPU, 1 + 1 threads): both arms train 2 updates
(8 envs x 32 steps), `kitedock` widening 587 to 592; the periodic evals on update 2 of
each, then the final evals of both parents and both last checkpoints at 4 to 12 a cell
(one block, 48 matches, a row of the order cost) and `report.md`: 10 minutes 22 seconds,
exit 0, no eval failed. The trainer's config resolves to the mix in the table above
(20,000 draws from it: dock 0.111 / 0.113, go-to 0.161, attack 0.063 / kite 0.061,
defend 0.041, deathmatch 0.132, carrier 0.113, convoy 0.116, citadel 0.090; orders shown
in 0.297 of draws, hidden in 0.153). Two updates change no actions (the critic warms up
for 20 updates first), so each arm's smoke columns equal its parent's.
