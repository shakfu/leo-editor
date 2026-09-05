# @+leo-ver=5-thin
# @+node:sa.20260908130000.1: * @file ../leolib/__init__.py
"""
leolib: Leo's outline model and file machinery, with no view of any kind.

This file is deliberately almost empty. The package holds two modules:

    leo.leolib.util   Leo's dependency-free layer: string, path, encoding and
                      scanning helpers that import nothing, from Leo or
                      anywhere else in Leo's stack. leo.core.leoGlobals
                      re-exports every name in it, so `g.splitLines` and
                      `util.splitLines` are the same function.

    leo.leolib.api    The library itself: open_outline, save, tangle and the
                      rest. See its docstring.

The API is reached lazily, through the module __getattr__ below, because
leoGlobals imports leo.leolib.util -- and importing any module in a package
runs the package's __init__ first. If this file imported api, then importing
leoGlobals would import leolib would import leoGlobals, half-built. Keeping
__init__ empty of imports is what makes the layering possible at all.

    from leo import leolib
    outline = leolib.open_outline('myfile.leo')
"""

import importlib
from typing import Any

# The package's own modules. See __getattr__.
_SUBMODULES = ('api', 'state', 'util')

__all__ = [
    'Outline',
    'ensure_app',
    'new_outline',
    'open_outline',
    'read_external_files',
    'save',
    'tangle',
    'to_xml',
    'write_external_files',
]


# @+others
# @+node:sa.20260908130000.2: ** leolib.__getattr__
def __getattr__(name: str) -> Any:
    """
    Load leolib.api on first use. See this module's docstring.

    import_module, not `from leo.leolib import api`: the `from` form asks the
    package for an attribute named 'api', which lands back here and recurses
    until the stack runs out.
    """
    # Never answer for a submodule. `from leo.leolib import state` asks the
    # package for the attribute first, and answering it by importing api would
    # drag leoGlobals in -- which imports util, which is what asked. That is a
    # circular import, and it fails at the least helpful moment: partway
    # through building util.
    if name.startswith('_') or name in _SUBMODULES:
        raise AttributeError(name)
    api = importlib.import_module('leo.leolib.api')
    try:
        value = getattr(api, name)
    except AttributeError:
        raise AttributeError(f"module 'leo.leolib' has no attribute {name!r}") from None
    globals()[name] = value  # Only the first access pays for the import.
    return value


# @+node:sa.20260908130000.3: ** leolib.__dir__
def __dir__() -> list[str]:
    return sorted(set(__all__) | set(globals()))


# @-others
# @@language python
# @@tabwidth -4
# @-leo
