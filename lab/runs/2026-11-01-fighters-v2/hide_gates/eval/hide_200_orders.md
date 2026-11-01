**policy:ppo_bc_200.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 72 (0.84 of 1257) | 0.355 | 0.534 | 405 | 0.342 | 189 | 0.487 (2031) | 0.490 (1836) | 0.456 (195) | 0.38 | 3934/3896/2759 |
| random/hidden | 75 (0.82 of 1332) | 0.366 | 0.508 | 428 | 0.336 | 205 | 0.393 (2172) | 0.399 (1963) | 0.335 (209) | 0.32 | 4142/4124/3027 |
| scripted/followed | 87 (0.85 of 757) | 0.413 | 0.027 | 151 | 0.432 | 174 | 0.199 (221) | 0.199 (206) | 0.200 (15) | 0.06 | 2113/594/256 |
| carrier_battle/random/followed | 90 (0.82 of 700) | 0.505 | 0.455 | 237 | 0.352 | 197 | 0.551 (1055) | 0.545 (926) | 0.589 (129) | 0.42 | 2165/2093/1528 |
| carrier_battle/random/hidden | 87 (0.81 of 714) | 0.484 | 0.446 | 239 | 0.328 | 200 | 0.451 (1121) | 0.460 (993) | 0.383 (128) | 0.37 | 2204/2131/1647 |
| convoy_escort/random/followed | 45 (0.87 of 557) | 0.188 | 0.645 | 168 | 0.330 | 179 | 0.418 (976) | 0.434 (910) | 0.197 (66) | 0.34 | 1769/1803/1231 |
| convoy_escort/random/hidden | 52 (0.83 of 618) | 0.205 | 0.586 | 188 | 0.349 | 211 | 0.330 (1051) | 0.336 (970) | 0.259 (81) | 0.27 | 1938/1993/1380 |
| carrier_battle/scripted/followed | 90 (0.91 of 410) | 0.622 | 0.005 | 121 | 0.306 | 189 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 1056/405/0 |
| convoy_escort/scripted/followed | 66 (0.79 of 347) | 0.205 | 0.118 | 30 | 0.965 | 140 | 0.199 (221) | 0.199 (206) | 0.200 (15) | 0.14 | 1057/189/256 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.19 | 0.17 | 0.17 | 0.26 |
| random/followed | gunship | 0.46 | 0.42 | 0.41 | 0.49 |
| random/followed | strafer | 0.24 | 0.24 | 0.24 | 0.24 |
| random/hidden | fighter | 0.19 | 0.19 | 0.19 | 0.20 |
| random/hidden | gunship | 0.46 | 0.47 | 0.47 | 0.49 |
| random/hidden | strafer | 0.27 | 0.27 | 0.28 | 0.29 |
| scripted/followed | fighter | 0.19 | 0.17 | 0.20 | 0.21 |
| scripted/followed | gunship | 0.39 | 0.42 | 0.40 | 0.42 |
| scripted/followed | strafer | 0.17 | 0.22 | 0.24 | 0.25 |
