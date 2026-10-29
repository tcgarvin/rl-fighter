# Collision damage: stop the head-on rams (2026-10-29)

Status: running. Asked for by the user on 2026-10-29: crashes should hurt, fighters
should be fragile, and the nose more fragile than the flanks, so pilots learn to turn
away. Done in the physics (SIM_VERSION 3), not as a reward penalty.

## 1. Why (survey before the change)

`tools/contact_survey.py`, 128 duels each, SIM_VERSION 2 (`survey/*.json`):

| pairing | contacts / match | closing p50 (m/s) | > 30 m/s share | nose-to-nose | median ticks |
|---|---|---|---|---|---|
| champion (ppo_bc_1200) vs script | 2.4 | 96 | 0.88 | 0.98 | 332 |
| champion vs champion | 4.4 | 28 | 0.47 | 0.99 | 252 |
| script vs script | 10.8 | 92 | 0.78 | 0.98 | 1259 |

Every match has contacts and nearly all are nose to nose. Contact costs nothing
(a 0.2-restitution bump), so ramming through the merge is free for both the script
and the learned pilot.

## 2. Change

- **Sim v3** (SIM_SPEC §5.5): damage on a closing contact,
  `0.002 hp/J × ½ μ (c − 10 m/s)²` per ship, times a per-hull `impact` arc multiplier
  at the contact bearing (fighter nose 1.5×, flanks and engine 1×). A ~96 m/s head-on
  costs each fighter ~55 of 80 hp; ~120 m/s kills both (a draw). Shields absorb first;
  no HitRecord; the victim's reward counts it as damage taken and nobody is credited.
  A `Collision` event drives a spark in the web renderer.
- **Script** (SIM_SPEC §11): the scripted fighter predicts closest approach and
  offsets its pass so it misses, then extends as before.

## 3. Training

Fine-tune the spike champion `ppo_bc_1200` under v3 with the spike's PPO
(`spacefight.train_spike ppo`), two arms concurrently, 800 updates each:

- **A, pure RL:** beta 0 (no script pull).
- **B, script pull:** beta 0.1 → 0 over updates 30–400, toward the new
  crash-avoiding script.

Opponent bands `[[0,0.5,0.3,0.2],[200,0.3,0.4,0.3]]`, critic warm-up 30 updates
(the critic was fitted to v2 returns), everything else the spike's PPO-BC preset.

## 4. Gates (fixed before any v3 eval)

Evaluated with the duel harness (n = 512, seed 100000) and the contact survey
(n = 128) under v3, sampled actions:

1. **Crashes:** contacts closing faster than 30 m/s, vs the v3 script, at most
   0.3 per match (v2 champion: ~2.1).
2. **Strength:** win vs the v3 script ≥ 0.90, and win vs the v2 champion
   (both under v3) > 0.5.
3. **Health (spike §6.3):** engine duty 0.2–0.95, outside-arena share < 0.05,
   draws < 0.10.

Reported but not gated: passes per match, median match length, hit rate, the share
of hull damage from crashes. Pick the arm and checkpoint that pass all gates with the
highest smoothed rollout win; ship it to `/duel/` only if one passes.
