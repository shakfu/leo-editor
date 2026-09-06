# @+leo-ver=5-thin
# @+node:sa.20260908160000.1: * @file ../leolib/state.py
"""
The process-wide flags Leo rebinds while it runs.

Everything else in leolib is a function of its arguments. These five names are
not: something assigns them at run time, and every reader has to see the new
value. That makes them the one thing that cannot simply be copied from module
to module, and it is why leoGlobals could not be split cleanly around them.

The problem in concrete terms: leoGlobals re-exports leo.leolib.util by value,
so if `unitTesting` lived in util, `g.unitTesting = True` would rebind
leoGlobals' name and util's readers would go on seeing False. That is not a
thought experiment -- it happened, and surfaced three test files later as a
test whose working directory had been deleted, because g.chdir returns early
during unit tests and had quietly stopped doing so.

So the flags live here, in one module, and are read through the module rather
than imported by name:

    from leo.leolib import state
    if state.unitTesting: ...        # right: late-bound
    from leo.leolib.state import unitTesting   # wrong: a snapshot

leoGlobals presents them as g.unitTesting and friends, reading and writing
through to this module, so no caller had to change. See the module-class
properties at the end of leoGlobals.py.
"""

from typing import Any

from leo.leolib import language_data

# @+others
# @+node:sa.20260908160000.2: ** state: the flags
# True while Leo's unit tests are running. Guards anything that would touch
# the environment the tests run in -- g.chdir is the classic case.
unitTesting: bool = False

# True while g.executeScript is running a script.
inScript: bool = False

# True: leoApp loads a null gui by default. Set by leoBridge.
in_bridge: bool = False

# True while running as leoserver.
in_leo_server: bool = False

# True when hosted by VS Code (#2098).
in_vs_code: bool = False

# @+node:sa.20260908160000.3: ** state: the reporting seam
# Where log output goes, and what colour an error is.
#
# util.es puts a message "to the log pane", which is a thing only a running
# editor has. Rather than have the model ask g.app for one -- the dependency
# this whole refactor exists to remove -- it calls whatever is installed here.
# leoGlobals installs Leo's real log writer as it loads, so inside Leo nothing
# changes. With no host, log_sink is None and es is a no-op, which is what
# leolib already did in effect: its minimal app has no gui and no log, so
# every message ended up on a list nobody read.
#
# Note what does *not* go through the sink: es_print still prints to stdout,
# so a library caller sees warnings and errors on the console.
log_sink: Any = None

# Returns the configured colour for errors, or None. Leo reads it from the
# outline's settings; without a host, callers fall back to 'red'.
error_color_hook: Any = None

# @+node:sa.20260909120000.1: ** state: the plugin seam
# Who handles g.doHook, or None if nobody does.
#
# Called as hook_dispatcher(tag, kwargs). leoGlobals installs Leo's real
# dispatcher as it loads -- the one that consults c.hookFunction, then
# app.hookFunction, then the plugins controller, and disables itself on error.
# With no host there is no plugin system, so doHook returns None, which is what
# it already did for leolib: its minimal app sets enablePlugins to False for
# exactly this reason.
hook_dispatcher: Any = None

# Registers a command with the commanders that already exist, and reports
# whether it could: an @g.command decorator runs at import time, often before
# there is any application at all, and the caller skips its bookkeeping when
# nothing was registered. leoGlobals installs Leo's version.
command_registrar: Any = None

# The module `g` refers to. ivars2instance can be asked for an attribute of it
# by name -- 'g' is a legal base in an ivars list, though nothing in Leo uses
# it -- and util has no other way to answer.
globals_module: Any = None

# @+node:sa.20260909100000.1: ** state: the language tables
# What a .py file is written in, and what a Python comment starts with. The
# readers and writers of external files cannot do their job without this, and
# they must be able to do it with no application running -- which is why the
# data sits in language_data and the live copies sit here.
#
# LeoApp and leolib's minimal app both point g.app.language_delims_dict and its
# siblings at these very dicts, not at copies, so a user who adds a language
# through the app adds it for the readers too. Mutate them; never rebind them.
language_delims_dict: dict[str, str] = dict(language_data.language_delims_dict)
extension_dict: dict[str, str] = dict(language_data.extension_dict)
language_extension_dict: dict[str, str] = dict(language_data.language_extension_dict)

# Languages that are spelled differently but coloured as something else.
# Keys are the new names, values are languages that exist in leo/modes.
# isValidLanguage consults it, so a reader has to be able to see it.
delegate_language_dict: dict[str, str] = {
    'codon': 'python',
    'elisp': 'lisp',
    'glsl': 'c',
    'handlebars': 'html',
    'hbs': 'html',
    'less': 'css',
    'katex': 'html',  # Leo 6.8.4
    'mathjax': 'html',  # Leo 6.8.4
    'toml': 'ini',
}

# Extensions associated with a mode file rather than a language, used by
# importCommands.languageForExtension. 'none' tells the unit tests that no
# extension file exists. Defined on LeoApp until it moved here with the rest.
extra_extension_dict: dict[str, str] = {
    'pod': 'perl',
    'unknown_language': 'none',
    'w': 'c',
}

# @+node:sa.20260909100000.2: ** state: the directory last opened from
# Set by util.setGlobalOpenDir when Leo reads or writes a file, and offered as
# the starting directory by the file dialogs. A fact about the session rather
# than about any window, which is why the model may set it without a gui.
# LeoApp.globalOpenDir is a property over this name.
global_open_dir: str = ''

# @+node:sa.20260908160000.4: ** state: translateString's flag
# True: util.translateString upper-cases everything instead of translating it.
# A debugging aid that lives on g.app in Leo, where leoApp's own comment says
# it is "never set to True". It is mirrored here because every printed message
# goes through translateString, and that is not a path the model should be
# reaching for the application on. LeoApp.translateToUpperCase is a property
# over this name, so the two cannot drift.
translate_to_upper_case: bool = False
# @-others
# @@language python
# @@tabwidth -4
# @-leo
