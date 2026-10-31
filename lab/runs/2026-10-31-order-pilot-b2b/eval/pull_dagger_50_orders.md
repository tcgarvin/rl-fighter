**policy:ppo_bc_50.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 89 (0.83 of 384) | 0.455 | 168.6 | 0.364 | 0.454 | 22 (0.89 of 1928) | 877/845/907 |
| scripted | 86 (0.86 of 849) | 0.444 | 176.7 | 0.507 | 0.114 | 21 (0.88 of 2729) | 2295/595/254 |
| carrier_battle/random | 116 (0.78 of 239) | 0.624 | 181.7 | 0.323 | 0.440 | 24 (0.89 of 1253) | 554/553/551 |
| convoy_escort/random | 68 (0.92 of 145) | 0.292 | 146.9 | 0.438 | 0.474 | 17 (0.90 of 675) | 323/292/356 |
| carrier_battle/scripted | 129 (0.82 of 591) | 0.666 | 187.5 | 0.494 | 0.000 | 24 (0.89 of 1750) | 1625/395/0 |
| convoy_escort/scripted | 42 (0.94 of 258) | 0.257 | 157.0 | 0.558 | 0.114 | 17 (0.85 of 979) | 670/200/254 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.16 | 0.36 | 0.28 | 0.33 |
| random | gunship | 0.47 | 0.50 | 0.48 | 0.51 |
| random | strafer | 0.25 | 0.29 | 0.28 | 0.28 |
| scripted | fighter | 0.13 | 0.36 | 0.28 | 0.38 |
| scripted | gunship | 0.41 | 0.50 | 0.47 | 0.51 |
| scripted | strafer | 0.18 | 0.28 | 0.30 | 0.24 |
