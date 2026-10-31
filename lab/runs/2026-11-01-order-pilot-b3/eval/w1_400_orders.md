**policy:ppo_bc_400.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 66 (0.85 of 1173) | 0.397 | 0.499 | 377 | 0.349 | 182 | 0.419 (1852) | 0.427 (1677) | 0.343 (175) | 0.33 | 3678/3557/2560 |
| random/hidden | 75 (0.82 of 1242) | 0.373 | 0.491 | 397 | 0.346 | 198 | 0.372 (1963) | 0.374 (1760) | 0.355 (203) | 0.30 | 3917/3778/2774 |
| scripted/followed | 63 (0.89 of 694) | 0.492 | 0.238 | 168 | 0.551 | 171 | 0.050 (239) | 0.060 (201) | 0.000 (38) | 0.03 | 1791/588/277 |
| carrier_battle/random/followed | 81 (0.81 of 705) | 0.497 | 0.462 | 241 | 0.364 | 184 | 0.465 (1128) | 0.476 (997) | 0.374 (131) | 0.37 | 2221/2152/1634 |
| carrier_battle/random/hidden | 87 (0.78 of 702) | 0.465 | 0.457 | 247 | 0.357 | 198 | 0.426 (1126) | 0.426 (995) | 0.427 (131) | 0.34 | 2283/2222/1687 |
| convoy_escort/random/followed | 32 (0.90 of 468) | 0.247 | 0.564 | 136 | 0.325 | 177 | 0.348 (724) | 0.354 (680) | 0.250 (44) | 0.28 | 1457/1405/926 |
| convoy_escort/random/hidden | 42 (0.86 of 540) | 0.233 | 0.549 | 150 | 0.328 | 199 | 0.299 (837) | 0.306 (765) | 0.222 (72) | 0.24 | 1634/1556/1087 |
| carrier_battle/scripted/followed | 75 (0.94 of 403) | 0.637 | 0.007 | 126 | 0.421 | 176 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 977/392/0 |
| convoy_escort/scripted/followed | 27 (0.82 of 291) | 0.230 | 0.933 | 42 | 0.965 | 154 | 0.050 (239) | 0.060 (201) | 0.000 (38) | 0.07 | 814/196/277 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.19 | 0.22 | 0.21 | 0.22 |
| random/followed | gunship | 0.48 | 0.48 | 0.47 | 0.50 |
| random/followed | strafer | 0.24 | 0.20 | 0.21 | 0.22 |
| random/hidden | fighter | 0.19 | 0.19 | 0.20 | 0.20 |
| random/hidden | gunship | 0.49 | 0.49 | 0.49 | 0.50 |
| random/hidden | strafer | 0.25 | 0.26 | 0.26 | 0.26 |
| scripted/followed | fighter | 0.17 | 0.25 | 0.22 | 0.22 |
| scripted/followed | gunship | 0.37 | 0.48 | 0.46 | 0.46 |
| scripted/followed | strafer | 0.14 | 0.20 | 0.21 | 0.19 |
