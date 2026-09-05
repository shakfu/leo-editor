# @+leo-ver=5-thin
# @+node:ekr.20210903161742.1: * @file ../unittests/core/test_leoFrame.py
"""Tests of leoFrame.py"""

from leo.core.leoTest2 import LeoUnitTest


# @+others
# @+node:ekr.20210903161742.2: ** class TestFrame(LeoUnitTest)
class TestFrame(LeoUnitTest):
    """Test cases for leoKeys.py"""

    # @+others
    # @+node:ekr.20210901140645.10: *3* TestFrame.test_official_frame_ivars
    def test_official_frame_ivars(self):
        c = self.c
        f = c.frame
        self.assertEqual(f.c, c)
        self.assertEqual(c.frame, f)
        for ivar in (
            'body',
            'iconBar',
            'log',
            'statusLine',
            'tree',
        ):
            assert hasattr(f, ivar), 'missing frame ivar: %s' % ivar
            val = getattr(f, ivar)
            self.assertTrue(val is not None, msg=ivar)

    # @+node:sa.20260905230000.1: *3* TestFrame.test_endEditLabel_commits_only_a_real_edit
    def test_endEditLabel_commits_only_a_real_edit(self):
        """
        endEditLabel must not commit a headline that nobody edited.

        onHeadChanged takes the new headline from headline_wrapper(p), not from
        p.h, so code that renames a node through the model leaves that widget
        stale. c.endEditing runs at the top of u.undo; committing a stale
        widget there records a headline change the user never made, which
        pushes an undo bead and silently eats the next undo.

        LeoQtTree.endEditLabel already returned early with no editor open; the
        base class did not, so only non-Qt views saw this.
        """
        c = self.c
        u = c.undoer
        p = c.rootPosition()
        p.h = 'original'
        c.selectPosition(p)

        # Rename through the model, as any view or script may.
        bunch = u.beforeChangeHeadline(p)
        p.v.setHeadString('renamed')
        u.afterChangeHeadline(p, 'Change Headline', bunch)
        self.assertEqual(len(u.beads), 1)

        # No edit was ever started, so this must record nothing.
        self.assertIsNone(c.frame.tree.editing_p)
        c.endEditing()
        self.assertEqual(len(u.beads), 1, 'endEditing invented a headline change')

        # ...and undo therefore still works.
        u.undo()
        self.assertEqual(p.h, 'original')

    # @+node:sa.20260905230000.2: *3* TestFrame.test_endEditLabel_after_a_real_edit
    def test_endEditLabel_after_a_real_edit(self):
        """A headline edit that really was started is still committed."""
        c = self.c
        p = c.rootPosition()
        p.h = 'original'
        c.selectPosition(p)
        c.frame.tree.editLabel(p)
        self.assertIsNotNone(c.frame.tree.editing_p)
        c.endEditing()
        self.assertIsNone(c.frame.tree.editing_p)

    # @+node:sa.20260905240000.1: *3* TestFrame.test_headline_widget_follows_the_model
    def test_headline_widget_follows_the_model(self):
        """
        A model-only rename must reach this view's headline widget.

        Otherwise onHeadChanged, which commits whatever the widget holds, puts
        the old headline back -- so a stale widget does not merely look wrong,
        it silently reverts the rename.
        """
        c = self.c
        tree = c.frame.tree
        p = c.rootPosition()
        p.h = 'original'
        c.selectPosition(p)
        w = tree.headline_wrapper(p)
        self.assertEqual(w.getAllText(), 'original')

        p.v.setHeadString('renamed')
        self.assertEqual(w.getAllText(), 'renamed')

        # The commit now agrees with the model instead of undoing it.
        tree.onHeadChanged(p)
        self.assertEqual(p.h, 'renamed')

    # @+node:sa.20260905240000.2: *3* TestFrame.test_open_editor_keeps_unsaved_keystrokes
    def test_open_editor_keeps_unsaved_keystrokes(self):
        """A rename from elsewhere must not overwrite what the user is typing."""
        c = self.c
        tree = c.frame.tree
        p = c.rootPosition()
        p.h = 'original'
        c.selectPosition(p)
        tree.editLabel(p)
        w = tree.headline_wrapper(p)
        w.setAllText('half-typ')  # Keystrokes the model has not seen.

        p.v.setHeadString('renamed elsewhere')
        self.assertEqual(w.getAllText(), 'half-typ')

    # @+node:sa.20260905240000.3: *3* TestFrame.test_untouched_editor_follows_the_model
    def test_untouched_editor_follows_the_model(self):
        """
        An *untouched* open editor still follows a programmatic rename.

        "An editor is open" is too broad a reason to freeze the widget: with
        nothing unsaved in it there is nothing to protect, and freezing it
        would leave the stale text that gets committed later.
        """
        c = self.c
        tree = c.frame.tree
        p = c.rootPosition()
        p.h = 'original'
        c.selectPosition(p)
        tree.editLabel(p)
        w = tree.headline_wrapper(p)
        self.assertEqual(w.getAllText(), 'original')

        p.h = 'renamed'
        self.assertEqual(w.getAllText(), 'renamed')

    # @+node:sa.20260905240000.4: *3* TestFrame.test_onHeadChanged_accepts_text
    def test_onHeadChanged_accepts_text(self):
        """A view with no headline widget can still commit a headline."""
        c = self.c
        u = c.undoer
        p = c.rootPosition()
        p.h = 'original'
        c.selectPosition(p)
        n = len(u.beads)

        c.frame.tree.onHeadChanged(p, undoType='Change Headline', s='from the model')
        self.assertEqual(p.h, 'from the model')
        self.assertEqual(len(u.beads), n + 1)
        u.undo()
        self.assertEqual(p.h, 'original')

    # @+node:sa.20260905240000.5: *3* TestFrame.test_onHeadChanged_truncates_only_the_model
    def test_onHeadChanged_truncates_only_the_model(self):
        """
        onHeadChanged stores less than the widget holds, and that must stand.

        Newlines collapse to blanks on the way into the model, but the widget
        keeps what the user typed. Syncing the widget back from the model here
        would delete the user's text in front of them.
        """
        c = self.c
        tree = c.frame.tree
        p = c.rootPosition()
        c.selectPosition(p)
        tree.editLabel(p)
        w = tree.headline_wrapper(p)
        w.setAllText('two\nlines')

        tree.onHeadChanged(p)
        self.assertEqual(p.h, 'two lines')
        self.assertEqual(w.getAllText(), 'two\nlines')

    # @+node:sa.20260905240000.6: *3* TestFrame.test_setHeadText
    def test_setHeadText(self):
        """c.setHeadText writes the model; undoType decides whether it is undoable."""
        c = self.c
        u = c.undoer
        p = c.rootPosition()
        p.h = 'original'
        c.selectPosition(p)

        n = len(u.beads)
        c.setHeadText('quietly', p=p)
        self.assertEqual(c.getHeadText(p), 'quietly')
        self.assertEqual(len(u.beads), n, 'a bare model write must push no bead')

        c.setHeadText('undoably', p=p, undoType='Change Headline')
        self.assertEqual(c.getHeadText(p), 'undoably')
        self.assertEqual(len(u.beads), n + 1)
        u.undo()
        self.assertEqual(p.h, 'quietly')

    # @+node:sa.20260905240000.7: *3* TestFrame.test_undo_updates_every_headline_widget
    def test_undo_updates_every_headline_widget(self):
        """
        Undoing a multi-node rename must refresh every node's headline widget.

        The undo helpers used to write the model and then re-drive the widget
        by hand, with the comment "otherwise redraw will revert the change!".
        For a multi-headline undo they only did that for u.p, so every *other*
        renamed node kept a stale widget -- and a stale widget is what
        onHeadChanged commits. Views follow head_changed now, so all of them
        keep up and the hand-driving is gone.
        """
        c = self.c
        u = c.undoer
        tree = c.frame.tree
        root = c.rootPosition()
        root.h = 'first'
        second = root.insertAsLastChild()
        second.h = 'second'
        c.selectPosition(c.rootPosition())

        bunch = u.beforeChangeMultiHeadline(c.p)
        c.rootPosition().h = 'first renamed'
        c.rootPosition().lastChild().h = 'second renamed'
        u.afterChangeMultiHeadline('Change Headlines', bunch)

        # The node that is *not* u.p is the one that used to be missed.
        other = c.rootPosition().lastChild()
        self.assertEqual(tree.headline_wrapper(other).getAllText(), 'second renamed')
        u.undo()
        other = c.rootPosition().lastChild()
        self.assertEqual(other.h, 'second')
        self.assertEqual(tree.headline_wrapper(other).getAllText(), 'second')

    # @-others


# @-others
# @-leo
