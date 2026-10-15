# Mentis ClassWiz Release Audit: Full Context Handoff

Written 15 Oct 2026. Owner: Zaidi. This file is meant to be pasted into ChatGPT so it can write small, safe prompts for opencode. Nothing here assumes you remember the earlier chat.

---

## 0. Instructions for ChatGPT (read this first)

You are writing prompts for **opencode**, a coding agent that runs on Zaidi's Windows PC against the real repo. Zaidi runs out of tokens fast, so:

1. Write **one phase per prompt**. Never one giant prompt. Each prompt must end with acceptance checks the agent can run and a checkpoint line to append to `E:\A.G\AUDIT_PROGRESS.md`.
2. Every prompt must tell the agent: never claim something passes unless it ran it and saw the result. Anything not run is marked UNTESTED.
3. Every prompt must say: stop and report if budget runs low. Do not rush the last commits.
4. Audit prompts and fix prompts are **separate**. An audit prompt must say "do not edit any file except docs/ reports". A fix prompt must name the exact bug, the exact failing input, and the expected output.
5. Do not trust anything a previous agent (Jules) claimed unless section 6 says it was verified. Treat Jules's work as hints, not as code to merge.
6. Git rules for every prompt are in section 9. Copy them in.

Working locations (Windows):

- Repo (the real working copy): `E:\A.G\casio_mvp`
- GitHub: `https://github.com/Red-swipe/mvp`
- Delivered release, READ ONLY, never overwrite: `C:\Users\DELL\OneDrive\Desktop\MentisClassWiz_v0.1`
- Clean copy of that release: `E:\A.G\mentis_release_clean`
- Playwright Chromium: `C:\Users\DELL\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe`
- Python with Playwright: `C:\Users\DELL\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe`
- Earlier helper scripts: `E:\A.G\probe_release.py`, `python_battery.py`, `file_release_battery.py`, `cdp_probe.py`, `release_file_list.txt`
- Progress checkpoint file: `E:\A.G\AUDIT_PROGRESS.md`
- Key code: `frontend.html` (function `localEvaluate`, plus `_evalStr`, `_parseEval`, `insertPower`, `_extractPowerBaseItems`, `exactFractionResult`), `mvp_server.py` (`safe_evaluate_expression`), `engine\parser.py`, `engine\evaluator.py`
- Release contents: `__pycache__`, `ClassWizFontSet`, `engine`, `katex`, `python` (bundled interpreter), `qrcode`, `frontend`, `launcher`, `MentisClassWiz` (the .bat), `mvp_server`, `README`

---

## 1. The project in one paragraph

Mentis ClassWiz is a Casio fx 991EX emulator. It has a PySide6 desktop app and a browser version (`mvp_server.py` plus `frontend.html`, using a shared Python engine). In the browser version the page can run in two ways: served by the Python server (calls `/api/key`, `/api/calc` and so on) or opened directly as `file://` where a JavaScript copy of the evaluator (`localEvaluate`) does the maths. The two evaluators must give identical results.

---

## 2. The incident (5W1H)

- **What**: A teacher ran release v0.1 in class. A simple expression showed **Math ERROR**.
- **Who**: A teacher with no Python and no git installed.
- **Where**: Her Windows PC, by double clicking the launcher .bat from the delivered release folder (which sits under OneDrive on the build machine).
- **When**: Before this audit started. The exact expression she typed is **not known**.
- **Why it matters**: A calculator that errors on simple input in front of a class destroys trust, and the cause is still unproven.
- **How it was investigated**: A previous agent ran case 1 (`5+-1(3-1)/(9-3)`) through the keypad on `file://` in a clean copy of the release. It showed 4.666666667 with no console errors. So the failure did **not** reproduce on `file://`. The .bat plus bundled python route was never tested.

### The most important unanswered question

Nobody has found the root cause. All candidates are theory. Do **not** write the root cause into any report as fact until it is reproduced.

---

## 3. Original task given to the agents

Role: release auditor and fixer. Find the root cause with evidence, fix it, prove the fix from a clean copy.

Original rules:

1. Never claim something passes unless run and seen. Else mark UNTESTED.
2. Do not overwrite the delivered release folder. Build fixes into a new folder.
3. Do not touch unrelated untracked files in the repo. No force push, no branch deletion.
4. Commit small, one concern per commit.
5. After every phase write a checkpoint (done, verified, next) to `E:\A.G\AUDIT_PROGRESS.md`. If budget runs low, stop and report.

Original phases: 0 snapshot, 1 launcher path (.bat plus bundled python, PATH stripped to System32 and Windows, folder with spaces), 2 swallowed error (Math ERROR only for genuine math errors, otherwise System ERROR plus console.error, hidden debug panel on Ctrl+Shift+D, replace "To infinity and beyonddd" with Math ERROR), 3 expression battery on three paths, 4 fix defects, 5 environment matrix (Chromium, Firefox, WebKit, space paths, OneDrive placeholder files), 6 packaging and proof (rewrite .bat, startup self test, build_release, verify_release, zip `MentisClassWiz_v0.1.1.zip`).

Three paths used everywhere:

- **Path A**: `frontend.html` on `file://`, no server, driven through keypad buttons (`data-key` attributes, screen is `.lcd`).
- **Path B**: same page served by the server started through the .bat, driven through the keypad.
- **Path C**: Python engine called directly (`mvp_server.safe_evaluate_expression`).

Any difference between paths counts as FAIL even if one path is right.

### Implicit multiplication convention (follow Casio)

A number, closing bracket or constant directly followed by an opening bracket, function or variable binds tighter than explicit × and ÷. So `8÷2(2+2) = 8÷(2(2+2)) = 1`. This must be written in the README.

### The 46 case battery (expected values)

Angle mode Degree.

| # | Input | Expect |
|---|---|---|
| 1 | 5+-1(3-1)/(9-3) | 14/3 (4.666666667) |
| 2 | 2+3×4 | 14 |
| 3 | (2+3)×4 | 20 |
| 4 | 10−4÷2 | 8 |
| 5 | −5+8 | 3 |
| 6 | 7−−3 | 10 |
| 7 | 2(3+4) | 14 |
| 8 | 2(3+4)(5−1) | 56 |
| 9 | (1+2)(3+4) | 21 |
| 10 | 3(−2) | −6 |
| 11 | 12÷(2+4) | 2 |
| 12 | 1÷3+1÷6 | 1/2 |
| 13 | 2^3 | 8 |
| 14 | 2^−2 | 1/4 |
| 15 | −2^2 | −4 |
| 16 | (−2)^2 | 4 |
| 17 | √16 | 4 |
| 18 | √(9+16) | 5 |
| 19 | 5! | 120 |
| 20 | 10÷4 | 5/2 |
| 21 | 0.1+0.2 | 0.3 |
| 22 | 100×1.05^2 | 110.25 |
| 23 | (3−1)/(9−3) | 1/3 |
| 24 | 8÷2(2+2) | 1 |
| 25 | 1/2+1/3 | 5/6 |
| 26 | 3.5×2 | 7 |
| 27 | 9−3×2+1 | 4 |
| 28 | sin(30) | 0.5 |
| 29 | log(100) | 2 |
| 30 | 2π | 6.283185307 |
| 31 | (5+3)/(2−2) | Math ERROR (genuine, must still show) |
| 32 | 99999×99999 | 9999800001 |
| 33 | 7+(−3)(−2) | 13 |
| 34 | 2×(3+(4−1)×2) | 18 |
| 35 | 5+5 then = then ×2 = | 20 (Ans chaining) |
| 36 | 1(3−1) | 2 |
| 37 | (2)(3) | 6 |
| 38 | 2(3)(4)(5) | 120 |
| 39 | −(3+4) | −7 |
| 40 | 3−(−2) | 5 |
| 41 | (((1))) | 1 |
| 42 | 2×−3 | −6 |
| 43 | 1+(2(3+4)) | 15 |
| 44 | (1+2)(3+4)(5+6) | 231 |
| 45 | 2(3+4)^2 | 98 |
| 46 | 1÷(1÷(1÷2)) | 1/2 |

Variant tests required for cases 1, 7, 9, 12: ASCII minus vs Unicode minus, × vs *, ÷ vs /, with and without spaces, keypad vs physical keyboard. Report any parser difference.

Display ambiguity to decide once: the Casio fraction setting `ab/c` shows improper fractions as mixed numbers (14/3 appears as `4 2/3`, 5/2 appears as `2 1/2`). Tests should compare **numeric value** for the maths check and check **display format separately** under a stated setting (ab/c or d/c).

---

## 4. Timeline: what happened in the chat

1. Zaidi gave a long local prompt (for an agent on his Windows PC) covering phases 0 to 6, plus the state left by a previous agent.
2. Zaidi asked for a version of that prompt for **Jules** (Google's cloud coding agent). Claude rewrote it because Jules runs on Linux and cannot run a .bat or the bundled Windows python. Claude marked Windows things UNTESTED.
3. **Mistake by Claude**: that rewritten prompt still told Jules to "fix it and open a pull request". Zaidi's original prompt had fix phases, and Claude carried them over instead of making Jules audit only. This is the answer to "why is Jules making changes?" It was told to. It should have been read only.
4. Jules reported Phases 0 to 3, then Phase 4 fixes, then Phases 5 and 6. Claude wrote a follow up prompt, then reviewed the reports and pasted files twice.
5. Claude tried to inspect the GitHub repo. Result: `main` has 4 commits and a stale snapshot (`mvp_server.py` on main is 1886 lines, much smaller than the working version). The only open PRs are #2 (Sep 8, "Add complete forensic audit report (audit.md)") and #3 (Sep 22, "Full Codebase Forensic Audit"), plus one closed PR. **There is no PR or visible branch for `release_fix_v0_1_1`.** GitHub blocked the branches and commits pages to automated access, so the fix branch could not be inspected.
6. Claude reviewed the pasted artifacts and found serious problems (section 5 and 6).
7. Zaidi asked for this document so ChatGPT can drive opencode, because tokens run out quickly.

---

## 5. What Jules reported (as claimed, not verified)

- Branch `release_fix_v0_1_1` created. Baseline: pytest 455 passed, 226 skipped. `verify.py` legacy scroll checks clean.
- Phase 1: split genuine Math ERROR from non math failures. Non math errors show `System ERROR` and log stack traces to `console.error`. Replaced "To infinity and beyonddd" with "Math ERROR". Added a hidden debug panel (Ctrl+Shift+D) with the last 20 errors.
- Phase 2: static dependency audit says standard library only. Static audit of `RUN_CALCULATOR.bat` and `BUILD_ON_MY_PC.bat` found unquoted path risk, port conflicts, no readiness check (all UNTESTED at runtime). Linux server audit hit `/api/key`, `/api/calc`, `/api/eval`, `/api/solve`, `/setup_update`. Static assets (`katex`, `ClassWizFontSet`, `qrcode`) exist.
- Phase 3: ran the 46 cases on paths A, B, C. Defects listed: adjacent brackets rejected, `8÷2(2+2)` gave 16, `(−2)^2` and `2(3+4)^2` failed in the browser, `100×1.05^2` gave 2500 in the browser, `√(9+16)` failed in the Python engine.
- Root causes Jules gave: D1 `insertPower()` took only the last digit as the base (so `100×1.05^2` became `100×1.0×(5^2)` = 2500). D2 `insertPower()` on a closing bracket took only `)` instead of the full bracket group. D3 changed between reports: first "parser rejects parenthesised radicand at `engine/parser.py` line 112", later "raw `√` not translated, `mvp_server.py` line 1360".
- Phase 4 commits claimed: `17ec1ef` (failing tests first), `bc690a5` (adjacent brackets), `92fde39` (implicit multiplication precedence, 8÷2(2+2)=1), `d18e478` (power base extraction in frontend.html). Pytest 501 passed, 226 skipped, 0 failed (455 + 46 new).
- Phase 5: cases 1 to 10 passed in Chromium, Firefox and WebKit via Playwright on Linux.
- Phase 6: rewrote `RUN_CALCULATOR.bat` (cd /d, quoted paths, launcher.log, friendly error). Added `run_startup_selftest()` in `mvp_server.py`. Said next: `build_release.py`, final reports.
- Skipped tests (226): 216 need Playwright plus Chrome, 4 need Playwright plus Chrome plus OpenCV, 2 need a PyInstaller spec, 1 needs node, 1 Playwright not installed. Jules says 12 of the skipped browser tests (in `test_frontend_math_io.py` and `test_unbalanced_parens.py`) cover browser side expression evaluation. **These are the tests that would catch frontend regressions and they were skipped.**

---

## 6. Everything that is wrong or untrustworthy (5W1H per problem)

Trust key: VERIFIED means seen directly in pasted code or files. READ ONLY means found by reading, not run. CLAIMED means only Jules said it.

### P1. The teacher's Math ERROR has no proven root cause

- **What**: Section A of the audit report lists three launcher candidates, all marked UNPROVEN.
- **Who**: Jules wrote them; no one reproduced them.
- **Where**: `docs/AUDIT_REPORT.md` Section A.
- **When**: Candidates created during Phase 3.
- **Why it is weak**: The teacher saw a working calculator screen that showed Math ERROR. If the bundled Python could not import `engine`, or port 8000 was taken, the page would not have loaded at all. Candidate 2 (working directory) is mostly ruled out because the server builds paths from `Path(__file__).resolve().parent`. Candidate 3 cites `Errno 98` which is the Linux code (Windows is `WinError 10048`), so it is theory written on Linux.
- **How**: The audit itself reproduced real Math ERRORs on the delivered v0.1 for plain input: `(1+2)(3+4)`, `2(3+4)(5−1)`, `(2)(3)`, `(−2)^2`, `2(3+4)^2`. A teacher can easily type `(2+3)²` or `(1+2)(3+4)`. This is now the **most likely cause**. Rank the launcher theories below it.

### P2. Adjacent bracket groups rejected (cases 8, 9, 37, 38, 44, 33)

- **What**: `(1+2)(3+4)` gave Math ERROR on all three paths in v0.1.
- **Where**: Python engine parser and `implicitMul`/`startsFactor` logic in `frontend.html`.
- **Why**: Implicit multiplication was refused when a group followed a closing bracket.
- **Status**: CLAIMED fixed (`bc690a5`). The pasted `frontend.html` shows `implicitAllowed = () => true` and an `implicitMul()` that binds tighter than `mulDiv()`, which supports the claim for the JS side (READ ONLY). Python side not seen.

### P3. Implicit multiplication precedence (case 24)

- **What**: `8÷2(2+2)` gave 16, Casio gives 1.
- **Why**: implicit multiplication parsed at the same level as explicit ×÷.
- **Status**: The pasted JS parser now calls `implicitMul()` from inside `mulDiv()` for both operands, so 8÷2(2+2) = 8÷8 = 1 (READ ONLY). Python side CLAIMED.
- **Watch**: `10%10%` must still be Math ERROR; the JS handles that with an earlier regex check, confirm Python does too.

### P4. Power template base extraction

- **What**: `100×1.05^2` gave 2500, `(−2)^2` and `2(3+4)^2` gave Math ERROR in the browser.
- **Where**: `frontend.html`, `insertPower` and new helper `_extractPowerBaseItems` (this is what the pasted file contains).
- **Status of old bug**: Root cause is plausible and consistent with the code.
- **NEW BUG introduced by the fix (READ ONLY, UNTESTED)**: when the base ends with `)`, the walk back only counts an item exactly equal to `(`. Function tokens such as `sin(`, `cos(`, `tan(`, `ln(`, `Abs(`, `Rnd(` are single string items ending in `(`, so they are never counted. Depth never returns to zero, the loop runs to the start of the slot, and the whole slot becomes the base. Example: type `1+sin(30)` then `x²`. Expected 1.25, likely gets (1+sin(30))² = 2.25.
- **Fix idea**: treat any string item ending in `(` as an opener.

### P5. The √ handling and the "D3" story keeps changing

- **What**: Case 17 and 18 failed on path C in the first table, then on A, B in other copies. Diagnosis changed from "parser line 112" to "raw √ not translated".
- **Where**: `mvp_server.safe_evaluate_expression`. On the GitHub `main` copy it does not translate `√`, but it does handle `sqrt(` through `_transform_special_functions` before the parser runs.
- **Why it matters**: The keypad serializes the radical to `sqrt(...)`, so a raw `√` is a test harness artifact, not a user path. But a naive replace of `√` by `sqrt(` leaves an unclosed bracket and would break `√16`.
- **Status**: UNVERIFIED. Needs a direct test of `√16`, `√(9+16)`, `2√9` on all paths.

### P6. Swallowed errors: System ERROR and debug panel

- **What**: Every fetch failure and unknown exception calls `showMathError()`, which shows "Math ERROR".
- **Where**: `frontend.html` in `evaluate()` (the `/api/key` catch), `storeMatrix`, `storeVector`, `doCalc`, `doSolve`, `toggleAnswerFormat`, `syncSpreadsheetCell`, `calculateRatioRemote`, `performConversionRemote`, `performResetRemote`, and the `file://` catch in `evaluate()` which turns any error into Math ERROR.
- **Why it matters**: A server failure looks exactly like a math failure. This is the likely reason the teacher's screen said Math ERROR for a non maths problem, if the cause was not the parser.
- **Status**: Jules says it was implemented. **The `frontend.html` pasted in chat contains none of it**: no "System ERROR" string, no Ctrl+Shift+D handler, and "To infinity and beyonddd" still appears in `DIV_ZERO_MSG`, `localEvaluate()` and `evaluate()`. Either that file was a mid branch snapshot or the Phase 1 changes were lost. Must be checked with grep (section 8).

### P7. "To infinity and beyonddd" for division by zero

- **What**: Case 31 `(5+3)/(2−2)` must show Math ERROR.
- **Status**: In the pasted frontend it still shows the joke text on `file://`. In the JSON battery table, case 31 on A and B shows that text yet is marked PASS. So either not fixed or the table is wrong.

### P8. Exact fraction display for repeating decimals (cases 23, 25, and 1)

- **What**: Spec expects `1/3` and `5/6`. Real path A output before the fixes was `0.3333333333` and `0.8333333333`.
- **Where**: `exactFractionResult()` in `frontend.html`. It takes the displayed 10 digit string, finds a candidate fraction, then rejects it unless `|num/den − n| <= 1e-12`. 5/6 differs from 0.8333333333 by about 3.3e-11, so it is rejected and the decimal stays.
- **Why it matters**: This is a real, probably still open defect that was hidden by fake PASS rows. Later report copies show `1/3` and `5/6` on path A with no fix commit explaining how.
- **Fix idea**: accept the fraction when `localFormat(num/den)` equals the displayed string (same 10 significant digits), keeping the denominator cap at 10000.

### P9. The audit report is corrupted and the PASS/FAIL logic is fake

- **What**: `docs/AUDIT_REPORT.md` contains about eight stacked copies of the battery table with contradictory values and statuses.
- **Where**: Section B of the report plus the JSON dump.
- **Why**: A script or editor appended new tables instead of overwriting. The status column is not computed correctly: one copy marks every row PASS even where output differs from expected (case 18 Math ERROR vs 5, case 31 beyonddd vs Math ERROR, case 29 on A and B, case 17 on C, case 35 on C); another copy marks rows FAIL when the values are correct; another marks case 17 PASS while path C shows Math ERROR; another treats `2 1/2` vs `5/2` as FAIL (string match).
- **Consequence**: "100% PASS on all paths" is not evidence of anything.
- **Also**: the all PASS copy changes path C values (`0.1+0.2` to `0.3`, `sin(30)` to `0.5`) with no matching fix, but leaves `1/3` at `0.3333333333333333`. Looks hand edited or from a different harness.
- **Also unexplained**: case 29 `log(100)` and case 35 (Ans chaining) went from FAIL to PASS with no root cause in the report.

### P10. The tests do not prove what the report says

- **What**: `test_expression_battery.py` calls only Python `safe_evaluate_expression` with ASCII `*` and `/`.
- **Missing**: no Unicode `×÷−` inputs, no variant tests, no JS evaluator test (the JS evaluator is where the implicit multiplication and power template changes live), no keypad driven test.
- **Fake test**: case 35 never tests Ans chaining. It just evaluates `(10.0)*2`.
- **Why the count rose**: 455 to 501 is exactly +46 new Python battery tests, not new coverage of the browser side. The 12 browser tests that cover frontend maths are among the 226 skipped.

### P11. The launcher .bat (UNTESTED on Windows)

- **What**: Jules rewrote `RUN_CALCULATOR.bat`.
- **Issues found by reading (READ ONLY)**:
  1. It calls `"%~dp0python\python.exe" -u "%~dp0launcher.py"`. The delivered release has a `launcher` folder and a bat called `MentisClassWiz`, and the repo root has no .bat and no `launcher.py`. The layout may not match.
  2. First log line uses `>` so launcher.log is overwritten each run (you asked for full output of every run, so append).
  3. `%ERRORLEVEL%` inside an `if` block is expanded at parse time, so the logged value is stale.
  4. No free port logic, no wait until the port answers, no browser opening in the .bat.
  5. If the user closes the server window normally, a non zero exit code shows a false failure message.
- **Why it matters**: This is the only piece that touches the teacher's actual double click route, and it cannot be run on Linux.

### P12. Packaging not delivered

- **What**: `build_release`, `verify_release` and `MentisClassWiz_v0.1.1.zip` were not reported as done.
- **Startup self test** `run_startup_selftest()` is claimed but unseen. Must be verified: on failure it should serve an error page with the real traceback.

### P13. Jules was allowed to change code and its work cannot be seen

- **What**: The Jules prompt (written by Claude) told it to fix bugs and open a PR.
- **Why it is a problem**: Zaidi wanted a pure audit and report. Edits mixed audit with fixes, and the branch is not visible on GitHub (no PR, `main` stale).
- **Where this leaves things**: Jules's commits may live only inside Jules's environment. The real source of truth is the local repo `E:\A.G\casio_mvp`, not GitHub `main`.

### P14. Environment gaps

- Path B and the whole Windows route (bundled python, PATH stripped, folder with spaces, OneDrive placeholder files) are untested.
- WebKit and Firefox results on Linux say nothing about the Windows .bat.

---

## 7. Where things stand (summary table)

| Item | State |
|---|---|
| Root cause of teacher's error | UNPROVEN. Best theory: parser bugs on common inputs (brackets, powers) plus swallowed errors |
| Adjacent brackets / precedence | JS side looks fixed by reading; Python side CLAIMED |
| Power base extraction | Fixed for numbers and plain brackets; new bug for function brackets (READ ONLY) |
| System ERROR / debug panel | CLAIMED, absent from pasted frontend |
| Division by zero text | Not fixed in pasted frontend |
| Exact fractions 1/3, 5/6 | Likely still broken |
| Audit report | Corrupted, cannot be trusted |
| Tests | Python only, ASCII only, fake Ans test, no JS coverage |
| .bat | Rewritten, UNTESTED, layout mismatch risk |
| build_release / verify_release / zip | Not done |
| GitHub | `main` stale, no fix branch or PR visible |

---

## 8. How to solve it (5W1H)

- **What**: Rebuild trust from the ground up on the real local repo. Reproduce the teacher's failure, make one honest comparator, write failing tests first, fix in small commits, prove the result from a clean copy with PATH stripped, then ship a v0.1.1 zip.
- **Who**: opencode does the work on Zaidi's PC. ChatGPT writes the prompts. Claude (or ChatGPT) reviews results. Jules is not needed again; if used, read only audit.
- **Where**: `E:\A.G\casio_mvp` on a new branch, built output in a **new** folder (never inside the delivered v0.1 folder).
- **When**: In this order, because it goes by likelihood and value: (1) safety and snapshot, (2) reproduce on the delivered release, (3) one honest comparator, (4) failing tests, (5) fixes, (6) error handling, (7) launcher and packaging, (8) final proof. Stop at any checkpoint if budget runs low.
- **Why this order**: A fix is worthless if the test harness cannot fail. Fix the measuring stick before fixing the code.
- **How**: Phases below. Each is a separate opencode prompt.

### Phase A: Safety and reality check (small)

1. In `E:\A.G\casio_mvp` run `git status`, `git branch -a`, `git log --oneline -15`, `git remote -v`, `git fetch origin`, then `git log --oneline origin/main -5`. Save the output to `E:\A.G\git_state.txt`.
2. Compare line counts of `frontend.html` and `mvp_server.py` against GitHub `main`. Record whether local history contains `origin/main`.
3. Save the diff of any uncommitted work to `E:\A.G\partial.patch`. Touch no untracked files.
4. Grep the checks from section 8 below and record results.

Checks to run:

```
grep -n "System ERROR\|beyonddd" frontend.html mvp_server.py
grep -n "run_startup_selftest" mvp_server.py
grep -n "√" mvp_server.py engine/*.py
```

### Phase B: Reproduce the teacher's error on the delivered release (highest value)

1. Ask the teacher (via Zaidi) exactly what she pressed. Text answer is the best evidence.
2. On the untouched clean copy `E:\A.G\mentis_release_clean`, test the likely inputs through the keypad on `file://`: `(1+2)(3+4)`, `(2+3)²`, `2(3+4)(5−1)`, `(−2)^2`, `1+sin(30)` then `x²`, and a simple `2+3`.
3. Then run the real Windows route: copy the release to a path with spaces outside OneDrive, for example `E:\A.G\release test\Mentis Test`, strip PATH to `C:\Windows\System32;C:\Windows`, run `python\python.exe -c "import engine"` from the folder and from `C:\`, start through the .bat with `cmd /c start`, capture stdout and stderr and `launcher.log`.
4. Send each case directly to the server evaluate endpoint, record HTTP status and body. Drive the real UI in Playwright (Chromium path above) and record the LCD text plus every console error and failed request.
5. Report the first point of failure with evidence, or say it could not be reproduced and list what was ruled out.

### Phase C: One honest comparator

1. Write one script (for example `E:\A.G\casio_mvp\tools\battery.py`) that runs all 46 cases on paths A, B, C and **overwrites** one results file.
2. Normalise outputs numerically: `5/2`, `2 1/2` and `2.5` are equal. Error cases compare as errors. Case 35 must press `5+5` `=` then `×2` `=` on the keypad (path A and B) and use a real Ans in path C.
3. PASS only if all three paths agree and match expected. Print the table from the script output, never hand edited.
4. Add variant runs for cases 1, 7, 9, 12.

### Phase D: Failing tests first (commit before fixing)

1. Add every battery case plus variants as tests. Python tests call the engine with Unicode and ASCII operators. Browser tests use Playwright against the keypad on `file://` and the served page. Mark current failures as expected fail so the failure is on record.
2. Add these specific regression tests: `1+sin(30)` then `x²` (expect 1.25), `1/3+1/6` (1/2), `1/2+1/3` (5/6), `(3−1)/(9−3)` (1/3), division by zero (Math ERROR, never the joke text), server stopped then `2+2` (System ERROR, never Math ERROR).
3. Run the full suite, record pass, fail and skip counts against the baseline (455 passed, 226 skipped). Make sure the 12 skipped browser maths tests actually run on this PC (Playwright is installed in the hermes venv). Never reduce the existing test count and never weaken an existing test to make something pass. If an existing test encodes old wrong behaviour (for example 8÷2(2+2)=16), show it and the change before editing.

### Phase E: Fixes, one concern per commit

Suggested commits (each message states input, old output, new output):

1. Adjacent brackets in Python parser (and JS if not already).
2. Implicit multiplication precedence, Python and JS identical.
3. `_extractPowerBaseItems`: treat items ending in `(` as openers.
4. Exact fraction acceptance in `exactFractionResult` (10 digit string match).
5. √ handling with balanced brackets.
6. Division by zero shows Math ERROR on `file://`, server and bridge (replace "To infinity and beyonddd" everywhere, including tests that assert it).
7. README: state the Casio implicit multiplication convention.

Python parser and JS evaluator must agree on every case. Prefer one shared fixture file that drives both, not two separate hand tuned fixes.

### Phase F: Error handling

1. Find every catch block, except clause and "Math ERROR" string in `frontend.html`, the bridge code and `mvp_server.py`. For each, note which real exception types can reach it.
2. Math ERROR only for genuine math errors (division by zero, domain, overflow). Anything else (network, import, parse failure on valid input, missing asset) shows System ERROR and logs real message and stack to `console.error`.
3. Hidden debug panel on Ctrl+Shift+D showing the last 20 logged errors.

### Phase G: Launcher and packaging

1. Rewrite the .bat against the **actual release layout** (check the release folder first). Use `cd /d "%~dp0"`, the bundled python by relative path, pick a free port if the default is taken, wait until the port answers before opening the browser, append (not overwrite) the full output of every run to `launcher.log`, and on failure show a plain message telling the user to send `launcher.log`. Avoid `%ERRORLEVEL%` inside parenthesised blocks.
2. Startup self test in `mvp_server.py`: before serving, evaluate `1+1` and case 1 through the real engine. On failure, serve an error page with the real traceback instead of letting the UI show Math ERROR.
3. `build_release` script: builds from a clean git checkout, includes every required asset even if untracked (katex, fonts, qrcode), deletes `__pycache__`, compares its file list against every file the page requests (report missing and extra).
4. `verify_release` script: unzip to a temp path with spaces, strip PATH, run the .bat, run all 46 cases through the UI, fail on any mismatch or console error.
5. Produce `MentisClassWiz_v0.1.1.zip`. Do not touch the delivered v0.1 folder.

### Phase H: Environment matrix

Cases 1 to 10 on path A in Chromium, Firefox, WebKit (mark any missing browser UNTESTED, do not download large browsers without need). Run once from a path with spaces and once from a OneDrive style path. List any OneDrive file that is cloud only.

### Phase I: Final report (one script run, one file)

Write `docs/AUDIT_REPORT.md` once with these sections: A root cause with evidence (or ranked candidates and what was ruled out), B the 46 case table across A, B, C, C every divergence between paths, D fixes as a list of commits, E tests added and final counts versus baseline, F remaining risks ranked by severity, and everything marked UNTESTED.

---

## 9. Git and GitHub plan (decided)

Goal: lots of real commits for the contribution graph, zero casualties for `main`, final merge when proven.

**Decision: work on a new branch, open a pull request, merge to `main` only after the gate below passes, using a normal merge commit (not squash).**

Why this way:

- A new branch means `main` can never be broken by half finished work. This is the "no casualties" rule.
- GitHub's contribution graph counts commits on the **default branch** (and merged PRs). Commits on a side branch do not show on the graph until merged. A normal merge commit keeps every individual commit, so all of them appear. A squash merge would collapse them into one and defeat the purpose. Rebase merge also works but rewrites hashes; a merge commit is the safest.
- The commit author email in `git config user.email` must be a verified email on Zaidi's GitHub account, otherwise commits will not count. Check this first.
- Do not pad the graph with empty or meaningless commits. Small, one concern commits (tests, each fix, docs, scripts) naturally give many commits. Keep messages clear: `fix:`, `test:`, `docs:`, `build:`.

Steps:

1. `git fetch origin`. Check whether local history contains `origin/main` (`git merge-base --is-ancestor origin/main HEAD`). GitHub `main` looked stale compared with the local working version. If local does not contain it, stop and decide (merge `origin/main` into the branch) before pushing, so the PR does not conflict or show unrelated history.
2. Create the branch from the current local state: `git switch -c release_fix_v0_1_1` (if it already exists from an earlier agent, inspect it, do not delete it, and continue on it or create `release_fix_v0_1_1b`).
3. Before anything else, make a safety tag on current `main`: `git tag pre_release_fix_main origin/main` and `git push origin pre_release_fix_main`. This allows instant rollback.
4. Commit small and often. After every few commits: `git push -u origin release_fix_v0_1_1` (first push uses `-u`). Never `--force`, never delete branches.
5. Never commit the bundled `python\` folder, build zips, `__pycache__`, `launcher.log`, or release test folders. Update `.gitignore` for them in its own commit. Large vendored folders (`katex`, fonts) that already exist in the repo stay as they are.
6. Do not touch unrelated untracked files.
7. Open a pull request into `main` titled `Release v0.1.1: audit fixes`, with the report as the description.

**Merge gate (all must be true before merging):**

- Honest comparator shows PASS on all 46 cases on all three paths (script output attached).
- Full pytest run: pass count at or above 501, zero failures, skipped count lower than 226 (browser tests now running), or each remaining skip explained.
- `verify_release` passes from the zip, from a path with spaces, with PATH stripped.
- No "System ERROR" regressions: a stopped server must not show Math ERROR.
- `AUDIT_REPORT.md` regenerated cleanly and consistent with script output.

After the gate: merge with **Create a merge commit**, then tag `v0.1.1` and push the tag. Keep the branch (do not delete it).

---

## 10. Rules to repeat in every opencode prompt

- Work only in `E:\A.G\casio_mvp` and new output folders. Never modify `C:\Users\DELL\OneDrive\Desktop\MentisClassWiz_v0.1`.
- Never claim something passes unless you ran it and saw the result. Mark everything else UNTESTED.
- Audit tasks edit only report files. Fix tasks name one bug, one failing input, one expected output.
- One concern per commit. No force push. No branch deletion. Do not touch unrelated untracked files.
- After every phase append to `E:\A.G\AUDIT_PROGRESS.md`: done, verified, next.
- If budget runs low: stop and report. Do not rush.
- Final answer format: A root cause with evidence, B 46 case table, C path divergences, D commits, E tests and counts versus baseline, F risks and UNTESTED items.