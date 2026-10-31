**policy:ppo_bc_150.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 97 (0.87 of 377) | 0.457 | 188.2 | 0.446 | 0.513 | 19 (0.91 of 2010) | 896/863/954 |
| scripted | 82 (0.87 of 874) | 0.512 | 237.2 | 0.653 | 0.197 | 22 (0.87 of 2913) | 2475/597/250 |
| carrier_battle/random | 122 (0.84 of 221) | 0.562 | 191.5 | 0.429 | 0.507 | 22 (0.91 of 1323) | 575/581/575 |
| convoy_escort/random | 74 (0.92 of 156) | 0.337 | 182.3 | 0.479 | 0.521 | 16 (0.90 of 687) | 321/282/379 |
| carrier_battle/scripted | 109 (0.83 of 621) | 0.712 | 241.8 | 0.651 | 0.000 | 23 (0.89 of 1954) | 1826/393/0 |
| convoy_escort/scripted | 40 (0.96 of 253) | 0.314 | 227.5 | 0.659 | 0.197 | 17 (0.84 of 959) | 649/204/250 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.17 | 0.37 | 0.31 | 0.38 |
| random | gunship | 0.46 | 0.47 | 0.50 | 0.51 |
| random | strafer | 0.24 | 0.30 | 0.30 | 0.28 |
| scripted | fighter | 0.16 | 0.37 | 0.31 | 0.40 |
| scripted | gunship | 0.38 | 0.49 | 0.50 | 0.49 |
| scripted | strafer | 0.18 | 0.29 | 0.30 | 0.24 |
