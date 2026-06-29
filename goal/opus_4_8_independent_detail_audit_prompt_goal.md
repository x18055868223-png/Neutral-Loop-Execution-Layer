

## Copy-Paste Prompt For Opus 4.8

You are Opus 4.8 acting as an adversarial, trader-centric live-readiness auditor.

Repository:

`C:\Users\Xu\Documents\Neutral-Loop-Execution-Layer`

Current claimed version:

`3.2.26-manual-gate`

Latest operator-facing FMZ artifact:

`C:\Users\Xu\Documents\Neutral-Loop-Execution-Layer\artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_26.py`

Expected SHA256:

`32E5D0DE17CA822E6715C44A58F3FCF5707AA0C1A9924B876C84568DE1FB18F1`

Current local verdict claimed by the repo:

`SMALL_SIZE_LIVE_TEST_READY`

Your job is to independently audit whether that verdict is justified. Treat all
existing Codex reports as evidence to challenge, not truth to trust. You should
try hard to falsify the verdict.

Do not claim FMZ live readiness from local tests. Local tests prove only local
code and artifact behavior. FMZ live acceptance requires actual FMZ robot logs,
command wiring evidence, and exchange state.

## Non-Negotiable Boundaries

1. FMZ runtime interaction must be only:
   - `执行:<确认码>`
   - `EXECUTE:<确认码>`
   - bare confirmation code

2. Do not reintroduce runtime commands for:
   - take-profit authorization,
   - risk-exit authorization,
   - reject,
   - stop / emergency stop,
   - resume / recovery,
   - revoke authorization,
   - manual hedge commands.

3. `RUN_PROFILE="TEST"` must never place real orders, including:
   - entry orders,
   - exit orders,
   - protection recovery orders,
   - hedge add/open orders,
   - hedge reduce-only orders,
   - orphan hedge cleanup orders,
   - recovery cleanup orders,
   - settlement cleanup orders.

4. `RUN_PROFILE="LIVE"` must still obey action-specific gates:
   - entry requires entry gate and all precommit checks;
   - option exit requires exit gate;
   - hedge add/open requires hedge gate;
   - hedge reduce/unwind may only occur when explicitly risk-reducing and
     policy-approved;
   - emergency reduce-only must not block risk-reducing option or hedge cleanup.

5. No option short risk may be created without:
   - current manual context valid;
   - valid, non-expired confirmation code;
   - locked plan hash / quality code match;
   - S:PM recheck;
   - VRP/context validity recheck where required;
   - projected account budget pass;
   - no unknown/conflicting active orders;
   - execution feasibility recheck;
   - spread/credit gates pass;
   - protection-leg-first invariant preserved.

6. Unknown data must not become zero. Missing exchange reads, missing Greeks,
   missing settlement price, missing order state, missing depth, or missing
   Binance position must become explicit data gaps / fail-closed states.

7. Settlement must not mutate local state when Deribit option-position reads
   fail.

8. Accounting must not double-count entry fills, exit fills, protection
   recovery, settlement, hedge fills, or archive records across repeated loops.

9. `LogStatus` is the trader's primary screen. It must be Chinese-first,
   human-readable, and must not show raw machine codes or internal field names
   as primary operator text in risk-critical states. Raw codes may appear only
   as secondary audit clues.

10. Generated FMZ bundle must not be hand-edited. Editable source is under:
    `realsrc/src/`

## Required First Reads

Read these before forming conclusions:

1. `README.md`
2. `doc/PROJECT_RULES.md`
3. `doc/OPEN_GAPS_TODO.md`
4. `LIFECYCLE_MAP.md`
5. `TEST_SUMMARY.md`
6. `AUDIT_REPORT.md`
7. `UX_STATUS_PANEL_AUDIT.md`
8. `doc/CODEX_HANDOFF_v3_2_26.md`
9. `goal/codex_live_readiness_and_ux_full_prompt_goal.md`
10. `realsrc/tests/test_lifecycle_matrix.py`
11. `realsrc/tests/run_all.py`
12. latest artifact:
    `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_26.py`

Then inspect source areas as needed, especially:

- `realsrc/src/strategy.py`
- `realsrc/src/display.py`
- `realsrc/src/execution.py`
- `realsrc/src/binance_io.py`
- `realsrc/src/cmd_router.py`
- `realsrc/src/gates.py`
- `realsrc/src/position.py`
- `realsrc/src/accounting.py`
- `realsrc/src/recovery.py`
- `realsrc/src/hedge.py`

## Current Local Evidence To Challenge

The repo currently claims:

- lifecycle matrix plus live-default version tests: `47 passed, 0 failed`;
- full local suite: `397 passed, 0 failed`;
- `realsrc\build_bundle.py --check`: passed;
- latest delivery `py_compile`: passed;
- `artifacts\最新交付\` contains exactly one file:
  `spm_manual_gate_execution_fmz_v3_2_26.py`;
- source/generic/versioned/latest bundle SHA256 values match.

Your job is to check whether the tests actually prove the claimed behaviors.
Look for under-specified assertions, overly narrow stubs, false positives,
missing negative cases, local-harness behavior that diverges from FMZ, and
source/artifact drift.

## Existing Lifecycle Matrix To Audit

The current matrix has 41 rows. Verify whether each row truly asserts state,
orders/no-orders, ledger mutation, and `LogStatus` output where relevant.

1. TEST plan phase shows no real trading
2. LIVE plan phase shows action gates
3. TEST TP-qualified position does not exit
4. TEST short-flat protection residual does not recover long leg
5. TEST hedge-ready position does not submit Binance order
6. TEST startup orphan cleanup is dry-run only
7. LIVE valid confirmation locks plan with entry gate closed
8. Wrong confirmation code does not lock or order
9. Unknown same-leg option order blocks precommit
10. LIVE entry protection and short fill freeze snapshot
11. LIVE protection fill but short not filled stays safe
12. LIVE short partial fill enters partial vertical management
13. LIVE protection maker order pending across loops
14. TEST confirmation code locks plan but stays dry
15. LIVE protection cancel late fill counted once
16. LIVE risk-exit ask-depth data gap blocks buyback readably
17. LIVE take-profit buyback fills once within budget
18. LIVE risk-exit depth-sufficient buyback uses taker once
19. LIVE risk-exit ask above cap does not over-spend
20. LIVE risk-exit quote gap blocks buyback readably
21. LIVE risk-exit insufficient depth blocks buyback readably
22. LIVE TP cancel late fill books once
23. LIVE partial TP exit completes next loop without double-counting
24. LIVE hedge pending order blocks duplicate submit readably
25. LIVE hedge missing order ID sets unknown guard
26. LIVE hedge pending terminal fill records history once
27. LIVE V32 SOFT initial hedge add is readable
28. LIVE V32 HARD trigger bypasses add cooldown readably
29. LIVE V32 final-3h SOFT add is suppressed
30. LIVE V32 reduce confirmation is reduce-only and readable
31. Startup orphan with unknown active order requires manual cleanup
32. Startup Binance hedge position read failure blocks readably
33. Startup Deribit option position read failure blocks readably
34. Snapshot exists but state key says `NO_POSITION`
35. LIVE settlement option read gap does not false-settle
36. LIVE short settlement keeps long residual and is idempotent
37. LIVE both legs settle and archive final PnL
38. LIVE closed archive is not duplicated on next loop
39. LIVE missing settlement price archives as DATA_GAP not zero
40. LIVE settlement with perp submits reduce-only cleanup before archive
41. LIVE protection recovery fill is not double-counted

## Detail-Hunting Checklist

Audit these areas specifically. Be skeptical.

### A. Artifact And Source Consistency

- Does `artifacts/最新交付/` contain exactly one file?
- Does the latest artifact contain `STRATEGY_VERSION = "3.2.26-manual-gate"`?
- Do source bundle, generic artifact, versioned artifact, and latest delivery
  share the expected hash?
- Did any test-only change after bundle generation create a source/artifact
  mismatch?
- Are any generated files hand-edited or stale?

### B. FMZ Runtime Interaction Boundary

- Search source and artifact for command parsing paths.
- Prove only confirmation-code commands can be consumed.
- Distinguish config variables/comments like `KILL_NEW_RISK` from runtime
  command branches.
- Check whether `GetCommand()` behavior in FMZ could produce forms not covered
  by tests.
- Confirm command idempotency cannot replay an old code after menu/context
  drift unless the refresh/session key intentionally changes.

### C. TEST Mode No-Order Boundary

- Find every path capable of order writes:
  Deribit buy/sell/cancel, Binance Buy/Sell/CancelOrder, orphan cleanup,
  protection recovery, settlement cleanup, hedge reduce-only.
- Verify effective gates prevent all real submits in TEST, even for
  reduce-only/orphan/cleanup actions.
- Check whether tests inspect all order logs, not only Deribit or only Binance.

### D. Entry / Naked Short Prevention

- Verify protection-leg-first invariant in code and tests.
- Try to find a path where short leg can submit before protection fill is
  confirmed.
- Check partial fill adoption: short quantity must never exceed protection
  quantity.
- Check cancel-late-fill logic for both protection and short orders.
- Check restart with locked entry progress and active orders.
- Check missing order ID / unreadable order state edge cases for Deribit entry.

### E. Precommit / Budget / Context Staleness

- Verify manual context, plan hash, quality code, strategy version, VRP/context,
  current portfolio, and execution feasibility are bound at the right time.
- Try config/version/manual-context drift after menu generation.
- Check candidate can never become lockable with missing hard safety context.
- Verify budget gaps are fail-closed and not converted to zero.

### F. TP / Risk Exit

- Check DTE ordinary TP pause and risk-exit independence.
- Verify risk exit requires price cap and ask depth.
- Check quote missing, depth missing, depth insufficient, ask above cap.
- Check partial exit, cancel-late-fill, repeated loop, and restart after fill.
- Confirm risk-exit blocked path only hedges if hedge action is independently
  executable.

### G. V32 Binance Hedge Controller

- Verify current Binance position is truth; local target is not blindly trusted.
- Check SOFT/HARD/final-3h/reduce behavior.
- HARD should bypass soft cooldown/cost warning where intended.
- Pending active must block duplicate orders.
- Missing order ID must create unknown-submit guard.
- Partial pending stale should record fill and avoid double-count.
- Direction mapping must reduce the actual position, not increase it.
- Binance `GetPosition() == None` must be a data gap, not flat zero.
- Live submit must require order lifecycle methods.
- V32 disabled must hold, not fall back to legacy submit.

### H. Startup Orphan Hedge Cleanup

Automatic cleanup in LIVE is allowed only when all safe evidence exists:

1. no option short risk;
2. Binance perp exists;
3. Binance position read succeeded;
4. Deribit option position read succeeded;
5. active/open order query succeeded;
6. no unknown active orders;
7. action is reduce-only;
8. side reduces existing position;
9. Binance order lifecycle support exists;
10. display clearly says automatic reduce-only cleanup.

Any missing evidence must show manual cleanup and submit no order. Check whether
all evidence combinations are tested.

### I. Settlement Reconciliation

- Option-position read failure must not settle or mutate quantities.
- Grace window must be respected.
- Absent expired short must zero short remaining qty only after safe evidence.
- Absent expired long must zero long remaining qty only after safe evidence.
- Missing settlement price must produce `DATA_GAP`, not zero.
- Both legs settled with no perp may archive.
- Both legs settled with perp must reduce-only cleanup first, no premature
  archive.
- Repeated settlement must not duplicate event history or PnL.

### J. Protection Recovery / Final Accounting

- Entry credit, exit spend, protection recovery, settlement cashflow, and final
  option PnL must be separate and signed.
- Hedge PnL must not be mixed into option PnL unless explicitly labeled combined.
- Protection recovery fill must not double-count across repeated loops.
- Closed archive must contain enough fields for trader reconciliation.
- Archive must not happen while hedge pending or real risk remains.
- Stale recovery state must clear after safe archive.

### K. LogStatus / Chinese Operator UX

For plan phase, verify:

- current phase;
- TEST/LIVE gates;
- manual gate;
- candidate confirmation code;
- lockable/non-lockable reason;
- selected/top candidate details;
- precommit state;
- next action.

For position management, verify:

- lifecycle;
- short/protection qty;
- TP/risk budget;
- risk-exit blocker;
- hedge current/target/pending/reduce-only/orphan state;
- settlement state;
- ledger and PnL status;
- recovery/manual cleanup instruction.

Look for:

- raw machine codes as primary text;
- internal field names as primary column labels;
- `None`, `null`, Python dicts, raw JSON fragments;
- fake zero for missing data;
- placeholder/reserved cost displayed as real;
- plan menu still prominent during position management;
- too much clutter for a real trader to read quickly.

## Severity Standard

Use this severity standard or stricter.

### P0

Any issue that can:

- place a real order in TEST;
- create naked option short risk;
- increase risk when gates forbid it;
- miss required hedge cleanup after confirmed option short risk disappears;
- mutate settlement state on failed reads;
- double-count ledger/PnL;
- archive closed while real risk remains;
- block risk-reducing actions indefinitely without operator-visible manual path;
- display a state that can reasonably cause a trader to take the wrong manual
  action in live risk.

### P1

Any issue that can:

- cause incorrect trader decision;
- produce materially wrong accounting;
- leave stale recovery state;
- hide data gaps;
- falsely display precision;
- require manual state surgery when safe automation evidence is sufficient;
- show raw machine codes/internal fields as primary operator language;
- make plan or position state materially unclear.

### P2

Wording, layout, documentation, or cleanup issues that do not materially change
trading safety, accounting correctness, or operator action.

## What To Produce

Produce a concise but evidence-grounded audit report:

1. Final independent verdict:
   - `NO_GO`
   - `CONDITIONAL_LIVE_TEST_AFTER_FIXES`
   - `SMALL_SIZE_LIVE_TEST_READY`
   - `LIVE_READY_WITH_LIMITS`

2. Findings first, sorted by severity. Each finding must include:
   - severity;
   - exact file and line/function references;
   - why it matters to a real trader;
   - how to reproduce or what test would fail;
   - whether it contradicts the current `SMALL_SIZE_LIVE_TEST_READY` verdict.

3. Coverage gaps:
   - cases not tested;
   - tests that assert too little;
   - local harness assumptions that may diverge from FMZ/exchange behavior.

4. Artifact consistency:
   - latest path;
   - SHA256 check;
   - source/generated/latest drift check.

5. Operator UX review:
   - any unreadable/misleading `LogStatus` rows;
   - raw-code-primary issues;
   - data-gap/fake-zero issues;
   - recommendations.

6. Suggested next tests:
   - write specific test names and scenarios;
   - state whether they should be added before any code change.

7. If no issues are found:
   - say so plainly;
   - still list residual live acceptance risks that local tests cannot prove.

Do not modify code unless explicitly asked. If you believe a P0/P1 fix is
needed, first propose the failing test that should be written.

---

## Goal Objective For Opus 4.8

```text
Independently audit C:\Users\Xu\Documents\Neutral-Loop-Execution-Layer at current
version 3.2.26-manual-gate. Treat the current local verdict
SMALL_SIZE_LIVE_TEST_READY as untrusted and try to falsify it. Inspect source,
latest artifact, tests, reports, lifecycle map, and operator UX. Verify whether
the FMZ Deribit S:PM manual-gate vertical credit spread execution layer is safe
and usable for small-size live testing from a real trader perspective.

The audit must be equal to or stricter than the previous Codex goal: cover manual
decision intake, FMZ boot, startup recovery, plan generation, confirmation-code
lock, precommit, protected entry, partial-fill recovery, position management,
take-profit/risk-exit, V32 Binance hedge control, settlement reconciliation,
orphan hedge cleanup, final accounting, closed archive, restart recovery, and
Chinese LogStatus/operator display.

Prioritize missed edge cases and detail-level defects. Do not trust local green
tests unless you verify they assert the relevant state, order/no-order behavior,
ledger mutation, artifact boundary, and LogStatus output. Do not claim FMZ live
readiness from local evidence. Return findings with severity, file/function
references, reproduction or failing-test suggestions, and whether each finding
changes the final verdict.
```

---

## Quick Verification Commands For The Audit Agent

Run these from:

`C:\Users\Xu\Documents\Neutral-Loop-Execution-Layer`

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_26.py
Get-FileHash -Algorithm SHA256 realsrc\spm_manual_gate_execution_fmz.py, artifacts\spm_manual_gate_execution_fmz.py, artifacts\spm_manual_gate_execution_fmz_v3_2_26.py, artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_26.py
Get-ChildItem -LiteralPath artifacts\最新交付 -File
```

Expected current local evidence:

- full suite: `397 passed, 0 failed`;
- lifecycle matrix plus live-default version tests: `47 passed, 0 failed`;
- build bundle check: syntax compile and smoke pass;
- latest artifact py_compile: pass;
- latest directory: exactly one file;
- all four bundle hashes:
  `32E5D0DE17CA822E6715C44A58F3FCF5707AA0C1A9924B876C84568DE1FB18F1`.

Again: these expected outputs are not proof by themselves. Verify the coverage
and try to break the conclusion.
