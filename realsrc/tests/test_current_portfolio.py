# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import fmz_shim
import strategy as ST


NOW = 1_000_000_000


def _clear():
    fmz_shim._STORE.clear()


def _patch(**items):
    old = {name: getattr(ST, name) for name in items}
    for name, value in items.items():
        setattr(ST, name, value)
    return old


def _restore(old):
    for name, value in old.items():
        setattr(ST, name, value)


def test_current_portfolio_empty_read_uses_real_account_margin_not_fixed_zero():
    _clear()
    old = _patch(
        dbt_account_summary=lambda _currency: {
            "initial_margin": 0.02,
            "equity": 1.0,
        },
        dbt_get_positions_strict=lambda _currency, kind=None: [] if kind == "option" else [],
    )
    try:
        current = ST._current_portfolio()
    finally:
        _restore(old)

    assert current["data_gap"] is None
    assert current["open_positions"] == 0
    assert current["short_gamma"] == 0.0
    assert current["short_vega"] == 0.0
    assert current["margin_used"] == 0.02
    assert current["margin_used_source"] == "initial_margin/equity"


def test_current_portfolio_account_summary_gap_blocks_budget_inputs():
    _clear()
    old = _patch(
        dbt_account_summary=lambda _currency: None,
        dbt_get_positions_strict=lambda _currency, kind=None: [],
    )
    try:
        current = ST._current_portfolio()
    finally:
        _restore(old)

    assert current["data_gap"] == "ACCOUNT_SUMMARY_QUERY_FAILED"
    assert "margin_used" not in current


def test_current_portfolio_option_position_gap_blocks_budget_inputs():
    _clear()
    old = _patch(
        dbt_account_summary=lambda _currency: {"initial_margin": 0.02, "equity": 1.0},
        dbt_get_positions_strict=lambda _currency, kind=None: None if kind == "option" else [],
    )
    try:
        current = ST._current_portfolio()
    finally:
        _restore(old)

    assert current["data_gap"] == "OPTION_POSITION_QUERY_FAILED"


def test_current_portfolio_short_option_greek_gap_blocks_budget_inputs():
    _clear()
    old = _patch(
        dbt_account_summary=lambda _currency: {"initial_margin": 0.02, "equity": 1.0},
        dbt_get_positions_strict=lambda _currency, kind=None: [
            {"instrument_name": "BTC-X-90000-P", "size": -0.2}
        ],
        dbt_ticker=lambda _inst: {"greeks": {"gamma": 0.0004}},
    )
    try:
        current = ST._current_portfolio()
    finally:
        _restore(old)

    assert current["data_gap"] == "OPTION_GREEK_DATA_GAP"
    assert current["data_gap_instrument"] == "BTC-X-90000-P"


def test_current_portfolio_short_option_greeks_accumulate_short_load():
    _clear()
    old = _patch(
        dbt_account_summary=lambda _currency: {"initial_margin": 0.02, "equity": 1.0},
        dbt_get_positions_strict=lambda _currency, kind=None: [
            {"instrument_name": "BTC-X-90000-P", "size": -0.2}
        ],
        dbt_ticker=lambda _inst: {"greeks": {"gamma": 0.0004, "vega": 0.12}},
    )
    try:
        current = ST._current_portfolio()
    finally:
        _restore(old)

    assert current["data_gap"] is None
    assert current["open_positions"] == 1
    assert abs(current["short_gamma"] - 0.00008) < 1e-12
    assert abs(current["short_vega"] - 0.024) < 1e-12


def test_precommit_budget_blocks_when_current_portfolio_has_data_gap():
    _clear()
    quote = {
        "mark": 0.003,
        "best_bid": 0.0029,
        "best_ask": 0.0031,
        "tick": 0.0001,
        "gamma": 0.0001,
    }
    locked = {
        "short_instrument": "BTC-X-90000-P",
        "long_instrument": "BTC-X-87500-P",
        "amount": 0.1,
        "max_loss": 0.01,
        "side": "PUT",
    }
    manual_context = {
        "direction_bias": "SHORT_PUT",
        "expires_ts_ms": NOW + 60_000,
        "planning_scope": {},
        "risk_policy": {},
        "market_context": {
            "source": "GEX_MONITOR_IV_RV_RANK",
            "side": "SHORT_PUT",
            "iv_rv_ratio": 1.2,
            "iv_rv_rank_pct": 70,
        },
    }
    old = _patch(
        exec_quote=lambda _inst: dict(quote),
        spm_simulate_structure=lambda *_args, **_kwargs: {
            "im_with_protection": 0.01,
            "relief_ratio": 0.2,
        },
        ledger_reconcile=lambda _currency: {"actual": {}, "expected": {}},
        validate_manual_context=lambda _ctx, _now: {"valid": True},
        _current_portfolio=lambda: {"data_gap": "ACCOUNT_SUMMARY_QUERY_FAILED"},
        dbt_get_open_orders=lambda _currency: [],
    )
    try:
        live = ST._build_precommit_live(locked, 88000.0, manual_context, NOW)
    finally:
        _restore(old)

    assert live["projected_budget_decision"] == "BLOCK"
    assert live["current_portfolio_data_gap"] == "ACCOUNT_SUMMARY_QUERY_FAILED"
    assert live["_budget"]["fail_closed"] is True
    assert "CURRENT_PORTFOLIO_DATA_GAP:ACCOUNT_SUMMARY_QUERY_FAILED" in live["_budget"]["reason_codes"]


def test_precommit_budget_blocks_when_proposed_short_vega_missing():
    _clear()
    quote = {
        "mark": 0.003,
        "best_bid": 0.0029,
        "best_ask": 0.0031,
        "tick": 0.0001,
        "gamma": 0.0001,
    }
    locked = {
        "short_instrument": "BTC-X-90000-P",
        "long_instrument": "BTC-X-87500-P",
        "amount": 0.1,
        "max_loss": 0.01,
        "side": "PUT",
    }
    manual_context = {
        "direction_bias": "SHORT_PUT",
        "expires_ts_ms": NOW + 60_000,
        "planning_scope": {},
        "risk_policy": {},
        "market_context": {
            "source": "GEX_MONITOR_IV_RV_RANK",
            "side": "SHORT_PUT",
            "iv_rv_ratio": 1.2,
            "iv_rv_rank_pct": 70,
        },
    }
    old = _patch(
        exec_quote=lambda _inst: dict(quote),
        spm_simulate_structure=lambda *_args, **_kwargs: {
            "im_with_protection": 0.01,
            "relief_ratio": 0.2,
        },
        ledger_reconcile=lambda _currency: {"actual": {}, "expected": {}},
        validate_manual_context=lambda _ctx, _now: {"valid": True},
        _current_portfolio=lambda: {
            "data_gap": None,
            "open_positions": 0,
            "short_gamma": 0.0,
            "short_vega": 0.0,
            "margin_used": 0.0,
        },
        dbt_get_open_orders=lambda _currency: [],
    )
    try:
        live = ST._build_precommit_live(locked, 88000.0, manual_context, NOW)
    finally:
        _restore(old)

    assert live["projected_budget_decision"] == "BLOCK"
    assert live["_budget"]["fail_closed"] is True
    assert "BUDGET_INPUT_INCOMPLETE:short_vega" in live["_budget"]["reason_codes"]
