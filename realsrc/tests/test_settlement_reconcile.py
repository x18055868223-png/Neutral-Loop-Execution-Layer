# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import fmz_shim
import strategy as ST


NOW = 1_000_000_000


def _clear():
    fmz_shim._STORE.clear()


def _expired():
    return NOW - ST.SETTLEMENT_RECONCILE_GRACE_MS - 1


def _future():
    return NOW + ST.SETTLEMENT_RECONCILE_GRACE_MS + 1


def _snap(expiry=None):
    exp = _expired() if expiry is None else expiry
    return {
        "position_id": "pos-settle",
        "side": "PUT",
        "short_instrument": "BTC-1JAN26-90000-P",
        "long_instrument": "BTC-1JAN26-87500-P",
        "remaining_short_qty": 0.1,
        "long_remaining_qty": 0.1,
        "short_expiry_ts": exp,
        "long_expiry_ts": exp,
    }


def test_settlement_finalizer_short_expired_absent_sets_remaining_short_zero():
    _clear()
    snap = _snap()
    opt_pos = [{"instrument_name": snap["long_instrument"], "size": 0.1}]

    out = ST._settlement_reconcile_snapshot(snap, opt_pos, NOW)

    assert out["changed"] is True
    assert out["snap"]["remaining_short_qty"] == 0.0
    assert out["snap"]["long_remaining_qty"] == 0.1
    assert out["snap"]["settlement_state"] == "SHORT_SETTLED"
    assert out["events"][-1]["leg"] == "short"
    assert out["snap"]["option_settlement_history"][-1]["settlement_pnl_status"] == "NOT_COMPUTED"


def test_settlement_finalizer_both_legs_expired_absent_sets_both_zero():
    _clear()
    out = ST._settlement_reconcile_snapshot(_snap(), [], NOW)

    assert out["changed"] is True
    assert out["snap"]["remaining_short_qty"] == 0.0
    assert out["snap"]["long_remaining_qty"] == 0.0
    assert out["snap"]["settlement_state"] == "BOTH_LEGS_SETTLED"
    assert [e["leg"] for e in out["events"]] == ["short", "long"]


def test_settlement_finalizer_unexpired_absent_does_not_zero_snapshot():
    _clear()
    snap = _snap(expiry=_future())

    out = ST._settlement_reconcile_snapshot(snap, [], NOW)

    assert out["changed"] is False
    assert out["snap"]["remaining_short_qty"] == 0.1
    assert out["snap"]["long_remaining_qty"] == 0.1


def test_hedge_after_settlement_forces_target_zero_and_orphan():
    _clear()
    orig = {
        "HEDGE_VENUE": ST.HEDGE_VENUE,
        "bnc_get_position_snapshot": ST.bnc_get_position_snapshot,
        "_spot_price": ST._spot_price,
    }
    try:
        ST.HEDGE_VENUE = "BINANCE"
        ST.bnc_get_position_snapshot = lambda *_a, **_k: {"qty": -0.01, "unrealized_pnl_usd": 0.0}
        ST._spot_price = lambda: 60000.0
        snap = _snap()
        snap["settlement_state"] = "SHORT_SETTLED"

        hedge = ST._evaluate_hedge(snap, quote_fn=lambda _inst: {})

        assert hedge["target"] == 0.0
        assert hedge["orphan"] is True
        assert hedge["action"]["action"] == "HEDGE_UNWIND"
        assert hedge["action"]["reduce_only"] is True
    finally:
        for name, value in orig.items():
            setattr(ST, name, value)


def test_take_profit_short_flat_does_not_quote_expired_leg():
    _clear()
    snap = _snap()
    snap["remaining_short_qty"] = 0.0

    def quote_should_not_be_called(_inst):
        raise AssertionError("short-flat take-profit path should not quote")

    tp = ST._evaluate_take_profit(snap, quote_fn=quote_should_not_be_called, now_ms=NOW)
    assert tp["qualified"] is False
    assert tp["remaining_short_qty"] == 0.0
    assert tp["quote_gap"] is None


def test_startup_recovery_expired_short_no_option_with_perp_returns_orphan():
    _clear()
    orig = {
        "dbt_get_positions": ST.dbt_get_positions,
        "dbt_get_open_orders": ST.dbt_get_open_orders,
        "bnc_get_position_btc": ST.bnc_get_position_btc,
        "HEDGE_VENUE": ST.HEDGE_VENUE,
    }
    try:
        fmz_shim._G(ST._POSITION_KEY, _snap())
        ST.HEDGE_VENUE = "BINANCE"
        ST.dbt_get_positions = lambda _currency, kind=None: [] if kind == "option" else []
        ST.dbt_get_open_orders = lambda *_a, **_k: []
        ST.bnc_get_position_btc = lambda *_a, **_k: -0.01

        verdict = ST.startup_recovery_check("BTC")

        assert verdict["state"] == "ORPHAN_HEDGE_EMERGENCY"
        assert "SETTLED_OPTION_WITH_PERP_HEDGE" in verdict["reasons"]
        saved = fmz_shim._G(ST._POSITION_KEY)
        assert saved["remaining_short_qty"] == 0.0
    finally:
        for name, value in orig.items():
            setattr(ST, name, value)


def test_startup_recovery_unexpired_record_short_no_exchange_option_still_blocked():
    _clear()
    orig = {
        "dbt_get_positions": ST.dbt_get_positions,
        "dbt_get_open_orders": ST.dbt_get_open_orders,
        "bnc_get_position_btc": ST.bnc_get_position_btc,
        "HEDGE_VENUE": ST.HEDGE_VENUE,
    }
    try:
        future_expiry = ST._now_ms() + ST.SETTLEMENT_RECONCILE_GRACE_MS + 1
        fmz_shim._G(ST._POSITION_KEY, _snap(expiry=future_expiry))
        ST.HEDGE_VENUE = "BINANCE"
        ST.dbt_get_positions = lambda _currency, kind=None: [] if kind == "option" else []
        ST.dbt_get_open_orders = lambda *_a, **_k: []
        ST.bnc_get_position_btc = lambda *_a, **_k: 0.0

        verdict = ST.startup_recovery_check("BTC")

        assert verdict["state"] == "RECOVERY_BLOCKED"
        assert "RECORD_SHORT_BUT_NO_EXCHANGE_OPTION" in verdict["reasons"]
    finally:
        for name, value in orig.items():
            setattr(ST, name, value)
