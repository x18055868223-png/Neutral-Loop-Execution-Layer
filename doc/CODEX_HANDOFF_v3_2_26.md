# Codex Handoff v3.2.26

## Release

- Version: `3.2.26-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_26.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_26.py`
- SHA256:
  `32E5D0DE17CA822E6715C44A58F3FCF5707AA0C1A9924B876C84568DE1FB18F1`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Completed `realsrc/tests/test_lifecycle_matrix.py` through rows 035-040 in
  the v3.2.26 artifact pass, bringing the centralized lifecycle matrix to the
  required 40 numbered rows. The final audit package later added row 041 as
  test-only coverage for protection recovery no-double-count behavior.
- Added row 035: expired settlement with Deribit option-position read failure
  does not false-settle, archive, or submit orders.
- Added row 036: absent expired short plus present long records
  `SHORT_SETTLED`, keeps the long residual managed, and is idempotent.
- Added row 037: absent expired short and long records `BOTH_LEGS_SETTLED`,
  computes final option PnL, and archives one closed record.
- Added row 038: a repeated loop after closed archive does not duplicate the
  closed history record.
- Added row 039: missing settlement price archives as `DATA_GAP` with final
  option PnL kept `None`, not fake `$0.00`.
- Added row 040: settlement with residual Binance perp submits one reduce-only
  orphan hedge cleanup and does not archive before the perp is flat.
- `strategy._build_ledger_detail()` now exposes `settlement_state`.
- The `POSITION_MANAGE` ledger table now renders settlement, protection
  recovery, option realized PnL, and final option PnL as Chinese-first operator
  rows, without `status=...` or English labels as the primary read-screen text.
- `ORPHAN_HEDGE_UNWIND` now has a Chinese display mapping.

## Tests Added First

- Rows 035-040 and the settlement display assertion were added before the
  production fix.
- Initial targeted RED evidence was 1 passed / 6 failed: row 038 already passed
  from existing archive idempotency, while the new display/ledger assertions
  failed on English settlement rows and missing `settlement_state`.
- After tightening the helper title lookup, the relevant RED set was 0 passed /
  6 failed for rows 035, 036, 037, 039, 040 and the display settlement test.
- Production changes were limited to ledger-detail exposure and display text.
  Settlement mutation, archive, hedge submit, and command-routing behavior were
  not loosened.

## Verification

- Targeted rows 035-040 + settlement display:
  `7 passed, 0 failed`
- Targeted lifecycle matrix + live-default version tests:
  `47 passed, 0 failed` after the final audit-package row 041.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `397 passed, 0 failed` after the final audit-package row 041.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_26.py`
  -> passed.
- `artifacts/最新交付/` contains only
  `spm_manual_gate_execution_fmz_v3_2_26.py` after removing py_compile cache.

## Remaining Goal Work

Superseded by the final v3.2.26 audit package:

- `AUDIT_REPORT.md` produced with final local verdict
  `SMALL_SIZE_LIVE_TEST_READY`.
- `UX_STATUS_PANEL_AUDIT.md` produced with Chinese-first display audit and
  operator UX runbook.
- `TEST_SUMMARY.md` now contains the final local Go/No-Go section.
- `realsrc/tests/test_lifecycle_matrix.py` now has 41 numbered rows, including
  row 041 for repeated-loop protection recovery no-double-count evidence.
- Full local suite after row 041: `397 passed, 0 failed`.
- Lifecycle matrix plus live-default version tests after row 041:
  `47 passed, 0 failed`.
- FMZ runtime interaction boundary remains confirmation-code-only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or bare confirmation code.
- Latest operator artifact remains v3.2.26; no new FMZ delivery was produced by
  the final report/test-only package.
