# Codex Handoff v3.2.20

## Release

- Version: `3.2.20-manual-gate`
- Source: `realsrc/src/`
- Bundle source: `realsrc/spm_manual_gate_execution_fmz.py`
- Versioned archive: `artifacts/spm_manual_gate_execution_fmz_v3_2_20.py`
- Latest delivery:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_20.py`
- SHA256:
  `C08109AEAE51B8A6C1BBCD5A00B75B915919AE9A892153CE08789D5B7DCD4FAF`
- Boundary: local verification only. This is not FMZ live proof.

## Changes

- Expanded `realsrc/tests/test_lifecycle_matrix.py` from 11 to 15
  deterministic scenario rows.
- Added scripted Deribit order lifecycle support to the lifecycle harness so
  run-cycle tests can assert multi-loop entry fills, open orders, cancels,
  `_G` state, ledger state, order logs, and parsed `LogStatus`.
- Added protected-entry matrix rows:
  - full protection+short fill freezes a position snapshot and enters
    `POSITION_MANAGE`;
  - protection fill with no short fill keeps the locked campaign and creates no
    short option risk;
  - short partial fill creates a `PARTIAL_VERTICAL` managed snapshot;
  - pending protection maker order persists across loops without duplicate
    order placement.
- Fixed immediate post-entry display so the first cycle that creates a snapshot
  shows position-management details instead of `无持仓`.
- Fixed partial-entry phase routing so partial short risk enters
  `POSITION_MANAGE` immediately.
- Changed entry execution report semantics: `fill_count` now counts actual
  filled records only, while zero-fill order events remain available as
  `order_event_count`.
- Added Chinese-first locked entry progress display for protection-only
  progress: `保护腿已成交`, `卖方腿未成交`, and `未形成期权空头`.

## Tests Added First

- New matrix rows 010-013 were written before implementation and initially
  failed because the harness could not script Deribit order states.
- After harness support, row 011 failed because protection-only progress was not
  readable in Chinese.
- Row 012 failed because partial short fill created a snapshot but the cycle
  still reported `PLAN_LOCKED`.
- Row 010 exposed misleading entry accounting because zero-fill order events
  were counted as fills.

## Verification

- Targeted lifecycle matrix + live-default version tests:
  `21 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `371 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py`; syntax compile and
  bundle smoke checks passed.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_20.py`
  -> passed.

## Remaining Goal Work

- Expand `realsrc/tests/test_lifecycle_matrix.py` to the full 40-row scenario
  matrix required by `goal/codex_live_readiness_and_ux_full_prompt_goal.md`.
- Highest next rows: entry restart/late cancel fill, TEST entry no-order row,
  TP/risk-exit blocked by depth, hedge pending/missing-order-id idempotency,
  settlement false-read/idempotency, Binance read failure, Deribit option read
  failure, and closed archive cleanup.
- Produce `AUDIT_REPORT.md` and `UX_STATUS_PANEL_AUDIT.md`.
- Add the final Go/No-Go section to `TEST_SUMMARY.md` only after the matrix and
  report checks are complete.
