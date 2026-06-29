# -*- coding: utf-8 -*-
"""币安 USDC 永续对冲适配（bnc_*）：经 FMZ exchanges[idx] 下对冲腿。

线性合约(单位 BTC)；风险触发对冲使用 prompt-limit，reduce_only 用平仓方向。
仅对冲腿用，不参与期权 / 人工审计。FMZ 多所：exchanges[0]=Deribit(期权)，exchanges[idx]=Binance。

注：真实下单调用形态依 FMZ 币安期货接口（SetContractType/SetDirection/Buy/Sell），**须真实机器人确认**；
默认 `ALLOW_HEDGE_TRADING=False`；跨所对账/恢复需人工核对。
"""
import math

from config import HEDGE_BINANCE_EXCHANGE_INDEX, HEDGE_BINANCE_PRICE_TICK
from fmz_shim import exchanges, Log

_BINANCE_PERP_CONTRACT_TYPE = "swap"


def _ex(idx):
    try:
        return exchanges[HEDGE_BINANCE_EXCHANGE_INDEX if idx is None else idx]
    except Exception:
        return None


def _binance_pair(symbol):
    raw = str(symbol or "BTCUSDC").strip().upper()
    if "." in raw:
        raw = raw.split(".", 1)[0]
    raw = raw.replace("-", "_").replace("/", "_")
    if "_" in raw:
        parts = [p for p in raw.split("_") if p]
        if len(parts) >= 2:
            return "%s_%s" % (parts[0], parts[1])
    for quote in ("USDC", "USDT", "USD"):
        if raw.endswith(quote) and len(raw) > len(quote):
            return "%s_%s" % (raw[:-len(quote)], quote)
    return raw


def _select_binance_perp(ex, symbol):
    pair = _binance_pair(symbol)
    io = getattr(ex, "IO", None)
    if callable(io):
        io("currency", pair)
    ex.SetContractType(_BINANCE_PERP_CONTRACT_TYPE)
    return pair, _BINANCE_PERP_CONTRACT_TYPE


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _position_unrealized_pnl(position):
    if not isinstance(position, dict):
        return None
    for key in ("Profit", "UnrealizedProfit", "unRealizedProfit",
                "unrealizedProfit", "unrealizedPnl", "unrealized_pnl_usd"):
        v = _num(position.get(key))
        if v is not None:
            return float(v)
    return None


def bnc_get_position_snapshot(symbol, idx=None):
    """读 BTCUSDC 永续快照；读失败 → None。qty 正=多 / 负=空。"""
    ex = _ex(idx)
    if ex is None:
        return None
    try:
        pair, contract_type = _select_binance_perp(ex, symbol)
        net = 0.0
        pnl = 0.0
        pnl_seen = False
        raw_positions = ex.GetPosition()
        if raw_positions is None:
            Log("[binance] GetPosition 返回 None，按数据缺口处理")
            return None
        positions = list(raw_positions or [])
        for p in positions:
            amt = p.get("Amount") or 0.0
            long_side = p.get("Type") in (0, "buy", "long", "Long")
            net += amt if long_side else -amt
            pp = _position_unrealized_pnl(p)
            if pp is not None:
                pnl += pp
                pnl_seen = True
        return {"qty": net, "unrealized_pnl_usd": pnl if pnl_seen else None,
                "positions": positions, "pair": pair, "contract_type": contract_type}
    except Exception as e:
        Log("[binance] GetPosition 异常:", str(e))
        return None


def bnc_get_position_btc(symbol, idx=None):
    """读 BTCUSDC 永续净持仓(BTC；正=多 / 负=空)。读失败 → None。"""
    snap = bnc_get_position_snapshot(symbol, idx)
    return None if snap is None else snap.get("qty")


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


def _tick_decimals(tick):
    s = ("%.12f" % tick).rstrip("0").rstrip(".")
    return len(s.split(".", 1)[1]) if "." in s else 0


def _round_prompt_price(price, side, tick=None):
    tick = HEDGE_BINANCE_PRICE_TICK if tick is None else tick
    if not tick or tick <= 0:
        return price
    if side == "buy":
        rounded = math.ceil((price / tick) - 1e-12) * tick
    else:
        rounded = math.floor((price / tick) + 1e-12) * tick
    return round(rounded, _tick_decimals(tick))


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


def bnc_get_hedge_order(symbol, order_id, idx=None):
    ex = _ex(idx)
    if ex is None or order_id is None:
        return None
    try:
        if callable(getattr(ex, "SetContractType", None)):
            _select_binance_perp(ex, symbol)
        return _get_order(ex, order_id)
    except Exception as e:
        Log("[binance] GetOrder 异常:", str(e))
        return None


def bnc_cancel_hedge_order(symbol, order_id, idx=None):
    ex = _ex(idx)
    if ex is None or order_id is None:
        return False
    try:
        if callable(getattr(ex, "SetContractType", None)):
            _select_binance_perp(ex, symbol)
        return _cancel_order(ex, order_id)
    except Exception as e:
        Log("[binance] CancelOrder 异常:", str(e))
        return False


def _missing_methods(ex, names):
    return [name for name in names if not callable(getattr(ex, name, None))]


def bnc_order_lifecycle_supported(symbol, idx=None):
    ex = _ex(idx)
    if ex is None:
        return {"ok": False, "reason": "BINANCE_EXCHANGE_UNAVAILABLE",
                "missing_methods": ["exchange"]}
    missing = _missing_methods(
        ex, ("SetContractType", "GetTicker", "SetDirection", "Buy", "Sell",
             "GetOrder", "CancelOrder"))
    return {"ok": not missing,
            "reason": None if not missing else "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED",
            "missing_methods": missing,
            "symbol": symbol}


def bnc_submit_hedge_order(symbol, side, amount, reduce_only, cross_bps=5,
                           allow_live=True, idx=None,
                           execution_style="PROMPT_LIMIT"):
    """Submit one Binance hedge order and leave lifecycle resolution to caller."""
    if not side or not amount or amount <= 0:
        return {"order_id": None, "filled": 0.0, "dry": (not allow_live),
                "venue": "BINANCE", "reason": "NO_OP"}
    if not allow_live:
        return {"order_id": None, "filled": 0.0, "dry": True, "venue": "BINANCE",
                "symbol": symbol, "side": side, "amount": amount,
                "reduce_only": reduce_only, "post_only": False,
                "execution_style": execution_style,
                "cross_bps": cross_bps, "reason": "BINANCE_HEDGE_DRYRUN"}
    ex = _ex(idx)
    if ex is None:
        return {"order_id": None, "filled": 0.0, "dry": False, "venue": "BINANCE",
                "reason": "BINANCE_EXCHANGE_UNAVAILABLE"}
    missing = _missing_methods(
        ex, ("SetContractType", "GetTicker", "SetDirection", "Buy", "Sell",
             "GetOrder", "CancelOrder"))
    if missing:
        return {"order_id": None, "filled": 0.0, "dry": False, "venue": "BINANCE",
                "reason": "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED",
                "blocked": True, "missing_methods": missing}
    try:
        pair, contract_type = _select_binance_perp(ex, symbol)
        t = ex.GetTicker() or {}
        raw_price = _prompt_limit_price(t, side, cross_bps)
        if raw_price is None or raw_price <= 0:
            return {"order_id": None, "filled": 0.0, "dry": False, "venue": "BINANCE",
                    "reduce_only": reduce_only, "post_only": False,
                    "execution_style": execution_style, "reason": "NO_QUOTE"}
        price = _round_prompt_price(raw_price, side, HEDGE_BINANCE_PRICE_TICK)
        direction = ("closesell" if side == "buy" else "closebuy") if reduce_only else side
        ex.SetDirection(direction)
        resp = ex.Buy(price, amount) if side == "buy" else ex.Sell(price, amount)
        oid = _order_id(resp)
        if oid is None:
            return {"order_id": None, "filled": 0.0, "dry": False, "venue": "BINANCE",
                    "symbol": symbol, "side": side, "amount": amount, "price": price,
                    "raw_price": raw_price, "price_tick": HEDGE_BINANCE_PRICE_TICK,
                    "order": resp, "reduce_only": reduce_only, "post_only": False,
                    "execution_style": execution_style, "cross_bps": cross_bps,
                    "pair": pair, "contract_type": contract_type,
                    "reason": "BINANCE_ORDER_ID_MISSING", "blocked": True}
        return {"order_id": oid, "filled": 0.0, "dry": False, "venue": "BINANCE",
                "symbol": symbol, "side": side, "amount": amount, "price": price,
                "raw_price": raw_price, "price_tick": HEDGE_BINANCE_PRICE_TICK,
                "order": resp, "reduce_only": reduce_only, "post_only": False,
                "execution_style": execution_style, "cross_bps": cross_bps,
                "pair": pair, "contract_type": contract_type,
                "reason": "BINANCE_HEDGE_SUBMITTED"}
    except Exception as e:
        Log("[binance] 下单异常:", str(e))
        return {"order_id": None, "filled": 0.0, "dry": False, "venue": "BINANCE",
                "reason": "BINANCE_ORDER_ERROR"}
