**policy:ppo_bc_250.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 98 (0.87 of 388) | 0.493 | 284.0 | 0.406 | 0.489 | 18 (0.91 of 2014) | 894/845/939 |
| scripted | 85 (0.85 of 921) | 0.559 | 341.0 | 0.644 | 0.191 | 20 (0.88 of 2872) | 2446/607/244 |
| carrier_battle/random | 127 (0.81 of 233) | 0.623 | 317.1 | 0.372 | 0.475 | 22 (0.90 of 1318) | 589/541/565 |
| convoy_escort/random | 75 (0.97 of 155) | 0.315 | 221.4 | 0.466 | 0.511 | 15 (0.91 of 696) | 305/304/374 |
| carrier_battle/scripted | 114 (0.80 of 666) | 0.739 | 388.4 | 0.644 | 0.000 | 22 (0.90 of 1869) | 1762/376/0 |
| convoy_escort/scripted | 39 (0.98 of 255) | 0.298 | 237.2 | 0.644 | 0.191 | 17 (0.84 of 1003) | 684/231/244 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.18 | 0.36 | 0.31 | 0.38 |
| random | gunship | 0.46 | 0.45 | 0.46 | 0.48 |
| random | strafer | 0.25 | 0.30 | 0.32 | 0.29 |
| scripted | fighter | 0.15 | 0.35 | 0.31 | 0.41 |
| scripted | gunship | 0.44 | 0.45 | 0.46 | 0.47 |
| scripted | strafer | 0.16 | 0.29 | 0.31 | 0.24 |
