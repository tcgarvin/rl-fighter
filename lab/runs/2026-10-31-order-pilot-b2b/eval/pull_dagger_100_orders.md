**policy:ppo_bc_100.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 95 (0.84 of 386) | 0.456 | 172.0 | 0.396 | 0.477 | 20 (0.91 of 1996) | 874/840/928 |
| scripted | 82 (0.85 of 903) | 0.473 | 198.3 | 0.590 | 0.165 | 20 (0.88 of 2895) | 2470/603/242 |
| carrier_battle/random | 120 (0.79 of 240) | 0.624 | 168.1 | 0.379 | 0.459 | 22 (0.91 of 1281) | 547/545/558 |
| convoy_escort/random | 68 (0.94 of 146) | 0.325 | 178.1 | 0.428 | 0.504 | 17 (0.91 of 715) | 327/295/370 |
| carrier_battle/scripted | 114 (0.81 of 643) | 0.693 | 199.7 | 0.583 | 0.000 | 22 (0.89 of 1920) | 1796/390/0 |
| convoy_escort/scripted | 40 (0.95 of 260) | 0.288 | 195.6 | 0.618 | 0.165 | 16 (0.85 of 975) | 674/213/242 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.17 | 0.35 | 0.30 | 0.36 |
| random | gunship | 0.48 | 0.50 | 0.49 | 0.52 |
| random | strafer | 0.24 | 0.30 | 0.31 | 0.29 |
| scripted | fighter | 0.15 | 0.36 | 0.30 | 0.41 |
| scripted | gunship | 0.46 | 0.51 | 0.51 | 0.50 |
| scripted | strafer | 0.18 | 0.29 | 0.32 | 0.26 |
