# Go-to school: squads learn the deadline, a ship alone does not

Shipped to the live page on 2026-11-15, `SIM_VERSION` 8 (the eighth version of the
game's rules, the one that gave go-to orders a deadline).

<!-- summary: A second night of teaching pilots to reach a point by a deadline. The pilot that spent most of its training on go-to practice drills now arrives in time seven times in ten where it made five, and six in ten of the tight deadlines where it made three. Paying more for the deadline did less, and all of the gain is in squads: a ship sent somewhere alone still fights first. Two of the new pilots join the live page. -->

A commander can tell a ship to go to a point, and since
[the first night on this game version](../2026-11-12-pilots-v8/results.md) the order can
say by when. That night the pilots could see the deadline and did not fly by it. We had
two guesses why: a night holds few go-to drills (short practice scenarios), and making
the deadline paid about the same as destroying an enemy fighter. This night tested both.
More drills worked: the pilot that got them as most of its training, a "school", now
makes seven deadlines in ten where it made five. More pay alone did less. And all of the
gain is in squads. A ship sent somewhere alone still fights first.

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a pilot, that learned to fly by trial and error (reinforcement learning). A second network
or a hand-written script, the commander, sees the whole side and gives its ships orders:
attack that ship, defend that ship, or go to that point. The [pilot page](/pilot/) and the
[commander page](/commander/) explain both.

Go-to has been the order pilots follow worst. On
[the first night of deadlines](../2026-11-12-pilots-v8/results.md) we let a go-to order
say "be there by this time", gave pilots four new inputs (numbers they see each moment)
showing the time left, and paid them for arriving in time. After a night of training they
arrived in time hardly more often than before. A lone pilot would fly to an enemy,
destroy it, and only then fly to the point. A commander's go-to is only worth giving if
pilots go when told, so this night tried the two most likely fixes.

<div data-figure="diagram" data-name="orders" data-caption="This night is about the go-to and its clock. In the practice drills a go-to usually carries a deadline. The commanders in real matches do not set one yet."></div>

## The night

Three lines trained from 01:30, each carrying on from a pilot of the first night. A family
is every pilot descended from one starting pilot. A line is one branch of a family: a
series of pilots, each trained on from the last, that share a name. A pilot's name is its line followed by the
training update it was saved at, where an update is one round of training: play a batch of
matches, then adjust the network once. `followers_v8_352` is from the `followers` family,
which descends from an early pilot that followed orders well but fought weakly and is bred
to fight and follow orders. `fighters_v8_362` is from the `fighters` family, descended
from our best fighter, `f995_701`, and bred mainly to win fights. `_v8_` in a name means
the pilot was widened to read go-to deadlines.

The table says what each line was given. "Go-to share" is the share of training matches
that were go-to drills rather than ordinary battles or other drills.

| Line | From | Go-to share of training starts | A deadline is worth |
|---|---|---|---|
| `followers_school` | `followers_v8_352` | 0.53 | 3 |
| `followers_pay3` | `followers_v8_352` | 0.21, as before | 3 |
| `fighters_v8` | `fighters_v8_362` | 0.18, as before | 3, as before |

In a go-to drill a squad of one to four ships is told to reach a circle on the map,
usually by a deadline. "Worth 3" means arriving in time pays 3 points of reward and
missing costs 3, where destroying a fighter pays about 0.8. On the first night the
`followers` line had it at 1.

- `followers_school` against `followers_pay3` shows what more drills buy at the same pay.
- `followers_pay3` against the first night shows what the pay buys alone.
- `fighters_v8` changed nothing. It is the check on "it only needed more time".

**Two of the three stopped early**, on a fault of ours described below. So the pilots
measured here are from each line's last saved point. Update counts carry on from the
parent, so `followers_school_600` is 248 updates past `followers_v8_352`:

| Pilot | Updates | Go-to drills | Ships under a deadline |
|---|---|---|---|
| `followers_school_600` | 248 | 3,550 | 6,616 |
| `followers_pay3_810` | 458 | 2,376 | 4,425 |
| `fighters_v8_500` | 138 | 594 | 1,100 |

For scale: on the whole first night the `followers` line flew 1,770 go-to drills.

## What the night answered

**More drills work.** The drill test: 256 go-to drills per pilot on the same fixed
starts, squads of one to four, played only to measure. Each number is the share of ships
in time, of those alive at the deadline. "In time" is all deadlines. Then they are split by how
tight the deadline was. A deadline is set as a multiple of the time a straight flight
would take: tight is under 2.5 times, medium 2.5 to 4.5, loose over 4.5. "Script" is our
hand-written, rule-based pilot, which flies straight there:

| Pilot | In time | Tight | Medium | Loose |
|---|---|---|---|---|
| Script | 0.99 | 0.96 | 0.99 | 1.00 |
| `followers_v8_352` (parent) | 0.51 | 0.30 | 0.55 | 0.74 |
| `followers_school_600` | 0.70 | 0.60 | 0.68 | 0.87 |
| `followers_pay3_810` | 0.59 | 0.46 | 0.62 | 0.77 |
| `fighters_v8_362` (parent) | 0.42 | 0.33 | 0.40 | 0.68 |
| `fighters_v8_500` | 0.50 | 0.42 | 0.49 | 0.68 |

Each number is good to about ±0.04 overall and ±0.10 on tight deadlines alone (± is the
margin of error: the true value is very likely within that range). School
doubled its parent on tight deadlines. It did so in 248 updates, about half of what
`followers_pay3` had.

**Pay alone does less.** `followers_pay3_810` gained 0.08 where school gained 0.19.
`fighters_v8_500` also gained 0.08, on a second night of the same settings. So some of
this is simply time: the first night's lesson was still arriving.

**Fewer ships go to the enemy instead.** Of the ships that were not in time, some came
within 60 m of the circle (a near miss) and some never got that close and were found
beside an enemy. Both are shares of all the ships alive at the deadline, like the in-time
share above:

| Pilot | Near miss | At the enemy |
|---|---|---|
| `followers_v8_352` | 0.26 | 0.21 |
| `followers_school_600` | 0.19 | 0.10 |
| `followers_pay3_810` | 0.25 | 0.15 |
| `fighters_v8_362` | 0.27 | 0.31 |
| `fighters_v8_500` | 0.26 | 0.23 |

**All of it is in squads. A ship alone did not move.** The same drills, split by whether
the ship had company:

| Pilot | In a squad | Alone |
|---|---|---|
| Script | 0.99 | 0.98 |
| `followers_v8_352` | 0.51 | 0.41 |
| `followers_school_600` | 0.72 | 0.41 |
| `followers_pay3_810` | 0.61 | 0.39 |
| `fighters_v8_362` | 0.43 | 0.24 |
| `fighters_v8_500` | 0.51 | 0.32 |

"Alone" rests on about 40 ships a pilot, so each is good to about ±0.15. School's lone
ships are where its parent's were: 0.41 in time, and more than a third beside an enemy.

The sweep is the larger test of a lone ship: one ship on 324 starts, each start flown at
several time allowances, from 0.8 to 8, and once with no deadline at all. An allowance of
2 is twice the time a straight flight takes. Each start has one of three layouts: a
single unarmed enemy parked at the map's edge, one armed enemy beside the route, or three. Each number is the share in time, of ships
alive at the deadline. With no deadline a ship counts as in time if it arrives within
twice the straight-flight time plus 10 s:

| Pilot | 2 | 5 | 8 | No deadline |
|---|---|---|---|---|
| Script | 0.96 | 1.00 | 1.00 | 1.00 |
| `followers_v8_352` | 0.06 | 0.43 | 0.69 | 0.26 |
| `followers_school_600` | 0.12 | 0.54 | 0.73 | 0.27 |
| `followers_pay3_810` | 0.09 | 0.56 | 0.75 | 0.26 |
| `fighters_v8_362` | 0.05 | 0.34 | 0.46 | 0.11 |
| `fighters_v8_500` | 0.08 | 0.45 | 0.65 | 0.14 |

<div data-figure="diagram" data-name="goto-sweep" data-caption="The table above gives the share in time at allowances of 2, 5 and 8 and with no deadline. At 2 the script made 0.96 of its deadlines."></div>

Everyone is a little better and nobody is close. At an allowance of 2 the best of them
makes one deadline in eight. In the layout where the only enemy is parked at the edge of
the map and cannot shoot, `followers_school_600` makes 0.02 of its deadlines at an
allowance of 2: it goes for the enemy first.

One reason the squads may have learned first: one go-to drill in four is a ship alone, but
the other drills carry two to four ships each, so only one ship in ten that flies a go-to
in training is alone.

**School reads the deadline, and it does not help it alone.** We flew each pilot through
the lone-ship sweep again with its deadline inputs blanked (set to zero, so it cannot see the deadline). Seeing
them, `followers_school_600` turns for the point sooner (half the distance covered in 18 s
against 28 s at an allowance of 1.5) and does less damage on the way (44 against 58 at an
allowance of 2). It is in time no more often: 0.31 seeing against 0.34 blanked, over the
sweep's allowances of 1.5 and over (the lower ones, 0.8 and 1, are at or past the limit of
what a ship can do). `fighters_v8_500` is in time more often seeing
than blanked (0.25 against 0.21), as its parent was.

**Attack and defend got better too, in school only.** An attack drill puts enemy groups on
opposite sides of the squad and names a target in one group. The same start is then flown
again with the target named in the other group. A defend drill does the same with two
friendly ships under attack. Each number is the share of starts where the squad went to
the named side both times, which shows it followed the order rather than going where it
would have gone anyway:

| Pilot | Attack | Defend |
|---|---|---|
| `followers_v8_352` | 0.72 | 0.76 |
| `followers_school_600` | 0.86 | 0.89 |
| `followers_pay3_810` | 0.75 | 0.73 |
| `fighters_v8_362` | 0.73 | 0.76 |
| `fighters_v8_500` | 0.76 | 0.81 |

School flew fewer attack and defend drills than its twin over the night, about 1,200
against 1,600, so this was not expected. `followers_school_600` meets every bar of the
drill gate, a set of pass marks on the drill test fixed in advance. Its parent missed
three.

**School cost nothing in a fight.** Two measures. "Won against parent" is the share of
matches the new pilot won with a whole side each against its parent. "Adds" is its wins
added per 100 in mixed matches: pilots are dropped at random, ship by ship, into matches
like the live page's, and a statistical fit estimates how many more matches in 100 a side
wins with this pilot flying its ships instead of the script. We call this WAR, wins above
replacement, after the baseball measure, and 0 is the script's level:

| Pilot | Won against parent | Adds | Parent adds |
|---|---|---|---|
| `followers_school_600` | 0.53 | +14.5 | +12.8 |
| `followers_pay3_810` | 0.53 | +13.8 | +12.8 |
| `fighters_v8_500` | 0.59 | +9.4 | +12.6 |

"Adds" is good to about ±3.3. `fighters_v8_500` is the odd one again: it beats its parent
clearly head to head and adds fewer wins than it in mixed matches.
[The first deadline night](../2026-11-12-pilots-v8/results.md) and
[the fourth night](../2026-11-10-fourth-night/results.md) saw the same kind of split, and
it is still not explained.

## The ten

The live page, the site's front page, plays matches forever, and each ship on it is flown
by one of ten pilots drawn at random. The ten are the pilots with the most wins added per
100 matches over the script flying the same ships, here from 4,320 matches this morning.
Names follow the same pattern as above. `f995_701`, `f995_400` and `f99_696` are older
fighters from [an earlier night](../2026-11-01-fighters-v2/results.md) that ignore orders,
named for how far ahead they were trained to plan (0.995 looks further ahead than 0.99).
`fighters_pay1` is a `fighters` branch paid less for following orders.

1. **`fighters_pay1_1317`, +17.4.**
2. **`f99_696`, +16.9.**
3. **`f995_701`, +15.4.**
4. **`followers_1323`, +15.1.**
5. **`fighters_pay1_462`, +15.0.**
6. **`followers_school_600`, +14.5.** New. The school pilot.
7. **`f995_400`, +14.3.**
8. **`followers_pay3_810`, +13.8.** New. Its twin on higher pay alone.
9. **`fighters_pay1_v8_351`, +13.7.**
10. **`followers_v8_352`, +12.8.**

Two pilots leave the list: `fighters_pay1_849` (+12.6) and `fighters_1832` (+11.6). Left
off: `fighters_v8_362` (+12.6) and `fighters_v8_500` (+9.4).

Four of the ten can now see a deadline. No commander on the page gives one yet, so
nothing on the page shows the new skill. What does show: `followers_school_600` follows
attack and defend orders as reliably as any pilot on the list.

## The fault that stopped two lines

`fighters_v8` stopped at 04:31 and `followers_school` at 05:09. Training was meant to run
to 07:20.

A go-to drill picks a start and a point by trial: draw a route, keep it if both ends are
inside the map. A long route fits on about one draw in eight. The code gave up after 64
draws, which fails once in about 6,700 long drills. A line flying thousands of go-to
drills a night was likely to hit that. A line's last save can be up to 50 updates old,
and both lines lost their last 33 updates.

The limit is now 4,096 draws. A drill that found its route keeps the same route, so the
tests above are unchanged. The night's training script now also restarts a line that
dies.

## The season's records

All three new pilots are added to the season, the record of every pilot trained under
these rules. Nobody is retired. The cull report lists who our retirement rules would drop,
and is a report only, which changes nothing. One of those rules keeps at most four
surviving members descended from one founder. It says the `fighters` family is over that
cap of four and names `fighters_v8_500`, `fighters_1832` and `fighters_v8_362` as the ones it would drop.

The data: `lab/population/2026-11-sim6/war/goto-school/war.json` (wins added),
`lab/population/2026-11-sim6/sweep/goto-school/` (one ship alone, by allowance), and
`lab/runs/2026-11-14-goto-school/eval/` (drills, and each pilot against its parent).

## What's next

[A second night of school](../2026-11-14-goto-school-2/results.md), already running as
this is written. `followers_school` carries on unchanged. A copy of it flies seven go-to drills in
ten alone, to see whether practice is what the lone ship lacks. And a `fighters` pilot
that mostly ignores orders gets school's first night, to see whether it works on a line
that would rather fight.
