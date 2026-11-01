"""The population report: plain Markdown that reads on a phone.

Short lines, no tables, no code blocks. The owner reviews on an iPhone in portrait, so
everything is lists and wraps naturally. The family tree folds a run of single-child
history pilots into one line, or its depth would push the text off the screen.
"""

from __future__ import annotations

import textwrap
from collections.abc import Sequence
from typing import Final

from spacefight.population.culling import (
    RULE_BOTTOM,
    RULE_FOUNDER_CAP,
    ShadowCullReport,
)
from spacefight.population.rating import Rating
from spacefight.population.records import (
    HISTORY_FAMILY,
    UNRELATED,
    Member,
    Population,
)
from spacefight.population.standings import (
    RoundRobinResults,
    Transitivity,
    WinMatrix,
)

# Longest line a section writes before wrapping.
LINE_WIDTH: Final = 64
# Pairs of each kind listed in the tree-against-behaviour section.
_BEHAVIOUR_PAIRS_LISTED: Final = 3
MISSION_NAMES: Final[dict[str, str]] = {
    "deathmatch": "Deathmatch",
    "carrier_battle": "Carrier battle",
    "convoy_escort": "Convoy escort",
}


def _wrap(text: str, indent: str = "") -> list[str]:
    return textwrap.wrap(
        text,
        width=LINE_WIDTH,
        initial_indent=indent,
        subsequent_indent=" " * len(indent),
        break_long_words=False,
        break_on_hyphens=False,
    )


def _bullet(text: str, depth: int = 0) -> list[str]:
    return _wrap(text, "  " * depth + "- ")


def _member_line(member: Member) -> str:
    name = f"**{member.id}**" if member.is_active else member.id
    if member.family == HISTORY_FAMILY:
        return name
    return f"{name} ({member.family}, {member.status})"


def _tree_lines(population: Population, member: Member, depth: int) -> list[str]:
    chain = [member]
    while chain[-1].family == HISTORY_FAMILY:
        children = population.children(chain[-1].id)
        if len(children) != 1:
            break
        chain.append(children[0])
    text = " > ".join([*(m.id for m in chain[:-1]), _member_line(chain[-1])])
    lines = _bullet(text, depth)
    for child in population.children(chain[-1].id):
        lines += _tree_lines(population, child, depth + 1)
    return lines


def family_tree_lines(population: Population) -> list[str]:
    """The tree as nested bullets; bold members are active."""
    lines = ["## Family tree", ""]
    for root in population.roots():
        lines += _tree_lines(population, root, 0)
    lines += ["", "Bold is active. The rest are history, kept for ancestry."]
    return lines


def _family_lines(population: Population) -> list[str]:
    families: dict[str, list[Member]] = {}
    for member in population.active():
        families.setdefault(member.family, []).append(member)
    lines = ["## Families", ""]
    for family, members in sorted(families.items()):
        founder = members[0].founder
        lines += _bullet(f"**{family}**: {len(members)} active, founder {founder}")
    if not families:
        lines.append("Nobody is active.")
    return lines


def _rating_lines(population: Population, ratings: Sequence[Rating]) -> list[str]:
    lines = ["## Combat ratings", ""]
    if not ratings:
        return [*lines, "No ratings yet."]
    for place, r in enumerate(ratings, start=1):
        word = ""
        if (
            r.member in population.members
            and not population.members[r.member].is_active
        ):
            word = ", archived"
        lines += _wrap(
            f"{place}. **{r.member}** {r.rating:+.0f} ± {r.sd:.0f} "
            f"({r.matches} matches{word})"
        )
    lines += ["", "Points are relative to this field. ± is one sd."]
    return lines


def _transitivity_lines(title: str, summary: Transitivity) -> list[str]:
    lines = [f"**{title}**", ""]
    lines += _bullet(
        f"Cycles: {summary.cyclic} of {summary.triads} decided triads "
        f"({summary.cyclic_share:.0%})"
    )
    if summary.beats_everyone:
        lines += _bullet(f"Beats everyone: {', '.join(summary.beats_everyone)}")
    else:
        lines += _bullet("Nobody beats everyone.")
    for cycle in summary.cycles[:3]:
        lines += _bullet(
            f"{' > '.join(cycle.cycle)} > {cycle.cycle[0]}: "
            f"weakest edge +{cycle.strength:.2f}, z {cycle.z:.1f}"
        )
    return lines


def _variety_lines(results: RoundRobinResults) -> list[str]:
    lines = ["## Is there variety to protect?", ""]
    lines += [*_transitivity_lines("Overall", results.transitivity_overall), ""]
    for mission, summary in results.transitivity_by_mission.items():
        lines += [
            *_transitivity_lines(MISSION_NAMES.get(mission, mission), summary),
            "",
        ]
    return lines[:-1]


def _matchup_lines(title: str, matrix: WinMatrix) -> list[str]:
    """Each member's best and worst results, in place of a wide matrix."""
    lines = [f"**{title}**", ""]
    for name in sorted(matrix.members):
        rates = {
            other: matrix.rate[(name, other)]
            for other in matrix.members
            if other != name and (name, other) in matrix.rate
        }
        if not rates:
            continue
        best = max(rates, key=lambda o: (rates[o], o))
        worst = min(rates, key=lambda o: (rates[o], o))
        lines += _bullet(
            f"**{name}**: best {rates[best]:.2f} v {best}, "
            f"worst {rates[worst]:.2f} v {worst}"
        )
    return lines


def _cull_lines(report: ShadowCullReport) -> list[str]:
    lines = [f"## Would-be culls ({report.phase})", ""]
    lines += _wrap("Shadow mode: nobody was culled and no record changed.")
    if report.below_target:
        lines += [""] + _wrap(
            "The population is under target, so a live rule would likely wait."
        )
    lines.append("")
    if not report.culls:
        lines.append("Nobody would go.")
    titles = {RULE_BOTTOM: "Bottom on combat", RULE_FOUNDER_CAP: "Founder cap"}
    for cull in report.culls:
        flag = " Close call." if cull.close_call else ""
        lines += _bullet(f"**{cull.member}**, {titles[cull.rule]}. {cull.reason}{flag}")
    for spared in report.protected:
        lines += _bullet(f"{spared.member} stays: {spared.reason}")
    if report.unrated:
        lines += _bullet(f"Not rated, so outside the rule: {', '.join(report.unrated)}")
    lines += ["", "**After the bonus**", ""]
    for row in report.standings:
        lines += _wrap(
            f"- {row.member}: {row.adjusted:+.0f} "
            f"({row.rating:+.0f} combat, {row.bonus:+.0f} for "
            f"{_distance_word(row.tree_distance)})"
        )
    return lines


def _distance_word(distance: int) -> str:
    if distance == UNRELATED:
        return "no relation"
    return f"{distance} edge" + ("" if distance == 1 else "s")


def _behaviour_lines(report: ShadowCullReport) -> list[str]:
    log = report.behaviour
    lines = ["## Tree against behaviour", ""]
    if not log.pairs:
        return [*lines, "No behaviour features for this phase."]
    if log.correlation_pairs:
        lines += _wrap(
            f"Rank correlation {log.tree_behaviour_correlation:+.2f} "
            f"over {log.correlation_pairs} related pairs."
        )
    else:
        lines += _wrap("Too few related pairs for a correlation.")
    lines += ["", "**Fly most alike**", ""]
    for pair in log.pairs[:_BEHAVIOUR_PAIRS_LISTED]:
        lines += _bullet(
            f"{pair.a} and {pair.b}: {pair.behaviour_distance:.2f}, "
            f"{_distance_word(pair.tree_distance)}"
        )
    # With few pairs the two lists would be the same pairs.
    if len(log.pairs) > 2 * _BEHAVIOUR_PAIRS_LISTED:
        lines += ["", "**Fly least alike**", ""]
        for pair in reversed(log.pairs[-_BEHAVIOUR_PAIRS_LISTED:]):
            lines += _bullet(
                f"{pair.a} and {pair.b}: {pair.behaviour_distance:.2f}, "
                f"{_distance_word(pair.tree_distance)}"
            )
    if log.missing:
        lines += ["", *_wrap(f"No features for: {', '.join(log.missing)}.")]
    return lines


def render_report(
    population: Population,
    phase: str = "",
    date: str = "",
    results: RoundRobinResults | None = None,
    shadow: ShadowCullReport | None = None,
    caveats: Sequence[str] = (),
) -> str:
    """The whole report as Markdown (module docstring).

    Args:
        population: The records.
        phase: Phase name, if the report covers one.
        date: Its date.
        results: The phase's round robin; ``None`` when there has been none yet.
        shadow: The phase's shadow culling; ``None`` when there has been none yet.
        caveats: Lines printed at the top, such as a small run's warning.
    """
    lines = [f"# Pilot population: {population.season}", ""]
    if phase:
        lines += [f"Phase {phase}, {date}.", ""]
    for caveat in caveats:
        lines += [*_wrap(f"**Note:** {caveat}"), ""]
    ratings = results.ratings if results is not None else ()
    sections = [
        _family_lines(population),
        family_tree_lines(population),
        _rating_lines(population, ratings),
    ]
    if results is not None:
        sections.append(_variety_lines(results))
        matchups = ["## Who beats whom", ""]
        matchups += [*_matchup_lines("Overall", results.overall), ""]
        for mission, matrix in results.by_mission.items():
            title = MISSION_NAMES.get(mission, mission)
            matchups += [*_matchup_lines(title, matrix), ""]
        sections.append(matchups[:-1])
    if shadow is not None:
        sections += [_cull_lines(shadow), _behaviour_lines(shadow)]
    for section in sections:
        lines += [*section, ""]
    return "\n".join(lines).rstrip() + "\n"
