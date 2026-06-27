# -*- coding: utf-8 -*-
"""R6：整合 PLAN 通顺缝端到端——真实 _build_menu → GEX VRP_CONTEXT → 组合硬预算 → 可锁定方案。

证明执行 bundle 的主流程真正用上整合层（VRP_CONTEXT/预算只过滤、独立 AND 门），而非模块挂着不用。
"""
import os, sys, time, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import fmz_shim

H = 3600000
SPOT = 73400.0
S48 = {74000: (0.45, 0.016), 75000: (0.38, 0.012), 76000: (0.30, 0.008),
       77000: (0.22, 0.005), 78000: (0.15, 0.0035)}
_BASE = {"t": None}


def _handler(*args):
    _, _m, path, query = args
    from urllib.parse import parse_qs
    qs = parse_qs(query or "")
    if _BASE["t"] is None:
        _BASE["t"] = int(time.time() * 1000)
    now = _BASE["t"]
    if path.endswith("/public/get_instruments"):
        return {"result": [{"instrument_name": "BTC-S-%d-C" % k, "strike": k, "option_type": "call",
                            "expiration_timestamp": now + 48 * H, "kind": "option", "tick_size": 0.0001}
                           for k in S48]}
    if path.endswith("/public/get_index_price"):
        return {"result": {"index_price": SPOT}}
    if path.endswith("/public/ticker"):
        k = int(qs.get("instrument_name", ["BTC-S-76000-C"])[0].split("-")[2])
        d, m = S48[k]
        return {"result": {"mark_price": m, "best_bid_price": round(m * 0.97, 6),
                           "best_ask_price": round(m * 1.03, 6), "underlying_price": SPOT,
                           "greeks": {"delta": d, "gamma": 0.00005}, "mark_iv": 0.7}}
    if path.endswith("/public/get_instrument"):
        return {"result": {"tick_size": 0.0001, "contract_size": 1, "min_trade_amount": 0.1}}
    if path.endswith("/private/get_account_summary"):
        return {"result": {"margin_model": "segregated_pm", "portfolio_margining_enabled": True}}
    if path.endswith("/private/get_positions"):
        return {"result": []}
    if path.endswith("/private/simulate_portfolio"):
        sp = json.loads(qs.get("simulated_positions", ["{}"])[0])
        im = 0.025 if len(sp) == 1 else 0.013
        return {"result": {"initial_margin": im, "maintenance_margin": im * 0.8, "available_funds": 1.0}}
    return {"result": None}


def _setup():
    fmz_shim.exchange.io_handler = _handler
    import strategy as ST
    ST.SETTLEMENT_CURRENCY = "BTC"; ST.DIRECTION_BIAS = "SHORT_CALL"
    ST.MENU_SIZE = 6; ST.SHORT_DELTA_RANGE = (0.15, 0.45); ST.PROTECTION_WIDTH_RANGE = (2000, 2500)
    ST.PLAN_WEIGHTS = {"win_rate": 0.35, "rr": 0.25, "efficiency": 0.40, "manual": 0.0}
    ST.TARGET_DTE_HOURS = 24; ST.ORDER_AMOUNT = 0.1; ST.MIN_MARGIN_RELIEF_RATIO = 0.0
    ST.UNDERLYING_REF_PRICE = None; ST.MAX_SPREAD_RATIO = 0.60
    ST._LOCKED["detail_id"] = None
    return ST


_GEX_VALID = dict(source="GEX_MONITOR_IV_RV_RANK", side="SHORT_CALL",
                  iv_rv_ratio=0.8, iv_rv_rank_pct=15.2)
_UNSUPPORTED_CONTEXT = dict(side="SHORT_CALL", front_anchor_iv=0.92, rv_24h=0.42)


def test_no_context_displays_menu_but_is_not_lockable():
    ST = _setup()
    out = ST.integrated_plan_preview(SPOT)
    assert out["reason"] == "OK" and out["menu"]
    assert out["lockable"] == []
    assert out["not_lockable_reason"] == "VRP_CONTEXT_MISSING"          # 无 VRP/预算上下文 → 不生成可锁定确认码


def test_unsupported_vrp_context_blocks_all_lockable_empty():
    ST = _setup()
    out = ST.integrated_plan_preview(SPOT, market_context=_UNSUPPORTED_CONTEXT)
    assert out["vrp_blocked"] and len(out["vrp_blocked"]) == len(out["menu"])
    assert out["lockable"] == []                    # 非 GEX 上下文不再走旧价格门控，fail-closed
    assert all(b["reason_codes"] for b in out["vrp_blocked"])


def test_gex_valid_context_makes_menu_lockable():
    ST = _setup()
    out = ST.integrated_plan_preview(SPOT, market_context=_GEX_VALID)
    assert out["vrp_passed"] is not None and out["vrp_blocked"] is not None
    assert len(out["vrp_passed"]) + len(out["vrp_blocked"]) == len(out["menu"])  # 纯过滤、partition 完整
    assert out["lockable"] == out["menu"]           # GEX 只检查上下文有效性，不按旧价格门控筛选


def test_portfolio_budget_breach_blocks_lockable():
    ST = _setup()
    pstate = {"current": {"open_positions": 2, "short_gamma": 0.9, "short_vega": 0.0, "margin_used": 0.0},
              "limits": {"max_open_positions": 1, "max_short_gamma": 0.5, "max_short_vega": 1.0, "max_margin": 5000.0},
              "proposed_size": 0.1}
    out = ST.integrated_plan_preview(SPOT, market_context=_GEX_VALID, portfolio_state=pstate)
    assert out["portfolio_budget"]["decision"] == "BLOCK"
    assert out["lockable"] == []                    # 组合预算超限 → 无可锁定（入场前 AND 门）
