# Fighters v2: a longer horizon made a much stronger fighter; order-only pay did not make a follower

Run the night of 2026-10-31 to 11-01, `SIM_VERSION` 6, plan: `plan.md` (arms, gates and
pick rule fixed before any eval). **`f995_701` promoted and deployed**, replacing
`reward_300`, which had been promoted and deployed earlier the same night.

<!-- summary: Plain PPO with no script pull, a constant learning rate and discount 0.995 beat the previous champion 0.71 of missions on a fresh seed and now flies the live page. Paying ordered pilots only for their orders moved go-to arrival by 0.17 but dropped its win rate against that champion to 0.11. Scripted pilots under random orders beat the scripted commander 0.75 of carrier battles, so a better commander has real room once pilots follow. -->

Verdict: **gate F passes, gate H fails, gate O waived for `reward_300` only.**

## What ran

Three arms from `reward_300`, no script pull, constant LR, about 40 s per update, 22:45 to
05:30, stopped by the clock (plan §3; daylight saving ended overnight, which gave an extra
hour).

| arm | gamma | order pay | stopped at update |
|---|---|---|---|
| `f99` | 0.99 | none | 696 |
| `f995` | 0.995 | none | 701 |
| `hide` | 0.99 | only the order, on ordered rows, with a KL anchor to `reward_300` | 644 |

## Screen (mean mission win vs R, n = 258 per mission; it picks, it decides nothing)

| candidate | mean | carrier | convoy |
|---|---|---|---|
| f995_400 | 0.702 | 0.736 | 0.667 |
| f995_701 | 0.698 | 0.756 | 0.640 |
| f995_200 | 0.698 | 0.721 | 0.674 |
| f99_696 | 0.657 | 0.663 | 0.651 |
| f99_200 | 0.595 | 0.616 | 0.574 |
| f99_400 | 0.492 | 0.589 | 0.395 |
| hide_200 | 0.388 | 0.306 | 0.469 |
| hide_400 | 0.250 | 0.287 | 0.213 |
| hide_644 | 0.109 | 0.105 | 0.112 |

`f995` reached 0.70 by update 200 and stayed there. `f99` reached 0.66 only at its last
checkpoint, and dipped to 0.49 at 400, so one seed of it is noisy. This is one seed per
arm, and the gap is a single comparison.

## Gate F (fresh seed 310000, n = 1032 per mission, `reward_300` rebalanced rosters)

| candidate | F | mean vs R | carrier | convoy | dm vs R | dm vs script |
|---|---|---|---|---|---|---|
| f995_400 | ✓ | 0.698 | 0.752 | 0.644 | 0.658 | 0.892 |
| f995_701 | ✓ | 0.714 | 0.771 | 0.658 | 0.741 | 0.904 |

Health for `f995_701`: no NaN or stuck matches, outside arena under 0.006, time limit 0.001
in carrier battles and 0 in convoys. Median match 82 s carrier, 48 s convoy. Engine duty
(reported, not gated): carrier fighter 0.19, strafer 0.27, gunship 0.57.

After the convoy retune below, `f995_701` wins 0.568 of convoys vs R (n = 1032), so the mean
vs R on the final rosters is about 0.67. Against v1 on the final rosters: 0.863 carrier,
0.965 convoy (n = 516); deathmatch 0.812.

## Gate H: `hide_200` fails O and M

| candidate | O | M | D | H | mission win vs v1 | vs w1_400 | attack share | threat share | go-to in time |
|---|---|---|---|---|---|---|---|---|---|
| hide_200 | ✗ | ✗ | ✓ | ✓ | 0.668 | 0.382 | 0.355 | 0.342 | 0.487 |

The screen selects on strength, so it sent the least changed checkpoint to the gate. To
answer the arm's actual question I also measured following on its last checkpoint (reported,
not gated; bars are hidden + 0.05, go-to 0.7):

| pilot, random commander | attack share, shown / hidden | threat share, shown / hidden | go-to in time, shown / hidden |
|---|---|---|---|
| script | 0.470 | 0.650 | 0.898 |
| hide_644 | 0.382 / 0.344 | 0.375 / 0.345 | 0.538 / 0.367 |
| reward_300 (B3) | 0.39 / 0.40 | 0.37 / 0.34 | 0.51 / 0.39 |
| f995_701 | 0.310 / 0.325 | 0.290 / 0.323 | 0.475 / 0.507 |

So 644 updates of order-only pay moved go-to by 0.17 and the others by 0.03-0.04, while the
win rate vs R fell to 0.109 and the fire rate fell from about 0.6 to about 0.38. Pilots
stopped shooting rather than started following: fire still costs, and a hit off target pays
nothing. KL to the parent on ordered rows kept growing, so behaviour changed a lot, in the
wrong direction. This is one seed, one anchor weight and one shaping of the pay.

`f995_701` shows no following at all, as expected with no order pay.

## How much the commander can matter (`commander_value*.py`, `*.jsonl`)

Same pilot both sides; side b under the scripted commander with orders shown; side a's
command varies. Side a's win rate:

| pilot | side a command | carrier | n |
|---|---|---|---|
| script | scripted (control) | 0.489 | 1032 |
| script | **random orders** | **0.748** | 1032 |
| reward_300 | scripted (control) | 0.531 | 516 |
| reward_300 | hidden | 0.469 | 516 |
| reward_300 | random orders | 0.479 | 516 |
| transit_300 | scripted (control) | 0.486 | 516 |
| transit_300 | hidden | **0.992** | 258 |
| transit_300 | random orders | 0.806 | 258 |

- With pilots that ignore orders, command changes nothing, as `reward_300` shows.
- With pilots that follow, command swings carrier wins by 26 points, and **the scripted
  commander loses to random orders**. It is a weak commander. Its squads are mostly a third
  on defence and a strike on the carrier, and the cause of the gap has not been studied.
- `transit_300` hidden wins 0.992: seeing the scripted commander's orders is what cripples
  it, which is the pull's damage made visible.
- Convoy with script pilots is not informative: on the first rebalanced rosters defenders won all of it, and it was not rerun on the final ones.

## Convoy

Rebalanced twice: for `reward_300`, then for `f995_701`, whose mirror had attackers at 0.19
on the first rosters. Final: 5, 6 or 7 freighters, `F S F G` v `F F S G F S`; attackers
0.616 / 0.589 / 0.545, medians 42-50 s. `convoy_balance.md` has both passes.

## Unresolved

- Pilots ignore orders on the live page, and `Show commands` draws them anyway. `/pilot/`
  says so; the live caption does not.
- Convoys rarely get through: 3-6 % of matches in the mirror. A defence nearly always wins
  by killing the raid.
- Replays of past champions fly today's rosters, and they are lopsided for them.
- `ORDER_SHAPING_GAMMA` is hard-coded to 0.99 (`reward.rs`), so any order pay at gamma 0.995
  would be biased until it follows the training gamma.
- Inference was not measured on a phone. The `/pilot/` weights are the same size as
  `reward_300`'s, and the biggest roster has fewer strike craft now.
