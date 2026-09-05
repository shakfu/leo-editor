# @+leo-ver=5-thin
# @+node:sa.20260905210100.1: * @file ../tui/model.py
"""
The model side of the terminal view.

Deliberately kept free of curses so it can be tested without a terminal, and
deliberately written against the *model* -- Outline, Position, the event bus --
rather than against a commander's frame. Every place this file is forced to
reach through c.frame is marked `# FRAME:` and collected in FRAME_REACHES, so
that the list of things a non-Qt view still cannot do is measured rather than
guessed. See LEO_REFACTOR.md.
"""

# @+<< tui.model imports >>
# @+node:sa.20260905210100.2: ** << tui.model imports >>
from __future__ import annotations
from typing import Any, TYPE_CHECKING
from leo.core import signal_manager

if TYPE_CHECKING:  # pragma: no cover
    from leo.core.leoCommands import Commands as Cmdr
    from leo.core.leoNodes import Position
# @-<< tui.model imports >>

# Things the terminal view still needs a commander's *frame* for.
# Empty is the goal; see LEO_REFACTOR.md.
FRAME_REACHES: list[str] = []

# Things the terminal view needs a *text wrapper* for. This is not the same
# failing: a view is entitled to a text buffer, and behind a NullFrame that
# buffer is a plain StringTextWrapper -- exactly right for a terminal. It is
# recorded because it means "a view must own a wrapper", which constrains any
# future leolib.
WRAPPER_REACHES: list[str] = [
    "u.beforeChangeBody/afterChangeBody read the caret, selection and scroll "
    "from c.frame.body.wrapper; afterChangeBody's docstring makes that the "
    "caller's contract.",
]


# @+others
# @+node:sa.20260905210100.3: ** class Row
class Row:
    """One visible outline line."""

    __slots__ = ('depth', 'expanded', 'has_children', 'p')

    def __init__(self, p: Position, depth: int, has_children: bool, expanded: bool) -> None:
        self.p = p
        self.depth = depth
        self.has_children = has_children
        self.expanded = expanded

    def render(self, width: int = 80, marker: str = ' ') -> str:
        box = '-' if not self.has_children else ('v' if self.expanded else '>')
        s = f"{marker}{'  ' * self.depth}{box} {self.p.h}"
        return s[:width]


# @+node:sa.20260905210100.4: ** class OutlineModel
class OutlineModel:
    """
    A terminal view's model access.

    Owns no widgets. Reads the outline, keeps its own cursor, and listens to
    the document's event bus so that a change made anywhere -- another view, a
    script, an external file reload -- marks this view dirty.
    """

    # @+others
    # @+node:sa.20260905210100.5: *3* model.__init__
    def __init__(self, c: Cmdr) -> None:
        self.c = c
        self.outline = c.outline
        self.index = 0  # Index into self.rows.
        self.body_scroll = 0
        self.dirty = True  # Something changed: rows need rebuilding.
        self.rows: list[Row] = []
        self.subscribe()

    # @+node:sa.20260905210100.6: *3* model.subscribe
    def subscribe(self) -> None:
        """Follow the document. The model never calls us; we listen."""
        for signal in (
            'body_changed',
            'head_changed',
            'structure_changed',
            'status_changed',
            'bulk_changed',
        ):
            signal_manager.connect(self.outline, signal, self.on_model_changed)

    def on_model_changed(self, v: Any | None = None, origin: Cmdr | None = None) -> None:
        if origin is not self.c:
            self.dirty = True

    # @+node:sa.20260905210100.7: *3* model.build_rows
    def build_rows(self) -> list[Row]:
        """Walk the outline, honouring *this* view's expansion state."""
        c = self.c
        rows: list[Row] = []
        with self.outline.acting_view(c):  # Folds are per view.
            p = c.rootPosition()
            while p:
                has_children = p.hasChildren()
                expanded = has_children and p.isExpanded()
                rows.append(Row(p.copy(), p.level(), has_children, expanded))
                if expanded:
                    p.moveToThreadNext()
                else:
                    p.moveToNodeAfterTree()
        self.rows = rows
        self.dirty = False
        self.index = max(0, min(self.index, len(rows) - 1))
        return rows

    # @+node:sa.20260905210100.8: *3* model.current
    @property
    def current(self) -> Position | None:
        if self.dirty:
            self.build_rows()
        if not self.rows:
            return None
        return self.rows[self.index].p

    # @+node:sa.20260905210100.9: *3* model.navigation
    def move(self, delta: int) -> None:
        if self.dirty:
            self.build_rows()
        if self.rows:
            self.index = max(0, min(self.index + delta, len(self.rows) - 1))
            self.body_scroll = 0
            self.select_current()

    def select_current(self) -> None:
        """Make this view's cursor the commander's current position."""
        p = self.current
        if p:
            with self.outline.acting_view(self.c):
                self.c.selectPosition(p)

    def toggle(self) -> None:
        """Expand or contract the current node, in this view only."""
        if self.dirty:
            self.build_rows()
        if not self.rows:
            return
        row = self.rows[self.index]
        if not row.has_children:
            return
        with self.outline.acting_view(self.c):
            if row.expanded:
                row.p.contract()
            else:
                row.p.expand()
        self.dirty = True

    def expand_all_ancestors(self) -> None:
        p = self.current
        if not p:
            return
        with self.outline.acting_view(self.c):
            for ancestor in p.parents():
                ancestor.expand()
        self.dirty = True

    # @+node:sa.20260905220000.1: *3* model.editing
    def run_command(self, name: str) -> None:
        """
        Run one of Leo's own commands as this view.

        All 19 structural commands tried -- insert, delete, move, promote,
        demote, clone, paste, sort, mark, undo, redo -- already work with a
        null frame, so a terminal view drives the real thing rather than
        reimplementing outline surgery.
        """
        c = self.c
        with self.outline.acting_view(c):
            c.doCommandByName(name)
        self.dirty = True
        self.sync_cursor_from_commander()

    def sync_cursor_from_commander(self) -> None:
        """Follow c.p after a command moved it."""
        self.build_rows()
        target = self.c.p
        if not target:
            return
        for i, row in enumerate(self.rows):
            if row.p == target:
                self.index = i
                return

    def set_headline(self, text: str) -> None:
        """Rename the current node, undoably."""
        c, p = self.c, self.current
        if not p:
            return
        text = text.replace('\n', '')
        if text == p.h:
            return
        u = c.undoer
        with self.outline.acting_view(c):
            bunch = u.beforeChangeHeadline(p)
            # No reach into c.frame.tree here. This used to have to call
            # tree.setHeadline itself, because a headline widget left stale by
            # a model-only rename is what onHeadChanged then commits -- so the
            # rename would be reverted. Every view now follows head_changed in
            # c.on_model_head_changed, which is the headline half of stage 6.
            p.v.setHeadString(text)
            p.setDirty()
            c.setChanged()
            u.afterChangeHeadline(p, 'Change Headline', bunch)
        self.dirty = True

    def set_body(self, text: str, insert: int = 0) -> None:
        """
        Replace the current node's body, undoably.

        Sets the view's text wrapper first: u.afterChangeBody reads the caret
        and selection from it (see WRAPPER_REACHES), and for a terminal view
        that wrapper is a StringTextWrapper holding exactly this text.
        """
        c, p = self.c, self.current
        if not p or text == p.b:
            return
        u = c.undoer
        with self.outline.acting_view(c):
            bunch = u.beforeChangeBody(p)
            p.v.setBodyString(text)  # The model. Not p.b: that would redraw.
            w = c.frame.body.wrapper
            if w:
                w.setAllText(text)
                w.setInsertPoint(min(insert, len(text)))
            p.setDirty()
            c.setChanged()
            u.afterChangeBody(p, 'Change Body', bunch)
        self.dirty = True

    def save(self) -> bool:
        """Save the document. Returns False when it has no file name."""
        c = self.c
        if not c.fileName():
            return False
        with self.outline.acting_view(c):
            c.fileCommands.save(c.fileName())
        return True

    # @+node:sa.20260905210100.10: *3* model.body_lines
    def body_lines(self) -> list[str]:
        """The current node's body, from the model."""
        p = self.current
        return p.b.split('\n') if p else []

    # @+node:sa.20260905210100.11: *3* model.status
    def status(self) -> str:
        p = self.current
        name = self.c.shortFileName() or '<unnamed>'
        changed = '*' if self.c.changed else ' '
        n = len(self.rows)
        views = len(self.outline.views)
        where = f"{self.index + 1}/{n}" if n else '0/0'
        gnx = p.gnx if p else ''
        return f"{changed}{name}  {where}  views:{views}  {gnx}"

    # @-others


# @-others
# @@language python
# @@tabwidth -4
# @-leo
