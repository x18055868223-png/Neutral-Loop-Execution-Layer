# BTC 短周期价差期权 · 对冲模块 v3.2 干净稳健改进方案

**交付目标:** 给 Codex / work agent 的可落地实现说明。  
**生成日期:** 2026-06-28  
**适用仓库:** `x18055868223-png/Neutral-Loop-Execution-Layer`  
**目标版本建议:** `STRATEGY_VERSION = "3.2.0-manual-gate"`  
**核心原则:** 复用 v3.1.4 已验证的 reconciliation 控制器；只替换触发后的 sizing / 持有 / 减仓规则；删除确认无活跃引用的旧对冲死代码；不新增运行时 hedge 指令；不把实现复杂度转嫁到 FMZ live。

---

## 0. 依据与审计范围

本方案对照了三类材料：

1. **原始 v3.1.4 inquiry 约束。** 必须保持 FMZ runtime 交互入口只有确认码，`POSITION_MANAGE` 仍是非交互读屏，不改候选库、确认码、入场确认、普通止盈、风险退出预算，不把 Binance position / depth / PnL 缺失当 0，本地测试和 bundle 编译不等于 FMZ live 通过。fileciteturn0file1
2. **Opus 4.8 模拟评审。** 结论是保留“风险恶化 → 永续对冲”的哲学，但收紧当前 v3.1.4；核心改进是 gamma-aware sizing、hold/no-trade band、reduce 侧 maker-first 候选、crash override、final-3h suppress_add。fileciteturn0file0
3. **GitHub 最新交付物。** 当前仓库交付为 `3.1.4-manual-gate`，最新 FMZ artifact 位于 `artifacts/最新交付/spm_manual_gate_execution_fmz_v3_1_4.py`，可编辑源在 `realsrc/src/`，bundle 由 `realsrc/build_bundle.py` 生成。fileciteturn4file0

GitHub 当前 v3.1.4 handoff 声明本地验证为 `304 passed, 0 failed`、bundle check 和当前交付 py_compile 均通过，但 FMZ live 状态未声称通过，必须以后续实盘日志为准。fileciteturn44file0

---

## 1. 执行结论

**结论：采用 v3.2 小步收束，不推翻 v3.1.4。**

当前 v3.1.4 的最大价值不是触发阈值本身，而是已经把 Binance hedge 执行改成了正确的工程结构：pending-first、read-as-truth、reconcile-to-`eff_target`、single-flight、HARD full、SOFT staged、orphan/reverse reduce-only。这个控制器应当完整复用。fileciteturn4file0

v3.2 不应做大重构，也不应上 ML / RL / ES optimizer / native conditional order。v3.2 应只做五件事：

| 优先级 | 改动 | 目标 |
|---:|---|---|
| P0 | **把 SOFT 固定 50% 改为 gamma-aware dynamic ratio** | 降低远离行权价的虚惊对冲，靠近行权价/高 gamma 时自动放大 |
| P0 | **加入 no-trade band + ordinary reduce min-hold** | 抑制 whipsaw 和连续小额 rehedge |
| P0 | **final-3h suppress SOFT add，但保留 HARD/CRASH/reduce/orphan** | 与最后 3h 普通止盈暂停的设计一致，避免临交割噪音反复开新 hedge |
| P1 | **加入 CRASH override，但不新增复杂行情历史模块** | 极端快速 adverse move 时直接 full target |
| P2 | **maker-first reduce 只作为第二阶段，待 FMZ order-shape 校验后打开** | Opus 模拟中有成本收益，但当前 handoff 明确建议先校验真实订单状态形态再考虑 |

一句话：

> **保留 V313 reconciliation，替换 sizing 和解除节奏；新增最少字段；删除确认无用的 dry intent / legacy hedge path；不要把 v3.2 做成另一个策略框架。**

---

## 2. 对照验证：Opus 4.8、GPT-5.5 Pro、GitHub v3.1.4 是否一致

| 问题 | Opus 4.8 模拟结论 | GPT-5.5 Pro 先前结论 | GitHub v3.1.4 当前实现 | v3.2 收束判断 |
|---|---|---|---|---|
| 是否保留“风险恶化即对冲” | 保留但收紧 | 保留但收紧 | 已实现 V313 reconciliation | **保留** |
| SOFT 首次比例 | 固定比例不如 gamma-aware；固定时 0.40–0.50 | 动态 25/50/75；不应只靠概率 | 固定 `HEDGE_SOFT_INITIAL_RATIO = 0.50`fileciteturn29file0 | **改为 0.40 floor + gamma-aware max** |
| HARD full target | 多数 full；CRASH 必须 full | HARD/CRASH full，概率型可分层 | HARD 直接 full target | **保留 HARD full，新增 CRASH 标记** |
| 触发信号 | breach probability 不够，应加 gamma / hold / band / crash | 应加 speed/RV/distance/gamma/DTE | 当前主要由 probability / drift / boundary 触发 | **第一版只加 gamma + crash + final3，不引入 RV/distance 多因子执行门** |
| 减仓 | hold-the-hedge + no-trade band；maker-first reduce 有价值 | 减仓需概率 + 安全区 + speed + persistence | 当前主要是 `p_now < watch - buffer` + persistencefileciteturn17file0 | **加 min-hold + 20% target band；distance/speed 先显示后校准** |
| final 3h | 推荐 suppress_add，保留 crash + reduce | 未确认 SOFT 更克制，HARD/CRASH 允许 | 普通 TP 有 final-3h gate，但 hedge 未做 suppress_add | **新增 SOFT add suppression** |
| maker-first reduce | BEST 组成项之一 | 推荐 reduce 侧 maker-first | v3.1.3 spec 明确暂不做 maker-first，列为 v3.2/v4 研究项fileciteturn40file0 | **第二阶段做，不进第一版主补丁** |
| 工程结构 | 不改交互边界 | 不改 FMZ runtime command | 当前 handoff 保持确认码唯一交互fileciteturn44file0 | **严格保持** |

关键分歧：Opus 建议 maker-first reduce 是 BEST 的成本项，但当前仓库 handoff 的 next check 明确要求先审真实 FMZ Binance order-status shape，再调 persistence/cooldown，之后再考虑 maker-first 或 segmented execution。fileciteturn44file0  
因此 v3.2 第一版不应立刻实现 maker-first reduce。否则会把已验证的 single-flight pending 生命周期扩展出新分支，增加撤单失败、晚成交、重启残单、maker 超时 fallback 的复杂度。

---

## 3. GitHub 最新交付物审核

### 3.1 当前做得对，必须复用

**交付结构正确。** README 和 handoff 均要求编辑 `realsrc/src/`，再由 `build_bundle.py` 合成单文件；不要直接手改 artifact。fileciteturn4file0  
`build_bundle.py` 的 module order 已把 `hedge`、`execution`、`hedge_risk`、`strategy` 纳入 bundle，`--check` 会 py_compile、注入 FMZ shim、检查主链和对冲函数符号，并扫描 KPF / calendar 残留。fileciteturn22file0

**Binance 适配方向正确。** `binance_io.py` 会把交易员配置的 `BTCUSDC` 映射为 FMZ currency `BTC_USDC`，并设置 `swap` contract type；position snapshot 会读净 BTC 数量与 unrealized PnL；prompt-limit 价格会按 `HEDGE_BINANCE_PRICE_TICK = 0.1` 买入向上、卖出向下取整。fileciteturn27file0

**对冲基础纯函数正确。** `hedge.py` 已经有方向、组合净 delta、线性 Binance target、direction consistency、reduce_only action、orphan、settlement guard 等纯函数。fileciteturn23file0 这些应扩展，不应重写。

**V313 controller 结构正确。** 当前 handoff 明确：resolve pending first、read Binance hedge position as truth、calculate `full_target`、stage/reconcile to `eff_target`、每轮最多 submit 一单；HARD 直接 full，SOFT 先 50%，orphan/reverse/short-flat 先 reduce-only。fileciteturn44file0

**测试覆盖强。** 当前 `test_v3_1_4_hedge_policy.py` 已覆盖 SOFT half target、SOFT persistence full、HARD full、late fill 不 overhedge、position read fail-closed、reconcile to `eff_target`、pending stale recovery、partial active single-flight、reverse unwind、sub-min deadband、submit idempotency。fileciteturn42file0 fileciteturn43file0

### 3.2 当前不足，v3.2 需要修正

1. **`full_target` 仍是静态 `HEDGE_REDUCTION_RATIO`。**  
   `_evaluate_hedge()` 当前通过 `hedge_target_position(net_opt, HEDGE_REDUCTION_RATIO, ...)` 生成 target。fileciteturn19file0 这意味着 trigger 后的最大 target 仍固定 50%，并不 gamma-aware。

2. **SOFT sizing 仍是固定 50%。**  
   `config.py` 默认 `HEDGE_SOFT_INITIAL_RATIO = 0.50`；`_hedge_policy_plan()` 中 SOFT 未持续时直接用该比例。fileciteturn29file0 fileciteturn16file0 这正是 Opus 和 GPT 模拟都指出需要收紧的点。

3. **risk layer 计算了 gamma 相关概念，但没有进入 active controller。**  
   `hedge_risk.py` 有 `_tail_exposure_acceleration()`，可以根据 delta/gamma ratio 判定 tail acceleration。fileciteturn25file0 但 `evaluate_position_risk()` 最终给 `_make_hedge_intent()` 传入的是 `PERSISTENCE_LOW`，active controller 实际仍主要消费 probability/drift/boundary。fileciteturn26file0

4. **`hedge_intent` 是旧 dry intent 语义，且仍写 `hedge_venue = DERIBIT`。**  
   `_make_hedge_intent()` 返回 `execution_mode = DRY_INTENT_ONLY`、`hedge_venue = DERIBIT`。fileciteturn26file0 当前真实默认 hedge venue 已是 Binance BTCUSDC。这个字段如果只用于展示也容易误导；如果没有 active consumer，应删除或改为中性 diagnostic。

5. **ordinary reduce 太依赖概率回落。**  
   当前普通 reduce 主要看 `p_now < watch`、`watch - buffer`、`HEDGE_REDUCE_PERSIST_SECONDS`。fileciteturn17file0 缺少 min-hold 和 target band，会让小额 live-test 在反弹时频繁撤对冲。

6. **当前 deadband 只是 min trade 级别。**  
   `_hedge_policy_action()` 用 `abs(delta) < min_trade` 做 LOT_DEADBAND。fileciteturn16file0 对 0.02–0.04 BTC target 还不够，Opus 的 BEST 靠 20% no-trade band 显著降低 churn。

7. **final-3h hedge 没有 suppress_add。**  
   v3.1.3/v3.1.4 只把普通 TP 在最后 3h 暂停，risk exit 和 hedge 仍 active。fileciteturn5file0 这符合安全边界，但没有实现 Opus 推荐的 “最后 3h 不新开 SOFT hedge，保留 crash / hard / reduce”。

8. **legacy `bnc_place_hedge()` 与 V313 `bnc_submit_hedge_order()` 并存。**  
   `bnc_submit_hedge_order()` 是 V313 当前 submit path；`bnc_place_hedge()` 是旧的一步式下单、Sleep、查单、撤残单路径。fileciteturn27file0 fileciteturn28file0 若 repo-wide grep 证实旧路径只服务 `HEDGE_POLICY_V313_ENABLED=False` 或测试，应在 v3.2 清理，而不是继续维护两套 hedge lifecycle。

---

## 4. v3.2 目标策略：Clean Universal Gamma-Aware Hedge

### 4.1 不新增复杂四层状态机

理论上 WATCH / SOFT / HARD / CRASH 四级更完整，但当前代码已有 V313 的 HARD/SOFT/NONE 结构。为了保持干净，v3.2 不应引入新的多态框架。

建议内部只做：

```text
NONE   = 不新增 hedge；已有 hedge 只按 reduce gate 处理
SOFT   = 风险恶化但未到硬边界；gamma-aware staged target
HARD   = boundary / emergency probability / hard drift；full target
CRASH  = 极端 adverse speed；full target，显示上独立于 HARD
WATCH  = display-only；不驱动下单
```

WATCH 不进入执行分支，只进 `policy_detail` 和 `LogStatus`，避免多一层状态产生新 bug。

### 4.2 full target 口径

v3.1.4 当前 `full_target = net_option_delta × HEDGE_REDUCTION_RATIO`。v3.2 建议改为：

```text
raw_full_target = - net_option_delta              # 100% delta hedge target，带方向
```

然后由 policy layer 决定实际 `eff_target`：

```text
SOFT eff_target  = raw_full_target × soft_ratio
HARD eff_target  = raw_full_target
CRASH eff_target = raw_full_target
NONE             = 不新增；已有 hedge 进入 reduce gate
```

这样 `full_target` 的语义恢复为“理论可对冲上限”，而不是“已被 reduction ratio 截断后的目标”。这也让 HARD / CRASH full target 不再被历史的 `HEDGE_REDUCTION_RATIO = 0.5` 锁死。

### 4.3 gamma-aware SOFT ratio

新增组合 gamma fraction：

```python
def hedge_gamma_fraction(short_gamma, long_gamma, remaining_short_qty, long_remaining_qty, spot,
                         ref=1_000_000.0, floor=0.30):
    combo_gamma = 0.0
    if is_num(short_gamma):
        combo_gamma += -remaining_short_qty * short_gamma
    if is_num(long_gamma):
        combo_gamma += long_remaining_qty * long_gamma
    dollar_gamma = abs(combo_gamma) * spot * spot
    gnorm = clamp(dollar_gamma / ref, 0.0, 1.0)
    return clamp(floor + (1.0 - floor) * gnorm, floor, 1.0)
```

SOFT ratio：

```python
if SOFT and not persisted and not worsened:
    soft_ratio = max(HEDGE_SOFT_INITIAL_RATIO, hedge_gamma_fraction)
else:
    soft_ratio = 1.0
```

建议默认：

```python
HEDGE_GAMMA_AWARE_ENABLED = True
HEDGE_GAMMA_NORM_REF = 1_000_000.0
HEDGE_GAMMA_FRAC_FLOOR = 0.30
HEDGE_SOFT_INITIAL_RATIO = 0.40
```

解释：

- 远离行权价、gamma 小：SOFT 约 40%，比当前固定 50% 更克制。
- 近行权价、近到期、gamma 抬升：SOFT 自动提高到 60%–100%。
- HARD / CRASH 不看 gamma fraction，直接 full target。

这比“固定 25/50/75”更干净，因为只用一个连续公式，不增加分档表和更多 if/else。

### 4.4 no-trade band

新增 target-relative deadband，替换单纯 min trade deadband：

```python
deadband = max(HEDGE_BINANCE_MIN_TRADE,
               abs(full_target) * HEDGE_REBALANCE_BAND_FRAC)
if abs(eff_target - current) < deadband:
    HOLD("TARGET_BAND_DEADBAND")
```

默认：

```python
HEDGE_REBALANCE_BAND_FRAC = 0.20
```

这直接吸收：

- 小额 live-test 的 0.001 BTC granularity；
- 0.0196 vs 0.0200 这类残差；
- gamma/delta 小幅抖动造成的频繁 rehedge。

### 4.5 ordinary reduce min-hold

新增普通 reduce 的最短持有。只限制普通 reduce，不限制 orphan / reverse / short-flat / risk exit cleanup。

```python
ordinary_reduce_allowed = (
    p_now <= watch_probability - HEDGE_REDUCE_PROB_BUFFER
    and reduce_persisted
    and now_ms >= last_add_fill_ts + HEDGE_MIN_HOLD_SECONDS * 1000
    and abs(current - eff_target) >= deadband
)
```

默认：

```python
HEDGE_MIN_HOLD_SECONDS = 720      # 12 min
```

说明：

- Opus BEST 的 “hold-the-hedge + no-trade band” 是抗 whipsaw 的主力。
- 12 分钟对 24h / 48h short vertical spread 足够短，不会显著拖累真正趋势行情。
- final-3h 可维持同一 min-hold；不再额外调短，避免临交割抖动。

### 4.6 final-3h suppress SOFT add

新增：

```python
HEDGE_FINAL3H_MODE = "SUPPRESS_SOFT_ADD"    # NORMAL | SUPPRESS_SOFT_ADD
```

行为：

| 剩余 DTE | 触发 | 行为 |
|---:|---|---|
| > 3h | SOFT | 正常 gamma-aware staged add |
| <= 3h | SOFT | 不新开 / 不增加 hedge，记录 `FINAL3H_SOFT_ADD_SUPPRESSED` |
| <= 3h | HARD | 允许 full target |
| <= 3h | CRASH | 允许 full target |
| 任意 | reduce / orphan / reverse / short-flat | 允许 reduce-only |

这与原系统“最后 3h 普通 TP 暂停，但 risk exit / hedge / orphan cleanup 仍 active”的边界兼容。fileciteturn5file0

### 4.7 CRASH override

第一版 CRASH 不要做复杂行情历史表。只加极简锚点：

```python
state["crash_ref_price"]
state["crash_ref_ts"]
```

每轮维护 adverse 10min move：

```python
adverse_bps = adverse_move_bps(direction, crash_ref_price, current_spot)
if now - crash_ref_ts > HEDGE_CRASH_SPEED_WINDOW_SECONDS * 1000:
    reset crash_ref_price = current_spot

if adverse_bps >= HEDGE_CRASH_MOVE_BPS:
    trigger_state = "CRASH"
```

默认：

```python
HEDGE_CRASH_ENABLED = True
HEDGE_CRASH_SPEED_WINDOW_SECONDS = 600
HEDGE_CRASH_MOVE_BPS = 110       # 约 1.10% / 10min adverse move
```

CRASH 行为：

```text
- eff_target = full_target
- bypass SOFT persistence
- bypass add cooldown
- bypass final3 SOFT suppression
- use HARD cross bps
- cost/slip 仅告警，不 gate
```

### 4.8 maker-first reduce：第二阶段，不进入 v3.2 第一版主补丁

Opus 模拟显示 maker-first reduce 能显著降低成本；但当前仓库的 v3.1.4 handoff 已经把下一步检查明确为：先核对真实 FMZ Binance order-status shapes，再调 SOFT persistence/cooldown，之后再考虑 maker-first 或 segmented execution。fileciteturn44file0

所以 v3.2 第一版不要立刻加 maker-first reduce。建议规则：

```python
HEDGE_MAKER_FIRST_REDUCE_ENABLED = False   # v3.2.0 默认 False
```

只有当 FMZ live log 证明以下形态稳定后，再在 v3.2.1 打开：

- GetOrder active / partial / terminal 状态可稳定区分；
- CancelOrder 后晚成交能被下一轮 read-as-truth 吸收；
- maker order timeout 后 fallback 不破坏 single-flight；
- reduce_only direction 在 Binance/FMZ 上行为一致。

---

## 5. 参数建议

| 参数 | v3.1.4 当前 | v3.2 建议 | 说明 |
|---|---:|---:|---|
| `HEDGE_POLICY_V313_ENABLED` | True | 保留 True；v3.2 直接升级该控制器 | 不新增新 policy engine |
| `HEDGE_SOFT_INITIAL_RATIO` | 0.50 | 0.40 | gamma-aware 后降低远端虚惊 drag |
| `HEDGE_GAMMA_AWARE_ENABLED` | 无 | True | 新增 |
| `HEDGE_GAMMA_FRAC_FLOOR` | 无 | 0.30 | gamma floor |
| `HEDGE_GAMMA_NORM_REF` | 无 | 1_000_000.0 | 与 Opus 公式一致，先固定，后用 FMZ logs 校准 |
| `HEDGE_REBALANCE_BAND_FRAC` | 无 | 0.20 | 抗 churn 主参数 |
| `HEDGE_MIN_HOLD_SECONDS` | 无 | 720 | 普通 reduce min-hold |
| `HEDGE_FINAL3H_MODE` | 无 | `SUPPRESS_SOFT_ADD` | 只压 SOFT add |
| `HEDGE_CRASH_ENABLED` | 无 | True | 极端 adverse speed override |
| `HEDGE_CRASH_SPEED_WINDOW_SECONDS` | 无 | 600 | 10min 简单锚点 |
| `HEDGE_CRASH_MOVE_BPS` | 无 | 110 | 1.10% adverse move |
| `HEDGE_HARD_CROSS_BPS` | 30 | 30 | 保持 |
| `HEDGE_SOFT_CROSS_BPS` | 3 | 3 | 保持 |
| `HEDGE_PENDING_STALE_SECONDS` | 10 | 10 | 保持，先看 FMZ logs |
| `HEDGE_MAKER_FIRST_REDUCE_ENABLED` | 无 | False | v3.2.1 才考虑打开 |

---

## 6. Codex 落地流程

### 6.1 分支与版本

```powershell
git checkout main
git pull
git checkout -b hedge-v3-2-clean-gamma-aware
```

修改：

```python
STRATEGY_VERSION = "3.2.0-manual-gate"
```

只编辑：

```text
realsrc/src/config.py
realsrc/src/hedge.py
realsrc/src/hedge_risk.py
realsrc/src/strategy.py
realsrc/src/display.py            # 只增字段展示，不改交互
realsrc/tests/test_*.py
```

不要手改：

```text
realsrc/spm_manual_gate_execution_fmz.py
artifacts/*.py
artifacts/最新交付/*.py
```

bundle 由 `build_bundle.py` 生成。fileciteturn22file0

### 6.2 Step 1：新增 config，保持默认干净

在 `config.py` hedge config block 下新增：

```python
HEDGE_GAMMA_AWARE_ENABLED = True
HEDGE_GAMMA_FRAC_FLOOR = 0.30
HEDGE_GAMMA_NORM_REF = 1_000_000.0
HEDGE_REBALANCE_BAND_FRAC = 0.20
HEDGE_MIN_HOLD_SECONDS = 720
HEDGE_FINAL3H_MODE = "SUPPRESS_SOFT_ADD"   # NORMAL | SUPPRESS_SOFT_ADD
HEDGE_CRASH_ENABLED = True
HEDGE_CRASH_SPEED_WINDOW_SECONDS = 600
HEDGE_CRASH_MOVE_BPS = 110
HEDGE_MAKER_FIRST_REDUCE_ENABLED = False
```

并把：

```python
HEDGE_SOFT_INITIAL_RATIO = 0.40
```

`validate_config()` 增加基本范围校验：

```text
0 <= HEDGE_SOFT_INITIAL_RATIO <= 1
0 <= HEDGE_GAMMA_FRAC_FLOOR <= 1
HEDGE_GAMMA_NORM_REF > 0
0 <= HEDGE_REBALANCE_BAND_FRAC <= 1
HEDGE_MIN_HOLD_SECONDS >= 0
HEDGE_FINAL3H_MODE in ("NORMAL", "SUPPRESS_SOFT_ADD")
HEDGE_CRASH_MOVE_BPS >= 0
HEDGE_CRASH_SPEED_WINDOW_SECONDS > 0
```

### 6.3 Step 2：在 `hedge.py` 新增纯函数

新增纯函数，保持无 `_G`、无 FMZ、无下单：

```python
def hedge_gamma_fraction(short_gamma, long_gamma, remaining_short_qty,
                         long_remaining_qty, spot, ref, floor):
    ...

def hedge_rebalance_deadband(full_target, min_trade, band_frac):
    return max(min_trade or 0.0, abs(full_target or 0.0) * max(0.0, band_frac or 0.0))

def hedge_target_ratio_for_soft(base_ratio, gamma_fraction, persisted=False, worsened=False):
    if persisted or worsened:
        return 1.0
    return max(base_ratio or 0.0, gamma_fraction or 0.0)
```

这一步必须配单测，不接入策略。

### 6.4 Step 3：在 `hedge_risk.py` 清理或改造旧 dry intent

当前 `_make_hedge_intent()` 仍返回 `hedge_venue = DERIBIT`，且 `execution_mode = DRY_INTENT_ONLY`。fileciteturn26file0

Codex 执行：

1. repo-wide grep：

```powershell
rg "hedge_intent|_make_hedge_intent|HedgeIntentPackage|EXECUTION_DRY_INTENT_ONLY"
```

2. 若只有 `hedge_risk.py` 和测试引用：删除 `_hedge_size_mode()`、`_make_hedge_intent()`、`BUY_HEDGE`、`SELL_HEDGE`、`EXECUTION_DRY_INTENT_ONLY`，`evaluate_position_risk()` 返回 `hedge_intent = None`。
3. 若 display 仍读取 `hedge_intent`：改为读取 active controller 的 `hedge_detail.policy_detail`，不要继续展示 dry intent。

原则：**active hedge 只能由 V313/V32 controller 决定，不允许 risk layer 再输出一个伪执行 intent。**

### 6.5 Step 4：在 `_evaluate_hedge()` 接入 raw full target 与 gamma fraction

当前 `_evaluate_hedge()` 已读取 short/protection delta、Binance position snapshot，并 fail-closed 处理 position gap。fileciteturn18file0 复用这段，不重写。

改动：

1. 读取 protection gamma：

```python
short_gamma = (quote(si) or {}).get("gamma")
prot_gamma = (quote(li) or {}).get("gamma") if li else None
```

2. 计算：

```python
net_opt = option_net_delta(rem_qty, short_delta, long_qty, prot_delta)
if HEDGE_GAMMA_AWARE_ENABLED:
    target_ratio_for_full = 1.0
else:
    target_ratio_for_full = HEDGE_REDUCTION_RATIO
full_target = hedge_target_position(net_opt, target_ratio_for_full, spot, contract_size, min_trade, linear=vcfg["linear"])
```

3. 附加 diagnostic：

```python
gamma_fraction = hedge_gamma_fraction(short_gamma, prot_gamma, rem_qty, long_qty, spot,
                                      HEDGE_GAMMA_NORM_REF, HEDGE_GAMMA_FRAC_FLOOR)
```

4. 返回 hedge dict 增加：

```python
"gamma_fraction": gamma_fraction,
"short_gamma": short_gamma,
"protection_gamma": prot_gamma,
"target_semantics": "RAW_FULL_DELTA" if HEDGE_GAMMA_AWARE_ENABLED else "V313_REDUCTION_RATIO",
```

缺 gamma 时：

```text
不 fail-closed，不当 0；gamma_fraction 使用 floor，并在 detail 里标 `GAMMA_DATA_FLOOR`。
```

理由：缺 gamma 不应阻断 HARD/CRASH；但也不应因为缺失而误以为 gamma=0。floor 是安全退化。

### 6.6 Step 5：在 `_hedge_policy_plan()` 接入 level / ratio / band / final3 / min-hold

保留当前顺序：

```text
pending-first → read current as truth → data gap hold → orphan/reverse → trigger classify → eff_target → action → cooldown → submit detail
```

只替换局部逻辑。

#### 6.6.1 level

当前 `_hedge_policy_trigger_state()` 返回 `HARD` / `SOFT` / `NONE`。保留函数，新增 wrapper：

```python
level = _hedge_policy_trigger_state(risk)
if _hedge_policy_crash_trigger(st, snap, risk, now_ms):
    level = "CRASH"
```

CRASH 仅覆盖为更强状态，不覆盖 orphan/reverse/flat unwind。

#### 6.6.2 SOFT ratio

替换当前：

```python
ratio = 1.0 if (persisted or worsened) else HEDGE_SOFT_INITIAL_RATIO
```

为：

```python
gamma_frac = out.get("gamma_fraction")
base = HEDGE_SOFT_INITIAL_RATIO
ratio = 1.0 if (persisted or worsened) else max(base, gamma_frac or HEDGE_GAMMA_FRAC_FLOOR)
ratio = min(1.0, max(0.0, ratio))
eff_target = full_target * ratio
```

#### 6.6.3 HARD / CRASH

```python
elif level in ("HARD", "CRASH"):
    eff_target = full_target
    forced_reason = "CRASH_TRIGGER_SPEED" if level == "CRASH" else "HARD_TRIGGER_EMERGENCY"
```

HARD/CRASH 继续绕过 SOFT persistence、add cooldown、SOFT slippage guard；episode cost 仍只告警不 gate。

#### 6.6.4 no-trade band

把 `_hedge_policy_action(current, eff_target, min_trade, forced_reason)` 扩展为：

```python
def _hedge_policy_action(current, eff_target, min_trade, forced_reason=None, deadband=None):
    threshold = max(min_trade, deadband or 0.0)
    if abs(delta) < threshold:
        return HOLD("TARGET_BAND_DEADBAND"), 0.0, None, False
```

`deadband` 来自：

```python
deadband = hedge_rebalance_deadband(full_target, HEDGE_BINANCE_MIN_TRADE, HEDGE_REBALANCE_BAND_FRAC)
```

orphan / reverse / short-flat unwind 不受 target band 阻断。

#### 6.6.5 ordinary reduce min-hold

普通 reduce 进入下单前增加：

```python
if is_reduce and forced_reason not in ("ORPHAN_HEDGE_UNWIND", "REVERSE_HEDGE_UNWIND"):
    if HEDGE_MIN_HOLD_SECONDS > 0 and st.get("last_action") == "ADD":
        if now_ms < (st.get("last_fill_ts") or 0) + HEDGE_MIN_HOLD_SECONDS * 1000:
            HOLD("REDUCE_MIN_HOLD_ACTIVE")
```

注意：

- partial pending active 仍先 pending-first，不到这里。
- resolved fill 才更新 `last_action` / `last_fill_ts`。
- reduce_only cleanup 不受 min-hold 限制。

#### 6.6.6 final3 SOFT suppression

在 action 判定后、submit 前：

```python
if level == "SOFT" and is_add and _in_final3h(snap, now_ms) and HEDGE_FINAL3H_MODE == "SUPPRESS_SOFT_ADD":
    HOLD("FINAL3H_SOFT_ADD_SUPPRESSED")
```

HARD/CRASH 不受此规则影响。

### 6.7 Step 6：display 只增可解释字段

`POSITION_MANAGE` 已显示 policy state、reason、full/eff/current/delta、pending、cooldown、persistence、episode cost。fileciteturn44file0

只新增以下字段，不改变交互：

```text
level: NONE/SOFT/HARD/CRASH
soft_ratio
gamma_fraction
gamma_data_state: OK / GAMMA_DATA_FLOOR
rebalance_deadband
final3_mode
crash_adverse_bps
min_hold_until
```

不要添加任何 runtime command hint。

### 6.8 Step 7：dead code cleanup

按以下顺序清理，避免误删：

#### A. 必删候选：旧 dry hedge intent

若 grep 证明无 active consumer，删除：

```text
hedge_risk._hedge_size_mode
hedge_risk._make_hedge_intent
EXECUTION_DRY_INTENT_ONLY
BUY_HEDGE / SELL_HEDGE   # 若只服务 dry intent
```

原因：该 intent 不是 active controller 的输入，且仍写 DERIBIT venue，和当前 Binance 默认冲突。fileciteturn26file0

#### B. 条件删除：legacy one-step Binance hedge

先 grep：

```powershell
rg "bnc_place_hedge|HEDGE_POLICY_V313_ENABLED = False|legacy_full_prompt_limit"
```

如果 `bnc_place_hedge()` 只被旧 fallback 和 tests 引用，且操作者确认不再需要 `HEDGE_POLICY_V313_ENABLED=False` live rollback：

- 删除 `bnc_place_hedge()`；
- 删除对应 tests；
- 保留 `bnc_submit_hedge_order()` / `bnc_get_hedge_order()` / `bnc_cancel_hedge_order()`；
- README / CHATGPT handoff 不再写 “False returns legacy one-step prompt-limit”。

若仍需要 fallback：

- 暂不删除；
- 但不要在 v3.2 新逻辑中继续扩展 legacy path；
- 在文档标注 legacy fallback 不参与新 policy。

#### C. 不应删除

```text
hedge.py direction / target / action pure functions
V313 state / pending / reconcile controller
Binance BTC_USDC + swap selection
position snapshot PnL display
orphan / reverse / short-flat reduce-only path
risk exit / TP / candidate / confirmation-code modules
```

---

## 7. 测试计划

### 7.1 新增/调整 deterministic tests

在现有 `test_hedge.py` 增加：

1. `test_gamma_fraction_bounds_and_monotonic`  
   gamma 越高 fraction 越高；缺 gamma 返回 floor；输出在 `[floor, 1]`。

2. `test_gamma_fraction_uses_combo_gamma`  
   short gamma 与 protection gamma 应按剩余腿数量组合，而不是只看短腿。

3. `test_rebalance_deadband_uses_target_band`  
   `full_target=0.02, band=0.20` 时 deadband 至少 0.004。

在 `test_v3_1_4_hedge_policy.py` 或新建 `test_v3_2_hedge_policy.py` 增加：

4. `test_soft_initial_ratio_is_max_base_and_gamma`  
   `base=0.40, gamma=0.65` → SOFT 初始 `eff=65% full`。

5. `test_soft_low_gamma_uses_40pct_not_50pct`  
   low gamma → SOFT initial 40%，验证 v3.2 确实收紧。

6. `test_soft_persistence_still_escalates_to_full`  
   persisted/worsened → 100%。

7. `test_hard_ignores_gamma_fraction_and_targets_full`  
   gamma floor 0.30，但 HARD `eff=full_target`。

8. `test_crash_overrides_final3_and_add_cooldown`  
   final3 + add cooldown + CRASH → 仍 full target。

9. `test_final3_blocks_soft_add_only`  
   final3 + SOFT add → HOLD `FINAL3H_SOFT_ADD_SUPPRESSED`；final3 + reduce → 允许。

10. `test_target_band_blocks_small_rehedge`  
   `delta < max(min_trade, 20% target)` → HOLD `TARGET_BAND_DEADBAND`。

11. `test_min_hold_blocks_ordinary_reduce`  
   add 后 12min 内 probability 回落 → HOLD `REDUCE_MIN_HOLD_ACTIVE`。

12. `test_min_hold_does_not_block_orphan_unwind`  
   short flat / orphan → 立即 reduce-only。

13. `test_missing_gamma_uses_floor_not_zero_and_not_fail_closed`  
   gamma 缺失不把 fraction 当 0，不阻断 HARD/CRASH。

14. `test_no_deribit_dry_hedge_intent_residual`  
   若删除 dry intent，bundle 中不得残留 `hedge_venue = "DERIBIT"` 的 hedge intent。

15. `test_policy_detail_contains_v32_fields`  
   `gamma_fraction / rebalance_deadband / final3_mode / min_hold_until / crash_adverse_bps` 可展示。

### 7.2 必须保持通过的旧测试

至少保持以下旧测试语义：

- pending order blocks new order first；
- late fill current absorbs delta；
- position read failure fail-closed；
- reconcile target is `eff_target` not `full_target`；
- pending stale recovers；
- active partial keeps pending；
- terminal fill mirrored into ledger event；
- reverse hedge unwinds to zero first；
- sub-min residual is deadbanded；
- submit idempotent。fileciteturn42file0 fileciteturn43file0

### 7.3 Verification commands

```powershell
$py = 'C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe'

& $py realsrc\tests\run_all.py
& $py realsrc\build_bundle.py --check
& $py -m py_compile realsrc\spm_manual_gate_execution_fmz.py
```

完成 bundle 后：

```text
1. copy realsrc/spm_manual_gate_execution_fmz.py -> artifacts/spm_manual_gate_execution_fmz.py
2. copy -> artifacts/spm_manual_gate_execution_fmz_v3_2_0.py
3. 清空 artifacts/最新交付/ 下旧版本，只保留 spm_manual_gate_execution_fmz_v3_2_0.py
4. 更新 CHECKSUMS.txt
5. 更新 README.md / CHATGPT5.5_PRO.md / doc/CODEX_HANDOFF_v3_2_0.md
```

README 当前已明确 `artifacts/最新交付/` 只保留一个当前版本文件。fileciteturn4file0

---

## 8. FMZ live 校准项

本地测试只能证明 deterministic logic，不证明 live readiness。当前项目 handoff 也明确 FMZ live status 未声称通过，结论必须来自用户 FMZ logs 和 exchange state。fileciteturn44file0

v3.2 上线后至少收集：

| 项目 | 用途 |
|---|---|
| Binance `GetOrder` active / partial / terminal 原始 shape | 决定是否能做 maker-first reduce |
| CancelOrder 后晚成交比例 | 验证 single-flight + read-as-truth 能否吸收 |
| prompt-limit 实际成交滑点 | 校准 `HEDGE_HARD_CROSS_BPS` / `HEDGE_SOFT_CROSS_BPS` |
| gamma_fraction 分布 | 校准 `HEDGE_GAMMA_NORM_REF` |
| SOFT suppressed final3 次数与后续尾部 | 判断 final3 suppress 是否过度保守 |
| target-band HOLD 次数 | 判断 `HEDGE_REBALANCE_BAND_FRAC=0.20` 是否过宽 |
| ordinary reduce 被 min-hold 阻挡后 PnL | 判断 12min hold 是否过长 |
| CRASH trigger 次数 | 判断 `110 bps / 10min` 是否过敏 |
| 小额 live-test 成本 / credit 占比 | 校验 min trade 粒度效应 |

---

## 9. 不做清单

为避免过度工程化，v3.2 明确不做：

1. 不新增 FMZ runtime hedge command。
2. 不改变确认码系统、候选库、入场、普通 TP、风险退出预算。
3. 不引入 ML / RL / online optimizer。
4. 不引入 ES/CVaR optimizer 作为 live decision engine。
5. 不新增交易所 native conditional order。
6. 不做 maker-first add。
7. 不把 maker-first reduce 放进 v3.2.0 第一版。
8. 不把缺失 depth / position / PnL / gamma 当 0。
9. 不把 WATCH 做成会改变仓位的真实执行状态。
10. 不为了兼容旧模式新增第二套 hidden bridge。
11. 不手改 artifact。

---

## 10. 最终验收标准

v3.2 可接受的完成定义：

1. `STRATEGY_VERSION = "3.2.0-manual-gate"`。
2. 所有 hedge 决策仍从 V313 reconciliation controller 进入。
3. SOFT initial 从固定 50% 变为 `max(0.40, gamma_fraction)`。
4. HARD / CRASH full target 不被 gamma fraction、cost alert、SOFT cooldown 阻断。
5. 普通 reduce 需要 probability hysteresis + persistence + min-hold + target band。
6. final3 只 suppress SOFT add，不 suppress HARD/CRASH/reduce/orphan。
7. pending-first、read-as-truth、single-flight、late fill absorption、reverse hedge unwind 全部旧测试仍通过。
8. 删除或中性化 `hedge_intent` 的旧 DERIBIT dry intent。
9. 若删除 legacy `bnc_place_hedge()`，必须有 grep 与测试证明无 active path 依赖。
10. `realsrc/tests/run_all.py` 全绿。
11. `realsrc/build_bundle.py --check` 通过。
12. 当前 versioned artifact、latest artifact、source bundle checksum 一致。
13. 文档明确：本地通过不等于 FMZ live 通过。

---

## 11. 给 Codex 的最短执行指令

```text
目标：在现有 v3.1.4 V313 Binance hedge reconciliation controller 上实现 v3.2.0 clean gamma-aware hedge policy。

边界：
- 不新增 runtime hedge command。
- 不改 candidate / confirm-code / entry / ordinary TP / risk-exit budget。
- 不把 Binance position/depth/PnL/gamma 缺失当 0。
- 不手改 artifacts；只改 realsrc/src 后 build。
- 不引入 ML/native conditional/maker-first add。

实现顺序：
1. config.py 新增 v3.2 参数；SOFT initial 改 0.40。
2. hedge.py 加 gamma_fraction、rebalance_deadband、soft_ratio 纯函数和单测。
3. hedge_risk.py 删除或中性化旧 DERIBIT dry hedge_intent。
4. strategy._evaluate_hedge 改 full_target 为 raw 100% net option delta，并附加 gamma_fraction diagnostic。
5. strategy._hedge_policy_plan 接入 SOFT max(base,gamma)、CRASH override、target band、reduce min-hold、final3 SOFT suppression。
6. display.py 只增 policy_detail 字段展示，不添加命令提示。
7. 清理经 grep 确认无 active 引用的旧 hedge 死代码；无法证明无用则保留但不扩展。
8. 更新 tests；旧 v3.1.4 hedge policy tests 必须继续覆盖 single-flight/read-as-truth/pending/late-fill/orphan/reverse。
9. run_all.py、build_bundle.py --check、py_compile 全通过后生成 v3.2.0 artifacts 和 handoff。
```

---

## 12. 决策备注

v3.2 的目标不是让对冲“收益最大”，而是让它在互相冲突的路径族里不过度失真：

- trend / jump / crash 中要有 full hedge 能力；
- whipsaw / high-IV-low-RV 中要减少虚惊和 churn；
- final 3h 不要因临交割 gamma 噪音频繁新开 SOFT hedge；
- 小额 live-test 不能被 0.001 BTC granularity 磨损；
- 所有执行正确性仍来自 read-as-truth，而不是订单历史推断。

因此，**v3.2 最优的工程答案不是新系统，而是在 v3.1.4 正确控制器上加入 gamma-aware ratio、band、min-hold、final3 suppress 和 crash override。**
