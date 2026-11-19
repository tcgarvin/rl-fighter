# Station commander: can a learned commander find the hand rules' gains?

Prepared 2026-11-19, 02:00, after [the hand-rule test](../2026-11-19-station-rules/results.md).
The design is `docs/COMMANDER.md`. `SIM_VERSION` 9, `COMMANDER_IO_VERSION` 1; no rule of
the game changes.

## Why

In the station assault, simple hand rules beat the side with no orders (`unseen`: the
script with its orders hidden from its own pilots) by 0.13 to 0.19 of a match, in both
roles. None of it is an order to a strike craft. It is the two decisions that are not
orders:

| Role | Rule | What it does | vs no orders (carrier reading, 1,024 matches) |
|---|---|---|---|
| Defender | `hold_late` | Keep the station's reserve docked until its hull < 60% | **+0.185 ± 0.039** |
| Defender | `hold_reserve` | Launch it when 4 attackers are inside 320 m | +0.140 ± 0.039 |
| Defender | `hold_never` | Never launch it | −0.489 ± 0.034 |
| Attacker | `carrier_push` | Once the hangar is empty, carrier waypoint 170 m short of the station | **+0.130 ± 0.038** |
| Either | strike-craft orders (go-to, defend, attack, the script's) | | level to −0.17 |

A learned commander sees what those rules use: the station's hull fraction (entity
feature 14), every enemy's position, the hangar counts. It decides the launches (three
launch heads) and the carrier's waypoint (26 choices; the centre point is about 157 m
from the station, close to the 170 m standoff). So: **can PPO find these?** Launch timing
has a steep payoff that is not monotone in the delay (never −0.49, at once 0, at the main
wave +0.14, at 60% hull +0.19), so a policy-gradient learner should be able to climb it,
but the payoff arrives a minute or more after the decision.

## Setup

Trainer: `spacefight.commander.train`, every match a station assault (the default and
only roster, "strike of 8"), the learner's team drawn at random each match (team 0
defends, team 1 attacks), so it plays both roles with one net.

| | Value | Why |
|---|---|---|
| Missions | station assault only (`mission_weights [0,0,0,1]`) | The question is this mission |
| Reading | half carrier, half convoy (`station_convoy_share 0.5`, new) | The hand rules hold on both (+0.15 / +0.20 on convoy); the live page can show either |
| Enemy | `unseen` 3 in 4, `scripted` 1 in 4 (`opponent_shares [0.25,0,0,0,0.75]`) | `unseen` is what the hand rules faced and what the bar is measured against. Some script keeps the learner from tuning only to the script's launch logistics without its orders; no self-play or snapshots, since the bar is against a fixed side |
| Pilots | the live ten, drawn ship by ship (`lab/live_pilots.json`) | As the hand-rule eval and the live page |
| Sizes | 128 matches at once, 8,192 decisions an update, minibatch 1,024 | Commander 3's |
| PPO | `ent_coef` 0.002, `shaping` 0.5, `order_price` 0, seed 0, gamma 0.99, lambda 0.95 | Commander 3's best arms. 0.01 kept commanders ordering half the time and cost them (commander 3) |
| Threads | 6 sim + 6 torch an arm (they take turns: about 6 cores an arm) | 16 threads on the laptop; 4 left free |
| Deadline | 2026-11-19 13:30 | The orchestrating session's |

Two arms, differing only in where the actor starts:

- **`fresh`**: a new net, `keep_prior` 0.8 (order and squad heads lean to "keep"). It
  starts ordering about 47% of ship time and launching at even odds per head, so it has to
  learn both "stop ordering" (as commander 3 did in a night) and the launch and waypoint
  timing. This is the clean test of whether the mission teaches the decisions.
- **`from_c3`**: starts from commander 3's `live` line (update 197,
  `lab/runs/2026-11-15-commander-3/live/checkpoints/commander_197.pt`). The brief
  suggested the best `c1` commander on the live page; I chose `c3 live` instead. It was
  trained over the same live ten against the same `unseen` side and ended level with it
  (0.49) by keeping ships under an order only 5 to 6% of the time. The `c1` lines keep
  ships under an order about half the time and, like every commander measured before
  commander 3, make their side worse than no orders (commander 3's plan).
  Starting quiet isolates the station's own decisions: what it has to learn is only the
  launches and the waypoint. In a 16-match check before training it already launches
  the station's reserve at once (2 s, as the script) and, attacking, brings its carrier
  in on its own (428 m at 10 s, 250 m at 45 s, 185 m at 90 s), closer than the script's
  patrol early. Its critic starts fresh.

## Trainer changes (defaults unchanged; tests in `tests/test_commander_train.py`)

- `TrainConfig.station_convoy_share` (default 0): the chance a station assault reads as a
  convoy escort. Drawn only when it can be convoy, so at 0 the assignment stream is the
  one before the change.
- `TrainConfig.init` (default ""): a commander checkpoint the actor starts from
  (`initial_actor`); the critic starts fresh.
- `TrainConfig.pilot_root` (default ""): the checkout holding the pilots' weights, so a
  worktree can train (it has no weights).
- The log scores each enemy per station role (`win_unseen_defender`,
  `win_unseen_attacker`, `win_scripted_*`).
- `station_rules.py` (the hand-rule eval) takes `--rule learned --commander <pt>`: the
  rule side in the sim's `learned` mode, decisions sampled as in training. Every rule's
  output now also times the rule side's launches (first launch, the station's hull then,
  hangar empty) and, for a learned side, the strike craft it re-orders a minute. Nothing
  else in its output changed.

## Measures

`eval.sh <commander.pt>`: the commander in each role against `unseen` at the hand-rule
eval's settings (the same seed 1,119,000, roster, pilot draws, one sim and one torch
thread a cell): carrier reading 1,024 matches a role, convoy 512. `summary.py` prints:

1. **The score in each role and its paired delta against no orders** (the hand-rule
   test's `none`, the same matches), next to the best hand rule's (`hold_late` +0.185,
   `carrier_push` +0.130) and the commander's paired difference from that rule.
2. **Telemetry**: when the commander side first launches (median, quartiles), the
   station's hull at that moment (`hold_late` waits for 0.60; the script launches at 2 s
   at 1.00), when the hangar is empty; the carrier's distance to the station at 10, 20,
   30, 45, 60 and 90 s (`carrier_push`: 396, 237 at 45 s, 163 at 90 s; the patrol 420 to
   460 m); strike craft re-ordered a minute and the share of ship time under an order.
3. Through the night, from `log.jsonl`: `win_unseen_defender`, `win_unseen_attacker`,
   `launch_per_decision`, `ordered_share`, the launch and waypoint heads' entropy.

**Bars** (carrier reading; set before the run):

- **PASS**: in both roles the commander beats no orders (the 95% interval of its delta
  above 0) and is not below the best hand rule by more than noise (its paired
  difference from `hold_late` defending and from `carrier_push` attacking, plus its 95%
  half-width, at least 0). Roughly: +0.19 defending and +0.13 attacking.
- **PARTIAL**: it beats no orders in both roles, but not by as much as the rules.
- **FAIL**: otherwise (say which role it fails in).

The convoy reading is reported beside it, not barred.

Which checkpoint: each arm's last, and if the log shows a peak in
`win_unseen_defender + win_unseen_attacker` well before the end, that one too (a log
average over 85 matches an update is noisy; read a 10-update mean).

## Running it

    DEADLINE="2026-11-19 13:30" nohup setsid lab/runs/2026-11-19-station-commander/run.sh \
        > lab/runs/2026-11-19-station-commander/run.out 2>&1 &
    SMOKE=1 lab/runs/2026-11-19-station-commander/run.sh   # 3 tiny updates an arm, smoke/

    lab/runs/2026-11-19-station-commander/eval.sh \
        lab/runs/2026-11-19-station-commander/<arm>/checkpoints/commander_<N>.pt

- Run from this worktree (`PYTHONPATH` is set to it; `run.sh` checks `spacefight` comes
  from it) with the main checkout's venv and pilot weights (`PY`, `PILOT_ROOT`).
- `kill -TERM <run.sh pid>` (or the process group) stops both trainers after their
  current update with a checkpoint; a trainer that dies early is restarted with
  `--resume` up to 3 times.
- Launched 2026-11-19 02:06. First update: 108 s an arm with both running (99 s
  rollout, 8 s learn; about 85 matches an update once the envs are out of step). So about
  380 updates an arm by 13:30 (commander 3 ran 197 to 233), checkpoints every 10.
- `eval.sh` runs four cells at once under nice 19, about 30 minutes on idle cores; beside
  the trainers it is much slower (overlapping training has cost about 6 times). Run it after
  13:30, or on a mid-run checkpoint with that cost in mind.

## Not tonight

- A sweep of the hand rules' thresholds (`hold_late` at other hull fractions, other
  standoffs). The learned commander may find a different optimum; the telemetry says
  where it settled.
- Both winning rules on opposite sides of one match, and self-play: the bar is against a
  fixed no-orders side.
- Bombers apart: a bomber reads as the gunship class, so no commander can single them out.
