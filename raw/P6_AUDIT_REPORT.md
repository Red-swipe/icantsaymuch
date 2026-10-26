# P6 Audit — Swallowed Errors on the Real Calculator Path

Date: 2026-10-15
Branch: `Release_fix_v0.12`
Status: **AUDIT ONLY — no application, test, or configuration file was modified.**

---

## 1. Git baseline (verified)

| Item | Value |
|---|---|
| Starting HEAD | `d62add87b82a6f99a1c53504b41bbf1b793fc160` (`d62add8`) — matches expected |
| Branch | `Release_fix_v0.12` — unchanged |
| Staged changes | none |
| Unstaged changes | `engine/parser.py` only (pre-existing) |
| Untracked | `.codex_test_tmp/`, `AUDIT_PROGRESS.md`, `CLAUDE_HANDOVER.md`, `audit.md`, `audit/evidence/`, `final_audit.md`, `graphify-out/`, `raw/context.md`, `raw/september_handover.md` |
| Phase F commits present | `d62add8`, `8090303` |

### Mandatory parser preservation

| | SHA-256 |
|---|---|
| `engine/parser.py` **file** | `3E0BC1387D8EA9C8AA46B824F1ADAF9A2588A80DBB3DF46F3331D29F8EAF10D7` |
| `engine/parser.py` **git diff** | `F1F1E216221F9C59A96B52746E8F11F200B2C53102782FE0BDA8BD6FFE282A1A` |

Note: the previously reported prefix `F1F1E216` refers to the **diff** hash, not the file
hash. Both recorded to prevent future ambiguity. Both unchanged after the
investigation. The file was never staged, edited, or committed.

## 2. Context consulted

`audit/evidence/phase-f-20261015/context_repo/raw/context.md` (419 lines, local
clone; remote reachable). Sections read: **0, 2, 3, 6, 8, 9, 10** (with 6/P6 and
6/P10 read in full). Section 2 confirms the teacher's exact expression is
**unknown** and that "nobody has found the root cause."

Context section 6/P6 states the mechanism as a *theory* and flags that a prior
pasted `frontend.html` contained no `System ERROR` string. **That is stale.**
The current local `frontend.html` does contain `System ERROR`
(`frontend.html:5089`) — but only on one of two paths, which is precisely the
defect.

---

## 3. Error-flow map (source-verified)

Real path: keypad → `getExpr()` → `prepareExpressionForEvaluation()` →
`POST /api/key {key:"equals", expression}` → server → response → LCD.

`evaluate()` contains **two structurally different error strategies**:

| # | Location | Strategy | Outcome for non-math failure |
|---|---|---|---|
| 1 | `frontend.html:7012` — `FILE_MODE` branch | `reportEvaluationFailure(e,'equals/file')` | `System ERROR` |
| 2 | `frontend.html:7037` — server branch outer catch | `catch(e) { showMathError(); }` | **`Math ERROR`** |

`showMathError` (`frontend.html:5072`):

```js
function showMathError(msg) {
  appState.error = msg || 'Math ERROR';
```

The server-path catch passes **no argument**, so `e` is **discarded entirely**:
no message, no stack, no `console.error`, no debug panel.

`reportEvaluationFailure` (`frontend.html:5079`) is the classifier that *does*
distinguish — it whitelists `Math ERROR` / `DIV_ZERO` / `RangeError` as
mathematical, and returns `System ERROR` with a logged detail string otherwise.
It is **not called on the server path**.

Additional boundary (`frontend.html:7029`): on `!r.ok` the code builds
`throw new Error(msg)` from the server's own error text — then the outer catch
throws that information away. The server's real diagnostic is discarded at the
last step.

---

## 4. Classification matrix — all cases EXECUTED

Driven through the real keypad against the real server, failures injected by
Playwright request interception (network layer only; no file modified).
Evidence: `p6_error_matrix.json`, `p6_error_matrix.txt`.

| Class | Case | Injected | LCD shows | `appState.error` | Console | Verdict |
|---|---|---|---|---|---|---|
| math | `1÷0` | — | `Math ERROR` | `Math ERROR` | resource 4xx | **correct** |
| math | `(5+3)/(2−2)` | — | `Math ERROR` | `Math ERROR` | resource 4xx | **correct** |
| math | `√(−1)` | — | `Math ERROR` | `Math ERROR` | resource 4xx | **correct** |
| math | `2+` incomplete | — | `Math ERROR` | `Math ERROR` | resource 4xx | **correct** |
| math | `2+3` control | — | `5` | `null` | — | **correct** |
| **non-math** | HTTP 500 + `{"error":"internal boom"}` | 500 JSON | **`Math ERROR`** | `Math ERROR` | resource 500 only | **MISCLASSIFIED** |
| **non-math** | HTTP 500, no `error`/`display` field | 500 JSON | **`Math ERROR`** | `Math ERROR` | resource 500 only | **MISCLASSIFIED** |
| **non-math** | HTTP 200, body not JSON | 200 `<<<not json>>>` | **`Math ERROR`** | `Math ERROR` | silent | **MISCLASSIFIED** |
| **non-math** | HTTP 200, no `result` and no `error` | 200 JSON | *(no error shown)* | `null` | silent | **SILENT NO-OP** |
| **non-math** | HTTP 200, `result:null, error:null` | 200 JSON | *(no error shown)* | `null` | silent | **SILENT NO-OP** |
| **non-math** | request aborted | `route.abort` | **`Math ERROR`** | `Math ERROR` | `net::ERR_CONNECTION_REFUSED` | **MISCLASSIFIED** |

No case produced `System ERROR` on the server path.

### Two distinct defects, not one

1. **Misclassification (4/6 non-math cases).** Network failure, HTTP 5xx, and
   malformed JSON all render `Math ERROR` — indistinguishable from a genuine
   divide-by-zero. Root cause: `catch(e) { showMathError(); }` at
   `frontend.html:7037`.
2. **Silent no-op (2/6).** A 200 response with neither `result` nor `error`
   matches no branch at `frontend.html:7031-7035`. The LCD keeps the old
   expression with a blank result and the user gets **no feedback at all** —
   a distinct and arguably worse failure than misclassification.

---

## 5. Findings

### CONFIRMED MECHANISM

A controlled **non-mathematical** failure — server 500, malformed JSON, and
network refusal — reproducibly reaches `frontend.html:7037` and is displayed as
`Math ERROR`, byte-identical to genuine mathematical errors. Verified on the
real browser path via the real keypad. The mechanism is **not hypothetical**;
it is the only error strategy the server path has.

### INCIDENT-COMPATIBLE, NOT INCIDENT-CAUSE-CONFIRMED

The mechanism is real and the symptom matches exactly (`Math ERROR` from a
non-maths cause). However the teacher's trigger is unknown, so this **cannot**
be labelled the incident's cause. Note the teacher's environment (bundled
Python via `.bat`, under OneDrive) is exactly where a transport-level failure
— network, asset, subprocess — is most plausible, which raises the mechanism's
plausibility without proving it.

### Is the display a defect?

**Yes, for the server path**, because the project already defines a different,
more precise contract 25 lines above it: `reportEvaluationFailure` returns
`System ERROR` for non-mathematical failures, writes
`console.error('[Mentis System ERROR]', detail)`, and populates `#debugPanel`.
The server path bypasses that existing contract. The behaviour is therefore
**internally inconsistent**, not an unspecified interface choice — the
correction is to route the server catch through the classifier that already
exists, not to invent a new message.

### Diagnostic survival

For all four misclassified cases the original diagnostic was **lost**. Only the
browser's generic resource-load line survives, which identifies neither the
status nor the cause. `#debugPanel` stayed empty in every case.

---

## 6. Adjacent defects kept separate

| Issue | Status in this phase |
|---|---|
| Gate A `8÷2(2+2)` | Not touched. Noted only: `1÷0` and `(5+3)/(2−2)` pass as `Math ERROR`, so Gate A is unrelated to P6. |
| Uncommitted `engine/parser.py` | Preserved byte-for-byte; not resolved or committed. |
| Shipped v0.1 stale buffer | Not re-tested, not re-claimed. v0.1 remains unmodified. |
| Square-root | Not reopened. No new contradictory evidence. |
| Server per-key emulation | Not exercised. Not implicated in the UI path. |
| Context P7 (`To infinity and beyonddd`) | Local branch shows `Math ERROR` for both div-zero cases, satisfying the case-31 expectation. The joke string is **not** reached on the server path here — consistent with the outer catch swallowing it. Shipped v0.1 behaviour not re-verified in this phase. |

## 7. Test-suite discipline

**UNTESTED in this phase.** The full suite was not run. Rationale: P6 changed no
code and added no test files, so the reported Phase F baseline
(`4 failed / 811 passed / 1 xfailed / 196 subtests`) is unaffected by
construction, and re-running it would not inform the P6 question. The browser
experiments above are the evidence for P6. Re-running remains required before
any P6 fix is accepted.

No test expectations were changed, disabled, or made to appear greener.

## 8. Shipped package

Not executed and not modified in this phase. Fingerprint not re-taken, because
P6 experiments ran exclusively against the local working copy. No claim is made
about v0.1's error handling; that is **UNTESTED**.

## 9. Scope compliance

- Files created: this directory only (`P6_AUDIT_REPORT.md`,
  `p6_inject_errors.py`, `p6_error_matrix.json`, `p6_error_matrix.txt`).
- File modified: `E:\A.G\AUDIT_PROGRESS.md` (checkpoint, appended only).
- `p6_inject_errors.py` is **disposable instrumentation** for this audit, not a
  permanent test fixture. It is not wired into any suite.
- No application code, test, configuration, launcher, or release asset touched.
- No `reset`, `clean`, `stash`, `rebase`, `restore`, merge, cherry-pick, push, or
  remote ref change.
- Shipped package untouched.

## 10. Remaining unknowns

1. The teacher's actual expression and launcher route remain unknown —
   **UNTESTED**. The `.bat` + bundled-interpreter path was not exercised.
2. Which non-math failure actually occurred in class — **UNTESTED**.
3. Whether `file://` correctly shows `System ERROR`: source at
   `frontend.html:7012` indicates yes, but this was **inferred from source, not
   executed** in a browser in this phase.
4. Behaviour of the 19 `showMathError` call sites in matrix/vector/calc/solve/
   conversion paths — not exercised; several likely share defect 1.
5. Full-suite regression baseline after any future fix.

## 11. Recommendation

A **separate, narrowly scoped fix prompt is justified.** Its scope should be
exactly: route the server-path catch in `evaluate()` through the existing
`reportEvaluationFailure` classifier, and handle the 200-with-no-`result`
response explicitly instead of silently. It must **not** touch Gate A,
`engine/parser.py`, the per-key emulation, or any shipped asset. First failing
tests should be committed before the fix, per context section 8 Phase D.
