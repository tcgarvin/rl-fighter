# A fourth night: the price of a shot, and crashes that hurt

Shipped to the live page on 2026-11-10, `SIM_VERSION` 7.

<!-- summary: Three new pilots join the live page. They trained with each shot costing twice as much and under new crash rules, and they hold the trigger less, hit a little more often and crash far less than their parents. A line that paid four times as much per shot got worse at winning, so twice is where the price stays. -->

The live page still flies ten pilots, drawn ship by ship. Three are new this morning, each
one more night of training on from a pilot on the [third list](../2026-11-09-third-night/).
The page also runs a new version of the game: crashing into things now does damage by how
hard you hit.

## What changed for the night

- **A shot costs twice as much.** Pilots were firing into empty space a lot. The game
  charges a little for each shot; in training we doubled that charge on every line. A
  copy of the `fighters` line paid four times as much, to see how far the idea goes.
- **Crashes hurt by how hard you hit.** In the new game version a fighter flying flat out
  into a carrier dies. Every pilot, old and new, was scored again under these rules.
- **The trainer learned what a dead ship is worth.** When a ship dies its match goes on,
  and the part of the trainer that predicts "how well is this going" had never been
  shown a dead ship. Its guesses for one ranged from very good to very bad. It now learns
  the right answer, about zero.
- **A longer night.** Four lines ran from 22:30 to 08:30, about 480 updates each (380
  the night before).

## The ten

Wins added per 100 matches over the script flying the same ships. Each is good to
about ±3.

1. **`f99_696`, +17.7.**
2. **`fighters_pay1_1317`, +16.0.** New. `fighters_pay1_849`, one night on.
3. **`fighters_1832`, +14.3.** New. `fighters_1338`, one night on.
4. **`fighters_pay1_462`, +14.1.**
5. **`f995_701`, +13.4.**
6. **`f995_400`, +13.4.**
7. **`followers_1793`, +13.2.** New. `followers_1323`, one night on.
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
pilot:

| Line | Time on the trigger, convoy | Shots per ship, carrier | Hit rate, convoy |
|---|---|---|---|
| `fighters` | 93% to 83% | 307 to 237 | 26% to 29% |
| `followers` | 89% to 72% | 276 to 202 | 31% to 35% |
| `fighters_pay1` | 87% to 66% | 222 to 188 | 28% to 35% |

They still fire most of the time. The change is real but modest.

**Four times the price is too much.** `fighters_fire4_1827` fired the least and hit the
most often of the `fighters` pair, but it adds 3.8 fewer wins per 100 than its twin at
twice the price, and 2.6 fewer than the parent they share. That line stops here. Every
line stays at twice.

**Pilots learned not to crash.** Crash damage taken per ship in convoy escort, new pilot
against parent, both under the new rules:

| Line | Parent | New pilot |
|---|---|---|
| `fighters` | 38 | 14 |
| `followers` | 23 | 6 |
| `fighters_pay1` | 36 | 22 |

Fighters and strafers account for nearly all of it. Gunships crash as much as before.

**Following orders did not improve, and slipped for the followers.** `followers_1793`
reaches a go-to point 39% of the time (47% for its parent) and changes target with an
attack order 72% of the time (81%). `fighters_1832` is about where its parent was (26%
go-to, 65% attack). `fighters_pay1_1317`, the night's best fighter, follows least of all.
The parents' drills were flown under the old crash rules, so read these loosely.

**The learned commanders hold their lead.** In the 1,572 matches where a learned
commander faced the script, it won 57.2% (±2.4); it was 57.5% yesterday.

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

The `fighters` family may keep four lines in training and had seven. The four-times line
is retired with the decision above, and the two weakest of the rest, `fighters_pay1_849`
and `fighters_1338`, are retired from training in favour of their own next nights. Both
still fly on the page. In training now: four `fighters`, five `followers` and the script.

The data is `lab/population/2026-11-sim6/war/fourth-night/war.json`; the shooting and
crash numbers are `lab/runs/2026-11-01-pilot-families/eval/shooting_*.md`. How the night
was run is in `lab/runs/2026-11-01-pilot-families/plan.md`.

## What's next

By the loop it is the commanders' turn, against these pilots. Before the pilots' next
night: why the new pilots lose carrier battles to their parents, and go-to, which three
nights of drills have not taught.
