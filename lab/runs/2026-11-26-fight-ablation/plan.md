# Fight ablation: which change cost the fighting (plan)

Prepared 2026-11-26 on the laptop; trains on Beast from about 14:00 until 03:00 the next
morning, then the final evals and WAR, all done before 07:00 (Beast's work day).

## Question

The [horizon and bombers](../2026-11-24-horizon-bombers/results.md) arms learned the
bomber and got much better at the station assault, but fought worse everywhere else:
against the script, the fleet suite fell from 0.88 to 0.74 and carrier battles from 0.89
to 0.66–0.73. In 3 v 3 against another pilot, followers_school_1052, wins fell from 0.59
to 0.11–0.23. WAR rated them below their parent. Both arms
had three changes at once:

1. **Bombers:** a fifth of the strike slots in matches and drills.
2. **The station assault** in the mission mix (the pilots_v1 defaults since 11-21; the
   parent trained before them).
3. **Live teammates:** the live ten flying about a quarter of the learner's side.

The horizon is ruled out: 0.999 and 0.995 fell alike. **Which of the three cost the
fighting?** The first suspect is the teammates. A pilot that always has live pilots
beside it may learn to let them start the fight, and in the fleet suite and the 3 v 3 it
flies every ship of its side. That fits the drop growing with fleet size.

## Arms

Two arms from the same parent, `followers_dock_v8_2676`, at its own `gamma` 0.995. Each
drops one of the optional changes. The station assault stays in both, since it is in
the defaults.

| Arm | Bombers | Teammates | Seed | Where |
|---|---|---|---|---|
| `solo` | 0.2 | none | 2611 | Beast, cuda:0 |
| `nobomb` | none | 0.3 | 2612 | Beast, cuda:1 |
| (`h995`, horizon-bombers) | 0.2 | 0.3 | 2412 | the reference: all three |

Everything else is `h995`'s config: the parent's own config, critic warm-up 50,
checkpoint every 25.

## Measures

`eval.sh` as in horizon-bombers. The quick evals now also run the fleet suite against
the script (8 a roster) and the unordered 3 v 3 against a free `followers_school_1052`
(6 blocks), every 500 updates, since the fighting is what is in question. The fall showed
by update 1,000 to 3,000 in `h995` (fleet 0.83 at 1,000, 0.72 at 3,000). After training:
the full evals, `report.md`, and WAR (`war.sh`) over the live ten plus both arms.

## Reading it

| `solo` | `nobomb` | Then the cause is most likely |
|---|---|---|
| holds | falls | the teammates |
| falls | holds | the bombers |
| falls | falls | the station assault in the mix, or more training on this config anyway |
| holds | holds | the bombers and teammates together |

"Holds" means the fleet suite and the 3 v 3 stay within noise of the parent (0.88, 0.59).
"Falls" means they drop as far as `h995` did.

## Timeline

| When | What |
|---|---|
| Thu ~14:00 | both arms start on Beast; quick evals every 500 updates |
| Fri 03:00 | training stops; final evals (about 25 min) |
| Fri ~03:30 | WAR, chained (about 1.5 h) |
| Fri morning | results, live list from WAR, deploy |
