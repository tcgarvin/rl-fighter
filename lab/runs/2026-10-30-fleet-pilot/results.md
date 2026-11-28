# Fleet pilot v1: one network flies every hull and beats the scripts, mostly by coasting

<!-- summary: Until now our learned pilot only knew one-on-one fighter duels. We trained one network to fly all three small ship types in mixed fleets of one to four ships a side, first by copying the hand-written pilots and then by trial and error. The best version wins 0.889 of fleet matches against the hand-written pilots and now flies every ship on the live page. It wins mostly by coasting: its fighters barely use their engines, which broke one of our own health checks until the owner waived it. -->

The question was whether one network can fly every kind of small ship, fighters,
strafers and gunships, in mixed fights of one to four ships a side, and beat our
hand-written pilots there. It can. The pilot we promoted, `2026-10-30-fleet-pilot-v1`
(often just "fleet pilot v1" or "v1" in later entries), wins 0.889 of fleet matches
against the hand-written pilots, and with every ship type it matches or beats them on
damage dealt and survival. The surprise is how: its fighters barely use their
engines. They mostly sit, turn and shoot, which makes for slower, more static fights
to watch on the live page.

Run 2026-10-30, plan: `plan.md` (pass marks fixed in §5 before any learned fleet
pilot was tested). **Promoted: warm arm, PPO update 400, as `2026-10-30-fleet-pilot-v1`.**
(The warm arm is the version of this run that started from the earlier duel pilot's
weights, and update 400 is the point in its trial-and-error training, PPO, at which it
was saved.) It now flies every
ship on the live page, in mixed fleets. The v3 fighter champion, the earlier duel
pilot, can still be watched at `/?champion=2026-10-29-v3-fighter`.

Verdict: **PARTIAL**. The pilot won, but it met the pass marks set before the run
only after the owner waived one of them, the mark on how much the fighters use their
engines. "Verdict in detail", below the results, gives the full reckoning.

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural
network that learned to fly by trial and error. Each ship type (hull) also has a
script, a hand-written rule-based pilot, which is the yardstick learned pilots are
measured against. Before this run, every learned pilot was a fighter duellist.
[The first training run](../2026-10-28-learnability-spike/results.md) found a recipe
that beat the fighter script in every duel: copy the script, correct the copy, then
train by trial and error. [The collision-damage run](../2026-10-29-collision-damage/results.md)
retrained that pilot after crashes started to do damage, under version 3 of the
game's rules. That pilot, `2026-10-29-v3-fighter`, is "the v3 duel champion" below.

The site's front page (the live page) was meant to show mixed fleets, with every ship
flown by the same network. The duel champion could not do that: flying every ship
against the scripts, it won 0.165 of fleet matches ([the plan](plan.md) §2). So this
run asked whether the duel recipe carries over to three ship types and bigger fights.

## What ran

- Behaviour cloning (BC: training the network to copy the scripts' choices) and DAgger
  (a correction step: the copy flies, and the scripts say what they would have done in
  the situations it gets into), on the three scripted pilots, one per ship type. This
  ran in two arms, two versions of the run side by side: *fresh* (new, random weights)
  and *warm* (started from the v3 duel champion). Then 600 PPO updates per arm with a
  decaying pull toward the scripts. PPO is our trial-and-error training method, an
  update is one round of play and adjustment, and the script pull is an extra
  training term that pulls the pilot's choices toward the scripts', fading to nothing.
  Candidates: each arm's DAgger best and PPO updates 200, 400 and 600.
- The plan's three hypotheses. H1: this recipe gives a fleet pilot that meets all four
  gates (the pass marks below). H2: the warm arm beats the fresh one. H0, the null: one
  shared network cannot serve three kinds of ship, and some ship type stays below its
  script.
- A candidate's name is its arm and the update it was saved at: warm_400 is the warm
  arm at update 400, and warm_dagger the warm arm's best DAgger round, before any
  trial-and-error training.
- PPO was stopped cleanly at updates 307/308 (the owner needed the machine) and
  resumed from those checkpoints (saved copies). The run is not bit-identical to an
  uninterrupted one.
- Timeline from `run.out`: DAgger 19:30–19:54, PPO 19:54 to 23:46 (with the
  break), gate evals 23:46–23:57.

<div data-figure="diagram" data-name="pilot" data-caption="This run asked whether one network could fly the three hulls of the time: fighter, strafer and gunship. The order numbers came in rules version 5 and the bomber in version 9, after this run."></div>

## Gates (fleet suite `fleet_v1`, 1024 matches; duels n = 512)

The gates are pass marks fixed in [the plan](plan.md) (§5) before any learned fleet
pilot was tested. The fleet suite is a fixed set of 16 rosters (who flies which ships
on each side): one-on-one mirrors of each ship type, 2v2, 3v3, 4v4, uneven 2v3 sides,
and drafts, where each side buys ships from a fixed budget. Each roster is played 64
times, with the learned pilot on each side half the time. The four gates are:

- **G1 strength:** win at least 0.60 of fleet matches against the scripts (a draw
  counts half), and at least 0.45 in every roster class (a group of similar rosters:
  the 1v1s, the 2v2s, the 3v3s, the uneven 2v3s, the drafts and the 4v4s).
- **G2 no hull left behind:** with each ship type, deal at least 0.9 of the script's
  damage per ship, and survive at least as often.
- **G3 health:** engine duty within bounds for every ship type (engine duty is the
  average thrust level of a ship's strongest thruster, from 0 to 1), little time
  outside the arena, few draws, few broken or stuck ships, and not many more time-outs
  than the scripts.
- **G4 the duel:** win at least 0.35 of fighter duels against the v3 duel champion,
  and at least 0.80 against the script.

Every table below is copied by script from `eval/gates.md` (written by `gates.py`) or
from the eval reports in `eval/`. G3 below is without the waived engine-duty checks.
In the first table, ✓ or ✗ says whether a candidate met each gate and "all" whether it
met every one. "Win vs script" is its fleet win rate, and "duel vs champ" its win rate
in fighter duels against the v3 duel champion (0.5 is an even fight in both).

| candidate | G1 | G2 | G3 | G4 | all | win vs script | duel vs champ |
|---|---|---|---|---|---|---|---|
| fresh_200 | ✗ | ✗ | ✓ | ✗ | ✗ | 0.333 | 0.025 |
| fresh_400 | ✓ | ✓ | ✓ | ✗ | ✗ | 0.849 | 0.050 |
| fresh_600 | ✓ | ✓ | ✓ | ✗ | ✗ | 0.865 | 0.250 |
| fresh_dagger | ✗ | ✗ | ✓ | ✗ | ✗ | 0.159 | 0.025 |
| warm_200 | ✗ | ✗ | ✓ | ✗ | ✗ | 0.428 | 0.010 |
| warm_400 | ✓ | ✓ | ✓ | ✓ | ✓ | 0.889 | 0.453 |
| warm_600 | ✓ | ✗ | ✓ | ✗ | ✗ | 0.898 | 0.291 |
| warm_dagger | ✗ | ✗ | ✓ | ✗ | ✗ | 0.112 | 0.015 |

Engine duty per hull (✗ marks the original 0.15–0.95 bound; the script's duty is
0.39 / 0.43 / 0.53 for fighter / strafer / gunship):

| candidate | fighter engine duty | strafer engine duty | gunship engine duty |
|---|---|---|---|
| fresh_200 | 0.348 | 0.304 | 0.536 |
| fresh_400 | 0.151 | 0.251 | 0.515 |
| fresh_600 | 0.113 ✗ | 0.344 | 0.396 |
| fresh_dagger | 0.344 | 0.312 | 0.545 |
| warm_200 | 0.350 | 0.238 | 0.530 |
| warm_400 | 0.130 ✗ | 0.224 | 0.442 |
| warm_600 | 0.124 ✗ | 0.222 | 0.448 |
| warm_dagger | 0.345 | 0.324 | 0.528 |

- **warm_400 is the only candidate that passes.** It wins 0.889 of fleet matches
  against the scripts, and every roster class at 0.74 or better. Every hull matches
  or beats its script on damage and survival (G2). It wins every duel against the
  script and 0.453 of duels against the v3 champion.
- **PPO taught the fighters to coast.** Every DAgger checkpoint and every update-200
  checkpoint flies fighters at about 0.35 duty, close to the script's 0.39. By
  update 400 both arms are at 0.13–0.15. In the duel, warm_400 uses its engine
  3.6 % of the time against the champion's 60 %. It mostly sits, turns and shoots,
  and that beats both the scripts and the champion. Expect slower, more static
  fighter play on the live page than the v3 champion's.
- **H2 holds: warm beats fresh.** At update 400, warm wins 0.453 of duels against
  the champion, while fresh wins 0.050. The fresh arm never learned to duel.
- **H0 does not hold.** One shared network (an MLP, the simplest kind) serves all
  three control schemes. warm_400 passes G2 for fighter, strafer and gunship, so there
  is no case for splitting a hull class off and giving it a network of its own.
- warm_600 is stronger in fleets (0.898) but slips on gunship damage (0.878 of the
  script's) and in the duel (0.291).

<!-- figure-idea: a chart of fighter engine duty against training update for both arms (about 0.35 for every DAgger and update-200 checkpoint, 0.13 to 0.15 by update 400), with the script's 0.39 and the 0.15 gate floor marked. It shows the coasting habit appearing during trial-and-error training. -->

warm_400 against the scripts, per hull (side a is the pilot), from
`eval/warm_400_fleet_vs_script.md`. Side b is the scripts. Numbers are per ship per
match: "ships" is how many ship-matches the row covers; dmg is hull damage dealt
(after armour) and shield dmg damage dealt to shields; survival is the share alive at
the end; shots are shots fired; engage is the share of time an enemy is within 1.2
times the ship's longest weapon range; outside is the share of time outside the
arena; engine is engine duty; passes are entries into gun range of the nearest enemy;
crash dmg is damage taken in collisions; and fire is the share of decisions that pull
a trigger.

| side | hull | ships | dmg | shield dmg | survival | hit rate | shots | engage | outside | engine | passes | crash dmg | fire |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| a | fighter | 1056 | 84.4 | 38.4 | 0.60 | 0.373 | 72.7 | 0.88 | 0.0010 | 0.13 | 1.30 | 1.6 | 0.486 |
| a | gunship | 448 | 218.4 | 58.4 | 0.95 | 0.287 | 237.9 | 0.79 | 0.0000 | 0.44 | 1.52 | 0.5 | 0.594 |
| a | strafer | 928 | 96.3 | 40.3 | 0.65 | 0.171 | 285.3 | 0.71 | 0.0120 | 0.22 | 1.86 | 0.1 | 0.449 |
| a | all | 2432 | 113.6 | 42.8 | 0.69 | 0.233 | 184.2 | 0.80 | 0.0054 | 0.23 | 1.56 | 0.8 | 0.492 |
| b | fighter | 1056 | 51.1 | 31.8 | 0.16 | 0.595 | 31.2 | 0.87 | 0.0000 | 0.33 | 1.50 | 1.7 | 0.141 |
| b | gunship | 448 | 72.4 | 57.5 | 0.09 | 0.195 | 170.2 | 0.89 | 0.0000 | 0.35 | 1.24 | 0.4 | 0.346 |
| b | strafer | 928 | 27.0 | 21.8 | 0.04 | 0.288 | 61.8 | 0.81 | 0.0000 | 0.41 | 1.68 | 0.4 | 0.098 |
| b | all | 2432 | 45.8 | 32.7 | 0.10 | 0.306 | 68.5 | 0.85 | 0.0000 | 0.36 | 1.52 | 1.0 | 0.178 |

## Verdict in detail

H1 is met only with the engine-duty bound waived, H2 holds (warm beats fresh), and H0
is rejected (one network serves every hull), meaning the pessimistic case turned out
false.

**The gates were amended after they ran.** Under the original gates (plan §5) no
candidate passed. warm_400 failed only G3's fighter engine-duty floor (0.130 against
0.15). The owner waived the engine-duty bound: if flying slowly is the strongest
strategy, it ships, and the sim or the reward shaping is what gets discussed. See the
amendment in plan.md §5.

## To discuss: why coasting wins

- **Is it the sim?** It could be the speed cap, the turn rate relative to the gun
  arcs, or projectile speed against the arena size. If a still ship that only turns
  is hard enough to hit and hits well itself, motion buys little.
- **Is it the reward?** Damage-only shaping (during a match, the reward is only for
  damage dealt and taken) plus a script pull that decays to zero gives no reason to move once the
  shots line up.
- A pass mark on the number of attacking runs (passes) a duel has, or on how long it
  lasts, would measure "dull" directly, rather than through engine duty.
  [The first training run](../2026-10-28-learnability-spike/results.md) put such a
  "watchability gate" on its to-do list.

## Next

- Rerun from warm only (warm clearly beats fresh), with checkpoints every 50
  updates and gate evals on each, to see where the duty collapses.
