# Sim v2: fighters that make passes instead of parking nose to nose

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

## What we did

**Sim v2** (details in `docs/SIM_SPEC.md` §0) lands nine changes at once, before any
training:

- **Lighter damping.** Ships coast and keep spinning longer, so momentum matters.
- **Throttle ramp.** Thrusters spool up over 0.2 s instead of switching on and off.
  This removes the jittery bang-bang look.
- **Reaction delay.** A pilot's command takes effect 2 ticks (67 ms) after it is
  chosen, so pilots behave like pilots, not servos. The delay is in the observation, so
  the learner can still plan around it.
- **Directional armour.** On the fighter, hits on the nose do half damage, hits on the
  flanks full damage and hits on the engines 1.5×. Getting on someone's tail now pays.
- **Shield-first hits.** Shots stop at the shield bubble, not at the hull.
- **A wider observation** (385 numbers instead of 204). It covers every other ship, the
  8 most threatening incoming shots, thruster levels and queued commands.
- **Exact action masks and shot credit**, so the learner credits the decision that
  fired a shot, not the tick the shot landed.
- **A new duel balance** (below).
- **The scripted fighter pilot extends after a pass** (below).

**The balance sweep.** `tools/duel_sweep.py` flies 200 scripted-vs-scripted 1v1
fighter duels per setting (a 450 m arena, 90 s limit, seeds 0–199), and patches the
weapon and hull numbers into a temporary copy of the assets. We swept the reaction
delay (0, 2 and 4 ticks) against gun damage, range and hull points, starting from the
plan's tuple: 3 dmg every 0.20 s, 220 m range, 200 m/s, 1° spread, 80 hp, fighter
armour on. The gate (spike plan §2.3) applies at the default delay of 2 ticks:

| gate | accept |
|---|---|
| median length | 450–1500 ticks (15–50 s) |
| mutual kills | < 10 % |
| time-limit endings | < 10 % |
| median passes (entries into gun range) | ≥ 3 |
| hull damage per pass | 10–40 % of hp |

## Results

**Round 1: the original pilot.** It came from the story prototype: point the nose at
the lead point, burn, and drop to 30 % throttle inside 60 m. No numbers passed the
gate.

| tuple (dmg / hp; 220 m, 0.20 s) | delay | median ticks (p25–p75) | mutual kill | time limit | passes | dmg/pass | hits nose / flank / engine | gate |
|---|---|---|---|---|---|---|---|---|
| 3 / 80 | 0 | 2700 (2700–2700) | 0 % | 91 % | 1 | 72 % | 99 / 1 / 0 % | fail |
| 3 / 80 | 2 | 1644 (1539–1811) | 2 % | 0 % | 1 | 98 % | 93 / 7 / 0 % | fail: length, passes, dmg/pass |
| 3 / 80 | 4 | 1458 (1343–1586) | 1.5 % | 0 % | 1 | 93 % | 74 / 25 / 1 % | fail: passes, dmg/pass |
| 4 / 80 | 2 | 1204 (1107–1316) | 4 % | 0 % | 1 | 96 % | 93 / 6 / 0 % | fail: passes, dmg/pass |
| 5 / 80 | 2 | 1006 (892–1125) | 1.5 % | 0 % | 1 | 95 % | 93 / 6 / 0 % | fail: passes, dmg/pass |
| 3 / 80, no armour | 2 | 935 (834–1080) | 6 % | 0 % | 1 | 96 % | (all 1×) | fail: passes, dmg/pass |

Duels did end in kills at delays of 2 and 4 ticks. But there was exactly one "pass" per
duel: after the first merge the two fighters never left gun range again. They hung
10–60 m apart, nose to nose, for 30–50 s. Ship collisions killed their speed at the
merge, the 30 % throttle kept them there, and each pilot turned straight back at the
other. Because each always faced the other, 93 % of hits landed on nose armour.
Armour then just halved the damage, and no setting of damage, range or hp could create
passes. The fix had to be in the pilot.

**The pilot change** (`crates/sim/src/scripted/fighter.rs`, SIM_SPEC §11 step 3). The
pilot keeps full thrust when its nose is on target. Once both ships have their backs
to each other, which is right after a merge, it flies straight out to 1.2 × gun range
before turning back. A pilot whose enemy sits on its tail, pointing at it, still turns
to fight; an earlier version that extended whenever the enemy was behind just flew
away in a straight line and got shot in the engines. The rule needs no new state, and
it reads the same `Match` state as before.

**Round 2: with the extending pilot** (200 duels per row; 220 m range unless noted):

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

Range hardly matters: the pilot extends to a multiple of the range, so every distance
scales with it.

**Chosen tuple:** gauss **5 dmg** every 0.20 s, 220 m range, 200 m/s, 1.0° spread;
fighter **80 hp**, armour as designed (nose 0.5×, flank 1×, engine 1.5×). This is the
plan's starting tuple with damage raised from 3 to 5. Damage was the first knob in the
plan's fallback order, and this is the smallest change that passes every gate at the
default delay. A typical duel at a delay of 2 ticks lasts 43 s and has three or four
attacking runs, each taking about a third of a ship's hull. Mutual kills are 1 % and
no duel times out. Neither side has an advantage (team 0 wins 52 % of decided duels).
It is written into `assets/weapons.yaml` and `assets/hulls/fighter/hull.yaml`, and the
golden determinism traces are regenerated as `SIM_VERSION` 2.

**Reaction time.** The delay changes the fight more than any weapon number does:

- **0 ticks (instant):** 20 % of duels hit the time limit. Without a delay the two
  scripted pilots often end up exact mirror images of each other (same bearings, same
  speeds, tick after tick). They hover nose to nose and trade glancing hits until the
  clock runs out. With any delay, small differences in timing break the symmetry.
- **2 ticks (default):** passes and kills as above.
- **4 ticks (133 ms):** hit rate drops from 0.60 to 0.54. Pilots overshoot more, so
  more hits land on flanks (21 %) and engines (3 %). Duels run longer (52 s median, 3 %
  time limit), just over the 50 s gate. 70 hp would bring a 4-tick default inside the
  gate (1340 ticks), if SIM_SPEC §15 q7 ever moves the default.

## What it looked like

- **Before:** two fighters meet head-on, bump, then hang 20 m apart, nose to nose,
  bobbing back and forth and firing into each other's nose armour until one dies.
- **After:** a classic joust. They close head-on and both fire, then pass, fly apart
  to about 260 m, turn and come back. When one pilot turns late, the other gets a few
  flank or tail shots. That is where the 1.5× engine hits come from.
- Nobody leaves the arena (outside-arena share 0.000–0.001 in every cell).

## What we learned

- The balance gate was designed to stop duels ending on the first pass. Without the
  pilot change the opposite happened: one endless pass. "Passes per duel" was what
  showed it; length and draw rate alone looked fine at a 2-tick delay with 4 dmg.
- With two pilots that both point at each other, directional armour mostly works as
  a 0.5× damage multiplier: 90 % of scripted hits are on the nose. The armour design
  is unchanged. It pays off only for a pilot that gets out of the joust and onto a
  tail, which is exactly what we hope the learner will find. It is also the obvious
  way for a learned policy to beat the script.
- The scripted pilot is now a better behaviour-cloning target for the spike. Its
  behaviour has phases (attack, extend, turn back) instead of one state, but it is
  still deterministic and reads only the simulation state.

## Next

The learnability spike (`lab/runs/2026-10-28-learnability-spike/plan.md`) is no
longer blocked. Its first step was this balance gate. Next: clone the scripted pilot,
then run PPO from the clone and from scratch, and see whether the clone learns to get
on a tail.

## Numbers

- Sweep: 36 cells × 200 duels (plus four trial variants of the pilot rule), about 1 s per
  cell on 12 threads. Reproduce with
  `uv run python tools/duel_sweep.py --n 200 --reaction-ticks 0 2 4 --damage 3 4 5 6`.
  Pass `--range` or `--hp` for the other rows. `--no-armour` strips the armour, and the
  round-1 rows need the old pilot (`18d69ec^`).
- Throughput (`tools/bench_env.py`, N = 256, random actions, obs on), on an idle
  laptop: **1v1 14,008 steps/s** (3.6 M match-ticks/s; target 6,000), **2v2
  fighter+strafer 8,114** (target 4,000), **single-thread 1v1 3,200** (target 600).
  The same benchmark inside `RLF_BENCH=1 scripts/check.sh`, right after the builds
  (load average about 7), measured 6,623 / 3,735 / 2,175, still above every floor.
- Gates: `scripts/check.sh` (native, wasip1 under wasmtime, wasm-pack, node smoke
  against the new golden ends, maturin + pytest) and the full `pytest tests/` (174
  tests) pass.
