# from_c3_392

| Reading | Role | n | Score | vs none | Best rule | Rule vs none | vs the rule | End: station / repelled / clock |
|---|---|---|---|---|---|---|---|---|
| carrier | defender | 1024 | 0.531 | -0.033 ± 0.040 | `hold_late` | +0.185 ± 0.039 | -0.218 ± 0.038 | 0.47 / 0.39 / 0.14 |
| carrier | attacker | 1024 | 0.448 | +0.013 ± 0.042 | `carrier_push` | +0.130 ± 0.038 | -0.117 ± 0.042 | 0.45 / 0.52 / 0.03 |
| convoy | defender | 512 | 0.535 | -0.039 ± 0.058 | `hold_late` | +0.203 ± 0.053 | -0.242 ± 0.055 | 0.46 / 0.41 / 0.12 |
| convoy | attacker | 512 | 0.445 | +0.020 ± 0.055 | `carrier_push` | +0.145 ± 0.054 | -0.125 ± 0.056 | 0.45 / 0.53 / 0.03 |

## Telemetry (commander side)

| Reading | Role | First launch s (median, IQR) | Station hull then | Hangar empty s | Re-orders / min | Under an order | Carrier to station m at 10/20/30/45/60/90 s | Station hull at 10/20/30/45/60/90 s |
|---|---|---|---|---|---|---|---|---|
| carrier | defender | 2 (2–2) | 1.00 | 9 | 6.4 | 0.14 | 461 / 441 / 430 / 424 / 419 / 360 | 1.00 / 0.99 / 0.91 / 0.75 / 0.65 / 0.55 |
| carrier | attacker | 2 (2–2) | 1.00 | 6 | 8.8 | 0.11 | 449 / 417 / 382 / 323 / 262 / 191 | 1.00 / 0.99 / 0.94 / 0.82 / 0.72 / 0.58 |
| convoy | defender | 2 (2–2) | 1.00 | 8 | 4.2 | 0.09 | 461 / 440 / 429 / 423 / 419 / 353 | 1.00 / 0.99 / 0.90 / 0.76 / 0.65 / 0.58 |
| convoy | attacker | 2 (2–2) | 1.00 | 6 | 9.9 | 0.13 | 450 / 416 / 379 / 317 / 257 / 183 | 1.00 / 0.99 / 0.94 / 0.83 / 0.74 / 0.53 |

Hand rules for comparison (carrier reading): the script (`none`) launches the station's reserve at about 2 s and has emptied it by 4 s; `hold_late` waits for hull < 0.60 (first launch about 30 s, 16-match smoke: median 32 s at hull 0.54). `carrier_push`'s carrier is 396 m out at 20 s, 237 m at 45 s, 163 m at 90 s; the patrol's 420 to 460 m.

**Verdict: FAIL** (defender: below the rule, does not beat no orders, attacker: below the rule, does not beat no orders)
