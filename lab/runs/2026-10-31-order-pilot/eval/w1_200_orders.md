**policy:ppo_bc_200.pt** following orders (opponent script)

| scenarios | attack: close ticks | attack: dmg share | attack: target dmg/min | guard: time within | hold: time inside | response ticks | instances a/g/h |
|---|---|---|---|---|---|---|---|
| random | 214 (0.60 of 492) | 0.425 | 224.7 | 0.194 | 0.093 | 41 (0.78 of 2628) | 969/992/1033 |
| scripted | 319 (0.70 of 839) | 0.466 | 216.4 | 0.255 | 0.008 | 25 (0.90 of 2202) | 1729/649/271 |
| carrier_battle/random | 239 (0.61 of 266) | 0.509 | 293.8 | 0.149 | 0.091 | 40 (0.77 of 1603) | 608/593/588 |
| convoy_escort/random | 206 (0.60 of 226) | 0.263 | 119.6 | 0.257 | 0.096 | 43 (0.81 of 1025) | 361/399/445 |
| carrier_battle/scripted | 568 (0.72 of 378) | 0.628 | 275.3 | 0.224 | 0.000 | 36 (0.92 of 1015) | 895/428/0 |
| convoy_escort/scripted | 129 (0.68 of 461) | 0.228 | 116.1 | 0.368 | 0.008 | 17 (0.88 of 1187) | 834/221/271 |

| scenarios | hull | none | attack | guard | hold |
|---|---|---|---|---|---|
| random | fighter | 0.19 | 0.18 | 0.19 | 0.20 |
| random | gunship | 0.48 | 0.48 | 0.48 | 0.49 |
| random | strafer | 0.24 | 0.25 | 0.26 | 0.24 |
| scripted | fighter | 0.14 | 0.21 | 0.20 | 0.15 |
| scripted | gunship | 0.39 | 0.48 | 0.46 | 0.46 |
| scripted | strafer | 0.15 | 0.24 | 0.26 | 0.26 |
