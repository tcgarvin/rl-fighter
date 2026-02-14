"""Tests for hull damage application."""

import numpy as np
import pytest

from spacefight.sim.damage import apply_damage


class TestApplyDamage:
    def test_damage_reduces_hull(self):
        hull = np.array([[100.0, 80.0]], dtype=np.float32)
        damage = np.array([[15.0, 0.0]], dtype=np.float32)
        alive = np.ones((1, 2), dtype=np.bool_)

        hull, alive = apply_damage(hull, damage, alive)

        assert hull[0, 0] == pytest.approx(85.0)
        assert hull[0, 1] == pytest.approx(80.0)
        assert alive[0, 0]
        assert alive[0, 1]

    def test_lethal_damage_kills(self):
        hull = np.array([[10.0, 80.0]], dtype=np.float32)
        damage = np.array([[15.0, 0.0]], dtype=np.float32)
        alive = np.ones((1, 2), dtype=np.bool_)

        hull, alive = apply_damage(hull, damage, alive)

        assert hull[0, 0] == 0.0
        assert not alive[0, 0]
        assert alive[0, 1]

    def test_dead_ship_takes_no_damage(self):
        hull = np.array([[0.0, 80.0]], dtype=np.float32)
        damage = np.array([[50.0, 0.0]], dtype=np.float32)
        alive = np.array([[False, True]], dtype=np.bool_)

        hull, alive = apply_damage(hull, damage, alive)

        assert hull[0, 0] == 0.0
        assert not alive[0, 0]

    def test_exact_lethal_damage(self):
        hull = np.array([[15.0, 80.0]], dtype=np.float32)
        damage = np.array([[15.0, 0.0]], dtype=np.float32)
        alive = np.ones((1, 2), dtype=np.bool_)

        hull, alive = apply_damage(hull, damage, alive)

        assert hull[0, 0] == 0.0
        assert not alive[0, 0]

    def test_batched(self):
        hull = np.array([[100.0, 80.0], [50.0, 200.0]], dtype=np.float32)
        damage = np.array([[10.0, 20.0], [60.0, 5.0]], dtype=np.float32)
        alive = np.ones((2, 2), dtype=np.bool_)

        hull, alive = apply_damage(hull, damage, alive)

        assert hull[0, 0] == pytest.approx(90.0)
        assert hull[0, 1] == pytest.approx(60.0)
        assert hull[1, 0] == 0.0
        assert not alive[1, 0]
        assert hull[1, 1] == pytest.approx(195.0)
