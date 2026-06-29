# Codex Handoff v3.2.21

## Release

- Version: `3.2.21-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_21.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_21.py`
- SHA256:
  `CD9DA7DA307CFA06031F27E7DEEE6F39D13C04F79467769356A9254571A3DFD0`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Expanded `realsrc/tests/test_lifecycle_matrix.py` from 15 to 18
  deterministic scenario rows.
- Added matrix row 014: TEST profile accepts a valid bare confirmation code for
  dry validation, keeps `_POSITION_KEY` empty, keeps ledger no-position, and
  submits no Deribit/Binance order.
- Added matrix row 015: a persistent protection maker order that fills only
  after cancel is counted once in locked entry progress; no duplicate
  protection fill is recorded and no snapshot is created without short fill.
- Added matrix row 016: LIVE risk-exit with missing best-ask depth remains
  fail-closed, submits no Deribit buyback order, and displays a trader-readable
  reason.
- Added Chinese-first risk-exit reason mapping for `NO_RISK_EXIT_BUDGET`,
  `EXIT_QUOTE_DATA_GAP`, `EXIT_PRICE_ABOVE_CAP`, `EXIT_DEPTH_DATA_GAP`, and
  `EXIT_DEPTH_INSUFFICIENT`.
- Updated `LogStatus` risk-exit budget/盘口 rows and low-frequency `Log`
  summaries to show the Chinese reason first while preserving the internal
  reason code in structured context.

## Tests Added First

- Rows 014-016 were added before production changes.
- Row 016 initially failed because `LogStatus` showed
  `不可执行:EXIT_DEPTH_DATA_GAP` and the risk-exit盘口 note exposed the raw code
  instead of `卖一深度缺口`.
- The production fix was limited to reason rendering; order gates, risk-exit
  budget logic, and confirmation-code-only interaction were not changed.

## Verification

- Targeted lifecycle matrix + live-default version tests:
  `24 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `374 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_21.py`
  -> passed.
- `artifacts/最新交付/` contains only
  `spm_manual_gate_execution_fmz_v3_2_21.py` after removing py_compile cache.

## Remaining Goal Work

- Expand `realsrc/tests/test_lifecycle_matrix.py` to the full 40-row scenario
  matrix required by `goal/codex_live_readiness_and_ux_full_prompt_goal.md`.
- Highest next rows: risk-exit insufficient depth, risk-exit quote gap,
  TP/risk exit late fill, hedge pending/missing-order-id idempotency, Binance
  position read failure, Deribit option read failure, settlement false-read and
  archive idempotency.
- Produce `AUDIT_REPORT.md` and `UX_STATUS_PANEL_AUDIT.md`.
- Add the final Go/No-Go section to `TEST_SUMMARY.md` only after the matrix and
  report checks are complete.
