# -*- coding: utf-8 -*-
import json
import os
import sys
import time
from urllib.parse import parse_qs

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import fmz_shim
import strategy as ST


H = 3600000
SPOT = 73400.0


def _tables_from_status(text):
    assert "`" in text
    raw = text.split("`", 1)[1].rsplit("`", 1)[0]
    return json.loads(raw)


def _rows_by_title(status_text, title):
    table = next(t for t in _tables_from_status(status_text) if t["title"] == title)
    return {r[0]: r[1:] for r in table["rows"]}


def _query_dict(query):
    if isinstance(query, dict):
        return query
    if not query:
        return {}
    parsed = parse_qs(str(query), keep_blank_values=True)
    return {k: (v[-1] if isinstance(v, list) and v else v) for k, v in parsed.items()}


class LifecycleHarness:
    def __init__(self):
        self.logs = []
        self.statuses = []
        self.deribit_orders = []
        self.deribit_cancels = []
        self.deribit_order_states = {}
        self.deribit_order_scripts = {}
        self.deribit_order_state_sequences = {}
        self.option_positions = []
        self.open_orders = []
        self.ticker_by_inst = {}
        self.market_context = None
        self.binance = _MatrixBinance(0.0)
        self._orig_exchange_1 = fmz_shim.exchanges[1]
        self._orig = {name: getattr(ST, name) for name in (
            "RUN_PROFILE", "MANUAL_PLANNING_ALLOWED", "ALLOW_ENTRY_TRADING",
            "ALLOW_EXIT_TRADING", "ALLOW_HEDGE_TRADING", "DRY_RUN_PASSED",
            "DIRECTION_BIAS", "TARGET_DTE_HOURS", "SHORT_DELTA_RANGE",
            "PROTECTION_WIDTH_RANGE", "ORDER_AMOUNT", "MENU_SIZE",
            "HEDGE_VENUE", "HEDGE_BINANCE_INSTRUMENT",
            "fetch_gex_vrp_context", "Log", "LogStatus")}

    def install(self, profile="TEST"):
        fmz_shim._STORE.clear()
        fmz_shim._commands.clear()
        ST.RUN_PROFILE = profile
        ST.MANUAL_PLANNING_ALLOWED = True
        ST.ALLOW_ENTRY_TRADING = profile == "LIVE"
        ST.ALLOW_EXIT_TRADING = profile == "LIVE"
        ST.ALLOW_HEDGE_TRADING = profile == "LIVE"
        ST.DRY_RUN_PASSED = profile == "LIVE"
        ST.DIRECTION_BIAS = "SHORT_CALL"
        ST.TARGET_DTE_HOURS = 24
        ST.SHORT_DELTA_RANGE = (0.15, 0.45)
        ST.PROTECTION_WIDTH_RANGE = (2000, 2500)
        ST.ORDER_AMOUNT = 0.1
        ST.MENU_SIZE = 6
        ST.HEDGE_VENUE = "BINANCE"
        ST.HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"
        ST.fetch_gex_vrp_context = self._fetch_market_context
        ST.Log = lambda *args: self.logs.append(" ".join(str(a) for a in args))
        ST.LogStatus = lambda *args: self.statuses.append(" ".join(str(a) for a in args))
        fmz_shim.exchange.io_handler = self._deribit_io
        fmz_shim.exchanges[1] = self.binance
        ST.ledger_set_state(ST.S_NO_POSITION)
        return self

    def restore(self):
        for name, value in self._orig.items():
            setattr(ST, name, value)
        fmz_shim.exchanges[1] = self._orig_exchange_1
        fmz_shim._STORE.clear()
        fmz_shim._commands.clear()
        ST.ledger_set_state(ST.S_NO_POSITION)

    def run(self, now_ms=None):
        return ST.run_cycle(now_ms or int(time.time() * 1000))

    def latest_status(self):
        assert self.statuses
        return self.statuses[-1]

    def enable_valid_market_context(self):
        self.market_context = {
            "source": "GEX_MONITOR_IV_RV_RANK",
            "side": "SHORT_CALL",
            "iv_rv_ratio": 0.8,
            "iv_rv_rank_pct": 15.2,
        }
        self.ticker_by_inst.update({
            "BTC-S-76000-C": {
                "mark_price": 0.008,
                "best_bid_price": 0.0078,
                "best_ask_price": 0.0082,
                "underlying_price": SPOT,
                "greeks": {"delta": 0.30, "gamma": 0.00005, "vega": 0.01},
                "mark_iv": 0.90,
            },
            "BTC-S-78000-C": {
                "mark_price": 0.0035,
                "best_bid_price": 0.0034,
                "best_ask_price": 0.0036,
                "underlying_price": SPOT,
                "greeks": {"delta": 0.15, "gamma": 0.00003, "vega": 0.01},
                "mark_iv": 0.88,
            },
        })
        return self

    def push_command(self, raw):
        fmz_shim._commands.append(raw)

    def script_deribit_order(self, side, instrument, states):
        key = (side, instrument)
        self.deribit_order_scripts.setdefault(key, []).append([dict(s) for s in states])

    def _next_order_script(self, side, instrument):
        scripts = self.deribit_order_scripts.get((side, instrument)) or []
        if not scripts:
            return []
        return scripts.pop(0)

    def _scripted_order_state(self, oid):
        seq = self.deribit_order_state_sequences.get(oid)
        if not seq:
            return self.deribit_order_states.get(oid)
        if len(seq) > 1:
            state = seq.pop(0)
        else:
            state = seq[0]
        base = dict(self.deribit_order_states.get(oid) or {})
        base.update(state)
        base.setdefault("order_id", oid)
        self.deribit_order_states[oid] = base
        return base

    def _fetch_market_context(self, *_a, **_k):
        if self.market_context:
            return {
                "valid": True,
                "status": "VRP_CONTEXT_VALID",
                "market_context": dict(self.market_context),
            }
        return {"valid": False, "status": "VRP_CONTEXT_MISSING", "market_context": None}

    def _deribit_io(self, _ex, _method, path, query):
        q = _query_dict(query)
        if path.endswith("/private/buy") or path.endswith("/private/sell"):
            side = "buy" if path.endswith("/private/buy") else "sell"
            inst = q.get("instrument_name")
            script = self._next_order_script(side, inst)
            oid = "matrix-%s-%d" % (side, len(self.deribit_orders) + 1)
            self.deribit_orders.append((side, dict(q)))
            order = {
                "order_id": oid,
                "order_state": "open",
                "filled_amount": 0.0,
                "average_price": q.get("price"),
            }
            self.deribit_order_states[oid] = order
            if script:
                self.deribit_order_state_sequences[oid] = script
            return {"result": {"order": order}}
        if path.endswith("/private/get_order_state"):
            oid = q.get("order_id")
            return {"result": {"order": self._scripted_order_state(oid)}}
        if path.endswith("/private/cancel"):
            oid = q.get("order_id")
            self.deribit_cancels.append(oid)
            return {"result": {"order": self.deribit_order_states.get(oid)}}
        if path.endswith("/public/get_index_price"):
            return {"result": {"index_price": SPOT}}
        if path.endswith("/public/get_instruments"):
            now = int(time.time() * 1000)
            return {"result": [
                {"instrument_name": "BTC-S-76000-C", "strike": 76000,
                 "option_type": "call", "expiration_timestamp": now + 48 * H,
                 "kind": "option", "tick_size": 0.0001},
                {"instrument_name": "BTC-S-78000-C", "strike": 78000,
                 "option_type": "call", "expiration_timestamp": now + 48 * H,
                 "kind": "option", "tick_size": 0.0001},
            ]}
        if path.endswith("/public/ticker"):
            inst = q.get("instrument_name")
            if inst in self.ticker_by_inst:
                return {"result": dict(self.ticker_by_inst[inst])}
            return {"result": {"mark_price": 0.008, "best_bid_price": 0.0078,
                               "best_ask_price": 0.0082,
                               "underlying_price": SPOT,
                               "greeks": {"delta": 0.30, "gamma": 0.00005,
                                           "vega": 0.01},
                               "mark_iv": 0.90}}
        if path.endswith("/public/get_instrument"):
            return {"result": {"tick_size": 0.0001, "contract_size": 1,
                               "min_trade_amount": 0.1}}
        if path.endswith("/private/get_account_summary"):
            return {"result": {"margin_model": "segregated_pm",
                               "portfolio_margining_enabled": True,
                               "initial_margin": 0.02,
                               "maintenance_margin": 0.015}}
        if path.endswith("/private/get_positions"):
            return {"result": self.option_positions}
        if path.endswith("/private/get_open_orders"):
            return {"result": self.open_orders}
        if path.endswith("/private/get_open_orders_by_currency"):
            return {"result": self.open_orders}
        if path.endswith("/private/simulate_portfolio"):
            return {"result": {"initial_margin": 0.013,
                               "maintenance_margin": 0.0104,
                               "available_funds": 1.0}}
        return {"result": None}


class _MatrixBinance:
    def __init__(self, qty=0.0, lifecycle=True, position_gap=False):
        self.qty = qty
        self.lifecycle = lifecycle
        self.position_gap = position_gap
        self.missing_order_id = False
        self.order_states = {}
        self.orders = []
        self.direction = None
        self.contract = None

    def IO(self, *args):
        return True

    def SetContractType(self, contract):
        self.contract = contract
        return True

    def GetPosition(self):
        if self.position_gap:
            return None
        if abs(self.qty) <= 1e-12:
            return []
        typ = 0 if self.qty > 0 else 1
        return [{"Type": typ, "Amount": abs(self.qty)}]

    def GetTicker(self):
        return {"Buy": 59990.0, "Sell": 60000.0}

    def SetDirection(self, direction):
        self.direction = direction
        return True

    def Buy(self, price, amount):
        self.orders.append(("buy", price, amount))
        if self.missing_order_id:
            return {}
        return {"id": "matrix-binance-buy"}

    def Sell(self, price, amount):
        self.orders.append(("sell", price, amount))
        if self.missing_order_id:
            return {}
        return {"id": "matrix-binance-sell"}

    def GetOrder(self, oid):
        if not self.lifecycle:
            raise AttributeError("GetOrder unavailable")
        if oid in self.order_states:
            return dict(self.order_states[oid])
        return {"Id": oid, "Status": 0, "DealAmount": 0.0}

    def CancelOrder(self, oid):
        if not self.lifecycle:
            raise AttributeError("CancelOrder unavailable")
        return True


def _active_snapshot(now_ms=None):
    now_ms = now_ms or int(time.time() * 1000)
    return {
        "position_id": "matrix-pos",
        "side": "CALL",
        "short_instrument": "BTC-S-76000-C",
        "long_instrument": "BTC-S-78000-C",
        "remaining_short_qty": 0.1,
        "long_remaining_qty": 0.1,
        "short_fill_amount": 0.1,
        "long_fill_amount": 0.1,
        "short_fill_price": 0.008,
        "long_fill_price": 0.0035,
        "entry_profit_ceiling_net": 0.00044,
        "target_profit_amount": 0.000352,
        "max_total_exit_spend": 0.000088,
        "realized_exit_spend": 0.0,
        "short_expiry_ts": now_ms + 48 * H,
        "entry_risk_anchor": {"entry_price": SPOT, "entry_dte_hours": 48,
                              "entry_loss_boundary": 77000,
                              "entry_touch_probability": 0.10},
    }


def _lock_first_live_plan(h, now_ms):
    first = h.run(now_ms)
    assert first["pending_candidates"]
    code = first["pending_candidates"][0]["confirm_code"]
    h.push_command("EXECUTE:" + code)
    return first, code


def _hedge_ready_snapshot(now_ms):
    snap = _active_snapshot(now_ms)
    snap["entry_risk_anchor"] = {
        "entry_price": 70000,
        "entry_dte_hours": 48,
        "entry_loss_boundary": 70000,
        "entry_touch_probability": 0.20,
        "hedge_trigger_policy": {
            "base_touch_probability": 0.20,
            "soft_delta": 0.01,
            "hard_delta": 0.10,
            "native_trigger": False,
        },
    }
    snap["hedge_trigger_policy"] = snap["entry_risk_anchor"]["hedge_trigger_policy"]
    return snap


def _install_hedge_fallback_position(h, now_ms):
    snap = _hedge_ready_snapshot(now_ms)
    h.ticker_by_inst[snap["short_instrument"]] = {
        "mark_price": 0.004,
        "best_bid_price": 0.0039,
        "best_ask_price": 0.020,
        "best_ask_amount": 0.2,
        "underlying_price": SPOT,
        "greeks": {"delta": 0.35, "gamma": 0.00005, "vega": 0.01},
        "mark_iv": 0.95,
    }
    h.ticker_by_inst[snap["long_instrument"]] = {
        "mark_price": 0.003,
        "best_bid_price": 0.0028,
        "best_ask_price": 0.0032,
        "underlying_price": SPOT,
        "greeks": {"delta": 0.10, "gamma": 0.00002, "vega": 0.01},
        "mark_iv": 0.90,
    }
    fmz_shim._G(ST._POSITION_KEY, snap)
    ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)
    return snap


def _install_soft_hedge_position(h, now_ms, final3=False):
    snap = _active_snapshot(now_ms)
    snap["entry_risk_anchor"] = {
        "entry_price": SPOT,
        "entry_dte_hours": 1 if final3 else 48,
        "entry_loss_boundary": 74500 if final3 else 77000,
        "entry_touch_probability": 0.20,
        "hedge_trigger_policy": {
            "base_touch_probability": 0.20,
            "watch_probability": 0.25,
            "open_probability": 0.30,
            "emergency_probability": 0.80,
            "min_probability_drift_to_open": 0.10,
            "native_trigger": False,
        },
    }
    snap["hedge_trigger_policy"] = snap["entry_risk_anchor"]["hedge_trigger_policy"]
    if final3:
        snap["short_expiry_ts"] = now_ms + H
        snap["long_expiry_ts"] = now_ms + H
    mark_iv = 1.5 if final3 else 0.70
    h.ticker_by_inst[snap["short_instrument"]] = {
        "mark_price": 0.004,
        "best_bid_price": 0.0039,
        "best_ask_price": 0.020,
        "best_ask_amount": 0.2,
        "underlying_price": SPOT,
        "greeks": {"delta": 0.35, "gamma": 0.00005, "vega": 0.01},
        "mark_iv": mark_iv,
    }
    h.ticker_by_inst[snap["long_instrument"]] = {
        "mark_price": 0.003,
        "best_bid_price": 0.0028,
        "best_ask_price": 0.0032,
        "underlying_price": SPOT,
        "greeks": {"delta": 0.10, "gamma": 0.00002, "vega": 0.01},
        "mark_iv": mark_iv,
    }
    fmz_shim._G(ST._POSITION_KEY, snap)
    ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)
    return snap


def _install_reduce_hedge_position(h, now_ms):
    snap = _active_snapshot(now_ms)
    snap["entry_risk_anchor"] = {
        "entry_price": SPOT,
        "entry_dte_hours": 48,
        "entry_loss_boundary": 80000,
        "entry_touch_probability": 0.20,
        "hedge_trigger_policy": {
            "base_touch_probability": 0.20,
            "watch_probability": 0.40,
            "open_probability": 0.50,
            "emergency_probability": 0.80,
            "min_probability_drift_to_open": 0.20,
            "native_trigger": False,
        },
    }
    snap["hedge_trigger_policy"] = snap["entry_risk_anchor"]["hedge_trigger_policy"]
    h.ticker_by_inst[snap["short_instrument"]] = {
        "mark_price": 0.004,
        "best_bid_price": 0.0039,
        "best_ask_price": 0.020,
        "best_ask_amount": 0.2,
        "underlying_price": SPOT,
        "greeks": {"delta": 0.10, "gamma": 0.00001, "vega": 0.01},
        "mark_iv": 0.30,
    }
    h.ticker_by_inst[snap["long_instrument"]] = {
        "mark_price": 0.003,
        "best_bid_price": 0.0028,
        "best_ask_price": 0.0032,
        "underlying_price": SPOT,
        "greeks": {"delta": 0.05, "gamma": 0.00001, "vega": 0.01},
        "mark_iv": 0.30,
    }
    h.binance.qty = 0.01
    fmz_shim._G(ST._POSITION_KEY, snap)
    ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)
    st = ST._hedge_policy_state(snap)
    st["reduce_since_ts"] = now_ms - int(ST.HEDGE_REDUCE_PERSIST_SECONDS * 1000) - 1000
    st["last_action"] = "REDUCE"
    ST._hedge_policy_save_state(st)
    return snap


def _assert_status_has_cn_reason_without_raw(status, raw_reason):
    reason_cn = ST.disp_reason_cn(raw_reason)
    assert reason_cn != raw_reason
    assert reason_cn in status
    assert raw_reason not in status


def _expired_settlement_snapshot(now_ms, include_settlement_price=True):
    snap = _active_snapshot(now_ms)
    expiry = now_ms - ST.SETTLEMENT_RECONCILE_GRACE_MS - 1000
    snap.update({
        "short_expiry_ts": expiry,
        "long_expiry_ts": expiry,
        "short_strike": 76000.0,
        "long_strike": 78000.0,
        "breakeven": 76000.0,
        "entry_profit_ceiling_net": 0.004,
        "entry_execution_report": {
            "actual_net_credit_after_fees": 0.004,
            "total_short_credit": 0.00080,
            "total_protection_cost": 0.00035,
            "total_fee_estimate": 0.00001,
            "fill_count": 2,
        },
    })
    if include_settlement_price:
        snap["settlement_index_price"] = 79000.0
        snap["settlement_price_source"] = "EXCHANGE_SETTLEMENT"
    return snap


def _install_settlement_position(h, now_ms, option_positions, binance_qty=0.0,
                                 include_settlement_price=True):
    snap = _expired_settlement_snapshot(now_ms, include_settlement_price)
    h.option_positions = option_positions
    h.binance.qty = binance_qty
    h.ticker_by_inst[snap["long_instrument"]] = {
        "mark_price": 0.0,
        "best_bid_price": 0.0,
        "best_ask_price": 0.001,
        "underlying_price": SPOT,
        "greeks": {"delta": 0.0, "gamma": 0.0, "vega": 0.0},
        "mark_iv": 0.50,
    }
    fmz_shim._G(ST._POSITION_KEY, snap)
    ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)
    return snap


def _assert_settlement_display_chinese_first(status):
    tables = _tables_from_status(status)
    table = next(
        t for t in tables
        if t["title"] in ("记账/对账/恢复", "璁拌处/瀵硅处/鎭㈠")
    )
    rows = {r[0]: r[1:] for r in table["rows"]}
    joined = json.dumps(rows, ensure_ascii=False)
    assert "Settlement" not in joined
    assert "Protection recovery" not in joined
    assert "Option realized PnL" not in joined
    assert "Final option PnL" not in joined
    assert "status=" not in joined
    assert "交割结算" in joined
    assert "保护腿回收" in joined
    assert "期权已实现PnL" in joined
    assert "最终期权PnL" in joined


def test_matrix_001_test_plan_phase_status_says_no_real_trading_and_no_orders():
    h = LifecycleHarness().install("TEST")
    try:
        ctx = h.run()
        status = h.latest_status()
        overview = _rows_by_title(status, "运行概览")

        assert ctx["console_phase"] == "PLAN_MENU_READY"
        assert ST.ledger_get_state() == ST.S_NO_POSITION
        assert h.deribit_orders == []
        assert "测试模式" in overview["RUN_PROFILE"][0]
        assert "不会真实下单" in overview["RUN_PROFILE"][0]
    finally:
        h.restore()


def test_matrix_002_live_plan_phase_status_shows_action_gates_in_chinese():
    h = LifecycleHarness().install("LIVE")
    try:
        ctx = h.run()
        status = h.latest_status()
        overview = _rows_by_title(status, "运行概览")

        assert ctx["console_phase"] == "PLAN_MENU_READY"
        assert "LIVE" in overview["RUN_PROFILE"][0]
        assert "实盘清单就绪" in overview["RUN_PROFILE"][0]
        assert "进场✓" in overview["执行门控"][0]
        assert "退出✓" in overview["执行门控"][0]
        assert "对冲开✓" in overview["执行门控"][0]
        assert h.deribit_orders == []
    finally:
        h.restore()


def test_matrix_003_test_take_profit_position_never_submits_exit_order():
    h = LifecycleHarness().install("TEST")
    now = int(time.time() * 1000)
    try:
        snap = _active_snapshot(now)
        snap["entry_profit_ceiling_net"] = 0.002
        snap["target_profit_amount"] = 0.0016
        snap["max_total_exit_spend"] = 0.0004
        h.ticker_by_inst[snap["short_instrument"]] = {
            "mark_price": 0.0002,
            "best_bid_price": 0.0001,
            "best_ask_price": 0.0002,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.10, "gamma": 0.00001, "vega": 0.01},
            "mark_iv": 0.70,
        }
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

        ctx = h.run(now)
        status = h.latest_status()
        titles = [t["title"] for t in _tables_from_status(status)]

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["take_profit_detail"]["qualified"] is True
        assert ctx["action_arb"]["preferred_action"] == "TAKE_PROFIT_READY"
        assert ctx["action_arb"]["executable_action"] == "HOLD"
        assert ctx["action_arb"]["blocked_reason"] == "EXIT_NOT_EXECUTABLE"
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert "固定备选方案库" not in titles
        assert any("止盈" in title and "退出" in title for title in titles)
        assert "测试模式" in status and "不会真实下单" in status
    finally:
        h.restore()


def test_matrix_004_test_short_flat_long_residual_never_submits_recovery_order():
    h = LifecycleHarness().install("TEST")
    now = int(time.time() * 1000)
    try:
        snap = _active_snapshot(now)
        snap["remaining_short_qty"] = 0.0
        snap["short_fill_amount"] = 0.0
        snap["long_remaining_qty"] = 0.1
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.001,
            "best_bid_price": 0.0009,
            "best_ask_price": 0.0011,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.05, "gamma": 0.00001, "vega": 0.01},
            "mark_iv": 0.70,
        }
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_FLAT_LONG_RESIDUAL)

        ctx = h.run(now)
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["exit_campaign_state"] in ("WORKING_LONG", "LONG_RESIDUAL_ONLY")
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert "保护" in status
        assert "测试模式" in status and "不会真实下单" in status
    finally:
        h.restore()


def test_matrix_005_test_hedge_ready_position_never_submits_binance_order():
    h = LifecycleHarness().install("TEST")
    now = int(time.time() * 1000)
    try:
        snap = _active_snapshot(now)
        snap["entry_risk_anchor"] = {
            "entry_price": 70000,
            "entry_dte_hours": 48,
            "entry_loss_boundary": 70000,
            "entry_touch_probability": 0.20,
            "hedge_trigger_policy": {
                "base_touch_probability": 0.20,
                "soft_delta": 0.01,
                "hard_delta": 0.10,
                "native_trigger": False,
            },
        }
        snap["hedge_trigger_policy"] = snap["entry_risk_anchor"]["hedge_trigger_policy"]
        h.ticker_by_inst[snap["short_instrument"]] = {
            "mark_price": 0.010,
            "best_bid_price": 0.0098,
            "best_ask_price": 0.0102,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.35, "gamma": 0.00005, "vega": 0.01},
            "mark_iv": 0.95,
        }
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.003,
            "best_bid_price": 0.0028,
            "best_ask_price": 0.0032,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.10, "gamma": 0.00002, "vega": 0.01},
            "mark_iv": 0.90,
        }
        h.binance.qty = 0.0
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

        ctx = h.run(now)
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["risk_state"] == ST.STATE_HEDGE_READY
        assert h.binance.orders == []
        assert h.deribit_orders == []
        assert "对冲" in status
        assert "测试模式" in status and "不会真实下单" in status
    finally:
        h.restore()


def test_matrix_006_test_orphan_hedge_cleanup_is_dryrun_only():
    h = LifecycleHarness().install("TEST")
    now = int(time.time() * 1000)
    try:
        h.binance.qty = -0.02

        verdict = ST.startup_recovery_check("BTC")
        ctx = h.run(now)
        status = h.latest_status()

        assert verdict["state"] == "ORPHAN_HEDGE_EMERGENCY"
        assert verdict["auto_cleanup_allowed"] is True
        assert ctx["console_phase"] == "ORPHAN_HEDGE_AUTO_CLEANUP"
        assert ctx["orphan_hedge_cleanup_step"]["reason"] == "BINANCE_HEDGE_DRYRUN"
        assert ctx["orphan_hedge_cleanup_step"]["dry"] is True
        assert h.binance.orders == []
        assert "测试模式：仅模拟自动只减清理，不会真实下单" in status
    finally:
        h.restore()


def test_matrix_007_live_valid_confirm_code_locks_plan_without_entry_gate_order():
    h = LifecycleHarness().install("LIVE").enable_valid_market_context()
    now = int(time.time() * 1000)
    try:
        ST.ALLOW_ENTRY_TRADING = False
        first = h.run(now)
        code = first["pending_candidates"][0]["confirm_code"]

        h.push_command("EXECUTE:" + code)
        locked = h.run(now + 1000)
        status = h.latest_status()

        assert first["console_phase"] == "HARD_APPROVAL_WAIT"
        assert locked["last_command"] == "EXECUTE"
        assert locked["last_command_outcome"] == "locked"
        assert locked["console_phase"] == "PLAN_LOCKED"
        assert fmz_shim._G(ST._LOCKED_KEY)["confirm_code"] == code
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert "方案已锁定" in status or "方案锁定" in status
        assert "预提交" in status
    finally:
        h.restore()


def test_matrix_008_wrong_confirm_code_does_not_lock_or_order():
    h = LifecycleHarness().install("LIVE").enable_valid_market_context()
    now = int(time.time() * 1000)
    try:
        ST.ALLOW_ENTRY_TRADING = False
        first = h.run(now)
        assert first["pending_candidates"]

        h.push_command("EXECUTE:ZZZZ")
        rejected = h.run(now + 1000)
        status = h.latest_status()

        assert rejected["last_command"] == "EXECUTE"
        assert rejected["last_command_outcome"] == "confirm_code_invalid_or_stale"
        assert fmz_shim._G(ST._LOCKED_KEY) is None
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert "确认码无效" in status or "确认码已失效" in status
    finally:
        h.restore()


def test_matrix_009_unknown_active_option_order_blocks_precommit_in_chinese():
    h = LifecycleHarness().install("LIVE").enable_valid_market_context()
    now = int(time.time() * 1000)
    try:
        first = h.run(now)
        cand = first["pending_candidates"][0]
        short_inst = first["menu"][0]["short_instrument"]
        h.open_orders = [{
            "order_id": "unknown-option-1",
            "instrument_name": short_inst,
            "label": "",
        }]

        h.push_command("执行:" + cand["confirm_code"])
        blocked = h.run(now + 1000)
        status = h.latest_status()

        assert blocked["last_command_outcome"] == "locked"
        assert blocked["console_phase"] == "PLAN_LOCKED"
        assert blocked["precommit"]["passed"] is False
        assert "no_unknown_orders" in blocked["precommit"]["failed"]
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert "未知活动订单" in status
        assert "no_unknown_orders" in status
    finally:
        h.restore()


def test_matrix_010_live_entry_protection_and_short_fill_freezes_snapshot():
    h = LifecycleHarness().install("LIVE").enable_valid_market_context()
    now = int(time.time() * 1000)
    try:
        _lock_first_live_plan(h, now)
        h.script_deribit_order("buy", "BTC-S-78000-C", [
            {"order_state": "filled", "filled_amount": 0.1, "average_price": 0.0036},
        ])
        h.script_deribit_order("sell", "BTC-S-76000-C", [
            {"order_state": "filled", "filled_amount": 0.1, "average_price": 0.0078},
        ])

        placed = h.run(now + 1000)
        assert placed["console_phase"] == "PLAN_LOCKED"
        ctx = h.run(now + 2000)
        snap = fmz_shim._G(ST._POSITION_KEY)
        status = h.latest_status()
        titles = [t["title"] for t in _tables_from_status(status)]

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ST.ledger_get_state() == ST.S_SHORT_ACTIVE_PROTECTED
        assert fmz_shim._G(ST._LOCKED_KEY) is None
        assert snap["remaining_short_qty"] == 0.1
        assert snap["long_remaining_qty"] == 0.1
        assert snap["entry_execution_report"]["fill_count"] == 2
        assert [o[0] for o in h.deribit_orders] == ["buy", "sell"]
        assert h.binance.orders == []
        assert "固定备选方案库" not in titles
        assert "持仓总览" in titles
        assert "持仓管理" in status
        assert "已保护" in status or "已建仓" in status
    finally:
        h.restore()


def test_matrix_011_live_protection_fill_short_not_filled_keeps_lock_and_reads_safe():
    h = LifecycleHarness().install("LIVE").enable_valid_market_context()
    now = int(time.time() * 1000)
    try:
        _lock_first_live_plan(h, now)
        h.script_deribit_order("buy", "BTC-S-78000-C", [
            {"order_state": "filled", "filled_amount": 0.1, "average_price": 0.0036},
        ])
        h.script_deribit_order("sell", "BTC-S-76000-C", [
            {"order_state": "open", "filled_amount": 0.0, "average_price": None},
        ])

        placed = h.run(now + 1000)
        assert placed["console_phase"] == "PLAN_LOCKED"
        ctx = h.run(now + 2000)
        locked = fmz_shim._G(ST._LOCKED_KEY)
        status = h.latest_status()

        assert ctx["console_phase"] == "PLAN_LOCKED"
        assert locked is not None
        assert locked["entry"]["prot_done"] == 0.1
        assert locked["entry"]["short_done"] == 0.0
        assert fmz_shim._G(ST._POSITION_KEY) is None
        assert ST.ledger_get_state() == ST.S_NO_POSITION
        assert len(h.deribit_orders) == 2
        assert h.binance.orders == []
        assert "保护腿已成交" in status
        assert "卖方腿未成交" in status
        assert "未形成期权空头" in status or "不会裸卖" in status
    finally:
        h.restore()


def test_matrix_012_live_short_partial_fill_enters_partial_vertical_manage():
    h = LifecycleHarness().install("LIVE").enable_valid_market_context()
    now = int(time.time() * 1000)
    try:
        _lock_first_live_plan(h, now)
        h.script_deribit_order("buy", "BTC-S-78000-C", [
            {"order_state": "filled", "filled_amount": 0.1, "average_price": 0.0036},
        ])
        h.script_deribit_order("sell", "BTC-S-76000-C", [
            {"order_state": "open", "filled_amount": 0.05, "average_price": 0.0078},
        ])

        placed = h.run(now + 1000)
        assert placed["console_phase"] == "PLAN_LOCKED"
        ctx = h.run(now + 2000)
        snap = fmz_shim._G(ST._POSITION_KEY)
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ST.ledger_get_state() == ST.S_SHORT_ACTIVE_PROTECTED
        assert fmz_shim._G(ST._LOCKED_KEY) is None
        assert snap["entry_completion_state"] == "PARTIAL_VERTICAL"
        assert snap["remaining_short_qty"] == 0.05
        assert snap["long_remaining_qty"] == 0.1
        assert h.binance.orders == []
        assert "开仓部分成交" in status or "部分垂直" in status
        assert "0.05" in status
    finally:
        h.restore()


def test_matrix_013_live_protection_order_pending_across_loops_no_duplicate_order():
    h = LifecycleHarness().install("LIVE").enable_valid_market_context()
    now = int(time.time() * 1000)
    try:
        _lock_first_live_plan(h, now)
        h.script_deribit_order("buy", "BTC-S-78000-C", [
            {"order_state": "open", "filled_amount": 0.0, "average_price": None},
            {"order_state": "open", "filled_amount": 0.0, "average_price": None},
        ])

        first_entry = h.run(now + 1000)
        second_entry = h.run(now + 2000)
        locked = fmz_shim._G(ST._LOCKED_KEY)
        status = h.latest_status()

        assert first_entry["console_phase"] == "PLAN_LOCKED"
        assert second_entry["console_phase"] == "PLAN_LOCKED"
        assert locked is not None
        assert locked["entry"]["prot_order"]["order_id"]
        assert locked["entry"]["prot_done"] == 0.0
        assert locked["entry"]["short_done"] == 0.0
        assert len(h.deribit_orders) == 1
        assert h.deribit_orders[0][0] == "buy"
        assert h.binance.orders == []
        assert "保护腿挂单" in status
        assert "maker等待" in status
    finally:
        h.restore()


def test_matrix_014_test_confirm_code_locks_plan_but_entry_stays_dry_no_order():
    h = LifecycleHarness().install("TEST").enable_valid_market_context()
    now = int(time.time() * 1000)
    try:
        first = h.run(now)
        assert first["pending_candidates"]
        code = first["pending_candidates"][0]["confirm_code"]

        h.push_command(code)
        locked = h.run(now + 1000)
        status = h.latest_status()

        assert locked["last_command_outcome"] == "locked"
        assert locked["console_phase"] == "PLAN_LOCKED"
        assert fmz_shim._G(ST._LOCKED_KEY)["confirm_code"] == code
        assert fmz_shim._G(ST._POSITION_KEY) is None
        assert ST.ledger_get_state() == ST.S_NO_POSITION
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert "测试模式" in status
        assert "不会真实下单" in status
    finally:
        h.restore()


def test_matrix_015_live_protection_cancel_late_fill_counted_once():
    h = LifecycleHarness().install("LIVE").enable_valid_market_context()
    now = int(time.time() * 1000)
    try:
        _lock_first_live_plan(h, now)
        h.script_deribit_order("buy", "BTC-S-78000-C", [
            {"order_state": "open", "filled_amount": 0.0, "average_price": None},
            {"order_state": "filled", "filled_amount": 0.1, "average_price": 0.0036},
            {"order_state": "filled", "filled_amount": 0.1, "average_price": 0.0036},
        ])
        h.script_deribit_order("sell", "BTC-S-76000-C", [
            {"order_state": "open", "filled_amount": 0.0, "average_price": None},
        ])
        h.script_deribit_order("sell", "BTC-S-76000-C", [
            {"order_state": "open", "filled_amount": 0.0, "average_price": None},
        ])

        first_entry = h.run(now + 1000)
        later = now + 1000 + int(ST.ENTRY_PROTECTION_TAKER_AFTER_SECONDS * 1000) + 1000
        second_entry = h.run(later)
        third_entry = h.run(later + 1000)
        locked = fmz_shim._G(ST._LOCKED_KEY)
        fills = (locked["entry"] or {}).get("entry_fills") or []
        protection_fills = [
            f for f in fills
            if f.get("leg") == "protection" and (f.get("filled") or 0.0) > 0
        ]

        assert first_entry["console_phase"] == "PLAN_LOCKED"
        assert second_entry["console_phase"] == "PLAN_LOCKED"
        assert third_entry["console_phase"] == "PLAN_LOCKED"
        assert locked["entry"]["prot_done"] == 0.1
        assert locked["entry"]["short_done"] == 0.0
        assert len(protection_fills) == 1
        assert protection_fills[0]["filled"] == 0.1
        assert h.deribit_cancels[0] == "matrix-buy-1"
        assert h.deribit_cancels.count("matrix-buy-1") == 1
        assert [o[0] for o in h.deribit_orders] == ["buy", "sell", "sell"]
        assert fmz_shim._G(ST._POSITION_KEY) is None
        assert h.binance.orders == []
    finally:
        h.restore()


def test_matrix_016_live_risk_exit_depth_gap_no_buyback_and_status_is_readable():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        ST.ALLOW_HEDGE_TRADING = False
        snap = _hedge_ready_snapshot(now)
        h.ticker_by_inst[snap["short_instrument"]] = {
            "mark_price": 0.004,
            "best_bid_price": 0.0039,
            "best_ask_price": 0.004,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.35, "gamma": 0.00005, "vega": 0.01},
            "mark_iv": 0.95,
        }
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.003,
            "best_bid_price": 0.0028,
            "best_ask_price": 0.0032,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.10, "gamma": 0.00002, "vega": 0.01},
            "mark_iv": 0.90,
        }
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

        ctx = h.run(now)
        status = h.latest_status()
        exit_rows = _rows_by_title(status, "止盈/退出预算")
        budget_line = exit_rows["风险退出预算"][0]
        book_value, book_note = exit_rows["风险退出盘口"]

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["risk_state"] == ST.STATE_HEDGE_READY
        assert ctx["risk_exit_detail"]["reason"] == "EXIT_DEPTH_DATA_GAP"
        assert ctx["action_arb"]["preferred_action"] == "EXIT_PREFERRED"
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert "卖一深度缺口" in budget_line
        assert "卖一深度缺口" in book_note
        assert "EXIT_DEPTH_DATA_GAP" not in budget_line
        assert "EXIT_DEPTH_DATA_GAP" not in book_note
        assert "深度受限" in book_value
    finally:
        h.restore()


def test_matrix_017_live_take_profit_exit_fills_once_within_budget():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        snap = _active_snapshot(now)
        snap["entry_profit_ceiling_net"] = 0.002
        snap["target_profit_amount"] = 0.0016
        snap["max_total_exit_spend"] = 0.0004
        h.ticker_by_inst[snap["short_instrument"]] = {
            "mark_price": 0.0002,
            "best_bid_price": 0.0001,
            "best_ask_price": 0.0002,
            "best_ask_amount": 0.2,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.10, "gamma": 0.00001, "vega": 0.01},
            "mark_iv": 0.70,
        }
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.001,
            "best_bid_price": 0.0,
            "best_ask_price": 0.0011,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.05, "gamma": 0.00001, "vega": 0.01},
            "mark_iv": 0.70,
        }
        h.script_deribit_order("buy", snap["short_instrument"], [
            {"order_state": "filled", "filled_amount": 0.1, "average_price": 0.0001},
        ])
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

        ctx = h.run(now)
        saved = fmz_shim._G(ST._POSITION_KEY)
        orders_after_first = list(h.deribit_orders)
        history_after_first = list(saved.get("exit_execution_history") or [])
        second = h.run(now + 1000)
        saved2 = fmz_shim._G(ST._POSITION_KEY)
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["action_arb"]["preferred_action"] == "TAKE_PROFIT_READY"
        assert ctx["action_arb"]["executable_action"] == "TAKE_PROFIT_READY"
        assert saved["remaining_short_qty"] == 0.0
        assert saved["realized_exit_spend"] > 0
        assert ST.ledger_get_state() == ST.S_SHORT_FLAT_LONG_RESIDUAL
        assert len(history_after_first) == 1
        assert history_after_first[0]["leg"] == "exit_short"
        assert history_after_first[0]["filled"] == 0.1
        assert len(h.deribit_orders) == 1
        assert orders_after_first[0][0] == "buy"
        assert orders_after_first[0][1].get("label") == "exit_short"
        assert orders_after_first[0][1].get("post_only") == "true"
        assert second["console_phase"] == "POSITION_MANAGE"
        assert saved2["remaining_short_qty"] == 0.0
        assert len(saved2.get("exit_execution_history") or []) == 1
        assert len(h.deribit_orders) == 1
        assert h.binance.orders == []
        assert "止盈" in status or "短腿已归零" in status
    finally:
        h.restore()


def test_matrix_018_live_risk_exit_depth_sufficient_uses_taker_once():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        snap = _hedge_ready_snapshot(now)
        h.ticker_by_inst[snap["short_instrument"]] = {
            "mark_price": 0.004,
            "best_bid_price": 0.0039,
            "best_ask_price": 0.004,
            "best_ask_amount": 0.2,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.35, "gamma": 0.00005, "vega": 0.01},
            "mark_iv": 0.95,
        }
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.003,
            "best_bid_price": 0.0,
            "best_ask_price": 0.0032,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.10, "gamma": 0.00002, "vega": 0.01},
            "mark_iv": 0.90,
        }
        h.script_deribit_order("buy", snap["short_instrument"], [
            {"order_state": "filled", "filled_amount": 0.1, "average_price": 0.004},
        ])
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

        ctx = h.run(now)
        saved = fmz_shim._G(ST._POSITION_KEY)
        orders_after_first = list(h.deribit_orders)
        history_after_first = list(saved.get("exit_execution_history") or [])
        second = h.run(now + 1000)
        saved2 = fmz_shim._G(ST._POSITION_KEY)
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["risk_state"] == ST.STATE_HEDGE_READY
        assert ctx["risk_exit_detail"]["within"] is True
        assert ctx["risk_exit_detail"]["depth_ok"] is True
        assert ctx["action_arb"]["preferred_action"] == "EXIT_PREFERRED"
        assert ctx["action_arb"]["executable_action"] == "EXIT_PREFERRED"
        assert saved["remaining_short_qty"] == 0.0
        assert saved["realized_exit_spend"] > 0
        assert len(history_after_first) == 1
        assert history_after_first[0]["taker"] is True
        assert orders_after_first[0][0] == "buy"
        assert orders_after_first[0][1].get("label") == "risk_exit"
        assert orders_after_first[0][1].get("post_only") == "false"
        assert second["console_phase"] == "POSITION_MANAGE"
        assert saved2["remaining_short_qty"] == 0.0
        assert len(saved2.get("exit_execution_history") or []) == 1
        assert len(h.deribit_orders) == 1
        assert h.binance.orders == []
        assert "风险退出" in status
    finally:
        h.restore()


def test_matrix_019_live_risk_exit_ask_above_cap_no_over_budget_buyback():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        ST.ALLOW_HEDGE_TRADING = False
        snap = _hedge_ready_snapshot(now)
        h.ticker_by_inst[snap["short_instrument"]] = {
            "mark_price": 0.004,
            "best_bid_price": 0.0039,
            "best_ask_price": 0.020,
            "best_ask_amount": 0.2,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.35, "gamma": 0.00005, "vega": 0.01},
            "mark_iv": 0.95,
        }
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.003,
            "best_bid_price": 0.0028,
            "best_ask_price": 0.0032,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.10, "gamma": 0.00002, "vega": 0.01},
            "mark_iv": 0.90,
        }
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

        ctx = h.run(now)
        saved = fmz_shim._G(ST._POSITION_KEY)
        status = h.latest_status()
        exit_rows = _rows_by_title(status, "止盈/退出预算")
        budget_line = exit_rows["风险退出预算"][0]
        book_value, book_note = exit_rows["风险退出盘口"]

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["risk_state"] == ST.STATE_HEDGE_READY
        assert ctx["risk_exit_detail"]["reason"] == "EXIT_PRICE_ABOVE_CAP"
        assert ctx["risk_exit_detail"]["within_price"] is False
        assert ctx["action_arb"]["preferred_action"] == "EXIT_PREFERRED"
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert saved["remaining_short_qty"] == 0.1
        assert "卖一高于预算上限" in budget_line
        assert "卖一高于预算上限" in book_note
        assert "EXIT_PRICE_ABOVE_CAP" not in budget_line
        assert "EXIT_PRICE_ABOVE_CAP" not in book_note
        assert "价格受限" in book_value
    finally:
        h.restore()


def test_matrix_020_live_risk_exit_quote_gap_blocks_buyback_readably():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        ST.ALLOW_HEDGE_TRADING = False
        snap = _hedge_ready_snapshot(now)
        h.ticker_by_inst[snap["short_instrument"]] = {
            "mark_price": 0.004,
            "best_bid_price": 0.0039,
            "best_ask_price": None,
            "best_ask_amount": 0.2,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.35, "gamma": 0.00005, "vega": 0.01},
            "mark_iv": 0.95,
        }
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.003,
            "best_bid_price": 0.0028,
            "best_ask_price": 0.0032,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.10, "gamma": 0.00002, "vega": 0.01},
            "mark_iv": 0.90,
        }
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

        ctx = h.run(now)
        saved = fmz_shim._G(ST._POSITION_KEY)
        status = h.latest_status()
        reason_cn = ST.disp_reason_cn("EXIT_QUOTE_DATA_GAP")

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["risk_state"] == ST.STATE_HEDGE_READY
        assert ctx["risk_exit_detail"]["reason"] == "EXIT_QUOTE_DATA_GAP"
        assert ctx["risk_exit_detail"]["quote_ok"] is False
        assert ctx["action_arb"]["preferred_action"] == "EXIT_PREFERRED"
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert saved["remaining_short_qty"] == 0.1
        assert reason_cn in status
        assert "EXIT_QUOTE_DATA_GAP" not in status
    finally:
        h.restore()


def test_matrix_021_live_risk_exit_depth_insufficient_blocks_buyback_readably():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        ST.ALLOW_HEDGE_TRADING = False
        snap = _hedge_ready_snapshot(now)
        h.ticker_by_inst[snap["short_instrument"]] = {
            "mark_price": 0.004,
            "best_bid_price": 0.0039,
            "best_ask_price": 0.004,
            "best_ask_amount": 0.01,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.35, "gamma": 0.00005, "vega": 0.01},
            "mark_iv": 0.95,
        }
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.003,
            "best_bid_price": 0.0028,
            "best_ask_price": 0.0032,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.10, "gamma": 0.00002, "vega": 0.01},
            "mark_iv": 0.90,
        }
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

        ctx = h.run(now)
        saved = fmz_shim._G(ST._POSITION_KEY)
        status = h.latest_status()
        reason_cn = ST.disp_reason_cn("EXIT_DEPTH_INSUFFICIENT")

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["risk_state"] == ST.STATE_HEDGE_READY
        assert ctx["risk_exit_detail"]["reason"] == "EXIT_DEPTH_INSUFFICIENT"
        assert ctx["risk_exit_detail"]["within_price"] is True
        assert ctx["risk_exit_detail"]["depth_ok"] is False
        assert ctx["action_arb"]["preferred_action"] == "EXIT_PREFERRED"
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert saved["remaining_short_qty"] == 0.1
        assert reason_cn in status
        assert "EXIT_DEPTH_INSUFFICIENT" not in status
    finally:
        h.restore()


def test_matrix_022_live_take_profit_cancel_late_fill_books_once():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        snap = _active_snapshot(now)
        snap["entry_profit_ceiling_net"] = 0.002
        snap["target_profit_amount"] = 0.0016
        snap["max_total_exit_spend"] = 0.0004
        h.ticker_by_inst[snap["short_instrument"]] = {
            "mark_price": 0.0002,
            "best_bid_price": 0.0001,
            "best_ask_price": 0.0002,
            "best_ask_amount": 0.2,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.10, "gamma": 0.00001, "vega": 0.01},
            "mark_iv": 0.70,
        }
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.001,
            "best_bid_price": 0.0,
            "best_ask_price": 0.0011,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.05, "gamma": 0.00001, "vega": 0.01},
            "mark_iv": 0.70,
        }
        h.script_deribit_order("buy", snap["short_instrument"], [
            {"order_state": "open", "filled_amount": 0.0, "average_price": 0.0001},
            {"order_state": "cancelled", "filled_amount": 0.04, "average_price": 0.0001},
        ])
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

        ctx = h.run(now)
        saved = fmz_shim._G(ST._POSITION_KEY)
        history = saved.get("exit_execution_history") or []
        second = h.run(now + 1000)
        saved2 = fmz_shim._G(ST._POSITION_KEY)

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["action_arb"]["executable_action"] == "TAKE_PROFIT_READY"
        assert h.deribit_cancels[0] == "matrix-buy-1"
        assert abs(saved["remaining_short_qty"] - 0.06) < 1e-12
        assert len(history) == 1
        assert history[0]["order_id"] == "matrix-buy-1"
        assert history[0]["filled"] == 0.04
        assert history[0]["cancelled"] is True
        assert saved["realized_exit_spend"] > 0
        assert second["console_phase"] == "POSITION_MANAGE"
        assert abs(saved2["remaining_short_qty"] - 0.06) < 1e-12
        assert len(saved2.get("exit_execution_history") or []) == 1
        assert len(h.deribit_orders) == 2
        assert abs(float(h.deribit_orders[1][1].get("amount")) - 0.06) < 1e-12
        assert h.binance.orders == []
    finally:
        h.restore()


def test_matrix_023_live_partial_exit_next_loop_finishes_without_double_count():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        snap = _active_snapshot(now)
        snap["entry_profit_ceiling_net"] = 0.002
        snap["target_profit_amount"] = 0.0016
        snap["max_total_exit_spend"] = 0.0004
        h.ticker_by_inst[snap["short_instrument"]] = {
            "mark_price": 0.0002,
            "best_bid_price": 0.0001,
            "best_ask_price": 0.0002,
            "best_ask_amount": 0.2,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.10, "gamma": 0.00001, "vega": 0.01},
            "mark_iv": 0.70,
        }
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.001,
            "best_bid_price": 0.0,
            "best_ask_price": 0.0011,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.05, "gamma": 0.00001, "vega": 0.01},
            "mark_iv": 0.70,
        }
        h.script_deribit_order("buy", snap["short_instrument"], [
            {"order_state": "open", "filled_amount": 0.0, "average_price": 0.0001},
            {"order_state": "cancelled", "filled_amount": 0.04, "average_price": 0.0001},
        ])
        h.script_deribit_order("buy", snap["short_instrument"], [
            {"order_state": "filled", "filled_amount": 0.06, "average_price": 0.0001},
        ])
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

        first = h.run(now)
        mid = fmz_shim._G(ST._POSITION_KEY)
        mid_remaining = mid["remaining_short_qty"]
        mid_history_count = len(mid.get("exit_execution_history") or [])
        spend_after_first = mid["realized_exit_spend"]
        second = h.run(now + 1000)
        saved = fmz_shim._G(ST._POSITION_KEY)
        history = saved.get("exit_execution_history") or []

        assert first["console_phase"] == "POSITION_MANAGE"
        assert abs(mid_remaining - 0.06) < 1e-12
        assert mid_history_count == 1
        assert second["console_phase"] == "POSITION_MANAGE"
        assert saved["remaining_short_qty"] <= 1e-12
        assert ST.ledger_get_state() == ST.S_SHORT_FLAT_LONG_RESIDUAL
        assert len(history) == 2
        assert [round(x["filled"], 8) for x in history] == [0.04, 0.06]
        assert saved["realized_exit_spend"] > spend_after_first
        assert len(h.deribit_orders) == 2
        assert abs(float(h.deribit_orders[0][1].get("amount")) - 0.1) < 1e-12
        assert abs(float(h.deribit_orders[1][1].get("amount")) - 0.06) < 1e-12
        assert h.binance.orders == []
    finally:
        h.restore()


def test_matrix_024_live_hedge_pending_order_blocks_duplicate_submit_readably():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        _install_hedge_fallback_position(h, now)

        first = h.run(now)
        st1 = fmz_shim._G(ST._HEDGE_POLICY_STATE_KEY)
        second = h.run(now + 1000)
        st2 = fmz_shim._G(ST._HEDGE_POLICY_STATE_KEY)
        status = h.latest_status()
        reason_cn = ST.disp_reason_cn("PENDING_ACTIVE")

        assert first["action_arb"]["executable_action"] == "HEDGE_READY"
        assert first["hedge_step"]["reason"] == "BINANCE_HEDGE_SUBMITTED"
        assert len(h.binance.orders) == 1
        assert st1["pending_order_id"] == "matrix-binance-buy"
        assert second["hedge_detail"]["policy_reason"] == "PENDING_ACTIVE"
        assert st2["pending_order_id"] == "matrix-binance-buy"
        assert len(h.binance.orders) == 1
        assert reason_cn != "PENDING_ACTIVE"
        assert reason_cn in status
        assert "PENDING_ACTIVE" not in status
    finally:
        h.restore()


def test_matrix_025_live_hedge_missing_order_id_sets_unknown_guard_no_duplicate():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        h.binance.missing_order_id = True
        _install_hedge_fallback_position(h, now)

        first = h.run(now)
        st1 = fmz_shim._G(ST._HEDGE_POLICY_STATE_KEY)
        second = h.run(now + 1000)
        st2 = fmz_shim._G(ST._HEDGE_POLICY_STATE_KEY)
        status = h.latest_status()
        reason_cn = ST.disp_reason_cn("SUBMIT_UNKNOWN_RECENT")

        assert first["action_arb"]["executable_action"] == "HEDGE_READY"
        assert first["hedge_step"]["reason"] == "BINANCE_ORDER_ID_MISSING"
        assert len(h.binance.orders) == 1
        assert st1["pending_order_id"] is None
        assert st1["last_submit_unknown_reason"] == "BINANCE_ORDER_ID_MISSING"
        assert second["hedge_detail"]["policy_reason"] == "SUBMIT_UNKNOWN_RECENT"
        assert st2["last_submit_unknown_reason"] == "BINANCE_ORDER_ID_MISSING"
        assert len(h.binance.orders) == 1
        assert reason_cn != "SUBMIT_UNKNOWN_RECENT"
        assert reason_cn in status
        assert "SUBMIT_UNKNOWN_RECENT" not in status
    finally:
        h.restore()


def test_matrix_026_live_hedge_pending_terminal_fill_records_history_once():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        _install_hedge_fallback_position(h, now)

        first = h.run(now)
        h.binance.qty = 0.025
        h.binance.order_states["matrix-binance-buy"] = {
            "Id": "matrix-binance-buy",
            "Status": 2,
            "DealAmount": 0.025,
            "AvgPrice": 60180.0,
        }
        second = h.run(now + 1000)
        saved = fmz_shim._G(ST._POSITION_KEY)
        st2 = fmz_shim._G(ST._HEDGE_POLICY_STATE_KEY)
        third = h.run(now + 2000)
        saved3 = fmz_shim._G(ST._POSITION_KEY)

        hist = saved.get("hedge_execution_history") or []
        hist3 = saved3.get("hedge_execution_history") or []

        assert first["hedge_step"]["reason"] == "BINANCE_HEDGE_SUBMITTED"
        assert len(h.binance.orders) == 1
        assert second["hedge_detail"]["policy_reason"] == "PENDING_FILLED"
        assert st2["pending_order_id"] is None
        assert len(hist) == 1
        assert hist[0]["order_id"] == "matrix-binance-buy"
        assert hist[0]["filled"] == 0.025
        assert hist[0]["reduce_only"] is False
        assert third["console_phase"] == "POSITION_MANAGE"
        assert len(hist3) == 1
        assert len(h.binance.orders) == 1
    finally:
        h.restore()


def test_matrix_027_live_v32_soft_initial_adds_hedge_and_reads_chinese():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        _install_soft_hedge_position(h, now)

        ctx = h.run(now)
        detail = ctx["hedge_detail"]
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["risk_state"] == ST.STATE_HEDGE_READY
        assert ctx["action_arb"]["executable_action"] == "HEDGE_READY"
        assert detail["policy_state"] == "SOFT"
        assert detail["policy_reason"] == "SOFT_TRIGGER_INITIAL"
        assert detail["action"] == "HEDGE_OPEN"
        assert detail["reduce_only"] is False
        assert detail["policy_cross_bps"] == ST.HEDGE_SOFT_CROSS_BPS
        assert ctx["hedge_step"]["reason"] == "BINANCE_HEDGE_SUBMITTED"
        assert ctx["hedge_step"]["side"] == "buy"
        assert ctx["hedge_step"]["reduce_only"] is False
        assert len(h.binance.orders) == 1
        assert h.binance.orders[0][0] == "buy"
        _assert_status_has_cn_reason_without_raw(status, "SOFT_TRIGGER_INITIAL")
    finally:
        h.restore()


def test_matrix_028_live_v32_hard_bypasses_add_cooldown_and_reads_chinese():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        snap = _install_hedge_fallback_position(h, now)
        st = ST._hedge_policy_state(snap)
        st["add_cooldown_until"] = now + 60_000
        ST._hedge_policy_save_state(st)

        ctx = h.run(now)
        detail = ctx["hedge_detail"]
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["risk_state"] == ST.STATE_HEDGE_READY
        assert ctx["action_arb"]["executable_action"] == "HEDGE_READY"
        assert detail["policy_state"] == "HARD"
        assert detail["policy_reason"] == "HARD_TRIGGER_EMERGENCY"
        assert detail["action"] == "HEDGE_OPEN"
        assert detail["policy_cross_bps"] == ST.HEDGE_HARD_CROSS_BPS
        assert ctx["hedge_step"]["reason"] == "BINANCE_HEDGE_SUBMITTED"
        assert ctx["hedge_step"]["side"] == "buy"
        assert len(h.binance.orders) == 1
        _assert_status_has_cn_reason_without_raw(status, "HARD_TRIGGER_EMERGENCY")
    finally:
        h.restore()


def test_matrix_029_live_v32_final3h_soft_add_suppressed_no_order_chinese():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        _install_soft_hedge_position(h, now, final3=True)

        ctx = h.run(now)
        detail = ctx["hedge_detail"]
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["risk_state"] == ST.STATE_HEDGE_READY
        assert ctx["action_arb"]["executable_action"] == "HOLD"
        assert detail["policy_state"] == "SOFT"
        assert detail["policy_reason"] == "FINAL3H_SOFT_ADD_SUPPRESSED"
        assert detail["action"] == "HEDGE_HOLD"
        assert ctx["hedge_step"] is None
        assert h.binance.orders == []
        _assert_status_has_cn_reason_without_raw(status, "FINAL3H_SOFT_ADD_SUPPRESSED")
    finally:
        h.restore()


def test_matrix_030_live_v32_reduce_confirmed_is_reduce_only_and_readable():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        _install_reduce_hedge_position(h, now)

        ctx = h.run(now)
        detail = ctx["hedge_detail"]
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["risk_state"] == "NORMAL"
        assert ctx["action_arb"]["executable_action"] == "HEDGE_READY"
        assert detail["policy_state"] == "HOLD"
        assert detail["policy_reason"] == "REDUCE_CONFIRMED"
        assert detail["action"] == "HEDGE_UNWIND"
        assert detail["reduce_only"] is True
        assert ctx["hedge_step"]["reason"] == "BINANCE_HEDGE_SUBMITTED"
        assert ctx["hedge_step"]["side"] == "sell"
        assert ctx["hedge_step"]["reduce_only"] is True
        assert len(h.binance.orders) == 1
        assert h.binance.orders[0][0] == "sell"
        _assert_status_has_cn_reason_without_raw(status, "REDUCE_CONFIRMED")
    finally:
        h.restore()


def test_matrix_031_unknown_active_order_forces_manual_orphan_cleanup_no_order():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        h.binance.qty = 0.01
        h.open_orders = [{"order_id": "mystery-1", "instrument_name": "BTC-S-76000-C"}]

        verdict = ST.startup_recovery_check("BTC")
        ctx = h.run(now)
        status = h.latest_status()

        assert verdict["state"] == "ORPHAN_HEDGE_EMERGENCY"
        assert verdict["auto_cleanup_allowed"] is False
        assert verdict["cleanup_block_reason"] == "UNKNOWN_ACTIVE_ORDERS"
        assert ctx["console_phase"] == "ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED"
        assert h.binance.orders == []
        assert "需要人工只减清理" in status
        assert "UNKNOWN_ACTIVE_ORDERS" in status
    finally:
        h.restore()


def test_matrix_032_startup_binance_read_failure_blocks_with_chinese_manual_check():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        h.binance.position_gap = True

        verdict = ST.startup_recovery_check("BTC")
        ctx = h.run(now)
        status = h.latest_status()

        assert verdict["state"] == "RECOVERY_BLOCKED"
        assert "HEDGE_POSITION_QUERY_FAILED" in verdict["reasons"]
        assert ctx["console_phase"] == "RECOVERY_BLOCKED"
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert "Binance" in status
        assert "仓位读取失败" in status
        assert "人工核对" in status
    finally:
        h.restore()


def test_matrix_033_startup_deribit_option_read_failure_blocks_with_chinese_manual_check():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        h.option_positions = None

        verdict = ST.startup_recovery_check("BTC")
        ctx = h.run(now)
        status = h.latest_status()

        assert verdict["state"] == "RECOVERY_BLOCKED"
        assert "OPTION_POSITION_QUERY_FAILED" in verdict["reasons"]
        assert ctx["console_phase"] == "RECOVERY_BLOCKED"
        assert h.deribit_orders == []
        assert h.binance.orders == []
        assert "Deribit" in status
        assert "期权持仓读取失败" in status
        assert "人工核对" in status
    finally:
        h.restore()


def test_matrix_034_snapshot_with_lost_state_enters_position_manage_and_hides_plan_menu():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        fmz_shim._G(ST._POSITION_KEY, _active_snapshot(now))
        ST.ledger_set_state(ST.S_NO_POSITION)

        ctx = h.run(now)
        status = h.latest_status()
        titles = [t["title"] for t in _tables_from_status(status)]

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["entry_snapshot"]["position_id"] == "matrix-pos"
        assert "固定备选方案库" not in titles
        assert "持仓总览" in titles
        assert h.deribit_orders == []
    finally:
        h.restore()


def test_matrix_035_live_settlement_option_read_gap_does_not_false_settle():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        _install_settlement_position(h, now, None)

        ctx = h.run(now)
        saved = fmz_shim._G(ST._POSITION_KEY)
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert saved["remaining_short_qty"] == 0.1
        assert saved["long_remaining_qty"] == 0.1
        assert not saved.get("option_settlement_history")
        assert fmz_shim._G(ST._CLOSED_HISTORY_KEY) is None
        assert ctx["ledger_detail"]["reconcile_reasons"] == ["OPTION_POSITION_QUERY_FAILED"]
        assert h.deribit_orders == []
        assert h.binance.orders == []
        _assert_settlement_display_chinese_first(status)
    finally:
        h.restore()


def test_matrix_036_live_short_settlement_keeps_long_residual_and_is_idempotent():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    long_pos = [{"instrument_name": "BTC-S-78000-C", "size": 0.1}]
    try:
        _install_settlement_position(h, now, long_pos)

        first = h.run(now)
        saved = fmz_shim._G(ST._POSITION_KEY)
        second = h.run(now + 1000)
        saved2 = fmz_shim._G(ST._POSITION_KEY)
        status = h.latest_status()

        assert first["console_phase"] == "POSITION_MANAGE"
        assert saved["remaining_short_qty"] == 0.0
        assert saved["long_remaining_qty"] == 0.1
        assert saved["settlement_state"] == "SHORT_SETTLED"
        assert first["ledger_detail"]["settlement_state"] == "SHORT_SETTLED"
        assert len(saved.get("option_settlement_history") or []) == 1
        assert saved["option_settlement_history"][0]["leg"] == "short"
        assert second["console_phase"] == "POSITION_MANAGE"
        assert len(saved2.get("option_settlement_history") or []) == 1
        assert fmz_shim._G(ST._CLOSED_HISTORY_KEY) is None
        assert h.deribit_orders == []
        assert h.binance.orders == []
        _assert_settlement_display_chinese_first(status)
    finally:
        h.restore()


def test_matrix_037_live_both_legs_settle_and_archive_final_pnl():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        _install_settlement_position(h, now, [])

        ctx = h.run(now)
        closed = fmz_shim._G(ST._CLOSED_HISTORY_KEY) or []
        rec = closed[-1]
        expected_short = -((79000.0 - 76000.0) / 79000.0) * 0.1
        expected_long = ((79000.0 - 78000.0) / 79000.0) * 0.1
        expected_final = 0.004 + expected_short + expected_long
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["ledger_detail"]["settlement_state"] == "BOTH_LEGS_SETTLED"
        assert fmz_shim._G(ST._POSITION_KEY) is None
        assert ST.ledger_get_state() == ST.S_CLOSED
        assert len(closed) == 1
        assert rec["settlement_state"] == "BOTH_LEGS_SETTLED"
        assert rec["final_pnl_status"] == "COMPUTED"
        assert abs(rec["final_option_pnl_ccy"] - expected_final) < 1e-12
        assert fmz_shim._G(ST._RECOVERY_KEY)["state"] == "OK"
        assert h.deribit_orders == []
        assert h.binance.orders == []
        _assert_settlement_display_chinese_first(status)
    finally:
        h.restore()


def test_matrix_038_live_closed_archive_is_not_duplicated_on_next_loop():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        _install_settlement_position(h, now, [])

        first = h.run(now)
        second = h.run(now + 1000)
        closed = fmz_shim._G(ST._CLOSED_HISTORY_KEY) or []

        assert first["console_phase"] == "POSITION_MANAGE"
        assert second["console_phase"] in ("PLAN_MENU_READY", "WAIT_MANUAL_AUDIT_GATE")
        assert fmz_shim._G(ST._POSITION_KEY) is None
        assert ST.ledger_get_state() == ST.S_CLOSED
        assert len(closed) == 1
        assert len(closed[0].get("option_settlement_history") or []) == 2
        assert h.deribit_orders == []
        assert h.binance.orders == []
    finally:
        h.restore()


def test_matrix_039_live_missing_settlement_price_archives_data_gap_not_zero():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    orig_index = ST.dbt_index_price
    try:
        ST.dbt_index_price = lambda _currency: None
        _install_settlement_position(h, now, [], include_settlement_price=False)

        ctx = h.run(now)
        closed = fmz_shim._G(ST._CLOSED_HISTORY_KEY) or []
        rec = closed[-1]
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert ctx["ledger_detail"]["settlement_state"] == "BOTH_LEGS_SETTLED"
        assert rec["settlement_pnl_status"] == "DATA_GAP"
        assert rec["option_settlement_cashflow_ccy"] is None
        assert rec["option_realized_pnl_ccy"] is None
        assert rec["final_option_pnl_ccy"] is None
        assert rec["final_pnl_status"] == "DATA_GAP"
        assert "$0.00" not in status
        _assert_settlement_display_chinese_first(status)
    finally:
        ST.dbt_index_price = orig_index
        h.restore()


def test_matrix_040_live_settlement_with_perp_submits_reduce_only_no_archive_yet():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        _install_settlement_position(h, now, [], binance_qty=-0.01)

        ctx = h.run(now)
        saved = fmz_shim._G(ST._POSITION_KEY)
        hedge_state = fmz_shim._G(ST._HEDGE_POLICY_STATE_KEY)
        status = h.latest_status()

        assert ctx["console_phase"] == "POSITION_MANAGE"
        assert saved["settlement_state"] == "BOTH_LEGS_SETTLED"
        assert ctx["ledger_detail"]["settlement_state"] == "BOTH_LEGS_SETTLED"
        assert ctx["hedge_detail"]["policy_reason"] == "ORPHAN_HEDGE_UNWIND"
        assert ctx["hedge_step"]["side"] == "buy"
        assert ctx["hedge_step"]["reduce_only"] is True
        assert len(h.binance.orders) == 1
        assert h.binance.orders[0][0] == "buy"
        assert hedge_state["pending_order_id"] == "matrix-binance-buy"
        assert fmz_shim._G(ST._CLOSED_HISTORY_KEY) is None
        assert "ORPHAN_HEDGE_UNWIND" not in status
        _assert_settlement_display_chinese_first(status)
    finally:
        h.restore()


def test_matrix_041_live_protection_recovery_fill_is_not_double_counted():
    h = LifecycleHarness().install("LIVE")
    now = int(time.time() * 1000)
    try:
        snap = _active_snapshot(now)
        snap["remaining_short_qty"] = 0.0
        snap["long_remaining_qty"] = 0.1
        snap["entry_execution_report"] = {
            "actual_net_credit_after_fees": 0.004,
            "total_short_credit": 0.00080,
            "total_protection_cost": 0.00035,
            "total_fee_estimate": 0.00001,
            "fill_count": 2,
        }
        h.ticker_by_inst[snap["long_instrument"]] = {
            "mark_price": 0.0035,
            "best_bid_price": 0.0034,
            "best_ask_price": 0.0036,
            "underlying_price": SPOT,
            "greeks": {"delta": 0.08, "gamma": 0.00001, "vega": 0.01},
            "mark_iv": 0.70,
        }
        h.script_deribit_order("sell", snap["long_instrument"], [{
            "order_state": "filled",
            "filled_amount": 0.1,
            "average_price": 0.0034,
        }])
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_FLAT_LONG_RESIDUAL)

        first = h.run(now)
        status = h.latest_status()
        closed = fmz_shim._G(ST._CLOSED_HISTORY_KEY) or []
        rec = closed[-1]

        tables = _tables_from_status(status)
        titles = [t["title"] for t in tables]

        assert first["exit_campaign_state"] == "WORKING_LONG"
        assert len(h.deribit_orders) == 1
        assert h.deribit_orders[0][0] == "sell"
        assert h.deribit_orders[0][1]["instrument_name"] == snap["long_instrument"]
        assert fmz_shim._G(ST._POSITION_KEY) is None
        assert ST.ledger_get_state() == ST.S_CLOSED
        assert len(rec["protection_recovery_history"]) == 1
        assert rec["long_remaining_qty"] == 0.0
        first_recovery_value = rec["realized_protection_recovery_value"]
        assert first_recovery_value > 0
        assert "持仓总览" in titles
        assert "记账/对账/恢复" in titles
        assert "保护腿合约" in status

        second = h.run(now + 1000)
        closed2 = fmz_shim._G(ST._CLOSED_HISTORY_KEY) or []

        assert second["console_phase"] in ("PLAN_MENU_READY", "HARD_APPROVAL_WAIT")
        assert len(h.deribit_orders) == 1
        assert len(closed2) == 1
        assert len(closed2[0]["protection_recovery_history"]) == 1
        assert closed2[0]["realized_protection_recovery_value"] == first_recovery_value
    finally:
        h.restore()
