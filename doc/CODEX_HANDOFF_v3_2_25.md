# Codex Handoff v3.2.25

## Release

- Version: `3.2.25-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_25.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_25.py`
- SHA256:
  `4A773FBADF69E33F3E9147B63E1D0F3E67443A11D1709A7640C91340927242A8`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Expanded `realsrc/tests/test_lifecycle_matrix.py` with rows 027-030.
- Added row 027: LIVE V32 SOFT initial trigger submits one Binance buy hedge
  order with soft cross bps and displays a Chinese SOFT reason.
- Added row 028: LIVE V32 HARD trigger submits one Binance buy hedge order
  even while add cooldown is active, using hard cross bps and displaying a
  Chinese HARD reason.
- Added row 029: LIVE V32 final-3h SOFT-add suppression holds with no Binance
  order and displays a Chinese suppression reason.
- Added row 030: LIVE V32 reduce-confirmed branch submits one Binance sell
  reduce-only unwind and displays a Chinese reduce reason.
- Added Chinese-first display mappings for `SOFT_TRIGGER_INITIAL`,
  `HARD_TRIGGER_EMERGENCY`, `FINAL3H_SOFT_ADD_SUPPRESSED`, and
  `REDUCE_CONFIRMED`.

## Tests Added First

- Rows 027-030 were added before production edits.
- All four rows failed initially at `disp_reason_cn(raw_reason) != raw_reason`,
  proving the status panel still exposed these V32 policy reasons as raw
  machine codes.
- The production fix was limited to `display.REASON_CN` mappings. V32 hedge
  order sizing, pending reconciliation, gate behavior, and command boundaries
  were not changed.

## Verification

- Targeted lifecycle matrix + live-default version tests:
  `40 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `390 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_25.py`
  -> passed.
- `artifacts/最新交付/` contains only
  `spm_manual_gate_execution_fmz_v3_2_25.py` after removing py_compile cache.

## Remaining Goal Work

- Expand `realsrc/tests/test_lifecycle_matrix.py` from the current 34 numbered
  rows to the full 40-row scenario matrix required by
  `goal/codex_live_readiness_and_ux_full_prompt_goal.md`.
- Highest next rows: settlement false-read/idempotency, archive/closed-history
  schema, final accounting display, hedge crash-speed/reverse/stale-partial
  display variants, and recovery negative evidence.
- Produce `AUDIT_REPORT.md` and `UX_STATUS_PANEL_AUDIT.md`.
- Add the final Go/No-Go section to `TEST_SUMMARY.md` only after the matrix and
  report checks are complete.
