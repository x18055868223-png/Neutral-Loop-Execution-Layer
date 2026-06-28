# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import fmz_shim
import strategy as ST


NOW = 1_000_000_000
H = 3600000


_MISSING = object()
_ORIG = {k: getattr(ST, k, _MISSING) for k in (
    "HEDGE_POLICY_V313_ENABLED", "HEDGE_STAGING_ENABLED", "HEDGE_HYSTERESIS_ENABLED",
    "HEDGE_COOLDOWN_ENABLED", "HEDGE_SLIPPAGE_GUARD_ENABLED",
    "HEDGE_SOFT_INITIAL_RATIO", "HEDGE_SOFT_ADD_DRIFT_STEP", "HEDGE_HARD_DRIFT",
    "HEDGE_HARD_CROSS_BPS", "HEDGE_SOFT_CROSS_BPS",
    "HEDGE_SOFT_PERSIST_SECONDS", "HEDGE_REDUCE_PERSIST_SECONDS",
    "HEDGE_REDUCE_PROB_BUFFER", "HEDGE_ADD_COOLDOWN_SECONDS",
    "HEDGE_REDUCE_COOLDOWN_SECONDS", "HEDGE_PENDING_STALE_SECONDS",
    "HEDGE_GAMMA_AWARE_ENABLED", "HEDGE_GAMMA_FRAC_FLOOR", "HEDGE_GAMMA_NORM_REF",
    "HEDGE_REBALANCE_BAND_FRAC", "HEDGE_MIN_HOLD_SECONDS", "HEDGE_FINAL3H_MODE",
    "HEDGE_CRASH_ENABLED", "HEDGE_CRASH_SPEED_WINDOW_SECONDS", "HEDGE_CRASH_MOVE_BPS",
    "HEDGE_BINANCE_MIN_TRADE", "bnc_submit_hedge_order",
    "bnc_get_hedge_order", "bnc_cancel_hedge_order",
)}


def _restore():
    fmz_shim._STORE.clear()
    for k, v in _ORIG.items():
        if v is _MISSING:
            try:
                delattr(ST, k)
            except AttributeError:
                pass
        else:
            setattr(ST, k, v)


def _setup():
    _restore()
    ST.HEDGE_POLICY_V313_ENABLED = True
    ST.HEDGE_STAGING_ENABLED = True
    ST.HEDGE_HYSTERESIS_ENABLED = True
    ST.HEDGE_COOLDOWN_ENABLED = True
    ST.HEDGE_SLIPPAGE_GUARD_ENABLED = True
    ST.HEDGE_SOFT_INITIAL_RATIO = 0.40
    ST.HEDGE_SOFT_ADD_DRIFT_STEP = 0.05
    ST.HEDGE_HARD_DRIFT = 0.35
    ST.HEDGE_HARD_CROSS_BPS = 30
    ST.HEDGE_SOFT_CROSS_BPS = 3
    ST.HEDGE_SOFT_PERSIST_SECONDS = 20
    ST.HEDGE_REDUCE_PERSIST_SECONDS = 20
    ST.HEDGE_REDUCE_PROB_BUFFER = 0.05
    ST.HEDGE_ADD_COOLDOWN_SECONDS = 30
    ST.HEDGE_REDUCE_COOLDOWN_SECONDS = 60
    ST.HEDGE_PENDING_STALE_SECONDS = 10
    ST.HEDGE_BINANCE_MIN_TRADE = 0.001
    ST.HEDGE_GAMMA_AWARE_ENABLED = True
    ST.HEDGE_GAMMA_FRAC_FLOOR = 0.30
    ST.HEDGE_GAMMA_NORM_REF = 1_000_000.0
    ST.HEDGE_REBALANCE_BAND_FRAC = 0.20
    ST.HEDGE_MIN_HOLD_SECONDS = 720
    ST.HEDGE_FINAL3H_MODE = "SUPPRESS_SOFT_ADD"
    ST.HEDGE_CRASH_ENABLED = True
    ST.HEDGE_CRASH_SPEED_WINDOW_SECONDS = 600
    ST.HEDGE_CRASH_MOVE_BPS = 110


def _snap(qty=0.10):
    return {
        "position_id": "pos-v314",
        "side": "CALL",
        "remaining_short_qty": qty,
        "short_instrument": "S",
        "long_instrument": "P",
        "short_expiry_ts": NOW + 24 * H,
    }


def _hedge(current=0.0, target=0.02, side="buy", venue="BINANCE",
           data_gap=None, gamma_fraction=0.30):
    action = {"action": "HEDGE_OPEN", "reduce_only": False,
              "delta_contracts": abs(target - current)}
    if data_gap:
        action = {"action": "HEDGE_HOLD", "reduce_only": False,
                  "delta_contracts": 0.0, "blocked": data_gap}
    return {
        "venue": venue,
        "instrument": "BTCUSDC",
        "venue_cfg": {"venue": venue, "instrument": "BTCUSDC", "linear": True, "exchange_index": 1},
        "perp_qty": None if data_gap else current,
        "target": None if data_gap else target,
        "side": side,
        "orphan": False,
        "action": action,
        "data_gap": data_gap,
        "gamma_fraction": gamma_fraction,
        "gamma_data_state": "OK",
    }


def _risk(p_now=0.55, p_entry=0.25, reason="TOUCH_PROBABILITY_DETERIORATED"):
    return {
        "tail_risk_state": ST.STATE_HEDGE_READY if reason != "TOUCH_PROBABILITY_NORMAL" else "NORMAL",
        "reason_codes": [reason],
        "current_risk": {
            "touch_probability_now": p_now,
            "touch_probability_drift": p_now - p_entry,
            "entry_touch_probability": p_entry,
            "watch_probability": 0.40,
            "open_probability": 0.50,
            "emergency_probability": 0.70,
            "min_probability_drift_to_open": 0.20,
        },
        "hedge_trigger_policy": {
            "watch_probability": 0.40,
            "open_probability": 0.50,
            "emergency_probability": 0.70,
            "min_probability_drift_to_open": 0.20,
        },
    }


def _plan(current=0.0, target=0.02, risk=None, snap=None, gamma_fraction=0.30):
    return ST._hedge_policy_plan(
        snap or _snap(), _hedge(current=current, target=target, gamma_fraction=gamma_fraction),
        risk or _risk(), NOW)


def test_soft_low_gamma_uses_40pct_not_50pct():
    _setup()
    h = _plan(current=0.0, target=0.02)
    assert h["policy_detail"]["trigger_state"] == "SOFT"
    assert h["policy_detail"]["soft_ratio"] == 0.40
    assert h["policy_detail"]["eff_target_qty"] == 0.008
    assert h["action"]["action"] == "HEDGE_OPEN"
    assert abs(h["action"]["delta_contracts"] - 0.008) < 1e-12
    assert h["policy_detail"]["reason"] == "SOFT_TRIGGER_INITIAL"


def test_soft_initial_ratio_is_max_base_and_gamma():
    _setup()
    h = _plan(current=0.0, target=0.02, gamma_fraction=0.65)
    assert h["policy_detail"]["trigger_state"] == "SOFT"
    assert h["policy_detail"]["soft_ratio"] == 0.65
    assert abs(h["policy_detail"]["eff_target_qty"] - 0.013) < 1e-12
    assert h["action"]["action"] == "HEDGE_OPEN"


def test_soft_reversion_clears_persistence_and_does_not_add():
    _setup()
    _plan(current=0.0, target=0.02)
    h = _plan(current=0.0, target=0.02, risk=_risk(p_now=0.30, reason="TOUCH_PROBABILITY_NORMAL"))
    st = ST._hedge_policy_state(_snap())
    assert st["soft_since_ts"] == 0
    assert h["action"]["action"] == "HEDGE_HOLD"


def test_soft_persistence_escalates_from_half_to_full():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st["soft_since_ts"] = NOW - 21_000
    ST._hedge_policy_save_state(st)
    h = _plan(current=0.01, target=0.02)
    assert h["policy_detail"]["soft_ratio"] == 1.0
    assert h["policy_detail"]["eff_target_qty"] == 0.02
    assert h["action"]["action"] == "HEDGE_INCREASE"
    assert h["policy_detail"]["reason"] == "SOFT_TRIGGER_CONFIRMED"


def test_hard_targets_full_and_bypasses_add_cooldown():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st["add_cooldown_until"] = NOW + 60_000
    ST._hedge_policy_save_state(st)
    h = _plan(current=0.0, target=0.02, risk=_risk(p_now=0.80, reason="EMERGENCY_TOUCH_PROBABILITY"))
    assert h["policy_detail"]["trigger_state"] == "HARD"
    assert h["policy_detail"]["soft_ratio"] is None
    assert h["policy_detail"]["eff_target_qty"] == 0.02
    assert h["action"]["action"] == "HEDGE_OPEN"
    assert h["policy_detail"]["cross_bps"] == ST.HEDGE_HARD_CROSS_BPS


def test_soft_add_blocked_by_add_cooldown_after_reduce():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st["add_cooldown_until"] = NOW + 60_000
    ST._hedge_policy_save_state(st)
    h = _plan(current=0.0, target=0.02)
    assert h["action"]["action"] == "HEDGE_HOLD"
    assert h["policy_detail"]["reason"] == "ADD_COOLDOWN_ACTIVE"


def test_pending_order_blocks_new_order_first():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st.update({"pending_order_id": "oid-1", "pending_order_created_ts": NOW,
               "pending_order_side": "buy", "pending_order_qty": 0.01})
    ST._hedge_policy_save_state(st)
    ST.bnc_get_hedge_order = lambda *_a, **_k: {"Id": "oid-1", "Status": 0, "DealAmount": 0.0}
    h = _plan(current=0.0, target=0.02)
    assert h["action"]["action"] == "HEDGE_HOLD"
    assert h["policy_detail"]["reason"] == "PENDING_ACTIVE"


def test_late_fill_current_absorbs_delta_and_prevents_overhedge():
    _setup()
    h = _plan(current=0.01, target=0.02)
    assert h["policy_detail"]["eff_target_qty"] == 0.008
    assert h["action"]["action"] == "HEDGE_HOLD"
    assert h["policy_detail"]["reason"] == "TARGET_BAND_DEADBAND"


def test_probability_reverts_but_reduce_waits_for_hysteresis():
    _setup()
    h = _plan(current=0.01, target=0.02,
              risk=_risk(p_now=0.36, reason="TOUCH_PROBABILITY_NORMAL"))
    assert h["action"]["action"] == "HEDGE_HOLD"
    assert h["policy_detail"]["reason"] == "REDUCE_HYSTERESIS_WAIT"


def test_reduce_after_persistence_uses_reduce_only():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st["reduce_since_ts"] = NOW - 21_000
    st["last_action"] = "REDUCE"
    ST._hedge_policy_save_state(st)
    h = _plan(current=0.01, target=0.02,
              risk=_risk(p_now=0.30, reason="TOUCH_PROBABILITY_NORMAL"))
    assert h["action"]["action"] == "HEDGE_UNWIND"
    assert h["action"]["reduce_only"] is True
    assert abs(h["action"]["delta_contracts"] - 0.01) < 1e-12


def test_min_hold_blocks_ordinary_reduce():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st["reduce_since_ts"] = NOW - 21_000
    st["last_action"] = "ADD"
    st["last_fill_ts"] = NOW - 60_000
    ST._hedge_policy_save_state(st)
    h = _plan(current=0.01, target=0.02,
              risk=_risk(p_now=0.30, reason="TOUCH_PROBABILITY_NORMAL"))
    assert h["action"]["action"] == "HEDGE_HOLD"
    assert h["policy_detail"]["reason"] == "REDUCE_MIN_HOLD_ACTIVE"
    assert h["policy_detail"]["min_hold_until"] == NOW - 60_000 + 720_000


def test_short_flat_unwinds_immediately_without_cooldown():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st["reduce_cooldown_until"] = NOW + 60_000
    st["last_action"] = "ADD"
    st["last_fill_ts"] = NOW - 60_000
    ST._hedge_policy_save_state(st)
    h = ST._hedge_policy_plan(_snap(qty=0.0), _hedge(current=0.01, target=0.0), _risk(), NOW)
    assert h["action"]["action"] == "HEDGE_UNWIND"
    assert h["action"]["reduce_only"] is True
    assert h["policy_detail"]["reason"] == "ORPHAN_HEDGE_UNWIND"


def test_position_read_failure_fails_closed_without_assuming_zero():
    _setup()
    h = ST._hedge_policy_plan(
        _snap(), _hedge(current=0.0, target=0.02, data_gap="HEDGE_POSITION_DATA_GAP"), _risk(), NOW)
    assert h["action"]["action"] == "HEDGE_HOLD"
    assert h["policy_detail"]["reason"] == "POSITION_READ_FAILED"
    assert h["policy_detail"]["current_hedge_qty"] is None


def test_reconcile_target_is_eff_target_not_full_target():
    _setup()
    h = _plan(current=0.008, target=0.02)
    assert h["policy_detail"]["full_target_qty"] == 0.02
    assert h["policy_detail"]["eff_target_qty"] == 0.008
    assert h["action"]["action"] == "HEDGE_HOLD"


def test_pending_stale_recovers_when_order_missing():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st.update({"pending_order_id": "oid-stale", "pending_order_created_ts": NOW - 11_000,
               "pending_order_side": "buy", "pending_order_qty": 0.01})
    ST._hedge_policy_save_state(st)
    cancels = []
    ST.bnc_get_hedge_order = lambda *_a, **_k: None
    ST.bnc_cancel_hedge_order = lambda *_a, **_k: cancels.append(_a) or True
    h = _plan(current=0.0, target=0.02)
    st2 = ST._hedge_policy_state(_snap())
    assert h["policy_detail"]["reason"] == "PENDING_STALE_RECOVERED"
    assert st2["pending_order_id"] is None
    assert cancels


def test_hard_gap_continues_after_partial_current_without_slippage_block():
    _setup()
    h = _plan(current=0.01, target=0.02, risk=_risk(p_now=0.80, reason="EMERGENCY_TOUCH_PROBABILITY"))
    assert h["policy_detail"]["trigger_state"] == "HARD"
    assert h["action"]["action"] == "HEDGE_INCREASE"
    assert abs(h["action"]["delta_contracts"] - 0.01) < 1e-12


def test_episode_cost_alert_does_not_gate_hard():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st["episode_cost_bps"] = 999.0
    ST._hedge_policy_save_state(st)
    h = _plan(current=0.0, target=0.02, risk=_risk(p_now=0.80, reason="EMERGENCY_TOUCH_PROBABILITY"))
    assert h["action"]["action"] == "HEDGE_OPEN"
    assert "EPISODE_COST_ALERT" in h["policy_detail"]["warnings"]


def test_add_fill_arms_reduce_cooldown():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st.update({"pending_order_id": "oid-fill", "pending_order_created_ts": NOW - 1000,
               "pending_order_side": "buy", "pending_order_qty": 0.01,
               "pending_is_add": True})
    ST._hedge_policy_save_state(st)
    ST.bnc_get_hedge_order = lambda *_a, **_k: {
        "Id": "oid-fill", "Status": 2, "DealAmount": 0.01, "AvgPrice": 60000.0}
    h = _plan(current=0.01, target=0.02)
    st2 = ST._hedge_policy_state(_snap())
    assert h["policy_detail"]["reason"] == "PENDING_FILLED"
    assert st2["reduce_cooldown_until"] > NOW


def test_pending_partial_active_keeps_pending_and_blocks_new_order():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st.update({"pending_order_id": "oid-partial", "pending_order_created_ts": NOW - 1000,
               "pending_order_side": "buy", "pending_order_qty": 0.02,
               "pending_is_add": True})
    ST._hedge_policy_save_state(st)
    ST.bnc_get_hedge_order = lambda *_a, **_k: {
        "Id": "oid-partial", "Status": 0, "DealAmount": 0.01, "AvgPrice": 60000.0}
    h = _plan(current=0.01, target=0.02)
    st2 = ST._hedge_policy_state(_snap())
    assert h["action"]["action"] == "HEDGE_HOLD"
    assert h["policy_detail"]["reason"] == "PENDING_PARTIAL_ACTIVE"
    assert st2["pending_order_id"] == "oid-partial"


def test_pending_terminal_fill_returns_ledger_event_and_clears_pending():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st.update({"pending_order_id": "oid-fill-ledger", "pending_order_created_ts": NOW - 1000,
               "pending_order_side": "sell", "pending_order_qty": 0.01,
               "pending_is_add": False, "pending_reduce_only": True})
    ST._hedge_policy_save_state(st)
    ST.bnc_get_hedge_order = lambda *_a, **_k: {
        "Id": "oid-fill-ledger", "Status": 2, "DealAmount": 0.01, "AvgPrice": 59950.0}
    h = _plan(current=0.0, target=0.0, risk=_risk(p_now=0.30, reason="TOUCH_PROBABILITY_NORMAL"))
    st2 = ST._hedge_policy_state(_snap())
    ev = h.get("policy_resolved_fill") or {}
    assert h["policy_detail"]["reason"] == "PENDING_FILLED"
    assert st2["pending_order_id"] is None
    assert ev["order_id"] == "oid-fill-ledger"
    assert ev["filled"] == 0.01
    assert ev["reduce_only"] is True


def test_same_direction_staged_build_not_blocked_by_reduce_cooldown():
    _setup()
    st = ST._hedge_policy_state(_snap())
    st["reduce_cooldown_until"] = NOW + 60_000
    st["soft_since_ts"] = NOW - 21_000
    ST._hedge_policy_save_state(st)
    h = _plan(current=0.01, target=0.02)
    assert h["action"]["action"] == "HEDGE_INCREASE"
    assert h["policy_detail"]["reason"] == "SOFT_TRIGGER_CONFIRMED"


def test_reverse_hedge_unwinds_to_zero_before_reopen():
    _setup()
    h = _plan(current=0.01, target=-0.02,
              risk=_risk(p_now=0.80, reason="EMERGENCY_TOUCH_PROBABILITY"))
    assert h["action"]["action"] == "HEDGE_UNWIND"
    assert h["action"]["reduce_only"] is True
    assert h["policy_detail"]["eff_target_qty"] == 0.0
    assert h["policy_detail"]["reason"] == "REVERSE_HEDGE_UNWIND"


def test_sub_min_lot_residual_is_deadbanded():
    _setup()
    h = _plan(current=0.0196, target=0.02,
              risk=_risk(p_now=0.80, reason="EMERGENCY_TOUCH_PROBABILITY"))
    assert h["action"]["action"] == "HEDGE_HOLD"
    assert h["policy_detail"]["reason"] == "TARGET_BAND_DEADBAND"


def test_target_band_blocks_small_rehedge():
    _setup()
    h = _plan(current=0.017, target=0.02,
              risk=_risk(p_now=0.80, reason="EMERGENCY_TOUCH_PROBABILITY"))
    assert h["action"]["action"] == "HEDGE_HOLD"
    assert h["policy_detail"]["reason"] == "TARGET_BAND_DEADBAND"
    assert h["policy_detail"]["rebalance_deadband"] == 0.004


def test_final3_blocks_soft_add_only():
    _setup()
    snap = _snap()
    snap["short_expiry_ts"] = NOW + H
    h = _plan(current=0.0, target=0.02, snap=snap)
    assert h["action"]["action"] == "HEDGE_HOLD"
    assert h["policy_detail"]["reason"] == "FINAL3H_SOFT_ADD_SUPPRESSED"

    st = ST._hedge_policy_state(snap)
    st["reduce_since_ts"] = NOW - 21_000
    st["last_action"] = "REDUCE"
    ST._hedge_policy_save_state(st)
    reduce_h = _plan(current=0.01, target=0.02, snap=snap,
                     risk=_risk(p_now=0.30, reason="TOUCH_PROBABILITY_NORMAL"))
    assert reduce_h["action"]["action"] == "HEDGE_UNWIND"
    assert reduce_h["action"]["reduce_only"] is True


def test_crash_overrides_final3_and_add_cooldown():
    _setup()
    snap = _snap()
    snap["short_expiry_ts"] = NOW + H
    st = ST._hedge_policy_state(snap)
    st["add_cooldown_until"] = NOW + 60_000
    st["crash_ref_price"] = 60000.0
    st["crash_ref_ts"] = NOW - 300_000
    ST._hedge_policy_save_state(st)
    risk = _risk(p_now=0.30, reason="TOUCH_PROBABILITY_NORMAL")
    risk["current_risk"]["current_price"] = 60700.0
    h = _plan(current=0.0, target=0.02, risk=risk, snap=snap)
    assert h["policy_detail"]["trigger_state"] == "CRASH"
    assert h["policy_detail"]["eff_target_qty"] == 0.02
    assert h["action"]["action"] == "HEDGE_OPEN"
    assert h["policy_detail"]["reason"] == "CRASH_TRIGGER_SPEED"


def test_submit_sets_pending_and_next_plan_is_idempotent():
    _setup()
    submits = []
    ST.bnc_submit_hedge_order = lambda **kw: submits.append(kw) or {
        "order_id": "oid-new", "price": 60000.0, "amount": kw["amount"],
        "side": kw["side"], "reduce_only": kw["reduce_only"],
        "reason": "BINANCE_HEDGE_SUBMITTED"}
    ST.bnc_get_hedge_order = lambda *_a, **_k: {"Id": "oid-new", "Status": 0, "DealAmount": 0.0}
    first = _plan(current=0.0, target=0.02)
    step = ST._hedge_policy_submit(first, NOW, allow_live=True)
    second = _plan(current=0.0, target=0.02)
    assert step["order_id"] == "oid-new"
    assert len(submits) == 1
    assert second["action"]["action"] == "HEDGE_HOLD"
    assert second["policy_detail"]["reason"] == "PENDING_ACTIVE"
