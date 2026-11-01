**policy:ppo_bc_701.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 75 (0.79 of 583) | 0.310 | 0.651 | 169 | 0.290 | 202 | 0.475 (774) | 0.468 (714) | 0.567 (60) | 0.35 | 1707/1715/1154 |
| random/hidden | 78 (0.79 of 593) | 0.325 | 0.603 | 165 | 0.323 | 197 | 0.507 (720) | 0.504 (659) | 0.541 (61) | 0.34 | 1653/1604/1097 |
| scripted/followed | 94 (0.84 of 1430) | 0.419 | 0.082 | 262 | 0.331 | 199 | 0.040 (379) | 0.039 (356) | 0.043 (23) | 0.02 | 4236/1218/485 |
| carrier_battle/random/followed | 81 (0.75 of 342) | 0.428 | 0.449 | 97 | 0.226 | 224 | 0.483 (408) | 0.463 (369) | 0.667 (39) | 0.34 | 935/889/684 |
| carrier_battle/random/hidden | 84 (0.73 of 338) | 0.452 | 0.487 | 94 | 0.283 | 214 | 0.549 (401) | 0.536 (360) | 0.659 (41) | 0.38 | 892/845/672 |
| convoy_escort/random/followed | 60 (0.85 of 241) | 0.170 | 0.924 | 72 | 0.378 | 176 | 0.467 (366) | 0.472 (345) | 0.381 (21) | 0.36 | 772/826/470 |
| convoy_escort/random/hidden | 69 (0.87 of 255) | 0.176 | 0.757 | 71 | 0.377 | 176 | 0.455 (319) | 0.465 (299) | 0.300 (20) | 0.29 | 761/759/425 |
| carrier_battle/scripted/followed | 90 (0.87 of 792) | 0.593 | 0.016 | 198 | 0.160 | 219 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 2366/823/0 |
| convoy_escort/scripted/followed | 114 (0.80 of 638) | 0.214 | 0.286 | 64 | 0.944 | 158 | 0.040 (379) | 0.039 (356) | 0.043 (23) | 0.04 | 1870/395/485 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.29 | 0.22 | 0.22 | 0.26 |
| random/followed | gunship | 0.58 | 0.56 | 0.54 | 0.59 |
| random/followed | strafer | 0.28 | 0.25 | 0.30 | 0.27 |
| random/hidden | fighter | 0.30 | 0.29 | 0.28 | 0.31 |
| random/hidden | gunship | 0.59 | 0.61 | 0.63 | 0.62 |
| random/hidden | strafer | 0.27 | 0.30 | 0.31 | 0.30 |
| scripted/followed | fighter | 0.34 | 0.24 | 0.29 | 0.18 |
| scripted/followed | gunship | 0.41 | 0.56 | 0.55 | 0.38 |
| scripted/followed | strafer | 0.23 | 0.26 | 0.32 | 0.15 |
