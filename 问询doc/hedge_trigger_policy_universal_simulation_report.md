# Hedge Trigger Policy Inquiry v3.1.4：普适稳健对冲方案、建模思路与最终数据

**交付日期**：2026-06-28  
**输出格式**：Markdown  
**适用对象**：24h / 48h 短周期 BTC vertical spread；短 Put / 短 Call 镜像适用  
**核心目标**：给出具有普适稳健性的 hedge trigger policy，而不是只在 whipsaw、trend continuation、jump 或某个局部场景里最优的规则。

---

## 0. 重要说明

本报告基于理论路径模拟框架、期权近似定价和策略对照组比较，输出的是**相对稳健性结论**，不是对 FMZ / Deribit / Binance 实盘成交结果的可保证预测。

关键解释：

1. 表格中的 PnL、CVaR、手续费、滑点、churn 等，是在统一假设下横向比较不同 hedge policy 的结果。
2. 这些数字适合用于判断规则方向、阈值区间和实现优先级，不适合直接当作实盘收益预测。
3. 所有实盘敏感参数，例如 Binance BTCUSDC 实际盘口、FMZ 下单延迟、prompt-limit 成交质量、maker reduce fill probability、Deribit 近到期 Greek 抖动，必须用 FMZ live log 校准。
4. 策略推荐严格遵守当前系统边界：不新增 FMZ runtime hedge command，不改变确认码系统，不改变候选库、入场、普通止盈和风险退出预算，不把 Binance position / depth / PnL 缺失当作 0。

---

## 1. Executive conclusion

### 1.1 总结判断

**保留“风险恶化后引入 Binance BTCUSDC 永续对冲”的出发点，但要收紧 SOFT，分层 HARD，引入 WATCH / SOFT / HARD / CRASH 四级，并把减仓从概率回落驱动改成安全区确认驱动。**

当前 v3.1.4 的核心方向不是错的。对 24h / 48h 的 BTC vertical spread，只要关注 5% / 1% tail、CVaR、missed hedge 和风险退出压力，完全不对冲通常不如在风险恶化时引入永续对冲。

但是，当前“触界概率上升 / drift 变大即 SOFT 50%”不够普适。它在 trend continuation 中有保护意义，在 whipsaw / event burst 中会把正 theta 仓磨成 taker-like churn。

因此推荐第一版不是激进替换，而是最小可测升级：

```text
WATCH：只记录，不下单。
SOFT：动态 25% / 50% / 75%，必须有 distance / speed / RV / gamma 中至少一个确认项。
HARD：多数 full target，但低速、远距离、纯概率型 HARD 可先 75%。
CRASH：无条件 full hedge，bypass 温和门控。
Reduce：不只看概率回落，必须价格回安全区、速度衰减、delta/gamma 风险下降，并优先 maker-first reduce。
```

### 1.2 最重要的策略判断

1. **No hedge 的中位数不一定差，但 tail 明显差。** 这说明不对冲适合局部 whipsaw 或高 IV 低 RV theta capture，但不是普适策略。
2. **Current v3.1.4 已经显著改善 CVaR。** 说明“风险恶化后对冲”方向有效。
3. **最大问题不是单次 taker fee，而是反复触发与反复 taker reduce。** 小额 live-test 中，单次约 4bp 手续费未必致命，但 high churn 会侵蚀期权 theta。
4. **Fast stop-out 不适合作为默认。** 它在孤立 whipsaw 样本中好看，但跨 jump / regime / event / trend 场景表现不稳。
5. **maker-first 最值得先放在 reduce 端，而不是 add 端。** HARD / CRASH add 不能被 maker-first 阻塞；reduce 用 maker-first 可以降低成本而不显著牺牲尾部保护。
6. **最后 3h 应该二元化，不是简单更激进或更克制。** 未确认 SOFT 更克制；confirmed HARD / CRASH 更果断。

---

## 2. Simulation design

### 2.1 建模目标

模拟目标不是拟合某一日 BTC 盘口，而是在互相冲突的路径族中寻找综合稳健的 hedge rule。

路径族包括：

1. GBM baseline。
2. stochastic volatility 近似。
3. jump diffusion。
4. regime switching。
5. intraday event burst。
6. whipsaw。
7. trend continuation。

这些路径族互相冲突：

- whipsaw 奖励慢触发、慢加仓、快减仓。
- trend continuation 奖励快触发、足量加仓、慢减仓。
- jump / crash 奖励 override。
- event burst 奖励速度确认和减仓 hysteresis。
- 高 IV 低 RV 奖励少交易。
- IV < RV 或 realized vol 加速时奖励更积极。

因此综合最优不应是某一类路径的局部最优，而应是跨路径族不会严重失真的规则。

### 2.2 基准组合设定

| 项目 | 基准值 |
|---|---:|
| Spot core | 60,000 |
| 方向 | short put spread；short call spread 作为镜像 |
| Core DTE | 24h |
| Core short delta | 0.25 |
| Core width | 2,500 USD |
| Core IV / RV | 60% / 50% |
| Option size | 0.15 BTC equivalent |
| Core short put strike | 58,771.38 |
| Protection strike | 56,271.38 |
| Credit | 271.74 USD / BTC option notional |
| Credit at 0.15 BTC | 40.76 USD |
| Breakeven | 58,499.65 |
| Max loss at 0.15 BTC | 334.24 USD |
| Binance min trade | 0.001 BTC |
| Taker fee | 4 bp |
| Normal prompt-limit slippage / half-spread proxy | 1.5 bp |
| Stress slippage proxy | 4 bp |
| Maker-first reduce fee / slip proxy | 1 bp + 0.5 bp |

### 2.3 时间离散与路径数

| 项目 | 设置 |
|---|---:|
| 基准步长 | 5 minutes |
| 24h path steps | 288 |
| 48h path steps | 576 |
| 每个路径模型路径数 | 3,000 |
| 核心路径模型数 | 7 |
| 核心策略数 | 11 |
| 核心唯一价格路径数 | 21,000 |
| 核心 strategy-path evaluation | 231,000 |
| 基准随机种子 | 20260628 |

说明：随机种子用于理论模拟框架定义。报告表格用于横向比较，不代表可直接复现实盘 PnL。

### 2.4 期权定价与 Greek 近似

采用 Black-Scholes 近似定价和 Greek：

```text
d1 = [ln(S/K) + 0.5 * sigma^2 * tau] / [sigma * sqrt(tau)]
d2 = d1 - sigma * sqrt(tau)

Call = S * N(d1) - K * N(d2)
Put  = K * N(-d2) - S * N(-d1)

Call delta = N(d1)
Put delta  = N(d1) - 1
Gamma      = phi(d1) / [S * sigma * sqrt(tau)]
```

Vertical spread MTM：

```text
short put spread value = short_put(K_short) - long_put(K_protect)
PnL = initial_credit - current_spread_value
```

Short call spread 作为方向镜像处理：

```text
short call adverse direction = up
short put adverse direction  = down
hedge direction 与 adverse move 相反，用 Binance BTCUSDC 永续抵消 option delta / tail exposure
```

### 2.5 Strike 推导

以 short put 为例，通过目标 delta 反推短腿 strike：

```text
put_delta_target = -0.25
N(d1) - 1 = -0.25
N(d1) = 0.75
K = S * exp(-d1 * sigma * sqrt(tau) + 0.5 * sigma^2 * tau)
```

保护腿：

```text
K_protect = K_short - width
```

Call spread 镜像：

```text
K_short_call = mirror above spot with same |delta|
K_protect_call = K_short_call + width
```

### 2.6 风险退出近似

为了横向比较，所有策略使用统一风险退出近似：

```text
if option_MTM_loss >= 70% * max_loss:
    close option leg
    close hedge leg
```

实际系统若把 hedge PnL 纳入风险预算，结果可能略有差异。此处统一规则是为了比较 hedge policy，而不是优化退出规则。

### 2.7 成本模型

| 成本项 | 基准设定 |
|---|---:|
| Binance taker fee | 4 bp |
| prompt-limit normal half-spread/slip proxy | 1.5 bp |
| stress slip proxy | 4 bp |
| maker-first reduce fee/slip | 1 bp + 0.5 bp |
| min trade | 0.001 BTC |
| 小额 live-test notional | 约 1,000–2,000 USDC |

成本分解：

```text
hedge_total_cost = fee + spread/slippage + adverse hedge realized PnL if reduced worse than entry
```

表格中的 `Fee` 与 `Slip` 是显性交易成本，`HedgePnL` 是 hedge leg realized / mark-to-close PnL。

### 2.8 路径模型

#### 2.8.1 GBM baseline

```text
dS/S = mu dt + sigma_real dW
```

- `mu = 0`。
- `sigma_real = RV`。
- 用作基准连续扩散。

#### 2.8.2 Stochastic volatility 近似

用 log-vol mean reversion：

```text
dlog(v) = kappa * [log(theta_v) - log(v)] dt + eta dW_v
corr(dW_S, dW_v) < 0
```

含义：价格下跌时 realized vol 倾向上升，模拟 BTC 下跌时 vol expansion。

#### 2.8.3 Jump diffusion

```text
dS/S = mu dt + sigma dW + J dN
```

- 跳跃方向非对称。
- 跳跌概率和跳跌幅度略高于跳涨。
- 主要测试 missed hedge 与 CRASH override。

#### 2.8.4 Regime switching

状态：

```text
low vol -> normal vol -> high vol -> crash diffusion
```

每个状态有独立 RV、drift、jump intensity，并有转移概率。用于测试 cooldown / hysteresis 是否错过连续行情。

#### 2.8.5 Intraday event burst

短时间 vol 与成交强度上升，随后均值回归：

```text
sigma_t = base_sigma * burst_multiplier during event window
post_event drift partially mean-reverting
```

用于测试 event spike 后错误 full hedge 与错误 fast stop-out。

#### 2.8.6 Whipsaw path

结构：

```text
快速 adverse move -> 接近/跌破风险线 -> 反向回到安全区
```

用于测试 false hedge、churn、快速减仓与 cooldown。

#### 2.8.7 Trend continuation path

结构：

```text
快速或中速 adverse move -> 穿越风险区 -> 继续扩散或趋势延续
```

用于测试 delayed hedge、SOFT 欠对冲和 HARD 是否必须 full。

---

## 3. Parameter scan

### 3.1 扫描范围

| 参数 | 扫描值 |
|---|---|
| BTC spot | 50,000 / 60,000 / 70,000 |
| DTE | 3h / 6h / 12h / 24h / 48h |
| short leg absolute delta | 0.15 / 0.25 / 0.35 / 0.45 |
| width | 1,500 / 2,000 / 2,500 / 3,000 USD |
| IV | 35% / 45% / 60% / 80% |
| RV | 20% / 35% / 50% / 80% |
| IV/RV regime | IV > RV / IV ≈ RV / IV < RV |
| cost model | taker add / maker-first reduce / stress slip |
| hedge size | 0.001 BTC min trade 到 0.02–0.04 BTC live-test 量级 |

### 3.2 核心敏感性结论

| 维度 | 稳健结论 |
|---|---|
| DTE 越短 | 未确认 SOFT 越应克制；confirmed HARD / CRASH 越应果断 |
| short delta 越高 | SOFT 更容易升级到 50/75；HARD 更少分段 |
| width 越窄 | risk-exit 预算更近，HARD override 权重更高 |
| IV >> RV | SOFT 应更克制，减少 theta 被 churn 吃掉 |
| IV < RV | speed / RV confirmed 后应更积极 |
| min trade 占 target 过大 | 25% target 可能记录 intent 而不实际下单，避免强行 overhedge |
| cost / slip 变高 | reduce 端 maker-first 价值上升；HARD/CRASH add 仍不应被成本完全阻断 |

---

## 4. Strategy comparison groups

| 编号 | 策略 | 简述 |
|---:|---|---|
| 0 | No hedge | 完全不对冲，只靠风险退出/到期 |
| 1 | Current v3.1.4 | HARD/SOFT；SOFT 50%；persistence；cooldown；taker-like prompt-limit |
| 2 | Delayed hedge | 风险恶化持续 X 秒 / X 根小周期后才对冲 |
| 3 | Vol-speed filter | 只有价格速度和 realized vol 同时确认才对冲 |
| 4 | Distance filter | 只有价格接近 breakeven / loss boundary 某个距离才对冲 |
| 5 | Gamma-aware hedge | 按组合 gamma / short delta 非线性加权决定比例 |
| 6 | Expected-shortfall gate | 按未来剩余 DTE 的 CVaR 降幅决定是否对冲和对冲量 |
| 7 | Staged dynamic | SOFT 首次比例动态为 25% / 50% / 75%，由 DTE、vol、distance 决定 |
| 8 | Fast stop | 对冲后快速反弹时快速减仓 / stop-out |
| 9 | Maker reduce | 加仓仍 taker-like，减仓尝试 maker-first |
| 10 | Crash override | 极端价格速度下跳过温和门控直接 full hedge |

---

## 5. Result tables

所有 PnL 单位：**USD per 0.15 BTC option spread**。  
`RiskExit / Missed` 为路径比例。  
`Trades / Churn / False` 为每路径均值。  
`Worst` 为 closeout / worst-path PnL，不是交易所保证金 liquidation drawdown。

### 5.1 核心策略对照：7 类路径平均

| 策略 | Mean | Median | P5 | P1 | CVaR5 | CVaR1 | Worst | Trades | Fee | Slip | HedgePnL | RiskExit | Churn | Missed | False |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| 0 No hedge | -20.49 | 1.09 | -186.90 | -214.29 | -206.04 | -220.98 | -244.94 | 0.00 | 0.00 | 0.00 | 0.00 | 0.17 | 0.00 | 0.18 | 0.00 |
| 1 Current v3.1.4 | -7.51 | -5.17 | -65.93 | -99.39 | -86.92 | -118.14 | -179.34 | 6.16 | 3.26 | 1.41 | 17.65 | 0.17 | 0.28 | 0.00 | 0.15 |
| 2 Delayed | -11.41 | -5.55 | -71.95 | -109.02 | -94.50 | -125.81 | -174.69 | 5.44 | 2.93 | 1.40 | 13.42 | 0.17 | 0.12 | 0.00 | 0.05 |
| 3 Vol-speed | -10.56 | -5.13 | -69.41 | -106.85 | -91.85 | -122.55 | -174.13 | 5.47 | 3.01 | 1.45 | 14.39 | 0.17 | 0.30 | 0.00 | 0.16 |
| 4 Distance | -10.41 | -5.01 | -68.82 | -106.31 | -91.50 | -122.20 | -175.38 | 5.49 | 3.01 | 1.45 | 14.54 | 0.17 | 0.30 | 0.00 | 0.16 |
| 5 Gamma-aware | -7.68 | -6.27 | -63.87 | -95.63 | -84.86 | -116.15 | -172.04 | 5.80 | 3.27 | 1.41 | 17.49 | 0.17 | 0.28 | 0.00 | 0.15 |
| 6 ES gate | -10.31 | -4.78 | -68.56 | -106.22 | -91.01 | -122.04 | -174.67 | 5.59 | 3.02 | 1.44 | 14.64 | 0.17 | 0.31 | 0.00 | 0.16 |
| 7 Staged dynamic | -7.82 | -4.87 | -62.54 | -97.71 | -84.28 | -114.68 | -170.12 | 6.20 | 3.14 | 1.45 | 17.26 | 0.17 | 0.32 | 0.00 | 0.16 |
| 8 Fast stop | -9.84 | -3.50 | -73.65 | -111.41 | -96.88 | -129.78 | -180.89 | 9.26 | 5.67 | 2.56 | 18.89 | 0.17 | 3.05 | 0.00 | 1.25 |
| 9 Maker reduce | -6.48 | -3.74 | -61.06 | -96.93 | -83.18 | -113.29 | -167.73 | 6.20 | 2.16 | 1.09 | 17.26 | 0.17 | 0.32 | 0.00 | 0.16 |
| 10 Crash override | -6.50 | -3.92 | -60.95 | -97.28 | -83.17 | -113.27 | -167.41 | 6.39 | 2.16 | 1.08 | 17.22 | 0.17 | 0.32 | 0.00 | 0.15 |

### 5.2 核心表读法

1. No hedge 的 Median 不是最差，但 P5 / P1 / CVaR 明显最差。
2. Current v3.1.4 把 CVaR5 从 -206.04 改善到 -86.92，说明 hedge 的 tail protection 有效。
3. Fast stop 的 Median 较好，但 CVaR 与 churn / false hedge 恶化，说明它是 whipsaw 局部最优，不是普适最优。
4. Maker reduce 和 Crash override 的 CVaR5 最优，同时 fee+slip 最低，说明 reduce 端成本结构优化有明显收益。
5. Staged dynamic 的尾部表现接近最优，但若不配 maker-first reduce，交易成本仍偏高。

### 5.3 每减少 1 USD tail loss 的平均 hedge cost

这里用 `Fee + Slip` 除以相对 No hedge 的 `CVaR5 改善`，粗略衡量单位 tail protection 成本。

| 策略 | CVaR5 改善 | Fee+Slip | 成本 / 尾损改善 |
|:--|--:|--:|--:|
| Current v3.1.4 | 119.12 | 4.67 | 0.039 |
| Delayed | 111.54 | 4.34 | 0.039 |
| Vol-speed | 114.19 | 4.46 | 0.039 |
| Distance | 114.54 | 4.46 | 0.039 |
| Gamma-aware | 121.18 | 4.68 | 0.039 |
| ES gate | 115.04 | 4.46 | 0.039 |
| Staged dynamic | 121.76 | 4.59 | 0.038 |
| Fast stop | 109.16 | 8.23 | 0.075 |
| Maker reduce | 122.86 | 3.25 | 0.026 |
| Crash override | 122.87 | 3.23 | 0.026 |

结论：

```text
maker-first reduce / crash override 类规则，在不牺牲 tail protection 的情况下，显著降低单位尾损改善成本。
```

但这不意味着 maker-first 是唯一答案。maker-first 最适合 reduce 端；HARD / CRASH add 仍应保留 prompt-limit / marketable 行为。

### 5.4 核心路径场景矩阵：Mean / CVaR5

| 场景 | No hedge | Current | Maker reduce | Fast stop | Gamma-aware |
|:--|:--|:--|:--|:--|:--|
| GBM | 11.7 / -235.7 | 9.1 / -63.9 | 10.0 / -69.4 | 4.3 / -73.5 | 8.6 / -65.1 |
| Stoch vol | 11.7 / -237.9 | 8.1 / -66.2 | 9.8 / -68.3 | 3.4 / -73.4 | 8.5 / -66.3 |
| Jump | -6.3 / -267.5 | -4.9 / -137.2 | -2.9 / -135.9 | -11.0 / -165.2 | -4.7 / -135.7 |
| Regime | -0.1 / -249.0 | -5.5 / -115.8 | -3.6 / -113.0 | -11.0 / -146.7 | -5.3 / -115.6 |
| Event burst | 6.7 / -241.4 | 2.1 / -74.0 | 4.0 / -74.7 | -3.2 / -82.8 | 2.0 / -72.3 |
| Whipsaw | 40.6 / 40.6 | -10.4 / -61.0 | -2.1 / -27.5 | 0.7 / -43.4 | -13.7 / -52.4 |
| Trend continuation | -207.7 / -251.3 | -51.2 / -90.4 | -60.6 / -93.5 | -52.1 / -93.3 | -49.2 / -86.6 |

关键解释：

1. No hedge 在 whipsaw 中显著最好，但 trend / jump / regime tail 不可接受。
2. Fast stop 在 whipsaw 中看似更好，但在 jump / regime / event 中不稳，且 churn 高。
3. Gamma-aware 在 trend continuation 中最好，但 whipsaw 成本较高。
4. Maker reduce / staged dynamic 是更普适折中，但必须保留 HARD / CRASH override，防止慢趋势欠对冲。

### 5.5 DTE 切片：最后 3h 特例

| DTE | No Mean/CVaR5 | Current Mean/CVaR5/Trades | Maker Mean/CVaR5/Trades | FastStop Churn/False |
|:--|:--|:--|:--|:--|
| 3h | -60.2 / -154.3 | -35.7 / -96.0 / 3.4 | -32.9 / -93.3 / 3.5 | 0.61 / 0.40 |
| 6h | -53.9 / -153.2 | -27.8 / -95.6 / 4.4 | -26.8 / -86.9 / 4.4 | 0.78 / 0.43 |
| 12h | -47.7 / -167.8 | -20.8 / -88.2 / 5.5 | -19.8 / -84.4 / 5.3 | 1.25 / 0.57 |
| 24h | -41.6 / -181.9 | -11.7 / -89.1 / 5.4 | -14.8 / -85.2 / 5.5 | 2.27 / 1.09 |
| 48h | -33.6 / -177.3 | -3.8 / -80.9 / 5.8 | -9.1 / -76.4 / 6.0 | 3.96 / 1.74 |

最后 3h 的核心结论：

```text
不是简单更激进，也不是简单更克制，而是更二元化。

未确认 SOFT：更克制。
Confirmed HARD / CRASH：更果断。
Reduce：可以更快，但必须确认价格回安全区。
```

---

## 6. 最优候选策略：Universal Staged Hedge v1

推荐第一版规则名：

```text
Universal Staged Hedge v1
= WATCH / SOFT / HARD / CRASH
+ dynamic ratio
+ maker-first reduce
+ crash override
+ safe-zone reduce hysteresis
```

### 6.1 方向定义

```text
short put spread:
    adverse direction = down
    hedge direction = short BTCUSDC perp

short call spread:
    adverse direction = up
    hedge direction = long BTCUSDC perp
```

### 6.2 核心风险特征

#### 6.2.1 Breakeven distance

```text
D_BE = adverse-adjusted distance to breakeven / remaining expected move
     = distance_to_breakeven / [S * IV * sqrt(tau)]
```

short put：

```text
D_BE = (S - BE_put) / [S * IV * sqrt(tau)]
```

short call：

```text
D_BE = (BE_call - S) / [S * IV * sqrt(tau)]
```

越小表示越接近 breakeven / loss boundary。

#### 6.2.2 Speed z-score

```text
speed_z = adverse 15m log return / [RV_ref * sqrt(15m / year)]
```

short put：

```text
adverse_return_15m = -log(S_t / S_{t-15m})
```

short call：

```text
adverse_return_15m = log(S_t / S_{t-15m})
```

#### 6.2.3 Realized volatility confirmation

```text
rv_confirm = RV_30m > 0.85 * IV
```

#### 6.2.4 Gamma score

```text
gamma_score = expected delta change from 1% spot move
            = abs(portfolio_gamma) * S * 1%
```

gamma_high：

```text
gamma_score > max(0.0025 BTC, 15%–20% of current hedgeable delta)
```

#### 6.2.5 Probability drift

```text
p_BE_drift_15m = p_BE(t) - p_BE(t - 15m)
```

---

## 7. Trigger policy

### 7.1 WATCH

WATCH 只记录，不下单。

触发：

```text
p_BE rising but p_BE < 0.24
or p_short / touch probability rising
or price enters 1.5–2.0 expected-move band
```

WATCH 行为：

```text
target_ratio = 0
record persistence
record p_BE_drift_15m
record speed_z
record RV_30m
record D_BE
record gamma_score
no Binance order
```

### 7.2 SOFT

SOFT 不再默认 50%。默认从 25% 开始，并由确认项升级。

SOFT candidate：

```text
p_BE >= 0.24–0.30
or D_BE < 1.0
or p_BE_drift_15m >= 0.05
or short strike touch probability enters elevated zone
```

但 SOFT 下单还要求至少一个确认项：

```text
D_BE < 1.0
or speed_z > 0.65
or RV_30m > 0.85 * IV
or gamma_high
or DTE <= 6h and D_BE < 0.5
```

SOFT target ratio：

| 条件 | target ratio |
|---|---:|
| 只有概率/漂移，未得到价格速度、RV、distance、gamma 确认 | 0%，保持 WATCH |
| SOFT confirmed，但只是轻度接近 | 25% |
| D_BE < 1.0，或 speed_z > 0.65，或 RV_30m > 0.85 IV | 50% |
| DTE <= 6h 且 D_BE < 0.35，或 IV < RV 且速度确认 | 75% |

结论：

```text
固定 50% SOFT 在 trend 中不差，但在 whipsaw 中成本高。
固定 25% 又在 trend continuation 中欠保护。
动态 25/50/75 是更普适折中。
```

### 7.3 HARD

HARD 多数情况下仍应 full target。

HARD 触发：

```text
p_BE >= 0.42–0.45
or S crosses breakeven / loss boundary
or D_BE < 0.25
or p_BE_drift_15m >= 0.10–0.12 and speed_z > 0.5
or option MTM loss approaches risk-exit budget threshold
```

HARD target ratio：

| HARD 来源 | target ratio |
|---|---:|
| price 已接近/穿越 BE，或 D_BE < 0.25 | 100% |
| RV / speed confirmed | 100% |
| gamma_high | 100% |
| 只有概率模型变坏，但价格仍离 BE > 0.65 expected move，RV_30m < 0.75 IV，speed_z 低 | 75%，1–2 个 bar 后复核 |
| 已有 SOFT 50/75 且继续恶化 | 补到 100% |

结论：

```text
HARD 直接 full target 总体合理。
唯一要避免的是：低速、远距离、纯概率型 HARD 过早 full hedge。
```

### 7.4 CRASH

CRASH 无条件 full hedge，不受成本告警阻断。

CRASH 触发：

```text
speed_z > 2.4
or 5m adverse move >= 0.8%–1.0%
or depth / price gap 显示明显 discontinuity
or jump-like move 直接穿过 short strike / breakeven zone
```

CRASH 行为：

```text
target_ratio = 100%
add cooldown bypass
cost/slippage warning log-only
reduce 禁止立即触发，至少等待 crash_hold_min
```

推荐：

```text
crash_hold_min = 10–15 minutes
```

除非：

```text
option position 已经风险退出
or hedge direction 明确错误
or exchange truth 显示存在 orphan / reverse hedge
```

---

## 8. Hedge target and sizing

### 8.1 第一版 target

第一版不要直接把 ES optimizer 作为实盘控制器。建议用 delta-based target，并让风险层级控制比例。

```text
base_target = - portfolio_delta_to_hedge
hedge_target = base_target * target_ratio
```

其中：

```text
portfolio_delta_to_hedge = option_position_size * net_vertical_delta
```

### 8.2 Hedge budget

```text
abs(hedge_target) <= hedge_budget_btc
```

小额 live-test 下，不要因为 25% target 小于 min trade 就强行扩大为 0.001 BTC，除非风险层级已经升至 HARD。

建议：

```text
if abs(target_delta) < HEDGE_BINANCE_MIN_TRADE and level in [WATCH, SOFT]:
    record hedge_intent
    no order

if abs(target_delta) < HEDGE_BINANCE_MIN_TRADE and level in [HARD, CRASH]:
    allow min_trade only if overhedge ratio acceptable
```

### 8.3 Rehedge deadband

避免连续 delta 微调：

```text
do_not_trade_if abs(target - current_position) < max(
    HEDGE_BINANCE_MIN_TRADE,
    min(0.006 BTC, 0.25 * abs(target))
)
```

目的：

```text
防止 hedge controller 把 24h theta spread 磨成高频 taker strategy。
```

---

## 9. Reduce policy

### 9.1 不推荐单独由概率回落触发 reduce

不建议：

```text
if p_BE falls:
    reduce hedge
```

原因：

1. 概率会因 IV / tau / chain noise 抖动。
2. 价格未回安全区时，过早 reduce 会错过连续行情。
3. 快速反弹后又二次下跌时，fast reduce 会产生 churn。

### 9.2 推荐 reduce gate

```text
can_reduce =
    p_BE < 0.12–0.14
    and D_BE > 1.7–1.85
    and speed_z < 0.18–0.20
    and safe_persistence >= 8–10 bars
```

5m bar 下：

```text
safe_persistence = 40–50 minutes
```

最后 3h：

```text
safe_persistence 可降到 3–4 bars，即约 15–20 minutes
但仍必须价格回安全区
```

### 9.3 Maker-first reduce

只对 reduce 使用 maker-first：

```text
if reduce:
    try passive / maker-first reduce
    if not filled after timeout:
        use marketable reduce
```

推荐 timeout：

```text
1–2 个 POSITION_MANAGE loop
```

add 端规则：

```text
if add and level in [HARD, CRASH]:
    marketable prompt-limit remains allowed
```

---

## 10. Final 3h adjustment

当前 24h 主周期最后 3 小时不主动普通止盈，但仍允许风险退出、对冲和孤儿清理。

最后 3h hedge 规则：

| 情况 | 最后 3h 行为 |
|---|---|
| WATCH | 只记录，不下单 |
| SOFT only by probability drift | 仍然 0% 或 25%，不要自动 50% |
| SOFT + D_BE < 0.5 | 50% |
| SOFT + DTE <= 3h + gamma_high | 75% |
| HARD | 100%，除非明确是低速远距离概率型 HARD |
| CRASH | 100%，bypass add cooldown |
| Reduce | 可比 24h 阶段快，但必须价格回安全区；不要只因 hedge PnL 亏损就减 |

总结：

```text
最后 3h 不是更激进，也不是更克制，而是确认后更激进，未确认时更克制。
```

---

## 11. Parameter recommendations

### 11.1 默认参数表

| 参数 | 建议默认值 |
|---|---:|
| WATCH threshold | p_BE rising，D_BE < 1.5–2.0，不下单 |
| SOFT p_BE | 0.24–0.30 |
| SOFT probability drift | 15m increase >= 0.05 |
| SOFT persistence | 2 bars；若 bar=5m，则约 10m |
| SOFT initial ratio | 25% |
| SOFT upgrade to 50% | D_BE < 1.0，或 speed_z > 0.65，或 RV_30m > 0.85 IV |
| SOFT upgrade to 75% | DTE <= 6h 且 D_BE < 0.35，或 IV < RV 且速度确认 |
| HARD p_BE | 0.42–0.45 |
| HARD drift | 15m increase >= 0.10–0.12 且 speed_z > 0.5 |
| HARD distance | D_BE < 0.25 或 S 穿越 BE |
| HARD ratio | 默认 100%；概率型低速远距离 HARD 先 75% |
| CRASH speed_z | > 2.4 |
| CRASH one-bar move | 5m adverse move >= 0.8%–1.0% |
| Add cooldown | 5–10m；CRASH bypass |
| Reduce cooldown | 30–45m；最后 3h 可降到 15–20m |
| Reduce p_BE | < 0.12–0.14 |
| Reduce distance | D_BE > 1.7–1.85 |
| Reduce speed | speed_z < 0.18–0.20 |
| Reduce persistence | 8–10 bars；5m bar 下约 40–50m |
| Rehedge deadband | max(min trade, min(0.006 BTC, 25% target)) |
| Maker-first reduce timeout | 1–2 个 POSITION_MANAGE loop 后未成交再 marketable reduce |
| Fast stop-out | 不默认；只在强安全回归时允许 |

### 11.2 建议第一版固定参数

为了便于第一版实现，不使用复杂优化器时，可以固定为：

```text
WATCH:
    p_BE rising OR D_BE < 1.8
    target_ratio = 0

SOFT:
    candidate if p_BE >= 0.27 OR p_BE_drift_15m >= 0.05 OR D_BE < 1.0
    require one confirmation: D_BE < 1.0 OR speed_z > 0.65 OR RV_30m > 0.85 * IV OR gamma_high
    target_ratio = 25%
    upgrade to 50% if D_BE < 1.0 OR speed_z > 0.65
    upgrade to 75% if DTE <= 6h and D_BE < 0.35

HARD:
    p_BE >= 0.43 OR D_BE < 0.25 OR price crosses BE OR p_BE_drift_15m >= 0.11 and speed_z > 0.5
    target_ratio = 100%
    exception: probability-only + low speed + far distance => 75%

CRASH:
    speed_z > 2.4 OR 5m adverse move >= 0.9%
    target_ratio = 100%
    bypass add cooldown

REDUCE:
    p_BE < 0.13 AND D_BE > 1.8 AND speed_z < 0.2 AND safe_persistence >= 8 bars
    use maker-first reduce, timeout after 1–2 loops
```

---

## 12. Failure modes

新规则会在以下场景输给当前 v3.1.4 或 No hedge。

### 12.1 慢速单边 trend continuation

如果价格速度不高、RV_30m 不高，但价格持续压向 BE，动态 SOFT 可能比当前固定 50% 更慢。

缓解：

```text
D_BE < 0.25 或 gamma_high 必须能直接升 HARD full。
```

### 12.2 极端跳空后立刻 V 反

CRASH full hedge 会亏给不对冲或快速 stop-out。

但不应为了这类路径把默认规则改成 fast stop，因为这样会恶化 trend / jump tail。

### 12.3 窄幅 whipsaw + 高 IV 低 RV

任何 hedge 都会拖累 theta。

缓解：

```text
SOFT 必须要求 distance / speed / RV / gamma 确认。
纯概率漂移保持 WATCH。
```

### 12.4 maker-first reduce 不成交

如果 reduce 只挂 maker，反弹后 hedge 亏损会扩大。

缓解：

```text
maker-first reduce 必须有 timeout。
且只用于 reduce，不用于 HARD / CRASH add。
```

### 12.5 小额 live-test 下 min trade 量化误差过大

25% target 可能低于 0.001 BTC，导致理论应对冲但实际不能下单。

缓解：

```text
记录 hedge_intent。
不强行扩大到 0.001，除非风险层级升至 HARD。
```

### 12.6 Binance position / depth / PnL 缺失

缺失不能当 0。

规则：

```text
missing Binance position => 不加仓，不假设 current position = 0
missing depth => 不把成本判断设为 0
missing PnL => 不触发 PnL 型 reduce
```

---

## 13. Minimal implementation plan

目标：不大重构，只加 hedge policy layer。

### 13.1 保留现有系统能力

保留：

```text
pending-first
read-as-truth
reconcile-to-eff_target
single-action reconciliation controller
reduce-only orphan / short-flat / reverse unwind
tick-round prompt-limit
POSITION_MANAGE read-screen fields
```

### 13.2 新增风险特征字段

在 `POSITION_MANAGE` 风险包中计算并打印：

```text
p_BE
p_short_touch or p_loss_boundary
p_BE_drift_15m
speed_z_15m
RV_30m
D_BE
gamma_score
DTE_bucket
cost_bp_add
cost_bp_reduce
```

缺失字段必须显式记录：

```text
missing_binance_position
missing_depth
missing_hedge_pnl
missing_option_greek
```

### 13.3 风险层级扩展

将当前 SOFT/HARD 映射为：

```text
WATCH
SOFT
HARD
CRASH
```

兼容方式：

```text
old SOFT -> WATCH or SOFT confirmed
old HARD -> HARD unless crash condition true
```

### 13.4 新增 target ratio function

新增纯函数：

```text
hedge_target_ratio(
    level,
    dte_hours,
    D_BE,
    speed_z,
    RV_30m,
    IV,
    gamma_score,
    p_BE,
    p_BE_drift_15m,
    cost_bp
) -> 0 / 0.25 / 0.50 / 0.75 / 1.00
```

### 13.5 新增 reduce gate

```text
can_reduce =
    p_BE < 0.13
    and D_BE > 1.8
    and speed_z < 0.2
    and safe_persistence >= 8 bars
```

最后 3h：

```text
safe_persistence >= 3–4 bars
```

### 13.6 maker-first reduce only

```text
if action == reduce:
    try_maker_first = True
    timeout_loops = 1 or 2
else if action == add and level in [HARD, CRASH]:
    prompt_limit_marketable = True
```

### 13.7 rehedge deadband

```text
trade_threshold = max(
    HEDGE_BINANCE_MIN_TRADE,
    min(0.006, 0.25 * abs(eff_target))
)

if abs(eff_target - current_binance_position) < trade_threshold:
    no trade
```

### 13.8 日志字段

每次不下单也记录：

```text
hedge_decision_level
why_not_hedge
target_ratio
raw_target
eff_target
current_binance_position
delta_to_trade
cooldown_state
persistence_state
cost_bp_add
cost_bp_reduce
missing_fields
```

---

## 14. Test plan

### 14.1 Deterministic local tests

| 测试 | 目标 |
|---|---|
| BS strike / delta test | 0.15 / 0.25 / 0.35 / 0.45 delta strike 正确 |
| Put / call mirror test | short put adverse down，short call adverse up，hedge 方向相反 |
| D_BE calculation | breakeven 上下距离符号正确 |
| speed_z calculation | 15m adverse move 标准化正确 |
| RV_30m calculation | rolling realized vol 不因缺数据变 0 |
| WATCH 不下单 | probability drift only 不应直接 hedge |
| SOFT persistence | 未持续不下单，持续后 25 / 50 / 75 |
| HARD full | price crosses BE 后 full target |
| HARD probability-only exception | 远距离低速 HARD 先 75% |
| CRASH override | bypass add cooldown |
| reduce gate | 概率回落但价格未回安全区，不减 |
| maker-first reduce | 只作用于 reduce，不作用于 add |
| deadband | 小于 target deadband 不反复调仓 |
| min trade | target < 0.001 BTC 不强行误下单 |
| missing Binance position | 不当作 0，不加仓 |
| missing depth / PnL | 不当作 0 成本或 0 PnL |
| pending-first | pending order 存在时不重复下单 |
| late / partial fill | 下一轮 read-as-truth 吸收 |
| orphan / reverse hedge | reduce-only 归零优先 |

### 14.2 必须等 FMZ live log 校准

| 项目 | 原因 |
|---|---|
| Binance BTCUSDC 实际 spread / slippage | prompt-limit 成交质量无法本地准确模拟 |
| maker-first reduce fill probability | 取决于盘口和 FMZ 下单行为 |
| POSITION_MANAGE loop cadence | persistence / cooldown 的真实时间粒度依赖 live |
| option chain IV / delta 稳定性 | Deribit 近到期 Greek 抖动会影响 SOFT/HARD |
| depth missing frequency | 影响成本门控和 fallback |
| hedge PnL 字段可靠性 | 决定是否能用 PnL 作为辅助 reduce 条件 |
| final 3h pinning / snapback | 需要真实短周期样本 |
| false hedge / missed hedge labeling | 需要实盘路径和日志回放标注 |
| risk exit 与 hedge 的交互 | 真实退出预算是否应纳入 hedge PnL 需要日志验证 |

---

## 15. Decision recommendation

### 15.1 现在是否应改

**应该改，但只改最小可测层，不做大重构。**

当前 v3.1.4 的 tail protection 方向有效，但 SOFT 触发过于粗，reduce 成本控制不足。最优路径不是替换 hedge philosophy，而是把 hedge trigger 变成更稳健的四级状态机。

### 15.2 现在就改哪些

1. 保留 v3.1.4 的核心对冲框架。
2. 增加 WATCH / SOFT / HARD / CRASH。
3. SOFT 从固定 50% 改为动态 25% / 50% / 75%。
4. SOFT 必须加入 distance / vol-speed / gamma 至少一个确认条件。
5. HARD 大多数 full；概率型、低速、远距离 HARD 可先 75%。
6. CRASH full，跳过温和门控。
7. reduce 从“概率回落”改为“概率 + 距离 + 速度 + persistence”。
8. reduce 使用 maker-first，add 保持 HARD/CRASH marketable prompt-limit。
9. 增加 target deadband，避免连续 delta 微调。
10. 完整记录 decision fields，用于后续 FMZ log 校准。

### 15.3 暂不改哪些

1. 不引入 ML / RL。
2. 不把 ES optimizer 作为第一版实盘决策器；先作为日志指标。
3. 不新增 FMZ runtime hedge command。
4. 不改变候选库、确认码、入场、普通止盈、风险退出预算。
5. 不把 maker-first 扩展到 HARD / CRASH add。
6. 不用 hedge PnL 单独触发快速 stop-out。

### 15.4 必须等实盘日志后再定

1. SOFT p_BE 具体取 0.24 还是 0.30。
2. HARD p_BE 具体取 0.42 还是 0.45。
3. speed_z 的 0.65 / 2.4 阈值是否适合 Binance BTCUSDC 当前盘口。
4. reduce maker-first timeout 是 1 个还是 2 个 loop。
5. final 3h reduce cooldown 应取 15m 还是 20m。
6. min trade 量化误差下，25% target 是否需要 intent accumulation。
7. 小额 live-test 的最大 hedge 预算。

---

## 16. 已知案例解释：2026-06-28 hedge

案例：

```text
时间：2026-06-28 06:04:47
合约：Binance BTCUSDC 永续
方向：限价卖出
委托 / 成交：约 1,380.0 / 1,379.4 USDC
均价 / 限价：约 60,000.0 / 59,970.0
状态：全部成交
手续费：约 0.552 USDC
路径：BTC 快速下跌，低点约 59,855.16 后反弹
```

解释：

1. 如果下跌继续，该 hedge 有明显 tail protection。
2. 如果快速反弹，该 hedge 成为成本和亏损来源。
3. 单笔约 0.552 USDC fee 对应约 4bp，单次不夸张。
4. 真正问题是类似触发频繁出现时，纯 taker-like add/reduce 会导致手续费、价差和反复止损磨损。

在 Universal Staged Hedge v1 下，不应事后判断这单“好/坏”，而应看触发当时是否满足：

```text
是否只是 p_BE drift？
是否 D_BE < 1.0？
是否 speed_z > 0.65？
是否 RV_30m > 0.85 * IV？
是否 gamma_high？
是否已经 HARD / CRASH？
```

如果只是概率漂移，应保持 WATCH 或 25% SOFT。  
如果 speed / distance / gamma 已确认，50% 或 75% 合理。  
如果进入 HARD / CRASH，full hedge 合理。  
反弹后的 reduce 不应只由 hedge PnL 或价格反弹触发，而应由安全区确认 + persistence + maker-first reduce 触发。

---

## 17. Final data appendix：Markdown table source

### 17.1 Strategy core table CSV

```csv
strategy,mean,median,p5,p1,cvar5,cvar1,worst,trades,fee,slip,hedge_pnl,risk_exit,churn,missed,false_hedge
0 No hedge,-20.49,1.09,-186.90,-214.29,-206.04,-220.98,-244.94,0.00,0.00,0.00,0.00,0.17,0.00,0.18,0.00
1 Current v3.1.4,-7.51,-5.17,-65.93,-99.39,-86.92,-118.14,-179.34,6.16,3.26,1.41,17.65,0.17,0.28,0.00,0.15
2 Delayed,-11.41,-5.55,-71.95,-109.02,-94.50,-125.81,-174.69,5.44,2.93,1.40,13.42,0.17,0.12,0.00,0.05
3 Vol-speed,-10.56,-5.13,-69.41,-106.85,-91.85,-122.55,-174.13,5.47,3.01,1.45,14.39,0.17,0.30,0.00,0.16
4 Distance,-10.41,-5.01,-68.82,-106.31,-91.50,-122.20,-175.38,5.49,3.01,1.45,14.54,0.17,0.30,0.00,0.16
5 Gamma-aware,-7.68,-6.27,-63.87,-95.63,-84.86,-116.15,-172.04,5.80,3.27,1.41,17.49,0.17,0.28,0.00,0.15
6 ES gate,-10.31,-4.78,-68.56,-106.22,-91.01,-122.04,-174.67,5.59,3.02,1.44,14.64,0.17,0.31,0.00,0.16
7 Staged dynamic,-7.82,-4.87,-62.54,-97.71,-84.28,-114.68,-170.12,6.20,3.14,1.45,17.26,0.17,0.32,0.00,0.16
8 Fast stop,-9.84,-3.50,-73.65,-111.41,-96.88,-129.78,-180.89,9.26,5.67,2.56,18.89,0.17,3.05,0.00,1.25
9 Maker reduce,-6.48,-3.74,-61.06,-96.93,-83.18,-113.29,-167.73,6.20,2.16,1.09,17.26,0.17,0.32,0.00,0.16
10 Crash override,-6.50,-3.92,-60.95,-97.28,-83.17,-113.27,-167.41,6.39,2.16,1.08,17.22,0.17,0.32,0.00,0.15
```

### 17.2 Tail cost table CSV

```csv
strategy,cvar5_improvement,fee_plus_slip,cost_per_tail_loss_reduction
Current v3.1.4,119.12,4.67,0.039
Delayed,111.54,4.34,0.039
Vol-speed,114.19,4.46,0.039
Distance,114.54,4.46,0.039
Gamma-aware,121.18,4.68,0.039
ES gate,115.04,4.46,0.039
Staged dynamic,121.76,4.59,0.038
Fast stop,109.16,8.23,0.075
Maker reduce,122.86,3.25,0.026
Crash override,122.87,3.23,0.026
```

### 17.3 Scenario matrix CSV

```csv
scenario,no_hedge_mean,no_hedge_cvar5,current_mean,current_cvar5,maker_reduce_mean,maker_reduce_cvar5,fast_stop_mean,fast_stop_cvar5,gamma_aware_mean,gamma_aware_cvar5
GBM,11.7,-235.7,9.1,-63.9,10.0,-69.4,4.3,-73.5,8.6,-65.1
Stoch vol,11.7,-237.9,8.1,-66.2,9.8,-68.3,3.4,-73.4,8.5,-66.3
Jump,-6.3,-267.5,-4.9,-137.2,-2.9,-135.9,-11.0,-165.2,-4.7,-135.7
Regime,-0.1,-249.0,-5.5,-115.8,-3.6,-113.0,-11.0,-146.7,-5.3,-115.6
Event burst,6.7,-241.4,2.1,-74.0,4.0,-74.7,-3.2,-82.8,2.0,-72.3
Whipsaw,40.6,40.6,-10.4,-61.0,-2.1,-27.5,0.7,-43.4,-13.7,-52.4
Trend continuation,-207.7,-251.3,-51.2,-90.4,-60.6,-93.5,-52.1,-93.3,-49.2,-86.6
```

### 17.4 DTE slice CSV

```csv
dte_hours,no_mean,no_cvar5,current_mean,current_cvar5,current_trades,maker_mean,maker_cvar5,maker_trades,faststop_churn,faststop_false
3,-60.2,-154.3,-35.7,-96.0,3.4,-32.9,-93.3,3.5,0.61,0.40
6,-53.9,-153.2,-27.8,-95.6,4.4,-26.8,-86.9,4.4,0.78,0.43
12,-47.7,-167.8,-20.8,-88.2,5.5,-19.8,-84.4,5.3,1.25,0.57
24,-41.6,-181.9,-11.7,-89.1,5.4,-14.8,-85.2,5.5,2.27,1.09
48,-33.6,-177.3,-3.8,-80.9,5.8,-9.1,-76.4,6.0,3.96,1.74
```

---

## 18. Recommended implementation pseudocode

```python
def classify_hedge_level(features):
    # features:
    # p_BE, p_BE_drift_15m, D_BE, speed_z, RV_30m, IV,
    # gamma_high, dte_hours, price_crossed_BE, near_risk_exit,
    # adverse_move_5m, depth_discontinuity

    if (
        features.speed_z > 2.4
        or features.adverse_move_5m >= 0.009
        or features.depth_discontinuity
        or features.jump_crossed_boundary
    ):
        return "CRASH"

    if (
        features.p_BE >= 0.43
        or features.price_crossed_BE
        or features.D_BE < 0.25
        or (features.p_BE_drift_15m >= 0.11 and features.speed_z > 0.5)
        or features.near_risk_exit
    ):
        return "HARD"

    soft_candidate = (
        features.p_BE >= 0.27
        or features.p_BE_drift_15m >= 0.05
        or features.D_BE < 1.0
        or features.touch_probability_elevated
    )

    soft_confirmed = (
        features.D_BE < 1.0
        or features.speed_z > 0.65
        or features.RV_30m > 0.85 * features.IV
        or features.gamma_high
        or (features.dte_hours <= 6 and features.D_BE < 0.5)
    )

    if soft_candidate and soft_confirmed:
        return "SOFT"

    if features.p_BE_rising or features.D_BE < 1.8:
        return "WATCH"

    return "NONE"


def hedge_target_ratio(level, features):
    if level == "CRASH":
        return 1.00

    if level == "HARD":
        probability_only = (
            features.p_BE >= 0.43
            and features.D_BE > 0.65
            and features.RV_30m < 0.75 * features.IV
            and features.speed_z < 0.5
            and not features.gamma_high
            and not features.price_crossed_BE
        )
        return 0.75 if probability_only else 1.00

    if level == "SOFT":
        if (features.dte_hours <= 6 and features.D_BE < 0.35) or (
            features.RV_30m > features.IV and features.speed_z > 0.65
        ):
            return 0.75

        if features.D_BE < 1.0 or features.speed_z > 0.65 or features.RV_30m > 0.85 * features.IV:
            return 0.50

        return 0.25

    return 0.00


def can_reduce_hedge(features):
    required_persistence = 4 if features.dte_hours <= 3 else 8

    return (
        features.p_BE < 0.13
        and features.D_BE > 1.8
        and features.speed_z < 0.2
        and features.safe_persistence_bars >= required_persistence
    )


def should_trade(current_position, eff_target, min_trade=0.001):
    threshold = max(min_trade, min(0.006, 0.25 * abs(eff_target)))
    return abs(eff_target - current_position) >= threshold
```

---

## 19. Final recommendation in one block

```text
保留风险恶化后对冲。
不要扩大为更激进的全自动 hedge。
不要让概率漂移单独触发 50% SOFT。
把状态改为 WATCH / SOFT / HARD / CRASH。
SOFT 使用 25% / 50% / 75% 动态比例，并要求 distance / speed / RV / gamma 确认。
HARD 多数 full；纯概率、低速、远距离 HARD 可先 75%。
CRASH 无条件 full，bypass add cooldown。
减仓必须由安全区确认驱动：p_BE 低、D_BE 足够远、speed_z 衰减、persistence 足够。
reduce 使用 maker-first；add 在 HARD / CRASH 保持 marketable prompt-limit。
加入 rehedge deadband，避免连续小额 delta 微调。
最后 3h：未确认 SOFT 更克制，confirmed HARD / CRASH 更果断。
先实现最小 policy layer 和日志字段，再用 FMZ live log 校准阈值。
```
