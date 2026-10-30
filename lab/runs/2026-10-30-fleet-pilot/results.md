# Fleet pilot v1: one network flies every hull and beats the scripts, mostly by coasting

Run 2026-10-30, plan: `plan.md` (gates fixed in §5 before any learned fleet policy was
evaluated). **Promoted: warm arm, PPO update 400, as `2026-10-30-fleet-pilot-v1`.**
It now flies every ship on the live page, in mixed fleets. The v3 fighter champion
can still be watched at `/?champion=2026-10-29-v3-fighter`.

**The gates were amended after they ran.** Under the original §5 no candidate
passed. warm_400 failed only G3's fighter engine-duty floor (0.130 against 0.15).
The user waived the engine-duty bound: if flying slowly is the strongest strategy, it
ships, and the sim or the reward shaping is what gets discussed. See the amendment
in plan.md §5.

## What ran

- BC + DAgger on the three scripted pilots in two arms: *fresh* (new weights) and
  *warm* (started from the v3 duel champion), then 600 PPO updates per arm with a
  decaying pull toward the scripts. Candidates: each arm's DAgger best and PPO
  updates 200, 400 and 600.
- PPO was stopped cleanly at updates 307/308 (the user needed the machine) and
  resumed from those checkpoints. The run is not bit-identical to an uninterrupted
  one.
- Timeline from `run.out`: DAgger 19:30–19:54, PPO 19:54 to 23:46 (with the
  break), gate evals 23:46–23:57.

## Gates (fleet suite `fleet_v1`, 1024 matches; duels n = 512)

Every table below is copied by script from `eval/gates.md` (written by `gates.py`) or
from the eval reports in `eval/`. G3 below is without the waived engine-duty checks.

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
0.39 / 0.43 / 0.53):

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
- **H0 does not hold.** One shared MLP serves all three control schemes. warm_400
  passes G2 for fighter, strafer and gunship, so there is no case for splitting a
  hull class off.
- warm_600 is stronger in fleets (0.898) but slips on gunship damage (0.878 of the
  script's) and in the duel (0.291).

warm_400 against the scripts, per hull (side a is the pilot), from
`eval/warm_400_fleet_vs_script.md`:

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
## To discuss: why coasting wins

- **Is it the sim?** It could be the speed cap, the turn rate relative to the gun
  arcs, or projectile speed against the arena size. If a still ship that only turns
  is hard enough to hit and hits well itself, motion buys little.
- **Is it the reward?** Damage-only shaping plus a script pull that decays to zero
  gives no reason to move once the shots line up.
- A gate on passes or duel length (the backlog's watchability gate) would measure
  "dull" directly, rather than through engine duty.

## Next

- Rerun from warm only (warm clearly beats fresh), with checkpoints every 50
  updates and gate evals on each, to see where the duty collapses.
