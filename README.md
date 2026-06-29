# Neutral Loop Execution Layer

Human Audit Gate execution-layer handoff package for GPT-5.5 Pro continuation.

This repository contains the current independent execution-layer deliverable only. It does not include the signal-layer FMZ artifact and must not be treated as proof of FMZ dry-run, exchange read-only validation, or live readiness.

## Current Artifact

- FMZ artifact: `artifacts/spm_manual_gate_execution_fmz.py`
- Latest FMZ delivery: `artifacts/最新交付/spm_manual_gate_execution_fmz_v1.py`
- Editable source: `realsrc/src/`
- Source bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- Version: `STRATEGY_VERSION = "v1"`
- Status: live-test defaults with manual confirm-code gate
- Release class: formal live-validation v1. All generated `v3*` bundles are
  test-round archives, not the current sealed live-validation artifact.
- Version classification: `artifacts/VERSION_CLASSIFICATION.md`
- Formal seal audit: `doc/FORMAL_V1_SEAL_AUDIT.md`
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
  resolved fills are mirrored into `hedge_execution_history`. This historical
  V313 path was superseded by the V32-only hedge path in v3.2.2.
- v3.1.5 wires option-settlement reconciliation into startup recovery and
  `POSITION_MANAGE`: after expiry grace and a successful exchange option read,
  absent settled legs are finalized in the local snapshot with
  `option_settlement_history` with a placeholder accounting status, settled
  shorts force hedge target zero/orphan reduce-only cleanup, and short-flat TP
  evaluation no longer quotes expired instruments. The `NOT_COMPUTED`
  settlement accounting placeholder is superseded by v3.2.3.
- v3.2.0 upgrades the Binance hedge reconciliation policy with gamma-aware
  SOFT sizing, raw full-delta HARD/CRASH targets, a 20% no-trade rebalance
  band, ordinary reduce min-hold, final-3h SOFT-add suppression, and a 10-minute
  crash override. The old Deribit dry hedge intent path is neutralized; runtime
  interaction remains confirmation-code only.
- v3.2.1 closes the first settlement/recovery safety gaps from the v3.2 audit:
  Deribit option-position reads now have strict failure semantics, settlement
  reconcile no longer treats read failure as empty exchange positions, CLOSED
  archive clears recovery only when no hedge pending remains, no-snapshot orphan
  hedge recovery gets an explicit manual-cleanup read-screen phase, and settled
  shorts no longer produce noisy risk quote gaps.
- v3.2.2 is the minimal clean V32 hedge-chain closeout: Binance `GetPosition()`
  returning `None` is a data gap rather than flat zero, V32 hedge submission
  requires `GetOrder`/`CancelOrder`, live submit responses without an order id
  enter an unknown-submit guard, the policy state key migrates from V313 to V32,
  policy-disabled cycles hold instead of falling back to the old submit path,
  and minimal V32 config rejects Deribit hedge venue plus maker-first reduce.
- v3.2.3 closes the settlement accounting loop: expired option legs record
  settlement cashflow and `COMPUTED` / `ESTIMATED` / `DATA_GAP` status,
  protection recovery fills record gross value, fees, and net recovery value,
  option realized PnL is recomputed from entry credit, exits, recovery, and
  settlement, and the position-management ledger table surfaces settlement,
  recovery, realized PnL, and final PnL status.
- v3.2.4 replaces fixed-zero current portfolio budget inputs with strict
  account summary and option-position reads. Account, option-position, position
  size, or short-option Greek data gaps now block new entries through the
  projected-budget package instead of defaulting current load to zero.
- v3.2.5 tightens proposed-budget Greek inputs: `exec_quote()` carries option
  vega from Deribit ticker greeks, and entry precommit no longer fills missing
  proposed short gamma/vega with zero. Missing proposed Greeks now fail closed
  through `BUDGET_INPUT_INCOMPLETE`.
- v3.2.6 codifies the no-snapshot orphan hedge policy as manual cleanup only:
  the read-screen detail now exposes `policy=MANUAL_CLEANUP_ONLY` and
  `auto_cleanup_allowed=False`, preserving the rule that unknown external perp
  exposure is never auto-closed without ownership evidence.
- v3.2.7 removes the live-capable legacy Binance hedge helper path from the
  current execution surface: V32 live hedge submits must use
  `bnc_submit_hedge_order()` plus pending-first reconciliation, while
  `bnc_place_hedge()` remains dry-run/test-only and live calls are blocked.
- v3.2.8 fully deletes the legacy Binance `bnc_place_hedge()` helper from the
  current source and bundle surface. Binance dry-run hedge steps now return a
  direct execution intent from `exec_hedge_step()`, while live Binance hedge
  execution still stays fail-closed unless driven by the V32 pending-first
  reconciliation controller and `bnc_submit_hedge_order()`.
- v3.2.9 replaces the remaining precommit `hedge_margin_reserve = 0.0`
  placeholder with a net-delta-based reserve. The projected budget now includes
  `abs(option_net_delta) * HEDGE_MARGIN_RESERVE_RATE`, normalized by account
  equity when margin usage is already expressed as an equity ratio; missing
  required delta/equity inputs fail closed through the existing budget package.
- v3.2.10 removes the obsolete source-only `authorization.py` module and its
  legacy tests. Runtime interaction remains confirmation-code-only; TP,
  risk-exit, reject, stop, resume, revoke, and manual hedge commands are still
  absent from the FMZ command router and generated bundle.
- v3.2.11 removes unimplemented hedge configuration switches from the operator
  surface: maker-first reduce, slippage guard enable, loss-boundary buffer, and
  slip alert bps. The remaining episode-cost threshold is kept because it is
  used as observability only and does not gate HARD hedge actions.
- v3.2.12 closes the remaining Deribit perpetual hedge compatibility surface:
  Deribit hedge fallback sizing constants are removed from the current config,
  strategy hedge evaluation fails closed on non-Binance hedge venues, and
  legacy Deribit perp hedge live execution is blocked before quote/order calls.
  Deribit option entry, exit, quote, and recovery logic are unchanged.
- v3.2.13 adds crash-trigger observability to the trader read screen. The V32
  hedge policy now carries `crash_ref_price`, `crash_ref_age_seconds`, and
  `crash_adverse_bps` into `POSITION_MANAGE`, and the risk/hedge table renders
  a read-only `Crash观测` row. No hedge gate, trigger threshold, or conditional
  order behavior changes.
- v3.2.14 closes two audit-found readiness gaps: TEST profile now forces V32
  hedge cleanup submits to dry-run even when reduce-only cleanup bypasses the
  normal hedge gate, and `run_cycle()` treats a persisted position snapshot as
  an active position even if the local ledger state was lost.
- v3.2.15 tightens two trader-facing execution details: V32 episode-cost display
  is now explicitly labeled `reserved_not_computed` telemetry rather than real
  computed cost, and protection-leg taker buy fallback uses taker-specific
  tick rounding so a buy crosses the quoted ask after rounding.
- v3.2.16 adds the required lifecycle map and closes the startup orphan hedge
  cleanup gap: when startup recovery has strict evidence of no option short
  risk, a Binance perp orphan, clean open-order reads, and Binance order
  lifecycle support, LIVE submits an automatic reduce-only cleanup while TEST
  stays dry-run. Missing lifecycle support remains manual cleanup with no order.
- v3.2.17 starts the centralized lifecycle scenario matrix with a deterministic
  local harness that asserts `_G` state, no-order evidence, and parsed
  `LogStatus` tables. It also changes the TEST plan-phase RUN_PROFILE row to
  Chinese-first wording: `测试模式：不会真实下单`.
- v3.2.18 expands the lifecycle matrix to cover TEST no-order behavior during
  take-profit, protection recovery, hedge-ready management, and orphan cleanup.
  It also classifies no-option-risk + Binance perp + unknown active orders as
  orphan manual cleanup, so the trader sees a clear manual only-reduce path
  instead of a generic recovery block.
- v3.2.19 expands the lifecycle matrix through the confirmation-code and
  precommit boundary: valid confirmation locks the plan without orders when the
  entry gate is closed, wrong confirmation codes do not lock or order, and
  unknown same-leg active option orders block precommit. The status panel now
  displays last-command outcomes and precommit failed checks in Chinese first,
  with raw check keys kept only in parentheses.
- v3.2.20 expands the lifecycle matrix through protected-entry multi-loop
  states: full protection+short fill freezes a snapshot, protection-only fill
  keeps the locked campaign without naked short risk, short partial fill enters
  position management, and a pending protection maker order is not duplicated
  across loops. It also fixes post-entry status display and counts only actual
  entry fills in `fill_count`.
- v3.2.21 expands the lifecycle matrix with TEST confirm-code dry/no-order,
  protection cancel late-fill idempotency, and risk-exit ask-depth data-gap
  coverage. Risk-exit blocked reasons now render Chinese-first in `LogStatus`
  and low-frequency `Log` summaries while keeping the internal reason code in
  structured context.
- v3.2.22 expands the lifecycle matrix through LIVE TP/risk-exit closeout
  paths and startup recovery read-failure screens: TP maker buyback and
  risk-exit taker buyback are idempotent across repeated loops, risk-exit
  ask-above-cap does not over-spend, and Binance/Deribit recovery read failures
  now display Chinese manual-check reasons in `LogStatus`.
- v3.2.23 expands the lifecycle matrix through remaining TP/risk-exit closeout
  evidence: risk-exit quote gap, risk-exit insufficient ask depth, TP maker
  cancel-late-fill accounting, and partial-exit next-loop completion without
  double-counting. No production behavior change was needed beyond the version
  bump and regenerated delivery bundle.
- v3.2.24 expands the lifecycle matrix through V32 Binance hedge order
  lifecycle behavior: live hedge submit writes a pending order and blocks
  duplicate submits, missing Binance order IDs enter the unknown-submit guard,
  terminal pending fills write hedge execution history once, and hedge policy
  pending/unknown reasons now render Chinese-first in `LogStatus`.
- v3.2.25 expands the lifecycle matrix through V32 hedge trigger/read-screen
  variants: SOFT initial add, HARD trigger while add-cooldown is active,
  final-3h SOFT-add suppression with no order, and ordinary reduce-only unwind.
  SOFT/HARD/final-3h/reduce policy reasons now render Chinese-first in
  `LogStatus`.
- v3.2.26 completes the 40-row lifecycle matrix with settlement/archive/accounting
  rows: option read gaps do not false-settle, short-leg settlement is
  idempotent while long residual remains, both-leg settlement archives final
  PnL, closed archive is not duplicated, missing settlement price archives as
  `DATA_GAP` instead of zero PnL, and settlement-with-perp submits reduce-only
  cleanup without premature archive. The ledger table now renders settlement,
  protection recovery, option realized PnL, and final option PnL in
  Chinese-first operator text.
- Final local audit package: `AUDIT_REPORT.md`,
  `UX_STATUS_PANEL_AUDIT.md`, and `TEST_SUMMARY.md` record the
  `SMALL_SIZE_LIVE_TEST_READY` local verdict, with an additional test-only row
  041 for protection-recovery no-double-count evidence. This verdict is not FMZ
  live proof; it requires live robot/exchange acceptance with the exact current
  artifact.
- v3.2.27 closes the Opus 4.8 P1 display gap: every reachable V32 hedge
  controller reason now has Chinese-first `LogStatus` wording, including
  steady-state, deadband, cooldown, reverse-unwind, crash, and policy-disabled
  states. The fix is display-only and adds registry/read-screen tests so raw
  machine codes no longer become primary operator text.
- v3.2.28 closes the Opus 4.8 P2 display note gap: exit-campaign states such as
  `WORKING_LONG`, `LONG_RESIDUAL_ONLY`, and `PAUSED_BY_BUDGET` now render as
  Chinese-first text in the lifecycle note, pipeline echo, and console rows.

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
