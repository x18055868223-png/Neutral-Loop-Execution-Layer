# Codex Handoff v3.2.18

## Release

- Version: `3.2.18-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_18.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_18.py`
- SHA256:
  `799F57C36DFAEE7C8D517EE73C7C80BFF82BCC8CAF59D21B021DDA2760C581E6`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Expanded `realsrc/tests/test_lifecycle_matrix.py` from 3 to 8 deterministic
  scenario rows.
- Added configurable Deribit/Binance stubs inside the lifecycle matrix harness:
  persisted `_G`, parsed `LogStatus`, Deribit private order recording, Binance
  order recording, option-position/open-order responses, ticker overrides, and
  repeated real `strategy.run_cycle()` loops.
- Added TEST no-order matrix rows for:
  - TP-qualified position management: no Deribit exit order.
  - short-flat/protection residual: no Deribit protection recovery order.
  - hedge-ready position: no Binance hedge order.
  - startup orphan cleanup: dry-run only, no Binance order.
- Added a startup orphan negative-evidence row:
  no option short risk plus Binance perp plus unknown active order now enters
  `ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED`, displays manual only-reduce cleanup,
  and submits no order.
- Updated `startup_recovery_check()` classification so this unknown-active-order
  orphan case is no longer surfaced as a generic `RECOVERY_BLOCKED`. It remains
  fail-closed and blocks new opening.

## Tests Added First

- `test_matrix_031_unknown_active_order_forces_manual_orphan_cleanup_no_order`
  failed before implementation because startup recovery returned
  `RECOVERY_BLOCKED` instead of the trader-facing orphan manual-cleanup phase.
- The TEST no-order matrix rows were added around existing intended behavior and
  assert state, no-order evidence, and Chinese `LogStatus` text together.

## Verification

- Targeted lifecycle matrix + live-default version tests:
  `14 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `364 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_18.py`
  -> passed.

## Remaining Goal Work

- Expand `realsrc/tests/test_lifecycle_matrix.py` to the full 40-row scenario
  matrix required by `goal/codex_live_readiness_and_ux_full_prompt_goal.md`.
- Highest next rows: protected-entry partial fill/restart, TP/risk-exit blocked
  by depth, hedge pending/missing-order-id idempotency, settlement false-read,
  Binance read failure, Deribit option read failure, and closed archive cleanup.
- Produce `AUDIT_REPORT.md` and `UX_STATUS_PANEL_AUDIT.md`.
- Add the final Go/No-Go section to `TEST_SUMMARY.md` only after the matrix and
  report checks are complete.
