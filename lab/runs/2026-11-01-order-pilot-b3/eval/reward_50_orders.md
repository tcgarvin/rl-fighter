**policy:ppo_bc_50.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | defend: hull lost / ward-min | defend: ward-min | defend: threat share | defend: dist m | go-to: in time (n) | near | far | arrivals/min | instances a/d/g |
|---|---|---|---|---|---|---|---|---|---|---|---|
| random/followed | 63 (0.85 of 1159) | 0.380 | 0.488 | 378 | 0.345 | 182 | 0.447 (1779) | 0.449 (1628) | 0.424 (151) | 0.34 | 3657/3564/2527 |
| random/hidden | 72 (0.84 of 1213) | 0.402 | 0.493 | 387 | 0.328 | 203 | 0.377 (1906) | 0.380 (1716) | 0.353 (190) | 0.30 | 3784/3605/2718 |
| scripted/followed | 54 (0.91 of 660) | 0.505 | 0.254 | 173 | 0.509 | 175 | 0.047 (236) | 0.052 (213) | 0.000 (23) | 0.03 | 1641/609/274 |
| carrier_battle/random/followed | 84 (0.82 of 678) | 0.478 | 0.410 | 245 | 0.341 | 187 | 0.494 (1080) | 0.500 (966) | 0.447 (114) | 0.38 | 2198/2179/1606 |
| carrier_battle/random/hidden | 87 (0.82 of 704) | 0.507 | 0.439 | 239 | 0.328 | 199 | 0.438 (1055) | 0.444 (927) | 0.391 (128) | 0.35 | 2196/2096/1611 |
| convoy_escort/random/followed | 33 (0.90 of 481) | 0.242 | 0.632 | 133 | 0.352 | 174 | 0.373 (699) | 0.375 (662) | 0.351 (37) | 0.29 | 1459/1385/921 |
| convoy_escort/random/hidden | 36 (0.86 of 509) | 0.233 | 0.580 | 148 | 0.328 | 207 | 0.302 (851) | 0.304 (789) | 0.274 (62) | 0.25 | 1588/1509/1107 |
| carrier_battle/scripted/followed | 75 (0.98 of 380) | 0.656 | 0.010 | 130 | 0.367 | 177 | 0.000 (0) | 0.000 (0) | 0.000 (0) | 0.00 | 916/400/0 |
| convoy_escort/scripted/followed | 24 (0.81 of 280) | 0.220 | 1.009 | 42 | 0.979 | 167 | 0.047 (236) | 0.052 (213) | 0.000 (23) | 0.09 | 725/209/274 |

| scenarios | hull | none | attack | defend | goto |
|---|---|---|---|---|---|
| random/followed | fighter | 0.19 | 0.23 | 0.22 | 0.24 |
| random/followed | gunship | 0.47 | 0.48 | 0.46 | 0.47 |
| random/followed | strafer | 0.24 | 0.19 | 0.19 | 0.19 |
| random/hidden | fighter | 0.19 | 0.19 | 0.20 | 0.19 |
| random/hidden | gunship | 0.47 | 0.48 | 0.48 | 0.49 |
| random/hidden | strafer | 0.25 | 0.26 | 0.26 | 0.26 |
| scripted/followed | fighter | 0.15 | 0.25 | 0.23 | 0.23 |
| scripted/followed | gunship | 0.35 | 0.48 | 0.47 | 0.42 |
| scripted/followed | strafer | 0.15 | 0.18 | 0.19 | 0.16 |
