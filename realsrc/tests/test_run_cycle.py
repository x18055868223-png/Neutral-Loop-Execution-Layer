# -*- coding: utf-8 -*-
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from urllib.parse import parse_qs

import fmz_shim

_BASE = {"t": None}
H = 3600000
SPOT = 73400.0
S48 = {
    74000: (0.45, 0.016),
    75000: (0.38, 0.012),
    76000: (0.30, 0.008),
    77000: (0.22, 0.005),
    78000: (0.15, 0.0035),
    79000: (0.10, 0.0025),
    80000: (0.06, 0.0018),
}


def _instruments(now_ms):
    exp = now_ms + 48 * H
    return [{"instrument_name": "BTC-S-%d-C" % k, "strike": k, "option_type": "call",
             "expiration_timestamp": exp, "kind": "option", "tick_size": 0.0001}
            for k in S48]


def _quote(inst):
    strike = int(inst.split("-")[2])
    delta, mark = S48[strike]
    return {"mark_price": mark, "best_bid_price": round(mark * 0.97, 6),
            "best_ask_price": round(mark * 1.03, 6), "underlying_price": SPOT,
            "greeks": {"delta": delta, "gamma": 0.00005}, "mark_iv": 0.90}


def _handler(*args):
    _ex, _m, path, query = args
    qs = parse_qs(query or "")
    if _BASE["t"] is None:
        _BASE["t"] = int(time.time() * 1000)
    now = _BASE["t"]
    if path.endswith("/public/get_instruments"):
        return {"result": _instruments(now)}
    if path.endswith("/public/get_index_price"):
        return {"result": {"index_price": SPOT}}
    if path.endswith("/public/ticker"):
        return {"result": _quote(qs.get("instrument_name", ["BTC-S-76000-C"])[0])}
    if path.endswith("/public/get_instrument"):
        return {"result": {"tick_size": 0.0001, "contract_size": 1, "min_trade_amount": 0.1}}
    if path.endswith("/private/get_account_summary"):
        return {"result": {"margin_model": "segregated_pm", "portfolio_margining_enabled": True,
                           "initial_margin": 0.02, "maintenance_margin": 0.015}}
    if path.endswith("/private/get_positions"):
        return {"result": []}
    if path.endswith("/private/simulate_portfolio"):
        simpos = json.loads(qs.get("simulated_positions", ["{}"])[0])
        im = 0.025 if len(simpos) == 1 else 0.013
        return {"result": {"initial_margin": im, "maintenance_margin": im * 0.8,
                           "available_funds": 1.0}}
    return {"result": None}


def _setup():
    fmz_shim._STORE.clear()
    fmz_shim._commands.clear()
    fmz_shim.exchange.io_handler = _handler
    import strategy as ST
    import execution as EX
    ST.SETTLEMENT_CURRENCY = "BTC"
    EX.SETTLEMENT_CURRENCY = "BTC"
    ST.MANUAL_PLANNING_ALLOWED = True
    ST.DIRECTION_BIAS = "SHORT_CALL"
    ST.SHORT_DELTA_RANGE = (0.15, 0.45)
    ST.PROTECTION_WIDTH_RANGE = (2000, 2500)
    ST.TARGET_DTE_HOURS = 24
    ST.ORDER_AMOUNT = 0.1
    ST.MENU_SIZE = 6
    ST.MIN_MARGIN_RELIEF_RATIO = 0.10
    ST.MAX_SPREAD_RATIO = 0.60
    ST.PLAN_WEIGHTS = {"win_rate": 0.50, "rr": 0.50, "manual": 0.0}
    ST.UNDERLYING_REF_PRICE = None
    ST.APPROVAL_TTL_MS = 30 * 60 * 1000
    ST.RUN_PROFILE = "LIVE"
    ST.DRY_RUN_PASSED = True
    ST.ALLOW_ENTRY_TRADING = False
    ST.ALLOW_EXIT_TRADING = False
    ST.ALLOW_HEDGE_TRADING = False
    ST.KILL_NEW_RISK = False
    ST.EMERGENCY_REDUCE_ONLY = False
    ST.RISK_EXIT_MAX_SPEND = 0.0
    ST.ROBOT_ID = "r-test"
    ST.HEDGE_VENUE = "DERIBIT"
    ST.fetch_gex_vrp_context = lambda *_a, **_k: {
        "valid": False, "status": "VRP_CONTEXT_MISSING", "market_context": None}
    ST._LOCKED["detail_id"] = None
    ST.ledger_set_state(ST.S_NO_POSITION)
    return ST


def _fat_vrp_context():
    return {
        "source": "GEX_MONITOR_IV_RV_RANK",
        "side": "SHORT_CALL",
        "iv_rv_ratio": 0.8,
        "iv_rv_rank_pct": 15.2,
    }


def _seed_market_context(ST, now_ms=None, market_context=None):
    now_ms = now_ms or ST._now_ms()
    ctx = ST._manual_context_for_cycle(now_ms)
    ctx["market_context"] = market_context or _fat_vrp_context()
    fmz_shim._G(ST._MANUAL_CONTEXT_KEY, ctx)
    return ctx


def _candidate():
    return {
        "id": 1,
        "short_instrument": "BTC-S-76000-C",
        "protection_instrument": "BTC-S-78000-C",
        "short_expiry_label": "S",
        "short_strike": 76000,
        "protection_strike": 78000,
        "short_expiry": (_BASE["t"] or int(time.time() * 1000)) + 48 * H,
        "short_dte_hours": 48,
        "short_delta": 0.30,
        "amount": 0.1,
        "qualified": True,
        "net_credit_effective": 0.0003,
        "margin_relief_ratio": 0.40,
        "width": 2000,
        "vrp_state": "PASS",
        "budget_decision": "ALLOW",
        "execution_feasibility_score": 80.0,
    }


def test_run_cycle_no_vrp_context_displays_menu_without_codes():
    ST = _setup()
    ctx = ST.run_cycle()
    assert ctx["console_phase"] == "PLAN_MENU_READY"
    assert ctx["display_candidates_count"] > 0
    assert ctx["lockable_candidates_count"] == 0
    assert ctx["not_lockable_reason"] == "VRP_CONTEXT_MISSING"
    assert not ctx["pending_candidates"]


def test_run_cycle_vrp_context_builds_library_then_locks():
    ST = _setup()
    _seed_market_context(ST)
    first = ST.run_cycle()
    assert first["console_phase"] == "HARD_APPROVAL_WAIT"
    assert first["pending_candidates"]
    code = first["pending_candidates"][0]["confirm_code"]
    fmz_shim._commands.append("执行:" + code)
    locked = ST.run_cycle()
    assert locked["last_command"] == "EXECUTE"
    assert locked["last_command_outcome"] == "locked"
    assert locked["console_phase"] == "PLAN_LOCKED"
    assert fmz_shim._G(ST._LOCKED_KEY)


def test_run_cycle_hard_approval_keeps_full_status_context_across_refreshes():
    ST = _setup()
    now = int(time.time() * 1000)
    _seed_market_context(ST, now)
    first = ST.run_cycle(now)
    second = ST.run_cycle(now + 1000)

    assert first["console_phase"] == "HARD_APPROVAL_WAIT"
    assert second["console_phase"] == "HARD_APPROVAL_WAIT"
    assert second["pending_candidates"]
    assert second["menu"]
    assert second["short_instrument"]
    assert second["preview_plan_detail"] == "stable_first_candidate"
    assert second["display_candidates_count"] == len(second["menu"])

    panel = ST.disp_status_panel(second, "测试")
    raw = panel.split("`", 1)[1].rsplit("`", 1)[0]
    titles = [t["title"] for t in json.loads(raw)]
    assert titles[0:3] == ["交互控制台", "运行概览", "完整主链模块回显"]
    assert any(t.startswith("固定备选方案库") for t in titles)
    assert any(t.startswith("候选方案预览") for t in titles)


def test_stable_menu_meta_requires_current_strategy_version():
    ST = _setup()
    now = int(time.time() * 1000)
    manual_context = ST._manual_context_for_cycle(now)
    meta = {
        "manual_context_id": manual_context["context_id"],
        "manual_context_hash": ST.manual_context_hash(manual_context),
        "config_signature": manual_context["config_signature"],
    }

    assert ST._stable_menu_meta_valid(meta, manual_context) is False
    meta["strategy_version"] = "3.0.17-manual-gate"
    assert ST._stable_menu_meta_valid(meta, manual_context) is False
    meta["strategy_version"] = ST.STRATEGY_VERSION
    assert ST._stable_menu_meta_valid(meta, manual_context) is True


def test_run_cycle_locked_plan_expires_and_rebuilds_library():
    ST = _setup()
    ST.APPROVAL_TTL_MS = 1000
    now = int(time.time() * 1000)
    _seed_market_context(ST, now)
    first = ST.run_cycle(now)
    fmz_shim._commands.append("执行:" + first["pending_candidates"][0]["confirm_code"])
    ST.run_cycle(now + 100)
    expired = ST.run_cycle(now + 2000)
    assert expired["lineage_invalidation"] == "APPROVAL_EXPIRED"
    assert expired["console_phase"] == "PLAN_MENU_READY"
    assert fmz_shim._G(ST._LOCKED_KEY) is None


def test_run_cycle_manual_context_change_invalidates_old_approval():
    ST = _setup()
    now = int(time.time() * 1000)
    _seed_market_context(ST, now)
    first = ST.run_cycle(now)
    fmz_shim._commands.append("执行:" + first["pending_candidates"][0]["confirm_code"])
    ST.run_cycle(now + 1)
    ST.ORDER_AMOUNT = 0.2
    changed = ST.run_cycle(now + 2)
    assert changed["lineage_invalidation"] == "MANUAL_CONTEXT_CHANGED"
    assert fmz_shim._G(ST._LOCKED_KEY) is None


def test_precommit_vrp_missing_context_fails_closed():
    ST = _setup()
    now = int(time.time() * 1000)
    ctx = ST._manual_context_for_cycle(now)
    lib = ST.build_recommendation_library([_candidate()], "s1", ctx, 1, now,
                                          config_hash=ctx["config_signature"])
    locked = lib["recommendations"][0]
    live = ST._build_precommit_live(locked, SPOT, ctx, now)
    pre = ST.evaluate_precommit_checks(locked, lib, live)
    assert live["vrp_pass"] is None
    assert "vrp_rechecked" in pre["failed"]


def test_precommit_vrp_rechecks_when_market_context_complete():
    ST = _setup()
    now = int(time.time() * 1000)
    ctx = _seed_market_context(ST, now)
    lib = ST.build_recommendation_library([_candidate()], "s1", ctx, 1, now,
                                          config_hash=ctx["config_signature"])
    locked = lib["recommendations"][0]
    live = ST._build_precommit_live(locked, SPOT, ctx, now)
    assert live["vrp_pass"] is True
    assert (live["vrp_gate"] or {}).get("pass") is True


def test_precommit_blocks_residual_entry_short_order_on_same_leg():
    ST = _setup()
    now = int(time.time() * 1000)
    ctx = _seed_market_context(ST, now)
    lib = ST.build_recommendation_library([_candidate()], "s1", ctx, 1, now,
                                          config_hash=ctx["config_signature"])
    locked = lib["recommendations"][0]
    orig = ST.dbt_get_open_orders
    try:
        ST.dbt_get_open_orders = lambda _currency: [
            {"order_id": "s1", "instrument_name": locked["short_instrument"],
             "label": "entry_short"}
        ]
        live = ST._build_precommit_live(locked, SPOT, ctx, now)
    finally:
        ST.dbt_get_open_orders = orig

    assert live["no_unknown_orders"] is False
    assert live["order_conflict_reason"] == "ENTRY_ACTIVE_ORDER_CONFLICT"


def test_precommit_blocks_extra_entry_protection_order_on_same_leg():
    ST = _setup()
    now = int(time.time() * 1000)
    ctx = _seed_market_context(ST, now)
    lib = ST.build_recommendation_library([_candidate()], "s1", ctx, 1, now,
                                          config_hash=ctx["config_signature"])
    locked = lib["recommendations"][0]
    orig = ST.dbt_get_open_orders
    try:
        ST.dbt_get_open_orders = lambda _currency: [
            {"order_id": "p-extra", "instrument_name": locked["long_instrument"],
             "label": "entry_prot"}
        ]
        live = ST._build_precommit_live(locked, SPOT, ctx, now)
    finally:
        ST.dbt_get_open_orders = orig

    assert live["no_unknown_orders"] is False
    assert live["order_conflict_reason"] == "ENTRY_ACTIVE_ORDER_CONFLICT"


def test_existing_position_manages_without_manual_planning_enabled():
    ST = _setup()
    ST.MANUAL_PLANNING_ALLOWED = False
    fmz_shim._G(ST._POSITION_KEY, {
        "position_id": "pos-manual",
        "manual_context_id": "manual-1",
        "side": "CALL",
        "short_instrument": "BTC-S-76000-C",
        "long_instrument": "BTC-S-78000-C",
        "remaining_short_qty": 0.1,
        "long_remaining_qty": 0.1,
        "short_expiry_ts": int(time.time() * 1000) + 48 * H,
        "entry_risk_anchor": {
            "entry_price": SPOT,
            "entry_dte_hours": 48,
            "entry_loss_boundary": 77000,
            "entry_touch_probability": 0.10,
            "entry_probability_confidence": "HIGH",
        },
    })
    ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)
    ctx = ST.run_cycle()
    assert ctx["console_phase"] == "POSITION_MANAGE"
    assert ctx.get("entry_snapshot", {}).get("position_id") == "pos-manual"


def test_position_manage_ctx_carries_structured_display_details():
    ST = _setup()
    now = int(time.time() * 1000)
    fmz_shim._G(ST._POSITION_KEY, {
        "position_id": "pos-display",
        "manual_context_id": "manual-1",
        "side": "CALL",
        "short_instrument": "BTC-S-76000-C",
        "long_instrument": "BTC-S-78000-C",
        "remaining_short_qty": 0.1,
        "long_remaining_qty": 0.1,
        "short_fill_amount": 0.1,
        "long_fill_amount": 0.1,
        "short_fill_price": 0.008,
        "long_fill_price": 0.0035,
        "entry_fees": 0.00001,
        "entry_profit_ceiling_net": 0.00044,
        "target_profit_amount": 0.000352,
        "max_total_exit_spend": 0.000088,
        "realized_exit_spend": 0.0,
        "short_expiry_ts": now + 48 * H,
        "entry_execution_report": {
            "fill_count": 2,
            "total_short_credit": 0.0008,
            "total_protection_cost": 0.00035,
            "total_fee_estimate": 0.00001,
            "actual_net_credit_after_fees": 0.00044,
        },
        "entry_risk_anchor": {
            "entry_price": SPOT,
            "entry_dte_hours": 48,
            "entry_loss_boundary": 77000,
            "entry_touch_probability": 0.10,
            "entry_probability_confidence": "HIGH",
        },
    })
    ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)

    ctx = ST.run_cycle(now)

    assert ctx["console_phase"] == "POSITION_MANAGE"
    assert ctx["position_detail"]["short_instrument"] == "BTC-S-76000-C"
    assert ctx["take_profit_detail"]["entry_profit_ceiling_net"] == 0.00044
    assert "action_cn" in ctx["hedge_detail"]
    assert ctx["ledger_detail"]["entry_fill_count"] == 2
    assert "option_unrealized_pnl_usd" in ctx["position_detail"]
    assert "combo_unrealized_pnl_usd" in ctx["position_detail"]
    assert ctx["take_profit_detail"]["tp_underlying_target_method"] in ("delta_linear", "data_gap")


def test_take_profit_exit_uses_config_gate_without_runtime_authorization():
    ST = _setup()
    orig = {name: getattr(ST, name) for name in (
        "dbt_get_positions", "dbt_get_open_orders", "_evaluate_take_profit",
        "_evaluate_hedge", "_evaluate_position_risk_now", "exec_exit_buyback_step")}
    ST.ALLOW_EXIT_TRADING = True
    now = int(time.time() * 1000)
    try:
        fmz_shim._G(ST._POSITION_KEY, {
            "position_id": "pos-auto-exit",
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
            "short_expiry_ts": now + 48 * H,
            "entry_risk_anchor": {"entry_price": SPOT, "entry_dte_hours": 48,
                                  "entry_loss_boundary": 77000,
                                  "entry_touch_probability": 0.10},
        })
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)
        ST.dbt_get_positions = lambda *_a: []
        ST.dbt_get_open_orders = lambda *_a: []
        ST._evaluate_take_profit = lambda *_a, **_k: {
            "qualified": True, "remaining_short_qty": 0.1, "remaining_budget": 0.001,
            "price_cap": 0.01, "quote_ok": True, "ratio": 0.85,
            "target_ratio": 0.8, "status": "已达标",
        }
        ST._evaluate_hedge = lambda *_a, **_k: {
            "perp_qty": 0.0, "target": 0.0, "orphan": False, "side": None,
            "venue": "BINANCE", "instrument": "BTCUSDC", "net_option_delta": 0.0,
            "delta_to_trade": 0.0,
            "venue_cfg": {"venue": "BINANCE", "instrument": "BTCUSDC"},
            "action": {"action": "HEDGE_HOLD", "reduce_only": False, "delta_contracts": 0.0},
        }
        ST._evaluate_position_risk_now = lambda *_a, **_k: {
            "tail_risk_state": "NORMAL",
            "current_risk": {"touch_probability_now": 0.20},
            "reason_codes": ["TOUCH_PROBABILITY_NORMAL"],
        }
        calls = []
        ST.exec_exit_buyback_step = lambda *a, **k: calls.append((a, k)) or {
            "dry": True, "filled": 0.0, "reason": "DRY"}

        out = ST.manage_cycle(now)

        assert out["auth"] is None
        assert calls and calls[0][0][0] == "BTC-S-76000-C"
        assert calls[0][1]["allow_taker"] is False
    finally:
        for name, value in orig.items():
            setattr(ST, name, value)


def test_take_profit_80_capture_near_expiry_does_not_buyback_without_risk():
    ST = _setup()
    orig = {name: getattr(ST, name) for name in (
        "dbt_get_positions", "dbt_get_open_orders", "_evaluate_hedge",
        "_evaluate_position_risk_now", "exec_exit_buyback_step")}
    ST.ALLOW_EXIT_TRADING = True
    ST.ALLOW_HEDGE_TRADING = True
    now = int(time.time() * 1000)
    try:
        fmz_shim._G(ST._POSITION_KEY, {
            "position_id": "pos-final-3h-tp-hold",
            "side": "CALL",
            "short_instrument": "BTC-S-76000-C",
            "long_instrument": "BTC-S-78000-C",
            "remaining_short_qty": 0.1,
            "long_remaining_qty": 0.1,
            "short_fill_amount": 0.1,
            "long_fill_amount": 0.1,
            "short_fill_price": 0.08,
            "long_fill_price": 0.0,
            "entry_profit_ceiling_net": 0.01,
            "target_profit_amount": 0.008,
            "max_total_exit_spend": 0.002,
            "realized_exit_spend": 0.0,
            "short_expiry_ts": now + 2 * H,
            "entry_risk_anchor": {"entry_price": SPOT, "entry_dte_hours": 24,
                                  "entry_loss_boundary": 77000,
                                  "entry_touch_probability": 0.10},
        })
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)
        ST.dbt_get_positions = lambda *_a: []
        ST.dbt_get_open_orders = lambda *_a: []
        ST._evaluate_hedge = lambda *_a, **_k: {
            "perp_qty": 0.0, "target": 0.0, "orphan": False, "side": None,
            "venue": "BINANCE", "instrument": "BTCUSDC", "net_option_delta": 0.0,
            "delta_to_trade": 0.0,
            "venue_cfg": {"venue": "BINANCE", "instrument": "BTCUSDC"},
            "action": {"action": "HEDGE_HOLD", "reduce_only": False, "delta_contracts": 0.0},
        }
        ST._evaluate_position_risk_now = lambda *_a, **_k: {
            "tail_risk_state": "NORMAL",
            "current_risk": {"touch_probability_now": 0.20},
            "reason_codes": ["TOUCH_PROBABILITY_NORMAL"],
        }
        calls = []
        ST.exec_exit_buyback_step = lambda *a, **k: calls.append((a, k)) or {
            "dry": True, "filled": 0.0, "reason": "DRY"}

        out = ST.manage_cycle(now)

        assert out["take_profit_detail"]["ratio"] >= 0.80
        assert out["take_profit_detail"]["qualified"] is False
        assert out["take_profit_detail"]["dte_gate_active"] is True
        assert out["take_profit_detail"]["dte_gate_reason"] == "TP_DTE_TOO_CLOSE_TO_EXPIRY"
        assert out["arb"]["preferred_action"] == "HOLD"
        assert calls == []
    finally:
        for name, value in orig.items():
            setattr(ST, name, value)


def test_near_expiry_take_profit_gate_does_not_block_risk_hedge_fallback():
    ST = _setup()
    orig = {name: getattr(ST, name) for name in (
        "dbt_get_positions", "dbt_get_open_orders", "_evaluate_hedge",
        "_evaluate_position_risk_now", "_risk_exit_budget_cap",
        "bnc_submit_hedge_order")}
    ST.ALLOW_EXIT_TRADING = True
    ST.ALLOW_HEDGE_TRADING = True
    now = int(time.time() * 1000)
    try:
        fmz_shim._G(ST._POSITION_KEY, {
            "position_id": "pos-final-3h-risk-hedge",
            "side": "CALL",
            "short_instrument": "BTC-S-76000-C",
            "long_instrument": "BTC-S-78000-C",
            "remaining_short_qty": 0.1,
            "long_remaining_qty": 0.1,
            "short_fill_amount": 0.1,
            "long_fill_amount": 0.1,
            "short_fill_price": 0.08,
            "long_fill_price": 0.0,
            "entry_profit_ceiling_net": 0.01,
            "target_profit_amount": 0.008,
            "max_total_exit_spend": 0.002,
            "realized_exit_spend": 0.0,
            "short_expiry_ts": now + 2 * H,
            "entry_risk_anchor": {"entry_price": SPOT, "entry_dte_hours": 24,
                                  "entry_loss_boundary": 77000,
                                  "entry_touch_probability": 0.10},
        })
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)
        ST.dbt_get_positions = lambda *_a: []
        ST.dbt_get_open_orders = lambda *_a: []
        ST._evaluate_hedge = lambda *_a, **_k: {
            "perp_qty": 0.0, "target": 0.02, "orphan": False, "side": "sell",
            "venue": "BINANCE", "instrument": "BTCUSDC", "net_option_delta": 0.02,
            "delta_to_trade": 0.02,
            "venue_cfg": {"venue": "BINANCE", "instrument": "BTCUSDC",
                          "linear": True, "exchange_index": 1},
            "action": {"action": "HEDGE_OPEN", "reduce_only": False, "delta_contracts": 0.02},
        }
        ST._evaluate_position_risk_now = lambda *_a, **_k: {
            "tail_risk_state": ST.STATE_HEDGE_READY,
            "current_risk": {"touch_probability_now": 0.62},
            "reason_codes": ["TOUCH_PROBABILITY_DETERIORATED"],
        }
        ST._risk_exit_budget_cap = lambda *_a, **_k: {
            "remaining_budget": 0.001, "price_cap": 0.0, "within": False,
            "within_price": False, "quote_ok": True, "ask": 0.004,
            "ask_depth": 0.01, "depth_ok": False, "reason": "EXIT_DEPTH_INSUFFICIENT",
        }
        calls = []
        ST.bnc_submit_hedge_order = lambda **kw: calls.append(kw) or {
            "order_id": "hedge-test", "filled": 0.0, "dry": True,
            "reason": "BINANCE_HEDGE_DRYRUN"}

        out = ST.manage_cycle(now)

        assert out["take_profit_detail"]["ratio"] >= 0.80
        assert out["take_profit_detail"]["qualified"] is False
        assert out["take_profit_detail"]["dte_gate_active"] is True
        assert out["arb"]["preferred_action"] == "EXIT_PREFERRED"
        assert out["arb"]["executable_action"] == "HEDGE_READY"
        assert calls and calls[0]["symbol"] == "BTCUSDC"
    finally:
        for name, value in orig.items():
            setattr(ST, name, value)


def test_manage_cycle_records_resolved_pending_hedge_fill_to_history():
    ST = _setup()
    orig = {name: getattr(ST, name) for name in (
        "dbt_get_positions", "dbt_get_open_orders", "_evaluate_take_profit",
        "_evaluate_hedge", "_evaluate_position_risk_now", "bnc_get_hedge_order")}
    now = int(time.time() * 1000)
    snap = {
        "position_id": "pos-pending-hedge-fill",
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
        "short_expiry_ts": now + 48 * H,
        "entry_risk_anchor": {"entry_price": SPOT, "entry_dte_hours": 48,
                              "entry_loss_boundary": 77000,
                              "entry_touch_probability": 0.10},
    }
    try:
        fmz_shim._G(ST._POSITION_KEY, snap)
        ST.ledger_set_state(ST.S_SHORT_ACTIVE_PROTECTED)
        st = ST._hedge_policy_state(snap)
        st.update({"pending_order_id": "hedge-fill-ledger",
                   "pending_order_created_ts": now - 1000,
                   "pending_order_side": "sell",
                   "pending_order_qty": 0.01,
                   "pending_is_add": False,
                   "pending_reduce_only": True})
        ST._hedge_policy_save_state(st)
        ST.dbt_get_positions = lambda *_a: []
        ST.dbt_get_open_orders = lambda *_a: []
        ST._evaluate_take_profit = lambda *_a, **_k: {
            "qualified": False, "remaining_short_qty": 0.1, "remaining_budget": 0.001,
            "price_cap": 0.01, "quote_ok": True, "ratio": 0.20,
            "target_ratio": 0.8, "status": "未达标",
        }
        ST._evaluate_hedge = lambda *_a, **_k: {
            "perp_qty": 0.0, "target": 0.0, "orphan": False, "side": None,
            "venue": "BINANCE", "instrument": "BTCUSDC", "net_option_delta": 0.0,
            "delta_to_trade": 0.0,
            "venue_cfg": {"venue": "BINANCE", "instrument": "BTCUSDC",
                          "linear": True, "exchange_index": 1},
            "action": {"action": "HEDGE_HOLD", "reduce_only": False, "delta_contracts": 0.0},
        }
        ST._evaluate_position_risk_now = lambda *_a, **_k: {
            "tail_risk_state": "NORMAL",
            "current_risk": {"touch_probability_now": 0.20},
            "reason_codes": ["TOUCH_PROBABILITY_NORMAL"],
        }
        ST.bnc_get_hedge_order = lambda *_a, **_k: {
            "Id": "hedge-fill-ledger", "Status": 2,
            "DealAmount": 0.01, "AvgPrice": 59950.0}

        ST.manage_cycle(now)

        saved = fmz_shim._G(ST._POSITION_KEY)
        hist = saved.get("hedge_execution_history") or []
        assert hist
        assert hist[-1]["order_id"] == "hedge-fill-ledger"
        assert hist[-1]["filled"] == 0.01
        assert hist[-1]["reduce_only"] is True
    finally:
        for name, value in orig.items():
            setattr(ST, name, value)


def test_risk_exit_budget_cap_requires_best_ask_depth():
    ST = _setup()
    snap = {
        "short_instrument": "BTC-S-76000-C",
        "remaining_short_qty": 0.10,
        "max_total_exit_spend": 0.001,
        "realized_exit_spend": 0.0,
    }

    result = ST._risk_exit_budget_cap(
        snap, None,
        lambda _inst: {"mark": 0.004, "best_ask": 0.004,
                       "best_ask_amount": 0.01, "tick": 0.0001})

    assert result["within_price"] is True
    assert result["ask_depth"] == 0.01
    assert result["depth_ok"] is False
    assert result["within"] is False
    assert result["reason"] == "EXIT_DEPTH_INSUFFICIENT"


def test_position_manage_routine_emit_keeps_log_silent():
    ST = _setup()
    logs = []
    statuses = []
    orig_log, orig_status = ST.Log, ST.LogStatus
    try:
        ST.Log = lambda *args: logs.append(" ".join(str(a) for a in args))
        ST.LogStatus = lambda *args: statuses.append(" ".join(str(a) for a in args))
        base = ST._ctx_base(ST.S_SHORT_ACTIVE_PROTECTED, SPOT, "RUN_CYCLE:POSITION_MANAGE")
        base.update(
            console_phase="POSITION_MANAGE",
            position_detail={"lifecycle": "已保护·卖方持仓",
                             "short_mark": 0.0012, "long_mark": 0.0001,
                             "combo_unrealized_pnl_usd": 1.23,
                             "hedge_pnl_state": "对冲未启用"},
            take_profit_detail={"status": "未达标", "ratio": 0.225, "target_ratio": 0.8},
            hedge_detail={"action_cn": "保持", "touch_probability_now": 0.385},
            ledger_detail={"reconciled": True, "recovery_state": "OK"},
        )
        ST._emit(base, "manual-gate")
        noisy = dict(base, position_detail=dict(base["position_detail"], short_mark=0.0013))
        ST._emit(noisy, "manual-gate")
    finally:
        ST.Log = orig_log
        ST.LogStatus = orig_status
    assert len(statuses) == 2
    assert logs == []


def test_position_manage_key_hedge_step_still_writes_event_log():
    ST = _setup()
    logs = []
    statuses = []
    orig_log, orig_status = ST.Log, ST.LogStatus
    try:
        ST.Log = lambda *args: logs.append(" ".join(str(a) for a in args))
        ST.LogStatus = lambda *args: statuses.append(" ".join(str(a) for a in args))
        ctx = ST._ctx_base(ST.S_SHORT_ACTIVE_PROTECTED, SPOT, "RUN_CYCLE:POSITION_MANAGE")
        ctx.update(
            console_phase="POSITION_MANAGE",
            hedge_step={"side": "sell", "amount": 0.001, "filled": 0.001,
                        "avg_price": 60000.0, "reason": "BINANCE_HEDGE_STEP"},
            hedge_detail={"action_cn": "增加对冲"},
            position_detail={"lifecycle": "已保护·卖方持仓",
                             "combo_unrealized_pnl_usd": -1.5,
                             "hedge_pnl_state": "对冲浮盈亏 0.25 USD"},
        )
        ST._emit(ctx, "manual-gate")
    finally:
        ST.Log = orig_log
        ST.LogStatus = orig_status
    assert len(statuses) == 1
    assert len(logs) == 1
    assert "对冲订单" in logs[0]
    assert "BINANCE_HEDGE_STEP" in logs[0]


def test_emit_deduplicates_repeated_log_summary_but_refreshes_status():
    ST = _setup()
    logs = []
    statuses = []
    orig_log, orig_status = ST.Log, ST.LogStatus
    try:
        ST.Log = lambda *args: logs.append(" ".join(str(a) for a in args))
        ST.LogStatus = lambda *args: statuses.append(" ".join(str(a) for a in args))
        ctx = ST._ctx_base(ST.S_NO_POSITION, SPOT, "RUN_CYCLE:HARD_APPROVAL_WAIT")
        ST._emit(ctx, "manual-gate")
        ST._emit(dict(ctx), "manual-gate")
        changed = dict(ctx, reason="RUN_CYCLE:PLAN_MENU_READY")
        ST._emit(changed, "manual-gate")
    finally:
        ST.Log = orig_log
        ST.LogStatus = orig_status
    assert len(statuses) == 3
    assert len(logs) == 2


def test_startup_self_check_records_read_only_interface_statuses():
    ST = _setup()
    orig = {name: getattr(ST, name) for name in (
        "HEDGE_VENUE", "dbt_index_price", "dbt_get_instruments",
        "dbt_account_summary", "bnc_get_position_btc", "fetch_gex_vrp_context")}
    try:
        ST.HEDGE_VENUE = "BINANCE"
        ST.dbt_index_price = lambda currency: 60000.0
        ST.dbt_get_instruments = lambda currency, kind: [{"instrument_name": "BTC-TEST"}]
        ST.dbt_account_summary = lambda currency: {
            "margin_model": "segregated_pm", "portfolio_margining_enabled": True}
        ST.bnc_get_position_btc = lambda symbol: 0.0
        ST.fetch_gex_vrp_context = lambda *_a, **_k: {
            "valid": True,
            "status": "OK",
            "market_context": {"source": "GEX_MONITOR_IV_RV_RANK"},
        }

        result = ST._startup_self_check("BTC")
    finally:
        for name, value in orig.items():
            setattr(ST, name, value)

    assert result["overall"] == "OK"
    checks = result["checks"]
    assert checks["deribit_index"]["ok"] is True
    assert checks["deribit_options"]["ok"] is True
    assert checks["deribit_account"]["ok"] is True
    assert checks["gex_context"]["ok"] is True
    assert checks["binance_hedge_position"]["ok"] is True
    assert fmz_shim._G(ST._SELF_CHECK_KEY) == result
