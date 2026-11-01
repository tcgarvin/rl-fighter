"""Attackers' win share in a mirror of one pilot, per candidate convoy roster (plan §4)."""

import json
import sys
import time

from spacefight.env.rosters import Roster
from spacefight.eval import missions as M
from spacefight.eval.controllers import make_controller

CODE = {"F": "fighter", "S": "strafer", "G": "gunship"}


def fleet(freighters: int, code: str) -> list[str]:
    """A fleet from a freighter count and hull letters."""
    return ["freighter"] * freighters + [CODE[c] for c in code]


def main() -> None:
    """argv: checkpoint, n per candidate, then candidates like 5:FSFGF:FFSGFS."""
    checkpoint, n = sys.argv[1], int(sys.argv[2])
    for spec in sys.argv[3:]:
        freighters, escorts, raiders = spec.split(":")
        roster = Roster(
            (fleet(int(freighters), escorts), fleet(0, raiders)),
            "convoy_escort",
            ("scripted", "scripted"),
        )
        M.default_rosters = lambda mission, r=roster, s=spec: [(s, r)]
        a = make_controller(checkpoint, sample=True, seed=0)
        b = make_controller(checkpoint, sample=True, seed=1)
        cfg = M.MissionEvalConfig(missions=("convoy_escort",), n_per_mission=n, seed=540000)
        a.reset(cfg.seed)
        b.reset(cfg.seed + 1)
        t0 = time.time()
        s = M.run_mission(a, b, "convoy_escort", cfg, 14)
        attackers = ((1 - s.win_rate_team0) + s.win_rate_team1) / 2
        print(
            json.dumps(
                {
                    "roster": spec,
                    "n": s.n,
                    "attackers": round(attackers, 3),
                    "median_s": round(s.length_median_s, 1),
                    "ends": {k: round(v, 2) for k, v in s.end_reasons.items()},
                    "secs": round(time.time() - t0),
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
