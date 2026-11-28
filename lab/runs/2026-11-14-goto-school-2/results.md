# A second night of school: squads make their deadlines; practice alone did not help a ship alone

Shipped to the live page on 2026-11-15, `SIM_VERSION` 8 (the eighth version of the
game's rules, the one that gave go-to orders a deadline).

<!-- summary: A second night of teaching pilots to reach a point by a deadline, mostly through practice drills. The pilot that simply carried on now arrives in time in 86 go-to drills in 100, up from 70, and nearly as often when the deadline is tight. A copy that practised mostly alone got no better alone than its twin and worse at everything else. The same school also worked on a pilot that used to ignore orders, and that one joins the live page. -->

A commander can tell a ship to go to a point by a deadline. In
[the first night of go-to school](../2026-11-14-goto-school/results.md) a pilot that got
go-to drills (short practice scenarios) as most of its training learned to make the
deadline in a squad, and did not learn it alone. This night asked three things: does more
of the same keep working, does practice alone fix the lone ship, and does school work on a
pilot that would rather fight. Yes, no, and yes. The school pilot now makes 86 deadlines in
100 in the drills. A copy that practised alone is no better alone than its twin. And a
fighter that ignored orders follows them clearly better after one night, though still well
short of the school pilot.

## Where this fits

RL Fighter is a space-combat game in which every ship is flown by a small neural network,
a pilot, that learned to fly by trial and error (reinforcement learning). A commander, a
second network or a hand-written script, gives the ships of a side orders: attack that
ship, defend that ship, or go to that point. The [pilot page](/pilot/) and the
[commander page](/commander/) explain both.

On [the first night of deadlines](../2026-11-12-pilots-v8/results.md) a go-to order
gained a "be there by" time that the pilot can see. Pilots kept fighting first and arrived
late. [The first night of school](../2026-11-14-goto-school/results.md) made go-to drills
most of one line's training, and its squads went from 51 to 70 deadlines in 100. A ship
sent alone did not improve: it still went for an enemy first. A commander that
sends one ship somewhere needs that case to work too, so this night aimed at it directly.

## The night

Three lines trained from 23:31 to 06:30, about 460 updates each. A family is every pilot
descended from one starting pilot, and a line is one branch of it: a series of pilots,
each trained on from the last, that share a name. An update is one round of training: play a batch of
matches, then adjust the network once. A pilot's name is its line followed by the update
it was saved at, counted on from its parent, so `followers_school_1052` is the
`followers_school` line at update 1052. The `followers` family descends from an early
pilot that followed orders well but fought weakly, and is bred to fight and follow orders.
The `fighters` family descends from our best fighter, `f995_701`, and is bred mainly to
win fights. `fighters_pay1` is a `fighters` branch paid less for following orders, and
`_v8_` in a name means the pilot was given four extra inputs, the numbers it sees each
moment, so it can read go-to deadlines.

| Line | From | What changed |
|---|---|---|
| `followers_school` | `followers_school_600` | Nothing. A second night |
| `followers_solo` | `followers_school_600` | 7 go-to drills in 10 flown by one ship alone, where it was 1 in 4 |
| `fighters_pay1_school` | `fighters_pay1_v8_351` | What `followers_school` got on its first night: go-to drills as most of its training, a deadline worth 3 |

In a go-to drill a squad of one to four ships is told to reach a circle on the map,
usually by a deadline. "A deadline worth 3" means arriving in time pays 3 points of reward
and missing costs 3, where destroying a fighter pays about 0.8. `fighters_pay1_v8_351` is
a pilot on the live page that fights well and mostly ignores orders.

How training went: the share of ships in training that were alive at their deadline and
not there, in the first and last quarter of the night. Lower is better:

| Line | Go-to drills | Ships under a deadline | Missed, first quarter | Last quarter |
|---|---|---|---|---|
| `followers_school` | 6,866 | 13,186 | 0.20 | 0.10 |
| `followers_solo` | 7,524 | 9,047 | 0.26 | 0.22 |
| `fighters_pay1_school` | 6,342 | 11,828 | 0.54 | 0.40 |

## What the night answered

**More of the same keeps working.** The drill test: 256 go-to drills per pilot on the
same fixed starts, squads of one to four, played only to measure. Each number is the share
of ships in time, of those alive at the deadline, first over all deadlines and then by how
tight the deadline was. A deadline is set as a multiple of the time a straight flight
would take: tight is under 2.5 times, medium 2.5 to 4.5, loose over 4.5. "Script" is our
hand-written, rule-based pilot, which flies straight there:

| Pilot | In time | Tight | Medium | Loose |
|---|---|---|---|---|
| Script | 0.99 | 0.96 | 0.99 | 1.00 |
| `followers_v8_352` (two nights ago) | 0.51 | 0.30 | 0.55 | 0.74 |
| `followers_school_600` (one night ago) | 0.70 | 0.60 | 0.68 | 0.87 |
| `followers_school_1052` | 0.86 | 0.84 | 0.88 | 0.93 |
| `followers_solo_1072` | 0.78 | 0.66 | 0.78 | 0.93 |
| `fighters_pay1_v8_351` (parent) | 0.31 | 0.20 | 0.30 | 0.49 |
| `fighters_pay1_school_821` | 0.48 | 0.40 | 0.50 | 0.64 |

Each number is good to about ±0.04 overall and ±0.10 on tight deadlines alone (± is the
margin of error: the true value is very likely within that range). Two nights ago this
line made three tight deadlines in ten. Now it makes more than eight. Of all its ships
alive at the deadline, only 4 in 100 never got near the circle and were found beside an
enemy instead. Two nights ago it was 21.

**Practice alone did not help a ship alone.** The same drills, split by whether the ship
had company, and then the sweep, the larger test of a lone ship: one ship on 324 starts,
each flown at several time allowances, where 2 means twice the time a straight flight
takes. The last column is all the sweep's allowances of 1.5 and over together. The lower
ones, 0.8 and 1, are at or past the limit of what a ship can do. All are shares in time:

| Pilot | In a squad | Alone | Sweep, 2 | 5 | 8 | 1.5 and over |
|---|---|---|---|---|---|---|
| Script | 0.99 | 0.98 | 0.96 | 1.00 | 1.00 | 0.94 |
| `followers_school_600` | 0.72 | 0.41 | 0.12 | 0.54 | 0.73 | 0.31 |
| `followers_school_1052` | 0.88 | 0.51 | 0.20 | 0.58 | 0.77 | 0.37 |
| `followers_solo_1072` | 0.80 | 0.53 | 0.22 | 0.62 | 0.80 | 0.38 |
| `fighters_pay1_v8_351` | 0.32 | 0.19 | 0.05 | 0.33 | 0.49 | 0.19 |
| `fighters_pay1_school_821` | 0.49 | 0.36 | 0.12 | 0.58 | 0.78 | 0.34 |

The first two columns are the drills. "Alone" rests on about 40 ships a pilot and is
good to about ±0.15. The sweep columns are good to about ±0.05.

`followers_solo` flew about 5,300 go-to drills alone in the night and its twin about
1,700. Alone, the two came out the same: 0.22 and 0.20 at the tight allowance, 0.38 and
0.37 over allowances of 1.5 and over. Both are better than their parent (0.31). Neither is close to the script. In training the solo line's share of misses hardly fell
all night.

The practice also cost it. Over all the drills it is behind its twin, 0.78 against 0.86
and 0.66 against 0.84 on tight deadlines, and it is the weakest fighter of the night
(below).

**Where the lone ship fails: when the enemy does nothing.** The sweep puts one of three
things on the map: an enemy parked at the edge that cannot shoot, one armed enemy beside
the route, or three. Share in time at the tight allowance of 2:

| Pilot | Parked | One armed | Three armed |
|---|---|---|---|
| Script | 0.97 | 0.93 | 1.00 |
| `followers_school_600` | 0.02 | 0.21 | 0.14 |
| `followers_school_1052` | 0.01 | 0.31 | 0.36 |
| `followers_solo_1072` | 0.05 | 0.29 | 0.40 |
| `fighters_pay1_school_821` | 0.03 | 0.24 | 0.07 |

<!-- figure-idea: shared: the go-to sweep's three layouts. One lone ship and its circle, shown three ways: an unarmed enemy parked at the map's edge, one armed enemy beside the route, three armed enemies beside it, with a typical pilot path in each. Makes the "parked" result, worst against the harmless enemy, easy to see. -->

A lone school pilot makes more deadlines against three armed enemies than against one
that sits still at the edge of the map. Against the armed ones it improved a lot this
night. Against the parked one it did not improve at all. These shares are of ships still
alive at the deadline, and against three enemies about half are not.

Our reading, not yet tested: armed enemies come to the pilot, so it can fight them on the
way to the point. A parked enemy has to be flown to, and the pilot flies to it. In every
training drill the enemies attack. Nothing in training has ever shown a pilot an enemy
that it should leave alone.

**The pilots learned "go now", not "go by when".** With its deadline inputs blanked (set
to zero, so it cannot see the deadline), `followers_school_1052` is in time just as often
(0.38 against 0.37) and turns for the point just as soon: it is halfway there about 12
seconds in, at every allowance and with no deadline at all. Given a go-to with no
deadline, it now gets there promptly (within twice the straight-flight time plus 10 s)
0.38 of the time, where its parent did 0.27. Seeing a tight deadline, it does shoot less
on the way (42 damage against 56).

That is not the behaviour the deadline was built for, which was to go at once when time
is short and fight first when it is not. Nobody yet spends spare time on purpose.

**School works on a pilot that ignored orders.** `fighters_pay1_school_821` against its
parent. "Changes sides" is the swap test for attack and defend: a drill puts enemies (or
friendly ships under attack) on opposite sides of the squad and names one, then the same
start is flown again naming the other. The number is the share of starts where the squad
went to the named side both times:

| | Parent | After school |
|---|---|---|
| Go-to drills, in time | 0.31 | 0.48 |
| Found beside an enemy instead | 0.44 | 0.26 |
| Changes sides with an attack order | 0.26 | 0.41 |
| Changes sides with a defend order | 0.33 | 0.55 |
| Lone ship in the sweep, allowances 1.5 and over | 0.19 | 0.34 |

It is still well short of the `followers` line, and it still fails every bar of the drill
gate, a set of pass marks on the drill test fixed in advance. `followers_school_1052` and
`followers_solo_1072` pass every bar, and change sides with an attack or defend order more than nine times in ten.

**The second night of school cost some fighting.** Two measures. "Won against parent" is
the share of matches the new pilot won with a whole side each against its parent. "Adds"
is its wins added per 100 in mixed matches: pilots are dropped at random, ship by ship,
into matches like the live page's, and a statistical fit estimates how many more matches
in 100 a side wins with this pilot flying its ships instead of the script. We call this
WAR, wins above replacement, after the baseball measure, and 0 is the script's level:

| Pilot | Won against parent | Adds | Parent adds |
|---|---|---|---|
| `followers_school_1052` | 0.46 | +11.4 | +13.7 |
| `followers_solo_1072` | 0.34 | +8.6 | +13.7 |
| `fighters_pay1_school_821` | 0.57 | +13.4 | +14.7 |

"Adds" is good to about ±3.3. The first night of school cost nothing. After the second,
`followers_school` adds about 2 fewer wins in 100 than its parent, which is inside the
noise, and loses to it a little head to head (0.46 over 1,032 matches, good to about
±0.03), which is not. The solo line lost clearly.
The `fighters_pay1` line beats its parent head to head and adds about as many wins.

## The ten

The live page, the site's front page, plays matches forever, and each ship on it is flown
by one of ten pilots drawn at random. The ten are the pilots with the most wins added per
100 matches over the script flying the same ships, here from 4,320 matches this morning.
`f995_701`, `f995_400` and `f99_696` are older fighters from
[an earlier night](../2026-11-01-fighters-v2/results.md) that ignore orders, named for how
far ahead they were trained to plan (0.995 looks further ahead than 0.99).

1. **`f995_701`, +15.9.**
2. **`fighters_pay1_v8_351`, +14.7.**
3. **`fighters_pay1_1317`, +14.1.**
4. **`followers_school_600`, +13.7.**
5. **`fighters_pay1_462`, +13.5.**
6. **`fighters_pay1_school_821`, +13.4.** New. `fighters_pay1_v8_351` after a night of school.
7. **`f99_696`, +12.9.**
8. **`f995_400`, +12.6.**
9. **`followers_pay3_810`, +11.9.**
10. **`followers_v8_352`, +11.8.**

One pilot leaves the list: `followers_1323` (+11.6). Left off: `followers_school_1052`
(+11.4) and `followers_solo_1072` (+8.6).

So the best follower we have is not on the page. `followers_school_1052` missed tenth
place by 0.4 wins in 100, and places nine to twelve are a coin toss at this many matches.
The list goes by wins added and nothing else, so it stays off for now. Its parent, one
night of school behind it, is fourth.

## One more fault of the same kind

`fighters_pay1_school` stopped at 01:49 when a drill failed to set itself up and the
training program halted with an error. The night's script started it again from its last
save, and it lost 14 updates.

The cause is a cousin of [yesterday's fault](../2026-11-14-goto-school/results.md), where
a go-to drill gave up after 64 tries at fitting a long route on the map and stopped two
training runs. This time it was
the next step: a drill places its enemies beside the route by trial, and also gave up
after 64 tries. When a route
starts near the middle of the map there is little room, and about one go-to drill in
150,000 found none. That limit is now 4,096 tries too.

## The season's records

All three new pilots are added to the season, the record of every pilot trained under
these rules. Nobody is retired. The cull report lists who our retirement rules would drop,
and is a report only, which changes nothing. One of those rules keeps at most four
surviving members descended from one founder. It says both families are over that cap of
four and names `followers_solo_1072`, `followers_school_1052` and `fighters_pay1_school_821` as the ones
it would drop.

The data: `lab/population/2026-11-sim6/war/goto-school-2/war.json` (wins added),
`lab/population/2026-11-sim6/sweep/goto-school-2/` (one ship alone, by allowance), and
`lab/runs/2026-11-14-goto-school-2/eval/` (drills, and each pilot against its parent).

## What's next

Not decided. Three things this night points at:

- **An enemy to leave alone.** Give go-to drills an enemy that sits still, the one case
  where a lone ship did not improve at all.
- **Spare time.** Pilots now hurry on every go-to. If a commander is to say "by when" and
  mean it, a drill has to pay for using the time, not only for making it.
- **A commander that gives deadlines.** No commander does yet. In a squad, school pilots
  can now meet one.
