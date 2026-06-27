# Neutral Loop Execution Layer — v3.0.0 到 v3.0.5 接手记忆

本文档用于交给 Codex 接手后续代码修改与 GitHub 推送。后续工作模式为：ChatGPT 负责策略架构、边界判断、验收口径与版本设计；Codex 负责实际改代码、跑本地检查、更新单文件交付物并推送仓库。

---

## 1. 项目定位

仓库：`x18055868223-png/Neutral-Loop-Execution-Layer`

策略运行环境：FMZ.com，单文件 Python 策略。

策略角色：这是交易员收到信号层信号之后使用的执行层，不是信号层。信号层负责方向或交易意图判断；执行层负责：

- 根据人工放行后的方向倾向、数量和默认执行参数扫描 Deribit 期权链；
- 构造同期 vertical credit spread 候选；
- 做 S:PM 保证金释放检查；
- 做 execution feasibility 检查；
- 做 VRP 价格过滤；
- 生成确认码；
- 预提交复核；
- 执行 entry campaign；
- 后续管理持仓、退出、对冲和恢复。

当前安全边界：

- 默认不真实下单；
- `ALLOW_ENTRY_TRADING = False`
- `ALLOW_EXIT_TRADING = False`
- `ALLOW_HEDGE_TRADING = False`
- `DRY_RUN_PASSED = False`
- 不允许把本地检查、语法检查、bundle 成功说成 FMZ dry-run 或实盘验收；
- VRP 缺失时可以展示候选，但不得生成确认码，不得进入锁定/开仓。

---

## 2. 工作流约定

ChatGPT 侧已经确认：由于当前对话工具推送大约 260KB 单文件不稳定，后续不再由 ChatGPT 直接推 GitHub。新流程为：

1. ChatGPT 设计版本改动、边界与验收点；
2. ChatGPT 生成或描述新版本交付物；
3. Codex 在仓库中完成实际修改；
4. Codex 运行测试、构建 bundle、更新 artifact、更新 checksum；
5. Codex commit / push；
6. 用户拿 `artifacts/spm_manual_gate_execution_fmz.py` 覆盖到 FMZ 运行；
7. 用户反馈日志、截图、异常；
8. ChatGPT 判断下一轮策略改动。

Codex 接手时应优先修改：

- `realsrc/src/`
- 必要测试文件
- `realsrc/spm_manual_gate_execution_fmz.py`
- `artifacts/spm_manual_gate_execution_fmz.py`
- `CHECKSUMS.txt`

不要只改 artifact 后不改源码，除非用户明确要求做一次临时单文件热修。

---

## 3. v3.0.0 基线状态

v3.0.0 是仓库初始交接版本：`STRATEGY_VERSION = "3.0.0-manual-gate"`。

初始问题：

1. 执行层把“人工审计门”做得过重，要求填写 `MANUAL_AUDIT_CARD_ID` 和 `MANUAL_AUDIT_NOTE`，用户认为这是重复确认，信号层人工确认后执行层只需要一个放行布尔值。
2. 代码仍保留 `ROUND_MODE = "PLAN"`、`SELECTED_PLAN = 0` 等计划轮/下单轮残留，但当前策略已经是完整 run_cycle 主链。
3. 配置入口过多，用户希望核心入口只保留：
   - 方向倾向；
   - 单结构数量；
   - 是否允许真实交易；
   - 其他 DTE / delta / 腿宽等作为次级默认参数。
4. FMZ 初始空跑能进入 `WAIT_MANUAL_AUDIT_GATE`，无异常、无真实下单。

---

## 4. v3.0.1 改动记忆：配置层收束

目标：减少执行层人工审计负担，删除计划/下单双轮残留，收束核心配置入口。

主要设计：

1. 版本号递推：
   - `STRATEGY_VERSION = "3.0.1-manual-gate"`

2. 核心入口重组为：

   ```python
   SETTLEMENT_CURRENCY = "BTC"
   MANUAL_PLANNING_ALLOWED = False
   DIRECTION_BIAS = "SHORT_CALL"
   ORDER_AMOUNT = 0.1
   ```

3. 人工审计资料变为可选：
   - `MANUAL_AUDIT_CARD_ID = ""`
   - `MANUAL_AUDIT_NOTE = ""`
   - 不再因为 audit card 为空导致 manual context invalid。

4. 删除或隐藏计划轮/下单轮残留：
   - 删除 `ROUND_MODE`
   - 删除 `SELECTED_PLAN`
   - 状态栏不再显示 “计划轮(PLAN)” / “下单轮(ORDER)” / “选用方案号”。

5. 次级默认配置下沉：
   - `SHORT_DTE_HOURS = (24, 72)`
   - `SHORT_DELTA_RANGE = (0.15, 0.45)`
   - `PROTECTION_WIDTH_RANGE = (2000, 2500)`
   - `CANDIDATE_MENU_SIZE = 10`
   - 保留 `MENU_SIZE = CANDIDATE_MENU_SIZE` 兼容原代码路径，避免大改。

6. 面板提示改成：
   - 信号层人工确认后，将 `MANUAL_PLANNING_ALLOWED` 改为 `True` 即可生成候选；
   - 不再提示填写 `MANUAL_AUDIT_CARD_ID`。

安全边界未改变：

- 不开交易门；
- 不取消确认码；
- 不改变 VRP fail-closed；
- 不改 entry / exit / hedge / recovery 核心逻辑。

用户 FMZ 验证结果：

- v3.0.1 启动成功；
- 版本显示正确；
- `MANUAL_PLANNING_ALLOWED=True` 后进入 `PLAN_MENU_READY`；
- 但看不到具体候选方案，只有“无效空方案”感受，无法定位卡点。

---

## 5. v3.0.2 改动记忆：链路回显与心跳诊断

目标：定位为什么人工放行后不生成可确认方案。

主要设计：

1. 版本号递推：
   - `STRATEGY_VERSION = "3.0.2-manual-gate"`

2. 新增诊断配置：

   ```python
   TRACE_LOG_SECONDS = 15
   TRACE_PLAN_STAGES = True
   ```

3. `_build_menu()` 增加阶段日志：

   ```text
   [trace][plan] build_start ...
   [trace][plan] option_chain instruments=...
   [trace][plan] expiry_filter expiries=...
   [trace][plan] account_spm pm_ok=... model=...
   [trace][plan] candidate_filter_pass / stop ...
   [trace][plan] spm_topk_start ...
   [trace][plan] menu_ready ...
   ```

4. `run_cycle()` 增加周期心跳：

   ```text
   [trace][cycle] phase=... state=... spot=... manual=... reason=... not_lockable=... candidates=... lockable=... vrp_blocked=... diag=...
   ```

5. 状态栏增加：
   - 候选/确认码数量；
   - 计划链路原因；
   - 枚举漏斗：
     - 短腿扫描；
     - delta 区间外；
     - 无报价/无买盘；
     - 权利金过薄；
     - 价差过宽；
     - 无合格保护腿；
     - 执行不可行；
     - 生成候选；
     - 进入菜单；
     - 合格数量。

用户 FMZ 验证结果：

- 诊断日志正常出现；
- 真实链路显示：
  - option_chain instruments=946；
  - expiry_filter expiries=2；
  - account_spm model=segregated_pm pm_ok=True；
  - candidate_filter_pass；
  - menu_ready；
  - candidates > 0；
  - not_lockable=VRP_CONTEXT_MISSING。
- 结论：不是没有候选，而是候选没有展示出来，并且因 VRP 缺失不能生成确认码。

---

## 6. v3.0.3 改动记忆：状态栏候选展示与模块回显

目标：把已经扫描出的候选方案展示到 FMZ 状态栏，不再只显示漏斗和空方案感觉。

主要设计：

1. 版本号递推：
   - `STRATEGY_VERSION = "3.0.3-manual-gate"`

2. 状态栏新增候选方案明细表：
   - 编号；
   - 确认码；
   - 推荐标签；
   - 模式；
   - 期号；
   - DTE；
   - 短腿行权价 / delta；
   - 保护腿行权价；
   - 腿宽；
   - 短腿距现价；
   - 胜率；
   - 有效净 credit；
   - 信用/保证金；
   - 盈亏比；
   - 盈亏平衡价；
   - 释放；
   - 合格状态。

3. 即使 `VRP_CONTEXT_MISSING`，也展示候选，只是不生成确认码。

4. 新增主链模块回显表：
   - 计划轮；
   - 候选展示；
   - 确认码；
   - 预提交；
   - 执行模块；
   - 预算模块；
   - 记账/恢复；
   - 对冲模块；
   - 退出模块。

5. 候选菜单写入 `_G(_MENU_KEY)`，在刷新周期中可持续展示，不只存在于当前循环变量。

6. 日志新增候选逐条输出：

   ```text
   [trace][plan_candidates] display=... codes=... not_lockable=...
   [trace][plan_candidate] #... expiry=... short=... K=... delta=... prot=... width=... credit=... rr=... relief=... ef=... confirm=... qualified=...
   ```

用户 FMZ 验证结果：

- 候选成功展示；
- 能看到 3 条候选，例如：
  - 61000/63000；
  - 61500/63500；
  - 62000/64000；
- 每条显示 `不可锁定:VRP_CONTEXT_MISSING`；
- 但候选方案明细仍会抖动，因实时行情刷新、排序变化导致表格顺序和内容变动。

---

## 7. v3.0.4 改动记忆：固定备选方案库，避免抖动

目标：候选库稳定展示，不随实时行情反复排序和变动。用户要求：完整显示整个备选方案库，不做实时排序和准入；明确显示 `VRP_CONTEXT_MISSING`。

主要设计：

1. 版本号递推：
   - `STRATEGY_VERSION = "3.0.4-manual-gate"`

2. 新增固定库配置：

   ```python
   PLAN_LIBRARY_FREEZE = True
   PLAN_LIBRARY_REFRESH_COMMAND_ONLY = True
   STATUS_MENU_SIZE = 50
   ```

3. 候选库第一次生成后固定下来：
   - 存入 `_G(_MENU_KEY)` 或类似固定库状态；
   - 不再每隔 `PLAN_REFRESH_SECONDS` 重新扫描并重排；
   - 状态栏显示来源：
     - `built_frozen`：刚扫描并冻结；
     - `frozen`：沿用固定库；
     - `实时`：未冻结模式。

4. 固定库失效条件：
   - 修改 `DIRECTION_BIAS`；
   - 修改 `ORDER_AMOUNT`；
   - 修改 DTE / delta / 腿宽；
   - 修改影响 manual context signature 的风险门配置；
   - 重启或清空 `_G` 状态；
   - 后续显式恢复或重建上下文。

5. 表标题调整为：
   - `固定备选方案库（完整展示；不随实时行情重排；VRP_CONTEXT_MISSING=仅展示不可锁定；有效$=净 credit）`

6. 每个候选明确显示锁定状态：
   - `不可锁定:VRP_CONTEXT_MISSING`

7. 主链模块回显显示：
   - 展示数量；
   - 可锁定数量；
   - VRP 阻断数量；
   - 来源；
   - `VRP_CONTEXT_MISSING`。

安全边界仍不放松：

- 无 VRP context 时只展示候选；
- 不生成确认码；
- 不进入 precommit；
- 不真实下单。

当前最新交付版本为 v3.0.4。

---

## 8. v3.0.5 下一步目标：补 VRP market context 输入契约

v3.0.5 尚未实现。下一轮应由 Codex 根据此设计实现。

目标：让用户可以手动输入执行侧 VRP 市场上下文，从而把候选从“展示可行但不可锁定”推进到“可生成确认码并 dry-run 锁定”。

建议新增顶部配置：

```python
MANUAL_MARKET_CONTEXT_JSON = ""
```

示例 JSON：

```json
{
  "front_anchor_iv": 0.62,
  "rv_24h": 0.48,
  "rv_72h": 0.50,
  "rv_7d": 0.52,
  "executable_short_iv": 0.64,
  "history_days": 60,
  "rv_percentile": 0.55,
  "atm_front_iv": 0.61,
  "term_reference_iv_5_10d": 0.58,
  "executable_protection_iv": 0.66
}
```

硬必需字段：

- `front_anchor_iv`
- `rv_24h`
- `rv_72h`
- `rv_7d`
- `executable_short_iv`

可选字段：

- `history_days`
- `rv_percentile`
- `atm_front_iv`
- `term_reference_iv_5_10d`
- `executable_protection_iv`

实现要求：

1. 新增 JSON 解析函数，标准库 `json` 即可，不引入依赖。
2. 当 `MANUAL_MARKET_CONTEXT_JSON` 为空：
   - `market_context` 不写入 manual context；
   - 候选继续展示；
   - 确认码仍显示不可锁定：`VRP_CONTEXT_MISSING`。
3. 当 JSON 格式错误：
   - 不应崩溃；
   - 状态栏显示 `VRP_CONTEXT_INVALID_JSON`；
   - 不生成确认码。
4. 当必填字段缺失：
   - 状态栏显示 `VRP_CONTEXT_MISSING_FIELDS:<fields>`；
   - 不生成确认码。
5. 当 JSON 合法：
   - 自动补 `side = DIRECTION_BIAS`；
   - 写入 `manual_context["market_context"]`；
   - 重新评估固定候选库；
   - VRP 通过的候选生成确认码；
   - VRP 不通过的候选显示阻断原因。
6. manual context signature 应纳入 market context 或 market context hash，使得修改 JSON 后旧确认码失效。
7. 状态栏必须展示：
   - VRP context 是否存在；
   - 是否合法；
   - 通过候选数量；
   - 阻断候选数量；
   - 每个候选的 VRP 状态/原因。
8. 日志必须输出：
   - `[trace][vrp_context] status=...`
   - `[trace][vrp_gate] candidate=... pass=... reason_codes=...`

---

## 9. 关于 VRP_CONTEXT 是否必要的结论

已讨论结论：VRP_CONTEXT 有必要保留，但不应阻塞候选展示。它只应阻塞确认码和真实开仓。

分层如下：

无 VRP_CONTEXT：

- 可以展示备选方案库；
- 可以看 delta / DTE / 腿宽 / credit / 保证金释放 / 执行评级；
- 不生成确认码；
- 不进入 precommit；
- 不真实下单。

有 VRP_CONTEXT 且通过：

- 候选进入可锁定集合；
- 生成确认码；
- 可执行 dry-run 锁定；
- 之后仍需 precommit 复核。

有 VRP_CONTEXT 但不通过：

- 继续展示备选方案；
- 标记 VRP 阻断原因；
- 不生成确认码。

不建议完全取消 VRP，因为：

- 候选库只说明结构形态和执行可行性；
- VRP 说明当前权利金是否足够补偿近期真实波动、IV/RV 关系、期限结构和全回路摩擦；
- 对卖方策略而言，这是执行层价格过滤，不应取消。

---

## 10. 给 Codex 的具体接手任务

从当前最新版本 v3.0.4 开始，执行：

1. 在仓库中找到最新对应代码：
   - `artifacts/spm_manual_gate_execution_fmz.py`
   - `realsrc/spm_manual_gate_execution_fmz.py`
   - `realsrc/src/` 中对应模块

2. 实现 v3.0.5：
   - 添加 `MANUAL_MARKET_CONTEXT_JSON`;
   - 添加解析/校验函数；
   - 把合法 market context 写入 manual context；
   - 将 market context 纳入 config signature 或 lineage hash；
   - 对固定候选库应用 VRP gate；
   - 为通过候选生成确认码；
   - 为未通过候选显示 VRP 阻断原因；
   - 补状态栏与 trace 日志。

3. 保持安全边界：
   - 不开交易门；
   - 不设置 `DRY_RUN_PASSED=True`；
   - 不取消确认码；
   - 不把 VRP 缺失当通过；
   - 不自动 top1 开仓；
   - 不重新接入信号层文件或外部 receiver。

4. 更新版本：
   - `STRATEGY_VERSION = "3.0.5-manual-gate"`

5. 运行检查：
   - `py_compile`
   - 如果仓库测试可运行，执行 `realsrc/tests/run_all.py`
   - 构建/同步 bundle
   - 更新 `CHECKSUMS.txt`

6. 输出交付：
   - 更新后的 `artifacts/spm_manual_gate_execution_fmz.py`
   - Commit SHA
   - SHA256
   - 变更说明
   - FMZ 验证点

---

## 11. FMZ v3.0.5 验证点

空 JSON：

```python
MANUAL_MARKET_CONTEXT_JSON = ""
```

预期：

- 候选库展示；
- 每条显示 `不可锁定:VRP_CONTEXT_MISSING`;
- 无确认码。

非法 JSON：

```python
MANUAL_MARKET_CONTEXT_JSON = "{bad json"
```

预期：

- 不崩溃；
- 状态栏显示 JSON 错误；
- 无确认码。

合法 JSON 但缺字段：

```json
{"front_anchor_iv": 0.62}
```

预期：

- 不崩溃；
- 显示缺字段；
- 无确认码。

合法完整 JSON：

- 显示 VRP context valid；
- 显示 VRP pass/block；
- pass 的候选生成确认码；
- 输入 `执行:<confirm_code>` 后进入 `PLAN_LOCKED`;
- 因交易门关闭，只输出 order intent / dry-run，不真实下单。

---

## 12. 版本规则

用户要求：

- 小版本递推；
- 如果重复就继续递推小版本号；
- 每 10 个小版本推进一个大版本号。

当前版本：

- 最新已设计/生成：`3.0.4-manual-gate`
- 下一步：`3.0.5-manual-gate`
