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

    # @-others


# @-others
# @-leo
