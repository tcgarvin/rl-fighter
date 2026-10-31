**policy:ppo_bc_400.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 162 (0.67 of 450) | 0.389 | 230.9 | 0.199 | 0.312 | 30 (0.80 of 2182) | 895/893/987 |
| scripted | 190 (0.76 of 780) | 0.479 | 243.9 | 0.246 | 0.013 | 25 (0.88 of 2248) | 1790/612/277 |
| carrier_battle/random | 187 (0.63 of 247) | 0.498 | 306.5 | 0.171 | 0.302 | 32 (0.78 of 1384) | 549/567/576 |
| convoy_escort/random | 141 (0.72 of 203) | 0.218 | 122.0 | 0.245 | 0.325 | 27 (0.83 of 798) | 346/326/411 |
| carrier_battle/scripted | 520 (0.72 of 427) | 0.613 | 294.6 | 0.211 | 0.000 | 30 (0.89 of 1135) | 1026/403/0 |
| convoy_escort/scripted | 63 (0.80 of 353) | 0.234 | 133.3 | 0.369 | 0.013 | 20 (0.86 of 1113) | 764/209/277 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.19 | 0.22 | 0.20 | 0.22 |
| random | gunship | 0.48 | 0.50 | 0.46 | 0.48 |
| random | strafer | 0.24 | 0.20 | 0.22 | 0.20 |
| scripted | fighter | 0.15 | 0.25 | 0.22 | 0.21 |
| scripted | gunship | 0.40 | 0.48 | 0.47 | 0.45 |
| scripted | strafer | 0.16 | 0.19 | 0.21 | 0.19 |
