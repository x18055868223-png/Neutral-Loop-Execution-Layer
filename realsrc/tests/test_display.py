# -*- coding: utf-8 -*-
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import display as D


V32_POLICY_REASONS = (
    "HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT",
    "SUBMIT_UNKNOWN_RECENT",
    "PENDING_ACTIVE",
    "PENDING_FILLED",
    "PENDING_PARTIAL_ACTIVE",
    "PENDING_STALE_RECOVERED",
    "PENDING_STALE_CANCEL_FAILED",
    "POSITION_READ_FAILED",
    "TARGET_DATA_GAP",
    "SOFT_TRIGGER_INITIAL",
    "SOFT_TRIGGER_CONFIRMED",
    "HARD_TRIGGER_EMERGENCY",
    "CRASH_TRIGGER_SPEED",
    "FINAL3H_SOFT_ADD_SUPPRESSED",
    "ADD_COOLDOWN_ACTIVE",
    "REDUCE_COOLDOWN_ACTIVE",
    "REDUCE_MIN_HOLD_ACTIVE",
    "REDUCE_HYSTERESIS_WAIT",
    "REDUCE_CONFIRMED",
    "REVERSE_HEDGE_UNWIND",
    "ORPHAN_HEDGE_UNWIND",
    "NO_TRIGGER",
    "HOLD_EXISTING",
    "LOT_DEADBAND",
    "TARGET_BAND_DEADBAND",
    "BINANCE_ORDER_ID_MISSING",
)


EXIT_CAMPAIGN_STATES = (
    "IDLE",
    "WAIT_TRIGGER",
    "WORKING_SHORT",
    "PAUSED_BY_BUDGET",
    "PAUSED_BY_DATA",
    "WORKING_LONG",
    "LONG_RESIDUAL_ONLY",
    "COMPLETE",
    "HOLD_PROTECTION_UNTIL_SHORT_FLAT",
)


def _tables_from_panel(panel):
    # 面板格式： "header...#color\n`<json array>`"
    assert "`" in panel
    raw = panel.split("`", 1)[1].rsplit("`", 1)[0]
    return json.loads(raw)


def _ctx():
    return {
        "currency": "BTC", "manual_gate_state": "PLANNING_ALLOWED",
        "manual_context_ttl_min": 30,
        "direction_bias": "SHORT_CALL", "allow_trading": False,
        "state": "SPM_SIMULATION", "spot": 73400.0, "reason": "DRY_RUN_PLAN_ONLY",
        "short_instrument": "BTC-31MAY26-78000-C", "short_strike": 78000,
        "short_dte_hours": 47.56, "short_mark": 0.0001, "short_bid": 0,
        "short_ask": 0.0002, "short_tick": 0.0001, "short_delta": 0.04,
        "protection_instrument": "BTC-5JUN26-79000-C", "protection_strike": 79000,
        "protection_dte_days": 6.98, "protection_mark": 0.0011, "protection_bid": 0.001,
        "protection_ask": 0.0011, "protection_tick": 0.0001, "protection_delta": 0.06,
        "im_short_only": 0.0073, "im_with_protection": 0.0012,
        "margin_relief_abs": 0.0061, "margin_relief_ratio": 0.837,
        "min_required_ratio": 0.1, "pm_accepted": True,
        "account_margin_model": "segregated_pm",
        "short_premium_income": 0.00001, "estimated_entry_fee": 0.0000125,
        "protection_entry_cost": 0.00011, "full_burn_cost": 0.000124,
        "estimated_spread_cost": 0.00001,
    }


def test_reason_and_state_maps():
    assert D.disp_reason_cn("DRY_RUN_PLAN_ONLY").startswith("空跑")
    assert D.disp_reason_cn("EXIT_REVIEW_MANUAL:MANUAL_CONTEXT_INVALID").find("无效") >= 0
    assert D.disp_state_cn("SHORT_ACTIVE_PROTECTED") == "已保护·卖方持仓"
    assert D.disp_manual_gate_state_cn("PLANNING_ALLOWED").find("已开启") >= 0


def test_v32_policy_reasons_are_chinese_mapped():
    for reason in V32_POLICY_REASONS:
        text = D.disp_reason_cn(reason)
        assert text != reason, reason
        assert reason not in text, reason


def test_exit_campaign_states_are_chinese_mapped():
    for state in EXIT_CAMPAIGN_STATES:
        text = D.disp_exit_campaign_state_cn(state)
        assert text != state, state
        assert state not in text, state


def test_panel_is_valid_fmz_tables():
    panel = D.disp_status_panel(_ctx(), "进场流水线 [空跑核对]")
    tables = _tables_from_panel(panel)
    # 交互控制台(置顶) + 运行概览 + 完整主链 + 保证金与成本 + 合理性检查 = 5 表
    assert isinstance(tables, list) and len(tables) == 5
    assert tables[0]["title"] == "交互控制台"
    assert tables[2]["title"] == "完整主链模块回显"
    for t in tables:
        assert t["type"] == "table"
        assert "title" in t and "cols" in t and "rows" in t
        for r in t["rows"]:
            assert len(r) == len(t["cols"])   # 行列对齐


def test_panel_restores_full_plan_and_order_status_tabs():
    ctx = _ctx()
    plan = {
        "id": 9269,
        "tags": ["可锁"],
        "expiry_role": "TARGET_24H",
        "mode_cn": "同期期权",
        "short_expiry_label": "29JUN26",
        "short_dte_hours": 24,
        "short_strike": 60000,
        "short_delta": -0.40,
        "protection_strike": 57500,
        "width": 2500,
        "win_rate": 0.71,
        "net_credit_effective": 0.0009,
        "credit_on_margin": 0.18,
        "credit_on_margin_per_24h": 0.18,
        "rr": 0.32,
        "breakeven": 59000,
        "margin_relief_ratio": 0.71,
        "qualified": True,
        "execution_feasibility_grade": "警示",
        "_confirm_code": "4PTU",
    }
    ctx.update(
        console_phase="PLAN_LOCKED",
        menu=[plan],
        selected_plan=9269,
        selected_id=9269,
        preview_plan_detail="stable_first_candidate",
        pending_candidates=[{"id": 9269, "summary": "PUT Δ-0.40", "confirm_code": "4PTU"}],
        display_candidates_count=1,
        lockable_candidates_count=1,
        plan_vrp_blocked=0,
        menu_source="built_frozen",
        plan_library_frozen=True,
        order_intent=[
            {"leg": "保护腿", "side": "buy", "instrument": "BTC-29JUN26-57500-P",
             "prices": [0.0009, 0.0010], "amount": 0.1},
            {"leg": "卖方腿", "side": "sell", "instrument": "BTC-29JUN26-60000-P",
             "prices": [0.0071, 0.0070], "amount": 0.1},
        ],
    )
    titles = [t["title"] for t in _tables_from_panel(D.disp_status_panel(ctx, "测试"))]
    assert titles[0:3] == ["交互控制台", "运行概览", "完整主链模块回显"]
    assert any(t.startswith("固定备选方案库") for t in titles)
    assert any(t.startswith("候选方案预览") for t in titles)
    assert "将下达订单（maker-only；计划价含一步追价）" in titles
    assert any(t.startswith("合理性检查") for t in titles)
    menu = next(t for t in _tables_from_panel(D.disp_status_panel(ctx, "测试"))
                if t["title"].startswith("固定备选方案库"))
    assert "确认码/锁定状态" in menu["cols"]
    code_idx = menu["cols"].index("确认码/锁定状态")
    assert menu["rows"][0][code_idx] == "4PTU"


def test_menu_promotes_earliest_displayed_backup_to_nearest_available():
    table = D.disp_menu_table([
        {"id": 1, "expiry_role": "NEXT_EXPIRY", "short_expiry": 2000,
         "short_expiry_label": "29JUN26", "mode_cn": "同期垂直",
         "short_dte_hours": 45.0, "short_strike": 60000, "short_delta": -0.30,
         "protection_strike": 57500, "width": 2500, "qualified": True},
        {"id": 2, "expiry_role": "NEXT_EXPIRY", "short_expiry": 2000,
         "short_expiry_label": "29JUN26", "mode_cn": "同期垂直",
         "short_dte_hours": 45.0, "short_strike": 59500, "short_delta": -0.22,
         "protection_strike": 57000, "width": 2500, "qualified": True},
    ], None, 60000)
    rows = table["rows"]
    role_idx = table["cols"].index("期号角色")
    assert rows
    assert all(r[role_idx] == "最近可用" for r in rows)


def test_health_flags_no_bid_and_cost_multiple():
    notes = D.disp_health_notes(_ctx())
    levels = [lv for lv, _ in notes]
    texts = " ".join(t for _, t in notes)
    assert "警示" in levels                 # best_bid=0
    assert "无买盘" in texts
    assert "倍" in texts                     # 保护成本/权利金倍数提示


def test_health_clean_passes():
    ctx = _ctx()
    ctx.update(short_bid=0.0002, short_premium_income=0.01,
               estimated_entry_fee=0.0001, protection_entry_cost=0.02,
               protection_delta=0.2)
    notes = D.disp_health_notes(ctx)
    assert any(lv == "通过" for lv, _ in notes)


def test_btc_usd_formatting():
    s = D._btc_usd(0.0001, 73400.0)
    assert "BTC" in s and "$" in s
    assert D._usd(None, 73400.0) == "—"


def test_console_table_present_and_confirm_code_and_hint():
    ctx = _ctx()
    ctx.update(
        console_phase="HARD_APPROVAL_WAIT",
        gate_summary={"ENTRY": {"allowed": False}, "EXIT": {"allowed": True},
                      "HEDGE_OPEN": {"allowed": False}, "HEDGE_REDUCE": {"allowed": True}},
        manual_verdict={"availability": "OK", "block_new_opens": False,
                        "direction_bias": "SHORT_CALL"},
        pending_candidates=[{"id": 1234, "summary": "SHORT_CALL Δ0.30", "confirm_code": "A4F2"}])
    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    assert tables[0]["title"] == "交互控制台"
    rows = {r[0]: r[1] for r in tables[0]["rows"]}
    assert "待计划硬授权" in rows["阶段"]
    assert "A4F2" in rows["待批 #1234"]
    assert "执行" in rows["操作提示"] and "确认码" in rows["操作提示"]
    assert "进场✗" in rows["执行门控"] and "退出✓" in rows["执行门控"]


def test_console_surfaces_entry_protection_persistent_order():
    ctx = _ctx()
    ctx.update(
        console_phase="PLAN_LOCKED",
        entry_state="ENTRY_WORKING",
        entry_net_credit=0.0005,
        entry_prot_order={
            "order_id": "p1", "price": 0.0002,
            "wait_elapsed_ms": 610000, "taker_due": True,
        },
    )
    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    rows = {r[0]: r[1] for r in tables[0]["rows"]}
    assert "保护腿挂单" in rows
    assert "p1" in rows["保护腿挂单"]
    assert "0.0002" in rows["保护腿挂单"]
    assert "610s" in rows["保护腿挂单"]
    assert "taker兜底区" in rows["保护腿挂单"]


def test_overview_uses_split_action_gates_not_single_allow_trading():
    ctx = _ctx()
    ctx.update(gate_summary={"ENTRY": {"allowed": False}, "EXIT": {"allowed": True},
                             "HEDGE_OPEN": {"allowed": False}, "HEDGE_REDUCE": {"allowed": True}})
    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    rows = {r[0]: r[1] for r in tables[1]["rows"]}
    assert "进场✗" in rows["执行门控"] and "退出✓" in rows["执行门控"]
    assert "ALLOW_TRADING" not in rows["执行门控"]


def test_overview_surfaces_startup_self_check_summary():
    ctx = _ctx()
    ctx.update(startup_self_check={
        "overall": "OK",
        "checks": {
            "deribit_index": {"ok": True},
            "deribit_options": {"ok": True},
            "gex_context": {"ok": False, "reason": "TIMEOUT"},
            "binance_hedge_position": {"ok": True},
        },
    })
    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    rows = {r[0]: r[1] for r in tables[1]["rows"]}
    assert rows["启动自检"].startswith("OK")
    assert "GEX:TIMEOUT" in rows["启动自检"]


def test_console_surfaces_manage_in_flight_orders():
    ctx = _ctx()
    ctx.update(console_phase="POSITION_MANAGE",
               action_arb={"preferred_action": "MANAGE_IN_FLIGHT",
                           "executable_action": "MANAGE_IN_FLIGHT",
                           "blocked_reason": None},
               manage_in_flight_order={"count": 1,
                                       "orders": [{"instrument_name": "BTC-X",
                                                   "label": "exit-working"}]})
    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    rows = {r[0]: r[1] for r in tables[0]["rows"]}
    assert "1" in rows["活动订单"]
    assert "exit-working" in rows["活动订单"]


def test_console_surfaces_hedge_position_data_gap():
    ctx = _ctx()
    ctx.update(console_phase="POSITION_MANAGE",
               hedge_data_gap="HEDGE_POSITION_DATA_GAP")
    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    rows = {r[0]: r[1] for r in tables[0]["rows"]}
    assert "HEDGE_POSITION_DATA_GAP" in rows["对冲数据"]
    assert "禁新增对冲" in rows["对冲数据"]


def test_position_manage_panel_adds_structured_module_tables():
    ctx = _ctx()
    ctx.update(
        console_phase="POSITION_MANAGE",
        state="SHORT_ACTIVE_PROTECTED",
        position_detail={
            "lifecycle": "已保护·卖方持仓",
            "short_instrument": "BTC-28JUN26-60000-P",
            "long_instrument": "BTC-28JUN26-58000-P",
            "remaining_short_qty": 0.1,
            "long_remaining_qty": 0.1,
            "short_fill_price": 0.0020,
            "long_fill_price": 0.0003,
            "short_mark": 0.0014,
            "short_bid": 0.0013,
            "short_ask": 0.0015,
            "long_mark": 0.0002,
            "long_bid": 0.0001,
            "long_ask": 0.0003,
            "dte_hours": 20.5,
            "breakeven": 59800.0,
            "short_distance_pct": -0.4,
            "option_short_unrealized_pnl_usd": 3.61,
            "option_long_unrealized_pnl_usd": -0.60,
            "option_unrealized_pnl_usd": 3.01,
            "hedge_unrealized_pnl_usd": None,
            "hedge_pnl_state": "对冲未启用",
            "combo_unrealized_pnl_usd": 3.01,
        },
        take_profit_detail={
            "status": "未达标",
            "ratio": 0.35,
            "target_ratio": 0.80,
            "entry_profit_ceiling_net": 0.00017,
            "target_profit_amount": 0.000136,
            "short_buyback_ref": 0.00014,
            "estimated_exit_fee": 0.000002,
            "exit_reserve": 0.000006,
            "remaining_budget": 0.000026,
            "price_cap": 0.0002,
            "short_price_cap": 0.0002,
            "tp_underlying_target_price": 59850.0,
            "tp_underlying_target_method": "delta_linear",
            "quote_ok": True,
        },
        risk_exit_detail={
            "auth_code": "J4OX",
            "authorized": False,
            "budget_source": "RISK_EXIT_MAX_SPEND",
            "remaining_budget": 0.001,
            "price_cap": 0.01,
            "within": True,
            "within_price": True,
            "ask": 0.008,
            "ask_depth": 0.12,
            "depth_ok": True,
        },
        hedge_detail={
            "venue": "BINANCE",
            "instrument": "BTCUSDC",
            "side": "sell",
            "action_cn": "新开对冲",
            "action": "HEDGE_OPEN",
            "reduce_only": False,
            "entry_touch_probability": 0.20,
            "touch_probability_now": 0.45,
            "touch_probability_drift": 0.25,
            "watch_probability": 0.40,
            "open_probability": 0.50,
            "emergency_probability": 0.70,
            "hedge_price_line": None,
            "hedge_underlying_trigger_price": 60350.0,
            "hedge_underlying_trigger_method": "probability_bisection",
            "net_option_delta": -0.03,
            "target": -0.015,
            "perp_qty": 0.0,
            "delta_to_trade": -0.015,
        },
        ledger_detail={
            "short_credit": 0.00020,
            "protection_cost": 0.00003,
            "entry_fees": 0.000002,
            "actual_net_credit": 0.000168,
            "realized_exit_spend": 0.0,
            "remaining_exit_budget": 0.000026,
            "entry_fill_count": 2,
            "exit_fill_count": 0,
            "protection_recovery_count": 0,
            "hedge_fill_count": 0,
            "settlement_event_count": 2,
            "settlement_pnl_status": "COMPUTED",
            "option_settlement_cashflow_ccy": -0.00002,
            "option_realized_pnl_status": "COMPUTED",
            "option_realized_pnl_ccy": 0.000148,
            "final_pnl_status": "OPEN",
            "final_option_pnl_ccy": None,
            "realized_protection_recovery_value": 0.0,
            "realized_protection_recovery_fees": 0.0,
            "reconciled": True,
            "reconcile_reasons": [],
            "recovery_state": "OK",
            "allow_new_open": True,
            "data_quality_state": "OK",
            "legacy_recovery_gaps": [],
            "active_orders": [{"instrument_name": "BTC-28JUN26-60000-P", "label": "exit_short"}],
        },
    )

    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    titles = [t["title"] for t in tables]
    assert "持仓总览" in titles
    assert "止盈/退出预算" in titles
    assert "风险与对冲" in titles
    assert "记账/对账/恢复" in titles
    hedge_rows = {r[0]: r[1] for r in next(t for t in tables if t["title"] == "风险与对冲")["rows"]}
    assert "45.0%" in hedge_rows["触界概率(入场/当前/漂移)"]
    assert "50.0%" in hedge_rows["对冲触发阈值"]
    assert "新开对冲" in hedge_rows["对冲动作"]
    assert "60350" in hedge_rows["对冲触发目标价"]
    tp_rows = {r[0]: r[1] for r in next(t for t in tables if t["title"] == "止盈/退出预算")["rows"]}
    assert "未达标" in tp_rows["止盈状态"]
    assert "预算内最高可买回价" in tp_rows["止盈目标价"]
    assert "59850" in tp_rows["止盈目标标的价"]
    assert "卖一" in tp_rows["风险退出盘口"]
    assert "深度" in tp_rows["风险退出盘口"]
    pos_rows = {r[0]: r[1] for r in next(t for t in tables if t["title"] == "持仓总览")["rows"]}
    assert "$3.01" in pos_rows["期权浮动盈亏"]
    assert "对冲未启用" in pos_rows["期货对冲浮动盈亏"]
    assert "$3.01" in pos_rows["组合浮动盈亏"]
    ledger_rows = {r[0]: r[1] for r in next(t for t in tables if t["title"] == "记账/对账/恢复")["rows"]}
    assert "已对齐" in ledger_rows["交易所对账"]
    assert "exit_short" in ledger_rows["活动订单"]


def test_position_manage_data_gap_uses_explicit_gap_text():
    ctx = _ctx()
    ctx.update(
        console_phase="POSITION_MANAGE",
        state="SHORT_ACTIVE_PROTECTED",
        hedge_detail={
            "data_gap": "HEDGE_DELTA_DATA_GAP",
            "action_cn": "保持",
            "venue": "BINANCE",
            "instrument": "BTCUSDC",
        },
        take_profit_detail={"status": "数据缺口", "quote_ok": False, "quote_gap": "NO_RELIABLE_QUOTE"},
        ledger_detail={"reconciled": None, "reconcile_reasons": ["NO_POSITION_SNAPSHOT"],
                       "recovery_state": "OK", "active_orders": []},
    )

    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    hedge_rows = {r[0]: r[1] for r in next(t for t in tables if t["title"] == "风险与对冲")["rows"]}
    assert "数据缺口" in hedge_rows["模块状态"]
    assert "HEDGE_DELTA_DATA_GAP" in hedge_rows["模块状态"]
    assert "0.0%" not in hedge_rows["触界概率(入场/当前/漂移)"]
    tp_rows = {r[0]: r[1] for r in next(t for t in tables if t["title"] == "止盈/退出预算")["rows"]}
    assert "数据缺口" in tp_rows["止盈状态"]
    ledger_rows = {r[0]: r[1] for r in next(t for t in tables if t["title"] == "记账/对账/恢复")["rows"]}
    assert "数据缺口" in ledger_rows["交易所对账"]


def test_position_manage_surfaces_crash_reference_observability_only():
    ctx = _ctx()
    ctx.update(
        console_phase="POSITION_MANAGE",
        state="SHORT_ACTIVE_PROTECTED",
        hedge_detail={
            "venue": "BINANCE",
            "instrument": "BTCUSDC",
            "side": "buy",
            "action_cn": "新开对冲",
            "action": "HEDGE_OPEN",
            "reduce_only": False,
            "hedge_policy": "V32",
            "policy_state": "CRASH",
            "policy_reason": "CRASH_TRIGGER_SPEED",
            "full_target_qty": 0.02,
            "eff_target_qty": 0.02,
            "current_hedge_qty": 0.0,
            "policy_delta_to_trade": 0.02,
            "crash_ref_price": 60000.0,
            "crash_ref_age_seconds": 300.0,
            "crash_adverse_bps": 116.7,
        },
        take_profit_detail={"status": "未达标", "ratio": 0.2, "target_ratio": 0.8},
        ledger_detail={"reconciled": True, "recovery_state": "OK", "active_orders": []},
    )

    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    hedge_rows = {r[0]: r[1:] for r in next(t for t in tables if t["title"] == "风险与对冲")["rows"]}

    assert "Crash观测" in hedge_rows
    assert "CRASH_TRIGGER_SPEED" not in D.disp_status_panel(ctx, "测试")
    assert "崩盘速度紧急触发" in D.disp_status_panel(ctx, "测试")
    assert "60000" in hedge_rows["Crash观测"][0]
    assert "300" in hedge_rows["Crash观测"][0]
    assert "116.7" in hedge_rows["Crash观测"][0]
    assert "只读观测" in hedge_rows["Crash观测"][1]


def test_position_manage_marks_episode_cost_as_reserved_not_computed():
    ctx = _ctx()
    ctx.update(
        console_phase="POSITION_MANAGE",
        state="SHORT_ACTIVE_PROTECTED",
        hedge_detail={
            "venue": "BINANCE",
            "instrument": "BTCUSDC",
            "side": "sell",
            "action_cn": "保持",
            "hedge_policy": "V32",
            "policy_state": "HARD",
            "policy_reason": "HARD_TRIGGER",
            "policy_cross_bps": 30,
            "episode_cost_bps": 12.3,
            "policy_warnings": ["EPISODE_COST_ALERT"],
        },
        take_profit_detail={"status": "未达标", "ratio": 0.2, "target_ratio": 0.8},
        ledger_detail={"reconciled": True, "recovery_state": "OK", "active_orders": []},
    )

    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    hedge_rows = {r[0]: r[1:] for r in next(t for t in tables if t["title"] == "风险与对冲")["rows"]}
    cost_text = " ".join(" ".join(str(x) for x in row)
                         for key, row in hedge_rows.items()
                         if key in ("控制器门控", "成本字段", "成本观测"))

    assert "reserved_not_computed" in cost_text
    assert "12.3" in cost_text
    assert "cost_bps" not in cost_text


def test_console_kill_hint_overrides():
    ctx = _ctx(); ctx.update(kill_new_risk=True, console_phase="POSITION_MANAGE")
    assert "无需交互" in D.disp_operation_hint(ctx)


def test_position_manage_hides_runtime_interaction_and_plan_empty_fields():
    ctx = _ctx()
    ctx.update(
        console_phase="POSITION_MANAGE",
        pending_candidates=[{"id": 1, "summary": "SHOULD_HIDE", "confirm_code": "ABCD"}],
        precommit={"passed": False, "failed": ["SHOULD_HIDE"]},
        display_candidates_count=3,
        lockable_candidates_count=2,
        position_detail={"lifecycle": "已保护·卖方持仓", "combo_unrealized_pnl_usd": 1.23,
                         "hedge_pnl_state": "对冲未启用"},
        take_profit_detail={"status": "未达标", "ratio": 0.2, "target_ratio": 0.8},
        hedge_detail={"action_cn": "保持", "touch_probability_now": 0.3},
        ledger_detail={"reconciled": True, "recovery_state": "OK"},
    )

    tables = _tables_from_panel(D.disp_status_panel(ctx, "测试"))
    console_rows = {r[0]: r[1] for r in tables[0]["rows"]}
    assert "操作提示" in console_rows and "无需交互" in console_rows["操作提示"]
    rendered = json.dumps(tables, ensure_ascii=False)
    for forbidden in ("授权码", "风险退出码", "点【授权", "点【风险退出", "点【拒绝】",
                      "点【急停】", "点【恢复】", "确认码", "待批", "候选展示", "预提交"):
        assert forbidden not in rendered


def test_position_manage_exit_campaign_state_is_chinese_first():
    ctx = _ctx()
    ctx.update(
        console_phase="POSITION_MANAGE",
        state="SHORT_FLAT_LONG_RESIDUAL",
        exit_campaign_state="WORKING_LONG",
        position_detail={
            "lifecycle": "短腿已归零·回收保护腿中",
            "short_instrument": "BTC-29JUN26-60000-P",
            "long_instrument": "BTC-29JUN26-57500-P",
            "remaining_short_qty": 0.0,
            "long_remaining_qty": 0.1,
            "combo_unrealized_pnl_usd": None,
            "pnl_data_gap": "数据缺口",
        },
        take_profit_detail={"status": "未达标", "ratio": 0.2, "target_ratio": 0.8},
        hedge_detail={"action_cn": "保持", "touch_probability_now": 0.3},
        ledger_detail={"reconciled": True, "recovery_state": "OK", "active_orders": []},
    )

    panel = D.disp_status_panel(ctx, "测试")

    assert "WORKING_LONG" not in panel
    assert "回收保护腿" in panel


def test_long_recovery_hint_does_not_expose_raw_exit_state():
    hint = D.disp_operation_hint({"console_phase": "LONG_RECOVERY"})

    assert "LONG_RESIDUAL_ONLY" not in hint
    assert "保护腿残留" in hint


def test_console_manual_gate_hint():
    ctx = _ctx(); ctx.update(manual_verdict={"availability": "MANUAL_GATE",
                                             "block_new_opens": False})
    assert "人工审计门模式" in D.disp_operation_hint(ctx)
