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
# @-others
# @@language python
# @@tabwidth -4
# @-leo
