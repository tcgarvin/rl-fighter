**policy:ppo_bc_200.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 93 (0.84 of 1421) | 0.503 | 0.500 | 433 | 0.614 | 186 | 0.676 (2021) | 0.675 (1833) | 0.681 (188) | 0.54 | 4154/4099/2724 |
| random/hidden | 81 (0.80 of 1270) | 0.401 | 0.482 | 395 | 0.335 | 199 | 0.397 (1936) | 0.401 (1771) | 0.352 (165) | 0.31 | 3898/3735/2758 |
| scripted/followed | 84 (0.91 of 878) | 0.489 | 0.351 | 188 | 0.984 | 239 | 0.590 (200) | 0.591 (198) | 0.500 (2) | 0.23 | 2213/600/218 |
| carrier_battle/random/followed | 114 (0.80 of 946) | 0.693 | 0.403 | 298 | 0.779 | 199 | 0.660 (1384) | 0.661 (1247) | 0.650 (137) | 0.57 | 2676/2737/1924 |
| carrier_battle/random/hidden | 93 (0.78 of 718) | 0.486 | 0.446 | 241 | 0.348 | 199 | 0.452 (1115) | 0.461 (1006) | 0.367 (109) | 0.36 | 2236/2163/1676 |
| convoy_escort/random/followed | 33 (0.92 of 475) | 0.299 | 0.712 | 135 | 0.449 | 156 | 0.711 (637) | 0.706 (586) | 0.765 (51) | 0.50 | 1478/1362/800 |
| convoy_escort/random/hidden | 42 (0.82 of 552) | 0.270 | 0.537 | 154 | 0.315 | 200 | 0.322 (821) | 0.322 (765) | 0.321 (56) | 0.24 | 1662/1572/1082 |
| carrier_battle/scripted/followed | 108 (0.89 of 673) | 0.681 | 0.123 | 147 | 0.971 | 259 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 1485/399/0 |
| convoy_escort/scripted/followed | 15 (0.98 of 205) | 0.275 | 1.185 | 40 | 0.995 | 152 | 0.590 (200) | 0.591 (198) | 0.500 (2) | 0.73 | 728/201/218 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.18 | 0.17 | 0.20 | 0.22 |
| random/followed | gunship | 0.48 | 0.44 | 0.44 | 0.53 |
| random/followed | strafer | 0.25 | 0.34 | 0.40 | 0.45 |
| random/hidden | fighter | 0.18 | 0.18 | 0.18 | 0.19 |
| random/hidden | gunship | 0.49 | 0.49 | 0.49 | 0.50 |
| random/hidden | strafer | 0.25 | 0.26 | 0.26 | 0.27 |
| scripted/followed | fighter | 0.18 | 0.15 | 0.17 | 0.34 |
| scripted/followed | gunship | 0.43 | 0.43 | 0.47 | 0.53 |
| scripted/followed | strafer | 0.19 | 0.33 | 0.39 | 0.41 |
