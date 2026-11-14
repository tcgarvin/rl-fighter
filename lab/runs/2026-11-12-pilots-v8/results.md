# Go-to orders get a deadline; one night did not teach pilots to fly by it

Shipped to the live page on 2026-11-14, `SIM_VERSION` 8.

<!-- summary: A commander's "go to this point" order can now say by when, and the pilot can see the time running down. Four lines trained for a night under the new rule. They can see the deadline but have not learned to fly by it: alone, a pilot still fights first and arrives in time only when the deadline is long. Two of the new pilots join the live page on their fighting. -->

A commander can give a ship three kinds of order: attack that ship, defend that ship, or
go to that point. Go-to is the one the pilots follow worst, and three nights of practice
had not moved it. This entry is a change to the game to fix that, and the first night of
training under it. The change is in. The lesson did not land in one night.

## What was wrong with go-to

Before changing anything we traced every ship's path in 256 go-to drills per pilot. A
drill is a short practice match: a squad of one to four ships is told to reach a circle.
Of the ships still alive when time ran out:

| Pilot | In time | Near miss | At the enemy |
|---|---|---|---|
| Script | 0.98 | 0.01 | 0.01 |
| `transit_300` | 0.64 | 0.26 | 0.10 |
| `followers_1793` | 0.32 | 0.35 | 0.31 |
| `fighters_1832` | 0.28 | 0.25 | 0.46 |
| `f995_701` | 0.20 | 0.23 | 0.57 |
| `fighters_pay1_1317` | 0.16 | 0.23 | 0.59 |

A near miss came within 60 m of the circle but was not inside it in time. "At the enemy"
never got that close and was found beside an enemy instead.

- **Pilots do read the order.** In the first five seconds `followers_1793` closes 66 m on
  the point when it can see the order, and none when the order is hidden.
- **They fight first.** A lone pilot would fly 500 m to a harmless parked enemy, destroy
  it, and only then fly straight to the point.
- **Nothing paid for being prompt.** Arriving paid the same whenever the ship arrived, and
  much less than a kill: about 0.2 against 0.8 for destroying a fighter. The time limit
  existed only in our scoring. The pilot was never told it.

## What a deadline is

In the new game version a go-to order can say "be there by this time". The pilot gets four
new inputs, 587 in all where it had 583: whether the order has a deadline, how much time
is left, how urgent that is for the distance still to fly, and how close it is over the
last 100 m.

The pay changes with it. Arriving in time pays 1.0. Missing the deadline costs 1.0, once,
and the order is then over. Nothing is charged for time used before the deadline, so an
order with time to spare leaves room to fight on the way. That is the behaviour we want: go
now when time is short, fight first when it is not.

Deadlines are set as a multiple of the straight-line flying time. An allowance of 2 means
twice the time a straight flight at top speed would take, plus three seconds to turn. In
training drills the allowance runs from 2 to 8. No commander issues a deadline yet, so
nothing on the live page shows one.

## The night

Four lines trained from 00:53 to 08:00, about 355 updates each. Each carries on from the
[fourth night](../2026-11-10-fourth-night/)'s pilot of its line: `followers_1793`,
`fighters_1832` and `fighters_pay1_1317`.

| Line | Sees the deadline | Order pay |
|---|---|---|
| `followers_v8` | Yes | 1 |
| `fighters_v8` | Yes | 3 |
| `fighters_pay1_v8` | Yes | 1 |
| `followers_v8_blind` | No | 1 |

Order pay multiplies everything an order pays, so for `fighters_v8` a deadline is worth
plus or minus 3. The blind line is the control: it is paid and charged by deadlines it
cannot see. If seeing the deadline matters, the seeing twin should pull ahead of it.

## The ten

The live page flies ten pilots, drawn ship by ship. Wins added per 100 matches over the
script flying the same ships; each is good to about ±3.4.

1. **`f995_701`, +16.8.**
2. **`fighters_pay1_1317`, +16.7.**
3. **`f99_696`, +16.7.**
4. **`followers_v8_352`, +16.6.** New. `followers_1793`, one night on.
5. **`fighters_pay1_462`, +15.5.**
6. **`fighters_pay1_849`, +14.6.**
7. **`f995_400`, +14.0.**
8. **`fighters_pay1_v8_351`, +13.0.** New. `fighters_pay1_1317`, one night on.
9. **`followers_1323`, +12.8.**
10. **`fighters_1832`, +12.4.**

Two pilots leave the list: `fighters_1338` (+12.2) and `followers_1793` (+11.0). Two of
the night's four did not make it: `followers_v8_blind_360` (+12.3) and `fighters_v8_362`
(+9.6).

The two new pilots are the first on the page that can see a deadline. The other eight
read the first 583 inputs, as before.

## What the night answered

**Alone, a pilot still fights first.** The cleanest test puts one ship alone on 324
starts and replays each start at several allowances. Share in time, of ships alive at
the deadline, at allowances of 2, 5 and 8 and with no deadline at all:

| Pilot | 2 | 5 | 8 | None |
|---|---|---|---|---|
| Script | 0.96 | 1.00 | 1.00 | 1.00 |
| `followers_1793` | 0.08 | 0.46 | 0.66 | 0.23 |
| `followers_v8_352` | 0.06 | 0.43 | 0.69 | 0.26 |
| `followers_v8_blind_360` | 0.13 | 0.42 | 0.60 | 0.21 |
| `fighters_1832` | 0.03 | 0.20 | 0.40 | 0.11 |
| `fighters_v8_362` | 0.05 | 0.34 | 0.46 | 0.11 |
| `fighters_pay1_1317` | 0.03 | 0.15 | 0.22 | 0.05 |
| `fighters_pay1_v8_351` | 0.05 | 0.33 | 0.49 | 0.11 |

The script, which flies straight there, makes nearly every deadline of twice the
straight-line time or more. No trained pilot makes even one in seven at that allowance.
They are in time only when the deadline is long enough to finish the fight first.

**The two `fighters` lines may be reading the new inputs. The followers line shows no
sign.** We flew each new pilot again with its deadline inputs blanked:

| Pilot | Allowance | Seeing | Blanked |
|---|---|---|---|
| `fighters_v8_362` | 5 | 0.34 | 0.22 |
| `fighters_pay1_v8_351` | 8 | 0.49 | 0.37 |
| `followers_v8_352` | 8 | 0.69 | 0.66 |

The first two gaps are about two and a half times the noise. They are also the largest
of several we could have picked, and over every allowance together the gap is smaller
(0.19 against 0.15, and 0.19 against 0.16). Call it a hint. Nobody arrives later when given
more time, so nobody is spending spare time on purpose.

**In squads, small gains.** The drills, squads of one to four, share in time:

| Line | Before | After |
|---|---|---|
| `followers` | 0.49 | 0.51 |
| `fighters` | 0.38 | 0.42 |
| `fighters_pay1` | 0.25 | 0.31 |

The script scores 0.99. For `followers_v8_352` by how tight the deadline was: tight 0.30,
medium 0.55, loose 0.74. Its parent: 0.30, 0.53, 0.72. Near misses stayed at about a
quarter of ships for every pilot. "At the enemy" barely moved: 0.23 to 0.21 for
`followers`, 0.35 to 0.31 for `fighters`, 0.47 to 0.44 for `fighters_pay1`.

These "before" numbers are the parents flown again on the new drill. They are not
comparable with the go-to numbers in earlier entries.

**Seeing against blind: no difference.** Both `followers` lines score 0.51 on the drills,
and the lone-ship table above does not separate them. Since neither learned to hurry, the
control had nothing to show.

**Attack and defend moved a little.** How often a pilot changes target when the order
changes, before and after:

| Pilot | Attack | Defend |
|---|---|---|
| `fighters_v8_362` | 0.65 to 0.73 | 0.67 to 0.76 |
| `followers_v8_blind_360` | 0.72 to 0.81 | 0.74 to 0.79 |
| `followers_v8_352` | 0.72 to 0.72 | 0.74 to 0.76 |
| `fighters_pay1_v8_351` | 0.21 to 0.26 | 0.23 to 0.33 |

**Fighting: one up, two down.** Wins added per 100, parent to child:
`followers_v8_352` +11.0 to +16.6, `fighters_pay1_v8_351` +16.7 to +13.0,
`fighters_v8_362` +12.4 to +9.6. Both `fighters` lines gave up some fighting for a little
following.

## Why so little moved

**A night is small for this lesson.** One update finishes 16 to 18 matches, and 3 to 5 of
them are go-to drills. Over the whole night:

| Line | Go-to drills | Ships | Missed |
|---|---|---|---|
| `followers_v8` | 1,770 | 3,306 | 0.34 |
| `fighters_v8` | 1,540 | 2,881 | 0.45 |
| `fighters_pay1_v8` | 1,100 | 2,070 | 0.57 |

"Ships" is how many flew under a deadline, and "missed" the share of them that were
alive when it passed and not there. That share hardly fell through the night. First quarter to last: 0.37 to 0.34,
0.50 to 0.44 and 0.55 to 0.54.

**The pay is close to a wash.** At order pay 1, making a deadline is worth 1 and missing
it costs 1. Destroying a fighter on the way pays about 0.8, and a bigger ship more. A pilot
that fights first and arrives late loses little.

Higher pay alone may not be the answer, though. `fighters_v8`, at order pay 3, had a
deadline worth clearly more than a kill, and it gained no more on go-to than
`fighters_pay1_v8` at pay 1 (0.04 against 0.06 on the drills). The two lines differ in
other ways too, so this is not a clean comparison.

## One thing that still doesn't fit

The scores above come from mixed matches, ships drawn one by one. We also fly each new
pilot against its parent with a whole side each:

| Pilot | Won | Adds | Parent |
|---|---|---|---|
| `followers_v8_blind_360` | 0.57 | +12.3 | +11.0 |
| `followers_v8_352` | 0.47 | +16.6 | +11.0 |
| `fighters_v8_362` | 0.43 | +9.6 | +12.4 |
| `fighters_pay1_v8_351` | 0.37 | +13.0 | +16.7 |

"Won" is the share of those head-to-head matches the new pilot won. "Adds" is its wins
added per 100 in mixed matches, with its parent's beside it.

For the two `fighters` lines both measures agree. For `followers_v8_352` they do not: it
loses to its parent head to head, yet adds more wins in mixed matches. Its blind twin
beats the same parent head to head and adds far fewer wins than it does. The
[fourth night](../2026-11-10-fourth-night/) saw the same kind of split. It is still not
explained. The live page flies mixed matches, so the list above goes by that measure.

## The season's records

All four new pilots are added to the season. Nobody is retired. The cull report, which is
a report only, notes that the `fighters` family is over its cap of four lines in training
and names `fighters_v8_362` and `fighters_1832` as the ones it would drop.

The data: `lab/population/2026-11-sim6/war/first-v8-night/war.json` (wins added),
`lab/population/2026-11-sim6/sweep/first-v8-night/` (one ship alone, by allowance), and
`lab/runs/2026-11-12-pilots-v8/eval/` (drills, and each pilot against its parent).

## What's next

Go-to school. The `followers` line gets go-to drills as most of its training, with a
deadline worth 3. A copy of it gets only the higher pay, to tell the two changes apart.
The `fighters` line gets a second night unchanged, to see whether its hint grows.
