# Dock pilot: teaching learned pilots to dock (plan)

Prepared 2026-11-20 on the laptop; stage 3 of `../2026-11-20-dock-repair/plan.md`.
Nothing here is launched by this plan: the coordinator starts `run.sh` on Beast.

## Question

Can a live pilot, widened to read the v11 `dock` block, learn to fly home and dock when
the scripted commander recalls it, in a fight and out of one, without losing what it has
on the old drills and missions?

Zero-shot, no learned pilot docks (`baseline/summary.md`, 128 drills a kind):

| Pilot | Calm: docked | Calm: shot down | Calm: closest, median | Threat: docked | Lift (order seen minus hidden) |
|---|---|---|---|---|---|
| script | 0.95 | 0.02 | 9 m | 0.58 (0.99 of survivors) | (flies orders it cannot see) |
| `followers_school_600` | 0.02 | 0.08 | 88 m | 0.02 | -0.01 |
| `followers_v8_352` | 0.01 | 0.12 | 126 m | 0.01 | -0.02 |
| best of the other eight | 0.03 | 0.09 to 0.78 | 105 to 160 m | 0.05 | 0.02 |

In matches (`../2026-11-20-dock-repair/results.md`) the live pilots complete 1 to 2
recalls in 100 (the script 54 to 64). They ignore the order: no pilot's lift exceeds 0.02.

**Hypothesis.** The order is already in the obs (the go-to reading, and since v11 the
dock flag, the bay's velocity and its direction). What is missing is practice and pay:
nothing ever paid these pilots to come home slowly. With dock drills a quarter of the
draws, recalls in real matches under the scripted commander, and a dock bonus worth more
than a last shot at the enemy carrier, a pilot learns to dock, first alone, then in a
fight, and carries it into matches. Little else changes in the mix, so the old skills
hold.

## The drill

`spacefight/env/drills.py`, `DrillGenerator.dock(seed)`; `docs/PILOT_TRAINING.md` §2
"Dock drills". One damaged strike craft (fighter, strafer, gunship or bomber; 20 to 50 %
hull) ordered home to its carrier under way (half), station or citadel (a quarter each),
150 to 350 m out, any bearing, heading and speed. Calm: alone. Threat: one or two script
craft ordered onto it, starting 90 to 200 m behind it. Team 1's carrier waits across the
arena, out of the way and out of flak range. The match is a carrier battle or station
assault laid out by hand under drill rules; it ends when the pilot docks, is shot down,
or on the clock (three times its straight line at its speed cap, plus 15 s). No crutches:
the pilot flies the approach on its actuators from the obs; the sim's docking rule (10 m,
15 m/s relative) is the only judge.

## Arms

Two arms, one config, one parent each, each widened from 587 to 592 inputs with
`--init <parent> --set obs_dim=592 --set new_input_lr_mult=3` (zero columns that step
three times as far; `tests/test_dock_train.py`).

| Arm | Parent | Seed | Where |
|---|---|---|---|
| `dock600` | `followers_school_600` (`../2026-11-14-goto-school/followers_school/checkpoints/ppo_bc_600.pt`) | 2011 | Beast, `update_device=cuda:0`, 3 + 3 threads |
| `dock352` | `followers_v8_352` (`../2026-11-12-pilots-v8/followers_v8/checkpoints/ppo_bc_352.pt`) | 2012 | Beast, `update_device=cuda:1`, 3 + 3 threads |

**Why these two.**

- `followers_school_600` is the strong all-rounder: fourth by WAR on the live list
  (+13.7, interval 10.5 to 17.3, overlapping the top three) and the best order follower
  on it (drill go-to 0.70, attack flip 0.86, defend flip 0.89; it passed every bar of the
  order gate). Docking is following an order, so the pilot that follows best is the
  likeliest to learn it, and it is strong enough that a live list could take its child.
  Zero-shot it came closest of all (88 m median) and was shot down least in calm drills.
- `followers_v8_352` docked most often zero-shot in the dock-repair matches (16 of 256
  carrier-battle recalls; 0.40 of the survivors) and is `600`'s parent, a weaker follower
  (go-to 0.51) with WAR +11.8. If both learn, docking does not depend on a night of go-to
  school; if only `600` learns, it does.
- Both read 587 floats (v8), so both widen the same way, and both are followers trained
  under one family's config, so the arms differ by their starting weights and seed only.
  The fighters (`fighters_pay1_v8_351`, the top 587 pilot by WAR) were passed over:
  they ignore orders (go-to 0.31) and attack the enemy carrier in a calm drill two times
  in three, so they would be learning to follow at all, not to dock. A fighters arm is
  the obvious next one if this works.

## Config

`followers_school`'s config (`../2026-11-14-goto-school/followers_school/config.yaml`:
order pay 1, go-to deadline pay 3 and 3, extra fire cost 0.002, gamma 0.995, actor lr
1e-4, 256 envs x 128 steps, PFSP over its pool seeds, critic warm-up 20, early clip 50),
with:

| Key | Value | Why |
|---|---|---|
| `obs_dim`, `new_input_lr_mult` | 592, 3 | the dock block (the 583 to 587 widening's recipe) |
| `dock_bonus` | 1.0 | see "Pay" |
| `commander_stable` | `[live, scripted]`, weights `[1, 1]` | the live stable (as the parent trained: the script and three learned commanders) with extra weight on the script, which recalls: 0.625 of commanded sides are scripted, against 0.25. Learned commanders never recall, so without this three sides in four would never send a pilot home |
| `drill_share` | 0.55 | the parents trained at 0.35 (`352`) and 0.7 (`600`) |
| `drill_dock_share` | 0.5 | dock drills are 0.275 of draws. A dock drill is one learner ship for 20 to 60 s; a match is 5 to 9 for 40 to 150 s, so this is a few per cent of the rows. At 256 envs it is about 4 to 6 finished dock drills an update, some 10,000 in a night |
| `drill_dock_threat_share` | 0.5 | calm and threat half each |
| `drill_weights` | [6, 1, 1] | the other 0.275 are order drills, go-to weighted as in school and the station-mix control: the go-to deadline skill is the one that decays first without practice |
| `commander_p`, `mixed_p` | 0.667, 0 | as the parent |
| `mission_weights` | the default 0.4 / 0.3 / 0.3 / 0 | no station assaults in matches: the station-mix run added them at a quarter and both seeds slipped on the old missions (`../2026-11-19-station-mix/results.md`). Docking at a station or citadel is in the drills; matches keep the parents' mix, and recalls happen in carrier battles (0.3 of matches, the longest) |
| `checkpoint_every` | 25 | |

## Pay

The sim pays a dock order as a go-to to the bay's dock point (potential shaping, about
+0.3 to +0.75 over 150 to 350 m) and `dock_bonus` on docking. The shaping is a potential,
so a pass through the bay that does not dock pays nothing it does not give back on the way
out, and loitering by the bay pays nothing: no pay for merely approaching can be farmed.

`dock_bonus` 1.0, not the sim's 0.2, because at 0.2 docking (about +0.5 to +0.95 in all)
pays no more than a damaged fighter earns by spending itself on the enemy carrier instead:
each second of gauss on it pays up to +0.25, and dying costs only the hull it had left
(0.16 to 0.4 for a fighter). The baseline shows the fighters doing exactly that two times
in three. At 1.0 docking pays about +1.3 to +1.75, clearly more, and it is the size of the
go-to deadline pay (+1 to +3) that these followers already answer to.

The risk at 1.0: in a match a pilot could take damage on purpose to be recalled and paid.
Being recalled needs the scripted commander, a carrier and a hull under half; the damage
costs 0.01 a point (0.4 for a fighter's half hull, 1.6 for a gunship's) and the time out of
the fight costs the team. We watch it: `mission_docks.carrier_battle.recalls_per_match`
against the zero-shot 4.8, and the drills' damage taken. If recalls a match climb well
above that while win rates fall, the bonus is being farmed: lower it or pay it only in
drills.

## Measures

`eval.sh` on a checkpoint writes into `eval/<name>/` (`summary.py eval <dir>` prints it):

- (a) **Dock drills**, calm and threat, 128 a kind (`--kinds dock_calm,dock_threat`),
  each flown again with the order hidden: docked, shot down, out of time, docked of the
  survivors, came within 30 m, fly-throughs, time to dock, hull at the dock, by base and
  hull, and the lift.
- (b) **Recalls in matches**: the candidate on every strike slot of both sides of 256
  carrier battles and 256 station assaults, scripted commanders, which recall below half
  hull (`../2026-11-20-dock-repair/dock_eval.py`): recalls and docks a match, completion,
  failure modes.
- (c) **No regression**: the order drill eval (64 a kind, with the gate), the mission eval
  against the script (carrier battle and convoy, 192 a mission) and the fleet_v1 suite
  against the script (16 a roster, 256 matches).

`run.sh` runs these at the quick sizes (64 dock drills a kind, 96 matches, 32 order
drills, 96 a mission, 8 a roster; nice 19, 2 threads) on every 500th update of each arm
while it trains, and after the deadline at the full sizes on each arm's last checkpoint
and on both parents (`eval/parent600`, `eval/parent352`), then writes `report.md`
(`summary.py report`): every eval of each arm beside its parent, the gates, and the
training telemetry from `log.jsonl` (`drill_dock`, `mission_docks`).

## Gates

Each arm is judged alone, on its final checkpoint's full-size evals against its parent's.

1. **Calm dock drills:** docked >= 0.60, and the lift over the order hidden >= 0.40 (it
   docks because it was told to). Script 0.95; parents 0.01 to 0.02, lift 0.
2. **Threat dock drills:** docked >= 0.30. Script 0.58; parents 0.01 to 0.02.
3. **Scripted-commander missions:** recall completion >= 0.25 in carrier battles and
   >= 0.15 in station assaults (the station's are in the drills only). Script 0.61 and
   0.64; the live pilots 0.02 and 0.01.
4. **Order drills, no regression:** no order-drill bar (go-to arrival and lift, attack
   target hit, side and flip, defend more-on-named, side and flip) below the parent's by
   more than two standard errors of the difference.
5. **Win rates against the script, no regression:** carrier battle, convoy and the
   fleet_v1 suite (all classes; 1 v 1 to 4 v 4 reported) each no lower than the parent's
   by more than two standard errors of the difference.

An arm that passes all five is a candidate for the population: WAR and the live list come
after, as for any member (`docs/PILOT_TRAINING.md` §5), and the live page then shows
learned pilots docking. If an earlier periodic checkpoint passes at the quick sizes where
the final does not (the station-mix run's regression grew with training), evaluate it at
full size by hand (`eval.sh` without `QUICK`) before choosing.

## Budget

About 6 to 8 hours on Beast. At the station-mix run's 12.5 s an update (two arms, one a
GPU, 3 + 3 threads), 6.5 hours is about 1,900 updates an arm. The periodic evals are
nice 19 on 2 threads (Beast's side jobs cost the trainers little at that priority), about
10 minutes each at the quick sizes, four an arm. The final evals take about 40 minutes for
four checkpoints. Suggested: `DEADLINE` 6.5 hours after the start, so the report is ready
about 7.5 hours in.

## Beast-side setup

- Pull this branch and rebuild the extension in the checkout's venv:
  `uv run maturin develop -m crates/sim-py/Cargo.toml --release` (run.sh refuses an
  `rlf_sim` without the dock drills).
- The parents' weights under the checkout: `lab/runs/2026-11-14-goto-school/
  followers_school/checkpoints/ppo_bc_600.pt` and `lab/runs/2026-11-12-pilots-v8/
  followers_v8/checkpoints/ppo_bc_352.pt` (gitignored; rsync from the laptop if missing),
  and the pool seeds `followers_school`'s config lists (the station-mix run used the same
  list on Beast).
- The live stable's learned commanders are fetched by HTTPS into
  `~/.cache/rl-fighter/weights` (already there from earlier runs).

```bash
DEADLINE="<now + 6.5 h>" nohup setsid lab/runs/2026-11-20-dock-pilot/run.sh \
    > lab/runs/2026-11-20-dock-pilot/run_beast.out 2>&1 &
```

## Smoke (laptop, 2026-11-20)

`SMOKE=1 DATA_ROOT=/home/timg/code/rl-fighter nice -n 19 run.sh` (from a worktree; CPU,
1 + 1 threads): both arms widen 587 to 592 and train 2 updates (8 envs x 32 steps), the
periodic evals run on update 2 of each, then the final evals of both parents and both
last checkpoints (dock drills, recalls in carrier battles and station assaults, order
drills, missions and fleets against the script, at 4 to 12 a cell) and `report.md`, in 7
minutes, exit 0, no eval failed. Its gates fail 1 to 3 (two updates teach nothing) and
pass 4 and 5, as they should.
