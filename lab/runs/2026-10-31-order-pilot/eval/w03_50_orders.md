**policy:ppo_bc_50.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 247 (0.59 of 543) | 0.367 | 172.1 | 0.186 | 0.104 | 35 (0.80 of 2717) | 1008/979/1092 |
| scripted | 346 (0.70 of 915) | 0.448 | 190.2 | 0.228 | 0.007 | 26 (0.88 of 2323) | 1868/628/258 |
| carrier_battle/random | 231 (0.61 of 304) | 0.441 | 209.8 | 0.158 | 0.093 | 34 (0.78 of 1645) | 619/583/643 |
| convoy_escort/random | 275 (0.56 of 239) | 0.254 | 116.7 | 0.222 | 0.118 | 39 (0.83 of 1072) | 389/396/449 |
| carrier_battle/scripted | 500 (0.72 of 426) | 0.625 | 255.1 | 0.212 | 0.000 | 29 (0.91 of 1117) | 999/413/0 |
| convoy_escort/scripted | 183 (0.68 of 489) | 0.210 | 94.5 | 0.295 | 0.007 | 22 (0.86 of 1206) | 869/215/258 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.22 | 0.22 | 0.22 |
| random | gunship | 0.49 | 0.50 | 0.48 | 0.50 |
| random | strafer | 0.26 | 0.23 | 0.25 | 0.25 |
| scripted | fighter | 0.17 | 0.24 | 0.24 | 0.16 |
| scripted | gunship | 0.37 | 0.50 | 0.49 | 0.45 |
| scripted | strafer | 0.16 | 0.25 | 0.25 | 0.28 |
