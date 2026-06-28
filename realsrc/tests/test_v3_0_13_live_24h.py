# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import config as C
import leg_selection as L
import manual_context as M
import plans as P

H = 3600000
SPOT = 60000.0


def test_default_config_is_live_ready_without_legacy_operator_fields():
    assert C.STRATEGY_VERSION == "3.2.13-manual-gate"
    assert C.RUN_PROFILE == "LIVE"
    assert C.DRY_RUN_PASSED is True
    assert C.ALLOW_ENTRY_TRADING is True
    assert C.ALLOW_EXIT_TRADING is True
    assert C.ALLOW_HEDGE_TRADING is True
    assert C.RISK_EXIT_MAX_SPEND > 0
    assert C.validate_config() == []
    for name in (
        "MANUAL_AUDIT_CARD_ID",
        "MANUAL_AUDIT_NOTE",
        "MANUAL_CONTEXT_TTL_MIN",
        "ROUND_MODE",
        "SELECTED_PLAN",
        "SHORT_DTE_HOURS",
        "ALLOW_TRADING",
        "KILL_SWITCH",
        "HEDGE_MAKER_FIRST_REDUCE_ENABLED",
        "HEDGE_SLIPPAGE_GUARD_ENABLED",
        "HEDGE_LOSS_BOUNDARY_BUFFER_SIGMA",
        "HEDGE_SLIP_ALERT_BPS",
        "HEDGE_CONTRACT_SIZE_FALLBACK",
        "HEDGE_MIN_TRADE_FALLBACK",
    ):
        assert not hasattr(C, name)
    assert C.TARGET_DTE_HOURS == 24


def test_manual_context_no_longer_requires_audit_reference():
    ctx = M.build_manual_context(
        1000,
        True,
        "SHORT_PUT",
        24,
        (0.15, 0.45),
        (2000, 2500),
        0.1,
        30 * 60 * 1000,
        {"allow_auto_take_profit": True},
    )
    check = M.validate_manual_context(ctx, 1000)
    assert check == {"valid": True, "errors": []}
    assert "audit_reference" not in ctx
    assert ctx["planning_scope"]["target_dte_hours"] == 24


def _inst(now, h, strike):
    return {
        "instrument_name": "BTC-E%d-%d-C" % (h, strike),
        "strike": strike,
        "option_type": "call",
        "expiration_timestamp": now + h * H,
        "kind": "option",
        "tick_size": 0.00001,
    }


def _put_inst(now, h, strike):
    return {
        "instrument_name": "BTC-E%d-%d-P" % (h, strike),
        "strike": strike,
        "option_type": "put",
        "expiration_timestamp": now + h * H,
        "kind": "option",
        "tick_size": 0.00001,
    }


def test_target_expiry_picker_returns_nearest_24h_and_next_later_only():
    now = 1000000
    instruments = [_inst(now, h, 61000) for h in (18, 26, 49, 70)]
    chosen = L.legsel_target_expiries(instruments, 24, now, True, max_expiries=2)
    assert [round(L.legsel_dte_hours(exp, now)) for exp in chosen] == [26, 49]

    one = L.legsel_target_expiries([_inst(now, 20, 61000)], 24, now, True, max_expiries=2)
    assert [round(L.legsel_dte_hours(exp, now)) for exp in one] == [20]


def test_plan_rank_prefers_24h_capital_efficiency_over_total_premium():
    weights = {"win_rate": 0.35, "rr": 0.25, "efficiency": 0.40, "manual": 0.0}
    fast = {
        "name": "near_24h",
        "qualified": True,
        "win_rate": 0.65,
        "rr": 0.12,
        "credit_on_margin_per_24h": 0.04,
        "delta_fit": 0.5,
        "execution_feasibility_penalty": 1.0,
        "tags": [],
    }
    slow = {
        "name": "longer_total_credit",
        "qualified": True,
        "win_rate": 0.65,
        "rr": 0.24,
        "credit_on_margin_per_24h": 0.01,
        "delta_fit": 0.5,
        "execution_feasibility_penalty": 1.0,
        "tags": [],
    }
    assert P.plan_rank([slow, fast], weights, 2)[0]["name"] == "near_24h"


def test_menu_keeps_thin_low_relief_24h_candidates_and_limits_expiries():
    import strategy as ST

    now = 2000000
    instruments = []
    for h in (18, 26, 49, 70):
        instruments.append(_inst(now, h, 61000))
        instruments.append(_inst(now, h, 63000))

    def quote(inst):
        strike = int(inst.split("-")[2])
        if strike == 61000:
            return {
                "mark": 0.00045,
                "best_bid": 0.00044,
                "best_ask": 0.00046,
                "tick": 0.00001,
                "delta": 0.30,
                "gamma": 0.00001,
            }
        return {
            "mark": 0.00010,
            "best_bid": 0.00009,
            "best_ask": 0.00010,
            "tick": 0.00001,
            "delta": 0.10,
            "gamma": 0.00001,
        }

    old = {
        name: getattr(ST, name)
        for name in (
            "SETTLEMENT_CURRENCY",
            "DIRECTION_BIAS",
            "SHORT_DELTA_RANGE",
            "PROTECTION_WIDTH_RANGE",
            "ORDER_AMOUNT",
            "MENU_SIZE",
            "MIN_MARGIN_RELIEF_RATIO",
            "UNDERLYING_REF_PRICE",
            "dbt_get_instruments",
            "_delta_lookup",
            "_quote_cache",
            "dbt_account_summary",
            "spm_account_is_portfolio_margin",
            "spm_simulate_structure",
        )
    }
    try:
        ST.SETTLEMENT_CURRENCY = "BTC"
        ST.DIRECTION_BIAS = "SHORT_CALL"
        ST.SHORT_DELTA_RANGE = (0.15, 0.45)
        ST.PROTECTION_WIDTH_RANGE = (2000, 2500)
        ST.ORDER_AMOUNT = 0.1
        ST.MENU_SIZE = 10
        ST.MIN_MARGIN_RELIEF_RATIO = 0.0
        ST.UNDERLYING_REF_PRICE = None
        ST.dbt_get_instruments = lambda *_args, **_kwargs: list(instruments)
        ST._delta_lookup = lambda: (lambda inst: quote(inst)["delta"])
        ST._quote_cache = lambda: quote
        ST.dbt_account_summary = lambda *_args, **_kwargs: {
            "margin_model": "segregated_pm",
            "portfolio_margining_enabled": True,
        }
        ST.spm_account_is_portfolio_margin = lambda *_args, **_kwargs: (
            True,
            "segregated_pm",
        )
        ST.spm_simulate_structure = lambda *_args, **_kwargs: {
            "im_short_only": 0.0300,
            "im_with_protection": 0.0294,
            "relief_abs": 0.0006,
            "relief_ratio": 0.02,
        }

        menu, _pm_ok, _model, reason, _diag = ST._build_menu(now, SPOT)
    finally:
        for name, value in old.items():
            setattr(ST, name, value)

    assert reason == "OK"
    assert menu
    assert sorted({round(p["short_dte_hours"]) for p in menu}) == [26, 49]
    assert all(p["short_mark"] < 0.0005 for p in menu)
    assert all(p["qualified"] for p in menu)
    assert all(p.get("credit_on_margin_per_24h") for p in menu)


def test_menu_keeps_20h_put_when_low_premium_protection_is_buyable():
    import strategy as ST

    now = 3000000
    instruments = [
        _put_inst(now, 20, 59500),
        _put_inst(now, 20, 60000),
        _put_inst(now, 20, 57500),
        _put_inst(now, 20, 58000),
        _put_inst(now, 20, 58500),
        _put_inst(now, 45, 60000),
        _put_inst(now, 45, 57500),
    ]
    quotes = {
        "BTC-E20-59500-P": {"mark": 0.0010, "best_bid": 0.0008, "best_ask": 0.0010,
                            "tick": 0.0001, "delta": -0.155, "gamma": 0.00031},
        "BTC-E20-60000-P": {"mark": 0.0024, "best_bid": 0.0021, "best_ask": 0.0025,
                            "tick": 0.0001, "delta": -0.33, "gamma": 0.00055},
        "BTC-E20-57500-P": {"mark": 0.0002, "best_bid": 0.0001, "best_ask": 0.0003,
                            "tick": 0.0001, "delta": -0.02, "gamma": 0.00002},
        "BTC-E20-58000-P": {"mark": 0.0002, "best_bid": 0.0001, "best_ask": 0.0003,
                            "tick": 0.0001, "delta": -0.03, "gamma": 0.00003},
        "BTC-E20-58500-P": {"mark": 0.0003, "best_bid": 0.0002, "best_ask": 0.0004,
                            "tick": 0.0001, "delta": -0.04, "gamma": 0.00004},
        "BTC-E45-60000-P": {"mark": 0.0066, "best_bid": 0.0060, "best_ask": 0.0070,
                            "tick": 0.0001, "delta": -0.41, "gamma": 0.00030},
        "BTC-E45-57500-P": {"mark": 0.0007, "best_bid": 0.0006, "best_ask": 0.0009,
                            "tick": 0.0001, "delta": -0.06, "gamma": 0.00006},
    }

    old = {
        name: getattr(ST, name)
        for name in (
            "SETTLEMENT_CURRENCY",
            "DIRECTION_BIAS",
            "SHORT_DELTA_RANGE",
            "PROTECTION_WIDTH_RANGE",
            "ORDER_AMOUNT",
            "MENU_SIZE",
            "MIN_MARGIN_RELIEF_RATIO",
            "UNDERLYING_REF_PRICE",
            "dbt_get_instruments",
            "_delta_lookup",
            "_quote_cache",
            "dbt_account_summary",
            "spm_account_is_portfolio_margin",
            "spm_simulate_structure",
        )
    }
    try:
        ST.SETTLEMENT_CURRENCY = "BTC"
        ST.DIRECTION_BIAS = "SHORT_PUT"
        ST.SHORT_DELTA_RANGE = (0.15, 0.45)
        ST.PROTECTION_WIDTH_RANGE = (2000, 2500)
        ST.ORDER_AMOUNT = 0.1
        ST.MENU_SIZE = 10
        ST.MIN_MARGIN_RELIEF_RATIO = 0.0
        ST.UNDERLYING_REF_PRICE = None
        ST.dbt_get_instruments = lambda *_args, **_kwargs: list(instruments)
        ST._delta_lookup = lambda: (lambda inst: quotes[inst]["delta"])
        ST._quote_cache = lambda: (lambda inst: quotes[inst])
        ST.dbt_account_summary = lambda *_args, **_kwargs: {
            "margin_model": "segregated_pm",
            "portfolio_margining_enabled": True,
        }
        ST.spm_account_is_portfolio_margin = lambda *_args, **_kwargs: (
            True,
            "segregated_pm",
        )
        ST.spm_simulate_structure = lambda *_args, **_kwargs: {
            "im_short_only": 0.0300,
            "im_with_protection": 0.0294,
            "relief_abs": 0.0006,
            "relief_ratio": 0.02,
        }

        menu, _pm_ok, _model, reason, _diag = ST._build_menu(now, 60140.0)
    finally:
        for name, value in old.items():
            setattr(ST, name, value)

    assert reason == "OK"
    near = [p for p in menu if round(p["short_dte_hours"]) == 20]
    assert len(near) >= 2
    assert {p["short_strike"] for p in near} >= {59500, 60000}
    assert any(p["width"] == 1500 for p in near)
    assert len([p for p in near if p["short_strike"] == 60000]) <= 2
