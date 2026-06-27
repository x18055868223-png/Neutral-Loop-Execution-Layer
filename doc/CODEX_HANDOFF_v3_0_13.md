# CODEX HANDOFF v3.0.13

## 当前交付

- 仓库：`x18055868223-png/Neutral-Loop-Execution-Layer`
- 本地路径：`C:\Users\Xu\Documents\Neutral-Loop-Execution-Layer`
- 当前版本：`3.0.13-manual-gate`
- FMZ 最新交付：`artifacts/最新交付/spm_manual_gate_execution_fmz_v3_0_13.py`
- 通用 artifact：`artifacts/spm_manual_gate_execution_fmz.py`
- 源码 bundle：`realsrc/spm_manual_gate_execution_fmz.py`
- SHA256：`7D03ED69D1E1EBF381A4BEEF4CF083BBECD390B8B5C797CCDBF6AA880E54EA26`

`artifacts/最新交付/` 已按交付流程清理为只剩一个当前版本文件。

## 本轮完成

v3.0.13 把执行层默认切到小额实盘测试姿态：

- `RUN_PROFILE = "LIVE"`
- `DRY_RUN_PASSED = True`
- `ALLOW_ENTRY_TRADING = True`
- `ALLOW_EXIT_TRADING = True`
- `ALLOW_HEDGE_TRADING = True`
- `RISK_EXIT_MAX_SPEND = 0.001`
- Binance 对冲仍为默认主流程

交易员核心配置入口已收束为：

- `ROBOT_ID`
- `DIRECTION_BIAS`
- `ORDER_AMOUNT`
- `SHORT_DELTA_RANGE`
- `PROTECTION_WIDTH_RANGE`
- `RISK_EXIT_MAX_SPEND`
- `ALLOW_ENTRY_TRADING`
- `ALLOW_EXIT_TRADING`
- `ALLOW_HEDGE_TRADING`
- `KILL_NEW_RISK`
- `EMERGENCY_REDUCE_ONLY`
- `HEDGE_VENUE`
- `HEDGE_BINANCE_INSTRUMENT`
- `HEDGE_BINANCE_MIN_TRADE`
- `HEDGE_BINANCE_EXCHANGE_INDEX`
- `GEX_CONTEXT_API_BASE`
- `GEX_CONTEXT_API_KEY`

已清理旧兼容项：

- 审计卡 / 备注 / 手动上下文 TTL 分钟
- `PLAN` / `ORDER` 轮概念
- 手动选择预览方案编号
- 旧 DTE 区间配置项
- 旧全局交易授权开关
- 旧急停别名
- 旧短腿最低权利金硬门控

## 24h 候选规则

计划库现在围绕内部 `TARGET_DTE_HOURS = 24`：

1. 先选距离 24h 最近的有效到期。
2. 再选它之后的下一个更晚到期。
3. 最多两个期号进入候选库。

短期限候选不再因为权利金薄或 S:PM 释放比例低被直接硬挡。它们会作为警示和评分输入。

真实下单前仍然 fail-closed 的约束：

- 有效报价
- 价差 / 流动性检查
- 正可执行净 credit
- 组合预算
- 风险退出预算
- 订单恢复
- 账本和持仓一致性

排序新增 `credit_on_margin_per_24h`，状态栏会展示期号角色、DTE、净 credit、24h 资金效率和警示原因。

## 验证证据

本轮已运行：

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_0_13.py
```

结果：

- `241 passed, 0 failed`
- bundle check 通过
- 当前交付 py_compile 通过
- 源码和当前交付面旧配置字段扫描无命中
- 四处 bundle hash 一致

## 下一轮建议

新对话从 v3.0.13 的 FMZ 实盘反馈开始，不要回到旧 dry-run 默认或计划轮 / 订单轮模式。

优先观察：

- 近 24h 与次日两个期号的候选展示是否符合交易员体感
- 薄权利金候选是否能展示但仍在真实下单前保留执行安全约束
- 实盘确认码锁定后的预览、合理性检查、将下达订单是否仍一致
- entry / hedge / exit / ledger 的成交后统计是否完整记录执行价差、损耗、手续费和 PnL 字段

如果继续修改，仍按流程：

1. 改 `realsrc/src/` 和测试。
2. 跑 `realsrc/tests/run_all.py`。
3. 跑 `realsrc/build_bundle.py --check`。
4. 同步 versioned artifact、通用 artifact、`artifacts/最新交付/` 单文件。
5. 更新 `CHECKSUMS.txt`。
6. 再 commit / push。
