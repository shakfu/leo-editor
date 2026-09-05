# @+leo-ver=5-thin
# @+node:sa.20260905150000.1: * @file ../unittests/core/test_leoOutline.py
"""Tests of leoOutline.py: one document, several views."""

from leo.core import leoCommands
from leo.core import signal_manager
from leo.core import leoGlobals as g
from leo.core.leoOutline import Outline
from leo.core.leoTest2 import LeoUnitTest


# @+others
# @+node:sa.20260905150000.2: ** class TestOutline(LeoUnitTest)
class TestOutline(LeoUnitTest):
    """Unit tests for the Outline class and for multiple views of one outline."""

    # @+others
    # @+node:sa.20260905150000.3: *3* TestOutline.second_view
    def second_view(self):
        """Return a second commander viewing self.c's outline."""
        c = self.c
        c2 = leoCommands.Commands(fileName=c.fileName(), gui=c.gui, outline=c.outline)
        self.addCleanup(c.outline.remove_view, c2)
        return c2

    # @+node:sa.20260905150000.4: *3* TestOutline.test_commander_owns_an_outline
    def test_commander_owns_an_outline(self):
        c = self.c
        self.assertIsInstance(c.outline, Outline)
        self.assertTrue(c.owns_outline)
        self.assertEqual(c.outline.views, [c])
        self.assertIs(c.outline.c, c)

    # @+node:sa.20260905150000.5: *3* TestOutline.test_v_context_is_the_outline
    def test_v_context_is_the_outline(self):
        """VNode.context must be a document, never a view."""
        c = self.c
        for p in c.all_unique_positions():
            self.assertIs(p.v.context, c.outline, p.h)
        self.assertIs(c.hiddenRootNode.context, c.outline)

    # @+node:sa.20260905150000.6: *3* TestOutline.test_document_state_is_shared
    def test_document_state_is_shared(self):
        c = self.c
        c2 = self.second_view()
        self.assertIs(c.outline, c2.outline)
        self.assertIs(c.hiddenRootNode, c2.hiddenRootNode)
        self.assertEqual(c.outline.views, [c, c2])
        self.assertFalse(c2.owns_outline)
        # The dirty flag belongs to the document.
        c2.changed = True
        self.assertTrue(c.changed)
        c.changed = False
        self.assertFalse(c2.changed)

    # @+node:sa.20260905150000.7: *3* TestOutline.test_second_view_keeps_the_tree
    def test_second_view_keeps_the_tree(self):
        """
        Creating a second view must not reset the outline.

        Every frame ctor calls frame.createFirstTreeNode, which used to clear
        c.hiddenRootNode.children and the gnx dict.
        """
        c = self.c
        root = c.rootPosition()
        root.h = 'root'
        root.insertAsLastChild().h = 'child'
        heads = [p.h for p in c.all_unique_positions()]
        gnxs = [p.v.gnx for p in c.all_unique_positions()]
        self.assertEqual(heads[:2], ['root', 'child'])
        c2 = self.second_view()
        # The second view sees the same nodes, not a fresh 'newHeadline' tree.
        self.assertEqual([p.h for p in c2.all_unique_positions()], heads)
        self.assertEqual([p.v.gnx for p in c2.all_unique_positions()], gnxs)

    # @+node:sa.20260905150000.8: *3* TestOutline.test_views_have_independent_positions
    def test_views_have_independent_positions(self):
        c = self.c
        root = c.rootPosition()
        root.insertAsLastChild().h = 'child A'
        root.insertAsLastChild().h = 'child B'
        c2 = self.second_view()
        c.selectPosition(c.rootPosition().firstChild())
        c2.selectPosition(c2.rootPosition().lastChild())
        self.assertEqual(c.p.h, 'child A')
        self.assertEqual(c2.p.h, 'child B')
        # Hoist state is per view too.
        c.hoistStack.append(g.Bunch(p=c.p.copy(), expanded=True))
        self.assertEqual(len(c.hoistStack), 1)
        self.assertEqual(len(c2.hoistStack), 0)

    # @+node:sa.20260905150000.9: *3* TestOutline.test_edits_are_visible_in_every_view
    def test_edits_are_visible_in_every_view(self):
        c = self.c
        root = c.rootPosition()
        root.h = 'root'
        c2 = self.second_view()
        c2.rootPosition().b = 'edited in the second view'
        self.assertEqual(c.rootPosition().b, 'edited in the second view')
        c.rootPosition().h = 'renamed in the first view'
        self.assertEqual(c2.rootPosition().h, 'renamed in the first view')

    # @+node:sa.20260905150000.10: *3* TestOutline.test_the_event_bus_is_document_level
    def test_the_event_bus_is_document_level(self):
        c = self.c
        c2 = self.second_view()
        heard: list[str] = []
        signal_manager.connect(c.outline, 'body_changed', lambda v: heard.append(v.h))
        # An edit made through *either* view reaches a listener on the outline.
        c2.rootPosition().h = 'root'
        c2.rootPosition().b = 'from the second view'
        c.rootPosition().b = 'from the first view'
        self.assertEqual(heard, ['root', 'root'])

    # @+node:sa.20260905150000.11: *3* TestOutline.test_selecting_across_views_is_allowed
    def test_selecting_across_views_is_allowed(self):
        """
        LeoTree.selectHelper used to reject any position whose context was not
        this commander. It must now reject only positions from another
        *document*.
        """
        c = self.c
        root = c.rootPosition()
        root.h = 'root'
        c2 = self.second_view()
        p_from_c = c.rootPosition()
        self.assertIs(p_from_c.v.context, c2.outline)
        c2.frame.tree.select(p_from_c)  # Must not be refused.
        self.assertEqual(c2.p.h, 'root')

    # @+node:sa.20260905160300.1: *3* TestOutline.test_undo_stack_is_per_outline
    def test_undo_stack_is_per_outline(self):
        """One outline, one undo history: see "Undo across views" in LEO_REFACTOR.md."""
        c = self.c
        c2 = self.second_view()
        self.assertIs(c.undoer, c2.undoer)
        self.assertIs(c.undoer, c.outline.undoer)
        self.assertIs(c.undoer.outline, c.outline)

    # @+node:sa.20260905160300.2: *3* TestOutline.test_either_view_can_undo_the_other_s_change
    def test_either_view_can_undo_the_other_s_change(self):
        c = self.c
        c.rootPosition().h = 'root'
        c2 = self.second_view()
        u = c.outline.undoer

        # The second view inserts a node...
        with u.acting_view(c2):
            undoData = u.beforeInsertNode(c2.rootPosition())
            p = c2.rootPosition().insertAsLastChild()
            p.h = 'inserted by the second view'
            u.afterInsertNode(p, 'Insert Node', undoData)
        self.assertIn('inserted by the second view', [z.h for z in c.all_unique_positions()])

        # ...and the *first* view undoes it, because the history is shared.
        with u.acting_view(c):
            u.undo()
        self.assertNotIn('inserted by the second view', [z.h for z in c.all_unique_positions()])

    # @+node:sa.20260905160300.3: *3* TestOutline.test_undo_revalidates_other_views
    def test_undo_revalidates_other_views(self):
        """
        An undo in one view can delete the node another view is sitting on.

        Every view's current position must survive the change.
        """
        c = self.c
        c.rootPosition().h = 'root'
        c2 = self.second_view()
        u = c.outline.undoer
        with u.acting_view(c2):
            undoData = u.beforeInsertNode(c2.rootPosition())
            p = c2.rootPosition().insertAsLastChild()
            p.h = 'doomed'
            u.afterInsertNode(p, 'Insert Node', undoData)

        # The first view parks on the node the second view is about to remove.
        c.selectPosition(c.rootPosition().lastChild())
        self.assertEqual(c.p.h, 'doomed')
        with u.acting_view(c2):
            u.undo()
        # No dangling position anywhere.
        self.assertTrue(c.positionExists(c.p), c.p)
        self.assertTrue(c2.positionExists(c2.p), c2.p)
        self.assertEqual(c.p.h, 'root')

    # @+node:sa.20260905160300.4: *3* TestOutline.test_undo_acts_on_the_view_that_asked
    def test_undo_acts_on_the_view_that_asked(self):
        """Undo restores the caret of the window the user is looking at."""
        c = self.c
        root = c.rootPosition()
        root.h, root.b = 'root', 'before'
        c2 = self.second_view()
        u = c.outline.undoer

        with u.acting_view(c):
            c.selectPosition(c.rootPosition())
            bunch = u.beforeChangeBody(c.p)
            c.p.b = 'after'
            c.frame.body.wrapper.setAllText('after')
            u.afterChangeBody(c.p, 'Change Body', bunch)

        # The *second* view undoes it, so the second view's widget is refreshed.
        with u.acting_view(c2):
            u.undo()
        self.assertEqual(c.rootPosition().b, 'before')  # The model, everywhere.
        self.assertEqual(c2.frame.body.wrapper.getAllText(), 'before')

    # @+node:sa.20260905160400.1: *3* TestOutline.test_other_views_are_asked_to_redraw
    def test_other_views_are_asked_to_redraw(self):
        """A change made in one window must not leave the others showing it stale."""
        c = self.c
        c.rootPosition().h = 'root'
        c2 = self.second_view()
        u = c.outline.undoer
        with u.acting_view(c2):
            undoData = u.beforeInsertNode(c2.rootPosition())
            p = c2.rootPosition().insertAsLastChild()
            p.h = 'child'
            u.afterInsertNode(p, 'Insert Node', undoData)
        c.requestLaterRedraw = False
        c2.requestLaterRedraw = False
        with u.acting_view(c2):
            u.undo()
        self.assertTrue(c.requestLaterRedraw)  # The view that did not act.
        self.assertFalse(c2.requestLaterRedraw)  # The acting view redrew itself.

    # @+node:sa.20260905160300.5: *3* TestOutline.test_interleaved_undo_groups_are_detected
    def test_interleaved_undo_groups_are_detected(self):
        """
        A change from one view must not be swallowed by a group another opened.

        Impossible with a single view, so this fails loudly rather than
        silently corrupting the shared history.
        """
        c = self.c
        c.rootPosition().h = 'root'
        c2 = self.second_view()
        u = c.outline.undoer
        with u.acting_view(c):
            u.beforeChangeGroup(c.p, 'Group')
        with self.assertRaises(AssertionError):
            with u.acting_view(c2):
                bunch = u.beforeChangeBody(c2.rootPosition())
                c2.rootPosition().b = 'sneaked in'
                u.afterChangeBody(c2.rootPosition(), 'Change Body', bunch)
        self.assertEqual(u.interleaved_groups, 1)

    # @+node:sa.20260905170200.1: *3* TestOutline.build_tree
    def build_tree(self):
        """root with two children, each with a child of its own."""
        c = self.c
        root = c.rootPosition()
        root.h = 'root'
        a = root.insertAsLastChild()
        a.h = 'A'
        a.insertAsLastChild().h = 'A1'
        b = root.insertAsLastChild()
        b.h = 'B'
        b.insertAsLastChild().h = 'B1'
        return root

    def folds(self, c):
        """(A expanded, B expanded) as seen by view c."""
        with c.outline.acting_view(c):
            root = c.rootPosition()
            return (root.firstChild().isExpanded(), root.lastChild().isExpanded())

    # @+node:sa.20260905170200.2: *3* TestOutline.test_expansion_is_per_view
    def test_expansion_is_per_view(self):
        """
        Folds belong to a window, not to the document.

        expandedBit lived on the VNode until stage 5, so collapsing a node in
        one pane collapsed it in every other.
        """
        c = self.c
        self.build_tree()
        c2 = self.second_view()
        self.assertIsNot(c.view_state, c2.view_state)
        with c.outline.acting_view(c):
            c.rootPosition().firstChild().expand()  # A, in the first view only.
        with c.outline.acting_view(c2):
            c2.rootPosition().lastChild().expand()  # B, in the second view only.
        self.assertEqual(self.folds(c), (True, False))
        self.assertEqual(self.folds(c2), (False, True))

    # @+node:sa.20260905170200.3: *3* TestOutline.test_a_new_view_inherits_the_folds
    def test_a_new_view_inherits_the_folds(self):
        """Opening a second view should not dump you at the top of a collapsed tree."""
        c = self.c
        self.build_tree()
        with c.outline.acting_view(c):
            c.rootPosition().firstChild().expand()
        c2 = self.second_view()
        self.assertEqual(self.folds(c2), (True, False))
        # ...but the copy is independent from then on.
        with c.outline.acting_view(c2):
            c2.rootPosition().firstChild().contract()
        self.assertEqual(self.folds(c), (True, False))
        self.assertEqual(self.folds(c2), (False, False))

    # @+node:sa.20260905170200.4: *3* TestOutline.test_caret_and_scroll_are_per_view
    def test_caret_and_scroll_are_per_view(self):
        c = self.c
        self.build_tree()
        c2 = self.second_view()
        with c.outline.acting_view(c):
            v = c.rootPosition().v
            v.insertSpot, v.scrollBarSpot = 11, 22
            v.setSelection(3, 4)
        with c.outline.acting_view(c2):
            v = c2.rootPosition().v
            v.insertSpot, v.scrollBarSpot = 99, 88
            v.setSelection(1, 2)
        with c.outline.acting_view(c):
            v = c.rootPosition().v
            self.assertEqual((v.insertSpot, v.scrollBarSpot), (11, 22))
            self.assertEqual((v.selectionStart, v.selectionLength), (3, 4))
        with c.outline.acting_view(c2):
            v = c2.rootPosition().v
            self.assertEqual((v.insertSpot, v.scrollBarSpot), (99, 88))
            self.assertEqual((v.selectionStart, v.selectionLength), (1, 2))

    # @+node:sa.20260905170200.5: *3* TestOutline.test_is_selected_is_derived
    def test_is_selected_is_derived(self):
        """
        v.selectedBit is gone: with several views there is no single answer.

        v.isSelected now reports the acting view's current node.
        """
        c = self.c
        self.build_tree()
        c2 = self.second_view()
        self.assertFalse(hasattr(type(c.p.v), 'selectedBit'))
        c.selectPosition(c.rootPosition().firstChild())
        c2.selectPosition(c2.rootPosition().lastChild())
        with c.outline.acting_view(c):
            self.assertTrue(c.rootPosition().firstChild().v.isSelected())
            self.assertFalse(c.rootPosition().lastChild().v.isSelected())
        with c.outline.acting_view(c2):
            self.assertFalse(c2.rootPosition().firstChild().v.isSelected())
            self.assertTrue(c2.rootPosition().lastChild().v.isSelected())

    # @+node:sa.20260905170200.6: *3* TestOutline.test_folds_are_persisted_from_the_primary_view
    def test_folds_are_persisted_from_the_primary_view(self):
        """
        c.db is per *document*, so which window ran the save must not change
        what the file remembers.
        """
        c = self.c
        self.build_tree()
        c2 = self.second_view()
        with c.outline.acting_view(c):
            c.rootPosition().firstChild().expand()  # A, primary view.
        with c.outline.acting_view(c2):
            c2.rootPosition().lastChild().expand()  # B, second view.
        c.mFileName = 'test.leo'
        c.db = {}
        c.fileCommands.currentPosition = c.rootPosition()
        with c.outline.acting_view(c2):  # Save from the *second* view.
            c.fileCommands.setCachedBits()
        saved = c.db['expanded'].split(',')
        self.assertEqual(saved, [c.rootPosition().firstChild().gnx])

    # @+node:sa.20260905170300.2: *3* TestOutline.test_deleted_nodes_are_not_pinned
    def test_deleted_nodes_are_not_pinned(self):
        """
        Per-view state must not keep deleted subtrees alive.

        expanded_positions holds Positions, and a Position holds VNodes. On the
        VNode this state died with the node; in a ViewState it does not, so it
        is swept whenever the outline changes structurally.
        """
        c = self.c
        self.build_tree()
        with c.outline.acting_view(c):
            p = c.rootPosition().firstChild()
            p.expand()
            gnx = p.gnx
            self.assertIn(gnx, c.view_state.expanded_positions)
            p.doDelete()
            c.setCurrentPosition(c.rootPosition())
            c.outline.revalidate_views()
            self.assertNotIn(gnx, c.view_state.expanded_positions)

    # @+node:sa.20260905150000.12: *3* TestOutline.test_removing_a_view
    def test_removing_a_view(self):
        c = self.c
        c2 = self.second_view()
        self.assertIs(c.outline.c, c)
        c.outline.remove_view(c)
        # The document survives, and the remaining view becomes the primary one.
        self.assertEqual(c.outline.views, [c2])
        self.assertIs(c.outline.c, c2)
        c.outline.add_view(c)
        self.assertEqual(c.outline.views, [c2, c])

    # @-others


# @-others
# @@language python
# @@tabwidth -4
# @-leo
