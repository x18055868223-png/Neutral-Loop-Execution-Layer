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


class _ContractAwareExchange:
    def __init__(self):
        self.io_calls = []
        self.contracts = []
        self.orders = []
        self.positions = [{"Type": "long", "Amount": 0.02}]
        self.ticker = {"Buy": 73000.0, "Sell": 73010.0}

    def IO(self, *args):
        self.io_calls.append(args)
        return True

    def SetContractType(self, contract_type):
        self.contracts.append(contract_type)
        if contract_type != "swap":
            raise Exception("Invalid ContractType")

    def GetPosition(self):
        return list(self.positions)

    def GetTicker(self):
        return dict(self.ticker)

    def SetDirection(self, _direction):
        pass

    def Buy(self, _price, _amount):
        self.orders.append(("buy", _price, _amount))
        return {"id": "b1"}

    def Sell(self, _price, _amount):
        self.orders.append(("sell", _price, _amount))
        return {"id": "s1"}

    def GetOrder(self, oid):
        return {"Id": oid, "Status": 2, "DealAmount": 0.0}

    def CancelOrder(self, _oid):
        return True


class _PositionNoneExchange(_ContractAwareExchange):
    def GetPosition(self):
        return None


class _MissingOrderIdExchange(_ContractAwareExchange):
    def Buy(self, _price, _amount):
        self.orders.append(("buy", _price, _amount))
        return {"status": "accepted"}

    def Sell(self, _price, _amount):
        self.orders.append(("sell", _price, _amount))
        return {"status": "accepted"}


def _restore():
    fmz_shim.exchanges[1] = _ORIG_EX


def test_get_position_empty_returns_zero():
    assert B.bnc_get_position_btc("BTCUSDC") == 0.0


def test_get_position_none_is_data_gap_not_zero():
    fake = _PositionNoneExchange()
    fmz_shim.exchanges[1] = fake
    try:
        assert B.bnc_get_position_snapshot("BTCUSDC") is None
        assert B.bnc_get_position_btc("BTCUSDC") is None
    finally:
        _restore()


def test_get_position_selects_btc_usdc_swap_contract():
    fake = _ContractAwareExchange()
    fmz_shim.exchanges[1] = fake
    try:
        assert B.bnc_get_position_btc("BTCUSDC") == 0.02
        assert fake.io_calls == [("currency", "BTC_USDC")]
        assert fake.contracts == ["swap"]
    finally:
        _restore()


def test_get_position_snapshot_includes_unrealized_pnl():
    fake = _ContractAwareExchange()
    fake.positions = [
        {"Type": "long", "Amount": 0.02, "Profit": 1.25},
        {"Type": "short", "Amount": 0.01, "UnrealizedProfit": -0.30},
    ]
    fmz_shim.exchanges[1] = fake
    try:
        snap = B.bnc_get_position_snapshot("BTCUSDC")
        assert abs(snap["qty"] - 0.01) < 1e-12
        assert abs(snap["unrealized_pnl_usd"] - 0.95) < 1e-12
        assert snap["pair"] == "BTC_USDC"
        assert snap["contract_type"] == "swap"
        assert B.bnc_get_position_btc("BTCUSDC") == 0.01
    finally:
        _restore()


def test_v32_submit_selects_btc_usdc_swap_contract():
    fake = _ContractAwareExchange()
    fmz_shim.exchanges[1] = fake
    try:
        r = B.bnc_submit_hedge_order("BTCUSDC", "buy", 0.01, False, allow_live=True)
        assert r["reason"] == "BINANCE_HEDGE_SUBMITTED"
        assert fake.io_calls == [("currency", "BTC_USDC")]
        assert fake.contracts == ["swap"]
    finally:
        _restore()


def test_v32_submit_rounds_binance_price_tick_by_side():
    fake = _ContractAwareExchange()
    fake.ticker = {"Buy": 59968.6007, "Sell": 60067.91895}
    fmz_shim.exchanges[1] = fake
    try:
        buy = B.bnc_submit_hedge_order("BTCUSDC", "buy", 0.001, False,
                                       allow_live=True, cross_bps=0)
        sell = B.bnc_submit_hedge_order("BTCUSDC", "sell", 0.001, True,
                                        allow_live=True, cross_bps=0)
        assert buy["price"] == 60068.0
        assert sell["price"] == 59968.6
        assert fake.orders[0] == ("buy", 60068.0, 0.001)
        assert fake.orders[1] == ("sell", 59968.6, 0.001)
    finally:
        _restore()


def test_v32_submit_blocks_without_order_lifecycle_methods():
    fake = _NoLifecycleExchange()
    fmz_shim.exchanges[1] = fake
    try:
        r = B.bnc_submit_hedge_order("BTCUSDC", "sell", 0.01, False, allow_live=True)
        assert r["reason"] == "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED"
        assert r["blocked"] is True
        assert r["order_id"] is None
        assert fake.orders == []
    finally:
        _restore()


def test_v32_submit_without_order_id_is_blocked_uncertain_submit():
    fake = _MissingOrderIdExchange()
    fmz_shim.exchanges[1] = fake
    try:
        r = B.bnc_submit_hedge_order("BTCUSDC", "buy", 0.01, False, allow_live=True)
        assert r["reason"] == "BINANCE_ORDER_ID_MISSING"
        assert r["blocked"] is True
        assert r["order_id"] is None
        assert fake.orders == [("buy", r["price"], 0.01)]
    finally:
        _restore()
