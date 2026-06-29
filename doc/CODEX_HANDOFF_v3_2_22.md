# Codex Handoff v3.2.22

## Release

- Version: `3.2.22-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_22.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_22.py`
- SHA256:
  `54EE383E2C7C6776547AF03224DC22A3F87A264399D6903E93FAF7B551AED988`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Expanded `realsrc/tests/test_lifecycle_matrix.py` from 18 to 23
  deterministic scenario rows.
- Added matrix row 017: LIVE TP-qualified position submits one Deribit maker
  buyback, applies the fill, flattens the short leg into
  `S_SHORT_FLAT_LONG_RESIDUAL`, and does not double count or rebuy on a
  repeated loop.
- Added matrix row 018: LIVE hedge-ready risk exit with ask <= cap and
  sufficient depth submits one Deribit taker buyback labeled `risk_exit`,
  applies the fill, and remains idempotent on a repeated loop.
- Added matrix row 019: LIVE hedge-ready risk exit with ask above the budget cap
  submits no buyback or Binance hedge fallback and displays
  `卖一高于预算上限`.
- Added matrix rows 032-033: startup recovery read failures for Binance hedge
  position and Deribit option position block recovery with no orders and show
  Chinese manual-check guidance in `LogStatus`.
- Recovery-blocked `LogStatus` now carries `recovery_reasons` from
  `startup_recovery_check()` and maps `HEDGE_POSITION_QUERY_FAILED` /
  `OPTION_POSITION_QUERY_FAILED` to trader-readable Chinese text while keeping
  the raw reason codes for audit.

## Tests Added First

- Rows 017-019 were added before production edits and passed as coverage of the
  existing TP/risk-exit lifecycle behavior.
- Rows 032-033 were added before production edits and failed initially because
  startup recovery showed only a generic recovery-blocked line instead of the
  concrete Binance/Deribit read-failure reason.
- The production fix was limited to recovery reason propagation and display
  mapping. Confirmation-code-only interaction, order gates, and runtime command
  boundaries were not changed.

## Verification

- Targeted lifecycle matrix + live-default version tests:
  `29 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `379 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_22.py`
  -> passed.
- `artifacts/最新交付/` contains only
  `spm_manual_gate_execution_fmz_v3_2_22.py` after removing py_compile cache.

## Remaining Goal Work

- Expand `realsrc/tests/test_lifecycle_matrix.py` to the full 40-row scenario
  matrix required by `goal/codex_live_readiness_and_ux_full_prompt_goal.md`.
- Highest next rows: risk-exit insufficient depth, risk-exit quote gap,
  TP/risk-exit late fill, hedge pending/missing-order-id idempotency,
  settlement false-read, archive idempotency, and closed-history schema checks.
- Produce `AUDIT_REPORT.md` and `UX_STATUS_PANEL_AUDIT.md`.
- Add the final Go/No-Go section to `TEST_SUMMARY.md` only after the matrix and
  report checks are complete.
