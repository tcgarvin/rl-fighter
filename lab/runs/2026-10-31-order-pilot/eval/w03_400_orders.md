**policy:ppo_bc_400.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 194 (0.65 of 468) | 0.385 | 212.0 | 0.230 | 0.110 | 40 (0.77 of 2446) | 914/940/992 |
| scripted | 148 (0.76 of 773) | 0.478 | 239.1 | 0.234 | 0.018 | 25 (0.86 of 2274) | 1812/628/279 |
| carrier_battle/random | 232 (0.61 of 281) | 0.477 | 262.4 | 0.183 | 0.111 | 40 (0.76 of 1557) | 589/590/598 |
| convoy_escort/random | 136 (0.70 of 187) | 0.223 | 123.3 | 0.303 | 0.108 | 42 (0.80 of 889) | 325/350/394 |
| carrier_battle/scripted | 463 (0.70 of 431) | 0.606 | 283.6 | 0.205 | 0.000 | 33 (0.88 of 1149) | 1036/418/0 |
| convoy_escort/scripted | 61 (0.84 of 342) | 0.235 | 135.0 | 0.340 | 0.018 | 19 (0.84 of 1125) | 776/210/279 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.19 | 0.21 | 0.20 | 0.22 |
| random | gunship | 0.47 | 0.46 | 0.46 | 0.46 |
| random | strafer | 0.25 | 0.19 | 0.19 | 0.19 |
| scripted | fighter | 0.15 | 0.22 | 0.22 | 0.19 |
| scripted | gunship | 0.34 | 0.45 | 0.43 | 0.43 |
| scripted | strafer | 0.13 | 0.18 | 0.19 | 0.16 |
