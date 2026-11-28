# Given the choice, the commanders learned to stop giving orders

Verdict: **FAIL**. No commander found orders worth more than no orders. Two of the three
learned to give almost none, and they score level with the side that gets none. No rule
of the game changed (`SIM_VERSION` 8, the eighth version of the game's rules).

<!-- summary: A commander is the network that gives a side's ships their orders. Just before this night we found that ships given no orders at all beat every commander we had. Three new commanders then trained for six hours, half their matches against that no-orders side, and none found orders that help: two learned to keep their ships under an order only 3 to 6% of the time and end level with it, and the one pushed to keep more randomness in its choices kept ordering about half the time and lost 0.34 to 0.66. The commanders on the live page are unchanged until the owner decides whether one that commands almost nothing belongs there. -->

A commander gives a side's ships their orders: attack that ship, defend that one, go to
that point. Before training this night we measured something awkward. A side whose pilots
see no orders at all beat the scripted commander 0.75 to 0.25, and beat every learned
commander we had. So the question for the night became: can a commander learn orders
that are worth more than none? Not in six hours. The two best of three new commanders
learned to stop giving orders, which brought them level with the side that gets none.

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a pilot, that learned to fly by trial and error (reinforcement learning). Above the pilots
each side has a commander: a second network, or a hand-written script (the scripted
commander), that sees the whole battle and sends orders to groups of its ships called
squads. The [commander page](/commander/) explains how one works.

<div data-figure="diagram" data-name="orders" data-caption="The commanders trained here choose, for each squad, one of these orders or none. Given that choice, they learned to give almost no orders."></div>

[The first learned commanders](../2026-11-08-commander-1/results.md) (`c1_shaped` and two
others, on the live page since) came out about level with the script.
[The second commander night](../2026-11-10-commander-2/results.md) made a changed order
last at least five seconds and tried charging a price for each change. Its best line,
`price5`, is "last phase's best" below. Both nights ended on the same note: most pilots
ignored orders, so orders hardly mattered. Then
[two nights of go-to school](../2026-11-14-goto-school-2/results.md) gave us pilots that
do follow them. This night was meant to train commanders over those pilots. The
measurements taken first, in the [plan](plan.md), changed the question.

The side with no orders is called **unseen**. It is the scripted commander with its orders
hidden from its own pilots: it launches ships from its carrier as the script does, but its
pilots fight on their own judgment. Before training it beat the scripted commander 0.75 to
0.25 over pilots that follow orders. A learned commander can always choose "no order" for
every squad, so about 0.50 against the unseen side is a commander that learned to stay out
of the way. Clearly above 0.50 would be orders that help.

<!-- figure-idea: shared: the unseen side. Two sides with the same scripted commander sending the same orders; on one side the order arrows reach the pilots, on the other they stop at a wall, so the pilots fly on their own. Explains the control used in this entry and the order-cost entries after it. -->

## The night

Three fresh commanders, new networks with nothing learned yet, trained from 01:04 to
07:01. Each is an arm: a version of the experiment, identical to the others except for the
one setting being tested. Each played half its matches against the unseen side, a quarter
against itself and a quarter against saved copies of itself from earlier in the night.
Orders cost nothing, unlike in the second commander night.

The columns: which pilots flew both sides of each arm's matches, its entropy bonus, and
how many updates (rounds of training: play a batch of matches, then adjust the network
once) it got through. The four best followers are the pilots that follow orders best
(`followers_school_1052`, `followers_school_600`, `followers_solo_1072` and
`followers_pay3_810`, listed in `pilots_followers.json`). The live ten are the ten pilots
the live page, the site's front page, draws from. The entropy bonus sets how hard training
pushes a network to keep some randomness in its choices, so it keeps trying new ones.

| Arm | Pilots | Entropy bonus | Updates |
|---|---|---|---|
| `followers` | the four best followers | 0.002 | 233 |
| `followers_ent01` | the same four | 0.01, as in both earlier commander nights | 231 |
| `live` | the live ten | 0.002 | 197 |

## Against the side with no orders

Each score is the share of matches the side won against the unseen side, so 0.50 is an
even fight. There are 1,152 matches a row, 384 in each of three missions (team
deathmatch, carrier battle and convoy escort), played from the same random starts as
the before-training table. Each score is good to about ±0.03 (± is the margin of error: the
true value is very likely within that range). The first column is each arm with the pilots
it trained with flying both sides, the second with the other pilot list. "Time under an
order" is the share of its ships' time spent with an order standing:

| Side | Over its own pilots | Over the other list | Time under an order |
|---|---|---|---|
| `followers` | **0.48** | 0.50 (live ten) | 3–4% |
| `live` | **0.49** | 0.44 (followers) | 5–6% |
| `followers_ent01` | **0.34** | 0.40 (live ten) | 48% |
| *Before training:* | | | |
| `price5` (last phase's best) | 0.34 (followers) | 0.41 (live ten) | 45% |
| Random orders | 0.33 (followers) | 0.38 (live ten) | 61% |
| Scripted commander | 0.25 (followers) | 0.31 (live ten) | 99% |

By mission, over its own pilots. In a deathmatch the last side standing wins. In a
carrier battle each side has a carrier, a big ship that launches the strike craft, and
wins by destroying the other's. In a convoy escort one side guards cargo ships and the
other attacks them:

| Side | Deathmatch | Carrier | Convoy |
|---|---|---|---|
| `followers` | 0.48 | 0.46 | 0.51 |
| `live` | 0.48 | 0.44 | 0.56 |
| `followers_ent01` | 0.37 | 0.29 | 0.37 |

- **No arm beats the side with no orders.** The two best are within the margin of error
  of 0.50.
- **They got there by going quiet.** Through the night, the share of ship time under an
  order fell from 45% to 3% in `followers` and from 40% to 6% in `live`. Their win rate
  against the unseen side rose as their ordering fell (from 0.28 and 0.38 in the first
  25 updates to about 0.48 in the last). What orders they still give are mostly attack
  orders, and a ship now goes about a minute and a half between changes of its order,
  not ten seconds.
- **`live` ended where `followers` did.** The plan expected that: if good orders existed,
  the arm over the followers should have found them first. It did not, and the two are
  even against each other (0.50 over the followers, 0.49 over the live ten). `live`
  scores 0.44 over the followers, mostly from the carrier battle, where it scores 0.36
  (a by-mission number not in the tables above). It never trained
  over them.
- **The larger entropy bonus kept `followers_ent01` ordering**, and it paid for it. It
  stayed under an order about half the time all night, its order choices drifted toward
  even odds (the entropy of the part of the network that picks orders, a measure of how
  random its choices are, rose from 2.8 to 3.8), and it ends exactly where
  `price5` was before training: 0.34. `followers` beats it 0.67 to 0.33.
  [Last phase](../2026-11-10-commander-2/results.md)'s reading holds: the entropy bonus is
  what kept learned commanders ordering.

<!-- figure-idea: a chart from each arm's log.jsonl: share of ship time under an order and win rate against the unseen side, update by update through the night, for the three arms. Shows the two quiet arms' ordering falling as their wins rise, and followers_ent01 staying near half. -->

## Against the commanders from before

Each score is the share of matches won against the scripted commander, and against a
commander that gives random orders, the two yardsticks of the earlier commander nights.
The last row is the unseen side before training, over each pilot list:

| Side | Against scripted | Against random orders |
|---|---|---|
| `followers` (over the followers) | 0.76 | 0.67 |
| `live` (over the live ten) | 0.64 | 0.61 |
| `followers_ent01` (over the followers) | 0.59 | 0.50 |
| No orders, before (followers / live ten) | 0.75 / 0.69 | 0.67 / 0.62 |

The quiet arms do what the no-orders side does against the older commanders, a little
less for `live` against the script. `followers_ent01` is level with random orders.

## What goes live

The stable is the set of commanders the live page draws from, one per side per match: the
scripted commander and [the three `c1` commanders](../2026-11-08-commander-1/results.md).
The plan set two rules before the run. A line joins the stable if, over the live ten, it
is not behind the unseen side by more than the margin of error (0.47 or better). But if it
gives orders less than 10% of ship time, the owner decides whether a commander that
commands almost nothing belongs on the page. Two clear the first bar:

| Line | Against unseen, over the live ten | Time under an order |
|---|---|---|
| `followers` (update 233) | 0.50 | 3% |
| `live` (update 197) | 0.49 | 6% |

Both give orders less than 10% of ship time, so by the second rule this is the owner's
call, and the stable is unchanged for now. The case for: either one would beat everything on the
live page now by a wide margin (the script and the three `c1` commanders all lose to no
orders). The case against: with `?commands=1`, the page setting that draws each ship's orders, the
page would show a commander that leaves nearly every ship without an order, which says
something true about the pilots but shows little of a commander. They still launch strike craft from the carrier and steer it.

## What we learned

- **Orders are not worth giving to these pilots, as far as a commander can find in one
  night.** Over followers and over the live ten alike, the best a learned commander did
  was to stop. Together with the before-training numbers, every way of ordering we have
  tried costs matches: the script's, random orders, three earlier learned lines and the
  noisy arm tonight, `followers_ent01`.
- **The cost is on the pilots' side.** The afternoon's measurements (the plan's "Where the
  cost is") found it grows with the size of the fleet and shows up as ships lost early,
  whether or not the pilots follow orders well by the measure of our practice drills. In
  even deathmatches the ordered side scored 0.46 to 0.48 with one ship a side and 0.11 to
  0.17 with four. Pilots that mostly ignore orders paid the same as the followers. And in
  a deathmatch's first 30 seconds the ordered side lost 1.07 ships a match against 0.76
  for the side with no orders. A commander cannot fix that by choosing
  better. It can only give fewer orders.

## Next

- Find what an ordered pilot does wrong in a fleet fight's first 30 seconds. The plan's
  guess is that a pilot sent after one enemy stops dealing with the others. That matters
  past commanders: the script commands both sides in pilot training, and the live stable
  commands the matches that rate pilots (WAR, wins above replacement: how many more
  matches in 100 a side wins with a pilot than with the script flying its ships).
- Then a pilot phase, nights spent training pilots rather than commanders, that makes an
  order cheap to follow: pilots that take the target they are given and still fight the
  ships around them.
- Only then is there a reason for another commander night.

The data, for checking the numbers: `eval/` (`morning.sh` runs it again) and each arm's
training log, `log.jsonl`.
