# TODO

Remaining work on the `decouple-model-gui` branch. Background, measurements and
the reasoning behind the design are in [LEO_REFACTOR.md](LEO_REFACTOR.md); this
file is only the list of what is left.

**Target architecture**

```
leolib                the model and its machinery. No view, ever.
   ^
   +-- leogui         the Qt front end       (today: leo/plugins/qt_*)
   +-- leotui         the terminal front end (today: leo/tui)
   +-- leoweb         the web front end      (today: leoserver, as a seed)
```

**Where it stands.** `leolib` exists and can open, create, edit, view and save
`.leo` files, including every `@<file>` directive. Opening `LeoPyRef.leo` and
reading all 376 of its external files puts 11 `leo.*` entries in `sys.modules`,
none of them a view module; the same file through `leoBridge` puts in 102, nine
of them views. But `leolib` is still a facade over `leo/core` rather than a
package of its own — see section 3. None of the three front ends uses it yet.
935 tests pass headless and under real PyQt6; `ruff`, `ty` and `check_leo_sync`
are clean.

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

- [ ] **`leo/tui` → `leo/leotui`, and point it at `leolib`.** It currently boots
      through `leoBridge` and the full commander stack. Smallest of the three
      front ends, and the first real test of the boundary.
      `leo/tui` also cannot create a new outline — only open an existing file.
- [ ] **`leo/leogui`.** The Qt front end is spread across `leo/plugins/qt_*` and
      the Qt halves of `leoFrame`. Renaming is cosmetic; the substance is making
      it depend on `leolib` rather than on `leo.core` wholesale.
- [ ] **`leo/leoweb`.** Unstarted. `leoserver.py` is the obvious seed — it is
      already a second front end driving Leo over websockets against a null gui,
      and it monkey-patches `g.app.gui` at runtime to redirect dialogs, which is
      the abstraction failing at exactly the seam this refactor addresses.

---

## 3. Make `leolib` a package, not a facade

`leo/leolib/__init__.py` is one file that defines no model code. `Outline`,
`VNode`, `Position`, the readers and the writers all still live in `leo/core`.
What the file actually contributes is `_MinimalApp` — a stand-in for `g.app`,
now carrying only data: the language tables, the XML prolog and the flags
`g.doHook` and `g.es` consult — plus lazy `@auto` dispatch tables and a
seven-function API.

That was deliberate. The expensive part of this refactor was the dependency
edges, not the file layout; moving files first would have made every later diff
unreviewable against upstream Leo and broken `check_leo_sync` while the boundary
was still moving. But it leaves the seam enforced by a test rather than by
structure, and nothing stops a caller from importing `leo.core.leoOutline`
directly and bypassing it.

It also makes "imports no view module" weaker than it sounds. `leoGlobals` is
8,974 lines with 13 references to `g.app.gui`; they sit in functions `leolib`
never calls, so the import graph looks clean while the dependency is still
there. A full open + read-all-external + serialize uses **38 of its 389
functions**. The other 90% comes along for the ride.

In dependency order:

- [x] **Move the gnx allocator off `g.app` and onto the `Outline`.** Done.
      `VNode.__init__` now asks `self.context.nodeIndices`, so creating a node
      needs no `g.app` at all; `Outline.nodeIndices` shares the app's allocator
      when there is one and takes its own from the constructor when there is
      not. This answers a request `leoNodes` had carried for years: *"To make
      VNode's independent of Leo's core, wrap all calls to the VNode ctor."*
      **The invariant to preserve:** allocators are shared per *process*, not
      per outline. A gnx is `userId.timestamp.counter`, so two allocators with
      one user id mint the same gnx inside the same second, and Leo copies
      nodes between outlines. Giving each `leolib` outline its own collided
      with the test harness on the first run — and reported it only as a
      printed internal error, with every test still green.
      `test_gnxs_do_not_collide_with_the_host` now covers it.
- [ ] **Split `leoGlobals`.** The elephant, and the reason the boundary is not
      yet structural. Extract the ~40 functions the model needs, and have
      `leoGlobals` re-export them so nothing upstream breaks. Do it *before* the
      move, not after: it is the step that decides which files the move can
      take, and it is where the real work is.
- [ ] **`git mv` the modules into `leo/leolib/`.** Mechanical, and worth doing
      only once the two steps above have landed. `check_leo_sync` pairs
      `leo/core/*.py` against nodes in `LeoPyRef.leo`, so it changes in the same
      commit. Until then the layout is honest about what it is: a named subset,
      held in place by `test_leolib_boundary`.

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

## 5. Conformance corpus (for a future `leolib-rs`)

If the model is reimplemented in Rust, the Python `leolib` becomes an executable
specification and the oracle to test against. Two properties already exist in
`leo/unittests/leolib/test_leolib_boundary.py` and are the right ones:

- `test_external_files_match_full_leo` — read a `.leo` file through `leolib` and
  through `leoBridge`, hash `headline + body` per gnx, require equality.
- `test_tangle_matches_disk` — tangling every external file reproduces it byte
  for byte.

- [ ] **Widen the corpus.** `LeoPyRef.leo` contains only `@file`, `@clean` and
      `@edit`, and just 2 of its 11,386 vnodes have more than one parent. It
      cannot exercise the model. A corpus should add: clones (several parents,
      and a clone whose subtree is edited), CRLF line endings, non-UTF-8
      encodings, all six directives, `@auto` in several languages, and **a file
      whose ordinary content looks like sentinels**.
- [ ] **Turn the two properties into golden files** so a port can be checked
      without a Python Leo in the loop.

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
uv run python run_ci_unit_tests.py      # 935 tests; 4 skips under Qt, 23 without
uv run ruff check leo
uv run ruff format --check leo
uv run ty check leo
PYTHONPATH=. python3 -m leo.scripts.check_leo_sync
uv run python launchLeo.py              # the GUI
```

`uv run` provisions the environment itself, PyQt6 included.
