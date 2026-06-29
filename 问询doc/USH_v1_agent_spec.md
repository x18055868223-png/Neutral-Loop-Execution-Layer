# Universal Staged Hedge v1 — Agent 实施规格（USH-v1）

**目标系统**：24h / 48h 短周期 BTC vertical spread（short put spread / short call spread 镜像），Binance BTCUSDC 永续对冲，FMZ Python 单文件部署。
**本规格定位**：把 `hedge_trigger_policy_universal_simulation_report.md` 中以「区间 + 5m bar 假设」表达的 *Universal Staged Hedge v1* 设计，固化为**一套无歧义、可直接实现、可逐项开关、可逐项测试**的工程规格，交付给实现 agent 落地。
**语言约定**：中文叙述 + 英文技术术语。

---

## A. Agent 执行须知（先读这一段）

1. **CONFIG 即唯一真相**。所有阈值都在 §5 的 `USH` CONFIG 区集中定义。实现 agent **不得**在函数体内写死任何魔法数，必须引用 CONFIG。源报告里出现的区间（如 `p_BE 0.24–0.30`）在本规格里已收敛成**单一第一版固定值**，并标注 `[CAL]` 表示「上线后用 FMZ live log 校准」。Agent 实现第一版固定值即可，不要自己在区间内挑数。
2. **纯函数必须按 §7–§11 的伪代码逐字实现**，输入输出签名不变，便于 §18 的 deterministic test 直接对拍。
3. **全部新逻辑挂在开关后**（§17）。主开关 `HEDGE_USH_V1_ENABLED=False` 时，系统回到现有 v3.1.4 行为，零行为变化、零额外 I/O。每个子特性单独可关，便于消融与回滚。
4. **§1 的硬边界是不可违反 invariant**。任何实现若需要触碰这些边界，必须停下来报告，而不是自行变通。
5. **不要新增任何 FMZ runtime hedge command，也不要把对冲接入确认码流程**。对冲始终是 `POSITION_MANAGE` 内部的自动 reconciliation 动作（与当前已自动下 Binance 限价单的行为同一条执行路径），确认码系统只管候选计划/入场，二者不交叉。
6. **缺失即缺失，绝不当 0**（§15）。这是安全红线，违反会直接造成错误加仓 / 错误成本判断。
7. **本地编译 / 本地单测通过 ≠ FMZ 实盘通过**。§18 明确区分了「本地可判定」与「必须等实盘日志校准」两类，agent 交付时必须同时给出本地测试结果与待校准清单。

---

## B. 设计共识（为什么是四级 + 确认驱动）

源报告与本会话中一套独立的 Monte-Carlo 路径模拟（GBM / stochastic-vol / jump / regime / intraday-burst / whipsaw / trend continuation 七族路径）得到**方向一致**的结论，构成本规格的依据：

| 结论 | 证据方向 | 落到规格的做法 |
|---|---|---|
| 「风险恶化后再对冲」方向正确，No-hedge 的 tail（CVaR5/P1）不可接受 | 对冲把 Mixed/CALM CVaR5 显著抬升 | **保留**对冲哲学 |
| 纯「触界概率上升 → SOFT 50%」不普适：trend 有用，whipsaw / event-burst 把正 theta 磨成 churn | whipsaw 场景下 No-hedge 反而最好 | SOFT 默认降到 25%，**强制要求确认项** |
| sizing 应跟 **gamma / delta-speed**，而非纯 breach probability | gamma-aware 在 trend continuation 最优、churn 最低 | §8 ratio 用 distance/speed/RV/gamma 升级 |
| **maker-first 放 reduce 端**性价比最高（cost / tail-improvement 最低），但不能阻塞 HARD/CRASH add | maker-reduce / crash-override 的 cost-per-tail 最低 | §11 reduce 用 maker-first，§12 add 保持 marketable |
| **fast stop-out 不能作默认**：whipsaw 局部最优，跨 jump/regime/event 不稳、churn/false 高 | fast-stop 的 CVaR、churn、false 全面恶化 | reduce 必须**安全区确认 + persistence**，不做快速止损 |
| **vol-speed AND-gate / first-hedge-delay 偏弱**：门控过严会漏掉连续行情 | delayed / vol-speed-AND 在 trend 欠保护 | confirmation 用 **OR**（任一确认即可），不用 AND |
| 最后 3h 不是「更激进 or 更克制」，而是**二元化**：未确认更克制，confirmed 更果断 | DTE 越短 churn/false 越敏感 | §13 最后 3h 分支 |
| 小额 live-test 的真问题不是单笔 4bp，而是 **min-trade 量化 + 反复 churn** | trades/churn 随 DTE 缩短上升 | §9 intent 机制 + §10 deadband |

> 这些数字用于**判定规则方向与阈值区间**，不是实盘 PnL 预测；上线前所有 `[CAL]` 项必须用 FMZ live log 校准。我不是持牌投资顾问，本规格是工程化的对冲控制设计，不构成投资建议。

---

## 1. 不可违反的硬边界（Invariants）

实现 agent 在任何情况下都不得违反：

1. **不新增 FMZ runtime hedge command**；不改变确认码语义（`执行:<确认码>` / `EXECUTE:<确认码>` / 裸确认码）。对冲是自动 reconciliation，不走确认码。
2. **不改动**：候选库、确认码生成、入场确认、普通止盈逻辑、风险退出预算逻辑。USH-v1 只接管「对冲触发 + 对冲 sizing + 对冲 reduce + 对冲日志」。
3. **`POSITION_MANAGE` 保持 non-interactive read-screen**：它读状态、算风险特征、执行自动对冲 reconciliation，不向用户索取输入。
4. **缺失绝不当 0**：缺失 Binance position → 不加仓、不假设 current=0；缺失 depth → 不把成本判定设为 0；缺失 hedge PnL → 不触发任何 PnL 型动作。
5. **对冲方向单边、不可投机翻向**：short put → 只允许 short perp 段（`[base_target, 0]`）；short call → 只允许 long perp 段（`[0, base_target]`）。永不越过 0 到反方向建立投机仓。
6. **pending-first / read-as-truth / 单动作 reconciliation** 既有机制保留，不被新逻辑绕过。
7. **本地测试通过不等于实盘通过**；交付必须区分本地可判定项与待实盘校准项（§18）。
8. **不引入 ML / RL**；ES optimizer 第一版**只作为日志指标**，不作实盘决策器。
9. **maker-first 不扩展到 HARD / CRASH 的 add**；HARD/CRASH add 必须保持 marketable prompt-limit。

---

## 2. 系统集成点（挂在哪里、复用什么）

USH-v1 是 `POSITION_MANAGE` 风险包内的一层，替换现有 v3.1.3/v3.1.4 的「对冲触发 + sizing」分支，**复用**下游执行与对账：

```
POSITION_MANAGE loop（每轮，read-screen）
  ├─ 读交易所真相：option 持仓/Greek、Binance position/depth/PnL（缺失显式标记）
  ├─ pending-first：存在未结对冲单 → 进入 §11.3 maker-first timeout 处理，不重复下单
  ├─ 计算风险特征（§4）→ 写入 state ring buffer
  ├─ classify_level()（§7） → level ∈ {NONE, WATCH, SOFT, HARD, CRASH}
  ├─ hedge_target_ratio()（§8） → ratio ∈ {0,0.25,0.5,0.75,1.0}
  ├─ sizing（§9）：base_target → raw_target → eff_target（含 min-trade / intent / overhedge）
  ├─ deadband（§10）：|eff_target - current| 太小 → 不动
  ├─ 决定动作类型：add / reduce / hold；reduce 走 maker-first（§11），add(HARD/CRASH) 走 marketable（§12）
  ├─ 调用【既有】单动作 reconcile-to-eff_target 控制器（tick-round prompt-limit、reduce-only orphan/reverse）
  └─ 写一行决策日志（§16），即使不下单也写
```

> **关键**：USH-v1 **不**自己发交易所 API 调用；它只产出 `(action, eff_target, exec_style)`，交给既有 reconciliation 执行器。这样既不新增 command，也复用所有已经过实盘验证的下单/对账细节。

---

## 3. 方向与镜像统一约定

所有公式对两个方向**用同一套符号**实现一次即可。引入 `dir_sign`：

```
short put spread :  adverse = 价格下跌 ;  dir_sign = +1 ;  hedge = SHORT perp
short call spread:  adverse = 价格上涨 ;  dir_sign = -1 ;  hedge = LONG  perp
```

- `breakeven` 记为 `BE`。`width` 为保护腿宽度（USD）。
- **adverse 距离**（>0 表示仍在安全侧，越小越危险）：
  `dist_be_usd = dir_sign * (S - BE)`
  - short put：`S - BE`（S 在 BE 上方为正＝安全）
  - short call：`BE - S`
- **adverse 对数收益**（>0 表示朝不利方向走）：
  `adverse_ret(window) = -dir_sign * ln(S_t / S_{t-window})`
- **base_target（满额对冲，BTC，带正负号表示方向）**：
  `base_target = - pos_delta * option_size_btc`
  其中 `pos_delta` 为 vertical spread 的组合 delta（short put spread 为正 → base_target 为负＝short perp；short call spread 为负 → base_target 为正＝long perp）。方向自动正确，无需分支。
- **单边夹紧**（invariant §1.5）：`eff_target` 必须落在 `[min(base_target,0), max(base_target,0)]`，即与 `base_target` 同号且幅度不超过满额。

---

## 4. 风险特征计算（含时间窗映射与缺失处理）

### 4.1 时间窗一律用 wall-clock 分钟（不用「bar 数」）

源报告里的 `bar` 是 5m 建模代理；实盘 `POSITION_MANAGE` loop cadence 是 live 变量，**因此本规格统一用分钟**。Agent 维护一个按 loop append 的 ring buffer：

```
ring: list of samples, each = { ts, S, p_BE, IV, RV_inst }
```

取窗口端点时，用「最接近 t − window_min 的样本」做差分。窗口默认值见 §5：`SPEED_WINDOW_MIN`、`RV_WINDOW_MIN`、`DRIFT_WINDOW_MIN`。

> 若 ring buffer 中 `t − window_min` 之前**没有足够样本**（如开仓不久），相应特征标记为 `unavailable`，**按缺失处理**（见 §4.7），**不**用 0 代入。

### 4.2 p_BE（finish-past-breakeven 概率，BS lognormal, drift=0）

```
tau   = 剩余到期年化
sig   = IV（定价用 IV）
d2_BE = ( ln(S / BE) - 0.5 * sig^2 * tau ) / ( sig * sqrt(tau) )

short put :  p_BE = N(-d2_BE)        # P(S_T < BE)
short call:  p_BE = N( d2_BE)        # P(S_T > BE)
```

`p_BE_drift = p_BE(t) - p_BE(t - DRIFT_WINDOW_MIN)`（缺历史则 unavailable）。

### 4.3 D_BE（到 breakeven 的「剩余预期波动」标准化距离）

```
exp_move = S * IV * sqrt(tau)             # 到期前的 1σ 预期幅度
D_BE     = max(dist_be_usd, 0) / exp_move # 越小越危险；价格已越过 BE 时 dist_be_usd<=0 → D_BE=0
```

### 4.4 speed_z（窗口内 adverse 速度，相对预期）

```
sig_ref = IV                              # [CAL] 可改 max(IV, RV_30m)
exp_win = sig_ref * sqrt(SPEED_WINDOW_MIN / MIN_PER_YEAR)
speed_z = adverse_ret(SPEED_WINDOW_MIN) / exp_win
```

`adverse_move_5m = max(adverse_ret(5), 0)`（CRASH 用，单位：对数收益≈百分比）。

### 4.5 RV_30m 与确认

```
RV_30m     = 窗口 RV_WINDOW_MIN 内的 realized vol（年化），样本不足 → unavailable
rv_confirm = (RV_30m is available) and (RV_30m > RV_CONFIRM_FRAC * IV)   # 默认 0.85
```

### 4.6 gamma_score 与 gamma_high

```
port_gamma   = vertical_spread_gamma * option_size_btc   # 组合 gamma（BTC/价格^2 量纲，取绝对值用）
gamma_score  = abs(port_gamma) * S * 0.01                # 1% spot 动作引起的 delta 变化（BTC）
hedgeable    = abs(pos_delta) * option_size_btc          # 满额对冲幅度 = abs(base_target)
gamma_high   = gamma_score > max(GAMMA_ABS_BTC, GAMMA_FRAC * hedgeable)   # 默认 0.0025, 0.15
```

### 4.7 缺失字段处理（硬规则）

| 缺失项 | 规则 |
|---|---|
| `missing_binance_position` | 不加仓、不 reduce；current 视为「未知」，本轮只记录、不调仓 |
| `missing_depth` | `cost_bp_*` 标记 unavailable；不得据此判 0 成本；HARD/CRASH add 仍可下（成本告警 log-only），SOFT 在成本未知时**不升级**比例 |
| `missing_hedge_pnl` | 禁止任何 PnL 型判断（本规格本就不用 PnL 触发，确保保持） |
| `missing_option_greek` | `pos_delta/gamma/p_BE/D_BE` 不可信 → level 至多停在 WATCH（记录），不主动 add；除非 §7.1 的 `price_crossed_BE`（纯价格、无需 Greek）成立则允许 HARD |
| 任一窗口特征 unavailable | 该确认项视为「未确认」，不能作为升级理由；但不可阻断基于价格的 HARD/CRASH |

---

## 5. CONFIG 默认参数（第一版固定值，`[CAL]`=待实盘校准）

```python
USH = {
  # ---- 主/子开关（§17）----
  "HEDGE_USH_V1_ENABLED":        True,   # 主开关；False → 回到 v3.1.4
  "USH_DYNAMIC_SOFT_ENABLED":    True,   # 关 → SOFT 恒为 SOFT_FALLBACK_RATIO
  "USH_GAMMA_CONFIRM_ENABLED":   True,
  "USH_CRASH_OVERRIDE_ENABLED":  True,
  "USH_MAKER_FIRST_REDUCE":      True,
  "USH_DEADBAND_ENABLED":        True,
  "USH_INTENT_BELOW_MINTRADE":   True,
  "USH_FINAL3H_BRANCH_ENABLED":  True,

  # ---- 时间窗（分钟，wall-clock）----
  "SPEED_WINDOW_MIN":  15,
  "RV_WINDOW_MIN":     30,
  "DRIFT_WINDOW_MIN":  15,

  # ---- WATCH ----
  "WATCH_DBE_MAX":     1.8,   # D_BE < 1.8 且 p_BE 上升 → 至少 WATCH

  # ---- SOFT ----
  "SOFT_PBE":          0.27,  # [CAL] 0.24–0.30
  "SOFT_DRIFT":        0.05,  # 15m p_BE 增量
  "SOFT_DBE_CAND":     1.0,
  "SOFT_PERSIST_MIN":  10,    # 候选需持续 ~10min 才下单
  "SOFT_CONFIRM_SPEEDZ": 0.65,
  "SOFT_UP50_SPEEDZ":  0.65,
  "SOFT_UP50_DBE":     1.0,
  "SOFT_UP75_DBE":     0.35,  # 且 DTE<=6h
  "SOFT_UP75_DTE_H":   6.0,
  "SOFT_FALLBACK_RATIO": 0.50, # 动态关闭时的退化固定比例（=旧行为）

  # ---- HARD ----
  "HARD_PBE":          0.43,  # [CAL] 0.42–0.45
  "HARD_DBE":          0.25,
  "HARD_DRIFT":        0.11,  # 且 speed_z>HARD_DRIFT_SPEEDZ
  "HARD_DRIFT_SPEEDZ": 0.5,
  "HARD_PROB_ONLY_RATIO": 0.75, # 纯概率/低速/远距离 HARD 先到 75%
  "HARD_PROBONLY_DBE": 0.65,    # 远距离判据
  "HARD_PROBONLY_RVFRAC": 0.75, # RV_30m < 0.75*IV 视为低 RV

  # ---- CRASH ----
  "CRASH_SPEEDZ":      2.4,   # [CAL]
  "CRASH_MOVE_5M":     0.009, # 5m adverse >= 0.9%
  "CRASH_HOLD_MIN":    12,    # crash 后最短持有，禁 reduce
  "RV_CONFIRM_FRAC":   0.85,

  # ---- gamma ----
  "GAMMA_ABS_BTC":     0.0025,
  "GAMMA_FRAC":        0.15,

  # ---- cooldown（分钟）----
  "ADD_COOLDOWN_MIN":        5,   # CRASH bypass
  "REDUCE_COOLDOWN_MIN":     30,  # [CAL] 30–45
  "REDUCE_COOLDOWN_F3H_MIN": 15,

  # ---- reduce gate ----
  "REDUCE_PBE":          0.13,   # [CAL] 0.12–0.14
  "REDUCE_DBE":          1.8,    # [CAL] 1.7–1.85
  "REDUCE_SPEEDZ":       0.20,   # [CAL] 0.18–0.20
  "REDUCE_PERSIST_MIN":  40,     # 安全区持续 ~40min（[CAL] 40–50）
  "REDUCE_PERSIST_F3H_MIN": 15,  # 最后 3h 降到 ~15min（仍需安全区）

  # ---- sizing / deadband ----
  "HEDGE_BINANCE_MIN_TRADE": 0.001,
  "DEADBAND_ABS_BTC":        0.006,
  "DEADBAND_FRAC":           0.25,
  "OVERHEDGE_TOL_FRAC":      1.5,  # HARD/CRASH 允许 min_trade 凑整的上限＝1.5×满额
  "HEDGE_BUDGET_BTC":        None, # [CAL] 小额 live-test 最大对冲预算；None=不额外限制（仍受满额夹紧）

  # ---- maker-first reduce ----
  "MAKER_REDUCE_TIMEOUT_LOOPS": 1, # [CAL] 1–2；超时未成交转 marketable reduce

  # ---- final 3h ----
  "FINAL3H_DTE_H": 3.0,

  "MIN_PER_YEAR": 525600.0,
}
```

---

## 6. 状态对象 Schema（跨 loop 持久化）

```python
ush_state = {
  # 时序缓存
  "ring": [],                 # §4.1 样本 ring buffer（保留 >= max(window)+裕量）
  # 层级 / 持续 / 冷却（全部存 wall-clock 时间戳，单位分钟或可比的 epoch）
  "level_prev": "NONE",
  "soft_candidate_since_ts": None,  # 进入 SOFT-candidate 的起始时刻；清零条件见 §7.2
  "safe_since_ts": None,            # 进入「安全区」的起始时刻（reduce persistence 用）
  "last_add_ts": None,
  "last_reduce_ts": None,
  "crash_entered_ts": None,         # 最近一次 CRASH 起始；crash_hold 用
  # 对冲执行
  "current_hedge_btc": 0.0,         # 由交易所真相回填；缺失时为 None（未知）
  "pending_reduce": None,           # {order_id, placed_loop, style, remaining_btc} 或 None
  "hedge_intent_btc": 0.0,          # 低于 min-trade 时记录的「应对冲但未下单」意图
  # 计数（仅日志/诊断）
  "loop_idx": 0,
}
```

「安全区」判据（供 `safe_since_ts` 维护）：
```
in_safe_zone = (p_BE < REDUCE_PBE) and (D_BE > REDUCE_DBE) and (speed_z < REDUCE_SPEEDZ)
# 进入安全区且 safe_since_ts is None → 置为当前 ts；一旦任一条件破坏 → safe_since_ts = None
```

---

## 7. 四级分类 `classify_level()`（纯函数）

输入：上面计算好的特征 + state + CONFIG。输出 level。**确认项一律 OR（任一即可），不用 AND**。

```python
def classify_level(f, st, C):
    # f: 已算好的特征命名空间; price_crossed_BE 为纯价格判据(无需 Greek)
    # --- CRASH（最高优先；可在 Greek 缺失下仅凭价格触发）---
    if C["USH_CRASH_OVERRIDE_ENABLED"] and (
        (avail(f.speed_z) and f.speed_z > C["CRASH_SPEEDZ"])
        or (avail(f.adverse_move_5m) and f.adverse_move_5m >= C["CRASH_MOVE_5M"])
        or f.depth_discontinuity            # 盘口/价格跳空
        or f.jump_crossed_strike            # 跳穿 short strike / BE 区
    ):
        return "CRASH"

    # --- HARD ---
    hard = (
        (avail(f.p_BE) and f.p_BE >= C["HARD_PBE"])
        or f.price_crossed_BE
        or (avail(f.D_BE) and f.D_BE < C["HARD_DBE"])
        or (avail(f.p_BE_drift) and avail(f.speed_z)
            and f.p_BE_drift >= C["HARD_DRIFT"] and f.speed_z > C["HARD_DRIFT_SPEEDZ"])
        or f.near_risk_exit                 # option MTM 逼近风险退出预算阈值
    )
    if hard:
        return "HARD"

    # --- SOFT（候选 + 至少一个确认；缺 Greek 时不能进 SOFT）---
    if greek_ok(f):
        soft_candidate = (
            f.p_BE >= C["SOFT_PBE"]
            or (avail(f.p_BE_drift) and f.p_BE_drift >= C["SOFT_DRIFT"])
            or f.D_BE < C["SOFT_DBE_CAND"]
            or f.touch_prob_elevated
        )
        soft_confirmed = (
            f.D_BE < C["SOFT_DBE_CAND"]
            or (avail(f.speed_z) and f.speed_z > C["SOFT_CONFIRM_SPEEDZ"])
            or f.rv_confirm
            or (C["USH_GAMMA_CONFIRM_ENABLED"] and f.gamma_high)
            or (f.dte_hours <= C["SOFT_UP75_DTE_H"] and f.D_BE < 0.5)
        )
        if soft_candidate and soft_confirmed:
            return "SOFT"

    # --- WATCH（只记录，不下单）---
    if (avail(f.p_BE) and f.p_BE_rising) or (avail(f.D_BE) and f.D_BE < C["WATCH_DBE_MAX"]):
        return "WATCH"

    return "NONE"
```

辅助：`avail(x)` = x 非 unavailable；`greek_ok(f)` = option Greek 未缺失；`p_BE_rising` = `p_BE_drift > 0`。

---

## 8. 目标比例 `hedge_target_ratio()`（纯函数）

```python
def hedge_target_ratio(level, f, C):
    if level == "CRASH":
        return 1.00

    if level == "HARD":
        probability_only = (
            avail(f.p_BE) and f.p_BE >= C["HARD_PBE"]
            and avail(f.D_BE) and f.D_BE > C["HARD_PROBONLY_DBE"]
            and avail(f.RV_30m) and f.RV_30m < C["HARD_PROBONLY_RVFRAC"] * f.IV
            and avail(f.speed_z) and f.speed_z < C["HARD_DRIFT_SPEEDZ"]
            and not f.gamma_high
            and not f.price_crossed_BE
        )
        return C["HARD_PROB_ONLY_RATIO"] if probability_only else 1.00   # 75% 否则 100%

    if level == "SOFT":
        if not C["USH_DYNAMIC_SOFT_ENABLED"]:
            return C["SOFT_FALLBACK_RATIO"]                              # 关闭动态 → 固定 50%
        # 75%
        if (f.dte_hours <= C["SOFT_UP75_DTE_H"] and avail(f.D_BE) and f.D_BE < C["SOFT_UP75_DBE"]) \
           or (avail(f.RV_30m) and f.RV_30m > f.IV and avail(f.speed_z) and f.speed_z > C["SOFT_CONFIRM_SPEEDZ"]):
            return 0.75
        # 50%
        if (avail(f.D_BE) and f.D_BE < C["SOFT_UP50_DBE"]) \
           or (avail(f.speed_z) and f.speed_z > C["SOFT_UP50_SPEEDZ"]) \
           or f.rv_confirm:
            return 0.50
        # 25%
        return 0.25

    # NONE / WATCH
    return 0.00
```

> **成本未知时的保护**（§4.7）：当 `missing_depth` 时，SOFT 的 50%/75% 升级**不生效**（停在 25%）；HARD/CRASH 不受影响。实现时在返回前对 SOFT 结果做一次 `if missing_depth: ratio = min(ratio, 0.25)`。

---

## 9. 仓位换算与 min-trade / intent / overhedge

```python
def compute_targets(level, ratio, base_target, current, st, C):
    # base_target: 满额对冲(带符号, BTC); current: 交易所真相回填(可能为 None)
    raw_target = base_target * ratio                     # 含符号
    # 预算夹紧（可选）+ 单边/满额夹紧（invariant §1.5）
    if C["HEDGE_BUDGET_BTC"] is not None:
        raw_target = clamp_mag(raw_target, C["HEDGE_BUDGET_BTC"])
    raw_target = clamp_to_side(raw_target, base_target)  # 同号且 |raw|<=|base_target|

    min_tr   = C["HEDGE_BINANCE_MIN_TRADE"]
    full_mag = abs(base_target)

    # 目标过小（小于 min trade）时的 intent 机制
    if abs(raw_target) < min_tr:
        if level in ("WATCH", "SOFT") and C["USH_INTENT_BELOW_MINTRADE"]:
            st["hedge_intent_btc"] = raw_target          # 记录意图，不下单
            return ("intent", 0.0 if current in (None,0.0) else current)  # 不主动调仓
        if level in ("HARD", "CRASH"):
            # 仅当 min_trade 凑整不会显著 overhedge 时，允许下一手 min_trade
            if min_tr <= C["OVERHEDGE_TOL_FRAC"] * full_mag and full_mag > 0:
                eff = sign(base_target) * min_tr
                return ("order", clamp_to_side(eff, base_target))
            else:
                st["hedge_intent_btc"] = raw_target      # 连满额都 < min_trade：只记录
                return ("intent", current if current is not None else 0.0)

    st["hedge_intent_btc"] = 0.0
    return ("order", raw_target)
```

辅助：`clamp_mag(x, m)`＝把 |x| 限到 m 且保号；`clamp_to_side(x, base)`＝与 base 同号且 |x|≤|base|，异号则取 0；`sign()` 标准符号。

> **current 为 None（missing position）时**：直接返回 `("hold", None)`，本轮不调仓（§4.7）。

---

## 10. Rehedge Deadband

```python
def passes_deadband(eff_target, current, C):
    if not C["USH_DEADBAND_ENABLED"]:
        return True
    if current is None:                      # 未知不动
        return False
    thr = max(C["HEDGE_BINANCE_MIN_TRADE"],
              min(C["DEADBAND_ABS_BTC"], C["DEADBAND_FRAC"] * abs(eff_target)))
    return abs(eff_target - current) >= thr
```

目的：阻止把 24h theta spread 磨成高频 taker。**例外**：CRASH 触发的「从 0/部分 → 满额」必须穿透 deadband（因为这是阶跃式补到 100%，差额通常已大于 thr；若恰好不大于，仍放行），实现上对 `level=="CRASH"` 跳过 deadband 检查。

---

## 11. Reduce Policy（安全区确认 + maker-first，绝不快速止损）

### 11.1 是否允许 reduce —— `can_reduce()`

```python
def can_reduce(f, st, C, ts, is_final3h):
    # crash 持有期内禁止 reduce（除非 option 已风险退出 / 方向错误 / orphan）
    if st["crash_entered_ts"] is not None and (ts - st["crash_entered_ts"]) < C["CRASH_HOLD_MIN"]:
        if not (f.option_risk_exited or f.hedge_wrong_direction or f.orphan_detected):
            return False
    # reduce 冷却
    rcool = C["REDUCE_COOLDOWN_F3H_MIN"] if is_final3h else C["REDUCE_COOLDOWN_MIN"]
    if st["last_reduce_ts"] is not None and (ts - st["last_reduce_ts"]) < rcool:
        return False
    # 安全区 + persistence（核心）
    need = C["REDUCE_PERSIST_F3H_MIN"] if is_final3h else C["REDUCE_PERSIST_MIN"]
    if st["safe_since_ts"] is None:
        return False
    persisted = (ts - st["safe_since_ts"]) >= need
    safe_now = (avail(f.p_BE) and f.p_BE < C["REDUCE_PBE"]
                and avail(f.D_BE) and f.D_BE > C["REDUCE_DBE"]
                and avail(f.speed_z) and f.speed_z < C["REDUCE_SPEEDZ"])
    return safe_now and persisted
```

> **禁止**：仅凭 `p_BE 回落` 或 `价格反弹` 或 `hedge PnL 亏损` 触发 reduce。必须价格**确实回到安全区**并**持续**足够时间。

### 11.2 reduce 目标

reduce 把对冲朝 0 收：当 `level` 降级（如回到 WATCH/NONE）且 `can_reduce` 为真，`eff_target` 取「当前层级 ratio 对应目标」或直接归零（保守：一次最多减到当前合法 ratio；若已 NONE → 目标 0）。reduce 永远朝 0，不反向（§1.5）。

### 11.3 maker-first reduce + timeout 状态机

```python
# 决定要 reduce 且通过 deadband 后：
if action == "reduce" and C["USH_MAKER_FIRST_REDUCE"]:
    if st["pending_reduce"] is None:
        place_passive_maker_reduce(eff_target)        # 挂被动/maker 单（既有执行器）
        st["pending_reduce"] = {order_id, placed_loop=st["loop_idx"], style="maker", remaining}
        return   # pending-first：本轮结束
    else:
        # 已有挂单：read-as-truth 检查成交
        refresh_fill(st["pending_reduce"])
        if filled(st["pending_reduce"]):
            st["pending_reduce"] = None; st["last_reduce_ts"] = ts
        elif (st["loop_idx"] - st["pending_reduce"]["placed_loop"]) >= C["MAKER_REDUCE_TIMEOUT_LOOPS"]:
            cancel(st["pending_reduce"]); 
            place_marketable_reduce(remaining)         # 超时转 marketable（reduce-only）
            st["pending_reduce"] = None; st["last_reduce_ts"] = ts
        # 否则继续等下一轮
        return
```

`add` **绝不**走 maker-first（§1.9）。

---

## 12. Add 行为（HARD/CRASH marketable；cooldown；crash bypass/hold）

```python
if action == "add":
    # add 冷却；CRASH 跳过
    if level != "CRASH":
        if st["last_add_ts"] is not None and (ts - st["last_add_ts"]) < C["ADD_COOLDOWN_MIN"]:
            return   # 冷却中，记录不下单
    # HARD/CRASH add 用 marketable prompt-limit（既有 tick-round 限价执行器）
    place_marketable_add(eff_target)
    st["last_add_ts"] = ts
    if level == "CRASH" and st["crash_entered_ts"] is None:
        st["crash_entered_ts"] = ts
```

CRASH 期间成本/滑点告警 **log-only**，不阻断 add。

---

## 13. 最后 3 小时调整（confirmed 更果断、未确认更克制）

`is_final3h = dte_hours <= FINAL3H_DTE_H`。最后 3h **不主动普通止盈**（既有规则），但允许风险退出/对冲/孤儿清理。覆盖如下（在 §7/§8 结果之上做最小修正）：

| 情况 | 最后 3h 行为 |
|---|---|
| WATCH | 只记录 |
| SOFT 仅由 p_BE/drift（无 distance/speed/gamma 确认） | 保持 0% 或 25%，**不自动 50%** |
| SOFT + `D_BE < 0.5` | 50% |
| SOFT + `dte<=3h` + `gamma_high` | 75% |
| HARD | 100%（除非纯概率低速远距离 → 75%，同 §8） |
| CRASH | 100%，bypass add cooldown |
| Reduce | 冷却/persistence 用 F3H 较短值（`REDUCE_*_F3H_MIN`），但**仍必须**价格回安全区；**不**因 hedge PnL 亏损而减 |

实现：`USH_FINAL3H_BRANCH_ENABLED=False` 时本节不生效（用通用阈值）。

---

## 14. 单 loop 总控制流（把上面串起来，按此顺序实现）

```python
def position_manage_hedge_step(market, st, C):
    st["loop_idx"] += 1
    # 1) 交易所真相（缺失显式标记，绝不当 0）
    truth = read_exchange_truth(market)   # option greek, binance position/depth/pnl + missing flags
    st["current_hedge_btc"] = truth.binance_position  # 可能为 None

    # 2) pending-first：有未结 reduce 挂单 → 先处理 §11.3，结束本轮
    if st["pending_reduce"] is not None:
        handle_pending_reduce(st, truth, C); log_decision(...); return

    # 3) 特征计算（§4）→ 更新 ring / safe_since_ts / drift 等
    f = compute_features(market, truth, st, C)
    update_safe_zone(st, f, C, now_ts())

    if not C["HEDGE_USH_V1_ENABLED"]:
        return legacy_v314_hedge_step(market, st)   # 主开关关闭 → 旧路径

    # 4) 分级 + 比例（§7,§8）+ 最后3h修正（§13）
    is_f3h = f.dte_hours <= C["FINAL3H_DTE_H"]
    level  = classify_level(f, st, C)
    ratio  = hedge_target_ratio(level, f, C)
    if C["USH_FINAL3H_BRANCH_ENABLED"] and is_f3h:
        level, ratio = apply_final3h(level, ratio, f, C)
    if truth.missing_depth and level == "SOFT":
        ratio = min(ratio, 0.25)

    # 5) sizing（§9）
    base_target = -f.pos_delta * f.option_size_btc
    kind, eff_target = compute_targets(level, ratio, base_target, st["current_hedge_btc"], st, C)
    if kind in ("intent", "hold"):
        log_decision(level, ratio, base_target, eff_target, reason=kind, st=st, f=f); return

    # 6) 决定 add / reduce / hold
    cur = st["current_hedge_btc"]
    action = decide_action(cur, eff_target)   # toward-0 => reduce; away-from-0 => add; equal => hold
    if action == "reduce" and not can_reduce(f, st, C, now_ts(), is_f3h):
        log_decision(..., reason="reduce_blocked"); return

    # 7) deadband（§10；CRASH 穿透）
    if level != "CRASH" and not passes_deadband(eff_target, cur, C):
        log_decision(..., reason="deadband"); return

    # 8) 执行（复用既有单动作 reconcile-to-eff_target；reduce→maker-first，add→marketable）
    if action == "reduce":
        execute_reduce_maker_first(eff_target, st, C)        # §11.3
    elif action == "add":
        execute_add_marketable(level, eff_target, st, C)     # §12
    update_crash_state(level, st, now_ts())

    # 9) 日志（无论是否下单都已在各分支写）
    log_decision(level, ratio, base_target, eff_target, action=action, st=st, f=f)
```

---

## 15. 交易所真相与缺失（再次强调，独立成节防遗漏）

- **pending-first**：任一未结对冲单存在 → 不发新单，先按 §11.3 处理（适用于 maker reduce 超时；marketable add 一般同 loop 完成，若未完成同样 pending-first 等待 read-as-truth 吸收）。
- **read-as-truth**：每轮以交易所回报为准回填 `current_hedge_btc`；迟到/部分成交在下一轮被吸收，不重复补单。
- **reduce-only 优先归零**：检测到 orphan / short-flat / reverse（方向错误）持仓 → 用 reduce-only 先归零，再谈新对冲。
- **缺失**：见 §4.7 表，三类缺失各有硬规则，**绝不当 0**。

---

## 16. 日志 Schema（每 loop 一行，不下单也写）

```
ush_decision = {
  ts, loop_idx, dte_hours, is_final3h,
  S, IV, RV_30m, p_BE, p_BE_drift, D_BE, speed_z, adverse_move_5m, gamma_score, gamma_high,
  level, target_ratio, base_target, raw_target, eff_target,
  current_hedge_btc, hedge_intent_btc, delta_to_trade,
  action, exec_style, reason,                 # reason: order/intent/hold/deadband/reduce_blocked/cooldown/crash_hold/missing_*
  add_cooldown_left, reduce_cooldown_left, safe_persist_min, soft_cand_persist_min, crash_hold_left,
  cost_bp_add, cost_bp_reduce,
  missing_binance_position, missing_depth, missing_hedge_pnl, missing_option_greek
}
```

该 schema 是后续用 FMZ live log 校准 `[CAL]` 阈值的数据基础（§21）。

---

## 17. 开关、回滚与消融

- **回滚**：`HEDGE_USH_V1_ENABLED=False` → 立即回到现行 v3.1.4，零行为差异、零额外 I/O（实现必须保证 disabled 时不进入任何 USH 计算路径）。
- **逐特性消融**（用于 A/B 与定位）：
  - `USH_DYNAMIC_SOFT_ENABLED=False` → SOFT 恒 50%（验证动态比例增益）。
  - `USH_GAMMA_CONFIRM_ENABLED=False` → 去掉 gamma 确认/升级（验证 gamma-aware 贡献）。
  - `USH_CRASH_OVERRIDE_ENABLED=False` → 无 CRASH 旁路（验证 jump 保护）。
  - `USH_MAKER_FIRST_REDUCE=False` → reduce 也走 marketable（验证成本结构收益）。
  - `USH_DEADBAND_ENABLED=False` → 关 deadband（验证 churn 抑制）。
  - `USH_INTENT_BELOW_MINTRADE=False` → 小目标强制 min_trade（验证小额 live-test overhedge）。
  - `USH_FINAL3H_BRANCH_ENABLED=False` → 最后 3h 用通用阈值。
- 建议上线顺序：先 `ENABLED=True` 但**所有子特性退化**（≈ v3.1.4 + 日志），先校准特征/阈值；再逐个打开子特性观察日志指标。

---

## 18. 测试矩阵

### 18.1 Deterministic（本地可判定，必须先全绿）

| 测试 | 期望 |
|---|---|
| BS strike/delta | 0.15/0.25/0.35/0.45 delta 反推 strike 正确 |
| put/call 镜像 | short put adverse=down、short call adverse=up，`dir_sign`/`base_target` 方向正确 |
| D_BE 符号 | 价格越过 BE → `dist_be_usd<=0` → D_BE=0；安全侧为正 |
| speed_z | 给定 15m adverse move，标准化值正确；样本不足→unavailable |
| RV_30m | rolling RV 正确；样本不足不返回 0 而是 unavailable |
| p_BE / drift | N(±d2) 方向正确；缺历史→drift unavailable |
| classify：WATCH 不下单 | 仅概率漂移 → 不产生 order |
| classify：SOFT 确认 | 无确认项→不进 SOFT；有确认→进 SOFT |
| classify：HARD full | `price_crossed_BE` → HARD，ratio=1.0 |
| classify：HARD 纯概率例外 | 远距离/低速/低RV/无gamma/未穿BE → 0.75 |
| classify：CRASH 旁路 | speed_z>2.4 → CRASH，bypass add cooldown |
| ratio：SOFT 25/50/75 | 升级条件命中对应比例；动态关→0.5 |
| reduce gate | p_BE 回落但 D_BE 未回安全区 → 不减 |
| reduce persistence | 安全区未持续够 → 不减；够 → 允许 |
| crash_hold | crash 后 < CRASH_HOLD_MIN 不减（除非风险退出/方向错/orphan） |
| maker-first reduce | reduce 先挂 maker；超时转 marketable；add 不走 maker |
| deadband | `|target-current|` < thr 不调仓；CRASH 穿透 |
| min-trade intent | WATCH/SOFT 小目标记录 intent 不下单；HARD/CRASH 仅在 overhedge 容忍内下 min_trade |
| missing position | 不加仓、不假设 current=0、本轮不调仓 |
| missing depth/PnL | 不当 0 成本/0 PnL；SOFT 在 depth 缺失下不升级 |
| pending-first | 有挂单不重复下单 |
| 迟到/部分成交 | 下一轮 read-as-truth 吸收，不重复补 |
| orphan/reverse | reduce-only 归零优先 |
| disabled no-op | `HEDGE_USH_V1_ENABLED=False` 不进入任何 USH 路径、无额外 I/O |

### 18.2 必须等 FMZ live log 校准（本地不可判定）

| 项目 | 原因 |
|---|---|
| Binance BTCUSDC 实际 spread / prompt-limit 成交质量 | 本地无法准确模拟 |
| maker-first reduce 实际成交率与所需 timeout（1 vs 2 loop） | 取决于盘口与下单行为 |
| `POSITION_MANAGE` loop cadence | persistence/cooldown 的真实时间粒度 |
| Deribit 近到期 IV/delta/gamma 抖动 | 影响 SOFT/HARD 边界与 gamma_high |
| depth 缺失频率 | 影响成本门控与 fallback 频率 |
| hedge PnL 字段可靠性 | 决定能否将其作为**辅助**诊断（仍不作触发） |
| final 3h pinning / snapback | 需真实短周期样本 |
| false/missed hedge 标注 | 需实盘路径回放 |
| risk-exit 与 hedge 交互（预算是否纳入 hedge PnL） | 需日志验证 |

---

## 19. 已知案例在 USH-v1 下的判定（2026-06-28 06:04:47）

事件：Binance BTCUSDC 限价卖出 ≈1380 USDC、均价≈60000、fee≈0.552（≈4bp）；BTC 跌至≈59855 后反弹。

USH-v1 不做事后「这单好/坏」判断，而看触发当时的特征：

```
是否仅 p_BE drift？           → 仅漂移：保持 WATCH 或 25% SOFT
D_BE < 1.0？                   → 是则可作 SOFT 确认
speed_z > 0.65？               → 是则 SOFT 升 50%
RV_30m > 0.85*IV？             → 是则确认/升级
gamma_high？                   → 是则确认/升级
speed_z > 2.4 或 5m move>=0.9% → CRASH，full
已 HARD（穿 BE / D_BE<0.25）？  → full
```

- 若当时只是概率漂移、价格离 BE 仍远、速度不高 → 应只 WATCH 或 25%，**不应**直接半仓 taker 卖出 → 这正是当前固定 50% 在 whipsaw 中被磨损的根因。
- 反弹后的 reduce **不应**由价格反弹或 hedge PnL 触发，而应等价格回安全区 + persistence，并用 maker-first reduce。

---

## 20. 待实盘校准清单（交付后第一阶段任务）

按优先级（全部用 §16 日志回放校准）：
1. SOFT `p_BE`（0.24 vs 0.27 vs 0.30）、HARD `p_BE`（0.42 vs 0.43 vs 0.45）。
2. `speed_z` 的 0.65 / 2.4 是否匹配 Binance BTCUSDC 当前盘口波动尺度。
3. maker-first reduce timeout（1 vs 2 loop）与实际成交率。
4. final-3h reduce cooldown（15 vs 20min）与 persistence（15min）。
5. min-trade 量化误差下，25% target 是否需要 intent 累计后择机一次性下单。
6. 小额 live-test 的 `HEDGE_BUDGET_BTC` 上限。
7. `sig_ref` 用 IV 还是 `max(IV, RV_30m)`；`RV_CONFIRM_FRAC` 0.85 是否偏松/偏紧。

---

## 21. 一页式落地清单（Definition of Done）

- [ ] CONFIG `USH` 全量接入，无函数体魔法数；`[CAL]` 项标注清楚。
- [ ] §4 特征（含 wall-clock 窗口映射、缺失→unavailable）实现并单测。
- [ ] §7 `classify_level` / §8 `hedge_target_ratio` / §9 sizing / §10 deadband / §11 reduce+maker-first / §12 add / §13 final-3h 按伪代码实现。
- [ ] §14 总控制流按序串接；§15 缺失/真相规则全覆盖。
- [ ] §1 九条 invariant 全部满足（尤其：不新增 command、不接确认码、单边不翻向、缺失不当 0、maker-first 不入 add）。
- [ ] §16 日志每 loop 一行落库。
- [ ] §18.1 deterministic 测试全绿；`HEDGE_USH_V1_ENABLED=False` 验证零行为变化、零额外 I/O。
- [ ] §17 逐特性开关可独立消融。
- [ ] 交付物附：本地测试结果 + §18.2/§20 待实盘校准清单（不得声称已实盘验证）。

---

### 一段话总纲（可直接贴给执行 agent）

> 保留「风险恶化后对冲」。把触发改成 **WATCH / SOFT / HARD / CRASH** 四级状态机：WATCH 只记录；SOFT 默认 25% 且必须有 distance/speed/RV/gamma 中**至少一个**确认，按确认强度升 50%/75%；HARD 多数 full，仅「纯概率+低速+远距离」先 75%；CRASH 无条件 full 并 bypass add cooldown、持有 ≥12min。**减仓只由安全区确认驱动**（p_BE 低 + D_BE 足够远 + speed_z 衰减 + persistence 足够），且用 **maker-first reduce**（超时转 marketable）；**add 在 HARD/CRASH 保持 marketable**。加 **rehedge deadband** 防微调churn；小额 live-test 下小于 min-trade 的目标**记录 intent 不强行下单**。最后 3h：未确认更克制、confirmed 更果断。**全部挂在 CONFIG 开关后、可逐项消融、disabled 时零行为变化**；不新增 FMZ command、不接确认码、缺失绝不当 0。先用日志校准 `[CAL]` 阈值，再逐特性打开。
