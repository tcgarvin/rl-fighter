"""Evaluation harnesses (learnability spike plan §6).

- ``spacefight.eval.duel``: ``evaluate(a, b) -> DuelResult``, the fixed 1v1 duel
  eval and its CLI (``python -m spacefight.eval.duel``).
- ``spacefight.eval.controllers``: the ``Controller`` protocol, ``Scripted``,
  ``RandomController`` and ``Policy``.
- ``spacefight.eval.features``: obs/event indices shared with ``tools/duel_sweep.py``.

Submodules are not imported here so ``python -m spacefight.eval.duel`` runs cleanly.
"""
