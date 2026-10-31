**policy:ppo_bc_100.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 63 (0.85 of 1176) | 0.378 | 0.519 | 371 | 0.345 | 177 | 0.458 (1744) | 0.469 (1597) | 0.333 (147) | 0.35 | 3593/3509/2475 |
| random/hidden | 78 (0.82 of 1237) | 0.393 | 0.468 | 398 | 0.314 | 197 | 0.387 (1944) | 0.394 (1762) | 0.324 (182) | 0.31 | 3756/3703/2717 |
| scripted/followed | 54 (0.92 of 648) | 0.484 | 0.248 | 173 | 0.537 | 179 | 0.055 (235) | 0.062 (209) | 0.000 (26) | 0.04 | 1628/621/272 |
| carrier_battle/random/followed | 81 (0.81 of 723) | 0.481 | 0.462 | 246 | 0.353 | 185 | 0.487 (1128) | 0.499 (1015) | 0.381 (113) | 0.40 | 2191/2210/1628 |
| carrier_battle/random/hidden | 87 (0.82 of 711) | 0.494 | 0.423 | 247 | 0.309 | 198 | 0.434 (1139) | 0.447 (1008) | 0.328 (131) | 0.36 | 2207/2179/1661 |
| convoy_escort/random/followed | 30 (0.92 of 453) | 0.239 | 0.632 | 125 | 0.332 | 163 | 0.404 (616) | 0.418 (582) | 0.176 (34) | 0.28 | 1402/1299/847 |
| convoy_escort/random/hidden | 44 (0.82 of 526) | 0.242 | 0.543 | 151 | 0.323 | 196 | 0.322 (805) | 0.322 (754) | 0.314 (51) | 0.25 | 1549/1524/1056 |
| carrier_battle/scripted/followed | 78 (0.96 of 390) | 0.625 | 0.023 | 128 | 0.410 | 188 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 895/409/0 |
| convoy_escort/scripted/followed | 21 (0.87 of 258) | 0.233 | 0.879 | 46 | 0.984 | 149 | 0.055 (235) | 0.062 (209) | 0.000 (26) | 0.11 | 733/212/272 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.19 | 0.21 | 0.20 | 0.22 |
| random/followed | gunship | 0.48 | 0.48 | 0.45 | 0.49 |
| random/followed | strafer | 0.23 | 0.18 | 0.18 | 0.19 |
| random/hidden | fighter | 0.18 | 0.19 | 0.19 | 0.19 |
| random/hidden | gunship | 0.48 | 0.49 | 0.49 | 0.49 |
| random/hidden | strafer | 0.25 | 0.25 | 0.25 | 0.27 |
| scripted/followed | fighter | 0.15 | 0.24 | 0.22 | 0.21 |
| scripted/followed | gunship | 0.41 | 0.49 | 0.46 | 0.43 |
| scripted/followed | strafer | 0.14 | 0.18 | 0.19 | 0.14 |
