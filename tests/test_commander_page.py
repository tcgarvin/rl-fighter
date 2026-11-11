"""The ``/commander/`` page states only facts that ``tools/commander_facts.py`` computes
from ``spacefight.commander`` and ``docs/COMMANDER.md``."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from spacefight.commander import io
from spacefight.commander.policy import CommanderActor, CommanderCritic, n_params
from tools.commander_facts import (
    DEFAULT_PAGE,
    DESIGN_DOC,
    CommanderFactsError,
    compute_facts,
    design_facts,
    live_pilot_count,
    map_points,
)
from tools.pilot_facts import check_page, page_facts

REPO = Path(__file__).resolve().parent.parent
VITE_CONFIG = REPO / "web/vite.config.ts"
NAV = REPO / "web/src/shell/nav.ts"


@pytest.fixture(scope="module")
def facts() -> dict[str, str]:
    return compute_facts()


@pytest.fixture(scope="module")
def page() -> str:
    return DEFAULT_PAGE.read_text()


def test_every_number_on_the_page_matches_the_code(
    page: str, facts: dict[str, str]
) -> None:
    assert check_page(page, facts) == []
    keys = {key for key, _ in page_facts(page)}
    # The headline numbers are all checked, not just present somewhere.
    for key in (
        "io.entity_dim",
        "io.global_dim",
        "io.action_dim",
        "io.n_points",
        "io.hold_decisions",
        "cadence.ticks",
        "cadence.per_s",
        "actor.params",
        "critic.params",
    ):
        assert key in keys


def test_the_layer_table_adds_up_to_the_actor(page: str, facts: dict[str, str]) -> None:
    rows = re.findall(r'<td class="num" data-fact="(actor\.[\w.]+)">[\d,]+</td>', page)
    table = [key for key in rows if key != "actor.params"]
    assert len(table) == len(set(table)) == 14
    total = sum(int(facts[key].replace(",", "")) for key in table)
    assert total == n_params(CommanderActor()) == 84_676
    assert facts["actor.params"] == f"{total:,}"


def test_the_stated_counts_are_the_networks(facts: dict[str, str]) -> None:
    actor = CommanderActor()
    assert facts["actor.trunk"] == f"{n_params(actor.trunk):,}"
    critic = CommanderCritic(int(facts["critic.n_pilots"]))
    assert facts["critic.params"] == f"{n_params(critic):,}"
    assert int(facts["critic.entity_in"]) == io.ENTITY_DIM + live_pilot_count() + 1


def test_the_layout_constants_are_the_codes(facts: dict[str, str]) -> None:
    assert (
        facts["io.entity_dim"],
        facts["io.global_dim"],
        facts["io.action_dim"],
        facts["io.n_points"],
        facts["io.hold_decisions"],
    ) == tuple(
        str(v)
        for v in (
            io.ENTITY_DIM,
            io.GLOBAL_DIM,
            io.ACTION_DIM,
            io.N_POINTS,
            io.HOLD_DECISIONS,
        )
    )
    # One decision a second at 30 ticks a second.
    assert (facts["cadence.ticks"], facts["cadence.per_s"]) == ("30", "1")


@pytest.mark.parametrize(
    ("figure", "total"),
    [("ent-fig", io.ENTITY_DIM), ("glob-fig", io.GLOBAL_DIM)],
)
def test_input_figures_have_every_number(page: str, figure: str, total: int) -> None:
    svg = page.split(f'aria-labelledby="{figure}-title')[1].split("</svg>")[0]
    widths = [int(w) for w in re.findall(r'data-width="(\d+)"', svg)]
    assert sum(widths) == total


def test_the_squad_blocks_are_where_the_network_reads_them(page: str) -> None:
    svg = page.split('aria-labelledby="glob-fig-title')[1].split("</svg>")[0]
    blocks = re.findall(r'data-block="(\w+)" data-width="(\d+)"', svg)
    offset = 0
    for name, width in blocks:
        if name == "squads":
            assert slice(offset, offset + int(width)) == io.SQUAD_GLOBALS
        offset += int(width)


def test_decision_figure_has_one_cell_per_action_column(page: str) -> None:
    heads = re.findall(r'data-head="(\w+)"', page)
    assert len(heads) == io.ACTION_DIM
    columns = {
        "launch": io.LAUNCH,
        "waypoint": slice(io.WAYPOINT, io.WAYPOINT + 1),
        "squad": io.SQUAD_OF_SLOT,
        "order": io.ORDER,
        "target": io.ATTACK_TARGET,
        "ward": io.DEFEND_WARD,
        "point": io.GOTO_POINT,
    }
    for name, cols in columns.items():
        assert heads[cols] == [name] * (cols.stop - cols.start)


def test_map_point_diagram_draws_the_designs_points(page: str) -> None:
    drawn = re.findall(
        r'data-point="(\d+)" data-x="(-?[\d.]+)" data-y="(-?[\d.]+)"', page
    )
    doc = DESIGN_DOC.read_text()
    facts = design_facts(doc)
    radii = tuple(float(r) for r in facts["points.radii"].split(", "))
    points = map_points(radii, int(facts["points.bearing"]))
    assert len(drawn) == len(points) == io.N_POINTS
    for index, x, y in drawn:
        want_x, want_y = points[int(index)]
        assert float(x) == pytest.approx(want_x, abs=1e-4)
        assert float(y) == pytest.approx(want_y, abs=1e-4)
    # Point 1 is straight at the enemy (+x), point 3 a quarter turn counter-clockwise.
    assert points[1] == pytest.approx((radii[0], 0.0))
    assert points[3] == pytest.approx((0.0, radii[0]), abs=1e-9)


def test_a_stale_number_is_reported(page: str, facts: dict[str, str]) -> None:
    stale = page.replace(
        '<dd data-fact="actor.params">84,676</dd>',
        '<dd data-fact="actor.params">80,000</dd>',
    )
    assert stale != page
    [mismatch] = check_page(stale, facts)
    assert (mismatch.key, mismatch.page, mismatch.expected) == (
        "actor.params",
        "80,000",
        facts["actor.params"],
    )


def test_the_design_doc_disagreeing_with_the_code_is_an_error() -> None:
    doc = DESIGN_DOC.read_text()
    changed = doc.replace("`ENTITY_DIM = 40`", "`ENTITY_DIM = 41`")
    assert changed != doc
    with pytest.raises(CommanderFactsError, match="ENTITY_DIM"):
        design_facts(changed)
    with pytest.raises(CommanderFactsError, match="LEARNED_COMMAND_TICKS"):
        design_facts(doc.replace("LEARNED_COMMAND_TICKS", "SOME_TICKS"))


def test_the_page_is_part_of_the_site() -> None:
    assert '"commander/index.html"' in VITE_CONFIG.read_text()
    assert 'href: "/commander/"' in NAV.read_text()
