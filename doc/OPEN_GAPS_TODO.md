# Open Gaps And Optimization TODO

This document is the running work queue for the current manual-gate execution
layer. Keep it updated on every small-version iteration. Do not delete an item
until the code, tests, bundle, and delivery notes prove it is closed.

## Current Baseline

- Current target line: `v1`
- Latest completed release: `v1`
- Delivery rule: every small version must keep a versioned backup under
  `artifacts/`, refresh `artifacts/spm_manual_gate_execution_fmz.py`, and keep
  `artifacts/最新交付/` to exactly one current versioned FMZ file.
- Boundary rule: local tests and bundle checks are not FMZ live proof.

## Closed In v1

- [x] Formal live-validation version label: `STRATEGY_VERSION = "v1"`.
- [x] Real-fill entry alignment from the Deribit/Binance public-data audit:
  protection leg keeps mark-derived persistent maker first, then allows the
  controlled taker fallback after 60 seconds when ask depth and net-credit floor
  still pass.
- [x] Short leg remains blocked until protection fill coverage exists, then uses
  mark-derived maker pricing with a 15-second wait by default.
- [x] `LogStatus` now surfaces protection-leg wait budget: elapsed time,
  fallback threshold, remaining time, and maker/taker-fallback state.
- [x] Delivery evidence refreshed for `artifacts/最新交付/spm_manual_gate_execution_fmz_v1.py`.

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
- [x] P2: clarify `HEDGE_REDUCTION_RATIO` without renaming it. The current
  config comment now states that it is a legacy full-target ratio only when
  `HEDGE_GAMMA_AWARE_ENABLED=False`; default V32 gamma-aware sizing uses
  `RAW_FULL_DELTA` for `full_target` and applies SOFT scaling later. The name is
  kept for config compatibility and entry risk-anchor policy context.

## Closed In v3.2.14

- [x] P1: enforce TEST profile as an absolute dry-run boundary for V32 hedge
  cleanup. Orphan/reduce-only hedge cleanup can still bypass the ordinary hedge
  gate, but `_hedge_policy_submit()` now receives `allow_live=False` unless the
  normalized run profile is `LIVE`.
- [x] P1: prevent local ledger drift from returning an active position to the
  entry-planning screen. `run_cycle()` now treats a persisted `_POSITION_KEY`
  snapshot as an active position even when `ledger_get_state()` has fallen back
  to `NO_POSITION`.

## Closed In v3.2.15

- [x] P2: mark V32 `episode_cost_bps` in `POSITION_MANAGE` as
  `reserved_not_computed` telemetry instead of displaying it as `cost_bps`.
  This avoids implying that the runtime has computed realized cumulative
  slippage/fees.
- [x] P2: add taker-specific tick rounding for `_post_taker_once()`. Buy taker
  fallback now rounds up to cross the quoted ask after tick alignment, while
  maker buy rounding remains passive.

## Closed In v3.2.16

- [x] P0/P1: add `LIFECYCLE_MAP.md`, mapping manual intake through boot,
  recovery, plan, entry, position management, hedge, settlement, accounting,
  archive, and display, including current tests and missing coverage.
- [x] P0/P1: startup orphan Binance hedge cleanup now has a strict safe-evidence
  automatic reduce-only path. With no option short risk, a successful Binance
  position read, successful Deribit option/open-order reads, no unknown active
  orders, and Binance order lifecycle support, `RUN_PROFILE=LIVE` submits one
  reduce-only cleanup order. `RUN_PROFILE=TEST` uses the same evidence path but
  remains dry-run only.
- [x] P1: missing Binance order lifecycle support keeps startup orphan cleanup
  in manual-only mode and does not submit an order; `LogStatus` shows a Chinese
  manual reduce-only cleanup instruction.

## Closed In v3.2.17

- [x] P1: start the centralized deterministic lifecycle scenario matrix in
  `realsrc/tests/test_lifecycle_matrix.py`. The harness runs real `run_cycle()`
  loops, captures parsed `LogStatus` tables, checks `_G`/ledger state, and
  tracks no-order evidence.
- [x] P1 UX: TEST plan-phase `RUN_PROFILE` display now says
  `测试模式：不会真实下单，全部真实交易门强制关闭` instead of the previous
  English `live gates forced off` wording.
- [x] P1: first matrix rows cover TEST no-order plan status, LIVE plan gate
  status, and `_POSITION_KEY` snapshot with lost `NO_POSITION` state entering
  `POSITION_MANAGE` while hiding the plan menu.

## Closed In v3.2.18

- [x] P1: expand `realsrc/tests/test_lifecycle_matrix.py` to cover additional
  TEST no-order scenarios inside real `run_cycle()` loops: take-profit
  qualified but no exit order, short-flat/protection-residual but no recovery
  order, hedge-ready but no Binance order, and startup orphan cleanup dry-run.
- [x] P1: add the first startup orphan negative-evidence matrix row: no option
  short risk plus Binance perp plus unknown active orders now displays orphan
  manual only-reduce cleanup and submits no Binance order.
- [x] P1 UX/recovery: classify that unknown-active-order orphan case as
  `ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED` instead of a generic
  `RECOVERY_BLOCKED`, preserving fail-closed behavior while giving the trader a
  clearer manual cleanup instruction.

## Closed In v3.2.19

- [x] P1: expand `realsrc/tests/test_lifecycle_matrix.py` through the
  confirmation-code and precommit boundary. New rows cover valid confirmation
  locking with entry gate closed and no orders, wrong confirmation code no
  lock/no order, and unknown same-leg active option order blocking precommit.
- [x] P1 UX: status panels now surface last-command outcomes in Chinese first:
  accepted confirmation, invalid/stale confirmation, duplicate confirmation,
  and ignored non-confirmation command.
- [x] P1 UX: precommit failed checks now render Chinese semantics first, with
  raw check keys in parentheses for audit. `no_unknown_orders` now reads as
  `未知活动订单/同腿冲突订单阻断（no_unknown_orders）`.

## Closed In v3.2.20

- [x] P1/P0-adjacent: expand `realsrc/tests/test_lifecycle_matrix.py` through
  protected-entry multi-loop behavior. New rows cover full protection+short
  fill snapshot freeze, protection fill with no short fill and no naked short,
  short partial fill entering position management, and pending protection maker
  order idempotency across loops.
- [x] P1 UX: locked entry progress is now surfaced in Chinese first:
  `保护腿已成交`, `卖方腿未成交`, and `未形成期权空头` are visible when protection
  fills but the short leg does not.
- [x] P1 safety/UX: a partial short fill now immediately displays as
  `POSITION_MANAGE` / `开仓部分成交·部分垂直持仓` instead of remaining on
  `PLAN_LOCKED`.
- [x] P1 accounting semantics: entry `fill_count` now counts actual filled
  execution records only; zero-fill order events remain available as
  `order_event_count`.

## Closed In v3.2.21

- [x] P1: expand `realsrc/tests/test_lifecycle_matrix.py` with rows 014-016:
  TEST confirmation-code dry/no-order locking, protection cancel late-fill
  idempotency, and LIVE risk-exit ask-depth data-gap no-buyback behavior.
- [x] P1 UX: risk-exit blocked reasons now render Chinese-first in `LogStatus`
  and low-frequency `Log` summaries. Structured context still preserves the
  internal reason code such as `EXIT_DEPTH_DATA_GAP` for audit/debug.
- [x] P1 safety evidence: the risk-exit depth-gap row proves missing sell-depth
  does not submit a Deribit buyback order and, with hedge gate disabled in the
  scenario, does not submit a Binance hedge fallback.

## Closed In v3.2.22

- [x] P1: expand `realsrc/tests/test_lifecycle_matrix.py` with rows 017-019:
  LIVE TP maker buyback idempotency, LIVE risk-exit taker buyback idempotency,
  and LIVE risk-exit ask-above-cap no-over-spend behavior.
- [x] P1 UX/recovery: add rows 032-033 for startup recovery read failures.
  Binance hedge-position read failure and Deribit option-position read failure
  now keep `RECOVERY_BLOCKED`, submit no orders, and display Chinese
  manual-check guidance in `LogStatus`.
- [x] P1 delivery evidence: v3.2.22 refreshes the generated/source/latest FMZ
  bundle surfaces with matching SHA256
  `54EE383E2C7C6776547AF03224DC22A3F87A264399D6903E93FAF7B551AED988`;
  local verification is still not FMZ live proof.

## Closed In v3.2.23

- [x] P1: expand `realsrc/tests/test_lifecycle_matrix.py` with rows 020-023:
  LIVE risk-exit quote gap no-buyback, LIVE risk-exit insufficient-depth
  no-buyback, LIVE TP cancel-late-fill accounting, and LIVE partial-exit
  next-loop completion without double-counting.
- [x] P1 UX: rows 020-021 verify `LogStatus` renders the Chinese
  risk-exit blocker and does not expose `EXIT_QUOTE_DATA_GAP` /
  `EXIT_DEPTH_INSUFFICIENT` as the primary operator message.
- [x] P1 delivery evidence: v3.2.23 refreshes the generated/source/latest FMZ
  bundle surfaces with matching SHA256
  `9D9DA5FEFB52E541D00C617E47D5C1D8C06D3EDD078EE061D951279D1EC34CCB`;
  local verification is still not FMZ live proof.

## Closed In v3.2.24

- [x] P1: expand `realsrc/tests/test_lifecycle_matrix.py` with rows 024-026:
  LIVE V32 hedge pending-order single-flight, LIVE missing-order-id
  unknown-submit guard, and LIVE pending terminal fill history idempotency.
- [x] P1 UX: hedge policy reasons `PENDING_ACTIVE`,
  `SUBMIT_UNKNOWN_RECENT`, `PENDING_FILLED`, and related pending/stale states
  now render Chinese-first in `LogStatus` instead of raw-code-primary text.
- [x] P1 delivery evidence: v3.2.24 refreshes the generated/source/latest FMZ
  bundle surfaces with matching SHA256
  `FAD203040A4FC498F323724D984F42C0E841EE95DC6DB1E890192055EF214B25`;
  local verification is still not FMZ live proof.

## Closed In v3.2.25

- [x] P1: expand `realsrc/tests/test_lifecycle_matrix.py` with rows 027-030:
  LIVE V32 SOFT initial hedge add, LIVE HARD trigger while add cooldown is
  active, LIVE final-3h SOFT-add suppression with no Binance order, and LIVE
  reduce-confirmed reduce-only unwind.
- [x] P1 UX: hedge policy reasons `SOFT_TRIGGER_INITIAL`,
  `HARD_TRIGGER_EMERGENCY`, `FINAL3H_SOFT_ADD_SUPPRESSED`, and
  `REDUCE_CONFIRMED` now render Chinese-first in `LogStatus` instead of
  raw-code-primary text.
- [x] P1 delivery evidence: v3.2.25 refreshes the generated/source/latest FMZ
  bundle surfaces with matching SHA256
  `4A773FBADF69E33F3E9147B63E1D0F3E67443A11D1709A7640C91340927242A8`;
  local verification is still not FMZ live proof.

## Closed In v3.2.26

- [x] P1: complete the centralized deterministic lifecycle scenario matrix
  through the required 40 numbered rows. New rows 035-040 cover settlement
  option-read gap false-settle prevention, short-leg settlement idempotency,
  both-leg settlement archive/final PnL, closed archive no-duplicate behavior,
  missing settlement price `DATA_GAP` accounting, and settlement-with-perp
  reduce-only cleanup before archive.
- [x] P1 UX/accounting: `POSITION_MANAGE` ledger detail now exposes
  `settlement_state`, and the settlement/protection recovery/option realized
  PnL/final PnL rows render Chinese-first operator text instead of
  `Settlement`, `Protection recovery`, `status=...`, or raw
  `ORPHAN_HEDGE_UNWIND` as the primary read-screen text.
- [x] P1 delivery evidence: v3.2.26 refreshes the generated/source/latest FMZ
  bundle surfaces with matching SHA256
  `32E5D0DE17CA822E6715C44A58F3FCF5707AA0C1A9924B876C84568DE1FB18F1`;
  local verification is still not FMZ live proof.

## Closed In Final v3.2.26 Audit Package

- [x] P1: add row 041 to cover the explicit repeated-run protection recovery
  no-double-count requirement. The row proves a protection-leg recovery sell is
  submitted once, archived with one `protection_recovery_history` item, and not
  repeated on the next `run_cycle()`.
- [x] P1: produce `AUDIT_REPORT.md` with final local verdict
  `SMALL_SIZE_LIVE_TEST_READY`, severity table, lifecycle audit, scenario
  matrix summary, recovery decision table, accounting audit, operational
  runbook, and residual live-test risks.
- [x] P1: produce `UX_STATUS_PANEL_AUDIT.md` with plan/position panel specs,
  Chinese-first wording rules, machine-code display rules, before/after
  examples, display scenario matrix, and operator UX runbook.
- [x] P1: update `TEST_SUMMARY.md` with the final local Go/No-Go verdict and
  refreshed evidence: full local suite `397 passed, 0 failed`; lifecycle matrix
  plus live-default version tests `47 passed, 0 failed`.
- [x] Boundary evidence: no new FMZ artifact version was produced by this final
  report/test-only package; latest operator artifact remains
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_26.py`. Local
  verification remains not FMZ live proof.

## Closed In v3.2.27

- [x] P1 UX: verified and closed the Opus 4.8 finding that reachable V32 hedge
  controller reasons could appear as raw machine codes in the main
  `POSITION_MANAGE` read screen. `REASON_CN` now covers steady-state,
  deadband, cooldown, min-hold, hysteresis wait, target data gap, policy
  disabled, reverse-unwind, soft-confirmed, crash, and Binance position-read
  failure reasons without adding a second display path.
- [x] P1 coverage: `test_v32_policy_reasons_are_chinese_mapped` now enumerates
  reachable V32 policy reasons, and the crash observability screen test asserts
  `CRASH_TRIGGER_SPEED` is not emitted as primary `LogStatus` text.
- [x] P1 delivery evidence: v3.2.27 refreshes the generated/source/latest FMZ
  bundle surfaces with matching SHA256
  `A6EC0448C69FBFF9309739AE63A01CF2A1AA16218A8D1BD1856341F51B2BDA0C`;
  local verification is still not FMZ live proof.

## Closed In v3.2.28

- [x] P2 UX: verified and closed the Opus 4.8 note that
  `exit_campaign_state` could appear raw in secondary read-screen rows.
  `disp_exit_campaign_state_cn()` now renders exit/long-recovery campaign
  states such as `WORKING_LONG`, `LONG_RESIDUAL_ONLY`, `PAUSED_BY_BUDGET`, and
  `PAUSED_BY_DATA` as Chinese-first text in the lifecycle note, pipeline echo,
  and console rows.
- [x] P2 coverage: `test_exit_campaign_states_are_chinese_mapped` and
  `test_position_manage_exit_campaign_state_is_chinese_first` were added before
  the production display change, followed by
  `test_long_recovery_hint_does_not_expose_raw_exit_state`; together they now
  prevent raw exit-campaign states from becoming operator-facing primary text.
- [x] P2 delivery evidence: v3.2.28 refreshes the generated/source/latest FMZ
  bundle surfaces with matching SHA256
  `A29EA7AB388AEF2B154BE850A9B4774E3FEFF7FDDFA34327F79FF0939BE308B6`;
  local verification is still not FMZ live proof.

## Must Fix Next

- [ ] No open must-fix currently identified. Next required evidence is FMZ
  small-size live-test acceptance with the exact current artifact, saved FMZ
  logs, and exchange state snapshots.

## Redundancy / Cleanup Candidates

- [ ] No open cleanup candidate currently identified. Keep this section active
  for the next audit pass rather than deleting it.

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
