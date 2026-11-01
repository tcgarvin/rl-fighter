"""The pilot population (``docs/PILOT_TRAINING.md`` sections 4 to 6).

- ``records``: one committed JSON per member under ``lab/population/<season>/members``
  and the family tree they form. Weights stay out of git.
- ``standings``: pairwise win matrices and the transitivity summary (pure).
- ``rating``: the combat rating with uncertainty (pure).
- ``culling``: shadow culling, which names who would go and changes nothing (pure).
- ``report``: the phone-readable Markdown report.
- ``round_robin``: all pairs of members in no-commander matches, resumable (needs the
  sim; import it directly, the modules above do not load ``rlf_sim``).

CLI: ``python -m spacefight.population --help``.
"""
