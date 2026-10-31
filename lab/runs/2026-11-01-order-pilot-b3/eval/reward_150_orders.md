**policy:ppo_bc_150.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 69 (0.82 of 1179) | 0.409 | 0.530 | 367 | 0.345 | 175 | 0.487 (1691) | 0.493 (1556) | 0.422 (135) | 0.36 | 3573/3436/2404 |
| random/hidden | 78 (0.83 of 1157) | 0.402 | 0.486 | 388 | 0.347 | 196 | 0.400 (1889) | 0.401 (1697) | 0.396 (192) | 0.31 | 3780/3656/2677 |
| scripted/followed | 48 (0.93 of 638) | 0.472 | 0.252 | 173 | 0.518 | 174 | 0.047 (234) | 0.051 (214) | 0.000 (20) | 0.04 | 1564/596/273 |
| carrier_battle/random/followed | 84 (0.79 of 733) | 0.527 | 0.470 | 242 | 0.331 | 184 | 0.518 (1065) | 0.524 (960) | 0.467 (105) | 0.40 | 2246/2168/1589 |
| carrier_battle/random/hidden | 96 (0.81 of 678) | 0.503 | 0.436 | 238 | 0.353 | 195 | 0.444 (1088) | 0.449 (949) | 0.410 (139) | 0.35 | 2238/2149/1637 |
| convoy_escort/random/followed | 30 (0.88 of 446) | 0.237 | 0.647 | 125 | 0.365 | 160 | 0.435 (626) | 0.443 (596) | 0.267 (30) | 0.31 | 1327/1268/815 |
| convoy_escort/random/hidden | 33 (0.86 of 479) | 0.237 | 0.566 | 150 | 0.337 | 198 | 0.341 (801) | 0.340 (748) | 0.358 (53) | 0.26 | 1542/1507/1040 |
| carrier_battle/scripted/followed | 75 (0.94 of 396) | 0.608 | 0.014 | 129 | 0.378 | 182 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 931/391/0 |
| convoy_escort/scripted/followed | 18 (0.90 of 242) | 0.213 | 0.952 | 44 | 0.956 | 150 | 0.047 (234) | 0.051 (214) | 0.000 (20) | 0.12 | 633/205/273 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.19 | 0.23 | 0.22 | 0.25 |
| random/followed | gunship | 0.48 | 0.49 | 0.45 | 0.49 |
| random/followed | strafer | 0.24 | 0.18 | 0.19 | 0.18 |
| random/hidden | fighter | 0.20 | 0.19 | 0.20 | 0.19 |
| random/hidden | gunship | 0.48 | 0.48 | 0.49 | 0.49 |
| random/hidden | strafer | 0.24 | 0.25 | 0.25 | 0.26 |
| scripted/followed | fighter | 0.16 | 0.26 | 0.23 | 0.25 |
| scripted/followed | gunship | 0.40 | 0.50 | 0.46 | 0.41 |
| scripted/followed | strafer | 0.15 | 0.18 | 0.19 | 0.13 |
