# -*- coding: utf-8 -*-
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import fmz_shim
import strategy as ST


_ORIG_EX = fmz_shim.exchanges[1]
_ORIG = {name: getattr(ST, name) for name in (
    "RUN_PROFILE", "MANUAL_PLANNING_ALLOWED", "HEDGE_VENUE",
    "HEDGE_BINANCE_INSTRUMENT", "dbt_get_positions_strict",
    "dbt_get_open_orders", "_spot_price")}


class _StartupBinance:
    def __init__(self, qty):
        self.qty = qty
        self.io_calls = []
        self.contract = None
        self.direction = None
        self.orders = []
        self.ticker = {"Buy": 59990.0, "Sell": 60000.0}

    def IO(self, *args):
        self.io_calls.append(args)
        return True

    def SetContractType(self, contract):
        self.contract = contract

    def GetPosition(self):
        if self.qty >= 0:
            return [{"Type": 0, "Amount": abs(self.qty)}]
        return [{"Type": 1, "Amount": abs(self.qty)}]

    def GetTicker(self):
        return dict(self.ticker)

    def SetDirection(self, direction):
        self.direction = direction

    def Buy(self, price, amount):
        self.orders.append(("buy", price, amount))
        return {"id": "orphan-buy"}

    def Sell(self, price, amount):
        self.orders.append(("sell", price, amount))
        return {"id": "orphan-sell"}

    def GetOrder(self, oid):
        return {"Id": oid, "Status": 0, "DealAmount": 0.0}

    def CancelOrder(self, oid):
        return True


class _NoLifecycleBinance:
    def __init__(self):
        self.orders = []

    def IO(self, *args):
        return True

    def SetContractType(self, contract):
        return True

    def GetPosition(self):
        return [{"Type": 0, "Amount": 0.01}]

    def GetTicker(self):
        return {"Buy": 59990.0, "Sell": 60000.0}

    def SetDirection(self, direction):
        return True

    def Buy(self, price, amount):
        self.orders.append(("buy", price, amount))
        return {"id": "bad-buy"}

    def Sell(self, price, amount):
        self.orders.append(("sell", price, amount))
        return {"id": "bad-sell"}


def _setup(profile="LIVE", qty=0.01):
    fmz_shim._STORE.clear()
    fmz_shim._commands.clear()
    fake = _StartupBinance(qty)
    fmz_shim.exchanges[1] = fake
    ST.RUN_PROFILE = profile
    ST.MANUAL_PLANNING_ALLOWED = False
    ST.HEDGE_VENUE = "BINANCE"
    ST.HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"
    ST.dbt_get_positions_strict = lambda *_a, **_k: []
    ST.dbt_get_open_orders = lambda *_a, **_k: []
    ST._spot_price = lambda: 60000.0
    ST.ledger_set_state(ST.S_NO_POSITION)
    return fake


def _setup_with_exchange(ex, profile="LIVE"):
    fmz_shim._STORE.clear()
    fmz_shim._commands.clear()
    fmz_shim.exchanges[1] = ex
    ST.RUN_PROFILE = profile
    ST.MANUAL_PLANNING_ALLOWED = False
    ST.HEDGE_VENUE = "BINANCE"
    ST.HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"
    ST.dbt_get_positions_strict = lambda *_a, **_k: []
    ST.dbt_get_open_orders = lambda *_a, **_k: []
    ST._spot_price = lambda: 60000.0
    ST.ledger_set_state(ST.S_NO_POSITION)
    return ex


def _restore():
    fmz_shim.exchanges[1] = _ORIG_EX
    fmz_shim._STORE.clear()
    fmz_shim._commands.clear()
    for name, value in _ORIG.items():
        setattr(ST, name, value)
    ST.ledger_set_state(ST.S_NO_POSITION)


def test_startup_orphan_hedge_clean_evidence_auto_reduces_in_live():
    fake = _setup("LIVE", qty=0.01)
    now = int(time.time() * 1000)
    try:
        verdict = ST.startup_recovery_check("BTC")

        assert verdict["state"] == "ORPHAN_HEDGE_EMERGENCY"
        assert verdict["auto_cleanup_allowed"] is True
        ctx = ST.run_cycle(now)
        panel = ST.disp_status_panel(ctx, "测试")

        assert ctx["console_phase"] == "ORPHAN_HEDGE_AUTO_CLEANUP"
        assert ctx["orphan_hedge_cleanup"]["policy"] == "AUTO_REDUCE_ONLY"
        assert ctx["orphan_hedge_cleanup"]["suggested_side"] == "sell"
        assert ctx["orphan_hedge_cleanup_step"]["reason"] == "BINANCE_HEDGE_SUBMITTED"
        assert ctx["orphan_hedge_cleanup_step"]["dry"] is False
        assert fake.direction == "closebuy"
        assert fake.orders and fake.orders[0][0] == "sell"
        assert "自动" in panel and "只减" in panel
    finally:
        _restore()


def test_startup_orphan_hedge_without_order_lifecycle_stays_manual_no_order():
    fake = _setup_with_exchange(_NoLifecycleBinance(), "LIVE")
    now = int(time.time() * 1000)
    try:
        verdict = ST.startup_recovery_check("BTC")

        assert verdict["state"] == "ORPHAN_HEDGE_EMERGENCY"
        assert verdict["auto_cleanup_allowed"] is False
        assert verdict["cleanup_block_reason"] == "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED"
        ctx = ST.run_cycle(now)
        panel = ST.disp_status_panel(ctx, "测试")

        assert ctx["console_phase"] == "ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED"
        assert ctx["orphan_hedge_cleanup"]["policy"] == "MANUAL_CLEANUP_ONLY"
        assert fake.orders == []
        assert "需要人工只减清理" in panel
    finally:
        _restore()


def test_startup_orphan_hedge_same_evidence_in_test_is_dry_only():
    fake = _setup("TEST", qty=-0.02)
    now = int(time.time() * 1000)
    try:
        verdict = ST.startup_recovery_check("BTC")

        assert verdict["state"] == "ORPHAN_HEDGE_EMERGENCY"
        assert verdict["auto_cleanup_allowed"] is True
        ctx = ST.run_cycle(now)

        assert ctx["console_phase"] == "ORPHAN_HEDGE_AUTO_CLEANUP"
        assert ctx["orphan_hedge_cleanup"]["policy"] == "AUTO_REDUCE_ONLY"
        assert ctx["orphan_hedge_cleanup"]["suggested_side"] == "buy"
        assert ctx["orphan_hedge_cleanup_step"]["reason"] == "BINANCE_HEDGE_DRYRUN"
        assert ctx["orphan_hedge_cleanup_step"]["dry"] is True
        assert fake.orders == []
    finally:
        _restore()
