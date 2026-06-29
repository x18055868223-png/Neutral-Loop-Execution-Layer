# Codex Handoff v3.2.24

## Release

- Version: `3.2.24-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_24.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_24.py`
- SHA256:
  `FAD203040A4FC498F323724D984F42C0E841EE95DC6DB1E890192055EF214B25`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Expanded `realsrc/tests/test_lifecycle_matrix.py` from 27 to 30
  deterministic scenario rows.
- Added matrix row 024: risk-exit fallback submits one Binance hedge order,
  records a pending V32 order, and the next loop sees `PENDING_ACTIVE` with no
  duplicate Binance submit.
- Added matrix row 025: a Binance submit response without an order ID records
  `BINANCE_ORDER_ID_MISSING`, sets the unknown-submit guard, and prevents an
  immediate duplicate submit on the next loop.
- Added matrix row 026: a terminal pending hedge fill clears pending state,
  writes exactly one `hedge_execution_history` item, and a repeated loop does
  not duplicate the fill or submit a second hedge order.
- Added Chinese-first display mappings for V32 hedge pending/unknown-submit
  states, and changed the hedge summary/controller rows to render mapped
  Chinese reasons instead of raw-code-primary policy reasons.

## Tests Added First

- Rows 024-026 were added before production edits.
- Row 026 passed immediately as existing hedge pending-fill behavior.
- Rows 024-025 failed initially because `PENDING_ACTIVE` and
  `SUBMIT_UNKNOWN_RECENT` had no Chinese display mapping and were exposed as
  raw policy reasons in `LogStatus`.
- The production fix was limited to display mapping/rendering. V32 hedge order
  submission, pending reconciliation, unknown-submit guard, and runtime command
  boundaries were not changed.

## Verification

- Targeted lifecycle matrix + live-default version tests:
  `36 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `386 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_24.py`
  -> passed.
- `artifacts/最新交付/` contains only
  `spm_manual_gate_execution_fmz_v3_2_24.py` after removing py_compile cache.

## Remaining Goal Work

- Expand `realsrc/tests/test_lifecycle_matrix.py` to the full 40-row scenario
  matrix required by `goal/codex_live_readiness_and_ux_full_prompt_goal.md`.
- Highest next rows: settlement false-read, settlement idempotency, archive
  idempotency, closed-history schema checks, TP DTE gate, and hedge
  SOFT/final-3h/reduce-unwind display variants.
- Produce `AUDIT_REPORT.md` and `UX_STATUS_PANEL_AUDIT.md`.
- Add the final Go/No-Go section to `TEST_SUMMARY.md` only after the matrix and
  report checks are complete.
