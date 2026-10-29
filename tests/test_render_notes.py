"""``tools/render_notes.py``: the lab-report Markdown subset renders to HTML."""

from __future__ import annotations

from pathlib import Path

from tools.render_notes import markdown_to_html, render


def test_headings_tables_lists_and_inline_markup_render() -> None:
    md = (
        "# A **bold** title\n\nSome `code` and a [link](https://x.y).\n\n"
        "- one\n- two\n  - nested\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"
    )
    title, body = markdown_to_html(md)
    assert title == "A bold title"
    assert "<h1>A <strong>bold</strong> title</h1>" in body
    assert "<code>code</code>" in body
    assert '<a href="https://x.y">link</a>' in body
    assert "<ul><li>one</li><li>two</li><ul><li>nested</li></ul></ul>" in body
    assert "<th>a</th><th>b</th>" in body and "<td>1</td><td>2</td>" in body


def test_hand_markers_drop_and_coordinator_todos_read_pending() -> None:
    md = (
        "# <!-- hand:title -->TODO(coordinator): fill me<!-- /hand:title -->\n\nx < y\n"
    )
    title, body = markdown_to_html(md)
    assert title == "Lab notes: results pending"
    assert "hand:title" not in body and "TODO" not in body
    assert "x &lt; y" in body


def test_missing_results_give_a_pending_page(tmp_path: Path) -> None:
    out = tmp_path / "notes.html"
    render(tmp_path / "absent.md", out)
    assert "Results pending" in out.read_text()
