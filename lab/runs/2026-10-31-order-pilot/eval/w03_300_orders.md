**policy:ppo_bc_300.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 175 (0.65 of 463) | 0.414 | 238.0 | 0.211 | 0.108 | 44 (0.78 of 2442) | 905/900/998 |
| scripted | 163 (0.79 of 769) | 0.445 | 213.4 | 0.241 | 0.007 | 26 (0.88 of 2141) | 1689/614/274 |
| carrier_battle/random | 209 (0.59 of 266) | 0.512 | 316.5 | 0.175 | 0.106 | 49 (0.76 of 1553) | 581/554/607 |
| convoy_escort/random | 127 (0.73 of 197) | 0.227 | 115.0 | 0.264 | 0.111 | 38 (0.82 of 889) | 324/346/391 |
| carrier_battle/scripted | 485 (0.74 of 409) | 0.583 | 253.4 | 0.201 | 0.000 | 30 (0.91 of 1037) | 923/406/0 |
| convoy_escort/scripted | 62 (0.83 of 360) | 0.216 | 124.7 | 0.396 | 0.007 | 21 (0.85 of 1104) | 766/208/274 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.18 | 0.19 | 0.19 | 0.20 |
| random | gunship | 0.48 | 0.46 | 0.44 | 0.45 |
| random | strafer | 0.26 | 0.19 | 0.21 | 0.21 |
| scripted | fighter | 0.14 | 0.22 | 0.21 | 0.17 |
| scripted | gunship | 0.36 | 0.46 | 0.44 | 0.43 |
| scripted | strafer | 0.15 | 0.20 | 0.21 | 0.20 |
