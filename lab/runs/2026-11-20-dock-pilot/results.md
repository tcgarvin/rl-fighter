# Dock pilot: two followers learn to come home

Since [dock and repair](../2026-11-20-dock-repair/results.md), a damaged strike craft
(one of the small piloted ships) can be called home to its carrier or station to be
repaired, but none of our trained pilots answered the call. Could a pilot learn to fly
home and land when ordered, and carry that into real battles? Two pilots from the
followers family (bred to fight and follow orders) trained for a night on dock drills,
short practice scenarios in which a damaged craft is ordered home, alone or chased. Dock
drills were half of their drills. Both learned to fly home and dock when ordered to,
which no learned pilot did before: the stronger one docks 57 calm drills in 100 where its
parent (the pilot it started from) docked 2, and 27 in 100 with enemies on its tail. In
real matches they still mostly don't make it home. The stronger one completes 5 to 8
recalls in 100, against its parent's 2; the other 3 to 7, against its parent's 3 to 5.
They became two new members of the pilot season (every pilot trained under the current
rules), and wins above replacement, a rating of how many more matches a side wins with a
pilot than with our hand-written one, decides whether they fly on the live page. No rule
of the game changed (`SIM_VERSION` 11).

<!-- summary: Damaged fighters can be called home to repair, but our trained pilots never answered the call. Two of them practised it for a night, alone and with enemies chasing them. They learned: the better one now lands more than half the time when it has a clear run home, and about a quarter of the time with enemies on its tail, where before it almost never did. In a real battle they still rarely make it back. They mostly never get close, perhaps because they keep fighting. They now compete for a place on the live page like every other pilot. -->

## Where this fits

RL Fighter is a space-combat game in which every small ship is flown by a neural network
that learned to fly by trial and error. Each side can also have a commander that gives
its ships orders. Earlier the same day, [dock and repair](../2026-11-20-dock-repair/results.md)
added the rule that lets a craft land, repair and launch again, and taught the scripted
commander (the hand-written one) to recall any craft below half its hull. With the script,
our hand-written rule-based pilot, flying, three recalls in five ended in a dock. With
the ten live pilots, the trained networks that fly on the website's front page, about 1
in 70 did: they kept fighting, and the few that reached the bay flew through it too fast.
The owner wants docking taught, not done for the pilots by the sim, so the next step was
a docking drill and a night of training on it. Both pilots chosen are followers.
`followers_school_600`, the best order follower among the live ten, came out of
[go-to school](../2026-11-14-goto-school/results.md), a night spent mostly on drills that
send ships to a point by a deadline. Its parent `followers_v8_352`, a weaker follower
from [pilots v8](../2026-11-12-pilots-v8/results.md), was the live pilot that docked most
often untrained. A pilot's name is its training line followed by the update (one round of
training) it was saved at.

The plan, including how the drill is built, is in [plan.md](plan.md); the dock rules are
in [dock and repair](../2026-11-20-dock-repair/results.md). Each of the two arms (versions
of the experiment, here identical except for the starting pilot and the random seed) gave
its parent the five new dock inputs (a "dock" flag, how the bay is moving and which way
it faces), widening it from 587 to 592 numbers read each moment. Both trained on Beast, the lab's
desktop with two graphics cards, from 18:20 to 01:30, about 8 s an update. The member id is the name each new pilot joined the season
under.

<div data-figure="diagram" data-name="training-night" data-caption="Here the night had two parents, followers_school_600 and its own parent followers_v8_352, and one arm from each, given the five new dock inputs. Both trained from 18:20 to 01:30."></div>

| Arm | Parent | Updates | Member id |
|---|---|---|---|
| `dock600` | `followers_school_600` | 2,624 | `followers_dock_2624` |
| `dock352` | `followers_v8_352` | 2,676 | `followers_dock_v8_2676` |

The full tables are in [report.md](report.md). The ± in this entry is the margin of
error (1.96 standard errors): the true value very likely lies within that range.

## Docking

Drills at the final checkpoint (the saved network at the end of training), 128 a kind.
The parents flew the same drills. A calm drill is a damaged craft alone, ordered home
from 150 to 350 m out. In a drill under fire, one or two script-flown craft start behind
it with orders to attack it. The home base is a carrier under way, a station, or the
citadel (a much bigger station). Each number is a share of drills, except the last two
rows, which are the share of recalls that ended in a dock in real matches under the
scripted commander: carrier battles (each side has a carrier, and a side wins by
destroying the other's) and station assaults (one side defends a station, the other
attacks it with a carrier and bombers).

<div data-figure="diagram" data-name="dock-loop" data-caption="A dock drill starts with a craft already ordered home, and practises the trip and the landing. The match rows below count the whole loop under the scripted commander."></div>

<!-- figure-idea: the two dock drills side by side: a damaged craft 150 to 350 m from its carrier, station or citadel, alone (calm) or with one or two script craft starting 90 to 200 m behind it (under fire), and the 10 m, 15 m/s capture rule at the bay. -->

| | `followers_school_600` | `dock600` 2624 | `followers_v8_352` | `dock352` 2676 |
|---|---|---|---|---|
| Calm: docked | 0.02 | **0.57** ± 0.09 | 0.01 | **0.38** ± 0.08 |
| Calm: shot down | 0.08 | 0.09 | 0.12 | 0.15 |
| Under fire: docked | 0.02 | **0.27** ± 0.08 | 0.01 | **0.14** ± 0.06 |
| Under fire: docked, of those not shot down | 0.05 | 0.53 | 0.02 | 0.27 |
| Carrier battle: recalls that end in a dock | 0.02 | 0.05 | 0.05 | 0.03 |
| Station assault: recalls that end in a dock | 0.02 | 0.08 | 0.03 | 0.07 |

The script docks 0.95 calm and 0.58 under fire; in matches it completes 0.54 to 0.64 of
its recalls.

`dock600` was still climbing when the clock stopped it: calm docks in training went from
0.15 to 0.51 over its last 900 updates. `dock352` levelled off near 0.35 from update 1,500.

**In matches the skill does not carry over yet.** Of the recalls that fail in a carrier
battle, two in three are "never close": the craft never gets near its bay. Overshooting
the bay and arriving too fast come next. In a drill the trip home is the whole exercise;
in a match the craft is still in the fight when the order comes, and it mostly stays
there. We haven't yet looked at what it does instead.

## What else moved

Order drills (practice scenarios for the attack, defend and go-to orders) held or
improved: go-to arrivals rose from 0.63 to 0.79 (`dock600`) and from 0.52 to 0.82
(`dock352`), since a dock order reads as a go-to (fly to a point) to the bay. Attack and
defend drills stayed within noise of the parents.

Against the script, both lost a little in carrier battles: their win rate went from 0.90
to 0.82 (`dock600`) and 0.95 to 0.89 (`dock352`), about two standard errors. Convoy and
fleet scores held. One guess, not tested: a pilot that now turns for home when recalled,
but doesn't finish the trip, spends fighting time for nothing.

## How they were judged

The plan set five pass bars, and on them both arms failed. The owner has since changed the
rule: a pilot that learns something new joins the season, and wins above replacement
(WAR) and the family rules (which keep any one line from crowding out the others) decide
what flies live, not a run's bars. The bars stay here as measurements.

## Wins above replacement

WAR is borrowed from baseball. Pilots are dropped at random into matches like the live
page's, and a statistical fit estimates how many more matches out of 100 a side wins with
that pilot flying its ships instead of the script. 0 is the script's level.

The two new pilots joined the season as children of their parents and played a WAR round
with the ten live pilots and both parents: 5,760 matches, 1,440 in each of the four live
missions. The station assault is in WAR for the first time, against the citadel, the big
station the live page always uses; before, WAR played only deathmatch, carrier battle and convoy. Commanders came from
the live stable (the commanders the live page draws from), so about one side in four had
the scripted commander, the only one that recalls. In the table, WAR is wins added per
100 matches a pilot flew in, over the script flying its ships. The interval is the range
the true value very likely lies in, and the last column is WAR in the station assault
alone. The new pilots are in bold. Of the other names, `fighters_...` pilots come from
the fighters family, bred mainly to win fights (`fighters_pay1_...` a branch paid less
for following orders), `followers_...` from the followers family, bred to fight and
follow orders, and `f995_...` / `f99_...` are strong fighters that ignore orders, from
[fighters v2](../2026-11-01-fighters-v2/results.md).

| Pilot | WAR | 95% interval | Station assault |
|---|--:|---|--:|
| fighters_pay1_1317 | +12.7 | +9.9 to +15.5 | +13.5 |
| followers_pay3_810 | +11.7 | +8.5 to +14.7 | +12.9 |
| fighters_pay1_v8_351 | +11.6 | +8.7 to +14.6 | +12.4 |
| f995_400 | +11.4 | +8.7 to +14.3 | +12.6 |
| f99_696 | +11.0 | +8.2 to +13.9 | +12.0 |
| fighters_pay1_462 | +10.5 | +7.7 to +13.5 | +11.8 |
| followers_v8_352 | +10.0 | +7.1 to +13.0 | +10.8 |
| f995_701 | +9.4 | +6.7 to +12.3 | +10.2 |
| followers_school_600 | +9.1 | +6.5 to +12.4 | +9.9 |
| **followers_dock_v8_2676** | **+8.9** | +5.9 to +12.1 | +9.8 |
| fighters_pay1_school_821 | +8.8 | +6.0 to +11.6 | +9.6 |
| **followers_dock_2624** | **+8.0** | +5.2 to +10.7 | +8.9 |

Each new pilot rates a little below its parent, within the interval. That fits the small
loss in carrier battles above: docking is not yet worth wins. `followers_dock_v8_2676` is
tenth, so it joins the live list and `fighters_pay1_school_821` leaves it. That is a
margin of 0.1 inside intervals six wide. It is the selection rule working as intended:
the ten highest by WAR fly live, with no pass marks to clear first, and that is how a
pilot with a new skill gets a place on the page. It is not a sign that the new pilot is
better. On the page it is the
one pilot that turns for home when the scripted commander recalls it.

The order of the top ten moved from the last round, in
[the second night of go-to school](../2026-11-14-goto-school-2/results.md), where
`f995_701` was first at +15.9: this round has the station assault, v11's recalls, and
different company, so the two rounds don't compare number for number. Each WAR table is
its own fit, so compare pilots within one table.

## Next

The match-level gap is the thing to fix: practice runs teach the approach, but in a fight
the recall competes with everything else the pilot was paid for. Recalls inside real
matches carry no extra pay beyond the dock bonus at the bay (a reward paid on landing, 1.0
in this run), so the trip home pays nothing until it ends.
