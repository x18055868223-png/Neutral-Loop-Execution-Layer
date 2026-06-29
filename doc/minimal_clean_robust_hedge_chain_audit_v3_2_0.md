# v3.2.0 对冲模块最小可用干净健壮链路审计与调整方案

**审计对象:** `spm_manual_gate_execution_fmz_v3_2_0.py`  
**审计口径:** 只以“最小可用、干净、健壮”的对冲链路为目标，不追求完整理论 BEST，不引入过度工程化。  
**结论:** 当前 v3.2.0 的核心对冲链路已经接近可用，但还不能称为“最小干净健壮”。需要做一轮**收束型调整**：修复两个安全边界、清理误导性配置、统一 V32 命名、压缩执行分支，并把未实现的 maker-first reduce 从当前交付面移除或强制关闭。

---

## 1. 最小可用链路的定义

这里的“最小可用”不是“功能最少”，而是指对实盘最重要的风险闭环必须明确、单一、可解释、可测试。

最小可用对冲链路只需要保留以下能力：

```text
1. 只在持仓管理阶段运行；
2. 只读现有期权快照、短腿行情、Binance BTCUSDC 当前仓位；
3. 读不到 Binance 仓位或目标数据时 fail-closed；
4. 先处理 pending hedge order，未清 pending 不发第二单；
5. 以交易所当前 hedge 仓位为唯一真值；
6. 根据风险状态生成 full_target；
7. 根据 SOFT / HARD / CRASH 生成 eff_target；
8. 只按 eff_target - current 下单；
9. 普通 add 非 reduce_only，reduce / orphan / reverse unwind 必须 reduce_only；
10. 每轮最多一个 hedge 动作；
11. 所有执行结果进入 pending-first 下一轮对账；
12. POSITION_MANAGE 只读展示，不新增运行时 hedge 指令。
```

不属于最小链路的内容：

```text
- maker-first reduce；
- ES optimizer；
- ML / RL；
- 多交易所 hedge fallback；
- native conditional order；
- 复杂 vol-speed AND filter；
- 运行时人工 hedge command；
- 任何把缺失 position / depth / PnL 当 0 的 fallback。
```

---

## 2. 当前 v3.2.0 的保留项

以下实现应保留，不建议推翻。

### 2.1 V313/V32 reconciliation 骨架

当前 `_hedge_policy_plan()` 的主结构是正确的：

```text
pending-first
→ read current Binance position
→ data gap fail-closed
→ orphan / reverse unwind
→ HARD / CRASH full target
→ SOFT staged target
→ no-trade band
→ cooldown / min-hold
→ one order submit
```

这条主链是当前对冲模块最值得复用的部分。不要重写成事件驱动，也不要把订单历史当仓位真值。

### 2.2 Gamma-aware sizing

当前 v3.2.0 的 `hedge_gamma_fraction()`、`hedge_target_ratio_for_soft()` 属于低复杂度、高收益的纯函数逻辑。它能让 SOFT 初始对冲不再固定死 50%，而是根据组合 gamma 变化自动放大或收缩。

建议保留，但要把注释说清楚：

```text
gamma-aware 开启时：
full_target = raw full delta hedge target
SOFT 阶段才按 gamma_fraction / soft ratio 缩放为 eff_target
HEDGE_REDUCTION_RATIO 不再决定 full_target
```

### 2.3 No-trade band

当前 `hedge_rebalance_deadband(full_target, min_trade, band_frac)` 是必要的，建议保留。

推荐最小默认值：

```python
HEDGE_REBALANCE_BAND_FRAC = 0.20
```

它避免 0.0003、0.0005 BTC 这种无意义残差反复下单。

### 2.4 Min-hold

当前普通 reduce 受 `HEDGE_MIN_HOLD_SECONDS` 限制，这是抗 whipsaw 的关键。建议保留。

推荐最小默认值：

```python
HEDGE_MIN_HOLD_SECONDS = 720  # 12 min
```

orphan / reverse / short-flat unwind 不受 min-hold 阻断。

### 2.5 Final 3h suppress SOFT add

当前最后 3 小时只压制 SOFT 新增，不压制 HARD / CRASH / reduce / orphan unwind。这个边界正确，建议保留。

推荐默认：

```python
HEDGE_FINAL3H_MODE = "SUPPRESS_SOFT_ADD"
```

### 2.6 CRASH override

当前 `HEDGE_CRASH_ENABLED` + adverse move bps 机制可保留。它是对概率模型滞后的低复杂度补丁。

推荐默认：

```python
HEDGE_CRASH_ENABLED = True
HEDGE_CRASH_SPEED_WINDOW_SECONDS = 600
HEDGE_CRASH_MOVE_BPS = 110
```

---

## 3. 必须调整的 P0 项

P0 是“达不到就不应声称最小干净健壮”的项目。

---

### P0-1：修复 Binance `GetPosition()` 返回 None 被误当作空仓的问题

当前逻辑：

```python
positions = list(ex.GetPosition() or [])
```

这会把两种情况混在一起：

```text
GetPosition() == []     → 真实无仓位，可以视为 0
GetPosition() == None   → 读取失败，必须 fail-closed
```

当前写法会把 `None` 变成 `[]`，最终返回 `qty = 0.0`。这违反了“不得把 Binance position 缺失当 0”的硬边界。

#### 必须改成

```python
raw_positions = ex.GetPosition()
if raw_positions is None:
    return None
positions = list(raw_positions or [])
```

更稳健的版本：

```python
def bnc_get_position_snapshot(symbol, idx=None):
    ex = _ex(idx)
    if ex is None:
        return None
    try:
        pair, contract_type = _select_binance_perp(ex, symbol)
        raw_positions = ex.GetPosition()
        if raw_positions is None:
            Log("[binance] GetPosition 返回 None，按数据缺口处理")
            return None

        net = 0.0
        pnl = 0.0
        pnl_seen = False
        for p in list(raw_positions or []):
            amt = p.get("Amount") or 0.0
            long_side = p.get("Type") in (0, "buy", "long", "Long")
            net += amt if long_side else -amt
            pp = _position_unrealized_pnl(p)
            if pp is not None:
                pnl += pp
                pnl_seen = True

        return {
            "qty": net,
            "unrealized_pnl_usd": pnl if pnl_seen else None,
            "positions": list(raw_positions or []),
            "pair": pair,
            "contract_type": contract_type,
        }
    except Exception as e:
        Log("[binance] GetPosition 异常:", str(e))
        return None
```

#### 验收测试

```python
def test_binance_position_none_is_data_gap_not_zero():
    fake.GetPosition = lambda: None
    assert bnc_get_position_snapshot("BTCUSDC") is None
    assert bnc_get_position_btc("BTCUSDC") is None
```

---

### P0-2：提交 hedge order 前必须确认订单生命周期方法可用

当前 `bnc_submit_hedge_order()` 只检查：

```python
("SetContractType", "GetTicker", "SetDirection", "Buy", "Sell")
```

但 V32 reconciliation controller 提交后依赖：

```text
GetOrder
CancelOrder
```

来做 pending-first、partial fill、stale recovery。

如果交易所对象不支持 `GetOrder` / `CancelOrder`，当前逻辑仍可能提交订单，然后下一轮无法可靠 resolve pending。这会破坏 single-flight 的核心安全性。

#### 必须改成

```python
missing = _missing_methods(
    ex,
    ("SetContractType", "GetTicker", "SetDirection", "Buy", "Sell", "GetOrder", "CancelOrder")
)
if missing:
    return {
        "order_id": None,
        "filled": 0.0,
        "dry": False,
        "venue": "BINANCE",
        "reason": "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED",
        "blocked": True,
        "missing_methods": missing,
    }
```

#### 验收测试

```python
def test_v32_submit_blocks_without_order_lifecycle_methods():
    fake_exchange_has_no_get_order_cancel_order()
    r = bnc_submit_hedge_order("BTCUSDC", "sell", 0.01, False, allow_live=True)
    assert r["reason"] == "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED"
    assert r["blocked"] is True
    assert r["order_id"] is None
```

---

### P0-3：提交返回缺少 `order_id` 时不能静默继续

当前 `_hedge_policy_submit()` 只有在 `oid` 存在时才写 pending：

```python
oid = (result or {}).get("order_id")
if oid:
    st["pending_order_id"] = oid
```

如果 live submit 已经发出，但返回结构里没有 order id，系统下一轮没有 pending 保护，可能重复下单。这个情况虽然不一定常见，但在最小健壮链路里必须显式处理。

#### 推荐最小处理

`bnc_submit_hedge_order()` 如果 live 下单响应中没有 order id，应返回明确阻断原因：

```python
oid = _order_id(resp)
if oid is None:
    return {
        "order_id": None,
        "filled": 0.0,
        "dry": False,
        "venue": "BINANCE",
        "symbol": symbol,
        "side": side,
        "amount": amount,
        "price": price,
        "order": resp,
        "reduce_only": reduce_only,
        "reason": "BINANCE_ORDER_ID_MISSING",
        "blocked": True,
    }
```

`_hedge_policy_submit()` 收到这个结果后应记录一次 submit uncertainty 状态，至少本轮不再继续动作，并在下一轮 read-as-truth 后恢复。

最小状态字段：

```python
"last_submit_unknown_ts": 0,
"last_submit_unknown_reason": None,
```

最小门控：

```python
if result.get("reason") == "BINANCE_ORDER_ID_MISSING":
    st["last_submit_unknown_ts"] = now_ms
    st["last_submit_unknown_reason"] = "BINANCE_ORDER_ID_MISSING"
    _hedge_policy_save_state(st)
    return result
```

可选更保守：在 `last_submit_unknown_ts` 后 1 个 pending stale window 内不再提交新 hedge，只读仓位。

#### 验收测试

```python
def test_submit_without_order_id_sets_unknown_submit_guard():
    bnc_submit_hedge_order_returns_order_without_id()
    r = _hedge_policy_submit(hedge, now_ms, allow_live=True)
    st = _hedge_policy_state(snap)
    assert r["reason"] == "BINANCE_ORDER_ID_MISSING"
    assert st["last_submit_unknown_reason"] == "BINANCE_ORDER_ID_MISSING"
```

---

### P0-4：统一 V32 开关与状态 key，消除 V313/V32 混名

当前版本的 policy detail 已经写 `V32`，但开关仍是：

```python
HEDGE_POLICY_V313_ENABLED = True
```

状态 key 仍是：

```python
_HEDGE_POLICY_STATE_KEY = "spm_hedge_policy_v313_state"
```

这不是运行 bug，但会严重干扰审计、日志定位和 Codex 后续维护。

#### 最小改法

新增 V32 正式开关：

```python
HEDGE_POLICY_V32_ENABLED = True
```

为了兼容旧配置，可以保留 alias，但不要暴露给操作者：

```python
try:
    HEDGE_POLICY_V32_ENABLED
except NameError:
    HEDGE_POLICY_V32_ENABLED = HEDGE_POLICY_V313_ENABLED
```

修改：

```python
def _hedge_policy_enabled_for(hedge):
    return bool(HEDGE_POLICY_V32_ENABLED and (hedge or {}).get("venue") == "BINANCE")
```

状态 key 改成：

```python
_HEDGE_POLICY_STATE_KEY = "spm_hedge_policy_v32_state"
```

如果担心升级后丢失旧 pending 状态，可以做一次迁移：

```python
_HEDGE_POLICY_STATE_KEY_V313 = "spm_hedge_policy_v313_state"
_HEDGE_POLICY_STATE_KEY = "spm_hedge_policy_v32_state"

def _hedge_policy_load_state_raw():
    st = _G(_HEDGE_POLICY_STATE_KEY)
    if not isinstance(st, dict):
        old = _G(_HEDGE_POLICY_STATE_KEY_V313)
        if isinstance(old, dict):
            old = dict(old)
            old["policy"] = "V32"
            _G(_HEDGE_POLICY_STATE_KEY, old)
            _G(_HEDGE_POLICY_STATE_KEY_V313, None)
            return old
    return st
```

#### 验收测试

```python
def test_v32_state_key_migrates_from_v313_once():
    _G("spm_hedge_policy_v313_state", {"policy": "V313", "pending_order_id": "x"})
    st = _hedge_policy_state(snap)
    assert st["policy"] == "V32"
    assert st["pending_order_id"] == "x"
    assert _G("spm_hedge_policy_v313_state") is None
```

---

## 4. P1：清理配置面，避免“看起来能用但实际没用”

P1 是干净度要求，不一定影响当前交易安全，但会影响后续维护和操作者判断。

---

### P1-1：删除或隐藏未接入的配置项

当前配置中存在以下未真正接入核心执行路径的开关或参数：

```python
HEDGE_SLIPPAGE_GUARD_ENABLED
HEDGE_LOSS_BOUNDARY_BUFFER_SIGMA
HEDGE_SLIP_ALERT_BPS
HEDGE_MAKER_FIRST_REDUCE_ENABLED
```

#### 建议

最小可用版本中直接删除：

```python
HEDGE_SLIPPAGE_GUARD_ENABLED
HEDGE_LOSS_BOUNDARY_BUFFER_SIGMA
HEDGE_SLIP_ALERT_BPS
HEDGE_MAKER_FIRST_REDUCE_ENABLED
```

如果暂时不删，则必须在 `validate_config()` 中强制：

```python
if HEDGE_MAKER_FIRST_REDUCE_ENABLED is not False:
    errs.append("HEDGE_MAKER_FIRST_REDUCE_ENABLED is not implemented in minimal V32; must be False")
```

并从操作者可编辑清单中移除。

#### 原因

`HEDGE_MAKER_FIRST_REDUCE_ENABLED = False` 当前只是配置项，不接入 `_hedge_policy_submit()`。保留它会让人以为打开后就能 maker-first reduce，但实际仍走 prompt-limit。这是最典型的“脏配置面”。

---

### P1-2：收敛对冲场所，只保留 Binance BTCUSDC

最小可用对冲链路建议只保留：

```python
HEDGE_VENUE = "BINANCE"
HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"
```

当前仍保留 Deribit BTC-PERPETUAL hedge branch，包括：

```text
hedge_venue_config("DERIBIT")
_evaluate_hedge() 中的 Deribit branch
exec_hedge_step() 中的 Deribit hedge order path
HEDGE_CONTRACT_SIZE_FALLBACK
HEDGE_MIN_TRADE_FALLBACK
```

如果当前实盘工作流只使用 Binance BTCUSDC，那么 Deribit perp hedge branch 对最小链路没有价值，只会增加测试面和误用风险。

#### 推荐做法

短期最小改法：配置校验只允许 Binance。

```python
if HEDGE_VENUE != "BINANCE":
    errs.append("Minimal V32 hedge supports BINANCE only")
```

中期清理：删除 Deribit hedge branch，但不要动 Deribit option entry / exit / quote 逻辑。

---

### P1-3：处理 `HEDGE_REDUCTION_RATIO` 的误导性

当前配置仍写：

```python
HEDGE_REDUCTION_RATIO = 0.5
```

但 gamma-aware 开启时，`_evaluate_hedge()` 实际用：

```python
target_ratio = 1.0 if HEDGE_GAMMA_AWARE_ENABLED else HEDGE_REDUCTION_RATIO
```

这意味着在默认 v3.2.0 下，`HEDGE_REDUCTION_RATIO` 不再决定 full target。它只用于 entry risk anchor 里的 trigger policy 参数，以及 gamma-aware 关闭后的 legacy sizing。

#### 最小改法

把注释改成：

```python
HEDGE_REDUCTION_RATIO = 0.5
# 仅在 HEDGE_GAMMA_AWARE_ENABLED=False 时作为 legacy full target ratio。
# V32 gamma-aware 默认 full_target 使用 RAW_FULL_DELTA，SOFT 再按 gamma_fraction 缩放 eff_target。
```

更干净的做法：

```python
HEDGE_LEGACY_REDUCTION_RATIO = 0.5
HEDGE_RAW_FULL_DELTA_TARGET_RATIO = 1.0
```

但这会多改一点测试。最小版本只改注释即可。

---

### P1-4：删除旧的立即成交式 hedge 路径，避免双语义

当前文件同时存在：

```text
bnc_submit_hedge_order()   # V32 pending-first controller 使用
bnc_place_hedge()          # 旧式 submit-sleep-query-cancel 路径
exec_hedge_step()          # policy disabled 或 Deribit branch 使用
```

最小可用链路应只有一条 hedge submit path：

```text
_hedge_policy_plan()
→ _hedge_policy_submit()
→ bnc_submit_hedge_order()
→ pending-first resolve
```

#### 建议

若 `HEDGE_POLICY_V32_ENABLED=True` 为唯一生产路径，则：

1. 不再在生产分支调用 `exec_hedge_step()`；
2. `HEDGE_POLICY_V32_ENABLED=False` 不应回退到旧 hedge 下单，而应只关闭自动 hedge 或进入 dry/hold；
3. `bnc_place_hedge()` 标记为 legacy test helper，下一版删除。

最小修改：

```python
def _hedge_policy_enabled_for(hedge):
    return bool(HEDGE_POLICY_V32_ENABLED and (hedge or {}).get("venue") == "BINANCE")
```

然后在 `manage_cycle()` 中，如果 policy disabled：

```python
else:
    hedge_step = {"filled": 0.0, "dry": False, "venue": hedge.get("venue"),
                  "reason": "HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT"}
```

这比回退旧式 prompt-limit 更干净。真的要停自动对冲，应该用 `ALLOW_HEDGE_TRADING=False` 或 `HEDGE_POLICY_V32_ENABLED=False`，而不是悄悄走另一套旧逻辑。

---

## 5. P2：参数收敛建议

P2 不是 bug，是为了让最小链路更稳定。

### 5.1 SOFT escalation persistence 建议调长

当前：

```python
HEDGE_SOFT_PERSIST_SECONDS = 20
```

它只决定 SOFT 从初始比例升级到 full，不决定首次 SOFT 是否下单。20 秒偏快，容易让普通 SOFT 在短时间里从 40% 升到 full。

最小稳健建议：

```python
HEDGE_SOFT_PERSIST_SECONDS = 60
```

更接近模拟 BEST 的保守值：

```python
HEDGE_SOFT_PERSIST_SECONDS = 120
```

不建议一开始直接设 480 秒，因为当前 SOFT 初始仓已经只有 40% + gamma fraction，过慢升级可能错过趋势行情。

### 5.2 Reduce persistence 可以保持 20 秒

当前：

```python
HEDGE_REDUCE_PERSIST_SECONDS = 20
HEDGE_MIN_HOLD_SECONDS = 720
```

普通 reduce 还有 min-hold 保护，因此 reduce persistence 不必过长。保持 20 秒可接受。

### 5.3 Crash ref warm-up 不做复杂化

当前 CRASH 需要先有窗口参考价，刚启动第一轮不会触发 CRASH。这不是 P0，因为 HARD probability / boundary 仍会兜底。

最小版本不建议加复杂 warm-up。只需在状态栏显示：

```text
crash_ref_price
crash_ref_age
last_crash_adverse_bps
```

让实盘日志验证是否足够。

---

## 6. 最小目标配置面

整理后，操作者真正需要看到的对冲配置只应是：

```python
# ---- Hedge venue ----
HEDGE_VENUE = "BINANCE"
HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"
HEDGE_BINANCE_MIN_TRADE = 0.001
HEDGE_BINANCE_PRICE_TICK = 0.1
HEDGE_BINANCE_EXCHANGE_INDEX = 1

# ---- V32 hedge policy ----
HEDGE_POLICY_V32_ENABLED = True
HEDGE_STAGING_ENABLED = True
HEDGE_HYSTERESIS_ENABLED = True
HEDGE_COOLDOWN_ENABLED = True

# ---- Sizing ----
HEDGE_GAMMA_AWARE_ENABLED = True
HEDGE_SOFT_INITIAL_RATIO = 0.40
HEDGE_GAMMA_FRAC_FLOOR = 0.30
HEDGE_GAMMA_NORM_REF = 1_000_000.0
HEDGE_REBALANCE_BAND_FRAC = 0.20

# ---- Trigger / execution ----
HEDGE_HARD_DRIFT = 0.35
HEDGE_HARD_CROSS_BPS = 30
HEDGE_SOFT_CROSS_BPS = 3

# ---- Hold / reduce ----
HEDGE_MIN_HOLD_SECONDS = 720
HEDGE_SOFT_PERSIST_SECONDS = 60
HEDGE_REDUCE_PERSIST_SECONDS = 20
HEDGE_REDUCE_PROB_BUFFER = 0.05
HEDGE_ADD_COOLDOWN_SECONDS = 30
HEDGE_REDUCE_COOLDOWN_SECONDS = 60

# ---- Final 3h / crash ----
HEDGE_FINAL3H_MODE = "SUPPRESS_SOFT_ADD"
HEDGE_CRASH_ENABLED = True
HEDGE_CRASH_SPEED_WINDOW_SECONDS = 600
HEDGE_CRASH_MOVE_BPS = 110

# ---- Pending ----
HEDGE_PENDING_STALE_SECONDS = 10

# ---- Observability only ----
HEDGE_EPISODE_COST_ALERT_BPS = 20
```

不出现在最小配置面的内容：

```python
HEDGE_MAKER_FIRST_REDUCE_ENABLED
HEDGE_SLIPPAGE_GUARD_ENABLED
HEDGE_LOSS_BOUNDARY_BUFFER_SIGMA
HEDGE_SLIP_ALERT_BPS
HEDGE_CONTRACT_SIZE_FALLBACK
HEDGE_MIN_TRADE_FALLBACK
```

---

## 7. Codex 落地流程

### Step 1：修 P0-1，Binance 持仓读取缺口

文件区域：

```text
binance_io.bnc_get_position_snapshot
```

改动：

```text
GetPosition() 返回 None → return None
GetPosition() 返回 [] → qty=0.0
```

测试：

```text
test_binance_position_none_is_data_gap_not_zero
test_binance_position_empty_list_is_flat_zero
```

---

### Step 2：修 P0-2，提交前检查完整生命周期方法

文件区域：

```text
binance_io.bnc_submit_hedge_order
```

改动：

```text
必须要求 GetOrder / CancelOrder 存在
否则 BINANCE_ORDER_LIFECYCLE_UNSUPPORTED
```

测试：

```text
test_v32_submit_blocks_without_order_lifecycle_methods
```

---

### Step 3：修 P0-3，submit 无 order_id 的保护

文件区域：

```text
binance_io.bnc_submit_hedge_order
strategy._hedge_policy_submit
strategy._hedge_policy_default_state
```

改动：

```text
live submit response 无 order id → 返回 BINANCE_ORDER_ID_MISSING
strategy 记录 last_submit_unknown_ts / reason
下一轮至少先 read-as-truth，不允许同一轮重复 submit
```

测试：

```text
test_submit_without_order_id_sets_unknown_submit_guard
test_unknown_submit_guard_prevents_immediate_duplicate
```

---

### Step 4：修 P0-4，V32 命名收束

文件区域：

```text
config
strategy._HEDGE_POLICY_STATE_KEY
strategy._hedge_policy_enabled_for
strategy._hedge_policy_default_state
tests
```

改动：

```text
HEDGE_POLICY_V32_ENABLED 新增为正式开关
HEDGE_POLICY_V313_ENABLED 只作为兼容 alias 或删除
state key 改为 spm_hedge_policy_v32_state
必要时迁移旧 state
```

测试：

```text
test_v32_state_key_migrates_from_v313_once
test_v32_enabled_switch_controls_policy
```

---

### Step 5：清理 P1 配置面

文件区域：

```text
config
validate_config
display risk hedge table
tests
CHATGPT handoff / README
```

改动：

```text
删除或隐藏 dead config
如果保留 maker-first reduce config，则 validate_config 强制 False
```

测试：

```text
test_minimal_config_has_no_dead_hedge_switches
test_maker_first_reduce_true_is_rejected_if_not_implemented
```

---

### Step 6：收敛 legacy hedge submit path

文件区域：

```text
strategy.manage_cycle
execution.exec_hedge_step
binance_io.bnc_place_hedge
hedge.hedge_venue_config
```

最小做法：

```text
生产只允许 V32 controller path
policy disabled 时不回退旧式 hedge submit
Deribit hedge venue 在 validate_config 中拒绝
```

测试：

```text
test_policy_disabled_does_not_use_legacy_hedge_submit
test_minimal_v32_rejects_deribit_hedge_venue
```

---

### Step 7：更新文档与验收命令

必须更新：

```text
README.md
CHATGPT5.5_PRO.md
doc/CODEX_HANDOFF_v3_2_1.md
CHECKSUMS.txt
```

命令：

```powershell
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\tests\run_all.py
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe realsrc\build_bundle.py --check
C:\Users\Xu\AppData\Local\Programs\Python\Python312\python.exe -m py_compile artifacts\最新交付\spm_manual_gate_execution_fmz_v3_2_1.py
```

---

## 8. 最小验收测试矩阵

### 8.1 安全读取

| 测试 | 预期 |
|---|---|
| Binance `GetPosition() is None` | `bnc_get_position_snapshot() is None`，不当 0 |
| Binance `GetPosition() == []` | qty = 0.0 |
| Binance position snapshot 缺 PnL | qty 可用，PnL 显示数据缺口，不当 0 |
| `_evaluate_hedge()` 收到 position data gap | `HEDGE_HOLD / POSITION_READ_FAILED` |

### 8.2 Pending / submit

| 测试 | 预期 |
|---|---|
| pending active | 不新发单 |
| pending partial active | 保留 pending，不二次 submit |
| pending stale + cancel ok | 清 pending，下一轮再 read-as-truth |
| pending stale + cancel fail | hold，原因 `PENDING_STALE_CANCEL_FAILED` |
| submit 缺 GetOrder/CancelOrder | 不下单 |
| submit 无 order_id | 设置 unknown submit guard |

### 8.3 Target / action

| 测试 | 预期 |
|---|---|
| SOFT + low gamma | `eff = full * 0.40` |
| SOFT + high gamma | `eff = full * gamma_fraction` |
| SOFT persisted | `eff = full` |
| HARD | `eff = full` |
| CRASH | `eff = full` |
| final 3h SOFT add | hold，原因 `FINAL3H_SOFT_ADD_SUPPRESSED` |
| final 3h HARD/CRASH | 不被 suppress |
| current 与 target 差额小于 band | hold，原因 `TARGET_BAND_DEADBAND` |
| short flat + hedge exists | reduce_only unwind |
| reverse hedge | 先 reduce_only 到 0，不单笔翻转 |

### 8.4 Gate / cleanup

| 测试 | 预期 |
|---|---|
| `HEDGE_POLICY_V32_ENABLED=False` | 不走旧式自动 hedge submit |
| `HEDGE_VENUE="DERIBIT"` | validate_config 报错 |
| `HEDGE_MAKER_FIRST_REDUCE_ENABLED=True` 若保留 | validate_config 报错 |
| dead config 不在 operator list | 文档与 README 不展示 |

---

## 9. 不建议本轮做的事项

### 9.1 不做 maker-first reduce

虽然模拟里 maker-first reduce 有成本优势，但它会引入：

```text
maker order id
post-only reject
timeout
cancel + late fill
fallback taker
重启恢复
stale maker price
partial fill
与 pending-first controller 的嵌套生命周期
```

这些复杂度超出“最小可用”的范围。本轮应删除或强制关闭 `HEDGE_MAKER_FIRST_REDUCE_ENABLED`，不要半实现。

### 9.2 不做 ES optimizer

Expected shortfall sizing 需要更多行情假设和路径模型，不适合最小链路。

### 9.3 不做 vol-speed AND filter

模拟结果显示 vol-speed AND filter 可能错过真正尾部，不适合作为主门控。

### 9.4 不做 native conditional order

它会把触发状态放到交易所，增加重启恢复和条件单撤销复杂度，不符合当前机器人侧 reconciliation 风格。

---

## 10. 最终调整优先级

### 必须做

1. `GetPosition() is None` 不得当 0。
2. `bnc_submit_hedge_order()` 必须检查 `GetOrder / CancelOrder`。
3. live submit 无 `order_id` 必须显式进入 unknown-submit guard。
4. V32 开关、policy 名称、state key 统一。

### 应该做

5. 删除或隐藏未接入配置。
6. 生产对冲链路只保留 V32 controller path。
7. 最小版本只支持 Binance BTCUSDC hedge venue。
8. 注释修正 `HEDGE_REDUCTION_RATIO` 在 gamma-aware 下的真实含义。

### 可以做，但不急

9. SOFT escalation persistence 从 20s 调到 60s。
10. 在状态栏展示 crash ref price / age。
11. 把 `bnc_place_hedge()` 降级为测试 helper 或下一版删除。

---

## 11. 最终判断

如果只以“最小可用、干净、健壮”的标准审计，当前 v3.2.0 的核心控制器方向正确，但需要再做一轮收束。

最重要的不是继续加功能，而是把以下四件事做干净：

```text
1. 缺失数据绝不当 0；
2. 没有完整订单生命周期能力就不提交 hedge；
3. 提交结果不可追踪时不允许静默继续；
4. 配置面与实际执行面一致，未实现的功能不暴露。
```

完成这些后，v3.2.x 就可以称为一条最小可用的干净稳健对冲链路。maker-first reduce、ES optimizer、多交易所 hedge fallback 都应放到后续版本，而不是混进最小版本。
