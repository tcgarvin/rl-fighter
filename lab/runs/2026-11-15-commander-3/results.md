# Given the choice, the commanders learned to stop giving orders

Verdict: **FAIL**. No commander found orders worth more than no orders. Two of the three
learned to give almost none, and they score level with the side that gets none. No rule
of the game changed (`SIM_VERSION` 8).

<!-- summary: Before this night we found that pilots with no orders beat every commander we had. Three fresh commanders then trained for six hours, half their matches against that no-orders side. None found orders that help. Two learned to keep their ships under an order only 3 to 6% of the time and end level with the no-orders side; the one with last phase's larger entropy bonus kept ordering about half the time and lost 0.34 to 0.66. The stable on the live page is unchanged, pending the owner's call on a commander that commands almost nothing. -->

The [plan](plan.md) has the background; the four followers are `pilots_followers.json`. Before training, a side whose pilots see no
orders ("unseen": the scripted commander with its orders hidden from its own pilots)
beat the scripted commander 0.75 to 0.25 over pilots that follow orders, and beat every
learned commander we had. The question for the night: can a commander learn orders that
are worth more than none? A commander can always pick "no order" for every squad, so
about 0.50 against the unseen side is a commander that learned to stay out of the way.
Clearly above 0.50 would be orders that help.

## The night

Three fresh commanders trained from 01:04 to 07:01. Each played half its matches against
the unseen side, a quarter against itself and a quarter against its own earlier
snapshots. Orders cost nothing.

| Arm | Pilots | Entropy bonus | Updates |
|---|---|---|---|
| `followers` | the four best followers | 0.002 | 233 |
| `followers_ent01` | the same four | 0.01, as in both earlier phases | 231 |
| `live` | the live ten | 0.002 | 197 |

## Against the side with no orders

1,152 matches a row, 384 a mission, the same seeds as the before-training table. Each
score is good to about ±0.03. The first column is each arm over the pilots it trained
with.

| Side | Over its own pilots | Over the other list | Time under an order |
|---|---|---|---|
| `followers` | **0.48** | 0.50 (live ten) | 3–4% |
| `live` | **0.49** | 0.44 (followers) | 5–6% |
| `followers_ent01` | **0.34** | 0.40 (live ten) | 48% |
| *Before training:* | | | |
| `price5` (last phase's best) | 0.34 (followers) | 0.41 (live ten) | 45% |
| Random orders | 0.33 (followers) | 0.38 (live ten) | 61% |
| Scripted commander | 0.25 (followers) | 0.31 (live ten) | 99% |

By mission, over its own pilots:

| Side | Deathmatch | Carrier | Convoy |
|---|---|---|---|
| `followers` | 0.48 | 0.46 | 0.51 |
| `live` | 0.48 | 0.44 | 0.56 |
| `followers_ent01` | 0.37 | 0.29 | 0.37 |

- **No arm beats the side with no orders.** The two best are within noise of 0.50.
- **They got there by going quiet.** Through the night, the share of ship time under an
  order fell from 45% to 3% in `followers` and from 40% to 6% in `live`. Their win rate
  against the unseen side rose as their ordering fell (from 0.28 and 0.38 in the first
  25 updates to about 0.48 in the last). What orders they still give are mostly attack
  orders, and a ship now goes about a minute and a half between changes of its order,
  not ten seconds.
- **`live` ended where `followers` did.** The plan expected that: if good orders existed,
  the arm over the followers should have found them first. It did not, and the two are
  even against each other (0.50 over the followers, 0.49 over the live ten). `live`
  scores 0.44 over the followers, mostly from the carrier battle (0.36). It never trained
  over them.
- **The larger entropy bonus kept `followers_ent01` ordering**, and it paid for it. It
  stayed under an order about half the time all night, its order choices drifted toward
  even odds (the order head's entropy rose from 2.8 to 3.8), and it ends exactly where
  `price5` was before training: 0.34. `followers` beats it 0.67 to 0.33. Last phase's
  reading holds: the entropy bonus is what kept learned commanders ordering.

## Against the commanders from before

| Side | v scripted | v random |
|---|---|---|
| `followers` (over the followers) | 0.76 | 0.67 |
| `live` (over the live ten) | 0.64 | 0.61 |
| `followers_ent01` (over the followers) | 0.59 | 0.50 |
| No orders, before (followers / live ten) | 0.75 / 0.69 | 0.67 / 0.62 |

The quiet arms do what the no-orders side does against the older commanders, a little
less for `live` against the script. `followers_ent01` is level with random orders.

## What goes live

The bar was set before the run: a line joins the stable if, over the live ten, it is not
behind the unseen side by more than noise (0.47 or better). Two clear it:

| Line | v unseen over the live ten | Time under an order |
|---|---|---|
| `followers` (update 233) | 0.50 | 3% |
| `live` (update 197) | 0.49 | 6% |

Both give orders less than 10% of ship time, so by the plan this is the owner's call, and
the stable is unchanged for now. The case for: either one would beat everything on the
live page now by a wide margin (the script and the three `c1` commanders all lose to no
orders). The case against: with `?commands=1` the page would show a commander that leaves
nearly every ship without an order, which says something true about the pilots but shows
little of a commander. They still launch strike craft from the carrier and steer it.

## What we learned

- **Orders are not worth giving to these pilots, as far as a commander can find in one
  night.** Over followers and over the live ten alike, the best a learned commander did
  was to stop. Together with the before-training numbers, every way of ordering we have
  tried costs matches: the script's, random orders, three earlier learned lines and the
  noisy arm tonight.
- **The cost is on the pilots' side.** The afternoon's measurements found it grows with
  the size of the fleet and shows up as ships lost early, whether or not the pilots
  follow orders well by the drills' measure. A commander cannot fix that by choosing
  better. It can only give fewer orders.

## Next

- Find what an ordered pilot does wrong in a fleet fight's first 30 seconds. The plan's
  guess is that a pilot sent after one enemy stops dealing with the others. That matters
  past commanders: the script commands both sides in pilot training, and the live stable
  commands the matches that rate pilots.
- Then a pilot phase that makes an order cheap to follow: pilots that take the target
  they are given and still fight the ships around them.
- Only then is there a reason for another commander night.

The data: `eval/` (`morning.sh` runs it again) and each arm's `log.jsonl`.
