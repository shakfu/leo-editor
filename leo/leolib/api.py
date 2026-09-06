# @+leo-ver=5-thin
# @+node:sa.20260906100000.1: * @file ../leolib/api.py
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

What this buys, measured: opening leo/core/LeoPyRef.leo through leoBridge puts
102 leo.* entries in sys.modules, 9 of them view modules (leoFrame, leoGui,
leoKeys, leoMenu, leoColorizer, leoAPI, leoVim, leoChapters, leoBackground).
Opening the same file through leolib.open_outline, reading every one of its 376
external files, puts in 11, and none of them is a view.

Status: this is the seam, not the finished package. The modules still live in
leo/core; leolib names the subset that is view-free and holds the line with a
test. That makes the boundary a test result rather than a structural fact, and
it flatters the module count: leoGlobals is not a view-free module, only one
whose view-touching functions leolib never calls. TODO.md section 3 has the
three steps, in dependency order, that would make this a package.

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

# util, not leoGlobals: this module is part of Leo's model, and the model
# no longer needs anything leoGlobals owns. util offers every name it uses,
# including g.app and the host flags, which are properties over
# leo.leolib.state and so read and write exactly as they did.
from leo.leolib import util as g
from leo.leolib import state
from leo.core import leoNodes
from leo.core.leoOutline import Outline

if TYPE_CHECKING:  # pragma: no cover
    from leo.core.leoNodes import Position

# @-<< leolib imports >>

__all__ = [
    'Outline',
    'new_outline',
    'open_outline',
    'read_external_files',
    'save',
    'to_xml',
]


# @+others
# @+node:sa.20260906100000.3: ** class _MinimalApp
class _MinimalApp:
    """
    The least g.app that the .leo reader and writer actually require.

    g.app is a process-wide singleton carrying the gui, the window list and the
    open-file list -- none of which a library has any business creating. What
    is left here is data, not machinery: comment delimiters, file extensions,
    the XML prolog, and the flags g.doHook and g.es consult. Every one of them
    is a constant that leolib reads and never writes.

    Creating a node no longer needs any of it. VNode.__init__ used to reach
    through g.app.nodeIndices for a gnx; it now asks its own Outline, and
    open_outline and new_outline hand each outline its own allocator. That was
    the last piece of *behaviour* this class stood in for.

    Deliberately *not* a NullGui: a null object answers every question, so a
    view dependency that crept back in would resolve quietly instead of raising.
    """

    # @+others
    # @+node:sa.20260906100000.4: *3* _MinimalApp.__init__
    def __init__(self) -> None:
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
        self.externalFilesController = None  # outline.setFileTimeStamp asks.
        # g.doHook's guards. No plugins are loaded, so no hook can fire;
        # the readers call g.doHook unconditionally and it must say no.
        self.killed = False
        self.hookError = False
        self.hookFunction = None
        self.idle_time_hooks_enabled = False
        # No plugins are loaded, so no hook can fire. This is what makes
        # g.doHook return None immediately rather than looking for a handler.
        self.enablePlugins = False
        # g.getScript asks. leolib is not the bridge, but it is the same
        # situation: no window, so p.b is the whole script.
        self.inBridge = True
        self.inScript = False
        self.scriptDict: dict[str, Any] = {}
        self.scriptResult: Any = None
        # at.putOpenLeoSentinel asks. Leo's own default.
        self.force_at_auto_sentinels = False
        # at.putRefLine asks when a << section >> has no node behind it.
        # False means "that is an error", which is Leo's default and the only
        # answer a library can give: there is no one to ask.
        self.allow_undefined_refs = False
        self.debug_dict: dict[str, Any] = {}
        self.loadDir = g.os_path_dirname(g.os_path_abspath(leoNodes.__file__))
        # The @auto dispatch tables. Filled on first use, not here: an @auto
        # file has no sentinels, so its structure has to come from a language
        # importer -- but importing all 34 of them triples the module count,
        # and most outlines contain no @auto node at all. See _load_plugins.
        self._plugins_loaded = False
        self._atAutoDict: dict[str, Any] = {}
        self._atAutoWritersDict: dict[str, Any] = {}
        self._classDispatchDict: dict[str, Any] = {}
        self._writersDispatchDict: dict[str, Any] = {}
        self.importerModulesDict: dict[str, Any] = {}
        self.importerClassesDict: dict[str, Any] = {}
        # g.es_print_error consults it for a colour. There are no global
        # settings without a settings file, which is the truth here.
        self.config = None
        # What g.es and friends consult. leolib has no log window, so messages
        # go to stdout via g.pr, which is what logInited=False already means.
        self.batchMode = False
        self.logInited = False
        self.logWaiting: list[Any] = []
        self.printWaiting: list[Any] = []
        self.signon = ''
        self.signon1 = ''
        self.signon2 = ''
        self.syntax_error_files: list[str] = []
        # outline.getPath falls back to this for an outline with no file name.
        self.homeDir = os.path.expanduser('~')
        # Comment delimiters and file extensions. The same dicts LeoApp uses:
        # leo.leolib.state holds them, and both apps point at them rather than
        # copying, so there is one set of tables in the process.
        self.extension_dict = state.extension_dict
        self.language_delims_dict = state.language_delims_dict
        self.language_extension_dict = state.language_extension_dict
        self.extra_extension_dict = state.extra_extension_dict
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

    # @+node:sa.20260907120000.6: *3* _MinimalApp: the @auto tables
    # Reading or writing an @auto node needs the language importers and
    # writers. They are the one thing under leo/plugins that leolib imports,
    # and they earn it: none of the 34 modules touches a front end. Loading is
    # deferred to first use so that an outline without an @auto node never
    # pays for them -- which is most outlines. See leoPluginRegistry.

    def _load_plugins(self) -> None:
        if self._plugins_loaded:
            return
        self._plugins_loaded = True  # First, so a failure is not retried forever.
        from leo.core import leoPluginRegistry

        leoPluginRegistry.create_importer_data(self)
        leoPluginRegistry.create_writers_data(self)

    @property
    def atAutoDict(self) -> dict[str, Any]:
        self._load_plugins()
        return self._atAutoDict

    @atAutoDict.setter
    def atAutoDict(self, d: dict[str, Any]) -> None:
        self._atAutoDict = d

    @property
    def atAutoWritersDict(self) -> dict[str, Any]:
        self._load_plugins()
        return self._atAutoWritersDict

    @atAutoWritersDict.setter
    def atAutoWritersDict(self, d: dict[str, Any]) -> None:
        self._atAutoWritersDict = d

    @property
    def classDispatchDict(self) -> dict[str, Any]:
        self._load_plugins()
        return self._classDispatchDict

    @classDispatchDict.setter
    def classDispatchDict(self, d: dict[str, Any]) -> None:
        self._classDispatchDict = d

    @property
    def writersDispatchDict(self) -> dict[str, Any]:
        self._load_plugins()
        return self._writersDispatchDict

    @writersDispatchDict.setter
    def writersDispatchDict(self, d: dict[str, Any]) -> None:
        self._writersDispatchDict = d

    def scanner_for_at_auto(self, p: Any) -> Any:
        from leo.core import leoPluginRegistry

        return leoPluginRegistry.scanner_for_at_auto(self, p)

    def scanner_for_ext(self, ext: str) -> Any:
        from leo.core import leoPluginRegistry

        return leoPluginRegistry.scanner_for_ext(self, ext)

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
        return  # Its dispatch tables fill themselves on first use.
    if isinstance(g.app, _MinimalApp):
        return
    if not getattr(g.app, 'classDispatchDict', None):
        # Somebody else's app, started without registering the language
        # importers -- a unit test, or a host that never opened a file.
        # Reading an @auto node is impossible without them, and filling empty
        # tables takes nothing away from whoever owns this app.
        from leo.core import leoPluginRegistry

        leoPluginRegistry.create_importer_data(g.app)
        leoPluginRegistry.create_writers_data(g.app)


# @+node:sa.20260908110000.1: ** leolib._shared_node_indices
_node_indices: Any = None


def _shared_node_indices() -> Any:
    """
    The gnx allocator leolib's outlines use, or None to share the app's.

    gnxs must be unique across every outline open in a process, not merely
    within one, because Leo copies and clones nodes between outlines. Two
    allocators with the same user id mint the same gnx within the same second,
    so allocators are shared per process, never per outline. That is not
    hypothetical: giving each leolib outline a fresh allocator clashed with
    Leo's test harness on the first run.

    So: when a real Leo is hosting us, return None and let the outline use
    g.app.nodeIndices like every other outline in that window. Standalone
    there is no g.app to share with, and leolib keeps one of its own with the
    same process-wide scope. Either way VNode.__init__ never has to reach for
    g.app, which is the point.
    """
    global _node_indices
    if g.app is not None and not isinstance(g.app, _MinimalApp):
        return None  # A real Leo owns the process. Share its allocator.
    if _node_indices is None:
        _node_indices = leoNodes.NodeIndices('leolib')
    return _node_indices


# @+node:sa.20260906100000.6: ** leolib.new_outline
def new_outline(fileName: str = '') -> Outline:
    """Create an empty outline with a single node, and no view."""
    ensure_app()
    outline = Outline(None, fileName=fileName, nodeIndices=_shared_node_indices())
    outline.hiddenRootNode = leoNodes.VNode(context=outline, gnx='hidden-root-vnode-gnx')
    root = leoNodes.VNode(context=outline)
    root.h = 'newHeadline'
    outline.hiddenRootNode.children = [root]
    root.parents.append(outline.hiddenRootNode)
    return outline


# @+node:sa.20260906100000.7: ** leolib.open_outline
def open_outline(path: str, read_external: bool = True) -> Outline:
    """
    Read a .leo file and return its Outline. No commander, no frame, no gui.

    A .leo file stores only the outline's own nodes; the contents of @file,
    @clean and friends live in the external files themselves. Reading them is
    on by default because otherwise this returns a shell -- LeoPyRef.leo is 530
    nodes without them and 11,373 with. Pass read_external=False to look at
    just the .leo file, which is much faster and is what you want if you only
    need the shape of the outline.

    The window size and pane ratios the file records are put on
    outline.window_geometry rather than applied to anything; a front end that
    wants them reads them from there.
    """
    ensure_app()
    path = g.finalize(path)
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    outline = Outline(None, fileName=path, nodeIndices=_shared_node_indices())
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
    if read_external:
        read_external_files(outline)
    outline.changed = False
    return outline


# @+node:sa.20260906140000.1: ** leolib.read_external_files
def read_external_files(outline: Outline) -> int:
    """
    Read every @file/@clean/@edit tree in the outline. Return how many were read.

    Errors on one file must not abandon the rest: a .leo file routinely refers
    to external files that have moved or that this machine does not have, and a
    library that raised on the first of them would be useless for exactly the
    bulk work it exists for. Failures leave the node as the .leo file described
    it, which is what Leo itself does.
    """
    from leo.core import leoAtFile

    at = leoAtFile.AtFile(outline)
    outline.ignored_at_file_nodes = []
    outline.orphan_at_file_nodes = []
    count = 0
    # findFilesToRead does the selecting: it honours @ignore, skips clones of
    # the same path, and yields each tree once. readFileAtPosition then
    # dispatches on the node's kind: @file, @clean, @edit, @auto, @shadow
    # and @jupytext are all read differently, and using at.read for all of
    # them reports every non-sentinel file as invalid.
    with outline.batch_events():
        for p in at.findFilesToRead(outline.rootPosition(), all=True):
            try:
                at.readFileAtPosition(p)
                count += 1
            except Exception:  # pragma: no cover (depends on files on disk)
                g.es_exception()
    for p in at.findFilesToRead(outline.rootPosition(), all=True):
        p.v.clearDirty()
    return count


# @+node:sa.20260907100000.1: ** leolib.write_external_files
def write_external_files(outline: Outline, dirty_only: bool = False) -> int:
    """
    Write every @file, @clean, @edit and @nosent tree back to disk.

    Tangle: the outline is the source of truth and the external files are
    regenerated from it. The counterpart of read_external_files, and the half
    of the .leo contract that lets an outline be edited headless and the
    result land in the files a compiler sees.

    Leo's own writer does the work, so the safeguards come with it: a file
    whose regenerated contents are unchanged is not touched at all, so writing
    an outline nobody edited is a no-op down to the mtimes; a backup is made
    before any replacement; and @ignore is honoured. With no view there is
    nobody to answer "overwrite this?", so at.promptForDangerousWrite refuses
    rather than guessing -- a node whose path changed is skipped and reported.

    Returns the number of files actually rewritten.
    """
    at = outline.atFileCommands
    before = at.unchangedFiles
    written_before = _count_files_to_write(at, outline)
    at.writeAll(all=False, dirty=dirty_only)
    # writeAll counts the files it left alone; the rest it rewrote.
    return max(0, written_before - (at.unchangedFiles - before))


def _count_files_to_write(at: Any, outline: Outline) -> int:
    """How many @<file> trees writeAll will consider."""
    files, _root = at.findFilesToWrite(False)
    return len(files)


# @+node:sa.20260907100000.2: ** leolib.tangle
def tangle(outline: Outline, p: Position) -> str:
    """
    Return the text of p's external file, without writing anything.

    The pure half of write_external_files: useful for checking what a write
    would produce, and for a caller that wants the bytes rather than a file.
    Sentinels are included only for the node kinds whose files carry them.
    """
    at = outline.atFileCommands
    sentinels = bool(p.isAtFileNode() or p.isAtThinFileNode() or p.isAtShadowFileNode())
    return at.atFileToString(p, sentinels=sentinels)


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
