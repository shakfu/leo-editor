"""
The model side of the terminal front end.

Written against leolib -- an Outline, Positions, the document's event bus, and
a TuiView -- and against nothing else. There is no commander here, so there is
no `c.doCommandByName`: Leo's own commands live on Commands and reach
`g.app.gui`, which is exactly the coupling this front end exists to avoid.
The structural edits below are therefore built from the Position primitives in
leoNodes, which are model. They move a node among its siblings; Leo's
move-outline-up moves it in *visible* order and honours hoists, which is a
larger thing and deliberately not reproduced.

Kept free of curses so it can be tested without a terminal.
"""

from __future__ import annotations
from typing import Any

from leo import leolib
from leo.core import signal_manager
from leo.leotui.view import TuiView


class Row:
    """One visible outline line."""

    __slots__ = ('depth', 'expanded', 'has_children', 'p')

    def __init__(self, p: Any, depth: int, has_children: bool, expanded: bool) -> None:
        self.p = p
        self.depth = depth
        self.has_children = has_children
        self.expanded = expanded

    def render(self, width: int = 80, marker: str = ' ') -> str:
        box = '-' if not self.has_children else ('v' if self.expanded else '>')
        mark = '*' if self.p.isMarked() else ' '
        s = f"{marker}{mark}{'  ' * self.depth}{box} {self.p.h}"
        return s[:width]


class OutlineModel:
    """A terminal view's access to one Outline."""

    def __init__(self, outline: Any, view: TuiView | None = None) -> None:
        self.outline = outline
        self.view = view if view is not None else TuiView(outline)
        self.index = 0
        self.body_scroll = 0
        self.dirty = True
        self.rows: list[Row] = []
        # One outline, one history: leolib creates it on first use and every
        # view of this outline shares it.
        self.undoer = leolib.undoer(outline)
        self.subscribe()

    # --- events -----------------------------------------------------------
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

    def on_model_changed(self, v: Any | None = None, origin: Any | None = None) -> None:
        if origin is not self.view:
            self.dirty = True

    # --- rows -------------------------------------------------------------
    def build_rows(self) -> list[Row]:
        """Walk the outline, honouring *this* view's expansion state."""
        rows: list[Row] = []
        with self.outline.acting_view(self.view):
            p = self.outline.rootPosition()
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

    @property
    def current(self) -> Any:
        if self.dirty:
            self.build_rows()
        if not self.rows:
            return None
        return self.rows[self.index].p

    # --- navigation -------------------------------------------------------
    def move(self, delta: int) -> None:
        if self.dirty:
            self.build_rows()
        if self.rows:
            self.index = max(0, min(self.index + delta, len(self.rows) - 1))
            self.body_scroll = 0
            self.select_current()

    def select_current(self) -> None:
        p = self.current
        if p:
            self.view.setCurrentPosition(p)
            self.view.wrapper.setAllText(p.b)
            self.view.wrapper.setInsertPoint(0)

    def toggle(self) -> None:
        """Expand or contract the current node, in this view only."""
        if self.dirty:
            self.build_rows()
        if not self.rows:
            return
        row = self.rows[self.index]
        if not row.has_children:
            return
        with self.outline.acting_view(self.view):
            if row.expanded:
                row.p.contract()
            else:
                row.p.expand()
        self.dirty = True

    def expand_all_ancestors(self) -> None:
        p = self.current
        if not p:
            return
        with self.outline.acting_view(self.view):
            for ancestor in p.parents():
                ancestor.expand()
        self.dirty = True

    # --- editing ----------------------------------------------------------
    def set_headline(self, text: str) -> None:
        p = self.current
        if not p:
            return
        text = text.replace('\n', '')
        if text == p.h:
            return
        u = self.undoer
        with self.outline.acting_view(self.view):
            bunch = u.beforeChangeHeadline(p)
            p.v.setHeadString(text)
            p.setDirty()
            self.outline.setChanged()
            u.afterChangeHeadline(p, 'Change Headline', bunch)
        self.dirty = True

    def set_body(self, text: str, insert: int = 0) -> None:
        p = self.current
        if not p or text == p.b:
            return
        u, w = self.undoer, self.view.wrapper
        with self.outline.acting_view(self.view):
            # beforeChangeBody reads the *old* caret and text off the buffer,
            # so the buffer has to still hold them.
            w.setAllText(p.b)
            bunch = u.beforeChangeBody(p)
            p.v.setBodyString(text)  # Not p.b: that would redraw.
            w.setAllText(text)
            w.setInsertPoint(min(insert, len(text)))
            p.setDirty()
            self.outline.setChanged()
            u.afterChangeBody(p, 'Change Body', bunch)
        self.dirty = True

    def toggle_mark(self) -> None:
        p = self.current
        if not p:
            return
        u = self.undoer
        command = 'Unmark' if p.isMarked() else 'Mark'
        with self.outline.acting_view(self.view):
            bunch = u.beforeMark(p, command)
            if p.isMarked():
                p.v.clearMarked()
            else:
                p.v.setMarked()
            self.outline.setChanged()
            u.afterMark(p, command, bunch)
        self.dirty = True

    # --- undo -------------------------------------------------------------
    def undo(self) -> bool:
        """Undo the last change. False when there is nothing to undo."""
        return self._replay('undo')

    def redo(self) -> bool:
        """Redo the last undone change. False when there is nothing to redo."""
        return self._replay('redo')

    def _replay(self, which: str) -> bool:
        u = self.undoer
        if not (u.canUndo() if which == 'undo' else u.canRedo()):
            return False
        with self.outline.acting_view(self.view):
            getattr(u, which)()
        self.dirty = True
        self.build_rows()
        target = self.view.p
        for i, row in enumerate(self.rows):
            if row.p == target:
                self.index = i
                break
        self.select_current()
        return True

    # --- structure --------------------------------------------------------
    # Built from the Position primitives in leoNodes rather than from Leo's
    # commands. See this module's docstring.
    def _after_change(self, p: Any) -> None:
        p.setDirty()
        self.outline.setChanged()
        self.view.setCurrentPosition(p)
        self.dirty = True
        self.build_rows()
        for i, row in enumerate(self.rows):
            if row.p == p:
                self.index = i
                break

    def insert_node(self) -> Any:
        u = self.undoer
        with self.outline.acting_view(self.view):
            p = self.current or self.outline.rootPosition()
            bunch = u.beforeInsertNode(p)
            new = p.insertAfter()
            new.h = 'newHeadline'
            self._after_change(new)
            u.afterInsertNode(new, 'Insert Node', bunch)
        return new

    def delete_node(self) -> None:
        u = self.undoer
        with self.outline.acting_view(self.view):
            p = self.current
            if not p:
                return
            if not p.back() and not p.next() and not p.parent():
                return  # Never delete the last top-level node.
            target = p.next() or p.back() or p.parent()
            bunch = u.beforeDeleteNode(p)
            p.setDirty()
            p.doDelete(target)
            self._after_change(target)
            u.afterDeleteNode(target, 'Delete Node', bunch)

    def move_up(self) -> None:
        with self.outline.acting_view(self.view):
            p = self.current
            back = p.back() if p else None
            if not back:
                return
            back2, parent = back.back(), p.parent()
            bunch = self.undoer.beforeMoveNode(p)
            if back2:
                p.moveAfter(back2)
            elif parent:
                p.moveToNthChildOf(parent, 0)
            else:
                p.moveToRoot()
            self._after_move(p, 'Move Up', bunch)

    def move_down(self) -> None:
        with self.outline.acting_view(self.view):
            p = self.current
            nxt = p.next() if p else None
            if not nxt:
                return
            bunch = self.undoer.beforeMoveNode(p)
            p.moveAfter(nxt)
            self._after_move(p, 'Move Down', bunch)

    def move_left(self) -> None:
        """Make the node a sibling of its parent, just after it."""
        with self.outline.acting_view(self.view):
            p = self.current
            parent = p.parent() if p else None
            if not parent:
                return
            bunch = self.undoer.beforeMoveNode(p)
            p.moveAfter(parent)
            self._after_move(p, 'Move Left', bunch)

    def move_right(self) -> None:
        """Make the node the last child of its previous sibling."""
        with self.outline.acting_view(self.view):
            p = self.current
            back = p.back() if p else None
            if not back:
                return
            bunch = self.undoer.beforeMoveNode(p)
            p.moveToLastChildOf(back)
            back.expand()
            self._after_move(p, 'Move Right', bunch)

    def _after_move(self, p: Any, command: str, bunch: Any) -> None:
        self._after_change(p)
        self.undoer.afterMoveNode(p, command, bunch)

    # --- files ------------------------------------------------------------
    def save(self) -> bool:
        """Write the .leo file. False when the outline has no file name."""
        from leo import leolib

        if not self.outline.fileName():
            return False
        with self.outline.acting_view(self.view):
            leolib.save(self.outline)
        return True

    def write_external_files(self) -> int:
        """Tangle every @<file> tree back to disk. Returns files rewritten."""
        from leo import leolib

        with self.outline.acting_view(self.view):
            return leolib.write_external_files(self.outline)

    # --- display ----------------------------------------------------------
    def body_lines(self) -> list[str]:
        p = self.current
        return p.b.split('\n') if p else []

    def status(self) -> str:
        p = self.current
        name = self.outline.shortFileName() or '<unnamed>'
        changed = '*' if self.outline.changed else ' '
        n = len(self.rows)
        where = f"{self.index + 1}/{n}" if n else '0/0'
        gnx = p.gnx if p else ''
        return f"{changed}{name}  {where}  views:{len(self.outline.views)}  {gnx}"
