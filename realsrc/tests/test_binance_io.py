# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import binance_io as B
import fmz_shim


_ORIG_EX = fmz_shim.exchanges[1]


class _NoLifecycleExchange:
    def __init__(self):
        self.ticker = {"Buy": 73000.0, "Sell": 73010.0}
        self.orders = []

    def SetContractType(self, _symbol):
        pass

    def GetTicker(self):
        return dict(self.ticker)

    def SetDirection(self, _direction):
        pass

    def Buy(self, price, amount):
        self.orders.append(("buy", price, amount))
        return {"id": "b1"}

    def Sell(self, price, amount):
        self.orders.append(("sell", price, amount))
        return {"id": "s1"}


def _restore():
    fmz_shim.exchanges[1] = _ORIG_EX


def test_place_hedge_dry():
    r = B.bnc_place_hedge("BTCUSDC", "buy", 0.01, False, allow_live=False)
    assert r["dry"] and r["venue"] == "BINANCE" and r["post_only"] is False
    assert r["reason"] == "BINANCE_HEDGE_DRYRUN"


def test_place_hedge_no_op():
    assert B.bnc_place_hedge("BTCUSDC", "buy", 0.0, False, allow_live=False)["reason"] == "NO_OP"


def test_get_position_empty_returns_zero():
    assert B.bnc_get_position_btc("BTCUSDC") == 0.0


def test_place_hedge_live_submits_via_exchange():
    fmz_shim.exchanges[1].ticker = {"Buy": 73000.0, "Sell": 73010.0}
    try:
        r = B.bnc_place_hedge("BTCUSDC", "buy", 0.01, False, allow_live=True)
        assert r["venue"] == "BINANCE" and r["reason"] == "BINANCE_HEDGE_STEP"
        # reduce_only 平仓方向
        r2 = B.bnc_place_hedge("BTCUSDC", "sell", 0.01, True, allow_live=True)
        assert r2["reduce_only"] is True
    finally:
        fmz_shim.exchanges[1].ticker = {}


def test_place_hedge_live_blocks_without_order_lifecycle_methods():
    fake = _NoLifecycleExchange()
    fmz_shim.exchanges[1] = fake
    try:
        r = B.bnc_place_hedge("BTCUSDC", "buy", 0.01, False, allow_live=True)
        assert r["reason"] == "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED"
        assert r["blocked"] is True
        assert fake.orders == []
    finally:
        _restore()
