# RL Design Notes

## Retroactive Projectile Credit Assignment

### Problem

When a projectile hits an enemy, the `+0.01/HP` reward lands at the impact tick. But the fire *decision* happened 15–60+ ticks earlier. GAE (γ=0.99, λ=0.95) dilutes the reward signal to ~22% over 30 steps. This weakens learning for projectile weapons (bullets, missiles). Lasers are hitscan and unaffected.

### Solution

**Additive credit at fire-time + tail buffer.**

1. **Keep existing impact reward at t_hit** — teammates see it, critic learns it.
2. **Add a shooter-local bonus at t_fire** when the projectile eventually hits.
3. **Use a tail buffer**: collect `T_STEPS` steps but defer GAE finalization of the last `T_TAIL` steps until the next rollout resolves in-flight projectiles.

### Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| `T_TAIL` | 48 ticks (1.6s) | Covers all bullet/double_gauss TTL. Missiles (180 tick TTL) get partial coverage. |
| `CREDIT_COEFF` | 0.01 | Same as `REWARD_DAMAGE_DEALT`. Effectively doubles signal for the shooter. |

### Architecture

- **`CreditAssigner`** (`spacefight/rl/credit.py`): Tracks episode generations per environment to prevent cross-episode credit leakage. Uses vectorized `np.add.at` for credit injection.
- **`RolloutBuffer`** tail support: Internal arrays sized `(n_steps + t_tail)`. Prepend/extract tail data between rollouts.
- **`proj_fire_step`** array on `SimState`: Records which rollout buffer step each projectile was fired at. Threaded through `fire_bullets` and `fire_missiles`.

### Data Flow

```
fire_bullets/fire_missiles → proj_fire_step[n, slot] = rollout_step
check_hits → proj_hit[n, p] mask
VecEnv.step → infos["proj_hit", "proj_owner", "proj_damage", "proj_fire_step"]
CreditAssigner.record_hits → credit[fire_step, shooter_flat_idx] += coeff * damage
CreditAssigner.inject_into_rewards → buf.rewards += credit
buf.compute_gae_with_tail → GAE over full range, output excludes tail
```

### Edge Cases

| Case | Handling |
|------|----------|
| First rollout (no tail) | `tail_size=0`, credits only for hits within rollout |
| Projectile pool recycling | `proj_fire_step` overwritten with new projectile's step |
| Episode auto-reset mid-rollout | `episode_gen` prevents cross-episode credit |
| Projectile misses (TTL expires) | No hit → no credit recorded |
| Laser hits | Hitscan, instant — no `proj_fire_step` tracking needed |
| Same-tick fire+hit | `proj_fire_step = current buf_step`, credit at same step |
| Missile exceeds `T_TAIL` | Impact reward at `t_hit` still exists, fire-time credit lost |
