# Codex Handoff v3.2.19

## Release

- Version: `3.2.19-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_19.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_19.py`
- SHA256:
  `228F61FE99D31B3BE8C43111507685F7E63BC33F37D2C126A354E63263EB55CF`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Expanded `realsrc/tests/test_lifecycle_matrix.py` from 8 to 11 deterministic
  scenario rows.
- Fixed the lifecycle matrix harness so its market stub can generate lockable
  `SHORT_CALL` plans with valid market context and realistic short/protection
  quotes.
- Added confirmation/precommit rows:
  - Valid `EXECUTE:<confirm_code>` locks the plan, enters `PLAN_LOCKED`, and
    submits no order when the entry gate is closed.
  - Wrong `EXECUTE` confirmation does not lock and does not submit orders.
  - Unknown same-leg active option order blocks precommit through
    `no_unknown_orders` and submits no Deribit/Binance order.
- Added Chinese-first display mapping for last-command outcomes:
  accepted confirmation, invalid/stale confirmation, duplicate confirmation,
  and ignored non-confirmation command.
- Added Chinese-first display mapping for precommit failed checks, keeping raw
  keys in parentheses for audit.

## Tests Added First

- `test_matrix_008_wrong_confirm_code_does_not_lock_or_order` failed before the
  display fix because the status panel did not say the confirmation code was
  invalid/stale in Chinese.
- `test_matrix_009_unknown_active_option_order_blocks_precommit_in_chinese`
  failed before the display fix because precommit failure showed raw
  `no_unknown_orders` without Chinese operator semantics.

## Verification

- Targeted lifecycle matrix + live-default version tests:
  `17 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `367 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_19.py`
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
