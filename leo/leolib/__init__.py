# @+leo-ver=5-thin
# @+node:sa.20260906100000.1: * @file ../leolib/__init__.py
"""
leolib: Leo's outline model and file machinery, with no view of any kind.

The goal of the decoupling described in LEO_REFACTOR.md, stated as an import
boundary rather than as prose:

    leolib          the model. Knows nothing about how it is displayed.
      ^
      +-- leogui    the Qt front end
      +-- leotui    the terminal front end
      +-- leoweb    the web front end

All three can open, create, edit, view and save .leo files, and none of them is
privileged: leolib must never import any of them, and `test_leolib_boundary`
fails the build if it does.

What this buys, measured: opening leo/core/LeoPyRef.leo through leoBridge
imports 99 leo modules, 9 of which are view modules (leoFrame, leoGui, leoKeys,
leoMenu, leoColorizer, leoAPI, leoVim, leoChapters, leoBackground). Opening the
same file through leolib.open_outline imports 6, and none of them is a view.

Status: this is the seam, not the finished package. The modules still live in
leo/core; leolib names the subset that is view-free and holds the line with a
test. Moving the files is a later, purely mechanical step -- and one worth
doing only once the boundary has stopped moving.

Usage:

    from leo import leolib
    outline = leolib.open_outline('myfile.leo')
    for p in outline.all_unique_positions():
        print(p.h)
    outline.rootPosition().b = 'edited with no window in sight'
    leolib.save(outline)
"""
# @+<< leolib imports >>
# @+node:sa.20260906100000.2: ** << leolib imports >>
from __future__ import annotations
import os
from typing import Any, TYPE_CHECKING

from leo.core import leoGlobals as g
from leo.core import leoNodes
from leo.core.leoOutline import Outline

if TYPE_CHECKING:  # pragma: no cover
    from leo.core.leoNodes import Position, VNode
# @-<< leolib imports >>

__all__ = ['Outline', 'new_outline', 'open_outline', 'save', 'to_xml']


# @+others
# @+node:sa.20260906100000.3: ** class _MinimalApp
class _MinimalApp:
    """
    The least g.app that VNode and the .leo reader actually require.

    g.app is a process-wide singleton carrying the gui, the window list and the
    open-file list -- none of which a library has any business creating. But
    VNode.__init__ reaches through it for the gnx allocator, and the source has
    carried a comment about that since long before this refactor:

        # To make VNode's independent of Leo's core,
        # wrap all calls to the VNode ctor

    This is that wrapper, for now. gnx allocation is document-level and belongs
    on the Outline; until it moves, leolib installs this rather than booting
    LeoApp, which would load settings, plugins and a gui.

    Deliberately *not* a NullGui: a null object answers every question, so a
    view dependency that crept back in would resolve quietly instead of raising.
    """

    # @+others
    # @+node:sa.20260906100000.4: *3* _MinimalApp.__init__
    def __init__(self) -> None:
        self.nodeIndices = leoNodes.NodeIndices('leolib')
        self.debug: list[str] = []
        self.unitTesting = False
        self.silentMode = True
        self.loadManager = None
        self.gui = None  # Not a NullGui: see the class docstring.
        self.log = None
        self.db: dict[str, Any] = {}
        self.windowList: list[Any] = []
        self.commanders_list: list[Any] = []
        self.positions = 0  # Position.__init__ counts allocations here.
        # v.contentModified asks whether any plugin is listening before it
        # records anything. None means "nobody is", which is the truth here.
        self.pluginsController = None
        # VNode asks for these on every dirty bit. leoGlobals owns the
        # constants; LeoApp copies the same ones.
        self.atAutoNames = set(g.atAutoNames)
        self.atFileNames = set(g.atFileNames)
        # The .leo writer's XML prolog. Same strings LeoApp uses.
        self.prolog_prefix_string = g.prolog_prefix_string
        self.prolog_postfix_string = g.prolog_postfix_string
        self.prolog_namespace_string = g.prolog_namespace_string

    def commanders(self) -> list[Any]:
        """No windows exist. @g.command decorators run at import time and ask."""
        return self.commanders_list

    # @-others


# @+node:sa.20260906100000.5: ** leolib.ensure_app
def ensure_app() -> None:
    """
    Install the minimal g.app, unless a real Leo is already running.

    Importing leolib inside a running Leo must not disturb it: a front end that
    uses leolib for a background read shares the process with the editor.
    """
    if g.app is None:
        g.app = _MinimalApp()
    elif getattr(g.app, 'nodeIndices', None) is None:
        g.app.nodeIndices = leoNodes.NodeIndices('leolib')


# @+node:sa.20260906100000.6: ** leolib.new_outline
def new_outline(fileName: str = '') -> Outline:
    """Create an empty outline with a single node, and no view."""
    ensure_app()
    outline = Outline(None, fileName=fileName)
    outline.hiddenRootNode = leoNodes.VNode(context=outline, gnx='hidden-root-vnode-gnx')
    root = leoNodes.VNode(context=outline)
    root.h = 'newHeadline'
    outline.hiddenRootNode.children = [root]
    root.parents.append(outline.hiddenRootNode)
    return outline


# @+node:sa.20260906100000.7: ** leolib.open_outline
def open_outline(path: str) -> Outline:
    """
    Read a .leo file and return its Outline. No commander, no frame, no gui.

    The window size and pane ratios the file records are put on
    outline.window_geometry rather than applied to anything; a front end that
    wants them reads them from there.
    """
    ensure_app()
    path = g.finalize(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    outline = Outline(None, fileName=path)
    outline.hiddenRootNode = leoNodes.VNode(context=outline, gnx='hidden-root-vnode-gnx')
    from leo.core import leoFileCommands
    fc = outline.fileCommands
    fc.mFileName = path
    reader = leoFileCommands.FastRead(outline, fc.gnxDict)
    with open(path, 'rb') as f:
        v = reader.readFile(f, path)
    if v is None:
        raise ValueError(f"not a readable .leo file: {path}")
    outline.hiddenRootNode = v
    outline.changed = False
    return outline


# @+node:sa.20260906100000.8: ** leolib.to_xml
def to_xml(outline: Outline) -> str:
    """Return the outline in .leo (XML) format."""
    return outline.fileCommands.outline_to_xml_string()


# @+node:sa.20260906100000.9: ** leolib.save
def save(outline: Outline, path: str = '') -> str:
    """
    Write the outline to a .leo file and return the path written.

    This writes the .leo file only. External @file nodes are a separate
    concern -- they are written by leoAtFile, which a front end drives -- and
    conflating them here would make a headless save touch the user's source
    tree as a side effect.
    """
    path = g.finalize(path) if path else outline.mFileName
    if not path:
        raise ValueError('no file name: pass one, or set outline.mFileName')
    outline.mFileName = path
    outline.fileCommands.mFileName = path
    s = to_xml(outline)
    with open(path, 'wb') as f:
        f.write(s.encode(outline.leo_file_encoding, 'replace'))
    outline.changed = False
    return path


# @-others
# @@language python
# @@tabwidth -4
# @-leo
