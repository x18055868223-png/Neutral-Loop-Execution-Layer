# Test Summary

This is the final local test summary for the live-readiness audit goal. It is
local evidence only, not FMZ live proof.

## Current Version

- Version: `3.2.28-manual-gate`
- Latest delivery after build:
  `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_28.py`
- Boundary: local tests and bundle checks only; not FMZ live proof.

## Final Local Verdict

`SMALL_SIZE_LIVE_TEST_READY`

No unresolved P0/P1 blocker remains in the local audit evidence. The Opus 4.8
v3.2.26 P1 display finding is closed in v3.2.27 with Chinese-first V32 hedge
reason mappings and regression tests; the Opus P2 exit-campaign display note is
closed in v3.2.28. This verdict is limited to the current source and generated
artifact. FMZ live acceptance still requires deploying this exact artifact and
verifying FMZ command wiring, startup/read-only status, exchange state, and
first-cycle logs.

## Latest Full Local Verification

The latest complete local suite at v3.2.28 passed with:

- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py`
  -> `401 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py` and passed syntax
  compile plus bundle smoke checks.
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_28.py`
  -> passed

Targeted verification after the latest matrix expansion:

- lifecycle matrix + live-default version tests:
  `47 passed, 0 failed`
- `C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check`
  -> generated `realsrc\spm_manual_gate_execution_fmz.py` and passed syntax
  compile plus bundle smoke checks.
- SHA256 for the v3.2.28 generated/source/latest delivery bundle:
  `A29EA7AB388AEF2B154BE850A9B4774E3FEFF7FDDFA34327F79FF0939BE308B6`

## Lifecycle Matrix Rows

| ID | Scenario | Evidence Assertions |
|---|---|---|
| 001 | TEST plan phase shows no real trading | `run_cycle()` phase, ledger no-position, no order log, parsed `LogStatus` RUN_PROFILE Chinese text. |
| 002 | LIVE plan phase shows action gates | `run_cycle()` phase, parsed `LogStatus` RUN_PROFILE and action gate row, no order log. |
| 003 | TEST TP-qualified position does not exit | `POSITION_MANAGE`, TP qualified, action arbiter holds because exit is not executable, no Deribit/Binance order, position display includes TP/exit tables. |
| 004 | TEST short-flat protection residual does not recover long leg | `POSITION_MANAGE`, long residual state, no Deribit/Binance order, display keeps protection wording and TEST no-real-order text. |
| 005 | TEST hedge-ready position does not submit Binance order | `POSITION_MANAGE`, `HEDGE_READY` risk state, no Binance/Deribit order, hedge display remains visible with TEST no-real-order text. |
| 006 | TEST startup orphan cleanup is dry-run only | startup recovery marks orphan auto cleanup allowed, `run_cycle()` enters `ORPHAN_HEDGE_AUTO_CLEANUP`, step is `BINANCE_HEDGE_DRYRUN`, no Binance order, display says simulated only-reduce cleanup. |
| 007 | LIVE valid confirmation locks plan with entry gate closed | `HARD_APPROVAL_WAIT` candidate code is accepted through `EXECUTE:<code>`, `_LOCKED_KEY` is set, phase becomes `PLAN_LOCKED`, no order is submitted, status shows locked/precommit wording. |
| 008 | Wrong confirmation code does not lock or order | invalid `EXECUTE` command records `confirm_code_invalid_or_stale`, `_LOCKED_KEY` stays empty, no orders are submitted, status shows Chinese invalid/stale confirmation text. |
| 009 | Unknown same-leg option order blocks precommit | valid confirmation locks the plan, precommit fails on `no_unknown_orders`, no Deribit/Binance order is submitted, status shows `未知活动订单/同腿冲突订单阻断（no_unknown_orders）`. |
| 010 | LIVE entry protection and short fill freeze snapshot | Multi-loop entry records protection then short fill, freezes `_POSITION_KEY`, clears `_LOCKED_KEY`, enters `POSITION_MANAGE`, hides plan menu, records actual fill count, and submits no Binance order. |
| 011 | LIVE protection fill but short not filled stays safe | Protection fill is persisted under the locked plan, no position snapshot or short risk is created, Deribit short order does not fill, and status says `保护腿已成交` / `卖方腿未成交` / `未形成期权空头`. |
| 012 | LIVE short partial fill enters partial vertical management | Partial short fill creates a managed snapshot with `entry_completion_state=PARTIAL_VERTICAL`, clears the locked plan, enters `POSITION_MANAGE`, and status shows `开仓部分成交` / `部分垂直`. |
| 013 | LIVE protection maker order pending across loops | A pending protection maker order remains on the locked plan across loops, no duplicate protection order is placed, no short/Binance order is submitted, and status shows `保护腿挂单` / `maker等待`. |
| 014 | TEST confirmation code locks plan but stays dry | Bare confirmation code can lock the plan in TEST for dry validation, `_POSITION_KEY` remains empty, ledger stays no-position, and no Deribit/Binance order is submitted. |
| 015 | LIVE protection cancel late fill counted once | A persistent protection maker order that fills only after cancel is counted once in locked entry progress, `prot_done` stays at 0.1, no duplicate protection fill is recorded, and no position snapshot is created without short fill. |
| 016 | LIVE risk-exit ask-depth data gap blocks buyback readably | Hedge-ready risk exit with missing sell-depth keeps `EXIT_DEPTH_DATA_GAP` in structured context, submits no Deribit buyback or Binance hedge, and `LogStatus` renders `卖一深度缺口` instead of exposing the raw code as the primary message. |
| 017 | LIVE take-profit buyback fills once within budget | TP-qualified position submits one Deribit maker buyback, applies the fill to flatten the short leg, records `S_SHORT_FLAT_LONG_RESIDUAL`, and a repeated loop does not double count or rebuy. |
| 018 | LIVE risk-exit depth-sufficient buyback uses taker once | Hedge-ready risk exit with ask <= cap and sufficient depth submits one Deribit taker buyback, records `risk_exit`, flattens the short leg, and a repeated loop is idempotent. |
| 019 | LIVE risk-exit ask above cap does not over-spend | Hedge-ready risk exit with ask above the budget cap submits no Deribit/Binance order, keeps the short leg open, and `LogStatus` renders `卖一高于预算上限` instead of a raw-code-primary message. |
| 020 | LIVE risk-exit quote gap blocks buyback readably | Hedge-ready risk exit with no reliable ask submits no Deribit/Binance order when hedge is not executable, preserves `EXIT_QUOTE_DATA_GAP`, and `LogStatus` renders the Chinese reason instead of the raw code. |
| 021 | LIVE risk-exit insufficient depth blocks buyback readably | Hedge-ready risk exit with ask <= cap but insufficient ask depth submits no Deribit/Binance order when hedge is not executable, preserves `EXIT_DEPTH_INSUFFICIENT`, and displays the Chinese blocker. |
| 022 | LIVE TP cancel late fill books once | TP maker buyback that fills only after cancel records one exit history item, reduces the remaining short leg to the residual amount, and the next loop uses only the residual size without double-counting the late fill. |
| 023 | LIVE partial TP exit completes next loop without double-counting | After a partial exit fill, the next run-cycle buys back only the remaining short quantity, records a second fill, moves to `S_SHORT_FLAT_LONG_RESIDUAL`, and does not duplicate the first fill. |
| 024 | LIVE hedge pending order blocks duplicate submit readably | Risk-exit fallback submits one Binance hedge order, records a pending V32 hedge order, the next loop sees `PENDING_ACTIVE`, submits no duplicate, and `LogStatus` shows a Chinese pending reason. |
| 025 | LIVE hedge missing order ID sets unknown guard | Binance submit response without an order ID records `BINANCE_ORDER_ID_MISSING`, sets `last_submit_unknown_reason`, submits no immediate duplicate on the next loop, and `LogStatus` shows a Chinese unknown-submit reason. |
| 026 | LIVE hedge pending terminal fill records history once | A terminal Binance pending fill clears the pending state, writes one `hedge_execution_history` item, and a repeated loop does not duplicate the fill or submit a second hedge order. |
| 027 | LIVE V32 SOFT initial hedge add is readable | SOFT trigger submits one Binance buy hedge order with soft cross bps, keeps `reduce_only=False`, and `LogStatus` shows the Chinese SOFT reason instead of the raw code. |
| 028 | LIVE V32 HARD trigger bypasses add cooldown readably | HARD trigger submits one Binance buy hedge order despite active add cooldown, uses hard cross bps, and `LogStatus` shows the Chinese HARD reason instead of the raw code. |
| 029 | LIVE V32 final-3h SOFT add is suppressed | In the final ordinary-TP gate window, SOFT add is held with no Binance order, action arbiter stays `HOLD`, and `LogStatus` shows the Chinese final-3h suppression reason. |
| 030 | LIVE V32 reduce confirmation is reduce-only and readable | Risk recedes after reduce persistence, one Binance sell reduce-only unwind is submitted, and `LogStatus` shows the Chinese reduce-confirmed reason instead of the raw code. |
| 031 | Startup orphan with unknown active order requires manual cleanup | no option short plus Binance perp plus unknown active order enters `ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED`, no Binance order, display says manual only-reduce cleanup and includes `UNKNOWN_ACTIVE_ORDERS`. |
| 032 | Startup Binance hedge position read failure blocks readably | Binance position read failure enters `RECOVERY_BLOCKED`, submits no orders, preserves `HEDGE_POSITION_QUERY_FAILED`, and `LogStatus` shows Binance/仓位读取失败/人工核对. |
| 033 | Startup Deribit option position read failure blocks readably | Deribit option position read failure enters `RECOVERY_BLOCKED`, submits no orders, preserves `OPTION_POSITION_QUERY_FAILED`, and `LogStatus` shows Deribit/期权持仓读取失败/人工核对. |
| 034 | Snapshot exists but state key says `NO_POSITION` | `run_cycle()` enters `POSITION_MANAGE`, `_POSITION_KEY` snapshot is surfaced, plan menu hidden, position tables shown. |
| 035 | LIVE settlement option read gap does not false-settle | Expired snapshot plus option-position query failure leaves short/long quantities untouched, writes no settlement/archive/order, preserves `OPTION_POSITION_QUERY_FAILED`, and keeps the ledger table Chinese-first. |
| 036 | LIVE short settlement keeps long residual and is idempotent | Absent expired short plus present long records `SHORT_SETTLED`, leaves the long residual managed, and a second loop does not duplicate settlement events. |
| 037 | LIVE both legs settle and archive final PnL | Absent expired short and long records `BOTH_LEGS_SETTLED`, computes final option PnL, archives one closed record, and clears the active snapshot. |
| 038 | LIVE closed archive is not duplicated on next loop | After closed archive, a repeated loop leaves closed history at one record and does not recreate settlement/archive entries. |
| 039 | LIVE missing settlement price archives as DATA_GAP not zero | With no settlement/index price, closed archive stores settlement/option/final PnL as `DATA_GAP`, keeps final option PnL `None`, and does not display `$0.00` as a fake result. |
| 040 | LIVE settlement with perp submits reduce-only cleanup before archive | Both option legs settle while Binance perp remains open; the cycle submits one reduce-only orphan hedge cleanup, keeps archive pending, and does not expose `ORPHAN_HEDGE_UNWIND` raw-primary in `LogStatus`. |
| 041 | LIVE protection recovery fill is not double-counted | After short-flat long-residual recovery sells the protection leg, the first loop archives one recovery history item and the next loop submits no second sell, creates no duplicate archive, and preserves the same recovery value. |

## Matrix Coverage Status

The centralized matrix now has 41 numbered scenario rows. It covers:

- TEST no-order entry/exit/hedge/protection/orphan cases.
- Protected entry partial-fill and restart rows.
- TP/risk-exit closeout, quote/depth/cap blockers, and idempotency rows.
- V32 hedge pending/missing-order-id/fill, SOFT/HARD/final-3h/reduce rows.
- Settlement false-read, idempotency, archive, and accounting rows.
- Protection recovery repeated-loop no-double-count behavior.
- Startup orphan cleanup negative evidence rows and read-failure rows.
- Display scenarios proving Chinese-first operator text and raw-code secondary
  placement across the covered lifecycle states.
- v3.2.27 adds `test_v32_policy_reasons_are_chinese_mapped` plus a crash
  read-screen assertion so reachable V32 hedge controller reasons cannot leak as
  primary raw machine-code text.
- v3.2.28 adds `test_exit_campaign_states_are_chinese_mapped` and
  `test_position_manage_exit_campaign_state_is_chinese_first`, plus a long
  recovery hint assertion, so exit-campaign states cannot leak as primary raw
  text in position-management display rows or operation hints.

The matrix is complete for the local audit. Future rows should be added only
when FMZ live acceptance or a new audit finding exposes another edge case.

## Final Reports

- `AUDIT_REPORT.md`: produced.
- `UX_STATUS_PANEL_AUDIT.md`: produced.
- Final local Go/No-Go verdict: `SMALL_SIZE_LIVE_TEST_READY`.
