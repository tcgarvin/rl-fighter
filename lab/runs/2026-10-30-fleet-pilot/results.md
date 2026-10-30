# Fleet pilot v1: one network can fly every hull and beat the scripts, but PPO taught its fighters to coast

Run 2026-10-30, plan: `plan.md` (gates fixed in §5 before any learned fleet policy was
evaluated). **Nothing promoted.** No candidate passes all four gates, so per §5 the
live page keeps fighter-only fleets with the v3 champion (`2026-10-29-v3-fighter`).

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
from the eval reports in `eval/`.

| candidate | G1 | G2 | G3 | G4 | all | win vs script | duel vs champ |
|---|---|---|---|---|---|---|---|
| fresh_200 | ✗ | ✗ | ✓ | ✗ | ✗ | 0.333 | 0.025 |
| fresh_400 | ✓ | ✓ | ✓ | ✗ | ✗ | 0.849 | 0.050 |
| fresh_600 | ✓ | ✓ | ✗ | ✗ | ✗ | 0.865 | 0.250 |
| fresh_dagger | ✗ | ✗ | ✓ | ✗ | ✗ | 0.159 | 0.025 |
| warm_200 | ✗ | ✗ | ✓ | ✗ | ✗ | 0.428 | 0.010 |
| warm_400 | ✓ | ✓ | ✗ | ✓ | ✗ | 0.889 | 0.453 |
| warm_600 | ✓ | ✗ | ✗ | ✗ | ✗ | 0.898 | 0.291 |
| warm_dagger | ✗ | ✗ | ✓ | ✗ | ✗ | 0.112 | 0.015 |

Engine duty per hull (G3 needs 0.15–0.95; the script's are 0.39 / 0.43 / 0.53):

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

- **warm_400 is one check from passing.** It wins 0.889 of fleet matches against
  the scripts, and every roster class at 0.74 or better. Every hull matches or
  beats its script on damage and survival (G2), and it wins 0.453 of duels against
  the v3 champion. It fails only on fighter engine duty, 0.130 against a floor of
  0.15.
- **PPO is what made the fighters coast.** Every DAgger checkpoint and every
  update-200 checkpoint flies fighters at about 0.35 duty, close to the script's
  0.39. By update 400 both arms are at 0.13–0.15. In the duel, warm_400 uses its
  engine 3.6 % of the time against the champion's 60 %. It sits still, turns and
  shoots, and that works against both the scripts and the champion. It is the
  dull, static fight the duty gate exists to keep off the live page, so the gate
  stands.
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
## Next

- **Make coasting cost something in PPO rather than only rejecting it at the gate.**
  Options: keep the script pull from decaying to zero for fighters, or add a gate-like
  engine-duty term to the reward. Either needs to be fixed in a plan before the
  rerun.
- **Rerun from warm_200 or warm_400** with that change; warm clearly beats fresh, so
  drop the fresh arm and spend its compute on the warm one.
- Update 400 reached the fleet skill and the coasting together. Checkpointing every
  50 updates, with gate evals on each, would show where the duty collapses.
