**policy:ppo_bc_400.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 343 (0.53 of 549) | 0.391 | 169.0 | 0.180 | 0.101 | 37 (0.81 of 2772) | 1040/1029/1080 |
| scripted | 370 (0.70 of 903) | 0.455 | 168.4 | 0.203 | 0.002 | 26 (0.90 of 2207) | 1747/634/273 |
| carrier_battle/random | 272 (0.54 of 304) | 0.452 | 209.3 | 0.147 | 0.094 | 37 (0.79 of 1682) | 640/614/618 |
| convoy_escort/random | 532 (0.51 of 245) | 0.290 | 113.0 | 0.223 | 0.110 | 37 (0.83 of 1090) | 400/415/462 |
| carrier_battle/scripted | 567 (0.70 of 435) | 0.619 | 222.6 | 0.180 | 0.000 | 30 (0.93 of 1051) | 936/419/0 |
| convoy_escort/scripted | 184 (0.71 of 468) | 0.235 | 90.6 | 0.298 | 0.002 | 22 (0.87 of 1156) | 811/215/273 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.21 | 0.21 | 0.21 | 0.21 |
| random | gunship | 0.48 | 0.48 | 0.48 | 0.49 |
| random | strafer | 0.26 | 0.28 | 0.29 | 0.28 |
| scripted | fighter | 0.18 | 0.22 | 0.22 | 0.16 |
| scripted | gunship | 0.35 | 0.48 | 0.48 | 0.44 |
| scripted | strafer | 0.18 | 0.29 | 0.30 | 0.32 |
