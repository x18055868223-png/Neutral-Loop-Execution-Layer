# -*- coding: utf-8 -*-
"""BTC-PERPETUAL 对冲生命周期（hedge_*）。纯函数，便于单测。

对冲场所由操作者显式配置：
  - 默认 BINANCE BTCUSDC 永续（线性），Deribit BTC-PERPETUAL 仅作兼容；
  - 风险触发对冲使用 PROMPT_LIMIT，不由场所 maker 偏好覆盖；
  - 目标数量随**剩余卖方期权敞口**变化；短腿归零 / 结构 CLOSED|SETTLED → 目标立即归零（不等保护腿）；
  - **HEDGE_OPEN/INCREASE 非 reduce_only**（reduce_only 无法建仓）；HEDGE_REDUCE/UNWIND 强制 reduce_only；
  - 期权卖方风险消失但 perp 仍有持仓 → 孤儿对冲紧急态（持续 reduce_only 清理，会话不得 CLOSED）。
  - 换算：DERIBIT 反向(USD 合约)=delta_btc·spot/contract_size；BINANCE 线性(BTC)=delta_btc。
"""
HEDGE_INSTRUMENT = "BTC-PERPETUAL"
HEDGE_VENUE = "BINANCE"

VENUE_DERIBIT = "DERIBIT"
VENUE_BINANCE = "BINANCE"

_EPS = 1e-9


def hedge_venue_config(venue=None, binance_instrument="BTCUSDC", exchange_index=1):
    """返回场所配置 {venue, instrument, linear, exchange_index?}。
    对冲执行方式由 exec_hedge_step 的 execution_style 决定，不在场所配置里夹 maker-only。"""
    if str(venue or VENUE_BINANCE).upper() == VENUE_BINANCE:
        return {"venue": VENUE_BINANCE, "instrument": binance_instrument,
                "linear": True, "exchange_index": exchange_index}
    return {"venue": VENUE_DERIBIT, "instrument": HEDGE_INSTRUMENT,
            "linear": False}


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def hedge_side(side):
    """SHORT_CALL 风险上升(delta 正) → BUY BTC-PERP；SHORT_PUT → SELL。"""
    s = str(side or "").upper()
    if s in ("CALL", "SHORT_CALL"):
        return "buy"
    if s in ("PUT", "SHORT_PUT"):
        return "sell"
    return None


def structure_net_delta(short_delta, protection_delta):
    """结构净 delta（每单位）= 短腿 delta − 保护腿 delta（P1）。
    短腿与保护腿同类型(同 call/put)、保护腿为多头 → 部分抵消短腿敞口，对冲应按净敞口而非仅短腿。
    保护腿 delta 缺失 → 退化为短腿 delta（保守：过对冲优于欠对冲）；短腿缺失 → None。"""
    if not _is_num(short_delta):
        return None
    if not _is_num(protection_delta):
        return short_delta
    return short_delta - protection_delta


def option_net_delta(remaining_short_qty, short_delta, long_remaining_qty=0.0,
                     protection_delta=None):
    """当前期权组合净 delta(BTC)：短腿卖出取负，保护腿买入取正。"""
    if not _is_num(short_delta):
        return None
    short_qty = remaining_short_qty or 0.0
    long_qty = long_remaining_qty or 0.0
    net = -short_qty * short_delta
    if _is_num(protection_delta):
        net += long_qty * protection_delta
    return net


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def hedge_gamma_fraction(short_gamma, long_gamma, remaining_short_qty,
                         long_remaining_qty, spot, ref, floor):
    """Gamma-aware SOFT hedge fraction.

    Missing gamma falls back to floor instead of zero; protection gamma offsets
    short gamma by current remaining leg quantities.
    """
    fl = _clamp(float(floor or 0.0), 0.0, 1.0)
    if not _is_num(spot) or spot <= 0 or not _is_num(ref) or ref <= 0:
        return fl
    combo_gamma = 0.0
    has_gamma = False
    if _is_num(short_gamma):
        combo_gamma += -(remaining_short_qty or 0.0) * short_gamma
        has_gamma = True
    if _is_num(long_gamma):
        combo_gamma += (long_remaining_qty or 0.0) * long_gamma
        has_gamma = True
    if not has_gamma:
        return fl
    dollar_gamma = abs(combo_gamma) * spot * spot
    norm = _clamp(dollar_gamma / ref, 0.0, 1.0)
    return _clamp(fl + (1.0 - fl) * norm, fl, 1.0)


def hedge_rebalance_deadband(full_target, min_trade, band_frac):
    min_qty = max(0.0, min_trade or 0.0)
    frac = max(0.0, band_frac or 0.0)
    return max(min_qty, abs(full_target or 0.0) * frac)


def hedge_target_ratio_for_soft(base_ratio, gamma_fraction, persisted=False, worsened=False):
    if persisted or worsened:
        return 1.0
    base = _clamp(base_ratio or 0.0, 0.0, 1.0)
    gamma = _clamp(gamma_fraction or 0.0, 0.0, 1.0)
    return max(base, gamma)


def _round_abs_to_step(value, step):
    if not step or step <= 0:
        return value
    sign = -1.0 if value < 0 else 1.0
    units = abs(value) / step
    rounded_units = int(units + 0.5 + 1e-12)
    return sign * rounded_units * step


def hedge_target_position(net_option_delta, reduction_ratio, spot, contract_size,
                          min_trade_amount, linear=False):
    """把期权净 delta 转为目标 hedge 仓位（带方向）。
    线性 Binance：BTC 数量；反向 Deribit：USD 合约数。"""
    if not _is_num(net_option_delta):
        return 0.0
    target_delta = -net_option_delta * (reduction_ratio or 1.0)
    if linear:
        raw = target_delta
    else:
        if not (_is_num(spot) and _is_num(contract_size)) or contract_size <= 0:
            return 0.0
        raw = target_delta * spot / contract_size
    return _round_abs_to_step(raw, min_trade_amount)


def hedge_direction_consistent(side, struct_net_delta):
    """方向符号核对（P1）：卖方腿为空头 → 结构 position delta = −struct_net_delta。
    SHORT_CALL（应 buy）要求 position delta ≤ 0；SHORT_PUT（应 sell）要求 ≥ 0。
    数据缺失 / 净敞口≈0 / 无对冲方向 → True（缺 greeks 不阻断既有逻辑，仅用于挡反向加仓）。"""
    h = hedge_side(side)
    if h is None or not _is_num(struct_net_delta) or abs(struct_net_delta) <= _EPS:
        return True
    position_delta = -struct_net_delta
    if h == "buy":
        return position_delta <= _EPS
    return position_delta >= -_EPS


def hedge_target_contracts(remaining_short_qty, structure_delta, reduction_ratio,
                           spot, contract_size, min_trade_amount,
                           option_structure_state="OPEN", linear=False):
    """对冲目标数量。硬不变量：短腿归零 或 结构 CLOSED/SETTLED → 0（不等保护腿出售）。
    linear=False(Deribit 反向)：USD 合约 = |rem·delta·ratio|·spot / contract_size；
    linear=True (Binance 线性)：BTC 数量 = |rem·delta·ratio|。结果取整到 min_trade。"""
    if str(option_structure_state).upper() in ("CLOSED", "SETTLED"):
        return 0.0
    if not remaining_short_qty or remaining_short_qty <= _EPS:
        return 0.0
    if not _is_num(structure_delta):
        return 0.0
    delta_btc = abs(remaining_short_qty * structure_delta * (reduction_ratio or 1.0))
    if linear:
        raw = delta_btc
    else:
        if not (_is_num(spot) and _is_num(contract_size)) or contract_size <= 0:
            return 0.0
        raw = delta_btc * spot / contract_size
    if min_trade_amount and min_trade_amount > 0:
        return round(raw / min_trade_amount) * min_trade_amount
    return raw


def hedge_order_action(current_qty, target_qty, min_trade_amount=0.0):
    """据当前 vs 目标决定动作 + reduce_only（P0-5）。
    目标>当前 → HEDGE_OPEN/INCREASE(非 reduce_only)；目标<当前 → HEDGE_REDUCE/UNWIND(reduce_only)。"""
    cur = current_qty or 0.0
    tgt = target_qty or 0.0
    thr = max(_EPS, (min_trade_amount or 0.0) * 0.5)
    if abs(tgt - cur) <= thr:
        return {"action": "HEDGE_HOLD", "reduce_only": False, "delta_contracts": 0.0}
    if abs(cur) > thr and abs(tgt) > thr and cur * tgt < 0:
        return {"action": "HEDGE_UNWIND", "reduce_only": True,
                "delta_contracts": abs(cur)}
    if abs(tgt) <= thr:
        return {"action": "HEDGE_UNWIND", "reduce_only": True,
                "delta_contracts": abs(cur)}
    if abs(cur) <= thr:
        return {"action": "HEDGE_OPEN", "reduce_only": False,
                "delta_contracts": abs(tgt)}
    if abs(tgt) > abs(cur):
        return {"action": "HEDGE_INCREASE", "reduce_only": False,
                "delta_contracts": abs(tgt - cur)}
    return {"action": "HEDGE_REDUCE", "reduce_only": True,
            "delta_contracts": abs(tgt - cur)}


def hedge_orphan(option_short_qty, perp_qty):
    """期权卖方风险已消失(short<=0) 但 perp 仍有持仓 → 孤儿对冲（须 reduce_only 清理）。"""
    return (not option_short_qty or option_short_qty <= _EPS) and abs(perp_qty or 0.0) > _EPS


def settlement_guard(remaining_short_qty, near_expiry, settled, perp_qty):
    """到期/交割保护：已交割 → 目标强制 0（perp 未归零即孤儿）；临近到期 → 不新增、随剩余短腿归零。"""
    if settled:
        return {"target": 0.0, "orphan": abs(perp_qty or 0.0) > _EPS, "reason": "SETTLED_FORCE_ZERO"}
    if near_expiry:
        flat = (not remaining_short_qty or remaining_short_qty <= _EPS)
        return {"target": (0.0 if flat else None), "orphan": False,
                "reason": "NEAR_EXPIRY_NO_NEW_HEDGE"}
    return {"target": None, "orphan": False, "reason": "NORMAL"}
