# @+leo-ver=5-thin
# @+node:sa.20260907120000.1: * @file leoPluginRegistry.py
"""
Registration of the importer and writer plugins.

An @auto node is read by an importer and written by a writer, one per language,
in leo/plugins/importers and leo/plugins/writers. Both are chosen through
dispatch tables that LoadManager built while starting the application, which
meant reading an @auto node required a running Leo.

None of the 34 modules imports anything from a front end -- they are language
parsers, model machinery that lives under leo/plugins for historical reasons
rather than architectural ones. So this is the registration, taking the object
that holds the tables as an argument instead of reaching for g.app. LoadManager
calls it while starting Leo; leolib calls it with its own minimal app.

See LEO_REFACTOR.md.
"""

# @+<< leoPluginRegistry imports >>
# @+node:sa.20260907120000.2: ** << leoPluginRegistry imports >>
from __future__ import annotations
import importlib
from types import ModuleType
from typing import Any

# util, not leoGlobals: this module is part of Leo's model, and the model
# no longer needs anything leoGlobals owns. util offers every name it uses,
# including g.app and the host flags, which are properties over
# leo.leolib.state and so read and write exactly as they did.
from leo.leolib import util as g
# @-<< leoPluginRegistry imports >>


# @+others
# @+node:sa.20260907120000.3: ** leoPluginRegistry: importers
def create_importer_data(app: Any) -> None:
    """Create the data structures describing importer plugins."""
    # Allow plugins to be defined in ~/.leo/plugins.
    for pattern in (
        # ~/.leo/plugins.
        g.finalize_join(app.homeDir, '.leo', 'plugins'),
        # leo/plugins/importers.
        g.finalize_join(app.loadDir, '..', 'plugins', 'importers', '*.py'),
    ):
        filenames = g.glob_glob(pattern)
        for filename in filenames:
            sfn = g.shortFileName(filename)
            if sfn.endswith('.py') and sfn != '__init__.py':
                try:
                    module_name = sfn[:-3]
                    language_name = 'rst' if module_name == 'leo_rst' else module_name
                    # Important: use importlib to give imported modules their fully qualified names.
                    m = importlib.import_module(f"leo.plugins.importers.{module_name}")
                    if module_name != 'base_importer':
                        app.importerModulesDict[language_name] = m
                        parse_importer_dict(app, sfn, m)
                except Exception:
                    g.warning(f"can not import leo.plugins.importers.{module_name}")
                    g.printObj(filenames)

    # Leo 6.7.8: Create app.importerClassesDict.
    for language_name in app.importerModulesDict:
        m = app.importerModulesDict.get(language_name, '')
        for z in dir(m):
            # A hack: all importer subclasses should end with '_Importer'.
            if z.endswith('_Importer'):
                if importer_class := getattr(m, z, None):
                    app.importerClassesDict[language_name] = importer_class
                    break
        else:
            g.trace(f"No importer for {language_name}")


def parse_importer_dict(app: Any, sfn: str, m: ModuleType) -> None:
    """
    Set entries in app.classDispatchDict, app.atAutoDict and
    app.atAutoNames using entries in m.importer_dict.
    """
    if importer_d := getattr(m, 'importer_dict', None):
        at_auto = importer_d.get('@auto', [])
        scanner_func = importer_d.get('func', None)
        # scanner_name = scanner_class.__name__
        extensions = importer_d.get('extensions', [])
        if at_auto:
            # Make entries for each @auto type.
            d = app.atAutoDict
            for s in at_auto:
                d[s] = scanner_func
                app.atAutoDict[s] = scanner_func
                app.atAutoNames.add(s)
        if extensions:
            # Make entries for each extension.
            d = app.classDispatchDict
            for ext in extensions:
                d[ext] = scanner_func  # importer_d.get('func')#scanner_class
    elif sfn not in (
        # This is a base class, not a real plugin.
        'base_importer.py',
    ):
        g.warning(f"leo/plugins/importers/{sfn} has no importer_dict")


# @+node:sa.20260907120000.4: ** leoPluginRegistry: writers
def create_writers_data(app: Any) -> None:
    """Create the data structures describing writer plugins."""
    # Do *not* remove this trace.
    trace = False and 'createWritersData' not in app.debug_dict
    if trace:
        # Suppress multiple traces.
        app.debug_dict['createWritersData'] = True
    app.writersDispatchDict = {}
    app.atAutoWritersDict = {}

    # Allow plugins to be defined in ~/.leo/plugins.
    for pattern in (
        # ~/.leo/plugins.
        g.finalize_join(app.homeDir, '.leo', 'plugins'),
        # leo/plugins/writers
        g.finalize_join(app.loadDir, '..', 'plugins', 'writers', '*.py'),
    ):
        for filename in g.glob_glob(pattern):
            sfn = g.shortFileName(filename)
            if sfn.endswith('.py') and sfn != '__init__.py':
                try:
                    # Important: use importlib to give imported modules their fully qualified names.
                    m = importlib.import_module(f"leo.plugins.writers.{sfn[:-3]}")
                    parse_writer_dict(app, sfn, m)
                except Exception:
                    g.es_exception()
                    g.warning(f"can not import leo.plugins.writers.{sfn}")
    if trace:
        g.trace('LM.writersDispatchDict')
        g.printDict(app.writersDispatchDict)
        g.trace('LM.atAutoWritersDict')
        g.printDict(app.atAutoWritersDict)


def parse_writer_dict(app: Any, sfn: str, m: ModuleType) -> None:
    """
    Set entries in app.writersDispatchDict and app.atAutoWritersDict
    using entries in m.writers_dict.
    """
    if writer_d := getattr(m, 'writer_dict', None):
        at_auto = writer_d.get('@auto', [])
        scanner_class = writer_d.get('class', None)
        extensions = writer_d.get('extensions', [])
        if at_auto:
            # Make entries for each @auto type.
            d = app.atAutoWritersDict
            for s in at_auto:
                aClass = d.get(s)
                if aClass and aClass != scanner_class:
                    g.trace(f"{sfn}: duplicate {s} class {aClass.__name__} in {m.__file__}:")
                else:
                    d[s] = scanner_class
                    app.atAutoNames.add(s)
        if extensions:
            # Make entries for each extension.
            d = app.writersDispatchDict
            for ext in extensions:
                aClass = d.get(ext)
                if aClass and aClass != scanner_class:
                    g.trace(f"{sfn}: duplicate {ext} class", aClass, scanner_class)
                else:
                    d[ext] = scanner_class
    elif sfn not in ('basewriter.py',):
        g.warning(f"leo/plugins/writers/{sfn} has no writer_dict")


# @+node:sa.20260907120000.5: ** leoPluginRegistry: dispatch
def scanner_for_at_auto(app: Any, p: Any) -> Any:
    """Return the scanner function for p, an @auto node, or None."""
    d = app.atAutoDict
    for key in d:
        func = d.get(key)
        if func and g.match_word(p.h, 0, key):
            return func
    return None


def scanner_for_ext(app: Any, ext: str) -> Any:
    """Return the scanner function for the given file extension, or None."""
    return app.classDispatchDict.get(ext)


# @-others
# @@language python
# @@tabwidth -4
# @-leo
