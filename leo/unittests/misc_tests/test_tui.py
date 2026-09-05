# @+leo-ver=5-thin
# @+node:sa.20260905210400.1: * @file ../unittests/misc_tests/test_tui.py
"""Tests of leo/tui: a view of an outline with no Qt anywhere."""

from leo.core import leoCommands
from leo.core.leoGui import NullGui
from leo.core.leoTest2 import LeoUnitTest
from leo.tui import model as tui_model
from leo.tui.model import OutlineModel
from leo.tui.screen import compose


# @+others
# @+node:sa.20260905210400.2: ** class TestTui(LeoUnitTest)
class TestTui(LeoUnitTest):
    """The terminal view is the first client of the model that is not Leo's own gui."""

    # @+others
    # @+node:sa.20260905210400.3: *3* TestTui.make_tree
    def make_tree(self):
        c = self.c
        root = c.rootPosition()
        root.h, root.b = 'root', 'root body'
        a = root.insertAsLastChild()
        a.h, a.b = 'A', 'aaa\nbbb'
        a.insertAsLastChild().h = 'A1'
        b = root.insertAsLastChild()
        b.h, b.b = 'B', 'bbb'
        return root

    # @+node:sa.20260905210400.4: *3* TestTui.test_compose_fills_the_screen_exactly
    def test_compose_fills_the_screen_exactly(self):
        self.make_tree()
        m = OutlineModel(self.c)
        lines = compose(m, width=40, height=12)
        self.assertEqual(len(lines), 12)
        self.assertTrue(all(len(ln) == 40 for ln in lines), [len(ln) for ln in lines])

    # @+node:sa.20260905210400.5: *3* TestTui.test_navigation_and_body_come_from_the_model
    def test_navigation_and_body_come_from_the_model(self):
        self.make_tree()
        m = OutlineModel(self.c)
        m.build_rows()
        self.assertEqual(m.current.h, 'root')
        m.toggle()  # Expand root so its children become visible.
        m.move(1)
        self.assertEqual(m.current.h, 'A')
        self.assertEqual(m.body_lines(), ['aaa', 'bbb'])
        # The body is read from the model, not from any widget.
        m.current.b = 'changed'
        self.assertEqual(m.body_lines(), ['changed'])

    # @+node:sa.20260905210400.6: *3* TestTui.test_folds_are_private_to_the_terminal_view
    def test_folds_are_private_to_the_terminal_view(self):
        c = self.c
        self.make_tree()
        other = leoCommands.Commands(fileName='', gui=c.gui, outline=c.outline)
        self.addCleanup(c.outline.remove_view, other)
        m = OutlineModel(other)
        m.build_rows()
        m.toggle()  # Expand root, in the terminal view only.
        with c.outline.acting_view(other):
            self.assertTrue(other.rootPosition().isExpanded())
        with c.outline.acting_view(c):
            self.assertFalse(c.rootPosition().isExpanded())

    # @+node:sa.20260905210400.7: *3* TestTui.test_the_bus_reaches_a_non_qt_view
    def test_the_bus_reaches_a_non_qt_view(self):
        c = self.c
        self.make_tree()
        other = leoCommands.Commands(fileName='', gui=NullGui(), outline=c.outline)
        self.addCleanup(c.outline.remove_view, other)
        m = OutlineModel(other)
        m.build_rows()
        self.assertFalse(m.dirty)
        # A change made through *another* view marks this one dirty...
        with c.outline.acting_view(c):
            c.rootPosition().b = 'edited elsewhere'
        self.assertTrue(m.dirty)
        # ...but a view does not need repainting for its own change.
        m.dirty = False
        with c.outline.acting_view(other):
            other.rootPosition().b = 'edited here'
        self.assertFalse(m.dirty)

    # @+node:sa.20260905220300.1: *3* TestTui.test_headline_and_body_edits_undo
    def test_headline_and_body_edits_undo(self):
        """
        Editing from a terminal view must round-trip through Leo's undo.

        The first attempt did not: changing p.h without also calling
        tree.setHeadline left the headline widget stale, so the c.endEditing at
        the top of u.undo believed the user had typed a headline edit and
        pushed a spurious bead, eating the undo.
        """
        c = self.c
        self.make_tree()
        m = OutlineModel(c)
        m.build_rows()
        m.toggle()
        m.move(1)
        self.assertEqual(m.current.h, 'A')
        m.set_headline('A renamed')
        m.set_body('one\ntwo')
        self.assertEqual(m.current.h, 'A renamed')
        self.assertEqual(m.body_lines(), ['one', 'two'])
        m.run_command('undo')
        self.assertEqual(m.body_lines(), ['aaa', 'bbb'])
        m.run_command('undo')
        self.assertEqual(m.current.h, 'A')
        m.run_command('redo')
        self.assertEqual(m.current.h, 'A renamed')

    # @+node:sa.20260905220300.2: *3* TestTui.test_leo_commands_run_in_a_terminal_view
    def test_leo_commands_run_in_a_terminal_view(self):
        """
        The terminal view drives Leo's real commands, not a reimplementation.

        Every command bound to a key was checked to work with a null frame.
        """
        from leo.tui.__main__ import COMMAND_KEYS

        c = self.c
        self.make_tree()
        m = OutlineModel(c)
        m.build_rows()
        m.toggle()
        m.move(1)
        before = [r.p.h for r in m.rows]
        m.run_command('insert-node')
        m.build_rows()
        self.assertIn('newHeadline', [r.p.h for r in m.rows])
        m.run_command('undo')
        m.build_rows()
        self.assertEqual([r.p.h for r in m.rows], before)
        # Every key-bound command exists.
        for name in COMMAND_KEYS.values():
            self.assertIn(name, c.commandsDict, name)

    # @+node:sa.20260905220300.3: *3* TestTui.test_edits_reach_the_other_view
    def test_edits_reach_the_other_view(self):
        """An edit typed in the terminal is visible in another view at once."""
        c = self.c
        self.make_tree()
        other = leoCommands.Commands(fileName='', gui=NullGui(), outline=c.outline)
        self.addCleanup(c.outline.remove_view, other)
        m = OutlineModel(other)
        m.build_rows()
        m.set_body('typed in the terminal')
        self.assertEqual(c.rootPosition().b, 'typed in the terminal')

    # @+node:sa.20260905210400.8: *3* TestTui.test_the_view_needs_no_frame
    def test_the_view_needs_no_frame(self):
        """
        A view of the model should not have to reach through a commander's frame.

        FRAME_REACHES is the measured list of places it still must. Keeping it
        empty is the point of the exercise; if it grows, the model API is
        missing something a non-Qt view needs.
        """
        self.assertEqual(tui_model.FRAME_REACHES, [])
        # A view *is* entitled to a text buffer; those are tracked separately.
        # This was 2 until the headline half of stage 6: committing a headline
        # no longer requires the view to keep a headline widget in step.
        self.assertEqual(len(tui_model.WRAPPER_REACHES), 1)

    # @-others


# @-others
# @@language python
# @@tabwidth -4
# @-leo
