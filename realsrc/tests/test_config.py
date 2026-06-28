# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import config as C


def _with_config(**overrides):
    old = {k: getattr(C, k) for k in overrides}
    try:
        for k, v in overrides.items():
            setattr(C, k, v)
        return C.validate_config()
    finally:
        for k, v in old.items():
            setattr(C, k, v)


def test_default_config_is_dry_run_ready():
    assert C.validate_config() == []


def test_run_profile_test_forces_effective_gates_off():
    old = {
        "RUN_PROFILE": C.RUN_PROFILE,
        "ALLOW_ENTRY_TRADING": C.ALLOW_ENTRY_TRADING,
        "ALLOW_EXIT_TRADING": C.ALLOW_EXIT_TRADING,
        "ALLOW_HEDGE_TRADING": C.ALLOW_HEDGE_TRADING,
        "DRY_RUN_PASSED": C.DRY_RUN_PASSED,
    }
    try:
        C.RUN_PROFILE = "TEST"
        C.ALLOW_ENTRY_TRADING = True
        C.ALLOW_EXIT_TRADING = True
        C.ALLOW_HEDGE_TRADING = True
        C.DRY_RUN_PASSED = True

        assert C.validate_config() == []
        gates = C.effective_trading_gates()
        assert gates["profile"] == "TEST"
        assert gates["allow_entry"] is False
        assert gates["allow_exit"] is False
        assert gates["allow_hedge"] is False
    finally:
        for k, v in old.items():
            setattr(C, k, v)


def test_run_profile_live_requires_minimum_checklist():
    old = {
        "RUN_PROFILE": C.RUN_PROFILE,
        "DRY_RUN_PASSED": C.DRY_RUN_PASSED,
        "ALLOW_ENTRY_TRADING": C.ALLOW_ENTRY_TRADING,
        "ALLOW_EXIT_TRADING": C.ALLOW_EXIT_TRADING,
        "ALLOW_HEDGE_TRADING": C.ALLOW_HEDGE_TRADING,
        "RISK_EXIT_MAX_SPEND": C.RISK_EXIT_MAX_SPEND,
    }
    try:
        C.RUN_PROFILE = "LIVE"
        C.DRY_RUN_PASSED = False
        C.ALLOW_ENTRY_TRADING = False
        C.ALLOW_EXIT_TRADING = False
        C.ALLOW_HEDGE_TRADING = False
        C.RISK_EXIT_MAX_SPEND = 0.0

        errs = C.validate_config()
        missing = C.live_checklist_missing()
        for key in ("DRY_RUN_PASSED", "ALLOW_ENTRY_TRADING",
                    "ALLOW_EXIT_TRADING", "RISK_EXIT_MAX_SPEND"):
            assert key in missing
            assert any(key in e for e in errs)
    finally:
        for k, v in old.items():
            setattr(C, k, v)


def test_live_trading_gates_require_dry_run_passed():
    errs = _with_config(RUN_PROFILE="LIVE", DRY_RUN_PASSED=False,
                        ALLOW_EXIT_TRADING=True)

    assert any("DRY_RUN_PASSED" in e for e in errs)


def test_entry_live_requires_exit_path_and_risk_budget():
    errs = _with_config(RUN_PROFILE="LIVE", DRY_RUN_PASSED=True, ALLOW_ENTRY_TRADING=True,
                        ALLOW_EXIT_TRADING=False, RISK_EXIT_MAX_SPEND=0.0)

    assert any("ALLOW_EXIT_TRADING" in e for e in errs)
    assert any("RISK_EXIT_MAX_SPEND" in e for e in errs)


def test_threshold_sanity_checks_fail_closed():
    errs = _with_config(
        RISK_EXIT_MAX_SPEND=-0.1,
        EXIT_RESERVE_RATIO=1.0,
        HEDGE_REDUCTION_RATIO=0.0,
        HEDGE_MARGIN_RESERVE_RATE=-0.1,
        PORTFOLIO_LIMITS={"max_open_positions": 1, "max_margin": -0.1},
    )

    assert any("RISK_EXIT_MAX_SPEND" in e for e in errs)
    assert any("EXIT_RESERVE_RATIO" in e for e in errs)
    assert any("HEDGE_REDUCTION_RATIO" in e for e in errs)
    assert any("HEDGE_MARGIN_RESERVE_RATE" in e for e in errs)
    assert any("PORTFOLIO_LIMITS" in e for e in errs)


def test_minimal_v32_rejects_deribit_hedge_venue():
    errs = _with_config(HEDGE_VENUE="DERIBIT")

    assert any("Minimal V32 hedge supports BINANCE only" in e for e in errs)


def test_minimal_config_does_not_expose_maker_first_reduce_switch():
    assert not hasattr(C, "HEDGE_MAKER_FIRST_REDUCE_ENABLED")


def test_v32_policy_switch_is_primary_config_name():
    assert C.HEDGE_POLICY_V32_ENABLED is True
    assert C.HEDGE_POLICY_V313_ENABLED == C.HEDGE_POLICY_V32_ENABLED
