**policy:ppo_bc_200.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 97 (0.86 of 403) | 0.529 | 265.1 | 0.409 | 0.521 | 18 (0.91 of 2044) | 911/835/959 |
| scripted | 87 (0.86 of 911) | 0.561 | 327.4 | 0.650 | 0.163 | 19 (0.88 of 2883) | 2458/605/229 |
| carrier_battle/random | 124 (0.80 of 243) | 0.675 | 281.8 | 0.383 | 0.519 | 22 (0.91 of 1350) | 596/550/584 |
| convoy_escort/random | 70 (0.96 of 160) | 0.363 | 235.6 | 0.460 | 0.524 | 14 (0.92 of 694) | 315/285/375 |
| carrier_battle/scripted | 112 (0.82 of 665) | 0.758 | 375.5 | 0.665 | 0.000 | 20 (0.90 of 1958) | 1840/384/0 |
| convoy_escort/scripted | 40 (0.96 of 246) | 0.287 | 222.0 | 0.599 | 0.163 | 17 (0.85 of 925) | 618/221/229 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.18 | 0.36 | 0.32 | 0.39 |
| random | gunship | 0.46 | 0.47 | 0.46 | 0.48 |
| random | strafer | 0.24 | 0.31 | 0.31 | 0.29 |
| scripted | fighter | 0.15 | 0.36 | 0.32 | 0.41 |
| scripted | gunship | 0.41 | 0.46 | 0.47 | 0.46 |
| scripted | strafer | 0.19 | 0.29 | 0.32 | 0.25 |
