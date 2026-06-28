# Hedge Trigger Policy Inquiry v3.1.4

本文档用于问询 GPT-5.5 Pro / Opus 4.8。目标不是复审当前
`3.1.4-manual-gate` 的代码实现细节，而是要求外部模型从更上层重新审视：

> 对一个 24h / 48h 短周期 BTC 期权价差仓位，是否应该在“风险恶化”时引入 Binance BTCUSDC 永续对冲？
> 如果应该，何时触发、触发多少、何时减仓、如何在尾部保护和 whipsaw 成本之间取得更优综合效果？

请回答方基于理论场景做大量路径模拟，不要只给经验判断。

## 1. 当前判断

目前 v3.1.4 的核心对冲思想没有根本改变：

- 核心仍是：持仓阶段风险恶化后，引入 Binance BTCUSDC 永续对冲来压缩尾部暴露。
- 对冲仍允许 taker-like / marketable prompt-limit 行为，尤其 HARD 风险下不因滑点或成本告警阻断。
- v3.1.4 主要改进的是状态管理与执行控制，而不是风险触发哲学：
  - pending-first，防止同一对冲腿重复下单；
  - read-as-truth，交易所仓位是唯一真值；
  - reconcile-to-`eff_target`，按有效目标与当前仓位差额下单；
  - SOFT 先 50% staged target，持续或恶化后补满；
  - HARD 直接 full target；
  - hysteresis / cooldown 降低反复加减仓；
  - orphan / short flat / reverse hedge 先 reduce-only 归零。

因此，本轮问询的重点应放在：

> “风险恶化即对冲”这个出发点是否足够好，以及如何让触发、目标、持有和解除规则在理论上更优。

## 2. 当前系统边界

回答方必须遵守以下边界：

- 不增加任何 FMZ runtime hedge 指令。
- FMZ runtime 唯一交互入口仍是计划确认码：
  `执行:<确认码>`、`EXECUTE:<确认码>` 或裸确认码。
- 持仓阶段 `POSITION_MANAGE` 是非交互读屏，不做运行时人工授权。
- 不改变候选方案库、确认码、入场确认、普通止盈、风险退出预算逻辑。
- 不把 Binance position / depth / PnL 缺失当作 0。
- 本地测试和 bundle 编译不等于 FMZ live 通过。
- 可以建议未来代码改动，但必须说明哪些可本地确定性测试覆盖，哪些必须等 FMZ 真实日志校准。

## 3. 当前策略背景

交易结构：

- 标的：BTC。
- 常见到期：主做 24h，也允许 48h。
- 结构：短腿 + 保护腿的 vertical spread。
- 方向：短 Put 或短 Call，依据人工配置方向。
- 短腿初始 `|delta|` 通常在 `0.15 - 0.45`。
- 保护腿宽度通常 `2000 - 2500 USD`，近到期可更宽容。
- 入场依赖人工配置、Deribit option chain、S:PM、执行可行性、VRP 有效性、预算过滤和确认码。

退出/止盈：

- 普通止盈是 80% capture。
- 对 24h 主周期，最后 `TAKE_PROFIT_MIN_DTE_HOURS = 3.0` 小时内不主动普通止盈，更倾向持有至交割。
- 但最后 3 小时仍允许风险退出、对冲和孤儿清理。

当前对冲：

- 场所：Binance BTCUSDC 永续。
- 价格：prompt-limit，按 `HEDGE_BINANCE_PRICE_TICK = 0.1` 取整。
- 最小下单：`HEDGE_BINANCE_MIN_TRADE = 0.001 BTC`。
- 当前 v3.1.4 默认 `HEDGE_POLICY_V313_ENABLED=True`。
- HARD/SOFT 分类来自触界概率、概率漂移、价格边界等风险包。
- HARD 直接 full target；SOFT 先 50%，持续或恶化后补满。

## 4. 已知案例

2026-06-28 06:04:47 Binance BTCUSDC hedge 案例：

- 合约：BTCUSDC 永续。
- 方向/类型：限价卖出。
- 委托数量 / 成交数量：约 `1,380.0 / 1,379.4 USDC`。
- 均价 / 限价：约 `60,000.0 / 59,970.0`。
- 状态：全部成交。
- 手续费：约 `0.552 USDC`。
- 当时 BTC 出现快速下跌，图上低点约 `59,855.16` 后反弹。

直观评价：

- 如果下跌继续扩大，该对冲有保护意义。
- 如果市场快速反弹，该对冲会成为成本和亏损来源。
- 如果类似触发频繁出现，纯 taker-like 对冲会产生手续费、价差和反复止损磨损。

请回答方不要只判断该单“好/坏”，而应把它当作一个典型路径样本，放入模拟框架里比较不同规则。

## 5. 需要模拟的核心问题

请基于大量理论路径模拟回答：

1. 对 24h / 48h BTC vertical spread，风险恶化时引入永续对冲是否在总体期望和尾部风险上优于不对冲？
2. “触界概率上升 / drift 变大”是否是足够好的触发信号？是否应加入价格速度、 realized vol、距离 breakeven、距离 loss boundary、gamma、DTE、盘口成本等条件？
3. 当前 HARD/SOFT 两级是否足够？是否需要 WATCH / SOFT / HARD / CRASH 四级？
4. SOFT 首次 50% 是否合理？在不同 IV/RV、DTE、delta、宽度、价格路径下，最佳初始比例是多少？
5. HARD 直接 full target 是否合理？什么情况下 HARD 也应该分段？
6. 对冲目标是否应该基于短腿 delta、组合 gamma、触界概率、expected shortfall、VaR/CVaR、或 breakeven 距离动态计算？
7. 减仓规则应该由概率回落驱动，还是由价格回到安全区、option delta 回落、剩余 DTE、或 hedge PnL / carry 成本驱动？
8. 当前方向键控 cooldown 和 hysteresis 是否会错过真实连续行情？最优时间窗口大约是多少？
9. 对 24h 主周期，最后 3 小时普通止盈暂停后，对冲应该更积极还是更克制？
10. 如果触发对冲后行情反弹，是否应允许快速 stop-out，还是应保持一段时间避免 whipsaw？

## 6. 模拟要求

请不要只做定性分析。请至少设计并报告以下模拟：

### 6.1 市场路径模型

至少覆盖：

- GBM 基线模型。
- Heston / stochastic volatility 或近似随机波动模型。
- Jump diffusion，包含跳跌和跳涨。
- Regime switching：低波动、正常波动、高波动、崩盘扩散。
- Intraday U-shape / event burst：短时间成交量和波动率上升后均值回归。
- Whipsaw path：快速下破风险线后反弹。
- Trend continuation path：下破后继续单边扩散。

### 6.2 参数范围

至少扫描：

- BTC spot：`50,000 / 60,000 / 70,000`。
- DTE：`3h / 6h / 12h / 24h / 48h`。
- 短腿 `|delta|`：`0.15 / 0.25 / 0.35 / 0.45`。
- 保护腿宽度：`1500 / 2000 / 2500 / 3000 USD`。
- IV：`35% / 45% / 60% / 80%`。
- RV：`20% / 35% / 50% / 80%`。
- IV/RV 组合：IV 高于 RV、接近 RV、低于 RV。
- 交易成本：maker / taker fee、半价差、滑点 bps。
- Binance 对冲大小：`0.001 BTC` 量级到小额 live-test 上限。

### 6.3 策略对照组

请至少比较：

0. No hedge：完全不对冲，只靠风险退出/到期。
1. Current v3.1.4：HARD/SOFT + SOFT 50% + persistence + cooldown + taker-like prompt-limit。
2. Delayed hedge：风险恶化持续 X 秒 / X 根小周期后才对冲。
3. Vol-speed filter：只有价格速度和 realized vol 同时确认才对冲。
4. Distance filter：只有价格接近 breakeven / loss boundary 某个距离才对冲。
5. Gamma-aware hedge：按组合 gamma / short delta 非线性加权决定比例。
6. Expected-shortfall hedge：按未来剩余 DTE 的 CVaR 降幅决定是否对冲和对冲量。
7. Staged dynamic：SOFT 首次比例动态为 25% / 50% / 75%，由 DTE、vol、distance 决定。
8. Hedge stop / hold policy：对冲后快速反弹时，比较快速减仓 vs cooldown 持有。
9. Maker-first only for reduce：加仓仍 taker-like，减仓尝试 maker-first。
10. Crash override：极端价格速度下跳过所有温和门控直接 full hedge。

## 7. 评价指标

请用表格报告每组策略在不同场景下的：

- 平均 PnL。
- PnL 中位数。
- 5% / 1% tail PnL。
- max drawdown 或 worst path。
- CVaR / expected shortfall。
- 对冲交易次数。
- 对冲总手续费。
- 价差/滑点成本。
- hedge realized PnL。
- option leg PnL。
- 组合 PnL。
- 到期前被迫风险退出次数。
- hedge churn 次数：短时间内加仓后又减仓，或减仓后又加仓。
- missed hedge 次数：没有对冲但后续进入严重亏损路径。
- false hedge 次数：对冲后价格快速回到安全区。
- 每减少 1 USD tail loss 付出的平均 hedge cost。

请特别关注：

- 小额 live-test 下成本占比是否过高。
- 24h DTE 下最后 3 小时是否应该改变 hedge 触发。
- 高频触发是否会把正期望 theta 仓磨成负期望。
- 对冲是否主要改善尾部，而牺牲均值；这个牺牲是否值得。

## 8. 需要回答方给出的输出格式

请按以下格式回答：

1. Executive conclusion
   明确回答：当前“风险恶化即对冲”的出发点应保留、收紧、放宽，还是替换。

2. Simulation design
   说明模拟模型、参数、路径数、随机种子、成本模型、期权定价/希腊值近似方法。

3. Result tables
   至少给出核心场景矩阵，不要只给文字。

4. Best candidate policy
   给出一套综合最优规则，说明触发、目标比例、加仓、减仓、HARD override、最后 3h 特例。

5. Parameter recommendations
   给出建议默认值，例如：
   - SOFT 初始比例；
   - SOFT persistence；
   - HARD drift；
   - reduce hysteresis；
   - add/reduce cooldown；
   - vol-speed filter；
   - distance-to-boundary filter；
   - final-3h hedge adjustment。

6. Failure modes
   列出新规则在哪些行情会输给当前 v3.1.4。

7. Minimal implementation plan
   如果要改代码，列出最小可测改动，不要建议大重构。

8. Test plan
   给出 deterministic tests 和需要 FMZ live log 校准的项目。

9. Decision recommendation
   给出：
   - 现在是否应改；
   - 改哪些；
   - 暂不改哪些；
   - 哪些必须等实盘日志。

## 9. 特别要求

- 不要只说“用机器学习/强化学习/回测一下”。必须提出可落地的规则和参数。
- 不要把 maker-first 当成唯一答案。本问询核心是“是否该触发对冲、触发多少、持有多久”。
- 不要把缺失盘口、缺失 Binance 仓位、缺失 PnL 当 0。
- 不要建议添加 FMZ runtime hedge command。
- 不要改变候选库和确认码系统。
- 如果建议更复杂的动态规则，必须同时给一个第一版固定参数方案。

## 10. 可以参考的当前 v3.1.4 状态

当前系统已经具备：

- 单动作 reconciliation controller。
- SOFT/HARD 分类。
- SOFT staged target。
- pending order 防重复。
- late fill / partial fill 跨轮吸收。
- reduce-only orphan / short-flat / reverse unwind。
- tick-round prompt-limit。
- `POSITION_MANAGE` 对冲控制器读屏字段。

当前系统尚未解决：

- 风险恶化触发本身是否最优。
- 对冲触发是否应加入价格速度、RV、gamma、distance、DTE 条件。
- SOFT 50% 是否在不同场景下最优。
- HARD full target 是否过度。
- 最后 3 小时普通止盈暂停后，对冲规则是否应动态变化。
- 对冲后反弹时，减仓速度和 cooldown 是否最优。
- 小额 live-test 下，成本与尾部保护的性价比边界。

请从这些未解决项出发，给出理论模拟支持的下一轮策略建议。
