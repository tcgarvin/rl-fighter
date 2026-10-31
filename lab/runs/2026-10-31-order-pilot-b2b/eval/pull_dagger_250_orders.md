**policy:ppo_bc_250.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 94 (0.84 of 388) | 0.504 | 261.7 | 0.428 | 0.507 | 19 (0.90 of 2028) | 889/873/945 |
| scripted | 88 (0.86 of 879) | 0.551 | 302.8 | 0.677 | 0.179 | 19 (0.89 of 2865) | 2420/588/283 |
| carrier_battle/random | 120 (0.79 of 236) | 0.676 | 288.0 | 0.413 | 0.499 | 22 (0.90 of 1320) | 560/573/573 |
| convoy_escort/random | 73 (0.91 of 152) | 0.335 | 221.5 | 0.458 | 0.518 | 17 (0.90 of 708) | 329/300/372 |
| carrier_battle/scripted | 116 (0.82 of 642) | 0.732 | 338.7 | 0.681 | 0.000 | 21 (0.90 of 1892) | 1788/371/0 |
| convoy_escort/scripted | 39 (1.00 of 237) | 0.293 | 220.0 | 0.660 | 0.179 | 16 (0.87 of 973) | 632/217/283 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.17 | 0.32 | 0.29 | 0.37 |
| random | gunship | 0.47 | 0.47 | 0.47 | 0.49 |
| random | strafer | 0.24 | 0.28 | 0.29 | 0.28 |
| scripted | fighter | 0.16 | 0.33 | 0.28 | 0.40 |
| scripted | gunship | 0.43 | 0.46 | 0.47 | 0.46 |
| scripted | strafer | 0.17 | 0.28 | 0.30 | 0.22 |
