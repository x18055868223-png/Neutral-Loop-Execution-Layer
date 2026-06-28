# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import fmz_shim
import strategy as ST


_ORIG = {k: getattr(ST, k) for k in (
    "_build_precommit_live", "evaluate_precommit_checks", "exec_entry_campaign_step",
    "exec_maker_only_fill", "exec_plan_prices", "_build_entry_risk_anchor", "dbt_get_positions",
    "dbt_get_open_orders", "dbt_cancel", "bnc_get_position_btc",
)}
_ORIG_VARS = {k: getattr(ST, k) for k in (
    "RUN_PROFILE", "ALLOW_ENTRY_TRADING", "ALLOW_EXIT_TRADING", "ALLOW_HEDGE_TRADING",
    "KILL_NEW_RISK", "EMERGENCY_REDUCE_ONLY", "ENTRY_MAX_ATTEMPTS", "HEDGE_VENUE",
)}


def _restore():
    for k, v in _ORIG.items():
        setattr(ST, k, v)
    for k, v in _ORIG_VARS.items():
        setattr(ST, k, v)
    fmz_shim._STORE.clear()
    ST.ledger_set_state(ST.S_NO_POSITION)


def _locked(prot_done, short_done, attempts=20):
    return {
        "amount": 0.1,
        "side": "CALL",
        "short_instrument": "BTC-29JUN26-60000-C",
        "long_instrument": "BTC-29JUN26-57500-C",
        "short_expiry": 1800000000000,
        "strategy_code": "s",
        "quality_code": "q",
        "plan_hash": "p",
        "manual_context_hash": "h",
        "entry": {
            "prot_done": prot_done,
            "short_done": short_done,
            "attempts": attempts,
            "prot_cost": prot_done * 0.001,
            "short_credit": short_done * 0.007,
        },
    }


def _prime_attempt(allow_live=True):
    ST._build_precommit_live = lambda *_a: {"_budget": {}}
    ST.evaluate_precommit_checks = lambda *_a: {"passed": True, "failed": []}
    ST.exec_entry_campaign_step = lambda *_a, **_k: {
        "quotes_ok": True, "credit_ok": True, "dry": not allow_live,
        "prot_price": 0.001, "short_price": 0.007,
        "net_credit": 0.0006, "prot_fill": 0.0, "short_fill": 0.0,
    }
    ST.exec_plan_prices = lambda side, inst, amount: {
        "side": side, "instrument": inst, "amount": amount, "prices": [0.001],
    }
    ST._build_entry_risk_anchor = lambda *_a: {"anchor": "ok"}
    ST.RUN_PROFILE = "LIVE" if allow_live else "TEST"
    ST.ALLOW_ENTRY_TRADING = bool(allow_live)
    ST.ALLOW_EXIT_TRADING = True
    ST.ALLOW_HEDGE_TRADING = False
    ST.KILL_NEW_RISK = False
    ST.EMERGENCY_REDUCE_ONLY = False
    ST.ENTRY_MAX_ATTEMPTS = 20


def test_abandoned_partial_short_freezes_vertical_not_protection_residual():
    calls = []
    try:
        _prime_attempt(True)
        ST.exec_maker_only_fill = lambda *a, **k: calls.append((a, k)) or {"filled": 0.0}
        locked = _locked(0.1, 0.05)
        fmz_shim._G(ST._LOCKED_KEY, locked)

        out = ST._attempt_commit(locked, 60000.0, {"market_context": {}}, 123456)
        snap = fmz_shim._G(ST._POSITION_KEY)

        assert out["entry_snapshot"] is snap
        assert out.get("partial_position") is True
        assert snap["remaining_short_qty"] == 0.05
        assert snap["long_remaining_qty"] == 0.1
        assert snap.get("residual_reason") is None
        assert ST.ledger_get_state() == ST.S_SHORT_ACTIVE_PROTECTED
        assert fmz_shim._G(ST._LOCKED_KEY) is None
        assert calls == []
    finally:
        _restore()


def test_protection_only_progress_keeps_locked_campaign():
    calls = []
    try:
        _prime_attempt(True)
        ST.exec_maker_only_fill = lambda *a, **k: calls.append((a, k)) or {"filled": 0.0}
        locked = _locked(0.1, 0.0)
        fmz_shim._G(ST._LOCKED_KEY, locked)

        out = ST._attempt_commit(locked, 60000.0, {"market_context": {}}, 123457)
        kept = fmz_shim._G(ST._LOCKED_KEY)

        assert out["entry_snapshot"] is None
        assert kept is not None
        assert kept["entry"]["prot_done"] == 0.1
        assert kept["entry"]["short_done"] == 0.0
        assert ST.ledger_get_state() == ST.S_NO_POSITION
        assert calls == []
    finally:
        _restore()


def test_no_fill_attempt_cap_keeps_locked_plan_in_entry_campaign():
    try:
        _prime_attempt(True)
        locked = _locked(0.0, 0.0, attempts=20)
        fmz_shim._G(ST._LOCKED_KEY, locked)

        out = ST._attempt_commit(locked, 60000.0, {"market_context": {}}, 123456)
        kept = fmz_shim._G(ST._LOCKED_KEY)

        assert out["entry_snapshot"] is None
        assert out["entry_state"] == ST.ENTRY_WORKING
        assert out["reason"].startswith("ENTRY_WORKING")
        assert kept is not None
        assert kept["entry"]["attempts"] == 21
        assert fmz_shim._G(ST._POSITION_KEY) is None
        assert ST.ledger_get_state() == ST.S_NO_POSITION
    finally:
        _restore()


def test_attempt_commit_persists_protection_order_state_on_locked_plan():
    try:
        _prime_attempt(True)
        ST.exec_entry_campaign_step = lambda *_a, **_k: {
            "quotes_ok": True, "credit_ok": True, "dry": False,
            "prot_price": 0.0002, "short_price": 0.0068,
            "net_credit": 0.0006, "prot_fill": 0.0, "short_fill": 0.0,
            "prot_order": {
                "order_id": "p1", "instrument": "BTC-29JUN26-57500-C",
                "price": 0.0002, "amount": 0.1, "filled_seen": 0.0,
                "placed_ms": 123456, "wait_start_ms": 123456,
                "label": "entry_prot",
            },
            "reason": "ENTRY_STEP",
        }
        locked = _locked(0.0, 0.0, attempts=0)
        fmz_shim._G(ST._LOCKED_KEY, locked)

        out = ST._attempt_commit(locked, 60000.0, {"market_context": {}}, 123456)
        kept = fmz_shim._G(ST._LOCKED_KEY)

        assert out["entry_state"] == ST.ENTRY_WORKING
        assert kept["entry"]["prot_order"]["order_id"] == "p1"
        assert kept["entry"]["prot_order"]["wait_start_ms"] == 123456
        assert fmz_shim._G(ST._POSITION_KEY) is None
    finally:
        _restore()


def test_abandoned_short_greater_than_protection_blocks_recovery():
    try:
        _prime_attempt(False)
        locked = _locked(0.1, 0.11)
        fmz_shim._G(ST._LOCKED_KEY, locked)

        out = ST._attempt_commit(locked, 60000.0, {"market_context": {}}, 123458)
        verdict = fmz_shim._G(ST._RECOVERY_KEY)

        assert out["reason"].startswith("RECOVERY_BLOCKED")
        assert verdict["state"] == "RECOVERY_BLOCKED"
        assert any("SHORT_GT_PROTECTION" in r for r in verdict["reasons"])
        assert fmz_shim._G(ST._LOCKED_KEY) is None
    finally:
        _restore()


def test_precommit_failure_after_partial_short_freezes_managed_snapshot():
    try:
        _prime_attempt(True)
        ST.evaluate_precommit_checks = lambda *_a: {"passed": False, "failed": ["VRP_CONTEXT_MISSING"]}
        locked = _locked(0.1, 0.05, attempts=3)
        fmz_shim._G(ST._LOCKED_KEY, locked)

        out = ST._attempt_commit(locked, 60000.0, {"market_context": {}}, 123459)
        snap = fmz_shim._G(ST._POSITION_KEY)

        assert out["entry_snapshot"] is snap
        assert out.get("partial_position") is True
        assert out["reason"] == "ENTRY_PARTIAL_VERTICAL_MANAGED_PRECOMMIT_FAILED"
        assert snap["remaining_short_qty"] == 0.05
        assert snap["long_remaining_qty"] == 0.1
        assert snap["entry_completion_state"] == "PARTIAL_VERTICAL"
        assert snap["entry_abandon_reason"] == "PRECOMMIT_FAILED_AFTER_PARTIAL_SHORT"
        assert snap["entry_target_amount"] == 0.1
        assert snap["entry_attempts"] == 3
        assert ST.ledger_get_state() == ST.S_SHORT_ACTIVE_PROTECTED
        assert fmz_shim._G(ST._LOCKED_KEY) is None
    finally:
        _restore()


def test_precommit_failure_after_protection_only_freezes_residual_snapshot():
    try:
        _prime_attempt(True)
        ST.evaluate_precommit_checks = lambda *_a: {"passed": False, "failed": ["ledger_reconciled"]}
        locked = _locked(0.1, 0.0, attempts=2)
        fmz_shim._G(ST._LOCKED_KEY, locked)

        out = ST._attempt_commit(locked, 60000.0, {"market_context": {}}, 123460)
        snap = fmz_shim._G(ST._POSITION_KEY)

        assert out["entry_snapshot"] is snap
        assert out.get("residual_position") is True
        assert out["reason"].startswith("ENTRY_PROTECTION_ONLY_RESIDUAL_MANAGED:")
        assert snap["remaining_short_qty"] == 0.0
        assert snap["long_remaining_qty"] == 0.1
        assert snap["entry_completion_state"] == "PROTECTION_ONLY_RESIDUAL"
        assert "PRECOMMIT_FAILED_AFTER_ENTRY_PROGRESS" in snap["entry_abandon_reason"]
        assert ST.ledger_get_state() == ST.S_SHORT_FLAT_LONG_RESIDUAL
        assert fmz_shim._G(ST._LOCKED_KEY) is None
    finally:
        _restore()


def test_live_protection_fill_without_short_fill_keeps_locked_campaign():
    try:
        _prime_attempt(True)
        ST.exec_entry_campaign_step = lambda *_a, **_k: {
            "quotes_ok": True, "credit_ok": True, "dry": False,
            "prot_price": 0.001, "short_price": 0.0075,
            "net_credit": 0.0006, "prot_fill": 0.1, "short_fill": 0.0,
            "reason": "ENTRY_STEP",
        }
        locked = _locked(0.0, 0.0, attempts=0)
        fmz_shim._G(ST._LOCKED_KEY, locked)

        out = ST._attempt_commit(locked, 60000.0, {"market_context": {}}, 123461)
        kept = fmz_shim._G(ST._LOCKED_KEY)

        assert out["entry_snapshot"] is None
        assert out["reason"].startswith("ENTRY_WORKING")
        assert kept is not None
        assert kept["entry"]["prot_done"] == 0.1
        assert kept["entry"]["short_done"] == 0.0
        assert ST.ledger_get_state() == ST.S_NO_POSITION
        assert fmz_shim._G(ST._POSITION_KEY) is None
    finally:
        _restore()


def test_full_entry_snapshot_uses_actual_fill_detail_accounting():
    try:
        _prime_attempt(True)
        ST.exec_entry_campaign_step = lambda *_a, **_k: {
            "quotes_ok": True, "credit_ok": True, "dry": False,
            "prot_price": 0.0010, "short_price": 0.0070,
            "prot_avg_price": 0.0011, "short_avg_price": 0.0069,
            "net_credit": 0.0006,
            "actual_net_credit_before_fees": (0.0069 - 0.0011) * 0.1,
            "actual_net_credit_after_fees": 0.00050,
            "entry_fees": 0.00008,
            "fills": [
                {"leg": "protection", "filled": 0.1, "avg_price": 0.0011,
                 "fee_estimate": 0.00002, "mark_slippage": 0.00001},
                {"leg": "short", "filled": 0.1, "avg_price": 0.0069,
                 "fee_estimate": 0.00006, "mark_slippage": 0.00001},
            ],
            "prot_fill": 0.1, "short_fill": 0.1,
            "reason": "ENTRY_STEP",
        }
        locked = _locked(0.0, 0.0, attempts=0)
        fmz_shim._G(ST._LOCKED_KEY, locked)

        out = ST._attempt_commit(locked, 60000.0, {"market_context": {}}, 123462)
        snap = fmz_shim._G(ST._POSITION_KEY)

        assert out["committed"] is True
        assert abs(snap["long_fill_price"] - 0.0011) < 1e-12
        assert abs(snap["short_fill_price"] - 0.0069) < 1e-12
        assert snap["entry_fees"] == 0.00008
        report = snap["entry_execution_report"]
        assert report["actual_net_credit_after_fees"] == 0.00050
        assert len(report["fills"]) == 2
        assert report["fills"][0]["leg"] == "protection"
        assert report["total_fee_estimate"] == 0.00008
    finally:
        _restore()


def test_startup_recovery_cancels_entry_orders_before_verdict():
    cancelled = []
    seq = [
        [{"order_id": "o1", "label": "entry_short", "instrument_name": "BTC-X"}],
        [],
    ]
    try:
        ST.dbt_get_positions = lambda *_a: []
        ST.dbt_get_open_orders = lambda *_a: seq.pop(0)
        ST.dbt_cancel = lambda oid: cancelled.append(oid) or {"order_id": oid}

        verdict = ST.startup_recovery_check("BTC")

        assert cancelled == ["o1"]
        assert verdict["state"] == "OK"
        assert verdict["allow_new_open"] is True
    finally:
        _restore()


def test_startup_recovery_adopts_locked_protection_only_progress():
    positions = [
        [{"instrument_name": "BTC-29JUN26-57500-C", "size": 0.1}],
        [],
        [{"instrument_name": "BTC-29JUN26-57500-C", "size": 0.1}],
        [],
    ]
    try:
        ST.HEDGE_VENUE = "DERIBIT"
        ST.dbt_get_positions = lambda *_a: positions.pop(0)
        ST.dbt_get_open_orders = lambda *_a: []
        ST.dbt_cancel = lambda _oid: True
        locked = _locked(0.1, 0.0, attempts=1)
        fmz_shim._G(ST._LOCKED_KEY, locked)

        verdict = ST.startup_recovery_check("BTC")
        snap = fmz_shim._G(ST._POSITION_KEY)

        assert verdict["state"] == "OK"
        assert verdict["adopted"] is True
        assert snap["remaining_short_qty"] == 0.0
        assert snap["long_remaining_qty"] == 0.1
        assert snap["entry_completion_state"] == "PROTECTION_ONLY_RESIDUAL"
        assert ST.ledger_get_state() == ST.S_SHORT_FLAT_LONG_RESIDUAL
        assert fmz_shim._G(ST._LOCKED_KEY) is None
    finally:
        _restore()


def test_startup_recovery_rereads_positions_after_entry_order_cancel():
    order = {"order_id": "o1", "label": "entry_short", "instrument_name": "BTC-X"}
    open_orders = [[order], []]
    positions = [
        [],
        [],
        [{"instrument_name": "BTC-29JUN26-60000-C", "size": -0.05}],
        [],
    ]
    try:
        ST.dbt_get_open_orders = lambda *_a: open_orders.pop(0)
        ST.dbt_cancel = lambda _oid: True
        ST.dbt_get_positions = lambda *_a: positions.pop(0)

        verdict = ST.startup_recovery_check("BTC")

        assert verdict["state"] == "RECOVERY_BLOCKED"
        assert any("EXCHANGE_OPTION_BUT_NO_RECORDED_POSITION" in r for r in verdict["reasons"])
    finally:
        _restore()


def test_startup_recovery_blocks_when_entry_order_remains_after_cancel():
    cancelled = []
    order = {"order_id": "o1", "label": "entry_prot", "instrument_name": "BTC-X"}
    seq = [[order], [order]]
    try:
        ST.dbt_get_positions = lambda *_a: []
        ST.dbt_get_open_orders = lambda *_a: seq.pop(0)
        ST.dbt_cancel = lambda oid: cancelled.append(oid) or {"order_id": oid}

        verdict = ST.startup_recovery_check("BTC")

        assert cancelled == ["o1"]
        assert verdict["state"] == "RECOVERY_BLOCKED"
        assert verdict["allow_new_open"] is False
        assert any("ENTRY_ACTIVE_ORDERS_REMAIN" in r for r in verdict["reasons"])
    finally:
        _restore()
