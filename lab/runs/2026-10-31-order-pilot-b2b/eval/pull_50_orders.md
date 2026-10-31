**policy:ppo_bc_50.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 96 (0.82 of 385) | 0.456 | 220.6 | 0.348 | 0.454 | 23 (0.88 of 2068) | 906/892/946 |
| scripted | 95 (0.86 of 801) | 0.472 | 242.3 | 0.494 | 0.073 | 22 (0.88 of 2652) | 2216/586/246 |
| carrier_battle/random | 117 (0.78 of 245) | 0.594 | 240.4 | 0.319 | 0.444 | 24 (0.88 of 1375) | 595/601/574 |
| convoy_escort/random | 70 (0.88 of 140) | 0.295 | 184.9 | 0.407 | 0.469 | 20 (0.89 of 693) | 311/291/372 |
| carrier_battle/scripted | 136 (0.81 of 544) | 0.662 | 265.8 | 0.478 | 0.000 | 25 (0.89 of 1693) | 1574/373/0 |
| convoy_escort/scripted | 41 (0.95 of 257) | 0.254 | 191.6 | 0.548 | 0.073 | 17 (0.86 of 959) | 642/213/246 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.16 | 0.34 | 0.29 | 0.33 |
| random | gunship | 0.46 | 0.47 | 0.44 | 0.48 |
| random | strafer | 0.25 | 0.27 | 0.27 | 0.26 |
| scripted | fighter | 0.13 | 0.35 | 0.28 | 0.36 |
| scripted | gunship | 0.39 | 0.48 | 0.44 | 0.48 |
| scripted | strafer | 0.17 | 0.26 | 0.28 | 0.22 |
