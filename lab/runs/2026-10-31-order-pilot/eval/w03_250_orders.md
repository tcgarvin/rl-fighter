**policy:ppo_bc_250.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 204 (0.61 of 489) | 0.394 | 217.5 | 0.215 | 0.097 | 37 (0.80 of 2503) | 935/940/991 |
| scripted | 203 (0.74 of 841) | 0.480 | 245.0 | 0.238 | 0.004 | 26 (0.87 of 2276) | 1814/644/273 |
| carrier_battle/random | 215 (0.58 of 288) | 0.470 | 266.3 | 0.188 | 0.090 | 38 (0.79 of 1584) | 606/577/599 |
| convoy_escort/random | 187 (0.65 of 201) | 0.252 | 132.3 | 0.257 | 0.107 | 35 (0.82 of 919) | 329/363/392 |
| carrier_battle/scripted | 466 (0.70 of 460) | 0.621 | 299.9 | 0.211 | 0.000 | 30 (0.90 of 1164) | 1046/429/0 |
| convoy_escort/scripted | 70 (0.80 of 381) | 0.230 | 130.3 | 0.338 | 0.004 | 22 (0.85 of 1112) | 768/215/273 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.21 | 0.23 | 0.22 | 0.24 |
| random | gunship | 0.47 | 0.46 | 0.45 | 0.48 |
| random | strafer | 0.26 | 0.21 | 0.22 | 0.21 |
| scripted | fighter | 0.15 | 0.24 | 0.25 | 0.20 |
| scripted | gunship | 0.38 | 0.47 | 0.45 | 0.43 |
| scripted | strafer | 0.16 | 0.20 | 0.21 | 0.22 |
