**policy:ppo_bc_400.pt:blank_orders** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 297 (0.56 of 499) | 0.442 | 220.8 | 0.170 | 0.106 | 46 (0.78 of 2679) | 1023/957/1065 |
| scripted | 296 (0.72 of 877) | 0.436 | 193.2 | 0.225 | 0.008 | 26 (0.89 of 2264) | 1815/624/272 |
| carrier_battle/random | 302 (0.56 of 292) | 0.526 | 283.4 | 0.126 | 0.109 | 45 (0.77 of 1655) | 649/571/629 |
| convoy_escort/random | 292 (0.55 of 207) | 0.273 | 118.7 | 0.229 | 0.103 | 46 (0.80 of 1024) | 374/386/436 |
| carrier_battle/scripted | 439 (0.73 of 409) | 0.597 | 258.7 | 0.199 | 0.000 | 32 (0.92 of 1050) | 944/417/0 |
| convoy_escort/scripted | 139 (0.71 of 468) | 0.214 | 98.3 | 0.320 | 0.008 | 21 (0.86 of 1214) | 871/207/272 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.19 | 0.20 | 0.19 |
| random | gunship | 0.48 | 0.48 | 0.48 | 0.49 |
| random | strafer | 0.26 | 0.24 | 0.25 | 0.26 |
| scripted | fighter | 0.17 | 0.21 | 0.22 | 0.15 |
| scripted | gunship | 0.39 | 0.48 | 0.49 | 0.45 |
| scripted | strafer | 0.18 | 0.27 | 0.27 | 0.31 |
