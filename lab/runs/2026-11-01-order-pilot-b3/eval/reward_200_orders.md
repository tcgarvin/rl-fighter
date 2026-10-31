**policy:ppo_bc_200.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 66 (0.86 of 1104) | 0.408 | 0.517 | 363 | 0.360 | 171 | 0.494 (1702) | 0.494 (1581) | 0.496 (121) | 0.38 | 3503/3448/2367 |
| random/hidden | 78 (0.79 of 1212) | 0.391 | 0.500 | 393 | 0.337 | 199 | 0.404 (1881) | 0.407 (1682) | 0.377 (199) | 0.31 | 3806/3668/2645 |
| scripted/followed | 51 (0.94 of 613) | 0.492 | 0.239 | 166 | 0.490 | 171 | 0.073 (233) | 0.076 (223) | 0.000 (10) | 0.07 | 1495/585/275 |
| carrier_battle/random/followed | 78 (0.82 of 698) | 0.504 | 0.447 | 239 | 0.346 | 180 | 0.518 (1075) | 0.513 (979) | 0.573 (96) | 0.41 | 2200/2170/1554 |
| carrier_battle/random/hidden | 93 (0.78 of 689) | 0.483 | 0.453 | 246 | 0.332 | 199 | 0.463 (1083) | 0.470 (945) | 0.413 (138) | 0.36 | 2245/2188/1602 |
| convoy_escort/random/followed | 27 (0.93 of 406) | 0.273 | 0.651 | 124 | 0.382 | 153 | 0.453 (627) | 0.463 (602) | 0.200 (25) | 0.34 | 1303/1278/813 |
| convoy_escort/random/hidden | 39 (0.81 of 523) | 0.250 | 0.580 | 147 | 0.344 | 199 | 0.325 (798) | 0.327 (737) | 0.295 (61) | 0.25 | 1561/1480/1043 |
| carrier_battle/scripted/followed | 75 (0.96 of 398) | 0.624 | 0.018 | 123 | 0.335 | 180 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 886/393/0 |
| convoy_escort/scripted/followed | 15 (0.89 of 215) | 0.240 | 0.867 | 43 | 0.982 | 143 | 0.073 (233) | 0.076 (223) | 0.000 (10) | 0.19 | 609/192/275 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.19 | 0.26 | 0.24 | 0.28 |
| random/followed | gunship | 0.48 | 0.46 | 0.44 | 0.49 |
| random/followed | strafer | 0.23 | 0.17 | 0.17 | 0.17 |
| random/hidden | fighter | 0.19 | 0.19 | 0.20 | 0.20 |
| random/hidden | gunship | 0.47 | 0.48 | 0.49 | 0.50 |
| random/hidden | strafer | 0.24 | 0.26 | 0.25 | 0.26 |
| scripted/followed | fighter | 0.16 | 0.28 | 0.25 | 0.28 |
| scripted/followed | gunship | 0.34 | 0.48 | 0.45 | 0.41 |
| scripted/followed | strafer | 0.14 | 0.16 | 0.18 | 0.12 |
