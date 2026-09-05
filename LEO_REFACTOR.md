# Decoupling Leo's model from its GUI

*An exploration of whether Leo's outline model can be separated from the Qt front end,
and whether multiple simultaneous views on one model are reachable.*

Written against `main` @ `2844177134`. All claims below were checked against the code
and, where marked **(verified)**, reproduced by running the code.

---

## Verdict

**Yes — and Leo is much closer to it than the source reads at first glance.**

The data model (`VNode` / `Position` in `leo/core/leoNodes.py`) is already free of GUI
concepts. I confirmed experimentally that two commanders can share a single `VNode`
tree, hold independent current positions, and see each other's edits, with only one
guard rejecting the arrangement. The obstacles are not in the model; they are in four
places that surround it:

1. an **import-time** dependency on PyQt6 that reaches all the way into `leoApp`,
2. the **commander** (`Commands`) conflating "the document" with "the window",
3. the **body widget** acting as the live source of truth for body text, and
4. the **absence of any change notification** from the model outward.

Each is addressable incrementally. None requires a rewrite. The realistic hard part is
(3), and it is quantifiable: roughly 660 calls in `leo/core` + `leo/commands` go through
the single body text wrapper.

One design question had to be settled before the plan could be written, and it has been:
**the undo stack is per outline, shared by all its views** — see *Undo across views*.

The complete plan is in *Staged plan* below: eight stages, ordered so each is
independently valuable and independently revertable, with the first two plausibly
upstreamable on their own merits.

---

## How I explored

Static reading, plus three executable probes. The probes matter because they turn
"looks coupled" into "is / isn't coupled".

PyQt6 is not installed in this environment, which produced the first result for free:

```
$ python3 -c "from leo.core import leoTest2"
ModuleNotFoundError: No module named 'PyQt6'
```

To get past it I wrote a ~25-line **fake `PyQt6` package** — modules and classes that
auto-generate attributes on demand and do nothing. With that on `PYTHONPATH`, Leo's
null-GUI stack came up completely:

```
created commander in 0.22s  gui= nullGui
frame: NullFrame  tree: NullTree  body: NullBody
```

That is itself a finding: **Leo's core does not *use* Qt headlessly, it only *imports*
it.** A shim of do-nothing objects is enough. The coupling at this layer is mechanical,
not semantic.

The probe scripts are reproduced in the appendix.

---

## The current architecture, as built

```
                    g.app  (LeoApp singleton)
                      │  .gui   .log   .windowList   .db
                      │
      ┌───────────────┴────────────────┐
      │                                │
   c = Commands  ──────────────────► c.frame = LeoFrame
   (one per .leo file)                  │  .tree  (LeoTree)
      │  .hiddenRootNode  ── model      │  .body  (LeoBody → .wrapper)
      │  .p / ._currentPosition         │  .log   (LeoLog)
      │  .hoistStack                    │  .menu, .statusLine, .iconBar
      │  .undoer, .fileCommands, .k     │
      │  .chapterController          Qt subclasses in leo/plugins/qt_*.py
      │                              Null* subclasses in leoFrame.py
      ▼
   VNode tree  (gnx-keyed, .context = c)
```

`Commands.__init__` calls `initObjects`, which does:

```python
self.hiddenRootNode = VNode(context=c, gnx='hidden-root-vnode-gnx')
...
self.frame = gui.createLeoFrame(c, title)      # leoCommands.py:355
```

Model root and window are created in the same constructor, three lines apart. That is
the structural statement of the 1:1 binding.

There is real abstraction here — `LeoGui`, `LeoFrame`, `LeoTree`, `LeoBody`, `LeoLog`
are base classes with `Null*` and `LeoQt*` implementations, and the `Null*` path
genuinely works. Leo is an MVC design whose V and C were merged for pragmatic reasons
over 25 years, not a monolith that never tried.

---

## Findings

### 1. The abstraction layer imports the implementation it abstracts

`leoGui.py` — whose docstring says *"These classes hide the details of which gui is
actually being used"* — begins:

```python
from leo.core.leoQt import QtWidgets                                   # leoGui.py:20
from leo.plugins.qt_frame import LeoQTreeWidget                        # leoGui.py:21
from leo.plugins.qt_text import QLineEditWrapper, QTextEditWrapper, …  # leoGui.py:22
```

These are unconditional, module-level imports of the Qt back end by the GUI-neutral
layer. The same pattern appears in:

| Module | Unconditional import |
|---|---|
| `leoAPI.py:12` | `from leo.plugins.qt_text import QTextMixin` |
| `leoApp.py:22,31,32` | `leoQt`, `qt_events.LossageData`, `qt_idle_time.IdleTime` |
| `leoConfig.py:16` | `from leo.plugins.mod_scripting import build_rclick_tree` |
| `leoFind.py:15` | `from leo.plugins.qt_frame import FindTabManager` |
| `leoKeys.py:21` | `from leo.core.leoQt import QtWidgets` |
| `leoVim.py:31` | `from leo.plugins.qt_text import QTextMixin` |
| `leoBackground.py:14` | `from leo.core.leoQt import QtCore` |

And `leoQt.py` itself has no fallback — `from PyQt6 import QtCore, QtGui, QtWidgets`
at line 10, no `try`. `pyproject.toml:270` makes `PyQt6>=6.6` a hard install dependency.

**Consequence:** `leoBridge`, `leoserver`, the null GUI, and the entire unit-test suite
cannot run without PyQt6 installed, despite none of them drawing a pixel. The dependency
is nominal, but it is load-bearing for packaging: no `pip install leo-core` without Qt.

**This is the cheapest high-value fix in the whole exercise** — see Stage 1.

### 2. The model is already view-agnostic (verified)

`leoNodes.py` is 3,095 lines with **six** references to anything GUI-shaped, and only
two are real (`leoNodes.py:2840`, `:2897`). `Position` and `VNode` know about parents,
children, gnx, body, headline, and status bits. Nothing else.

I tested the strong form of the claim — one model, two commanders:

```python
c2 = leoCommands.Commands(fileName=None, gui=g.app.gui)
c2.hiddenRootNode = c1.hiddenRootNode          # share the model outright

c2 sees root: shared root | children: ['child A']
c1.p = child A    c2.p = shared root           # independent cursors ✓
p.b = 'edited via c2'  →  c1 root body: 'edited via c2'   # shared state ✓
```

Two independent views on one outline, with separate current positions and separate
undo stacks, working. The only complaint was one guard:

```
selectHelper Wrong context: Commander …592304 != Commander …345088
```

from `LeoTree.selectHelper` (`leoFrame.py:930`), because `v.context` is a *commander*,
not a document. **That single field is the conceptual error at the centre of the
problem**, and it is referenced in only ~50 places in `leo/core`.

### 3. `c` is the document *and* the window

The commander mixes three distinct responsibilities:

| Document state | View state | Wiring |
|---|---|---|
| `hiddenRootNode`, `fileCommands`, `undoer`, `mFileName`, `changed`, `db` | `p` / `_currentPosition`, `hoistStack`, `chapterController`, `expansionLevel`, `requestedFocusWidget`, `enableRedrawFlag`, `requestLaterRedraw` | `frame`, `k`, `gui` |

`c.p` is the clearest case: "which node is selected" is a property of a *view*, but it
lives on the object that owns the data. Two views of one outline must have two `c.p`
values — which is exactly why the probe above needed two commanders to get two cursors.

The `Commands` class is 5,676 lines with 78 direct GUI references.

### 4. The body widget is the source of truth for body text

This is the deepest coupling, and the one with real cost. Across `leo/core` and
`leo/commands`:

| Path | Count |
|---|---|
| `c.frame.body.wrapper` (usually aliased to `w`) | 222 |
| `w.getAllText()` | 150 |
| `w.getInsertPoint()` | 140 |
| `w.setSelectionRange()` | 113 |
| `w.setInsertPoint()` | 68 |
| `w.getSelectionRange()` | 88 |
| `w.setAllText()` | 43 |
| scroll / `seeInsertPoint` | 55 |

**~660 calls** treating the widget as the buffer. Core commands don't edit `p.b`; they
edit the widget and let the widget tell the model afterwards, via
`QTextMixin.onTextChanged` (`qt_text.py:199`) → `c.undoer.doTyping(...)` →
`p.v.setBodyString(newText)` (`leoUndo.py:1221`).

The divergence is observable **(verified)**:

```
v.b            = 'bytes body'
wrapper text   = 'hello world'        ← stale
after select   = 'bytes body'         ← reconciled only on selection change
```

With one view this is invisible. With two views it is the whole problem: a second
editor on the same node reads `p.b` and gets text that is one selection-change behind
whatever the user is typing in the first.

`LeoTree.set_body_text_after_select` (`leoFrame.py:985`) is the reconciliation point,
and it also sets `c.p` as a side effect of setting widget text — model state updated
from inside a view-refresh routine.

### 5. View state is stored on the shared model

`VNode.statusBits` (`leoNodes.py:2260`) carries `expandedBit` and `selectedBit`;
`VNode` also has `insertSpot` and `scrollBarSpot` (`leoNodes.py:2298-2299`). These are
per-*view* facts — "is this node expanded **in which outline pane**?" — stored on the
node itself. Expanded/marked sets are persisted per-commander in `c.db`
(`leoFileCommands.py:210`), so the persistence layer is already per-document rather
than baked into the `.leo` file, which helps.

With two views open, expansion state collides: collapsing a node in one pane collapses
it in the other. Any multi-view design must move these bits into a per-view side table
keyed by gnx.

### 6. The one model→view notification that exists is dead code

`leoNodes.py` imports `signal_manager` and emits exactly one signal:

```python
def setBodyString(self, s: bytes | str) -> None:
    v = self
    if isinstance(s, str):
        v._bodyString = s                                    # ← normal path: silent
    else:  # pragma: no cover
        v._bodyString = g.toUnicode(s, reportErrors=True)
        self.contentModified()                               # #1413
        signal_manager.emit(self.context, 'body_changed', self)
    v.updateIcon()
```

The `emit` — and `contentModified()` with it — sit in the `bytes` branch. Every normal
`p.b = "..."` assignment in Python 3 takes the `str` branch and notifies nobody.
Verified:

```
after p.b = str            -> signal hits: 0
after setBodyString(bytes) -> signal hits: 1
```

`setHeadString` has the identical shape. `git log -L` shows the structure predates the
recent commits that touched the region, so this is long-standing, not a fresh
regression. The `# pragma: no cover` on the live branch says as much.

`leo/plugins/editpane/editpane.py:226` subscribes to `'body_changed'` — the only
consumer in the tree, and it effectively never fires. That is presumably why the other
in-tree second-view plugin, **freewin**, gave up and polls: `self.handlers = [('idle',
self.update)]` (`freewin.py:818`), diffing the host node's text on every idle tick.

**Two independent implementations of "a second view on a node" both had to work around
the missing notification.** That is the strongest argument in the repo that this
refactor is worth doing.

### 7. Undo is entangled with the view

`leoUndo.py` has 35 GUI references, nearly all `w = c.frame.body.wrapper`. Undo bunches
record and restore selection ranges and scroll positions, and call
`c.frame.tree.setHeadline(...)` directly (`leoUndo.py:1441,1466,1479,1494`). So undo is
not a pure model operation: replaying it drives one specific widget.

The undoer is also per-commander. My probe confirmed that two commanders sharing one
`VNode` tree get two independent undo stacks — each blind to the other's edits, each
able to replay a bunch whose preconditions the other has already invalidated. That is
not a workable arrangement for multiple views.

**Resolved: the undo stack is per outline.** See *Undo across views* below for what
that implies.

### 8. Global singletons

`g.app` holds `gui`, `log`, `windowList`, `db` as process globals
(`leoApp.py:144,204,217,275`). `g.app.gui` is read 173 times in `leo/core` alone, 543
times across `core` + `commands` + `plugins`. This means "the GUI" is a process-wide
fact, not a per-view one — two *different kinds* of view (say Qt and a web client) in
one process is out of reach until this is per-view or per-frame.

`leoserver.py` shows the pressure this creates: it monkey-patches the singleton at
runtime to redirect dialogs:

```python
g.app.gui.runAskOkDialog       = self._runAskOkDialog        # leoserver.py:1005
g.app.gui.runAskYesNoDialog    = self._runAskYesNoDialog
g.app.gui.show_find_success    = self._show_find_success
```

That is the abstraction failing and being patched over at the seam.

---

## What already exists (don't rebuild it)

| Component | What it proves |
|---|---|
| `NullGui` / `NullFrame` / `NullTree` / `NullBody` (`leoGui.py`, `leoFrame.py`) | The frame interface is already implementable without Qt, and the null path works. |
| `leoBridge.py` (370 lines) | Full commander access from outside Leo, explicitly designed to import no Leo modules at top level. |
| `leoserver.py` (6,247 lines) | A **real second front end** — leoInteg / LeoJS drive Leo over websockets against a null GUI, serializing "cheap redraw data" per response (`_get_position_d`, `leoserver.py:5250`). |
| `editpane/` (Terry Brown) | A per-node view framework with pluggable renderers, wired to `signal_manager`. The intended design; starved of events. |
| `freewin.py` (Thomas Passin) | A detached node-locked editor window, kept in sync by idle-polling. |
| `signal_manager.py` | A tiny, dependency-free pub/sub already vendored in core. |
| `leo/unittests/` (41 test files) | A headless regression net — the safety harness for all of this. |

The 85 distinct `c.frame.*` attribute paths used by `core` + `commands` constitute the
de-facto view interface. It is already written down, just not as a protocol.

---

## Target architecture

```
   Outline                     ← the model. Owns hiddenRootNode, gnx index,
     .hiddenRootNode              file name, dirty flag, undo history.
     .gnxDict                     Knows nothing about views.
     .changes  (event bus)      ← emits: body_changed, head_changed,
                                   structure_changed, node_inserted/deleted
        ▲          │
        │          ▼  events
   commands    ┌───────────────┬───────────────┬──────────────┐
   operate     │               │               │              │
   on model  View A          View B          View C        leoserver
   (Qt tree +  (Qt outline)   (second Qt      (web / TUI /   (websocket)
    body)                      pane, same      read-only
                               outline)        renderer)
     each View owns: current position, hoist stack, chapter, expansion set,
                     selection & scroll, focus — keyed by gnx, never on the VNode
```

Three rules to hold the line:

1. **The model never calls a view.** It emits events. Views subscribe.
2. **Commands mutate the model, never a widget.** `p.b = s`, not `w.setAllText(s)`.
3. **Per-view state is keyed by gnx in the view**, never stored on the `VNode`.
4. **One outline, one undo history.** See below.

### Undo across views

**Decision: the undo stack lives on the `Outline`, shared by every view of it.**

The alternative — a stack per view — is superficially attractive because it matches
what a user's hands expect from tabbed editors, but it is incoherent here. Two views
of one outline are editing *the same nodes*, not two copies. A per-view stack would let
view B undo past a change view A made in between, replaying a bunch whose preconditions
no longer hold. There is no honest way to reconcile that: undo is a property of the
document's history, and Leo has exactly one document here.

What follows from the decision:

- **`Outline.undoer`, not `Commands.undoer`.** `c.undoer` becomes a forwarding property
  so existing code and plugins keep working.
- **Undo is global to the outline, and the UI must say so.** `Ctrl-Z` in view B undoes
  the last change to the outline, even if view A made it. This is the correct behaviour
  and it *will* surprise people, so the status line should name what was undone
  (`c.frame.putStatusLine` already exists for this) rather than silently teleporting the
  user's outline out from under them.
- **Every bunch splits in two parts:**

  | Part | Contents | Replayed |
  |---|---|---|
  | Model state | node identity (gnx), before/after body and headline, structural change | always, authoritatively |
  | View hint | originating view id, insert point, selection range, y-scroll | only into the originating view, only if it still exists |

  A view that did not originate a change learns about it through the stage 2 events and
  updates itself; it keeps its own cursor. A view that has since been closed simply
  drops its hint.
- **Selection restore stops being part of undo's contract.** Today undo restores the
  selection into `c.frame.body.wrapper` unconditionally. With several views that is
  ambiguous, so it degrades to a best-effort hint. This is a small, deliberate
  behavioural regression for the single-view case and should be called out in the
  commit message rather than discovered by users.
- **Positions must be clamped after every undo.** An undo initiated in view A can delete
  the node view B is sitting on. Each view revalidates its current position on
  `structure_changed` and falls back to the nearest surviving ancestor.
- **Undo groups are shared too.** `beforeChangeGroup` / `afterChangeGroup` open a group
  on the outline, not on a view, so an unrelated edit from another view must not be
  swallowed into someone else's group.

---

## Staged plan

Ordered so every stage is independently valuable, independently revertable, and leaves
the tests green. Effort figures are rough calibration, not estimates.

| Stage | What | Effort | Risk | Gives you |
|---|---|---|---|---|
| 0 | Headless CI safety net | small | none | permission to touch anything |
| 1 | Break the import-time Qt dependency | small | low | `import leo` with no Qt; upstreamable |
| 2 | Fix and complete model notifications | small-med | low | a live event bus; upstreamable bug fix |
| 3 | Extract `Outline` from `Commands` | medium | medium | **two views on one outline** |
| 4 | Unify the undo stack on the `Outline` | medium | medium | coherent undo across views |
| 5 | Move per-view state off the `VNode` | medium | medium | independent expansion/scroll per view |
| 6 | Make the model authoritative for body text | large | medium | live sync of an actively-edited body |
| 7 | Per-view GUI, retire `g.app.gui` | large | high | heterogeneous views in one process |

Stages 1-5 are the project. Stage 6 is the long tail. Stage 7 is optional and probably
unnecessary — see below.

### Stage 0 — Safety net (prerequisite)

Get the existing 41 test files running in CI in this fork before touching anything.
`run_pytest_tests.py` and `run_ci_unit_tests.py` are present. Add a headless job.
Nothing else in this plan is safe without it.

Also capture a **baseline load-time profile** — open a large `.leo` file and record the
time — because stages 2 and 6 both add per-mutation work on the file-reading hot path
and you will want to know what it cost.

### Stage 1 — Break the import-time Qt dependency
*Effort: small. Risk: low. Value: immediate and standalone.*

Goal: `import leo.core.leoApp` works with no Qt installed, and the null-GUI test suite
runs on a machine that has never heard of PyQt6.

- Move `qt_*` imports in `leoGui`, `leoAPI`, `leoApp`, `leoFind`, `leoKeys`, `leoVim`,
  `leoConfig`, `leoBackground` behind `TYPE_CHECKING` or function-level lazy imports.
  Several modules (`leoChapters:17`, `leoMenu:15`, `leoImport:45`) are already
  `TYPE_CHECKING`-only — follow the pattern that is already in the file.
- The awkward cases are the ones imported for *runtime* use, not annotation:
  `leoApp`'s `LossageData` and `IdleTime`, `leoFind`'s `FindTabManager`, `leoGui`'s
  `LeoQTreeWidget` and the wrapper classes. Each needs either a lazy import at the
  point of use or a small neutral base class in core with the Qt subclass in plugins.
  `IdleTime` in particular wants a neutral interface — the null GUI already substitutes
  `g.NullObject` for it (`leoGui.py:278`), so the seam exists.
- Move `QTextMixin`'s GUI-independent half into `leoAPI.py`. Its own comment says
  *"These are independent of the kind of Qt widget"* — the split is already documented
  in the source, just not performed.
- Give `leoQt.py` a graceful failure mode rather than an unguarded top-level
  `from PyQt6 import ...`.
- Split the dependency in `pyproject.toml`: a core install without Qt, a `[gui]` extra
  with it.
- Add a CI job that installs **without** PyQt6 and runs the null-GUI tests.

The fake-PyQt6 shim in Appendix A is direct evidence this is achievable: nothing in the
headless path actually *calls* Qt, so the imports are removable rather than replaceable.

**Ship this one on its own.** It is plausibly upstreamable as a standalone packaging
improvement, independent of everything that follows.

### Stage 2 — Fix and complete model notifications
*Effort: small-medium. Risk: low. Value: unblocks everything downstream.*

- **Fix the branch bug** in `VNode.setBodyString` / `setHeadString` so `str` assignments
  emit and call `contentModified()` (finding 6). A genuine bug fix, upstreamable on its
  own, and it repairs `editpane` as a side effect.
- **Extend emission to structural mutations**: `insertAsNthChild`, `insertAsLastChild`,
  `doDelete`, `moveTo*`, `setDirty`, `setMarked`, `clearMarked`. Define the event set
  deliberately and keep it small:

  | Event | Payload | Emitted by |
  |---|---|---|
  | `body_changed` | `v`, origin | `VNode.setBodyString` |
  | `head_changed` | `v`, origin | `VNode.setHeadString` |
  | `structure_changed` | `parent_v`, origin | insert / delete / move |
  | `status_changed` | `v`, bits, origin | dirty / marked |

- **Carry an `origin` on every event** — the view (or `None` for a script) that caused
  it. Views ignore their own events. Without this, stage 6 produces cursor thrash the
  moment two views are open, and you will not enjoy debugging it retroactively.
- **Batch during bulk operations.** Emitting per node while reading a 10,000-node file
  is not acceptable. Add a suppress/replay context manager and use it in
  `leoFileCommands` and `leoAtFile`; `c.disable_redraw()` already establishes the
  precedent for this shape of thing. Measure against the stage 0 baseline.
- **Convert `freewin` from idle-polling to event subscription** as the first consumer.
  It is a small, self-contained plugin, and it is the proof that the event set is
  complete and correctly ordered. If freewin can be made correct with events alone,
  the event set is good enough for stage 3.

Interim wiring: emit on `v.context` (the commander) and have views subscribe there.
Stage 3 moves the bus to the `Outline` without changing the subscriber API.

### Stage 3 — Extract `Outline` from `Commands`
*Effort: medium. Risk: medium. Value: the conceptual fix.*

Introduce an `Outline` (document) object owning `hiddenRootNode`, the gnx index, the
file name, the dirty flag, `fileCommands`, and the event bus. Change `VNode.context` to
point at it rather than at a commander.

- Keep `c.hiddenRootNode`, `c.fileCommands`, `c.mFileName`, `c.changed` as forwarding
  properties so nothing breaks on day one. ~50 `.context` sites in `leo/core` need
  review; most are mechanical (`c = v.context` → `outline = v.context`).
- The commander keeps everything that is genuinely per-view: `p`, `hoistStack`,
  `chapterController`, `expansionLevel`, `frame`, `k`, focus flags.
- Relax `LeoTree.selectHelper`'s guard (`leoFrame.py:930`) from `p.v.context != c` to
  `p.v.context is not c.outline`. The probe in Appendix A says that guard is the *only*
  thing rejecting a second view — everything past it already worked.
- `Outline` keeps a list of its attached views, so a change can be broadcast and a
  close can be refused while another view is dirty.
- Add a command — `open-second-view` or similar — that constructs a commander against
  an existing `Outline` instead of loading a file. This is the user-visible feature and
  the thing to demo.

Deliverable at the end of this stage: **two Qt windows on one outline, both usable,
edits visible in both.** Crude — shared expansion state, body sync only on selection
change — but real.

### Stage 4 — Unify the undo stack on the `Outline`
*Effort: medium. Risk: medium.*

**Decision: the undo stack is per outline.** One document, one history. See
*Undo across views* above for the rationale and the design; this stage implements it.

- Move `undoer` from `Commands` to `Outline`; leave `c.undoer` as a forwarding property.
  (Today two commanders on one outline get two independent undoers — verified — which
  would corrupt each other's view of history the moment both are used.)
- Split every undo bunch into **model state** (mandatory, replayed always) and
  **view hint** (optional: `origin` view id, insert point, selection range, scroll
  position). Restore the hint only into the originating view, only if it still exists.
  Every other view receives the model events from stage 2 and updates itself.
- Remove the direct widget drives from `leoUndo.py`: `c.frame.tree.setHeadline(...)`
  at `leoUndo.py:1441,1466,1479,1494` becomes a `head_changed` event; the ~20
  `w = c.frame.body.wrapper` sites become model writes plus a view hint. This is the
  one place where a slice of stage 6's work has to happen early — undo cannot be made
  view-neutral while it edits a specific widget.
- **Clamp positions after undo.** An undo initiated in view A can delete the node
  selected in view B. Each view, on `structure_changed`, must verify its current
  position still exists and fall back to the nearest surviving ancestor. This is the
  single most likely source of crashes in the whole plan; write the tests first.
- Undo grouping (`beforeChangeGroup` / `afterChangeGroup`) is now shared. A group opened
  by view A must not swallow view B's unrelated edit — assert that groups are not
  interleaved across origins, and fail loudly in unit tests if they are.

### Stage 5 — Move per-view state off the `VNode`
*Effort: medium. Risk: medium.*

Move `expandedBit`, `selectedBit`, `insertSpot` and `scrollBarSpot` from `VNode`
(`leoNodes.py:2260-2299`) into a per-view `ViewState` keyed by gnx.

- Keep `v.isExpanded()`, `v.expand()`, `v.contract()` as deprecated shims that delegate
  to a designated "primary" view during the transition, so the 424 plugin call sites
  keep working.
- Persist per view in `c.db` — already per-document there (`leoFileCommands.py:210`),
  so this is a key-scoping change, not a new persistence mechanism.
- `selectedBit` should simply die: "is this node current" is `view.p == p`, derivable,
  and storing it invites exactly the multi-view inconsistency this stage exists to fix.
- Decide and document the default: does a newly opened second view inherit the first
  view's expansion set, or start from the saved document default? Inheriting is less
  surprising.

After this, two panes can be expanded, scrolled and hoisted independently on the same
outline. Combined with stages 3 and 4, this is a genuinely usable multi-view Leo.

### Stage 6 — Make the model authoritative for body text
*Effort: large. This is the real work.*

The ~660 wrapper calls. Do **not** attempt this as one sweep.

1. Add `c.getBodyText()` / `c.setBodyText()` reading and writing `p.b` and pushing to
   views via stage 2 events.
2. Invert `QTextMixin.onTextChanged` (`qt_text.py:199`): widget edit → model mutation →
   event → *all* views update, with the originating view suppressed via the `origin`
   field. Today the flow is widget → undoer → model, with the widget authoritative
   between selection changes.
3. Migrate call sites **file by file**, easiest first — `leo/commands/*` (194 refs)
   before `leo/core/*` (297). Each file is a self-contained, testable commit. The big
   ones (`leoKeys.py`, `leoFind.py`, `leoVim.py`, `editCommands.py`) come last.
4. **Leave selection and scroll on the wrapper.** They are genuinely view state and
   belong there; only *text* needs to move. Resist the urge to do both at once.
5. Retire `LeoTree.set_body_text_after_select` (`leoFrame.py:985`) as the reconciliation
   point, and with it the side effect of setting `c.p` from inside a view-refresh
   routine.

This stage plausibly takes as long as 1-5 combined. It is also the stage that can be
deferred longest: after stage 5 you already have working multiple views, with the single
limitation that a body being *actively typed into* in view A reaches view B on the next
selection change rather than keystroke by keystroke. For most of the use cases that
motivate multiple views — an outline pane plus a rendered pane, two different subtrees,
a read-only reference view — that limitation is barely visible.

### Stage 7 — Per-view GUI, retire the `g.app.gui` singleton
*Effort: large. Risk: high. Probably unnecessary.*

Only needed for **heterogeneous** views in one process — a Qt tree and a web client
simultaneously. Route GUI access through `view.gui` rather than `g.app.gui`: 543 call
sites across core, commands and plugins, and it would also remove the need for
`leoserver`'s runtime monkey-patching (`leoserver.py:1005-1008`).

If the goal is "several Qt views" or "Qt plus an out-of-process client", **skip this**.
`leoserver` already handles the out-of-process case, and stages 1-6 make it a much
better citizen than it is today.

---

## Risks, honestly

- **Upstream divergence.** Leo is actively developed. Stages 3-6 touch `leoCommands.py`,
  `leoFrame.py`, `leoUndo.py` — the busiest files in the tree. Merge pain compounds.
  Mitigation: ship stages 1 and 2 as upstreamable PRs (they are defensible bug fixes
  and packaging improvements on their own merits) so the permanently divergent surface
  stays as small as possible. Rebase on upstream `main` at every stage boundary, never
  mid-stage.
- **The `.leo` file format is a public contract.** Nothing in stages 1-6 needs to change
  it. Keep it that way; a format change turns a refactor into a migration.
- **Plugins.** 424 `c.frame.*` references live in `leo/plugins`. Forwarding properties
  keep them working through stage 5; stage 6 will break some. Inventory the plugins you
  actually use before starting stage 6, and treat that list as the compatibility target
  rather than trying to keep all of them alive.
- **Performance.** Event emission on every `p.b` assignment is real cost on file load
  and on `@file` writes. This is why stage 0 captures a baseline and stage 2 batches.
- **Position invalidation across views** (stage 4) is the most likely source of hard
  crashes: view B holding a `Position` into a subtree that view A just deleted. Leo's
  `Position` is a `(v, childIndex, stack)` triple and already goes stale within a single
  view; multiple views multiply the opportunities. Tests before code.
- **Scope discipline.** Every one of these stages opens onto an adjacent cleanup that
  looks free and is not. The staging exists to be obeyed.

## Where I'd start tomorrow

Stage 1 plus the `setBodyString` fix from stage 2. Together they are maybe a day's work,
they are independently useful, they are both plausibly upstreamable, and completing them
tells you a great deal about how this codebase responds to being pushed on — before you
commit to the parts measured in weeks.

The first milestone worth aiming at is the end of **stage 3**: two Qt windows on one
outline. It is a small enough increment to reach, and a convincing enough demo to decide
by — if it feels right, stages 4-6 are worth the months; if it doesn't, you have learned
that for the cost of stages 0-3 rather than the cost of the whole thing.
---

## Appendix A — Probe scripts

Both require the Qt shim below on `PYTHONPATH` (or a real PyQt6 install).

**`shim/PyQt6/__init__.py`** — enough fake Qt to import Leo headlessly:

```python
import sys, types

class _Meta(type):
    def __getattr__(cls, name):
        if name.startswith('__'): raise AttributeError(name)
        v = _Meta(name, (_Any,), {}); setattr(cls, name, v); return v

class _Any(metaclass=_Meta):
    def __init__(self, *a, **k): pass
    def __call__(self, *a, **k): return _Any()
    def __getattr__(self, n):
        if n.startswith('__'): raise AttributeError(n)
        return _Any()
    def __or__(self, o): return self
    __ror__ = __or__

class _Mod(types.ModuleType):
    def __getattr__(self, name):
        if name.startswith('__'): raise AttributeError(name)
        v = _Meta(name, (_Any,), {}); setattr(self, name, v); return v

for _n in ('QtCore', 'QtGui', 'QtWidgets', 'QtPrintSupport', 'QtSvg',
           'QtWebEngineWidgets', 'QtWebEngineCore', 'Qsci', 'QtDesigner',
           'QtMultimedia'):
    m = _Mod('PyQt6.' + _n)
    sys.modules['PyQt6.' + _n] = m
    globals()[_n] = m
```

**`probe.py`** — headless startup, dead signal, stale wrapper:

```python
import sys; sys.argv = ['probe']
from leo.core import leoTest2, signal_manager
from leo.core import leoGlobals as g

c = leoTest2.create_app('null')
print('gui =', g.app.gui.guiName(), c.frame.__class__.__name__)

root, hits = c.rootPosition(), []
signal_manager.connect(c, 'body_changed', lambda *a, **k: hits.append(a))
root.b = 'hello world'
print('after p.b = str   -> hits:', len(hits))      # 0  ← bug
root.v.setBodyString(b'bytes body')
print('after bytes       -> hits:', len(hits))      # 1
print('v.b     =', repr(root.v.b))                  # 'bytes body'
print('wrapper =', repr(c.frame.body.wrapper.getAllText()))   # 'hello world' ← stale
c.selectPosition(root)
print('wrapper =', repr(c.frame.body.wrapper.getAllText()))   # 'bytes body'
```

**`probe2.py`** — two views on one model:

```python
import sys; sys.argv = ['probe']
from leo.core import leoTest2, leoCommands
from leo.core import leoGlobals as g

c1 = leoTest2.create_app('null')
root = c1.rootPosition()
root.h, root.b = 'shared root', 'shared body'
root.insertAsLastChild().h = 'child A'

c2 = leoCommands.Commands(fileName=None, gui=g.app.gui)
c2.hiddenRootNode = c1.hiddenRootNode          # share the model
p = c2.rootPosition()
print('c2 sees:', p.h, [x.h for x in p.children()])
c2.selectPosition(p)                            # logs "Wrong context" — the one guard
c1.selectPosition(c1.rootPosition().firstChild())
print('c1.p =', c1.p.h, '  c2.p =', c2.p.h)     # independent cursors
p.b = 'edited via c2'
print('c1 sees:', repr(c1.rootPosition().b))    # 'edited via c2' — shared state
```

## Appendix B — Numbers

| Measure | Value |
|---|---|
| Total Python in `leo/` | 370,128 lines |
| `leo/core/` | 75,418 lines, 39 modules |
| `c.frame.*` references | core 297 · commands 194 · plugins 424 · tests 71 |
| Distinct `c.frame.*` paths (core + commands) | 85 |
| `g.app.gui` references | core 173 · commands 51 · plugins 319 |
| Body-wrapper API calls (core + commands) | ~660 |
| GUI references in `leoNodes.py` (the model) | 6, of which 2 are real |
| `signal_manager` emit sites in the whole tree | 1 (unreachable in practice) |
| `v.context` references in `leo/core` | ~50 |
| Headless test files | 41 |
