**policy:ppo_bc_100.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 93 (0.83 of 1408) | 0.485 | 0.526 | 427 | 0.581 | 187 | 0.634 (2036) | 0.643 (1856) | 0.539 (180) | 0.52 | 4238/4034/2749 |
| random/hidden | 78 (0.82 of 1202) | 0.389 | 0.509 | 389 | 0.337 | 196 | 0.388 (1929) | 0.395 (1753) | 0.318 (176) | 0.31 | 3844/3640/2734 |
| scripted/followed | 87 (0.89 of 863) | 0.482 | 0.360 | 185 | 0.975 | 232 | 0.591 (186) | 0.595 (185) | 0.000 (1) | 0.22 | 2188/581/208 |
| carrier_battle/random/followed | 114 (0.78 of 979) | 0.664 | 0.426 | 294 | 0.747 | 199 | 0.622 (1396) | 0.635 (1263) | 0.496 (133) | 0.54 | 2767/2692/1945 |
| carrier_battle/random/hidden | 93 (0.79 of 701) | 0.476 | 0.474 | 245 | 0.344 | 196 | 0.440 (1126) | 0.452 (1009) | 0.333 (117) | 0.36 | 2275/2166/1676 |
| convoy_escort/random/followed | 27 (0.94 of 429) | 0.282 | 0.747 | 133 | 0.431 | 159 | 0.659 (640) | 0.659 (593) | 0.660 (47) | 0.48 | 1471/1342/804 |
| convoy_escort/random/hidden | 36 (0.86 of 501) | 0.260 | 0.567 | 144 | 0.326 | 197 | 0.315 (803) | 0.317 (744) | 0.288 (59) | 0.25 | 1569/1474/1058 |
| carrier_battle/scripted/followed | 106 (0.87 of 660) | 0.666 | 0.096 | 145 | 0.973 | 253 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 1471/374/0 |
| convoy_escort/scripted/followed | 15 (0.97 of 203) | 0.266 | 1.322 | 40 | 0.976 | 135 | 0.591 (186) | 0.595 (185) | 0.000 (1) | 0.69 | 717/207/208 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.18 | 0.20 | 0.22 | 0.22 |
| random/followed | gunship | 0.47 | 0.45 | 0.46 | 0.52 |
| random/followed | strafer | 0.25 | 0.34 | 0.38 | 0.43 |
| random/hidden | fighter | 0.17 | 0.18 | 0.18 | 0.18 |
| random/hidden | gunship | 0.48 | 0.49 | 0.49 | 0.49 |
| random/hidden | strafer | 0.25 | 0.25 | 0.25 | 0.25 |
| scripted/followed | fighter | 0.19 | 0.19 | 0.19 | 0.31 |
| scripted/followed | gunship | 0.41 | 0.44 | 0.51 | 0.52 |
| scripted/followed | strafer | 0.19 | 0.31 | 0.40 | 0.37 |
