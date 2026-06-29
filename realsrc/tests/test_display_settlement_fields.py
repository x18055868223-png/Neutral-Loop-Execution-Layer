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
            "settlement_state": "BOTH_LEGS_SETTLED",
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
    assert "交割结算" in rows
    assert "期权已实现PnL" in rows
    assert "最终期权PnL" in rows
    assert "保护腿回收" in rows
    assert "已计算" in rows["交割结算"]
    assert "已计算" in rows["期权已实现PnL"]
    assert "仍在管理中" in rows["最终期权PnL"]
    assert "0.00001 BTC" in rows["保护腿回收"]
    assert "Settlement" not in rows
    assert "status=" not in " ".join(rows.values())
