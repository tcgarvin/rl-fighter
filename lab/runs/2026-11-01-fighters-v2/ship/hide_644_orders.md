**policy:ppo_bc_644.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 90 (0.79 of 671) | 0.382 | 0.548 | 223 | 0.375 | 213 | 0.538 (1012) | 0.546 (917) | 0.453 (95) | 0.39 | 2104/2099/1429 |
| random/hidden | 84 (0.80 of 645) | 0.344 | 0.520 | 210 | 0.345 | 210 | 0.367 (1071) | 0.374 (973) | 0.296 (98) | 0.30 | 2009/2000/1536 |
| scripted/followed | 117 (0.83 of 1552) | 0.431 | 0.139 | 358 | 0.535 | 211 | 0.301 (471) | 0.302 (450) | 0.286 (21) | 0.09 | 4520/1468/513 |
| carrier_battle/random/followed | 132 (0.72 of 355) | 0.537 | 0.429 | 128 | 0.386 | 227 | 0.605 (577) | 0.614 (515) | 0.532 (62) | 0.46 | 1142/1113/852 |
| carrier_battle/random/hidden | 88 (0.81 of 322) | 0.451 | 0.449 | 117 | 0.335 | 204 | 0.436 (560) | 0.437 (506) | 0.426 (54) | 0.35 | 1050/1049/834 |
| convoy_escort/random/followed | 54 (0.86 of 316) | 0.195 | 0.707 | 95 | 0.360 | 196 | 0.448 (435) | 0.460 (402) | 0.303 (33) | 0.31 | 962/986/577 |
| convoy_escort/random/hidden | 57 (0.80 of 323) | 0.210 | 0.610 | 93 | 0.361 | 217 | 0.292 (511) | 0.306 (467) | 0.136 (44) | 0.24 | 959/951/702 |
| carrier_battle/scripted/followed | 129 (0.86 of 899) | 0.643 | 0.081 | 267 | 0.363 | 238 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 2501/891/0 |
| convoy_escort/scripted/followed | 54 (0.79 of 653) | 0.197 | 0.308 | 91 | 0.956 | 156 | 0.301 (471) | 0.302 (450) | 0.286 (21) | 0.20 | 2019/577/513 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.19 | 0.09 | 0.06 | 0.23 |
| random/followed | gunship | 0.48 | 0.39 | 0.37 | 0.54 |
| random/followed | strafer | 0.25 | 0.27 | 0.29 | 0.25 |
| random/hidden | fighter | 0.19 | 0.19 | 0.20 | 0.19 |
| random/hidden | gunship | 0.49 | 0.50 | 0.49 | 0.51 |
| random/hidden | strafer | 0.27 | 0.27 | 0.27 | 0.28 |
| scripted/followed | fighter | 0.18 | 0.08 | 0.07 | 0.18 |
| scripted/followed | gunship | 0.47 | 0.38 | 0.34 | 0.47 |
| scripted/followed | strafer | 0.19 | 0.25 | 0.30 | 0.26 |
