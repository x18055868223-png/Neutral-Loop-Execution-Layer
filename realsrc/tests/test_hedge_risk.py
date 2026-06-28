# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import hedge_risk as H


def test_entry_anchor_builds_probability_and_trigger_policy_can_freeze():
    entry = H.build_entry_risk_anchor(
        direction_bias="SHORT_CALL",
        entry_price=73000,
        entry_dte_hours=48,
        entry_short_delta=0.22,
        entry_short_gamma=0.00005,
        entry_iv=0.70,
        entry_loss_boundary=76000,
    )
    policy = H.build_hedge_trigger_policy(entry["entry_touch_probability"], 0.5)
    assert policy["schema_version"] == "nrd.execution.hedge_trigger.v1"
    assert policy["trigger_mode"] == "BOT_SIDE_RECHECK"
    assert policy["native_trigger"] is False
    assert policy["open_probability"] >= policy["entry_touch_probability"]


def test_probability_deterioration_drives_hedge_ready_without_external_context():
    anchor = {"entry_touch_probability": 0.20, "entry_loss_boundary": 76000}
    policy = H.build_hedge_trigger_policy(0.20, 0.5)
    pkg = H.evaluate_hedge_trigger(
        "SHORT_CALL", anchor, current_price=75500, probability_now=0.55,
        policy=policy)
    assert pkg["tail_risk_state"] == H.STATE_HEDGE_READY
    assert "TOUCH_PROBABILITY_DETERIORATED" in pkg["reason_codes"]


def test_boundary_breach_is_hard_hedge_ready():
    anchor = {"entry_touch_probability": 0.20, "entry_loss_boundary": 76000}
    policy = H.build_hedge_trigger_policy(0.20, 0.5)
    pkg = H.evaluate_hedge_trigger(
        "SHORT_CALL", anchor, current_price=76001, probability_now=0.30,
        policy=policy)
    assert pkg["tail_risk_state"] == H.STATE_HEDGE_READY
    assert "BOUNDARY_BREACHED" in pkg["reason_codes"]


def test_evaluate_position_risk_surfaces_policy_and_reason_codes():
    entry = H.build_entry_risk_anchor(
        direction_bias="SHORT_PUT",
        entry_price=73000,
        entry_dte_hours=48,
        entry_short_delta=-0.20,
        entry_short_gamma=0.00004,
        entry_iv=0.65,
        entry_loss_boundary=70000,
    )
    entry["hedge_trigger_policy"] = H.build_hedge_trigger_policy(0.20, 0.5)
    pkg = H.evaluate_position_risk(
        position_id="p2",
        direction_bias="SHORT_PUT",
        entry_risk_anchor=entry,
        current_price=70400,
        dte_hours=30,
        short_delta=-0.62,
        short_gamma=0.00010,
        iv=0.72,
        loss_boundary=70000,
    )
    assert pkg["schema_version"] == "nrd.integration.position_risk.v0.4"
    assert pkg["hedge_trigger_policy"]["native_trigger"] is False
    assert "touch_probability_now" in pkg["current_risk"]


def test_position_risk_no_longer_emits_deribit_dry_hedge_intent():
    entry = H.build_entry_risk_anchor(
        direction_bias="SHORT_CALL",
        entry_price=73000,
        entry_dte_hours=24,
        entry_short_delta=0.25,
        entry_short_gamma=0.00005,
        entry_iv=0.70,
        entry_loss_boundary=76000,
    )
    entry["hedge_trigger_policy"] = H.build_hedge_trigger_policy(0.20, 0.5)
    pkg = H.evaluate_position_risk(
        position_id="p3",
        direction_bias="SHORT_CALL",
        entry_risk_anchor=entry,
        current_price=75900,
        dte_hours=12,
        short_delta=0.65,
        short_gamma=0.00012,
        iv=1.10,
        loss_boundary=76000,
    )
    assert pkg["tail_risk_state"] == H.STATE_HEDGE_READY
    assert pkg["hedge_intent"] is None
