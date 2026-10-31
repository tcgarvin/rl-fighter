**policy:ppo_bc_150.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 224 (0.59 of 499) | 0.413 | 196.5 | 0.176 | 0.095 | 42 (0.77 of 2640) | 986/977/1036 |
| scripted | 274 (0.72 of 906) | 0.445 | 198.4 | 0.227 | 0.005 | 26 (0.89 of 2313) | 1866/640/264 |
| carrier_battle/random | 225 (0.60 of 287) | 0.496 | 243.7 | 0.149 | 0.091 | 46 (0.75 of 1615) | 616/587/604 |
| convoy_escort/random | 221 (0.57 of 212) | 0.266 | 119.9 | 0.213 | 0.101 | 37 (0.81 of 1025) | 370/390/432 |
| carrier_battle/scripted | 442 (0.73 of 434) | 0.594 | 253.2 | 0.202 | 0.000 | 30 (0.92 of 1078) | 970/424/0 |
| convoy_escort/scripted | 125 (0.70 of 472) | 0.235 | 112.2 | 0.315 | 0.005 | 22 (0.87 of 1235) | 896/216/264 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.19 | 0.19 | 0.20 | 0.20 |
| random | gunship | 0.47 | 0.47 | 0.46 | 0.49 |
| random | strafer | 0.28 | 0.25 | 0.25 | 0.24 |
| scripted | fighter | 0.16 | 0.21 | 0.22 | 0.15 |
| scripted | gunship | 0.36 | 0.47 | 0.45 | 0.42 |
| scripted | strafer | 0.17 | 0.24 | 0.24 | 0.25 |
