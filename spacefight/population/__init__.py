"""The pilot population (``docs/PILOT_TRAINING.md`` sections 4 to 6).

- ``records``: one committed JSON per member under ``lab/population/<season>/members``
  and the family tree they form. Weights stay out of git.
- ``standings``: pairwise win matrices and the transitivity summary (pure).
- ``rating``: the combat rating with uncertainty (pure).
- ``culling``: shadow culling, which names who would go and changes nothing (pure).
- ``war``: wins above replacement, the ridge logistic fit and its bootstrap (pure).
- ``report``: the phone-readable Markdown report.
- ``round_robin``: all pairs of members in no-commander matches, resumable (needs the
  sim; import it directly, the modules above do not load ``rlf_sim``).
- ``war_matches``: the WAR matches, live-like with the script in the pilot draw,
  chunked and resumable (needs the sim, like ``round_robin``).

CLI: ``python -m spacefight.population --help``.
"""
