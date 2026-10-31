**policy:ppo_bc_150.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 202 (0.60 of 504) | 0.443 | 217.1 | 0.215 | 0.104 | 42 (0.79 of 2663) | 993/1002/1080 |
| scripted | 220 (0.71 of 938) | 0.436 | 198.0 | 0.246 | 0.005 | 24 (0.89 of 2407) | 1926/669/269 |
| carrier_battle/random | 226 (0.59 of 294) | 0.529 | 266.6 | 0.183 | 0.111 | 40 (0.77 of 1626) | 621/600/629 |
| convoy_escort/random | 174 (0.61 of 210) | 0.293 | 136.8 | 0.259 | 0.094 | 44 (0.82 of 1037) | 372/402/451 |
| carrier_battle/scripted | 498 (0.71 of 455) | 0.598 | 248.6 | 0.220 | 0.000 | 32 (0.93 of 1069) | 957/436/0 |
| convoy_escort/scripted | 106 (0.70 of 483) | 0.220 | 113.7 | 0.342 | 0.005 | 18 (0.86 of 1338) | 969/233/269 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.19 | 0.19 | 0.19 |
| random | gunship | 0.48 | 0.47 | 0.46 | 0.49 |
| random | strafer | 0.25 | 0.24 | 0.25 | 0.25 |
| scripted | fighter | 0.16 | 0.20 | 0.20 | 0.16 |
| scripted | gunship | 0.39 | 0.48 | 0.47 | 0.48 |
| scripted | strafer | 0.16 | 0.24 | 0.25 | 0.26 |
