# Open Gaps And Optimization TODO

This document is the running work queue for the current manual-gate execution
layer. Keep it updated on every small-version iteration. Do not delete an item
until the code, tests, bundle, and delivery notes prove it is closed.

## Current Baseline

- Current target line: `3.2.x-manual-gate`
- Latest completed release: `3.2.13-manual-gate`
- Delivery rule: every small version must keep a versioned backup under
  `artifacts/`, refresh `artifacts/spm_manual_gate_execution_fmz.py`, and keep
  `artifacts/最新交付/` to exactly one current versioned FMZ file.
- Boundary rule: local tests and bundle checks are not FMZ live proof.

## Closed In v3.2.1

- [x] P0: add strict Deribit position read semantics so option position query
  failure is not folded into an empty list.
- [x] P0: prevent settlement reconciliation from finalizing legs when option
  positions are `None` / data gap.
- [x] P0: startup recovery blocks with `OPTION_POSITION_QUERY_FAILED` on strict
  option-position read failure and leaves the snapshot quantities untouched.
- [x] P0/P1: `_archive_closed()` now refuses to archive while hedge policy has a
  pending order, and clears `_RECOVERY_KEY` back to OK after a real archive.
- [x] P1: no-snapshot orphan hedge recovery now gets an explicit
  `ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED` read-screen phase instead of a generic
  `RECOVERY_BLOCKED`.
- [x] P2: settled or short-flat positions skip short-leg risk quote and return
  `OPTION_SETTLED_NO_SHORT_RISK`.

## Closed In v3.2.2

- [x] P0: Binance `GetPosition()` returning `None` is treated as
  `HEDGE_POSITION_DATA_GAP`, not flat zero.
- [x] P0: V32 Binance hedge submit requires `GetOrder` and `CancelOrder` before
  submitting, preserving pending-first single-flight recovery.
- [x] P0: live hedge submit responses without an order id return
  `BINANCE_ORDER_ID_MISSING` and set an unknown-submit guard for the next cycle.
- [x] P0/P1: hedge policy naming is consolidated on V32 with migration from
  `spm_hedge_policy_v313_state` to `spm_hedge_policy_v32_state`.
- [x] P1: disabling V32 hedge policy no longer falls back to legacy hedge submit;
  the cycle holds with `HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT`.
- [x] P1: minimal V32 config rejects Deribit hedge venue and rejects
  `HEDGE_MAKER_FIRST_REDUCE_ENABLED=True` until maker-first reduce is actually
  implemented and tested.
- [x] P2: default SOFT persistence is lengthened from 20s to 60s.

## Closed In v3.2.3

- [x] P0: settlement cashflow and final option PnL accounting.
  Expired option legs now record intrinsic settlement cashflow in settlement
  currency, with `COMPUTED`, `ESTIMATED`, or `DATA_GAP` status. Tests cover
  OTM short, both-ITM vertical, missing settlement price, and fallback index
  price marked `ESTIMATED`.
- [x] P0: protection recovery accounting.
  `_apply_protection_recovery_fill()` records gross recovery value, fees, and
  net recovery value, and recomputes option realized PnL.
- [x] P1: ledger/display settlement and final PnL fields.
  `POSITION_MANAGE` ledger detail now surfaces settlement count/cashflow,
  protection recovery, option realized PnL, and final PnL status.

## Closed In v3.2.4

- [x] P1: real current portfolio inputs for precommit budget.
  `_current_portfolio()` now reads account summary and strict option positions,
  accumulates current short-option gamma/vega load, derives margin usage from
  account initial margin, and returns explicit data gaps for account,
  option-position, size, or short-option Greek failures.
- [x] P1: projected-budget fail-closed on current portfolio data gaps.
  `_build_precommit_live()` now converts current-portfolio `data_gap` into a
  `ProjectedBudgetPackage` with `decision=BLOCK`, instead of passing an
  incomplete current portfolio into zero-default budget math.

## Closed In v3.2.5

- [x] P1: proposed option Greek inputs for precommit budget.
  `exec_quote()` now carries option vega from Deribit ticker greeks, and
  `_build_precommit_live()` passes proposed short gamma/vega as real required
  inputs instead of defaulting missing values to zero. Missing proposed Greeks
  now block through `BUDGET_INPUT_INCOMPLETE`.

## Closed In v3.2.6

- [x] P1: no-snapshot orphan hedge policy decision.
  The permanent policy is `MANUAL_CLEANUP_ONLY`: no-snapshot external perp
  exposure keeps the explicit `ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED` phase and
  exposes `auto_cleanup_allowed=False`, so the runtime does not auto-close an
  orphan hedge without ownership evidence.

## Closed In v3.2.7

- [x] P1: legacy Binance hedge helper exposure.
  `bnc_place_hedge()` is now dry-run/test-only for Binance and live calls return
  `LEGACY_HEDGE_HELPER_LIVE_DISABLED` without probing the exchange. The
  `exec_hedge_step()` Binance branch no longer bridges to the helper in live
  mode and returns `HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT`; V32 live hedge
  submits stay on `bnc_submit_hedge_order()` and pending-first reconciliation.

## Closed In v3.2.8

- [x] P1: fully delete the legacy Binance hedge helper.
  `bnc_place_hedge()` has been removed from the current source and generated
  bundle surface. Binance dry-run hedge steps now return a direct intent from
  `exec_hedge_step()`, while live Binance hedge execution remains fail-closed
  outside the V32 pending-first reconciliation path.

## Closed In v3.2.9

- [x] P1: replace the remaining precommit hedge margin reserve placeholder.
  `_build_precommit_live()` now derives `hedge_margin_reserve` from proposed
  option net delta and `HEDGE_MARGIN_RESERVE_RATE`, normalizing by account
  equity when current margin usage is equity-ratio based. Missing delta or
  equity inputs fail closed through the existing projected-budget package.

## Closed In v3.2.10

- [x] P1: remove stale current authorization surface.
  A current-doc scan found no current runtime authorization prompt instructions
  outside historical handoffs; current docs state confirmation-code-only
  interaction. The obsolete source-only `realsrc/src/authorization.py` module
  and its legacy tests were deleted, and a source isolation test now prevents
  the runtime authorization module from returning.

## Closed In v3.2.11

- [x] P1: remove unimplemented hedge config switches from the current operator
  surface. `HEDGE_MAKER_FIRST_REDUCE_ENABLED`,
  `HEDGE_SLIPPAGE_GUARD_ENABLED`, `HEDGE_LOSS_BOUNDARY_BUFFER_SIGMA`, and
  `HEDGE_SLIP_ALERT_BPS` were deleted from source and bundle output. Tests now
  assert these non-wired switches are absent. `HEDGE_EPISODE_COST_ALERT_BPS`
  remains because it is an observability threshold used by the V32 controller.

## Closed In v3.2.12

- [x] P1: close the remaining Deribit perpetual hedge compatibility surface
  without touching Deribit option entry/exit/quote logic. The minimal config no
  longer exposes `HEDGE_CONTRACT_SIZE_FALLBACK` or
  `HEDGE_MIN_TRADE_FALLBACK`, `_evaluate_hedge()` fails closed with
  `UNSUPPORTED_HEDGE_VENUE` for non-Binance hedge venues, and
  `exec_hedge_step()` blocks legacy Deribit perp hedge live execution before
  quote/order calls.

## Closed In v3.2.13

- [x] P2: surface crash reference price/age in `POSITION_MANAGE` as
  observability only. `policy_detail` now carries `crash_ref_price`,
  `crash_ref_age_seconds`, and `crash_adverse_bps`; the risk/hedge table renders
  a `Crash观测` row that explicitly states it is read-only and does not add
  gates or native conditional orders.

## Must Fix Next

- [ ] P1: no open must-fix item currently identified beyond cleanup candidates
  below.

## Redundancy / Cleanup Candidates

- [ ] Clarify or rename `HEDGE_REDUCTION_RATIO` so it is not mistaken for the
  default gamma-aware full-target sizing control. It is legacy sizing context
  when gamma-aware behavior is disabled or when building entry risk anchors.

## Guardrails For Every Iteration

- [ ] Write failing tests before production fixes.
- [ ] Do not weaken `evaluate_precommit_checks()`, `gate_decision()`,
  execution feasibility, risk-exit budget, or the V32 pending hedge
  single-flight controller.
- [ ] Do not reintroduce runtime commands beyond `执行:<确认码>`,
  `EXECUTE:<确认码>`, or bare confirmation code.
- [ ] Do not auto-close no-snapshot perp exposure without ownership evidence.
- [ ] After code changes, run:
  `realsrc/tests/run_all.py`, `realsrc/build_bundle.py --check`, and
  `py_compile` on the latest delivery artifact.
