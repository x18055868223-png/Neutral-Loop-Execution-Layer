# -*- coding: utf-8 -*-
"""币安 USDC 永续对冲适配（bnc_*）：经 FMZ exchanges[idx] 下对冲腿。

线性合约(单位 BTC)；风险触发对冲使用 prompt-limit，reduce_only 用平仓方向。
仅对冲腿用，不参与期权 / 人工审计。FMZ 多所：exchanges[0]=Deribit(期权)，exchanges[idx]=Binance。

注：真实下单调用形态依 FMZ 币安期货接口（SetContractType/SetDirection/Buy/Sell），**须真实机器人确认**；
默认 `ALLOW_HEDGE_TRADING=False`；跨所对账/恢复需人工核对。
"""
from config import HEDGE_BINANCE_EXCHANGE_INDEX
from fmz_shim import exchanges, Log, Sleep


def _ex(idx):
    try:
        return exchanges[HEDGE_BINANCE_EXCHANGE_INDEX if idx is None else idx]
    except Exception:
        return None


def bnc_get_position_btc(symbol, idx=None):
    """读 BTCUSDC 永续净持仓(BTC；正=多 / 负=空)。读失败 → None。"""
    ex = _ex(idx)
    if ex is None:
        return None
    try:
        ex.SetContractType(symbol)
        net = 0.0
        for p in (ex.GetPosition() or []):
            amt = p.get("Amount") or 0.0
            long_side = p.get("Type") in (0, "buy", "long", "Long")
            net += amt if long_side else -amt
        return net
    except Exception as e:
        Log("[binance] GetPosition 异常:", str(e))
        return None


def _order_id(resp):
    if isinstance(resp, dict):
        return resp.get("id") or resp.get("Id") or resp.get("order_id") or resp.get("OrderId")
    return resp


def _filled_amount(order):
    if not isinstance(order, dict):
        return 0.0
    for k in ("DealAmount", "deal_amount", "filled_amount", "filled", "Filled"):
        v = order.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return 0.0


def _avg_price(order, fallback):
    if not isinstance(order, dict):
        return fallback
    for k in ("AvgPrice", "avg_price", "average_price", "Price", "price"):
        v = order.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            return float(v)
    return fallback


def _prompt_limit_price(ticker, side, max_slippage_bps):
    bid = ticker.get("Buy") or ticker.get("best_bid") or ticker.get("Bid")
    ask = ticker.get("Sell") or ticker.get("best_ask") or ticker.get("Ask")
    bps = (max_slippage_bps or 0) / 10000.0
    if side == "buy":
        return None if not ask or ask <= 0 else ask * (1.0 + bps)
    return None if not bid or bid <= 0 else bid * (1.0 - bps)


def _get_order(ex, oid):
    fn = getattr(ex, "GetOrder", None)
    if not fn or oid is None:
        return None
    return fn(oid)


def _cancel_order(ex, oid):
    fn = getattr(ex, "CancelOrder", None)
    if not fn or oid is None:
        return False
    return bool(fn(oid))


def _missing_methods(ex, names):
    return [name for name in names if not callable(getattr(ex, name, None))]


def bnc_place_hedge(symbol, side, amount, reduce_only, allow_live=True, idx=None,
                    execution_style="PROMPT_LIMIT", max_slippage_bps=5):
    """下币安对冲腿。PROMPT_LIMIT 用盘口限价保护但不 post-only；reduce_only→平仓方向。
    allow_live=False → 仅意图(dry)，不下单。"""
    if not side or not amount or amount <= 0:
        return {"filled": 0.0, "dry": (not allow_live), "venue": "BINANCE", "reason": "NO_OP"}
    if not allow_live:
        return {"filled": 0.0, "dry": True, "venue": "BINANCE", "symbol": symbol, "side": side,
                "amount": amount, "reduce_only": reduce_only, "post_only": False,
                "execution_style": execution_style,
                "reason": "BINANCE_HEDGE_DRYRUN"}
    ex = _ex(idx)
    if ex is None:
        return {"filled": 0.0, "dry": False, "venue": "BINANCE", "reason": "BINANCE_EXCHANGE_UNAVAILABLE"}
    missing = _missing_methods(
        ex, ("SetContractType", "GetTicker", "SetDirection", "Buy", "Sell", "GetOrder", "CancelOrder"))
    if missing:
        return {"filled": 0.0, "dry": False, "venue": "BINANCE",
                "reason": "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED",
                "blocked": True, "missing_methods": missing}
    try:
        ex.SetContractType(symbol)
        t = ex.GetTicker() or {}
        price = _prompt_limit_price(t, side, max_slippage_bps)
        if price is None or price <= 0:
            return {"filled": 0.0, "dry": False, "venue": "BINANCE",
                    "reduce_only": reduce_only, "post_only": False,
                    "execution_style": execution_style, "reason": "NO_QUOTE"}
        direction = ("closesell" if side == "buy" else "closebuy") if reduce_only else side
        ex.SetDirection(direction)
        resp = ex.Buy(price, amount) if side == "buy" else ex.Sell(price, amount)
        oid = _order_id(resp)
        Sleep(1000)
        st = _get_order(ex, oid) or {}
        filled = _filled_amount(st)
        avg = _avg_price(st, price)
        remaining = max(0.0, amount - filled)
        cancelled = False
        if remaining > 1e-12:
            cancelled = _cancel_order(ex, oid)
            st2 = _get_order(ex, oid) or st
            filled2 = _filled_amount(st2)
            if filled2 > filled:
                filled = filled2
                avg = _avg_price(st2, avg)
            remaining = max(0.0, amount - filled)
        return {"filled": filled, "avg_price": avg, "remaining": remaining,
                "cancelled": cancelled, "dry": False, "venue": "BINANCE",
                "symbol": symbol, "side": side, "amount": amount, "price": price,
                "order_id": oid, "order": resp, "reduce_only": reduce_only,
                "post_only": False, "execution_style": execution_style,
                "reason": "BINANCE_HEDGE_STEP"}
    except Exception as e:
        Log("[binance] 下单异常:", str(e))
        return {"filled": 0.0, "dry": False, "venue": "BINANCE", "reason": "BINANCE_ORDER_ERROR"}
