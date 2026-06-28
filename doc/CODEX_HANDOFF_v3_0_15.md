# CODEX HANDOFF v3.0.15

## 当前交付

- 仓库：`x18055868223-png/Neutral-Loop-Execution-Layer`
- 本地路径：`C:\Users\Xu\Documents\Neutral-Loop-Execution-Layer`
- 当前版本：`3.0.15-manual-gate`
- FMZ 最新交付：`artifacts/最新交付/spm_manual_gate_execution_fmz_v3_0_15.py`
- 通用 artifact：`artifacts/spm_manual_gate_execution_fmz.py`
- 源码 bundle：`realsrc/spm_manual_gate_execution_fmz.py`
- SHA256：`01A25D5D0630C6E5771DC48A7AA3FBA73AA257D9FEBCE973D4FB17A4C558870A`

## 本轮结论

v3.0.14 的 Binance `Invalid ContractType` 已解除。截图显示状态展示层没有在 v3.0.14 修复里被删除：`LogStatus` 仍包含 `交互控制台` 和 `运行概览` 两张置顶表；第一张截图停在交互控制台页，第二张截图切到运行概览页后完整信息可见。

本轮不从旧 artifact 整文件覆盖展示层，只做三项小修：

1. 保留完整状态面板，并在 `运行概览` 增加 `启动自检` 行。
2. 普通 `Log()` 只在摘要变化时写入，避免每 3 秒重复刷空方案或同一方案；`LogStatus` 仍每轮刷新供交易员阅读。
3. 恢复 `config.py` 顶部中文语义注释，但不恢复旧审计卡、PLAN/ORDER、单一 `ALLOW_TRADING` 等废弃字段。

## 启动自检

`main()` 启动后会跑一轮只读自检并写入 `_G("spm_startup_self_check_v1")`：

- 配置合法性
- Deribit index price
- Deribit option instruments
- Deribit account summary
- GEX_CONTEXT 数据接口
- Binance BTCUSDC 永续对冲读仓（当 `HEDGE_VENUE="BINANCE"`）

自检结果进入 `运行概览` 的 `启动自检` 行。它只能证明启动时接口读路径可用，不能替代 FMZ 实盘成交验证。

## 验证证据

本轮源码层已运行：

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
```

结果：

- `246 passed, 0 failed`

交付时继续按流程运行：

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_0_15.py
```

## 下一步 FMZ 复测重点

1. `Invalid ContractType` 不应再出现。
2. `运行概览` 应显示 `启动自检`，如有 `WARN`，按具体接口名排查。
3. 日志区不应每 3 秒重复刷同一条 `RUN_CYCLE:HARD_APPROVAL_WAIT`。
4. 交易员主要从 `状态信息` 的状态面板读候选和操作提示，不从日志区选方案。
