# @+leo-ver=5-thin
# @+node:sa.20260908140000.1: * @file ../leolib/util.py
"""
Leo's app-independent layer: everything in leoGlobals that never reads g.app.

g.app is Leo's process-wide application object -- the gui, the open windows,
the settings, the plugin controller, the language tables. It is the single
piece of state that makes leoGlobals a Leo-application module rather than a
library, and reaching for it is what turns a helper into something that needs
a running editor.

The 195 names here never do. They are the string, path, encoding, scanning
and directive helpers that Leo's model is written in, and they behave the same
whether a Leo is running, a test harness is running, or nothing is. Some take
a commander or a position -- these are Leo's helpers, not generic ones -- but
none asks the application for anything.

leo.core.leoGlobals imports every name below, so `splitLines` and
`util.splitLines` are the same function object and no caller had to change.
The point of the split is the direction of the arrow: leoGlobals depends on
util, never the reverse. util imports no Leo module at runtime, which
test_leolib_util enforces along with the no-g.app rule.

This is the first half of taking leoGlobals apart (TODO.md section 3). The
half that remains -- logging, hooks, the language tables, script execution --
is app-dependent for a reason, and needs a seam rather than a move.
"""

# @+<< leolib.util: imports >>
# @+node:sa.20260908140000.2: ** << leolib.util: imports >>
from __future__ import annotations
from collections.abc import Callable, Sequence
import codecs
from functools import reduce
import gc
import glob
import inspect
import io
import operator
import os
from pathlib import Path
import pprint
import re
import string
import subprocess
import sys
import time
import traceback
import types
from typing import Any, TYPE_CHECKING
import urllib
import urllib.parse as urlparse

if TYPE_CHECKING:  # pragma: no cover
    from leo.core.leoCommands import Commands as Cmdr
    from leo.core.leoNodes import Position, VNode

    Args = Any
    KWargs = Any
    Value = Any

StringIO = io.StringIO
# @-<< leolib.util: imports >>


# @+others
# @+node:sa.20260908140000.3: ** leoGlobals: global constants
# @+node:sa.20260908140000.4: *3* util.minimum_python_version
minimum_python_version = '3.10'


# @+node:sa.20260908140000.5: *3* util.minimum_python_version_tuple
minimum_python_version_tuple = (3, 10, 0)


# @+node:sa.20260908140000.6: *3* util.python_version_tuple
python_version_tuple = sys.version_info[:3]


# @+node:sa.20260908140000.7: *3* util.isPython3
isPython3 = python_version_tuple >= (3, 0, 0)


# @+node:sa.20260908140000.8: *3* util.isValidPython
isValidPython = python_version_tuple >= minimum_python_version_tuple


# @+node:sa.20260908140000.9: *3* util.isMac
isMac = sys.platform.startswith('darwin')


# @+node:sa.20260908140000.10: *3* util.isWindows
isWindows = sys.platform.startswith('win')


# @+node:sa.20260908140000.11: ** define binary_file_extensions
# @+node:sa.20260908140000.12: *3* util.binary_file_extensions
# https://github.com/sindresorhus/binary-extensions/blob/main/binary-extensions.json
binary_file_extensions = [
    "3dm",
    "3ds",
    "3g2",
    "3gp",
    "7z",
    "a",
    "aac",
    "adp",
    "afdesign",
    "afphoto",
    "afpub",
    "ai",
    "aif",
    "aiff",
    "alz",
    "ape",
    "apk",
    "appimage",
    "ar",
    "arj",
    "asf",
    "au",
    "avi",
    "bak",
    "baml",
    "bh",
    "bin",
    "bk",
    "bmp",
    "btif",
    "bz2",
    "bzip2",
    "cab",
    "caf",
    "cgm",
    "class",
    "cmx",
    "cpio",
    "cr2",
    "cr3",
    "cur",
    "dat",
    "dcm",
    "deb",
    "dex",
    "djvu",
    "dll",
    "dmg",
    "dng",
    "doc",
    "docm",
    "docx",
    "dot",
    "dotm",
    "dra",
    "DS_Store",
    "dsk",
    "dts",
    "dtshd",
    "dvb",
    "dwg",
    "dxf",
    "ecelp4800",
    "ecelp7470",
    "ecelp9600",
    "egg",
    "eol",
    "eot",
    "epub",
    "exe",
    "f4v",
    "fbs",
    "fh",
    "fla",
    "flac",
    "flatpak",
    "fli",
    "flv",
    "fpx",
    "fst",
    "fvt",
    "g3",
    "gh",
    "gif",
    "graffle",
    "gz",
    "gzip",
    "h261",
    "h263",
    "h264",
    "icns",
    "ico",
    "ief",
    "img",
    "ipa",
    "iso",
    "jar",
    "jpeg",
    "jpg",
    "jpgv",
    "jpm",
    "jxr",
    "key",
    "ktx",
    "lha",
    "lib",
    "lvp",
    "lz",
    "lzh",
    "lzma",
    "lzo",
    "m3u",
    "m4a",
    "m4v",
    "mar",
    "mdi",
    "mht",
    "mid",
    "midi",
    "mj2",
    "mka",
    "mkv",
    "mmr",
    "mng",
    "mobi",
    "mov",
    "movie",
    "mp3",
    "mp4",
    "mp4a",
    "mpeg",
    "mpg",
    "mpga",
    "mxu",
    "nef",
    "npx",
    "numbers",
    "nupkg",
    "o",
    "odp",
    "ods",
    "odt",
    "oga",
    "ogg",
    "ogv",
    "otf",
    "ott",
    "pages",
    "pbm",
    "pcx",
    "pdb",
    "pdf",
    "pea",
    "pgm",
    "pic",
    "png",
    "pnm",
    "pot",
    "potm",
    "potx",
    "ppa",
    "ppam",
    "ppm",
    "pps",
    "ppsm",
    "ppsx",
    "ppt",
    "pptm",
    "pptx",
    "psd",
    "pya",
    "pyc",
    "pyo",
    "pyv",
    "qt",
    "rar",
    "ras",
    "raw",
    "resources",
    "rgb",
    "rip",
    "rlc",
    "rmf",
    "rmvb",
    "rpm",
    "rtf",
    "rz",
    "s3m",
    "s7z",
    "scpt",
    "sgi",
    "shar",
    "snap",
    "sil",
    "sketch",
    "slk",
    "smv",
    "snk",
    "so",
    "stl",
    "suo",
    "sub",
    "swf",
    "tar",
    "tbz",
    "tbz2",
    "tga",
    "tgz",
    "thmx",
    "tif",
    "tiff",
    "tlz",
    "ttc",
    "ttf",
    "txz",
    "udf",
    "uvh",
    "uvi",
    "uvm",
    "uvp",
    "uvs",
    "uvu",
    "viv",
    "vob",
    "war",
    "wav",
    "wax",
    "wbmp",
    "wdp",
    "weba",
    "webm",
    "webp",
    "whl",
    "wim",
    "wm",
    "wma",
    "wmv",
    "wmx",
    "woff",
    "woff2",
    "wrm",
    "wvx",
    "xbm",
    "xif",
    "xla",
    "xlam",
    "xls",
    "xlsb",
    "xlsm",
    "xlsx",
    "xlt",
    "xltm",
    "xltx",
    "xm",
    "xmind",
    "xpi",
    "xpm",
    "xwd",
    "xz",
    "z",
    "zip",
    "zipx",
]


# @+node:sa.20260908140000.13: ** define globalDirectiveList
# @+node:sa.20260908140000.14: *3* util.globalDirectiveList
# Visible externally so plugins may add to the list of directives.
# The atFile write logic uses this, but not the atFile read logic.
globalDirectiveList = [
    # Order does not matter.
    'all',
    'beautify',
    'c',
    'code',
    'color',
    'colorcache',
    'comment',
    'delims',
    'doc',
    'encoding',
    # 'end_raw',  # #2276.
    'first',
    'header',
    'ignore',
    'killbeautify',
    'killcolor',
    'language',
    'last',
    'lineending',
    'markup',
    'nobeautify',
    'nocolor-node',
    'nocolor',
    'noheader',
    'nowrap',
    'nopyflakes',  # Leo 6.1.
    'nosearch',  # Leo 5.3.
    'others',
    'pagewidth',
    'path',
    'quiet',
    # 'raw',  # #2276.
    'section-delims',  # Leo 6.6. #2276.
    'silent',
    'tabwidth',
    'unit',
    'verbose',
    'wrap',
]


# @+node:sa.20260908140000.15: ** define global decorator dicts >> (leoGlobals.py)
# @+node:sa.20260908140000.16: *3* util.global_commands_dict
global_commands_dict: dict[str, Callable] = {}


# @+node:sa.20260908140000.17: *3* util.cmd_instance_dict
cmd_instance_dict: dict[str, list[str]] = {
    # Keys are class names, values are attribute chains.
    'AbbrevCommandsClass':      ['c', 'abbrevCommands'],
    'AtFile':                   ['c', 'atFileCommands'],
    'AutoCompleterClass':       ['c', 'k', 'autoCompleter'],
    'ChapterController':        ['c', 'chapterController'],
    'Commands':                 ['c'],
    'ControlCommandsClass':     ['c', 'controlCommands'],
    'DebugCommandsClass':       ['c', 'debugCommands'],
    'EditCommandsClass':        ['c', 'editCommands'],
    'EditFileCommandsClass':    ['c', 'editFileCommands'],
    'FileCommands':             ['c', 'fileCommands'],
    'HelpCommandsClass':        ['c', 'helpCommands'],
    'KeyHandlerClass':          ['c', 'k'],
    'KeyHandlerCommandsClass':  ['c', 'keyHandlerCommands'],
    'KillBufferCommandsClass':  ['c', 'killBufferCommands'],
    'LeoApp':                   ['g', 'app'],
    'LeoFind':                  ['c', 'findCommands'],
    'LeoImportCommands':        ['c', 'importCommands'],
    # 'MacroCommandsClass':       ['c', 'macroCommands'],
    'PrintingController':       ['c', 'printingController'],
    'RectangleCommandsClass':   ['c', 'rectangleCommands'],
    'RstCommands':              ['c', 'rstCommands'],
    'SpellCommandsClass':       ['c', 'spellCommands'],
    'Undoer':                   ['c', 'undoer'],
    'VimCommands':              ['c', 'vimCommands'],
}  # fmt: skip


# @+node:sa.20260908140000.18: ** define global error regexes >> (leoGlobals.py)
# @+node:sa.20260908140000.19: *3* util.mypy_pat
mypy_pat = re.compile(r'^(.+?):([0-9]+):\s*(error|note)\s*(.*)\s*$')


# @+node:sa.20260908140000.20: *3* util.python_pat
python_pat = re.compile(r'^\s*File\s+"(.*?)",\s*line\s*([0-9]+)\s*$')


# @+node:sa.20260908140000.21: *3* util.ruff_pat
ruff_pat = re.compile(r'^(.+?):([0-9]+):[0-9]+:.*$')  # ruff's --output-format=concise.


# @+node:sa.20260908140000.22: *3* util.ty_pat
ty_pat = re.compile(r'^\s*-->\s*(.+?):([0-9]+):[0-9]+.*$')


# @+node:sa.20260908140000.23: ** define regexes >> (leoGlobals.py)
# @+node:sa.20260908140000.24: *3* util.g_language_pat
# Regex used by this module, and in leoColorizer.py.
g_language_pat = re.compile(r'^@language\s+(\w+)+', re.MULTILINE)


# @+node:sa.20260908140000.25: *3* util.g_is_directive_pattern
# g_is_directive_pattern excludes @encoding.whatever and @encoding(whatever)
# It must allow @language python, @nocolor-node, etc.
g_is_directive_pattern = re.compile(r'^\s*@([\w-]+)\s*')


# @+node:sa.20260908140000.26: *3* util.g_tabwidth_pat
g_tabwidth_pat = re.compile(r'(^@tabwidth)', re.MULTILINE)


# @+node:sa.20260908140000.27: *3* util.g_section_delims_pat
# #2267: Support for @section-delims.
g_section_delims_pat = re.compile(r'^@section-delims[ \t]+([^ \w\n\t]+)[ \t]+([^ \w\n\t]+)[ \t]*$')


# @+node:sa.20260908140000.28: *3* util.gnx_char
# New in Leo 6.6.4: gnxs must start with 'gnx:'
gnx_char = r"""[^.,"'\s]"""  # LeoApp.cleanLeoID() removes these characters.


# @+node:sa.20260908140000.29: *3* util.gnx_id
gnx_id = rf"{gnx_char}{{3,}}"  # id's must have at least three characters.


# @+node:sa.20260908140000.30: *3* util.gnx_regex
gnx_regex = re.compile(rf"\bgnx:{gnx_id}\.[0-9]+\.[0-9]+")


# @+node:sa.20260908140000.31: *3* util.unl_regex
# Unls end with quotes.
unl_regex = re.compile(r"""\bunl:[^`'"]+""")


# @+node:sa.20260908140000.32: *3* util.url_leadins
# Urls end at space or quotes.
url_leadins = 'fghmnptw'


# @+node:sa.20260908140000.33: *3* util.url_kinds
url_kinds = '(file|ftp|gopher|http|https|mailto|news|nntp|prospero|telnet|wais)'


# @+node:sa.20260908140000.34: *3* util.url_regex
url_regex = re.compile(rf"""\b{url_kinds}://[^\s'"]+""")


# @+node:sa.20260908140000.35: *3* util.user_dict
user_dict: dict[str, Value] = {}  # Non-persistent dictionary for scripts and plugins.


# @+node:sa.20260908140000.36: *3* util.atAutoNames
# The @<file> spellings Leo understands. These are constants, and VNode asks
# for them on every dirty bit, so they live here rather than only on g.app:
# leoNodes must be able to answer "is this an @file node?" without a running
# application. LeoApp copies them into app.atAutoNames / app.atFileNames,
# which stay the names the rest of Leo uses.
atAutoNames: set[str] = {
    "@auto-rst",
    "@auto",
}


# @+node:sa.20260908140000.37: *3* util.xml_namespace_url
# The .leo file's XML prolog. Constants, needed by the writer with no app
# running; LeoApp copies them into the app attributes the rest of Leo uses.
xml_namespace_url = 'https://leo-editor.github.io/leo-editor/namespaces/leo-python-editor/1.1'


# @+node:sa.20260908140000.38: *3* util.prolog_prefix_string
prolog_prefix_string = '<?xml version="1.0" encoding='


# @+node:sa.20260908140000.39: *3* util.prolog_postfix_string
prolog_postfix_string = '?>'


# @+node:sa.20260908140000.40: *3* util.prolog_namespace_string
prolog_namespace_string = f'xmlns:leo="{xml_namespace_url}"'


# @+node:sa.20260908140000.41: *3* util.atFileNames
atFileNames: set[str] = {
    "@asis",
    "@clean",
    "@edit",
    "@file-asis",
    "@file-thin",
    "@file-nosent",
    "@file",
    "@jupytext",
    "@nosent",
    "@shadow",
    "@thin",
}


# @+node:sa.20260908140000.42: ** util.Backup
# @+node:sa.20260908140000.43: *3* util.standard_timestamp
def standard_timestamp() -> str:
    """Return a reasonable timestamp."""
    return time.strftime("%Y%m%d-%H%M%S")


# @+node:sa.20260908140000.44: ** util.Classes & class accessors
# @+node:sa.20260908140000.45: *3* util.Bunch
class Bunch:
    """
    From The Python Cookbook:

        Create a Bunch whenever you want to group a few variables:

            point = Bunch(datum=y, squared=y*y, coord=x)

        You can read/write the named attributes you just created, add others,
        del some of them, etc::

            if point.squared > threshold:
                point.isok = True
    """

    def __init__(self, **kwargs: KWargs) -> None:
        self.__dict__.update(kwargs)

    def __repr__(self) -> str:
        return self.toString()

    def ivars(self) -> list:
        return sorted(self.__dict__)

    def keys(self) -> list:
        return sorted(self.__dict__)

    def toString(self) -> str:
        tag = self.__dict__.get('tag')
        entries = [
            f"{key}: {str(self.__dict__.get(key)) or repr(self.__dict__.get(key))}"
            for key in self.ivars()
            if key != 'tag'
        ]
        # Fail.
        result = [f'Bunch({tag or ""})']
        result.extend(entries)
        return '\n    '.join(result) + '\n'

    # Used by new undo code.

    def __setitem__(self, key: str, value: Value) -> Value:
        """Support aBunch[key] = val"""
        return operator.setitem(self.__dict__, key, value)

    def __getitem__(self, key: str) -> Value:
        """Support aBunch[key]"""
        return operator.getitem(self.__dict__, key)

    def get(self, key: str, theDefault: Value = None) -> Value:
        return self.__dict__.get(key, theDefault)

    def __contains__(self, key: str) -> bool:
        return key in self.__dict__


# @+node:sa.20260908140000.46: *3* util.bunch
bunch = Bunch


# @+node:sa.20260908140000.47: *3* util.ReadLinesClass
class ReadLinesClass:
    """A class whose next method provides a readline method for Python's tokenize module."""

    def __init__(self, s: str) -> None:
        self.lines = splitLines(s)
        self.i = 0

    def next(self) -> str:
        if self.i < len(self.lines):
            line = self.lines[self.i]
            self.i += 1
        else:
            line = ''
        return line

    __next__ = next


# @+node:sa.20260908140000.48: *3* util.tracing_tags
tracing_tags: dict[int, str] = {}  # Keys are id's, values are tags.


# @+node:sa.20260908140000.49: *3* util.UiTypeException
class UiTypeException(Exception):
    pass


# @+node:sa.20260908140000.50: ** util.Debugging, GC, Stats & Timing
# @+node:sa.20260908140000.51: *3* util.qt_text_classes
qt_text_classes = [
    'LeoQTextBrowser',
    'LeoQTreeWidget',
    'LeoQtLog',
    'QHeadlineWrapper',
    'QLineEdit',
    'QMenuWrapper',
    'QMinibufferWrapper',
    'QTextBrowser',
    'QTextEditWrapper',
    'StringTextWrapper',
    'VisLineEdit',  # In the DynamicWindow class.
]


# @+node:sa.20260908140000.52: *3* util.widget_classes
widget_classes = [
    'BodyWrapper',  # --gui=console
    'DynamicWindow',
    'LeoQTextBrowser',
    'LeoQTreeWidget',
    'LeoQtLog',
    'LeoQtTree',
    'QHeadlineWrapper',
    'QLineEdit',
    'QMenuBar',
    'QMenuWrapper',
    'QMinibufferWrapper',
    'QPushButton',
    'QTextBrowser',
    'QTextEditWrapper',
    'StringTextWrapper',
    'VisLineEdit',
]


# @+node:sa.20260908140000.53: *3* util.dump
def dump(s: str) -> str:
    out = ""
    for i in s:
        out += str(ord(i)) + ","
    return out


# @+node:sa.20260908140000.54: *3* util.oldDump
def oldDump(s: str) -> str:
    out = ""
    for i in s:
        if i == '\n':
            out += "["
            out += "n"
            out += "]"
        if i == '\t':
            out += "["
            out += "t"
            out += "]"
        elif i == ' ':
            out += "["
            out += " "
            out += "]"
        else:
            out += i
    return out


# @+node:sa.20260908140000.55: *3* util.dump_tree
def dump_tree(c: Cmdr, dump_body: bool = False, msg: str = '') -> None:
    if msg:
        print(msg.rstrip())
    else:
        print('')
    for p in c.all_positions():
        print(f"clone? {int(p.isCloned())} {' ' * p.level()} {p.h}")
        if dump_body:
            for z in splitLines(p.b):
                print(z.rstrip())


# @+node:sa.20260908140000.56: *3* util.tree_to_string
def tree_to_string(c: Cmdr, dump_body: bool = False, msg: str = '') -> str:
    result = ['\n']
    if msg:
        result.append(msg)
    for p in c.all_positions():
        result.append(f"clone? {int(p.isCloned())} {' ' * p.level()} {p.h}")
        if dump_body:
            for z in splitLines(p.b):
                result.append(z.rstrip())
    return '\n'.join(result)


# @+node:sa.20260908140000.57: *3* util.get_line
def get_line(s: str, i: int) -> str:
    nl = ""
    if is_nl(s, i):
        i = skip_nl(s, i)
        nl = "[nl]"
    j = find_line_start(s, i)
    k = skip_to_end_of_line(s, i)
    return nl + s[j:k]


# @+node:sa.20260908140000.58: *3* util.get_line_after
def get_line_after(s: str, i: int) -> str:
    nl = ""
    if is_nl(s, i):
        i = skip_nl(s, i)
        nl = "[nl]"
    k = skip_to_end_of_line(s, i)
    return nl + s[i:k]


# @+node:sa.20260908140000.59: *3* util.getLineAfter
getLineAfter = get_line_after


# @+node:sa.20260908140000.60: *3* util.getIvarsDict
def getIvarsDict(obj: object) -> dict[str, Value]:
    """Return a dictionary of ivars:values for non-methods of obj."""
    d: dict[str, Value] = dict(
        [
            [key, getattr(obj, key)]
            for key in dir(obj)
            if not isinstance(getattr(obj, key), types.MethodType)
        ]
    )
    return d


# @+node:sa.20260908140000.61: *3* util.objToString
def objToString(
    obj: object,
    *,
    indent: int = 0,
    tag: str = '',
    width: int = 120,
    offset: int = 0,  # Offset into array-like objects.
) -> str:
    """Pretty print any Python object to a string."""
    if isinstance(obj, dict):
        if obj:
            result_list = ['{\n']
            try:
                keys = sorted(obj, key=str)
            except TypeError:  # Unsortable keys.
                keys = obj.keys()
            for key in keys:
                result_list.append(f"key: {str(key)}:\n{obj.get(key)}\n")
            result_list.append('}')
            result = ''.join(result_list)
        else:
            result = '{}'
    elif isinstance(obj, (list, tuple)):
        if obj:
            # Return the enumerated lines of the list.
            result_list = ['[\n' if isinstance(obj, list) else '(\n']
            for i, z in enumerate(obj):
                result_list.append(f"  {i + offset:4}: {z!r}\n")
            result_list.append(']\n' if isinstance(obj, list) else ')\n')
            result = ''.join(result_list)
        else:
            result = '[]' if isinstance(obj, list) else '()'
    elif not isinstance(obj, str):
        result = pprint.pformat(obj, indent=indent, width=width)
        # Put opening/closing delims on separate lines.
        if result.count('\n') > 0 and result[0] in '([{' and result[-1] in ')]}':
            result = f"{result[0]}\n{result[1:-2]}\n{result[-1]}"
    elif '\n' not in obj:
        result = repr(obj)
    else:
        # Return the enumerated lines of the string.
        lines = ''.join([f"  {i + offset:4}: {z!r}\n" for i, z in enumerate(splitLines(obj))])
        result = f"[\n{lines}]\n"
    return f"{tag.strip()}: {result}" if tag and tag.strip() else result


# @+node:sa.20260908140000.62: *3* util.toString
toString = objToString


# @+node:sa.20260908140000.63: *3* util.dictToString
dictToString = objToString


# @+node:sa.20260908140000.64: *3* util.listToString
listToString = objToString


# @+node:sa.20260908140000.65: *3* util.tupleToString
tupleToString = objToString


# @+node:sa.20260908140000.66: *3* util.sleep
def sleep(n: float) -> None:
    """Wait about n milliseconds."""
    from time import sleep

    sleep(n)


# @+node:sa.20260908140000.67: *3* util.clearAllIvars
def clearAllIvars(o: object) -> None:
    """Clear all ivars of o, a member of some class."""
    if o:
        o.__dict__.clear()


# @+node:sa.20260908140000.68: *3* util.enable_gc_debug
def enable_gc_debug() -> None:
    gc.set_debug(
        gc.DEBUG_STATS  # prints statistics.
        | gc.DEBUG_LEAK  # Same as all below.
        | gc.DEBUG_COLLECTABLE
        | gc.DEBUG_UNCOLLECTABLE
        |
        # gc.DEBUG_INSTANCES |
        # gc.DEBUG_OBJECTS |
        gc.DEBUG_SAVEALL
    )


# @+node:sa.20260908140000.69: *3* util.printGcSummary
def printGcSummary() -> None:
    enable_gc_debug()
    try:
        n = len(gc.garbage)
        n2 = len(gc.get_objects())
        s = f"printGCSummary: garbage: {n}, objects: {n2}"
        print(s)
    except Exception:
        traceback.print_exc()


# @+node:sa.20260908140000.70: *3* util._int_stat_prefix
_int_stat_prefix = 'stat_count: '


# @+node:sa.20260908140000.71: *3* util.getTime
def getTime() -> float:
    return time.time()


# @+node:sa.20260908140000.72: *3* util.timeSince
def timeSince(start: float) -> str:
    return f"{time.time() - start:5.2f} sec."


# @+node:sa.20260908140000.73: ** util.Directives
# @+node:sa.20260908140000.74: *3* util.findTabWidthDirectives
def findTabWidthDirectives(c: Cmdr, p: Position) -> int | None:
    """Return the tab width in effect at position p."""
    if c is None:
        return None  # c may be None for testing.
    w = None
    # 2009/10/02: no need for copy arg to iter
    for p in p.self_and_parents(copy=False):
        if w:
            break
        for s in p.h, p.b:
            if w:
                break
            anIter = g_tabwidth_pat.finditer(s)
            for m in anIter:
                word = m.group(0)
                i = m.start(0)
                j = skip_ws(s, i + len(word))
                _, w = skip_long(s, j)
                if w == 0:
                    w = None
    return w


# @+node:sa.20260908140000.75: *3* util.findReference
def findReference(name: str, root: Position) -> Position | None:
    """Return the position containing the section definition for name."""
    for p in root.subtree(copy=False):
        assert p != root
        if p.matchHeadline(name) and not p.isAtIgnoreNode():
            return p.copy()
    return None


# @+node:sa.20260908140000.76: *3* util.inAtNosearch
def inAtNosearch(p: Position) -> bool:
    """Return True if p or p's ancestors contain an @nosearch directive."""
    if not p:
        return False  # #2288.
    for p in p.self_and_parents():
        if p.is_at_ignore() or re.search(r'(^@|\n@)nosearch\b', p.b):
            return True
    return False


# @+node:sa.20260908140000.77: *3* util.isDirective
def isDirective(s: str) -> bool:
    """Return True if s starts with a directive."""
    if m := g_is_directive_pattern.match(s):
        s2 = s[m.end(1) :]
        if s2 and s2[0] in ".(":
            return False
        return bool(m.group(1) in globalDirectiveList)
    return False


# @+node:sa.20260908140000.78: *3* util.stripPathCruft
def stripPathCruft(path: str) -> str:
    """Strip cruft from a path name."""
    if not path:
        return path  # Retain empty paths for warnings.
    if len(path) > 2 and (
        (path[0] == '<' and path[-1] == '>')
        or (path[0] == '"' and path[-1] == '"')
        or (path[0] == "'" and path[-1] == "'")
    ):
        path = path[1:-1].strip()
    # We want a *relative* path, not an absolute path.
    return path.strip()


# @+node:sa.20260908140000.79: ** util.Files & Directories
# @+node:sa.20260908140000.80: *3* util.fullPath
def fullPath(c: Cmdr, p: Position) -> str:
    """
    Return the full path in effect at p.

    If p is an @<file> node, return the path, including the filename.
    Otherwise the return the path to the enclosing directory.

    Neither the path nor the fileName will be created if it does not exist.

    Takes an Outline or a commander: where a node's file lives is a document
    fact, and callers that hold only a VNode have an Outline in v.context.
    """
    return getattr(c, 'outline', c).fullPath(p)


# @+node:sa.20260908140000.81: *3* util.getBaseDirectory
def getBaseDirectory(c: Cmdr) -> str:
    """
    This function is deprecated.

    Previously it convert '!' or '.' to proper directory references using
    @string relative-path-base-directory.
    """
    return ''


# @+node:sa.20260908140000.82: *3* util.is_binary_file
def is_binary_file(f: io.IOBase) -> bool:
    return bool(f and isinstance(f, io.FileIO))


# @+node:sa.20260908140000.83: *3* util.is_binary_external_file
def is_binary_external_file(fileName: str) -> bool:
    if not fileName:
        return False
    _root, ext = os.path.splitext(fileName)
    return ext in binary_file_extensions


# @+node:sa.20260908140000.84: *3* util.makePathRelativeTo
def makePathRelativeTo(fullPath: str, basePath: str) -> str:
    if fullPath.startswith(basePath):
        s = fullPath[len(basePath) :]
        if s.startswith(os.path.sep):
            s = s[len(os.path.sep) :]
        return s
    return fullPath


# @+node:sa.20260908140000.85: *3* util.sanitize_filename
def sanitize_filename(s: str) -> str:
    """
    Prepares string s to be a valid file name:

    - substitute '_' for whitespace and special path characters.
    - eliminate all other non-alphabetic characters.
    - convert double quotes to single quotes.
    - strip leading and trailing whitespace.
    - return at most 128 characters.
    """
    result = []
    for ch in s:
        if ch in string.ascii_letters:
            result.append(ch)
        elif ch == '\t':
            result.append(' ')
        elif ch == '"':
            result.append("'")
        elif ch in '\\/:|<>*:._':
            result.append('_')
    s = ''.join(result).strip()
    while len(s) > 1:
        n = len(s)
        s = s.replace('__', '_')
        if len(s) == n:
            break
    return s[:128]


# @+node:sa.20260908140000.86: *3* util.splitLongFileName
def splitLongFileName(fn: str, limit: int = 40) -> str:
    """Return fn, split into lines at slash characters."""
    aList = fn.replace('\\', '/').split('/')
    n, result = 0, []
    for i, s in enumerate(aList):
        n += len(s)
        result.append(s)
        if i + 1 < len(aList):
            result.append('/')
            n += 1
        if n > limit:
            result.append('\n')
            n = 0
    return ''.join(result)


# @+node:sa.20260908140000.87: ** util.Finding & Scanning
# @+node:sa.20260908140000.88: *3* util.find_word
def find_word(s: str, word: str, i: int = 0) -> int:
    """
    Return the index of the first occurrence of word in s, or -1 if not found.

    find_word is *not* the same as s.find(i,word);
    find_word ensures that only word-matches are reported.
    """
    while i < len(s):
        progress = i
        i = s.find(word, i)
        if i == -1:
            return -1
        # Make sure we are at the start of a word.
        if i > 0:
            ch = s[i - 1]
            if ch == '_' or ch.isalnum():
                i += len(word)
                continue
        if match_word(s, i, word):
            return i
        i += len(word)
        assert progress < i
    return -1


# @+node:sa.20260908140000.89: *3* util.findAncestorVnodeByPredicate
def findAncestorVnodeByPredicate(p: Position, v_predicate: Callable) -> VNode | None:
    """
    Return first ancestor vnode matching the predicate.

    The predicate must must be a function of a single vnode argument.
    """
    if not p:
        return None
    # First, look up the tree.
    for p2 in p.self_and_parents():
        if v_predicate(p2.v):
            return p2.v
    # Look at parents of all cloned nodes.
    if not p.isCloned():
        return None
    seen = []  # vnodes that have already been searched.
    assert p.v
    parents = p.v.parents[:]  # vnodes to be searched.
    while parents:
        parent_v = parents.pop()
        if parent_v in seen:
            continue
        seen.append(parent_v)
        if v_predicate(parent_v):
            return parent_v
        for grand_parent_v in parent_v.parents:
            if grand_parent_v not in seen:
                parents.append(grand_parent_v)
    return None


# @+node:sa.20260908140000.90: *3* util.findRootsWithPredicate
def findRootsWithPredicate(
    c: Cmdr,
    root: Position,
    predicate: Callable | None = None,
) -> list[Position]:
    """
    Commands often want to find one or more **roots**, given a position p.
    A root is the position of any node matching a predicate.

    This function formalizes the search order used by the black-beautify
    and rst3 commands, returning a list of zero or more found roots.
    """
    seen = []
    roots = []
    if predicate is None:
        # A useful default predicate for python.
        # pylint: disable=function-redefined

        def predicate(p: Position) -> bool:
            headline = p.h.strip()
            is_python = headline.endswith(('py', 'pyw'))
            return p.isAnyAtFileNode() and is_python

    # 1. Search p's tree.
    for p in root.self_and_subtree(copy=False):
        if predicate(p) and p.v not in seen:
            seen.append(p.v)
            roots.append(p.copy())
    if roots:
        return roots
    # 2. Look up the tree.
    for p in root.parents():
        if predicate(p):
            return [p.copy()]
    # 3. Expand the search if root is a clone.
    clones = []
    for p in root.self_and_parents(copy=False):
        if p.isCloned():
            clones.append(p.v)
    if clones:
        for p in c.all_positions(copy=False):
            if predicate(p):
                # Match if any node in p's tree matches any clone.
                for p2 in p.self_and_subtree():
                    if p2.v in clones:
                        return [p.copy()]
    return []


# @+node:sa.20260908140000.91: *3* util.scanf
def scanf(s: str, pat: str) -> list[str]:
    count = pat.count("%s") + pat.count("%d")
    pat = pat.replace("%s", r"(\S+)")
    pat = pat.replace("%d", r"(\d+)")
    parts = re.split(pat, s)
    result: list[str] = []
    for part in parts:
        if part and len(result) < count:
            result.append(part)
    return result


# @+node:sa.20260908140000.92: *3* util.see_more_lines
def see_more_lines(s: str, ins: int, n: int = 4) -> int:
    """
    Extend index i within string s to include n more lines.
    """
    # Show more lines, if they exist.
    if n > 0:
        for _z in range(n):
            if ins >= len(s):
                break
            i, j = getLine(s, ins)
            ins = j
    return max(0, min(ins, len(s)))


# @+node:sa.20260908140000.93: *3* util.splitLines
def splitLines(s: str) -> list[str]:
    """
    Split s into lines, preserving the number of lines and
    the endings of all lines, including the last line.
    """
    # The guard protects only against s == None.
    return s.splitlines(True) if s else []  # This is a Python string function!


# @+node:sa.20260908140000.94: *3* util.splitlines
splitlines = splitLines


# @+node:sa.20260908140000.95: *3* util.splitLinesAtNewline
def splitLinesAtNewline(s: str) -> list[str]:
    """
    Split lines *only* at '\n', preserving form-feeds and other unusual line-ending characters.
    """
    if not s:
        return []
    lines = s.split(sep='\n')
    if lines[-1] == '':
        lines.pop()
    lines = [f"{z}\n" for z in lines]
    if not s.endswith('\n'):
        lines[-1] = lines[-1][:-1]
    return lines


# @+node:sa.20260908140000.96: *3* util.escaped
def escaped(s: str, i: int) -> bool:
    count = 0
    while i - 1 >= 0 and s[i - 1] == '\\':
        count += 1
        i -= 1
    return (count % 2) == 1


# @+node:sa.20260908140000.97: *3* util.find_line_start
def find_line_start(s: str, i: int) -> int:
    """Return the index in s of the start of the line containing s[i]."""
    if i < 0:
        return 0  # New in Leo 4.4.5: add this defensive code.
    # bug fix: 11/2/02: change i to i+1 in rfind
    i = s.rfind('\n', 0, i + 1)  # Finds the highest index in the range.
    return 0 if i == -1 else i + 1


# @+node:sa.20260908140000.98: *3* util.find_on_line
def find_on_line(s: str, i: int, pattern: str) -> int:
    j = s.find('\n', i)
    if j == -1:
        j = len(s)
    k = s.find(pattern, i, j)
    return k


# @+node:sa.20260908140000.99: *3* util.is_special
def is_special(s: str, directive: str) -> tuple[bool, int]:
    """Return True if the body text contains the @ directive."""
    assert directive and directive[0] == '@'
    # Most directives must start the line.
    lws = directive in ("@others", "@all")
    pattern_s = r'^\s*(%s\b)' if lws else r'^(%s\b)'
    pattern = re.compile(pattern_s % directive, re.MULTILINE)
    if m := re.search(pattern, s):
        return True, m.start(1)
    return False, -1


# @+node:sa.20260908140000.100: *3* util.is_c_id
def is_c_id(ch: str) -> bool:
    return isWordChar(ch)


# @+node:sa.20260908140000.101: *3* util.is_nl
def is_nl(s: str, i: int) -> bool:
    return i < len(s) and (s[i] == '\n' or s[i] == '\r')


# @+node:sa.20260908140000.102: *3* util.is_ws
def is_ws(ch: str) -> bool:
    return ch == '\t' or ch == ' '


# @+node:sa.20260908140000.103: *3* util.is_ws_or_nl
def is_ws_or_nl(s: str, i: int) -> bool:
    return is_nl(s, i) or (i < len(s) and is_ws(s[i]))


# @+node:sa.20260908140000.104: *3* util.match
def match(s: str, i: int, pattern: str) -> bool:
    """
    Return True if the given pattern matches at s[i].

    Warning: this method makes no assumptions about what precedes or
    follows the pattern.
    """
    return bool(s and pattern and s.find(pattern, i, i + len(pattern)) == i)


# @+node:sa.20260908140000.105: *3* util.match_c_word
def match_c_word(s: str, i: int, name: str) -> bool:
    n = len(name)
    return bool(name and name == s[i : i + n] and (i + n == len(s) or not is_c_id(s[i + n])))


# @+node:sa.20260908140000.106: *3* util.match_ignoring_case
def match_ignoring_case(s1: str, s2: str) -> bool:
    return bool(s1 and s2 and s1.lower() == s2.lower())


# @+node:sa.20260908140000.107: *3* util.match_words
def match_words(s: str, i: int, patterns: Sequence[str], *, ignore_case: bool = False) -> bool:
    """Return true if any of the given patterns match at s[i]"""
    return any(match_word(s, i, pattern, ignore_case=ignore_case) for pattern in patterns)


# @+node:sa.20260908140000.108: *3* util.match_word
def match_word(s: str, i: int, pattern: str, *, ignore_case: bool = False) -> bool:
    """Return True if s[i] starts the word given by pattern."""
    if not pattern:
        return False

    # 1. Compute the required boundaries.
    bound1 = isWordChar1(pattern[0])
    bound2 = isWordChar(pattern[-1])

    # 2. Add regex escapes.
    pattern = re.escape(pattern)

    # 3. Add the boundaries.
    if bound1:
        pattern = '\\b' + pattern
    if bound2:
        pattern = pattern + '\\b'

    # Compile the pattern so we can specify the starting position.
    pat = re.compile(pattern, flags=re.I if ignore_case else 0)
    return bool(pat.match(s, i))


# @+node:sa.20260908140000.109: *3* util.skip_blank_lines
def skip_blank_lines(s: str, i: int) -> int:
    while i < len(s):
        if is_nl(s, i):
            i = skip_nl(s, i)
        elif is_ws(s[i]):
            j = skip_ws(s, i)
            if is_nl(s, j):
                i = j
            else:
                break
        else:
            break
    return i


# @+node:sa.20260908140000.110: *3* util.skip_c_id
def skip_c_id(s: str, i: int) -> int:
    n = len(s)
    while i < n and isWordChar(s[i]):
        i += 1
    return i


# @+node:sa.20260908140000.111: *3* util.skip_line
def skip_line(s: str, i: int) -> int:
    if i >= len(s):
        return len(s)
    i = max(i, 0)
    i = s.find('\n', i)
    if i == -1:
        return len(s)
    return i + 1


# @+node:sa.20260908140000.112: *3* util.skip_to_end_of_line
def skip_to_end_of_line(s: str, i: int) -> int:
    if i >= len(s):
        return len(s)
    i = max(i, 0)
    i = s.find('\n', i)
    if i == -1:
        return len(s)
    return i


# @+node:sa.20260908140000.113: *3* util.skip_to_start_of_line
def skip_to_start_of_line(s: str, i: int) -> int:
    if i >= len(s):
        return len(s)
    if i <= 0:
        return 0
    # Don't find s[i], so it doesn't matter if s[i] is a newline.
    i = s.rfind('\n', 0, i)
    if i == -1:
        return 0
    return i + 1


# @+node:sa.20260908140000.114: *3* util.skip_long
def skip_long(s: str, i: int) -> tuple[int, int | None]:
    """
    Scan s[i:] for a valid int.
    Return (i, val) or (i, None) if s[i] does not point at a number.
    """
    val = 0
    i = skip_ws(s, i)
    n = len(s)
    if i >= n or (not s[i].isdigit() and s[i] not in '+-'):
        return i, None
    j = i
    if s[i] in '+-':  # Allow sign before the first digit
        i += 1
    while i < n and s[i].isdigit():
        i += 1
    try:  # There may be no digits.
        val = int(s[j:i])
        return i, val
    except Exception:
        return i, None


# @+node:sa.20260908140000.115: *3* util.skip_nl
def skip_nl(s: str, i: int) -> int:
    """Skips a single "logical" end-of-line character."""
    if match(s, i, "\r\n"):
        return i + 2
    if match(s, i, '\n') or match(s, i, '\r'):
        return i + 1
    return i


# @+node:sa.20260908140000.116: *3* util.skip_non_ws
def skip_non_ws(s: str, i: int) -> int:
    n = len(s)
    while i < n and not is_ws(s[i]):
        i += 1
    return i


# @+node:sa.20260908140000.117: *3* util.skip_pascal_braces
def skip_pascal_braces(s: str, i: int) -> int:
    # No constructs are recognized inside Pascal block comments!
    if i == -1:
        return len(s)
    return s.find('}', i)


# @+node:sa.20260908140000.118: *3* util.skip_python_string
def skip_python_string(s: str, i: int) -> int:
    if match(s, i, "'''") or match(s, i, '"""'):
        delim = s[i] * 3
        i += 3
        k = s.find(delim, i)
        if k > -1:
            return k + 3
        return len(s)
    return skip_string(s, i)


# @+node:sa.20260908140000.119: *3* util.skip_string
def skip_string(s: str, i: int) -> int:
    """Scan forward to the end of a string."""
    delim = s[i]
    i += 1
    assert delim in '\'"', (repr(delim), repr(s))
    n = len(s)
    while i < n and s[i] != delim:
        if s[i] == '\\':
            i += 2
        else:
            i += 1
    if i >= n:
        pass
    elif s[i] == delim:
        i += 1
    return i


# @+node:sa.20260908140000.120: *3* util.skip_to_char
def skip_to_char(s: str, i: int, ch: str) -> tuple[int, str]:
    j = s.find(ch, i)
    if j == -1:
        return len(s), s[i:]
    return j, s[i:j]


# @+node:sa.20260908140000.121: *3* util.skip_ws
def skip_ws(s: str, i: int) -> int:
    n = len(s)
    while i < n and is_ws(s[i]):
        i += 1
    return i


# @+node:sa.20260908140000.122: *3* util.skip_ws_and_nl
def skip_ws_and_nl(s: str, i: int) -> int:
    n = len(s)
    while i < n and (is_ws(s[i]) or is_nl(s, i)):
        i += 1
    return i


# @+node:sa.20260908140000.123: ** util.Git
# @+node:sa.20260908140000.124: *3* util.getModifiedFiles
def getModifiedFiles(repo_path: str) -> list[str]:
    """Return the modified files in the given repo."""
    if not repo_path:
        return []
    old_cwd = os.getcwd()
    os.chdir(repo_path)
    try:
        # We are not checking the return code here, so:
        # pylint: disable=subprocess-run-check
        result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Error running git command")
            return []
        modified_files = []
        for line in result.stdout.split('\n'):
            if line.startswith((' M', 'M ', 'A ', ' A')):
                modified_files.append(line[3:])
        return [os.path.abspath(z) for z in modified_files]
    finally:
        os.chdir(old_cwd)


# @+node:sa.20260908140000.125: *3* util.gitHeadPath
def gitHeadPath(path_s: str) -> str:
    """
    Compute the path to .git/HEAD given the path.
    """
    path = Path(path_s)
    # #1780: Look up the directory tree, looking the .git directory.
    while os.path.exists(path):
        head = os.path.join(path, '.git', 'HEAD')
        if os.path.exists(head):
            return head
        if path == path.parent:
            break
        path = path.parent
    return ''


# @+node:sa.20260908140000.126: ** util.Hooks & Plugins
# @+node:sa.20260908140000.127: *3* util.childrenModifiedSet
childrenModifiedSet: set[VNode] = set()


# @+node:sa.20260908140000.128: *3* util.contentModifiedSet
contentModifiedSet: set[VNode] = set()


# @+node:sa.20260908140000.129: ** util.Indices, Strings, Unicode & Whitespace
# @+node:sa.20260908140000.130: *3* util.convertPythonIndexToRowCol
def convertPythonIndexToRowCol(s: str, i: int) -> tuple[int, int]:
    """Convert index i into string s into zero-based row/col indices."""
    if not s or i <= 0:
        return 0, 0
    i = min(i, len(s))
    # works regardless of what s[i] is
    row = s.count('\n', 0, i)  # Don't include i
    if row == 0:
        return row, i
    prevNL = s.rfind('\n', 0, i)  # Don't include i
    return row, i - prevNL - 1


# @+node:sa.20260908140000.131: *3* util.convertRowColToPythonIndex
def convertRowColToPythonIndex(s: str, row: int, col: int, lines: list[str] | None = None) -> int:
    """Convert zero-based row/col indices into a python index into string s."""
    if row < 0:
        return 0
    if not lines:
        lines = splitLines(s)
    if row >= len(lines):
        return len(s)
    col = min(col, len(lines[row]))
    # A big bottleneck
    prev = 0
    for line in lines[:row]:
        prev += len(line)
    return prev + col


# @+node:sa.20260908140000.132: *3* util.getWord
def getWord(s: str, i: int) -> tuple[int, int]:
    """Return i,j such that s[i:j] is the word surrounding s[i]."""
    if i >= len(s):
        i = len(s) - 1
    i = max(i, 0)
    # Scan backwards.
    while 0 <= i < len(s) and isWordChar(s[i]):
        i -= 1
    i += 1
    # Scan forwards.
    j = i
    while 0 <= j < len(s) and isWordChar(s[j]):
        j += 1
    return i, j


# @+node:sa.20260908140000.133: *3* util.getLine
def getLine(s: str, i: int) -> tuple[int, int]:
    """
    Return i,j such that s[i:j] is the line surrounding s[i].
    s[i] is a newline only if the line is empty.
    s[j] is a newline unless there is no trailing newline.
    """
    if i > len(s):
        i = len(s) - 1
    i = max(i, 0)
    # A newline *ends* the line, so look to the left of a newline.
    j = s.rfind('\n', 0, i)
    if j == -1:
        j = 0
    else:
        j += 1
    k = s.find('\n', i)
    if k == -1:
        k = len(s)
    else:
        k = k + 1
    return j, k


# @+node:sa.20260908140000.134: *3* util.angleBrackets
def angleBrackets(s: str) -> str:
    """Returns < < s > >"""
    lt = "<<"
    rt = ">>"
    return lt + s + rt


# @+node:sa.20260908140000.135: *3* util.virtual_event_name
virtual_event_name = angleBrackets


# @+node:sa.20260908140000.136: *3* util.ensureLeadingNewlines
def ensureLeadingNewlines(s: str, n: int) -> str:
    s = removeLeading(s, '\t\n\r ')
    return ('\n' * n) + s


# @+node:sa.20260908140000.137: *3* util.ensureTrailingNewlines
def ensureTrailingNewlines(s: str, n: int) -> str:
    s = removeTrailing(s, '\t\n\r ')
    return s + '\n' * n


# @+node:sa.20260908140000.138: *3* util.isascii
def isascii(s: str) -> bool:
    # s.isascii() is defined in Python 3.7.
    return all(ord(ch) < 128 for ch in s)


# @+node:sa.20260908140000.139: *3* util.longestCommonPrefix
def longestCommonPrefix(s1: str, s2: str) -> str:
    """Find the longest prefix common to strings s1 and s2."""
    prefix = ''
    for ch in s1:
        if s2.startswith(prefix + ch):
            prefix = prefix + ch
        else:
            return prefix
    return prefix


# @+node:sa.20260908140000.140: *3* util.itemsMatchingPrefixInList
def itemsMatchingPrefixInList(
    s: str, aList: list[str], matchEmptyPrefix: bool = False
) -> tuple[list, str]:
    """This method returns a sorted list items of aList whose prefix is s.

    It also returns the longest common prefix of all the matches.
    """
    if s:
        pmatches = [a for a in aList if a.startswith(s)]
    elif matchEmptyPrefix:
        pmatches = aList[:]
    else:
        pmatches = []
    if pmatches:
        pmatches.sort()
        common_prefix = reduce(longestCommonPrefix, pmatches)
    else:
        common_prefix = ''
    return pmatches, common_prefix


# @+node:sa.20260908140000.141: *3* util.removeLeading
def removeLeading(s: str, chars: str) -> str:
    """Remove all characters in chars from the front of s."""
    i = 0
    while i < len(s) and s[i] in chars:
        i += 1
    return s[i:]


# @+node:sa.20260908140000.142: *3* util.removeTrailing
def removeTrailing(s: str, chars: str) -> str:
    """Remove all characters in chars from the end of s."""
    i = len(s) - 1
    while i >= 0 and s[i] in chars:
        i -= 1
    i += 1
    return s[:i]


# @+node:sa.20260908140000.143: *3* util.stripBrackets
def stripBrackets(s: str) -> str:
    """Strip leading and trailing angle brackets."""
    if s.startswith('<'):
        s = s[1:]
    if s.endswith('>'):
        s = s[:-1]
    return s


# @+node:sa.20260908140000.144: *3* util.unCamel
def unCamel(s: str) -> list[str]:
    """Return a list of sub-words in camelCased string s."""
    result: list[str] = []
    word: list[str] = []
    for ch in s:
        if ch.isalpha() and ch.isupper():
            if word:
                result.append(''.join(word))
            word = [ch]
        elif ch.isalpha():
            word.append(ch)
        elif word:
            result.append(''.join(word))
            word = []
    if word:
        result.append(''.join(word))
    return result


# @+node:sa.20260908140000.145: *3* util.isWordChar
def isWordChar(ch: str) -> bool:
    """Return True if ch should be considered a letter."""
    return bool(ch and (ch.isalnum() or ch == '_'))


# @+node:sa.20260908140000.146: *3* util.isWordChar1
def isWordChar1(ch: str) -> bool:
    return bool(ch and (ch.isalpha() or ch == '_'))


# @+node:sa.20260908140000.147: *3* util.stripBOM
def stripBOM(s_bytes: bytes) -> tuple[str, bytes]:
    """
    If there is a BOM, return (e,s2) where e is the encoding
    implied by the BOM and s2 is the s stripped of the BOM.

    If there is no BOM, return (None,s)

    s must be the contents of a file (a string) read in binary mode.
    """
    table = (
        # Important: test longer bom's first.
        (4, 'utf-32', codecs.BOM_UTF32_BE),
        (4, 'utf-32', codecs.BOM_UTF32_LE),
        (3, 'utf-8',  codecs.BOM_UTF8),
        (2, 'utf-16', codecs.BOM_UTF16_BE),
        (2, 'utf-16', codecs.BOM_UTF16_LE),
    )  # fmt: skip
    if s_bytes:
        for n, e, bom in table:
            assert len(bom) == n
            if bom == s_bytes[: len(bom)]:
                return e, s_bytes[len(bom) :]
    return '', s_bytes


# @+node:sa.20260908140000.148: *3* util.computeLeadingWhitespace
def computeLeadingWhitespace(width: int, tab_width: int) -> str:
    if width <= 0:
        return ""
    if tab_width > 1:
        tabs = int(width / tab_width)
        blanks = int(width % tab_width)
        return ('\t' * tabs) + (' ' * blanks)
    # Negative tab width always gets converted to blanks.
    return ' ' * width


# @+node:sa.20260908140000.149: *3* util.computeLeadingWhitespaceWidth
def computeLeadingWhitespaceWidth(s: str, tab_width: int) -> int:
    w = 0
    for ch in s:
        if ch == ' ':
            w += 1
        elif ch == '\t':
            w += abs(tab_width) - (w % abs(tab_width))
        else:
            break
    return w


# @+node:sa.20260908140000.150: *3* util.computeWidth
def computeWidth(s: str, tab_width: int) -> int:
    w = 0
    for ch in s:
        if ch == '\t':
            w += abs(tab_width) - (w % abs(tab_width))
        elif ch == '\n':  # Bug fix: 2012/06/05.
            break
        else:
            w += 1
    return w


# @+node:sa.20260908140000.151: *3* util.wrap_lines
def wrap_lines(lines: list[str], pageWidth: int, firstLineWidth: int | None = None) -> list[str]:
    """Returns a list of lines, consisting of the input lines wrapped to the given pageWidth."""
    pageWidth = max(pageWidth, 10)
    # First line is special
    if not firstLineWidth:
        firstLineWidth = pageWidth
    firstLineWidth = max(firstLineWidth, 10)
    outputLineWidth = firstLineWidth
    # Sentence spacing
    # This should be determined by some setting, and can only be either 1 or 2
    sentenceSpacingWidth = 1
    assert 0 < sentenceSpacingWidth < 3
    result = []  # The lines of the result.
    line = ""  # The line being formed.  It never ends in whitespace.
    for s in lines:
        i = 0
        while i < len(s):
            assert len(line) <= outputLineWidth  # DTHEIN 18-JAN-2004
            j = skip_ws(s, i)
            k = skip_non_ws(s, j)
            word = s[j:k]
            assert k > i
            i = k
            # DTHEIN 18-JAN-2004: wrap at exactly the text width,
            # not one character less

            wordLen = len(word)
            if line.endswith(('.', '?', '!')):
                space = ' ' * sentenceSpacingWidth
            else:
                space = ' '
            if line and wordLen > 0:
                wordLen += len(space)
            if wordLen + len(line) <= outputLineWidth:
                if wordLen > 0:
                    # @+<< place blank and word on the present line >>
                    # @+node:ekr.20110727091744.15084: *4* << place blank and word on the present line >>
                    if line:
                        # Add the word, preceded by a blank.
                        line = space.join((line, word))
                    else:
                        # Just add the word to the start of the line.
                        line = word
                    # @-<< place blank and word on the present line >>
                else:
                    pass  # discard the trailing whitespace.
            else:
                # @+<< place word on a new line >>
                # @+node:ekr.20110727091744.15085: *4* << place word on a new line >>
                # End the previous line.
                if line:
                    result.append(line)
                    outputLineWidth = pageWidth  # DTHEIN 3-NOV-2002: width for remaining lines
                # Discard the whitespace and put the word on a new line.
                line = word
                # Careful: the word may be longer than pageWidth.
                if len(line) > pageWidth:  # DTHEIN 18-JAN-2004: line can equal pagewidth
                    result.append(line)
                    outputLineWidth = pageWidth  # DTHEIN 3-NOV-2002: width for remaining lines
                    line = ""
                # @-<< place word on a new line >>
    if line:
        result.append(line)
    return result


# @+node:sa.20260908140000.152: *3* util.get_leading_ws
def get_leading_ws(s: str) -> str:
    """Returns the leading whitespace of 's'."""
    i = 0
    n = len(s)
    while i < n and s[i] in (' ', '\t'):
        i += 1
    return s[0:i]


# @+node:sa.20260908140000.153: *3* util.optimizeLeadingWhitespace
def optimizeLeadingWhitespace(line: str, tab_width: int) -> str:
    i, width = skip_leading_ws_with_indent(line, 0, tab_width)
    s = computeLeadingWhitespace(width, tab_width) + line[i:]
    return s


# @+node:sa.20260908140000.154: *3* util.regularizeTrailingNewlines
def regularizeTrailingNewlines(s: str, kind: str) -> None:
    """Kind is 'asis', 'zero' or 'one'."""


# @+node:sa.20260908140000.155: *3* util.removeBlankLines
def removeBlankLines(s: str) -> str:
    lines = splitLines(s)
    lines = [z for z in lines if z.strip()]
    return ''.join(lines)


# @+node:sa.20260908140000.156: *3* util.removeLeadingBlankLines
def removeLeadingBlankLines(s: str) -> str:
    lines = splitLines(s)
    result = []
    remove = True
    for line in lines:
        if remove and not line.strip():
            pass
        else:
            remove = False
            result.append(line)
    return ''.join(result)


# @+node:sa.20260908140000.157: *3* util.removeLeadingWhitespace
def removeLeadingWhitespace(s: str, first_ws: int, tab_width: int) -> str:
    j = 0
    ws = 0
    first_ws = abs(first_ws)
    for ch in s:
        if ws >= first_ws:
            break
        elif ch == ' ':
            j += 1
            ws += 1
        elif ch == '\t':
            j += 1
            ws += abs(tab_width) - (ws % abs(tab_width))
        else:
            break
    if j > 0:
        s = s[j:]
    return s


# @+node:sa.20260908140000.158: *3* util.removeTrailingWs
def removeTrailingWs(s: str) -> str:
    j = len(s) - 1
    while j >= 0 and (s[j] == ' ' or s[j] == '\t'):
        j -= 1
    return s[: j + 1]


# @+node:sa.20260908140000.159: *3* util.skip_leading_ws
def skip_leading_ws(s: str, i: int, ws: int, tab_width: int) -> int:
    count = 0
    while count < ws and i < len(s):
        ch = s[i]
        if ch == ' ':
            count += 1
            i += 1
        elif ch == '\t':
            count += abs(tab_width) - (count % abs(tab_width))
            i += 1
        else:
            break
    return i


# @+node:sa.20260908140000.160: *3* util.skip_leading_ws_with_indent
def skip_leading_ws_with_indent(s: str, i: int, tab_width: int) -> tuple[int, int]:
    """Skips leading whitespace and returns (i, indent),

    - i points after the whitespace
    - indent is the width of the whitespace, assuming tab_width wide tabs."""
    count = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch == ' ':
            count += 1
            i += 1
        elif ch == '\t':
            count += abs(tab_width) - (count % abs(tab_width))
            i += 1
        else:
            break
    return i, count


# @+node:sa.20260908140000.161: *3* util.stripBlankLines
def stripBlankLines(s: str) -> str:
    lines = splitLines(s)
    for i, line in enumerate(lines):
        j = skip_ws(line, 0)
        if j >= len(line):
            lines[i] = ''
        elif line[j] == '\n':
            lines[i] = '\n'
    return ''.join(lines)


# @+node:sa.20260908140000.162: ** util.Logging & Printing
# @+node:sa.20260908140000.163: *3* util.doKeywordArgs
def doKeywordArgs(keys: dict, d: dict | None = None) -> dict:
    """
    Return a result dict that is a copy of the keys dict
    with missing items replaced by defaults in d dict.
    """
    if d is None:
        d = {}
    result = {}
    for key, default_val in d.items():
        isBool = default_val in (True, False)
        val = keys.get(key)
        if isBool and val in (True, 'True', 'true'):
            result[key] = True
        elif isBool and val in (False, 'False', 'false'):
            result[key] = False
        elif val is None:
            result[key] = default_val
        else:
            result[key] = val
    return result


# @+node:sa.20260908140000.164: *3* util.getLastTracebackFileAndLineNumber
def getLastTracebackFileAndLineNumber() -> tuple[str, int]:
    typ, val, tb = sys.exc_info()
    if typ is SyntaxError:
        # IndentationError is a subclass of SyntaxError.
        return val.filename, val.lineno
    # Data is a list of tuples, one per stack entry.
    # Tuples have the form (filename,lineNumber,functionName,text).
    if data := traceback.extract_tb(tb):
        item = data[-1]  # Get the item at the top of the stack.
        filename, n, functionName, text = item
        return filename, n
    # Should never happen.
    return '<string>', 0


# @+node:sa.20260908140000.165: *3* util.is_unique_class_dict
# Keys are strings: g.callers. Values are lists of obj.__class__.__name__.
is_unique_class_dict: dict[str, list[str]] = {}


# @+node:sa.20260908140000.166: *3* util.prettyPrintType
def prettyPrintType(obj: object) -> str:
    if isinstance(obj, str):
        return 'string'
    t: object = type(obj)
    if t in (types.BuiltinFunctionType, types.FunctionType):
        return 'function'
    if t == types.ModuleType:  # noqa
        return 'module'
    if t in [types.MethodType, types.BuiltinMethodType]:
        return 'method'
    # Fall back to a hack.
    t = str(type(obj))
    if t.startswith("<type '"):
        t = t[7:]
    if t.endswith("'>"):
        t = t[:-2]
    return t


# @+node:sa.20260908140000.167: *3* util.print_exception
def print_exception(
    full: bool = True,
    c: Cmdr | None = None,
    flush: bool = False,
    color: str = "red",
) -> tuple[str, int]:
    """Print exception info about the last exception."""
    # val is the second argument to the raise statement.
    typ, val, tb = sys.exc_info()
    if full:
        lines = traceback.format_exception(typ, val, tb)
    else:
        lines = traceback.format_exception_only(typ, val)
    print(''.join(lines), flush=flush)
    try:
        fileName, n = getLastTracebackFileAndLineNumber()
        return fileName, n
    except Exception:
        return "<no file>", 0


# @+node:sa.20260908140000.168: *3* util.printStack
def printStack() -> None:
    traceback.print_stack()


# @+node:sa.20260908140000.169: *3* util.g_unique_message_d
g_unique_message_d: dict[str, bool] = {}


# @+node:sa.20260908140000.170: *3* util.print_unique_message
def print_unique_message(message: str) -> bool:
    """
    Print the given message once. Return True if the message was printed.
    """
    if message not in g_unique_message_d:
        g_unique_message_d[message] = True
        print(message)
        return True
    return False


# @+node:sa.20260908140000.171: *3* util.trace_unique_dict
# Keys are strings: g.callers. Values are lists of str(value).
trace_unique_dict: dict[str, list[str]] = {}


# @+node:sa.20260908140000.172: *3* util.trace_unique_class_dict
# Keys are strings: g.callers. Values are lists of obj.__class__.__name__.
trace_unique_class_dict: dict[str, list[str]] = {}


# @+node:sa.20260908140000.173: ** util.Miscellaneous
# @+node:sa.20260908140000.174: *3* util.CheckVersion
def CheckVersion(
    s1: str,
    s2: str,
    condition: str = ">=",
    delimiter: str = '.',
    trace: bool = False,
) -> bool:
    """
    Return True if the indicated relationship holds.
    Deprecated: not used in Leo's core.
    """
    vals1 = [CheckVersionToInt(s) for s in s1.split(delimiter)]
    n1 = len(vals1)
    vals2 = [CheckVersionToInt(s) for s in s2.split(delimiter)]
    n2 = len(vals2)
    n = max(n1, n2)
    if n1 < n:
        vals1.extend([0 for _i in range(n - n1)])
    if n2 < n:
        vals2.extend([0 for _i in range(n - n2)])
    for cond, val in (
        ('==', vals1 == vals2),
        ('!=', vals1 != vals2),
        ('<', vals1 < vals2),
        ('<=', vals1 <= vals2),
        ('>', vals1 > vals2),
        ('>=', vals1 >= vals2),
    ):
        if condition == cond:
            result = val
            break
    else:
        raise OSError("condition must be one of '>=', '>', '==', '!=', '<', or '<='.")
    return result


# @+node:sa.20260908140000.175: *3* util.CheckVersionToInt
def CheckVersionToInt(s: str) -> int:
    try:
        return int(s)
    except ValueError:
        aList = []
        for ch in s:
            if ch.isdigit():
                aList.append(ch)
            else:
                break
        if aList:
            s = ''.join(aList)
            return int(s)
        return 0


# @+node:sa.20260908140000.176: *3* util.funcToMethod
def funcToMethod(f: Callable, theClass: object, name: str = '') -> None:
    """
    From the Python Cookbook...

    The following method allows you to add a function as a method of
    any class. That is, it converts the function to a method of the
    class. The method just added is available instantly to all
    existing instances of the class, and to all instances created in
    the future.

    The function's first argument should be self.

    The newly created method has the same name as the function unless
    the optional name argument is supplied, in which case that name is
    used as the method name.
    """
    setattr(theClass, name or f.__name__, f)


# @+node:sa.20260908140000.177: *3* util.init_zodb_failed
init_zodb_failed: dict[str, bool] = {}  # Keys are paths, values are True.


# @+node:sa.20260908140000.178: *3* util.init_zodb_db
init_zodb_db: dict[str, Value] = {}  # Keys are paths, values are ZODB.DB instances.


# @+node:sa.20260908140000.179: *3* util.isMacOS
def isMacOS() -> bool:
    return sys.platform == 'darwin'


# @+node:sa.20260908140000.180: *3* util.makeDict
def makeDict(**kwargs: KWargs) -> dict:
    """Returns a Python dictionary from using the optional keyword arguments."""
    return kwargs


# @+node:sa.20260908140000.181: *3* util.pep8_class_name
def pep8_class_name(s: str) -> str:
    """Return the proper class name for s."""
    # Warning: s.capitalize() does not work.
    # It lower cases all but the first letter!
    return ''.join([z[0].upper() + z[1:] for z in s.split('_') if z])


# @+node:sa.20260908140000.182: *3* util.plural
def plural(obj: Any) -> str:
    """
    Return "s" or "" depending on n or len(n).
    """
    if isinstance(obj, int):
        return '' if obj == 1 else 's'
    if isinstance(obj, (list, tuple, str)):
        return '' if len(obj) == 1 else 's'
    return ''


# @+node:sa.20260908140000.183: *3* util.truncate
def truncate(s: str, n: int) -> str:
    """Return s truncated to n characters."""
    if len(s) <= n:
        return s
    # Fail: weird ws.
    s2 = s[: n - 3] + f"...({len(s)})"
    if s.endswith('\n'):
        return s2 + '\n'
    return s2


# @+node:sa.20260908140000.184: ** util.os_path_ Wrappers
# @+node:sa.20260908140000.185: *3* util.glob_glob
def glob_glob(pattern: str) -> list:
    """Return the regularized glob.glob(pattern)"""
    aList = glob.glob(pattern)
    # os.path.normpath does the *reverse* of what we want.
    if isWindows:
        aList = [z.replace('\\', '/') for z in aList]
    return aList


# @+node:sa.20260908140000.186: *3* util.os_path_dirname
def os_path_dirname(path: str) -> str:
    """Return the first half of the pair returned by split(path)."""
    if not path:
        return ''
    path = os.path.dirname(path)
    path = os_path_normslashes(path)
    return path


# @+node:sa.20260908140000.187: *3* util.os_path_getmtime
def os_path_getmtime(path: str) -> float:
    """Return the modification time of a file for a given path."""
    if not path:
        return 0
    try:
        return os.path.getmtime(path)
    except Exception:
        return 0


# @+node:sa.20260908140000.188: *3* util.os_path_getsize
def os_path_getsize(path: str) -> int:
    """Return the size of path."""
    return os.path.getsize(path) if path else 0


# @+node:sa.20260908140000.189: *3* util.os_path_isabs
def os_path_isabs(path: str) -> bool:
    """Return True if path is an absolute path."""
    return os.path.isabs(path) if path else False


# @+node:sa.20260908140000.190: *3* util.os_path_isdir
def os_path_isdir(path: str) -> bool:
    """Return True if the path is a directory."""
    return os.path.isdir(path) if path else False


# @+node:sa.20260908140000.191: *3* util.os_path_isfile
def os_path_isfile(path: str) -> bool:
    """Return True if path is a file."""
    return os.path.isfile(path) if path else False


# @+node:sa.20260908140000.192: *3* util.os_path_join
def os_path_join(*args: Args, **kwargs: KWargs) -> str:
    """
    Wrap os.path.join, *without* finalizing the result.
    """
    uargs = [z for z in args if z]
    if not uargs:
        return ''
    path = os.path.join(*uargs)
    path = os_path_normslashes(path)
    return path


# @+node:sa.20260908140000.193: *3* util.os_path_normcase
def os_path_normcase(path: str) -> str:
    """Normalize the path's case."""
    if not path:
        return ''
    path = os.path.normcase(path)
    path = os_path_normslashes(path)
    return path


# @+node:sa.20260908140000.194: *3* util.os_path_normslashes
def os_path_normslashes(path: str) -> str:
    """
    Convert backslashes to forward slashes (Windows only).

    In effect, this convert Windows paths to POSIX paths.
    """
    if not path:
        return ''
    return path.replace('\\', '/') if isWindows else path


# @+node:sa.20260908140000.195: *3* util.os_path_realpath
def os_path_realpath(path: str) -> str:
    """Return the canonical path of the specified filename, eliminating any
    symbolic links encountered in the path (if they are supported by the
    operating system).
    """
    if not path:
        return ''
    path = os.path.realpath(path)
    path = os_path_normslashes(path)
    return path


# @+node:sa.20260908140000.196: ** util.Parsing & Tokenizing
# @+node:sa.20260908140000.197: *3* util.createTopologyList
def createTopologyList(c: Cmdr, root: Position | None = None, useHeadlines: bool = False) -> list:
    """Creates a list describing a node and all its descendants"""
    if not root:
        root = c.rootPosition()
    v = root
    aList: list
    if useHeadlines:
        aList = [(v.numberOfChildren(), v.headString())]
    else:
        aList = [v.numberOfChildren()]
    child = v.firstChild()
    while child:
        aList.append(createTopologyList(c, child, useHeadlines))
        child = child.next()
    return aList


# @+node:sa.20260908140000.198: *3* util.getDocString
def getDocString(s: str) -> str:
    """Return the text of the first docstring found in s."""
    tags = ('"""', "'''")
    tag1, tag2 = tags
    i1, i2 = s.find(tag1), s.find(tag2)
    if i1 == -1 and i2 == -1:
        return ''
    if i1 > -1 and i2 > -1:
        i = min(i1, i2)
    else:
        i = max(i1, i2)
    tag = s[i : i + 3]
    assert tag in tags
    j = s.find(tag, i + 3)
    if j > -1:
        return s[i + 3 : j]
    return ''


# @+node:sa.20260908140000.199: *3* util.getDocStringForFunction
def getDocStringForFunction(func: Callable) -> str:
    """Return the docstring for a function that creates a Leo command."""

    def name(func: Callable) -> str:
        return str(func.__name__) if hasattr(func, '__name__') else '<no __name__>'

    def get_defaults(func: Callable, i: int) -> Value:
        defaults = inspect.getfullargspec(func)[3]
        return defaults[i] if defaults else ''

    # Fix bug 1251252: https://bugs.launchpad.net/leo-editor/+bug/1251252
    # Minibuffer commands created by mod_scripting.py have no docstrings.
    # Do special cases first.

    if name(func) == 'minibufferCallback':
        func = get_defaults(func, 0)
        s = getattr(func, '__doc__', None)
        if s and s.strip():
            return s
    if name(func) == 'commonCommandCallback':
        script = get_defaults(func, 1)
        if s := getDocString(script):  # Do a text scan for the function.
            return s
    # Now the general cases.  Prefer __doc__ to docstring()
    s = getattr(func, '__doc__', None)
    if s and s.strip():
        return s
    s = getattr(func, 'docstring', None)
    if s and s.strip():
        return s
    return ''


# @+node:sa.20260908140000.200: ** util.Scripting
# @+node:sa.20260908140000.201: *3* util.exec_file
def exec_file(path: str, d: dict[str, Value], script: str = '') -> None:
    """Simulate python's execfile statement for python 3."""
    if not script:
        with open(path) as f:
            script = f.read()
    exec(compile(script, path, 'exec'), d)


# @+node:sa.20260908140000.202: *3* util.findNodeAnywhere
def findNodeAnywhere(c: Cmdr, headline: str, exact: bool = True) -> Position | None:
    h = headline.strip()
    for p in c.all_unique_positions(copy=False):
        if p.h.strip() == h:
            return p.copy()
    if not exact:
        for p in c.all_unique_positions(copy=False):
            if p.h.strip().startswith(h):
                return p.copy()
    return None


# @+node:sa.20260908140000.203: *3* util.findNodeInChildren
def findNodeInChildren(c: Cmdr, p: Position, headline: str, exact: bool = True) -> Position | None:
    """Search for a node in v's tree matching the given headline."""
    p1 = p.copy()
    h = headline.strip()
    for p in p1.children():
        if p.h.strip() == h:
            return p.copy()
    if not exact:
        for p in p1.children():
            if p.h.strip().startswith(h):
                return p.copy()
    return None


# @+node:sa.20260908140000.204: *3* util.findNodeInTree
def findNodeInTree(c: Cmdr, p: Position, headline: str, exact: bool = True) -> Position | None:
    """Search for a node in v's tree matching the given headline."""
    h = headline.strip()
    p1 = p.copy()
    for p in p1.subtree():
        if p.h.strip() == h:
            return p.copy()
    if not exact:
        for p in p1.subtree():
            if p.h.strip().startswith(h):
                return p.copy()
    return None


# @+node:sa.20260908140000.205: *3* util.findTopLevelNode
def findTopLevelNode(c: Cmdr, headline: str, exact: bool = True) -> Position | None:
    h = headline.strip()
    for p in c.rootPosition().self_and_siblings(copy=False):
        if p.h.strip() == h:
            return p.copy()
    if not exact:
        for p in c.rootPosition().self_and_siblings(copy=False):
            if p.h.strip().startswith(h):
                return p.copy()
    return None


# @+node:sa.20260908140000.206: ** util.Sentinels
# @+node:sa.20260908140000.207: *3* util.is_invisible_sentinel
def is_invisible_sentinel(delims: tuple[str, str, str], contents: list[str], i: int) -> bool:
    """
    delims are the comment delims in effect.

    contents is the contents *with* sentinels of an external file that
    normally does *not* have sentinels.

    Return True if contents[i] corresponds to a line visible in the outline
    but not the external file.
    """
    delim1 = delims[0] or delims[1]

    # Get previous line, to test for previous @verbatim sentinel.
    line1 = contents[i - 1] if i > 0 else ''  # previous line.
    line2 = contents[i]
    if not is_sentinel(line2, delims):
        return False  # Non-sentinels are visible everywhere.

    # Strip off the leading sentinel comment. Works for blackened sentinels.
    s1 = line1.strip()[len(delim1) :]
    s2 = line2.strip()[len(delim1) :]
    if s1.startswith('@verbatim'):
        return False  # *This* line is visible in the outline.
    if s2.startswith('@@'):
        # Directives are visible in the outline, but not the external file.
        return True
    if s2.startswith(('@+others', '@+<<')):
        # @verbatim
        # @others and section references are visible everywhere.
        return True
    # Not visible anywhere. For example, @+leo, @-leo, @-others, @+node, @-node.
    return True


# @+node:sa.20260908140000.208: *3* util.is_sentinel
def is_sentinel(line: str, delims: tuple[str, str, str]) -> bool:
    """
    Return True if line starts with a sentinel comment.

    Leo 6.7.2: Support blackened sentinels.
    """
    delim1, delim2, delim3 = delims
    # Defensive code. Make *sure* delim has no trailing space.
    if delim1:
        delim1 = delim1.rstrip()
    line = line.lstrip()
    if delim1:
        sentinel1 = delim1 + '@'
        sentinel2 = delim1 + ' @'
        return line.startswith((sentinel1, sentinel2))
    if delim2 and delim3:
        sentinel1 = delim2 + '@'
        sentinel2 = delim2 + ' @'
        if sentinel1 in line:
            i = line.find(sentinel1)
            j = line.find(delim3)
            return 0 == i < j
        if sentinel2 in line:
            i = line.find(sentinel2)
            j = line.find(delim3)
            return 0 == i < j
    # #3458: This case *can* happen when the user changes an @language directive.
    #        Don't bother trying to recover.
    return False


# @+node:sa.20260908140000.209: ** util.Urls & UNLs
# @+node:sa.20260908140000.210: *3* util.es_clickable_link
def es_clickable_link(
    c: Cmdr, p: Position, line_number: int, message: str
) -> None:  # pragma: no cover
    """
    Write a clickable message to the given line number of p.b.

    Negative line numbers indicate global lines.

    """
    # Not used in Leo's core.
    unl = p.get_UNL()
    c.frame.log.put(message.strip() + '\n', nodeLink=f"{unl}::{line_number}")


# @+node:sa.20260908140000.211: *3* util.find_gnx_pat
find_gnx_pat = re.compile(r'^(.*)::([-\d]+)?$')


# @+node:sa.20260908140000.212: *3* util.findGnx
def findGnx(gnx: str, c: Cmdr) -> Position | None:
    """
    gnx: the gnx part of a gnx-based unl.

    The gnx part may be the actual gnx or <actual-gnx>::<line-number>

    Return the first position in c with the actual gnx.
    """
    # Get the actual gnx and line number.
    n: int = 0  # The line number.
    if m := find_gnx_pat.match(gnx):
        # Get the actual gnx and line number.
        gnx = m.group(1)
        try:
            n = int(m.group(2))
        except (TypeError, ValueError):
            pass
    # Search forwards, setting p2.
    for p in c.all_unique_positions():
        if p.gnx == gnx:
            if n is None:
                return p
            p2, offset = c.gotoCommands.find_file_line(-n, p)
            return p2 or p
    return None


# @+node:sa.20260908140000.213: *3* util.valid_unl_pattern
# unls must contain a (possible empty) file part followed by something else.
valid_unl_pattern = re.compile(r"(unl:gnx|unl|file)://(.*?)#.+")


# @+node:sa.20260908140000.214: *3* util.isValidUnl
def isValidUnl(unl_s: str) -> bool:
    """Return true if the given unl is valid."""
    return bool(valid_unl_pattern.match(unl_s))


# @+node:sa.20260908140000.215: *3* util.isValidUrl
def isValidUrl(url: str) -> bool:
    """Return true if url *looks* like a valid url."""
    table = (
        'file',
        'ftp',
        'gopher',
        'hdl',
        'http',
        'https',
        'imap',
        'mailto',
        'mms',
        'news',
        'nntp',
        'prospero',
        'rsync',
        'rtsp',
        'rtspu',
        'sftp',
        'shttp',
        'sip',
        'sips',
        'snews',
        'svn',
        'svn+ssh',
        'telnet',
        'wais',
    )
    if not url:
        return False  # pragma: no cover (defensive)
    if isValidUnl(url):
        return True
    if url.startswith('@'):
        return False
    parsed: tuple = urlparse.urlparse(url)
    scheme = parsed.scheme
    for s in table:
        if scheme.startswith(s):
            return True
    return False


# @+node:sa.20260908140000.216: *3* util.unquoteUrl
def unquoteUrl(url: str) -> str:  # pragma: no cover
    """Replace escaped characters (especially %20, by their equivalent)."""
    return urllib.parse.unquote(url)


# @+node:sa.20260908140000.217: *3* util.file_part_pattern
file_part_pattern = re.compile(r'//(.*?)#.*')


# @+node:sa.20260908140000.218: *3* util.getUNLFilePart
def getUNLFilePart(s: str) -> str:
    """Return the file part of a unl, that is, everything *between* '//' and '#'."""
    # Strip the prefix if it exists.
    for prefix in ('unl:gnx:', 'unl:', 'file:'):
        if s.startswith(prefix):
            s = s[len(prefix) :]
            break
    m = file_part_pattern.match(s)
    return m.group(1) if m else ''


# @+node:sa.20260908140000.219: *3* util.path_data_pattern
path_data_pattern = re.compile(r'(.+?):\s*(.+)')


# @-others
# @@language python
# @@tabwidth -4
# @-leo
