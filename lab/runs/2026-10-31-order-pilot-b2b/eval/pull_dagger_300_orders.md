**policy:ppo_bc_300.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 99 (0.87 of 379) | 0.512 | 289.8 | 0.440 | 0.486 | 19 (0.91 of 1999) | 878/860/951 |
| scripted | 91 (0.85 of 930) | 0.568 | 337.5 | 0.674 | 0.174 | 19 (0.87 of 2931) | 2482/613/276 |
| carrier_battle/random | 122 (0.82 of 236) | 0.653 | 327.1 | 0.417 | 0.474 | 21 (0.91 of 1281) | 547/552/564 |
| convoy_escort/random | 71 (0.95 of 143) | 0.345 | 230.5 | 0.481 | 0.502 | 16 (0.91 of 718) | 331/308/387 |
| carrier_battle/scripted | 120 (0.81 of 680) | 0.724 | 371.8 | 0.690 | 0.000 | 21 (0.88 of 1975) | 1865/388/0 |
| convoy_escort/scripted | 41 (0.96 of 250) | 0.315 | 251.1 | 0.616 | 0.174 | 17 (0.85 of 956) | 617/225/276 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.18 | 0.34 | 0.31 | 0.39 |
| random | gunship | 0.46 | 0.44 | 0.44 | 0.47 |
| random | strafer | 0.24 | 0.28 | 0.29 | 0.27 |
| scripted | fighter | 0.16 | 0.34 | 0.31 | 0.41 |
| scripted | gunship | 0.42 | 0.45 | 0.45 | 0.46 |
| scripted | strafer | 0.17 | 0.27 | 0.29 | 0.21 |
