**policy:ppo_bc_300.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 92 (0.84 of 416) | 0.511 | 318.2 | 0.410 | 0.510 | 20 (0.89 of 2045) | 921/852/960 |
| scripted | 90 (0.83 of 978) | 0.556 | 364.9 | 0.641 | 0.166 | 20 (0.87 of 2885) | 2455/581/262 |
| carrier_battle/random | 114 (0.79 of 259) | 0.614 | 345.5 | 0.372 | 0.497 | 22 (0.90 of 1349) | 598/566/580 |
| convoy_escort/random | 71 (0.92 of 157) | 0.372 | 270.2 | 0.484 | 0.530 | 18 (0.89 of 696) | 323/286/380 |
| carrier_battle/scripted | 118 (0.78 of 721) | 0.704 | 415.4 | 0.657 | 0.000 | 22 (0.89 of 1902) | 1797/373/0 |
| convoy_escort/scripted | 41 (0.96 of 257) | 0.305 | 246.8 | 0.583 | 0.166 | 17 (0.84 of 983) | 658/208/262 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.17 | 0.35 | 0.31 | 0.37 |
| random | gunship | 0.46 | 0.46 | 0.45 | 0.48 |
| random | strafer | 0.23 | 0.29 | 0.30 | 0.28 |
| scripted | fighter | 0.17 | 0.34 | 0.31 | 0.40 |
| scripted | gunship | 0.42 | 0.46 | 0.45 | 0.47 |
| scripted | strafer | 0.17 | 0.28 | 0.31 | 0.23 |
