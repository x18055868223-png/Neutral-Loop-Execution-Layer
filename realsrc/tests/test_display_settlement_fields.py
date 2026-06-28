# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import display as D


def test_ledger_table_surfaces_settlement_and_final_pnl_fields():
    table = D._ledger_recovery_table({
        "spot": 60000.0,
        "ledger_detail": {
            "reconciled": True,
            "settlement_event_count": 2,
            "settlement_pnl_status": "COMPUTED",
            "option_settlement_cashflow_ccy": -0.00002,
            "option_realized_pnl_status": "COMPUTED",
            "option_realized_pnl_ccy": 0.000148,
            "final_pnl_status": "OPEN",
            "final_option_pnl_ccy": None,
            "realized_protection_recovery_value": 0.00001,
            "realized_protection_recovery_fees": 0.000001,
        },
    })

    rows = {r[0]: r[1] for r in table["rows"]}
    assert "COMPUTED" in rows["Settlement"]
    assert "COMPUTED" in rows["Option realized PnL"]
    assert "OPEN" in rows["Final option PnL"]
    assert "0.00001 BTC" in rows["Protection recovery"]
