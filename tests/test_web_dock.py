"""The live page's v11 dock numbers and names agree with the sim (``rlf_sim``).

The page reads strides and phases from the wasm, but two of the scripted commander's
numbers, the hull share it relaunches a returned craft at and the hangar's repair rate,
are not in the wasm's interface: the inspector keeps its own copies for its "out at 90%"
countdown (``web/src/live/inspector.ts``). The event names at 15 to 19 and the dock
phases are the page's own spellings of the sim's (``web/src/live/sim.ts``).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

rlf_sim = pytest.importorskip("rlf_sim")

REPO = Path(__file__).resolve().parents[1]
INSPECTOR = REPO / "web/src/live/inspector.ts"
SIM_TS = REPO / "web/src/live/sim.ts"


def _ts_number(source: str, name: str) -> float:
    match = re.search(rf"export const {name} = ([0-9.]+);", source)
    if match is None:
        raise AssertionError(f"no `export const {name} = <number>;` in the source")
    return float(match.group(1))


def _camel(snake: str) -> str:
    head, *rest = snake.split("_")
    return head + "".join(word.capitalize() for word in rest)


def test_inspector_relaunch_share_and_repair_rate_match_the_sim() -> None:
    source = INSPECTOR.read_text()
    dock = rlf_sim.DOCK
    assert _ts_number(source, "SCRIPT_RELAUNCH_HULL") == pytest.approx(
        dock["relaunch_hull_frac"], abs=1e-6
    )
    assert _ts_number(source, "REPAIR_PER_SECOND") == pytest.approx(
        dock["repair_frac_per_s"], abs=1e-6
    )


def test_event_kinds_list_the_sims_kinds_in_order() -> None:
    source = SIM_TS.read_text()
    block = re.search(r"export const EVENT_KINDS = \[(.*?)\] as const;", source, re.S)
    assert block is not None
    page = re.findall(r'"([A-Za-z]+)"', re.sub(r"//[^\n]*", "", block.group(1)))
    sim = sorted(rlf_sim.EVENT_KINDS, key=rlf_sim.EVENT_KINDS.get)
    assert page == [_camel(name) for name in sim]


def test_dock_phase_codes_match_the_sim() -> None:
    source = SIM_TS.read_text()
    names = {
        "none": "DOCK_NONE",
        "inbound": "DOCK_INBOUND",
        "repairing": "DOCK_REPAIRING",
        "ready": "DOCK_READY",
    }
    for code, phase in enumerate(rlf_sim.DOCK_PHASES):
        assert _ts_number(source, names[phase]) == code
