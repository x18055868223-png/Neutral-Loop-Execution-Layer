# Project Rules

## Version Cleanup

- Each small-version delivery must remove obsolete compatibility paths after a strict reference audit.
- Before deleting old code, run `rg` for every old entrypoint/function name and confirm current call sites.
- After deleting old code, run `rg` again and keep only intentional data-field history, not callable legacy gates.
- Do not leave unused fallback implementations "just in case"; if the workflow no longer uses it, delete it.
- Add the smallest runnable test or compile check that would fail if the old path comes back.

## Delivery Boundary

- `artifacts/最新交付` contains the current operator-facing file.
- `artifacts/` keeps versioned backups.
- Do not claim FMZ dry-run, exchange read-only validation, or live readiness from local tests.

## FMZ Runtime Notes

- FMZ Python robots may not define global `HttpQuery`; external HTTP calls should use Python `urllib` in the delivered strategy file.
- Confirmation-code interaction must be configured as command `执行` with type `string`; never use `number` because codes contain letters.
- FMZ 运行时 `GetCommand()` 的唯一策略交互是方案确认：`执行:<确认码>`、`EXECUTE:<确认码>` 或裸确认码。止盈授权、风险退出授权、拒绝、急停、恢复、撤销授权等不得作为运行时命令分支重新引入。
- Binance Futures 永续对冲不要把 `BTCUSDC` 直接传给 `SetContractType()`；先切 `IO("currency", "BTC_USDC")`，再 `SetContractType("swap")`。
- Binance BTCUSDC 永续对冲的 prompt-limit 价格必须按 `HEDGE_BINANCE_PRICE_TICK` 取整：买入向上、卖出向下；不要把原始浮点保护价直接传给 FMZ `Buy`/`Sell`。
- Binance BTCUSDC 默认启用 `HEDGE_POLICY_V313_ENABLED` reconciliation controller：先处理 pending，再读交易所仓位为真，按 `eff_target - current` 单动作下单；仓位读取失败、pending 未清、sub-min 残量必须 fail-closed/hold，不得叠加第二张同向对冲单。活动 pending 部分成交不得提前清空，必须继续阻断新对冲单；终态成交或 stale 残量撤单后，已成交部分必须进入 `hedge_execution_history`。`HEDGE_POLICY_V313_ENABLED=False` 才走旧 `bnc_place_hedge` prompt-limit 全量路径。
- 对冲 controller 的 HARD 可以绕过 SOFT persistence、add cooldown 和 SOFT slippage guard；成本/滑点只告警不阻断 HARD。SOFT 必须支持 50% staged target、持续后补满、减仓 hysteresis 和方向 cooldown，且孤儿/短腿归零/反向 hedge 必须优先 reduce-only 归零。
- 入场 precommit 必须检查同腿活动订单冲突：残留 `entry_short` 或额外 `entry_prot` 均 fail-closed；保护腿只能复用当前锁定计划记录的持久订单 id。
- 风险退出必须同时满足预算价格和卖一深度覆盖剩余短腿数量；盘口深度缺失时显示 `数据缺口` 并 fail-closed，允许既有逻辑评估对冲兜底，不得把缺口显示为 0。
- 普通 80% 捕获止盈必须同时满足剩余短腿 DTE 大于 `TAKE_PROFIT_MIN_DTE_HOURS`（当前 3.0h）；最后 3 小时只暂停普通止盈，不得阻断风险退出、风险对冲、孤儿对冲清理或交割结算。

## v3.2.3 Hedge And Settlement Closeout Override

- Current hedge execution is V32-only for Binance BTCUSDC. `HEDGE_POLICY_V32_ENABLED`
  is the primary switch; `HEDGE_POLICY_V313_ENABLED` is only a compatibility
  alias for older references. Disabling V32 must hold with
  `HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT`, not fall back to old hedge submit.
- Minimal V32 hedge supports `HEDGE_VENUE = "BINANCE"` only. Deribit option
  entry/exit/quote paths remain separate and must not be confused with the
  hedge venue.
- Binance hedge submit requires order lifecycle methods (`GetOrder` and
  `CancelOrder`). If a live submit returns no order id, record
  `BINANCE_ORDER_ID_MISSING` / `SUBMIT_UNKNOWN_RECENT` and wait for the next
  exchange-position read instead of submitting another hedge.
- Settlement reconciliation must preserve accounting status. Expired option
  legs record settlement cashflow as `COMPUTED`, `ESTIMATED`, or `DATA_GAP`;
  protection recovery fills must record net recovery value and fees; final PnL
  is only final when both option legs are closed.

## Operator Surface

- `LogStatus` 是交易员主阅读面板，必须保留完整状态展示层：`交互控制台`、`运行概览`、`完整主链模块回显`、`固定备选方案库`、候选/选用方案预览、`将下达订单`、`合理性检查`。
- 清理显示层或判断“死代码”前，必须跨历史 artifact 回溯对比最后一个完整版本；不要只用最近一个残缺版本当基准。
- 固定备选方案库必须直接显示确认码/锁定状态；如果最终展示库没有近 24h 候选，最早可用到期显示为 `最近可用`，不要让整表都显示为 `次日备选`。
- 近 24h 低价保护腿的可执行性不要只按相对价差硬拒；只要买入 ask 存在、短腿可卖、净 credit 为正且保护腿绝对 bid-ask 宽度在小额阈值内，应允许进入候选并以可执行性评分体现质量。
- 末日轮/近 24h 候选允许使用更宽容的保护腿宽度下限（当前 1500），并可为同一合格短腿保留少量不同保护腿宽度；普通更晚到期仍按常规 `PROTECTION_WIDTH_RANGE` 控制，避免候选库膨胀。
- 固定备选方案库的 `_G` 稳定缓存必须绑定 `STRATEGY_VERSION`；升级后缺版本或旧版本的冻结菜单必须失效重建，避免 FMZ 展示上一版旧方案。
- 方案确认后进入 entry campaign，必须围绕已锁定方案继续展示、评估和下单；无成交达到等待上限不能清锁回方案库，只有人工拒绝、确认过期、预提交失败后已有真实进度、重启恢复接管或完整建仓才允许退出锁定方案。
- 保护腿确认方案后必须进入持久 maker 挂单：目标价取当前 mark 的买入方向 tick 价，若 mark 触及/高于卖一则压到 `best_ask - tick` 保持 post-only；同一保护腿订单每轮只查状态，只有目标价变化至少 1 tick 才撤旧单并重挂，且 `wait_start_ms` 不因重挂重置。
- 保护腿从首次 maker 挂单起超过 10 分钟后，允许取消 maker 并受控吃当前卖一；此时不再要求卖一价只高出 mark 一个 tick，但必须满足卖一深度覆盖剩余数量、组合净 credit 仍不低于 `ENTRY_MIN_NET_CREDIT`。深度或净 credit 不合格时继续保持/重挂 mark maker，不能清锁或推新方案。
- 卖方腿必须等保护腿已有成交后才允许执行；卖方腿保持 post-only maker 逻辑，当前挂单存续 60 秒并可按后续实盘反馈单独优化。
- 持仓后 `POSITION_MANAGE` 的 `LogStatus` 是交易员主读屏层，不能只靠 `hedge_state`、`venue=...`、`entry_p=...` 这类机器串承载信息；必须结构化展示 `持仓总览`、`止盈/退出预算`、`风险与对冲`、`记账/对账/恢复`，中文语义优先，关键英文 reason/code 保留为回溯线索。
- 持仓阶段顶部表是非交互的“当前环节摘要”，只能展示阶段、生命周期、当前自动动作、活动订单、止盈/风险/对冲状态和组合浮盈亏；不得展示授权码、风险退出码、拒绝/恢复/急停等按钮提示。
- 止盈目标价和对冲触发目标价需要尽量换算为标的物价格展示。止盈标的价用 delta 线性估算，缺 delta/spot/盘口时显示明确 `数据缺口`；对冲触发价优先显示显式价格线，否则可用当前风险模型反推展示估算价，不改变原交易判定。
- 持仓总览必须分开显示期权腿浮动盈亏、期货对冲腿浮动盈亏、组合浮动盈亏，并统一折 USD。无对冲仓位显示 `对冲未启用`，不能把缺失或未启用渲染成 0。
- 展示层不得把缺失数据渲染成误导性 0 值；盘口、delta、概率、预算、对账等缺口统一显示 `数据缺口` 和原因，并说明影响范围（例如禁新增对冲、仅保守持仓、只影响展示）。
- 持仓阶段不再推送新的方案库干扰读屏；方案库和确认码展示属于计划轮，锁定/建仓/持仓阶段应围绕当前选定结构展示评估、下单、预算、对冲和恢复链路。
- `Log` 只作为事件流和异常流，不要每轮重复刷空方案、同一个最优方案或每轮 mark 微动。普通 `POSITION_MANAGE` 轮只刷新 `LogStatus`，不写 `Log`；只有错误、数据缺口、订单/成交/撤单、止盈、风险退出、对冲、交割结算、恢复或阶段变化才进入 `Log`。
- 配置层必须保留中文语义注释，说明每个交易员可编辑字段的实盘含义；删除旧字段时只删字段，不要把有用中文说明一起抹掉。
- 启动后允许做一轮只读自检，覆盖 Deribit 行情/账户、GEX 数据、Binance 对冲读仓和模块配置；自检结果应进入状态面板，不能被本地测试误称为 FMZ live 通过。
