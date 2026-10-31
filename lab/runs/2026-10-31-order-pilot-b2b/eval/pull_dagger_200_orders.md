**policy:ppo_bc_200.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 90 (0.85 of 404) | 0.514 | 246.6 | 0.411 | 0.512 | 18 (0.91 of 2034) | 895/852/966 |
| scripted | 84 (0.87 of 868) | 0.523 | 268.6 | 0.672 | 0.171 | 20 (0.88 of 2870) | 2444/581/250 |
| carrier_battle/random | 106 (0.81 of 247) | 0.670 | 274.8 | 0.375 | 0.499 | 20 (0.92 of 1339) | 566/558/590 |
| convoy_escort/random | 73 (0.93 of 157) | 0.336 | 199.9 | 0.475 | 0.533 | 16 (0.90 of 695) | 329/294/376 |
| carrier_battle/scripted | 112 (0.82 of 622) | 0.716 | 285.4 | 0.680 | 0.000 | 22 (0.90 of 1917) | 1806/368/0 |
| convoy_escort/scripted | 40 (0.99 of 246) | 0.306 | 232.7 | 0.639 | 0.171 | 16 (0.84 of 953) | 638/213/250 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.17 | 0.34 | 0.31 | 0.39 |
| random | gunship | 0.46 | 0.47 | 0.48 | 0.50 |
| random | strafer | 0.24 | 0.30 | 0.31 | 0.29 |
| scripted | fighter | 0.16 | 0.35 | 0.30 | 0.41 |
| scripted | gunship | 0.44 | 0.47 | 0.49 | 0.48 |
| scripted | strafer | 0.18 | 0.29 | 0.30 | 0.24 |
