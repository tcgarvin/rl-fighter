# Crashes now hurt: the learned pilot rams 82 % less and still wins every duel

Run 2026-10-29, plan: `plan.md` (gates fixed before any v3 eval). Shipped:
**arm A (pure RL), update 600**.

## What changed

- **Sim v3.** A closing contact now does damage that grows with the square of the
  closing speed above 10 m/s. Fighters take 1.5× on the nose, so a ~96 m/s head-on
  costs each one about 55 of its 80 hp. Nobody is credited for the other ship's crash
  damage. A crash shows as a white flash with amber sparks.
- **Script.** The hand-written fighter predicts the closest approach and sidesteps
  so its pass misses. Script vs script: fast contacts per match fell from 8.4 to 0.02
  and passes rose from 2.9 to 4.9. Its hit rate fell from 0.60 to 0.46.
- **Pilot.** The spike champion was fine-tuned for 800 PPO updates under v3, in two
  arms: A with no script pull, B with a decaying pull toward the new script.

## Gates (512 duels; contact survey of 128 duels vs the script)

| pilot | win vs script | win vs old champion | fast contacts / match | matches with a crash death | engine duty | passes | median ticks |
|---|---|---|---|---|---|---|---|
| old champion, on v3 | 1.000 | 0.50 | 1.16 | 19.5 % | 0.90 | 1.0 | 387 |
| **A, update 600 (shipped)** | **1.000** | **0.82** | **0.21** | **7.8 %** | 0.78 | 1.0 | 307 |
| A, update 800 | 1.000 | 0.74 | 0.46 | 16.4 % | 0.75 | 1.1 | 326 |
| B, update 600 | 1.000 | 0.46 | 0.23 | 0.8 % | 0.23 | 1.0 | 370 |
| B, update 800 | 1.000 | 0.56 | 0.01 | 0 % | 0.15 | 1.0 | 276 |

- Gates: G1 fast contacts ≤ 0.3, G2 win vs script ≥ 0.9 and vs old champion > 0.5,
  G3 engine duty 0.2–0.95. **A-600 is the only candidate to pass all three.**
- **B-800 crashes least but fails health.** It learned to barely use the engine
  (duty 0.15) and wait for the script to come to it. That is safe but dull, so the
  duty gate rejects it.
- **A drifted back toward contact between updates 600 and 800.** That is why the
  earlier checkpoint was picked.
- Hit rate rose from 0.57 to 0.76 for A-600, and only 4 % of the hull damage it deals
  or takes comes from crashes (21 % for the old champion).

## What did not change

- **Each duel is still one approach and a close fight.** That is about one pass, with
  the median match around 10 s.
- **The pilot no longer flies into the other ship, but it still doesn't extend and
  come round** the way the new script does.
- **Learned vs learned rarely touches now:** only 37 % of the contacts that remain
  are head-on (98 % before).

## Next

- Gate on passes or duel length (the backlog's watchability gate) so selection
  rewards longer, readable fights rather than only fewer crashes.
- Rerun DAgger from the new, passing script before PPO. The current pilot was cloned
  from the old ramming script, and fine-tuning kept its close-brawl style.
- The script's heading controller wobbles about ±0.3 rad, so most of its shots are
  sweeps. Fixing that would make it a better teacher.
