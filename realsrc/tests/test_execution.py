# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import execution as EX

# 捕获原始依赖，patch 后还原，避免泄漏到后续测试文件（execution 早于 integration 运行）
_ORIG = {k: getattr(EX, k) for k in
         ("dbt_ticker", "dbt_get_instrument", "dbt_place_order",
          "dbt_order_book", "dbt_get_order_state", "dbt_cancel", "Sleep")}
_ORIG_VARS = {k: getattr(EX, k) for k in (
    "ENTRY_SHORT_ORDER_WAIT_SECONDS", "ENTRY_PROTECTION_TAKER_AFTER_SECONDS",
)}


def _restore_ex():
    for k, v in _ORIG.items():
        setattr(EX, k, v)
    EX.ALLOW_ENTRY_TRADING = False
    EX.RUN_PROFILE = "TEST"
    EX.KILL_NEW_RISK = False
    EX.EMERGENCY_REDUCE_ONLY = False
    for k, v in _ORIG_VARS.items():
        setattr(EX, k, v)


def _approx(a, b, eps=1e-9):
    return abs(a - b) <= eps


def test_buy_price_step0_uses_min_mark_ask():
    # mark 低于 ask-tick -> step0 = mark
    assert _approx(EX.exec_buy_price(0.0010, 0.0013, 0.0001, 0), 0.0010)
    # mark 高于 ask-tick -> 封顶 ask-tick
    assert _approx(EX.exec_buy_price(0.0013, 0.0013, 0.0001, 0), 0.0012)


def test_buy_price_chase_one_step_clamped():
    # step1 = step0 + tick，封顶 ask-tick
    assert _approx(EX.exec_buy_price(0.0010, 0.0013, 0.0001, 1), 0.0011)
    assert _approx(EX.exec_buy_price(0.0011, 0.0013, 0.0001, 1), 0.0012)  # 不超过 ask-tick


def test_sell_price_step0_uses_max_mark_bid():
    assert _approx(EX.exec_sell_price(0.0010, 0.0007, 0.0001, 0), 0.0010)
    # mark 低于 bid+tick -> 封底 bid+tick
    assert _approx(EX.exec_sell_price(0.0005, 0.0007, 0.0001, 0), 0.0008)


def test_sell_price_chase_one_step_clamped():
    assert _approx(EX.exec_sell_price(0.0010, 0.0007, 0.0001, 1), 0.0009)
    assert _approx(EX.exec_sell_price(0.0009, 0.0007, 0.0001, 1), 0.0008)  # 不低于 bid+tick


def test_tick_rounding_no_cross():
    # mark 不在 tick 网格上 -> 买价向下取整，卖价向上取整，避免越价
    assert _approx(EX.exec_buy_price(0.00105, 0.0013, 0.0001, 0), 0.0010)
    assert _approx(EX.exec_sell_price(0.00105, 0.0007, 0.0001, 0), 0.0011)


def test_tick_size_steps_round_sell_to_effective_deribit_grid():
    meta = {"tick_size": 0.0001,
            "tick_size_steps": [{"above_price": 0.005, "tick_size": 0.0005}]}
    tick = EX.exec_effective_tick(meta, 0.0072)
    assert _approx(tick, 0.0005)
    assert _approx(EX.exec_sell_price(0.0072, 0.0065, tick, 0, meta), 0.0075)


def test_price_for_dispatch():
    assert _approx(EX.exec_price_for("buy", 0.0010, 0.0007, 0.0013, 0.0001, 0), 0.0010)
    assert _approx(EX.exec_price_for("sell", 0.0010, 0.0007, 0.0013, 0.0001, 0), 0.0010)


def test_plan_prices_buy_uses_single_persistent_mark_maker_price():
    EX.dbt_ticker = lambda inst: {
        "mark_price": 0.0005, "best_bid_price": 0.0001,
        "best_ask_price": 0.0004, "greeks": {},
    }
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}

    r = EX.exec_plan_prices("buy", "P", 0.1)

    assert r["prices"] == [0.0003]
    _restore_ex()


def test_spread_ratio():
    assert abs(EX.exec_spread_ratio({"best_bid": 0.0097, "best_ask": 0.0103}) - 0.06) < 1e-6
    assert EX.exec_spread_ratio({"best_bid": None, "best_ask": 0.01}) is None


def _mock_quote(_inst):
    return {"mark_price": 0.01, "best_bid_price": 0.0097, "best_ask_price": 0.0103,
            "greeks": {"delta": 0.3}}


def test_maker_fill_dry_shows_intent():
    EX.RUN_PROFILE = "TEST"
    EX.ALLOW_ENTRY_TRADING = False
    EX.dbt_ticker = _mock_quote
    EX.dbt_get_instrument = lambda i: {"tick_size": 0.0001}
    r = EX.exec_maker_only_fill("sell", "X", 0.1)
    assert r["dry"] and r["filled"] == 0.0 and r["intended_prices"]
    _restore_ex()


def test_maker_fill_live_fills():
    EX.RUN_PROFILE = "LIVE"
    EX.ALLOW_ENTRY_TRADING = True
    EX.dbt_ticker = _mock_quote
    EX.dbt_get_instrument = lambda i: {"tick_size": 0.0001}
    EX.dbt_place_order = lambda side, inst, amt, price, **k: {
        "order": {"order_id": "1", "order_state": "open", "filled_amount": 0.0}}
    EX.dbt_get_order_state = lambda oid: {
        "order": {"order_id": oid, "order_state": "filled", "filled_amount": 0.1,
                  "average_price": 0.0097}}
    EX.dbt_cancel = lambda oid: {"order_id": oid}
    EX.Sleep = lambda ms: None
    r = EX.exec_maker_only_fill("sell", "X", 0.1)
    assert not r["dry"] and _approx(r["filled"], 0.1) and _approx(r["avg_price"], 0.0097)
    _restore_ex()


def test_maker_fill_wide_spread_guard():
    EX.RUN_PROFILE = "LIVE"
    EX.ALLOW_ENTRY_TRADING = True
    EX.dbt_ticker = lambda i: {"mark_price": 0.01, "best_bid_price": 0.005,
                               "best_ask_price": 0.02, "greeks": {}}
    EX.dbt_get_instrument = lambda i: {"tick_size": 0.0001}
    r = EX.exec_maker_only_fill("sell", "X", 0.1)
    assert r.get("reason") == "WIDE_SPREAD" and r["filled"] == 0.0
    _restore_ex()


# ---- F1：风险退出可越价吃单 vs 止盈退出被动 maker ----

def test_exit_buyback_taker_crosses_at_cap():
    EX.dbt_ticker = _mock_quote                      # ask 0.0103
    EX.dbt_get_instrument = lambda i: {"tick_size": 0.0001}
    seen = {}
    def _place(side, inst, amt, price, **k):
        seen["price"], seen["post_only"] = price, k.get("post_only")
        return {"order": {"order_id": "1", "order_state": "filled",
                          "filled_amount": amt, "average_price": 0.0101}}
    EX.dbt_place_order = _place
    EX.dbt_get_order_state = lambda oid: {"order": {"order_id": oid, "order_state": "filled",
                                                    "filled_amount": 0.1, "average_price": 0.0101}}
    EX.dbt_cancel = lambda oid: {"order_id": oid}
    EX.Sleep = lambda ms: None
    r = EX.exec_exit_buyback_step("X", 0.1, price_cap=0.02, allow_live=True, allow_taker=True)
    assert not r["dry"] and r["taker"] is True and _approx(r["filled"], 0.1)
    assert seen["post_only"] is False and _approx(seen["price"], 0.02)   # 限价=cap、可越价吃单
    _restore_ex()


def test_exit_buyback_maker_passive_below_ask():
    EX.dbt_ticker = _mock_quote                      # ask 0.0103 tick 0.0001 → maker_safe 0.0102
    EX.dbt_get_instrument = lambda i: {"tick_size": 0.0001}
    seen = {}
    def _place(side, inst, amt, price, **k):
        seen["price"], seen["post_only"] = price, k.get("post_only")
        return {"order": {"order_id": "1", "order_state": "open", "filled_amount": 0.0}}
    EX.dbt_place_order = _place
    EX.dbt_get_order_state = lambda oid: {"order": {"order_id": oid, "order_state": "open", "filled_amount": 0.0}}
    EX.dbt_cancel = lambda oid: {"order_id": oid}
    EX.Sleep = lambda ms: None
    r = EX.exec_exit_buyback_step("X", 0.1, price_cap=0.02, allow_live=True, allow_taker=False)
    assert seen["post_only"] is True and _approx(seen["price"], 0.0102)  # ask-tick，被动不越价
    _restore_ex()


# ---- C1：Deribit 对冲 None 盘口守门 + 成交确认 ----

def test_hedge_step_deribit_no_quote_guard():
    EX.dbt_ticker = lambda i: {"mark_price": 50000, "best_bid_price": None, "best_ask_price": None}
    EX.dbt_get_instrument = lambda i: {"tick_size": 0.5}
    vcfg = {"venue": "DERIBIT", "instrument": "BTC-PERPETUAL", "maker_only": False}
    r = EX.exec_hedge_step(vcfg, "buy", 100.0, reduce_only=False, allow_live=True)
    assert r["reason"] == "NO_QUOTE" and r["filled"] == 0.0           # price=None → 不下单
    _restore_ex()


def test_hedge_step_deribit_confirms_fill():
    EX.dbt_ticker = lambda i: {"mark_price": 50000, "best_bid_price": 49999, "best_ask_price": 50001}
    EX.dbt_get_instrument = lambda i: {"tick_size": 0.5}
    seen = {}
    def _place(side, inst, amt, price, **k):
        seen["price"] = price
        seen["post_only"] = k.get("post_only")
        return {"order": {"order_id": "h1", "order_state": "open", "filled_amount": 0.0}}
    EX.dbt_place_order = _place
    EX.dbt_get_order_state = lambda oid: {
        "order": {"order_id": oid, "order_state": "filled", "filled_amount": 100.0, "average_price": 50001}}
    EX.dbt_cancel = lambda oid: {"order_id": oid}
    EX.Sleep = lambda ms: None
    vcfg = {"venue": "DERIBIT", "instrument": "BTC-PERPETUAL", "maker_only": False}
    r = EX.exec_hedge_step(vcfg, "buy", 100.0, reduce_only=False, allow_live=True)
    assert not r["dry"] and _approx(r["filled"], 100.0) and r["reason"] == "HEDGE_STEP"  # 等待后查得成交
    assert seen["post_only"] is False and _approx(seen["price"], 50026.0005)
    assert r["execution_style"] == "PROMPT_LIMIT"
    _restore_ex()


def test_entry_campaign_step_returns_fill_accounting_details():
    quotes = {
        "P": {"mark_price": 0.0010, "best_bid_price": 0.0009,
              "best_ask_price": 0.0012, "greeks": {"delta": 0.1}},
        "S": {"mark_price": 0.0070, "best_bid_price": 0.0065,
              "best_ask_price": 0.0075, "greeks": {"delta": 0.3}},
    }
    order_ids = []

    EX.dbt_ticker = lambda inst: quotes[inst]
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}

    def _place(side, inst, amt, price, **kwargs):
        oid = "p1" if inst == "P" else "s1"
        order_ids.append((oid, side, inst, amt, price, kwargs.get("label")))
        return {"order": {"order_id": oid, "order_state": "open", "filled_amount": 0.0}}

    def _state(oid):
        avg = 0.0010 if oid == "p1" else 0.0070
        return {"order": {"order_id": oid, "order_state": "filled",
                          "filled_amount": 0.1, "average_price": avg}}

    EX.dbt_place_order = _place
    EX.dbt_get_order_state = _state
    EX.dbt_cancel = lambda oid: {"order_id": oid}
    EX.Sleep = lambda ms: None

    prot_order = {"order_id": "p1", "instrument": "P", "price": 0.0010,
                  "amount": 0.1, "filled_seen": 0.0, "placed_ms": 1000,
                  "wait_start_ms": 1000, "label": "entry_prot"}
    r = EX.exec_entry_campaign_step(
        "P", "S", 0.1, credit_floor=0.0, max_tick_steps=0,
        attempt=0, prot_done_qty=0.0, short_done_qty=0.0,
        allow_live=True, label="entry", prot_order=prot_order, now_ms=4000)

    assert r["prot_fill"] == 0.1 and r["short_fill"] == 0.1
    assert r["prot_avg_price"] == 0.0010
    assert r["short_avg_price"] == 0.0070
    assert r["actual_net_credit_after_fees"] < r["actual_net_credit_before_fees"]
    assert [f["order_id"] for f in r["fills"]] == ["p1", "s1"]
    assert r["fills"][0]["leg"] == "protection" and r["fills"][0]["fee_estimate"] > 0
    assert r["fills"][1]["leg"] == "short" and r["fills"][1]["spread_cost_estimate"] > 0
    assert order_ids == [("s1", "sell", "S", 0.1, 0.0070, "entry_short")]
    _restore_ex()


def test_entry_protection_before_ten_minutes_starts_persistent_maker_even_when_ask_is_one_tick():
    quotes = {
        "P": {"mark_price": 0.0002, "best_bid_price": 0.0001,
              "best_ask_price": 0.0003, "greeks": {"delta": 0.05}},
        "S": {"mark_price": 0.0068, "best_bid_price": 0.0067,
              "best_ask_price": 0.0070, "greeks": {"delta": 0.3}},
    }
    calls, sleeps = [], []
    EX.dbt_ticker = lambda inst: quotes[inst]
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}
    EX.dbt_order_book = lambda inst, depth=1: {"asks": [[0.0003, 0.1]]}

    def _place(side, inst, amt, price, **kwargs):
        calls.append((side, inst, amt, price, kwargs))
        return {"order": {"order_id": "%s-%s" % (side, inst),
                          "order_state": "open", "filled_amount": 0.0}}

    def _state(oid):
        if oid == "buy-P":
            return {"order": {"order_id": oid, "order_state": "filled",
                              "filled_amount": 0.1, "average_price": 0.0003}}
        return {"order": {"order_id": oid, "order_state": "open",
                          "filled_amount": 0.0}}

    EX.dbt_place_order = _place
    EX.dbt_get_order_state = _state
    EX.dbt_cancel = lambda oid: {"order_id": oid}
    EX.Sleep = lambda ms: sleeps.append(ms)
    EX.ENTRY_PROTECTION_TAKER_AFTER_SECONDS = 600
    EX.ENTRY_SHORT_ORDER_WAIT_SECONDS = 60

    r = EX.exec_entry_campaign_step(
        "P", "S", 0.1, credit_floor=0.0, max_tick_steps=3,
        attempt=20, prot_done_qty=0.0, short_done_qty=0.0,
        allow_live=True, label="entry", prot_order=None, now_ms=1000)

    assert r["prot_fill"] == 0.0
    assert calls[0][0] == "buy" and calls[0][1] == "P"
    assert calls[0][4]["post_only"] is True
    assert calls[0][4]["reject_post_only"] is True
    assert _approx(calls[0][3], 0.0002)
    assert len(calls) == 1
    assert sleeps == []
    assert r["prot_order"]["order_id"] == "buy-P"
    _restore_ex()


def test_entry_protection_before_ten_minutes_holds_maker_when_ask_not_one_tick():
    quotes = {
        "P": {"mark_price": 0.0002, "best_bid_price": 0.0001,
              "best_ask_price": 0.0004, "greeks": {"delta": 0.05}},
        "S": {"mark_price": 0.0068, "best_bid_price": 0.0067,
              "best_ask_price": 0.0070, "greeks": {"delta": 0.3}},
    }
    calls = []
    EX.dbt_ticker = lambda inst: quotes[inst]
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}
    EX.dbt_order_book = lambda inst, depth=1: {"asks": [[0.0004, 0.1]]}

    def _place(side, inst, amt, price, **kwargs):
        calls.append((side, inst, amt, price, kwargs))
        return {"order": {"order_id": "p1", "order_state": "open",
                          "filled_amount": 0.0}}

    EX.dbt_place_order = _place
    EX.dbt_get_order_state = lambda oid: {"order": {"order_id": oid,
                                                    "order_state": "open",
                                                    "filled_amount": 0.0}}
    EX.dbt_cancel = lambda oid: {"order_id": oid}
    EX.Sleep = lambda ms: None
    EX.ENTRY_PROTECTION_TAKER_AFTER_SECONDS = 600

    r = EX.exec_entry_campaign_step(
        "P", "S", 0.1, credit_floor=0.0, max_tick_steps=3,
        attempt=20, prot_done_qty=0.0, short_done_qty=0.0,
        allow_live=True, label="entry", prot_order=None, now_ms=1000)

    assert r["prot_fill"] == 0.0 and len(calls) == 1
    assert calls[0][4]["post_only"] is True
    assert _approx(calls[0][3], 0.0002)
    _restore_ex()


def test_entry_protection_posts_persistent_maker_without_sleep_or_cancel():
    quotes = {
        "P": {"mark_price": 0.0002, "best_bid_price": 0.0001,
              "best_ask_price": 0.0003, "greeks": {"delta": 0.05}},
        "S": {"mark_price": 0.0068, "best_bid_price": 0.0067,
              "best_ask_price": 0.0070, "greeks": {"delta": 0.3}},
    }
    calls, cancels, sleeps = [], [], []
    EX.dbt_ticker = lambda inst: quotes[inst]
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}
    EX.dbt_place_order = lambda side, inst, amt, price, **kwargs: (
        calls.append((side, inst, amt, price, kwargs))
        or {"order": {"order_id": "p1", "order_state": "open", "filled_amount": 0.0}}
    )
    EX.dbt_get_order_state = lambda oid: {"order": {"order_id": oid, "order_state": "open",
                                                    "filled_amount": 0.0}}
    EX.dbt_cancel = lambda oid: cancels.append(oid) or {"order_id": oid}
    EX.Sleep = lambda ms: sleeps.append(ms)

    r = EX.exec_entry_campaign_step(
        "P", "S", 0.1, credit_floor=0.0, max_tick_steps=3,
        attempt=0, prot_done_qty=0.0, short_done_qty=0.0,
        allow_live=True, label="entry", prot_order=None, now_ms=1000)

    assert r["prot_fill"] == 0.0
    assert calls == [("buy", "P", 0.1, 0.0002,
                      {"post_only": True, "reject_post_only": True, "label": "entry_prot"})]
    assert cancels == [] and sleeps == []
    assert r["prot_order"]["order_id"] == "p1"
    assert r["prot_order"]["price"] == 0.0002
    assert r["prot_order"]["wait_start_ms"] == 1000
    assert r["prot_order"]["placed_ms"] == 1000
    _restore_ex()


def test_entry_protection_reuses_persistent_order_when_mark_unchanged():
    quotes = {
        "P": {"mark_price": 0.0002, "best_bid_price": 0.0001,
              "best_ask_price": 0.0003, "greeks": {"delta": 0.05}},
        "S": {"mark_price": 0.0068, "best_bid_price": 0.0067,
              "best_ask_price": 0.0070, "greeks": {"delta": 0.3}},
    }
    calls, cancels, states = [], [], []
    EX.dbt_ticker = lambda inst: quotes[inst]
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}
    EX.dbt_place_order = lambda *a, **k: calls.append((a, k)) or None
    EX.dbt_get_order_state = lambda oid: (
        states.append(oid)
        or {"order": {"order_id": oid, "order_state": "open", "filled_amount": 0.0}}
    )
    EX.dbt_cancel = lambda oid: cancels.append(oid) or {"order_id": oid}
    EX.Sleep = lambda ms: None
    prot_order = {"order_id": "p1", "instrument": "P", "price": 0.0002,
                  "amount": 0.1, "filled_seen": 0.0, "placed_ms": 1000,
                  "wait_start_ms": 1000, "label": "entry_prot"}

    r = EX.exec_entry_campaign_step(
        "P", "S", 0.1, credit_floor=0.0, max_tick_steps=3,
        attempt=1, prot_done_qty=0.0, short_done_qty=0.0,
        allow_live=True, label="entry", prot_order=prot_order, now_ms=4000)

    assert r["prot_fill"] == 0.0
    assert r["prot_order"]["order_id"] == "p1"
    assert r["prot_order"]["wait_start_ms"] == 1000
    assert states == ["p1"] and calls == [] and cancels == []
    assert r["fills"] == []
    _restore_ex()


def test_entry_protection_state_unknown_preserves_order_without_duplicate():
    quotes = {
        "P": {"mark_price": 0.0002, "best_bid_price": 0.0001,
              "best_ask_price": 0.0003, "greeks": {"delta": 0.05}},
        "S": {"mark_price": 0.0068, "best_bid_price": 0.0067,
              "best_ask_price": 0.0070, "greeks": {"delta": 0.3}},
    }
    calls, cancels = [], []
    EX.dbt_ticker = lambda inst: quotes[inst]
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}
    EX.dbt_place_order = lambda *a, **k: calls.append((a, k)) or None

    def _state(_oid):
        raise RuntimeError("temporary exchange state error")

    EX.dbt_get_order_state = _state
    EX.dbt_cancel = lambda oid: cancels.append(oid) or {"order_id": oid}
    EX.Sleep = lambda ms: None
    prot_order = {"order_id": "p1", "instrument": "P", "price": 0.0002,
                  "amount": 0.1, "filled_seen": 0.0, "placed_ms": 1000,
                  "wait_start_ms": 1000, "label": "entry_prot"}

    r = EX.exec_entry_campaign_step(
        "P", "S", 0.1, credit_floor=0.0, max_tick_steps=3,
        attempt=1, prot_done_qty=0.0, short_done_qty=0.0,
        allow_live=True, label="entry", prot_order=prot_order, now_ms=4000)

    assert r["reason"] == "ENTRY_STEP"
    assert r["prot_order"]["order_id"] == "p1"
    assert r["fills"] == []
    assert calls == [] and cancels == []
    _restore_ex()


def test_entry_protection_reprices_on_one_tick_mark_move_without_resetting_wait():
    quotes = {
        "P": {"mark_price": 0.0003, "best_bid_price": 0.0002,
              "best_ask_price": 0.0005, "greeks": {"delta": 0.05}},
        "S": {"mark_price": 0.0068, "best_bid_price": 0.0067,
              "best_ask_price": 0.0070, "greeks": {"delta": 0.3}},
    }
    calls, cancels, states = [], [], []
    EX.dbt_ticker = lambda inst: quotes[inst]
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}
    EX.dbt_place_order = lambda side, inst, amt, price, **kwargs: (
        calls.append((side, inst, amt, price, kwargs))
        or {"order": {"order_id": "p2", "order_state": "open", "filled_amount": 0.0}}
    )
    EX.dbt_get_order_state = lambda oid: (
        states.append(oid)
        or {"order": {"order_id": oid, "order_state": "open", "filled_amount": 0.0}}
    )
    EX.dbt_cancel = lambda oid: cancels.append(oid) or {"order_id": oid}
    EX.Sleep = lambda ms: None
    prot_order = {"order_id": "p1", "instrument": "P", "price": 0.0002,
                  "amount": 0.1, "filled_seen": 0.0, "placed_ms": 1000,
                  "wait_start_ms": 1000, "label": "entry_prot"}

    r = EX.exec_entry_campaign_step(
        "P", "S", 0.1, credit_floor=0.0, max_tick_steps=3,
        attempt=2, prot_done_qty=0.0, short_done_qty=0.0,
        allow_live=True, label="entry", prot_order=prot_order, now_ms=4000)

    assert states == ["p1", "p1"]
    assert cancels == ["p1"]
    assert calls[0][0:4] == ("buy", "P", 0.1, 0.0003)
    assert r["prot_order"]["order_id"] == "p2"
    assert r["prot_order"]["wait_start_ms"] == 1000
    assert r["prot_order"]["placed_ms"] == 4000
    _restore_ex()


def test_entry_protection_after_ten_minutes_takes_ask_when_depth_and_credit_pass():
    quotes = {
        "P": {"mark_price": 0.0002, "best_bid_price": 0.0001,
              "best_ask_price": 0.0009, "greeks": {"delta": 0.05}},
        "S": {"mark_price": 0.0068, "best_bid_price": 0.0067,
              "best_ask_price": 0.0070, "greeks": {"delta": 0.3}},
    }
    calls, cancels = [], []
    EX.dbt_ticker = lambda inst: quotes[inst]
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}
    EX.dbt_order_book = lambda inst, depth=1: {"asks": [[0.0009, 0.1]]}
    EX.dbt_place_order = lambda side, inst, amt, price, **kwargs: (
        calls.append((side, inst, amt, price, kwargs))
        or {"order": {"order_id": "t1", "order_state": "open", "filled_amount": 0.0}}
    )
    EX.dbt_get_order_state = lambda oid: (
        {"order": {"order_id": oid, "order_state": "filled",
                   "filled_amount": 0.1, "average_price": 0.0009}}
        if oid == "t1" else
        {"order": {"order_id": oid, "order_state": "open", "filled_amount": 0.0}}
    )
    EX.dbt_cancel = lambda oid: cancels.append(oid) or {"order_id": oid}
    EX.Sleep = lambda ms: None
    EX.ENTRY_PROTECTION_TAKER_AFTER_SECONDS = 600
    prot_order = {"order_id": "p1", "instrument": "P", "price": 0.0002,
                  "amount": 0.1, "filled_seen": 0.0, "placed_ms": 1000,
                  "wait_start_ms": 1000, "label": "entry_prot"}

    r = EX.exec_entry_campaign_step(
        "P", "S", 0.1, credit_floor=0.0, max_tick_steps=3,
        attempt=2, prot_done_qty=0.0, short_done_qty=0.0,
        allow_live=True, label="entry", prot_order=prot_order, now_ms=601000)

    assert cancels == ["p1"]
    assert calls[0][0:4] == ("buy", "P", 0.1, 0.0009)
    assert calls[0][4]["post_only"] is False
    assert r["prot_fill"] == 0.1
    assert r["prot_order"] is None
    _restore_ex()


def test_entry_protection_after_ten_minutes_reposts_maker_when_depth_fails():
    quotes = {
        "P": {"mark_price": 0.0002, "best_bid_price": 0.0001,
              "best_ask_price": 0.0009, "greeks": {"delta": 0.05}},
        "S": {"mark_price": 0.0068, "best_bid_price": 0.0067,
              "best_ask_price": 0.0070, "greeks": {"delta": 0.3}},
    }
    calls, cancels = [], []
    EX.dbt_ticker = lambda inst: quotes[inst]
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}
    EX.dbt_order_book = lambda inst, depth=1: {"asks": [[0.0009, 0.01]]}
    EX.dbt_place_order = lambda side, inst, amt, price, **kwargs: (
        calls.append((side, inst, amt, price, kwargs))
        or {"order": {"order_id": "p2", "order_state": "open", "filled_amount": 0.0}}
    )
    EX.dbt_get_order_state = lambda oid: {"order": {"order_id": oid, "order_state": "open",
                                                    "filled_amount": 0.0}}
    EX.dbt_cancel = lambda oid: cancels.append(oid) or {"order_id": oid}
    EX.Sleep = lambda ms: None
    EX.ENTRY_PROTECTION_TAKER_AFTER_SECONDS = 600
    prot_order = {"order_id": "p1", "instrument": "P", "price": 0.0002,
                  "amount": 0.1, "filled_seen": 0.0, "placed_ms": 1000,
                  "wait_start_ms": 1000, "label": "entry_prot"}

    r = EX.exec_entry_campaign_step(
        "P", "S", 0.1, credit_floor=0.0, max_tick_steps=3,
        attempt=2, prot_done_qty=0.0, short_done_qty=0.0,
        allow_live=True, label="entry", prot_order=prot_order, now_ms=601000)

    assert cancels == ["p1"]
    assert calls[0][0:4] == ("buy", "P", 0.1, 0.0002)
    assert calls[0][4]["post_only"] is True
    assert r["prot_order"]["order_id"] == "p2"
    assert r["prot_order"]["wait_start_ms"] == 1000
    _restore_ex()


def test_entry_protection_counts_only_new_partial_fill_from_persistent_order():
    quotes = {
        "P": {"mark_price": 0.0002, "best_bid_price": 0.0001,
              "best_ask_price": 0.0003, "greeks": {"delta": 0.05}},
        "S": {"mark_price": 0.0068, "best_bid_price": 0.0067,
              "best_ask_price": 0.0070, "greeks": {"delta": 0.3}},
    }
    EX.dbt_ticker = lambda inst: quotes[inst]
    EX.dbt_get_instrument = lambda inst: {"tick_size": 0.0001}
    EX.dbt_place_order = lambda *a, **k: {"order": {"order_id": "s1",
                                                    "order_state": "open",
                                                    "filled_amount": 0.0}}
    EX.dbt_get_order_state = lambda oid: (
        {"order": {"order_id": oid, "order_state": "open",
                   "filled_amount": 0.05, "average_price": 0.0002}}
        if oid == "p1" else
        {"order": {"order_id": oid, "order_state": "open", "filled_amount": 0.0}}
    )
    EX.dbt_cancel = lambda oid: {"order_id": oid}
    EX.Sleep = lambda ms: None
    prot_order = {"order_id": "p1", "instrument": "P", "price": 0.0002,
                  "amount": 0.1, "filled_seen": 0.02, "placed_ms": 1000,
                  "wait_start_ms": 1000, "label": "entry_prot"}

    r = EX.exec_entry_campaign_step(
        "P", "S", 0.1, credit_floor=0.0, max_tick_steps=3,
        attempt=2, prot_done_qty=0.02, short_done_qty=0.0,
        allow_live=True, label="entry", prot_order=prot_order, now_ms=4000)

    assert abs(r["prot_fill"] - 0.03) < 1e-12
    assert r["prot_order"]["filled_seen"] == 0.05
    _restore_ex()
