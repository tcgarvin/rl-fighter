## Scores (ordered side against the unseen side)

| k v k | rule | matches | score | minus no orders, paired | minus scripted, paired | fighter | strafer | gunship |
|---|---|---|---|---|---|---|---|---|
| 3 | scripted | 1152 | 0.235 ± 0.024 | -0.227 ± 0.037 |  | 0.29 | 0.27 | 0.14 |
| 3 | nearest | 1152 | 0.250 ± 0.025 | -0.211 ± 0.037 | 0.016 ± 0.033 | 0.27 | 0.29 | 0.18 |
| 3 | none | 1152 | 0.461 ± 0.028 |  | 0.227 ± 0.037 | 0.47 | 0.44 | 0.48 |

## First 30 s, per side

Shares are of a ship's time alive in the window. Damage is per match (hull and shield), split by whether the other ship is the ship's own (seen or hidden) target.

| k | rule | side | lost /match | under order | target in arc | other in arc | any in arc | target is nearest | m to target | m to nearest other | taken from target | taken from others | taken from behind | dealt to target | dealt to others |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | scripted | ordered | 0.76 | 0.91 | 0.126 | 0.073 | 0.176 | 0.52 | 344 | 352 | 144 | 86 | 45 | 118 | 59 |
| 3 | scripted | unseen | 0.63 | 0.91 | 0.126 | 0.067 | 0.165 | 0.53 | 345 | 354 | 123 | 54 | 30 | 160 | 70 |
| 3 | nearest | ordered | 0.78 | 0.91 | 0.171 | 0.028 | 0.175 | 0.93 | 305 | 384 | 201 | 25 | 40 | 179 | 6 |
| 3 | nearest | unseen | 0.68 | 0.91 | 0.125 | 0.064 | 0.164 | 0.55 | 344 | 356 | 131 | 55 | 29 | 158 | 68 |
| 3 | none | ordered | 0.66 | 0.00 | 0.000 | 0.135 | 0.135 | 0.00 | 0 | 0 | 0 | 188 | 28 | 0 | 185 |
| 3 | none | unseen | 0.65 | 0.91 | 0.102 | 0.050 | 0.135 | 0.50 | 381 | 384 | 131 | 54 | 27 | 129 | 59 |

## Movement and shooting, first 30 s, per side

| k | rule | side | speed (m/s) | toward enemy fleet (m/s) | m from own centroid | trigger held | trigger held, enemy in arc | hits per s in arc | m per hit | landed first hit | retreating | of which nose on nearest enemy | m/s toward own target |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | scripted | ordered | 40 | 7.9 | 82 | 0.29 | 0.48 | 3.6 | 121 | 0.53 | | | |
| 3 | scripted | unseen | 40 | 2.1 | 91 | 0.20 | 0.67 | 4.8 | 125 | 0.46 | | | |
| 3 | nearest | ordered | 40 | 7.5 | 84 | 0.31 | 0.46 | 3.8 | 122 | 0.57 | | | |
| 3 | nearest | unseen | 40 | 2.5 | 92 | 0.21 | 0.67 | 4.8 | 124 | 0.42 | | | |
| 3 | none | ordered | 41 | 3.7 | 84 | 0.17 | 0.62 | 4.7 | 126 | 0.48 | | | |
| 3 | none | unseen | 41 | 4.1 | 85 | 0.17 | 0.62 | 4.8 | 127 | 0.46 | | | |

## Timeline, 2-s bins (first 30 s)


3 v 3, scripted:

| t (s) | 0 | 2 | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 20 | 22 | 24 | 26 | 28 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fleet gap (m) | 482 | 373 | 382 | 411 | 409 | 392 | 369 | 347 | 325 | 302 | 280 | 263 | 252 | 243 | 235 |
| ordered: toward (m/s) | 15 | 19 | -10 | 5 | 7 | 9 | 10 | 11 | 11 | 11 | 9 | 7 | 5 | 4 | 3 |
| unseen: toward (m/s) | 15 | 21 | -17 | -11 | -5 | -1 | 1 | 2 | 3 | 3 | 4 | 4 | 5 | 6 | 6 |
| ordered: dealt /match | 0 | 0 | 0 | 0 | 2 | 7 | 12 | 13 | 15 | 19 | 22 | 23 | 22 | 21 | 21 |
| unseen: dealt /match | 0 | 0 | 0 | 0 | 2 | 8 | 13 | 15 | 18 | 22 | 26 | 29 | 31 | 33 | 34 |
| ordered: lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.07 | 0.16 | 0.26 | 0.37 | 0.46 | 0.55 | 0.63 | 0.70 | 0.76 |
| unseen: lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.05 | 0.13 | 0.22 | 0.31 | 0.38 | 0.45 | 0.52 | 0.58 | 0.63 |

3 v 3, nearest:

| t (s) | 0 | 2 | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 20 | 22 | 24 | 26 | 28 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fleet gap (m) | 482 | 373 | 382 | 414 | 412 | 395 | 372 | 348 | 323 | 300 | 278 | 263 | 252 | 245 | 237 |
| ordered: toward (m/s) | 15 | 19 | -10 | 3 | 6 | 8 | 10 | 11 | 11 | 10 | 9 | 7 | 5 | 4 | 3 |
| unseen: toward (m/s) | 15 | 21 | -17 | -11 | -4 | 1 | 2 | 3 | 3 | 3 | 3 | 4 | 5 | 5 | 6 |
| ordered: dealt /match | 0 | 0 | 0 | 0 | 2 | 7 | 11 | 13 | 16 | 19 | 24 | 24 | 23 | 23 | 23 |
| unseen: dealt /match | 0 | 0 | 0 | 0 | 1 | 7 | 12 | 15 | 18 | 21 | 26 | 29 | 30 | 32 | 34 |
| ordered: lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.07 | 0.16 | 0.27 | 0.36 | 0.46 | 0.56 | 0.64 | 0.71 | 0.78 |
| unseen: lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.05 | 0.12 | 0.21 | 0.30 | 0.39 | 0.46 | 0.54 | 0.62 | 0.68 |

3 v 3, none:

| t (s) | 0 | 2 | 4 | 6 | 8 | 10 | 12 | 14 | 16 | 18 | 20 | 22 | 24 | 26 | 28 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| fleet gap (m) | 482 | 372 | 385 | 431 | 436 | 422 | 400 | 384 | 372 | 353 | 334 | 317 | 307 | 301 | 297 |
| ordered: toward (m/s) | 15 | 20 | -17 | -6 | -0 | 3 | 4 | 4 | 5 | 5 | 5 | 5 | 5 | 5 | 5 |
| unseen: toward (m/s) | 15 | 20 | -17 | -6 | -0 | 3 | 5 | 5 | 5 | 5 | 6 | 6 | 5 | 5 | 5 |
| ordered: dealt /match | 0 | 0 | 0 | 0 | 0 | 5 | 12 | 13 | 15 | 18 | 21 | 23 | 26 | 26 | 26 |
| unseen: dealt /match | 0 | 0 | 0 | 0 | 0 | 5 | 12 | 14 | 15 | 18 | 21 | 24 | 25 | 26 | 27 |
| ordered: lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.12 | 0.20 | 0.29 | 0.37 | 0.44 | 0.53 | 0.60 | 0.66 |
| unseen: lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.11 | 0.20 | 0.26 | 0.35 | 0.43 | 0.50 | 0.59 | 0.65 |

## The first ship lost in each match

| k | rule | side lost it first | of those: killed by its own target | killer behind its beam | its target in arc, last 2 s | enemies hitting it, last 3 s | its target off the nose (median deg) | m to target | m to killer | t (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| 3 | scripted | ordered: 0.56 | 0.52 | 0.24 | 0.53 | 1.69 | 64 | 115 | 96 | 28.8 |
| 3 | scripted | unseen: 0.44 | 0.45 | 0.31 | 0.55 | 1.87 | 33 | 91 | 85 | 28.6 |
| 3 | nearest | ordered: 0.58 | 0.76 | 0.24 | 0.78 | 1.64 | 20 | 87 | 94 | 28.4 |
| 3 | nearest | unseen: 0.42 | 0.45 | 0.32 | 0.55 | 1.87 | 40 | 96 | 86 | 28.5 |
| 3 | none | ordered: 0.49 | nan | 0.24 | nan | 1.71 | nan | nan | 100 | 30.5 |
| 3 | none | unseen: 0.45 | 0.54 | 0.22 | 0.62 | 1.69 | 55 | 114 | 97 | 29.9 |
