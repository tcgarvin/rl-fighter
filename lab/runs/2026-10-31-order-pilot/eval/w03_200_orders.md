**policy:ppo_bc_200.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 199 (0.60 of 488) | 0.416 | 203.8 | 0.205 | 0.097 | 43 (0.78 of 2616) | 991/964/1040 |
| scripted | 314 (0.69 of 927) | 0.452 | 208.9 | 0.234 | 0.006 | 26 (0.87 of 2385) | 1932/653/263 |
| carrier_battle/random | 272 (0.56 of 272) | 0.505 | 254.4 | 0.167 | 0.097 | 42 (0.77 of 1627) | 620/592/608 |
| convoy_escort/random | 144 (0.64 of 216) | 0.266 | 124.3 | 0.258 | 0.096 | 45 (0.79 of 989) | 371/372/432 |
| carrier_battle/scripted | 574 (0.68 of 473) | 0.612 | 266.4 | 0.212 | 0.000 | 35 (0.88 of 1177) | 1063/440/0 |
| convoy_escort/scripted | 128 (0.69 of 454) | 0.222 | 112.7 | 0.320 | 0.006 | 22 (0.87 of 1208) | 869/213/263 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.19 | 0.20 | 0.21 |
| random | gunship | 0.46 | 0.46 | 0.46 | 0.47 |
| random | strafer | 0.25 | 0.22 | 0.24 | 0.23 |
| scripted | fighter | 0.16 | 0.22 | 0.22 | 0.16 |
| scripted | gunship | 0.36 | 0.46 | 0.46 | 0.42 |
| scripted | strafer | 0.17 | 0.23 | 0.24 | 0.25 |
