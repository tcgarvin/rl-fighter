**policy:ppo_bc_300.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 64 (0.86 of 1148) | 0.389 | 0.523 | 348 | 0.366 | 173 | 0.514 (1618) | 0.513 (1479) | 0.525 (139) | 0.39 | 3432/3343/2251 |
| random/hidden | 78 (0.80 of 1195) | 0.404 | 0.454 | 391 | 0.342 | 197 | 0.393 (1919) | 0.395 (1738) | 0.376 (181) | 0.31 | 3771/3645/2714 |
| scripted/followed | 42 (0.95 of 587) | 0.478 | 0.223 | 161 | 0.455 | 171 | 0.071 (225) | 0.073 (219) | 0.000 (6) | 0.06 | 1561/590/266 |
| carrier_battle/random/followed | 80 (0.83 of 726) | 0.499 | 0.449 | 232 | 0.345 | 185 | 0.543 (1061) | 0.543 (948) | 0.540 (113) | 0.44 | 2192/2099/1516 |
| carrier_battle/random/hidden | 90 (0.77 of 687) | 0.507 | 0.407 | 244 | 0.349 | 198 | 0.455 (1112) | 0.464 (987) | 0.384 (125) | 0.37 | 2207/2157/1651 |
| convoy_escort/random/followed | 27 (0.93 of 422) | 0.230 | 0.671 | 116 | 0.400 | 150 | 0.460 (557) | 0.460 (531) | 0.462 (26) | 0.32 | 1240/1244/735 |
| convoy_escort/random/hidden | 39 (0.83 of 508) | 0.245 | 0.531 | 147 | 0.329 | 195 | 0.307 (807) | 0.304 (751) | 0.357 (56) | 0.24 | 1564/1488/1063 |
| carrier_battle/scripted/followed | 69 (0.96 of 395) | 0.606 | 0.023 | 118 | 0.290 | 180 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 1012/387/0 |
| convoy_escort/scripted/followed | 15 (0.95 of 192) | 0.223 | 0.767 | 43 | 0.972 | 143 | 0.071 (225) | 0.073 (219) | 0.000 (6) | 0.16 | 549/203/266 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.18 | 0.28 | 0.24 | 0.29 |
| random/followed | gunship | 0.47 | 0.45 | 0.42 | 0.47 |
| random/followed | strafer | 0.23 | 0.18 | 0.18 | 0.19 |
| random/hidden | fighter | 0.19 | 0.19 | 0.19 | 0.19 |
| random/hidden | gunship | 0.47 | 0.48 | 0.48 | 0.50 |
| random/hidden | strafer | 0.25 | 0.25 | 0.25 | 0.26 |
| scripted/followed | fighter | 0.18 | 0.29 | 0.27 | 0.26 |
| scripted/followed | gunship | 0.36 | 0.47 | 0.43 | 0.38 |
| scripted/followed | strafer | 0.14 | 0.18 | 0.19 | 0.12 |
