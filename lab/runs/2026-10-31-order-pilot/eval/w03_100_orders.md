**policy:ppo_bc_100.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 240 (0.60 of 486) | 0.391 | 194.4 | 0.183 | 0.097 | 41 (0.79 of 2621) | 973/965/1057 |
| scripted | 251 (0.72 of 909) | 0.461 | 208.0 | 0.234 | 0.012 | 26 (0.87 of 2378) | 1920/647/252 |
| carrier_battle/random | 286 (0.59 of 274) | 0.476 | 242.1 | 0.151 | 0.092 | 44 (0.78 of 1637) | 613/588/630 |
| convoy_escort/random | 177 (0.62 of 212) | 0.246 | 118.1 | 0.230 | 0.103 | 34 (0.81 of 984) | 360/377/427 |
| carrier_battle/scripted | 450 (0.71 of 459) | 0.620 | 267.4 | 0.207 | 0.000 | 31 (0.89 of 1212) | 1082/428/0 |
| convoy_escort/scripted | 114 (0.72 of 450) | 0.230 | 111.5 | 0.331 | 0.012 | 20 (0.86 of 1166) | 838/219/252 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.20 | 0.22 | 0.22 |
| random | gunship | 0.47 | 0.48 | 0.48 | 0.48 |
| random | strafer | 0.25 | 0.22 | 0.23 | 0.23 |
| scripted | fighter | 0.16 | 0.22 | 0.22 | 0.16 |
| scripted | gunship | 0.37 | 0.49 | 0.48 | 0.43 |
| scripted | strafer | 0.16 | 0.24 | 0.24 | 0.24 |
