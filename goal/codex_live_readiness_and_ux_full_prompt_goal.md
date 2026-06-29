
You are auditing and hardening the current repository version of the Deribit S:PM vertical credit spread execution layer.

Treat this strategy as a real trader-facing execution service, not as a toy script. The strategy receives an upstream/manual decision, starts inside FMZ, displays candidate plans, waits for a manual confirmation code, opens a protected vertical credit spread, manages take-profit/risk-exit/hedge/accounting, survives restarts and data gaps, and finally settles or closes the round with a complete ledger.

The current artifact is an FMZ single-file strategy with `run_cycle()` as the main orchestrator and V32 Binance hedge policy enabled. Do not perform a narrow bug fix. Perform a full live-readiness audit and hardening pass from a trader’s perspective.

This task has two equally important tracks:

1. **Execution safety and accounting correctness.**
2. **Trader-facing status panel / Chinese UX correctness.**

The second track is not cosmetic. If the code is correct but the trader cannot correctly read the plan phase or position-management state, the execution layer is not live-ready.

---

## 0. Non-Negotiable Safety Principles

1. `RUN_PROFILE="TEST"` must never place real orders, including:
   - entry orders,
   - exit orders,
   - protection recovery orders,
   - hedge add/open orders,
   - hedge reduce-only orders,
   - orphan hedge cleanup orders,
   - recovery cleanup orders,
   - settlement cleanup orders.

2. `RUN_PROFILE="LIVE"` must still obey action-specific gates:
   - entry requires entry gate and all precommit checks,
   - option exit requires exit gate,
   - hedge add/open requires hedge gate,
   - hedge reduce/unwind may be allowed only when explicitly risk-reducing and policy-approved,
   - emergency reduce-only must not block risk-reducing hedge unwind or option risk reduction.

3. No new option short risk may be created without:
   - current manual context valid,
   - confirmation code valid and non-expired,
   - locked plan hash / quality code match,
   - S:PM rechecked,
   - VRP/context rechecked if required,
   - projected account budget pass,
   - no unknown or conflicting active orders,
   - execution feasibility rechecked,
   - spread/credit gates pass,
   - protection-leg-first invariant preserved.

4. No stale local snapshot may keep a nonexistent option short alive after settlement.

5. No Binance perp may remain open indefinitely after option short risk disappears if the system has enough evidence to safely reduce-only clean it.

6. If evidence is insufficient, the system must fail closed and clearly tell the operator what must be manually checked.

7. Accounting must distinguish:
   - entry credit,
   - option exit spend,
   - protection recovery,
   - option settlement cashflow,
   - hedge realized/unrealized effects,
   - final option PnL,
   - combined PnL if explicitly computed,
   - data gaps / not-computed fields.

8. Operator display must not imply a field is precise if it is only a placeholder, reserved value, estimated value, or partially computed value.

---

## 1. Required First Step: Current Lifecycle Map

Before making changes, map the current code into a lifecycle table:

```text
manual decision
→ FMZ boot
→ startup recovery
→ plan menu
→ confirmation code
→ precommit
→ entry campaign
→ snapshot freeze
→ position manage
→ TP/risk exit
→ hedge policy
→ settlement reconcile
→ protection recovery
→ orphan hedge cleanup
→ closed archive
```

For each stage, list:

- function entry point,
- persisted keys read,
- persisted keys written,
- exchange reads,
- possible exchange writes,
- dry-run behavior,
- failure/data-gap behavior,
- operator display output,
- tests currently covering it,
- missing tests,
- whether this stage can create risk, reduce risk, or only display state.

Do not proceed to patching until this lifecycle map exists.

Deliverable:

- `LIFECYCLE_MAP.md`

---

## 2. Pre-Trade / Planning / Manual Gate Audit

Trace from manual config/context to candidate menu and confirmation code.

Audit:

- manual context expiration,
- manual context hash binding,
- stable menu generation,
- stale menu invalidation after config/version/context change,
- candidate ranking and display stability,
- confirmation-code uniqueness,
- duplicate command handling,
- expired approval handling,
- VRP/context-missing behavior,
- whether a candidate can become lockable without full safety context.

Simulate:

1. valid manual context → candidate library generated;
2. expired manual context → no lockable plan;
3. stale menu after config change → no execution;
4. stale menu after strategy version change → no execution;
5. wrong confirm code → no lock;
6. duplicate confirm code / command replay → idempotent no double lock;
7. candidate rejected by VRP/context gap → shown but not lockable;
8. candidate with stale quotes → no lock or precommit failure;
9. candidate ranking changes after refresh → locked plan remains hash-bound.

Deliverable:

- tests proving stale context/menu cannot execute;
- display tests proving plan status is understandable in Chinese.

---

## 3. Precommit and Entry Audit

Audit complete entry path:

- locked plan validity,
- order conflict detection,
- protection-leg-first invariant,
- persistent maker protection order,
- controlled taker fallback,
- short leg cannot exceed filled protection amount,
- partial fill adoption,
- crash/restart during entry,
- dry-run/TEST behavior,
- LIVE gate behavior,
- fee and entry credit recording.

Simulate:

1. TEST profile: no entry order placed;
2. LIVE valid plan: protection fills, short fills, snapshot frozen;
3. protection fills, short does not;
4. short partially fills;
5. protection order active across loops;
6. cancel captures late fill exactly once;
7. active order state unreadable;
8. order cancel fails;
9. Deribit order state returns late fills;
10. FMZ returns missing order ID;
11. entry quote disappears after lock;
12. entry credit floor violated after protection fills;
13. restart with locked entry progress;
14. unknown active order on option leg blocks precommit.

Deliverable:

- regression tests proving no naked short option can be created;
- regression tests proving no real order in TEST;
- clear behavior for protection-only residual and partial vertical.

---

## 4. Position Management and Take-Profit Audit

Audit:

- frozen entry profit ceiling,
- 80% capture logic,
- DTE gate near expiry,
- risk-exit budget,
- risk-exit taker behavior,
- quote gaps,
- ask depth requirements,
- repeated loop behavior,
- stale or expired option quote behavior,
- exit fill idempotency,
- budget overspend prevention.

Simulate:

1. normal TP eligible and maker exit succeeds;
2. TP eligible but DTE too close, ordinary TP paused;
3. risk exit triggers and ask depth is sufficient;
4. risk exit triggers but ask depth missing;
5. risk exit triggers but ask depth insufficient;
6. quote missing;
7. mark/delta missing;
8. exit partial fill then restart;
9. exit fill updates realized spend exactly once;
10. repeated `run_cycle()` does not double count exit;
11. ask > cap does not over-budget buyback;
12. risk exit blocked but hedge fallback is allowed only if hedge executable.

Deliverable:

- tests proving TP cannot exceed budget;
- tests proving risk exit is fail-closed on missing depth;
- status display showing TP, risk-exit budget, DTE gate, cap, and blocker in Chinese.

---

## 5. Hedge / V32 Binance Controller Audit

Audit V32 controller end-to-end:

- current hedge position read as truth,
- target semantics,
- gamma-aware target fraction,
- SOFT/HARD trigger behavior,
- crash-speed behavior,
- final-3h soft add suppression,
- min hold / cooldown / hysteresis,
- pending order single-flight,
- stale pending order recovery,
- partial pending fill resolution,
- direction consistency,
- reduce-only unwind,
- orphan hedge cleanup,
- Binance order lifecycle support,
- missing order ID handling,
- TEST-mode hard no-submit.

Critical safety condition:

No hedge order, including orphan reduce-only cleanup, may be submitted in `RUN_PROFILE="TEST"`.

In `LIVE`, startup orphan cleanup may be automatic only when all are true:

1. no option short risk exists;
2. Binance perp position exists;
3. Binance position read succeeded;
4. Deribit option position read succeeded;
5. active/open order query succeeded;
6. no unknown active orders exist;
7. cleanup action is reduce-only;
8. side is consistent with reducing the existing position;
9. order lifecycle support is available;
10. action is clearly displayed as automatic reduce-only cleanup.

Otherwise, show manual cleanup required and do not trade.

Simulate:

1. no option short + Binance perp + clean reads + no unknown orders → reduce-only cleanup allowed in LIVE only;
2. same scenario in TEST → dry-run only, no real submit;
3. no option short + Binance read fails → manual cleanup;
4. no option short + Deribit option read fails → manual cleanup;
5. no option short + unknown active order → manual cleanup;
6. no option short + Binance order lifecycle unsupported → manual cleanup;
7. option short still exists + perp exists → normal hedge policy, not orphan;
8. pending hedge order partially fills then becomes stale;
9. Binance submit returns missing order ID;
10. Binance order state unavailable;
11. reduce-only side mapping buy/sell correctness;
12. HARD trigger bypasses soft cooldown when appropriate;
13. final-3h soft add suppressed but reduce/unwind allowed;
14. episode cost placeholders do not block HARD risk action.

Deliverable:

- tests proving TEST never submits hedge;
- tests proving startup orphan cleanup is automatic only under exact safe evidence set;
- tests proving manual cleanup branch never submits orders;
- Chinese status display clearly distinguishes:
  - normal hedge,
  - soft hedge,
  - hard hedge,
  - pending hedge,
  - orphan auto-cleanup,
  - orphan manual cleanup,
  - hedge data gap.

---

## 6. Settlement Reconciliation Audit

Audit:

- short option settlement detection,
- long/protection option settlement detection,
- grace window,
- strict position-read behavior,
- false settlement prevention when Deribit position read fails,
- settlement after restart,
- settlement while hedge still open,
- settlement while protection leg still has value/bid,
- settlement when both legs disappear,
- archived closed-state behavior,
- settlement event idempotency.

Simulate:

1. option positions read success and expired short absent → short remaining qty becomes 0;
2. option positions read failure → no settlement mutation;
3. long leg absent after expiry → long remaining qty becomes 0;
4. both legs settled + no perp → archive closed;
5. short settled + perp exists → hedge target zero and reduce-only cleanup;
6. short settled + protection still tradable → recover/sell protection if allowed;
7. short settled + protection not tradable → wait or settle via finalizer;
8. restart after settlement but before hedge cleanup;
9. restart after hedge cleanup but before closed archive;
10. repeated settlement reconciliation does not double count settlement events;
11. settlement price missing → `DATA_GAP` / `NOT_COMPUTED`, not zero.

Deliverable:

- tests proving no false settlement on read failure;
- tests proving settlement leads to correct hedge target zero;
- tests proving archive only occurs when option legs and hedge are flat or safely settled;
- Chinese status display clearly shows settlement state and remaining cleanup action.

---

## 7. Accounting / Ledger / Final PnL Audit

Audit ledger as if a real trader will use it for reconciliation:

- entry execution report,
- exit execution history,
- protection recovery history,
- hedge execution history,
- option settlement history,
- final option PnL,
- settlement cashflow,
- fees,
- realized spend,
- hedge PnL separation,
- data gaps,
- closed archive.

Required accounting semantics:

- Entry credit = short credit - protection cost - entry fees.
- Exit spend = short buyback cost + exit fees.
- Protection recovery = protection sale proceeds - protection recovery fees.
- Settlement cashflow must be explicit and signed.
- Final option PnL must include entry credit, exits, protection recovery, and settlement cashflow.
- If settlement PnL cannot be computed, display `DATA_GAP` or `NOT_COMPUTED`; never display it as 0.
- Hedge PnL must not be mixed into option PnL unless explicitly named as combined PnL.
- `episode_cost_bps` and `episode_cost_usdc` must not be displayed as real cost if they are only reserved placeholders. Rename, hide, or label them clearly as reserved / not fully computed.
- A repeated loop must not double-count any event.

Simulate:

1. normal entry → TP exit → protection recovery → closed final PnL;
2. entry → settlement worthless → no hedge → closed final PnL;
3. entry → short ITM settlement cashflow → hedge cleanup → closed final PnL;
4. protection-only residual → recovery/settlement final ledger;
5. partial vertical → exit/settlement final ledger;
6. accounting with missing settlement price → data gap not zero;
7. repeated loop does not double-count exit;
8. repeated loop does not double-count protection recovery;
9. repeated loop does not double-count settlement;
10. repeated loop does not double-count hedge events;
11. closed history contains enough fields for trader reconciliation.

Deliverable:

- accounting finalization tests;
- final closed history schema;
- Chinese ledger display showing:
  - actual net credit,
  - realized exit spend,
  - protection recovery,
  - settlement cashflow,
  - option realized PnL,
  - hedge PnL separate,
  - final PnL status,
  - data gaps.

---

## 8. Recovery and Restart Audit

Audit all restart states:

- clean no-position startup,
- locked plan startup,
- entry in progress,
- protection-only residual,
- partial vertical,
- full vertical,
- exit in progress,
- hedge pending order,
- settlement detected,
- orphan hedge,
- unknown active orders,
- missing local snapshot but exchange position exists,
- local snapshot exists but state key says `NO_POSITION`,
- closed archive exists but recovery key stale,
- no option short risk + Binance perp orphan.

Deliverable:

Create a recovery decision table:

| State | Evidence required | allow_new_open | auto_cleanup_allowed | real order allowed? | operator message | expected display |
|---|---|---:|---:|---:|---|---|

Simulate every row.

Important rule:

- If evidence is sufficient and action is reduce-only, automatic cleanup may be allowed.
- If evidence is insufficient, fail closed and show manual cleanup required.
- Never let stale recovery state block future clean no-position cycles after archive is complete.

---

## 9. Trader-Facing Status Panel / Chinese UX Audit

This is a first-class live-readiness requirement.

The display layer must help a real trader answer:

1. 我现在处于什么阶段？
2. 这个机器人是否会真实下单？
3. 当前是否可以新开仓？
4. 如果不能，原因是什么？
5. 当前是否已有持仓？
6. 短腿和保护腿还剩多少？
7. 止盈是否触发？预算够不够？
8. 风险退出是否可执行？卡在哪里？
9. 对冲是否已开、要开、要减、要清？
10. 是否有未知订单或恢复阻塞？
11. 交割是否完成？期货腿是否还在？
12. 本轮账是否完整？PnL 是已计算、估算、还是数据缺口？
13. 操作员下一步应该做什么？

### 9.1 Display Hard Rules

1. Do not display raw machine codes as the primary text for humans.
   - Bad: `HEDGE_POSITION_DATA_GAP`
   - Good: `对冲仓位读取失败：禁止新增对冲，请人工核对 Binance 持仓（HEDGE_POSITION_DATA_GAP）`
2. Do not display raw internal field names as column titles unless paired with Chinese semantics.
   - Bad: `episode_cost_bps`
   - Good: `对冲成本统计：未完整计算 / reserved（episode_cost_bps）`
3. Do not display placeholder/reserved values as precise real metrics.
4. Do not display `None`, `null`, raw Python dicts, or raw JSON fragments in trader-facing rows unless they are inside a developer/debug appendix.
5. Do not show too many low-level fields in the first screen. Use layered tables:
   - current phase summary,
   - plan candidates or position summary,
   - TP/risk-exit,
   - hedge,
   - ledger/recovery,
   - debug appendix only if needed.
6. Status panel must balance information density and readability:
   - concise titles,
   - grouped modules,
   - stable ordering,
   - no duplicated fields across too many tables,
   - enough numbers for decision-making,
   - enough Chinese explanation for action.
7. Display must clearly distinguish:
   - actual value,
   - estimate,
   - frozen entry value,
   - budget limit,
   - realized value,
   - data gap,
   - not computed,
   - reserved / placeholder.
8. During position management, plan menu should be hidden or clearly downgraded to avoid implying a new entry is available.
9. During manual cleanup required, display must prominently show:
   - what risk remains,
   - why automation is not safe,
   - what the trader must check manually,
   - that new opening is blocked until resolved.
10. All important status must be expressed in Chinese first. Machine code can be appended in parentheses for audit/debug.

### 9.2 Plan Phase Display Requirements

Plan phase display must show:

- current phase:
  - 等待人工审计,
  - 方案库就绪,
  - 待确认码,
  - 方案锁定,
  - 预提交中,
  - 禁新开,
  - 空跑.
- RUN_PROFILE:
  - TEST must say `测试模式：不会真实下单`,
  - LIVE must show which action gates are open.
- manual gate status:
  - 人工审计门已开启 / 过期 / 无效 / 等待.
- plan candidates:
  - candidate number,
  - confirmation code,
  - lockable or not lockable,
  - non-lockable reason in Chinese,
  - short leg,
  - protection leg,
  - expiry / DTE,
  - delta,
  - width,
  - net credit,
  - max loss,
  - margin used,
  - credit-on-margin,
  - 24h efficiency,
  - execution feasibility,
  - liquidity/spread warning.
- precommit state:
  - not triggered,
  - passed,
  - failed with Chinese reason.
- next action:
  - input confirmation code,
  - wait,
  - refresh plan,
  - fix config,
  - manual audit required.

Plan phase must not over-emphasize raw plan hashes, quality hashes, schema names, internal IDs, or raw machine codes.

If those are useful for audit, place them in a clearly labeled `审计追踪 / Debug` subsection, not in the first human-facing rows.

### 9.3 Position Management Display Requirements

Position management display must show:

- lifecycle:
  - 已建仓,
  - 开仓部分成交,
  - 持仓监控,
  - 止盈买回中,
  - 风险退出中,
  - 对冲监控中,
  - 交割确认中,
  - 短腿已归零,
  - 保护腿待回收,
  - 孤儿对冲清理,
  - 需要人工清理,
  - 已归档.
- option legs:
  - short instrument,
  - protection instrument,
  - remaining short qty,
  - remaining long/protection qty,
  - DTE,
  - breakeven,
  - distance to spot,
  - mark / bid / ask,
  - quote data quality.
- take-profit:
  - capture ratio,
  - target ratio,
  - frozen entry profit ceiling,
  - target profit amount,
  - short buyback reference,
  - remaining budget,
  - price cap,
  - DTE gate,
  - TP status in Chinese.
- risk exit:
  - risk trigger,
  - exit budget,
  - ask price,
  - ask depth,
  - cap pass/fail,
  - depth pass/fail,
  - why exit is blocked if blocked.
- hedge:
  - Binance perp qty,
  - hedge target,
  - effective target,
  - delta_to_trade,
  - reduce_only,
  - pending order,
  - soft/hard reason,
  - final-3h behavior,
  - orphan cleanup auto/manual state,
  - hedge data gap.
- accounting:
  - entry credit,
  - exit spend,
  - protection recovery,
  - settlement cashflow,
  - option realized PnL,
  - hedge PnL separate,
  - final PnL status,
  - not-computed/data-gap status.
- recovery:
  - startup recovery state,
  - allow_new_open,
  - unknown active orders,
  - manual cleanup instruction.

### 9.4 Display Scenario Tests

For each lifecycle scenario, tests must assert display output, not only internal state.

Required display scenarios:

1. TEST plan phase shows no real trading.
2. LIVE plan phase shows opened/closed gates.
3. valid plan candidate shows confirmation code and Chinese plan summary.
4. non-lockable plan shows Chinese non-lockable reason.
5. stale menu shows no execution and Chinese stale reason.
6. precommit failed shows Chinese failed checks.
7. entry in progress shows protection-first progress.
8. protection-only residual shows no naked short and next action.
9. partial vertical shows current qty and management mode.
10. normal holding shows legs, TP, hedge, ledger summaries.
11. TP eligible shows budget/cap.
12. risk exit blocked by depth shows depth reason.
13. hedge soft trigger shows staged hedge explanation.
14. hedge hard trigger shows urgent hedge explanation.
15. pending hedge order shows no duplicate order and pending state.
16. settlement recognized shows settlement state.
17. settlement data gap shows not-computed, not zero.
18. orphan hedge auto cleanup shows reduce-only cleanup action.
19. orphan hedge manual cleanup shows manual instruction and no order.
20. CLOSED archive shows final PnL status and no active risk.
21. recovery blocked shows why and what to check manually.
22. unknown active order shows block reason.
23. episode cost placeholder is labeled reserved/not fully computed.
24. no raw machine code appears as primary human-facing text.
25. raw code, if present, is appended in parentheses after Chinese explanation.

Deliverable:

- `UX_STATUS_PANEL_AUDIT.md`
- display regression tests
- before/after sample status panels for:
  - plan phase,
  - locked plan/precommit,
  - normal holding,
  - TP eligible,
  - hedge active,
  - settlement,
  - orphan manual cleanup,
  - closed archive.

---

## 10. Required Simulation Harness

Build or extend a deterministic local test harness that can run outside FMZ with stubs/mocks for:

- `_G` persistence,
- `Log`,
- `LogStatus`,
- `Sleep`,
- `GetCommand`,
- Deribit `exchange.IO`,
- Binance `exchanges[index]` methods:
  - `SetContractType`,
  - `GetTicker`,
  - `GetPosition`,
  - `SetDirection`,
  - `Buy`,
  - `Sell`,
  - `GetOrder`,
  - `CancelOrder`.

The harness must support:

- time travel via `now_ms`,
- repeated `run_cycle()` calls,
- startup via `main()` or equivalent boot sequence where feasible,
- deterministic option position responses,
- deterministic hedge position responses,
- deterministic order lifecycle scripts:
  - accepted,
  - rejected,
  - missing order ID,
  - partially filled,
  - filled,
  - cancelled,
  - stale,
  - state read failure.
- display capture:
  - latest `LogStatus`,
  - parsed table titles,
  - parsed rows,
  - assertions on human-facing Chinese text.

Do not rely only on pure function tests. Include end-to-end scenario tests where `run_cycle()` mutates `_G` state across multiple loops.

---

## 11. Required Scenario Matrix

Create tests or documented simulations for at least these 40 scenarios:

1. TEST profile: no entry order placed.
2. TEST profile: no exit order placed.
3. TEST profile: no hedge order placed.
4. TEST profile: orphan hedge cleanup is dry-run only.
5. TEST profile status panel clearly says no real trading.
6. LIVE valid plan: confirmation code locks correct plan.
7. Expired confirmation code: no lock / no order.
8. Stale menu after config/version/manual context change: no execution.
9. Unknown active order on target option legs: precommit blocked.
10. Entry: protection fills, short fills, snapshot frozen.
11. Entry: protection fills, short does not, residual managed safely.
12. Entry: short partial fill, partial vertical managed safely.
13. Entry: protection order pending across loops, no duplicate order spam.
14. Entry: cancel captures late fill exactly once.
15. TP: 80% capture and sufficient DTE exits within budget.
16. TP: DTE <= threshold pauses ordinary TP.
17. Risk exit: ask <= cap and depth sufficient → taker allowed.
18. Risk exit: depth missing → no exit, hedge fallback only if hedge executable.
19. Risk exit: ask > cap → no over-budget buyback.
20. Hedge SOFT trigger: staged target, no full immediate hedge unless persisted/worsened.
21. Hedge HARD trigger: full target, cooldown does not block emergency.
22. Hedge final 3h: soft add suppressed, reduce/unwind allowed.
23. Hedge pending active: no second order.
24. Hedge pending partial stale: record fill and cancel residual.
25. Hedge submit missing order ID: state remains safe and visible.
26. Settlement: option read failure does not mutate snapshot.
27. Settlement: short absent after grace → remaining short qty zero.
28. Settlement: both legs absent → both quantities zero.
29. Settlement + Binance perp exists → target zero and reduce-only cleanup in LIVE when safe.
30. Startup no option short + Binance perp + clean evidence → automatic reduce-only cleanup allowed in LIVE only.
31. Startup no option short + Binance perp + unknown active orders → manual cleanup required, no order.
32. Startup no option short + Binance read failure → manual cleanup required, no order.
33. Startup no option short + Deribit option read failure → manual cleanup required, no order.
34. Snapshot exists but state key is `NO_POSITION` → position management, not plan opening.
35. Closed archive clears stale recovery state.
36. Repeated run cycles do not double-count settlement.
37. Repeated run cycles do not double-count exit fills.
38. Repeated run cycles do not double-count protection recovery.
39. Reserved fields such as `episode_cost_bps/usdc` are not displayed as precise real cost.
40. Status panel hides or downgrades plan menu during position management.

Add more scenarios if discovered during audit.

For each scenario record:

- setup,
- initial `_G` state,
- exchange stub state,
- command input if any,
- expected orders,
- expected no-orders,
- expected state mutation,
- expected ledger mutation,
- expected display text,
- pass/fail.

---

## 12. P0 / P1 / P2 Severity Classification

### P0

Any issue that can:

- place a real order in TEST,
- create naked option short risk,
- increase risk when gates forbid it,
- miss required hedge cleanup after confirmed option risk disappearance,
- mutate settlement state on failed reads,
- double-count ledger/PnL,
- archive closed while real risk remains,
- block risk-reducing actions indefinitely without operator-visible manual path,
- display a state that can reasonably cause the trader to take the wrong manual action in a live-risk situation.

### P1

Any issue that can:

- cause incorrect trader decision,
- produce materially wrong accounting,
- leave stale recovery state,
- hide data gaps,
- falsely display precision,
- require manual state surgery even though evidence is sufficient for safe automation,
- show machine codes/internal field names as primary operator language,
- make plan phase or position-management state materially unclear.

### P2

Cosmetic, layout, wording, or documentation issues that do not change trading, accounting, or operator safety.

---

## 13. Required Output

At the end, produce:

1. `LIFECYCLE_MAP.md`
   - stage table,
   - state transitions,
   - persisted keys,
   - exchange reads/writes,
   - display mapping.

2. `AUDIT_REPORT.md`
   - executive summary,
   - Go / No-Go / Conditional-Go verdict,
   - P0/P1/P2 table,
   - full lifecycle state diagram or table,
   - scenario matrix with pass/fail and evidence,
   - remaining risks,
   - operational runbook.

3. `UX_STATUS_PANEL_AUDIT.md`
   - display design goals,
   - current display issues,
   - before/after examples,
   - plan-phase status panel spec,
   - position-management status panel spec,
   - Chinese wording rules,
   - machine-code/internal-field display rules,
   - display test matrix.

4. Code changes for all discovered P0/P1 issues.

5. Regression tests:
   - pure function tests,
   - run_cycle scenario tests,
   - startup/recovery tests,
   - accounting finalization tests,
   - hedge/orphan cleanup tests,
   - display/Chinese UX tests.

6. `TEST_SUMMARY.md`
   - exact commands run,
   - tests passed/failed,
   - unresolved tests and why,
   - display scenarios passed/failed.

7. Final verdict, one of:
   - `NO_GO`,
   - `CONDITIONAL_LIVE_TEST_AFTER_P0_FIXES`,
   - `SMALL_SIZE_LIVE_TEST_READY`,
   - `LIVE_READY_WITH_LIMITS`.

If any P0 remains unresolved, do not mark the strategy live-ready.

---

## 14. Constraints

- Do not hand-edit generated bundle if the repo has editable source and build pipeline; edit source first and rebuild.
- If only the uploaded single-file artifact is available, keep changes clearly isolated and documented.
- Do not loosen safety gates to make tests pass.
- Do not convert unknown data into zero.
- Do not silently catch exceptions that should become explicit data-gap states.
- Do not rely on comments as proof; prove behavior with tests.
- Do not mark a scenario passed unless assertions inspect:
  - `_G` state,
  - order submission logs,
  - ledger mutation,
  - status panel output.
- Do not introduce background jobs or async assumptions that FMZ cannot run.
- Treat Binance/Deribit API reads as fallible.
- Treat repeated loops as normal behavior; all mutations must be idempotent.
- Keep display human-first:
  - Chinese first,
  - internal code second only when useful,
  - no raw dicts in first-level status,
  - no misleading precision,
  - no cluttered “everything everywhere” table.
- Do not remove auditability. If raw codes are hidden from the main display, preserve them in debug/audit fields or logs.

---

## 15. Recommended Implementation Order

1. Lifecycle map.
2. Existing test harness inventory.
3. Safety P0 tests:
   - TEST no real order,
   - no naked short,
   - no false settlement,
   - orphan cleanup evidence gate,
   - no double counting.
4. Fix P0.
5. Accounting/PnL P1 tests and fixes.
6. Recovery/restart P1 tests and fixes.
7. Status panel Chinese UX tests and fixes.
8. Full 40-scenario matrix.
9. Final audit and test summary.
10. Final Go/No-Go verdict.

---

## 16. Explicit Status Panel Layout Target

Target panel structure should be stable and readable.

### Plan Phase Layout

1. **当前阶段 / 操作提示**
   - 一句话告诉交易员：等待、可确认、禁开、测试模式、预提交中。
2. **运行门控**
   - RUN_PROFILE、进场/退出/对冲门、急停、只减。
3. **候选方案库**
   - 只显示交易员需要比较的列。
   - 不把 plan_hash、quality_code、schema_name 放在主表。
4. **候选详情 / 建仓可行性**
   - 只展示选中或置顶候选的详细风险/成本。
5. **预提交检查**
   - 中文失败原因，不只显示 raw check key。
6. **审计追踪 / Debug**
   - 可选折叠或低优先级展示 raw code/hash。

### Position Management Layout

1. **当前阶段 / 自动动作**
   - 当前状态、是否自动管理中、下一步动作。
2. **持仓总览**
   - 短腿/保护腿剩余、DTE、盘口、盈亏平衡、距现价。
3. **止盈 / 风险退出**
   - 捕获率、预算、price cap、深度、DTE gate。
4. **对冲**
   - 当前 perp、目标、待交易、pending、reduce_only、orphan 状态。
5. **记账 / PnL**
   - entry、exit、recovery、settlement、final option PnL、hedge PnL separate。
6. **恢复 / 人工清理**
   - recovery state、unknown order、manual cleanup instruction。
7. **Debug**
   - raw internal codes only if paired with Chinese explanation.

---

## 17. Definition of Done

The task is not complete until all are true:

1. All P0 fixed or final verdict is `NO_GO`.
2. All P1 either fixed or explicitly justified as safe for small-size live test.
3. TEST profile cannot submit any real order.
4. No option short can be created without filled protection coverage.
5. Settlement does not mutate state on failed position reads.
6. Confirmed option short disappearance drives hedge target to zero.
7. Orphan hedge cleanup is automatic only under strict evidence and LIVE mode.
8. Accounting is idempotent and distinguishes computed vs data-gap values.
9. Status panel is human-readable in Chinese.
10. Status panel does not primarily expose raw machine codes/internal field names.
11. Reserved fields such as `episode_cost_bps/usdc` cannot mislead operator as precise true cost.
12. Plan phase and position-management phase have distinct displays.
13. Every lifecycle scenario has both state/order assertions and display assertions.
14. Final reports are generated.
