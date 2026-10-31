# Order pilot B2b: pilots follow orders, and stop winning

Run 2026-10-31, M3 stage B, `SIM_VERSION` 5, plan: `plan.md` (gates and pick rule fixed in §5 before any candidate was
evaluated; two O bounds amended from the teacher at 04:55, also before). **Nothing
promoted.** Fleet pilot v1 stays the champion.

<!-- summary: Pulling the pilot toward the order-following scripts taught it to follow orders at the scripts' level, but also overwrote its combat flying: it won 0–4 % of carrier battles against fleet pilot v1, against 79 % before. -->

Verdict: **FAIL.** The script pull taught following: from update 100 on, every `pull`
candidate and most `pull_dagger` candidates pass gate O, at the teacher's level. But no
candidate passes M (missions) or D (deathmatch): carrier battle win vs v1 is 0.000–0.039
at every checkpoint, against run 1's 0.787.

## What ran

- Two arms from run 1's w1_400, 300 PPO updates each, run concurrently 04:59–06:47:
  `pull` (script pull on ordered rows, movement heads only, β 0.1 → 0 over updates
  30–300) and `pull_dagger` (the same after one ordered-rows DAgger round). Random hold
  points near the action, presence 0.0009/tick. KL anchor to v1 on unordered rows.
- Gate evals 06:47–08:23 (anchor cache: about 21 s/update, 4.3 k samples/s).

## Gates (copied from `eval/gates.md`)

| candidate | O | M | D | H | mission win vs v1 | guard (random) | hold (random) | dm vs script | dm vs v1 |
|---|---|---|---|---|---|---|---|---|---|
| pull_50 | ✗ | ✗ | ✗ | ✓ | 0.233 | 0.348 | 0.454 | 0.697 | 0.203 |
| pull_100 | ✓ | ✗ | ✗ | ✓ | 0.214 | 0.407 | 0.488 | 0.678 | 0.210 |
| pull_200 | ✓ | ✗ | ✗ | ✓ | 0.243 | 0.409 | 0.521 | 0.743 | 0.236 |
| pull_300 | ✓ | ✗ | ✗ | ✓ | 0.302 | 0.410 | 0.510 | 0.811 | 0.354 |
| pull_dagger_50 | ✗ | ✗ | ✗ | ✓ | 0.171 | 0.364 | 0.454 | 0.521 | 0.080 |
| pull_dagger_150 | ✓ | ✗ | ✗ | ✓ | 0.193 | 0.446 | 0.513 | 0.632 | 0.128 |
| pull_dagger_300 | ✓ | ✗ | ✗ | ✓ | 0.271 | 0.440 | 0.486 | 0.805 | 0.296 |

(Every candidate is in `eval/gates.md`.) For comparison, run 1's w1_400: mission win vs
v1 0.763, guard 0.227, hold 0.116 (0.31 with near-action holds), deathmatch 0.892 / 0.613.
Against w1_400 itself, the best B2b candidate wins 0.008 of carrier battles.

## Why

- **The pull overwrote combat flying, not just transit.** It applied to every ordered,
  non-advisory row: about 0.67–0.70 of all rows (`beta_rows_share` in `log.jsonl`).
  Most of those rows are a ship in a fight, where the script's movement is much worse
  than v1's evasive flying. Side-a fighters in carrier battles dealt about 10 damage
  against v1's 112, hit 0.13 of shots against 0.31, and almost none survived.
- **It happened by update 50, while β was still 0.09.** Decaying β to zero did not undo
  it: missions and deathmatch recover only slowly (dm vs script 0.70 → 0.81 over updates
  50–300) once the pull is gone. The plan's risk table (§7) named this failure but
  expected the schedule to contain it; it needs a row filter, not a schedule.
- DAgger first made it worse (dm vs v1 0.080 at update 50).

## Next

The design review that followed (team lead, user and Fable, 2026-10-31) changes the
orders themselves, not only the recipe. To be written into `docs/M3_PLAN.md`:

- **Orders:** attack (as now), defend (no location reward: damage to enemies that
  threaten the ward, i.e. within their own weapon range of it or that hit it in the last
  150 ticks, minus a shared penalty on the ward's hull fraction lost and its death), go-to
  (replaces hold; completes per ship on arrival; arrival bonus about 0.2), none. Return
  to carrier waits for docking in the sim.
- **Obs:** when defending, fill the 7 ship slots by distance to the ward; new tail block
  per observed ship: distance to my order point, hull type and max weapon range, "hit my
  ward recently".
- **Teacher:** the scripted guard uses the same threat set.
- **Pull:** only on transit rows (ordered rows where the script has no target), never on
  combat rows.
- **Gates:** per order, on the same definitions as the reward; missions vs v1 and w1_400.
