# Mission survey: carrier battles end in a carrier kill, convoys are a real contest

Run 2026-10-30, plan: `plan.md`. `SIM_VERSION` 4 (the fourth version of the game's
rules), branch `m3-sim2`.

<!-- summary: We added two new missions, a carrier battle and a convoy escort, and tuned them until they were fair fights worth watching. With the hand-written commander and the learned pilot of the day, carrier battles end with a carrier destroyed 98 % of the time after a median 116 s, each side winning about half. Convoy attackers win 52 to 62 % of matches on every default lineup. -->

The game was getting two new missions. In a **carrier battle** each side has a carrier,
a big slow ship that launches its small strike craft over the course of the match. A
side wins by destroying the enemy carrier, and at the time limit the side whose carrier
has more hull left wins. In a **convoy escort** one side's escorts guard three to five
freighters flying to a jump point, where they charge and jump out. The other side jumps
in to attack. The attackers win by destroying at least half the freighters, and the
defenders win when enough escape. Each side also gets a **commander**, a hand-written
program that decides when to launch ships, where the big ships go, and what each squad
should do. Before anyone trained pilots on these missions, we wanted each one to end
for the right reason, at a length worth watching, and close to even. We played batches
of matches, changed ship numbers and lineups, and played again. The answer is yes:
carrier battles nearly always end with a carrier destroyed, after about two minutes,
and either side wins about half. Convoys go either way on every lineup.

Verdict: **PASS**. Every target the plan set is met in the setup the project's website
shows its visitors.

## Where this fits

RL Fighter is a space-combat game where every small ship is flown by a neural network
that learned to fly by trial and error. Its website's front page, the **live page**,
plays matches forever. Until now every match was a straight fight, first duels, then
team deathmatch: small ships only, 1 to 4 a side, until one side is destroyed. The day
before, [fleet pilot v1](../2026-10-30-fleet-pilot/results.md) became the first single
network that flies every ship type and beats the hand-written pilots in fleet fights.
It was then the one pilot on the live page. The owner's next ask was carriers, convoys
and a layer of command above the pilots, so matches have different goals. The
commander gives each squad an **order** (attack a ship, guard a ship, hold a point).
This entry is the first measurement with the real hand-written commander in place.
Fleet pilot v1 cannot see orders, so for now the commander acts only through launches
and the movement of the big ships. The next step, called stage B in the project plan
(`docs/M3_PLAN.md`, where this survey is milestone M3, stage A, work package WP-S2),
teaches pilots to follow orders by copying hand-written pilots that already do.

<div data-figure="diagram" data-name="missions" data-caption="This survey played the first three missions. The station assault, bottom right, did not exist yet: it came three weeks later, in rules version 9."></div>
<!-- figure-idea: shared: the command layer, a commander above its side's ships, sending launches, a carrier waypoint and one order per squad (attack, guard, hold) down to the pilots. -->

## Verdict in detail

The setup being balanced is the live one: fleet pilot v1 flying every strike craft,
hand-written scripts flying the carriers and freighters, and the scripted commander on
both sides. In it, every target the plan set in its §3 is met (the table of targets is
below the convoy results). When hand-written pilots fly every ship instead, the convoy
is lopsided lineup by lineup. That matters for stage B, where pilots learn from those
scripts, not for the live page.

## What ran

- Two ways of playing, the same matches otherwise. *Live*: as above, the setup the
  page shows, which is the one being balanced. *Script*: hand-written pilots fly every
  ship and follow their commander's orders. Script mode is checked only to see that it
  makes a real match, since stage B will learn from it.
- A baseline first: the placeholder ("stub") commander and ship numbers from the
  previous step (WP-S1), 32 matches per lineup. Then the real commander
  (`scripted/commander.rs`), strike-craft scripts that follow orders
  (`scripted/orders.rs`) and a retuned script for flying the carrier, tuned in live
  mode at 32 to 96 matches per lineup. Then a final 128 matches per lineup in both
  modes (`survey/*.json`, tables in `survey/*.md`). Tuning and final runs used
  different random seeds (500000, and seed 1 for some carrier steps).
- `tools/mission_survey.py --mode live|script`. In live mode pilot v1 picks each
  action at random from its learned odds, as it does on the page, rather than always
  taking its top choice.

## Final, live configuration (n = 128 per roster)

A **roster** is the lineup of ships each side gets. Each row below is one default
carrier-battle roster ("wing of 8" means each side has its carrier and 8 strike craft:
2 jump in at the start and the other 6 wait in the hangar to be launched, so "launches"
counts 12 a match, both sides together), and "all" pools them. The columns: the share of matches each side won (a draw counts
half), the share that ran out the 150 s clock, the match length that half the matches
end within (median) and that 90 % end within (p90), strike craft
launched per match, when in the match the launches happened (median and p90, in
seconds), and the average number of launches in each 30-second slice of the match.

Carrier battle (150 s clock):

| roster | team 0 win | team 1 win | time limit | median s | p90 s | launches | launch median s | launch p90 s | launches per 30 s |
|---|---|---|---|---|---|---|---|---|---|
| wing of 8 | 0.52 | 0.48 | 0.01 | 120 | 138 | 12.0 | 36 | 64 | 4.9 5.3 1.8 0 0 |
| wing of 6 | 0.48 | 0.52 | 0.02 | 105 | 130 | 8.0 | 10 | 24 | 7.6 0.4 0 0 0 |
| wing of 9 | 0.48 | 0.52 | 0.03 | 124 | 139 | 14.0 | 40 | 70 | 5.0 5.8 3.1 0.1 0 |
| all | 0.49 | 0.51 | 0.02 | 116 | 136 | 11.3 | 28 | 64 | 5.8 3.8 1.6 0 0 |

Every other ending is a carrier kill. Carriers move about 270 m a match; a surviving
carrier ends with about 37 % of its hull.

<!-- figure-idea: a carrier battle on a timeline: launches per 30-second slice as bars, the two wings thinning, and the carriers closing for the endgame. Helps the reader see "launches are front-loaded" and "the result rests on the carriers' endgame" at a glance. -->

In the convoy table each row is a default roster named by its number of freighters.
"Escaped" and "destroyed" are freighters per match, "route progress" is how far along
its route the convoy got (1 is the jump point), and the last column is the share of
defender wins in which at least one freighter escaped.

Convoy escort (120 s clock):

| roster | defenders win | attackers win | time limit | median s | p90 s | escaped | destroyed | route progress | defender wins with an escape |
|---|---|---|---|---|---|---|---|---|---|
| 4 freighters | 0.39 | 0.61 | 0.00 | 64 | 72 | 1.33 | 1.38 | 0.87 | 1.00 |
| 3 freighters | 0.38 | 0.62 | 0.00 | 64 | 68 | 0.82 | 1.34 | 0.90 | 1.00 |
| 5 freighters | 0.48 | 0.52 | 0.00 | 71 | 75 | 1.66 | 2.05 | 0.93 | 1.00 |
| all | 0.42 | 0.58 | 0.00 | 67 | 72 | 1.27 | 1.59 | 0.90 | 1.00 |

Defenders win by getting the convoy through (`convoy_through`: enough freighters escape
that the attackers can no longer destroy half, so 3 of 4, 2 of 3 or 3 of 5), and in one
or two matches by destroying all the raiders. Attackers win by destroying enough of it
(`convoy_destroyed`: at least half the convoy). Nothing goes to the clock.

The targets were fixed in the plan before the tuning began. Each line is one target and
what the final run measured:

| target (plan §3) | result |
|---|---|
| carrier: time-limit rate ≲ 20 % | 2 % ✓ |
| carrier: median 60–150 s | 116 s ✓ |
| carrier: symmetric rosters ~50/50 | 0.48–0.52 ✓ |
| carrier: launches across the match | median 28 s, p90 64 s, some to 90 s ✓ (front-loaded, see below) |
| convoy: attackers 35–65 % on every roster | 0.61 / 0.62 / 0.52 ✓ |
| convoy: median 45–120 s | 64–71 s ✓ |
| convoy: route travelled, escapes in defender wins | progress 0.90; an escape in 100 % of defender wins ✓ |
| deathmatch unchanged | `v3_compat_*` pass untouched ✓ |

The last row means recorded deathmatches from the previous rules version still replay
move for move, so nothing here changed how a deathmatch plays.

## Baseline (WP-S1 stub and hull numbers, n = 32 per roster)

The same measurements with the placeholder commander, before any tuning, in both modes:

| mode | mission | team 0 win | time limit | median s | launch median / p90 s | launches per 30 s | escaped / destroyed |
|---|---|---|---|---|---|---|---|
| live | carrier battle | 0.44 | 0.14 | 123 | 4 / 28 | 10.4 0.9 0 0 0 | |
| live | convoy escort | 0.96 | 0.00 | 54 | | | 2.61 / 0.23 |
| script | carrier battle | 0.45 | 0.10 | 122 | 4 / 16 | 11.3 0 0 0 0 | |
| script | convoy escort | 0.95 | 0.00 | 54 | | | 2.61 / 0.19 |

The stub emptied both hangars in the first seconds, and the convoy (14 m/s freighters
with 500 hp, or hit points) got through 96 % of the time.

## Tuning (live mode)

Each step changed some numbers and played again. This is the record of how the final
numbers were reached, and a reader can skip to the paragraph after it. "hp" is hit
points, "mains" and "RCS" are the carrier's main engines and its turning thrusters
(in newtons), "cap" is top speed in m/s, and `WING_BASE` is how many strike craft the
commander keeps in space at the least (one more is added every 30 s). In step 8,
"winning" is the commander's own judgment that its side is ahead, which makes its
carrier close on the enemy's.

| step | change | result |
|---|---|---|
| 1 | WP-S2 commander, order-following scripts, carrier pilot (hp 1500, mains 300 N, RCS 450 N, cap 8) | carrier: time limit 0.24, launches still 8.3 of 11.3 in the first 30 s |
| 2 | freighter hp 500 → 360, cap 14 → 10 | convoy attackers 0.71 (0.47 / 0.94 / 0.72) |
| 3 | freighter 420 hp, cap 11 | attackers 0.36 |
| 4 | freighter 400 hp, cap 10.5 | attackers 0.47 overall, but 0.38 / 0.78 / 0.27 per roster |
| 5 | six candidate convoy rosters (n = 96) | 4F + 3 escorts v 6: 0.54; 3F + 4 v 5: 0.55; 5F + 4 v 8: 0.48 → the defaults (4F + 4 v 6 was 0.24, 3F + 3 v 4 0.82, 5F + 4 v 7 0.33) |
| 6 | carrier hp 1100, `WING_BASE` 4 → 3, launches ≥ 6 s apart | carrier: time limit 0.12, launch p90 52 s |
| 7 | launches ≥ 12 s apart (seed 1) | time limit 0.23 (wing of 9: 0.35): fewer ships early, slower kills |
| 8 | carrier hp 1000; the last 60 s (was 40) the carrier closes on the enemy carrier even when threatened; "winning" also on a 0.2 hull lead | time limit 0.02, median 116 s |

In step 5, "4F + 3 escorts v 6" means four freighters and three escorts against six
attackers.

What decided the carrier battle: by the end both wings are spent (0.7 strike craft
left a side, hangars empty), so the result rests on the carriers' endgame. With the
stub and in step 7, a threatened carrier retreated instead of closing, and two
crippled carriers ran out the clock. Letting the clock override the retreat, with a
somewhat lighter carrier, turned nearly all of those into kills.

## Script vs script (n = 128 per roster)

Here the hand-written pilots fly every ship. "Team 0 win" is the first side's share of
wins (in a convoy, the defenders').

| mission | roster | team 0 win | time limit | median s | notes |
|---|---|---|---|---|---|
| carrier battle | wing of 8 | 0.41 | 0.23 | 138 | |
| carrier battle | wing of 6 | 0.55 | 0.16 | 136 | |
| carrier battle | wing of 9 | 0.39 | 0.15 | 135 | |
| carrier battle | all | 0.45 | 0.18 | 136 | launch median 16 s, p90 40 s (more scrambles) |
| convoy escort | 4 freighters | 0.00 | 0.00 | 50 | the 3 scripted escorts lose every time |
| convoy escort | 3 freighters | 0.98 | 0.00 | 68 | 4 escorts against 5 raiders win every time |
| convoy escort | 5 freighters | 0.73 | 0.00 | 75 | |

(A "scramble" is the commander launching from every bay at once because enemies threaten
its carrier.)

The scripts play every mission to a proper end, but the scripted convoy escort is
lopsided per roster: scripted escorts guarding a transport fight far better against
5 raiders than 3 escorts do against 6. Pilot v1 does not read orders, so none of this
reaches the live page. It does matter for stage B, where the scripts are the
order-following teacher. If the teacher needs balanced convoys, that should be tuned
in how the defending commander splits its escorts between guarding a freighter and
flying out to intercept raiders, not in the hulls the live balance rests on.

## Decisions and notes

- **Arena, route and clocks unchanged** (450 m, `(0, −0.55 R)` → `(0, +0.75 R)`
  with R the arena radius, 150 s and 120 s, and `jump_in` 2: the first two
  strike craft a side jump in at the start, the rest launch from the hangar). The balance came from hulls, rosters and the
  commander. The carrier's mounts are unchanged (they are the art contract, the fixed
  points the rules and the 3D model share); only its forces, cap and hull
  changed.
- **Launch spread.** Launches are paced (12 s apart outside a scramble), but pilot
  v1's dogfights empty a wing fast, so most launches come in the first minute. Wider
  spacing (step 7) brought back the clock problem. Visible launches to about 90 s
  look like a fair trade.
- **Carrier braking.** The carrier slows down by drag alone (it sheds most of its
  speed in about 10 s, a ≈ 10 s time constant). It turns so slowly (0.15 rad/s²) that
  turning round to fire its engines against its motion, a flip-and-burn, would take
  longer than coasting down, so its script does not try.
- Survey runs on a busy machine (another project's sweep was using most cores) took
  4–12 minutes each; the numbers do not depend on it.
