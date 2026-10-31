**policy:ppo_bc_300.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 99 (0.83 of 1411) | 0.512 | 0.479 | 419 | 0.584 | 186 | 0.662 (2021) | 0.664 (1837) | 0.636 (184) | 0.55 | 4182/4003/2727 |
| random/hidden | 72 (0.83 of 1216) | 0.376 | 0.468 | 390 | 0.333 | 197 | 0.385 (1943) | 0.388 (1759) | 0.359 (184) | 0.31 | 3765/3630/2718 |
| scripted/followed | 78 (0.92 of 859) | 0.494 | 0.317 | 190 | 0.992 | 230 | 0.783 (217) | 0.790 (195) | 0.727 (22) | 0.26 | 2049/567/245 |
| carrier_battle/random/followed | 123 (0.78 of 964) | 0.684 | 0.397 | 288 | 0.755 | 198 | 0.637 (1366) | 0.641 (1232) | 0.597 (134) | 0.57 | 2786/2676/1916 |
| carrier_battle/random/hidden | 84 (0.83 of 705) | 0.463 | 0.431 | 242 | 0.334 | 196 | 0.439 (1115) | 0.446 (994) | 0.388 (121) | 0.36 | 2175/2122/1623 |
| convoy_escort/random/followed | 33 (0.94 of 447) | 0.300 | 0.658 | 131 | 0.435 | 159 | 0.713 (655) | 0.711 (605) | 0.740 (50) | 0.52 | 1396/1327/811 |
| convoy_escort/random/hidden | 36 (0.83 of 511) | 0.239 | 0.529 | 149 | 0.332 | 197 | 0.313 (828) | 0.314 (765) | 0.302 (63) | 0.25 | 1590/1508/1095 |
| carrier_battle/scripted/followed | 105 (0.92 of 653) | 0.662 | 0.086 | 147 | 0.987 | 249 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 1411/363/0 |
| convoy_escort/scripted/followed | 15 (0.94 of 206) | 0.270 | 1.096 | 43 | 0.995 | 152 | 0.783 (217) | 0.790 (195) | 0.727 (22) | 0.83 | 638/204/245 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.18 | 0.14 | 0.18 | 0.19 |
| random/followed | gunship | 0.47 | 0.45 | 0.45 | 0.55 |
| random/followed | strafer | 0.25 | 0.31 | 0.37 | 0.43 |
| random/hidden | fighter | 0.18 | 0.18 | 0.18 | 0.19 |
| random/hidden | gunship | 0.48 | 0.48 | 0.48 | 0.50 |
| random/hidden | strafer | 0.25 | 0.26 | 0.26 | 0.27 |
| scripted/followed | fighter | 0.17 | 0.12 | 0.15 | 0.28 |
| scripted/followed | gunship | 0.39 | 0.44 | 0.46 | 0.52 |
| scripted/followed | strafer | 0.20 | 0.29 | 0.37 | 0.37 |
