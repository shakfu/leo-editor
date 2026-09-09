"""
Composing the terminal image.

Pure: takes an OutlineModel and a size, returns a list of strings. Keeping the
drawing separate from curses is what lets the terminal view be tested without a
terminal, the same way the null gui lets Leo's core be tested without Qt.

A near-copy of leo/tui/screen.py, which this package replaces. The duplicate
goes when leo/tui does.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from leo.leotui.model import OutlineModel


def compose(model: OutlineModel, width: int = 80, height: int = 24) -> list[str]:
    """Return exactly `height` lines of at most `width` characters."""
    if model.dirty:
        model.build_rows()
    tree_h = max(3, (height - 2) // 2)
    body_h = height - tree_h - 2  # One divider, one status line.
    lines: list[str] = []

    # The outline pane, scrolled to keep the cursor visible.
    top = max(0, min(model.index - tree_h // 2, len(model.rows) - tree_h))
    top = max(0, top)
    for i in range(tree_h):
        n = top + i
        if n < len(model.rows):
            marker = '>' if n == model.index else ' '
            lines.append(model.rows[n].render(width, marker))
        else:
            lines.append('')

    # The divider names the node whose body is shown.
    p = model.current
    title = f" {p.h} " if p else ' '
    bar = f"--{title}".ljust(width, '-')
    lines.append(bar[:width])

    # The body pane.
    body = model.body_lines()[model.body_scroll :]
    for i in range(body_h):
        lines.append(body[i][:width] if i < len(body) else '')

    lines.append(model.status()[:width].ljust(width))
    return [ln.ljust(width)[:width] for ln in lines[:height]]
