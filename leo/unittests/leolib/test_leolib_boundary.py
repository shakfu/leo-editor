# @+leo-ver=5-thin
# @+node:sa.20260906110000.1: * @file ../unittests/leolib/test_leolib_boundary.py
"""
Tests of leolib: the model, with no view of any kind.

The boundary test is the point of the package. leolib must never import a view
module, and "must never" is only worth anything if something checks: the
dependency it forbids is the kind that arrives by accident, in a helper someone
adds to leoNodes six months from now, and that nothing else would catch.

It runs in a subprocess because import state is global and permanent: any other
test that has already imported leoFrame would make an in-process check pass for
the wrong reason.
"""
# @+<< test_leolib_boundary imports >>
# @+node:sa.20260906110000.2: ** << test_leolib_boundary imports >>
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

from leo.core.leoTest2 import LeoUnitTest
# @-<< test_leolib_boundary imports >>

# The modules that make Leo a Qt application. leolib exists to not need them.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
LEO_PY_REF = os.path.join(REPO, 'leo', 'core', 'LeoPyRef.leo')

VIEW_MODULES = (
    'leoFrame',
    'leoGui',
    'leoKeys',
    'leoMenu',
    'leoColorizer',
    'leoBackground',
    'leoAPI',
    'leoVim',
    'leoChapters',
    'leoQt',
)


# @+others
# @+node:sa.20260906110000.3: ** def run_isolated
def run_isolated(body: str) -> str:
    """Run body in a fresh interpreter with the repo on sys.path; return stdout."""
    repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    env = dict(os.environ, PYTHONPATH=repo)
    proc = subprocess.run(
        [sys.executable, '-c', textwrap.dedent(body)],
        capture_output=True, text=True, env=env, cwd=repo, timeout=120,
    )
    if proc.returncode != 0:
        raise AssertionError(f"subprocess failed:\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout


# @+node:sa.20260906110000.4: ** class TestLeolibBoundary
class TestLeolibBoundary(unittest.TestCase):
    """leolib must not import, or need, any view module."""

    # @+others
    # @+node:sa.20260906110000.5: *3* TestLeolibBoundary.test_import_pulls_in_no_view_module
    def test_import_pulls_in_no_view_module(self):
        """Importing leolib must not drag in a single view module."""
        out = run_isolated(f"""
            import sys
            from leo import leolib
            view = {VIEW_MODULES!r}
            leaks = [m for m in sys.modules
                     if m.startswith('leo.') and any(k in m for k in view)]
            plugins = [m for m in sys.modules if m.startswith('leo.plugins')]
            print('LEAKS', ','.join(sorted(leaks)))
            print('PLUGINS', ','.join(sorted(plugins)))
        """)
        leaks = out.split('LEAKS')[1].split('\n')[0].strip()
        plugins = out.split('PLUGINS')[1].split('\n')[0].strip()
        self.assertEqual(leaks, '', f"leolib imported view modules: {leaks}")
        self.assertEqual(plugins, '', f"leolib imported plugins: {plugins}")

    # @+node:sa.20260906110000.6: *3* TestLeolibBoundary.test_round_trip_pulls_in_no_view_module
    def test_round_trip_pulls_in_no_view_module(self):
        """
        Creating, editing, saving and reopening a .leo file must stay view-free.

        Importing cleanly is the easy half. This is the half that matters: the
        whole documented capability -- open, create, edit, view, save -- with
        nothing from a front end anywhere in it.
        """
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'boundary.leo')
            out = run_isolated(f"""
                import sys
                from leo import leolib
                o = leolib.new_outline()
                root = o.rootPosition()
                root.h, root.b = 'root', 'root body'
                child = root.insertAsLastChild()
                child.h, child.b = 'child', 'child body'
                leolib.save(o, {path!r})
                o2 = leolib.open_outline({path!r})
                o2.rootPosition().h = 'renamed'
                leolib.save(o2)
                o3 = leolib.open_outline({path!r})
                print('HEADS', '|'.join(p.h for p in o3.all_unique_positions()))
                print('BODIES', '|'.join(p.b for p in o3.all_unique_positions()))
                view = {VIEW_MODULES!r}
                leaks = [m for m in sys.modules
                         if m.startswith('leo.') and any(k in m for k in view)]
                print('LEAKS', ','.join(sorted(leaks)))
                print('COUNT', len([m for m in sys.modules if m.startswith('leo.')]))
            """)
            heads = out.split('HEADS')[1].split('\n')[0].strip()
            bodies = out.split('BODIES')[1].split('\n')[0].strip()
            leaks = out.split('LEAKS')[1].split('\n')[0].strip()
            self.assertEqual(heads, 'renamed|child')
            self.assertEqual(bodies, 'root body|child body')
            self.assertEqual(leaks, '', f"a view module was needed: {leaks}")

    # @+node:sa.20260906110000.7: *3* TestLeolibBoundary.test_module_count_stays_small
    def test_module_count_stays_small(self):
        """
        A ratchet, not a law of nature.

        Opening a .leo file through leoBridge imports about 99 leo modules.
        Through leolib it is a handful. The number is asserted loosely -- the
        point is that it cannot quietly climb back toward the commander stack.
        """
        out = run_isolated("""
            import sys
            from leo import leolib
            leolib.open_outline('leo/core/LeoPyRef.leo')
            print('COUNT', len([m for m in sys.modules if m.startswith('leo.')]))
        """)
        count = int(out.split('COUNT')[1].split('\n')[0].strip())
        self.assertLess(count, 20, f"leolib now imports {count} leo modules")

    # @-others


# @+node:sa.20260906110000.8: ** class TestLeolibApi
class TestLeolibApi(LeoUnitTest):
    """leolib's own behaviour, in-process."""

    # @+others
    # @+node:sa.20260906110000.9: *3* TestLeolibApi.test_open_outline
    def test_open_outline(self):
        from leo import leolib
        # An absolute path: LeoUnitTest does not promise a cwd, and
        # leolib.open_outline resolves relative paths against it as any
        # library should.
        outline = leolib.open_outline(LEO_PY_REF)
        self.assertEqual(outline.views, [], 'an outline opened by leolib has no view')
        heads = [p.h for p in outline.rootPosition().self_and_siblings()]
        self.assertIn('Startup', heads)
        # The geometry the file records is data, not something applied.
        self.assertIn('width', outline.window_geometry)

    # @+node:sa.20260906110000.10: *3* TestLeolibApi.test_round_trip
    def test_round_trip(self):
        from leo import leolib
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'x.leo')
            o = leolib.new_outline()
            o.rootPosition().h = 'first'
            o.rootPosition().b = 'first body'
            leolib.save(o, path)
            self.assertTrue(os.path.exists(path))
            o2 = leolib.open_outline(path)
            self.assertEqual(o2.rootPosition().h, 'first')
            self.assertEqual(o2.rootPosition().b, 'first body')

    # @+node:sa.20260906110000.11: *3* TestLeolibApi.test_open_missing_file
    def test_open_missing_file(self):
        from leo import leolib
        with self.assertRaises(FileNotFoundError):
            leolib.open_outline('/no/such/file.leo')

    # @+node:sa.20260906110000.12: *3* TestLeolibApi.test_save_without_a_name
    def test_save_without_a_name(self):
        from leo import leolib
        with self.assertRaises(ValueError):
            leolib.save(leolib.new_outline())

    # @-others


# @-others
# @@language python
# @@tabwidth -4
# @-leo
