"""Hull-only damage model for milestone 1.

Shields and armor are deferred to later milestones.
"""

import numpy as np
from numpy.typing import NDArray


def apply_damage(
    hull: NDArray[np.float32],
    damage: NDArray[np.float32],
    alive: NDArray[np.bool_],
) -> tuple[NDArray[np.float32], NDArray[np.bool_]]:
    """Apply damage to hull HP and update alive status.

    Args:
        hull: Current hull HP, shape [N, S].
        damage: Damage to apply this tick, shape [N, S].
        alive: Current alive mask, shape [N, S].

    Returns:
        Updated (hull, alive) arrays. Hull is clamped to >= 0.
    """
    hull = hull - damage * alive
    hull = np.maximum(hull, 0.0)
    alive = alive & (hull > 0.0)
    return hull, alive
