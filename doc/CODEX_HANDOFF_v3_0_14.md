# CODEX HANDOFF v3.0.14

## 当前交付

- 仓库：`x18055868223-png/Neutral-Loop-Execution-Layer`
- 本地路径：`C:\Users\Xu\Documents\Neutral-Loop-Execution-Layer`
- 当前版本：`3.0.14-manual-gate`
- FMZ 最新交付：`artifacts/最新交付/spm_manual_gate_execution_fmz_v3_0_14.py`
- 通用 artifact：`artifacts/spm_manual_gate_execution_fmz.py`
- 源码 bundle：`realsrc/spm_manual_gate_execution_fmz.py`
- SHA256：`A373AC50F65EB6A02D2418B7B856CF19CD4B03E6C18C034A6CBDD1C1F2F1DBC8`

`artifacts/最新交付/` 已清理为只剩一个当前版本文件。

## 本轮实盘反馈

v3.0.13 在 FMZ Binance Futures 侧报错：

- `GetPositions: Invalid ContractType`
- `Futures_OP 2: Invalid ContractType`

交易所配置顺序确认仍为 `exchanges[0]=Deribit`、`exchanges[1]=Binance Futures`。目标对冲合约仍是 Binance `BTCUSDC` 永续。

## 根因

旧代码把 trader 配置 `HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"` 直接传给：

```python
ex.SetContractType(symbol)
```

但在 FMZ Futures 接口里，`SetContractType()` 接收的是合约类型，永续应为 `swap`；`BTC_USDC` 是交易对/币种选择，不是 contract type。

因此 v3.0.13 实际调用等价于 `SetContractType("BTCUSDC")`，触发 `Invalid ContractType`。

## 修复

v3.0.14 保持 trader 配置入口不变：

```python
HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"
```

内部 Binance 适配层在读仓和下单前统一执行：

```python
ex.IO("currency", "BTC_USDC")
ex.SetContractType("swap")
```

`BTCUSDC`、`BTC_USDC`、`BTC-USDC`、`BTC/USDC`、`BTC_USDC.swap` 会统一归一到 `BTC_USDC`。

## 验证证据

本轮已运行：

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
```

结果：

- `243 passed, 0 failed`
- bundle check 通过
- 四份 bundle hash 一致

最终还需在 FMZ 上用 `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_0_14.py` 复测。不要把本地通过误认为 FMZ live 已通过；实盘确认仍以 FMZ 日志和交易所状态为准。

## 下一步 FMZ 复测重点

1. 启动后不再出现 `Invalid ContractType`。
2. Binance 对冲读仓应落在 `BTC_USDC` 永续 `swap`。
3. 如果仍有交易所侧错误，优先检查 Binance exchange 是否支持 USDC 本位合约、API 权限、以及 FMZ 交易所对象是否允许 `IO("currency", "BTC_USDC")`。
4. 若进入真实对冲下单，继续观察 prompt-limit 价格、reduce_only 方向和成交回写。
