**policy:ppo_bc_100.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 240 (0.58 of 508) | 0.402 | 194.2 | 0.191 | 0.101 | 33 (0.79 of 2684) | 1013/1007/1050 |
| scripted | 235 (0.73 of 892) | 0.460 | 212.9 | 0.232 | 0.006 | 25 (0.88 of 2388) | 1916/642/279 |
| carrier_battle/random | 235 (0.60 of 290) | 0.474 | 239.6 | 0.161 | 0.088 | 34 (0.78 of 1640) | 643/608/594 |
| convoy_escort/random | 247 (0.56 of 218) | 0.267 | 118.9 | 0.236 | 0.118 | 31 (0.82 of 1044) | 370/399/456 |
| carrier_battle/scripted | 391 (0.72 of 444) | 0.614 | 275.7 | 0.206 | 0.000 | 32 (0.87 of 1165) | 1047/424/0 |
| convoy_escort/scripted | 124 (0.74 of 448) | 0.226 | 109.9 | 0.324 | 0.006 | 18 (0.89 of 1223) | 869/218/279 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.18 | 0.19 | 0.19 |
| random | gunship | 0.47 | 0.45 | 0.45 | 0.46 |
| random | strafer | 0.27 | 0.24 | 0.26 | 0.24 |
| scripted | fighter | 0.16 | 0.20 | 0.20 | 0.16 |
| scripted | gunship | 0.40 | 0.46 | 0.45 | 0.44 |
| scripted | strafer | 0.18 | 0.24 | 0.27 | 0.27 |
