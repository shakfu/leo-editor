# @+leo-ver=5-thin
# @+node:sa.20260908150000.1: * @file ../unittests/leolib/test_leolib_util.py
"""
Tests of leo.leolib.util: Leo's app-independent layer.

util holds the half of leoGlobals that never reads g.app. That is a property
nothing enforces on its own -- the natural thing to do when a helper needs a
setting, a language table or the log is to reach for g.app, and the first
person to do it here would put the dependency back without noticing. Hence
these tests.
"""

# @+<< test_leolib_util imports >>
# @+node:sa.20260908150000.2: ** << test_leolib_util imports >>
import ast
import os
import pathlib
import subprocess
import sys
import textwrap
import types
import unittest
# @-<< test_leolib_util imports >>

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
UTIL_PY = os.path.join(REPO, 'leo', 'leolib', 'util.py')


# @+others
# @+node:sa.20260908150000.3: ** class TestLeolibUtil
class TestLeolibUtil(unittest.TestCase):
    """util must stay independent of g.app, and of Leo."""

    # @+others
    # @+node:sa.20260908150000.4: *3* TestLeolibUtil.test_util_never_reads_g_app
    def test_util_never_reads_g_app(self):
        """
        No code in util may read g.app.

        This is the whole property the module is named for. g.app carries the
        gui, the open windows, the settings and the plugin controller, so a
        function that reads it needs a running Leo, and putting one here would
        quietly make the layer app-dependent again.

        Checked on the parse tree, not the text, so that the prose in this
        file's own docstrings -- which has to name g.app to explain itself --
        does not count.
        """
        with open(UTIL_PY) as f:
            tree = ast.parse(f.read())
        bad = [
            f'line {n.lineno}'
            for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id == 'g'
        ]
        self.assertEqual(bad, [], f"util reaches for g: {bad}")
        names = [
            f'line {n.lineno}' for n in ast.walk(tree) if isinstance(n, ast.Name) and n.id == 'app'
        ]
        self.assertEqual(names, [], f"util names 'app': {names}")

    # @+node:sa.20260908150000.5: *3* TestLeolibUtil.test_util_imports_no_leo_module
    def test_util_imports_no_leo_module(self):
        """
        Importing util must pull in nothing from Leo but leolib.state.

        leoGlobals imports util, so anything util imported back would be a
        cycle -- and the point of the split is that the arrow points one way.
        state is the exception, and it earns it by importing nothing but
        language_data, which imports nothing at all: state exists precisely so
        that util can read Leo's mutable flags and language tables without
        reaching for leoGlobals. A subprocess, because any other test
        in this process has already imported half of Leo.
        """
        out = subprocess.run(
            [
                sys.executable,
                '-c',
                textwrap.dedent("""
                import sys
                import leo.leolib.util
                print(sorted(
                    m for m in sys.modules
                    if m.startswith('leo') and not hasattr(sys.modules[m], '__path__')))
            """),
            ],
            capture_output=True,
            text=True,
            cwd=REPO,
            env=dict(os.environ, PYTHONPATH=REPO),
            timeout=120,
        )
        self.assertEqual(out.returncode, 0, out.stderr)
        loaded = eval(out.stdout.strip())  # noqa: S307
        self.assertEqual(
            loaded,
            ['leo.leolib.language_data', 'leo.leolib.state', 'leo.leolib.util'],
            f"util dragged in Leo modules: {loaded}",
        )

    # @+node:sa.20260908150000.6: *3* TestLeolibUtil.test_leoGlobals_reexports_every_name
    def test_leoGlobals_reexports_every_name(self):
        """
        g.<name> and util.<name> must be the same object, for every name.

        Nothing in Leo was changed to call util directly: the split is supposed
        to be invisible to callers. It stays invisible only while leoGlobals
        re-exports the whole module, so a name added to util and forgotten in
        leoGlobals' import list would be missing from g.
        """
        from leo.core import leoGlobals as g
        from leo.leolib import util

        missing, different = [], []
        for name in dir(util):
            if name.startswith('_') or name in ('TYPE_CHECKING', 'annotations'):
                continue
            value = getattr(util, name)
            if isinstance(value, types.ModuleType):
                continue  # A stdlib module util imports, not a name it defines.
            if getattr(value, '__module__', None) not in (None, 'leo.leolib.util'):
                continue  # An import of util's own, not a name it defines.
            if not hasattr(g, name):
                missing.append(name)
            elif getattr(g, name) is not value:
                different.append(name)
        self.assertEqual(missing, [], f"leoGlobals does not re-export: {missing}")
        self.assertEqual(different, [], f"g.<name> is not util.<name>: {different}")

    # @+node:sa.20260908150000.7: *3* TestLeolibUtil.test_mutable_globals_stayed_behind
    def test_mutable_globals_stayed_behind(self):
        """
        A module global that anything rebinds at run time must not be in util.

        leoGlobals re-exports by value, so a moved global would leave two
        copies: `g.unitTesting = True` would set leoGlobals' and util's readers
        would go on seeing False. That is not hypothetical -- it is what
        happened when unitTesting moved, and it showed up three test files
        later as a deleted working directory, because g.chdir returns early
        during tests and had stopped doing so.
        """
        from leo.leolib import util

        for name in (
            'app',
            'unitTesting',
            'inScript',
            'in_bridge',
            'in_leo_server',
            'in_vs_code',
            'tree_popup_handlers',
            'console_encoding',
        ):
            self.assertFalse(
                hasattr(util, name), f"{name} is rebound at run time and cannot live in util"
            )

    # @+node:sa.20260908190000.2: *3* TestLeolibUtil.test_runtime_patches_hit_both_modules
    def test_runtime_patches_hit_both_modules(self):
        """
        Anything that rebinds g.<name> at run time must rebind util.<name> too.

        Three places in Leo swap a function out while it runs: leoApp redirects
        stdout under pythonw, leoserver redirects the log to its client, and
        mod_speedups substitutes faster path helpers. leoGlobals re-exports
        util, so g.<name> and util.<name> are two bindings to one function --
        and patching only the first leaves util's own callers on the original.
        For g.es_print that means error, warning and internalError go on
        writing where the patch was meant to stop them.

        Checked by reading the source, because the failure is invisible at run
        time: everything keeps working, just not where the caller intended.
        """
        import re

        from leo.leolib import util

        names = {n for n in dir(util) if not n.startswith('_')}
        offenders = []
        for path in sorted(pathlib.Path(os.path.join(REPO, 'leo')).rglob('*.py')):
            for i, line in enumerate(path.read_text(errors='replace').split('\n'), 1):
                for m in re.finditer(r'\bg\.([A-Za-z_]\w*)\s*=[^=]', line):
                    name = m.group(1)
                    if name in names and f'util.{name}' not in line:
                        rel = path.relative_to(REPO)
                        offenders.append(f'{rel}:{i}: g.{name} without util.{name}')
        self.assertEqual(offenders, [], '\n'.join(offenders))

    # @-others


# @-others
# @@language python
# @@tabwidth -4
# @-leo
