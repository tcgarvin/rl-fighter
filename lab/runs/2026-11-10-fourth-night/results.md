# A fourth night: the price of a shot, and crashes that hurt

Shipped to the live page on 2026-11-10, `SIM_VERSION` 7 (the seventh version of the game's rules).

<!-- summary: Three new pilots join the live page. They trained with each shot costing twice as much and under new rules where crashing hurts by how hard you hit, and they hold the trigger less, hit a little more often and crash far less than the pilots they were trained from. A line that paid four times as much per shot got worse at winning, so twice is where the price stays. -->

This night asked two things. Would making each shot cost more in training teach pilots to
shoot less and better, without losing fights? And would they learn not to crash, now that
the game's rules make a crash do damage by how hard you hit?

The answer: at twice the old price per shot, pilots hold the trigger less, hit a little
more often and crash far less than their parents, the pilots they were trained from. In
matches like the live page's, a side wins at least as often with them flying as with their
parents. At four times the price it wins less often. Three new pilots join the ten on
the live page, the site's front page, each one more night of training on from a pilot on
the [third list](../2026-11-09-third-night/results.md).

## Where this fits

RL Fighter is a space-combat game in which every small ship is flown by a **pilot**, a small
neural network that learned to fly by trial and error: it plays many matches, scores points
(reward) for good outcomes such as damage dealt and wins, and is adjusted to do more of what
scored. Each night we train a few pilots further and each morning pick the ten that fly the
live page.

The [third night](../2026-11-09-third-night/results.md), the day before, picked them for the
first time by wins above replacement: how many more matches out of 100 a side wins with a
pilot flying its ships instead of the script, our hand-written pilot. The owner pointed to
two habits worth fixing. Ships fired into empty space a lot, and a small ship that crashed
into a big one, such as a carrier (the big ship that launches the small ones), seemed to
pay nothing for it. This night trained the same three lines as before under a higher price
per shot, in a new version of the game where a fighter that hits a carrier flat out dies.

## What changed for the night

- **A shot costs twice as much.** Pilots were firing into empty space a lot. The game's
  scoring charges a little reward for each shot. In training we doubled that charge on
  every line. A copy of the `fighters` line paid four times as much, to see how far the idea
  goes.
- **Crashes hurt by how hard you hit.** In the new game version a fighter flying flat out
  into a carrier dies. Every pilot, old and new, was scored again under these rules.
- **The trainer learned what a dead ship is worth.** When a ship dies its match goes on,
  and the part of the trainer that predicts "how well is this going" (the critic, used
  only in training) had never been shown a dead ship. Its guesses for one ranged from very
  good to very bad. It now learns the right answer, about zero.
- **A longer night.** Four lines ran from 22:30 to 08:30, about 480 updates each (380
  the night before). An update is one round of training: play a batch of matches, then
  adjust the network once.

<div data-figure="diagram" data-name="training-night" data-caption="This night had no single parent. Three lines carried on from their own pilots of the night before, and the fourth, fighters_fire4, started as a copy of fighters that paid four times as much per shot. Each trained for about 480 rounds."></div>

## The ten

A pilot's name is its training line followed by the update it was saved at:
`fighters_1832` is the `fighters` line after 1,832 updates. The lines are `fighters`
(strong fighters, paid well for following orders), `followers` (pilots that follow orders,
learning to fight), `fighters_pay1` (the `fighters` setup paid a third as much for
following) and, new tonight, `fighters_fire4`, the four-times copy of `fighters`. `f995`
and `f99` are older fighters from an [earlier run](../2026-11-01-fighters-v2/results.md).

Each number is wins added per 100 matches over the script flying the same ships, measured
the way the [third night](../2026-11-09-third-night/results.md) describes: thousands of
matches like the live page's, each ship's pilot drawn at random. Each is good to about ±3:
± is the margin of error, and the true value is very likely within 3 of the number shown.

1. **`f99_696`, +17.7.**
2. **`fighters_pay1_1317`, +16.0.** New: `fighters_pay1_849` after one more night of training.
3. **`fighters_1832`, +14.3.** New: `fighters_1338` after one more night of training.
4. **`fighters_pay1_462`, +14.1.**
5. **`f995_701`, +13.4.**
6. **`f995_400`, +13.4.**
7. **`followers_1793`, +13.2.** New: `followers_1323` after one more night of training.
8. **`fighters_1338`, +13.1.**
9. **`fighters_pay1_849`, +12.5.**
10. **`followers_1323`, +11.8.**

Left off: `fighters_506` (+11.7), `followers_955` (+10.9), `fighters_fire4_1827` (+10.5,
the four-times line), `fighters_959` (+8.3) and `transit_300` (+2.6).

Everyone's number is lower than yesterday's. That is the new crash rules and a stronger
field, not pilots getting worse: scores only compare within one morning's matches.

## What the night answered

**Twice the price: less wasted fire, no cost in wins.** All three new pilots score above
their parents: `fighters_pay1` by 3.5, `fighters` by 1.2, `followers` by 1.4. Only the
first is clearly more than noise. Flying against its parent in the same matches, each new
pilot changed as the table shows. Each cell is the parent's number, then the new pilot's.
"Time on the trigger" is the share of moments a pilot holds its fire button down, in convoy
escort (one side guards cargo ships, the other attacks them). "Shots per ship" counts shots
in a carrier battle (each side has a carrier, and destroying the enemy's wins). "Hit rate"
is the share of shots that hit, in convoy escort.

| Line | Time on the trigger, convoy | Shots per ship, carrier | Hit rate, convoy |
|---|---|---|---|
| `fighters` | 93% to 83% | 307 to 237 | 26% to 29% |
| `followers` | 89% to 72% | 276 to 202 | 31% to 35% |
| `fighters_pay1` | 87% to 66% | 222 to 188 | 28% to 35% |

They still fire most of the time. The change is real but modest.

**Four times the price is too much.** `fighters_fire4_1827` fired the least and hit the
most often of the `fighters` pair, but it adds 3.8 fewer wins per 100 than its twin at
twice the price (`fighters_1832`), and 2.6 fewer than the parent they share. That line
stops here. Every line stays at twice.

**Pilots learned not to crash.** Crash damage taken per ship in convoy escort, new pilot
against parent, both under the new rules:

| Line | Parent | New pilot |
|---|---|---|
| `fighters` | 38 | 14 |
| `followers` | 23 | 6 |
| `fighters_pay1` | 36 | 22 |

Fighters and strafers, two of the three small ship types, account for nearly all of it.
Gunships, the third and heaviest, crash as much as before.

**Following orders did not improve, and slipped for the followers.** We measure following
in drills, short practice scenarios built around one order. `followers_1793` reaches the
point it was sent to with a go-to order 39% of the time (47% for its parent) and changes
target when given a new attack order 72% of the time (81%). `fighters_1832` is about where
its parent was (26% go-to, 65% attack). `fighters_pay1_1317`, the night's best fighter,
follows least of all. The parents' drills were flown under the old crash rules, so read
these loosely.

**The learned commanders hold their lead.** A commander is a second network, or a
hand-written script, that gives a side's ships their orders. In the 1,572 matches where a
[learned commander](../2026-11-08-commander-1/results.md) faced the scripted one, it won
57.2% (±2.4); it was 57.5% yesterday.

## One thing that doesn't fit

Three of the four new pilots lose to their own parent when each flies a whole side
(44 to 46% of matches, and `fighters_1832` only 28% of carrier battles). Only
`fighters_pay1_1317` beats its parent (53%). Yet in the mixed matches that set the scores
above, the children add more wins than the parents. The two measure different things, a
whole side of one pilot against ships drawn one by one, and the live page is the second.
But a gap this size in carrier battles wants a look before the next night is planned.

## What these numbers can't separate

Three things changed at once for each new pilot: the price of a shot, the crash rules,
and the trainer's fix for dead ships. A new pilot against its parent shows all three
together. Only twice against four times is a clean comparison, since those two lines
differ in nothing else.

## The season's records

The season is the record of every pilot trained under this version of the rules, which
the new crash rules did not restart. Active members are the ones training may carry on
from. An archived one (retired from training) stays on record and can still fly on the
live page. A family, a pilot and its descendants, may have at most four active pilots
among those measured that morning. The `fighters` family had seven. The four-times line is archived
with the decision above, and the two weakest of the rest, `fighters_pay1_849` and
`fighters_1338`, are archived in favour of their own next nights. Both still fly on the
page. Active now: four `fighters`, five `followers` and the script, which is never trained
but stays as the yardstick. The `followers` are within the cap because only four of them
were measured this morning: `followers_513`, off the live list, was not.

The data is `lab/population/2026-11-sim6/war/fourth-night/war.json`; the shooting and
crash numbers are `lab/runs/2026-11-01-pilot-families/eval/shooting_*.md`. How the night
was run is in `lab/runs/2026-11-01-pilot-families/plan.md`.

## What's next

We alternate a night of training for the commanders with a night for the pilots, so it is
the commanders' turn, against these pilots. Before the pilots' next night: why the new
pilots lose carrier battles to their parents, and go-to, which three nights of drills have
not taught.
