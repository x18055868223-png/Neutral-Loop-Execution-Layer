# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import binance_io as B
import execution as EX
import fmz_shim
import hedge_risk as HR
import strategy as ST


_ORIG_BNC_EX = fmz_shim.exchanges[1]
_MISSING = object()
_ORIG_ST = {k: getattr(ST, k, _MISSING) for k in (
    "RUN_PROFILE", "ALLOW_ENTRY_TRADING", "ALLOW_EXIT_TRADING", "ALLOW_HEDGE_TRADING",
    "KILL_NEW_RISK", "EMERGENCY_REDUCE_ONLY", "HEDGE_VENUE", "HEDGE_BINANCE_INSTRUMENT",
    "HEDGE_BINANCE_EXCHANGE_INDEX", "HEDGE_REDUCTION_RATIO", "HEDGE_MAX_SLIPPAGE_BPS",
    "HEDGE_POLICY_V313_ENABLED",
    "dbt_get_positions", "dbt_get_open_orders", "dbt_get_instrument", "exec_hedge_step",
    "bnc_get_position_btc", "bnc_get_position_snapshot", "exec_quote", "_spot_price", "_evaluate_hedge",
    "_evaluate_position_risk_now", "_evaluate_take_profit",
)}


def _restore():
    fmz_shim.exchanges[1] = _ORIG_BNC_EX
    fmz_shim._STORE.clear()
    for k, v in _ORIG_ST.items():
        if v is _MISSING:
            try:
                delattr(ST, k)
            except AttributeError:
                pass
        else:
            setattr(ST, k, v)
    ST.ledger_set_state(ST.S_NO_POSITION)


class _FakeBinance:
    def __init__(self):
        self.contract = None
        self.io_calls = []
        self.direction = None
        self.cancelled = []
        self.orders_seen = 0
        self.ticker = {"Buy": 59990.0, "Sell": 60000.0}

    def IO(self, *args):
        self.io_calls.append(args)
        return True

    def SetContractType(self, symbol):
        self.contract = symbol

    def GetTicker(self):
        return dict(self.ticker)

    def SetDirection(self, direction):
        self.direction = direction

    def Buy(self, price, amount):
        self.last_order = ("buy", price, amount)
        return {"id": "b1"}

    def Sell(self, price, amount):
        self.last_order = ("sell", price, amount)
        return {"id": "s1"}

    def GetOrder(self, oid):
        self.orders_seen += 1
        if self.orders_seen == 1:
            return {"Id": oid, "Status": 0, "DealAmount": 0.04, "AvgPrice": 60002.0}
        return {"Id": oid, "Status": 2, "DealAmount": 0.05, "AvgPrice": 60003.0}

    def CancelOrder(self, oid):
        self.cancelled.append(oid)
        return True


def test_binance_prompt_limit_buy_confirms_cancels_and_rechecks():
    fake = _FakeBinance()
    fmz_shim.exchanges[1] = fake
    B.Sleep = lambda _ms: None
    r = B.bnc_place_hedge("BTCUSDC", "buy", 0.10, reduce_only=False, allow_live=True,
                          execution_style="PROMPT_LIMIT", max_slippage_bps=5)
    assert fake.io_calls == [("currency", "BTC_USDC")]
    assert fake.contract == "swap" and fake.direction == "buy"
    assert abs(fake.last_order[1] - 60030.0) < 1e-9
    assert r["post_only"] is False and r["execution_style"] == "PROMPT_LIMIT"
    assert abs(r["filled"] - 0.05) < 1e-12 and abs(r["remaining"] - 0.05) < 1e-12
    assert r["cancelled"] is True and fake.cancelled == ["b1"]
    _restore()


def test_binance_prompt_limit_sell_reduce_uses_closebuy_direction():
    fake = _FakeBinance()
    fmz_shim.exchanges[1] = fake
    B.Sleep = lambda _ms: None
    r = B.bnc_place_hedge("BTCUSDC", "sell", 0.10, reduce_only=True, allow_live=True,
                          execution_style="PROMPT_LIMIT", max_slippage_bps=5)
    assert fake.direction == "closebuy"
    assert abs(fake.last_order[1] - 59960.0) < 1e-9
    assert r["reduce_only"] is True and r["post_only"] is False
    _restore()


def test_probability_policy_triggers_only_after_open_probability_and_drift():
    policy = HR.build_hedge_trigger_policy(0.20, 0.5)
    hold = HR.evaluate_hedge_trigger(
        "SHORT_CALL", {"entry_touch_probability": 0.20, "entry_loss_boundary": 61000},
        current_price=60500, probability_now=0.45, policy=policy)
    assert hold["tail_risk_state"] != HR.STATE_HEDGE_READY
    ready = HR.evaluate_hedge_trigger(
        "SHORT_CALL", {"entry_touch_probability": 0.20, "entry_loss_boundary": 61000},
        current_price=60500, probability_now=0.55, policy=policy)
    assert ready["tail_risk_state"] == HR.STATE_HEDGE_READY
    assert "TOUCH_PROBABILITY_DETERIORATED" in ready["reason_codes"]


def test_price_line_rechecks_but_does_not_open_without_probability_confirmation():
    policy = HR.build_hedge_trigger_policy(0.20, 0.5, hedge_price_line=60400)
    r = HR.evaluate_hedge_trigger(
        "SHORT_CALL", {"entry_touch_probability": 0.20, "entry_loss_boundary": 61000},
        current_price=60450, probability_now=0.42, policy=policy)
    assert r["price_line_touched"] is True
    assert r["tail_risk_state"] == HR.STATE_WATCH
    assert "PRICE_LINE_TOUCHED_RECHECK_NOT_CONFIRMED" in r["reason_codes"]


def test_strategy_hedge_target_uses_binance_actual_leg_quantities():
    ST.HEDGE_VENUE = "BINANCE"
    ST.HEDGE_POLICY_V313_ENABLED = False
    ST.HEDGE_REDUCTION_RATIO = 0.5
    ST.bnc_get_position_btc = lambda _symbol: 0.0
    ST.bnc_get_position_snapshot = lambda _symbol: {
        "qty": 0.0, "unrealized_pnl_usd": None}
    snap = {"side": "CALL", "remaining_short_qty": 0.05, "long_remaining_qty": 0.10,
            "short_instrument": "S", "long_instrument": "P"}
    q = {"S": {"delta": 0.35}, "P": {"delta": 0.10}}
    h = ST._evaluate_hedge(snap, lambda inst: q.get(inst, {}))
    assert h["venue"] == "BINANCE" and h["side"] == "buy"
    assert abs(h["net_option_delta"] - (-0.0075)) < 1e-12
    assert abs(h["target"] - 0.008) < 1e-12
    assert h["target_semantics"] == "RAW_FULL_DELTA"
    assert h["action"]["action"] == "HEDGE_OPEN"
    assert "maker_only" not in h["venue_cfg"]
    _restore()


def test_strategy_hedge_snapshot_carries_binance_unrealized_pnl_to_display():
    ST.HEDGE_VENUE = "BINANCE"
    ST.HEDGE_REDUCTION_RATIO = 0.5
    ST.bnc_get_position_snapshot = lambda _symbol: {
        "qty": -0.002, "unrealized_pnl_usd": 1.75}
    snap = {"side": "PUT", "remaining_short_qty": 0.05, "long_remaining_qty": 0.05,
            "short_instrument": "S", "long_instrument": "P"}
    q = {"S": {"delta": -0.35}, "P": {"delta": -0.10}}

    h = ST._evaluate_hedge(snap, lambda inst: q.get(inst, {}))
    detail = ST._build_hedge_detail(h, {"current_risk": {}, "reason_codes": []})

    assert h["perp_qty"] == -0.002
    assert h["unrealized_pnl_usd"] == 1.75
    assert detail["hedge_unrealized_pnl_usd"] == 1.75
    assert detail["hedge_pnl_state"] == "OK"
    _restore()


def test_manage_cycle_falls_back_to_binance_hedge_when_risk_exit_not_authorized():
    ST.RUN_PROFILE = "LIVE"
    ST.ALLOW_ENTRY_TRADING = False
    ST.ALLOW_EXIT_TRADING = True
    ST.ALLOW_HEDGE_TRADING = True
    ST.KILL_NEW_RISK = False
    ST.EMERGENCY_REDUCE_ONLY = False
    ST.HEDGE_POLICY_V313_ENABLED = False
    ST.HEDGE_VENUE = "BINANCE"
    ST.HEDGE_REDUCTION_RATIO = 0.5
    now = 1000000
    anchor = {"entry_touch_probability": 0.20, "entry_loss_boundary": 61000,
              "entry_dte_hours": 24, "entry_short_gamma": 0.00005}
    fmz_shim._G(ST._POSITION_KEY, {
        "position_id": "pos-hedge", "side": "CALL", "short_instrument": "S",
        "long_instrument": "P", "remaining_short_qty": 0.10, "long_remaining_qty": 0.10,
        "short_fill_amount": 0.10, "long_fill_amount": 0.10,
        "short_expiry_ts": now + 24 * 3600000, "entry_risk_anchor": anchor,
        "hedge_trigger_policy": HR.build_hedge_trigger_policy(0.20, 0.5),
        "entry_profit_ceiling_net": 0.001, "max_total_exit_spend": 0.0002,
        "realized_exit_spend": 0.0,
    })
    ST.dbt_get_positions = lambda *_a: []
    ST.dbt_get_open_orders = lambda *_a: []
    ST.bnc_get_position_btc = lambda _symbol: 0.0
    ST._spot_price = lambda: 60500.0
    def _quote(inst):
        if inst == "S":
            return {"delta": 0.65, "gamma": 0.00012, "mark_iv": 1.60,
                    "best_bid": 0.009, "best_ask": 0.030, "mark": 0.020, "tick": 0.0001}
        if inst == "P":
            return {"delta": 0.10, "best_bid": 0.001, "best_ask": 0.002,
                    "mark": 0.0015, "tick": 0.0001}
        return {}
    ST.exec_quote = _quote
    calls = []
    ST.exec_hedge_step = lambda *a, **k: calls.append((a, k)) or {
        "filled": 0.0, "dry": True, "reason": "HEDGE_DRYRUN"}
    out = ST.manage_cycle(now)
    assert out["arb"]["preferred_action"] == "EXIT_PREFERRED"
    assert out["arb"]["executable_action"] == "HEDGE_READY"
    assert calls and calls[0][0][0]["venue"] == "BINANCE"
    assert calls[0][1]["execution_style"] == "PROMPT_LIMIT"
    _restore()


def test_manage_cycle_allows_existing_hedge_reduce_when_hedge_gate_off():
    ST.RUN_PROFILE = "LIVE"
    ST.ALLOW_ENTRY_TRADING = False
    ST.ALLOW_EXIT_TRADING = True
    ST.ALLOW_HEDGE_TRADING = False
    ST.KILL_NEW_RISK = False
    ST.EMERGENCY_REDUCE_ONLY = False
    ST.HEDGE_POLICY_V313_ENABLED = False
    fmz_shim._G(ST._POSITION_KEY, {
        "position_id": "pos-reduce", "side": "CALL", "short_instrument": "S",
        "long_instrument": "P", "remaining_short_qty": 0.10, "long_remaining_qty": 0.10,
        "entry_profit_ceiling_net": 0.001, "max_total_exit_spend": 0.0002,
        "realized_exit_spend": 0.0,
    })
    ST.dbt_get_positions = lambda *_a: []
    ST.dbt_get_open_orders = lambda *_a: []
    ST._evaluate_take_profit = lambda *_a, **_k: {
        "qualified": False, "remaining_short_qty": 0.10,
        "remaining_budget": 0.0001, "price_cap": 0.001, "quote_ok": True,
        "ratio": 0.0,
    }
    ST._evaluate_hedge = lambda *_a, **_k: {
        "perp_qty": 0.02, "target": 0.01, "orphan": False, "side": "sell",
        "venue": "BINANCE", "instrument": "BTCUSDC",
        "venue_cfg": {"venue": "BINANCE", "instrument": "BTCUSDC", "linear": True, "exchange_index": 1},
        "action": {"action": "HEDGE_REDUCE", "reduce_only": True, "delta_contracts": 0.01},
    }
    ST._evaluate_position_risk_now = lambda *_a, **_k: {
        "tail_risk_state": HR.STATE_HEDGE_READY,
        "current_risk": {},
        "reason_codes": ["TOUCH_PROBABILITY_DETERIORATED"],
    }
    calls = []
    ST.exec_hedge_step = lambda *a, **k: calls.append((a, k)) or {
        "filled": 0.0, "dry": True, "reason": "HEDGE_DRYRUN"}

    out = ST.manage_cycle(1000000)

    assert out["arb"]["executable_action"] == "HEDGE_READY"
    assert calls and calls[0][0][3] is True
    _restore()
