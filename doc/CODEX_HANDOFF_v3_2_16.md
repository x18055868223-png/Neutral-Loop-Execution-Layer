# Codex Handoff v3.2.16

## Release

- Version: `3.2.16-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_16.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_16.py`
- SHA256:
  `0B700D99849F0D3B23C09B47CD944D33FE5CC9479FF95161F388DC17EE0FCD0B`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Added root `LIFECYCLE_MAP.md` as the required first-step lifecycle map:
  stages, persisted keys, exchange reads/writes, display mapping, current tests,
  and missing coverage.
- Added startup orphan Binance hedge cleanup decisioning:
  clean no-option-risk evidence plus Binance perp exposure, clean open-order
  reads, and Binance order lifecycle support now marks cleanup as
  `AUTO_REDUCE_ONLY`.
- In `RUN_PROFILE=LIVE`, `run_cycle()` submits one Binance reduce-only cleanup
  order for that safe-evidence startup orphan state.
- In `RUN_PROFILE=TEST`, the same safe-evidence path returns
  `BINANCE_HEDGE_DRYRUN` and does not call Binance `Buy`/`Sell`.
- Missing Binance `GetOrder`/`CancelOrder` support remains
  `MANUAL_CLEANUP_ONLY` and submits no order.
- `LogStatus` now has Chinese orphan-cleanup phase wording and a
  `孤儿对冲清理` row that distinguishes automatic reduce-only cleanup, TEST
  dry-run, blocked auto cleanup, and manual reduce-only cleanup.

## Tests Added First

- `test_startup_orphan_hedge_clean_evidence_auto_reduces_in_live`
  failed before implementation because startup orphan verdicts had no
  `auto_cleanup_allowed` field and `run_cycle()` always went manual-only.
- `test_startup_orphan_hedge_same_evidence_in_test_is_dry_only`
  failed for the same reason, proving the TEST dry-run path was absent.
- `test_startup_orphan_hedge_without_order_lifecycle_stays_manual_no_order`
  locks the negative evidence branch: lifecycle support missing means manual
  cleanup and no Binance order.

## Verification

- Targeted red tests reproduced the missing auto-cleanup path before
  implementation.
- Targeted tests passed after implementation.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `356 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> syntax compile passed; bundle smoke passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_16.py`
  -> passed.

## Remaining Goal Work

- Build the centralized deterministic lifecycle scenario harness/matrix required
  by `goal/codex_live_readiness_and_ux_full_prompt_goal.md`.
- Produce `AUDIT_REPORT.md`, `UX_STATUS_PANEL_AUDIT.md`, and
  `TEST_SUMMARY.md`.
- Add matrix coverage for negative orphan evidence cases beyond lifecycle
  support, including Binance read failure, Deribit option read failure, unknown
  active orders, and repeated pending cleanup display.
