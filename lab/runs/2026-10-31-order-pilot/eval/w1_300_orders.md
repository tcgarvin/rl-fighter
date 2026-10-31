**policy:ppo_bc_300.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 220 (0.62 of 472) | 0.417 | 224.5 | 0.195 | 0.095 | 45 (0.77 of 2528) | 927/942/1030 |
| scripted | 198 (0.75 of 800) | 0.480 | 237.5 | 0.254 | 0.014 | 26 (0.88 of 2231) | 1752/625/282 |
| carrier_battle/random | 258 (0.61 of 277) | 0.520 | 287.0 | 0.161 | 0.096 | 48 (0.74 of 1588) | 592/578/615 |
| convoy_escort/random | 171 (0.64 of 195) | 0.227 | 117.2 | 0.245 | 0.093 | 39 (0.82 of 940) | 335/364/415 |
| carrier_battle/scripted | 533 (0.73 of 417) | 0.627 | 285.8 | 0.218 | 0.000 | 31 (0.90 of 1060) | 952/402/0 |
| convoy_escort/scripted | 72 (0.78 of 383) | 0.227 | 132.0 | 0.382 | 0.014 | 20 (0.85 of 1171) | 800/223/282 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.20 | 0.22 | 0.19 | 0.22 |
| random | gunship | 0.47 | 0.48 | 0.45 | 0.48 |
| random | strafer | 0.24 | 0.20 | 0.23 | 0.22 |
| scripted | fighter | 0.16 | 0.24 | 0.22 | 0.20 |
| scripted | gunship | 0.37 | 0.47 | 0.45 | 0.46 |
| scripted | strafer | 0.14 | 0.20 | 0.23 | 0.21 |
