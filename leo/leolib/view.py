# @+leo-ver=5-thin
# @+node:sa.20260911120000.10: * @file ../leolib/view.py
"""
leolib's minimal view: what the model asks of a view, and nothing more.

`leolib.open_outline` returns an Outline with no view at all. Facts about a
*window* rather than the document -- which nodes are folded, where the cursor
is, what the body buffer holds -- have to come from somewhere, and View is
that somewhere. Undo needs one, because it restores the caret into the view
that acted.

View is not a commander. Its members are the ones the model actually asks
for, so adding one means the model reached for something new. Outline.ask_view
lets a view decline anything else, so there are no settings, no document cache
and no window geometry here. leo/leotui uses it as its view.
"""

from __future__ import annotations
from typing import Any, TYPE_CHECKING, cast

from leo.core.leoOutline import ViewState

if TYPE_CHECKING:  # pragma: no cover
    from leo.core.leoCommands import Commands as Cmdr


# @+others
# @+node:sa.20260911120000.11: ** class Buffer
class Buffer:
    """
    The view's text buffer.

    A view is entitled to a text buffer -- Leo's undoer reads the caret,
    selection and scroll position from one -- so this is not a coupling to be
    removed. It implements only what the body editor reads.
    """

    def __init__(self) -> None:
        self.s = ''
        self.ins = 0
        self.sel: tuple[int, int] = (0, 0)
        self.y = 0

    def getAllText(self) -> str:
        return self.s

    def setAllText(self, s: str) -> None:
        self.s = s

    def getInsertPoint(self) -> int:
        return self.ins

    def setInsertPoint(self, i: int, s: str | None = None) -> None:
        self.ins = max(0, min(i, len(self.s)))

    def getSelectionRange(self, sort: bool = True) -> tuple[int, int]:
        return self.sel

    def setSelectionRange(self, i: int, j: int, insert: int | None = None) -> None:
        self.sel = (i, j)

    def seeInsertPoint(self) -> None:
        pass  # Nothing is displayed, so there is nothing to scroll.

    def getYScrollPosition(self) -> int:
        return self.y

    def setYScrollPosition(self, y: int) -> None:
        self.y = y


# @+node:sa.20260911120000.12: ** class _Body
class _Body:
    """What Leo calls a frame's body: only a buffer, here."""

    def __init__(self, wrapper: Buffer) -> None:
        self.wrapper = wrapper


# @+node:sa.20260911120000.13: ** class Frame
class Frame:
    """
    What Leo calls a frame -- here, just somewhere to hang the buffer.

    Undo reads the caret, selection and scroll position from
    `c.frame.body.wrapper`, so a view that wants undo must expose one.
    Deliberately nothing else: no geometry, no menu bar, no tree, so that the
    model's other frame reaches decline rather than receive a made-up answer.
    `fc.putGlobals` and `u.setUndoType` both test for what they need.
    """

    def __init__(self, wrapper: Buffer) -> None:
        self.body = _Body(wrapper)


# @+node:sa.20260911120000.14: ** class View
class View:
    """
    One view onto an Outline.

    Attach with View(outline); the outline's `views` list is what makes
    per-view folding and `outline.c` work. Every member below exists because
    the model asks for it.
    """

    def __init__(self, outline: Any) -> None:
        self.outline = outline
        self.wrapper = Buffer()
        self.frame = Frame(self.wrapper)
        # ViewState and outline.views are annotated Cmdr because Leo's own
        # views are commanders. The contract they actually rely on is the one
        # below, not the class; widening the annotation cascades through core,
        # which outline.c already declined to do.
        self.view_state = ViewState(cast('Cmdr', self))
        self.exists = True
        self.requestLaterRedraw = False
        self._p = outline.rootPosition()
        outline.add_view(self)

    # --- the current position -------------------------------------------
    @property
    def p(self) -> Any:
        return self._p

    def setCurrentPosition(self, p: Any) -> None:
        self._p = p.copy() if p else p

    def selectPosition(self, p: Any) -> None:
        self.setCurrentPosition(p)

    def rootPosition(self) -> Any:
        return self.outline.rootPosition()

    def positionExists(self, p: Any, root: Any = None) -> bool:
        return self.outline.positionExists(p, root)

    def shouldBeExpanded(self, p: Any) -> bool:
        # Asked for cloned nodes, whose expansion cannot be read off one VNode.
        return self.view_state.is_expanded(p.gnx)

    # --- redraw -----------------------------------------------------------
    # A deferred redraw is only a flag the model can set and clear; the
    # front end decides when to repaint.
    def redraw_later(self) -> None:
        self.requestLaterRedraw = True

    def outerUpdate(self) -> None:
        self.requestLaterRedraw = False

    # --- view jobs undo asks for ------------------------------------------
    # Each of these is real work in a Qt window and none here: there is no
    # colourizer, nothing can take focus, and no headline widget can go stale.
    def recolor(self, p: Any = None) -> None:
        pass

    def bodyWantsFocus(self) -> None:
        pass

    def bodyWantsFocusNow(self) -> None:
        pass

    def on_model_head_changed(self, v: Any = None, origin: Any = None) -> None:
        pass

    def editHeadline(self) -> None:
        pass


# @-others
# @@language python
# @@tabwidth -4
# @-leo
