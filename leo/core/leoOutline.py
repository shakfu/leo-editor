# @+leo-ver=5-thin
# @+node:sa.20260905130000.1: * @file leoOutline.py
"""
The Outline class: one open Leo document, independent of any view.

Historically Leo's commander (leoCommands.Commands) was both the document and
the window: `Commands.__init__` created the VNode tree and the gui frame three
lines apart, and `VNode.context` pointed at the commander. That made the
document and the view the same object, so an outline could have exactly one
view.

An Outline owns the state that belongs to the *document*: the hidden root
VNode, the file commands, the file name, the dirty flag. A commander owns the
state that belongs to a *view*: the current position, the hoist stack, the
chapter, the frame. Several commanders may be attached to one Outline.

`VNode.context` now points at an Outline, never at a commander.

See LEO_REFACTOR.md for the staged plan this belongs to.
"""

# @+<< leoOutline imports and annotations >>
# @+node:sa.20260905130000.2: ** << leoOutline imports and annotations >>
from __future__ import annotations
import os
import re
from typing import Any, TYPE_CHECKING
from leo.core import signal_manager
from leo.core import leoGlobals as g

if TYPE_CHECKING:  # pragma: no cover
    from leo.core.leoCommands import Commands as Cmdr
    from leo.core.leoNodes import Position, VNode
# @-<< leoOutline imports and annotations >>


# @+others
# @+node:sa.20260906130000.1: ** class DefaultConfig
class DefaultConfig:
    """
    The settings an outline has when nobody has configured anything.

    Leo's settings live in .leo files that a *commander* reads, so an Outline
    with no view has none. Every caller in leoAtFile and leoFileCommands
    already passes an explicit `default=`, so answering with the caller's
    default is not a stub: it is exactly what Leo does when a setting is unset.

    Deliberately narrow. A setting this does not know about raises rather than
    guessing, because a wrong default here would show up as a subtly wrong
    external file rather than as an error. That is not hypothetical: this class
    began with new_leo_file_encoding = 'UTF-8' where Leo uses 'utf-8', which
    changed the XML declaration of every file leolib wrote.

    Note that "no settings" is not the same as "Leo's shipped settings".
    leoSettings.leo ships `@int page-width = 80` while the code default is 132,
    so an outline opened by leolib takes 132. Anything whose value can reach an
    external file should be checked against leoSettings.leo before it is
    trusted for writing.
    """

    # @+others
    # @+node:sa.20260906130000.2: *3* default_config: getters
    def getBool(self, setting: str, default: Any = None) -> Any:
        return default

    def getString(self, setting: str, default: Any = None) -> Any:
        return default

    def getInt(self, setting: str, default: Any = None) -> Any:
        return default

    def getFloat(self, setting: str, default: Any = None) -> Any:
        return default

    def getColor(self, setting: str, default: Any = None) -> Any:
        return default

    def getData(self, setting: str, default: Any = None) -> Any:
        return default

    def getDirectory(self, setting: str, default: Any = None) -> Any:
        return default

    # @+node:sa.20260906130000.3: *3* default_config: file-format settings
    # Named attributes the readers and writers use directly, copied verbatim
    # from LocalConfigManager so that a file leolib writes is byte-identical to
    # one Leo writes. 'UTF-8' here instead of 'utf-8' was enough to change the
    # XML declaration of every .leo file leolib saved.
    new_leo_file_encoding = 'utf-8'
    default_derived_file_encoding = 'utf-8'
    default_at_auto_file_encoding = 'utf-8'
    output_newline = 'nl'

    # @-others


# @+node:sa.20260905170000.1: ** class ViewState
class ViewState:
    """
    One view's private outline state, keyed by gnx.

    Which nodes are expanded, and where the caret and scrollbar sat in each
    node's body, are facts about a *window*, not about the document. They lived
    on the VNode until stage 5 of LEO_REFACTOR.md, which meant two views of one
    outline had to share one set of folds and one caret per node.

    Keyed by gnx rather than by VNode so that state survives a reload, and so
    that nothing here keeps a deleted node alive.
    """

    # @+others
    # @+node:sa.20260905170000.2: *3* view_state.__init__
    def __init__(self, c: Cmdr, inherit_from: ViewState = None) -> None:
        self.c = c
        self.expanded: set[str] = set()
        self.expanded_positions: dict[str, list] = {}
        self.insert_spot: dict[str, int] = {}
        self.scroll_spot: dict[str, int] = {}
        self.selection: dict[str, tuple[int, int]] = {}
        if inherit_from is not None:
            # A new view opens looking like the view it was opened from.
            # Starting fully collapsed would be the bigger surprise.
            self.expanded = set(inherit_from.expanded)
            self.expanded_positions = {
                gnx: list(v) for gnx, v in inherit_from.expanded_positions.items()
            }
            self.insert_spot = dict(inherit_from.insert_spot)
            self.scroll_spot = dict(inherit_from.scroll_spot)
            self.selection = dict(inherit_from.selection)

    # @+node:sa.20260905170000.3: *3* view_state.expansion
    def is_expanded(self, gnx: str) -> bool:
        return gnx in self.expanded

    def expand(self, gnx: str) -> None:
        self.expanded.add(gnx)

    def contract(self, gnx: str) -> None:
        self.expanded.discard(gnx)

    # @+node:sa.20260905170300.1: *3* view_state.prune
    def prune(self) -> None:
        """
        Drop remembered Positions that point into deleted subtrees.

        expanded_positions holds Positions, and a Position holds VNodes. This
        state used to live on the VNode and die with it; now that it outlives
        the node, a deleted subtree would be pinned in memory forever.

        Only this dict needs sweeping: it has one entry per expanded node --
        13 for a freshly opened LeoPyRef.leo -- so this is cheap, unlike a walk
        of the whole outline (~9ms for 11k nodes).
        """
        c = self.c
        for gnx, positions in list(self.expanded_positions.items()):
            alive = [p for p in positions if c.positionExists(p)]
            if alive:
                self.expanded_positions[gnx] = alive
            else:
                del self.expanded_positions[gnx]

    # @-others


# @+node:sa.20260905130000.3: ** class Outline
class Outline:
    """One open Leo document. Knows nothing about how it is displayed."""

    # @+others
    # @+node:sa.20260905130000.4: *3* outline.__init__
    def __init__(self, c: Cmdr, fileName: str = '', relativeFileName: str = '') -> None:
        """
        Create an Outline owned by commander c, which becomes its first view.

        The hidden root VNode is created by the commander and assigned to
        self.hiddenRootNode, because creating it here would make leoOutline.py
        import leoNodes.py at module level.
        """
        # The views attached to this outline. views[0] is the primary view.
        # May be empty: an Outline opened by leolib has no view at all until
        # a front end attaches one.
        self.views: list[Cmdr] = [c] if c is not None else []
        self._acting_c: Cmdr | None = None  # See self.acting_view.
        self._batch_depth = 0  # See self.batch_events.
        self._pending: set[str] = set()
        self.structure_dirty = False  # Set by 'structure_changed', read by c.doCommand.
        # Bumped by the low-level VNode link methods on every structural
        # change. It used to be c.frame.tree.generation -- the model reaching
        # into a widget to bump a counter that nothing ever read. Counting
        # changes to the tree is the document's job; a view that wants to know
        # whether the outline moved under it can compare this against its own
        # last-seen value.
        self.generation = 0
        self.scanAtPathDirectivesCount = 0  # An important statistic.
        self._default_config: Any = None  # See outline.config.
        # What the last read of this document's external files skipped or
        # could not place. Facts about the files, not about a window; a front
        # end turns them into dialogs, and leolib just reads them.
        self.ignored_at_file_nodes: list[str] = []
        self.orphan_at_file_nodes: list[str] = []

        # Model state owned by the document.
        self.hiddenRootNode: VNode = None  # Set by Commands.initObjects.
        # One outline, one undo history. Set by Commands.initObjects; shared by
        # every view. See "Undo across views" in LEO_REFACTOR.md.
        self.undoer: Any = None
        self.mFileName: str = fileName or ''
        self.mRelativeFileName: str = relativeFileName or ''
        self.changed = False  # True: the outline has changed since the last save.

        # #4875: In-memory, session-scoped cache of @clean nodes' last-seen file
        # mod times, keyed by gnx. Never serialized.
        self.mod_time_cache: dict[str, float] = {}

        # Reading and writing the .leo file. Owned here, not on a commander:
        # the gnx index is one per document, never one per window.
        self._fileCommands: Any = None
        self._atFileCommands: Any = None
        self._shadowController: Any = None
        self._persistenceController: Any = None
        self._importCommands: Any = None

        # Stands in for c.db while this outline has no view. leolib opens
        # outlines with no window and therefore no commander cache.
        self._viewless_db: dict[str, Any] = {}

        # The window size and pane ratios the .leo file recorded. The reader
        # used to push these straight into c.frame, which meant reading a file
        # required a window. It is data now; a front end applies it if it wants
        # to, and a headless reader ignores it.
        self.window_geometry: dict[str, Any] = {}

        # The per-view caches the file records, kept here until a view claims
        # them: an outline opened with no view still has to round-trip them.
        self.expanded_gnxs: list[str] = []
        self.marked_gnxs: list[str] = []

    # @+node:sa.20260905130000.5: *3* outline.__repr__
    def __repr__(self) -> str:
        return f"<Outline {self.mFileName or '<unnamed>'} views:{len(self.views)}>"

    __str__ = __repr__

    # @+node:sa.20260905130000.6: *3* outline.views
    def add_view(self, c: Cmdr) -> None:
        """Attach commander c to this outline."""
        if c not in self.views:
            self.views.append(c)

    def remove_view(self, c: Cmdr) -> None:
        """Detach commander c. The outline itself survives its last view."""
        if c in self.views:
            self.views.remove(c)

    # @+node:sa.20260905180000.1: *3* outline.events
    # The document's event bus. Views subscribe with
    # signal_manager.connect(outline, signal, listener); the model never calls
    # a view directly. Listeners are called as listener(v, origin=c), where
    # origin is the view whose command caused the change, or None for a script.
    # A view ignores its own events by testing `origin is self.c`.

    #     body_changed       v      a node's body text changed
    #     head_changed       v      a node's headline changed
    #     structure_changed  v      children of v were inserted, deleted or moved
    #     status_changed     v      a dirty or marked bit changed
    #     bulk_changed       None   many nodes changed at once (see batch_events)

    def emit(self, signal: str, v: VNode = None) -> None:
        """Tell every listener about a change to this document."""
        if signal == 'structure_changed':
            # Checked once per command by c.doCommand, not once per link.
            self.structure_dirty = True
        if self._batch_depth:
            self._pending.add(signal)
            return
        signal_manager.emit(self, signal, v, origin=self._acting_c)

    def batch_events(self) -> Any:
        """
        A context manager that coalesces events during a bulk operation.

        Reading a 10,000-node file must not emit 10,000 events. Inside the
        block nothing is delivered; on exit a single `bulk_changed` stands in
        for whatever happened, and listeners refresh wholesale.
        """
        outline = self

        class _Batch:
            def __enter__(self_) -> None:
                outline._batch_depth += 1

            def __exit__(self_, *args: object) -> None:
                outline._batch_depth -= 1
                if outline._batch_depth == 0 and outline._pending:
                    outline._pending.clear()
                    signal_manager.emit(outline, 'bulk_changed', None, origin=outline._acting_c)

        return _Batch()

    # @+node:sa.20260905190000.1: *3* outline.subscribe_view
    def subscribe_view(self, c: Cmdr) -> None:
        """
        Make view c follow this document.

        Until stage 6 the body widget was authoritative between selection
        changes, so a change made anywhere else -- another window, a script --
        was invisible until the view happened to reselect the node. Now the
        model tells every view, and each view repaints itself.

        A view ignores its own events: it made the change, its widget is
        already right, and repainting would move the user's caret mid-keystroke.
        """
        signal_manager.connect(self, 'body_changed', c.on_model_body_changed)
        # Not 'status_changed': a dirty or marked bit only changes a node's
        # icon, and v.updateIcon already pokes every tree. Redrawing for it
        # would be wasteful, and a redraw resets the body caret.
        # A headline widget needs more than a redraw: it is what
        # LeoTree.onHeadChanged commits, so it must track the model even in the
        # view that made the change. See c.on_model_head_changed.
        signal_manager.connect(self, 'head_changed', c.on_model_head_changed)
        signal_manager.connect(self, 'structure_changed', c.on_model_outline_changed)
        signal_manager.connect(self, 'bulk_changed', c.on_model_bulk_changed)

    # @+node:sa.20260905200000.1: *3* outline.update_other_views
    def update_other_views(self, acting_c: Cmdr = None) -> None:
        """
        Flush pending redraws in every view except the one that just acted.

        c.redraw_later only sets a flag; the flag is drained by that view's own
        c.outerUpdate, which runs when its user does something. For the window
        that made the change that is fine, but a *passive* window would sit
        showing stale content until it was clicked. Measured: Qt's event loop
        does not drain it -- processEvents leaves the flag set.

        Safe at this point: outerUpdate only moves focus when the view asked
        for it, and a passive view has not.
        """
        for c in self.views:
            if c is not acting_c and c.exists and c.requestLaterRedraw:
                c.outerUpdate()

    # @+node:sa.20260905160100.1: *3* outline.revalidate_views
    def revalidate_views(self, acting_c: Cmdr = None) -> None:
        """
        Make sure every view's current position still exists, after a change.

        A structural change made through one view -- an undo, most dangerously --
        can delete the node another view is sitting on, leaving that view with a
        Position into a subtree that is gone. Fall back to the nearest surviving
        ancestor, else to the root.

        Views other than acting_c are also asked to redraw: the change happened
        in someone else's window, so nothing else would prompt them.

        Called once per command that changed the outline's shape, and after
        every undo and redo. Deliberately *not* a listener for
        'structure_changed': that fires on each individual link and unlink, so
        subscribing would run this O(views) sweep hundreds of times during a
        single paste.
        """
        self.structure_dirty = False
        from leo.core.leoNodes import Position

        for c in self.views:
            c.view_state.prune()
            p = c.p
            if p and c.positionExists(p):
                if c is not acting_c:
                    c.redraw_later()  # The outline changed under this view.
                continue
            found = None
            stack = list(p.stack) if p else []
            while stack:
                v, childIndex = stack.pop()  # Nearest ancestor first.
                candidate = Position(v, childIndex, list(stack))
                if c.positionExists(candidate):
                    found = candidate
                    break
            if not found:
                found = c.rootPosition()
            if found:
                c.setCurrentPosition(found)
                # Do not redraw from inside the change: ask for one afterwards.
                c.redraw_later()
        self.update_other_views(acting_c=acting_c)

    # @+node:sa.20260905160200.1: *3* outline.c
    @property
    def c(self) -> Cmdr:
        """
        The view to act on: the one whose command is running, else the primary.

        Call sites that need a *commander* rather than a document use this, and
        `.context.c` is therefore the grep that lists the coupling still to be
        removed. Prefer self.views when an operation should reach every view.
        """
        if self._acting_c is not None:
            return self._acting_c
        return self.views[0] if self.views else None

    def acting_view(self, c: Cmdr) -> Any:
        """
        A context manager naming the view whose command is running.

        Set by c.doCommand around every command. It decides which window undo
        restores the caret into, and which view's expansion state `p.expand()`
        changes -- neither of which the model itself can know.
        """
        outline = self

        class _ActingView:
            def __enter__(self_) -> None:
                self_.saved = outline._acting_c
                outline._acting_c = c

            def __exit__(self_, *args: object) -> None:
                outline._acting_c = self_.saved

        return _ActingView()

    # @+node:sa.20260905250002.1: *3* outline: owned by the document
    # These used to forward to the primary view. They are here because they
    # need nothing but state this object already owns -- the hidden root and
    # the file name -- so the commander now forwards to *them*, which is the
    # direction the coupling is meant to run.

    def positionExists(
        self, p: Position | None, root: Position | None = None, trace: bool = False
    ) -> bool:
        """Return True if position p exists in this outline."""
        if not p or not p.v:
            return False
        rstack = root.stack + [(root.v, root._childIndex)] if root else []
        pstack = p.stack + [(p.v, p._childIndex)]
        if len(rstack) > len(pstack):
            return False
        par = self.hiddenRootNode
        for j, x in enumerate(pstack):
            if j < len(rstack) and x != rstack[j]:
                return False
            v, i = x
            if i >= len(par.children) or v is not par.children[i]:
                return False
            par = v
        return True

    def shortFileName(self) -> str:
        return g.shortFileName(self.mFileName)

    def rootPosition(self) -> Position:
        """Return a new copy of this outline's root position."""
        # Imported here, not at module level: leoNodes imports leoGlobals only,
        # but keeping leoOutline free of an eager leoNodes import preserves the
        # option of a model package that does not depend on this file.
        from leo.core.leoNodes import Position
        children = self.hiddenRootNode.children if self.hiddenRootNode else []
        v = children[0] if children else None
        return Position(v=v, childIndex=0, stack=None)

    def all_unique_positions(self, copy: bool = True) -> Any:
        """Yield the first position of every vnode, in outline order."""
        p = self.rootPosition()
        seen = set()
        while p:
            if p.v in seen:
                p.moveToNodeAfterTree()
            else:
                seen.add(p.v)
                yield p.copy() if copy else p
                p.moveToThreadNext()

    def all_unique_nodes(self) -> Any:
        """Yield every vnode of this outline."""
        for p in self.all_unique_positions(copy=False):
            yield p.v

    def clearAllVisited(self) -> None:
        """Clear the visited and write bits on every node."""
        for v in self.all_unique_nodes():
            v.clearVisited()
            v.clearWriteBit()

    @property
    def fileCommands(self) -> Any:
        """
        This document's .leo reader/writer, created on demand.

        Owned here rather than on a commander because the gnx index it carries
        is the document's: two views of one outline must never disagree about
        which VNode a gnx names.
        """
        if self._fileCommands is None:
            from leo.core import leoFileCommands
            self._fileCommands = leoFileCommands.FileCommands(self)
        return self._fileCommands

    @fileCommands.setter
    def fileCommands(self, fc: Any) -> None:
        self._fileCommands = fc

    @property
    def db(self) -> Any:
        """
        This document's cache.

        Already per-document in substance -- leoCache keys every entry by
        c.mFileName, so two views of one outline read and write the same rows --
        but it was only reachable through a commander, which made "which window
        ran the save" look like it might matter. It does not, and an outline
        with no view at all still needs somewhere to put these.
        """
        primary = self.views[0] if self.views else None
        if primary is None:
            return self._viewless_db
        return primary.db

    # @+node:sa.20260906120000.1: *3* outline: paths
    # Where a node's external file lives is a fact about the *document*: it
    # falls out of the @path directives in the tree and the directory the .leo
    # file sits in, and every view of an outline must agree about it. It lived
    # on Commands, which is why a script holding only a VNode -- whose .context
    # is an Outline -- could not ask for it. See LEO_REFACTOR.md.

    # Use a regex to avoid allocating temp strings.
    # https://en.wikipedia.org/wiki/Filename
    at_path_pattern = re.compile(r'^@path\s+(.+)$', re.MULTILINE)

    def getPathFromNode(self, p: Position) -> str | None:
        """Scan p.h then p.b for @path directives."""
        self.scanAtPathDirectivesCount += 1  # An important statistic.

        def get_path(m: re.Match) -> str | None:
            return g.stripPathCruft(m.group(1)) if m else None

        # The headline has higher precedence because it is more visible.
        paths: list[str] = []
        for kind, s in (('head', p.h), ('body', p.b)):
            for m in self.at_path_pattern.finditer(s):
                if kind == 'body' and p.isAtFileNode():
                    message = '@path is not allowed in the body text of @file nodes\n'
                    g.print_unique_message(message)
                elif path := get_path(m):
                    paths.append(path)
            if paths:
                break
        if len(paths) > 1:
            message = (
                f"Multiple @path directives in {p.h!r}\n"
                f"Using the first path: @path {paths[0]}"
            )  # fmt: skip
            g.print_unique_message(message)
        return paths[0] if paths else None

    def getPath(self, p: Position) -> str:
        """
        Scan for @path directives in p and all its direct ancestors.

        Return an absolute path or a reasonable default.
        """
        paths = []
        for p2 in p.self_and_parents():
            if path := self.getPathFromNode(p2):
                paths.append(path)
        # Add absbase and reverse the list.
        absbase = g.os_path_dirname(self.fileName()) if self.fileName() else g.app.homeDir
        paths.append(absbase)
        paths.reverse()
        # Compute the full, effective, absolute path.
        return g.finalize_join(*paths)

    def fullPath(self, p: Position) -> str:
        """
        Return the absolute path in effect at p.

        Return the path to an external file if p is an @<file> node.
        Otherwise return the path to the enclosing directory.
        """
        return g.finalize_join(self.getPath(p), p.anyAtFileNodeName())

    def setFileTimeStamp(self, fn: str) -> None:
        """Update the recorded modification time for the external file fn."""
        # Never used a commander: the external-files controller is a global.
        efc = getattr(g.app, 'externalFilesController', None)
        if efc:
            efc.set_time(fn)

    def relativeDirectory(self, path: str) -> str:
        """Return the path relative to this outline, or the full, absolute path."""
        return g.relativeDirectory(os.path.dirname(self.fileName()), path)

    # @+node:sa.20260906160001.1: *3* outline: directive scanners
    # Scanning the tree for the @language, @comment, @encoding, @tabwidth,
    # pagewidth, wrap and lineending directives. These read directives out
    # of headlines
    # and body text and fall back to the outline's settings, so the answer is a
    # property of the *document*: two windows on one outline must not disagree
    # about what language a node is written in. `c = self` below is an Outline,
    # and every c.<name> it uses is one this class provides.

    # @+node:ekr.20250405040620.1: *3* outline.getDelims
    # Use a regex to avoid allocating temp strings.
    at_comment_pattern = re.compile(r'^@comment\s+(.*)$', re.MULTILINE)

    def getDelims(self, p: Position) -> tuple[str, str, str]:
        c = self
        # The headline has higher precedence because it is more visible.
        for p2 in p.self_and_parents():
            for s in (p2.h, p2.b):
                for m in c.at_comment_pattern.finditer(s):
                    comment = m.group(1)
                    return g.set_delims_from_string(comment)

        # Return the default comment delims.
        default_language = c.getLanguage(p) or c.target_language or 'python'
        return g.set_delims_from_language(default_language)

    # @+node:ekr.20250404072805.1: *3* outline.getEncoding
    # Use a regex to avoid allocating temp strings.
    at_encoding_pattern = re.compile(r'^@encoding\s+([\w_-]+)', re.MULTILINE)

    def getEncoding(self, p: Position) -> str:
        """
        Scan p and all ancestors for the first @encoding direcive.

        Return c.config.default_derived_file_encoding or 'utf-8' by default.
        """
        c = self
        # The headline has higher precedence because it is more visible.
        for p2 in p.self_and_parents():
            for s in (p2.h, p2.b):
                for m in c.at_encoding_pattern.finditer(s):
                    encoding = m.group(1)
                    if g.isValidEncoding(encoding):
                        return encoding
                    g.error("invalid @encoding:", encoding)
        return c.config.default_derived_file_encoding or 'utf-8'

    # @+node:ekr.20250405141653.1: *3* outline.getLanguage
    def getLanguage(self, p: Position) -> str:
        """
        Return the language in effect at node p, checking that the language is valid."""
        v0 = p.v
        assert v0
        assert p.v
        seen: set[VNode]

        # The same generator as in v.setAllAncestorAtFileNodesDirty.
        # Original idea by Виталије Милошевић (Vitalije Milosevic).
        # Modified by EKR.

        def v_and_parents(v: VNode) -> VNodeGenerator:
            if v in seen:
                return
            seen.add(v)
            yield v
            for parent_v in v.parents:
                if parent_v not in seen:
                    yield from v_and_parents(parent_v)

        # First, see if p contains any @language directive.
        if language := g.findFirstValidAtLanguageDirective(p.b):
            return language

        # Passes 1 and 2: Search body text for unambiguous @language directives.

        # Pass 1: Search body text in direct parents for unambiguous @language directives.
        for p2 in p.self_and_parents(copy=False):
            languages = g.findAllValidLanguageDirectives(p2.v.b)
            if len(languages) == 1:  # An unambiguous language
                return languages[0]

        # Pass 2: Search body text in extended parents for unambiguous @language directives.
        seen = set([v0.context.hiddenRootNode])
        for v in v_and_parents(v0):
            languages = g.findAllValidLanguageDirectives(v.b)
            if len(languages) == 1:  # An unambiguous language
                return languages[0]

        # Passes 3 & 4: Use the file extension in @<file> nodes.

        def get_language_from_headline(v: VNode) -> str:
            """Return the extension for @<file> nodes."""
            if v.isAnyAtFileNode():
                name = v.anyAtFileNodeName()
                _, ext = g.os_path_splitext(name)
                ext = ext[1:]  # strip the leading period.
                language = g.app.extension_dict.get(ext, '')
                if g.isValidLanguage(language):
                    return language
            return ''

        # Pass 3: Use file extension in headline of @<file> in direct parents.
        for p2 in p.self_and_parents(copy=False):
            if language := get_language_from_headline(p2.v):
                return language

        # Pass 4: Use file extension in headline of @<file> nodes in extended parents.
        seen = set([v0.context.hiddenRootNode])
        for v in v_and_parents(v0):
            assert v
            if language := get_language_from_headline(v):
                return language

        # Return the default language for the commander.
        c = p.v.context
        return c.target_language or 'python'

    # @+node:ekr.20250405053842.1: *3* outline.getLineEnding
    # Use a regex to avoid allocating temp strings.
    at_lineending_pattern = re.compile(r'^@lineending\s+([\w]+)', re.MULTILINE)

    def getLineEnding(self, p: Position) -> str:
        """
        Scan p and all ancestors for the first @lineending direcive.
        Return None (*not* '\n') by default.
        """
        c = self
        # The headline has higher precedence because it is more visible.
        for p2 in p.self_and_parents():
            for s in (p2.h, p2.b):
                for m in c.at_lineending_pattern.finditer(s):
                    ending = m.group(1)
                    if ending in ("cr", "crlf", "lf", "nl", "platform"):
                        return g.getOutputNewline(name=ending)
        return ''

    # @+node:ekr.20250404153234.1: *3* outline.getPageWidth
    # Use a regex to avoid allocating temp strings.
    at_pagewidth_pattern = re.compile(r'^@pagewidth\s+(-?[0-9]+)', re.MULTILINE)

    def getPageWidth(self, p: Position) -> int:
        """
        Scan p.b and all ancestors for the first @pagewith direcive.

        Return c.page_width by default.
        """
        c = self
        # The headline has higher precedence because it is more visible.
        for p2 in p.self_and_parents():
            for s in (p2.h, p2.b):
                for m in c.at_pagewidth_pattern.finditer(s):
                    width = m.group(1)
                    try:
                        return int(width)
                    except ValueError:
                        g.error("ignoring m.group(0)")
        return c.page_width

    # @+node:ekr.20250404153250.1: *3* outline.getTabWidth
    # Use a regex to avoid allocating temp strings.
    at_tabwidth_pattern = re.compile(r'^@tabwidth\s+(-?[0-9]+)', re.MULTILINE)

    def getTabWidth(self, p: Position) -> int:
        """
        Scan p.b and all ancestors for the first @encoding direcive.

        Return c.tab_width by default.
        """
        c = self
        # The headline has higher precedence because it is more visible.
        for p2 in p.self_and_parents():
            for s in (p2.h, p2.b):
                for m in c.at_tabwidth_pattern.finditer(s):
                    width = m.group(1)
                    try:
                        return int(width)
                    except ValueError:
                        g.error("ignoring m.group(0)")
        return c.tab_width

    # @+node:ekr.20250405143421.1: *3* outline.getWrap
    # Use a regex to avoid allocating temp strings.
    at_wrap_pattern = re.compile(r'^@wrap', re.MULTILINE)
    at_nowrap_pattern = re.compile(r'^@nowrap', re.MULTILINE)

    def getWrap(self, p: Position) -> int:
        """
        Scan p.b and all ancestors for @wrap and @nowrap directives.
        Return @bool body-pane-wraps by default.
        """
        c = self
        # The headline has higher precedence because it is more visible.
        for p2 in p.self_and_parents():
            for s in (p2.h, p2.b):
                if c.at_wrap_pattern.search(s) is not None:
                    return True
                if c.at_nowrap_pattern.search(s) is not None:
                    return False
        return c.config.getBool("body-pane-wraps")

    # @+node:sa.20260906120001.1: *3* outline.gnx_kind
    @property
    def gnx_kind(self) -> str:
        """
        How this document allocates gnxs: 'none' (legacy), 'uuid' or 'ksuid'.

        A document-level fact -- every view of an outline must mint gnxs the
        same way -- so it is answered here rather than read out of a commander's
        settings by the allocator. Defaults to legacy when there are no
        settings to consult, which is the case for an outline leolib opened.
        """
        return (self.config.getString('gnx-kind') or 'none').lower()

    @property
    def atFileCommands(self) -> Any:
        """This document's external-file reader/writer, created on demand."""
        if self._atFileCommands is None:
            from leo.core import leoAtFile
            self._atFileCommands = leoAtFile.AtFile(self)
        return self._atFileCommands

    @atFileCommands.setter
    def atFileCommands(self, at: Any) -> None:
        self._atFileCommands = at

    @property
    def shadowController(self) -> Any:
        """This document's @shadow machinery, created on demand."""
        if self._shadowController is None:
            from leo.core import leoShadow
            self._shadowController = leoShadow.ShadowController(self)
        return self._shadowController

    @shadowController.setter
    def shadowController(self, x: Any) -> None:
        self._shadowController = x

    @property
    def persistenceController(self) -> Any:
        """This document's @persistence machinery, created on demand."""
        if self._persistenceController is None:
            from leo.core import leoPersistence
            self._persistenceController = leoPersistence.PersistenceDataController(self)
        return self._persistenceController

    @persistenceController.setter
    def persistenceController(self, pc: Any) -> None:
        self._persistenceController = pc

    @property
    def importCommands(self) -> Any:
        """
        This document's importer for @auto trees.

        Unlike the readers above, leoImport still reaches for a window in
        places, so this is a forward while there is a view and a best effort
        without one. Reading an @auto node is the one part of
        leolib.read_external_files that may still fail for that reason; the
        failure is per node and leaves the node as the .leo file described it.
        """
        if self.c is not None:
            return self.c.importCommands
        if self._importCommands is None:
            from leo.core import leoImport
            self._importCommands = leoImport.LeoImportCommands(self)
        return self._importCommands

    @property
    def leo_file_encoding(self) -> str:
        """The encoding for this document's .leo file."""
        return self.config.new_leo_file_encoding

    def setHeadString(self, p: Position, s: str) -> None:
        """Set p's headline. Every view follows the head_changed event."""
        p.initHeadString(s)
        p.setDirty()

    def setBodyString(self, p: Position, s: str) -> None:
        """
        Set p's body text.

        With a view attached this goes through the commander, which also
        repaints the widget the user is looking at -- the acting view suppresses
        its own body_changed event, so nothing else would. With no view at all
        the model half is the whole job.
        """
        if self.c is not None:
            self.c.setBodyString(p, s)
            return
        self.set_body_in_model(p, s)

    def set_body_in_model(self, p: Position, s: str) -> None:
        """
        The model half of setBodyString: no widget, no view.

        Called by c.setBodyString after it has updated its own widget, and
        directly when this outline has no view.
        """
        v = p.v
        if not v:
            return
        s = g.toUnicode(s)
        if v.b == s:
            return
        v.setBodyString(s)
        v.setSelection(0, 0)
        p.setDirty()
        if not self.changed:
            self.setChanged()

    # @+node:sa.20260905130000.7: *3* outline: forwarded to the primary view
    # Everything below still lives on the commander. Each one is a call site
    # that stages 4-6 of LEO_REFACTOR.md move to the document or to the views;
    # until then it resolves against the primary view, which is what the code
    # did before the Outline existed. This list *is* the remaining coupling:
    # it should only ever get shorter.

    # Model operations that happen to live on Commands (harmless to forward:
    # they read the shared VNode tree and give the same answer for any view).

    def createNodeHierarchy(
        self, heads: list, parent: Position = None, forcecreate: bool = False
    ) -> Position:
        return self.c.createNodeHierarchy(heads, parent=parent, forcecreate=forcecreate)

    def fileName(self) -> str:
        # Owned outright: the document knows its own name.
        return self.mFileName

    @property
    def config(self) -> Any:
        """This document's settings, or Leo's defaults when it has no view."""
        if self.c is not None:
            return self.c.config
        if self._default_config is None:
            self._default_config = DefaultConfig()
        return self._default_config

    @property
    def target_language(self) -> str:
        if self.c is None:
            return self.config.getString('target-language') or 'python'
        return self.c.target_language

    @property
    def tab_width(self) -> int:
        """The document's default tab width, from its settings."""
        if self.c is None:
            return self.config.getInt('tab-width') or -4
        return self.c.tab_width

    @property
    def page_width(self) -> int:
        """The document's default page width, from its settings."""
        if self.c is None:
            return self.config.getInt('page-width') or 132
        return self.c.page_width

    # View operations. Stage 5 gives each view its own expansion state; stage 6
    # makes the model, not the widget, authoritative for body text. Until then
    # these reach the primary view only.

    @property
    def frame(self) -> Any:
        return self.c.frame

    @property
    def p(self) -> Position:
        return self.c.p

    def shouldBeExpanded(self, p: Position) -> bool:
        return self.c.shouldBeExpanded(p)

    def setChanged(self) -> None:
        if self.c is None:
            self.changed = True  # No window to mark dirty.
            return
        self.c.setChanged()

    def alert(self, message: str) -> None:
        if self.c is None:
            g.es_print(message)  # No window to raise a dialog in.
            return
        self.c.alert(message)

    def redraw(self, p: Position = None) -> None:
        if self.c is None:
            return  # Nothing is drawn, so nothing to redraw.
        self.c.redraw(p)

    def bodyWantsFocusNow(self) -> None:
        if self.c is None:
            return  # No widget can take focus.
        self.c.bodyWantsFocusNow()

    # These are things a *window* does. The file machinery calls them around
    # every read and write, so on an outline with no window they are no-ops
    # rather than errors: there is no headline being edited to commit, no
    # dialog to raise, and no selection to move.

    def endEditing(self) -> None:
        if self.c is None:
            return
        self.c.endEditing()

    def init_error_dialogs(self) -> None:
        self.ignored_at_file_nodes = []
        self.orphan_at_file_nodes = []
        if self.c is not None:
            self.c.init_error_dialogs()

    def raise_error_dialogs(self, kind: str = 'read') -> None:
        if self.c is None:
            return
        self.c.raise_error_dialogs(kind)

    def selectPosition(self, p: Position) -> None:
        if self.c is None:
            return
        self.c.selectPosition(p)

    # @-others


# @-others
# @@language python
# @@tabwidth -4
# @-leo
