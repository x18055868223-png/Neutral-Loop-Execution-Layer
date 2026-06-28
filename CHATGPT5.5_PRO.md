# GPT-5.5 Pro Handoff: Neutral Loop Execution Layer

## Current State

This repo is the standalone FMZ execution-layer handoff for
`spm_manual_gate_execution_fmz.py`. The current deliverable is
`STRATEGY_VERSION = "3.1.4-manual-gate"`.

Editable source lives in `realsrc/src/`. Tests live in `realsrc/tests/`.
The FMZ single-file bundle is built by `realsrc/build_bundle.py`.

Delivery convention:

- Versioned backups stay in `artifacts/`.
- `artifacts/最新交付/` contains exactly one current versioned FMZ file.
- Do not hand-edit generated artifacts; edit `realsrc/src/`, then rebuild.

## Ponytail Rule

Default future work is ponytail/full: reuse first, standard library second,
minimum new code last. Delete stale paths instead of preserving compatibility
that the operator will not use.

Do not add speculative adapters, old-mode bridges, hidden fallback inputs, or
unused strategy phases. If a compatibility path is not part of the current FMZ
workflow, remove it precisely and cover the deletion with a focused test.

## Operator Configuration

The top config block is now live-test oriented by default. The operator should
normally only edit the core live fields:

- `ROBOT_ID`
- `DIRECTION_BIAS`
- `ORDER_AMOUNT`
- `SHORT_DELTA_RANGE`
- `PROTECTION_WIDTH_RANGE`
- `ENDGAME_PROTECTION_WIDTH_MIN`
- `ENDGAME_PROTECTION_CHOICES_PER_SHORT`
- `ENTRY_SHORT_ORDER_WAIT_SECONDS`
- `ENTRY_PROTECTION_TAKER_AFTER_SECONDS`
- `RISK_EXIT_MAX_SPEND`
- `TAKE_PROFIT_MIN_DTE_HOURS`
- `ALLOW_ENTRY_TRADING`
- `ALLOW_EXIT_TRADING`
- `ALLOW_HEDGE_TRADING`
- `KILL_NEW_RISK`
- `EMERGENCY_REDUCE_ONLY`
- `HEDGE_VENUE`
- `HEDGE_BINANCE_INSTRUMENT`
- `HEDGE_BINANCE_MIN_TRADE`
- `HEDGE_BINANCE_PRICE_TICK`
- `HEDGE_BINANCE_EXCHANGE_INDEX`
- `HEDGE_POLICY_V313_ENABLED`
- `HEDGE_STAGING_ENABLED`
- `HEDGE_HYSTERESIS_ENABLED`
- `HEDGE_COOLDOWN_ENABLED`
- `HEDGE_SLIPPAGE_GUARD_ENABLED`
- `GEX_CONTEXT_API_BASE`
- `GEX_CONTEXT_API_KEY`

Default small-live-test posture:

- `RUN_PROFILE = "LIVE"`
- `DRY_RUN_PASSED = True`
- `ALLOW_ENTRY_TRADING = True`
- `ALLOW_EXIT_TRADING = True`
- `ALLOW_HEDGE_TRADING = True`
- `RISK_EXIT_MAX_SPEND = 0.001`
- `TAKE_PROFIT_MIN_DTE_HOURS = 3.0`
- Binance hedge venue is the default; Deribit perpetual remains compatibility
  only.
- Binance hedge input remains `HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"`, but the
  FMZ exchange call must select `BTC_USDC` as currency and `swap` as contract
  type. Do not pass `BTCUSDC` to `SetContractType()`.
- Binance hedge prompt-limit prices must use `HEDGE_BINANCE_PRICE_TICK = 0.1`;
  buy prices round up, sell prices round down. Position reads should prefer the
  snapshot path so BTC quantity and unrealized PnL can both reach the
  `POSITION_MANAGE` display.
- Ordinary 80% capture take-profit is allowed only when remaining short-leg DTE
  is greater than `TAKE_PROFIT_MIN_DTE_HOURS`. Inside the final 3 hours, normal
  TP is paused and the position tends toward settlement, but risk exit and
  hedge arbitration must remain live.
- Binance hedge defaults to the V313 reconciliation controller in this v3.1.4
  delivery. It resolves pending orders first, reads exchange hedge position as
  truth, reconciles to `eff_target`, keeps SOFT staged/cooldown behavior, and
  lets HARD reach full target without being blocked by SOFT guards. Turning
  `HEDGE_POLICY_V313_ENABLED = False` returns to the legacy one-step
  prompt-limit hedge path.

Legacy operator inputs for audit-card references, manual notes, plan/order
rounds, selected preview plans, the old global trading switch, and the old
kill switch have been removed. Do not reintroduce them.

FMZ runtime interaction is intentionally narrower than the config surface:
`GetCommand()` is only for `执行:<确认码>` / `EXECUTE:<确认码>` / a bare
confirmation code during the planning cycle. Position management, take-profit,
risk exit, hedge, recovery, stop/resume, and revoke behavior are not runtime
commands; they are governed by the startup config gates above.

## Planning Rule

The candidate library is centered on near-24h capital efficiency:

- Internal target DTE is 24 hours.
- The planner selects the expiry nearest to 24h, then the next later exchange
  expiry if available.
- At most two expiries enter the candidate library.
- Thin premium and low margin relief are warnings/scoring inputs, not hard
  blockers for these short-dated candidates.

Hard fail-closed checks still apply to real execution:

- valid option quotes,
- spread/liquidity sanity,
- positive executable net credit,
- portfolio budget,
- risk-exit budget,
- order recovery and ledger checks.

## Main Path

`manual live config -> Deribit option-chain -> nearest-24h vertical candidates
-> S:PM / execution feasibility / VRP validity / budget filters -> confirm code
-> precommit -> entry campaign -> position management -> exit / hedge / recovery`

Existing positions continue through management, exit, hedge, orphan cleanup, and
recovery even if new planning is disabled.

## Verification

Windows / Python 3.12:

```powershell
$py = 'C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe'

& $py realsrc\tests\run_all.py
& $py realsrc\build_bundle.py --check
& $py -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_1_4.py

# Run the v3.0.13 legacy-config scan listed in
# realsrc\tests\test_v3_0_13_live_24h.py against source and current delivery.
```

Expected:

- all tests pass; current v3.1.4 local suite expectation is `304 passed, 0 failed`,
- build check passes,
- py_compile passes,
- LogStatus includes `交互控制台`, `运行概览`, `完整主链模块回显`,
  `固定备选方案库`, candidate/selected preview, order-intent, and
  reasonable-check panels when plan data exists,
- the fixed candidate library shows `确认码/锁定状态`, and the earliest
  displayed expiry is not mislabeled as `次日备选` when no near-24h row remains,
- near-24h low-premium protection legs with small absolute spread remain
  eligible; upgraded robots rebuild old frozen candidate menus because stable
  menu metadata is bound to `STRATEGY_VERSION`,
- endgame-expiry candidates can use 1500 minimum protection width and up to two
  protection choices per qualified short leg; normal later expiries still use
  the regular `PROTECTION_WIDTH_RANGE` behavior,
- confirmed plans stay locked through the entry campaign; no-fill cycles and
  protection-only progress must not rebuild the candidate library,
- protection-leg entry uses one persistent post-only maker order at the
  mark-derived price; each cycle queries the same order, reprices only when the
  mark target moves by at least one tick, and does not reset the 10-minute
  timer when repricing,
- after 10 minutes from the first protection maker order, the robot cancels the
  maker and may buy best ask without the old one-tick restriction, but only
  when ask depth covers the remaining quantity and projected net credit remains
  above `ENTRY_MIN_NET_CREDIT`; otherwise it keeps/refreshes the mark maker,
- short-leg maker orders still wait until protection fill exists and rest for
  60 seconds,
- ordinary take-profit requires both 80% capture and remaining DTE greater than
  `TAKE_PROFIT_MIN_DTE_HOURS`; the final 3h gate must not block risk exit or
  hedge fallback,
- entry precommit must fail closed when an unknown active `entry_short` order
  or an extra protection-leg entry order already exists on the same leg; the
  current persistent protection order id is the only reusable protection order,
- risk exit must require both price-budget approval and best-ask depth covering
  the remaining short-leg quantity; missing depth is a data gap, not a zero,
- Binance BTCUSDC hedge order prices must be tick-rounded before FMZ `Buy` or
  `Sell`, avoiding precision `-1111` errors from raw float prompt limits,
- Binance hedge position snapshots should surface unrealized PnL to
  `POSITION_MANAGE` while keeping quantity-read failures fail-closed,
- Binance V313 hedge controller must remain single-flight: pending orders are
  queried/cancelled/cleared before any new submit; late fills must not create
  overhedge; SOFT starts at 50% effective target and only persists/worsens to
  full target; HARD reaches full target and bypasses SOFT cooldown/slippage
  gates; short-flat/orphan/reverse hedge paths unwind reduce-only first,
- active partial Binance hedge fills must keep the pending order alive and
  block any second hedge submit; terminal or stale-cancelled pending fills must
  be mirrored into `hedge_execution_history` so the operator ledger sees the
  real resolved fill,
- in `POSITION_MANAGE`, the trader-facing `LogStatus` is no longer carried by a
  single raw `hedge_state` string. It should show the four structured Chinese
  tables `持仓总览`, `止盈/退出预算`, `风险与对冲`, and `记账/对账/恢复`; machine
  reason/code fields may remain as traceable detail, but not as the primary
  reading surface,
- in `POSITION_MANAGE`, no runtime command hints for TP authorization, risk
  exit authorization, reject, stop, resume, or revoke should appear. The top
  table is a non-interactive current-stage summary and should include automatic
  action, TP/risk/hedge status, and combo floating PnL,
- `止盈/退出预算` should show both the short-option buyback cap and the
  delta-linear underlying target estimate; `风险与对冲` should show a hedge
  trigger underlying price when it is explicit or can be estimated,
- `持仓总览` should separate option-leg floating PnL, hedge-leg floating PnL,
  and combo floating PnL in USD, showing `对冲未启用` instead of `0` when no
  hedge position exists,
- ordinary `POSITION_MANAGE` cycles should refresh `LogStatus` but should not
  write `Log` lines unless there is an error, data gap, order/fill/cancel,
  take-profit, risk-exit, hedge, settlement, recovery, or phase-change event,
- the exact legacy config scan has no hits in source or current delivery,
- `artifacts/最新交付/` contains only the current versioned file.

## Guardrails

Do not treat local tests or bundle compilation as FMZ live proof. Live readiness
comes from the user's FMZ run logs and exchange state. Keep planning, entry,
hedge, exit, recovery, and ledger concerns separated; do not let a hedge change
candidate selection or precommit behavior.
