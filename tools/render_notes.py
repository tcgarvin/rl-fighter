"""Render a lab ``results.md`` to a small standalone HTML page (``/duel/notes.html``).

Rendering is ``tools/lab_markdown.py`` (the ``markdown`` package plus the lab
files' quirks), shared with ``tools/build_notebook.py``: ``<!-- hand:NAME -->``
markers are dropped (their content is kept) and a ``TODO(coordinator)`` hand
section renders as "pending".

    python -m tools.render_notes --md lab/runs/<run>/results.md --out dist/duel/notes.html
"""

from __future__ import annotations

import argparse
import html
import sys
from collections.abc import Sequence
from pathlib import Path

from tools.lab_markdown import render_markdown

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
.table-scroll {{ overflow-x: auto; margin: 1em 0; }}
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


def markdown_to_html(md: str) -> tuple[str, str]:
    """Return ``(title, body_html)``; the renderer is shared with the notebook."""
    rendered = render_markdown(md)
    return rendered.title, rendered.body


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
