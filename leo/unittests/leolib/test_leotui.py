"""
Tests of leo.leotui: a front end driven by leolib alone.

leolib's own tests show the model needs no view. They cannot show the boundary
is *usable*: a library that nothing consumes from outside can satisfy any
import rule at all. These tests are the other half -- a real front end opens,
folds, edits and saves a .leo file, and the modules it does not import are the
measurement.
"""

import os
import unittest

from leo.unittests.leolib.test_leolib_boundary import run_isolated

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
LEO_PY_REF = os.path.join(REPO, 'leo', 'core', 'LeoPyRef.leo')

# A front end may import anything it likes; the point is that this one needs
# none of these. leoGlobals and leoCommands are on the list because they are
# what "driven by leolib" has to mean: 5,800 lines of host and the commander
# stack are exactly what a second front end would otherwise inherit.
FORBIDDEN = (
    'leoGlobals',
    'leoCommands',
    'leoBridge',
    'leoApp',
    'leoFrame',
    'leoGui',
    'leoKeys',
    'leoMenu',
    'leoColorizer',
    'leoAPI',
    'leoVim',
    'leoChapters',
    'leoQt',
    'qt_',
)


class TestLeotuiBoundary(unittest.TestCase):
    """Opening and editing a real outline must not reach past leolib."""

    def test_open_imports_no_view_module_or_commander(self):
        out = run_isolated(f"""
            import sys
            from leo.leotui.__main__ import open_model
            model = open_model({LEO_PY_REF!r})
            nodes = sum(1 for _ in model.outline.all_unique_positions())
            bad = [m for m in sys.modules
                   if m.startswith('leo.') and any(k in m for k in {FORBIDDEN!r})]
            print('NODES', nodes)
            print('MODULES', len([m for m in sys.modules if m.startswith('leo.')]))
            print('BAD', ','.join(sorted(bad)))
        """)
        nodes = int(out.split('NODES')[1].split('\n')[0].strip())
        modules = int(out.split('MODULES')[1].split('\n')[0].strip())
        bad = out.split('BAD')[1].split('\n')[0].strip()
        self.assertEqual(bad, '', f"leotui reached past leolib: {bad}")
        self.assertGreater(nodes, 11000, 'the external files were not read')
        # Through leoBridge the same file imports 108 modules. The ceiling is
        # loose on purpose: what matters is the order of magnitude and the
        # empty BAD list above, not an exact count that churns.
        self.assertLess(modules, 40, f"leotui imported {modules} leo modules")

    def test_edit_and_save_round_trip(self):
        """Edit a headline and a body through the front end; reopen and check."""
        out = run_isolated("""
            import os, tempfile
            from leo import leolib
            from leo.leotui.model import OutlineModel

            path = os.path.join(tempfile.mkdtemp(), 'rt.leo')
            o = leolib.new_outline(path)
            r = o.rootPosition(); r.h = 'root'; r.b = 'root body\\n'
            for name in ('alpha', 'beta'):
                ch = r.insertAsLastChild(); ch.h = name; ch.b = name + ' body\\n'
            leolib.save(o)

            # A leolib outline starts collapsed: folds live in outline.db,
            # which is a fresh dict for an outline opened with no view.
            model = OutlineModel(leolib.open_outline(path))
            model.build_rows()
            model.toggle()                      # expand the root
            model.build_rows()
            model.move(1)                       # onto 'alpha'
            assert model.current.h == 'alpha', model.current.h
            model.set_headline('alpha renamed')
            model.set_body('new alpha body\\n')
            assert model.save(), 'save returned False'

            o2 = leolib.open_outline(path)
            print('RESULT', [(p.h, p.b) for p in o2.all_unique_positions()])
        """)
        result = out.split('RESULT')[1].strip()
        self.assertIn("('alpha renamed', 'new alpha body\\n')", result)
        self.assertIn("('beta', 'beta body\\n')", result)
        # The root must be untouched: an earlier version of this test passed
        # because the outline was collapsed and it renamed the root instead.
        self.assertIn("('root', 'root body\\n')", result)

    def test_structural_edits(self):
        """Insert, move and delete, built on the Position primitives."""
        out = run_isolated("""
            import os, tempfile
            from leo import leolib
            from leo.leotui.model import OutlineModel

            path = os.path.join(tempfile.mkdtemp(), 'st.leo')
            o = leolib.new_outline(path)
            r = o.rootPosition(); r.h = 'root'
            for name in ('a', 'b', 'c'):
                ch = r.insertAsLastChild(); ch.h = name
            leolib.save(o)

            model = OutlineModel(leolib.open_outline(path))
            model.build_rows()
            model.toggle()                      # expand the root
            model.build_rows()
            def heads():
                model.dirty = True
                return [row.p.h for row in model.build_rows()]
            model.move(2)                       # onto 'b'
            model.move_up()
            print('AFTER_UP', heads())
            model.move_down()
            print('AFTER_DOWN', heads())
            model.move_right()                  # 'b' becomes a child of 'a'
            print('AFTER_RIGHT', heads())
            model.move_left()
            print('AFTER_LEFT', heads())
            model.insert_node()
            model.set_headline('inserted')
            print('AFTER_INSERT', heads())
            model.delete_node()
            print('AFTER_DELETE', heads())
        """)

        def row(tag):
            return out.split(tag)[1].split('\n')[0].strip()

        self.assertEqual(row('AFTER_UP'), "['root', 'b', 'a', 'c']")
        self.assertEqual(row('AFTER_DOWN'), "['root', 'a', 'b', 'c']")
        self.assertEqual(row('AFTER_RIGHT'), "['root', 'a', 'b', 'c']")
        self.assertEqual(row('AFTER_LEFT'), "['root', 'a', 'b', 'c']")
        self.assertIn('inserted', row('AFTER_INSERT'))
        self.assertNotIn('inserted', row('AFTER_DELETE'))

    def test_folds_are_per_view(self):
        """Two terminal views of one outline fold independently."""
        out = run_isolated("""
            import os, tempfile
            from leo import leolib
            from leo.leotui.model import OutlineModel

            path = os.path.join(tempfile.mkdtemp(), 'fold.leo')
            o = leolib.new_outline(path)
            r = o.rootPosition(); r.h = 'root'
            ch = r.insertAsLastChild(); ch.h = 'child'
            leolib.save(o)

            o = leolib.open_outline(path)
            a = OutlineModel(o)
            b = OutlineModel(o)
            a.build_rows(); b.build_rows()
            a.toggle()                          # expand root in view a only
            print('A', [row.p.h for row in a.build_rows()])
            print('B', [row.p.h for row in b.build_rows()])
            print('VIEWS', len(o.views))
        """)
        a = out.split('A')[1].split('\n')[0].strip()
        b = out.split('\nB')[1].split('\n')[0].strip()
        views = int(out.split('VIEWS')[1].split('\n')[0].strip())
        self.assertEqual(views, 2)
        self.assertEqual(a, "['root', 'child']")
        self.assertEqual(b, "['root']", 'folds leaked between views')

    def test_edit_reaches_the_external_file(self):
        """
        The whole contract: edit a node in the terminal, and the @file on disk
        changes. Saving the .leo file is not enough -- an outline whose bodies
        never reach the files a compiler sees is a viewer, not an editor.
        """
        out = run_isolated("""
            import os, tempfile
            from leo import leolib
            from leo.leotui.model import OutlineModel

            d = tempfile.mkdtemp()
            path = os.path.join(d, 'ext.leo')
            target = os.path.join(d, 'hello.py')

            o = leolib.new_outline(path)
            r = o.rootPosition(); r.h = '@file hello.py'
            r.b = 'print("before")\\n'
            leolib.save(o)
            leolib.write_external_files(o)
            print('ON_DISK_1', repr(open(target).read()))

            model = OutlineModel(leolib.open_outline(path))
            model.build_rows()
            model.set_body('print("after")\\n')
            model.save()
            print('WROTE', model.write_external_files())
            print('ON_DISK_2', repr(open(target).read()))
        """)

        def row(tag):
            return out.split(tag)[1].split('\n')[0].strip()

        self.assertIn('print("before")', row('ON_DISK_1'))
        self.assertIn('print("after")', row('ON_DISK_2'))
        self.assertNotIn('print("before")', row('ON_DISK_2'))

    def test_a_view_that_answers_little_still_works(self):
        """
        A view is not necessarily a window.

        Outline used to guard its forwards with `if self.c is None`, so any
        attached view had to answer everything a commander answers -- settings,
        a cache, window geometry, error dialogs -- or the save path raised
        AttributeError. Outline.ask_view asks what the view implements instead.
        This view answers only the outline questions a terminal genuinely has
        an answer for; saving and tangling must still work.
        """
        out = run_isolated(r"""
            import os, tempfile
            from leo import leolib
            from leo.core.leoOutline import ViewState

            class BareView:
                'No config, no db, no frame, no setChanged, no dialogs.'
                def __init__(self, outline):
                    self.outline = outline
                    self.view_state = ViewState(self)
                    self.exists = True
                    self.requestLaterRedraw = False
                    self._p = outline.rootPosition()
                    outline.add_view(self)
                @property
                def p(self): return self._p
                def setCurrentPosition(self, p): self._p = p.copy() if p else p
                def rootPosition(self): return self.outline.rootPosition()
                def positionExists(self, p, root=None):
                    return self.outline.positionExists(p, root)

            d = tempfile.mkdtemp()
            path, target = os.path.join(d, 'bare.leo'), os.path.join(d, 'bare.py')
            o = leolib.new_outline(path)
            r = o.rootPosition(); r.h = '@file bare.py'; r.b = 'x = 1\n'
            leolib.save(o); leolib.write_external_files(o)

            o = leolib.open_outline(path)
            view = BareView(o)
            assert o.c is view, o.c

            # Each of these used to raise AttributeError with a view attached.
            o.init_error_dialogs()
            o.raise_error_dialogs()
            o.alert('ignored')
            o.setChanged()
            o.redraw()
            o.endEditing()
            print('CONFIG', type(o.config).__name__)
            print('DB_IS_VIEWLESS', o.db is o._viewless_db)
            print('FRAME', o.frame)
            print('WIDTHS', o.tab_width, o.page_width, o.target_language)

            o.setBodyString(o.rootPosition(), 'x = 2\n')
            leolib.save(o)
            print('WROTE', leolib.write_external_files(o))
            print('ON_DISK', 'x = 2' in open(target).read())

            # A file that exists but this outline never read needs a
            # confirmation this view cannot raise: refuse, do not crash on
            # g.app.gui being None.
            other = os.path.join(d, 'never_read.py')
            with open(other, 'w') as f:
                f.write('# written by someone else')
            added = o.rootPosition().insertAfter()
            added.h = '@file never_read.py'
            added.b = 'y = 1'
            leolib.write_external_files(o)
            with open(other) as f:
                print('REFUSED', f.read() == '# written by someone else')
        """)

        def row(tag):
            return out.split(tag)[1].split('\n')[0].strip()

        self.assertEqual(row('CONFIG'), 'DefaultConfig')
        self.assertEqual(row('DB_IS_VIEWLESS'), 'True')
        self.assertEqual(row('FRAME'), 'None')
        self.assertEqual(row('WIDTHS'), '-4 132 python')
        self.assertEqual(row('WROTE'), '1')
        self.assertEqual(row('ON_DISK'), 'True')
        self.assertEqual(row('REFUSED'), 'True')

    def test_undo_and_redo(self):
        """
        Undo works in a front end with no commander and no gui.

        leoUndo is a model module now: it imports leolib.util, and the four
        things it used a host for -- settings, the Edit menu, the body buffer
        and the gui's text-wrapper test -- are asked of the view, which may
        decline. A terminal declines three of the four.
        """
        out = run_isolated(r"""
            import os, sys, tempfile
            from leo import leolib
            from leo.leotui.model import OutlineModel

            path = os.path.join(tempfile.mkdtemp(), 'undo.leo')
            o = leolib.new_outline(path)
            r = o.rootPosition(); r.h = 'root'; r.b = 'first\n'
            for name in ('a', 'b'):
                ch = r.insertAsLastChild(); ch.h = name
            leolib.save(o)

            m = OutlineModel(leolib.open_outline(path))
            m.build_rows(); m.toggle(); m.build_rows()   # expand the root
            heads = lambda: [row.p.h for row in (setattr(m, 'dirty', True), m.build_rows())[1]]

            # 1. headline
            m.move(1)
            m.set_headline('a renamed')
            print('HEAD_EDIT', m.current.h)
            m.undo(); print('HEAD_UNDO', heads())
            m.redo(); print('HEAD_REDO', heads())
            m.undo()

            # 2. body
            m.index = 0; m.dirty = True; m.select_current()
            m.set_body('second\n')
            print('BODY_EDIT', repr(m.current.b))
            m.undo(); print('BODY_UNDO', repr(m.current.b))
            m.redo(); print('BODY_REDO', repr(m.current.b))
            m.undo()

            # 3. insert
            m.insert_node(); m.set_headline('inserted')
            print('INS_EDIT', heads())
            m.undo(); m.undo()          # the headline, then the insert
            print('INS_UNDO', heads())

            # 4. delete
            m.dirty = True; m.build_rows(); m.index = 1
            m.delete_node()
            print('DEL_EDIT', heads())
            m.undo(); print('DEL_UNDO', heads())

            # 5. move
            m.dirty = True; m.build_rows(); m.index = 2
            m.move_up()
            print('MOVE_EDIT', heads())
            m.undo(); print('MOVE_UNDO', heads())

            bad = [x for x in sys.modules if x.startswith('leo.')
                   and any(k in x for k in ('leoGlobals', 'leoCommands', 'leoGui'))]
            print('BAD', ','.join(sorted(bad)))
        """)

        def row(tag):
            return out.split(tag)[1].split('\n')[0].strip()

        self.assertEqual(row('HEAD_EDIT'), 'a renamed')
        self.assertEqual(row('HEAD_UNDO'), "['root', 'a', 'b']")
        self.assertEqual(row('HEAD_REDO'), "['root', 'a renamed', 'b']")
        self.assertEqual(row('BODY_EDIT'), "'second\\n'")
        self.assertEqual(row('BODY_UNDO'), "'first\\n'")
        self.assertEqual(row('BODY_REDO'), "'second\\n'")
        self.assertIn('inserted', row('INS_EDIT'))
        self.assertEqual(row('INS_UNDO'), "['root', 'a', 'b']")
        self.assertEqual(row('DEL_EDIT'), "['root', 'b']")
        self.assertEqual(row('DEL_UNDO'), "['root', 'a', 'b']")
        self.assertEqual(row('MOVE_EDIT'), "['root', 'b', 'a']")
        self.assertEqual(row('MOVE_UNDO'), "['root', 'a', 'b']")
        self.assertEqual(row('BAD'), '', 'undo dragged in the host')

    def test_leoUndo_is_a_model_module(self):
        """
        Importing leoUndo must not import leoGlobals.

        The same assertion as test_no_leoGlobals_anywhere, for the module that
        joined the model last. One `from leo.core import leoGlobals as g` in
        leoUndo puts all 5,800 lines back, and undo is on the path of every
        edit, so it would come back for every front end at once.
        """
        out = run_isolated("""
            import sys
            from leo.core import leoUndo  # noqa: F401
            mods = sorted(m for m in sys.modules if m.startswith('leo.'))
            print('COUNT', len(mods))
            print('MODS', ','.join(mods))
        """)
        count = int(out.split('COUNT')[1].split('\n')[0].strip())
        mods = out.split('MODS')[1].split('\n')[0].strip().split(',')
        self.assertNotIn('leo.core.leoGlobals', mods, f"leoGlobals came back: {mods}")
        self.assertNotIn('leo.core.leoApp', mods, f"leoApp came back: {mods}")
        self.assertLess(count, 12, f"leoUndo now imports {count} leo modules")

    def test_undo_stays_lazy(self):
        """Reading a .leo file must not pay for an undo stack nobody asked for."""
        out = run_isolated(f"""
            import sys
            from leo import leolib
            leolib.open_outline({LEO_PY_REF!r}, read_external=False)
            print('LOADED', 'leo.core.leoUndo' in sys.modules)
        """)
        self.assertEqual(out.split('LOADED')[1].split('\n')[0].strip(), 'False')


if __name__ == '__main__':
    unittest.main()
