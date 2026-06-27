# -*- coding: utf-8 -*-
import importlib.util
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import fmz_shim


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _latest_bundle_path():
    artifacts = os.path.join(ROOT, "artifacts")
    latest_dir = next(os.path.join(artifacts, d) for d in os.listdir(artifacts)
                      if d == "最新交付")
    files = [f for f in os.listdir(latest_dir) if f.endswith(".py")]
    assert len(files) == 1
    return os.path.join(latest_dir, files[0])


def _load_bundle():
    spec = importlib.util.spec_from_file_location("spm_latest_bundle", _latest_bundle_path())
    mod = importlib.util.module_from_spec(spec)
    for name in fmz_shim.__all__:
        setattr(mod, name, getattr(fmz_shim, name))
    spec.loader.exec_module(mod)
    return mod


def _gex_payload(stale=False, rank_pct=15.206185567010309):
    return {
        "asset": "BTC",
        "fetched_at": "2026-06-27T02:25:46.894379+00:00",
        "stale": stale,
        "availability": "ready",
        "volatility": {"iv_rv_ratio": 0.8},
        "missing_fields": [],
        "rank": {
            "window": {"mode": "rolling_30d_or_available", "lookback_days": 30},
            "metrics": {
                "volatility.iv_rv_ratio": {
                    "value": 0.8,
                    "percentile": 0.15206185567010308,
                    "rank_pct": rank_pct,
                    "sample_count": 388,
                    "quality": "warming_up",
                }
            },
        },
    }


def _install_urlopen(payload):
    import json
    import urllib.request

    old = urllib.request.urlopen

    class _Resp(object):
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps(payload).encode("utf-8")

    def fake_urlopen(req, timeout=None):
        assert req.full_url.endswith("/v1/info")
        assert req.headers.get("Authorization", "").startswith("Bearer ")
        return _Resp()

    urllib.request.urlopen = fake_urlopen
    return old


def test_gex_api_becomes_validity_only_market_context():
    b = _load_bundle()
    old = _install_urlopen(_gex_payload())
    try:
        verdict = b.fetch_gex_vrp_context("SHORT_CALL")
    finally:
        import urllib.request
        urllib.request.urlopen = old
    assert verdict["valid"]
    assert verdict["status"] == "VRP_CONTEXT_VALID"
    mc = verdict["market_context"]
    assert mc["source"] == "GEX_MONITOR_IV_RV_RANK"
    assert mc["side"] == "SHORT_CALL"
    assert mc["iv_rv_ratio"] == 0.8
    assert round(mc["iv_rv_rank_pct"], 6) == round(15.206185567010309, 6)
    assert not hasattr(b, "apply_vrp_gate")
    assert not hasattr(b, "gate_plan")


def test_stale_gex_api_blocks_locking_without_price_gate():
    b = _load_bundle()
    old = _install_urlopen(_gex_payload(stale=True))
    try:
        verdict = b.fetch_gex_vrp_context("SHORT_CALL")
    finally:
        import urllib.request
        urllib.request.urlopen = old
    assert not verdict["valid"]
    assert verdict["status"] == "VRP_CONTEXT_STALE"
    assert verdict["market_context"] is None


def test_gex_context_is_material_lineage():
    b = _load_bundle()
    old = _install_urlopen(_gex_payload())
    try:
        v1 = b.fetch_gex_vrp_context("SHORT_CALL")
    finally:
        import urllib.request
        urllib.request.urlopen = old
    old = _install_urlopen(_gex_payload(rank_pct=16.0))
    try:
        v2 = b.fetch_gex_vrp_context("SHORT_CALL")
    finally:
        import urllib.request
        urllib.request.urlopen = old

    ctx1 = b.build_manual_context(1000, True, "SHORT_CALL", (24, 72), (0.15, 0.45),
                                  (2000, 2500), 0.1, "", "", 30, {},
                                  market_context=v1["market_context"],
                                  vrp_context_status=v1["status"])
    ctx2 = b.build_manual_context(1000, True, "SHORT_CALL", (24, 72), (0.15, 0.45),
                                  (2000, 2500), 0.1, "", "", 30, {},
                                  market_context=v2["market_context"],
                                  vrp_context_status=v2["status"])

    assert b.manual_context_hash(ctx1) != b.manual_context_hash(ctx2)


def test_fmz_interaction_command_audit_survives_invalid_code():
    b = _load_bundle()
    fmz_shim._STORE.clear()
    meta = {"robot_id": "r1", "session_id": "s1", "refresh_seq": 1}

    out = b._dispatch_command("3WIC", meta, 1000)

    assert out["action"] == "EXECUTE"
    assert out["status"] == "ACCEPTED"
    assert out["outcome"] == "confirm_code_invalid_or_stale"
    audit = fmz_shim._G(b._LAST_COMMAND_KEY)
    assert audit["raw"] == "3WIC"
    assert audit["arg"] == "3WIC"
    assert audit["outcome"] == "confirm_code_invalid_or_stale"


def _display_plan(plan_id, short_i, prot_i, short_k, prot_k):
    return {
        "id": plan_id,
        "short_instrument": short_i,
        "protection_instrument": prot_i,
        "short_expiry_label": "29JUN26",
        "protection_expiry_label": "29JUN26",
        "short_strike": short_k,
        "protection_strike": prot_k,
        "short_expiry": 1000 + 48 * 3600000,
        "short_dte_hours": 48,
        "protection_dte_hours": 48,
        "protection_dte_days": 2.0,
        "short_delta": 0.30,
        "protection_delta": 0.10,
        "amount": 0.1,
        "qualified": True,
        "short_mark": 0.006,
        "short_bid": 0.0059,
        "short_ask": 0.0061,
        "short_tick": 0.0001,
        "protection_mark": 0.001,
        "protection_bid": 0.0009,
        "protection_ask": 0.0011,
        "protection_tick": 0.0001,
        "im_short_only": 0.01,
        "im_with_protection": 0.004,
        "margin_relief_abs": 0.006,
        "margin_relief_ratio": 0.6,
        "pm_ok": True,
        "account_model": "segregated_pm",
        "premium_income": 0.0006,
        "entry_fee": 0.00004,
        "spread_cost": 0.00002,
        "protection_premium": 0.0001,
        "full_burn": 0.00014,
        "win_rate": 0.7,
        "net_credit_effective": 0.00046,
        "net_credit_single": 0.0046,
        "max_loss": 0.003,
        "rr": 0.15,
        "ev": 0.0,
        "covered_cycles": 1,
        "residual_value": 0.0,
        "amortized_cost_per_cycle": 0.0001,
        "mode": 2,
        "mode_cn": "同期垂直",
        "tags": [],
        "width": abs(short_k - prot_k),
        "breakeven": short_k - 100,
        "credit_on_margin": 0.1,
        "execution_feasibility_grade": "BUILDABLE",
        "execution_feasibility_score": 88,
        "execution_feasibility_score_norm": 0.88,
        "execution_feasibility_warnings": [],
        "vrp_state": "PASS",
        "budget_decision": "ALLOW",
    }


def test_plan_locked_display_uses_locked_plan_not_first_frozen_candidate():
    b = _load_bundle()
    fmz_shim._STORE.clear()
    now = 1000
    manual_context = b.build_manual_context(
        now, True, "SHORT_PUT", (24, 72), (0.15, 0.45), (2000, 2500),
        0.1, "", "", 30, {}, market_context={"source": "GEX_MONITOR_IV_RV_RANK"},
        vrp_context_status="VRP_CONTEXT_VALID")
    first = _display_plan(1111, "BTC-29JUN26-60000-P", "BTC-29JUN26-57500-P", 60000, 57500)
    locked_plan = _display_plan(2222, "BTC-29JUN26-59500-P", "BTC-29JUN26-57000-P", 59500, 57000)
    lib = b.build_recommendation_library([first, locked_plan], "s1", manual_context, 1, now,
                                         config_hash=manual_context["config_signature"])
    locked = dict(lib["recommendations"][1])
    fmz_shim._G(b._LOCKED_KEY, locked)

    b._manual_context_for_cycle = lambda _now: manual_context
    b._lineage_invalidated = lambda _obj, _ctx, _now: None
    b._load_stable_menu = lambda _ctx: ([first, locked_plan], {"reason": "OK", "diag": {},
                                                              "vrp_blocked": 0, "lockable_count": 2})
    b._spot_price = lambda: 60000.0
    b.ledger_get_state = lambda: b.S_NO_POSITION
    b._attempt_commit = lambda *_args: {"committed": False,
                                        "precommit": {"passed": True, "failed": []},
                                        "order_intent": [], "reason": "ENTRY_WORKING:dry",
                                        "entry_state": "ENTRY_WORKING", "net_credit": 0.00046}

    ctx = b.run_cycle(now + 1)

    assert ctx["console_phase"] == "PLAN_LOCKED"
    assert ctx["preview_plan_detail"] == "locked_plan"
    assert ctx["selected_id"] == locked["plan_id"]
    assert ctx["short_instrument"] == locked["short_instrument"]
    assert ctx["menu"][0]["id"] == locked["plan_id"]
