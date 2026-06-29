# Codex Handoff v3.2.17

## Release

- Version: `3.2.17-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_17.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_17.py`
- SHA256:
  `6E254F2C8E5B55213E88331920D6A3345FFFD9180C4073D68C623BC5C80ECDC0`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Added `realsrc/tests/test_lifecycle_matrix.py` as the first centralized
  deterministic lifecycle matrix harness.
- The matrix harness runs real `strategy.run_cycle()` loops, captures parsed
  `LogStatus` tables, checks `_G`/ledger state, and records no-order evidence
  from Deribit/Binance stubs.
- Added first rows for:
  - TEST plan phase: no real trading text, no order calls, no active position.
  - LIVE plan phase: action gate status is visible in Chinese, no order calls.
  - Lost local ledger state with `_POSITION_KEY` present: enters
    `POSITION_MANAGE`, hides plan menu, and keeps position tables visible.
- Updated the TEST plan-phase `RUN_PROFILE` row from mixed English wording to:
  `TEST / 测试模式：不会真实下单，全部真实交易门强制关闭`.
- Updated `TEST_SUMMARY.md` with current v3.2.17 local verification evidence.

## Tests Added First

- `test_matrix_001_test_plan_phase_status_says_no_real_trading_and_no_orders`
  failed before implementation because the TEST `RUN_PROFILE` row did not
  contain the Chinese `测试模式` / no-real-order wording.
- `test_matrix_002_live_plan_phase_status_shows_action_gates_in_chinese`
  locks the LIVE plan display expectation around Chinese action-gate evidence.
- `test_matrix_034_snapshot_with_lost_state_enters_position_manage_and_hides_plan_menu`
  locks the restart/state-drift behavior added in v3.2.14 inside the shared
  matrix harness.

## Verification

- Targeted matrix tests reproduced the TEST display gap before implementation.
- Targeted matrix tests passed after implementation.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `359 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_17.py`
  -> passed.

## Remaining Goal Work

- Expand `realsrc/tests/test_lifecycle_matrix.py` to the full 40-row scenario
  matrix required by `goal/codex_live_readiness_and_ux_full_prompt_goal.md`.
- Highest next rows: protected-entry partial fill/restart, TP/risk-exit blocked
  by depth, hedge pending/missing-order-id idempotency, settlement false-read,
  and negative startup orphan evidence cases.
- Produce `AUDIT_REPORT.md` and `UX_STATUS_PANEL_AUDIT.md`.
- Add the final Go/No-Go section to `TEST_SUMMARY.md` only after the matrix and
  report checks are complete.
