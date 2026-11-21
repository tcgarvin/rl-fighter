# Dock pilot: two followers learn to come home

Two live followers trained for a night with dock drills as half their drills. Both learned
to fly home and dock when ordered to, which no learned pilot did before: the stronger one
docks 57 calm drills in 100 where its parent docked 2, and 27 in 100 with enemies on its
tail. In real matches they still mostly don't make it home: 5 to 8 recalls in 100 end in a
dock, against 2 before. They became two new members of the pilot season, and wins above
replacement decides whether they fly on the live page. No rule of the game changed
(`SIM_VERSION` 11).

<!-- summary: Damaged fighters can be called home to repair, but our trained pilots never answered the call. Two of them practised it for a night, alone and with enemies chasing them. They learned: the better one now lands more than half the time when it has a clear run home, and about a quarter of the time with enemies on its tail, where before it almost never did. In a real battle they still rarely make it back. They mostly never get close, perhaps because they keep fighting. They now compete for a place on the live page like every other pilot. -->

The plan is in [plan.md](plan.md), the drills and the rules in
[dock and repair](../2026-11-20-dock-repair/results.md). Both arms widened their parent from
587 to 592 inputs (the dock block) and trained on Beast from 18:20 to 01:30, about 8 s an
update:

| Arm | Parent | Updates | Member id |
|---|---|---|---|
| `dock600` | `followers_school_600` | 2,624 | `followers_dock_2624` |
| `dock352` | `followers_v8_352` | 2,676 | `followers_dock_v8_2676` |

The full tables are in [report.md](report.md). The ± are 1.96 standard errors.

## Docking

Drills at the final checkpoint, 128 a kind (the parents on the same drills):

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

Order drills held or improved: go-to arrivals rose from 0.63 to 0.79 (`dock600`) and from
0.52 to 0.82 (`dock352`), since a dock order reads as a go-to to the bay. Attack and defend
drills stayed within noise of the parents.

Against the script, both lost a little in carrier battles: 0.90 to 0.82 (`dock600`) and
0.95 to 0.89 (`dock352`), about two standard errors. Convoy and fleet scores held. One
guess, not tested: a pilot that now turns for home when recalled, but doesn't finish the
trip, spends fighting time for nothing.

## How they were judged

The plan set five pass bars, and on them both arms failed. The owner has since changed the
rule: a pilot that learns something new joins the season, and wins above replacement
(WAR) and the family rules decide what flies live, not a run's bars. The bars stay here as
measurements.

## Wins above replacement

The two new pilots joined the season as children of their parents and played a WAR round
with the ten live pilots and both parents: 5,760 matches, 1,440 in each of the four live
missions. The station assault is in WAR for the first time, the citadel as the live page
plays it; before, WAR played only deathmatch, carrier battle and convoy. Commanders came from
the live stable, so about one side in four had the scripted commander, the only one that
recalls. Wins added per 100 matches a pilot flew in, over the script flying its ships:

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
margin of 0.1 inside intervals six wide; it is the rule doing what it is for, giving a new
skill a place on the page, not a sign that the new pilot is better. On the page it is the
one pilot that turns for home when the scripted commander recalls it.

The order of the top ten moved from the last round (`goto-school-2`), where `f995_701` was
first at +15.9: this round has the station assault, v11's recalls, and different
company, so the two rounds don't compare number for number.

## Next

The match-level gap is the thing to fix: practice runs teach the approach, but in a fight
the recall competes with everything else the pilot was paid for. Recalls inside real
matches carry no extra pay beyond the dock bonus at the bay, so the trip home pays nothing
until it ends.
