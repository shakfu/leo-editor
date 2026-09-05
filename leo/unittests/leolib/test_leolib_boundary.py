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
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest

from leo.core import leoGlobals as g
from leo.core.leoTest2 import LeoUnitTest
# @-<< test_leolib_boundary imports >>

# The modules that make Leo a Qt application. leolib exists to not need them.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
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
    repo = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    env = dict(os.environ, PYTHONPATH=repo)
    proc = subprocess.run(
        [sys.executable, '-c', textwrap.dedent(body)],
        capture_output=True,
        text=True,
        env=env,
        cwd=repo,
        timeout=120,
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

    # @+node:sa.20260907130000.1: *3* TestLeolibBoundary.test_only_importers_and_writers
    def test_only_importers_and_writers(self):
        """
        The one thing leolib may import from leo/plugins is language support.

        An @auto file carries no sentinels, so its structure has to come from a
        language importer, and there are 34 of those under leo/plugins. They
        are model machinery -- none touches a front end -- so the rule worth
        enforcing is "no view module", not "nothing under leo.plugins", which
        was only ever a proxy for it and is wrong for exactly these.

        Nothing else under leo.plugins may be imported, and they must stay
        lazy: an outline with no @auto node pays nothing for them.
        """
        out = run_isolated(f"""
            import sys
            from leo import leolib
            from leo.core import leoGlobals as g
            leolib.ensure_app()
            before = len([m for m in sys.modules if m.startswith('leo.plugins')])
            g.app.atAutoDict          # First touch: loads the importers.
            after = sorted(m for m in sys.modules if m.startswith('leo.plugins'))
            other = [m for m in after
                     if not m.startswith(('leo.plugins.importers',
                                          'leo.plugins.writers'))
                     and m != 'leo.plugins']
            view = {VIEW_MODULES!r}
            leaks = [m for m in sys.modules
                     if m.startswith('leo.') and any(k in m for k in view)]
            print('BEFORE', before)
            print('AFTER', len(after))
            print('OTHER', ','.join(other))
            print('LEAKS', ','.join(sorted(leaks)))
        """)
        before = int(out.split('BEFORE')[1].split('\n')[0].strip())
        after = int(out.split('AFTER')[1].split('\n')[0].strip())
        other = out.split('OTHER')[1].split('\n')[0].strip()
        leaks = out.split('LEAKS')[1].split('\n')[0].strip()
        self.assertEqual(before, 0, 'the importers loaded before anything asked')
        self.assertGreater(after, 20, 'the importers did not load')
        self.assertEqual(other, '', f"leolib imported other plugins: {other}")
        self.assertEqual(leaks, '', f"a view module came in with them: {leaks}")

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

    # @+node:sa.20260906170000.1: *3* TestLeolibBoundary.test_external_files_match_full_leo
    def test_external_files_match_full_leo(self):
        """
        Reading @file trees headless must give exactly what Leo gives.

        Compared by hashing each node's headline *and body*, keyed by gnx.
        Counting nodes is not enough and neither is counting children: an
        @clean node stores its whole tree in the .leo file, so a failed
        external read still leaves a correct-looking shape with stale text.
        That is exactly how twelve files were silently not being read while
        two weaker checks both passed.
        """
        out = run_isolated(f"""
            import hashlib, json, sys
            from leo import leolib
            o = leolib.open_outline({LEO_PY_REF!r})
            d = {{p.gnx: hashlib.sha1((p.h + chr(0) + p.b).encode()).hexdigest()
                 for p in o.all_unique_positions()}}
            print('LIB', json.dumps(d))
        """)
        lib = json.loads(out.split('LIB', 1)[1].strip())

        out = run_isolated(f"""
            import sys; sys.argv = ['x']
            import hashlib, json
            from leo.core import leoBridge
            b = leoBridge.controller(
                gui='nullGui', loadPlugins=False, readSettings=False,
                silent=True, verbose=False)
            c = b.openLeoFile({LEO_PY_REF!r})
            d = {{p.gnx: hashlib.sha1((p.h + chr(0) + p.b).encode()).hexdigest()
                 for p in c.all_unique_positions()}}
            print('LEO', json.dumps(d))
        """)
        leo = json.loads(out.split('LEO', 1)[1].strip())

        self.assertEqual(len(lib), len(leo))
        self.assertEqual(set(lib) - set(leo), set(), 'nodes leolib invented')
        self.assertEqual(set(leo) - set(lib), set(), 'nodes leolib missed')
        differing = [k for k in lib if lib[k] != leo[k]]
        self.assertEqual(differing, [], f"{len(differing)} nodes differ in text")

    # @+node:sa.20260906170000.2: *3* TestLeolibBoundary.test_reading_externals_stays_view_free
    def test_reading_externals_stays_view_free(self):
        """Reading every external file of a real outline must import no view."""
        out = run_isolated(f"""
            import sys
            from leo import leolib
            o = leolib.open_outline({LEO_PY_REF!r})
            view = {VIEW_MODULES!r}
            leaks = [m for m in sys.modules
                     if m.startswith('leo.') and any(k in m for k in view)]
            print('NODES', sum(1 for _ in o.all_unique_positions()))
            print('LEAKS', ','.join(sorted(leaks)))
            print('PLUGINS', len([m for m in sys.modules
                                  if m.startswith('leo.plugins')]))
        """)
        nodes = int(out.split('NODES')[1].split('\n')[0].strip())
        leaks = out.split('LEAKS')[1].split('\n')[0].strip()
        plugins = int(out.split('PLUGINS')[1].split('\n')[0].strip())
        self.assertGreater(nodes, 10000, 'the external files were not read')
        self.assertEqual(leaks, '', f"a view module was needed: {leaks}")
        self.assertEqual(plugins, 0)

    # @+node:sa.20260907110000.1: *3* TestLeolibBoundary.test_tangle_matches_disk
    def test_tangle_matches_disk(self):
        """
        Tangling every external file of a real outline reproduces it byte for
        byte.

        The strongest statement of the write contract, and it costs nothing:
        leolib.tangle returns text without touching the filesystem, so this
        compares against leo-editor's own source tree with no risk of writing
        to it.

        Isolated in a subprocess, like the other checks here, and for a sharper
        reason than usual: what a node tangles to depends on its language, and
        g.app.language_delims_dict is process-global. Run in-process after the
        rest of the suite, one @@language plain file came out with Python's
        blackened sentinels ('# @+leo' instead of '#@+leo'). The writer is not
        at fault -- it is right standalone and under LeoUnitTest -- but a
        byte-for-byte assertion has no business depending on what earlier tests
        left in a global table.
        """
        out = run_isolated(f"""
            import os
            from leo import leolib
            outline = leolib.open_outline({LEO_PY_REF!r})
            at = outline.atFileCommands
            checked, differing = 0, []
            for p in at.findFilesToRead(outline.rootPosition(), all=True):
                if p.isAtAutoNode() or p.isAtShadowFileNode() or p.isAtJupytextNode():
                    continue  # Not plain tangles; they have their own writers.
                path = outline.fullPath(p)
                if not os.path.exists(path):
                    continue
                with open(path, encoding='utf-8') as f:
                    disk = f.read()
                if leolib.tangle(outline, p) != disk:
                    differing.append(p.h)
                checked += 1
            print('CHECKED', checked)
            print('DIFFERING', '|'.join(differing))
        """)
        checked = int(out.split('CHECKED')[1].split('\n')[0].strip())
        differing = out.split('DIFFERING')[1].split('\n')[0].strip()
        self.assertGreater(checked, 300, 'the corpus did not load')
        self.assertEqual(
            differing, '', f"of {checked} files, these did not round-trip: {differing}"
        )

    # @+node:sa.20260906110000.7: *3* TestLeolibBoundary.test_module_count_stays_small
    def test_module_count_stays_small(self):
        """
        A ratchet, not a law of nature.

        Opening a .leo file through leoBridge imports about 100 leo modules.
        Through leolib it is a handful. The number is asserted loosely -- the
        point is that it cannot quietly climb back toward the commander stack.
        """
        out = run_isolated(f"""
            import sys
            from leo import leolib
            leolib.open_outline({LEO_PY_REF!r})
            print('COUNT', len([m for m in sys.modules if m.startswith('leo.')]))
        """)
        count = int(out.split('COUNT')[1].split('\n')[0].strip())
        self.assertLess(count, 20, f"leolib now imports {count} leo modules")

    # @-others


# @+node:sa.20260906110000.8: ** class TestLeolibApi
class TestLeolibApi(LeoUnitTest):
    """leolib's own behaviour, in-process."""

    # @+others
    # @+node:sa.20260907140000.1: *3* TestLeolibApi.test_all_supported_directives
    def test_all_supported_directives(self):
        """
        Every supported @<file> directive reads and writes.

        LeoPyRef.leo contains only @file, @clean and @edit, so the corpus that
        looked comprehensive -- 376 files, byte-identical -- covered half the
        directive set. This builds the other half. @auto matters most of the
        three that were missing: it is one of the three Leo recommends, and it
        is the only kind whose structure comes from a language importer rather
        than from the file.

        Sentinels are the dividing line: only @file carries them. Everything
        else must come out as a file with nothing Leo-specific in it.
        """
        from leo import leolib

        with tempfile.TemporaryDirectory() as tmp:
            # An @auto node imports an existing file, so write one first.
            auto_py = os.path.join(tmp, 'auto.py')
            with open(auto_py, 'w', encoding='utf-8') as f:
                f.write('def alpha():\n    return 1\n')
            leo_file = os.path.join(tmp, 'six.leo')

            outline = leolib.new_outline()
            root = outline.rootPosition()
            root.h, root.b = 'root', ''

            def add(headline, body, child=None):
                p = root.insertAsLastChild()
                p.h, p.b = headline, body
                if child:
                    c = p.insertAsLastChild()
                    c.h, c.b = child
                return p

            others = '@language python\n@others\n'
            add('@file f.py', others, ('body', 'f = 1\n'))
            add('@clean c.py', others, ('body', 'c = 1\n'))
            add('@edit e.py', 'e = 1\n')
            add('@asis a.py', 'a = 1\n')
            add('@nosent n.py', others, ('body', 'n = 1\n'))
            add('@auto auto.py', '')
            leolib.save(outline, leo_file)
            leolib.write_external_files(outline)

            expected = {
                'f.py': 'f = 1',
                'c.py': 'c = 1',
                'e.py': 'e = 1',
                'a.py': 'a = 1',
                'n.py': 'n = 1',
            }
            for name, content in expected.items():
                path = os.path.join(tmp, name)
                self.assertTrue(os.path.exists(path), f"{name} was not written")
                with open(path, encoding='utf-8') as f:
                    text = f.read()
                self.assertIn(content, text, name)
                # Only @file carries sentinels.
                self.assertEqual('@+leo' in text, name == 'f.py', f"{name}: wrong sentinel policy")

            # Now @auto: read via a language importer, edited, written back.
            # Reopening is what imports it: the .leo file records only the
            # node itself, never its children.
            outline = leolib.open_outline(leo_file)
            auto = next(p for p in outline.all_unique_positions() if p.h == '@auto auto.py')
            self.assertEqual([c.h for c in auto.children()], ['function: alpha'])
            fn = auto.firstChild()
            fn.b = fn.b.replace('return 1', 'return 42')
            self.assertEqual(leolib.write_external_files(outline), 1)
            with open(auto_py, encoding='utf-8') as f:
                text = f.read()
            self.assertIn('return 42', text)
            self.assertNotIn('@+leo', text, '@auto must carry no sentinels')

    # @+node:sa.20260907110000.2: *3* TestLeolibApi.test_write_external_files
    def test_write_external_files(self):
        """
        Writing an untouched outline must touch nothing; writing an edited one
        must touch exactly what changed.

        The no-op case is the one that matters. Tangling is destructive by
        nature -- it regenerates the files a compiler reads -- so a writer that
        rewrote everything on every call would churn timestamps, defeat build
        caches, and turn any bug into a whole-tree corruption instead of a
        single bad file.
        """
        from leo import leolib

        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'prog.py')
            leo_file = os.path.join(tmp, 'x.leo')

            outline = leolib.new_outline()
            root = outline.rootPosition()
            root.h = '@file prog.py'
            root.b = '@language python\n@others\n'
            child = root.insertAsLastChild()
            child.h, child.b = 'main', 'def main():\n    return 1\n'
            leolib.save(outline, leo_file)
            self.assertEqual(leolib.write_external_files(outline), 1)
            self.assertTrue(os.path.exists(src))
            with open(src, encoding='utf-8') as f:
                first = f.read()
            self.assertIn('def main():', first)

            # Nothing changed: nothing may be written.
            reopened = leolib.open_outline(leo_file)
            self.assertEqual(leolib.write_external_files(reopened), 0)
            with open(src, encoding='utf-8') as f:
                self.assertEqual(f.read(), first, 'a no-op write changed the file')

            # One change: exactly one write, and it round-trips.
            p = reopened.rootPosition().firstChild()
            p.b = 'def main():\n    return 2\n'
            self.assertEqual(leolib.write_external_files(reopened), 1)
            with open(src, encoding='utf-8') as f:
                self.assertIn('return 2', f.read())
            again = leolib.open_outline(leo_file)
            self.assertIn('return 2', again.rootPosition().firstChild().b)

    # @+node:sa.20260907110000.3: *3* TestLeolibApi.test_write_at_clean_has_no_sentinels
    def test_write_at_clean_has_no_sentinels(self):
        """
        An @clean file carries no sentinels, and reading it back recovers the
        outline anyway.

        This is the pair that makes Leo's external files interesting: tangle
        produces a file with nothing Leo-specific in it, and the read side
        recovers the node structure by diffing against a regenerated copy.
        """
        from leo import leolib

        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, 'clean.py')
            leo_file = os.path.join(tmp, 'x.leo')
            outline = leolib.new_outline()
            root = outline.rootPosition()
            root.h = '@clean clean.py'
            root.b = '@language python\n@others\n'
            child = root.insertAsLastChild()
            child.h, child.b = 'body', 'x = 1\n'
            leolib.save(outline, leo_file)
            leolib.write_external_files(outline)
            with open(src, encoding='utf-8') as f:
                text = f.read()
            self.assertIn('x = 1', text)
            for marker in ('@+leo', '@+node', '@+others', '@@language'):
                self.assertNotIn(marker, text, f"@clean file contains {marker}")
            # And the outline survives a round trip through that bare file.
            back = leolib.open_outline(leo_file)
            self.assertIn('x = 1', ''.join(p.b for p in back.all_unique_positions()))

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

    # @+node:sa.20260908120000.1: *3* TestLeolibApi.test_gnxs_do_not_collide_with_the_host
    def test_gnxs_do_not_collide_with_the_host(self):
        """
        An outline leolib opens inside a running Leo must share its allocator.

        gnxs have to be unique across every outline in a process, because Leo
        copies and clones nodes between them. A gnx is
        `userId.timestamp.counter`, so two allocators with one user id hand out
        the same gnx twice within the same second -- and a fresh allocator
        starts its counter at 1, which is where the host's already is.

        This is a regression test with a story: moving the allocator off g.app
        first gave each leolib outline its own, and this collided with the test
        harness's on the first run. It reported itself only as a printed
        internal error, so every test still passed. Hence an explicit check.
        """
        from leo import leolib

        c = self.c
        host_gnxs = {v.gnx for v in c.all_unique_nodes()}
        # The outline leolib opens must mint gnxs the host has never used.
        outline = leolib.new_outline()
        self.assertIs(outline.nodeIndices, g.app.nodeIndices)
        new_gnxs = {outline.hiddenRootNode.insertAsLastChild().gnx for _ in range(20)}
        self.assertEqual(len(new_gnxs), 20, 'leolib minted a gnx twice')
        clashes = host_gnxs & new_gnxs
        self.assertFalse(clashes, f"leolib reused the host's gnxs: {sorted(clashes)}")

    # @-others


# @-others
# @@language python
# @@tabwidth -4
# @-leo
