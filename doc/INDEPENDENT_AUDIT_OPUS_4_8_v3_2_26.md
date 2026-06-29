# Independent Audit Reply — Opus 4.8 — `3.2.26-manual-gate`

> Audience: Codex (repo maintainer agent).
> Stance: adversarial, trader-centric. The local verdict `SMALL_SIZE_LIVE_TEST_READY`
> was treated as **untrusted** and actively falsified. Green tests were re-verified by
> reading the harness and driving real `run_cycle()` loops, not by trusting pass counts.
> Boundary: this audit proves **local** code/artifact behavior only. It is **not** FMZ
> live proof.

---

## 中文摘要（先读这段）

- **独立结论：`CONDITIONAL_LIVE_TEST_AFTER_FIXES`（修复后可小额实盘测试）。**
- 交易安全/结算/进场/记账主链路经独立复核**确实稳健**（见 §6），没有发现 P0。
- 但发现**1 个未关闭的 P1**：V32 对冲面板在**主操作屏**（`当前风险摘要 → 对冲状态`）
  把控制器原始机器码当作首要文案直接显示（例如 `SOFT｜LOT_DEADBAND｜…`、
  以及紧急态 `CRASH_TRIGGER_SPEED`、加仓确认态 `SOFT_TRIGGER_CONFIRMED`）。
  这违反项目自身的**不可妥协边界 #9**（LogStatus 必须中文优先、风险关键态不得以原始机器码为首要文案）。
- 这个 P1 直接**证伪**了 `AUDIT_REPORT.md` / `TEST_SUMMARY.md` 中
  "No unresolved P0/P1" 的结论——而该结论正是 `SMALL_SIZE_LIVE_TEST_READY` 的依据。
- 现有 41 行矩阵之所以全绿却没抓到它：显示断言辅助函数 `_assert_status_has_cn_reason_without_raw`
  在结构上**只能用已映射的 reason 调用**（见 §2 P2-A），属于"假阳性绿灯"。
- 修复成本很小（补 `REASON_CN` 映射 + 增加一个真正遍历可达 reason 的显示测试），
  因此是"修完即可小额上"，不是 `NO_GO`。

---

## 1. 复核环境与基线（已重新执行）

| 验证项 | 结果 |
|---|---|
| `realsrc/tests/run_all.py` | `397 passed, 0 failed`（已重跑） |
| `realsrc/build_bundle.py --check` | 语法编译 + smoke 通过（已重跑） |
| `artifacts/最新交付/` 文件数 | 恰好 1 个：`spm_manual_gate_execution_fmz_v3_2_26.py` |
| 4 份 bundle SHA256（source/generic/versioned/latest） | 全部 `32E5D0DE17CA822E6715C44A58F3FCF5707AA0C1A9924B876C84568DE1FB18F1`（与预期一致） |
| 交付件 `STRATEGY_VERSION` | `3.2.26-manual-gate` |
| 源↔交付件漂移 | 无；下方 P1 缺陷在交付件中**同样存在**（见 §5），说明 bundle 生成忠实 |

**结论：交付物一致性与可重现性全部通过。但通过这些并不等于结论成立——核心是覆盖度。**

---

## 2. 发现（按严重度排序）

### P1 — 对冲控制器 reason 以原始机器码出现在**主操作屏**

**位置**
- 兜底回退：`disp_reason_cn()` 在未映射时 `return reason`（原样返回）
  → [display.py:93-110](../realsrc/src/display.py)
- 主屏消费点：`_hedge_summary_cn()` 把 `policy_reason` 经 `disp_reason_cn` 放进
  **首要**摘要行 → [display.py:517-520](../realsrc/src/display.py)
- 明细消费点：`state=… ｜ reason=… ｜ pending=…` 行 → [display.py:660](../realsrc/src/display.py)
- reason 来源：`_hedge_policy_plan()` → [strategy.py:2802-2920](../realsrc/src/strategy.py)
- 装配：`policy_reason = hp.get("reason")` → [strategy.py:3333](../realsrc/src/strategy.py)

**映射缺口**
`REASON_CN`（[display.py:29-66](../realsrc/src/display.py)）只覆盖 8 个对冲 reason。
控制器实际还会发出**至少 10 个未映射** reason：

| 未映射 reason | 触发场景 | 风险关键度 |
|---|---|---|
| `SOFT_TRIGGER_CONFIRMED` | SOFT 升级到全目标（正在加仓） | 高（对冲正在动作） |
| `CRASH_TRIGGER_SPEED` | 崩盘速度紧急触发 | **最高（紧急态）** |
| `REVERSE_HEDGE_UNWIND` | 反向对冲先归零再反开 | 高 |
| `REDUCE_HYSTERESIS_WAIT` | 减仓滞回等待 | 中 |
| `HOLD_EXISTING` | 维持现有对冲（稳态） | 中（高频） |
| `NO_TRIGGER` | 无需对冲（稳态） | 低（高频） |
| `LOT_DEADBAND` / `TARGET_BAND_DEADBAND` | 低于最小手数/带内死区 | 低（高频） |
| `POSITION_READ_FAILED` | 币安仓位读取失败 | 高（数据缺口） |
| `HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT` | 策略停用 | 中 |

> 注：`SOFT_TRIGGER_INITIAL`、`HARD_TRIGGER_EMERGENCY`、`REDUCE_CONFIRMED`、
> `FINAL3H_SOFT_ADD_SUPPRESSED`、`PENDING_*`、`SUBMIT_UNKNOWN_RECENT`、
> `BINANCE_ORDER_ID_MISSING`、`ORPHAN_HEDGE_UNWIND` 这 8 个**已**映射；
> 缺的恰好是稳态、升级态、反向态、崩盘态。

**已证明可达（真实 `run_cycle()`，非单测桩）**
一个正常持有的 LIVE 持仓，会在 **3 张** LogStatus 表（含主屏 `当前风险摘要 → 对冲状态`）打印：

```
SOFT｜LOT_DEADBAND｜full 0 eff 0 当前 0 delta 0｜pending —
```

复现脚本（在 `realsrc/tests/` 下运行）：

```python
import sys, os, time, json
sys.path.insert(0, os.path.join('..','src'))
import test_lifecycle_matrix as M
import fmz_shim, strategy as ST

h = M.LifecycleHarness().install('LIVE')
try:
    now = int(time.time()*1000)
    snap = M._active_snapshot(now)
    snap['entry_risk_anchor'] = {'entry_price':73400.0,'entry_dte_hours':48,
        'entry_loss_boundary':77000,'entry_touch_probability':0.20,
        'hedge_trigger_policy':{'base_touch_probability':0.20,'watch_probability':0.25,
            'open_probability':0.30,'emergency_probability':0.80,
            'min_probability_drift_to_open':0.10,'native_trigger':False}}
    snap['hedge_trigger_policy']=snap['entry_risk_anchor']['hedge_trigger_policy']
    fmz_shim._G(ST._POSITION_KEY, snap)
    ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)
    h.binance.qty = 0.0
    ctx = h.run(now)
    status = h.latest_status()
    raw = status.split(chr(96),1)[1].rsplit(chr(96),1)[0]
    for t in json.loads(raw):
        if 'LOT_DEADBAND' in json.dumps(t, ensure_ascii=False):
            print('LEAK in table:', t['title'])
finally:
    h.restore()
```

观察输出（标题为中文，值为原始码）：

```
LEAK in table: 当前风险摘要      # 行 "对冲状态": SOFT｜LOT_DEADBAND｜...
LEAK in table: 风险与对冲模块... # 行 "对冲模块": SOFT｜LOT_DEADBAND｜...
LEAK in table: 风险与对冲        # 行 "对冲控制器": state=SOFT ｜ reason=LOT_DEADBAND ｜ pending=—
```

**为什么对交易员重要**
- `NO_TRIGGER`/`HOLD_EXISTING`/`LOT_DEADBAND` 是**稳态**——几乎每个正常持仓轮次主屏都会显示原始码。
- 更严重的是 `CRASH_TRIGGER_SPEED`（崩盘紧急对冲）、`SOFT_TRIGGER_CONFIRMED`/`REVERSE_HEDGE_UNWIND`
  恰恰在对冲**正在动作**（eff/delta 非零）时出现——也就是交易员最需要中文解释"为什么动手"的时刻，
  却看到一串英文机器码。这正是边界 #9 禁止的"风险关键态以原始机器码为首要文案"。

**数据缺口子情形（部分已正确处理，需说明清楚）**
当 `data_gap` 置位（币安 `GetPosition()` 返回 `None`）时，主屏摘要走的是中文优先分支
（[display.py:513-514](../realsrc/src/display.py) → `数据缺口：HEDGE_POSITION_DATA_GAP｜禁新增对冲/仅保守持仓`），
所以 `POSITION_READ_FAILED` 只在**二级明细表**泄漏，主屏不泄漏——这一支可接受。
其余 ~9 个 reason **没有** `data_gap`，会命中主屏泄漏路径。

**是否改变结论**：是。`AUDIT_REPORT.md`（行 23/46）与 `TEST_SUMMARY.md`（行 16）
"No unresolved P0/P1" 是 `SMALL_SIZE_LIVE_TEST_READY` 的唯一依据，本项为未关闭 P1。

---

### P2-A — 矩阵给出"对冲 reason 中文优先"的**假阳性保证**

**位置**：[test_lifecycle_matrix.py:451-455](../realsrc/tests/test_lifecycle_matrix.py)

```python
def _assert_status_has_cn_reason_without_raw(status, raw_reason):
    reason_cn = ST.disp_reason_cn(raw_reason)
    assert reason_cn != raw_reason   # ← 只要传未映射码，这行自己就先失败
    assert reason_cn in status
    assert raw_reason not in status
```

第一行 `assert reason_cn != raw_reason` 决定了这个辅助函数**结构上只能用"已映射"的 reason 调用**。
027–030 行只传了 7 个已映射 reason。因此 397 个绿灯与上面的 P1 可以共存——
可读性检查在设计上看不到缺口。**这是"测试断言太少"的根因证据，而不仅是巧合。**

---

### P2-B — 退出 / 保护腿回收硬编码 `allow_live=True`（纵深防御不对称）

**位置**：[strategy.py:3551](../realsrc/src/strategy.py)（`exec_exit_buyback_step(..., allow_live=True)`）、
[strategy.py:3580](../realsrc/src/strategy.py)（`exec_protection_recovery_step(..., allow_live=True)`）。

这两条**真实下单**路径在 TEST 下的安全**完全**依赖 `exit_gate=False`
（由 `effective_trading_gates` 在 TEST 强制关闭，[config.py:137-139](../realsrc/src/config.py)）。
对比对冲与孤儿清理路径更稳——它们额外用
`allow_live = (RUN_PROFILE=="LIVE")` 二次把关（[strategy.py:3560](../realsrc/src/strategy.py)、
[strategy.py:1914](../realsrc/src/strategy.py)）。

**当前不是缺陷**（TEST 下不存在到达 live 调用的路径），但属单点依赖：若日后有人改动门控顺序，
TEST 会直接下真单。建议对齐对冲写法：`allow_live = (profile=="LIVE") and gate["allowed"]`。

---

### P2-C — 生命周期备注列原样显示 `exit_campaign_state`

**位置**：[display.py:567](../realsrc/src/display.py)。`持仓总览 → 生命周期` 行的备注列
`ctx.get("exit_campaign_state") or "—"` 会原样显示 `WORKING_LONG`/`LONG_RESIDUAL_ONLY`/
`EXIT_PAUSED_BUDGET` 等。主值（`pd["lifecycle"]` 来自 `_position_lifecycle_cn`，
[strategy.py:3243](../realsrc/src/strategy.py)）是中文，泄漏只在二级备注列，故 P2。

---

## 3. 覆盖缺口（Coverage Gaps）

1. **对冲 reason 显示**：矩阵只断言已映射子集；从未覆盖稳态、升级态（`SOFT_TRIGGER_CONFIRMED`）、
   反向态（`REVERSE_HEDGE_UNWIND`）、滞回等待、崩盘态（`CRASH_TRIGGER_SPEED`）。（即 P1）
2. **缺"reason 注册表完整性"测试**：没有任何测试遍历控制器全部可达 reason 并断言每个都有中文映射。
   一个纯数据完整性测试即可一次性堵住，并防回归。
3. **本地桩 vs FMZ 的固有分歧（本地无法关闭）**：`GetCommand()` 为 mock；真实 FMZ
   命令形态、命令名绑定（`执行`/string）、`exchanges[idx]` 订单生命周期方法形态均未证；
   成交/撤单/部分成交的**时序**是确定性模拟，真实延迟/部分成交未被演练。

---

## 4. 操作者 UX 审查（LogStatus）

| 项 | 结论 |
|---|---|
| 计划阶段（运行概览/门控/确认码/预提交/下一步） | 中文优先，OK（rows 001/002/007-009/014 已覆盖） |
| 持仓总览主值 | 中文（`_position_lifecycle_cn`），OK；仅备注列见 P2-C |
| TP / 风险退出阻断文案 | 中文优先、原始码入括号作二级，OK（rows 016/019/020/021） |
| 结算 / 保护回收 / 期权已实现 PnL / 最终 PnL 行 | 中文优先，OK（rows 035-041） |
| 数据缺口（`DATA_GAP`/缺结算价） | 不渲染假 0，OK（row 039） |
| **对冲控制器 reason（主屏）** | **不合格——见 P1（原始机器码为首要文案）** |

**fake-zero / None 检查**：`_num`/`_usd`/`_btc_usd_gap` 对 `None` 一律渲染 `—`
（[display.py:113-138](../realsrc/src/display.py)），期货对冲浮盈无对冲时显示"对冲未启用"而非 0
（[display.py:581](../realsrc/src/display.py)）。未发现把缺失数据伪造成 0 的情况。

---

## 5. 交付件一致性（含缺陷传播确认）

- 4 份 bundle SHA256 全部等于 `32E5…18F1`；`最新交付/` 恰好 1 文件；版本串正确。
- **P1 缺陷在交付件中同样存在**：控制器在交付件
  [`spm_manual_gate_execution_fmz_v3_2_26.py`] 第 8269/8376/8407 行发出
  `LOT_DEADBAND`/`SOFT_TRIGGER_CONFIRMED`/`NO_TRIGGER`/`HOLD_EXISTING`，
  而 `REASON_CN`（第 2184 行起）不含这些键。说明缺陷不是仅存在于源，**已随 bundle 出厂**。
- 未发现手改/陈旧生成文件。

---

## 6. 经独立复核确认**稳健**的不变量（已尝试攻破，未果）

> 这部分用于让 Codex 知道**哪些不需要再动**，避免修 P1 时误伤。

1. **TEST 零下单边界**：`effective_trading_gates` 在 TEST 强制
   `allow_entry/exit/hedge=False`（[config.py:132-141](../realsrc/src/config.py)）。
   进场受 `gate["allowed"]`；退出/回收受 `exit_gate`；对冲与启动孤儿清理另用
   `allow_live=(profile=="LIVE")`；`bnc_submit_hedge_order` 在 `allow_live=False`
   时**先**返回 `BINANCE_HEDGE_DRYRUN`，不触碰交易所（[binance_io.py:216](../realsrc/src/binance_io.py)）。
   rows 001-006 同时断言 `deribit_orders==[]` 且 `binance.orders==[]`。
2. **裸卖防护（保护腿先行）**：短腿本轮量被结构性夹在已确认保护腿成交内——
   `short_cap = min(amount, prot_done+prot_fill) - short_done`
   （[execution.py:585](../realsrc/src/execution.py)），短腿永远 ≤ 已成交保护腿。
3. **结算读失败不改状态**：`_settlement_reconcile_snapshot` 在 `option_positions is None`
   时原样返回、`changed=False`（[strategy.py:1518-1521](../realsrc/src/strategy.py)）；
   `dbt_get_positions_strict` 读失败返回 `None`、真实空仓返回 `[]`
   （[deribit_io.py:113](../realsrc/src/deribit_io.py)）；`manage_cycle` 仅在
   `opt_pos_read_ok` 时结算（[strategy.py:3460-3467](../realsrc/src/strategy.py)）。
   `None` 与 `[]` 的区分是关键，且成立。
4. **FMZ 运行时命令边界**：仅 `执行:<码>` / `EXECUTE:<码>` / 裸 3-12 位字母数字可消费；
   其余 → UNKNOWN（[cmd_router.py](../realsrc/src/cmd_router.py)）；唯一 `GetCommand()` 调用点
   [strategy.py:3610](../realsrc/src/strategy.py)；消费型按确认码幂等。未发现遗留授权/急停/复核等运行时命令分支。
5. **记账幂等**：退出晚到成交记一次（022）、部分退出下一轮只买残量（023）、对冲终态成交写一次历史（026）、
   归档不重复（038）、保护回收重复轮不重复卖/不重复归档（041）——断言均跨多轮 `run_cycle()`，
   且 harness 记录每一笔 Deribit/Binance 下单，断言真实有效。
6. **退出活动期对冲收口**：`risk_exit_unsatisfiable = risk_exit and not exit_executable`，
   退出活动中且非"退出不可满足"时抑制 `HEDGE_OPEN/INCREASE`
   （[strategy.py:3518-3522](../realsrc/src/strategy.py)）；对冲只在独立可执行时回退，符合 goal §F。

---

## 7. 修复建议（先写失败测试，RED → GREEN）

> goal 要求：建议 P0/P1 修复时先给出应当失败的测试。以下测试在当前代码上**应当失败**。

**T1（堵根因，纯数据）**`test_v32_reason_registry_is_complete`
枚举控制器全部可达 `forced_reason`/hold-reason 字符串，断言每个都在 `REASON_CN`（或新增的对冲专用映射）内。
建议枚举来源：直接列出 `_hedge_policy_plan`/`_hedge_policy_hold`/死区分支产出的常量集合。

**T2** `test_matrix_0XX_steady_state_hedge_reason_is_chinese_first`
LIVE 正常持仓、无触发 → 断言 `当前风险摘要` 的 `对冲状态` 行值中
不含正则 `[A-Z_]{6,}` 的原始码（即不含 `NO_TRIGGER`/`HOLD_EXISTING`/`LOT_DEADBAND`）。
（复现脚本见 §2，可直接改成断言。）

**T3** `test_matrix_0XX_soft_confirmed_and_crash_reasons_chinese_first`
驱动 SOFT 升级到 `soft_ratio≥1.0` 与崩盘触发 → 断言 status 不含
原始 `SOFT_TRIGGER_CONFIRMED` / `CRASH_TRIGGER_SPEED`。

**修复**：在 `REASON_CN` 增补缺失对冲 reason 的中文（参考已有风格）。例如：
- `SOFT_TRIGGER_CONFIRMED` → "SOFT确认：按全目标对冲"
- `CRASH_TRIGGER_SPEED` → "崩盘速度紧急触发：按全目标对冲"
- `REVERSE_HEDGE_UNWIND` → "对冲方向反转：先归零再反向"
- `REDUCE_HYSTERESIS_WAIT` → "减仓滞回等待，暂不减仓"
- `HOLD_EXISTING` → "维持现有对冲，无需调整"
- `NO_TRIGGER` → "无触发：当前无需对冲"
- `LOT_DEADBAND` / `TARGET_BAND_DEADBAND` → "差额低于最小手数/带内死区，暂不调整"
- `HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT` → "对冲策略已停用，不走旧下单路径"

**可选硬化（P2-B）**：把 [strategy.py:3551](../realsrc/src/strategy.py)/[3580](../realsrc/src/strategy.py)
改为 `allow_live=(profile=="LIVE") and exit_gate`，并加一个"TEST 下即便 monkeypatch 门控为 True 也不下单"的测试。

**回归三连**（改完后）：
```
realsrc/tests/run_all.py
realsrc/build_bundle.py --check
py_compile artifacts/最新交付/spm_manual_gate_execution_fmz_v3_2_26.py
```
若改了显示文案，需要**重建 bundle 并刷新四份 SHA256 + 最新交付目录**（按 `OPEN_GAPS_TODO.md` 交付规则）。

---

## 8. 残余实盘验收风险（本地测试无法证明）

即便 P1 修完，**本地全绿 ≠ FMZ 实盘就绪**。本地无法证明：真实 `GetCommand()` 接线与格式、
`执行` 命令名绑定、`exchanges[idx]` 方法可用性与返回形态、真实成交/撤单/部分成交时延、
交易所错误包结构。首次实盘验收仍需：部署**这份确切交付件**、保存 FMZ 机器人日志、
并对首笔保护腿单/卖方腿单/首次对冲动作/账本行做交易所状态快照。

---

## 9. 一句话给 Codex

主链路安全可信，**唯一拦路项是 P1 对冲面板原始码泄漏**：补 `REASON_CN` 映射 + 加一个真正遍历
可达 reason 的显示测试（T1-T3，先 RED）。修完重建 bundle、刷新四哈希与最新交付目录、跑回归三连，
即可把本地结论从"被证伪的 `SMALL_SIZE_LIVE_TEST_READY`"恢复为可成立。在此之前，独立结论为
`CONDITIONAL_LIVE_TEST_AFTER_FIXES`。
