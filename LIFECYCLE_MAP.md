# Lifecycle Map

Current source line mapped from `realsrc/src/` after the v3.2.28 Opus follow-up
audit patch.
This document is evidence inventory, not FMZ live proof.

## Current Version

- `STRATEGY_VERSION`: `3.2.28-manual-gate`
- Main orchestrator: `strategy.run_cycle(now_ms=None)`
- FMZ loop entry: `strategy.main()`
- Editable source: `realsrc/src/`
- Generated bundle: `realsrc/spm_manual_gate_execution_fmz.py`
- Latest local delivery after build: `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_28.py`

## Persisted Keys

| Key | Owner | Purpose |
|---|---|---|
| `spm_manual_context_v1` | `strategy` | Current manual decision/config context. |
| `spm_plan_menu_v1` / `spm_plan_menu_meta_v1` | `strategy` | Stable displayed candidate menu and menu metadata. |
| `spm_reco_lib_v1` / `spm_lib_build_ts_v1` | `strategy` | Lockable recommendation library and build time. |
| `spm_locked_plan_v1` | `strategy` | Confirmation-code locked plan plus entry progress. |
| `spm_entry_snapshot_v1` | `strategy` | Frozen position snapshot used as position truth after entry/adoption. |
| `spm_state_v1` | `ledger` | Local lifecycle state. |
| `spm_ledger_v1` | `ledger` | Inventory ledger. |
| `spm_recovery_verdict_v1` | `strategy` | Startup/recovery verdict and manual-cleanup state. |
| `spm_hedge_policy_v32_state` | `strategy` | V32 hedge controller state and pending hedge order. |
| `spm_closed_history_v1` | `strategy` | Closed position archive. |
| `spm_cmd_ledger_v1` | `cmd_router` | FMZ command idempotency ledger. |
| `spm_last_command_v1` | `strategy` | Last command display/audit state. |
| `spm_startup_self_check_v1` | `strategy` | One-shot startup self-check summary. |
| `spm_session_id_v1` / `spm_refresh_seq_v1` | `strategy` | Command idempotency and refresh sequencing. |
| `spm_plan_trace_v1` | `strategy` | Plan-build diagnostics. |
| `spm_last_log_summary_v1` / `spm_last_log_summary_ts_v1` | `strategy` | Event-log dedupe state. |

## Stage Table

| Stage | Entry Point | Reads | Writes | Exchange Reads | Exchange Writes | Dry-Run / TEST Behavior | Failure / Data Gap Behavior | Operator Display | Current Tests | Missing / Weak Tests | Risk Type |
|---|---|---|---|---|---|---|---|---|---|---|---|
| manual decision | `strategy._manual_context_for_cycle()` | config constants, `spm_manual_context_v1` | `spm_manual_context_v1` | optional GEX context via stdlib HTTP | none | no orders | invalid manual context blocks lockability | console + overview show manual gate state | `test_manual_gate.py`, `test_manual_lineage.py`, `test_v3_0_7_gex_context_bundle.py` | no full multi-loop display matrix for stale/expired manual context | display / plan-risk gating |
| FMZ boot | `strategy.main()`, `_startup_self_check()` | config, `_G` state | `spm_startup_self_check_v1`, recovery verdict via `startup_recovery_check()` | Deribit index/instruments/account/options; Binance hedge position when configured | cancels entry orders during startup recovery only | self-check is read-only; recovery order cancel path still depends on live Deribit cancel helpers | read failures become explicit self-check/recovery gaps | overview startup row | `test_startup_self_check_records_read_only_interface_statuses`, recovery tests | no deterministic `main()` multi-loop boot harness with captured `LogStatus` | recovery / display |
| startup recovery | `strategy.startup_recovery_check()` | `spm_entry_snapshot_v1`, `spm_locked_plan_v1` | `spm_recovery_verdict_v1`, may adopt `_POSITION_KEY`, may clear locked plan | strict Deribit option positions; Binance position or Deribit future; open orders | cancels known entry orders before verdict | no generic order submit; cancel path is live helper behavior | option/hedge/open-order read failures block recovery; entry-progress mismatch blocks | recovery/manual cleanup rows through `run_cycle()` | `test_recovery.py`, `test_v3_0_8_entry_recovery.py`, `test_settlement_reconcile.py`, `test_startup_orphan_cleanup.py`, rows 031-034 | FMZ live boot display still requires operator observation | recovery / risk-reduction |
| plan menu | `strategy._build_menu()`, `build_recommendation_library()` | manual context, market context, stable menu, config signature | `spm_plan_menu_v1`, `spm_plan_menu_meta_v1`, `spm_plan_trace_v1`, `spm_reco_lib_v1` | Deribit option chain, tickers, account/SPM simulations | none | no orders | missing VRP/context can display candidates but not lockable; data gaps block hard checks | fixed candidate table, plan previews, checks | `test_run_cycle.py`, `test_integrated_flow.py`, `test_integration_dryrun.py`, `test_plans.py`, rows 001-002/007-009/014 | FMZ live visual wrapping still requires screen observation | display / no-risk |
| confirmation code | `cmd_router.route_command()`, `strategy._handle_execute()` | `spm_reco_lib_v1`, command ledger | `spm_cmd_ledger_v1`, `spm_last_command_v1`, `spm_locked_plan_v1` | none | none | no orders | unknown/duplicate/stale commands ignored and recorded | console shows last command/outcome | `test_cmd_router.py`, `test_run_cycle.py`, rows 007-009/014 | FMZ command field must be configured as `执行` string in live robot | operator action gate |
| precommit | `strategy._attempt_commit()`, `_build_precommit_live()` | locked plan, manual context, current portfolio, recovery, open orders | locked plan entry progress, `_POSITION_KEY` if adoption/full entry | Deribit option positions, open orders, account summary, ticker/quotes, SPM simulate | none directly before entry step | entry gate blocks live order; TEST returns dry entry intent | stale lineage, conflict orders, data gaps, budget/feasibility failures block | precommit/check tables | `test_precommit.py`, `test_current_portfolio.py`, `test_run_cycle.py`, `test_v3_0_8_entry_recovery.py`, row 009 | no open local P0/P1; live exchange response shapes remain acceptance risk | new-risk gate |
| protected entry | `execution.exec_entry_campaign_step()`, `strategy._attempt_commit()` | locked plan entry progress, quotes, active protection order | locked plan entry progress, `_POSITION_KEY`, ledger state | Deribit ticker/instrument/order state/order book | Deribit buy protection, sell short, cancel protection maker | TEST/live gate yields dry intent; no real entry when gate closed | quote/order/read/cancel gaps return explicit states; partial fills are adopted into safe snapshots | console shows entry campaign/protection order | `test_execution.py`, `test_v3_0_8_entry_recovery.py`, rows 010-015 | live fill/cancel latency remains acceptance risk | creates option risk |
| snapshot freeze | `build_vertical_entry_snapshot()`, `_attempt_commit()`, `_adopt_entry_progress_or_block()` | fills, locked plan, manual lineage | `spm_entry_snapshot_v1`, `spm_locked_plan_v1`, ledger state | may re-read positions for adoption | none | dry entries do not create live snapshot unless adopted from real progress | precommit failure after progress can freeze partial/protection-only snapshot | position manage display on next cycle | `test_position.py`, `test_v3_0_8_entry_recovery.py`, `test_manual_lineage.py`, rows 010-012/034 | no open local P0/P1 | state/accounting |
| position manage | `strategy.manage_cycle()` | `_POSITION_KEY`, recovery verdict, hedge policy state | snapshot updates, hedge state, histories, archive | strict Deribit positions/open orders/quotes; Binance hedge position/order | exits, protection recovery, Binance hedge submit | v3.2.14 forces V32 hedge submit dry unless `RUN_PROFILE=LIVE`; option exits/recovery use effective gates | option read failure becomes reconcile data gap; quote/risk gaps displayed | `持仓总览`, `止盈/退出预算`, `风险与对冲`, `记账/对账/恢复` | `test_run_cycle.py`, `test_display.py`, `test_display_settlement_fields.py`, rows 003-006/016-041, `UX_STATUS_PANEL_AUDIT.md` | FMZ viewport/rendering still requires live screen observation | manages/reduces risk |
| TP / risk exit | `_evaluate_take_profit()`, `exec_exit_buyback_step()`, `_apply_exit_fill()` | snapshot, quotes, risk budget | exit history, realized spend, remaining short qty | Deribit ticker/instrument/order state/order book | buy short back; cancel residual order | exit gate controls live; TEST should dry through effective gates | missing quote/depth/cap blocks; DTE gate pauses ordinary TP | TP/risk-exit table | `test_takeprofit.py`, `test_execution.py`, `test_run_cycle.py`, rows 016-023 | no open local P0/P1; live order lifecycle still acceptance risk | reduces option risk |
| V32 hedge policy | `_evaluate_hedge()`, `_hedge_policy_plan()`, `_hedge_policy_submit()` | snapshot, risk, hedge policy state | hedge policy state, hedge execution history | Binance position/order/ticker, Deribit quote/risk inputs | Binance Buy/Sell through `bnc_submit_hedge_order()` | TEST hedge submits dry via `allow_live=False`; live requires lifecycle support | Binance position read gap fail-closed; pending blocks duplicate; missing order ID guards | risk/hedge table | `test_v3_1_4_hedge_policy.py`, `test_v3_0_9_binance_hedge.py`, `test_binance_io.py`, `test_v32_policy_reasons_are_chinese_mapped`, rows 024-030/040 | no open local P0/P1; live Binance API latency remains acceptance risk | hedge risk control |
| settlement reconcile | `_settlement_reconcile_snapshot()` | snapshot, strict option positions | snapshot settlement state/history/cashflow/PnL | Deribit strict option positions, settlement/index fallback | none | no orders | option read failure does not mutate; missing settlement price marks data gap | ledger/recovery table | `test_settlement_reconcile.py`, `test_display_settlement_fields.py`, rows 035-040 | no open local P0/P1 | accounting / risk-state |
| protection recovery | `exec_protection_recovery_step()`, `_apply_protection_recovery_fill()` | snapshot long qty, quotes, exit gate | protection recovery history, realized recovery value/fees, long qty | Deribit ticker/instrument/order state | sell protection leg; cancel residual | exit gate controls live; TEST stays no-real-order through effective gates | no bid / quote gap holds residual | TP/ledger tables | `test_takeprofit.py`, `test_settlement_reconcile.py`, `test_execution.py`, rows 004/041 | no open local P0/P1 | reduces/monetizes residual |
| orphan hedge cleanup | startup recovery plus `_startup_orphan_cleanup_decision()`, `_submit_orphan_hedge_cleanup()`, `_orphan_hedge_cleanup_detail()`, and normal `manage_cycle()` orphan hedge path | recovery verdict, hedge state, Binance position | recovery verdict, hedge policy/hedge history in position-managed path | Binance position/order/ticker, Deribit option/open orders | startup no-snapshot orphan can submit one Binance reduce-only cleanup in LIVE only when strict evidence is present; position-managed orphan can submit reduce-only hedge | TEST uses the same evidence path but `_hedge_policy_submit(... allow_live=False)` returns dry-run only | missing lifecycle support or missing explicit safe evidence stays manual cleanup; pending hedge order blocks duplicate submit | `ORPHAN_HEDGE_AUTO_CLEANUP` or `ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED` phase | `test_startup_orphan_cleanup.py`, `test_orphan_hedge_without_snapshot_has_explicit_manual_cleanup_phase`, `test_test_profile_orphan_hedge_cleanup_stays_dry_even_when_gate_bypassed`, rows 006/031-033/040 | no open local P0/P1 | risk-reducing cleanup |
| closed archive | `_archive_closed()` | snapshot, hedge policy pending state | `spm_closed_history_v1`, clears `_POSITION_KEY`, ledger state `CLOSED`, recovery OK, hedge state reset | none directly | none | no orders | refuses archive if hedge pending remains | ledger table / phase | `test_settlement_reconcile.py`, rows 037-038/041 | no open local P0/P1 | final accounting |

## Current State Transition Sketch

```text
manual context valid
  -> PLAN_MENU_READY / HARD_APPROVAL_WAIT
  -> EXECUTE confirmation code
  -> PLAN_LOCKED
  -> precommit
  -> ENTRY_WORKING
  -> POSITION_MANAGE
  -> TAKE_PROFIT_READY / EXIT_PREFERRED / HEDGE_READY / HOLD
  -> SHORT_FLAT_LONG_RESIDUAL
  -> protection recovery / settlement / hedge unwind
  -> CLOSED archive

startup recovery may instead enter:
  RECOVERY_BLOCKED
  ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED
  POSITION_MANAGE when `_POSITION_KEY` exists
```

## Immediate Gaps From This Map

1. `LIFECYCLE_MAP.md` and the incremental `TEST_SUMMARY.md` now exist, and the
   centralized deterministic lifecycle matrix now has 41 numbered rows. The
   required `AUDIT_REPORT.md`, `UX_STATUS_PANEL_AUDIT.md`, and final local
   Go/No-Go verdict are produced.
2. The centralized deterministic lifecycle matrix in
   `realsrc/tests/test_lifecycle_matrix.py` now covers plan display,
   confirmation-code lock/reject behavior, precommit unknown-order blocking,
   protected-entry full/partial/pending states, TEST no-order
   position-management paths, startup orphan dry-run, one unknown-active-order
   negative evidence row, one restart/state-drift row, V32 hedge order/trigger
   branches, settlement false-read/idempotency, archive, final PnL, DATA_GAP
   accounting, settlement-with-perp reduce-only cleanup, and protection-recovery
   repeated-loop no-double-count behavior.
3. No-snapshot startup orphan hedge cleanup has the strict safe-evidence LIVE
   auto reduce-only path, TEST dry-run proof, unknown-active-order manual
   cleanup, Binance read-failure, Deribit read-failure, and lifecycle-unsupported
   tests.
4. The recovery decision table required by the goal is in `AUDIT_REPORT.md`.
5. UX tests cover the required primary panels and `UX_STATUS_PANEL_AUDIT.md`
   records the Chinese-first/raw-code-secondary audit. v3.2.27 adds explicit
   coverage that reachable V32 hedge policy reasons map to Chinese text before
   reaching the trader screen. v3.2.28 adds equivalent coverage for
   exit-campaign states before they reach lifecycle, pipeline, and console rows.
6. Entry, exit, settlement, protection recovery, archive, and hedge idempotency
   have targeted local tests; FMZ live acceptance remains outside local proof.

## Next Highest-Risk Work Item

No open local P0/P1 target remains in this map. The next required evidence is
external to the repository: FMZ live-test acceptance using the exact current
artifact and saved exchange/log evidence.
