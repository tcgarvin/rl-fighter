**policy:ppo_bc_400.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 84 (0.85 of 152) | 0.399 | 0.550 | 49 | 0.348 | 184 | 0.427 (225) | 0.421 (209) | 0.500 (16) | 0.35 | 494/446/316 |
| carrier_battle/random/followed | 90 (0.82 of 105) | 0.499 | 0.508 | 34 | 0.331 | 195 | 0.452 (135) | 0.442 (120) | 0.533 (15) | 0.35 | 301/292/203 |
| convoy_escort/random/followed | 36 (0.91 of 47) | 0.265 | 0.645 | 15 | 0.388 | 160 | 0.389 (90) | 0.393 (89) | 0.000 (1) | 0.36 | 193/154/113 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.18 | 0.23 | 0.19 | 0.24 |
| random/followed | gunship | 0.47 | 0.49 | 0.46 | 0.48 |
| random/followed | strafer | 0.24 | 0.20 | 0.22 | 0.19 |
