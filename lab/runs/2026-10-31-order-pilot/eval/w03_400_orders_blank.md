**policy:ppo_bc_400.pt:blank_orders** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 260 (0.56 of 500) | 0.423 | 207.7 | 0.173 | 0.104 | 40 (0.78 of 2633) | 1000/940/1070 |
| scripted | 362 (0.66 of 956) | 0.462 | 198.5 | 0.222 | 0.002 | 26 (0.89 of 2410) | 1940/635/276 |
| carrier_battle/random | 232 (0.59 of 267) | 0.492 | 264.7 | 0.144 | 0.099 | 40 (0.77 of 1636) | 629/576/628 |
| convoy_escort/random | 395 (0.52 of 233) | 0.289 | 121.5 | 0.215 | 0.110 | 40 (0.79 of 997) | 371/364/442 |
| carrier_battle/scripted | 549 (0.69 of 443) | 0.620 | 265.9 | 0.198 | 0.000 | 31 (0.91 of 1145) | 1021/426/0 |
| convoy_escort/scripted | 235 (0.64 of 513) | 0.228 | 98.4 | 0.311 | 0.002 | 21 (0.87 of 1265) | 919/209/276 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.19 | 0.18 | 0.20 | 0.20 |
| random | gunship | 0.47 | 0.48 | 0.48 | 0.48 |
| random | strafer | 0.26 | 0.26 | 0.27 | 0.27 |
| scripted | fighter | 0.16 | 0.21 | 0.21 | 0.15 |
| scripted | gunship | 0.36 | 0.48 | 0.48 | 0.43 |
| scripted | strafer | 0.18 | 0.28 | 0.29 | 0.30 |
