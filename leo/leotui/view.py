"""
The view half of the terminal front end.

`leolib.open_outline` returns an Outline with no view at all. Everything that
is a fact about a *window* rather than about the document -- which nodes are
folded, where the cursor is, what the body buffer holds -- has to come from
somewhere, and this is that somewhere.

TuiView is not a commander. It is the set of members the model actually asks a
view for, listed in one place so the size of that protocol is measured rather
than guessed. Adding a member here means the model reached for something new;
the list should only ever get shorter. See LEO_REFACTOR.md and TODO.md.

What is *not* here is the measurement that matters. There are no settings, no
document cache and no window geometry, because Outline.ask_view lets a view
decline to answer and falls back to what the document already knows. A terminal
answers the questions a terminal can answer.
"""

from __future__ import annotations
from typing import Any, TYPE_CHECKING, cast

from leo.core.leoOutline import ViewState

if TYPE_CHECKING:  # pragma: no cover
    from leo.core.leoCommands import Commands as Cmdr


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
        pass  # The terminal recomputes its scroll on every frame.

    def getYScrollPosition(self) -> int:
        return self.y

    def setYScrollPosition(self, y: int) -> None:
        self.y = y


class _Body:
    """What Leo calls a frame's body: only a buffer, here."""

    def __init__(self, wrapper: Buffer) -> None:
        self.wrapper = wrapper


class Frame:
    """
    What Leo calls a frame -- for a terminal, just somewhere to hang the buffer.

    Undo reads the caret, selection and scroll position from
    `c.frame.body.wrapper`, so a view that wants undo must expose one.
    Deliberately nothing else: no geometry, no menu bar, no tree, so that the
    model's other frame reaches decline rather than receive a made-up answer.
    `fc.putGlobals` and `u.setUndoType` both test for what they need.
    """

    def __init__(self, wrapper: Buffer) -> None:
        self.body = _Body(wrapper)


class TuiView:
    """
    One terminal window onto an Outline.

    Attach with TuiView(outline); the outline's `views` list is what makes
    per-view folding and `outline.c` work. Every member below exists because
    the model asks for it and a terminal can answer it.
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
    # A terminal repaints the whole screen on every keystroke, so a deferred
    # redraw is only a flag the model can set and clear.
    def redraw_later(self) -> None:
        self.requestLaterRedraw = True

    def outerUpdate(self) -> None:
        self.requestLaterRedraw = False

    # --- view jobs undo asks for ------------------------------------------
    # Each of these is real work in a Qt window and no work at all here. They
    # are no-ops because a terminal has nothing to do, not because they are
    # unimplemented: the screen is redrawn wholesale on the next keystroke,
    # there is no colourizer, and nothing can take focus.
    def recolor(self, p: Any = None) -> None:
        pass

    def bodyWantsFocus(self) -> None:
        pass

    def bodyWantsFocusNow(self) -> None:
        pass

    def on_model_head_changed(self, v: Any = None, origin: Any = None) -> None:
        pass  # The model rebuilds its rows; see leo/leotui/model.py.

    def editHeadline(self) -> None:
        pass  # The terminal runs its own one-line editor.
