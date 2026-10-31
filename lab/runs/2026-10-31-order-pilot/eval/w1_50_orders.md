**policy:ppo_bc_50.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 211 (0.58 of 519) | 0.417 | 200.1 | 0.187 | 0.099 | 42 (0.78 of 2727) | 1014/1008/1087 |
| scripted | 326 (0.69 of 907) | 0.444 | 184.9 | 0.225 | 0.003 | 26 (0.90 of 2327) | 1859/633/270 |
| carrier_battle/random | 226 (0.58 of 277) | 0.481 | 254.7 | 0.151 | 0.102 | 43 (0.76 of 1660) | 627/607/631 |
| convoy_escort/random | 202 (0.57 of 242) | 0.287 | 115.8 | 0.239 | 0.094 | 40 (0.82 of 1067) | 387/401/456 |
| carrier_battle/scripted | 544 (0.69 of 426) | 0.598 | 242.4 | 0.202 | 0.000 | 33 (0.91 of 1088) | 972/419/0 |
| convoy_escort/scripted | 148 (0.69 of 481) | 0.235 | 101.3 | 0.310 | 0.003 | 21 (0.88 of 1239) | 887/214/270 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.21 | 0.21 | 0.21 |
| random | gunship | 0.49 | 0.47 | 0.50 | 0.48 |
| random | strafer | 0.27 | 0.26 | 0.28 | 0.26 |
| scripted | fighter | 0.18 | 0.22 | 0.23 | 0.16 |
| scripted | gunship | 0.38 | 0.49 | 0.49 | 0.44 |
| scripted | strafer | 0.17 | 0.27 | 0.28 | 0.30 |
