# Mission survey: are the carrier battle and the convoy escort real contests?

| | |
|---|---|
| Run | `2026-10-30-mission-survey` (M3 stage A, WP-S2, `docs/M3_PLAN.md` §2) |
| Branch | `m3-sim2` |
| Question | With the real scripted commander, the carrier pilot retuned and the strike-craft scripts following orders, do the two new missions end for the right reasons, at a watchable length, and close to even, in the configuration visitors see? |
| Scenario | `SIM_VERSION` 4, arena 450 m (`arena_radius_for_mission`), `reaction_ticks` 2, each mission's default rosters (`rlf_sim.mission_rosters`) and clock, scripted commanders on both sides |
| Tool | `tools/mission_survey.py` (pytest: `tests/test_mission_survey.py`), JSON schema `rlf.survey.mission/1` |

## 1. Two modes

- **live** is the balance target: it is what the page shows. Fleet pilot v1
  (`2026-10-30-fleet-pilot-v1`, sampling its heads like the page) flies every strike
  craft on both sides; the Rust scripts fly the carriers and freighters; the scripted
  commander launches, sets the carrier's waypoint and gives squad orders. Pilot v1
  does not read orders (stage B adds them), so in this mode the commander acts
  through launches and the carrier's movement only.
- **script**: the scripted pilots fly everything and follow their squad's orders.
  This is the teacher stage B will learn order-following from, so it should at
  least be a meaningful match; it is not tuned to the targets.

## 2. What is measured, per mission and roster

Win rate per side (draws count ½), end-reason distribution, time-limit rate, match
length (median, p90), launches per match and their spread over the match (median
and p90 launch time, launches per 30 s bin), how far the carriers moved; for the
convoy, transports escaped and destroyed, route progress at the end and the share
of defender wins in which a transport escaped. The end state (strike craft left per
side, hangar left, carrier hull) is sampled every second for diagnosis.

## 3. Targets (live mode), fixed before the tuning

- **Carrier battle**: mostly ends in a carrier kill (time-limit rate ≲ 20 %), median
  60–150 s, symmetric rosters about 50/50, launches visible across the match (not
  all in the first seconds).
- **Convoy escort**: attacker win rate 35–65 % on every default roster, median
  45–120 s, the route visibly travelled, at least some transports escape in most
  defender wins.
- **Deathmatch**: unchanged (the `v3_compat_*` traces still replay bit for bit).

## 4. Levers

Mission constants and clocks, the convoy route, hangar sizes and `jump_in`, the
default rosters, hull numbers (never mounts: they are the art contract), and the
commander's own constants. The freighter script itself is final (no evasion).

## 5. Procedure

1. Baseline: the WP-S1 stub commander and hull numbers, both modes, n = 32 per
   roster (`survey/before_*.json`).
2. Land the commander, the order-following pilots and the carrier pilot; retune
   with the live mode at n = 32–96, recording each step in `results.md`.
3. Final: both modes at n = 128 per roster (`survey/script.json`, `survey/live.json`).
