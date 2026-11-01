# Convoy balance for `reward_300`

Plan §1's blocker: with `reward_300` on both sides, convoy attackers won about 97 % in a
median 33 s. Target (live default rosters, `reward_300` mirror, scripted commanders,
n >= 258 per roster): attackers 35-65 % on every roster, median >= 45 s, time-limit rate
<= 0.10.

**Result: every roster is in the band, by rosters alone.** No hull, route or clock
changed, no `SIM_VERSION` bump, and the golden traces did not move (they build their own
fleets; `cargo test -p sim` passes unchanged). Every run is at 450 m, `SIM_VERSION` 6.

## Rosters

Six a side on all three, and only the freighter count varies. `F S F G F S` escorts,
`F F S G F S` raiders. `5 freighters` stays first (the page plays the first roster half
the time). 7 freighters is 19 ships, under the 20-ship cap; the last freighter starts at
`y = -439 m`, just inside the 450 m arena. 8 freighters would start outside it, so it was
surveyed but not used.

## Before and after (table of record: seed 530000, n = 258 per roster)

Attackers' share of wins, median and p90 length, and how matches end. Time-limit and draw
rates are 0.000 in all twelve rows.

`reward_300` mirror, old rosters:

| roster | attackers | median s | p90 s | eliminated | through | destroyed |
|---|---|---|---|---|---|---|
| 4 freighters, F S F v 6 | **1.000** | **29** | 33 | 0.00 | 0.00 | 1.00 |
| 3 freighters, F S F G v 5 | **0.953** | **39** | 53 | 0.05 | 0.00 | 0.95 |
| 5 freighters, F S F G v 8 | **0.992** | **34** | 43 | 0.01 | 0.00 | 0.99 |

`reward_300` mirror, new rosters (live `rlf_sim.mission_rosters`, checked equal to these):

| roster | attackers | median s | p90 s | eliminated | through | destroyed |
|---|---|---|---|---|---|---|
| 5 freighters | 0.632 | 48 | 68 | 0.33 | 0.04 | 0.63 |
| 6 freighters | 0.504 | 50 | 74 | 0.43 | 0.06 | 0.50 |
| 7 freighters | 0.415 | 59 | 75 | 0.43 | 0.15 | 0.41 |

Standard error of a win rate here is about 0.03. An independent sample of the same three
rosters (seed 520000) gave 0.574 / 0.508 / 0.430 and medians 49 / 49 / 59, so
`5 freighters` is near the top of the band rather than over it.

v1 mirror, for the record:

| rosters | roster | attackers | median s | p90 s | eliminated | through | destroyed |
|---|---|---|---|---|---|---|---|
| old | 4 freighters | 0.612 | 66 | 72 | 0.00 | 0.39 | 0.61 |
| old | 3 freighters | 0.550 | 65 | 68 | 0.03 | 0.41 | 0.55 |
| old | 5 freighters | 0.488 | 71 | 75 | 0.00 | 0.51 | 0.49 |
| new | 5 freighters | **0.004** | 72 | 72 | 0.16 | 0.83 | 0.00 |
| new | 6 freighters | **0.004** | 75 | 75 | 0.21 | 0.79 | 0.00 |
| new | 7 freighters | **0.000** | 75 | 75 | 0.17 | 0.83 | 0.00 |

**The new rosters are balanced for this pilot, not for v1.** A past-champion replay of v1
(`/?champion=2026-10-30-fleet-pilot-v1`) now always gets its convoy through. It still plays
the mission to a proper end, so it is left as is; the rosters are in the sim, not in the
bundle, and a replay flies the current build's.

## How the rosters were found

`reward_300` mirror, sampled pilots, n = 60 per candidate (standard error 0.06), then the
best seven at n = 258. Attackers / median s:

| candidate | n = 60 | n = 258 |
|---|---|---|
| 4F, F S F G v F F S G F S | 1.00 / 33 | |
| 4F, F S F G F v F F S G F S | 0.98 / 33 | |
| 4F, F S F G F S v F F S G F S | 0.60 / **41** | |
| 4F, F S F G F S F v F F S G F S | 0.50 / **39** | |
| 4F, F S F G v F S G F | 0.85 / 41 | |
| 3F, F S F G F v F S F G F | 0.83 / 45 | |
| 3F, F S F G F S v F S F G F | 0.40 / **41** | |
| 3F, F S F G F S F v F F S G F S | 0.63 / **44** | |
| 5F, F S F G F S v F F S G F S F F | 0.82 / 44 | |
| 5F, F S F G F S F F v F F S G F S F | 0.27 / 47 | |
| 5F, F S F G F S v F F S G F S | 0.57, 0.48 / 48, 45 | 0.574 / 49 |
| 5F, F F S G F S v F F S G F F | 0.62 / 53 | 0.628 / 52 |
| 5F, F S F G F S F v F F S G F S | 0.42 / 48 | 0.434 / 48 |
| 6F, F S F G F S v F F S G F S | 0.53 / 52 | 0.508 / 49 |
| 6F, F S F G F S F v F F S G F S F | 0.47 / 50 | 0.453 / 46 |
| 6F, F S F G F v F F S G F | 0.83 / 51 | |
| 7F, F S F G F S v F F S G F S | 0.35 / 55 | 0.430 / 59 |
| 7F, F S F G F S v F F S G F S F | 0.60 / 55 | 0.516 / 55 |
| 7F, F S F G F v F F S G F | 0.73 / 62 | |
| 8F, F S F G F S v F F S G F S | 0.35 / 58 | |

What decided it:

- **Win rate is set by the escort count.** This pilot's raiders kill a freighter so fast
  that three or four escorts never matter: 6 escorts against 6 raiders is where it turns.
- **Length is set by the freighter count.** Both ways to win are fast with this pilot,
  and a raid that needs two kills (3 or 4 freighters) is over in about 40 s even when
  balanced, under the 45 s bound. Three kills (5 or 6) take about 50 s, four kills (7)
  about 60 s. So the bound rules out 3 and 4 freighters, not the win rate.
- **The convoy rarely gets through.** Through takes 72-75 s and most matches are over
  sooner: 4-15 % of matches, 7 freighters the most. Defenders mostly win by eliminating
  the raid (about 45 s), which reads differently from v1's convoy (0.4-0.5 through) on
  screen: escorts win a dogfight rather than shepherd the convoy home. Getting more
  convoys through would take a hull or route change, which was not needed for the target.

## Retuned for the pilot that shipped: `f995_701`

The rosters above were tuned for `reward_300`. In `f995_701`'s mirror on them (seed 530000,
n = 774) attackers won only 0.19, median 43 s, ending eliminated 0.78. It is a much better
defender, so plan §4's "retuned by the roster" applied. Only the escort count changed:
**5, 6 or 7 freighters; `F S F G` escorts v `F F S G F S` raiders**. Script:
`convoy_survey.py`, sampled pilots, seed 540000.

| candidate | n = 120 attackers / median s | n = 516 attackers / median s |
|---|---|---|
| 5F, F S F G F v F F S G F S | 0.383 / 42 | |
| 6F, F S F G F v F F S G F S | 0.325 / 44 | |
| 7F, F S F G F v F F S G F S | 0.333 / 52 | |
| 5F, F S F G F S v F F S G F S F | 0.308 / 42 | |
| 6F, F S F G F S v F F S G F S F | 0.283 / 43 | |
| 7F, F S F G F S v F F S G F S F | 0.242 / 48 | |
| 5F, F S F G v F F S G F S | 0.550 / 41 | **0.616 / 42** |
| 6F, F S F G v F F S G F S | 0.633 / 43 | **0.589 / 44** |
| 7F, F S F G v F F S G F S | 0.475 / 51 | **0.545 / 50** |

All three are inside 35-65 %. Convoys get through in 3-6 % of matches; a defence nearly
always wins by killing the raid. Medians of 42-50 s are shorter than the 45 s the
`reward_300` pass aimed for at the low end, and above the plan's 30 s call-out.
