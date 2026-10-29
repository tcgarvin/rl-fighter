"""Obs feature indices, event columns and small counters shared by the duel tools.

Used by the eval harness (``spacefight/eval/duel.py``) and the balance sweep
(``tools/duel_sweep.py``) so both read the same SIM_SPEC §7.2 features and §9 event
columns and count passes the same way.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from spacefight.env.rust_env import OBS_LAYOUT, OBS_SLOTS

# Obs scales (SIM_SPEC §7.2).
VELOCITY_SCALE = 100.0  # VS, m/s

# Flat obs indices (SIM_SPEC §7.2). Self block: 0 present, 2 speed/VS,
# 19 (R - |pos|)/R (negative outside the arena).
SELF_OFFSET = OBS_LAYOUT["self"][0]
SELF_PRESENT = SELF_OFFSET + 0
SELF_SPEED = SELF_OFFSET + 2
SELF_EDGE_MARGIN = SELF_OFFSET + 19

# Ships block: 7 records sorted by distance; record feature 0 present,
# 1 is_enemy, 11 dist/R. Slot 0 is the nearest other ship.
SHIPS_OFFSET, SHIPS_WIDTH = OBS_LAYOUT["ships"]
SHIP_RECORD = SHIPS_WIDTH // OBS_SLOTS["ships"]
SHIP_PRESENT, SHIP_IS_ENEMY, SHIP_DIST = 0, 1, 11
NEAREST_PRESENT = SHIPS_OFFSET + SHIP_PRESENT
NEAREST_DIST = SHIPS_OFFSET + SHIP_DIST

# Thrusters block: 8 records; feature 0 present, 5 (max_force/mass)/A,
# 6 thrust_level in [0, 1].
THRUSTER_PRESENT, THRUSTER_ACCEL, THRUSTER_LEVEL = 0, 5, 6

# Flat event columns from ``events()``: [match, kind, a, b, x, y, s5, s6, extra]
# (SIM_SPEC §9 with the leading match index).
EV_MATCH, EV_KIND, EV_A, EV_B, EV_SLOT5, EV_EXTRA = 0, 1, 2, 3, 6, 8
KIND_FIRE, KIND_BEAM, KIND_HIT, KIND_SHIELD_HIT, KIND_DEATH = 0, 1, 2, 3, 5
KIND_BURST, KIND_ARRIVAL = 4, 6
# SIM_VERSION 3: a damaging ship-ship collision, ``[k, a, b, x, y, nx, ny, closing]``.
KIND_COLLISION = 7

# Columns of the per-step ``hits`` rows (SIM_SPEC §8).
HIT_SHOOTER, HIT_TARGET, HIT_FIRE_TICK, HIT_DAMAGE, HIT_SHIELD, HIT_DECISION = range(6)


def range_entries(
    measured: NDArray[np.bool_], now_in: NDArray[np.bool_], in_range: NDArray[np.bool_]
) -> tuple[NDArray[np.bool_], NDArray[np.bool_]]:
    """One tick of pass counting: entries into gun range (plan §2.3).

    A pass is a transition from out of range to in range, seen on ticks where the
    distance is measured (both ships present, match still running); unmeasured ticks
    keep the previous state, so a ship's arrival inside range counts as one entry.

    Args:
        measured: Where the distance is valid this tick.
        now_in: Where the distance is under the gun range this tick.
        in_range: The in-range state carried from the last measured tick.

    Returns:
        ``(entered, new_in_range)``, both shaped like the inputs.
    """
    entered = measured & now_in & ~in_range
    return entered, np.where(measured, now_in, in_range)
