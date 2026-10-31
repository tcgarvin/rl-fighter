**policy:ppo_bc_150.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 93 (0.82 of 1418) | 0.510 | 0.538 | 432 | 0.579 | 185 | 0.667 (2079) | 0.668 (1885) | 0.655 (194) | 0.55 | 4197/4087/2747 |
| random/hidden | 69 (0.83 of 1203) | 0.394 | 0.506 | 389 | 0.324 | 196 | 0.374 (1969) | 0.380 (1783) | 0.317 (186) | 0.30 | 3852/3661/2767 |
| scripted/followed | 84 (0.91 of 873) | 0.495 | 0.369 | 187 | 0.989 | 233 | 0.619 (194) | 0.620 (192) | 0.500 (2) | 0.24 | 2116/593/208 |
| carrier_battle/random/followed | 114 (0.77 of 989) | 0.692 | 0.425 | 296 | 0.764 | 197 | 0.651 (1449) | 0.653 (1299) | 0.640 (150) | 0.59 | 2776/2706/1957 |
| carrier_battle/random/hidden | 87 (0.79 of 700) | 0.493 | 0.456 | 242 | 0.333 | 196 | 0.433 (1117) | 0.444 (991) | 0.349 (126) | 0.36 | 2249/2134/1650 |
| convoy_escort/random/followed | 27 (0.94 of 429) | 0.306 | 0.786 | 135 | 0.426 | 159 | 0.703 (630) | 0.703 (586) | 0.705 (44) | 0.49 | 1421/1381/790 |
| convoy_escort/random/hidden | 36 (0.87 of 503) | 0.243 | 0.588 | 147 | 0.309 | 196 | 0.296 (852) | 0.299 (792) | 0.250 (60) | 0.24 | 1603/1527/1117 |
| carrier_battle/scripted/followed | 104 (0.88 of 670) | 0.666 | 0.101 | 146 | 0.984 | 254 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 1424/387/0 |
| convoy_escort/scripted/followed | 15 (0.98 of 203) | 0.290 | 1.329 | 41 | 0.992 | 139 | 0.619 (194) | 0.620 (192) | 0.500 (2) | 0.78 | 692/206/208 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.18 | 0.18 | 0.20 | 0.22 |
| random/followed | gunship | 0.47 | 0.45 | 0.46 | 0.55 |
| random/followed | strafer | 0.25 | 0.36 | 0.40 | 0.44 |
| random/hidden | fighter | 0.18 | 0.18 | 0.18 | 0.18 |
| random/hidden | gunship | 0.48 | 0.48 | 0.49 | 0.50 |
| random/hidden | strafer | 0.25 | 0.25 | 0.25 | 0.26 |
| scripted/followed | fighter | 0.18 | 0.17 | 0.18 | 0.36 |
| scripted/followed | gunship | 0.38 | 0.44 | 0.48 | 0.55 |
| scripted/followed | strafer | 0.19 | 0.33 | 0.40 | 0.40 |
