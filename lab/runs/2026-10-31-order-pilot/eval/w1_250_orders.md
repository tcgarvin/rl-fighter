**policy:ppo_bc_250.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 211 (0.63 of 475) | 0.428 | 217.3 | 0.204 | 0.103 | 42 (0.78 of 2583) | 965/942/1042 |
| scripted | 202 (0.74 of 851) | 0.462 | 219.8 | 0.249 | 0.016 | 25 (0.88 of 2242) | 1779/630/277 |
| carrier_battle/random | 241 (0.61 of 277) | 0.538 | 265.3 | 0.167 | 0.098 | 41 (0.77 of 1633) | 621/585/621 |
| convoy_escort/random | 170 (0.65 of 198) | 0.259 | 137.6 | 0.258 | 0.110 | 42 (0.81 of 950) | 344/357/421 |
| carrier_battle/scripted | 424 (0.72 of 451) | 0.612 | 270.3 | 0.225 | 0.000 | 36 (0.89 of 1122) | 1002/430/0 |
| convoy_escort/scripted | 96 (0.76 of 400) | 0.223 | 120.8 | 0.334 | 0.016 | 19 (0.87 of 1120) | 777/200/277 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.22 | 0.19 | 0.22 |
| random | gunship | 0.48 | 0.48 | 0.47 | 0.50 |
| random | strafer | 0.25 | 0.22 | 0.25 | 0.22 |
| scripted | fighter | 0.15 | 0.23 | 0.22 | 0.19 |
| scripted | gunship | 0.38 | 0.50 | 0.47 | 0.47 |
| scripted | strafer | 0.14 | 0.22 | 0.24 | 0.25 |
