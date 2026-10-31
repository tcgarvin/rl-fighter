**policy:ppo_bc_400.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 195 (0.62 of 459) | 0.442 | 242.5 | 0.227 | 0.116 | 41 (0.78 of 2531) | 963/929/1011 |
| scripted | 190 (0.76 of 780) | 0.479 | 243.9 | 0.246 | 0.013 | 25 (0.88 of 2248) | 1790/612/277 |
| carrier_battle/random | 240 (0.60 of 280) | 0.526 | 289.8 | 0.194 | 0.117 | 40 (0.76 of 1623) | 629/585/614 |
| convoy_escort/random | 133 (0.65 of 179) | 0.292 | 159.1 | 0.277 | 0.113 | 44 (0.81 of 908) | 334/344/397 |
| carrier_battle/scripted | 520 (0.72 of 427) | 0.613 | 294.6 | 0.211 | 0.000 | 30 (0.89 of 1135) | 1026/403/0 |
| convoy_escort/scripted | 63 (0.80 of 353) | 0.234 | 133.3 | 0.369 | 0.013 | 20 (0.86 of 1113) | 764/209/277 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.22 | 0.20 | 0.23 |
| random | gunship | 0.47 | 0.47 | 0.47 | 0.48 |
| random | strafer | 0.24 | 0.20 | 0.22 | 0.21 |
| scripted | fighter | 0.15 | 0.25 | 0.22 | 0.21 |
| scripted | gunship | 0.40 | 0.48 | 0.47 | 0.45 |
| scripted | strafer | 0.16 | 0.19 | 0.21 | 0.19 |
