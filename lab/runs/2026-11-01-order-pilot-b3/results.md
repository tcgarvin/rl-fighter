# Order pilot B3: the pull still costs the fight; the reward alone barely moves

Run 2026-10-31 (dir dated for the night it was planned for), M3 stage B3, `SIM_VERSION`
6, plan: `plan.md` (gates, teacher-first bounds and pick rule fixed before any candidate
was evaluated; new-input step amended 10× → 3× before launch). **Nothing promoted.**
Fleet pilot v1 stays the champion.

<!-- summary: With the redesigned orders (attack, defend, go-to) and threat inputs, a script pull even on transit rows only taught following but again wrecked combat (2 % of carrier battles won against v1); without the pull the pilot kept its strength but followed orders only a little better than with them hidden. -->

Verdict: **FAIL.** No candidate passes every gate. The two arms fail in opposite ways:
- `transit` (script pull on transit rows, β 0.05 → 0): follows (threat-set share 0.58,
  go-to in time 0.66, attack share 0.51) but wins 0.2–5 % of carrier battles against v1.
- `reward` (no pull): keeps its strength (mission win vs v1 0.70–0.73, vs w1_400
  0.43–0.53; deathmatch 0.90 / 0.54–0.61) but follows little better than with its
  orders hidden.

## What ran

- Both arms from run 1's w1_400, widened 403 → 583 inputs with the new columns zeroed,
  stepped at 3× the LR; KL anchor to w1_400 on unordered rows; frozen pool v1 + w1_400;
  order reward weight 1. 300 updates each, concurrently, 09:44–11:42 (about 23 s per
  update). Baseline 09:31–09:44, gate evals 11:42–14:07.
- Order eval v2: each pilot with its orders and with them **hidden by the sim**, on the
  same matches.

## Gates (from `eval/gates.md`; random commander unless noted)

| candidate | O | M | D | mission win vs v1 | vs w1_400 | attack share | threat share | go-to in time | dm vs script | dm vs v1 |
|---|---|---|---|---|---|---|---|---|---|---|
| reward_150 | ✗ | ✓ | ✓ | 0.719 | 0.486 | 0.409 | 0.345 | 0.487 | 0.905 | 0.593 |
| reward_300 | ✗ | ✓ | ✓ | 0.726 | 0.531 | 0.389 | 0.366 | 0.514 | 0.900 | 0.613 |
| transit_150 | ✗ | ✗ | ✗ | 0.255 | 0.140 | 0.510 | 0.579 | 0.667 | 0.681 | 0.305 |
| transit_300 | ✗ | ✗ | ✗ | 0.305 | 0.186 | 0.512 | 0.584 | 0.662 | 0.744 | 0.350 |

Bounds: attack share ≥ hidden + 0.05; threat share ≥ hidden + 0.05; go-to ≥ 0.7. The
teacher scores 0.470 / 0.650 / 0.898 on these. The defend hull-lost bound was replaced
from the teacher (0.62 per ward-minute), because w1_400's wards lose less (0.39) than
the scripts' (0.59): a pilot that fights well protects its ward better than one that
stations by it.

`reward_300` with its orders vs hidden: go-to in time 0.514 vs 0.393, threat share
0.366 vs 0.342, attack share 0.389 vs 0.404, attack close 64 vs 78 ticks. Go-to is the
only order it reads clearly. Under the scripted commander nobody reaches a go-to in
time (0.05–0.07; teacher 0.86).

## Why

- **The pull wrecks aiming, because movement is aiming.** The pull covers only the
  thruster and power heads. But fixed guns aim by turning the ship, and the thrusters
  turn it. On 13–15 % of rows (`beta_rows_share`), β 0.05 was enough: by update 50,
  carrier-battle fighters went from 61 to 9 damage, hit rate 0.26 → 0.08, fire share
  0.66 → 0.38. KL to w1_400 on ordered rows reached 2.3 (reward arm: 0.6). B2b (pull on
  67 % of rows) and B3 (13 %) fail the same way; the row filter was not the problem.
- **Without the pull, 300 updates move following only a little.** Go-to improves
  steadily (0.45 → 0.51 over the run, against 0.39 hidden); defend and attack do not.
  approx_kl at 3× stayed 0.005–0.007, so the step size has room.

## Next (proposed)

- **Drop the script pull for strike craft.** Two runs agree; it is not a tuning issue.
- **Continue the `reward` arm** from `reward_300`: it is as strong as w1_400 in
  missions and improving on go-to. Options for the next night: more updates (600), the
  new-input step at 10× (the reward arm's approx_kl leaves room the transit probe did
  not), and a larger order reward weight for defend and go-to.
- **Decide what "following" must look like on screen.** The teacher's defend is worse
  for the ward than w1_400's fighting. The defend gate should judge the ward's fate
  (hull lost, survival) against the hidden pilot, as it does, not the threat-set share.
