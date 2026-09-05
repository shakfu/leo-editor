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
        signal_manager.connect(c.outline, 'body_changed', lambda v, origin=None: heard.append(v.h))
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
    def test_other_views_are_redrawn_after_undo(self):
        """An undo in one window must not leave the others showing it stale."""
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
        # Both views are up to date: the acting one redrew itself, and the
        # passive one was drained by Outline.update_other_views rather than
        # being left holding a flag nothing would act on.
        self.assertFalse(c.requestLaterRedraw)
        self.assertFalse(c2.requestLaterRedraw)

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

    # @+node:sa.20260905180100.1: *3* TestOutline.record_events
    def record_events(self, c, signals=None):
        """Subscribe to the outline's bus and return the list events land in."""
        heard: list[tuple] = []
        signals = signals or (
            'body_changed',
            'head_changed',
            'structure_changed',
            'status_changed',
            'bulk_changed',
        )
        for sig in signals:
            signal_manager.connect(
                c.outline,
                sig,
                lambda v, origin=None, sig=sig: heard.append((sig, v and v.h, origin)),
            )
        return heard

    # @+node:sa.20260905180100.2: *3* TestOutline.test_the_event_set_covers_every_mutation
    def test_the_event_set_covers_every_mutation(self):
        """
        Every way of changing the model must reach a listener.

        A view that cannot see a change cannot stay in sync, and both in-tree
        second-view plugins had to poll because of gaps here.
        """
        c = self.c
        root = c.rootPosition()
        root.h = 'root'
        heard = self.record_events(c)

        root.b = 'body'
        self.assertIn('body_changed', [z[0] for z in heard])

        heard.clear()
        root.h = 'renamed'
        self.assertIn('head_changed', [z[0] for z in heard])

        heard.clear()
        child = root.insertAsLastChild()
        child.h = 'child'
        self.assertIn('structure_changed', [z[0] for z in heard])

        heard.clear()
        child.setMarked()
        self.assertIn('status_changed', [z[0] for z in heard])

        heard.clear()
        child.clearMarked()
        self.assertIn('status_changed', [z[0] for z in heard])

        heard.clear()
        child.doDelete()
        c.setCurrentPosition(c.rootPosition())
        self.assertIn('structure_changed', [z[0] for z in heard])

    # @+node:sa.20260905180100.3: *3* TestOutline.test_events_carry_their_origin
    def test_events_carry_their_origin(self):
        """
        A listener must be able to tell which window caused a change.

        Without it a view cannot ignore its own events, and stage 6 would make
        every keystroke fight the caret of the window doing the typing.
        """
        c = self.c
        c.rootPosition().h = 'root'
        c2 = self.second_view()
        heard = self.record_events(c, ('body_changed',))
        with c.outline.acting_view(c2):
            c2.rootPosition().b = 'typed in the second view'
        with c.outline.acting_view(c):
            c.rootPosition().b = 'typed in the first view'
        c.rootPosition().b = 'from a script'
        self.assertEqual([z[2] for z in heard], [c2, c, None])

    # @+node:sa.20260905180100.4: *3* TestOutline.test_bulk_changes_are_coalesced
    def test_bulk_changes_are_coalesced(self):
        """Reading a 10,000-node file must not deliver 10,000 events."""
        c = self.c
        root = c.rootPosition()
        root.h = 'root'
        heard = self.record_events(c)
        with c.outline.batch_events():
            for i in range(50):
                p = root.insertAsLastChild()
                p.h = f'child {i}'
                p.b = f'body {i}'
        self.assertEqual([z[0] for z in heard], ['bulk_changed'])
        # Nesting is safe: only the outermost block delivers.
        heard.clear()
        with c.outline.batch_events():
            with c.outline.batch_events():
                root.b = 'x'
            self.assertEqual(heard, [])
        self.assertEqual([z[0] for z in heard], ['bulk_changed'])

    # @+node:sa.20260905180100.5: *3* TestOutline.test_a_structural_command_revalidates_views
    def test_a_structural_command_revalidates_views(self):
        """
        c.doCommand sweeps the views when a command changed the outline's shape.

        Undo is not the only way one window can delete the node another is
        sitting on.
        """
        c = self.c
        c.rootPosition().h = 'root'
        child = c.rootPosition().insertAsLastChild()
        child.h = 'child'
        c2 = self.second_view()
        c2.selectPosition(c2.rootPosition().lastChild())
        self.assertEqual(c2.p.h, 'child')

        def delete_the_child(event=None):
            c.rootPosition().lastChild().doDelete()
            c.setCurrentPosition(c.rootPosition())

        # Building the tree above already set the flag: start from a clean slate.
        c.outline.structure_dirty = False
        c.doCommand(delete_the_child, 'delete-the-child')
        # The other view was sitting on the deleted node.
        self.assertTrue(c2.positionExists(c2.p), c2.p)
        self.assertEqual(c2.p.h, 'root')
        self.assertFalse(c.outline.structure_dirty)

    # @+node:sa.20260905190300.1: *3* TestOutline.test_body_text_syncs_live_between_views
    def test_body_text_syncs_live_between_views(self):
        """
        A change to a node's body reaches every view showing it, at once.

        Until stage 6 the widget was authoritative between selection changes,
        so a second view showed stale text until it reselected the node.
        """
        c = self.c
        root = c.rootPosition()
        root.h, root.b = 'root', 'original'
        c2 = self.second_view()
        c.selectPosition(c.rootPosition())
        c2.selectPosition(c2.rootPosition())
        w, w2 = c.frame.body.wrapper, c2.frame.body.wrapper
        self.assertEqual(w2.getAllText(), 'original')
        with c.outline.acting_view(c):
            c.p.b = 'typed in the first view'
        # No reselect, no redraw: the second view's widget is already right.
        self.assertEqual(w2.getAllText(), 'typed in the first view')
        self.assertEqual(w.getAllText(), 'typed in the first view')

    # @+node:sa.20260905190300.2: *3* TestOutline.test_a_view_keeps_its_caret_when_another_edits
    def test_a_view_keeps_its_caret_when_another_edits(self):
        """
        Following someone else's edit must not move this view's caret.

        The caret is clamped when the new text is shorter than the old one.
        """
        c = self.c
        root = c.rootPosition()
        root.h, root.b = 'root', 'a long original body'
        c2 = self.second_view()
        c.selectPosition(c.rootPosition())
        c2.selectPosition(c2.rootPosition())
        w2 = c2.frame.body.wrapper
        w2.setInsertPoint(5)
        with c.outline.acting_view(c):
            c.p.b = 'another long body here'
        self.assertEqual(w2.getInsertPoint(), 5)  # Untouched.
        with c.outline.acting_view(c):
            c.p.b = 'tiny'
        self.assertEqual(w2.getAllText(), 'tiny')
        self.assertEqual(w2.getInsertPoint(), 4)  # Clamped, not out of range.

    # @+node:sa.20260905190300.3: *3* TestOutline.test_a_view_ignores_its_own_edits
    def test_a_view_ignores_its_own_edits(self):
        """
        The view that made a change must not repaint from its own event.

        Repainting would replace the widget's text under the user's cursor on
        every keystroke.
        """
        c = self.c
        c.rootPosition().h = 'root'
        c.selectPosition(c.rootPosition())
        w = c.frame.body.wrapper
        calls = []
        original = w.setAllText

        def counting_setAllText(s):
            calls.append(s)
            original(s)

        w.setAllText = counting_setAllText
        try:
            with c.outline.acting_view(c):
                c.p.v.setBodyString('typed here')
        finally:
            w.setAllText = original
        self.assertEqual(calls, [], 'the acting view repainted its own widget')

    # @+node:sa.20260905260000.1: *3* TestOutline.test_context_is_not_a_commander
    def test_context_is_not_a_commander(self):
        """
        Code that needs a *window* must say `.context.c`, not `.context`.

        Stage 3 changed VNode.context from a commander to an Outline, and
        Outline deliberately has no __getattr__ -- the explicit forwarding list
        *is* the remaining coupling, so it must not be papered over. The cost
        is that any call site still treating .context as a commander raises
        AttributeError the first time a user reaches it, rather than at import
        or in a test.

        These are the paths that were found that way. Each needs a member the
        document does not have and should not grow: c.getPath here, and
        c.hoistStack via p.isVisible below.
        """
        c = self.c
        # A saved outline: computeFileUrl only consults c.getPath when the
        # outline has a file name, which is why an unsaved one hid this.
        c.outline.mFileName = '/tmp/does-not-need-to-exist.leo'
        p = c.rootPosition()
        p.h = '@url some/file.txt'
        g.getUrlFromNode(p)  # Raised: 'Outline' object has no attribute 'getPath'.

        # p.isVisible reads c.hoistStack, which is per-view and is deliberately
        # not forwarded. The helper takes the caller's commander now.
        c.selectPosition(p)
        p.insertAsLastChild().h = 'child'
        c.p.copy().moveToVisBack(c)

    # @+node:sa.20260905250003.1: *3* TestOutline.test_document_operations_are_owned_by_the_outline
    def test_document_operations_are_owned_by_the_outline(self):
        """
        Some questions have one answer per *document*, not one per window.

        These three were forwarded from the Outline to its primary view, which
        is backwards: the commander should ask the document. Every view must
        get the same answer, including a view that is not the primary one.
        """
        c = self.c
        root = c.rootPosition()
        root.h = 'root'
        c2 = self.second_view()
        outline = c.outline

        # Whether a position exists is a fact about the tree.
        p = c.rootPosition()
        self.assertTrue(outline.positionExists(p))
        self.assertTrue(c.positionExists(p))
        self.assertTrue(c2.positionExists(p))
        gone = p.insertAsLastChild()
        gone.doDelete()
        self.assertFalse(outline.positionExists(gone))
        self.assertFalse(c2.positionExists(gone))

        # So is the document's name.
        self.assertEqual(c.shortFileName(), outline.shortFileName())
        self.assertEqual(c2.shortFileName(), outline.shortFileName())

        # And setting a headline is a model write that every view follows.
        outline.setHeadString(c.rootPosition(), 'renamed by the document')
        self.assertEqual(c2.rootPosition().h, 'renamed by the document')
        w2 = c2.frame.tree.headline_wrapper(c2.rootPosition())
        self.assertEqual(w2.getAllText(), 'renamed by the document')

    # @+node:sa.20260905240100.1: *3* TestOutline.test_headline_syncs_live_between_views
    def test_headline_syncs_live_between_views(self):
        """
        A rename in one view reaches the other view's headline widget at once.

        The headline half of the previous test. It matters more than it looks:
        onHeadChanged commits whatever the widget holds, so a second view left
        with a stale widget does not merely display the old name -- it puts the
        old name back the next time anything commits that widget.
        """
        c = self.c
        c.rootPosition().h = 'original'
        c2 = self.second_view()
        c.selectPosition(c.rootPosition())
        c2.selectPosition(c2.rootPosition())
        w2 = c2.frame.tree.headline_wrapper(c2.p)
        self.assertEqual(w2.getAllText(), 'original')

        with c.outline.acting_view(c):
            c.p.h = 'renamed in the first view'
        self.assertEqual(w2.getAllText(), 'renamed in the first view')

        # And the second view's commit agrees rather than reverting.
        c2.frame.tree.onHeadChanged(c2.p)
        self.assertEqual(c.rootPosition().h, 'renamed in the first view')

    # @+node:sa.20260905240100.2: *3* TestOutline.test_get_and_set_head_text
    def test_get_and_set_head_text(self):
        """c.getHeadText/c.setHeadText answer for the document, not a window."""
        c = self.c
        root = c.rootPosition()
        root.h = 'root'
        other = root.insertAsLastChild()
        other.h = 'other'
        c.selectPosition(c.rootPosition())
        self.assertEqual(c.getHeadText(), 'root')
        # A node this window has no headline widget for: it could not answer.
        self.assertEqual(c.getHeadText(c.rootPosition().lastChild()), 'other')
        c.setHeadText('changed', p=c.rootPosition().lastChild())
        self.assertEqual(c.rootPosition().lastChild().h, 'changed')

    # @+node:sa.20260905190300.4: *3* TestOutline.test_get_and_set_body_text
    def test_get_and_set_body_text(self):
        """c.getBodyText/c.setBodyText answer for the document, not a window."""
        c = self.c
        root = c.rootPosition()
        root.h, root.b = 'root', 'body'
        other = root.insertAsLastChild()
        other.h, other.b = 'other', 'other body'
        c.selectPosition(c.rootPosition())
        self.assertEqual(c.getBodyText(), 'body')
        # A node this window is *not* showing: the widget could not answer.
        self.assertEqual(c.getBodyText(c.rootPosition().lastChild()), 'other body')
        c.setBodyText('changed', p=c.rootPosition().lastChild())
        self.assertEqual(c.rootPosition().lastChild().b, 'changed')

    # @+node:sa.20260905200100.1: *3* TestOutline.test_passive_views_are_drawn_not_just_flagged
    def test_passive_views_are_drawn_not_just_flagged(self):
        """
        A window that did not act must actually repaint, not just be flagged.

        c.redraw_later only sets requestLaterRedraw. Measured under real Qt:
        the event loop does not drain it -- a passive window showed stale
        content until it was clicked.
        """
        c = self.c
        c.rootPosition().h = 'root'
        c2 = self.second_view()
        c.requestLaterRedraw = False
        c2.requestLaterRedraw = False
        with c.outline.acting_view(c2):
            p = c2.rootPosition().insertAsLastChild()
            p.h = 'added by the second view'
            c.outline.revalidate_views(acting_c=c2)
        self.assertFalse(c.requestLaterRedraw, 'the passive view was left undrawn')

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
