# UX Status Panel Audit

## Verdict

`PASS_FOR_SMALL_SIZE_LIVE_TEST`

The current `LogStatus` surface is usable as the trader's primary read screen
for the audited small-size live-test workflow. The display separates plan phase
from position management, keeps runtime interaction confirmation-code-only, and
renders the covered risk/accounting blockers in Chinese-first text. v3.2.27
also closes the Opus 4.8 P1 finding that some V32 hedge controller reasons could
leak as raw primary text. v3.2.28 closes the related P2 note that exit-campaign
state codes could appear raw in secondary lifecycle/pipeline rows.

This is not a statement that FMZ live rendering has been observed. It is a local
artifact/source audit backed by deterministic `LogStatus` parsing tests.

## Design Goals

The panel must let a trader answer these questions without reading code:

- What phase am I in?
- Will this robot place real orders?
- Is a new entry allowed?
- If blocked, why?
- Is there an active position or partial entry?
- How much short/protection quantity remains?
- Is TP/risk-exit executable and within budget?
- Is Binance hedge open, pending, adding, reducing, or manually blocked?
- Is settlement complete?
- Is final PnL computed, estimated, open, or data gap?
- What should the operator do next?

## Current Layout

| Phase | Current Primary Tables |
|---|---|
| Plan phase | `交互控制台`, `运行概览`, `完整主链模块回显`, fixed candidate menu, selected/top candidate details, order intent, health/reasonable checks. |
| Locked/precommit | Same plan-phase shell, with locked-plan/last-command/precommit rows emphasized. |
| Position management | `当前环节摘要`, `运行概览`, `完整主链模块回显`, `持仓总览`, `止盈/退出预算`, `风险与对冲`, `记账/对账/恢复`. |
| Recovery/manual cleanup | Current phase and recovery/manual cleanup rows are promoted; candidate menu is not used as the primary action surface. |

## Hard Rules Checked

| Rule | Final State | Evidence |
|---|---|---|
| TEST profile must say no real trading | Pass | Matrix rows 001/003-006/014 assert `测试模式` and `不会真实下单`. |
| Runtime interaction only confirmation code | Pass | `test_cmd_router.py` rejects TP/risk/reject/stop/resume/revoke runtime commands. |
| Position management must not show plan menu as next action | Pass | Display tests and row 034 hide/downgrade plan phase during active snapshot management. |
| Raw machine codes must not be primary for critical blockers | Pass | Rows 016, 020-021, 024-030, 040 assert Chinese reason is shown and raw policy code is not primary; v3.2.27 adds a registry test for all reachable V32 hedge policy reasons plus a crash read-screen assertion. |
| Exit campaign states must be Chinese-first | Pass | v3.2.28 maps `WORKING_SHORT`, `WORKING_LONG`, `LONG_RESIDUAL_ONLY`, budget/data pauses, and idle/complete states before they reach lifecycle, pipeline, console rows, or operation hints. |
| Data gaps must not render as zero | Pass | Rows 016/020/021/039 and display tests assert explicit data-gap wording and no fake `$0.00`. |
| Placeholder cost must not look real | Pass | `test_position_manage_marks_episode_cost_as_reserved_not_computed` labels V32 episode cost as reserved telemetry. |
| Settlement/accounting rows must be Chinese-first | Pass | Row 039 and `test_display_settlement_fields.py` assert `交割结算`, `保护腿回收`, `期权已实现PnL`, `最终期权PnL`, no English primary `Settlement`, no `status=...`; row 041 keeps position/ledger tables visible during protection recovery. |

## Plan-Phase Status Spec

The plan phase is acceptable when it shows:

- current phase: waiting, menu ready, confirmation-code wait, locked, precommit,
  blocked, or dry-run;
- `RUN_PROFILE`: TEST/no real trading or LIVE action gates;
- manual gate state;
- candidate table with confirmation code, lockability, legs, expiry/DTE, delta,
  width, credit, max loss, margin relief/usage, and feasibility;
- precommit summary with Chinese failed-check reasons;
- next action: enter confirmation code, wait, refresh, fix config, or manually
  audit.

The main tables should not emphasize plan hashes, schema names, raw quality
codes, or internal IDs. Those remain audit/debug fields, not operator commands.

## Position-Management Status Spec

The position-management phase is acceptable when it shows:

- lifecycle and automatic action;
- short/protection instruments and remaining quantities;
- option marks/bid/ask/DTE/data quality;
- TP capture, frozen ceiling, remaining exit budget, cap, DTE gate;
- risk-exit ask/depth/cap blockers;
- Binance perp quantity, target/effective target, pending order, reduce-only
  state, SOFT/HARD/final-3h/orphan reason;
- entry credit, realized exit spend, protection recovery, settlement cashflow,
  option realized PnL, final PnL status;
- recovery state, active orders, unknown-order/manual-cleanup instruction.

## Before / After Examples

These are representative wording changes validated by tests or current display
helpers.

| Scenario | Before Risk | Current Read Screen |
|---|---|---|
| TEST plan phase | `live gates forced off` could be read as an implementation detail | `测试模式：不会真实下单，全部真实交易门强制关闭` |
| Wrong confirmation code | Stale/invalid code could be invisible or raw | `确认码无效/已失效` in last-command row |
| Precommit unknown order | `no_unknown_orders` primary | `未知活动订单/同腿冲突订单阻断（no_unknown_orders）` |
| Protection filled, short not filled | Could look like entry failure | `保护腿已成交 / 卖方腿未成交 / 未形成期权空头` |
| Risk-exit depth gap | `EXIT_DEPTH_DATA_GAP` primary | `卖一深度缺口` with no buyback order |
| Hedge pending | `PENDING_ACTIVE` primary | Chinese pending explanation, duplicate hedge blocked |
| SOFT/HARD hedge | `SOFT_TRIGGER_INITIAL` / `HARD_TRIGGER_EMERGENCY` primary | Chinese staged/urgent hedge reason |
| Crash / deadband hedge | `CRASH_TRIGGER_SPEED` / `LOT_DEADBAND` primary | Chinese crash/deadband reason; raw code stays out of primary read text |
| Exit / protection recovery state | `WORKING_LONG` or `PAUSED_BY_BUDGET` primary | `回收保护腿中` / `退出预算暂停` in lifecycle, pipeline, and console rows |
| Episode cost | `episode_cost_bps=12.3` could imply real cost | `reserved_not_computed` telemetry |
| Settlement | `Settlement status=COMPUTED` | `交割结算 / 已计算 / 事件 / 净现金流` |
| Settlement data gap | fake `$0.00` possible | `DATA_GAP` status, final PnL kept not computed |
| Orphan manual cleanup | generic recovery blocked | `需要人工只减清理` plus evidence gap reason |

## Display Scenario Matrix

| ID | Scenario | Status |
|---|---|---|
| UX-01 | TEST plan phase shows no real trading | Pass |
| UX-02 | LIVE plan phase shows action gates | Pass |
| UX-03 | Valid plan candidate shows confirmation code | Pass |
| UX-04 | Non-lockable/blocked plan shows Chinese reason | Pass |
| UX-05 | Wrong/stale confirmation does not lock | Pass |
| UX-06 | Precommit failed checks show Chinese first | Pass |
| UX-07 | Entry in progress shows protection-first progress | Pass |
| UX-08 | Protection-only residual shows no naked short | Pass |
| UX-09 | Partial vertical shows current qty and management mode | Pass |
| UX-10 | Normal holding shows position-management module tables | Pass |
| UX-11 | TP eligible shows budget/cap path | Pass |
| UX-12 | Risk exit blocked by depth shows depth reason | Pass |
| UX-13 | Hedge SOFT trigger shows staged hedge reason | Pass |
| UX-14 | Hedge HARD trigger shows urgent hedge reason | Pass |
| UX-15 | Pending hedge order shows no duplicate order and pending state | Pass |
| UX-16 | Settlement recognized shows settlement state | Pass |
| UX-17 | Settlement data gap shows not-computed/data-gap, not zero | Pass |
| UX-18 | Orphan auto cleanup shows reduce-only cleanup action | Pass |
| UX-19 | Orphan manual cleanup shows manual instruction and no order | Pass |
| UX-20 | Reachable V32 hedge controller reasons map to Chinese-first text | Pass |
| UX-21 | Exit campaign states map to Chinese-first text | Pass |
| UX-20 | Closed archive stores final PnL status and no active snapshot | Pass |
| UX-21 | Recovery blocked shows what to manually check | Pass |
| UX-22 | Unknown active order shows block reason | Pass |
| UX-23 | Reserved cost fields are labeled not fully computed | Pass |
| UX-24 | Critical raw policy codes are not primary human-facing text | Pass |
| UX-25 | Raw codes, when retained, are secondary audit/debug evidence | Pass |

## Machine-Code Display Rule

Machine codes are acceptable only when they are secondary to Chinese semantics,
for example:

- good: `未知活动订单/同腿冲突订单阻断（no_unknown_orders）`;
- good: `需要人工只减清理 ... UNKNOWN_ACTIVE_ORDERS`;
- bad: a table row whose main value is only `EXIT_DEPTH_DATA_GAP`;
- bad: `Settlement status=DATA_GAP value=0`.

The current high-risk lifecycle rows assert that critical hedge, risk-exit, and
settlement policy codes are not shown as the primary human message.

## LogStatus vs Log

- `LogStatus` is the primary, continuously refreshed trader screen.
- `Log` is event-oriented: orders, fills, data gaps, recovery, settlement,
  hedge transitions, or phase changes.
- Routine `POSITION_MANAGE` loops should refresh status without noisy repeated
  `Log` spam.

## Residual UX Limits

- The local parser confirms FMZ-table JSON structure, but actual FMZ visual
  wrapping/viewport behavior still requires a live robot screen check.
- Some raw codes are intentionally preserved for audit/debug. They are
  acceptable when paired with Chinese instructions and not used as the sole
  operator-facing meaning.
- This audit does not add a collapsible debug appendix because FMZ table support
  is limited; instead, debug evidence remains lower priority inside existing
  rows and logs.

## UX Runbook

1. Read `LogStatus` first; use `Log` for event confirmation.
2. In plan phase, act only on displayed confirmation codes.
3. In position phase, do not enter runtime commands; use config gates before
   startup and manual exchange action only when the panel says manual cleanup is
   required.
4. Treat `数据缺口`, `人工核对`, `未知活动订单`, and `需要人工只减清理` as stop-and-check
   states for new risk.
5. Treat `COMPUTED`, `ESTIMATED`, `DATA_GAP`, and `仍在管理中` as different PnL
   states; do not reconcile a round as final while final PnL is open/data-gap.
