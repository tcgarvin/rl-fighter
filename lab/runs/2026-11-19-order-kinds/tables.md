# followers_school_1052

## Scores (ordered side against the unseen side, 3 v 3)

| Rule | Matches | Ordered score | Minus no orders (paired) | fighter (cost) | strafer (cost) | gunship (cost) |
|---|---|---|---|---|---|---|
| `none` | 1152 | 0.502 ± 0.029 |  | 0.49 | 0.48 | 0.54 |
| `nearest` | 1152 | 0.136 ± 0.020 | -0.366 ± 0.035 | 0.12 (-0.367 ± 0.062) | 0.03 (-0.444 ± 0.054) | 0.26 (-0.286 ± 0.066) |
| `goto_front` | 1152 | 0.422 ± 0.028 | -0.080 ± 0.041 | 0.37 (-0.120 ± 0.071) | 0.35 (-0.125 ± 0.073) | 0.55 (0.005 ± 0.069) |
| `goto_front_deadline` | 1152 | 0.418 ± 0.028 | -0.084 ± 0.041 | 0.34 (-0.143 ± 0.072) | 0.35 (-0.121 ± 0.070) | 0.56 (0.012 ± 0.069) |
| `goto_rally` | 1152 | 0.361 ± 0.028 | -0.141 ± 0.038 | 0.15 (-0.341 ± 0.058) | 0.12 (-0.359 ± 0.057) | 0.82 (0.276 ± 0.062) |
| `defend_ward` | 1152 | 0.287 ± 0.026 | -0.215 ± 0.038 | 0.07 (-0.419 ± 0.056) | 0.08 (-0.396 ± 0.054) | 0.71 (0.171 ± 0.067) |
| `defend_ring` | 1152 | 0.288 ± 0.026 | -0.214 ± 0.038 | 0.03 (-0.461 ± 0.052) | 0.01 (-0.467 ± 0.051) | 0.83 (0.286 ± 0.061) |

## First 30 s, per match

| Side | Lost | Advance (m/s) | Under an order | Any enemy in arc | Dealt | Taken | Share on target | Defenders' share on threats | Defender to ward (m) | Wards lost | Taken as ward |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `none`, free side (unseen) | 0.72 | +1.2 | 0.92 | 0.079 | 112 | 112 | 0.74 |  |  | 0.00 | 0 |
| `none`, ordered | 0.71 | +1.2 | 0.00 | 0.079 | 112 | 112 |  |  |  | 0.00 | 0 |
| `nearest`, ordered | 1.00 | +13.5 | 0.92 | 0.111 | 90 | 150 | 0.98 |  |  | 0.00 | 0 |
| `goto_front`, ordered | 0.84 | +8.8 | 0.32 | 0.109 | 115 | 142 |  |  |  | 0.00 | 0 |
| `goto_front_deadline`, ordered | 0.85 | +5.0 | 0.17 | 0.094 | 114 | 128 |  |  |  | 0.00 | 0 |
| `goto_rally`, ordered | 0.90 | -2.5 | 0.58 | 0.071 | 77 | 120 |  |  |  | 0.00 | 0 |
| `defend_ward`, ordered | 0.49 | -2.8 | 0.61 | 0.054 | 61 | 94 |  | 0.40 | 181 | 0.35 | 58 |
| `defend_ring`, ordered | 0.42 | -7.1 | 0.93 | 0.027 | 25 | 70 |  | 0.33 | 131 | 0.42 | 67 |

## Whole match: how the orders ended (ordered side, per ship)

| Rule | Ships | Go-to: arrived | missed | died first | still open at the end | s to arrive (quartiles) | Order spent (share) | s to spent (median) | Match s |
|---|---|---|---|---|---|---|---|---|---|
| `nearest` | 3456 |  |  |  |  |  | 0.31 | 24.6 | 54 |
| `goto_front` | 3456 | 0.95 | 0.00 | 0.04 | 0.01 | 3.6 / 4.5 / 8.2 | 0.95 | 4.5 | 55 |
| `goto_front_deadline` | 3456 | 1.00 | 0.00 | 0.00 | 0.00 | 2.9 / 3.4 / 7.0 | 1.00 | 3.4 | 56 |
| `goto_rally` | 3456 | 0.89 | 0.00 | 0.09 | 0.02 | 10.6 / 14.0 / 20.8 | 0.89 | 14.0 | 54 |
| `defend_ward` | 3456 |  |  |  |  |  | 0.52 | 27.5 | 64 |
| `defend_ring` | 3456 |  |  |  |  |  | 0.39 | 31.1 | 63 |

## Over time (2-s bins, first 30 s; t is the bin's start)

| Rule | Row | 0 | 2 | 4 | 6 | 8 | 10 | 12 | 16 | 20 | 24 | 28 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `none` | gap (m) | 482 | 375 | 397 | 491 | 534 | 503 | 456 | 422 | 416 | 430 | 434 |
| `none` | ordered toward (m/s) | +15 | +18 | -22 | -22 | -3 | +11 | +7 | -1 | -0 | +3 | +9 |
| `none` | unseen toward (m/s) | +15 | +19 | -23 | -22 | -3 | +11 | +7 | -2 | +0 | +3 | +8 |
| `none` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.11 | 0.44 | 0.71 |
| `none` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.13 | 0.44 | 0.72 |
| `nearest` | gap (m) | 482 | 370 | 357 | 404 | 418 | 397 | 364 | 325 | 321 | 289 | 254 |
| `nearest` | ordered toward (m/s) | +15 | +28 | +6 | +7 | +14 | +19 | +19 | +12 | +11 | +10 | +6 |
| `nearest` | unseen toward (m/s) | +15 | +18 | -28 | -29 | -16 | -10 | -9 | -6 | +0 | +4 | +3 |
| `nearest` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.28 | 0.62 | 0.84 | 1.00 |
| `nearest` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.09 | 0.25 | 0.41 |
| `goto_front` | gap (m) | 482 | 365 | 318 | 340 | 377 | 383 | 370 | 335 | 318 | 325 | 301 |
| `goto_front` | ordered toward (m/s) | +15 | +36 | +30 | +10 | -4 | -0 | +2 | +3 | +4 | +7 | +8 |
| `goto_front` | unseen toward (m/s) | +15 | +18 | -30 | -34 | -15 | -3 | -1 | +3 | +3 | +3 | +4 |
| `goto_front` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.13 | 0.39 | 0.64 | 0.84 |
| `goto_front` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.27 | 0.54 | 0.68 |
| `goto_front_deadline` | gap (m) | 482 | 363 | 301 | 328 | 373 | 378 | 377 | 365 | 367 | 403 | 392 |
| `goto_front_deadline` | ordered toward (m/s) | +15 | +41 | +37 | +1 | -7 | -2 | -6 | -2 | -4 | +2 | +6 |
| `goto_front_deadline` | unseen toward (m/s) | +15 | +18 | -31 | -34 | -13 | -3 | -2 | +8 | +3 | +4 | +7 |
| `goto_front_deadline` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.01 | 0.14 | 0.36 | 0.63 | 0.85 |
| `goto_front_deadline` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.04 | 0.32 | 0.59 | 0.72 |
| `goto_rally` | gap (m) | 482 | 374 | 401 | 494 | 518 | 493 | 457 | 404 | 366 | 356 | 356 |
| `goto_rally` | ordered toward (m/s) | +15 | +18 | -34 | -26 | -8 | +2 | +5 | -1 | -3 | -2 | -0 |
| `goto_rally` | unseen toward (m/s) | +15 | +19 | -16 | -8 | +9 | +13 | +10 | +10 | +9 | +9 | +10 |
| `goto_rally` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.01 | 0.02 | 0.04 | 0.04 | 0.07 | 0.28 | 0.65 | 0.90 |
| `goto_rally` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 0.12 | 0.30 |
| `defend_ward` | gap (m) | 482 | 373 | 393 | 492 | 545 | 551 | 535 | 481 | 424 | 388 | 360 |
| `defend_ward` | ordered toward (m/s) | +15 | +21 | -25 | -27 | -16 | -6 | -0 | +3 | +0 | -3 | -4 |
| `defend_ward` | unseen toward (m/s) | +15 | +19 | -22 | -19 | -0 | +8 | +10 | +12 | +11 | +13 | +15 |
| `defend_ward` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.11 | 0.29 | 0.49 |
| `defend_ward` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.04 | 0.12 | 0.22 |
| `defend_ring` | gap (m) | 482 | 372 | 389 | 475 | 520 | 535 | 540 | 519 | 474 | 430 | 394 |
| `defend_ring` | ordered toward (m/s) | +15 | +22 | -24 | -21 | -16 | -16 | -11 | -6 | -6 | -7 | -9 |
| `defend_ring` | unseen toward (m/s) | +15 | +19 | -20 | -17 | +0 | +9 | +11 | +16 | +18 | +19 | +20 |
| `defend_ring` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.04 | 0.18 | 0.42 |
| `defend_ring` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.04 |

# f995_701

## Scores (ordered side against the unseen side, 3 v 3)

| Rule | Matches | Ordered score | Minus no orders (paired) | fighter (cost) | strafer (cost) | gunship (cost) |
|---|---|---|---|---|---|---|
| `none` | 576 | 0.458 ± 0.038 |  | 0.44 | 0.48 | 0.45 |
| `nearest` | 576 | 0.554 ± 0.038 | 0.095 ± 0.052 | 0.53 (0.089 ± 0.097) | 0.61 (0.125 ± 0.094) | 0.52 (0.073 ± 0.082) |
| `goto_front` | 576 | 0.380 ± 0.038 | -0.078 ± 0.053 | 0.54 (0.096 ± 0.097) | 0.18 (-0.305 ± 0.084) | 0.42 (-0.026 ± 0.083) |
| `goto_front_deadline` | 576 | 0.438 ± 0.038 | -0.021 ± 0.053 | 0.49 (0.052 ± 0.097) | 0.34 (-0.141 ± 0.096) | 0.48 (0.026 ± 0.078) |
| `goto_rally` | 576 | 0.362 ± 0.037 | -0.096 ± 0.051 | 0.55 (0.104 ± 0.099) | 0.29 (-0.190 ± 0.085) | 0.25 (-0.203 ± 0.074) |
| `defend_ward` | 576 | 0.484 ± 0.040 | 0.025 ± 0.054 | 0.61 (0.172 ± 0.101) | 0.37 (-0.109 ± 0.098) | 0.46 (0.013 ± 0.078) |
| `defend_ring` | 576 | 0.571 ± 0.039 | 0.113 ± 0.053 | 0.63 (0.190 ± 0.090) | 0.51 (0.026 ± 0.099) | 0.57 (0.122 ± 0.086) |

## First 30 s, per match

| Side | Lost | Advance (m/s) | Under an order | Any enemy in arc | Dealt | Taken | Share on target | Defenders' share on threats | Defender to ward (m) | Wards lost | Taken as ward |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `none`, free side (unseen) | 0.73 | +5.3 | 0.91 | 0.106 | 121 | 119 | 0.70 |  |  | 0.00 | 0 |
| `none`, ordered | 0.73 | +5.2 | 0.00 | 0.106 | 119 | 121 |  |  |  | 0.00 | 0 |
| `nearest`, ordered | 0.78 | +5.3 | 0.91 | 0.130 | 145 | 128 | 0.95 |  |  | 0.00 | 0 |
| `goto_front`, ordered | 0.81 | +9.0 | 0.82 | 0.158 | 118 | 139 |  |  |  | 0.00 | 0 |
| `goto_front_deadline`, ordered | 0.80 | +7.9 | 0.41 | 0.142 | 126 | 134 |  |  |  | 0.00 | 0 |
| `goto_rally`, ordered | 0.74 | +7.4 | 0.91 | 0.143 | 123 | 129 |  |  |  | 0.00 | 0 |
| `defend_ward`, ordered | 0.65 | +4.2 | 0.60 | 0.107 | 117 | 114 |  | 0.33 | 128 | 0.06 | 21 |
| `defend_ring`, ordered | 0.67 | +3.8 | 0.91 | 0.116 | 126 | 116 |  | 0.42 | 126 | 0.67 | 107 |

## Whole match: how the orders ended (ordered side, per ship)

| Rule | Ships | Go-to: arrived | missed | died first | still open at the end | s to arrive (quartiles) | Order spent (share) | s to spent (median) | Match s |
|---|---|---|---|---|---|---|---|---|---|
| `nearest` | 1728 |  |  |  |  |  | 0.46 | 19.4 | 55 |
| `goto_front` | 1728 | 0.38 | 0.00 | 0.22 | 0.40 | 9.3 / 15.3 / 31.1 | 0.38 | 15.3 | 55 |
| `goto_front_deadline` | 1728 | 0.09 | 0.91 | 0.00 | 0.00 | 3.8 / 6.3 / 7.8 | 1.00 | 9.2 | 55 |
| `goto_rally` | 1728 | 0.09 | 0.00 | 0.36 | 0.55 | 19.2 / 22.1 / 33.6 | 0.09 | 22.1 | 56 |
| `defend_ward` | 1728 |  |  |  |  |  | 0.10 | 29.7 | 58 |
| `defend_ring` | 1728 |  |  |  |  |  | 0.30 | 24.8 | 57 |

## Over time (2-s bins, first 30 s; t is the bin's start)

| Rule | Row | 0 | 2 | 4 | 6 | 8 | 10 | 12 | 16 | 20 | 24 | 28 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `none` | gap (m) | 482 | 364 | 339 | 354 | 360 | 359 | 343 | 295 | 259 | 235 | 219 |
| `none` | ordered toward (m/s) | +15 | +26 | -6 | -2 | -1 | +2 | +5 | +6 | +5 | +4 | +4 |
| `none` | unseen toward (m/s) | +15 | +26 | -6 | -3 | -3 | +1 | +5 | +7 | +6 | +5 | +4 |
| `none` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.03 | 0.13 | 0.31 | 0.52 | 0.73 |
| `none` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.02 | 0.13 | 0.33 | 0.55 | 0.73 |
| `nearest` | gap (m) | 482 | 365 | 345 | 363 | 368 | 362 | 343 | 292 | 251 | 217 | 203 |
| `nearest` | ordered toward (m/s) | +15 | +24 | -10 | -7 | -4 | -0 | +4 | +8 | +9 | +7 | +6 |
| `nearest` | unseen toward (m/s) | +15 | +27 | -3 | +1 | +1 | +5 | +8 | +6 | +5 | +2 | +1 |
| `nearest` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.16 | 0.37 | 0.59 | 0.78 |
| `nearest` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.14 | 0.35 | 0.60 | 0.81 |
| `goto_front` | gap (m) | 482 | 361 | 321 | 337 | 337 | 326 | 303 | 260 | 230 | 214 | 206 |
| `goto_front` | ordered toward (m/s) | +15 | +31 | +1 | +0 | +6 | +10 | +11 | +11 | +8 | +4 | +4 |
| `goto_front` | unseen toward (m/s) | +15 | +27 | -8 | -5 | -6 | -3 | -0 | -1 | +0 | +2 | +2 |
| `goto_front` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.16 | 0.40 | 0.64 | 0.81 |
| `goto_front` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.06 | 0.25 | 0.43 | 0.64 |
| `goto_front_deadline` | gap (m) | 482 | 361 | 321 | 337 | 337 | 326 | 307 | 272 | 237 | 221 | 211 |
| `goto_front_deadline` | ordered toward (m/s) | +15 | +31 | +1 | +0 | +6 | +9 | +7 | +9 | +6 | +3 | +3 |
| `goto_front_deadline` | unseen toward (m/s) | +15 | +27 | -8 | -5 | -6 | -2 | +0 | +2 | +3 | +4 | +3 |
| `goto_front_deadline` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.16 | 0.37 | 0.62 | 0.80 |
| `goto_front_deadline` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.11 | 0.30 | 0.51 | 0.71 |
| `goto_rally` | gap (m) | 482 | 360 | 324 | 341 | 343 | 344 | 330 | 278 | 239 | 222 | 209 |
| `goto_rally` | ordered toward (m/s) | +15 | +31 | -2 | +3 | +3 | +3 | +7 | +9 | +7 | +4 | +3 |
| `goto_rally` | unseen toward (m/s) | +15 | +26 | -9 | -7 | -7 | -2 | +3 | +5 | +3 | +2 | +1 |
| `goto_rally` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.04 | 0.16 | 0.35 | 0.55 | 0.74 |
| `goto_rally` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.10 | 0.28 | 0.49 | 0.65 |
| `defend_ward` | gap (m) | 482 | 363 | 338 | 360 | 362 | 357 | 347 | 310 | 268 | 240 | 225 |
| `defend_ward` | ordered toward (m/s) | +15 | +27 | -10 | -5 | -1 | +0 | +1 | +4 | +5 | +4 | +4 |
| `defend_ward` | unseen toward (m/s) | +15 | +26 | -6 | -1 | -0 | +2 | +4 | +8 | +7 | +4 | +3 |
| `defend_ward` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.12 | 0.30 | 0.47 | 0.65 |
| `defend_ward` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.07 | 0.26 | 0.46 | 0.63 |
| `defend_ring` | gap (m) | 482 | 362 | 337 | 362 | 372 | 374 | 357 | 305 | 264 | 236 | 219 |
| `defend_ring` | ordered toward (m/s) | +15 | +28 | -10 | -8 | -7 | -4 | +1 | +6 | +6 | +5 | +4 |
| `defend_ring` | unseen toward (m/s) | +15 | +26 | -6 | -0 | +1 | +6 | +10 | +8 | +6 | +4 | +2 |
| `defend_ring` | ordered lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.01 | 0.12 | 0.28 | 0.48 | 0.67 |
| `defend_ring` | unseen lost so far | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 | 0.02 | 0.10 | 0.30 | 0.49 | 0.67 |
