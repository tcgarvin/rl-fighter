# Sim v2: fighters that make passes instead of parking nose to nose

<!-- summary: Before we try to teach a neural network to fly a fighter, the game it learns in has to produce fights worth learning: duels that last a while, have several attacking runs, and rarely end with both ships dead or the clock run out. Under the new rules our hand-written pilot made one run and then hung nose to nose with its enemy, and no weapon numbers could change that. Once the pilot flew out and turned back after each run, raising gun damage from 3 to 5 gave duels of about 43 seconds with three or four runs. -->

| | |
|---|---|
| Date | 2026-10-28 |
| Run dir | `lab/runs/2026-10-28-sim-v2/` |
| Branch | `m1-sim` |
| Commits | `18d69ec` (sweep tool, scripted pilot change), `019c830` (SIM_VERSION 2, balance, golden traces) |
| SIM_VERSION | 2 |
| Verdict | **PASS** on the duel-balance gate at the default reaction delay, after one change to the scripted pilot |

## What we asked

Before we try to teach a neural network to fly a fighter, the simulation it learns in
has to produce fights worth learning: duels that last a while, have several attacking
runs, and rarely end in a tie. Does the new version of the simulator do that with the
planned weapon numbers, and if not, what is the smallest change that fixes it?

The answer was no, at first. With the new rules our scripted pilot (a hand-written,
rule-based pilot, flown on both sides in these tests) made one attacking run and then
hung nose to nose with its enemy until one of them died. No setting of damage, range or
hit points changed that. Once the pilot was changed to fly out and turn back after each
run, raising the gun's damage per shot from 3 to 5 gave duels that met every target we
had set.

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural
network that learns to fly by trial and error (reinforcement learning). The game runs
in a simulation, a program that plays out the physics and rules of thousands of
matches at once, far faster than real time, so a network can practise. `SIM_VERSION`
is the version number of those rules. This entry is the first in the notebook, and no
network had been trained yet.

The next step was [the learnability spike](../2026-10-28-learnability-spike/results.md),
the project's first training run: could a network learn to fly a fighter at all? Its
[plan](../2026-10-28-learnability-spike/plan.md) (§2.1) had found that under the first
version of the rules a scripted duel ended in about 5 seconds, on the first head-on
pass, and half the time both ships died at once. A fight that short gives a learner
almost nothing to learn from: one burst of reward a match, and about two seconds in
which the trigger matters. So the rules had to produce real fights first.

## What we did

**Sim v2**, version 2 of the game's rules (details in `docs/SIM_SPEC.md` §0), lands
nine changes at once, before any training:

- **Lighter damping.** Damping is the artificial drag that slows a ship and its spin.
  With less of it, ships coast and keep spinning longer, so momentum matters.
- **Throttle ramp.** Thrusters spool up over 0.2 s instead of switching on and off.
  This removes the jittery bang-bang (full on, full off) look.
- **Reaction delay.** The simulation advances in ticks, 30 a second. A pilot's command
  now takes effect 2 ticks (67 ms) after it is chosen, so pilots behave like pilots,
  not servos. The pilot can see its own queued commands, so a learner can still plan
  around the delay.
- **Directional armour.** On the fighter, hits on the nose do half damage, hits on the
  flanks full damage and hits on the engines 1.5×. Getting on someone's tail now pays.
- **Shield-first hits.** Shots stop at the shield bubble (a ship's protective energy
  field), not at the hull inside it. While its shield is up, a ship is a bigger target:
  a shot that would have passed just beside the hull now hits the bubble, at the point
  where it crossed.
- **A wider observation** (385 numbers instead of 204). The observation is the list of
  numbers a pilot sees each moment. It now covers every other ship, the 8 most
  threatening incoming shots, thruster levels and queued commands.
- **Exact action masks and shot credit.** These are bookkeeping for learning. A mask
  marks the outputs that have no effect at a given moment, so training ignores them.
  Shot credit means the learner credits the decision that fired a shot, not the tick
  the shot landed.
- **A new duel balance** (below).
- **The scripted fighter pilot extends after a pass**: it flies straight on, out of
  gun range, before turning back (below).

**The balance sweep.** `tools/duel_sweep.py` flies 200 scripted-vs-scripted 1v1
fighter duels per setting (one fighter against one, both flown by the script; a 450 m
arena, 90 s limit, seeds 0–199, the random numbers that set up each duel, so every
setting is tried on the same 200 starts). It patches the weapon and hull numbers into
a temporary copy of the game's data files. We swept the reaction delay (0, 2 and 4
ticks) against gun damage, range and hull points, starting from the plan's set of
numbers (the "tuple"): the gun does 3 damage (dmg) a shot, fires every 0.20 s, reaches
220 m, its shots fly at 200 m/s with 1° of spread, and a fighter has 80 hit points
(hp), with armour on. The gate, a set of pass marks fixed in advance
([the learnability spike's plan](../2026-10-28-learnability-spike/plan.md) §2.3),
applies at the default delay of 2 ticks:

| gate | accept |
|---|---|
| median length | 450–1500 ticks (15–50 s) |
| mutual kills | < 10 % |
| time-limit endings | < 10 % |
| median passes (entries into gun range) | ≥ 3 |
| hull damage per pass | 10–40 % of hp |

A pass is one attacking run: the two ships come into gun range, fire, and go past each
other. A mutual kill is a duel in which both ships die on the same tick, a draw.

## Results

**Round 1: the original pilot.** It came from the story prototype (`prototypes/story/`,
an earlier scripted demo of the game): point the nose at the lead point (where the
enemy will be when the shot arrives), burn, and drop to 30 % throttle inside 60 m. No
numbers passed the gate.

Each row below is 200 duels with one setting. The first column is the gun's damage per
shot and the fighter's hp. Delay is the reaction delay in ticks. Median ticks is the
typical duel length (1500 ticks is 50 s), with the middle half of duels in brackets
(p25–p75). Mutual kill and time limit are the shares of duels that ended with both
ships dead or with the 90 s clock run out. Passes is the median number of passes per
duel, dmg/pass the hull damage one pass does as a share of hp, and the hits column says
where on the target the hits landed. The last column names the gates a row missed.

| tuple (dmg / hp; 220 m, 0.20 s) | delay | median ticks (p25–p75) | mutual kill | time limit | passes | dmg/pass | hits nose / flank / engine | gate |
|---|---|---|---|---|---|---|---|---|
| 3 / 80 | 0 | 2700 (2700–2700) | 0 % | 91 % | 1 | 72 % | 99 / 1 / 0 % | fail |
| 3 / 80 | 2 | 1644 (1539–1811) | 2 % | 0 % | 1 | 98 % | 93 / 7 / 0 % | fail: length, passes, dmg/pass |
| 3 / 80 | 4 | 1458 (1343–1586) | 1.5 % | 0 % | 1 | 93 % | 74 / 25 / 1 % | fail: passes, dmg/pass |
| 4 / 80 | 2 | 1204 (1107–1316) | 4 % | 0 % | 1 | 96 % | 93 / 6 / 0 % | fail: passes, dmg/pass |
| 5 / 80 | 2 | 1006 (892–1125) | 1.5 % | 0 % | 1 | 95 % | 93 / 6 / 0 % | fail: passes, dmg/pass |
| 3 / 80, no armour | 2 | 935 (834–1080) | 6 % | 0 % | 1 | 96 % | (all 1×) | fail: passes, dmg/pass |

Duels did end in kills at delays of 2 and 4 ticks. But there was exactly one "pass" per
duel: after the first merge (the moment the two ships meet and cross) the two fighters
never left gun range again. They hung 10–60 m apart, nose to nose, for 30–50 s. Ship
collisions killed their speed at the merge, the 30 % throttle kept them there, and each
pilot turned straight back at the other. Because each always faced the other, 93 % of
hits landed on nose armour. Armour then just halved the damage, and no setting of
damage, range or hp could create passes. The fix had to be in the pilot.

<!-- figure-idea: an overhead animation of two fighters, before and after the pilot change: before, they meet head-on and hang nose to nose; after, they joust, fly apart to about 1.2 times gun range, turn and come back. It shows what "a pass" means and why one endless pass failed the gate. -->

**The pilot change** (`crates/sim/src/scripted/fighter.rs`, SIM_SPEC §11 step 3). The
pilot keeps full thrust when its nose is on target. Once both ships have their backs
to each other, which is right after a merge, it flies straight out to 1.2 × gun range
before turning back. A pilot whose enemy sits on its tail, pointing at it, still turns
to fight. An earlier version that extended whenever the enemy was behind just flew
away in a straight line and got shot in the engines. The rule gives the pilot nothing
new to remember, and it reads the same game state (`Match`) as before, so it stays a
simple, predictable pilot for a network to copy.

**Round 2: with the extending pilot** (200 duels per row; 220 m range unless noted).
The columns are as above, plus two. Team-0 wins is the share of decided duels won by
team 0, one of the two sides. With the same pilot on both sides, 0.50 means neither
side has an edge. Hit rate is the share of shots that hit. The gate applies only at a delay of 2
ticks, so the rows at 0 and 4 ticks are marked "(not gated)" or show in brackets what
the gate would have said. The bold row is the setting we chose.

| tuple (dmg / hp) | delay | median ticks (p25–p75) | mutual kill | time limit | team-0 wins | passes | dmg/pass | hit rate | hits nose / flank / engine | gate |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 / 80 | 0 | 2700 (2700–2700) | 0 % | 98.5 % | – | 1 | 72 % | 0.59 | 99 / 1 / 0 % | fail |
| 3 / 80 | 2 | 2231 (2049–2416) | 0.5 % | 5 % | 0.51 | 4 | 23 % | 0.60 | 90 / 9 / 1 % | fail: length |
| 3 / 80 | 4 | 2700 (2334–2700) | 0 % | 50.5 % | 0.41 | 5 | 17 % | 0.54 | 76 / 21 / 3 % | fail |
| 4 / 80 | 2 | 1626 (1481–1800) | 1 % | 0 % | 0.50 | 3 | 30 % | 0.60 | 90 / 9 / 1 % | fail: length |
| 4 / 80 | 4 | 1888 (1708–2183) | 1.5 % | 7 % | 0.52 | 4 | 21 % | 0.54 | 76 / 22 / 3 % | fail: length |
| **5 / 80** | 0 | 2162 (1796–2610) | 3 % | 20.5 % | 0.53 | 1 | 95 % | 0.57 | 99 / 1 / 0 % | (not gated) |
| **5 / 80** | **2** | **1296 (1174–1502)** | **1 %** | **0 %** | **0.52** | **3** | **32 %** | **0.60** | **91 / 9 / 1 %** | **pass** |
| **5 / 80** | 4 | 1571 (1369–1769) | 0.5 % | 3 % | 0.51 | 4 | 25 % | 0.54 | 76 / 21 / 3 % | (fail: length) |
| 6 / 80 | 2 | 1102 (968–1220) | 3.5 % | 0 % | 0.52 | 2 | 42 % | 0.60 | 91 / 9 / 1 % | fail: passes, dmg/pass |
| 6 / 80 | 4 | 1272 (1089–1523) | 3.5 % | 0.5 % | 0.51 | 3 | 29 % | 0.54 | 75 / 22 / 3 % | (pass) |
| 5 / 80, 200 m | 2 | 1334 (1200–1484) | 3.5 % | 0 % | 0.52 | 3 | 32 % | 0.60 | 91 / 9 / 1 % | pass |
| 5 / 80, 260 m | 2 | 1274 (1173–1418) | 3 % | 0 % | 0.53 | 3 | 32 % | 0.60 | 90 / 9 / 1 % | pass |
| 5 / 70 | 2 | 1154 (1025–1298) | 2.5 % | 0 % | 0.50 | 3 | 33 % | 0.60 | 91 / 8 / 1 % | pass |
| 5 / 70 | 4 | 1340 (1116–1632) | 4.5 % | 0 % | 0.53 | 3 | 29 % | 0.54 | 75 / 22 / 3 % | (pass) |
| 5 / 90 | 2 | 1470 (1332–1632) | 1 % | 0 % | 0.46 | 3 | 31 % | 0.61 | 91 / 9 / 1 % | pass |

Range hardly matters (the 200 m and 260 m rows): the pilot extends to a multiple of the
range, so every distance scales with it.

**Chosen tuple:** gauss (the fighter's gun) **5 dmg** every 0.20 s, 220 m range,
200 m/s, 1.0° spread; fighter **80 hp**, armour as designed (nose 0.5×, flank 1×,
engine 1.5×). This is the plan's starting tuple with damage raised from 3 to 5. The plan
said what to adjust, in order, if a gate failed: damage first, then range, then hp.
Damage was enough, and this is the smallest change that
passes every gate at the default delay. A typical duel at a delay of 2 ticks lasts 43 s
and has three or four attacking runs, each taking about a third of a ship's hull.
Mutual kills are 1 % and no duel times out. Neither side has an advantage (team 0 wins
52 % of decided duels). It is written into `assets/weapons.yaml` and
`assets/hulls/fighter/hull.yaml`, and the golden determinism traces (recorded
reference matches that check the simulation still gives exactly the same results on
every machine) are regenerated as `SIM_VERSION` 2.

**Reaction time.** The delay changes the fight more than any weapon number does:

- **0 ticks (instant):** 20 % of duels hit the time limit. Without a delay the two
  scripted pilots often end up exact mirror images of each other (same bearings, same
  speeds, tick after tick). They hover nose to nose and trade glancing hits until the
  clock runs out. With any delay, small differences in timing break the symmetry.
- **2 ticks (default):** passes and kills as above.
- **4 ticks (133 ms):** hit rate drops from 0.60 to 0.54. Pilots overshoot more, so
  more hits land on flanks (21 %) and engines (3 %). Duels run longer (52 s median, 3 %
  time limit), just over the 50 s gate. 70 hp would bring a 4-tick default inside the
  gate (1340 ticks), if the default delay ever moves (an open question, SIM_SPEC §15
  q7).

## What it looked like

- **Before:** two fighters meet head-on, bump, then hang 20 m apart, nose to nose,
  bobbing back and forth and firing into each other's nose armour until one dies.
- **After:** a classic joust. They close head-on and both fire, then pass, fly apart
  to about 260 m, turn and come back. When one pilot turns late, the other gets a few
  flank or tail shots. That is where the 1.5× engine hits come from.
- Nobody leaves the arena (outside-arena share 0.000–0.001 in every cell).

## What we learned

- The balance gate was designed to stop duels ending on the first pass, as they did
  under the first version of the rules. Without the pilot change the opposite
  happened: one endless pass. "Passes per duel" was what showed it. Length and draw
  rate alone looked fine at a 2-tick delay with 4 dmg.
- With two pilots that both point at each other, directional armour mostly works as
  a 0.5× damage multiplier: 90 % of scripted hits are on the nose. The armour design
  is unchanged. It pays off only for a pilot that gets out of the joust and onto a
  tail, which is exactly what we hope the learner will find. It is also the obvious
  way for a learned pilot to beat the script.
- The scripted pilot is now a better teacher for behaviour cloning (training a network
  to copy the script's choices), the spike's first step. Its behaviour has phases
  (attack, extend, turn back) instead of one state, but it is still deterministic (the
  same situation always gets the same response) and reads only the simulation state.

## Next

[The learnability spike](../2026-10-28-learnability-spike/results.md)
(`lab/runs/2026-10-28-learnability-spike/plan.md`) is no longer blocked. Its first
step was this balance gate. Next: train a network to copy the scripted pilot, then
improve the copy by trial-and-error training (PPO), beside a second network trained by
trial and error from nothing, and see whether the copy learns to get on a tail.

## Numbers

How the sweep was run and how fast the simulation is, for anyone reproducing it. A
reader can skip this section.

- Sweep: 36 cells × 200 duels (plus four trial variants of the pilot rule), about 1 s per
  cell on 12 threads. Reproduce with
  `uv run python tools/duel_sweep.py --n 200 --reaction-ticks 0 2 4 --damage 3 4 5 6`.
  Pass `--range` or `--hp` for the other rows. `--no-armour` strips the armour, and the
  round-1 rows need the old pilot (`18d69ec^`).
- Throughput (`tools/bench_env.py`, N = 256 matches at once, random actions, obs on;
  a step advances every match by one tick), on an idle laptop: **1v1 14,008 steps/s**
  (3.6 M match-ticks/s; target 6,000), **2v2 fighter+strafer 8,114** (target 4,000),
  **single-thread 1v1 3,200** (target 600). The same benchmark inside
  `RLF_BENCH=1 scripts/check.sh`, right after the builds (load average about 7),
  measured 6,623 / 3,735 / 2,175, still above every floor.
- Gates: `scripts/check.sh` (native, wasip1 under wasmtime, wasm-pack, node smoke
  against the new golden ends, maturin + pytest) and the full `pytest tests/` (174
  tests) pass.
