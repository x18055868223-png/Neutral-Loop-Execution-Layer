# Open Gaps And Optimization TODO

This document is the running work queue for the current manual-gate execution
layer. Keep it updated on every small-version iteration. Do not delete an item
until the code, tests, bundle, and delivery notes prove it is closed.

## Current Baseline

- Current target line: `3.2.x-manual-gate`
- Latest completed release before this queue: `3.2.0-manual-gate`
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

## Must Fix Next

- [ ] P0: settlement cashflow and final option PnL accounting.
  Evidence gap: `_append_settlement_event()` still defaults
  `settlement_pnl_status=NOT_COMPUTED`. Add tests for OTM/ITM short, ITM long,
  both-ITM vertical, missing settlement price, and fallback index price marked
  `ESTIMATED`.
- [ ] P0: protection recovery accounting.
  Current recovery only decrements `long_remaining_qty` and appends history.
  Add `_apply_protection_recovery_fill()` so net recovery value and fees are
  included in option realized PnL.
- [ ] P1: real current portfolio inputs for precommit budget.
  `_current_portfolio()` still returns fixed zeros. Replace with strict account
  summary + option position reads; account/position/Greek gaps must block new
  entry, not default to zero.
- [ ] P1: ledger/display settlement and final PnL fields.
  Add settlement event count, cashflow, option realized PnL status, final PnL
  status, and visible non-OK display for `DATA_GAP` / `ESTIMATED`.
- [ ] P1: no-snapshot orphan hedge policy decision.
  v3.2.1 chose safe manual cleanup display. Later decide whether to keep this
  as the permanent policy or add ownership-proven reduce-only cleanup with
  explicit config and tests.

## Redundancy / Cleanup Candidates

- [ ] Review `realsrc/src/authorization.py`.
  Runtime authorization commands are no longer part of the FMZ surface and the
  bundle excludes this module. Keep it only if tests still need it as a legacy
  pure-function reference; otherwise remove in a dedicated cleanup release.
- [ ] Remove or rewrite stale docs that still describe authorization prompts as
  runtime behavior. Historical handoffs may remain, but current continuation
  docs should state confirmation-code-only interaction.
- [ ] Review placeholder budget fields:
  `short_vega = 0.0` and `hedge_margin_reserve = 0.0` in precommit live data.
  These are not acceptable long-term risk inputs.
- [ ] Keep `HEDGE_MAKER_FIRST_REDUCE_ENABLED = False` until live/order-book
  evidence proves maker-first reduce lowers cost without increasing stuck
  pending risk.

## Guardrails For Every Iteration

- [ ] Write failing tests before production fixes.
- [ ] Do not weaken `evaluate_precommit_checks()`, `gate_decision()`,
  execution feasibility, risk-exit budget, or the V32/V313 pending hedge
  single-flight controller.
- [ ] Do not reintroduce runtime commands beyond `执行:<确认码>`,
  `EXECUTE:<确认码>`, or bare confirmation code.
- [ ] Do not auto-close no-snapshot perp exposure without ownership evidence.
- [ ] After code changes, run:
  `realsrc/tests/run_all.py`, `realsrc/build_bundle.py --check`, and
  `py_compile` on the latest delivery artifact.
