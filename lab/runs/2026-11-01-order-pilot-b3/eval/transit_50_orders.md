**policy:ppo_bc_50.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 93 (0.85 of 1420) | 0.445 | 0.526 | 424 | 0.515 | 183 | 0.531 (2021) | 0.548 (1855) | 0.349 (166) | 0.46 | 4148/4042/2754 |
| random/hidden | 81 (0.82 of 1234) | 0.390 | 0.531 | 390 | 0.332 | 195 | 0.386 (1900) | 0.392 (1737) | 0.325 (163) | 0.31 | 3852/3682/2705 |
| scripted/followed | 81 (0.96 of 768) | 0.467 | 0.339 | 188 | 0.951 | 217 | 0.473 (224) | 0.486 (216) | 0.125 (8) | 0.22 | 1982/577/237 |
| carrier_battle/random/followed | 117 (0.82 of 965) | 0.592 | 0.404 | 289 | 0.622 | 196 | 0.549 (1403) | 0.567 (1278) | 0.360 (125) | 0.50 | 2696/2683/1962 |
| carrier_battle/random/hidden | 96 (0.81 of 712) | 0.487 | 0.466 | 244 | 0.322 | 196 | 0.438 (1126) | 0.447 (1012) | 0.360 (114) | 0.36 | 2245/2170/1653 |
| convoy_escort/random/followed | 30 (0.93 of 455) | 0.267 | 0.786 | 136 | 0.408 | 154 | 0.492 (618) | 0.504 (577) | 0.317 (41) | 0.37 | 1452/1359/792 |
| convoy_escort/random/hidden | 39 (0.84 of 522) | 0.248 | 0.640 | 145 | 0.347 | 192 | 0.311 (774) | 0.316 (725) | 0.245 (49) | 0.24 | 1607/1512/1052 |
| carrier_battle/scripted/followed | 108 (0.97 of 565) | 0.634 | 0.107 | 145 | 0.913 | 234 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 1283/364/0 |
| convoy_escort/scripted/followed | 18 (0.95 of 203) | 0.249 | 1.135 | 42 | 0.985 | 142 | 0.473 (224) | 0.486 (216) | 0.125 (8) | 0.68 | 699/213/237 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.17 | 0.17 | 0.18 | 0.19 |
| random/followed | gunship | 0.47 | 0.45 | 0.40 | 0.52 |
| random/followed | strafer | 0.26 | 0.31 | 0.35 | 0.37 |
| random/hidden | fighter | 0.17 | 0.17 | 0.17 | 0.17 |
| random/hidden | gunship | 0.48 | 0.48 | 0.48 | 0.49 |
| random/hidden | strafer | 0.26 | 0.27 | 0.27 | 0.27 |
| scripted/followed | fighter | 0.16 | 0.16 | 0.18 | 0.28 |
| scripted/followed | gunship | 0.34 | 0.47 | 0.43 | 0.49 |
| scripted/followed | strafer | 0.21 | 0.29 | 0.37 | 0.34 |
