# Fighters v2: a longer horizon made a much stronger fighter; order-only pay did not make a follower

Run the night of 2026-10-31 to 11-01, `SIM_VERSION` 6 (the sixth version of the game's
rules, with attack, defend and go-to orders), plan: `plan.md` (arms, gates and pick rule
fixed before any eval). **`f995_701` promoted and deployed**: it became the pilot on
the project's website, replacing `reward_300`, which had been promoted and deployed
earlier the same night.

<!-- summary: We trained the live pilot further by plain trial and error, with nothing pulling it toward a hand-written pilot. The copy that weighed rewards further into the future became much stronger, beat the previous live pilot in 0.71 of missions on fresh matches, and now flies the live page. A copy paid only for its orders whenever it had one got a little better at reaching go-to points (up 0.17) but won only 0.11 against that previous pilot. Hand-written pilots given random orders beat the hand-written commander in 0.75 of carrier battles, so a better commander has real room once pilots follow. -->

Three runs in a row had tried to teach pilots to follow orders, and none had a pilot
that both follows and fights. But each one that trained without pulling the pilot toward
a hand-written pilot made a stronger fighter. So this night ran more of that plain
training, in three versions. The question for two of them was simply whether we could
make a better fighter, and one, which plans further ahead, did: `f995_701` beats the
pilot it started from in 0.71 of missions and now flies the live page. The third tried
a different way to get orders followed, paying a pilot only for its order whenever it
had one. It got a little better at go-to orders and much worse at winning. A side
measurement found that the hand-written commander gives worse orders than random ones,
when pilots follow them.

## Where this fits

RL Fighter is a space-combat game where every small ship is flown by a neural network,
the **pilot**, that learned to fly by trial and error. The project's website plays
matches forever on its front page, the **live page**. The small piloted ships are the
**fighter** and **strafer**, with guns fixed to the nose, and the slower **gunship**,
whose turrets aim on their own. Besides team deathmatch (small ships only, 1 to 4 a
side, until one side is destroyed) there are two missions. In a **carrier battle** each
side has a carrier that launches its small ships, and a side wins by destroying the
enemy carrier. In a **convoy escort** one side's escorts guard freighters flying to a
jump point and the other side attacks, winning if it destroys at least half of them.
Each side's **commander** gives its squads orders: attack a named enemy, defend a
friendly ship (the **ward**, the one to protect), or go to a point. Three runs had
tried to get pilots to follow them: [run 1](../2026-10-31-order-pilot/results.md) made a strong pilot that ignored orders, and
[B2b](../2026-10-31-order-pilot-b2b/results.md) and
[B3](../2026-11-01-order-pilot-b3/results.md) pulled the pilot toward the hand-written,
"scripted", pilot (**the script**). That taught following and wrecked fighting. B3's
`reward` arm, trained without the pull, gave `reward_300` (that arm saved at training
update 300). It wins 0.726 of missions against [fleet pilot
v1](../2026-10-30-fleet-pilot/results.md), the pilot then on the live page, but follows orders little. Going to bed, the owner asked for experiments
with a better chance of putting something live by morning, maybe just better fighters.
On that instruction the order-following gate was waived for `reward_300` alone, and it
went live earlier this night (`shipping.md`). This run is the rest of that request.

Pilot names in this entry are the training line followed by the update a copy was saved
at: `f995_701` is the `f995` arm at update 701.

## What ran

Three **arms** (versions of the experiment, trained side by side) from `reward_300`,
with no script pull and a constant learning rate (the size of each adjustment to the
network; earlier runs shrank it to zero by the end). About 40 s per update (one batch
of matches played, then one adjustment), 22:45 to 05:30, stopped by the clock (plan §3; daylight saving ended overnight, which gave an extra hour).

"Gamma" is the discount, how far ahead the pilot weighs future reward. 0.99 weighs about
the next 3.3 s, 0.995 about 6.7 s.

| arm | gamma | order pay | stopped at update |
|---|---|---|---|
| `f99` | 0.99 | none | 696 |
| `f995` | 0.995 | none | 701 |
| `hide` | 0.99 | only the order, whenever the ship has one, with a KL anchor to `reward_300` | 644 |

`hide` tests "reward hiding": on rows (moments of training) where a ship has an order,
the usual pay for damage dealt is switched off. The order pays instead: for damage to
the attack target or to enemies threatening the ward, and for reaching a go-to point.
Damage taken, the cost of firing, and the win or loss at the end still count. A "KL
anchor", a training term that penalises the pilot for moving its choices far from
another network's, kept it close to `reward_300` on moments with no order.

<!-- figure-idea: shared: a training night. One parent pilot, three arms trained side by side, a saved copy every 50 updates, a quick screen of a few copies, then the gate on fresh matches deciding what goes live. Helps here because the entry moves from arms to screen to gates. -->

## How the night was judged

The plan fixed two tests before any copy was measured. **R** is the reigning pilot,
`reward_300`.

- **Gate F, a better fighter**, for an `f99` or `f995` copy: a mean mission win of at
  least 0.55 against R and at least 0.47 in each mission, a deathmatch win of at least
  0.50 against R and 0.85 against the script, and healthy matches (none broken or stuck,
  few outside the arena or out of time).
- **Gate H, following at a price we can accept**, for a `hide` copy: B3's four bars,
  unchanged. O, following, measured under the **random commander**, which hands out
  random orders. "Attack share" is the share of a ship's damage under an attack order
  that lands on its target, "threat share" the share of a defender's damage that lands
  on enemies threatening its ward, and "go-to in time" the share of go-to orders
  reached by a deadline set from the distance. The bars: attack share and threat share
  each at least the same pilot's score with its orders hidden + 0.05, and go-to in time
  at least 0.7. M, missions: at least 0.47 against v1 in each mission, 0.52 on
  average, and 0.45 on average against `w1_400`, run 1's best pilot. D,
  deathmatch: at least 0.85 against the script and 0.45 against v1. H, health.

Verdict: **gate F passes, gate H fails, gate O waived for `reward_300` only.** (Gate O,
the order-following part of B3's bars, was the one `reward_300` failed when it went
live earlier in the night.)

## Screen (mean mission win vs R, n = 258 per mission; it picks, it decides nothing)

The screen played 258 matches of each mission
(carrier battle and convoy escort) against R for a few saved copies of each arm, to
choose which go on to the gates. Each number is the share of matches won, where 0.5 is
an even fight and a draw counts half. "Mean" is the average of the two missions.

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
checkpoint, and dipped to 0.49 at 400, so one seed of it is noisy. This is one seed (one
random setup) per arm, and the gap is a single comparison.

<div data-figure="diagram" data-name="discount" data-caption="The f99 and f995 arms differed only in the discount, 0.99 against 0.995. The 0.999 curve is from a later run."></div>

## Gate F (fresh seed 310000, n = 1032 per mission, `reward_300` rebalanced rosters)

Gate F asks whether an `f99` or `f995` copy is a better fighter than R, by the bars
above. It plays fresh matches (a new random seed), so a copy that won the screen by luck
does not get the same luck again. A **roster** is the lineup of ships each side gets,
and these matches used the convoy rosters as first rebalanced for `reward_300` (see
Convoy below). "dm" is deathmatch.

| candidate | F | mean vs R | carrier | convoy | dm vs R | dm vs script |
|---|---|---|---|---|---|---|
| f995_400 | ✓ | 0.698 | 0.752 | 0.644 | 0.658 | 0.892 |
| f995_701 | ✓ | 0.714 | 0.771 | 0.658 | 0.741 | 0.904 |

Health for `f995_701`: no NaN or stuck matches, outside arena under 0.006, time limit 0.001
in carrier battles and 0 in convoys. Median match 82 s carrier, 48 s convoy. Engine duty
(how hard a ship runs its strongest thruster, on average; reported, not gated): carrier
fighter 0.19, strafer 0.27, gunship 0.57.

After the convoy retune below, `f995_701` wins 0.568 of convoys vs R (n = 1032), so the mean
vs R on the final rosters is about 0.67. Against v1 on the final rosters: 0.863 carrier,
0.965 convoy (n = 516); deathmatch 0.812.

## Gate H: `hide_200` fails O and M

Gate H, for the `hide` arm, uses B3's bars as listed above. "vs w1_400" is the mission
win against `w1_400`, and the last three columns are the following measures. `hide_200`
misses all three following bars (attack share 0.355 against the 0.416 it needed, threat share
0.342 against 0.386, go-to 0.487 against 0.7) and the mission bar against `w1_400`
(0.382 against 0.45).

| candidate | O | M | D | H | mission win vs v1 | vs w1_400 | attack share | threat share | go-to in time |
|---|---|---|---|---|---|---|---|---|---|
| hide_200 | ✗ | ✗ | ✓ | ✓ | 0.668 | 0.382 | 0.355 | 0.342 | 0.487 |

The screen selects on strength, so it sent the least changed checkpoint to the gate. To
answer the arm's actual question I also measured following on its last checkpoint
(reported, not gated). "Shown / hidden" is the same pilot on the same matches with its
orders shown and with them hidden from it, so the gap is what seeing the order changes.
The bars are hidden + 0.05, and 0.7 for go-to. The script reads its orders straight
from the game, not from what a pilot sees, so they cannot be hidden from it and it has
one number.

| pilot, random commander | attack share, shown / hidden | threat share, shown / hidden | go-to in time, shown / hidden |
|---|---|---|---|
| script | 0.470 | 0.650 | 0.898 |
| hide_644 | 0.382 / 0.344 | 0.375 / 0.345 | 0.538 / 0.367 |
| reward_300 (B3) | 0.39 / 0.40 | 0.37 / 0.34 | 0.51 / 0.39 |
| f995_701 | 0.310 / 0.325 | 0.290 / 0.323 | 0.475 / 0.507 |

So 644 updates of order-only pay moved go-to by 0.17 and the others by 0.03-0.04, while the
win rate vs R fell to 0.109 and the fire rate (the share of moments a pilot pulls a
trigger) fell from about 0.6 to about 0.38. Pilots stopped shooting rather than started
following: fire still costs, and a hit off target pays nothing. KL to the parent on
ordered rows (how far its choices had drifted from `reward_300`'s) kept growing, so
behaviour changed a lot, in the wrong direction. This is one seed, one anchor weight
and one shaping of the pay.

`f995_701` shows no following at all, as expected with no order pay.

## How much the commander can matter (`commander_value*.py`, `*.jsonl`)

Here the same pilot flies both sides. Side b is under the scripted commander with its
orders shown. Side a's command varies: the scripted commander (the control), random
orders, or the scripted commander's orders hidden from its pilots. `transit_300` is B3's
`transit` arm at update 300, a pilot that followed orders well but fought weakly. The
numbers are side a's share of carrier battles won:

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
  commander loses to random orders**. It is a weak commander. It mostly keeps a third of its
  ships defending its own carrier and sends the rest to strike the enemy carrier. The
  cause of the gap has not been studied.
- With the scripted commander's orders hidden from its pilots, `transit_300`'s side
  wins 0.992. Shown the same orders, it wins 0.486. Seeing orders is what cripples it:
  the damage done by B3's script pull, made visible.
- Convoy with script pilots is not informative: on the first rebalanced rosters defenders won all of it, and it was not rerun on the final ones.

## Convoy

The convoy rosters were rebalanced twice: for `reward_300`, then for `f995_701`, which, flying both sides on the first
rosters, had attackers winning only 0.19. Final: 5, 6 or 7 freighters, with escorts
`F S F G` against raiders `F F S G F S` (F fighter, S strafer, G gunship); attackers win
0.616 / 0.589 / 0.545, medians 42-50 s. `convoy_balance.md` has both passes.

## Unresolved

- Pilots ignore orders on the live page, and `Show commands` draws them anyway. `/pilot/`
  says so; the live caption does not.
- Convoys rarely get through: 3-6 % of matches in the mirror (the same pilot on both
  sides). A defence nearly always wins by killing the raid.
- Replays of past champions fly today's rosters, and they are lopsided for them.
- `ORDER_SHAPING_GAMMA`, the discount used inside the order reward, is hard-coded to
  0.99 (`reward.rs`), so any order pay at gamma 0.995 would be biased until it follows
  the training gamma.
- Inference (the pilot's per-move computation in the browser) was not measured on a
  phone. The new pilot's network, the one the `/pilot/` page describes, is the same
  size as `reward_300`'s, and the biggest
  roster has fewer strike craft now.
