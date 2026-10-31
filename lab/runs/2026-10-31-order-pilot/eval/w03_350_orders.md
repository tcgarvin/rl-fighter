**policy:ppo_bc_350.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 168 (0.67 of 460) | 0.444 | 256.0 | 0.197 | 0.104 | 38 (0.78 of 2444) | 907/910/981 |
| scripted | 164 (0.78 of 774) | 0.481 | 240.4 | 0.264 | 0.014 | 26 (0.88 of 2149) | 1696/627/268 |
| carrier_battle/random | 188 (0.66 of 271) | 0.555 | 318.4 | 0.142 | 0.106 | 39 (0.78 of 1564) | 589/563/603 |
| convoy_escort/random | 120 (0.69 of 189) | 0.250 | 146.0 | 0.287 | 0.102 | 34 (0.78 of 880) | 318/347/378 |
| carrier_battle/scripted | 473 (0.72 of 452) | 0.615 | 283.3 | 0.235 | 0.000 | 34 (0.90 of 1105) | 994/413/0 |
| convoy_escort/scripted | 56 (0.87 of 322) | 0.227 | 135.6 | 0.360 | 0.014 | 20 (0.86 of 1044) | 702/214/268 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.19 | 0.20 | 0.18 | 0.21 |
| random | gunship | 0.47 | 0.47 | 0.45 | 0.46 |
| random | strafer | 0.25 | 0.18 | 0.20 | 0.20 |
| scripted | fighter | 0.13 | 0.22 | 0.22 | 0.18 |
| scripted | gunship | 0.29 | 0.46 | 0.44 | 0.44 |
| scripted | strafer | 0.14 | 0.18 | 0.19 | 0.16 |
