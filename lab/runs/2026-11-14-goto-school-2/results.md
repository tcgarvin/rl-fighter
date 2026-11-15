# A second night of school: squads make their deadlines; practice alone did not help a ship alone

Shipped to the live page on 2026-11-15, `SIM_VERSION` 8.

<!-- summary: Another night of go-to school. The pilot that simply carried on now makes 86 go-to deadlines in 100 in a squad, up from 70, and nearly as many when the deadline is tight. A copy that flew most of its go-to drills alone got no better alone than its twin and worse at everything else. School also worked on a pilot that used to ignore orders, and that one joins the live page. -->

A commander can tell a ship to go to a point by a deadline. In
[the first night of go-to school](../2026-11-14-goto-school/) a pilot that got go-to drills
as most of its training learned to make the deadline in a squad, and did not learn it
alone. This night asked three things: does more of the same keep working, does practice
alone fix the lone ship, and does school work on a pilot that would rather fight.

## The night

Three lines trained from 23:31 to 06:30, about 460 updates each.

| Line | From | What changed |
|---|---|---|
| `followers_school` | `followers_school_600` | Nothing. A second night |
| `followers_solo` | `followers_school_600` | 7 go-to drills in 10 flown by one ship alone, where it was 1 in 4 |
| `fighters_pay1_school` | `fighters_pay1_v8_351` | What `followers_school` got on its first night: go-to drills as most of its training, a deadline worth 3 |

A drill is a short practice match: a squad of one to four ships is told to reach a
circle. `fighters_pay1_v8_351` is a pilot on the live page that fights well and mostly
ignores orders.

Through the night, the share of ships in training that were alive at their deadline and
not there:

| Line | Go-to drills | Ships under a deadline | Missed, first quarter | Last quarter |
|---|---|---|---|---|
| `followers_school` | 6,866 | 13,186 | 0.20 | 0.10 |
| `followers_solo` | 7,524 | 9,047 | 0.26 | 0.22 |
| `fighters_pay1_school` | 6,342 | 11,828 | 0.54 | 0.40 |

## What the night answered

**More of the same keeps working.** The drill test: 256 go-to drills per pilot on fixed
starts, squads of one to four. Share of ships in time, of those alive at the deadline,
and then by how tight the deadline was:

| Pilot | In time | Tight | Medium | Loose |
|---|---|---|---|---|
| Script | 0.99 | 0.96 | 0.99 | 1.00 |
| `followers_v8_352` (two nights ago) | 0.51 | 0.30 | 0.55 | 0.74 |
| `followers_school_600` (one night ago) | 0.70 | 0.60 | 0.68 | 0.87 |
| `followers_school_1052` | 0.86 | 0.84 | 0.88 | 0.93 |
| `followers_solo_1072` | 0.78 | 0.66 | 0.78 | 0.93 |
| `fighters_pay1_v8_351` (parent) | 0.31 | 0.20 | 0.30 | 0.49 |
| `fighters_pay1_school_821` | 0.48 | 0.40 | 0.50 | 0.64 |

Each number is good to about ±0.04 overall and ±0.10 on tight deadlines alone. Two
nights ago this line made three tight deadlines in ten. Now it makes more than eight.
Only 4 ships in 100 are found beside an enemy instead; two nights ago it was 21.

**Practice alone did not help a ship alone.** The same drills, split by whether the ship
had company, and then the sweep: one ship on 324 starts, each flown at several time
allowances, where 2 means twice the time a straight flight takes.

| Pilot | In a squad | Alone | Sweep, 2 | 5 | 8 |
|---|---|---|---|---|---|
| Script | 0.99 | 0.98 | 0.96 | 1.00 | 1.00 |
| `followers_school_600` | 0.72 | 0.41 | 0.12 | 0.54 | 0.73 |
| `followers_school_1052` | 0.88 | 0.51 | 0.20 | 0.58 | 0.77 |
| `followers_solo_1072` | 0.80 | 0.53 | 0.22 | 0.62 | 0.80 |
| `fighters_pay1_v8_351` | 0.32 | 0.19 | 0.05 | 0.33 | 0.49 |
| `fighters_pay1_school_821` | 0.49 | 0.36 | 0.12 | 0.58 | 0.78 |

The first two columns are the drills; "Alone" rests on about 40 ships a pilot and is
good to about ±0.15. The sweep columns are good to about ±0.05.

`followers_solo` flew about 5,300 go-to drills alone in the night and its twin about
1,700. Alone, the two came out the same: 0.22 and 0.20 at the tight allowance, 0.38 and
0.37 over every allowance a ship can make. Both are better than their parent (0.31).
Neither is close to the script. In training the solo line's share of misses hardly fell
all night.

The practice also cost it. Over all the drills it is behind its twin, 0.78 against 0.86
and 0.66 against 0.84 on tight deadlines, and it is the weakest fighter of the night
(below).

**Where the lone ship fails: when the enemy does nothing.** The sweep puts one of three
things on the map: an enemy parked at the edge that cannot shoot, one armed enemy beside
the route, or three. Share in time at the tight allowance:

| Pilot | Parked | One armed | Three armed |
|---|---|---|---|
| Script | 0.97 | 0.93 | 1.00 |
| `followers_school_600` | 0.02 | 0.21 | 0.14 |
| `followers_school_1052` | 0.01 | 0.31 | 0.36 |
| `followers_solo_1072` | 0.05 | 0.29 | 0.40 |
| `fighters_pay1_school_821` | 0.03 | 0.24 | 0.07 |

A lone school pilot makes more deadlines against three armed enemies than against one
that sits still at the edge of the map. Against the armed ones it improved a lot this
night. Against the parked one it did not improve at all. These shares are of ships still
alive at the deadline, and against three enemies about half are not.

Our reading, not yet tested: armed enemies come to the pilot, so it can fight them on the
way to the point. A parked enemy has to be flown to, and the pilot flies to it. In every
training drill the enemies attack. Nothing in training has ever shown a pilot an enemy
that it should leave alone.

**The pilots learned "go now", not "go by when".** With its deadline inputs blanked,
`followers_school_1052` is in time just as often (0.38 against 0.37) and turns for the
point just as soon: it is halfway there about 12 seconds in, at every allowance and with
no deadline at all.
Given a go-to with no deadline, it now gets there promptly 0.38 of the time, where its
parent did 0.27. Seeing a tight deadline, it does shoot less on the way (42 damage
against 56).

That is not the behaviour the deadline was built for, which was to go at once when time
is short and fight first when it is not. Nobody yet spends spare time on purpose.

**School works on a pilot that ignored orders.** `fighters_pay1_school_821` against its
parent:

| | Parent | After school |
|---|---|---|
| Go-to drills, in time | 0.31 | 0.48 |
| Found beside an enemy instead | 0.44 | 0.26 |
| Changes sides with an attack order | 0.26 | 0.41 |
| Changes sides with a defend order | 0.33 | 0.55 |
| Lone ship, over every allowance it can make | 0.19 | 0.34 |

It is still well short of the `followers` line, and it still fails every bar of the drill
gate. `followers_school_1052` and `followers_solo_1072` pass every bar, and
change sides with an attack or defend order more than nine times in ten.

**The second night of school cost some fighting.** Each new pilot against its parent, a
whole side each, and wins added per 100 in mixed matches:

| Pilot | Won against parent | Adds | Parent adds |
|---|---|---|---|
| `followers_school_1052` | 0.46 | +11.4 | +13.7 |
| `followers_solo_1072` | 0.34 | +8.6 | +13.7 |
| `fighters_pay1_school_821` | 0.57 | +13.4 | +14.7 |

"Adds" is good to about ±3.3. The first night of school cost nothing. After the second,
`followers_school` adds about 2 fewer wins in 100 than its parent, which is inside the
noise, and loses to it a little head to head, which is not. The solo line lost clearly. The `fighters_pay1` line beats
its parent head to head and adds about as many wins.

## The ten

The live page flies ten pilots, drawn ship by ship. Wins added per 100 matches over the
script flying the same ships, from 4,320 matches this morning.

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

`fighters_pay1_school` stopped at 01:49. The night's script started it again from its
last save, and it lost 14 updates.

The cause is a cousin of [yesterday's fault](../2026-11-14-goto-school/). A go-to drill
places its enemies beside the route by trial, and gave up after 64 tries. When a route
starts near the middle of the map there is little room, and about one go-to drill in
150,000 found none. That limit is now 4,096 tries too.

## The season's records

All three new pilots are added to the season. Nobody is retired. The cull report, which is
a report only, says both families are over their cap of four lines and names
`followers_solo_1072`, `followers_school_1052` and `fighters_pay1_school_821` as the ones
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
