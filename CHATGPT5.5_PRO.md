# GPT-5.5 Pro 接手文档：Human Audit Gate 执行层

## 当前状态

这是独立执行层交接仓，只服务 `spm_manual_gate_execution_fmz.py` 的后续推进。当前版本为 `STRATEGY_VERSION = "3.0.0-manual-gate"`，交付状态为 `MANUAL_GATE_PLAN_READY`。

当前 FMZ 单文件交付物位于 `artifacts/spm_manual_gate_execution_fmz.py`。可继续开发的源码位于 `realsrc/src/`，测试位于 `realsrc/tests/`，打包脚本为 `realsrc/build_bundle.py`。

本交接包不包含信号层 FMZ，不消费信号层输入，也不声明 FMZ 真机 dry-run、交易所只读验收或实盘可用。

## Ponytail 约束

Pro 后续改动默认按 Ponytail/full 模式执行，目标是最小可用、低冗余、少造新东西：

- 先问这个改动是否必须存在。没有当前需求或验证价值的扩展不要做。
- 能复用 `realsrc/src/` 现有资产就复用，不重新发明调用链、状态机、打包器或确认码机制。
- 标准库能解决就用标准库；不要为了轻量解析、校验、复制、hash 或路径处理加依赖。
- 不新增只有一个实现的抽象层、工厂、插件系统、兼容层或“以后可能用”的配置。
- 优先删除和收敛旧残留，而不是为旧路径写兼容。当前版本是独立 manual-gate 执行层。
- 非平凡逻辑必须配最小测试；不要为了覆盖率堆大测试框架或大 fixture。
- 任何新文档都要服务交付和验收，避免写成架构愿望清单。

一句话：先复用，再标准库，最后才写最少的新代码。

## 执行层接口与主链路

人工审计门输入来自 FMZ 顶部参数：

- `MANUAL_PLANNING_ALLOWED`
- `DIRECTION_BIAS`
- `SHORT_DTE_HOURS`
- `SHORT_DELTA_RANGE`
- `PROTECTION_WIDTH_RANGE`
- `ORDER_AMOUNT`
- `MANUAL_AUDIT_CARD_ID`
- `MANUAL_AUDIT_NOTE`
- `MANUAL_CONTEXT_TTL_MIN`

当前主链路：

`人工审计门参数 -> Deribit option-chain -> 同期垂直候选 -> S:PM / execution feasibility / VRP / budget -> 确认码 -> precommit -> entry campaign`

`run_cycle()` 的主要阶段包括：

- `WAIT_MANUAL_AUDIT_GATE`
- `MANUAL_CONTEXT_INVALID`
- `PLAN_MENU_READY`
- `HARD_APPROVAL_WAIT`
- `PLAN_LOCKED`
- `POSITION_MANAGE`
- `RECOVERY_BLOCKED`

人工审批和持仓快照使用 manual lineage：

- `manual_context_id`
- `manual_context_hash`
- `audit_card_id`
- `operator_note`
- `direction_bias`
- `approval_id`
- `plan_hash`

确认码绑定 manual context 与执行事实。人工上下文缺失、过期、配置变化或 plan hash 变化时，旧审批必须失效。

## 安全边界

安全门默认关闭：

- `ALLOW_ENTRY_TRADING = False`
- `ALLOW_EXIT_TRADING = False`
- `ALLOW_HEDGE_TRADING = False`
- `ALLOW_TRADING = False`
- `DRY_RUN_PASSED = False`

后续修改不得把本地测试、`py_compile`、bundle check、hash 一致性说成 FMZ 真机验收。`DRY_RUN_PASSED=True` 只能在真实 FMZ 机器人确认码 dry-run 与交易所只读验证完成后讨论。

VRP 是执行侧价格/过滤门，不判断方向、不选期、不解锁交易门。缺少执行侧 VRP `market_context` 时，只展示候选，不生成可锁定确认码；precommit 继续 fail-closed。

## 后续修改规则

优先修改 `realsrc/src/`，不要直接手改 `artifacts/spm_manual_gate_execution_fmz.py`。标准流程：

1. 修改 `realsrc/src/` 和必要测试。
2. 运行 `realsrc/tests/run_all.py`。
3. 运行 `realsrc/build_bundle.py --check`。
4. 将 `realsrc/spm_manual_gate_execution_fmz.py` 同步到 `artifacts/spm_manual_gate_execution_fmz.py`。
5. 运行 `py_compile` 与 SHA256 一致性检查。
6. 更新 `CHECKSUMS.txt`。

不要重新引入外部信号接收、外部 source selection、旧 lineage package、unsupported execution paths 或 latest-surface stale artifact。

## 验证命令

Windows / Python 3.12:

```powershell
$py = 'C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe'

cd realsrc
& $py tests\run_all.py
& $py build_bundle.py --check
cd ..

& $py -m py_compile `
  realsrc\spm_manual_gate_execution_fmz.py `
  artifacts\spm_manual_gate_execution_fmz.py

Get-FileHash -Algorithm SHA256 `
  realsrc\spm_manual_gate_execution_fmz.py, `
  artifacts\spm_manual_gate_execution_fmz.py
```

Expected current local evidence:

- `realsrc/tests/run_all.py`: `206 passed, 0 failed`
- `realsrc/build_bundle.py --check`: passes
- `realsrc/spm_manual_gate_execution_fmz.py` and `artifacts/spm_manual_gate_execution_fmz.py` share SHA256 `3F05A45695AEB46AF16B895E6A5302C415C6D164A222874C427EEE2EFD18BD6C`

## Suggested Next Work

Good next increments for Pro:

- Improve operator-facing manual audit gate UI text without changing trading gates.
- Add an explicit execution-side VRP market context input contract if needed.
- Strengthen tests around confirm-code invalidation after manual context, risk-policy, or plan changes.
- Keep position management, exits, hedge, and recovery independent from new planning enablement.

Avoid:

- Treating missing VRP context as pass.
- Wiring back to signal-layer files or external package lineage.
- Marking FMZ/live acceptance from local checks alone.
- Editing generated artifact without updating source and tests.
