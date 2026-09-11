# TODO

Remaining work on the `decouple-model-gui` branch. Background, measurements and
the reasoning behind the design are in [LEO_REFACTOR.md](LEO_REFACTOR.md); this
file is only the list of what is left.

**Target architecture**

```
leolib                the model and its machinery. No view, ever.
   ^
   +-- leogui         the Qt front end       (today: leo/plugins/qt_*)
   +-- leotui         the terminal front end (leo/leotui, on leolib)
   +-- leoweb         the web front end      (today: leoserver, as a seed)
```

**Where it stands.** `leolib` can open, create, edit, view and save `.leo`
files, including every `@<file>` directive, and **the model no longer imports
`leoGlobals` or any view module.** Opening `LeoPyRef.leo` and reading all 376 of
its external files imports 13 `leo.*` modules; the same file through `leoBridge`
imports 105. The model still lives in `leo/core`; see section 3. None of the
three front ends uses `leolib` yet, but a fourth does: `leo/leotui` opens,
folds, edits and saves a `.leo` file, and tangles its external files, through
`leolib` alone, undo included. 959 tests pass headless and under real PyQt6;
`ruff`, `ty` and `check_leo_sync` are clean.

---

## Pick up here

**One decision is open, and it is the only thing blocking the last step.** The
dependency work is finished and enforced by tests; what remains is where the
files live.

`leo/leolib/` holds `util.py`, `state.py`, `language_data.py`, `api.py`,
`view.py` and an `__init__.py` with no imports. The ten model modules —
`leoNodes`, `leoOutline`, `leoFileCommands`, `leoAtFile`, `leoShadow`,
`leoImport`, `signal_manager`, `leoPluginRegistry`, `leoUndo` and
`leoPersistence` — still sit in `leo/core/`, even though nothing about their
imports requires it any more. The language importers and writers under
`leo/plugins` are model code too. Moving them is `git mv` plus four mechanical
follow-ups (below). The decision is what the old import paths should do:

| option | cost |
|---|---|
| **Leave re-export shims** at `leo/core/leoNodes.py` etc. | Nine extra one-line files, two names per module. Nothing in Leo or in any plugin breaks. |
| **Move and update all 110 in-tree files** | Cleanest result. Every out-of-tree plugin doing `from leo.core.leoNodes import Position` breaks on upgrade — that is most of them. |
| **Don't move them** | Nothing breaks and nothing improves. The boundary is already correct and enforced; the location is cosmetic. Spend the effort on section 2 instead. |

101 files import `leo.core.leoNodes`, nearly all of them only to name a
`Position` or a `VNode` in an annotation.

A second question follows only if they do move: keep the existing filenames
(`leo/leolib/leoNodes.py` — least churn, easiest to diff against upstream Leo)
or rename to fit the package (`leo/leolib/nodes.py`, `outline.py`, `at_file.py`
— reads far better beside `util.py` and `state.py`).

**If the move goes ahead, four things have to happen with it**, all of which
`check_leo_sync` will catch if they do not:

1. `git mv`, and change each file's own `@file` sentinel headline
   (`# @+node:...: * @file leoNodes.py` → `* @file ../leolib/nodes.py`).
2. Move the matching `<v t="..."><vh>@file ...</vh></v>` line in
   `leo/core/LeoPyRef.leo`. @file nodes have no `<t>` entry and no children
   there, so the one line is the whole registration.
3. Update the moved modules' imports of *each other*.
4. Give any newly written node a fresh gnx. A reused one makes two files stop
   round-tripping, and it is not obvious from reading either of them.

**Everything else on this list is unblocked and independent of that decision.**
Section 2 (put a front end on `leolib`) is the one I would take next either
way: nothing consumes the boundary from outside yet, so nothing proves it is
usable.

---

## 1. Verify by hand: two windows on one outline

**The only claim in this branch with no automated cover.** No headless test can
open two Qt windows, and the Qt-only tests that do run never open a second one.
`LeoQtTree.begin_edit_headline` is unreachable from any test, because
`headline_wrapper` returns a widget only while a real `QLineEdit` is open.

In a running Leo (`uv run python launchLeo.py`):

1. `Alt-X` → `open-second-view`.
2. Rename a node in window A. Window B's tree should show the new name.
3. **Click that node in window B and commit without typing anything.** It must
   *not* revert to the old name. This is the bug the headline half of stage 6
   exists to fix: window B's stale headline widget used to be committed on any
   `endEditing`, restoring the old name and pushing a bogus undo bead.
4. Start typing a headline in A without committing, then rename that node from
   B. The half-typed text in A must survive.
5. Rename several nodes under one undo, `Ctrl-Z`, and check *every* headline
   updates — not only the selected one.

Single-window editing (headline add/edit, body edit with highlighting, save) is
already confirmed working in the GUI.

---

## 2. Put a front end on `leolib`

Nothing yet consumes the boundary from outside, so nothing proves it is usable.

- [x] **`leo/leotui`: a terminal front end on `leolib`.** Done, as a second
      package beside `leo/tui` rather than a rename, so the two can be measured
      against each other. Opening `LeoPyRef.leo` and reading all 376 external
      files imports **18** `leo.*` modules through `leotui` and **107** through
      `leo/tui`'s `leoBridge`; both build the same 11,581 nodes.
      `test_leotui.py` asserts the count stays under 40 and that no
      `leoGlobals`, `leoCommands`, `leoBridge` or view module is imported at
      all. Editing, structural edits, per-view folds and tangling to disk are
      each covered.

      **What a front end has to supply is a view.** `leolib.View`
      (`leo/leolib/view.py`) is the minimal one, and `leotui` uses it
      unchanged. It holds a `ViewState`, a current position, a text buffer and
      a redraw flag -- and nothing else, because it no longer has to
      impersonate a window to be allowed to save. It was `leotui`'s `TuiView`
      until undo needed a view that a script could attach.

      That is the result of the fix below, not of the first draft. `TuiView`
      started at ~20 members and 234 lines, most of them settings, a document
      cache and fake window geometry it invented to satisfy the model.
- [x] **`Outline` now asks what a view can answer, not whether one exists.**
      Every forward was guarded by `if self.c is None`, which made "a view is
      attached" mean "a Qt window is attached". `Outline.ask_view(name, default)`
      replaces that: a view supplies what it has, and the document keeps the
      headless answer -- already written and already correct -- for the rest. A
      view that answers nothing is now indistinguishable from no view.

      Converted: `config`, `target_language`, `tab_width`, `page_width`, `db`,
      `frame`, `importCommands`, `setBodyString`, `setChanged`,
      `shouldBeExpanded`, `alert`, `redraw`, `bodyWantsFocusNow`, `endEditing`,
      `init_error_dialogs`, `raise_error_dialogs`, `selectPosition`. Real Leo is
      unaffected: a commander answers everything, so `getattr` finds it.

      Three of these were live crashes, not tidiness. `alert`,
      `init_error_dialogs` and `raise_error_dialogs` were `AttributeError` for
      any view that is not a commander, and `leoAtFile.writeAll` calls the last
      two on every write.

      Four sites outside `Outline` had the same shape:

      - `fc.putGlobals` wanted `c.frame.compute_ratio()` and `get_window_info()`
        on every save. It now asks the view for a frame and keeps the geometry
        the file was read with when there is none.
      - `fc.putStyleSheetLine` read `c.config` whenever a view existed.
      - `at.initAllIvars` passed the view to `g.getOutputNewline(c=c)`, which
        reads `c.config`. Its two sibling call sites already asked the document;
        this one had been missed.
      - `at.promptForDangerousWrite` refused when `c is None`, then called
        `g.app.gui.runAskYesNoCancelDialog` unconditionally. A view with no gui
        now gets the same refusal as no view, rather than a crash.

      `test_a_view_that_answers_little_still_works` is the guard: a view with
      ten members, no settings, no cache and no dialogs must still save and
      tangle. Reverting either the `Outline.config` change or the
      `promptForDangerousWrite` change fails four tests.

      **Still binary, deliberately:** `outline.p` and `createNodeHierarchy`
      have no headless answer, so they still require a view that provides them.
      See section 4.

      While fixing this: nine `at.write*` helpers referenced `fileName` in their
      `except` clause before assigning it, so any exception before
      `initWriteIvars` surfaced as `UnboundLocalError` instead of the real
      error. That is what hid `getOutputNewline` above.
- [x] **`leoUndo` is a model module: undo works with no commander and no gui.**
      It was the last thing `leotui` could not do. `leoUndo` now says
      `from leo.leolib import util as g`; importing it pulls 8 modules and
      `leoGlobals` is not among them. `leolib.undoer(outline)` creates the
      stack on first use -- one outline, one history, shared by every view --
      and imports `leoUndo` only then, so a script that just reads a `.leo`
      file still opens `LeoPyRef.leo` in 13 modules. Through `leotui` the count
      goes 17 to 18.

      Undo restores the caret into the acting view, so it needs one.
      `leolib.undoer` raises `ValueError` on an outline with no view; a script
      attaches `leolib.View(outline)` first. Until 2026-09-11 it raised
      `AttributeError` from inside `Undoer`, and only the `leotui` path, which
      always has a view, was tested.

      Two names had to move with it. `checkUnicode` was view-free and belongs
      in `util`; `leoGlobals` re-exports it, so `g.checkUnicode` is unchanged
      and `test_leoGlobals_reexports_every_name` enforces that it is the same
      object. `isTextWrapper` could not move: it asks `g.app.gui`, and
      `_MinimalApp.gui` is `None` on purpose. `util.is_text_wrapper` is a
      duck-type test instead -- both gui implementations are class checks, and
      a `NullObject` passes it exactly as the Qt gui special-cases by hand. It
      is deliberately not called `isTextWrapper`: `g.isTextWrapper` still asks
      the gui for the ten view modules that call it, and two names that mean
      almost the same thing beat one name that means two things.

      What the undoer used a host for, and what it does now:

      | was | now |
      |---|---|
      | `c.config` for granularity and stack size | `outline.config`: settings are the document's |
      | `c.frame.menu` relabelling Edit/Undo | `u.menu_bar()`; the labels are u's own state and are tracked with or without a menu |
      | `c.frame.body.wrapper` | `u.body_wrapper()` in some helpers; `createCommonBunch` and the body helpers still read `c.frame.body.wrapper`, so a view needs a buffer even for structural undo |
      | `g.app.gui.isTextWrapper` | `g.is_text_wrapper` |
      | `c.recolor`, `c.bodyWantsFocus`, `c.editHeadline` | still the view's job, and a terminal's are no-ops |
      | `c.checkOutline`, `c.chapterController`, `c.deleteOutline` | `u.ask_view(...)`, with a model fallback where undo needs one |
      | `c.all_unique_positions`, `c.fileCommands`, `c.nodeIndices`, `c.hiddenRootNode`, `c.redraw`, `c.setChanged`, ... (18 lines) | `self.outline`: they were always document operations that happened to live on Commands |

      `c.set/clearMarked` was the subtle one: the bit is model state and the
      commander only adds a hook, so the bit is set directly when no view
      offers the hook. Undoing a mark used to be an `AttributeError`.

      `test_undo_and_redo` covers undo and redo of a headline, a body, an
      insert, a delete and a move through `leotui`, and asserts that none of it
      imports `leoGlobals`, `leoCommands` or a gui.

      **Not covered:** undo of the commands `leotui` cannot run -- hoist,
      chapters, clone/copy/delete-marked, sort, paste. Their helpers still ask
      the view and now decline rather than crash, but nothing exercises them
      without a commander because nothing can create those beads without one.
- [ ] **`leo/tui` is now redundant.** Deleting it removes the duplicate of
      `screen.py`. Left in place so the comparison above can be re-run.
- [ ] **Commands stay out of reach, as recorded in section 4.**
      `commanderOutlineCommands` imports `leoGlobals` and calls
      `g.app.gui.replaceClipboardWith`; `c.doCommandByName` calls
      `g.app.gui.create_key_event` and `c.frame.updateStatusLine`. `leotui`
      therefore builds insert, delete and the four moves from the `Position`
      primitives in `leoNodes`, which are model. They move a node among its
      *siblings*; Leo's `move-outline-up` moves it in visible order and honours
      hoists, and that difference is deliberate, not an approximation to finish
      later.
- [ ] **`leo/leogui`.** The Qt front end is spread across `leo/plugins/qt_*` and
      the Qt halves of `leoFrame`. Renaming is cosmetic; the substance is making
      it depend on `leolib` rather than on `leo.core` wholesale.
- [ ] **`leo/leoweb`.** Unstarted. `leoserver.py` is the obvious seed — it is
      already a second front end driving Leo over websockets against a null gui,
      and it monkey-patches `g.app.gui` at runtime to redirect dialogs, which is
      the abstraction failing at exactly the seam this refactor addresses.

---

## 3. Make `leolib` a package, not a facade

`leo/leolib/` holds six modules:

| module | what it is |
|---|---|
| `util.py` | Everything in `leoGlobals` that never reads `g.app`, plus the seams below. 299 names. |
| `state.py` | The names Leo rebinds while it runs: `app`, the host flags, the language tables, and the four seams. Imports only `language_data`. |
| `language_data.py` | Comment delimiters and file extensions. Imports nothing. |
| `api.py` | The library: `open_outline`, `save`, `tangle`, `write_external_files`. |
| `view.py` | `View`, the minimal view: what the model asks of one. Undo needs a view; `leotui` uses this one. |
| `__init__.py` | Empty of imports, so `leoGlobals` can import `util` without a cycle. |

`leoGlobals` imports every name in `util` back, so `g.splitLines` and
`util.splitLines` are the same object and no caller changed. It is 5,816 lines,
down from 8,975.

**The model imports `util as g`, not `leoGlobals`.** All 983 of its `g.<name>`
uses resolve through `util` and `state`, `g.app` included: `app` and the host
flags are properties over `state` on *both* modules, so a model module cannot
tell which one it was handed. `test_no_leoGlobals_anywhere` says so, and is
easy to break — one `from leo.core import leoGlobals as g` in a model module
puts all 5,800 lines back.

The language importers and writers, and `leoPersistence`, import `util` too.
Until 2026-09-11, 17 importers and writers and `leoPersistence` imported
`leoGlobals`, and `basewriter` and `org` imported `leoCommands` at run time,
so one `@auto` node took `leolib` from 13 modules to 53.
`test_only_importers_and_writers` missed it because its own subprocess
imported `leoGlobals`. It now imports `util` and checks for application
modules, and `test_at_auto_loads_no_app_module` reads and writes an `@auto`
file.

`test_no_path_to_an_app_module` checks the import graph statically. It follows
every import that can run, including those inside functions, from
`leo/leolib` and the importers and writers. Three function-level imports are
allowed, each with a reason in the test: `leo.run`, and `leoAtFile`'s
`runRuff` and `runTy`. An allowed entry that no longer exists fails the test.

**The four seams**, each replacing something the model used to ask `g.app` for:

| seam | replaced |
|---|---|
| `state.log_sink` | `g.es` writing to the log pane |
| `state.hook_dispatcher` | `g.doHook` and the plugin controller |
| `state.command_registrar` | `@g.command` registering with open commanders |
| `state.file_opener` | `g.openWithFileName` making a window |

`leoGlobals` installs Leo's real implementation of each as it loads, so inside
Leo nothing changed. With no host each is `None` and the operation is a no-op,
which is what `leolib` already did in effect.

**Three rules came out of the split**, each found by a failure:

- *A name something rebinds at run time cannot be re-exported by value.*
  `g.unitTesting = True` sets `leoGlobals`' copy; a reader in `util` goes on
  seeing `False`. `g.chdir` returns early during tests, stopped doing so, and a
  test three files later found its working directory deleted. Those names live
  in `state` and are presented through a module *class* with properties — a
  module `__getattr__` never sees an assignment, so the first write would
  shadow `state` from then on.
- *The same applies to functions Leo swaps out.* `leoApp` redirects stdout under
  pythonw, `leoserver` redirects the log, `mod_speedups` substitutes path
  helpers, the Pygments colorizer replaces `isValidLanguage`. All four patch
  `g.<name>` **and** `util.<name>`; `test_runtime_patches_hit_both_modules`
  reads every file's parse tree to enforce it, because at run time the failure
  is silent — everything keeps working, just not where the caller intended.
- *Moving code between Leo files means moving sentinels.* A `<< section >>`
  whose body all moved has to go completely, or the reference left in the
  root's body has no node behind it; a moved body carrying sentinels of its own
  needs its levels shifted; and a reused gnx makes two files stop
  round-tripping. `check_leo_sync` caught all of it, and nothing else did.

**Still to do:** move the ten model modules into `leo/leolib/`. Nothing
blocks it — the imports all point the right way — but it needs a decision about
the old paths first. See **Pick up here** at the top of this file.

---

## 4. Finish `leolib`

- [ ] **Three `Outline` members still require a view**: `p`, `shouldBeExpanded`,
      `createNodeHierarchy`. Of 32 members exercised against an outline with no
      view, these are the only ones that raise. `p` is honest — there is no
      selected node without a window — so the real remainder is two.
      `grep 'self.c' leo/core/leoOutline.py` is the running to-do list.
- [ ] **No commands are reachable without a commander.** `leo/tui` showed all 19
      structural commands already work against a null frame, so they are
      view-agnostic in substance; they are simply not callable from `leolib`.
- [ ] **`DefaultConfig` is riskier for writing than for reading.** "No settings"
      is not "Leo's shipped settings": `leoSettings.leo` ships
      `@int page-width = 80` against a code default of 132. Nothing the writer
      currently touches depends on it — all 376 files round-trip byte for byte —
      but check any setting that can reach a file before widening that surface.

---

## 5. Conformance corpus (shared with leo-rs)

The Rust port (`~/projects/leo-rs`) and this `leolib` answer to one corpus.
`leo-rs/scripts/make_corpus.py` builds it in `leo-rs/demo/` and writes each
case's `.expected.json` from Python `leolib`; `crates/leolib/tests/corpus.rs`
checks Rust against it. `leo/unittests/leolib/corpus/` is a byte-identical
copy, and `test_leolib_corpus.py` checks Python against it: each case reads to
the expected positions, `to_xml` reproduces each `.leo` file, and writing every
external file changes no byte. Refresh the copy from `leo-rs` with

    python3 scripts/make_corpus.py --leo-editor ~/projects/leo-editor --check \
        --copy-to ~/projects/leo-editor/leo/unittests/leolib/corpus

`.gitattributes` keeps the copy's exact bytes: it holds CRLF and latin-1 files.

- [x] **Widen the corpus.** Nine cases: clones, CRLF line endings, latin-1, all
      six directives, `@auto` in four languages, sentinel lookalikes, and three
      real outlines, `LeoPyRef.leo` among them.
- [x] **Golden files**, so neither implementation needs the other to test.
- [x] **The lookalike case found a Leo bug, fixed 2026-09-12.** Reading an
      unchanged `@clean` file doubled every line that looks like a sentinel,
      and writing `@nosent` doubled such a line's indentation.
      `put_verbatim_sentinel` wrote the escape's indent even when no sentinel
      followed. The #2996 guard (995dadf445) avoided that for `@clean` writes
      by skipping the escape for `@clean` altogether, which broke the read. The
      escape is now skipped only when no sentinels are written. Worth
      reporting upstream, with the `sentinel_lookalikes` case.
- [x] **Unread files agree.** The `unreadable` case holds an `@file` with no
      sentinels, which both implementations report unread and refuse to
      overwrite. Python had reported every file read: `at.read` returned
      `True` without checking `read_into_root`. And Leo marks a file read even
      when reading failed (#760531), so a headless write replaced it. `leolib`
      now unmarks a failed read; GUI Leo keeps #760531.
- [x] **`write_external_files` writes every tree**, as its docstring and Rust
      say; it wrote only dirty ones. Its count now compares file contents:
      `writeAll` resets its own tally on each call and does not count refusals.
- [x] **`@auto` works with no view.** The Markdown and Org writers were built
      with `at.c`, which is `None` without a view, so the corpus's write check
      passed on them by writing nothing; Org also needed a plugins controller.
      An `@auto` file with no importer crashed in `leoImport.setBodyString`.
- [ ] **`@edit` decodes a non-UTF-8 file lossily, in both implementations.**
      A probe read the bytes `caf\xe9` as `caf` followed by U+FFFD in each.
      Writing it back would
      then store U+FFFD in place of the byte; that is inferred, not tested.
- [ ] **An `@auto` file with no importer:** Leo reads it whole into the node;
      Rust reports it unread. Not in the corpus.

**Traps worth encoding in the corpus,** each of which cost time here:

- *A sentinel is just a comment.* A source line beginning `# @` is ambiguous
  with a Leo sentinel; Leo escapes it with `@verbatim`. Ordinary code comments
  broke Leo's own file reader three times during this work.
- *`@clean` hides read failures.* An `@clean` node stores its whole tree inside
  the `.leo` file, so a completely failed external read still yields the right
  *shape* holding stale *text*. Node counts and child counts both matched while
  twelve files were not being read at all. **Compare body text, not structure.**
- *Tangle output depends on process-global state.* `g.app.language_delims_dict`
  decides comment delimiters, so what a node tangles to is sensitive to whatever
  else is in the process. A port should design this out rather than inherit it.
- *`gnx` has three allocation modes* — legacy timestamp (machine id plus a
  per-second counter), uuid, ksuid.

---

## 6. Known-deferred, with reasons

Not oversights — each was investigated and left deliberately.

- **`c.p` is still set inside `LeoTree.set_body_text_after_select`**, which is
  model state assigned during a view refresh. Moving it to
  `change_current_position` passed every test, then had to be reverted: under Qt
  `w.setAllText` runs the `QSyntaxHighlighter` synchronously and
  `JEditColorizer.recolor` reads `c.p` to choose the language, so moving it
  colorizes the new node with the old node's language. No headless test can see
  this — the null gui has no highlighter. The reason is recorded in the source
  so the next person does not repeat the experiment.
- **`freewin` still idle-polls** instead of subscribing to the events that now
  exist. It is a ~1,000-line Qt plugin with subtle widget state; a blind rewrite
  would prove nothing. Convert it on a machine with Qt. While there: its idle
  handler walks `c.all_unique_positions()` on every tick, per open window.
- **Stage 7 (per-view GUI, retiring `g.app.gui`) is not started and looks
  unnecessary.** A Qt window and a terminal view already share one outline in
  one process. Stage 7 is about *input* — dialogs, clipboard, focus — not
  rendering, so its scope is narrower than the plan assumed.

---

## 7. Risks to keep in view

- **Out-of-tree plugins that use `v.context` as a commander will break.** Stage 3
  changed `VNode.context` from a commander to an `Outline`, and `Outline` has no
  `__getattr__` by design, so a miss is an `AttributeError` the first time a user
  reaches it. In-tree callers are fixed; third-party ones are not, and this is a
  real cost of stage 3 that the plan did not price. The rule is
  **`v.context` is the document; `v.context.c` is a window.**
- **Re-run the audits after any change to `Outline`'s forwarding list.** Two AST
  passes find the two shapes this bug takes: an attribute used directly on a
  `.context` value, and a `.context` value *passed onward* to something that
  expects a commander. The second is the shape that actually caused a crash, and
  grep cannot see it.
- **Run `ty check leo` often.** `main` passes it clean; this branch had silently
  accumulated 46 diagnostics before anyone ran it. Clearing them exposed two live
  bugs — `p.script` and five `source_c=p.v.context` sites in `mod_scripting` —
  of exactly the class above. A type checker found statically what an audit had
  only found by crashing.

---

## Running the checks

```bash
uv run python run_ci_unit_tests.py      # 959 tests; 4 skips under Qt, 23 without
uv run ruff check leo
uv run ruff format --check leo
uv run ty check leo
PYTHONPATH=. python3 -m leo.scripts.check_leo_sync
uv run python launchLeo.py              # the GUI
```

`uv run` provisions the environment itself, PyQt6 included.
