**policy:ppo_bc_250.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 102 (0.82 of 1431) | 0.521 | 0.468 | 426 | 0.610 | 186 | 0.672 (2072) | 0.674 (1903) | 0.645 (169) | 0.57 | 4152/3991/2720 |
| random/hidden | 75 (0.84 of 1177) | 0.385 | 0.471 | 385 | 0.329 | 197 | 0.403 (1912) | 0.404 (1738) | 0.391 (174) | 0.32 | 3765/3662/2705 |
| scripted/followed | 90 (0.90 of 889) | 0.507 | 0.322 | 185 | 0.990 | 236 | 0.662 (225) | 0.670 (215) | 0.500 (10) | 0.27 | 2253/577/246 |
| carrier_battle/random/followed | 126 (0.77 of 961) | 0.704 | 0.379 | 298 | 0.765 | 199 | 0.648 (1421) | 0.655 (1295) | 0.579 (126) | 0.59 | 2720/2683/1925 |
| carrier_battle/random/hidden | 90 (0.82 of 687) | 0.482 | 0.423 | 238 | 0.337 | 196 | 0.455 (1130) | 0.460 (1012) | 0.407 (118) | 0.37 | 2194/2142/1670 |
| convoy_escort/random/followed | 33 (0.93 of 470) | 0.304 | 0.675 | 128 | 0.461 | 156 | 0.724 (651) | 0.715 (608) | 0.837 (43) | 0.52 | 1432/1308/795 |
| convoy_escort/random/hidden | 36 (0.86 of 490) | 0.233 | 0.550 | 147 | 0.317 | 198 | 0.329 (782) | 0.326 (726) | 0.357 (56) | 0.25 | 1571/1520/1035 |
| carrier_battle/scripted/followed | 111 (0.87 of 685) | 0.668 | 0.098 | 145 | 0.984 | 256 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 1534/378/0 |
| convoy_escort/scripted/followed | 15 (0.97 of 204) | 0.300 | 1.150 | 39 | 0.995 | 147 | 0.662 (225) | 0.670 (215) | 0.500 (10) | 0.87 | 719/199/246 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.18 | 0.16 | 0.19 | 0.20 |
| random/followed | gunship | 0.47 | 0.45 | 0.44 | 0.55 |
| random/followed | strafer | 0.24 | 0.30 | 0.36 | 0.43 |
| random/hidden | fighter | 0.17 | 0.18 | 0.18 | 0.18 |
| random/hidden | gunship | 0.47 | 0.48 | 0.48 | 0.48 |
| random/hidden | strafer | 0.24 | 0.25 | 0.25 | 0.26 |
| scripted/followed | fighter | 0.18 | 0.14 | 0.16 | 0.29 |
| scripted/followed | gunship | 0.41 | 0.43 | 0.45 | 0.50 |
| scripted/followed | strafer | 0.18 | 0.29 | 0.36 | 0.39 |
