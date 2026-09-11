# @+leo-ver=5-thin
# @+node:sa.20260912100000.10: * @file ../unittests/leolib/test_leolib_corpus.py
"""
Check Python leolib against the conformance corpus in corpus/.

corpus/ is a copy of leo-rs's demo/, and leo-rs checks its Rust leolib against
the same files. Each .leo file is a case, beside the external files it names,
with a <name>.expected.json recording what Python leolib reads from it.
leo-rs's scripts/make_corpus.py writes the expected files, and its --copy-to
option refreshes this copy.

A failure means Python leolib no longer gives the answers the Rust port is held
to: fix the regression, or regenerate the corpus in leo-rs and say why.
"""

import json
import os
import unittest

from leo.unittests.leolib.test_leolib_boundary import run_isolated

CORPUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'corpus')


# @+others
# @+node:sa.20260912100000.11: ** CHECK_CORPUS
# Runs in a subprocess: what a node tangles to depends on process-global
# language tables, which earlier tests may have changed.
CHECK_CORPUS = r'''
import json, os, shutil, tempfile
from leo import leolib


def all_positions(o):
    """Every position in outline order, clones included each time."""
    p = o.rootPosition()
    while p:
        yield p.copy()
        p.moveToThreadNext()


def describe(path):
    """What leolib reads from path. Mirrors describe() in make_corpus.py."""
    probe = leolib.open_outline(path, read_external=False)
    at = probe.atFileCommands
    targets = [probe.fullPath(p) for p in at.findFilesToRead(probe.rootPosition(), all=True)]
    read_external = bool(targets) and all(os.path.exists(t) for t in targets)
    o, report = leolib.open_outline_with_report(path, read_external)
    positions = []
    for p in all_positions(o):
        imported = any(q.isAtAutoNode() for q in p.parents())
        positions.append({'level': p.level(), 'gnx': None if imported else p.gnx, 'h': p.h, 'b': p.b})
    return {
        'read_external': read_external,
        'unread': sorted(e.headline for e in report.errors),
        'positions': positions,
    }


def first_difference(got, want):
    for i, (g, w) in enumerate(zip(got['positions'], want['positions'])):
        if g != w:
            return f"position {i}: got {g}, expected {w}"
    if got['unread'] != want['unread']:
        return f"unread {got['unread']}, expected {want['unread']}"
    return f"{len(got['positions'])} positions, expected {len(want['positions'])}"


def snapshot(folder):
    out = {}
    for d, _, files in os.walk(folder):
        for f in files:
            with open(os.path.join(d, f), 'rb') as fh:
                out[os.path.relpath(os.path.join(d, f), folder)] = fh.read()
    return out


cases = sorted(
    os.path.join(d, f) for d, _, files in os.walk(CORPUS) for f in files if f.endswith('.leo')
)
result = {'cases': len(cases), 'read': [], 'xml': [], 'files': 0, 'rewritten': []}
for case in cases:
    name = os.path.relpath(case, CORPUS)
    with open(case[:-4] + '.expected.json', encoding='utf-8') as f:
        want = json.load(f)
    got = describe(case)
    if got != want:
        result['read'].append(f"{name}: {first_difference(got, want)}")
    with open(case, encoding='utf-8', newline='') as f:
        if leolib.to_xml(leolib.open_outline(case, read_external=False)) != f.read():
            result['xml'].append(name)
    if not want['read_external']:
        continue
    # Write every external file of a copy. Leo's writer leaves a file alone
    # when the text it would write is the text on disk, so no byte may change.
    with tempfile.TemporaryDirectory() as tmp:
        copy = os.path.join(tmp, 'case')
        shutil.copytree(os.path.dirname(case), copy)
        before = snapshot(copy)
        o = leolib.open_outline(os.path.join(copy, os.path.basename(case)))
        result['files'] += len(list(o.atFileCommands.findFilesToRead(o.rootPosition(), all=True)))
        leolib.write_external_files(o)
        after = snapshot(copy)
        for path in sorted(set(before) | set(after)):
            if before.get(path) != after.get(path):
                result['rewritten'].append(f"{name}: {path}")
print('RESULT', json.dumps(result))
'''


# @+node:sa.20260912100000.12: ** class TestLeolibCorpus
class TestLeolibCorpus(unittest.TestCase):
    """Python leolib gives the answers recorded in the corpus."""

    result: dict

    @classmethod
    def setUpClass(cls) -> None:
        out = run_isolated(f"CORPUS = {CORPUS!r}\n" + CHECK_CORPUS)
        cls.result = json.loads(out.split('RESULT', 1)[1])

    def test_corpus_is_present(self) -> None:
        self.assertGreaterEqual(self.result['cases'], 9, f"no corpus under {CORPUS}")
        self.assertGreater(self.result['files'], 10, 'too few external files in the corpus')

    def test_every_case_reads_as_expected(self) -> None:
        self.assertEqual(self.result['read'], [], 'read differently from the expected files')

    def test_the_leo_writer_reproduces_every_outline(self) -> None:
        self.assertEqual(self.result['xml'], [], 'not rewritten unchanged')

    def test_writing_changes_no_external_file(self) -> None:
        self.assertEqual(self.result['rewritten'], [], 'external files that writing changed')


# @-others
# @@language python
# @@tabwidth -4
# @-leo
