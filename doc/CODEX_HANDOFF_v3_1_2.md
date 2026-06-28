# CODEX HANDOFF v3.1.2

## Current Delivery

- Current version: `3.1.2-manual-gate`
- FMZ latest delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_1_2.py`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- SHA256: `E6935924EDC575DA6CE1511C9046DED2AEA02C6AB24016F49A534DB360BE1F04`

## Scope

v3.1.2 is a narrow execution-detail and trader-screen release. It does not
change candidate selection, the manual confirmation-code gate, the strategic
hedge trigger idea, or any FMZ runtime commands.

The only FMZ runtime command that should produce a strategy action remains:

- `执行:<确认码>`
- `EXECUTE:<确认码>`
- bare confirmation code

Position management remains non-interactive. Take-profit, risk exit, hedge,
recovery, and settlement behavior are governed by startup config gates and
automatic evaluation.

## Behavioral Changes

1. Same-leg order safety.
   - Entry precommit now scans active orders for same-leg conflicts.
   - Residual `entry_short` orders fail closed before new entry.
   - Extra protection-leg entry orders fail closed.
   - The only protection order that may be reused is the persistent order id
     already stored on the locked plan.
2. Risk-exit depth gate.
   - `_risk_exit_budget_cap` now returns structured state.
   - Risk exit requires both budget/price approval and best-ask depth covering
     the remaining short-leg quantity.
   - Missing or insufficient depth is reported as a data gap / restricted
     reason and can fall through to the existing hedge-or-hold arbitration.
3. Binance hedge plumbing.
   - Added `HEDGE_BINANCE_PRICE_TICK = 0.1`.
   - BTCUSDC prompt-limit prices are rounded before FMZ `Buy`/`Sell`: buy
     prices up, sell prices down.
   - Added `bnc_get_position_snapshot(symbol, idx=None)` for BTC quantity,
     unrealized PnL, and raw position summaries.
   - `bnc_get_position_btc` remains compatible and returns net BTC quantity.
4. Trader screen and event log.
   - `LogStatus` still refreshes every cycle as the primary read screen.
   - Routine `POSITION_MANAGE` cycles no longer write `Log`.
   - `Log` is reserved for errors, data gaps, order/fill/cancel, take-profit,
     risk exit, hedge, settlement, recovery, and phase-change events.
   - `POSITION_MANAGE` now can display Binance hedge unrealized PnL when the
     venue provides it.
5. Hedge review artifact.
   - `doc/HEDGE_MODULE_INQUIRY_v3_1_2.md` documents the 2026-06-28 morning
     BTCUSDC hedge case and the open design question around prompt-limit/taker
     urgency versus maker-first, staged sizing, hysteresis, and cooldown.

## Regression Coverage Added

- `POSITION_MANAGE` ordinary cycles refresh `LogStatus` but keep `Log` silent.
- Key hedge events in `POSITION_MANAGE` still write event logs.
- Entry precommit blocks residual same-leg `entry_short` orders.
- Entry precommit blocks extra protection-leg entry orders while allowing the
  current persistent protection order id.
- Risk exit is not executable when best-ask depth is missing or insufficient.
- Binance hedge prices are rounded to the configured tick by side.
- Binance position snapshots include unrealized PnL and carry it into the
  status display.
- Existing protection-leg 10-minute taker fallback, short-leg 60-second maker
  behavior, confirmation-only command parsing, and fixed candidate-library
  display remain covered by regression tests.

## Verification

Fresh local verification required for this delivery:

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_1_2.py
```

Expected final results:

- `279 passed, 0 failed`
- build check passed
- latest FMZ delivery `py_compile` passed
- four bundle hashes matched
  `E6935924EDC575DA6CE1511C9046DED2AEA02C6AB24016F49A534DB360BE1F04`
- `artifacts/最新交付/` contains only
  `spm_manual_gate_execution_fmz_v3_1_2.py`

## FMZ Retest Focus

After replacing the FMZ code with v3.1.2:

- Confirm ordinary `POSITION_MANAGE` rounds no longer spam `Log` with
  `RUN_CYCLE:POSITION_MANAGE` lines, while `LogStatus` continues refreshing.
- Confirm Binance precision errors from raw prompt-limit float prices do not
  recur for BTCUSDC hedge orders.
- Confirm risk-exit display shows price/depth status and uses `数据缺口` when
  ask depth is missing instead of showing a misleading zero.
- Confirm same-leg residual orders are treated as blockers before new entry.
- Confirm fixed candidate-library rows, confirmation codes, and Chinese labels
  still appear in the planning cycle.
- Review hedge fills and fees with `doc/HEDGE_MODULE_INQUIRY_v3_1_2.md` before
  changing hedge trigger frequency or maker/taker policy.

Do not treat this local verification as FMZ live proof; live acceptance still
comes from the user's FMZ logs and exchange state.
