**policy:ppo_bc_400.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 270 (0.56 of 536) | 0.399 | 187.6 | 0.163 | 0.258 | 30 (0.81 of 2462) | 1022/979/1097 |
| scripted | 370 (0.70 of 903) | 0.455 | 168.4 | 0.203 | 0.002 | 26 (0.90 of 2207) | 1747/634/273 |
| carrier_battle/random | 234 (0.60 of 284) | 0.483 | 251.5 | 0.126 | 0.279 | 30 (0.79 of 1473) | 607/581/617 |
| convoy_escort/random | 344 (0.51 of 252) | 0.258 | 104.4 | 0.214 | 0.232 | 29 (0.85 of 989) | 415/398/480 |
| carrier_battle/scripted | 567 (0.70 of 435) | 0.619 | 222.6 | 0.180 | 0.000 | 30 (0.93 of 1051) | 936/419/0 |
| convoy_escort/scripted | 184 (0.71 of 468) | 0.235 | 90.6 | 0.298 | 0.002 | 22 (0.87 of 1156) | 811/215/273 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.21 | 0.20 | 0.21 | 0.20 |
| random | gunship | 0.47 | 0.47 | 0.47 | 0.48 |
| random | strafer | 0.27 | 0.27 | 0.29 | 0.27 |
| scripted | fighter | 0.18 | 0.22 | 0.22 | 0.16 |
| scripted | gunship | 0.35 | 0.48 | 0.48 | 0.44 |
| scripted | strafer | 0.18 | 0.29 | 0.30 | 0.32 |
