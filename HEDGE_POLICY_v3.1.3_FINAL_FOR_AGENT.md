# Hedge Policy v3.1.3 — Final Implementation Spec (for Codex / Work Agent)

> 本文档是交付给实现 agent 的**最终权威规范**,合并了两份独立外部审阅:
> `HEDGE_MODULE_REVIEW_v3.1.2.md`(Opus 4.8)与
> `HEDGE_POLICY_REVIEW_v3.1.2_TO_v3.1.3.md`(GPT-5.5 Pro)。
> 两份审阅在架构层面完全收敛,本规范在其共识之上做了收紧与隐患修复。
> 实现以本文档为准;凡与上述两份提案冲突处,以本文档为准。
>
> **边界(不变,继承自 inquiry):** 不增加运行时 hedge 指令;FMZ 运行时仍以确认码交互为主;
> `POSITION_MANAGE` 仍是非交互读屏;不改候选选择 / 确认码 / 人工放行门;
> 不把 Binance depth/position/PnL 缺失当 0;不明确仓位读取一律 fail-closed;
> 改动必须先被本地确定性测试覆盖,再进 FMZ 试运行;单文件、不强制新增 class、主链路不动、
> **每个新机制独立 CONFIG 可关**。

---

## 0. 置信度与改动定位

两份审阅独立得到**同一架构**:保留 `PROMPT_LIMIT`、HARD/SOFT 两级触发、SOFT 分段建仓、
persistence、加仓/减仓不对称、下单后按真实仓位对账、fail-closed、orphan 立即 reduce-only。
独立收敛 ⇒ 主架构高置信,**不再改动主架构**。

本规范只做两件事:

1. **把架构统一表述为一个 reconciliation 控制器**(外层对账,内层由 HARD/SOFT 分类器设定目标),
   使「重复下单 / late-fill overhedge」在结构上不可能,而不是靠事后补救。
2. **修复几处会在真实行情里咬人的隐患**(见 §2),其中 3 处为安全级。

---

## 1. 核心架构:Reconciliation 控制器

把模块从「事件驱动(触发→执行→事后校准)」改为「**对账驱动**」。每个 hedge cycle 执行一次下面的控制器。
真值永远来自实时仓位读取;`epoch / last_fill / pending` 都只是记账,**永不覆盖 read**。

```text
# ===== hedge_cycle(): 每轮对账,幂等,单动作 =====

if not HEDGE_POLICY_V313_ENABLED:
    return legacy_full_prompt_limit()          # 一键回滚到 v3.1.2 行为

# 0) 先清 pending,绝不在已有在途单时再下第二单(single-flight + 死锁恢复)
if state.pending_order_id is not None:
    resolve_pending(state, now)                # 查状态; 终态->清; 超时->撤单+清
    return                                     # 一轮一动作,下一轮重新读真值

# 1) 真值:实时仓位读取(signed),失败一律 fail-closed
current = bnc_get_position_btc()               # 带方向的 BTC 数量
if current is None:
    log("[hedge][fail_closed] POSITION_READ_FAILED")
    return                                     # 不假设 0,不下单

# 2) orphan / flat / 反向 -> 立即 reduce-only 解除(绕过一切 hysteresis/cooldown)
if option_leg_closed() or remaining_short_qty()==0 or sign_mismatch(current):
    if current != 0:
        if state.pending_order_id: cancel_and_clear(state)   # 紧急解除可先撤在途加仓单
        submit_reduce_only(target=0.0)         # 平到 0;反向时绝不单笔翻转(见 §8)
    return

# 3) 分类 regime -> 设定 FULL 目标(signed,风险隐含)
regime      = classify_trigger(p_now, drift, spot, loss_boundary)   # HARD / SOFT / NONE
full_target = risk_target_qty(regime)          # NONE 时为 0

# 4) staged 目标:SOFT 可能只授权一部分;HARD = full。对账驱动到这个目标,不是 full_target
eff_target  = staged_target(regime, full_target, state)             # <-- reconcile 到此

# 5) delta(始终对 eff_target 计算并 clamp;late/partial fill 下一轮自动被吸收)
delta = eff_target - current
if abs(delta) < HEDGE_BINANCE_MIN_TRADE:
    return
is_add = increases_exposure(delta, current)

# 6) 不对称门控
if is_add:
    if regime != "HARD":                       # SOFT 加仓:受门控
        if not persisted("SOFT", now):         return hold("SOFT_PERSIST_WAIT")
        if in_cooldown(state.add_cooldown_until, now): return hold("ADD_COOLDOWN_ACTIVE")
        if HEDGE_SLIPPAGE_GUARD_ENABLED and soft_would_exceed_cross():
                                               return hold("SOFT_SLIPPAGE_GUARD")
    band = hard_cross_band() if regime=="HARD" else soft_cross_band()
    reduce_only = False
else:                                          # 普通减仓(非 orphan 路径):比加仓更慢
    if not persisted("REDUCE", now):           return hold("REDUCE_HYSTERESIS_WAIT")
    if in_cooldown(state.reduce_cooldown_until, now): return hold("REDUCE_COOLDOWN_ACTIVE")
    band = reduce_cross_band()
    reduce_only = True

# 7) 下且仅下一单;pending 在提交前置位;cooldown 方向键控
px = tick_round(marketable_limit(side_of(delta), band))    # HEDGE_BINANCE_PRICE_TICK
state.pending_order_id      = submit(side_of(delta), clamp_lot(delta), px, reduce_only)
state.pending_order_created_ts = now
arm_direction_keyed_cooldown(is_add, now)      # add 成交后锁 reduce;reduce 成交后锁 add
log_order(side_of(delta), clamp_lot(delta), regime, band, reduce_only)
```

控制器自带的健壮性(无需额外补救):

- **先清 pending → 不会双发**;`resolve_pending` 含超时撤单,**不会 in-flight 卡死**。
- **read 为真值 + delta 对 eff_target clamp** → 撤单后晚成交只会进下一轮 `current`,delta 自动缩小,**结构上不可能 overhedge**。
- **reconcile 到 eff_target(staged)** → staging 不会被对账器静默打满。
- **HARD 不放弃**:残量逐轮重算,直到 `current=full_target`(见 §8),**不被 slippage 截断**。
- **HEDGE_POLICY_V313_ENABLED=False** 即整层关闭,退回 v3.1.2「永远全量 prompt-limit」。

---

## 2. 关键改进(相对 v3.1.2→v3.1.3 提案)

实现 agent 注意:以下是相对 GPT-5.5 Pro 提案的**刻意偏离**,务必按本文档执行。

**安全级(必须):**

1. **HARD 永不被 slippage cap 截断。** 提案给 HARD=5bps,但真实 gap-down 里 5bps 的 marketable
   limit 会挂不上——正是对冲唯一要保护的场景失效。HARD 用激进穿价带保证成交,残量逐轮对账直到打满;
   slippage 对 HARD **仅作观测/告警,不作成交约束**。
2. **episode cost cap 纯观测,永不 gate。** 成本帽绝不能挡住 HARD 加仓。只显示/告警;
   SOFT 至多用更强 persistence,**绝不因成本硬阻**。永远 fail toward hedging。
3. **reconcile 目标 = `eff_target`(staged),不是 `full_target`。** 否则对账器会把 SOFT 的 50%
   静默打满,staging 失效。staging 逻辑全部放进 `staged_target()`,对账器保持「目标−当前」的傻瓜逻辑。

**健壮性/正确性:**

4. **cooldown 方向键控(direction-keyed)。** add 成交后锁 `reduce_cooldown`;reduce 成交后锁
   `add_cooldown`。同向 staged build(add→add)只由 persistence 管,**不被 cooldown 阻塞**。
   这修掉提案里 `add_cooldown` 与「50%→100% 升级」互相打架的问题,且方向键控本身就是最干净的抗 whipsaw 语义
   (加仓后一段时间内不许减,减仓后一段时间内不许加)。
5. **persistence 基于时间,不数 cycle。** 用 `*_since_ts`(条件首次为真的时间戳)做 debounce,
   对 loop 抖动鲁棒、状态更少。可选:加 2-sample 最小计数,避免单次长 cycle 凭时间误判持续。
6. **pending 死锁恢复。** pending 超过 `HEDGE_PENDING_STALE_SECONDS` 且交易所查不到 → cancel+clear,
   避免在途标志卡死导致**永久不再对冲**(错误方向的 fail-closed)。
7. **价格空间 buffer 才按波动率缩放。** 概率空间阈值(`p_now`/`drift`)可固定(概率已吸收波动率);
   但贴近 `loss_boundary` 的**价格带**建议用既有 detrended-σ 缩放,固定点偏移高波动时太窄、低波动时太宽。
8. **反向 hedge 两步解除。** 永远 `reduce_only` 平到 0,再开反向,**绝不单笔翻转**,防 overshoot。
9. **read 是唯一真值。** `epoch` 仅用于日志归因(某笔成交属于哪个 campaign),**不参与控制**;
   控制正确性来自 read-as-truth + single-flight + reconcile-to-eff_target 三者。

---

## 3. CONFIG(均可独立关闭;标注的需用实盘数据校准)

```python
# ---- 主开关 / 回滚 ----
HEDGE_POLICY_V313_ENABLED      = True     # False => 退回 v3.1.2 全量 prompt-limit
HEDGE_STAGING_ENABLED          = True     # 关 => SOFT 也直接打满
HEDGE_HYSTERESIS_ENABLED       = True     # 关 => 不做 persistence 去抖
HEDGE_COOLDOWN_ENABLED         = True     # 关 => 不做方向键控冷却
HEDGE_SLIPPAGE_GUARD_ENABLED   = True     # 关 => SOFT 不做滑点价格约束(仍记录)

# ---- 继承自 v3.1.2(不动)----
HEDGE_BINANCE_PRICE_TICK       = 0.1      # buy up / sell down,下单前 tick round
HEDGE_BINANCE_MIN_TRADE        = 0.001    # BTC;dead-band,吸收 lot 余量

# ---- staging ----
HEDGE_SOFT_INITIAL_RATIO       = 0.50     # SOFT 首次只到 full_target 的 50%
HEDGE_SOFT_ADD_DRIFT_STEP      = 0.05     # p_now 再恶化≥此值可提前升级(免等满 persist)

# ---- 触发阈值(概率空间,可固定;★需校准)----
HEDGE_HARD_DRIFT               = 0.35     # ★
# open_probability / emergency_probability / watch_probability 沿用策略既有定义

# ---- 价格带(★需校准;建议用 detrended-σ 缩放而非纯固定)----
HEDGE_HARD_CROSS_BPS           = 30       # ★ HARD 穿价带:够激进、保证成交;不足量下一轮续打
HEDGE_SOFT_CROSS_BPS           = 3        # ★ SOFT marketable-limit 价格约束;不足量保留余额
HEDGE_LOSS_BOUNDARY_BUFFER_SIGMA = 1.0    # ★ loss_boundary 邻近带按 σ_slow 缩放的系数

# ---- persistence(时间制)----
HEDGE_SOFT_PERSIST_SECONDS     = 20       # ★ SOFT 升级到 full 需持续秒数
HEDGE_REDUCE_PERSIST_SECONDS   = 20       # ★ 普通减仓需持续秒数
HEDGE_REDUCE_PROB_BUFFER       = 0.05     # 减仓门槛:p_now <= watch_probability - 此值

# ---- 方向键控冷却 ----
HEDGE_ADD_COOLDOWN_SECONDS     = 30       # reduce 成交后,此秒内不许新 add(HARD 例外)
HEDGE_REDUCE_COOLDOWN_SECONDS  = 60       # add 成交后,此秒内不许 reduce(orphan 例外)

# ---- 观测(不 gate,仅显示/告警)----
HEDGE_SLIP_ALERT_BPS           = 8        # 实际滑点超此值仅记 warn
HEDGE_EPISODE_COST_ALERT_BPS   = 20       # episode 累计成本超此值仅记 warn,不阻任何下单

# ---- 死锁恢复 ----
HEDGE_PENDING_STALE_SECONDS    = 10       # pending 超此且交易所查不到 -> cancel+clear
```

---

## 4. 状态结构(signed;时间制;比提案更少状态)

```python
hedge_state = {
    # 归因(仅日志,不参与控制)
    "position_id": None,
    "hedge_epoch": 1,

    # 目标 / 真值(均 signed)
    "full_target_qty": 0.0,        # 风险隐含全量目标
    "eff_target_qty":  0.0,        # 当前授权目标(staged);对账驱动到此
    "current_hedge_qty": 0.0,      # 仅来自仓位快照,绝不由订单历史推断

    # 最近成交(记账)
    "last_fill_ts": 0,
    "last_fill_qty": 0.0,
    "last_fill_price": 0.0,
    "last_action": None,           # ADD / REDUCE / UNWIND

    # 触发上下文
    "last_trigger_state": "NONE",  # HARD / SOFT / NONE
    "last_p_now": 0.0,
    "last_drift": 0.0,

    # 时间制 debounce(取代 cycle 计数)
    "soft_since_ts":   0,          # SOFT 条件首次为真;0=当前不满足
    "reduce_since_ts": 0,
    # (可选)各加 1 个 sample 计数防单次长 cycle 误判,见 §2.5

    # 方向键控冷却
    "add_cooldown_until":    0,    # reduce 后置位
    "reduce_cooldown_until": 0,    # add 后置位

    # single-flight + 死锁恢复
    "pending_order_id": None,
    "pending_order_side": None,
    "pending_order_qty": 0.0,
    "pending_order_created_ts": 0,

    # 观测成本(不 gate)
    "episode_cost_usdc": 0.0,
    "episode_cost_bps":  0.0,
}
```

最低必需:`full/eff/current`、`pending_*`、`last_fill_*`、`last_trigger_state`、
`*_since_ts`、两个 `*_cooldown_until`、`episode_cost_*`。

---

## 5. 触发分类与 staged target

```python
def classify_trigger(p_now, drift, spot, loss_boundary):
    # HARD:任一硬风险边界
    if (spot_breached(spot, loss_boundary)                      # 价格触/穿 loss_boundary(带按σ缩放)
        or p_now >= emergency_probability
        or drift >= HEDGE_HARD_DRIFT):
        return "HARD"
    # SOFT:进入开仓概率但无硬边界
    if p_now >= open_probability and drift >= min_probability_drift_to_open:
        return "SOFT"
    return "NONE"

def staged_target(regime, full_target, st):
    if regime == "HARD":
        return full_target                                     # 全量
    if regime == "SOFT":
        if not HEDGE_STAGING_ENABLED:
            return full_target
        # 已满足升级条件 => full;否则 => 50% 档
        if soft_escalated(st):                                 # persist 达标 / p_now 再恶化≥step / 升级为HARD
            return full_target
        return full_target * HEDGE_SOFT_INITIAL_RATIO          # 首段 50%
    return 0.0                                                  # NONE:不主动加;减仓由对账+hysteresis处理
```

要点:**staging 全部体现在 `eff_target` 上**,对账器只做 `eff_target - current`。
因此「SOFT 第一次只打 50%、持续后补到 100%」是 `staged_target` 返回值变化的自然结果,
对账器不会绕过它,也不会重复打满(`current≈eff_target` 时 delta≈0)。

---

## 6. 不对称门控

- **加仓 vs 减仓:** 加仓在风险真升级时偏快;减仓**永不紧急**——过度对冲多挂几秒几乎无成本
  (期权腿基本对冲),而急于解除正是 whipsaw 的来源。
- **方向键控冷却(§2.4):** add 成交 → 置 `reduce_cooldown`;reduce 成交 → 置 `add_cooldown`。
  同向 staged build 只受 persistence 管,不被冷却阻塞。
- **HARD 绕过 SOFT 的全部门控**(persistence / add cooldown / soft slippage guard)。
- **减仓双门(更慢):** `p_now <= watch_probability - HEDGE_REDUCE_PROB_BUFFER` **且**
  持续 `HEDGE_REDUCE_PERSIST_SECONDS` **且**不在 `reduce_cooldown`。
- **立即 reduce-only 解除(绕过一切 hysteresis/cooldown):** `remaining_short_qty==0` /
  orphan hedge / 方向相反 / `emergency_reduce_only` / 期权腿已关闭。所有 reduce/unwind 必须
  `reduce_only=True`。

---

## 7. persistence(时间制 debounce)

```python
def mark_condition(st_key, cond_now, now):
    # 维护 *_since_ts:条件首次为真记时间;转假清 0
    if cond_now and hedge_state[st_key] == 0:
        hedge_state[st_key] = now
    elif not cond_now:
        hedge_state[st_key] = 0

def persisted(kind, now):
    if not HEDGE_HYSTERESIS_ENABLED:
        return True
    since = hedge_state["soft_since_ts" if kind=="SOFT" else "reduce_since_ts"]
    need  = HEDGE_SOFT_PERSIST_SECONDS if kind=="SOFT" else HEDGE_REDUCE_PERSIST_SECONDS
    return since != 0 and (now - since) >= need
```

(可选硬化:再要求 `sample_count >= 2`,防单次长 cycle 凭时间误判。)

---

## 8. 执行与滑点(HARD 保命 / SOFT 温和)

- **HARD = 不放弃。** 用 `HEDGE_HARD_CROSS_BPS` 的激进穿价 marketable limit(tick round 后仍朝远离 mid
  方向,保证 crossing);若极端 gap 致部分成交,**残量下一轮继续对账,直到 `current=full_target`**。
  HARD 的正确性**不依赖**带宽数值正确——因为对账逐轮重试。slippage 对 HARD 只记录/告警。
- **SOFT = 温和分段。** 用 `HEDGE_SOFT_CROSS_BPS` 的较紧 marketable limit;不足量则保留余额,
  仅在门控仍满足的下一轮可能补足(SOFT 不追价)。
- **tick round(v3.1.2 修复保留):** buy up / sell down;round 后仍须满足 min-notional。
- **reduce_only:** 所有减仓/解除 `reduce_only=True`。
- **反向解除两步:** 先 `reduce_only` 平到 0,再下独立的反向开仓单,**绝不单笔翻转**。
- **下单后对账(继承主设计):** 下 prompt-limit → 短等待 → 查成交 → 撤残单 → 撤后再查一次 →
  下一轮读真实 Binance 仓位 → 按 `eff_target - current` 重算。**绝不连续复用上一次目标数量重复下单。**

---

## 9. 明确不做(v3.1.3)

- **不做 maker-first。** 挂在下跌市场之上的 maker sell 在真实 gap-down 里不成交——保护场景失效;
  且引入 maker id / 超时 / 撤后晚成交 / 补 taker / 防重复 / 重启残单 / 撤单失败 / stale 价 等订单生命周期复杂度。
  列为 **v3.2 / v4 研究项,且仅可能用于减仓侧**(减仓不赶时间)。
- **不做交易所 native conditional order。** 需要记录/撤销条件单 id、处理触发后机器人未感知、重启恢复、
  与 reduce_only/orphan 的关系,以及 Binance/Deribit/FMZ 行为差异。机器人侧 prompt-limit + 读真值对账更简单。
- **不加运行时 hedge 指令。** 确认码交互、候选选择、人工放行门一律不动。

---

## 10. 状态栏(`POSITION_MANAGE`)与日志

`POSITION_MANAGE` 增列(非交互):

```text
触发:  state=HARD/SOFT/HOLD/NONE  p_entry  p_now  drift  open_p  emergency_p  watch_p
目标:  full_target  eff_target(staged)  current_hedge  delta_to_trade
执行:  style=PROMPT_LIMIT  cross_bps  pending_order_id  last_fill_qty  last_fill_price
门控:  add_cooldown_until  reduce_cooldown_until  soft_since_ts  reduce_since_ts
成本:  episode_cost_usdc  episode_cost_bps   (仅观测)
原因:  SOFT_TRIGGER_INITIAL / SOFT_TRIGGER_CONFIRMED / HARD_TRIGGER_BOUNDARY /
       HARD_TRIGGER_EMERGENCY / ADD_COOLDOWN_ACTIVE / REDUCE_HYSTERESIS_WAIT /
       REDUCE_COOLDOWN_ACTIVE / SOFT_SLIPPAGE_GUARD / ORPHAN_HEDGE_UNWIND /
       POSITION_READ_FAILED / PENDING_STALE_RECOVERED
```

日志样例:

```text
[hedge][soft]        p_now=0.52 drift=0.23 full=0.020 eff=0.010 reason=SOFT_TRIGGER_INITIAL
[hedge][soft_add]    since=20s p_now=0.57 drift=0.28 eff=0.020 reason=SOFT_TRIGGER_CONFIRMED
[hedge][hard]        p_now=0.74 drift=0.39 eff=0.020 band_bps=30 reason=HARD_TRIGGER_EMERGENCY
[hedge][hold]        reason=ADD_COOLDOWN_ACTIVE until=...
[hedge][reduce_wait] p_now=0.41 watch=0.45 since=8s/20s reason=REDUCE_HYSTERESIS_WAIT
[hedge][order]       side=sell qty=0.010 style=PROMPT_LIMIT cross_bps=3 reduce_only=False pending=...
[hedge][fail_closed] POSITION_READ_FAILED
[hedge][pending]     PENDING_STALE_RECOVERED id=... age=12s
[hedge][unwind]      reason=ORPHAN_HEDGE_UNWIND reduce_only=True target=0.0
```

(沿用既有 `DebugRecorder` JSONL 分流与 `REASON_CODE` 风格;`run_id/epoch` 仅用于归因。)

---

## 11. 必测用例(本地确定性,进 FMZ 前必须全绿)

继承提案 11 项,并补齐每方各自缺的项。**加粗为本规范新增/强化、必须覆盖的项。**

1. SOFT 首次只开 50%:`current=0, full=0.02, SOFT` ⇒ `eff=0.01`,下单 0.01,`state=SOFT`。
2. SOFT 未持续不追加:上轮 SOFT,本轮 `p_now` 回落 ⇒ `soft_since_ts` 清 0,不追加。
3. SOFT 持续达标补满:`soft_since>=PERSIST` ⇒ `eff=0.02, delta=0.01, reason=SOFT_TRIGGER_CONFIRMED`。
4. HARD 直接 100% 并绕过 cooldown:`p_now>=emergency 或 boundary breach` ⇒ `eff=full`,无视 add cooldown。
5. cooldown 阻止**方向反转的** add:刚 reduce 过、`now<add_cooldown_until`、SOFT 仍真 ⇒ 不加,`ADD_COOLDOWN_ACTIVE`。
6. pending 防重复:`pending_order_id` 存在 ⇒ 不新发,先查/撤/更新 pending。
7. late fill 不 overhedge:撤单后晚成交、下一轮 `current` 已更新 ⇒ 按 `eff-current` 重算,不重复打满。
8. `p_now` 回落但未过 hysteresis 不减:`watch-buffer < p_now < open` ⇒ HOLD,不减。
9. 连续低于 `watch-buffer` 达标才减:持续 `REDUCE_PERSIST` ⇒ `HEDGE_REDUCE, reduce_only=True`。
10. short flat 立即 unwind:`remaining_short_qty=0, current!=0` ⇒ `HEDGE_UNWIND, reduce_only=True`,不等 cooldown。
11. 仓位读取失败 fail-closed:`bnc_get_position_btc()=None` ⇒ 不假设 0、不下单、不解除。
12. **reconcile 不绕过 staging:** SOFT 已在 50%、未持续 ⇒ `eff=0.01`,`delta≈0`,**不自动补到 full**。
13. **pending 死锁恢复:** pending 超 `STALE` 且交易所查无此单 ⇒ cancel+clear,`PENDING_STALE_RECOVERED`,
    恢复后可正常对账。
14. **HARD 在 gap 中不放弃:** 单轮部分成交、`current<full` ⇒ 下一轮仍按 `delta=full-current` 续打,
    **不被 slippage 截断**直到 `current=full`。
15. **episode cost 高仍不阻 HARD:** `episode_cost_bps>ALERT` 且 HARD 触发 ⇒ 仍全量下单,仅记 warn。
16. **方向键控抗 whipsaw:** add 成交后短时出现减仓条件 ⇒ 被 `reduce_cooldown` 挡;reduce 成交后短时
    出现 SOFT 加仓 ⇒ 被 `add_cooldown` 挡(HARD/orphan 例外)。
17. **同向 staged build 不被 cooldown 阻:** add(50%)后立即满足升级 ⇒ 升级(50%→100%)**不**被 add cooldown 阻塞
    (只由 persistence 管)。
18. **反向 hedge 两步解除:** `sign_mismatch(current)` ⇒ 先 `reduce_only` 平到 0,再独立反向开仓,
    **无单笔翻转、无 overshoot**。
19. **tick round 边界:** buy up / sell down 跨 tick 正确,且 round 后仍满足 min-notional;`-1111` 不复现。
20. **lot 余量不空转:** sub-min 余量(如 1380 vs 1379.4)落在 dead-band ⇒ 不反复重试下单。
21. **幂等:** 相同输入连跑两次只产生一单,不产生两单。

---

## 12. 约束合规 + 回滚

- 不加运行时 hedge 指令 — ✅ 仅 CONFIG 门控,确认码/候选/放行门未动。
- depth/position/PnL 缺失不当 0 — ✅ read 失败 fail-closed;成本预算只观测、fail toward hedging。
- 不明确仓位读取 fail-closed — ✅ 更强:控制器读真值为先,失败即停。
- 本地确定性测试先行 — ✅ §11 全部本地可测,可在任何 FMZ trial 之前建好。
- 单文件 / 不强制 class / 主链路不动 / 每机制独立可关 — ✅ dict 状态 + 纯函数;§3 每机制独立 enable;
  `HEDGE_POLICY_V313_ENABLED=False` 即**整层回滚到 v3.1.2**。

---

## 13. 交付实现顺序(建议)

纯函数,便于本地测试:

```python
classify_trigger(p_now, drift, spot, loss_boundary) -> "HARD"|"SOFT"|"NONE"
staged_target(regime, full_target, st)              -> float          # eff_target
mark_condition(st_key, cond_now, now)               -> None           # debounce 维护
persisted(kind, now)                                -> bool
in_cooldown(until_ts, now)                          -> bool
resolve_pending(st, now)                            -> None           # 查/撤/清 + 死锁恢复
clamp_lot(delta)                                    -> float
tick_round(px)                                      -> float          # v3.1.2 保留
marketable_limit(side, band)                        -> float
```

实现步骤:

1. `hedge_state` 持久结构 + `HEDGE_POLICY_V313_ENABLED` 回滚分支。
2. **reconciliation 控制器外层**(§1):pending-first → read-truth → orphan → classify → eff_target → delta → 门控 → 单单。
3. `classify_trigger` + `staged_target`(HARD/SOFT,eff_target)。
4. 时间制 `persisted` + 方向键控 cooldown。
5. `resolve_pending` 死锁恢复。
6. 状态栏 + 日志字段。
7. §11 全部本地用例转测试桩,全绿后再进 FMZ trial。
8. **不**加 runtime command;**不**引入 maker-first;**不**引入 native conditional order。
```
