**policy:ppo_bc_250.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 66 (0.86 of 1094) | 0.413 | 0.534 | 360 | 0.362 | 172 | 0.489 (1700) | 0.499 (1546) | 0.396 (154) | 0.38 | 3461/3385/2409 |
| random/hidden | 78 (0.82 of 1190) | 0.400 | 0.465 | 385 | 0.337 | 201 | 0.405 (1934) | 0.408 (1743) | 0.377 (191) | 0.32 | 3786/3626/2695 |
| scripted/followed | 48 (0.95 of 604) | 0.485 | 0.200 | 162 | 0.474 | 167 | 0.061 (230) | 0.064 (220) | 0.000 (10) | 0.06 | 1538/594/261 |
| carrier_battle/random/followed | 84 (0.81 of 682) | 0.512 | 0.486 | 240 | 0.362 | 183 | 0.521 (1089) | 0.530 (965) | 0.452 (124) | 0.42 | 2169/2157/1607 |
| carrier_battle/random/hidden | 99 (0.79 of 685) | 0.501 | 0.429 | 240 | 0.335 | 201 | 0.447 (1142) | 0.454 (996) | 0.404 (146) | 0.37 | 2198/2137/1659 |
| convoy_escort/random/followed | 24 (0.94 of 412) | 0.261 | 0.629 | 120 | 0.363 | 153 | 0.434 (611) | 0.448 (581) | 0.167 (30) | 0.31 | 1292/1228/802 |
| convoy_escort/random/hidden | 36 (0.86 of 505) | 0.240 | 0.525 | 145 | 0.339 | 201 | 0.345 (792) | 0.348 (747) | 0.289 (45) | 0.26 | 1588/1489/1036 |
| carrier_battle/scripted/followed | 72 (0.96 of 396) | 0.596 | 0.013 | 120 | 0.317 | 173 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 947/392/0 |
| convoy_escort/scripted/followed | 15 (0.92 of 208) | 0.259 | 0.734 | 42 | 0.967 | 149 | 0.061 (230) | 0.064 (220) | 0.000 (10) | 0.16 | 591/202/261 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.18 | 0.26 | 0.22 | 0.26 |
| random/followed | gunship | 0.47 | 0.46 | 0.42 | 0.47 |
| random/followed | strafer | 0.24 | 0.18 | 0.18 | 0.19 |
| random/hidden | fighter | 0.19 | 0.19 | 0.19 | 0.19 |
| random/hidden | gunship | 0.47 | 0.48 | 0.48 | 0.49 |
| random/hidden | strafer | 0.25 | 0.26 | 0.26 | 0.27 |
| scripted/followed | fighter | 0.17 | 0.27 | 0.25 | 0.25 |
| scripted/followed | gunship | 0.34 | 0.47 | 0.43 | 0.40 |
| scripted/followed | strafer | 0.15 | 0.17 | 0.19 | 0.12 |
