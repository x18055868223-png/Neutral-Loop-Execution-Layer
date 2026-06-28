# CODEX HANDOFF v3.1

## Current Delivery

- Current version: `3.1-manual-gate`
- FMZ latest delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_1.py`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- SHA256: `924317754BE2C4A6C095F6A70B1648E15826F41E466E6BB8329861AFA78AE6CC`

## Scope

v3.1 is a status-display release on top of the v3.0.21 entry behavior. It does
not change order placement, hedge thresholds, take-profit formulas, budget
rules, or recovery decisions.

The issue exposed by live testing was not that the modules were absent, but
that the post-entry state surface was too thin: `POSITION_MANAGE` compressed
hedge, take-profit, ledger, recovery, and active-order context into sparse rows
or raw machine strings. That made the robot harder to supervise once a real
short vertical was open.

## Display Changes

`POSITION_MANAGE` now uses dedicated trader-facing tables:

1. `持仓总览`
   - lifecycle state,
   - short/protection contracts and remaining quantities,
   - frozen entry average prices,
   - current mark/bid/ask for both legs,
   - DTE, breakeven, short-leg distance from spot,
   - explicit quote data-gap reason when quote reads fail.
2. `止盈/退出预算`
   - entry profit ceiling,
   - target take-profit amount and capture ratio,
   - current reference capture status,
   - short buyback reference cost, fee/reserve, remaining budget,
   - budget price cap,
   - risk-exit authorization and independent spend boundary.
3. `风险与对冲`
   - entry/current touch probability and drift,
   - watch/open/emergency thresholds,
   - hedge trigger price line or probability-only trigger text,
   - option net delta, target hedge, current perp position, expected trade size,
   - venue/instrument/side,
   - Chinese action labels such as `保持`, `新开对冲`, `增加对冲`, `减少对冲`,
     and `清理孤儿对冲`,
   - explicit data-gap labels such as `HEDGE_POSITION_DATA_GAP` or
     `HEDGE_DELTA_DATA_GAP`.
4. `记账/对账/恢复`
   - short-leg credit, protection cost, entry fees, actual net credit,
   - realized exit spend and remaining exit budget,
   - execution-history counts,
   - exchange reconcile result and reasons,
   - recovery state and whether new opens are allowed,
   - current active orders by instrument/label.

The top `交互控制台` remains the fast action strip: phase, gates, arbitration,
authorization hints, active orders, concise TP/hedge/ledger summaries, and one
operation hint.

The `完整主链模块回显` table now prefers Chinese summaries from structured
fields instead of raw strings like `venue=... entry_p=...`. The old
`hedge_state` compatibility field remains available, but it is not the primary
reading surface.

## Data-Gap Rule

Missing or unreliable values are rendered as `数据缺口` plus a reason/code
instead of misleading zeroes. Quote reads added purely for display are
fail-soft: if they fail, the position-management logic continues and the
overview table shows `SHORT_QUOTE_DATA_GAP` / `LONG_QUOTE_DATA_GAP`.

## Regression Coverage Added

- `POSITION_MANAGE` status panel includes `持仓总览`, `止盈/退出预算`,
  `风险与对冲`, and `记账/对账/恢复`.
- Hedge display includes entry/current probability, open threshold, target
  hedge, current perp position, expected trade quantity, and Chinese action.
- Take-profit display includes profit ceiling, target TP, capture ratio,
  remaining budget, price cap, and risk authorization.
- Ledger display includes entry income/cost, fees, exit spend/budget,
  reconcile result, recovery state, and active orders.
- Data gaps are displayed explicitly and are not rendered as `0.0%`.
- `manage_cycle()` / `run_cycle()` carry structured display details while
  preserving existing position-management behavior.

## Verification

Fresh local verification:

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_1.py
```

Results:

- `268 passed, 0 failed`
- build check passed
- latest FMZ delivery `py_compile` passed
- four bundle hashes matched `924317754BE2C4A6C095F6A70B1648E15826F41E466E6BB8329861AFA78AE6CC`
- `artifacts/最新交付/` contains only `spm_manual_gate_execution_fmz_v3_1.py`

## FMZ Retest Focus

After replacing the FMZ code with v3.1:

- Confirm the planning cycle still shows the fixed candidate library with
  confirmation codes and current Chinese labels.
- Enter or resume a protected short vertical and verify `POSITION_MANAGE` shows
  the four dedicated tables.
- Check that hedge, TP, ledger, reconcile, recovery, and active-order context
  can be read from `LogStatus` without relying on long raw machine strings.
- If an exchange/data read is missing, verify the table shows `数据缺口` and a
  reason rather than a misleading zero.
- Confirm no new candidate library is pushed while already in position
  management.

Do not treat this local verification as FMZ live proof; live acceptance still
comes from the user's FMZ logs and exchange state.
