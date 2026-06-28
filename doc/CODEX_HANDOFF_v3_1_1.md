# CODEX HANDOFF v3.1.1

## Current Delivery

- Current version: `3.1.1-manual-gate`
- FMZ latest delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_1_1.py`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- SHA256: `67965ACED8BC423210C1F5A3FCD214F230571BE75291402601683009C355D1F9`

## Scope

v3.1.1 contracts the runtime interaction surface and finishes the
trader-facing position-management read screen started in v3.1. It does not
change candidate selection, entry pricing, hedge thresholds, take-profit
math, or recovery decisions.

The only FMZ runtime command that should produce a strategy action is the plan
confirmation code:

- `执行:<确认码>`
- `EXECUTE:<确认码>`
- bare confirmation code

Legacy runtime commands for `拒绝`, `授权止盈`, `风险退出授权`, `撤销授权`,
`急停`, and `恢复` now parse as unknown/ignored and must not trigger strategy
actions.

## Behavioral Changes

1. Position management no longer asks for authorization codes.
   - Take-profit exit may execute automatically when `take_profit_ready`,
     `ALLOW_EXIT_TRADING`, budget, quote, and price-cap gates pass.
   - Risk exit uses configured `RISK_EXIT_MAX_SPEND` when positive; otherwise
     it falls back to the frozen exit budget.
   - If risk exit cannot satisfy budget/quote/price gates, arbitration can
     still fall back to hedge or hold. The status panel explains the boundary;
     it does not ask for a risk-exit code.
2. `POSITION_MANAGE` top status is non-interactive.
   - The first table is `当前环节摘要`, showing phase, lifecycle, automatic
     action, active orders, TP/risk/hedge state, combo PnL, and the fixed
     message `无需交互，按配置门控自动管理`.
   - Plan-only fields such as candidate display, confirmation codes,
     precommit rows, and plan rejection prompts are hidden after entry.
3. The structured display includes target underlying prices.
   - `止盈/退出预算` shows the short-option buyback cap and a delta-linear
     estimated underlying target price.
   - `风险与对冲` shows the hedge trigger underlying price from an explicit
     line when present, otherwise a probability-model estimate when data is
     sufficient; otherwise it shows a data-gap reason.
4. `持仓总览` splits floating PnL.
   - option short-leg PnL,
   - option protection-leg PnL,
   - option total PnL,
   - hedge PnL or `对冲未启用`,
   - combo floating PnL in USD.
5. Data gaps are centralized.
   - Recovery-takeover gaps such as missing breakeven/strike/entry report are
     summarized in `记账/对账/恢复`.
   - Market/quote/delta/hedge PnL gaps render as `数据缺口:<code>`.
   - Hidden plan-only fields are not reported as data gaps during position
     management.
6. `Log` is lower-noise.
   - `LogStatus` still refreshes every cycle.
   - `Log` records phase/action/risk/order changes or a low-frequency
     position heartbeat.
   - Position summaries no longer include per-cycle short/protection mark
     prices, so small mark moves do not spam the event log.

## Regression Coverage Added

- Command parsing accepts only execute/confirmation-code commands; old
  runtime commands are unknown and non-consuming.
- Take-profit exit can execute with config gates and no runtime authorization.
- Risk-exit quote failures fail closed and allow hedge fallback instead of
  aborting the position-management cycle.
- `POSITION_MANAGE` display excludes runtime authorization/stop/recovery
  prompts and plan-only empty fields.
- The position tables include underlying target estimates, option/hedge/combo
  PnL, and explicit data-gap labels.
- Position log summaries ignore mark-only noise while preserving status
  refresh.

## Verification

Fresh local verification:

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_1_1.py
```

Results after final build:

- `272 passed, 0 failed`
- build check passed
- latest FMZ delivery `py_compile` passed
- four bundle hashes matched
  `67965ACED8BC423210C1F5A3FCD214F230571BE75291402601683009C355D1F9`
- `artifacts/最新交付/` should contain only
  `spm_manual_gate_execution_fmz_v3_1_1.py`

## FMZ Retest Focus

After replacing the FMZ code with v3.1.1:

- In planning, confirm the fixed candidate library still shows confirmation
  codes and plan Chinese labels.
- In locked/entry, confirm protection-leg persistent order behavior from
  v3.0.21 is unchanged.
- In `POSITION_MANAGE`, confirm no buttons/prompts mention TP authorization,
  risk-exit authorization, reject, stop, resume, or revoke.
- Verify `持仓总览` shows option PnL, hedge PnL or `对冲未启用`, and combo PnL.
- Verify `止盈/退出预算` and `风险与对冲` show estimated underlying target
  prices or explicit data-gap codes.
- Confirm event logs do not refresh on every small mark move; `LogStatus`
  remains the main live read screen.

Do not treat this local verification as FMZ live proof; live acceptance still
comes from the user's FMZ logs and exchange state.
