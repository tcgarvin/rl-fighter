"""Render a lab ``results.md`` to a small standalone HTML page (``/duel/notes.html``).

Handles the Markdown subset the lab reports use: ATX headings, paragraphs, bullet
lists (one level of nesting by indent), pipe tables, fenced code, inline code,
bold, italics and links. ``<!-- hand:NAME -->`` markers are dropped (their content
is kept); a ``TODO(coordinator)`` hand section renders as "pending". No third-party
Markdown package is needed.

    python -m tools.render_notes --md lab/runs/<run>/results.md --out dist/duel/notes.html
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from collections.abc import Sequence
from pathlib import Path

_COMMENT = re.compile(r"<!--.*?-->", re.S)
_TODO = re.compile(r"TODO\(coordinator\):[^\n]*")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^(\s*)[-*]\s+(.*)$")
_TABLE_RULE = re.compile(r"^\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
<meta name="theme-color" content="#060a10" />
<title>{title}</title>
<style>
:root {{ --bg: #060a10; --fg: #e5e1d8; --muted: #8c99a8; --line: #1d2633; --accent: #63bfff; }}
html {{ background: var(--bg); color: var(--fg); -webkit-text-size-adjust: 100%; }}
body {{ margin: 0 auto; max-width: 820px; font: 15px/1.55 "Helvetica Neue", Arial, sans-serif;
  padding: max(20px, env(safe-area-inset-top)) max(16px, env(safe-area-inset-right))
  max(40px, env(safe-area-inset-bottom)) max(16px, env(safe-area-inset-left)); }}
a {{ color: var(--accent); }}
nav {{ font-size: 12px; letter-spacing: .06em; color: var(--muted); margin-bottom: 18px; }}
nav a {{ color: var(--muted); text-decoration: none; }}
h1 {{ font-size: 22px; line-height: 1.3; letter-spacing: .02em; }}
h2 {{ font-size: 17px; margin-top: 2em; border-top: 1px solid var(--line); padding-top: 1em; }}
h3 {{ font-size: 15px; margin-top: 1.6em; }}
code {{ font: 12.5px ui-monospace, "SF Mono", Menlo, monospace; background: #0f1621;
  padding: 1px 4px; border-radius: 3px; overflow-wrap: anywhere; }}
pre {{ background: #0f1621; padding: 10px; overflow-x: auto; }}
pre code {{ background: none; padding: 0; }}
.table {{ overflow-x: auto; margin: 1em 0; }}
table {{ border-collapse: collapse; font-size: 12.5px; font-variant-numeric: tabular-nums; }}
th, td {{ border-bottom: 1px solid var(--line); padding: 5px 8px; text-align: left; white-space: nowrap; }}
th {{ color: var(--muted); font-weight: 600; }}
li {{ margin: .3em 0; }}
.pending {{ color: var(--muted); font-style: italic; }}
</style>
</head>
<body>
<nav><a href="/duel/">← Live duel</a> &nbsp;·&nbsp; <a href="/">Story demo</a></nav>
{body}
</body>
</html>
"""


def _inline(text: str) -> str:
    """Escape ``text`` and apply inline code, links, bold and italics."""
    parts = re.split(r"(`[^`]*`)", text)
    out = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) >= 2:
            out.append(f"<code>{html.escape(part[1:-1])}</code>")
            continue
        s = html.escape(part, quote=False)
        s = re.sub(
            r"\[([^\]]+)\]\(([^)\s]+)\)",
            lambda m: f'<a href="{html.escape(m.group(2))}">{m.group(1)}</a>',
            s,
        )
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])", r"<em>\1</em>", s)
        s = s.replace("PENDING_NOTE", '<span class="pending">pending</span>')
        out.append(s)
    return "".join(out)


def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _table(lines: list[str]) -> str:
    head = "".join(f"<th>{_inline(c)}</th>" for c in _cells(lines[0]))
    rows = "".join(
        "<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in _cells(r)) + "</tr>"
        for r in lines[2:]
    )
    return (
        f'<div class="table"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{rows}</tbody></table></div>"
    )


def _list(items: list[tuple[int, str]]) -> str:
    """Bullets as ``(indent, text)``; deeper indents nest one level."""
    base = items[0][0]
    out = ["<ul>"]
    open_sub = False
    for indent, text in items:
        if indent > base and not open_sub:
            out.append("<ul>")
            open_sub = True
        elif indent <= base and open_sub:
            out.append("</ul>")
            open_sub = False
        out.append(f"<li>{_inline(text)}</li>")
    if open_sub:
        out.append("</ul>")
    out.append("</ul>")
    return "".join(out)


def markdown_to_html(md: str) -> tuple[str, str]:
    """Return ``(title, body_html)`` for the supported Markdown subset."""
    md = _TODO.sub("PENDING_NOTE", _COMMENT.sub("", md))
    lines = md.splitlines()
    blocks: list[str] = []
    title = "Lab notes"
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        if line.startswith("```"):
            j = i + 1
            while j < len(lines) and not lines[j].startswith("```"):
                j += 1
            code = html.escape("\n".join(lines[i + 1 : j]))
            blocks.append(f"<pre><code>{code}</code></pre>")
            i = j + 1
            continue
        heading = _HEADING.match(line)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            if text == "PENDING_NOTE":
                text = "Lab notes: results pending"
            if level == 1 and title == "Lab notes":
                title = re.sub(r"[`*]", "", text)
            blocks.append(f"<h{level}>{_inline(text)}</h{level}>")
            i += 1
            continue
        if line.lstrip().startswith("|") and i + 1 < len(lines):
            if _TABLE_RULE.match(lines[i + 1].strip()):
                j = i
                while j < len(lines) and lines[j].lstrip().startswith("|"):
                    j += 1
                blocks.append(_table(lines[i:j]))
                i = j
                continue
        if _BULLET.match(line):
            items: list[tuple[int, str]] = []
            while i < len(lines) and lines[i].strip():
                bullet = _BULLET.match(lines[i])
                if bullet:
                    items.append((len(bullet.group(1)), bullet.group(2)))
                elif items:
                    # Continuation line of the previous bullet.
                    indent, text = items[-1]
                    items[-1] = (indent, f"{text} {lines[i].strip()}")
                i += 1
            blocks.append(_list(items))
            continue
        para = []
        while i < len(lines) and lines[i].strip():
            if _HEADING.match(lines[i]) or _BULLET.match(lines[i]):
                break
            para.append(lines[i].strip())
            i += 1
        blocks.append(f"<p>{_inline(' '.join(para))}</p>")
    return title, "\n".join(blocks)


def render(md_path: Path | None, out_path: Path) -> None:
    """Write the notes page; a missing ``md_path`` gives a "results pending" page."""
    if md_path is not None and md_path.is_file():
        title, body = markdown_to_html(md_path.read_text())
    else:
        title = "Lab notes"
        body = (
            "<h1>Lab notes</h1><p class='pending'>Results pending: the overnight "
            "evals have not landed yet.</p>"
        )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(PAGE.format(title=html.escape(title), body=body))


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--md", type=Path, default=None)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.md is not None and not args.md.is_file():
        print(f"render_notes: {args.md} not found; writing a pending page")
    render(args.md, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
