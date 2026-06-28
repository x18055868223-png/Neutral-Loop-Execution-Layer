# -*- coding: utf-8 -*-
"""
执行层（exec_*，§10）：保护腿优先、短腿 maker-only、末日保护腿受控 taker 兜底。

价格计算为纯函数（可单测）；下单/轮询/撤单走 dbt_*。
进场门控经 gates.gate_decision(ENTRY)：ALLOW_ENTRY_TRADING=False（或 KILL_NEW_RISK /
EMERGENCY_REDUCE_ONLY）时，进场真实下单短路为「记录意图」（空跑核对）。
"""

import math

from config import (RUN_PROFILE, ALLOW_ENTRY_TRADING, KILL_NEW_RISK, EMERGENCY_REDUCE_ONLY,
                    MAX_CHASE_STEPS, CHASE_WAIT_SECONDS, MAX_SPREAD_RATIO,
                    ENTRY_PROTECTION_TAKER_AFTER_SECONDS,
                    ENTRY_SHORT_ORDER_WAIT_SECONDS,
                    HEDGE_OPEN_EXECUTION_STYLE, HEDGE_MAX_SLIPPAGE_BPS,
                    effective_trading_gates)
from gates import gate_decision, ACTION_ENTRY
from deribit_io import (dbt_ticker, dbt_get_instrument, dbt_order_book, dbt_place_order,
                       dbt_get_order_state, dbt_cancel)
from binance_io import bnc_place_hedge
from accounting import (acct_option_fee_ccy, acct_mark_slippage,
                        acct_chase_cost, acct_spread_cost)
from position import entry_credit_capped_index, entry_net_credit
from fmz_shim import Log, Sleep


# ---------- 纯价格计算（§10.3）----------

def _round_to_tick(price, tick, mode):
    if not tick:
        return price
    n = price / tick
    # 加微小 epsilon 抵消浮点误差（如 0.0013-0.0001 落在 0.00119999…，floor 会误降一格）
    n = math.floor(n + 1e-9) if mode == "down" else math.ceil(n - 1e-9)
    return round(n * tick, 10)


def _float_or_none(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def exec_effective_tick(meta, price):
    tick = _float_or_none((meta or {}).get("tick_size")) or 0.0
    pval = _float_or_none(price)
    for st in ((meta or {}).get("tick_size_steps") or []):
        above = _float_or_none((st or {}).get("above_price"))
        step = _float_or_none((st or {}).get("tick_size"))
        if pval is not None and above is not None and step and pval >= above:
            tick = step
    return tick


def exec_round_order_price(side, price, meta, tick=None):
    eff_tick = exec_effective_tick(meta, price) or tick or 0.0
    mode = "down" if side == "buy" else "up"
    return _round_to_tick(price, eff_tick, mode)


def exec_buy_price(mark, best_ask, tick, step, meta=None):
    """买 protection：step0=min(mark,ask-tick)；每追一步 +tick，封顶 ask-tick。"""
    cap = best_ask - tick
    base = min(mark, cap)
    p = base + step * tick
    return exec_round_order_price("buy", min(p, cap), meta, tick)


def exec_sell_price(mark, best_bid, tick, step, meta=None):
    """卖 short：step0=max(mark,bid+tick)；每追一步 -tick，封底 bid+tick。"""
    floor_p = best_bid + tick
    base = max(mark, floor_p)
    p = base - step * tick
    return exec_round_order_price("sell", max(p, floor_p), meta, tick)


def exec_protection_maker_price(mark, best_bid, best_ask, tick, meta=None):
    """买保护腿：挂标记价；若 mark 触及卖一，则压到 ask-tick 保持 maker。"""
    cap = best_ask - tick if tick else best_ask
    return exec_round_order_price("buy", min(mark, cap), meta, tick)


def exec_price_for(side, mark, best_bid, best_ask, tick, step, meta=None):
    return (exec_buy_price(mark, best_ask, tick, step, meta) if side == "buy"
            else exec_sell_price(mark, best_bid, tick, step, meta))


# ---------- 行情快照 ----------

def exec_quote(instrument):
    """返回 {mark, best_bid, best_ask, tick} 或 None。"""
    t = dbt_ticker(instrument)
    meta = dbt_get_instrument(instrument)
    if not t or not meta:
        return None
    mark = t.get("mark_price")
    return {
        "mark": mark,
        "mark_iv": t.get("mark_iv"),
        "best_bid": t.get("best_bid_price"),
        "best_ask": t.get("best_ask_price"),
        "best_bid_amount": t.get("best_bid_amount"),
        "best_ask_amount": t.get("best_ask_amount"),
        "tick": exec_effective_tick(meta, mark),
        "meta": meta,
        "underlying": t.get("underlying_price"),
        "delta": (t.get("greeks") or {}).get("delta"),
        "gamma": (t.get("greeks") or {}).get("gamma"),
        "vega": (t.get("greeks") or {}).get("vega"),
    }


def exec_spread_ratio(q):
    """相对价差 (ask-bid)/mid；缺数据返回 None。"""
    if not q:
        return None
    bid, ask = q.get("best_bid"), q.get("best_ask")
    if bid is None or ask is None or bid <= 0 or ask <= 0:
        return None
    mid = (bid + ask) / 2.0
    return (ask - bid) / mid if mid > 0 else None


def exec_plan_prices(side, instrument, amount):
    """返回该腿的下单意图：计划价(含追价档)+盘口，供「将下达订单」意图表展示。"""
    q = exec_quote(instrument)
    if not q or q.get("best_bid") is None or q.get("best_ask") is None:
        return {"instrument": instrument, "side": side, "amount": amount, "prices": [], "quote": q}
    if side == "buy":
        prices = [exec_protection_maker_price(
            q["mark"], q["best_bid"], q["best_ask"], q["tick"], q.get("meta"))]
    else:
        prices = [exec_price_for(side, q["mark"], q["best_bid"], q["best_ask"], q["tick"], s, q.get("meta"))
                  for s in range(MAX_CHASE_STEPS + 1)]
    return {"instrument": instrument, "side": side, "amount": amount, "prices": prices,
            "mark": q.get("mark"), "best_bid": q.get("best_bid"), "best_ask": q.get("best_ask"),
            "spread_ratio": exec_spread_ratio(q)}


def _extract_order(resp):
    if not resp:
        return None
    return resp.get("order") if isinstance(resp, dict) and "order" in resp else resp


def _exec_num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _order_fee(order):
    if not isinstance(order, dict):
        return None
    for k in ("commission", "fee", "fees", "Fee", "Commission"):
        v = _exec_num(order.get(k))
        if v is not None:
            return float(v)
    return None


def _execution_detail(leg, side, instrument, amount, intended_price, final_price,
                      filled, avg_price, order_id, quote, cancelled=False,
                      remaining=None, order=None, taker=False):
    filled = filled or 0.0
    avg_price = avg_price if avg_price is not None else final_price
    q = quote or {}
    fee_actual = _order_fee(order)
    fee_est = acct_option_fee_ccy(avg_price or 0.0, filled) if filled > 0 else 0.0
    spread = acct_spread_cost(q.get("best_bid"), q.get("best_ask"), filled)
    mark_slip = (acct_mark_slippage(side, avg_price, q.get("mark"), filled)
                 if filled > 0 and avg_price is not None and q.get("mark") is not None else None)
    chase = (acct_chase_cost(side, intended_price, avg_price, filled)
             if filled > 0 and intended_price is not None and avg_price is not None else None)
    return {
        "leg": leg, "side": side, "instrument": instrument,
        "amount": amount, "filled": filled,
        "intended_price": intended_price, "final_price": final_price,
        "avg_price": avg_price, "order_id": order_id,
        "remaining": max(0.0, (amount or 0.0) - filled) if remaining is None else remaining,
        "cancelled": bool(cancelled),
        "taker": bool(taker),
        "quote_mark": q.get("mark"), "quote_bid": q.get("best_bid"),
        "quote_ask": q.get("best_ask"), "quote_tick": q.get("tick"),
        "spread_cost_estimate": spread,
        "mark_slippage": mark_slip,
        "chase_slippage": chase,
        "fee_actual": fee_actual,
        "fee_estimate": fee_est,
        "fee_used": fee_actual if fee_actual is not None else fee_est,
    }


# ---------- maker-only 成交（只追一步）----------

def exec_maker_only_fill(side, instrument, target_amount, label=None):
    """返回 dict：
       {filled, avg_price, price0, final_price, dry, steps_used, quote}
    空跑(dry)时只计算并记录意图，不下单（filled=0, dry=True）。"""
    q = exec_quote(instrument)
    if not q or q["best_bid"] is None or q["best_ask"] is None:
        Log("[exec] 盘口缺失，跳过:", instrument)
        return {"filled": 0.0, "dry": False, "quote": q, "reason": "NO_QUOTE"}

    price0 = exec_price_for(side, q["mark"], q["best_bid"], q["best_ask"], q["tick"], 0, q.get("meta"))
    # 进场门控（ENTRY）：exec_open_structure 为唯一调用方；退出/对冲执行器后续各自传专属门控
    gates = effective_trading_gates(RUN_PROFILE, ALLOW_ENTRY_TRADING, False, False)
    live = gate_decision(ACTION_ENTRY, gates["allow_entry"], False, False,
                         KILL_NEW_RISK, EMERGENCY_REDUCE_ONLY)["allowed"]

    if not live:
        intents = [exec_price_for(side, q["mark"], q["best_bid"], q["best_ask"], q["tick"], s, q.get("meta"))
                   for s in range(MAX_CHASE_STEPS + 1)]
        Log("[exec][DRY] 意图 %s %s amt=%s 计划价(含追价)=%s 盘口=%s/%s mark=%s" %
            (side, instrument, target_amount, intents, q["best_bid"], q["best_ask"], q["mark"]))
        return {"filled": 0.0, "dry": True, "price0": price0,
                "intended_prices": intents, "quote": q}

    # 实盘成交价守门：价差过宽不下单（防高磨损/难成交）
    sr = exec_spread_ratio(q)
    if sr is not None and sr > MAX_SPREAD_RATIO:
        Log("[exec] 价差过宽 %.0f%% > 上限 %.0f%%，放弃下单: %s" %
            (sr * 100, MAX_SPREAD_RATIO * 100, instrument))
        return {"filled": 0.0, "dry": False, "quote": q, "reason": "WIDE_SPREAD"}

    filled = 0.0
    avg_acc = 0.0
    final_price = price0
    steps_used = 0
    for step in range(MAX_CHASE_STEPS + 1):
        remaining = target_amount - filled
        if remaining <= 0:
            break
        price = exec_price_for(side, q["mark"], q["best_bid"], q["best_ask"], q["tick"], step, q.get("meta"))
        final_price = price
        steps_used = step
        resp = dbt_place_order(side, instrument, remaining, price,
                               post_only=True, reject_post_only=True, label=label)
        order = _extract_order(resp)
        if order is None:
            # reject_post_only 拒单（会越价）→ 视为需要追一步
            Log("[exec] 挂单被拒/失败 step=%s price=%s，尝试追价" % (step, price))
            continue
        oid = order.get("order_id")
        # 等待后查状态
        Sleep(int(CHASE_WAIT_SECONDS * 1000))
        st = _extract_order(dbt_get_order_state(oid)) or order
        fa = st.get("filled_amount") or 0.0
        if fa > 0:
            ap = st.get("average_price") or price
            avg_acc += ap * fa
            filled += fa
        state = st.get("order_state")
        if state not in ("filled",) and (target_amount - filled) > 0:
            # 未完全成交 → 撤掉残单，进入下一步追价
            dbt_cancel(oid)
        if filled >= target_amount:
            break

    avg_price = (avg_acc / filled) if filled > 0 else final_price
    return {"filled": filled, "avg_price": avg_price, "price0": price0,
            "final_price": final_price, "dry": False, "steps_used": steps_used,
            "quote": q}


# ---------- 保护腿优先开仓（§10.1）----------

def exec_open_structure(short_instrument, protection_instrument, amount):
    """先买 protection，再以 min(amount, 已成交保护量) 卖 short。
    返回 {protection_fill, short_fill, short_amount}。
    空跑下两腿都只记录意图。"""
    prot = exec_maker_only_fill("buy", protection_instrument, amount,
                                label="prot")
    if prot.get("dry"):
        short = exec_maker_only_fill("sell", short_instrument, amount, label="short")
        return {"protection_fill": prot, "short_fill": short, "short_amount": amount,
                "dry": True}

    filled_prot = prot.get("filled", 0.0)
    if filled_prot <= 0:
        Log("[exec] 保护腿未成交，按保护腿优先原则不卖 short")
        return {"protection_fill": prot, "short_fill": None, "short_amount": 0.0,
                "dry": False}

    short_amount = min(amount, filled_prot)   # 硬保证 short <= protection 可用量
    short = exec_maker_only_fill("sell", short_instrument, short_amount, label="short")
    return {"protection_fill": prot, "short_fill": short,
            "short_amount": short_amount, "dry": False}


# ---------- 开仓活动（entry campaign）：跨轮持久 maker、信用底线约束、保护腿先成交 ----------

def _post_maker_once(side, instrument, amount, price, label, meta=None, quote=None, leg=None,
                     wait_seconds=None):
    """单次 post-only 挂单(给定价)，等一周期，查成交，撤未成交后再查捕捉晚到成交。返回 filled。"""
    if not amount or amount <= 0 or price is None or price <= 0:
        return _execution_detail(leg or label, side, instrument, amount, price, price,
                                 0.0, None, None, quote)
    intended_price = price
    meta = meta or dbt_get_instrument(instrument) or {}
    rounded = exec_round_order_price(side, price, meta)
    if rounded != price:
        Log("[exec][round] leg=%s raw_price=%s rounded_price=%s tick=%s" %
            (side, price, rounded, exec_effective_tick(meta, price)))
        price = rounded
    resp = dbt_place_order(side, instrument, amount, price,
                           post_only=True, reject_post_only=True, label=label)
    order = _extract_order(resp)
    if order is None:
        return _execution_detail(leg or label, side, instrument, amount,
                                 intended_price, price, 0.0, None, None, quote)
    oid = order.get("order_id")
    wait_s = CHASE_WAIT_SECONDS if wait_seconds is None else wait_seconds
    Sleep(int(wait_s * 1000))
    st = _extract_order(dbt_get_order_state(oid)) or order
    filled = st.get("filled_amount") or 0.0
    avg = st.get("average_price") or price
    cancelled = False
    if st.get("order_state") not in ("filled",) and (amount - filled) > 0:
        dbt_cancel(oid)
        cancelled = True
        st2 = _extract_order(dbt_get_order_state(oid)) or st
        if (st2.get("filled_amount") or 0.0) > filled:
            filled = st2.get("filled_amount")
            avg = st2.get("average_price") or avg
            st = st2
    return _execution_detail(leg or label, side, instrument, amount,
                              intended_price, price, filled, avg, oid, quote,
                              cancelled=cancelled, order=st)


def _post_taker_once(side, instrument, amount, price, label, meta=None, quote=None, leg=None):
    if not amount or amount <= 0 or price is None or price <= 0:
        return _execution_detail(leg or label, side, instrument, amount, price, price,
                                 0.0, None, None, quote, taker=True)
    intended_price = price
    meta = meta or dbt_get_instrument(instrument) or {}
    price = exec_round_order_price(side, price, meta)
    resp = dbt_place_order(side, instrument, amount, price,
                           post_only=False, reject_post_only=False, label=label)
    order = _extract_order(resp)
    if order is None:
        return _execution_detail(leg or label, side, instrument, amount,
                                 intended_price, price, 0.0, None, None, quote,
                                 taker=True)
    oid = order.get("order_id")
    Sleep(1000)
    st = _extract_order(dbt_get_order_state(oid)) or order
    filled = st.get("filled_amount") or 0.0
    avg = st.get("average_price") or price
    cancelled = False
    if st.get("order_state") not in ("filled",) and (amount - filled) > 0:
        dbt_cancel(oid)
        cancelled = True
        st2 = _extract_order(dbt_get_order_state(oid)) or st
        if (st2.get("filled_amount") or 0.0) > filled:
            filled = st2.get("filled_amount")
            avg = st2.get("average_price") or avg
            st = st2
    return _execution_detail(leg or label, side, instrument, amount,
                             intended_price, price, filled, avg, oid, quote,
                             cancelled=cancelled, order=st, taker=True)


def _level_amount(level):
    if isinstance(level, (list, tuple)) and len(level) >= 2:
        return _float_or_none(level[1])
    if isinstance(level, dict):
        for k in ("amount", "quantity", "size"):
            v = _float_or_none(level.get(k))
            if v is not None:
                return v
    return None


def _best_ask_depth(instrument, quote=None):
    q = quote or {}
    amount = _float_or_none(q.get("best_ask_amount"))
    if amount is not None:
        return amount
    book = dbt_order_book(instrument, depth=1)
    asks = (book or {}).get("asks") or []
    return _level_amount(asks[0]) if asks else None


def _entry_order_state(order_id):
    try:
        return _extract_order(dbt_get_order_state(order_id))
    except Exception:
        return None


def _entry_filled_amount(order):
    return _float_or_none((order or {}).get("filled_amount")) or 0.0


def _entry_order_closed(order, target_amount=None):
    if not order:
        return False
    state = order.get("order_state")
    filled = _entry_filled_amount(order)
    if state in ("filled", "cancelled", "rejected"):
        return True
    return target_amount is not None and filled >= target_amount - 1e-12


def _protection_order_record(order, instrument, amount, price, now_ms, wait_start_ms, label):
    oid = (order or {}).get("order_id")
    if not oid:
        return None
    return {
        "order_id": oid,
        "instrument": instrument,
        "price": price,
        "amount": amount,
        "filled_seen": _entry_filled_amount(order),
        "placed_ms": now_ms,
        "wait_start_ms": wait_start_ms,
        "label": label,
    }


def _post_protection_maker(instrument, amount, price, quote, label, meta, now_ms, wait_start_ms):
    if not amount or amount <= 0 or price is None or price <= 0:
        detail = _execution_detail("protection", "buy", instrument, amount, price, price,
                                   0.0, None, None, quote)
        detail["prot_order"] = None
        return detail
    resp = dbt_place_order("buy", instrument, amount, price,
                           post_only=True, reject_post_only=True, label=label)
    order = _extract_order(resp)
    detail = _execution_detail("protection", "buy", instrument, amount,
                               price, price, 0.0, None,
                               (order or {}).get("order_id"), quote, order=order)
    detail["prot_order"] = _protection_order_record(
        order, instrument, amount, price, now_ms, wait_start_ms, label)
    return detail


def _post_entry_protection_once(instrument, amount, maker_price, quote, attempt,
                                short_price, fees, credit_floor, label, meta=None,
                                prot_order=None, now_ms=None):
    q = quote or {}
    ask = q.get("best_ask")
    now_ms = now_ms or 0
    meta = meta or {}
    active = dict(prot_order or {})
    wait_start_ms = active.get("wait_start_ms") or now_ms
    remaining = amount
    filled_delta = 0.0
    avg_price = None

    if active.get("order_id"):
        st = _entry_order_state(active.get("order_id"))
        if st is None:
            detail = _execution_detail("protection", "buy", instrument, amount,
                                       active.get("price"), active.get("price"),
                                       0.0, None, active.get("order_id"), q)
            detail["prot_order"] = active
            detail["reason"] = "PROTECTION_ORDER_STATE_UNKNOWN"
            detail["active_order_only"] = True
            return detail
        total_filled = _entry_filled_amount(st)
        seen = active.get("filled_seen") or 0.0
        filled_delta = max(0.0, total_filled - seen)
        avg_price = st.get("average_price") or active.get("price")
        active["filled_seen"] = max(seen, total_filled)
        remaining = max(0.0, amount - filled_delta)
        if remaining <= 1e-12 or _entry_order_closed(st, active.get("amount")):
            detail = _execution_detail("protection", "buy", instrument, amount,
                                       active.get("price"), active.get("price"),
                                       filled_delta, avg_price,
                                       active.get("order_id"), q, order=st)
            detail["prot_order"] = None
            return detail

        elapsed_ms = now_ms - wait_start_ms if now_ms else 0
        target_changed = abs((active.get("price") or 0.0) - (maker_price or 0.0)) >= ((q.get("tick") or 0.0) - 1e-12)
        taker_due = elapsed_ms >= ENTRY_PROTECTION_TAKER_AFTER_SECONDS * 1000
        if not target_changed and not taker_due:
            detail = _execution_detail("protection", "buy", instrument, amount,
                                       active.get("price"), active.get("price"),
                                       filled_delta, avg_price,
                                       active.get("order_id"), q, order=st)
            detail["prot_order"] = active
            if filled_delta <= 0:
                detail["active_order_only"] = True
            return detail

        dbt_cancel(active.get("order_id"))
        st2 = _entry_order_state(active.get("order_id")) or st
        total2 = _entry_filled_amount(st2)
        if total2 > active.get("filled_seen", 0.0):
            late_delta = total2 - active.get("filled_seen", 0.0)
            filled_delta += late_delta
            active["filled_seen"] = total2
            avg_price = st2.get("average_price") or avg_price
            remaining = max(0.0, amount - filled_delta)
        if remaining <= 1e-12:
            detail = _execution_detail("protection", "buy", instrument, amount,
                                       active.get("price"), active.get("price"),
                                       filled_delta, avg_price,
                                       active.get("order_id"), q,
                                       cancelled=True, order=st2)
            detail["prot_order"] = None
            return detail

        if taker_due:
            ask_depth = _best_ask_depth(instrument, q)
            depth_ok = ask_depth is not None and ask_depth + 1e-12 >= remaining
            credit_ok = (ask is not None
                         and entry_net_credit(short_price, ask, remaining, fees) >= credit_floor)
            if ask is not None and depth_ok and credit_ok:
                taker = _post_taker_once("buy", instrument, remaining, ask,
                                         label + "_taker", meta, quote=q, leg="protection")
                taker_fill = taker.get("filled") or 0.0
                total_fill = filled_delta + taker_fill
                detail = _execution_detail("protection", "buy", instrument, amount,
                                           active.get("price"), taker.get("final_price") or ask,
                                           total_fill, taker.get("avg_price") or avg_price,
                                           taker.get("order_id"), q,
                                           cancelled=True, order=taker, taker=True)
                detail["prot_order"] = None
                detail["reason"] = "PROTECTION_TAKER_AFTER_WAIT"
                return detail
            Log("[entry][prot] taker_after_wait hold ask=%s depth=%s remaining=%s credit_ok=%s" %
                (ask, ask_depth, remaining, credit_ok))

        maker = _post_protection_maker(instrument, remaining, maker_price, q, label,
                                       meta, now_ms, wait_start_ms)
        maker["filled"] = filled_delta
        maker["avg_price"] = avg_price or maker.get("avg_price")
        return maker

    return _post_protection_maker(instrument, amount, maker_price, q, label,
                                  meta, now_ms, wait_start_ms)


def exec_entry_campaign_step(prot_inst, short_inst, amount, credit_floor, max_tick_steps,
                             attempt, prot_done_qty, short_done_qty, allow_live, label="entry",
                             prot_order=None, now_ms=None):
    """开仓活动一轮：保护腿先成交，价格在「净 credit ≥ credit_floor」内逐 tick 改善(本轮档=min(attempt,信用上限档))。
    跨轮持久（每轮一次 post-only）。allow_live=False → 仅意图(dry)。
    返回 {quotes_ok, credit_ok, dry, prot_price, short_price, net_credit, n_used, prot_fill, short_fill, reason}。"""
    pq, sq = exec_quote(prot_inst), exec_quote(short_inst)
    quotes_ok = bool(pq and sq and pq.get("mark") is not None and sq.get("mark") is not None
                     and pq.get("best_ask") is not None and pq.get("best_bid") not in (None, 0)
                     and sq.get("best_bid") not in (None, 0) and sq.get("best_ask") is not None)
    if not quotes_ok:
        return {"quotes_ok": False, "credit_ok": False, "dry": (not allow_live),
                "prot_fill": 0.0, "short_fill": 0.0, "reason": "NO_QUOTE"}
    steps = max(0, int(max_tick_steps))
    prot_maker_price = exec_protection_maker_price(
        pq["mark"], pq["best_bid"], pq["best_ask"], pq["tick"], pq.get("meta"))
    prot_buy_prices = [prot_maker_price for _n in range(steps + 1)]
    short_sell_prices = [exec_sell_price(sq["mark"], sq["best_bid"], sq["tick"], n, sq.get("meta"))
                         for n in range(steps + 1)]
    fees = acct_option_fee_ccy(pq["mark"], amount) + acct_option_fee_ccy(sq["mark"], amount)
    i_cap = entry_credit_capped_index(prot_buy_prices, short_sell_prices, amount, fees, credit_floor)
    if i_cap < 0:
        nc0 = entry_net_credit(short_sell_prices[0], prot_buy_prices[0], amount, fees)
        return {"quotes_ok": True, "credit_ok": False, "dry": (not allow_live), "net_credit": nc0,
                "prot_fill": 0.0, "short_fill": 0.0, "reason": "BELOW_CREDIT_FLOOR"}
    n = min(max(0, int(attempt)), i_cap)
    prot_price, short_price = prot_buy_prices[n], short_sell_prices[n]
    net_credit = entry_net_credit(short_price, prot_price, amount, fees)
    if not allow_live:
        return {"quotes_ok": True, "credit_ok": True, "dry": True, "prot_price": prot_price,
                "short_price": short_price, "net_credit": net_credit, "n_used": n,
                "prot_fill": 0.0, "short_fill": 0.0, "reason": "ENTRY_DRYRUN"}
    prot_detail = _execution_detail("protection", "buy", prot_inst, 0.0,
                                    prot_price, prot_price, 0.0, None, None, pq)
    prot_detail["prot_order"] = None
    if (prot_done_qty or 0.0) < amount - 1e-12:                 # 保护腿先成交（持久重挂）
        prot_detail = _post_entry_protection_once(
            prot_inst, amount - (prot_done_qty or 0.0), prot_price, pq, attempt,
            short_price, fees, credit_floor, label + "_prot", pq.get("meta"),
            prot_order=prot_order, now_ms=now_ms)
    prot_fill = prot_detail.get("filled") or 0.0
    short_cap = min(amount, (prot_done_qty or 0.0) + prot_fill) - (short_done_qty or 0.0)
    short_detail = _execution_detail("short", "sell", short_inst, 0.0,
                                     short_price, short_price, 0.0, None, None, sq)
    if short_cap > 1e-12:                                       # 短腿数量 ≤ 已成交保护腿量
        short_detail = _post_maker_once("sell", short_inst, short_cap, short_price,
                                        label + "_short", sq.get("meta"),
                                        quote=sq, leg="short",
                                        wait_seconds=ENTRY_SHORT_ORDER_WAIT_SECONDS)
    short_fill = short_detail.get("filled") or 0.0
    fills = [d for d in (prot_detail, short_detail)
             if (d.get("filled") or 0.0) > 0
             or (d.get("order_id") and not d.get("active_order_only"))]
    prot_avg = prot_detail.get("avg_price") if prot_fill > 0 else None
    short_avg = short_detail.get("avg_price") if short_fill > 0 else None
    fee_used = sum((d.get("fee_used") or 0.0) for d in fills)
    actual_before = ((short_avg or 0.0) * short_fill
                     - (prot_avg or 0.0) * prot_fill)
    actual_after = actual_before - fee_used
    return {"quotes_ok": True, "credit_ok": True, "dry": False, "prot_price": prot_price,
            "short_price": short_price, "net_credit": net_credit, "n_used": n,
            "prot_fill": prot_fill, "short_fill": short_fill,
            "prot_avg_price": prot_avg, "short_avg_price": short_avg,
            "prot_order": prot_detail.get("prot_order"),
            "entry_fees": fee_used,
            "actual_net_credit_before_fees": actual_before,
            "actual_net_credit_after_fees": actual_after,
            "fills": fills, "reason": "ENTRY_STEP"}


# ---------- 低成本退出：买回卖方短腿（§7.3；每轮一次、价格 ≤ 预算上限、post-only）----------

def exec_exit_buyback_step(short_instrument, target_amount, price_cap, allow_live,
                           allow_taker=False, label="exit_short", quote=None):
    """退出活动一轮：买回（平）卖方短腿。
    - **止盈退出**(allow_taker=False)：被动 post-only，买价 ≤ min(ask−tick, price_cap)，patient 不越价。
    - **风险退出**(allow_taker=True)：可**越价吃单**至 price_cap（限价=price_cap、非 post-only，
      扫所有 ask ≤ cap 的卖盘、残量挂 cap）；成本仍硬封在 price_cap·qty 内（由风险退出预算反推）。
    allow_live=False → 仅返回意图(dry)。撤未成交单后再查一次以捕捉晚到成交。
    返回 {filled, avg_price, dry, price, taker, reason}。"""
    q = quote if quote is not None else exec_quote(short_instrument)
    if not q or q.get("best_bid") is None or q.get("best_ask") is None or q.get("mark") is None:
        return {"filled": 0.0, "dry": (not allow_live), "reason": "NO_QUOTE"}
    tick = q.get("tick") or 0.0
    if allow_taker:
        price = price_cap                       # 限价=预算上限：≤cap 的卖盘成交、残量挂 cap（成本硬封）
        post_only = False
    else:
        maker_safe = (q["best_ask"] - tick) if tick else q["best_bid"]   # 最高仍为 maker 的买价
        price = min(maker_safe, price_cap)
        post_only = True
    if price <= 0 or price > price_cap + 1e-12:
        return {"filled": 0.0, "dry": (not allow_live), "price": price, "reason": "ABOVE_BUDGET_CAP"}
    if not allow_live:
        return {"filled": 0.0, "dry": True, "price": price, "taker": allow_taker, "reason": "EXIT_DRYRUN"}
    resp = dbt_place_order("buy", short_instrument, target_amount, price,
                           post_only=post_only, reject_post_only=post_only, label=label)
    order = _extract_order(resp)
    if order is None:
        return {"filled": 0.0, "dry": False, "price": price, "taker": allow_taker,
                "reason": ("ORDER_REJECTED" if allow_taker else "POST_ONLY_REJECTED")}
    oid = order.get("order_id")
    Sleep(int(CHASE_WAIT_SECONDS * 1000))
    st = _extract_order(dbt_get_order_state(oid)) or order
    filled = st.get("filled_amount") or 0.0
    avg = st.get("average_price") or price
    cancelled = False
    if st.get("order_state") not in ("filled",) and (target_amount - filled) > 0:
        dbt_cancel(oid)
        cancelled = True
        st2 = _extract_order(dbt_get_order_state(oid)) or st        # 撤单后再查，捕捉晚到成交
        if (st2.get("filled_amount") or 0.0) > filled:
            filled = st2.get("filled_amount")
            avg = st2.get("average_price") or avg
    detail = _execution_detail("exit_short", "buy", short_instrument, target_amount,
                               price, price, filled, avg, oid, q,
                               cancelled=cancelled, order=st, taker=allow_taker)
    return {"filled": filled, "avg_price": avg, "dry": False, "price": price,
            "taker": allow_taker, "reason": "EXIT_STEP", **detail}


# ---------- 保护腿回收（§7.5；短腿归零后 maker 卖出；无 bid → LONG_RESIDUAL_ONLY）----------

def exec_protection_recovery_step(long_inst, qty, allow_live, label="recover_long", quote=None):
    """短腿归零后回收保护腿：被动 maker 卖出(post-only，join bid)；无 bid → LONG_RESIDUAL_ONLY(保持等结算)。
    allow_live=False → 仅意图(dry)。返回 {sold, price, state, dry, reason}。"""
    if not qty or qty <= 0:
        return {"sold": 0.0, "dry": (not allow_live), "state": "COMPLETE", "reason": "NO_LONG"}
    if not long_inst:
        return {"sold": 0.0, "dry": (not allow_live), "state": "LONG_RESIDUAL_ONLY",
                "reason": "NO_LONG_INSTRUMENT"}
    q = quote if quote is not None else exec_quote(long_inst)
    bid = (q or {}).get("best_bid")
    if not q or bid in (None, 0) or bid <= 0:
        return {"sold": 0.0, "dry": (not allow_live), "state": "LONG_RESIDUAL_ONLY", "reason": "NO_BID"}
    price = bid                                    # 被动 maker 卖：join bid（不接受负净回收 → bid>0 已保证）
    if not allow_live:
        return {"sold": 0.0, "dry": True, "price": price, "state": "WORKING_LONG", "reason": "RECOVER_DRYRUN"}
    detail = _post_maker_once("sell", long_inst, qty, price, label, quote=q, leg="recover_long")
    sold = detail.get("filled") or 0.0
    return {"sold": sold, "price": price, "avg_price": detail.get("avg_price"),
            "dry": False, "execution": detail,
            "state": ("COMPLETE" if sold >= qty - 1e-12 else "WORKING_LONG"), "reason": "RECOVER_STEP"}


# ---------- BTC-PERPETUAL 对冲下单（§10.4；REDUCE/UNWIND 强制 reduce_only）----------

def exec_hedge_step(venue_cfg, side, amount, reduce_only, allow_live, label="hedge",
                    execution_style=None, max_slippage_bps=None):
    """对冲一步（场所感知）。OPEN/INCREASE 非 reduce_only；REDUCE/UNWIND 强制 reduce_only。
    venue_cfg: hedge.hedge_venue_config 结果(含 venue/instrument/linear/exchange_index)。
    BINANCE → binance_io(PROMPT_LIMIT/USDC 永续)；DERIBIT → BTC-PERPETUAL。allow_live=False → 仅意图(dry)。"""
    venue_cfg = venue_cfg or {}
    venue = venue_cfg.get("venue")
    instrument = venue_cfg.get("instrument")
    execution_style = execution_style or HEDGE_OPEN_EXECUTION_STYLE
    max_slippage_bps = HEDGE_MAX_SLIPPAGE_BPS if max_slippage_bps is None else max_slippage_bps
    if not side or not amount or amount <= 0:
        return {"filled": 0.0, "dry": (not allow_live), "venue": venue, "reason": "NO_OP"}
    if venue == "BINANCE":
        if not allow_live:
            return bnc_place_hedge(instrument, side, amount, reduce_only,
                                   allow_live=False,
                                   idx=venue_cfg.get("exchange_index"),
                                   execution_style=execution_style,
                                   max_slippage_bps=max_slippage_bps)
        return {"filled": 0.0, "dry": False, "venue": "BINANCE",
                "instrument": instrument, "side": side, "amount": amount,
                "reduce_only": reduce_only, "post_only": False,
                "execution_style": execution_style, "blocked": True,
                "reason": "HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT"}
    # DERIBIT 反向永续
    if not allow_live:
        return {"filled": 0.0, "dry": True, "venue": venue, "instrument": instrument,
                "side": side, "amount": amount, "reduce_only": reduce_only,
                "post_only": False, "execution_style": execution_style, "reason": "HEDGE_DRYRUN"}
    q = exec_quote(instrument) or {}
    bps = (max_slippage_bps or 0) / 10000.0
    price = ((q.get("best_ask") or 0) * (1.0 + bps) if side == "buy"
             else (q.get("best_bid") or 0) * (1.0 - bps))
    if price is None or price <= 0:                       # C1：无可成交盘口 → 不下单（防 price=None 误单）
        return {"filled": 0.0, "dry": False, "venue": venue, "reduce_only": reduce_only,
                "post_only": False, "execution_style": execution_style, "reason": "NO_QUOTE"}
    resp = dbt_place_order(side, instrument, amount, price, post_only=False,
                           reject_post_only=False, label=label, reduce_only=reduce_only)
    order = _extract_order(resp)
    if order is None:
        return {"filled": 0.0, "dry": False, "venue": venue, "reduce_only": reduce_only,
                "post_only": False, "execution_style": execution_style, "reason": "HEDGE_ORDER_FAILED"}
    oid = order.get("order_id")
    Sleep(int(CHASE_WAIT_SECONDS * 1000))                 # C1：等一周期再查成交（原即查多为 0）
    st = _extract_order(dbt_get_order_state(oid)) or order
    filled = st.get("filled_amount") or 0.0
    cancelled = False
    if st.get("order_state") not in ("filled",) and (amount - filled) > 0:
        dbt_cancel(oid)                                  # 残单撤掉(不留挂)，撤后再查捕捉晚到成交
        cancelled = True
        st2 = _extract_order(dbt_get_order_state(oid)) or st
        if (st2.get("filled_amount") or 0.0) > filled:
            filled = st2.get("filled_amount")
    remaining = max(0.0, amount - filled)
    return {"filled": filled, "avg_price": st.get("average_price") or price,
            "remaining": remaining, "cancelled": cancelled, "dry": False, "venue": venue,
            "instrument": instrument, "side": side, "amount": amount, "price": price,
            "order_id": oid, "reduce_only": reduce_only, "post_only": False,
            "execution_style": execution_style, "reason": "HEDGE_STEP"}
