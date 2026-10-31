**policy:ppo_bc_100.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 100 (0.85 of 375) | 0.457 | 206.6 | 0.407 | 0.488 | 19 (0.91 of 2060) | 902/868/959 |
| scripted | 83 (0.87 of 873) | 0.512 | 257.8 | 0.620 | 0.145 | 20 (0.88 of 2841) | 2419/605/249 |
| carrier_battle/random | 121 (0.82 of 234) | 0.567 | 200.1 | 0.384 | 0.479 | 21 (0.90 of 1365) | 580/587/589 |
| convoy_escort/random | 74 (0.91 of 141) | 0.349 | 217.7 | 0.453 | 0.502 | 18 (0.92 of 695) | 322/281/370 |
| carrier_battle/scripted | 109 (0.83 of 622) | 0.716 | 288.1 | 0.604 | 0.000 | 22 (0.89 of 1877) | 1766/386/0 |
| convoy_escort/scripted | 39 (0.98 of 251) | 0.277 | 196.1 | 0.679 | 0.145 | 17 (0.86 of 964) | 653/219/249 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.16 | 0.35 | 0.30 | 0.36 |
| random | gunship | 0.47 | 0.50 | 0.47 | 0.51 |
| random | strafer | 0.24 | 0.29 | 0.32 | 0.29 |
| scripted | fighter | 0.15 | 0.35 | 0.30 | 0.38 |
| scripted | gunship | 0.42 | 0.50 | 0.47 | 0.48 |
| scripted | strafer | 0.18 | 0.28 | 0.32 | 0.24 |
