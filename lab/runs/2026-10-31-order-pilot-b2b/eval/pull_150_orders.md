**policy:ppo_bc_150.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 94 (0.83 of 409) | 0.531 | 255.0 | 0.424 | 0.505 | 19 (0.91 of 1984) | 906/836/943 |
| scripted | 85 (0.87 of 936) | 0.549 | 297.6 | 0.650 | 0.165 | 19 (0.88 of 2936) | 2521/598/226 |
| carrier_battle/random | 120 (0.77 of 257) | 0.704 | 290.0 | 0.396 | 0.498 | 22 (0.91 of 1299) | 573/561/578 |
| convoy_escort/random | 70 (0.93 of 152) | 0.320 | 192.5 | 0.482 | 0.515 | 16 (0.93 of 685) | 333/275/365 |
| carrier_battle/scripted | 112 (0.85 of 676) | 0.739 | 325.6 | 0.663 | 0.000 | 22 (0.89 of 1969) | 1858/369/0 |
| convoy_escort/scripted | 40 (0.94 of 260) | 0.307 | 235.6 | 0.600 | 0.165 | 15 (0.86 of 967) | 663/229/226 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.17 | 0.37 | 0.31 | 0.37 |
| random | gunship | 0.47 | 0.49 | 0.46 | 0.49 |
| random | strafer | 0.24 | 0.32 | 0.32 | 0.30 |
| scripted | fighter | 0.17 | 0.37 | 0.31 | 0.40 |
| scripted | gunship | 0.41 | 0.48 | 0.48 | 0.48 |
| scripted | strafer | 0.19 | 0.30 | 0.32 | 0.26 |
