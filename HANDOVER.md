# Mentis ClassWiz — Bug Fix Handover Document

## 0. Read This First (Instructions for ChatGPT)

You are acting as the **implementation planner** for this project. Your job has a strict scope. Do not deviate from it.

**Your job is:**
1. Read this entire document before writing any prompt.
2. Write prompts for the coding agent (OpenCode / Codex / Antigravity) that fix the bugs listed in Section 2, in the exact order listed, one bug at a time.
3. Each prompt you write must include: the file path, the root cause explanation from this document, the fix direction, and the exact test cases from Section 3 that must pass before the bug is marked fixed.
4. Instruct the coding agent to run the tests itself and report pass/fail output, not just claim the fix works.
5. Do not invent new bugs, do not reprioritize, do not skip a bug because it looks minor. If you think something here is wrong, flag it back to the user instead of silently changing the plan.
6. Do not let the coding agent touch files outside what's listed per bug. Scope creep is explicitly forbidden.
7. All work happens on branch `v0.12_port_oct21`. Do not merge to `v0.12` until Section 5 (Definition of Done) is fully satisfied.
8. When a bug is fixed and tested, move to the next one. Do not batch multiple bugs into one commit — one bug, one commit, one test run.
9. At the end of each bug fix, the coding agent must paste: (a) the diff, (b) the test output, (c) a one-line confirmation it did not touch unrelated files.
10. When all bugs in Section 2 are resolved and Section 5 is satisfied, stop. Report back "ALL BUGS RESOLVED, READY FOR MERGE" and nothing else. Do not attempt the merge yourself unless explicitly told to.

**You do not get to decide severity, order, or whether a bug is "worth fixing." That has already been decided below.**

---

## 1. Repository / Environment Facts

- Repo: `Red-swipe/mvp`
- Working branch: `v0.12_port_oct21` (all fixes happen here)
- Target branch for eventual merge: `v0.12` (do NOT merge until told to)
- Last known commit on working branch: `b971636` ("Normalize implicit variable multiplication in Table mode")
- Calculation pipeline: `frontend.html (UI/state)` → `mvp_server.py (string preprocessing + regex transforms + HTTP handlers)` → `engine/tokenizer.py` → `engine/parser.py` → `engine/evaluator.py` → back through `mvp_server.py` for formatting → `frontend.html` for display
- Key files:
  - `frontend.html` — UI state machine, phases, key bindings, LCD rendering
  - `mvp_server.py` — backend server, `safe_evaluate_expression()`, `/api/fraction`, trig/log/equation handlers
  - `engine/tokenizer.py`, `engine/parser.py`, `engine/evaluator.py` — standalone calculation engine
  - `engine/equation/equation_engine.py` — linear/quadratic/cubic/quartic solvers
  - `engine/calculus/calculus_engine.py` — differentiation (5-point stencil + Richardson), integration (Simpson's rule)
  - `tests/` — pytest suite, 871 test items total, 249 skipped in headless CLI (browser/GUI dependent)

---

## 2. Bug List (Fix in This Exact Order)

Each entry below is ordered by **fix order**, not just severity — some fixes must happen before others because later bugs depend on earlier ones being correct (e.g., fraction display must be sane before equation screen flow is redesigned, since the equation screens render fractions).

---

### BUG-A — No batch/run file for local execution
**Severity:** LOW (quality of life, not correctness)
**Status:** Confirmed by user
**File:** repo root (new file needed)

**Problem:** User must manually run the server via CLI every time instead of double-clicking a batch file.

**Root cause:** No `.bat` (Windows) launcher exists in the repo.

**Fix direction:** Create a `run.bat` in repo root that:
- Activates the Python virtual environment if one exists (check for `venv/Scripts/activate.bat` or `.venv/Scripts/activate.bat`)
- Runs `python mvp_server.py`
- Does NOT close the window on exit (use `pause` or keep terminal open) so errors are visible

**Decision tree:**
- IF a venv folder exists in repo → activate it first, then run server
- IF no venv exists → run with system Python directly, but print a warning line in the batch file output that no venv was found
- IF `mvp_server.py` is not found at repo root → search one level into common subfolders (`backend/`, `server/`) before failing

**Test:** Double-click `run.bat` from a clean checkout. Server must start and be reachable at its usual local URL (check `mvp_server.py` for the port it binds to — do not assume 8000 or 5000, read the actual bind call). No manual CLI interaction required.

---

### BUG-B — `/api/fraction` produces mathematically misleading fractions for irrational numbers
**Severity:** HIGH (correctness — this is the `sin(60) = 2521/2911` bug)
**Status:** Confirmed by both user and Jules audit (BUG-002), flagged independently by ChatGPT review
**File:** `mvp_server.py`, lines ~3827–3842 (verify exact line numbers in current checkout before editing, code may have shifted)
**Function:** HTTP handler for `/api/fraction`

**Problem:** Any decimal value, including irrational results like `sin(60°) = 0.8660254037844386` (which is exactly `√3/2`), gets forced through `Fraction(value).limit_denominator(10000)`. This returns `2521/2911` — a fraction that is numerically close but has zero mathematical relationship to the actual exact value. Same problem affects `pi` → `355/113`, and will affect any irrational trig/log/sqrt result.

**Root cause:** `limit_denominator(10000)` is designed for "give me the simplest fraction close to this float," not "tell me if this is actually rational." It cannot and does not distinguish between a genuine rational number (like `0.25` → `1/4`) and an irrational approximation (like `0.8660254...` → should NOT become a clean-looking fraction).

**Fix direction:** The endpoint needs to know, or be told, whether the value it's converting came from a known exact/symbolic source (e.g., the evaluator already knows `sin(60)` involved a special angle) versus an arbitrary float. Two acceptable approaches, pick based on what's feasible given the current architecture:

**Decision tree:**
- IF the calling code (wherever `/api/fraction` is invoked from, trace this in `frontend.html` and `mvp_server.py`) already has access to the symbolic/exact form (e.g., special-angle trig results, known constants like `sqrt(n)` for small `n`) → pass that symbolic form through and render it directly (e.g., `√3/2`) instead of calling `/api/fraction` on the decimal approximation at all.
- IF no symbolic form is available (general arbitrary decimal) → apply a correctness check before returning a fraction: compute `abs(float(frac) - value)`. If this error is below a tight tolerance (e.g., `1e-9`) AND the denominator found is "small" in a way consistent with the number of decimal digits actually entered/computed (not just "whatever `limit_denominator(10000)` found"), accept it. Otherwise, do NOT silently return a misleading fraction — return the decimal with an indicator that no clean exact fraction exists (exact wording/format is an implementation decision for whoever codes it, but it must not claim false precision).
- IF the value is a "nice" terminating decimal (e.g., `0.25`, `0.5`, `0.125`) → the existing `limit_denominator` approach is fine as-is, no change needed for these cases.
- IF the value came from a user-entered fraction originally (e.g., user typed `1÷4`) → that should already be tracked as exact and never need this approximation path at all. Verify this is the case; if the app is losing exactness somewhere between input and this endpoint, that's part of this same fix.

**Test:**
- Request fraction conversion for `sin(60°)` in degree mode → must NOT return `2521/2911`. Must either show `√3/2` symbolically or clearly indicate no exact simple fraction.
- Request fraction conversion for `pi` → must NOT return `355/113` as if exact.
- Request fraction conversion for `0.25` → must still return `1/4` (regression check — don't break the working case).
- Request fraction conversion for `1/4` entered directly as a fraction → must return `1/4` exactly, unaffected by this fix.
- Add the missing test: `tests/integration/test_fraction_api_irrational.py` (currently does not exist per Jules audit, Section 11, finding 1) — write it as part of this fix, not as an afterthought.

---

### BUG-C — Base answer format should default to improper fraction unless changed in SHIFT+MENU setup
**Severity:** MEDIUM
**Status:** Confirmed by user, exact mechanism unverified ("i have no idea if SHIFT + menu setup works")
**File:** `frontend.html` (answer formatting / settings state) and `mvp_server.py` (if format preference is sent server-side)

**Problem:** Two issues bundled together:
1. Default answer format should be improper fraction, not mixed number, unless the user has explicitly changed this via SHIFT+MENU setup.
2. It's unknown whether SHIFT+MENU setup even works at all currently.

**Root cause:** Unknown until investigated — this is a "find out first, then fix" bug, not a "fix directly" bug.

**Decision tree:**
- FIRST: trace the SHIFT+MENU+SETUP key sequence in `frontend.html`. Find the phase/state handler for it.
- IF the setup menu opens and changes a state variable but that variable is never read by the fraction-rendering code → the bug is a disconnected setting. Fix: wire the setting into the actual rendering path (`exactSolveFormat()` and `equationNumberToLatex()` per the earlier source excerpt, and wherever general calculation answers are formatted).
- IF the setup menu doesn't open at all (key sequence broken) → the bug is in the key-handling state machine for that phase. Fix: trace what phase SHIFT+MENU+SETUP is supposed to enter and why it's not reaching that phase, fix the phase transition.
- IF the setup menu opens, the setting changes, and it IS read by the fraction renderer, but the renderer's default (with no setting applied) is wrong → fix the default value only, in whichever state initializer sets `appState` or equivalent at startup.
- IN ALL CASES: once the setting works, the **default on fresh calculator state / reset** must be improper fraction, not mixed number.

**Test:**
- On a fresh/reset calculator state, compute a result that would render as a fraction greater than 1 (e.g., `7/2`). Must display as `7/2`, not `3 1/2`.
- Enter SHIFT+MENU+SETUP, locate the fraction format option, change it to mixed number, exit setup, repeat the same calculation. Must now display as `3 1/2`.
- Change it back to improper, confirm it returns to `7/2`.
- Reset the calculator (if a reset function exists) and confirm it returns to the improper-fraction default, not whatever was last set.

---

### BUG-D — Polynomial degree selection requires manual `=` press instead of auto-confirming
**Severity:** MEDIUM (UX, not correctness)
**Status:** Confirmed by user and by code inspection
**File:** `frontend.html`, around line 8635 (verify current line number — code shifts)
**Function:** Key handler for `polynomialDegree` phase

**Problem:** Pressing `2`, `3`, or `4` during polynomial degree selection only highlights/selects that degree. The user must then press `=` to confirm and proceed. It should auto-proceed immediately on pressing 2, 3, or 4, and do nothing on any other key.

**Current code (from prior inspection):**
```javascript
case "2": case "3": case "4":
  selectedMenuItem = parseInt(key) - 2;
  renderLCD();
  break;
```

**Root cause:** The key handler sets the selection state but relies on a separate `=` handler (confirmed to exist, sets `polynomialDegree`, initializes coefficient slots, and transitions to `polynomialInput` phase) instead of doing all of that immediately.

**Fix direction:** Merge the confirm logic into the 2/3/4 key handler itself, so no separate `=` press is needed. The existing `=` handler's logic (set `polynomialDegree` to selection+2, initialize `appState.polynomial` with the right number of null coefficient slots, set `appState.phase = "polynomialInput"`) needs to run immediately when 2, 3, or 4 is pressed.

**Decision tree:**
- IF pressing `=` elsewhere in the app (outside this phase) has other meanings that must be preserved → do not remove the `=` handler for this phase entirely if it's reused for something else; just make 2/3/4 not require it.
- IF any other key is pressed during `polynomialDegree` phase (not 2, 3, or 4, and not a legitimate navigation/cancel key like `AC` or `EXIT`) → it must do nothing. Verify this is already the case or add a no-op default.
- IF `AC` or `EXIT` is pressed during this phase → confirm existing cancel/back behavior is preserved and not broken by this change.

**Test:**
- From the polynomial degree selection screen, press `2`. Calculator must immediately move to the quadratic coefficient input phase (no second keypress needed).
- Same for `3` (cubic) and `4` (quartic).
- Press any other key (e.g., `7`, `+`) while on the degree selection screen — nothing should happen, screen stays on degree selection.
- Press `AC` on the degree selection screen — must return to the prior menu/screen as it did before this change.

---

### BUG-E — Quadratic/polynomial solver dumps all output on one screen instead of paging through separate screens
**Severity:** HIGH (this is the biggest UX/authenticity gap — real Casio ClassWiz pages through results one screen at a time)
**Status:** Confirmed by user with exact mockup provided
**File:** `frontend.html` — equation result rendering logic (equation UI state `appState.equation`, phase transitions after a quadratic is solved)

**Problem:** After solving a quadratic, the calculator currently shows everything at once on one screen: the equation, both roots, the 1/2 d/c toggle, and the extremum — all stacked together (see reference screenshot: `5x² + 10x + 25 = 0`, `Solution`, `x1 = -1 - 2i`, `1/2 d/c`, `Extremum: x = -1, y = 20` all visible simultaneously).

Real Casio behavior, and what's needed here, is **one piece of information per screen**, navigated with arrow keys (the "1/2 d/c" indicator is the paging hint the real calculator shows — "page 1 of 2, use d/c or arrow to continue").

**Required screen sequence (exact layout, using `[]` to represent the entered coefficient values):**

**Screen 1 — Equation + first root:**
```
[]x^2+[]x+[]=0

x1 =

                    ANS [in fraction/exact form]
```

**Screen 2 — Equation + second root:**
```
[]x^2+[]x+[]=0

x2 =

                    ANS [in fraction/exact form]
```

**Screen 3 — Minimum/maximum x-coordinate:**
```
Min of y = ax^2+bx+c

x =

                    ANS
```

**Screen 4 — Minimum/maximum y-coordinate:**
```
Min of y = ax^2+bx+c

y =

                    ANS
```

Note: "Min" should correctly say "Max" when the parabola opens downward (`a < 0`) — this must be checked, do not hardcode "Min".

**Root cause:** The result-rendering code builds one combined string/template with all values and dumps it to the LCD in a single render call, instead of maintaining a `resultScreenIndex` (or equivalent) and rendering only the current screen's content, advancing on arrow key / navigation input.

**Fix direction:**
1. Add a state variable (e.g., `appState.equation.resultPage`, 0-indexed, 0 to 3 for the four screens above) that tracks which of the four result screens is currently displayed.
2. Rewrite the result-rendering function to output ONLY the content for the current `resultPage`, matching the four layouts exactly above.
3. Wire the arrow keys (down/right, whatever the existing "d/c" paging convention uses elsewhere in the app — check if other multi-screen results like simultaneous equations already do this correctly and reuse that exact pattern) to increment `resultPage`, wrapping or stopping at page 3 (last page) as appropriate.
4. Confirm "Min" vs "Max" label logic reads the leading coefficient sign correctly.
5. For non-real (complex) roots, confirm Screen 1 and Screen 2 still each show one root, not both at once, same paging behavior.
6. For repeated roots (discriminant = 0), decide and implement: does it still show two screens with the same value, or one screen noting the repeated root? Check what the real Casio ClassWiz does for this case if any reference material exists in the repo; if not, default to showing the same root on both x1 and x2 screens for consistency with the paging pattern, and flag this assumption back to the user for confirmation rather than silently deciding.

**Decision tree:**
- IF the app already has a working paging pattern elsewhere (e.g., simultaneous equations might already page between `x=`, `y=`, `z=` screens) → copy that exact mechanism rather than inventing a new one.
- IF no existing paging pattern exists anywhere in the app → build the minimal state machine described above, and flag that this is a new pattern so it can be reused for other multi-result features later.
- IF the equation has only real, distinct roots → four screens as described.
- IF the equation has a repeated root → see note above, implement the default, flag the assumption.
- IF the equation has complex roots → x1 and x2 each show their complex value on their own screen, same four-screen structure, extremum screens still apply (extremum is still well-defined for a real-coefficient quadratic even with complex roots).

**Test:**
- Solve `x² - 5x + 6 = 0`. Screen 1 must show only the equation and `x1 = 2` (or 3, whichever the app orders first) with no other roots or extremum visible. Press next/arrow → Screen 2 shows only `x2 =` the other root. Press next → Screen 3 shows only `x = ` for the extremum. Press next → Screen 4 shows only `y = ` for the extremum.
- Solve `5x² + 10x + 25 = 0` (the exact case from the bug report screenshot) and confirm it no longer dumps all four pieces of info at once.
- Confirm a downward-opening parabola (negative leading coefficient) shows "Max" not "Min" on screens 3 and 4.
- Confirm arrow/navigation key works to move forward through all four screens and does not crash or show blank content on any screen.
- Confirm pressing `AC` or exiting from any of the four screens correctly returns to the main calculator state, not a broken intermediate state.

---

### BUG-F — LCD cursor `|` vertical position needs minor downward adjustment
**Severity:** LOW (cosmetic)
**Status:** Confirmed by user
**File:** `frontend.html` — CSS/positioning for the cursor element on the LCD

**Problem:** The blinking `|` cursor sits slightly too high and needs to move down "a lil bit... not that much."

**Fix direction:** Locate the cursor element's CSS (likely a `top`, `margin-top`, or `transform: translateY()` value). Adjust by a small amount — start with 1-2px and let the user visually confirm, do not guess a large value.

**Decision tree:**
- IF the cursor position is controlled by a fixed CSS offset → adjust that offset by 1-2px downward, screenshot/confirm with user before considering this done since "a lil bit" is subjective and the user needs to visually approve it.
- IF the cursor position is computed dynamically relative to text baseline → find where that calculation happens and adjust the offset constant there instead.

**Test:** Visual only — render the calculator, show the cursor in its default blinking state, compare before/after position. This requires user visual confirmation, it cannot be purely automated. Flag this test as requiring a screenshot back to the user before being marked DONE.

---

### BUG-G (from Jules audit, BUG-001) — JS test harness `ReferenceError: getParent is not defined`
**Severity:** HIGH for test suite integrity (not a user-facing bug, but it's silently hiding real test coverage)
**Status:** Confirmed, reproduced by Jules
**File:** `tests/unit/test_lowercase_x_variable.py`, lines ~265–275
**Function:** `TestFrontendVariableRouting._route()`

**Problem:** This test extracts a JS snippet from `frontend.html` and runs it in Node.js to test variable routing logic. The extracted snippet calls `getParent()`, which is defined elsewhere in `frontend.html` but not included in the extraction, causing a `ReferenceError` and failing 2 tests.

**Root cause:** Incomplete extraction — the test's snippet-builder doesn't pull in all the JS dependencies the snippet under test actually needs.

**Fix direction:** In the test file's snippet-construction logic, include the `getParent()` function definition (either by extracting it from `frontend.html` alongside the code under test, or by stubbing a minimal equivalent directly in the test file if `getParent()` is simple and self-contained).

**Decision tree:**
- IF `getParent()` is a small, pure utility function (no external dependencies itself) → extract its exact source from `frontend.html` and prepend it to the generated `.x_variable_route_tmp.js`.
- IF `getParent()` itself depends on other undefined functions/DOM state → this could cascade; in that case, write a minimal test-only stub of `getParent()` that satisfies what the specific test actually needs, and comment clearly in the test file that it's a stub, not the real implementation.

**Test:** Run `PYTHONPATH=. pytest tests/unit/test_lowercase_x_variable.py -v`. Both `test_no_route_inserts_bare_lowercase_x` and `test_plain_right_paren_unchanged` must pass with no `ReferenceError`.

---

### BUG-H (from Jules audit, BUG-003) — Standalone `engine.tokenizer` cannot tokenize function names like `sin`, `sqrt`, `log`
**Severity:** LOW for current app function (the app works because `mvp_server.py` pre-transforms these before they ever reach the tokenizer), but HIGH for future maintainability and the "frontend/backend parity" concern ChatGPT flagged
**Status:** Confirmed, suspected defect per Jules, direct repro confirmed
**File:** `engine/tokenizer.py`, lines ~63–66
**Function:** `tokenize()`

**Problem:** `engine.tokenizer.tokenize("sin(30)")` throws `TokenizerError: Unexpected character 's' at position 0`. The tokenizer only recognizes digits, decimal points, `+ - * / ( )`, and `**`. It has no concept of identifiers/function names at all. The app currently works around this entirely inside `mvp_server.py`, which regex-transforms `sin(...)`, `sqrt(...)`, etc. into lower-level operations before the string ever reaches the tokenizer.

**Why this matters beyond "it's just a standalone module issue":** This is also the underlying reason the "frontend/backend parity" risk ChatGPT flagged exists — if `frontend.html` has its own JS-side evaluation logic for anything (preview rendering, live calculation feedback, etc.) that does NOT go through `mvp_server.py`'s regex transform layer, it is evaluating a different grammar than the Python engine. This needs to be checked as part of this fix, not assumed away.

**Fix direction:**
1. Extend `TokenKind` in `engine/tokenizer.py` to include an `IDENTIFIER` or `FUNCTION` token type.
2. Extend `tokenize()` to recognize alphabetic runs as identifier tokens (e.g., `sin`, `cos`, `sqrt`, `log`, `ln`, `cbrt`) instead of throwing on the first letter.
3. Extend `engine/parser.py` to handle `FUNCTION LPAREN expression RPAREN` as a valid grammar production.
4. Extend `engine/evaluator.py` to actually evaluate these function nodes (map `sin` → `math.sin` with correct degree/radian handling, etc. — check how `mvp_server.py`'s `safe_evaluate_expression` currently handles angle mode and mirror that logic here so there is ONE source of truth for angle handling, not two).
5. **Separately and importantly:** audit `frontend.html` for any independent JS-side math evaluation (not just display formatting) that duplicates logic instead of calling the backend. If found, document it — do not silently leave two diverging implementations in place. This is the "Expression rewriting" and "Frontend/backend parity" risk ChatGPT flagged as "Potentially high."

**Decision tree:**
- IF `frontend.html` does NO independent evaluation (pure display/state management, all math goes to `mvp_server.py`) → this bug is purely about the standalone `engine` module's completeness, fix as described in steps 1-4, no parity risk exists.
- IF `frontend.html` DOES perform some independent evaluation (e.g., live preview before hitting `=`) → flag this explicitly back to the user as a separate, higher-priority finding before proceeding, since it means two implementations can silently disagree. Do not fix this silently as a side effect of BUG-H; it may need its own bug entry and its own test matrix.

**Test:**
- `engine.tokenizer.tokenize("sin(30)")` must return valid tokens, not throw.
- `engine.parser.parse(engine.tokenizer.tokenize("sin(30)"))` must build a valid AST.
- Full pipeline: evaluating `sin(30)` through the standalone `engine` module directly (bypassing `mvp_server.py` entirely) must match the result `mvp_server.py` already produces for the same input, in the same angle mode.
- Add the missing test: `tests/unit/test_engine_standalone_functions.py` (currently does not exist per Jules audit Section 11, finding 2).
- Repeat for `sqrt`, `log`, `ln`, `cos`, `tan`, `cbrt` at minimum.

---

### BUG-I (from Jules audit, BUG-004) — Inconsistent AST representation for unary minus
**Severity:** INFORMATIONAL / LOW — fix only if time allows after all above are done and tested
**Status:** Informational, confirmed structural asymmetry, not a behavioral bug
**File:** `engine/parser.py`, lines ~110–114 and ~122–126

**Problem:** `-5` parses to `NumberNode(-5)` (direct constant folding), but `-(2+3)` parses to `BinaryOpNode(NumberNode(0), MINUS, right)` (dummy zero-subtraction). Both are numerically correct but structurally inconsistent, which makes future AST-based features (symbolic simplification, step-by-step display) harder to build correctly.

**Fix direction:** Introduce a dedicated `UnaryOpNode` AST type and use it consistently for all unary negation, removing both the constant-folding special case and the dummy-zero-subtraction special case.

**Decision tree:**
- ONLY attempt this fix after BUG-A through BUG-H are fixed and tested, since this touches the core parser and any regression here risks breaking everything downstream.
- IF introducing `UnaryOpNode` requires changes to the evaluator's visitor/dispatch logic → make sure every place that currently pattern-matches on `BinaryOpNode` with a zero-left-operand as a unary-minus detector is updated, not left as dead/unreachable code.

**Test:** Add `tests/unit/test_parser_ast_structure.py` (missing per Jules audit). Confirm `-5` and `-(2+3)` both produce `UnaryOpNode` structurally, and confirm all existing arithmetic tests (Section 3, AR series) still pass after this refactor — this is a pure refactor, it must not change any numerical output.

---

### BUG-J (from Jules audit, BUG-005) — Trig functions show float noise instead of exact values for special angles
**Severity:** INFORMATIONAL / LOW, but worth fixing alongside BUG-B since they're related (both are "special angle exactness" problems)
**Status:** Informational, confirmed
**File:** `mvp_server.py`, lines ~1335–1342
**Function:** `_safe_sin()`, `_safe_cos()`

**Problem:** `sin(30°)` in degree mode returns `0.49999999999999994` instead of exactly `0.5`, because `30 * (math.pi / 180)` is not exactly `π/6` in IEEE 754 floating point. The code already special-cases exact multiples of 90° (0°, 180°, 360°) to return clean `0.0`, but doesn't extend this to other well-known special angles (30°, 45°, 60°, etc.).

**Fix direction:** Extend the existing special-angle guard pattern (whatever mechanism already handles 0°/180°/360° cleanly) to also cover 30°, 45°, 60°, and their reflections/multiples, returning exact values (`0.5`, `√2/2`, `√3/2`, etc. as appropriate — decide whether to return these as floats rounded to match exactly, or hand off to the symbolic form from BUG-B's fix) instead of the raw float computation.

**Decision tree:**
- IF BUG-B is already fixed and produces symbolic exact forms for special angles → this fix should feed directly into that, i.e., `_safe_sin(30, degrees=True)` should internally know it's hitting a special angle and route to the same exact-value path BUG-B's fraction logic uses, rather than being fixed independently with duplicate logic.
- IF BUG-B's fix does not end up covering this at the trig-function level → implement this as a standalone lookup table in `_safe_sin`/`_safe_cos` (and `_safe_tan` if it exists) for the standard special angles, checked before falling through to raw float computation.

**Test:** Add `tests/unit/test_trig_exact_values.py` (missing per Jules audit). `sin(30°)` must return exactly `0.5`, `cos(60°)` must return exactly `0.5`, `tan(45°)` must return exactly `1.0`, in addition to the existing 0°/180°/360° guards continuing to pass.

---

## 3. Full Regression Test Checklist (Run After ALL Bugs Fixed, Before Merge)

This is the complete mathematical correctness suite. Every test below must be run through the actual on-screen keypad UI (not just unit tests calling internal functions directly), per the original test plan's execution requirements. Record test ID, exact key sequence used, expected result, actual result, and PASS/FAIL/BLOCKED/UNSUPPORTED for each.

### 3.1 Arithmetic
AR-01 through AR-16 — see table below.

| ID | Input | Expected |
|---|---|---|
| AR-01 | `2 + 3` | `5` |
| AR-02 | `9 - 14` | `-5` |
| AR-03 | `7 × 8` | `56` |
| AR-04 | `45 ÷ 9` | `5` |
| AR-05 | `2 + 3 × 4` | `14` |
| AR-06 | `(2 + 3) × 4` | `20` |
| AR-07 | `-5 + 12` | `7` |
| AR-08 | `2^5` | `32` |
| AR-09 | `√144` | `12` |
| AR-10 | `1 ÷ 4` | Exact fraction `1/4`; decimal mode `0.25` |
| AR-11 | `2.5 + 3.75` | `6.25` |
| AR-12 | `(-3)^2` | `9` |
| AR-13 | `-3^2` | `-9` |
| AR-14 | `0 ÷ 5` | `0` |
| AR-15 | `5 ÷ 0` | Math ERROR, no crash |
| AR-16 | `√(-1)` | Domain error or complex result if supported |

### 3.2 Integration (symbolic, mark UNSUPPORTED if not implemented rather than FAIL)
IN-01 through IN-10 — `∫(x^2 dx)` = `x^3/3 + C`, etc. per original spec. Also verify definite numerical integration separately (e.g. `∫₀¹ x^2 dx` = `1/3`).

### 3.3 Differentiation (symbolic where implemented, numerical-at-a-point otherwise)
DI-01 through DI-10 per original spec — `d/dx(x^2)` = `2x`, etc.

### 3.4 Equation/Function Mode
- 4.1 Quadratics: EQ-01 through EQ-08 (includes complex roots EQ-07/EQ-08 if supported) — **this is where BUG-E's new four-screen paging gets exercised, test the paging explicitly for every one of these, not just the final numeric answer.**
- 4.2 Simultaneous equations: SE-01 through SE-05, including dependent (SE-04) and inconsistent (SE-05) systems handled gracefully.
- 4.3 Function mode: FN-01 through FN-06, only if implemented.

### 3.5 SHIFT, CALC, SOLVE
CS-01 through CS-12 per original spec — **CS-10 specifically must verify SHIFT+MENU+SETUP (BUG-C) actually works now.**

### 3.6 Formula Verification
FM-01 (angle between lines) through FM-09 (modulus) per original spec.

### 3.7 Quadratic Regression List
QR-01 through QR-07, cross-checked against discriminant. **Every one of these must be re-verified through the new BUG-E four-screen flow, and every one of these exercises BUG-B's fraction/exactness fix where roots are irrational (QR-06, QR-07).**

### 3.8 New Tests Required By This Handover (write these, they don't exist yet)
- `tests/integration/test_fraction_api_irrational.py` (BUG-B)
- `tests/unit/test_engine_standalone_functions.py` (BUG-H)
- `tests/unit/test_parser_ast_structure.py` (BUG-I)
- `tests/unit/test_trig_exact_values.py` (BUG-J)

### 3.9 Frontend/Backend Parity Check (from ChatGPT's review concern)
As part of BUG-H's audit step, produce a short written confirmation (not a full new test suite unless a real divergence is found) of whether `frontend.html` has any independent math evaluation path. If one is found and it diverges from backend results for ANY test in this section, that is a new CRITICAL bug and must be reported back before continuing, not silently patched.

---

## 4. Git Workflow

1. All fixes happen as commits on `v0.12_port_oct21`.
2. One bug fix = one commit. Commit message format: `Fix BUG-X: <short description>`.
3. Do NOT run `git merge` into `v0.12` until Section 5 is fully satisfied.
4. Do NOT force-push. Do NOT rewrite history on this branch once work has started.
5. After each commit, run the relevant test(s) for that specific bug (listed in each bug's "Test" section above) and paste the output before moving to the next bug.
6. At the very end, run the full suite: `PYTHONPATH=. pytest` and confirm pass count is equal to or higher than the baseline (619 passed / 2 failed / 249 skipped / 1 xfailed, per the Jules audit baseline — the 2 failed should become 0 once BUG-G is fixed).

---

## 5. Definition of Done

This work is considered COMPLETE and ready to report back only when ALL of the following are true:

- [ ] BUG-A through BUG-J are each individually fixed, committed separately, and their individual tests pass.
- [ ] The full regression checklist in Section 3 has been run through the actual UI (not just unit tests) and every result recorded as PASS, FAIL, BLOCKED, or UNSUPPORTED — no test silently skipped without a reason noted.
- [ ] Any FAIL found during Section 3 that isn't already covered by BUG-A through BUG-J is reported back as a new finding, not silently fixed or silently ignored.
- [ ] The frontend/backend parity check (Section 3.9) has been explicitly performed and its result reported.
- [ ] Full `PYTHONPATH=. pytest` run shows 0 failures (previously 2, both from BUG-G) and the skip count is understood (249 skipped is expected/acceptable, headless environment limitation — do not try to force these to run unless you can explain exactly why a specific one can run headless).
- [ ] No file outside the files explicitly named per bug above has been modified. If a fix genuinely required touching an additional file, that must be called out explicitly in that bug's final report, not discovered later.
- [ ] The visual-only test (BUG-F cursor position) has been screenshotted and is awaiting the user's explicit visual approval before being marked done.

Only after every box above is checked: report "ALL BUGS RESOLVED, READY FOR MERGE" and stop. The user will handle the merge to `v0.12` themselves, or explicitly instruct otherwise.

---

## 6. Explicit Non-Goals

Do not do any of the following unless the user explicitly asks later:
- Do not redesign the UI beyond what BUG-E specifies.
- Do not add new calculator features not listed in this document.
- Do not "improve" code style, naming, or structure outside the specific lines needed for each bug fix.
- Do not upgrade dependencies.
- Do not touch the 249 headless-skipped tests to try to make them run in CI unless a bug fix specifically requires it and it's explained why.
