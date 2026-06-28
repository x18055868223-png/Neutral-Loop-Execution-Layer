# Neutral Loop Execution Layer

Human Audit Gate execution-layer handoff package for GPT-5.5 Pro continuation.

This repository contains the current independent execution-layer deliverable only. It does not include the signal-layer FMZ artifact and must not be treated as proof of FMZ dry-run, exchange read-only validation, or live readiness.

## Current Artifact

- FMZ artifact: `artifacts/spm_manual_gate_execution_fmz.py`
- Latest FMZ delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_0.py`
- Editable source: `realsrc/src/`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- Version: `STRATEGY_VERSION = "3.2.0-manual-gate"`
- Status: live-test defaults with manual confirm-code gate
- v3.0.14 fixes Binance BTCUSDC perpetual selection by switching FMZ to
  `BTC_USDC` and `swap` before hedge position reads/orders.
- v3.0.15 keeps the full status panel, deduplicates repeated Log lines, adds a
  one-shot read-only startup self-check, and restores Chinese config comments.
- v3.0.16 restores the historical full LogStatus tabs from v3.0.10, including
  the main-chain echo table, fixed candidate library, candidate preview, order
  intent, and reasonable-check panels across planning and locked-plan cycles.
- v3.0.17 restores the confirmation-code column inside the fixed candidate
  library and labels the earliest displayed expiry as `最近可用` when no
  near-24h candidate survived into the displayed plan set.
- v3.0.18 keeps 20h near-24h put candidates when the short leg is executable
  and the low-premium protection leg is buyable with a small absolute spread;
  stable FMZ candidate-library cache now includes `STRATEGY_VERSION` so old
  frozen menus are rebuilt after an upgrade.
- v3.0.19 adds endgame-expiry protection-leg tolerance: near-24h candidates use
  `ENDGAME_PROTECTION_WIDTH_MIN = 1500` and keep up to two protection-width
  choices per qualified short leg, allowing 2-4 expiry-day vertical candidates
  when quotes and net credit remain executable.
- v3.0.20 fixes locked-plan entry campaign behavior: no-fill soft wait caps no
  longer clear the locked plan or rebuild the candidate library, protection-only
  progress keeps building the same selected structure, expiry-day protection
  legs can use a guarded taker fallback only when ask depth and one-tick price
  checks pass, and the short leg maker order now rests for 60 seconds.
- v3.0.21 changes protection-leg entry to a persistent maker order at the
  mark-derived price: the same order is kept on exchange, only repriced when
  the mark target moves by at least one tick, and after 10 minutes it may take
  best ask only when ask depth covers the remaining quantity and net credit
  stays above the floor.
- v3.1 enhances the `POSITION_MANAGE` status layer only: `LogStatus` now
  shows trader-facing Chinese tables for `持仓总览`, `止盈/退出预算`, `风险与对冲`,
  and `记账/对账/恢复`, while preserving the planning-cycle candidate library
  display and existing trading logic.
- v3.1.1 contracts the FMZ runtime interaction surface to one action only:
  entering a plan confirmation code. Position management no longer asks for
  TP/risk-exit authorization, reject, stop, resume, or revoke commands; exits
  are evaluated by config gates. The position display also adds underlying
  target-price estimates, option/hedge/combo floating PnL in USD, centralized
  data-gap labels, and low-frequency Chinese event logs.
- v3.1.2 tightens live execution boundaries without changing the strategy
  idea: entry precommit blocks residual same-leg active orders, risk exit now
  requires both budget price and best-ask depth, Binance BTCUSDC prompt-limit
  hedge prices are tick-rounded while unrealized PnL is read into
  `POSITION_MANAGE`, and routine position cycles keep `Log` quiet while
  `LogStatus` remains the trader's read screen.
- v3.1.3 adds the near-expiry ordinary take-profit gate for short-dated
  positions: 80% capture still qualifies normal profit-taking only when
  remaining DTE is greater than `TAKE_PROFIT_MIN_DTE_HOURS` (default `3.0`).
  Inside the final gate window, ordinary TP is paused and the screen explains
  the boundary, while risk exit and hedge fallback remain active.
- v3.1.4 replaces the default Binance BTCUSDC hedge action path with the
  V313 reconciliation controller: pending orders are resolved first, exchange
  hedge position is read as truth, SOFT triggers stage to an effective target,
  HARD triggers go straight to full target, cooldown/hysteresis reduce
  whipsaw, and each cycle submits at most one Binance hedge order. Active
  partial pending fills now keep single-flight blocking, while terminal/stale
  resolved fills are mirrored into `hedge_execution_history`. Deribit and
  `HEDGE_POLICY_V313_ENABLED = False` keep the legacy prompt-limit path.
- v3.1.5 wires option-settlement reconciliation into startup recovery and
  `POSITION_MANAGE`: after expiry grace and a successful exchange option read,
  absent settled legs are finalized in the local snapshot with
  `option_settlement_history` (`settlement_pnl_status=NOT_COMPUTED`), settled
  shorts force hedge target zero/orphan reduce-only cleanup, and short-flat TP
  evaluation no longer quotes expired instruments.
- v3.2.0 upgrades the Binance hedge reconciliation policy with gamma-aware
  SOFT sizing, raw full-delta HARD/CRASH targets, a 20% no-trade rebalance
  band, ordinary reduce min-hold, final-3h SOFT-add suppression, and a 10-minute
  crash override. The old Deribit dry hedge intent path is neutralized; runtime
  interaction remains confirmation-code only.

## Boundary

The execution layer is independent from the signal layer. Current planning input comes from FMZ/manual live config, not from signal files, receiver modules, or external lineage packages.

Main path:

`manual live config -> Deribit option-chain -> nearest-24h vertical candidates -> S:PM / execution feasibility / VRP validity / budget filters -> confirm code -> precommit -> entry campaign`

Existing positions continue through position management, exit, hedge, and recovery even when manual planning is disabled.

## Live-Test Defaults

The current artifact defaults to the user's small live-test posture:

- `RUN_PROFILE = "LIVE"`
- `DRY_RUN_PASSED = True`
- `ALLOW_ENTRY_TRADING = True`
- `ALLOW_EXIT_TRADING = True`
- `ALLOW_HEDGE_TRADING = True`
- `RISK_EXIT_MAX_SPEND = 0.001`

Do not claim FMZ live readiness from local checks alone. Local tests prove only the code and artifact boundary; live acceptance comes from the user's FMZ logs and exchange state.

## Development Workflow

Edit source first:

```powershell
cd realsrc
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe build_bundle.py --check
```

After `build_bundle.py --check`, copy the generated bundle to a versioned backup under `artifacts/`, update `artifacts/spm_manual_gate_execution_fmz.py`, and keep `artifacts/最新交付/` to exactly one current versioned file.

See `CHATGPT5.5_PRO.md` for the full continuation brief.
