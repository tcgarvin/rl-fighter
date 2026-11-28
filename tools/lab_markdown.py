"""Render lab ``results.md`` / ``plan.md`` files to HTML with the ``markdown`` package.

Shared by ``tools/build_notebook.py`` (the ``/notebook/`` data) and
``tools/render_notes.py`` (the standalone notes page). The lab files are written by
hand and by ``tools/lab_report.py``, so the input is normalised before rendering
instead of asking the files to change:

- ``<!-- hand:NAME -->`` / ``<!-- /hand:NAME -->`` markers and other comments are
  dropped (their content is kept); ``TODO(coordinator): ...`` reads "pending".
- A list that starts straight after a paragraph line gets the blank line Markdown
  needs, and two-space nested bullets are indented to four.
- Tables are wrapped in ``<div class="table-scroll">`` so they scroll sideways on a
  phone instead of widening the page.
- Inline code that names a file or directory in the repo becomes a link: a lab run's
  ``results.md`` (or its directory) to its notebook entry, a run's ``plan.md`` to the
  entry's plan section, anything else to GitHub. Markdown links written relative to
  the document (``[last night](../2026-01-01-a/results.md)``) go to the same places;
  one that names a missing file raises ``BrokenLinkError``.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path

import markdown  # type: ignore[import-untyped]

GITHUB_BLOB = "https://github.com/tcgarvin/rl-fighter/blob/main"
GITHUB_TREE = "https://github.com/tcgarvin/rl-fighter/tree/main"
PENDING_HTML = '<span class="pending">pending</span>'
PENDING_TITLE = "Lab notes: results pending"

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_TODO = re.compile(r"TODO\(coordinator\):[^\n<]*")
_PENDING_TOKEN = "PENDINGNOTE"
_FENCE = re.compile(r"^\s*(```|~~~)")
_BULLET = re.compile(r"^(\s*)([-*+]|\d+\.)\s+")
_H1 = re.compile(r"<h1>(.*?)</h1>\s*", re.S)
_TAG = re.compile(r"<[^>]+>")
_CODE = re.compile(r"<code>([^<]+)</code>")
_PATH_LIKE = re.compile(r"^[\w.\-/]+$")
_HREF = re.compile(r'<a href="([^"]*)"')
_NON_RELATIVE_HREF = re.compile(r"^(?:[a-z][a-z0-9+.-]*:|/|#)", re.I)
_EXTENSIONS = ["tables", "fenced_code", "sane_lists"]


class BrokenLinkError(ValueError):
    """A lab document links, relative to itself, to a file the repo does not have."""


@dataclass(frozen=True)
class LinkContext:
    """Where a document lives, for turning repo paths in inline code into links.

    ``repo_root`` is the checkout; ``run_dir`` the lab run the document belongs to
    (its relative paths resolve there first); ``run_ids`` the runs that have a
    notebook entry, so links to them stay on the site.
    """

    repo_root: Path
    run_dir: Path
    run_ids: frozenset[str]


@dataclass(frozen=True)
class Rendered:
    """A rendered document: plain-text ``title`` (its first H1) and ``body`` HTML.

    ``body`` keeps the H1; ``body_without_title`` drops it for pages that show the
    title themselves.
    """

    title: str
    body: str
    body_without_title: str


def _normalise(md: str) -> str:
    """Make the lab files' loose Markdown parse the way it reads (see module doc)."""
    md = _TODO.sub(_PENDING_TOKEN, _COMMENT.sub("", md))
    out: list[str] = []
    in_fence = False
    prev = ""
    for line in md.splitlines():
        if _FENCE.match(line):
            in_fence = not in_fence
            out.append(line)
            prev = line
            continue
        if not in_fence:
            bullet = _BULLET.match(line)
            if bullet:
                indent = len(bullet.group(1).expandtabs(4))
                if 0 < indent < 4:
                    line = "    " + line.lstrip()
                elif (
                    prev.strip() and not _BULLET.match(prev) and not prev[:1].isspace()
                ):
                    # A list straight after a paragraph line: Markdown needs a gap.
                    out.append("")
        out.append(line)
        prev = line
    return "\n".join(out) + "\n"


def plain_text(fragment: str) -> str:
    """Strip tags and entities from an HTML fragment and collapse whitespace."""
    return " ".join(html.unescape(_TAG.sub("", fragment)).split())


def _site_target(path: Path, ctx: LinkContext) -> str | None:
    """Where the site serves an existing repo ``path``: its notebook entry or GitHub.

    ``None`` when the path does not exist or lies outside the repo.
    """
    root = ctx.repo_root.resolve()
    path = path.resolve()
    if not path.exists() or not path.is_relative_to(root):
        return None
    rel = path.relative_to(root)
    parts = rel.parts
    if len(parts) >= 3 and parts[:2] == ("lab", "runs") and parts[2] in ctx.run_ids:
        run_id = parts[2]
        rest = parts[3:]
        if rest == ("plan.md",):
            return f"/notebook/#{run_id}/plan"
        if rest in ((), ("results.md",)):
            return f"/notebook/#{run_id}"
    prefix = GITHUB_TREE if path.is_dir() else GITHUB_BLOB
    return f"{prefix}/{rel.as_posix()}"


def _resolve_link(text: str, ctx: LinkContext) -> str | None:
    """Return a link target for an inline-code repo path, or ``None`` if it is not one."""
    candidate = text.split(":", 1)[0].rstrip("/")
    if not candidate or not _PATH_LIKE.match(candidate) or candidate.startswith("."):
        return None
    if "/" not in candidate and "." not in candidate:
        return None
    for base in (ctx.run_dir, ctx.repo_root):
        target = _site_target(base / candidate, ctx)
        if target is not None:
            return target
    return None


def _link_code_paths(body: str, ctx: LinkContext) -> str:
    def replace(match: re.Match[str]) -> str:
        target = _resolve_link(html.unescape(match.group(1)), ctx)
        if target is None:
            return match.group(0)
        external = target.startswith("http")
        attrs = ' rel="noopener"' if external else ""
        return f'<a class="code-link" href="{html.escape(target)}"{attrs}>{match.group(0)}</a>'

    return _CODE.sub(replace, body)


def _rewrite_relative_hrefs(body: str, ctx: LinkContext) -> str:
    """Point Markdown links written relative to the document at their site targets.

    A link such as ``[last night](../2026-01-01-a/results.md)`` reads correctly in
    the repo but would resolve against ``/notebook/`` on the site. Links with a
    scheme, an absolute path or only a fragment are left alone.

    Raises:
        BrokenLinkError: a relative link names a file that does not exist in the repo.
    """

    def replace(match: re.Match[str]) -> str:
        href = html.unescape(match.group(1))
        if _NON_RELATIVE_HREF.match(href):
            return match.group(0)
        path_part, _, fragment = href.partition("#")
        target = _site_target(ctx.run_dir / path_part, ctx)
        if target is None:
            raise BrokenLinkError(
                f"{ctx.run_dir}: link {href!r} names no file in the repo"
            )
        if fragment and not target.startswith("/notebook/"):
            target = f"{target}#{fragment}"
        external = ' rel="noopener"' if target.startswith("http") else ""
        return f'<a href="{html.escape(target)}"{external}'

    return _HREF.sub(replace, body)


def render_markdown(md: str, ctx: LinkContext | None = None) -> Rendered:
    """Render one lab Markdown document.

    Args:
        md: the document text.
        ctx: where the document lives; without it inline-code paths stay plain and
            relative links are left as written.

    Returns:
        The title (first H1 as plain text, ``"Lab notes"`` if there is none, or
        ``PENDING_TITLE`` when the H1 is still a coordinator TODO) and the HTML.

    Raises:
        BrokenLinkError: with ``ctx``, a relative link names a missing file.
    """
    body = markdown.markdown(
        _normalise(md), extensions=_EXTENSIONS, output_format="html"
    )
    body = body.replace("<table>", '<div class="table-scroll"><table>').replace(
        "</table>", "</table></div>"
    )
    if ctx is not None:
        body = _rewrite_relative_hrefs(body, ctx)
        body = _link_code_paths(body, ctx)
    title = "Lab notes"
    h1 = _H1.search(body)
    if h1 is not None:
        heading = plain_text(h1.group(1))
        title = PENDING_TITLE if heading == _PENDING_TOKEN else heading
        if heading == _PENDING_TOKEN:
            body = body.replace(
                h1.group(0), f"<h1>{html.escape(PENDING_TITLE)}</h1>\n", 1
            )
    body = body.replace(_PENDING_TOKEN, PENDING_HTML)
    without = _H1.sub("", body, count=1) if h1 is not None else body
    return Rendered(title=title, body=body, body_without_title=without)
