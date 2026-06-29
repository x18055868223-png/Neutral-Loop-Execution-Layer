# Codex Handoff v3.2.23

## Release

- Version: `3.2.23-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_23.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_23.py`
- SHA256:
  `9D9DA5FEFB52E541D00C617E47D5C1D8C06D3EDD078EE061D951279D1EC34CCB`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Expanded `realsrc/tests/test_lifecycle_matrix.py` from 23 to 27
  deterministic scenario rows.
- Added matrix row 020: LIVE hedge-ready risk exit with a quote gap submits no
  Deribit buyback or Binance hedge when hedge is not executable, preserves
  `EXIT_QUOTE_DATA_GAP`, and displays a Chinese risk-exit blocker.
- Added matrix row 021: LIVE hedge-ready risk exit with insufficient ask depth
  submits no Deribit buyback or Binance hedge when hedge is not executable,
  preserves `EXIT_DEPTH_INSUFFICIENT`, and displays a Chinese blocker.
- Added matrix row 022: LIVE TP maker buyback captures a fill that appears only
  after cancel, books it once, and the next loop uses only the residual short
  quantity.
- Added matrix row 023: after a partial TP exit, the next run-cycle buys back
  only the remaining short quantity, records a second fill, moves the ledger to
  `S_SHORT_FLAT_LONG_RESIDUAL`, and does not duplicate the first fill.
- No production behavior change was required beyond bumping
  `STRATEGY_VERSION` and regenerating the FMZ bundle.

## Tests Added First

- Rows 020-023 were added before any production edits.
- Rows 020-021 passed immediately as coverage of existing fail-closed
  risk-exit behavior and Chinese reason rendering.
- Rows 022-023 initially failed because the tests used exact float equality and
  retained a mutable snapshot reference across loops. Diagnostic evidence showed
  the implementation was already correct, so only the test assertions were
  adjusted to use quantity tolerance and scalar snapshots.

## Verification

- Targeted lifecycle matrix + live-default version tests:
  `33 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `383 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_23.py`
  -> passed.
- `artifacts/最新交付/` contains only
  `spm_manual_gate_execution_fmz_v3_2_23.py` after removing py_compile cache.

## Remaining Goal Work

- Expand `realsrc/tests/test_lifecycle_matrix.py` to the full 40-row scenario
  matrix required by `goal/codex_live_readiness_and_ux_full_prompt_goal.md`.
- Highest next rows: hedge pending/missing-order-id idempotency, settlement
  false-read, archive idempotency, closed-history schema checks, TP DTE gate,
  and risk-exit hedge-fallback behavior.
- Produce `AUDIT_REPORT.md` and `UX_STATUS_PANEL_AUDIT.md`.
- Add the final Go/No-Go section to `TEST_SUMMARY.md` only after the matrix and
  report checks are complete.
