# -*- coding: utf-8 -*-
"""
主编排 main()（FMZ 入口）。Human Audit Gate 版本只接收本地人工审计参数。

run_cycle() 主链：
  人工审计门有效 → 枚举同期垂直候选 → S:PM/执行可行性/VRP/预算过滤 →
  生成短确认码 → 人工输入确认码后进入预提交与开仓活动。
  持仓存在时直接进入持仓管理，不依赖外部信号层。

约定：本项目内一律用「裸名 + 模块前缀」，合成单文件后位于同一命名空间，bundle 仅剥离项目内 import。
"""

import json
import time
import urllib.request

from config import *
from fmz_shim import _G, Log, LogStatus, Sleep, GetCommand
from gates import (gate_summary, gate_decision, ACTION_ENTRY, ACTION_HEDGE_OPEN,
                  ACTION_HEDGE_REDUCE, ACTION_EXIT)
from cmd_router import route_command, cmd_ledger_record
from manual_context import (build_manual_context, validate_manual_context,
                            manual_config_signature)
from recommend import (build_recommendation_library, resolve_confirm_code,
                       precommit_recheck, evaluate_precommit_checks,
                       manual_context_hash)
from position import (build_vertical_entry_snapshot, reference_profit_capture_ratio,
                      take_profit_qualified, short_buyback_budget, short_buyback_price_cap,
                      exit_campaign_decision, EXIT_PAUSED_BUDGET, EXIT_PAUSED_DATA,
                      EXIT_WORKING_SHORT, EXIT_WORKING_LONG,
                      entry_campaign_decision, ENTRY_ABANDONED, ENTRY_WORKING,
                      position_reconcile, protection_recovery_decision)
from hedge import (hedge_target_contracts, hedge_target_position, hedge_order_action, hedge_orphan,
                  hedge_side, hedge_venue_config, HEDGE_INSTRUMENT,
                  structure_net_delta, hedge_direction_consistent, option_net_delta,
                  settlement_guard, hedge_gamma_fraction,
                  hedge_rebalance_deadband, hedge_target_ratio_for_soft)
from binance_io import (bnc_get_position_btc, bnc_get_position_snapshot,
                        bnc_submit_hedge_order, bnc_get_hedge_order,
                        bnc_cancel_hedge_order)
from deribit_io import *
from leg_selection import *
from spm_sim import *
from accounting import *
from plans import *
from ledger import *
from execution import *
from display import *
from hedge_risk import (build_entry_risk_anchor, build_hedge_trigger_policy,
                       evaluate_position_risk, estimate_touch_probability,
                       STATE_EXIT_PREFERRED, STATE_HEDGE_READY)
from risk_controls import (evaluate_portfolio_budget, evaluate_projected_budget,
                          unified_action_arbiter)
from execution_feasibility import (evaluate_execution_feasibility,
                                   feasibility_penalty)

_MENU_KEY = "spm_plan_menu_v1"
_MENU_META_KEY = "spm_plan_menu_meta_v1"
_MANUAL_CONTEXT_KEY = "spm_manual_context_v1"
_LAST_COMMAND_KEY = "spm_last_command_v1"
_LAST = {"plan_ms": 0}
# 选用方案明细锁定：启动时锁定一个方案的编号，之后不随方案库刷新而改变（重启复位）
_LOCKED = {"detail_id": None}
_HEDGE_POLICY_STATE_KEY_V313 = "spm_hedge_policy_v313_state"
_HEDGE_POLICY_STATE_KEY = "spm_hedge_policy_v32_state"
MANUAL_GATE_ISOLATION_TESTS_PASSED = True


def _now_ms():
    return int(time.time() * 1000)


def _spot_price():
    if UNDERLYING_REF_PRICE:
        return UNDERLYING_REF_PRICE
    return dbt_index_price(SETTLEMENT_CURRENCY)


def _delta_lookup():
    cache = {}

    def fn(inst):
        if inst not in cache:
            t = dbt_ticker(inst) or {}
            cache[inst] = (t.get("greeks") or {}).get("delta")
        return cache[inst]
    return fn


def _quote_cache():
    cache = {}

    def fn(inst):
        if inst not in cache:
            q = exec_quote(inst)
            if q is not None:
                cache[inst] = q
            return q
        return cache[inst]
    return fn


def _num_or_none(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def fetch_gex_vrp_context(direction_bias, base_url=None, api_key=None, timeout=None):
    """Fetch lightweight IV/RV rank context. This is a data-validity check only."""
    try:
        base = (base_url or GEX_CONTEXT_API_BASE).rstrip("/")
        key = api_key if api_key is not None else GEX_CONTEXT_API_KEY
        req = urllib.request.Request(base + "/v1/info")
        if key:
            req.add_header("Authorization", "Bearer " + str(key))
        with urllib.request.urlopen(req, timeout=timeout or GEX_CONTEXT_TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("stale"):
            return {"valid": False, "status": "VRP_CONTEXT_STALE", "market_context": None,
                    "raw": payload}
        if payload.get("availability") not in (None, "ready"):
            return {"valid": False, "status": "VRP_CONTEXT_UNAVAILABLE", "market_context": None,
                    "raw": payload}
        if payload.get("missing_fields"):
            return {"valid": False, "status": "VRP_CONTEXT_MISSING_FIELDS",
                    "market_context": None, "raw": payload}
        ratio = _num_or_none(((payload.get("volatility") or {}).get("iv_rv_ratio")))
        metric = (((payload.get("rank") or {}).get("metrics") or {})
                  .get("volatility.iv_rv_ratio") or {})
        rank_pct = _num_or_none(metric.get("rank_pct"))
        if rank_pct is None and _num_or_none(metric.get("percentile")) is not None:
            rank_pct = metric.get("percentile") * 100.0
        if ratio is None or rank_pct is None:
            return {"valid": False, "status": "VRP_CONTEXT_INVALID", "market_context": None,
                    "raw": payload}
        mc = {
            "source": "GEX_MONITOR_IV_RV_RANK",
            "side": direction_bias,
            "iv_rv_ratio": ratio,
            "iv_rv_rank_pct": rank_pct,
            "sample_count": metric.get("sample_count"),
            "quality": metric.get("quality"),
            "asset": payload.get("asset"),
            "fetched_at": payload.get("fetched_at"),
        }
        return {"valid": True, "status": "VRP_CONTEXT_VALID", "market_context": mc,
                "raw": payload}
    except Exception as exc:
        return {"valid": False, "status": "VRP_CONTEXT_API_ERROR:%s" % exc,
                "market_context": None}


def _is_gex_vrp_context(mc):
    return (mc or {}).get("source") == "GEX_MONITOR_IV_RV_RANK"


def _first_in_width(prots, width_range=None):
    lo, hi = width_range or PROTECTION_WIDTH_RANGE
    for p in prots:
        if lo <= p.get("_width", 1e18) <= hi:
            return p
    return None


def _in_width(prots, width_range=None):
    lo, hi = width_range or PROTECTION_WIDTH_RANGE
    return [p for p in (prots or []) if lo <= p.get("_width", 1e18) <= hi]


def _is_endgame_dte(dte_h, target_dte_h):
    if not isinstance(dte_h, (int, float)) or isinstance(dte_h, bool):
        return False
    target = target_dte_h if isinstance(target_dte_h, (int, float)) else TARGET_DTE_HOURS
    threshold = min(float(target), float(ENDGAME_DTE_HOURS))
    return dte_h <= threshold + 1e-9


def _width_range_for_dte(width_range, dte_h, target_dte_h):
    lo, hi = width_range or PROTECTION_WIDTH_RANGE
    if _is_endgame_dte(dte_h, target_dte_h):
        lo = min(lo, ENDGAME_PROTECTION_WIDTH_MIN)
    return lo, hi


def _protection_choice_limit_for_dte(dte_h, target_dte_h):
    return ENDGAME_PROTECTION_CHOICES_PER_SHORT if _is_endgame_dte(dte_h, target_dte_h) else 1


def _execution_feasibility_cfg():
    return {"max_short_spread": MAX_SPREAD_RATIO,
            "max_protection_spread": MAX_SPREAD_RATIO,
            "protection_low_premium_max": PROTECTION_LOW_PREMIUM_MAX,
            "protection_abs_spread_max": PROTECTION_ABS_SPREAD_MAX,
            "min_retention": 0.25,
            "retention_bad": 0.25,
            "min_net_credit": ENTRY_MIN_NET_CREDIT}


def _attach_execution_feasibility(plan, sq, pq):
    ef = evaluate_execution_feasibility({
        "short_quote": sq, "protection_quote": pq,
        "amount": plan.get("amount") or ORDER_AMOUNT,
        "fee_estimate": plan.get("entry_fee") or 0.0,
        "credit_floor": ENTRY_MIN_NET_CREDIT,
        "max_tick_steps": ENTRY_MAX_TICK_STEPS,
    }, _execution_feasibility_cfg())
    plan["execution_feasibility"] = ef
    plan["execution_feasibility_grade"] = ef.get("grade")
    plan["execution_feasibility_score"] = ef.get("score")
    plan["execution_feasibility_score_norm"] = ef.get("score_norm")
    plan["execution_feasibility_penalty"] = feasibility_penalty(ef.get("score_norm"))
    plan["execution_feasibility_warnings"] = ef.get("warnings") or []
    if not ef.get("hard_gate_passed"):
        plan["qualified"] = False
        plan["reject_reason"] = "执行可行性:" + ",".join(ef.get("hard_failures") or [])
    return plan


# ---------- 计划轮：方案库构建 ----------

def _build_menu(now_ms, spot, manual_context=None, _external_unused=None):
    """枚举同期垂直→初筛→top-K 跑 S:PM→排序。返回 (menu, pm_ok, model, reason, diag)。
    diag = 枚举漏斗计数，用于看清是哪个门控在生效（无候选时尤其有用）。"""
    if isinstance(manual_context, str):
        manual_context = {"direction_bias": manual_context}
    manual_context = manual_context or {}
    scope = manual_context.get("planning_scope") or {}
    target_dte = scope.get("target_dte_hours", TARGET_DTE_HOURS)
    dmin = scope.get("short_delta_min", SHORT_DELTA_RANGE[0])
    dmax = scope.get("short_delta_max", SHORT_DELTA_RANGE[1])
    width_range = (scope.get("protection_width_min", PROTECTION_WIDTH_RANGE[0]),
                   scope.get("protection_width_max", PROTECTION_WIDTH_RANGE[1]))
    amount = scope.get("amount", ORDER_AMOUNT)
    want_call = legsel_is_call_bias(manual_context.get("direction_bias") or DIRECTION_BIAS)
    delta_fn, quote_fn = _delta_lookup(), _quote_cache()
    diag = {"短腿扫描": 0, "delta区间外": 0, "无报价/无买盘": 0, "权利金过薄": 0,
            "价差过宽": 0, "无合格保护腿(腿宽内)": 0, "执行不可行": 0,
            "生成候选": 0, "进入菜单": 0, "合格": 0}
    instruments = dbt_get_instruments(SETTLEMENT_CURRENCY, "option")
    if not instruments:
        return [], False, None, "NO_INSTRUMENTS", diag
    short_exps = legsel_target_expiries(instruments, target_dte, now_ms, want_call)
    if not short_exps:
        return [], False, None, "NO_TARGET_EXPIRY", diag
    expiry_roles = {}
    for i, exp in enumerate(short_exps.keys()):
        expiry_roles[exp] = "TARGET_24H" if i == 0 else "NEXT_EXPIRY"
    pm_ok, model = spm_account_is_portfolio_margin(dbt_account_summary(SETTLEMENT_CURRENCY))
    pref = (dmin + dmax) / 2.0

    prelim = []
    for s_exp, s_insts in short_exps.items():
        s_dte_h = legsel_dte_hours(s_exp, now_ms)
        for short in legsel_short_enriched(s_insts, spot, want_call, delta_fn):
            diag["短腿扫描"] += 1
            if not (dmin <= abs(short["_delta"]) <= dmax):
                diag["delta区间外"] += 1
                continue
            sq = quote_fn(short["instrument_name"])
            if not sq or sq.get("best_bid") in (None, 0) or sq.get("mark") is None:
                diag["无报价/无买盘"] += 1
                continue
            if sq["mark"] < THIN_SHORT_PREMIUM_WARN:
                diag["权利金过薄"] += 1
            ssr = exec_spread_ratio(sq)
            if ssr is not None and ssr > MAX_SPREAD_RATIO:
                diag["价差过宽"] += 1
                continue
            # 同期垂直：保护腿取同到期、更价外、腿宽达标者；长腿是定额风险封顶，
            # 便宜的 OTM 长腿正是所需 → **不套用过度虚值过滤**
            active_width_range = _width_range_for_dte(width_range, s_dte_h, target_dte)
            prot_choices = _in_width(legsel_protection_candidates(
                s_insts, short["strike"], want_call, active_width_range,
                None, 0.0), active_width_range)
            prot_choices = prot_choices[:_protection_choice_limit_for_dte(s_dte_h, target_dte)]
            if not prot_choices:
                diag["无合格保护腿(腿宽内)"] += 1
                continue
            for vprot in prot_choices:
                pq = quote_fn(vprot["instrument_name"])
                if not pq or pq.get("mark") is None:
                    continue
                c = plan_assemble(amount, spot, MIN_MARGIN_RELIEF_RATIO, pref,
                                  want_call, short, sq, vprot, pq,
                                  None, pm_ok, model, s_dte_h, s_dte_h)
                c["expiry_role"] = expiry_roles.get(s_exp)
                _attach_execution_feasibility(c, sq, pq)
                if (c.get("execution_feasibility") or {}).get("hard_gate_passed") is False:
                    diag["执行不可行"] += 1
                    continue
                c["_re"] = {"short": short, "sq": sq, "prot": vprot, "pq": pq,
                            "s_dte": s_dte_h, "p_dte": s_dte_h}
                prelim.append(c)
                diag["生成候选"] += 1

    if not prelim:
        return [], pm_ok, model, ("NO_EXECUTION_FEASIBLE" if diag["执行不可行"] else "NO_CANDIDATE"), diag
    prelim.sort(key=lambda c: plan_prelim_score(c, PLAN_WEIGHTS), reverse=True)
    topk = prelim[:max(MENU_SIZE * 2, MENU_SIZE)]

    final = []
    for c in topk:                                    # 仅对 top-K 跑 S:PM（控制 API 调用）
        re = c["_re"]
        spm = spm_simulate_structure(SETTLEMENT_CURRENCY, re["short"]["instrument_name"],
                                     re["prot"]["instrument_name"], amount)
        plan = plan_assemble(
            amount, spot, MIN_MARGIN_RELIEF_RATIO, pref,
            want_call, re["short"], re["sq"], re["prot"], re["pq"], spm, pm_ok, model,
            re["s_dte"], re["p_dte"])
        plan["expiry_role"] = expiry_roles.get(plan.get("short_expiry"))
        plan = _attach_execution_feasibility(plan, re["sq"], re["pq"])
        if (plan.get("execution_feasibility") or {}).get("hard_gate_passed") is False:
            diag["执行不可行"] += 1
            continue
        final.append(plan)
    if not final:
        return [], pm_ok, model, "NO_EXECUTION_FEASIBLE", diag
    menu = plan_rank(final, PLAN_WEIGHTS, MENU_SIZE)
    diag["进入菜单"] = len(menu)
    diag["合格"] = sum(1 for c in menu if c.get("qualified"))
    return menu, pm_ok, model, "OK", diag


# ---------- ctx 组装 ----------

def _ctx_base(state, spot, reason=None):
    profile = normalize_run_profile(RUN_PROFILE)
    snap = {
        "version": STRATEGY_VERSION,
        "run_profile": profile,
        "live_checklist_missing": live_checklist_missing(
            profile, DRY_RUN_PASSED, ALLOW_ENTRY_TRADING, ALLOW_EXIT_TRADING,
            RISK_EXIT_MAX_SPEND),
        "currency": SETTLEMENT_CURRENCY,
        "direction_bias": DIRECTION_BIAS,
        "manual_gate_state": ("PLANNING_ALLOWED" if MANUAL_PLANNING_ALLOWED
                              else "WAIT_MANUAL_AUDIT_GATE"),
        "target_dte_hours": TARGET_DTE_HOURS,
        "approval_ttl_ms": APPROVAL_TTL_MS,
        "state": state,
        "max_chase_steps": MAX_CHASE_STEPS, "min_required_ratio": MIN_MARGIN_RELIEF_RATIO,
        "reason": reason, "spot": spot, "amount": ORDER_AMOUNT,
        "selected_plan": None, "protection_mode": None,
        "startup_self_check": _G(_SELF_CHECK_KEY),
    }
    return snap


def _flat_plan_fields(p):
    return dict(
        short_instrument=p["short_instrument"], short_strike=p["short_strike"],
        short_dte_hours=p["short_dte_hours"], short_mark=p["short_mark"],
        short_bid=p["short_bid"], short_ask=p["short_ask"], short_tick=p["short_tick"],
        short_delta=p["short_delta"],
        protection_instrument=p["protection_instrument"], protection_strike=p["protection_strike"],
        protection_dte_days=p["protection_dte_days"], protection_mark=p["protection_mark"],
        protection_bid=p["protection_bid"], protection_ask=p["protection_ask"],
        protection_tick=p["protection_tick"], protection_delta=p["protection_delta"],
        im_short_only=p["im_short_only"], im_with_protection=p["im_with_protection"],
        margin_relief_abs=p["margin_relief_abs"], margin_relief_ratio=p["margin_relief_ratio"],
        pm_accepted=p["pm_ok"], account_margin_model=p["account_model"],
        short_premium_income=p["premium_income"], estimated_entry_fee=p["entry_fee"],
        estimated_spread_cost=p["spread_cost"], protection_entry_cost=p["protection_premium"],
        full_burn_cost=p["full_burn"],
        win_rate=p["win_rate"], net_credit=p["net_credit_effective"],
        net_credit_single=p["net_credit_single"], max_loss=p["max_loss"], rr=p["rr"],
        ev=p.get("ev"),
        covered_cycles=p["covered_cycles"], residual_value=p["residual_value"],
        amortized_cost_per_cycle=p["amortized_cost_per_cycle"],
        protection_mode=p["mode"], protection_mode_cn=p["mode_cn"], plan_tags=p.get("tags"),
        selected_id=p.get("id"),
        short_expiry_label=p.get("short_expiry_label"),
        protection_expiry_label=p.get("protection_expiry_label"),
        protection_dte_hours=p.get("protection_dte_hours"),
        expiry_role=p.get("expiry_role"),
        breakeven=p.get("breakeven"), credit_on_margin=p.get("credit_on_margin"),
        credit_on_margin_per_24h=p.get("credit_on_margin_per_24h"),
        execution_feasibility_grade=p.get("execution_feasibility_grade"),
        execution_feasibility_score=p.get("execution_feasibility_score"),
        execution_feasibility_score_norm=p.get("execution_feasibility_score_norm"),
        execution_feasibility_warnings=p.get("execution_feasibility_warnings"),
    )


def _ctx_with_menu(state, spot, reason, menu, selected_no, detail_plan):
    ctx = _ctx_base(state, spot, reason)
    ctx["menu"] = menu
    ctx["selected_plan"] = selected_no
    if detail_plan:
        ctx.update(_flat_plan_fields(detail_plan))
    return ctx


def _store_plan_trace(now_ms, reason=None, diag=None, menu_count=0, lockable_count=0,
                      vrp_blocked=0, not_lockable_reason=None):
    _G(_PLAN_TRACE_KEY, {
        "ts": now_ms,
        "reason": reason,
        "diag": diag or {},
        "menu_count": menu_count or 0,
        "lockable_count": lockable_count or 0,
        "vrp_blocked": vrp_blocked or 0,
        "not_lockable_reason": not_lockable_reason,
    })


def _stable_menu_meta_valid(meta, manual_context):
    """固定备选库是否仍属于当前人工上下文。"""
    if not meta or not manual_context:
        return False
    if meta.get("manual_context_id") != manual_context.get("context_id"):
        return False
    if meta.get("manual_context_hash") != manual_context_hash(manual_context):
        return False
    if meta.get("config_signature") != manual_context.get("config_signature"):
        return False
    if meta.get("strategy_version") != STRATEGY_VERSION:
        return False
    return True


def _load_stable_menu(manual_context):
    menu = list(_G(_MENU_KEY) or [])
    meta = _G(_MENU_META_KEY) or {}
    if menu and _stable_menu_meta_valid(meta, manual_context):
        return menu, meta
    if menu or meta:
        _G(_MENU_KEY, None)
        _G(_MENU_META_KEY, None)
    return [], {}


def _store_stable_menu(menu, manual_context, now_ms, reason, diag, lockable_count,
                       vrp_blocked, not_lockable_reason):
    menu = list(menu or [])
    meta = {
        "ts": now_ms,
        "manual_context_id": (manual_context or {}).get("context_id"),
        "manual_context_hash": manual_context_hash(manual_context) if manual_context else None,
        "config_signature": (manual_context or {}).get("config_signature"),
        "strategy_version": STRATEGY_VERSION,
        "reason": reason,
        "diag": diag or {},
        "menu_count": len(menu),
        "lockable_count": lockable_count or 0,
        "vrp_blocked": vrp_blocked or 0,
        "not_lockable_reason": not_lockable_reason,
    }
    _G(_MENU_KEY, menu)
    _G(_MENU_META_KEY, meta)
    return meta


def _annotate_menu_lock_state(menu, pending=None, not_lockable_reason=None):
    rows = [dict(p) for p in (menu or [])]
    codes = dict((c.get("id"), c.get("confirm_code")) for c in (pending or []))
    for p in rows:
        pid = p.get("id")
        if pid in codes and codes[pid]:
            p["_confirm_code"] = codes[pid]
            p["_not_lockable_reason"] = None
        elif not_lockable_reason:
            p["_confirm_code"] = None
            p["_not_lockable_reason"] = not_lockable_reason
    return rows


def _locked_display_candidate(locked, menu):
    if not locked:
        return None
    plan_id = locked.get("plan_id")
    short_i = locked.get("short_instrument")
    long_i = locked.get("long_instrument")
    for p in (menu or []):
        if p.get("id") == plan_id or (
                p.get("short_instrument") == short_i
                and p.get("protection_instrument") == long_i):
            row = dict(p)
            row["_confirm_code"] = locked.get("confirm_code")
            row["_locked"] = True
            return row
    return None


def _fmt_event_value(v, digits=6):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return ("%%.%df" % digits) % v
    return "-"


def _position_event_log_summary(ctx, note):
    if not isinstance(ctx, dict) or ctx.get("console_phase") != "POSITION_MANAGE":
        return None
    step = ctx.get("hedge_step")
    if isinstance(step, dict) and step:
        return ("%s｜对冲订单｜方向=%s 数量=%s 成交=%s 均价=%s 原因=%s" %
                (note or "manual-gate", step.get("side") or "-",
                 _fmt_event_value(step.get("amount")),
                 _fmt_event_value(step.get("filled")),
                 _fmt_event_value(step.get("avg_price"), 2),
                 step.get("reason") or "-"))
    for key, label in (("hedge_data_gap", "对冲数据缺口"),
                       ("order_state_gap", "订单状态缺口")):
        if ctx.get(key):
            return "%s｜%s｜数据缺口:%s" % (note or "manual-gate", label, ctx.get(key))
    risk_detail = ctx.get("risk_exit_detail") or {}
    if risk_detail.get("risk_exit_active") and risk_detail.get("reason"):
        return "%s｜风险退出受限｜原因=%s" % (note or "manual-gate", risk_detail.get("reason"))
    recovery_state = ctx.get("recovery_state")
    if recovery_state and recovery_state != "OK":
        return "%s｜恢复/对账异常｜%s" % (note or "manual-gate", recovery_state)
    return None


def _emit(ctx, note=""):
    LogStatus(disp_status_panel(ctx, note))
    position_mode = (ctx or {}).get("console_phase") == "POSITION_MANAGE"
    event_summary = _position_event_log_summary(ctx, note) if position_mode else None
    if position_mode and event_summary is None:
        return
    summary = event_summary or disp_log_summary(ctx, note)
    now_ms = ctx.get("now_ms") if isinstance(ctx, dict) else None
    if not isinstance(now_ms, (int, float)) or isinstance(now_ms, bool):
        now_ms = _now_ms()
    last = _G(_LAST_LOG_SUMMARY_KEY)
    last_ts = _G(_LAST_LOG_SUMMARY_TS_KEY) or 0
    heartbeat_due = bool(position_mode and summary == last
                         and now_ms - (last_ts or 0) >= POSITION_LOG_HEARTBEAT_MS)
    if summary != last or heartbeat_due:
        Log(summary)
        _G(_LAST_LOG_SUMMARY_KEY, summary)
        _G(_LAST_LOG_SUMMARY_TS_KEY, now_ms)


def _check_result(ok, reason=None, detail=None):
    out = {"ok": bool(ok)}
    if reason:
        out["reason"] = str(reason)
    if detail is not None:
        out["detail"] = detail
    return out


def _startup_self_check(currency):
    """启动后一轮只读自检：配置、Deribit 行情/账户、GEX 数据、Binance 对冲读仓。"""
    checks = {}
    errs = validate_config()
    checks["config"] = _check_result(not errs, ";".join(errs) if errs else None)
    try:
        px = dbt_index_price(currency)
        ok = isinstance(px, (int, float)) and not isinstance(px, bool) and px > 0
        checks["deribit_index"] = _check_result(ok, None if ok else "NO_INDEX_PRICE", px)
    except Exception as e:
        checks["deribit_index"] = _check_result(False, e)
    try:
        instruments = dbt_get_instruments(currency, "option") or []
        checks["deribit_options"] = _check_result(
            bool(instruments), None if instruments else "NO_OPTIONS", len(instruments))
    except Exception as e:
        checks["deribit_options"] = _check_result(False, e)
    try:
        account = dbt_account_summary(currency) or {}
        checks["deribit_account"] = _check_result(
            bool(account), None if account else "NO_ACCOUNT_SUMMARY",
            account.get("margin_model") or account.get("account_type"))
    except Exception as e:
        checks["deribit_account"] = _check_result(False, e)
    try:
        verdict = fetch_gex_vrp_context(DIRECTION_BIAS)
        checks["gex_context"] = _check_result(
            bool(verdict.get("valid")), verdict.get("status"),
            bool(verdict.get("market_context")))
    except Exception as e:
        checks["gex_context"] = _check_result(False, e)
    if HEDGE_VENUE == "BINANCE":
        try:
            qty = bnc_get_position_btc(HEDGE_BINANCE_INSTRUMENT)
            checks["binance_hedge_position"] = _check_result(
                qty is not None, None if qty is not None else "HEDGE_POSITION_QUERY_FAILED", qty)
        except Exception as e:
            checks["binance_hedge_position"] = _check_result(False, e)
    else:
        checks["binance_hedge_position"] = _check_result(True, "SKIPPED_DERIBIT_HEDGE")
    result = {
        "overall": "OK" if all(v.get("ok") for v in checks.values()) else "WARN",
        "checks": checks,
        "checked_at_ms": _now_ms(),
    }
    _G(_SELF_CHECK_KEY, result)
    return result


# ---------- 计划轮 ----------

def integrated_plan_preview(spot, market_context=None, portfolio_state=None):
    """整合执行流的 PLAN 段（执行会话式）：真实 _build_menu → VRP 双门过滤(给 market_context 时)
    → 组合硬预算(给 portfolio_state 时) → 返回可锁定方案 + 各域裁决。

    main() 在拿到实时 IV/RV(market_context) 与组合状态后调用本函数；选中方案的会话锁定/授权
    plan_hash + TTL 与 FMZ 命令栏交互由人工审计门主链接管。
    边界：VRP/预算**只过滤**，不进 PLAN_WEIGHTS、不判方向、不打开交易门。"""
    now_ms = _now_ms()
    menu, pm_ok, model, reason, diag = _build_menu(now_ms, spot)
    out = {"reason": reason, "menu": menu, "enum_diag": diag, "pm_ok": pm_ok,
           "vrp_passed": None, "vrp_blocked": None, "portfolio_budget": None,
           "lockable": []}
    if reason != "OK" or not menu:
        out["lockable"] = []
        return out
    # VRP_CONTEXT: GEX path is validity-only; legacy price gate stays source-test only.
    if market_context:
        mc = _plan_vrp_context({"market_context": market_context}, DIRECTION_BIAS)
        if mc:
            out["vrp_passed"] = list(menu)
            out["vrp_blocked"] = []
            out["lockable"] = list(menu)
        else:
            out["vrp_passed"] = []
            out["vrp_blocked"] = [{"id": p.get("id"), "reason_codes": ["VRP_CONTEXT_UNSUPPORTED"]}
                                  for p in menu]
            out["lockable"] = []
    else:
        out["not_lockable_reason"] = "VRP_CONTEXT_MISSING"
    # 组合硬预算（缺口2，入场前额外 AND 门；占位安全：超即 size=0 → 无可锁定）
    if portfolio_state:
        budget = evaluate_portfolio_budget(
            portfolio_state.get("current", {}), portfolio_state.get("limits", {}),
            portfolio_state.get("proposed_size", ORDER_AMOUNT))
        out["portfolio_budget"] = budget
        if budget["decision"] == "BLOCK":
            out["lockable"] = []
    return out


def _plan_vrp_context(verdict, direction_bias):
    mc = dict((verdict or {}).get("market_context") or {})
    if not mc:
        return None
    if not mc.get("side"):
        mc["side"] = direction_bias
    if _is_gex_vrp_context(mc):
        return mc if (mc.get("iv_rv_ratio") is not None
                      and mc.get("iv_rv_rank_pct") is not None) else None
    return None


def _filter_menu_by_vrp(menu, verdict, direction_bias, diag=None):
    mc = _plan_vrp_context(verdict, direction_bias)
    if not (menu and mc):
        return menu, 0
    if _is_gex_vrp_context(mc):
        if diag is not None:
            diag["VRP阻断"] = 0
        return menu, 0
    if diag is not None:
        diag["VRP阻断"] = len(menu)
    return [], len(menu)


# ---------- 下单轮 ----------

# ========== E2：单一持续主链 run_cycle（取代 PLAN/ORDER 双脚本；main() 于 E2.3 切换）==========

_SESSION_KEY = "spm_session_id_v1"
_REFRESH_KEY = "spm_refresh_seq_v1"
_LIB_KEY = "spm_reco_lib_v1"
_LOCKED_KEY = "spm_locked_plan_v1"
_RUNTIME_KILL_KEY = "spm_runtime_kill_v1"
_LIB_BUILD_TS_KEY = "spm_lib_build_ts_v1"
_PLAN_TRACE_KEY = "spm_plan_trace_v1"
_LAST_LOG_SUMMARY_KEY = "spm_last_log_summary_v1"
_LAST_LOG_SUMMARY_TS_KEY = "spm_last_log_summary_ts_v1"
_SELF_CHECK_KEY = "spm_startup_self_check_v1"
POSITION_LOG_HEARTBEAT_MS = 10 * 60 * 1000


def _session_id():
    sid = _G(_SESSION_KEY)
    if not sid:
        sid = "sess-%d" % _now_ms()
        _G(_SESSION_KEY, sid)
    return sid


def _refresh_seq():
    return int(_G(_REFRESH_KEY) or 0)


def _bump_refresh_seq():
    n = _refresh_seq() + 1
    _G(_REFRESH_KEY, n)
    return n


def _effective_kill():
    """只读取配置层 KILL_NEW_RISK；运行时不再提供急停交互命令。"""
    return bool(KILL_NEW_RISK)


def _effective_gate_cfg():
    return effective_trading_gates(
        RUN_PROFILE, ALLOW_ENTRY_TRADING, ALLOW_EXIT_TRADING, ALLOW_HEDGE_TRADING)


def _gate_summary_now():
    g = _effective_gate_cfg()
    return gate_summary(g["allow_entry"], g["allow_exit"], g["allow_hedge"],
                        _effective_kill(), EMERGENCY_REDUCE_ONLY)


def _manual_risk_policy():
    g = _effective_gate_cfg()
    return {
        "max_loss_per_trade": PORTFOLIO_LIMITS.get("max_spread_loss_per_trade"),
        "min_net_credit": ENTRY_MIN_NET_CREDIT,
        "allow_hedge_open": bool(g["allow_hedge"]),
        "allow_hedge_reduce": True,
        "allow_auto_take_profit": bool(g["allow_exit"]),
        "allow_auto_risk_exit": bool(g["allow_exit"]),
    }


def _manual_context_signature():
    return manual_config_signature(
        MANUAL_PLANNING_ALLOWED, DIRECTION_BIAS, TARGET_DTE_HOURS, SHORT_DELTA_RANGE,
        PROTECTION_WIDTH_RANGE, ORDER_AMOUNT, APPROVAL_TTL_MS, _manual_risk_policy())


def _refresh_vrp_context(ctx, now_ms):
    if not ctx:
        return ctx
    if ctx.get("market_context") and ctx.get("vrp_context_status") != "VRP_CONTEXT_VALID":
        ctx["vrp_context_status"] = "VRP_CONTEXT_VALID"
        ctx["vrp_context_checked_ts_ms"] = now_ms
        return ctx
    last = ctx.get("vrp_context_checked_ts_ms") or 0
    if (ctx.get("vrp_context_status") == "VRP_CONTEXT_VALID"
            and now_ms - last < PLAN_REFRESH_SECONDS * 1000):
        return ctx
    verdict = fetch_gex_vrp_context(ctx.get("direction_bias") or DIRECTION_BIAS)
    ctx["market_context"] = verdict.get("market_context") or {}
    ctx["vrp_context_status"] = verdict.get("status")
    ctx["vrp_context_checked_ts_ms"] = now_ms
    return ctx


def _manual_context_for_cycle(now_ms):
    if not MANUAL_PLANNING_ALLOWED:
        return None
    sig = _manual_context_signature()
    ctx = _G(_MANUAL_CONTEXT_KEY)
    if (not ctx or ctx.get("config_signature") != sig
            or (ctx.get("expires_ts_ms") is not None and ctx.get("expires_ts_ms") <= now_ms)):
        ctx = build_manual_context(
            now_ms, MANUAL_PLANNING_ALLOWED, DIRECTION_BIAS, TARGET_DTE_HOURS,
            SHORT_DELTA_RANGE, PROTECTION_WIDTH_RANGE, ORDER_AMOUNT,
            APPROVAL_TTL_MS, _manual_risk_policy())
        _G(_MANUAL_CONTEXT_KEY, ctx)
    ctx = _refresh_vrp_context(ctx, now_ms)
    _G(_MANUAL_CONTEXT_KEY, ctx)
    return ctx


def _clear_plan_lineage(clear_menu=True):
    _G(_LOCKED_KEY, None)
    _G(_LIB_KEY, None)
    _G(_LIB_BUILD_TS_KEY, 0)
    if clear_menu:
        _G(_MENU_KEY, None)
        _G(_MENU_META_KEY, None)


def _approval_expired(snapshot, now_ms):
    ts = (snapshot or {}).get("locked_ts")
    return (isinstance(ts, (int, float))
            and isinstance(now_ms, (int, float))
            and now_ms - ts >= APPROVAL_TTL_MS)


def _lineage_invalidated(snapshot, manual_context, now_ms=None):
    if not snapshot:
        return None
    if _approval_expired(snapshot, now_ms):
        return "APPROVAL_EXPIRED"
    if not manual_context:
        return "MANUAL_CONTEXT_MISSING"
    if snapshot.get("manual_context_id") != manual_context.get("context_id"):
        return "MANUAL_CONTEXT_CHANGED"
    if snapshot.get("manual_context_hash") != manual_context_hash(manual_context):
        return "MANUAL_CONTEXT_CHANGED"
    if snapshot.get("config_hash") and snapshot.get("config_hash") != manual_context.get("config_signature"):
        return "MANUAL_CONFIG_CHANGED"
    return None


def _apply_manual_context_to_ctx(ctx, manual_context, manual_check):
    ctx["manual_context"] = manual_context
    ctx["manual_context_hash"] = manual_context_hash(manual_context) if manual_context else None
    ctx["manual_gate_status"] = ("MANUAL_CONTEXT_VALID" if (manual_check or {}).get("valid")
                                 else "MANUAL_CONTEXT_INVALID")
    ctx["manual_gate_state"] = ("PLANNING_ALLOWED" if (manual_check or {}).get("valid")
                                else ("WAIT_MANUAL_AUDIT_GATE" if not manual_context
                                      else "MANUAL_CONTEXT_INVALID"))
    ctx["manual_context_errors"] = (manual_check or {}).get("errors") or []
    if manual_context:
        ctx["direction_bias"] = manual_context.get("direction_bias")
    return ctx

def _has_position(state):
    return state in (S_SHORT_ACTIVE_PROTECTED, S_PROTECTION_ACTIVE_NO_SHORT,
                     S_SHORT_FLAT_LONG_RESIDUAL)


def _handle_execute(code, now_ms):
    """硬授权：在当前推荐库按确认码定位冻结快照 → 锁定不可变副本。
    预提交硬门与受控真实开仓由后续每轮 _attempt_commit 评估（见 E3.4）。"""
    lib = _G(_LIB_KEY)
    snap = resolve_confirm_code(lib, code)
    if not snap:
        return "confirm_code_invalid_or_stale"
    locked = dict(snap)
    locked["locked_ts"] = now_ms
    _G(_LOCKED_KEY, locked)
    return "locked"


def _handle_command(ctype, cmd, now_ms):
    if ctype == "EXECUTE":
        return _handle_execute(cmd.get("arg"), now_ms)
    return "ignored_non_execute_command"


def _dispatch_command(raw, meta, now_ms):
    """轮询并分发一条 FMZ 命令；全部入命令账本审计，消费型严格幂等。"""
    res = route_command(raw, meta, now_ms)
    status, cmd = res["status"], res["command"]
    if status == "EMPTY":
        return {"action": None, "status": status}
    if status == "UNKNOWN":
        cmd_ledger_record(cmd, None, "UNKNOWN", "ignored", now_ms)
        _G(_LAST_COMMAND_KEY, {"raw": cmd.get("raw"), "arg": cmd.get("arg"),
                               "type": cmd.get("type"), "status": status,
                               "outcome": "ignored", "ts": now_ms})
        return {"action": "UNKNOWN", "status": status}
    if status == "DUPLICATE":
        cmd_ledger_record(cmd, res["key"], "DUPLICATE", "ignored", now_ms)
        _G(_LAST_COMMAND_KEY, {"raw": cmd.get("raw"), "arg": cmd.get("arg"),
                               "type": cmd.get("type"), "status": status,
                               "outcome": "duplicate_ignored", "key": res.get("key"),
                               "ts": now_ms})
        return {"action": cmd["type"], "status": status, "outcome": "duplicate_ignored"}
    outcome = _handle_command(cmd["type"], cmd, now_ms)
    cmd_ledger_record(cmd, res["key"], "ACCEPTED", outcome, now_ms)
    _G(_LAST_COMMAND_KEY, {"raw": cmd.get("raw"), "arg": cmd.get("arg"),
                           "type": cmd.get("type"), "status": status,
                           "outcome": outcome, "key": res.get("key"), "ts": now_ms})
    return {"action": cmd["type"], "status": status, "outcome": outcome}


_POSITION_KEY = "spm_entry_snapshot_v1"      # 冻结的 VerticalEntrySnapshot


def _current_portfolio():
    """当前组合风险载荷（E3：无并发持仓时为空；E4 接入真实多仓汇总）。"""
    return {"open_positions": 0, "short_gamma": 0.0, "short_vega": 0.0, "margin_used": 0.0}


_KNOWN_ORDER_LABELS = ("entry", "exit", "short", "prot", "hedge", "recover", "risk_exit")


def _label_known(label):
    s = str(label or "")
    return bool(s) and any(s.startswith(p) for p in _KNOWN_ORDER_LABELS)


def _no_unknown_orders(currency, instruments):
    """交易所活动订单中**没有**落在我方合约、且非我方 label 的未知挂单（防双开/与本策略冲突）。
    任一未知挂单 / 查询失败 → False（fail-closed：预提交不过，不真实开仓）。"""
    insts = set(i for i in instruments if i)
    if not insts:
        return False
    try:
        orders = dbt_get_open_orders(currency)
    except Exception:
        return False
    if orders is None:
        return False
    for o in orders:
        if o.get("instrument_name") in insts and not _label_known(o.get("label")):
            return False
    return True


def _order_identity(order):
    if not isinstance(order, dict):
        return None
    return order.get("order_id") or order.get("id") or order.get("Id") or order.get("OrderId")


def _allowed_entry_order_ids(locked):
    entry = (locked or {}).get("entry") or {}
    ids = set()
    prot = entry.get("prot_order") or {}
    oid = _order_identity(prot)
    if oid:
        ids.add(str(oid))
    return ids


def _order_safety_status(currency, instruments, locked=None):
    insts = set(i for i in instruments if i)
    if not insts:
        return {"ok": False, "reason": "NO_INSTRUMENTS"}
    try:
        orders = dbt_get_open_orders(currency)
    except Exception:
        return {"ok": False, "reason": "OPEN_ORDERS_QUERY_FAILED"}
    if orders is None:
        return {"ok": False, "reason": "OPEN_ORDERS_QUERY_FAILED"}
    allowed_entry_ids = _allowed_entry_order_ids(locked)
    for o in orders:
        if (o or {}).get("instrument_name") not in insts:
            continue
        label = str((o or {}).get("label") or "")
        if not _label_known(label):
            return {"ok": False, "reason": "UNKNOWN_ACTIVE_ORDER", "order": o}
        if label.startswith("entry"):
            oid = _order_identity(o)
            if not oid or str(oid) not in allowed_entry_ids:
                return {"ok": False, "reason": "ENTRY_ACTIVE_ORDER_CONFLICT", "order": o}
    return {"ok": True, "reason": None}


def _quote_abs_spread(q):
    bid, ask = (q or {}).get("best_bid"), (q or {}).get("best_ask")
    if not isinstance(bid, (int, float)) or not isinstance(ask, (int, float)):
        return None
    if bid <= 0 or ask <= 0 or ask < bid:
        return None
    return ask - bid


def _protection_spread_ok(q, ratio):
    if ratio is not None and ratio <= MAX_SPREAD_RATIO:
        return True
    abs_spread = _quote_abs_spread(q)
    ask = (q or {}).get("best_ask")
    return (isinstance(abs_spread, (int, float))
            and isinstance(ask, (int, float))
            and ask <= PROTECTION_LOW_PREMIUM_MAX
            and abs_spread <= PROTECTION_ABS_SPREAD_MAX + 1e-12)


def _vrp_recheck_locked(locked, spot, amount, short_quote, protection_quote, manual_context):
    mc = dict((manual_context or {}).get("market_context") or {})
    if not mc:
        return None, None
    if not mc.get("side"):
        mc["side"] = _side_to_direction_bias((locked or {}).get("side"))
    if _is_gex_vrp_context(mc):
        valid = (mc.get("iv_rv_ratio") is not None and mc.get("iv_rv_rank_pct") is not None)
        return valid, {"pass": valid,
                       "status": (manual_context or {}).get("vrp_context_status"),
                       "source": mc.get("source"),
                       "iv_rv_ratio": mc.get("iv_rv_ratio"),
                       "iv_rv_rank_pct": mc.get("iv_rv_rank_pct")}
    return None, {"error": "VRP_CONTEXT_UNSUPPORTED"}


def _build_precommit_live(locked, spot, manual_context, now_ms):
    """预取实时复核数据供 evaluate_precommit_checks。
    VRP 需执行侧 manual_context.market_context；缺失时 vrp_pass=None（fail-closed）。"""
    short_i = locked.get("short_instrument")
    long_i = locked.get("long_instrument")
    amount = locked.get("amount") or ORDER_AMOUNT
    sq, lq = exec_quote(short_i), exec_quote(long_i)
    quotes_fresh = bool(sq and lq and sq.get("mark") is not None and lq.get("mark") is not None
                        and sq.get("best_bid") not in (None, 0) and lq.get("best_ask") not in (None, 0))
    ssr, lsr = exec_spread_ratio(sq), exec_spread_ratio(lq)
    spread_ok = (ssr is not None and ssr <= MAX_SPREAD_RATIO
                 and _protection_spread_ok(lq, lsr))
    net_credit = fee_reserve = None
    if quotes_fresh:
        fee_reserve = (acct_option_fee_ccy(sq["mark"], amount)
                       + acct_option_fee_ccy(lq["mark"], amount))
        net_credit = (sq["mark"] - lq["mark"]) * amount - fee_reserve
    execution_feasibility_live = evaluate_execution_feasibility({
        "short_quote": sq,
        "protection_quote": lq,
        "amount": amount,
        "fee_estimate": fee_reserve or 0.0,
        "credit_floor": ENTRY_MIN_NET_CREDIT,
        "max_tick_steps": ENTRY_MAX_TICK_STEPS,
    }, _execution_feasibility_cfg())
    spm = spm_simulate_structure(SETTLEMENT_CURRENCY, short_i, long_i, amount)
    relief = (spm or {}).get("relief_ratio")
    proposed = {
        "short_gamma": (sq or {}).get("gamma") or 0.0,
        "short_vega": 0.0,                       # vega 待 Greeks 接入（E6/E7）
        "structure_margin": (spm or {}).get("im_with_protection"),
        "max_spread_loss": locked.get("max_loss"),
        "hedge_margin_reserve": 0.0,             # E7 接对冲保证金估算
        "fee_reserve": fee_reserve,
    }
    budget = evaluate_projected_budget(proposed, _current_portfolio(), PORTFOLIO_LIMITS)
    rec = ledger_reconcile(SETTLEMENT_CURRENCY)
    reconciled = (rec.get("actual") == rec.get("expected"))
    manual_check = validate_manual_context(manual_context, now_ms)
    vrp_pass, vrp_gate = _vrp_recheck_locked(locked, spot, amount, sq, lq, manual_context)
    order_safety = _order_safety_status(SETTLEMENT_CURRENCY, [short_i, long_i], locked)
    return {
        "manual_context_valid": manual_check.get("valid"),
        "manual_context_hash": manual_context_hash(manual_context) if manual_context else None,
        "approval_not_expired": not _approval_expired(locked, now_ms),
        "same_expiry": plan_expiry_label(short_i) == plan_expiry_label(long_i),
        "vrp_pass": vrp_pass,
        "vrp_gate": vrp_gate,
        "spm_relief": relief, "min_relief": MIN_MARGIN_RELIEF_RATIO,
        "quotes_fresh": quotes_fresh,
        "net_credit_after_costs": net_credit,
        "projected_budget_decision": budget.get("decision"),
        "ledger_reconciled": reconciled,
        "no_unknown_orders": order_safety.get("ok") is True,  # C3：真实活动订单查询 + 同腿入场残单防重挂
        "order_conflict_reason": order_safety.get("reason"),
        "order_conflict_detail": order_safety.get("order"),
        "spread_ok": spread_ok,
        "spread_detail": {"short_ratio": ssr, "protection_ratio": lsr,
                          "protection_abs_spread": _quote_abs_spread(lq),
                          "protection_low_premium_soft": bool(lsr is not None and lsr > MAX_SPREAD_RATIO
                                                              and _protection_spread_ok(lq, lsr))},
        "execution_feasibility_live": execution_feasibility_live,
        "_budget": budget,
    }


def _side_to_direction_bias(side):
    """持仓 side（'CALL'/'PUT' 或已是 'SHORT_*'）→ hedge_risk 方向偏置（'SHORT_CALL'/'SHORT_PUT'）。"""
    s = str(side or "").upper()
    if s in ("CALL", "SHORT_CALL"):
        return "SHORT_CALL"
    if s in ("PUT", "SHORT_PUT"):
        return "SHORT_PUT"
    return s


def _dte_hours_to(expiry_ts, now_ms):
    """到期剩余小时（毫秒时间戳 → 小时）；无到期 → None。"""
    if not expiry_ts:
        return None
    return (expiry_ts - now_ms) / 3600000.0


def _build_entry_risk_anchor(locked, spot, now_ms):
    """入场冻结风险锚：短腿当前 greeks + 入场行情 → 触界概率基线（供持仓后风险评估）。"""
    sq = exec_quote((locked or {}).get("short_instrument")) or {}
    anchor = build_entry_risk_anchor(
        _side_to_direction_bias((locked or {}).get("side")),
        spot, _dte_hours_to((locked or {}).get("short_expiry"), now_ms),
        sq.get("delta"), sq.get("gamma"), sq.get("mark_iv"),
        (locked or {}).get("breakeven"), "MANUAL_GATE", "UNKNOWN")
    anchor["hedge_trigger_policy"] = build_hedge_trigger_policy(
        anchor.get("entry_touch_probability"), HEDGE_REDUCTION_RATIO)
    return anchor


def _entry_execution_report(prog):
    prog = prog or {}
    fills = list(prog.get("entry_fills") or [])
    total_fee = prog.get("entry_fee_used")
    if total_fee is None:
        total_fee = sum((f.get("fee_used") or f.get("fee_estimate") or 0.0) for f in fills)
    prot_cost = prog.get("prot_cost") or 0.0
    short_credit = prog.get("short_credit") or 0.0
    before_fee = short_credit - prot_cost
    return {
        "fills": fills,
        "fill_count": len(fills),
        "total_fee_estimate": total_fee,
        "total_protection_cost": prot_cost,
        "total_short_credit": short_credit,
        "actual_net_credit_before_fees": before_fee,
        "actual_net_credit_after_fees": before_fee - (total_fee or 0.0),
        "total_mark_slippage": sum((f.get("mark_slippage") or 0.0) for f in fills),
        "total_chase_slippage": sum((f.get("chase_slippage") or 0.0) for f in fills),
        "total_spread_cost_estimate": sum((f.get("spread_cost_estimate") or 0.0) for f in fills),
    }


def _attach_entry_execution_report(snap, prog):
    if snap is not None:
        snap["entry_execution_report"] = _entry_execution_report(prog)
    return snap


def _append_execution_history(snap, key, item, now_ms):
    if not snap or not item:
        return snap
    hist = list(snap.get(key) or [])
    rec = dict(item)
    rec["ts"] = now_ms
    hist.append(rec)
    snap[key] = hist[-50:]
    return snap


def _settlement_is_num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _option_position_map(option_positions):
    actual = {}
    for p in option_positions or []:
        inst = (p or {}).get("instrument_name") or (p or {}).get("instrument")
        if not inst:
            continue
        raw_size = (p or {}).get("size")
        if raw_size is None:
            raw_size = (p or {}).get("amount")
        try:
            size = float(raw_size or 0.0)
        except Exception:
            size = 0.0
        actual[inst] = actual.get(inst, 0.0) + size
    return actual


def _leg_expired_for_settlement(expiry_ts, now_ms):
    return (_settlement_is_num(expiry_ts) and _settlement_is_num(now_ms)
            and now_ms >= expiry_ts + SETTLEMENT_RECONCILE_GRACE_MS)


def _leg_absent_or_zero(actual, inst):
    if not inst:
        return False
    return abs(actual.get(inst, 0.0) or 0.0) <= 1e-9


def _option_kind_from_instrument(inst, fallback_side=None):
    parts = str(inst or "").upper().split("-")
    token = parts[-1] if parts else ""
    if token in ("P", "PUT"):
        return "PUT"
    if token in ("C", "CALL"):
        return "CALL"
    side = str(fallback_side or "").upper()
    if "PUT" in side:
        return "PUT"
    if "CALL" in side:
        return "CALL"
    return None


def _option_strike_from_instrument(inst):
    parts = str(inst or "").split("-")
    if len(parts) < 3:
        return None
    try:
        return float(parts[-2])
    except Exception:
        return None


def _settlement_float(value):
    if _settlement_is_num(value):
        return float(value)
    return None


def _settlement_leg_strike(snap, leg, inst):
    keys = ["%s_strike" % leg]
    if leg == "long":
        keys.append("protection_strike")
    for key in keys:
        value = _settlement_float((snap or {}).get(key))
        if value is not None:
            return value
    return _option_strike_from_instrument(inst)


def _entry_net_credit_ccy(snap):
    report = (snap or {}).get("entry_execution_report") or {}
    for value in (report.get("actual_net_credit_after_fees"),
                  (snap or {}).get("entry_profit_ceiling_net")):
        out = _settlement_float(value)
        if out is not None:
            return out
    return None


def _settlement_can_use_index_fallback(snap):
    return _entry_net_credit_ccy(snap) is not None


def _settlement_status_from_source(source):
    s = str(source or "").upper()
    if s in ("INDEX_FALLBACK", "ESTIMATED", "FALLBACK_INDEX"):
        return "ESTIMATED"
    return "COMPUTED"


def _settlement_price_context(snap, leg):
    snap = snap or {}
    for key in ("%s_settlement_index_price" % leg, "settlement_index_price"):
        price = _settlement_float(snap.get(key))
        if price is not None and price > 0:
            source = (snap.get("%s_settlement_price_source" % leg)
                      or snap.get("settlement_price_source")
                      or "EXCHANGE_SETTLEMENT")
            return {"price": price, "source": source,
                    "status": _settlement_status_from_source(source)}
    if _settlement_can_use_index_fallback(snap):
        try:
            price = _settlement_float(dbt_index_price(SETTLEMENT_CURRENCY))
        except Exception:
            price = None
        if price is not None and price > 0:
            return {"price": price, "source": "INDEX_FALLBACK", "status": "ESTIMATED"}
    return {"price": None, "source": "DATA_GAP", "status": "DATA_GAP"}


def _option_intrinsic_ccy(kind, strike, index_price):
    if kind not in ("PUT", "CALL") or strike is None or index_price is None or index_price <= 0:
        return None
    if kind == "PUT":
        return max(strike - index_price, 0.0) / index_price
    return max(index_price - strike, 0.0) / index_price


def _settlement_status_join(statuses):
    states = [s for s in statuses if s]
    if any(s == "DATA_GAP" for s in states):
        return "DATA_GAP"
    if any(s == "ESTIMATED" for s in states):
        return "ESTIMATED"
    if states:
        return "COMPUTED"
    return "COMPUTED"


def _build_settlement_event(snap, leg, instrument, qty_before, actual_size, reason, now_ms):
    ctx = _settlement_price_context(snap, leg)
    kind = _option_kind_from_instrument(instrument, (snap or {}).get("side"))
    strike = _settlement_leg_strike(snap, leg, instrument)
    intrinsic = _option_intrinsic_ccy(kind, strike, ctx.get("price"))
    status = ctx.get("status")
    cashflow = None
    gap = None
    if intrinsic is None:
        status = "DATA_GAP"
        if kind is None:
            gap = "OPTION_KIND_MISSING"
        elif strike is None:
            gap = "OPTION_STRIKE_MISSING"
        else:
            gap = "SETTLEMENT_INDEX_PRICE_MISSING"
    else:
        qty = qty_before or 0.0
        signed = -1.0 if leg == "short" else 1.0
        cashflow = signed * intrinsic * qty
    return {
        "ts": now_ms, "leg": leg, "instrument": instrument,
        "qty_before": qty_before, "qty_after": 0.0,
        "exchange_position_size": actual_size,
        "reason": reason,
        "option_kind": kind,
        "strike": strike,
        "settlement_index_price": ctx.get("price"),
        "settlement_price_source": ctx.get("source"),
        "intrinsic_ccy": intrinsic,
        "settlement_cashflow_ccy": cashflow,
        "settlement_pnl_ccy": cashflow,
        "settlement_pnl_status": status,
        "settlement_data_gap": gap,
    }


def _recompute_option_realized_pnl(snap):
    if snap is None:
        return snap
    hist = list((snap or {}).get("option_settlement_history") or [])
    statuses = []
    data_gap = False
    short_cashflow = 0.0
    long_cashflow = 0.0
    for rec in hist:
        status = (rec or {}).get("settlement_pnl_status")
        statuses.append(status)
        cashflow = (rec or {}).get("settlement_cashflow_ccy")
        if status in ("DATA_GAP", "NOT_COMPUTED") or cashflow is None:
            data_gap = True
            continue
        if (rec or {}).get("leg") == "short":
            short_cashflow += cashflow
        elif (rec or {}).get("leg") == "long":
            long_cashflow += cashflow
    settlement_status = _settlement_status_join(statuses)
    if data_gap:
        settlement_status = "DATA_GAP"
        snap["short_settlement_cashflow_ccy"] = None
        snap["long_settlement_cashflow_ccy"] = None
        snap["option_settlement_cashflow_ccy"] = None
    else:
        total_cashflow = short_cashflow + long_cashflow
        snap["short_settlement_cashflow_ccy"] = short_cashflow
        snap["long_settlement_cashflow_ccy"] = long_cashflow
        snap["option_settlement_cashflow_ccy"] = total_cashflow
    snap["settlement_pnl_status"] = settlement_status
    entry_credit = _entry_net_credit_ccy(snap)
    if entry_credit is None or data_gap:
        snap["option_realized_pnl_ccy"] = None
        snap["option_realized_pnl_status"] = "DATA_GAP"
    else:
        total_cashflow = snap.get("option_settlement_cashflow_ccy") or 0.0
        exit_spend = snap.get("realized_exit_spend") or 0.0
        recovery_value = snap.get("realized_protection_recovery_value") or 0.0
        snap["option_realized_pnl_ccy"] = entry_credit - exit_spend + recovery_value + total_cashflow
        snap["option_realized_pnl_status"] = settlement_status
    short_now = snap.get("remaining_short_qty") or 0.0
    long_now = snap.get("long_remaining_qty")
    if long_now is None:
        long_now = snap.get("long_fill_amount") or 0.0
    if short_now <= 1e-12 and (long_now or 0.0) <= 1e-12:
        snap["final_option_pnl_ccy"] = snap.get("option_realized_pnl_ccy")
        snap["final_pnl_status"] = snap.get("option_realized_pnl_status")
    else:
        snap["final_option_pnl_ccy"] = None
        snap["final_pnl_status"] = "OPEN"
    return snap


def _append_settlement_event(snap, event):
    rec = dict(event or {})
    rec.setdefault("settlement_pnl_ccy", None)
    rec.setdefault("settlement_pnl_status", "NOT_COMPUTED")
    hist = list((snap or {}).get("option_settlement_history") or [])
    hist.append(rec)
    snap["option_settlement_history"] = hist[-50:]
    _recompute_option_realized_pnl(snap)
    return rec


def _settlement_reconcile_snapshot(snap, option_positions, now_ms):
    if not snap:
        return {"snap": snap, "changed": False, "events": [],
                "settlement_state": "NONE", "reason": "NO_POSITION_SNAPSHOT"}
    if option_positions is None:
        return {"snap": snap, "changed": False, "events": [],
                "settlement_state": (snap or {}).get("settlement_state") or "NONE",
                "reason": "OPTION_POSITION_DATA_GAP"}
    actual = _option_position_map(option_positions)
    updated = dict(snap)
    events = []
    short_inst = updated.get("short_instrument")
    long_inst = updated.get("long_instrument")
    short_expiry = updated.get("short_expiry_ts")
    long_expiry = updated.get("long_expiry_ts") or short_expiry
    short_qty = updated.get("remaining_short_qty") or 0.0
    long_qty = updated.get("long_remaining_qty")
    if long_qty is None:
        long_qty = updated.get("long_fill_amount") or 0.0

    if (short_qty > 1e-12
            and _leg_expired_for_settlement(short_expiry, now_ms)
            and _leg_absent_or_zero(actual, short_inst)):
        updated["remaining_short_qty"] = 0.0
        ev = _build_settlement_event(updated, "short", short_inst, short_qty,
                                     actual.get(short_inst, 0.0),
                                     "SHORT_OPTION_SETTLED_ABSENT_ON_EXCHANGE", now_ms)
        events.append(_append_settlement_event(updated, ev))
        ledger_set_state(S_SHORT_FLAT_LONG_RESIDUAL)

    if (long_qty > 1e-12
            and _leg_expired_for_settlement(long_expiry, now_ms)
            and _leg_absent_or_zero(actual, long_inst)):
        updated["long_remaining_qty"] = 0.0
        ev = _build_settlement_event(updated, "long", long_inst, long_qty,
                                     actual.get(long_inst, 0.0),
                                     "LONG_OPTION_SETTLED_ABSENT_ON_EXCHANGE", now_ms)
        events.append(_append_settlement_event(updated, ev))

    if not events:
        return {"snap": snap, "changed": False, "events": [],
                "settlement_state": updated.get("settlement_state") or "NONE",
                "reason": "NO_SETTLEMENT_CHANGE"}
    short_now = updated.get("remaining_short_qty") or 0.0
    long_now = updated.get("long_remaining_qty")
    if long_now is None:
        long_now = updated.get("long_fill_amount") or 0.0
    if short_now <= 1e-12 and long_now <= 1e-12:
        state = "BOTH_LEGS_SETTLED"
    elif short_now <= 1e-12:
        state = "SHORT_SETTLED"
    else:
        state = "LONG_SETTLED"
    updated["settlement_state"] = state
    _recompute_option_realized_pnl(updated)
    return {"snap": updated, "changed": True, "events": events,
            "settlement_state": state, "reason": "OPTION_SETTLEMENT_RECONCILED"}


def _build_protection_residual_snapshot(locked, prog, remaining_qty, now_ms):
    """保护腿已成交、短腿未建成时的最小残值快照；复用持仓管理的保护腿回收分支。"""
    locked = locked or {}
    prog = prog or {}
    filled = prog.get("prot_done") or remaining_qty or 0.0
    avg_long = (prog.get("prot_cost") / filled) if filled > 0 else None
    snap = {
        "schema_name": "VerticalEntrySnapshot",
        "position_id": "pos-residual-%s" % now_ms,
        "session_id": locked.get("session_id"),
        "manual_context_id": locked.get("manual_context_id"),
        "manual_context_hash": locked.get("manual_context_hash"),
        "direction_bias": locked.get("direction_bias"),
        "approval_id": locked.get("approval_id"),
        "strategy_code": locked.get("strategy_code"),
        "quality_code": locked.get("quality_code"),
        "plan_hash": locked.get("plan_hash"),
        "side": locked.get("side"),
        "short_instrument": locked.get("short_instrument"),
        "long_instrument": locked.get("long_instrument"),
        "short_fill_amount": 0.0, "short_fill_price": None,
        "long_fill_amount": filled, "long_fill_price": avg_long,
        "entry_fees": _entry_execution_report(prog).get("total_fee_estimate"), "entry_profit_ceiling_net": None,
        "take_profit_target_ratio": 0.80, "target_profit_amount": None,
        "max_total_exit_spend": None, "realized_exit_spend": 0.0,
        "remaining_short_qty": 0.0,
        "long_remaining_qty": max(0.0, remaining_qty or 0.0),
        "short_expiry_ts": locked.get("short_expiry"),
        "long_expiry_ts": locked.get("long_expiry") or locked.get("short_expiry"),
        "entry_risk_anchor": None,
        "frozen_ts": now_ms,
        "manual_lineage_only": True,
        "immutable": True,
        "residual_reason": "PROTECTION_ONLY_AFTER_ENTRY_ABANDON",
    }
    return _attach_entry_execution_report(snap, prog)


def _block_recovery(reason):
    verdict = {"state": "RECOVERY_BLOCKED", "reasons": [reason], "allow_new_open": False}
    _G(_RECOVERY_KEY, verdict)
    _G(_LOCKED_KEY, None)
    return verdict


def _build_partial_vertical_snapshot(locked, prog, spot, now_ms,
                                     abandon_reason="ENTRY_ABANDONED_AFTER_PARTIAL_SHORT"):
    short_done = prog.get("short_done") or 0.0
    prot_done = prog.get("prot_done") or 0.0
    avg_prot = (prog.get("prot_cost") / prot_done) if prot_done > 0 else None
    avg_short = (prog.get("short_credit") / short_done) if short_done > 0 else None
    entry_fees = (prog.get("entry_fee_used") if prog.get("entry_fills") else None)
    if entry_fees is None:
        entry_fees = (acct_option_fee_ccy(avg_short or 0.0, short_done)
                      + acct_option_fee_ccy(avg_prot or 0.0, prot_done))
    snap = build_vertical_entry_snapshot(
        locked, {"filled": short_done, "avg_price": avg_short},
        {"filled": prot_done, "avg_price": avg_prot}, entry_fees, now_ms,
        entry_risk_anchor=_build_entry_risk_anchor(locked, spot, now_ms))
    snap["entry_completion_state"] = "PARTIAL_VERTICAL"
    snap["entry_abandon_reason"] = abandon_reason
    snap["entry_target_amount"] = locked.get("amount") or ORDER_AMOUNT
    snap["entry_attempts"] = prog.get("attempts") or 0
    return _attach_entry_execution_report(snap, prog)


def _has_entry_progress(prog):
    prog = prog or {}
    return ((prog.get("prot_done") or 0.0) > 1e-12
            or (prog.get("short_done") or 0.0) > 1e-12)


def _adopt_entry_progress_or_block(locked, prog, spot, now_ms, reason):
    prog = prog or {}
    prot_done = prog.get("prot_done") or 0.0
    short_done = prog.get("short_done") or 0.0
    if short_done > prot_done + 1e-12:
        _block_recovery("ENTRY_SHORT_GT_PROTECTION")
        return {"adopted": False, "blocked": True,
                "reason": "RECOVERY_BLOCKED:ENTRY_SHORT_GT_PROTECTION"}
    if short_done > 1e-12:
        snap = _build_partial_vertical_snapshot(locked, prog, spot, now_ms, reason)
        _G(_POSITION_KEY, snap)
        _G(_LOCKED_KEY, None)
        ledger_set_state(S_SHORT_ACTIVE_PROTECTED)
        Log("[entry][adopt] state=PARTIAL_VERTICAL short_done=%s prot_done=%s reason=%s" %
            (short_done, prot_done, reason))
        return {"adopted": True, "blocked": False, "snapshot": snap,
                "position_kind": "partial",
                "reason": "ENTRY_PARTIAL_VERTICAL_MANAGED:" + reason}
    if prot_done > 1e-12:
        snap = _build_protection_residual_snapshot(locked, prog, prot_done, now_ms)
        snap["entry_completion_state"] = "PROTECTION_ONLY_RESIDUAL"
        snap["entry_abandon_reason"] = reason
        snap["entry_target_amount"] = (locked or {}).get("amount") or ORDER_AMOUNT
        snap["entry_attempts"] = prog.get("attempts") or 0
        _G(_POSITION_KEY, snap)
        _G(_LOCKED_KEY, None)
        ledger_set_state(S_SHORT_FLAT_LONG_RESIDUAL)
        Log("[entry][adopt] state=PROTECTION_ONLY_RESIDUAL qty=%s inst=%s reason=%s" %
            (prot_done, (locked or {}).get("long_instrument"), reason))
        return {"adopted": True, "blocked": False, "snapshot": snap,
                "position_kind": "residual",
                "reason": "ENTRY_PROTECTION_ONLY_RESIDUAL_MANAGED:" + reason}
    return {"adopted": False, "blocked": False, "reason": "NO_ENTRY_PROGRESS"}


def _entry_progress_explained_by_positions(locked, prog, option_positions):
    actual = {}
    for p in (option_positions or []):
        inst = p.get("instrument_name")
        if inst:
            actual[inst] = actual.get(inst, 0.0) + abs(p.get("size") or 0.0)
    checks = []
    if (prog.get("prot_done") or 0.0) > 1e-12:
        checks.append(((locked or {}).get("long_instrument"), prog.get("prot_done") or 0.0))
    if (prog.get("short_done") or 0.0) > 1e-12:
        checks.append(((locked or {}).get("short_instrument"), prog.get("short_done") or 0.0))
    return bool(checks) and all(inst and actual.get(inst, 0.0) + 1e-12 >= qty for inst, qty in checks)


def _attempt_commit(locked, spot, manual_context, now_ms):
    """锁定方案 → 预提交硬门 → **开仓活动(entry campaign)**：信用底线内 maker、保护腿先成交、
    **跨轮持久保护腿订单**（仅随 mark 目标变化改价）。预提交不过/门控关 → 仅空跑预览；
    两腿成交达标 → 冻结入场快照；保护腿 taker 兜底按首次挂单后的时间上限触发。"""
    lib = _G(_LIB_KEY)
    live = _build_precommit_live(locked, spot, manual_context, now_ms)
    pre = evaluate_precommit_checks(locked, lib, live)
    amount = locked.get("amount") or ORDER_AMOUNT
    short_i, long_i = locked.get("short_instrument"), locked.get("long_instrument")
    prog = dict(locked.get("entry") or {"prot_done": 0.0, "short_done": 0.0, "attempts": 0,
                                        "prot_cost": 0.0, "short_credit": 0.0,
                                        "entry_fee_used": 0.0, "entry_fills": []})
    prog.setdefault("entry_fee_used", 0.0)
    prog.setdefault("entry_fills", [])
    prog.setdefault("prot_order", None)
    result = {"precommit": pre, "budget": live.get("_budget"), "committed": False,
              "entry_snapshot": None, "entry_state": None, "net_credit": None, "reason": None,
              "order_intent": [
                  dict(leg="保护腿", **exec_plan_prices("buy", long_i, amount)),
                  dict(leg="卖方腿", **exec_plan_prices("sell", short_i, amount))]}
    if (prog.get("short_done") or 0.0) > (prog.get("prot_done") or 0.0) + 1e-12:
        adopted = _adopt_entry_progress_or_block(
            locked, prog, spot, now_ms, "ENTRY_SHORT_GT_PROTECTION")
        result["reason"] = adopted.get("reason")
        return result
    if not pre["passed"]:
        if _has_entry_progress(prog):
            adopt_reason = ("PRECOMMIT_FAILED_AFTER_PARTIAL_SHORT"
                            if (prog.get("short_done") or 0.0) > 1e-12
                            else "PRECOMMIT_FAILED_AFTER_ENTRY_PROGRESS:" + ",".join(pre["failed"]))
            adopted = _adopt_entry_progress_or_block(
                locked, prog, spot, now_ms, adopt_reason)
            result["entry_snapshot"] = adopted.get("snapshot")
            result["reason"] = ("ENTRY_PARTIAL_VERTICAL_MANAGED_PRECOMMIT_FAILED"
                                if adopted.get("position_kind") == "partial"
                                else adopted.get("reason"))
            if adopted.get("position_kind") == "partial":
                result["partial_position"] = True
            if adopted.get("position_kind") == "residual":
                result["residual_position"] = True
            return result
        result["reason"] = "PRECOMMIT_FAILED:" + ",".join(pre["failed"])
        return result
    g = _effective_gate_cfg()
    gate = gate_decision(ACTION_ENTRY, g["allow_entry"], g["allow_exit"],
                         g["allow_hedge"], _effective_kill(), EMERGENCY_REDUCE_ONLY)
    step = exec_entry_campaign_step(long_i, short_i, amount, ENTRY_MIN_NET_CREDIT,
                                    ENTRY_MAX_TICK_STEPS, prog["attempts"],
                                    prog["prot_done"], prog["short_done"],
                                    allow_live=gate["allowed"], label="entry",
                                    prot_order=prog.get("prot_order"), now_ms=now_ms)
    result["net_credit"] = step.get("net_credit")
    decision = entry_campaign_decision(
        True, step.get("quotes_ok"), step.get("credit_ok"), prog["attempts"], ENTRY_MAX_ATTEMPTS,
        prog["prot_done"] >= amount - 1e-12, prog["short_done"] >= amount - 1e-12)
    result["entry_state"] = decision["state"]
    pf, sf = (step.get("prot_fill") or 0.0), (step.get("short_fill") or 0.0)
    if gate["allowed"] and not step.get("dry"):                  # 仅门开且真实下单时累计/计尝试
        pf, sf = (step.get("prot_fill") or 0.0), (step.get("short_fill") or 0.0)
        next_prot = min(amount, prog["prot_done"] + pf)
        next_short = prog["short_done"] + sf
        if next_short > next_prot + 1e-12:
            _block_recovery("ENTRY_SHORT_GT_PROTECTION")
            result["reason"] = "RECOVERY_BLOCKED:ENTRY_SHORT_GT_PROTECTION"
            return result
        prog["prot_done"] = next_prot
        prog["short_done"] = min(amount, next_short)
        prog["prot_cost"] += pf * (step.get("prot_avg_price") or step.get("prot_price") or 0.0)
        prog["short_credit"] += sf * (step.get("short_avg_price") or step.get("short_price") or 0.0)
        prog["entry_fee_used"] = (prog.get("entry_fee_used") or 0.0) + (step.get("entry_fees") or 0.0)
        prog["entry_fills"] = list(prog.get("entry_fills") or []) + list(step.get("fills") or [])
        prog["prot_order"] = step.get("prot_order")
        prog["attempts"] += 1
        locked["entry"] = prog
        _G(_LOCKED_KEY, locked)
        result["entry_prot_order"] = prog.get("prot_order")
        if ((prog.get("short_done") or 0.0) > 1e-12
                and not (prog["prot_done"] >= amount - 1e-12
                         and prog["short_done"] >= amount - 1e-12)):
            reason = ("SHORT_NOT_FILLED_AFTER_PROTECTION"
                      if (prog.get("short_done") or 0.0) <= 1e-12
                      else "PARTIAL_ENTRY_PROGRESS_AFTER_STEP")
            adopted = _adopt_entry_progress_or_block(locked, prog, spot, now_ms, reason)
            result["entry_snapshot"] = adopted.get("snapshot")
            result["reason"] = adopted.get("reason")
            if adopted.get("position_kind") == "partial":
                result["partial_position"] = True
            if adopted.get("position_kind") == "residual":
                result["residual_position"] = True
            return result
    if prog["prot_done"] >= amount - 1e-12 and prog["short_done"] >= amount - 1e-12:
        avg_prot = (prog["prot_cost"] / prog["prot_done"]) if prog["prot_done"] > 0 else step.get("prot_price")
        avg_short = (prog["short_credit"] / prog["short_done"]) if prog["short_done"] > 0 else step.get("short_price")
        entry_fees = (prog.get("entry_fee_used") if prog.get("entry_fills") else None)
        if entry_fees is None:
            entry_fees = (acct_option_fee_ccy(avg_short or 0.0, prog["short_done"])
                          + acct_option_fee_ccy(avg_prot or 0.0, prog["prot_done"]))
        anchor = _build_entry_risk_anchor(locked, spot, now_ms)   # 冻结入场风险锚
        snap = build_vertical_entry_snapshot(
            locked, {"filled": prog["short_done"], "avg_price": avg_short},
            {"filled": prog["prot_done"], "avg_price": avg_prot}, entry_fees, now_ms,
            entry_risk_anchor=anchor)
        _attach_entry_execution_report(snap, prog)
        _G(_POSITION_KEY, snap)
        _G(_LOCKED_KEY, None)
        ledger_set_state(S_SHORT_ACTIVE_PROTECTED)
        result.update({"committed": True, "entry_snapshot": snap, "reason": "STRUCTURE_OPEN"})
        return result
    if decision["state"] == ENTRY_ABANDONED:
        if (prog.get("short_done") or 0.0) > (prog.get("prot_done") or 0.0) + 1e-12:
            _block_recovery("ENTRY_SHORT_GT_PROTECTION")
            result["reason"] = "RECOVERY_BLOCKED:ENTRY_SHORT_GT_PROTECTION"
            return result
        if (prog.get("short_done") or 0.0) > 1e-12:
            snap = _build_partial_vertical_snapshot(locked, prog, spot, now_ms)
            _G(_POSITION_KEY, snap)
            _G(_LOCKED_KEY, None)
            ledger_set_state(S_SHORT_ACTIVE_PROTECTED)
            result.update({"entry_snapshot": snap, "partial_position": True,
                           "reason": "ENTRY_ABANDONED_PARTIAL_VERTICAL:" + decision["reason"]})
            return result
        residual_qty = prog.get("prot_done") or 0.0
        if residual_qty > 1e-12:
            snap = _build_protection_residual_snapshot(locked, prog, residual_qty, now_ms)
            _G(_POSITION_KEY, snap)
            ledger_set_state(S_SHORT_FLAT_LONG_RESIDUAL)
            result["entry_snapshot"] = snap
            result["residual_position"] = True
        _G(_LOCKED_KEY, None)
        result["reason"] = "ENTRY_ABANDONED:" + decision["reason"]
        return result
    result["reason"] = decision["state"] + (":dry" if step.get("dry") else "")
    result["entry_prot_order"] = prog.get("prot_order")
    return result


_RECOVERY_KEY = "spm_recovery_verdict_v1"
_CLOSED_HISTORY_KEY = "spm_closed_history_v1"


def _recovery_verdict():
    return _G(_RECOVERY_KEY) or {"state": "OK", "allow_new_open": True}


def _orphan_hedge_cleanup_detail(recovery):
    recovery = recovery or {}
    qty = recovery.get("perp_qty")
    side = None
    if isinstance(qty, (int, float)) and not isinstance(qty, bool):
        if qty > 1e-12:
            side = "sell"
        elif qty < -1e-12:
            side = "buy"
    return {
        "state": recovery.get("state") or "ORPHAN_HEDGE_EMERGENCY",
        "mode": "MANUAL_REDUCE_ONLY_REQUIRED",
        "venue": recovery.get("venue") or HEDGE_VENUE,
        "instrument": recovery.get("instrument") or (
            HEDGE_BINANCE_INSTRUMENT if HEDGE_VENUE == "BINANCE" else HEDGE_INSTRUMENT),
        "perp_qty": qty,
        "suggested_side": side,
        "reasons": recovery.get("reasons") or [],
    }


def _clear_recovery_ok(reason, now_ms):
    verdict = {"state": "OK", "reasons": [], "allow_new_open": True,
               "cleared_reason": reason, "cleared_ts": now_ms}
    _G(_RECOVERY_KEY, verdict)
    return verdict


def _archive_closed(snap, now_ms):
    """P0②：两腿 + 对冲 perp 均归零 → 归档 closed_position_history、清快照、置 CLOSED。"""
    hedge_state = _hedge_policy_load_state_raw() or {}
    if hedge_state.get("pending_order_id"):
        return False
    hist = list(_G(_CLOSED_HISTORY_KEY) or [])
    rec = dict(snap or {})
    _recompute_option_realized_pnl(rec)
    rec["closed_ts"] = now_ms
    hist.append(rec)
    _G(_CLOSED_HISTORY_KEY, hist[-50:])
    _G(_POSITION_KEY, None)
    ledger_set_state(S_CLOSED)
    _clear_recovery_ok("POSITION_CLOSED_ARCHIVED", now_ms)
    _G(_HEDGE_POLICY_STATE_KEY, _hedge_policy_default_state(None))
    return True


def _is_entry_order_label(label):
    s = str(label or "")
    return s == "entry" or s.startswith("entry_") or s in ("prot", "short")


def _cancel_startup_entry_orders(currency):
    try:
        orders = dbt_get_open_orders(currency)
    except Exception:
        return None, {"state": "RECOVERY_BLOCKED",
                      "reasons": ["ENTRY_OPEN_ORDERS_QUERY_FAILED"],
                      "allow_new_open": False}
    if orders is None:
        return None, {"state": "RECOVERY_BLOCKED",
                      "reasons": ["ENTRY_OPEN_ORDERS_QUERY_FAILED"],
                      "allow_new_open": False}
    entry_orders = [o for o in (orders or []) if _is_entry_order_label(o.get("label"))]
    reasons = []
    for o in entry_orders:
        oid = o.get("order_id")
        if not oid:
            reasons.append("ENTRY_ACTIVE_ORDER_WITHOUT_ID")
            continue
        try:
            dbt_cancel(oid)
        except Exception:
            reasons.append("ENTRY_CANCEL_FAILED:%s" % oid)
    if reasons:
        return None, {"state": "RECOVERY_BLOCKED", "reasons": reasons,
                      "allow_new_open": False}
    if not entry_orders:
        return orders, None
    try:
        after = dbt_get_open_orders(currency)
    except Exception:
        return None, {"state": "RECOVERY_BLOCKED",
                      "reasons": ["ENTRY_OPEN_ORDERS_RECHECK_FAILED"],
                      "allow_new_open": False}
    if after is None:
        return None, {"state": "RECOVERY_BLOCKED",
                      "reasons": ["ENTRY_OPEN_ORDERS_RECHECK_FAILED"],
                      "allow_new_open": False}
    remaining = [o for o in (after or []) if _is_entry_order_label(o.get("label"))]
    if remaining:
        return None, {"state": "RECOVERY_BLOCKED",
                      "reasons": ["ENTRY_ACTIVE_ORDERS_REMAIN:%d" % len(remaining)],
                      "allow_new_open": False}
    return after, None


def _read_startup_positions(currency):
    try:
        opt = dbt_get_positions_strict(currency, "option")
    except Exception:
        opt = None
    if opt is None:
        return None, None, {"state": "RECOVERY_BLOCKED",
                            "reasons": ["OPTION_POSITION_QUERY_FAILED"],
                            "allow_new_open": False}
    if HEDGE_VENUE == "BINANCE":
        b_qty = bnc_get_position_btc(HEDGE_BINANCE_INSTRUMENT)
        if b_qty is None:
            return opt, None, {"state": "RECOVERY_BLOCKED",
                               "reasons": ["HEDGE_POSITION_QUERY_FAILED"],
                               "allow_new_open": False}
        perp_qty = b_qty
    else:
        try:
            perp = dbt_get_positions_strict(currency, "future")
        except Exception:
            perp = None
        if perp is None:
            return opt, None, {"state": "RECOVERY_BLOCKED",
                               "reasons": ["HEDGE_POSITION_QUERY_FAILED"],
                               "allow_new_open": False}
        perp_qty = sum((p.get("size") or 0.0) for p in perp)
    return opt, perp_qty, None


def startup_recovery_check(currency):
    """启动恢复（P0①：以 _POSITION_KEY 入场快照为持仓真相）：读交易所真实期权/永续持仓 +
    快照剩余短/保护腿（无快照但开仓活动在途 → 用活动进度作期望，按成交重校验）+ 真实活动订单
    → 裁决并落 _G（恢复完成前禁开新仓）。"""
    opt, perp_qty, read_block = _read_startup_positions(currency)
    if read_block:
        _G(_RECOVERY_KEY, read_block)
        return read_block
    snap = _G(_POSITION_KEY)
    locked = _G(_LOCKED_KEY) or {}
    prog = {}
    short_qty = (snap or {}).get("remaining_short_qty") or 0.0
    long_qty = (snap or {}).get("long_remaining_qty") or 0.0
    if not snap:                                   # C3②：在途开仓活动按其进度作期望（与交易所成交重校验）
        prog = locked.get("entry") or {}
        short_qty = prog.get("short_done") or 0.0
        long_qty = prog.get("prot_done") or 0.0
    orders, entry_order_block = _cancel_startup_entry_orders(currency)
    if entry_order_block:
        _G(_RECOVERY_KEY, entry_order_block)
        return entry_order_block
    opt, perp_qty, read_block = _read_startup_positions(currency)
    if read_block:
        _G(_RECOVERY_KEY, read_block)
        return read_block
    if snap:
        settlement = _settlement_reconcile_snapshot(snap, opt, _now_ms())
        if settlement.get("changed"):
            snap = settlement.get("snap")
            _G(_POSITION_KEY, snap)
            short_qty = (snap or {}).get("remaining_short_qty") or 0.0
            long_qty = (snap or {}).get("long_remaining_qty")
            if long_qty is None:
                long_qty = (snap or {}).get("long_fill_amount") or 0.0
            if short_qty <= 1e-12 and abs(perp_qty or 0.0) > 1e-9:
                verdict = {"state": "ORPHAN_HEDGE_EMERGENCY",
                           "reasons": ["SETTLED_OPTION_WITH_PERP_HEDGE"],
                           "allow_new_open": False,
                           "perp_qty": perp_qty, "venue": HEDGE_VENUE,
                           "instrument": (HEDGE_BINANCE_INSTRUMENT if HEDGE_VENUE == "BINANCE"
                                          else HEDGE_INSTRUMENT)}
                _G(_RECOVERY_KEY, verdict)
                return verdict
    if (not snap) and _has_entry_progress(prog):
        if _entry_progress_explained_by_positions(locked, prog, opt):
            adopted = _adopt_entry_progress_or_block(
                locked, prog, _spot_price(), _now_ms(), "STARTUP_RECOVERY_ENTRY_PROGRESS")
            verdict = {"state": "OK", "reasons": [], "allow_new_open": True,
                       "adopted": bool(adopted.get("adopted")),
                       "reason": adopted.get("reason")}
            _G(_RECOVERY_KEY, verdict)
            return verdict
        block = {"state": "RECOVERY_BLOCKED",
                 "reasons": ["ENTRY_PROGRESS_NOT_MATCH_EXCHANGE"],
                 "allow_new_open": False}
        _G(_RECOVERY_KEY, block)
        return block
    verdict = evaluate_startup_recovery(opt, perp_qty, short_qty, active_orders=orders,
                                        expected_long_qty=long_qty)
    if verdict.get("state") == "ORPHAN_HEDGE_EMERGENCY":
        verdict.update({"perp_qty": perp_qty, "venue": HEDGE_VENUE,
                        "instrument": (HEDGE_BINANCE_INSTRUMENT if HEDGE_VENUE == "BINANCE"
                                       else HEDGE_INSTRUMENT)})
    _G(_RECOVERY_KEY, verdict)
    return verdict


def _evaluate_take_profit(snap, quote_fn=None, now_ms=None):
    """据入场快照 + 实时短腿盘口算止盈资格(参考捕获率) 与退出预算/价格上限。保护腿价值不入分母。"""
    if not snap:
        return {"ratio": None, "qualified": False, "remaining_short_qty": 0.0,
                "remaining_budget": None, "price_cap": 0.0, "quote_ok": False,
                "status": "数据缺口", "quote_gap": "NO_POSITION_SNAPSHOT"}
    rem_qty = snap.get("remaining_short_qty") or 0.0
    if rem_qty <= 1e-12:
        dte_h = _dte_hours_to(snap.get("short_expiry_ts"), now_ms if now_ms is not None else _now_ms())
        ceiling = snap.get("entry_profit_ceiling_net")
        max_spend = snap.get("max_total_exit_spend")
        realized = snap.get("realized_exit_spend") or 0.0
        return {"ratio": None, "qualified": False, "remaining_short_qty": 0.0,
                "remaining_budget": None, "price_cap": 0.0, "quote_ok": False,
                "status": "短腿已归零", "quote_gap": None,
                "capture_qualified": False,
                "remaining_dte_hours": dte_h,
                "take_profit_min_dte_hours": TAKE_PROFIT_MIN_DTE_HOURS,
                "dte_gate_active": False,
                "dte_gate_reason": None,
                "entry_profit_ceiling_net": ceiling,
                "target_profit_amount": snap.get("target_profit_amount"),
                "target_ratio": snap.get("take_profit_target_ratio") or 0.80,
                "max_total_exit_spend": max_spend,
                "realized_exit_spend": realized,
                "short_buyback_ref": None,
                "estimated_exit_fee": None,
                "exit_reserve": None,
                "short_price_cap": 0.0,
                "tp_underlying_target_price": None,
                "tp_underlying_target_method": "data_gap",
                "tp_target_data_gap": None,
                "short_mark": None,
                "short_bid": None,
                "short_ask": None,
                "short_delta": None}
    quote = quote_fn or exec_quote
    q = quote(snap.get("short_instrument"))
    quote_ok = bool(q and q.get("mark") is not None and q.get("best_bid") not in (None, 0)
                    and q.get("best_ask") is not None)
    ceiling = snap.get("entry_profit_ceiling_net")
    max_spend = snap.get("max_total_exit_spend")
    realized = snap.get("realized_exit_spend") or 0.0
    cons_ref = (q["mark"] * rem_qty) if (quote_ok and rem_qty) else None
    est_fee = acct_option_fee_ccy(q["mark"], rem_qty) if quote_ok else None
    reserve = (max_spend * EXIT_RESERVE_RATIO) if isinstance(max_spend, (int, float)) else None
    ratio = reference_profit_capture_ratio(ceiling, cons_ref, est_fee, reserve)
    capture_qualified = take_profit_qualified(ratio, snap.get("take_profit_target_ratio") or 0.80)
    dte_h = _dte_hours_to(snap.get("short_expiry_ts"), now_ms if now_ms is not None else _now_ms())
    min_dte = TAKE_PROFIT_MIN_DTE_HOURS
    dte_gate_active = False
    dte_gate_reason = None
    qualified = capture_qualified
    if capture_qualified and isinstance(min_dte, (int, float)) and not isinstance(min_dte, bool) and min_dte > 0:
        if dte_h is None:
            qualified = False
            dte_gate_active = True
            dte_gate_reason = "TP_DTE_DATA_GAP"
        elif dte_h <= min_dte + 1e-12:
            qualified = False
            dte_gate_active = True
            dte_gate_reason = "TP_DTE_TOO_CLOSE_TO_EXPIRY"
    fee_reserve = reserve or 0.0
    rem_budget = short_buyback_budget(max_spend, realized, fee_reserve)
    tick = (q or {}).get("tick") or 0.0
    cap = short_buyback_price_cap(rem_budget, fee_reserve, rem_qty, tick) if rem_budget else 0.0
    status = ("交割临近持有" if dte_gate_active else
              ("已达标" if qualified else ("未达标" if ratio is not None else "数据缺口")))
    quote_gap = None if quote_ok else "NO_RELIABLE_QUOTE"
    short_delta = (q or {}).get("delta")
    target_underlying, target_gap = None, None
    if quote_ok and isinstance(cap, (int, float)) and isinstance((q or {}).get("mark"), (int, float)):
        if isinstance(short_delta, (int, float)) and abs(short_delta) > 1e-9:
            spot = _spot_price()
            if isinstance(spot, (int, float)):
                target_underlying = spot + (cap - q.get("mark")) / short_delta
            else:
                target_gap = "SPOT_MISSING"
        else:
            target_gap = "SHORT_DELTA_MISSING"
    elif not quote_ok:
        target_gap = quote_gap
    return {"ratio": ratio, "qualified": qualified, "remaining_short_qty": rem_qty,
            "remaining_budget": rem_budget, "price_cap": cap, "quote_ok": quote_ok,
            "status": status, "quote_gap": quote_gap,
            "capture_qualified": capture_qualified,
            "remaining_dte_hours": dte_h,
            "take_profit_min_dte_hours": min_dte,
            "dte_gate_active": dte_gate_active,
            "dte_gate_reason": dte_gate_reason,
            "entry_profit_ceiling_net": ceiling,
            "target_profit_amount": snap.get("target_profit_amount"),
            "target_ratio": snap.get("take_profit_target_ratio") or 0.80,
            "max_total_exit_spend": max_spend,
            "realized_exit_spend": realized,
            "short_buyback_ref": cons_ref,
            "estimated_exit_fee": est_fee,
            "exit_reserve": reserve,
            "short_price_cap": cap,
            "tp_underlying_target_price": target_underlying,
            "tp_underlying_target_method": "delta_linear" if target_underlying is not None else "data_gap",
            "tp_target_data_gap": target_gap,
            "short_mark": (q or {}).get("mark"),
            "short_bid": (q or {}).get("best_bid"),
            "short_ask": (q or {}).get("best_ask"),
            "short_delta": short_delta}


def _risk_exit_level_amount(level):
    if isinstance(level, (list, tuple)) and len(level) >= 2:
        return level[1] if isinstance(level[1], (int, float)) and not isinstance(level[1], bool) else None
    if isinstance(level, dict):
        for key in ("amount", "quantity", "size"):
            v = level.get(key)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return v
    return None


def _risk_exit_best_ask_depth(instrument, quote):
    q = quote or {}
    v = q.get("best_ask_amount")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return v
    try:
        book = dbt_order_book(instrument, depth=1)
    except Exception:
        return None
    asks = (book or {}).get("asks") or []
    return _risk_exit_level_amount(asks[0]) if asks else None


def _risk_exit_budget_cap(snap, auth, quote_fn=None):
    """风险退出预算/价格/深度上限：配置预算优先；缺深度 fail-closed。"""
    inst = (snap or {}).get("short_instrument")
    detail = {"remaining_budget": None, "price_cap": 0.0, "within": False,
              "within_price": False, "quote_ok": False, "ask": None,
              "ask_depth": None, "depth_ok": False, "reason": None}
    max_spend = RISK_EXIT_MAX_SPEND if RISK_EXIT_MAX_SPEND > 0 else (snap or {}).get("max_total_exit_spend")
    rem_qty = (snap or {}).get("remaining_short_qty") or 0.0
    if not isinstance(max_spend, (int, float)) or max_spend <= 0 or rem_qty <= 0:
        detail["reason"] = "NO_RISK_EXIT_BUDGET"
        return detail
    quote = quote_fn or exec_quote
    try:
        q = quote(inst) or {}
    except Exception:
        detail["reason"] = "EXIT_QUOTE_DATA_GAP"
        return detail
    realized = (snap or {}).get("realized_exit_spend") or 0.0
    fee_reserve = acct_option_fee_ccy(q.get("mark") or 0.0, rem_qty)
    rem_budget = short_buyback_budget(max_spend, realized, fee_reserve)
    tick = q.get("tick") or 0.0
    cap = short_buyback_price_cap(rem_budget, fee_reserve, rem_qty, tick) if rem_budget else 0.0
    ask = q.get("best_ask")
    within_price = bool(ask is not None and cap > 0 and ask <= cap + 1e-12)
    ask_depth = _risk_exit_best_ask_depth(inst, q) if inst else None
    depth_ok = bool(ask_depth is not None and ask_depth + 1e-12 >= rem_qty)
    detail.update({"remaining_budget": rem_budget, "price_cap": cap,
                   "within_price": within_price, "quote_ok": ask is not None,
                   "ask": ask, "ask_depth": ask_depth, "depth_ok": depth_ok,
                   "within": bool(within_price and depth_ok)})
    if ask is None:
        detail["reason"] = "EXIT_QUOTE_DATA_GAP"
    elif not within_price:
        detail["reason"] = "EXIT_PRICE_ABOVE_CAP"
    elif ask_depth is None:
        detail["reason"] = "EXIT_DEPTH_DATA_GAP"
    elif not depth_ok:
        detail["reason"] = "EXIT_DEPTH_INSUFFICIENT"
    return detail


def _apply_exit_fill(snap, step, now_ms):
    """把一次短腿买回成交计入入场快照：减剩余短腿、加已用退出支出；归零则转 SHORT_FLAT_LONG_RESIDUAL。"""
    filled = step.get("filled") or 0.0
    price = step.get("avg_price") or step.get("price") or 0.0
    fee = acct_option_fee_ccy(price, filled)
    snap["remaining_short_qty"] = max(0.0, (snap.get("remaining_short_qty") or 0.0) - filled)
    snap["realized_exit_spend"] = (snap.get("realized_exit_spend") or 0.0) + price * filled + fee
    snap["last_exit_ts"] = now_ms
    _append_execution_history(snap, "exit_execution_history", step, now_ms)
    _recompute_option_realized_pnl(snap)
    if snap["remaining_short_qty"] <= 1e-12:
        ledger_set_state(S_SHORT_FLAT_LONG_RESIDUAL)   # 短腿归零，转保护腿回收（不可直跳 CLOSED）
    _G(_POSITION_KEY, snap)


def _apply_protection_recovery_fill(snap, step, now_ms):
    if not snap or not step:
        return snap
    detail = dict(step.get("execution") or step)
    sold = detail.get("sold")
    if sold is None:
        sold = detail.get("filled")
    if sold is None:
        sold = step.get("sold") or step.get("filled") or 0.0
    price = detail.get("avg_price") or detail.get("price") or step.get("avg_price") or step.get("price") or 0.0
    fee = detail.get("fee") or detail.get("fee_used")
    if fee is None:
        fee = acct_option_fee_ccy(price, sold)
    gross_value = price * sold
    net_value = gross_value - fee
    snap["long_remaining_qty"] = max(0.0, (snap.get("long_remaining_qty") or 0.0) - sold)
    snap["realized_protection_recovery_gross"] = (
        (snap.get("realized_protection_recovery_gross") or 0.0) + gross_value)
    snap["realized_protection_recovery_fees"] = (
        (snap.get("realized_protection_recovery_fees") or 0.0) + fee)
    snap["realized_protection_recovery_value"] = (
        (snap.get("realized_protection_recovery_value") or 0.0) + net_value)
    detail["sold"] = sold
    detail["avg_price"] = price
    detail["gross_recovery_value"] = gross_value
    detail["recovery_fee"] = fee
    detail["net_recovery_value"] = net_value
    _append_execution_history(snap, "protection_recovery_history", detail, now_ms)
    _recompute_option_realized_pnl(snap)
    _G(_POSITION_KEY, snap)
    return snap


def _evaluate_hedge(snap, quote_fn=None):
    """对冲决策（场所感知）：按 HEDGE_VENUE 选 Deribit(反向) 或 Binance(线性) → perp 真实持仓 +
    目标(随剩余短腿敞口) + open/reduce 动作 + 孤儿。默认不真实下单。"""
    rem_qty = (snap or {}).get("remaining_short_qty") or 0.0
    long_qty = (snap or {}).get("long_remaining_qty")
    if long_qty is None:
        long_qty = (snap or {}).get("long_fill_amount") or 0.0
    settlement_state = (snap or {}).get("settlement_state")
    settled = settlement_state in ("SHORT_SETTLED", "BOTH_LEGS_SETTLED", "SETTLED")
    if settled:
        rem_qty = 0.0
    vcfg = hedge_venue_config(HEDGE_VENUE, HEDGE_BINANCE_INSTRUMENT, HEDGE_BINANCE_EXCHANGE_INDEX)
    state = "SETTLED" if rem_qty <= 0 else "OPEN"
    si, li = (snap or {}).get("short_instrument"), (snap or {}).get("long_instrument")
    quote = quote_fn or exec_quote
    sq = {} if state == "SETTLED" or not si else (quote(si) or {})
    lq = {} if state == "SETTLED" or not li else (quote(li) or {})
    short_delta = None if state == "SETTLED" else sq.get("delta")
    prot_delta = None if state == "SETTLED" else lq.get("delta")
    short_gamma = None if state == "SETTLED" else sq.get("gamma")
    prot_gamma = None if state == "SETTLED" else lq.get("gamma")
    gamma_fraction = None
    gamma_data_state = None
    settlement_orphan = False
    settlement_reason = None
    hedge_pnl_usd = None
    if vcfg["venue"] == "BINANCE":
        snap_bnc = bnc_get_position_snapshot(vcfg["instrument"])
        perp_qty = None if snap_bnc is None else snap_bnc.get("qty")
        hedge_pnl_usd = None if snap_bnc is None else snap_bnc.get("unrealized_pnl_usd")
        contract_size, min_trade = 1.0, HEDGE_BINANCE_MIN_TRADE
    else:
        try:
            perp = dbt_get_positions(SETTLEMENT_CURRENCY, "future") or []
        except Exception:
            perp = []
        perp_qty = sum((p.get("size") or 0.0) for p in perp)
        meta = dbt_get_instrument(vcfg["instrument"]) or {}
        contract_size = meta.get("contract_size") or HEDGE_CONTRACT_SIZE_FALLBACK
        min_trade = meta.get("min_trade_amount") or HEDGE_MIN_TRADE_FALLBACK
    if perp_qty is None:
        action = {"action": "HEDGE_HOLD", "reduce_only": False, "delta_contracts": 0.0,
                  "blocked": "HEDGE_POSITION_DATA_GAP"}
        return {"perp_qty": None, "target": None, "action": action,
                "orphan": False, "side": hedge_side((snap or {}).get("side")),
                "net_delta": None, "net_option_delta": None,
                "direction_consistent": True, "venue": vcfg["venue"],
                "instrument": vcfg["instrument"], "venue_cfg": vcfg,
                "short_gamma": short_gamma, "protection_gamma": prot_gamma,
                "gamma_fraction": gamma_fraction, "gamma_data_state": gamma_data_state,
                "unrealized_pnl_usd": hedge_pnl_usd,
                "data_gap": "HEDGE_POSITION_DATA_GAP"}
    sg = settlement_guard(rem_qty, False, state == "SETTLED", perp_qty)
    if sg.get("target") == 0.0:
        state = "SETTLED"
    settlement_orphan = bool(sg.get("orphan"))
    settlement_reason = sg.get("reason")
    if state == "SETTLED":
        net_opt = 0.0
        target = 0.0
    elif short_delta is None:
        action = {"action": "HEDGE_HOLD", "reduce_only": False, "delta_contracts": 0.0,
                  "blocked": "HEDGE_DELTA_DATA_GAP"}
        return {"perp_qty": perp_qty, "target": None, "action": action,
                "orphan": hedge_orphan(rem_qty, perp_qty),
                "side": hedge_side((snap or {}).get("side")),
                "net_delta": None, "net_option_delta": None,
                "direction_consistent": True, "venue": vcfg["venue"],
                "instrument": vcfg["instrument"], "venue_cfg": vcfg,
                "short_gamma": short_gamma, "protection_gamma": prot_gamma,
                "gamma_fraction": gamma_fraction, "gamma_data_state": gamma_data_state,
                "unrealized_pnl_usd": hedge_pnl_usd,
                "data_gap": "HEDGE_DELTA_DATA_GAP"}
    else:
        net_opt = option_net_delta(rem_qty, short_delta, long_qty, prot_delta)
        spot = _spot_price()
        target_ratio = 1.0 if HEDGE_GAMMA_AWARE_ENABLED else HEDGE_REDUCTION_RATIO
        target = hedge_target_position(net_opt, target_ratio, spot,
                                       contract_size, min_trade, linear=vcfg["linear"])
        if HEDGE_GAMMA_AWARE_ENABLED:
            gamma_fraction = hedge_gamma_fraction(
                short_gamma, prot_gamma, rem_qty, long_qty, spot,
                HEDGE_GAMMA_NORM_REF, HEDGE_GAMMA_FRAC_FLOOR)
            gamma_data_state = ("OK" if isinstance(short_gamma, (int, float))
                                and not isinstance(short_gamma, bool) else "GAMMA_DATA_FLOOR")
    action = hedge_order_action(perp_qty, target, min_trade)
    delta_to_trade = (target or 0.0) - (perp_qty or 0.0)
    side = "buy" if delta_to_trade > 0 else ("sell" if delta_to_trade < 0 else hedge_side((snap or {}).get("side")))
    struct_delta = structure_net_delta(short_delta, prot_delta)
    consistent = hedge_direction_consistent((snap or {}).get("side"), struct_delta)
    if not consistent and action["action"] in ("HEDGE_OPEN", "HEDGE_INCREASE"):
        action = {"action": "HEDGE_HOLD", "reduce_only": False, "delta_contracts": 0.0,
                  "blocked": "DIRECTION_INCONSISTENT"}
    return {"perp_qty": perp_qty, "target": target, "action": action,
            "orphan": bool(settlement_orphan or hedge_orphan(rem_qty, perp_qty)),
            "side": side,
            "net_delta": struct_delta, "net_option_delta": net_opt,
            "delta_to_trade": delta_to_trade,
            "direction_consistent": consistent,
            "venue": vcfg["venue"], "instrument": vcfg["instrument"], "venue_cfg": vcfg,
            "short_gamma": short_gamma, "protection_gamma": prot_gamma,
            "gamma_fraction": gamma_fraction, "gamma_data_state": gamma_data_state,
            "target_semantics": ("RAW_FULL_DELTA" if HEDGE_GAMMA_AWARE_ENABLED else "V313_REDUCTION_RATIO"),
            "unrealized_pnl_usd": hedge_pnl_usd,
            "settlement_reason": settlement_reason}


def _hedge_policy_default_state(position_id=None):
    return {
        "policy": "V32",
        "position_id": position_id,
        "hedge_epoch": 0,
        "full_target_qty": 0.0,
        "eff_target_qty": 0.0,
        "current_hedge_qty": 0.0,
        "pending_order_id": None,
        "pending_order_side": None,
        "pending_order_qty": 0.0,
        "pending_order_created_ts": 0,
        "pending_is_add": False,
        "pending_reduce_only": False,
        "soft_since_ts": 0,
        "reduce_since_ts": 0,
        "add_cooldown_until": 0,
        "reduce_cooldown_until": 0,
        "last_fill_ts": 0,
        "last_fill_qty": 0.0,
        "last_fill_price": None,
        "last_action": None,
        "last_trigger_state": "NONE",
        "last_p_now": None,
        "last_drift": None,
        "crash_ref_price": None,
        "crash_ref_ts": 0,
        "last_crash_adverse_bps": 0.0,
        "episode_cost_usdc": 0.0,
        "episode_cost_bps": 0.0,
        "last_submit_unknown_ts": 0,
        "last_submit_unknown_reason": None,
    }


def _hedge_policy_load_state_raw():
    st = _G(_HEDGE_POLICY_STATE_KEY)
    if isinstance(st, dict):
        return st
    old = _G(_HEDGE_POLICY_STATE_KEY_V313)
    if isinstance(old, dict):
        migrated = dict(old)
        migrated["policy"] = "V32"
        _G(_HEDGE_POLICY_STATE_KEY, migrated)
        _G(_HEDGE_POLICY_STATE_KEY_V313, None)
        return migrated
    return st


def _hedge_policy_state(snap=None):
    pos_id = (snap or {}).get("position_id")
    st = _hedge_policy_load_state_raw()
    if not isinstance(st, dict) or st.get("position_id") != pos_id:
        st = _hedge_policy_default_state(pos_id)
        _G(_HEDGE_POLICY_STATE_KEY, st)
        _G(_HEDGE_POLICY_STATE_KEY_V313, None)
    return dict(st)


def _hedge_policy_save_state(st):
    _G(_HEDGE_POLICY_STATE_KEY, dict(st or {}))
    _G(_HEDGE_POLICY_STATE_KEY_V313, None)
    return st


def _hedge_policy_v32_enabled():
    return bool(globals().get("HEDGE_POLICY_V32_ENABLED",
                              globals().get("HEDGE_POLICY_V313_ENABLED", True)))


def _hedge_policy_enabled_for(hedge):
    return bool(_hedge_policy_v32_enabled() and (hedge or {}).get("venue") == "BINANCE")


def _hedge_policy_order_filled(order):
    if not isinstance(order, dict):
        return 0.0
    for k in ("DealAmount", "deal_amount", "filled_amount", "filled", "Filled"):
        v = order.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return 0.0


def _hedge_policy_order_avg(order):
    if not isinstance(order, dict):
        return None
    for k in ("AvgPrice", "avg_price", "average_price", "Price", "price"):
        v = order.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            return float(v)
    return None


def _hedge_policy_order_active(order):
    if not isinstance(order, dict):
        return False
    st = order.get("Status")
    if st is None:
        st = order.get("status") or order.get("State") or order.get("state")
    if st in (0, "0", "open", "new", "NEW", "pending", "PARTIALLY_FILLED",
              "partially_filled"):
        return True
    return False


def _hedge_policy_detail(st, hedge, risk, trigger_state, reason, full_target,
                         eff_target, current, delta, action, cross_bps,
                         warnings=None, wants_action=False,
                         soft_ratio=None, rebalance_deadband=None,
                         min_hold_until=None, crash_adverse_bps=None):
    cr = (risk or {}).get("current_risk") or {}
    detail = {
        "policy": "V32",
        "position_id": st.get("position_id"),
        "state": trigger_state,
        "trigger_state": trigger_state,
        "reason": reason,
        "warnings": list(warnings or []),
        "full_target_qty": full_target,
        "eff_target_qty": eff_target,
        "current_hedge_qty": current,
        "delta_to_trade": delta,
        "pending_order_id": st.get("pending_order_id"),
        "pending_order_side": st.get("pending_order_side"),
        "pending_order_qty": st.get("pending_order_qty"),
        "pending_order_created_ts": st.get("pending_order_created_ts"),
        "cross_bps": cross_bps,
        "soft_ratio": soft_ratio,
        "gamma_fraction": (hedge or {}).get("gamma_fraction"),
        "gamma_data_state": (hedge or {}).get("gamma_data_state"),
        "rebalance_deadband": rebalance_deadband,
        "final3_mode": HEDGE_FINAL3H_MODE,
        "crash_adverse_bps": crash_adverse_bps,
        "min_hold_until": min_hold_until,
        "target_semantics": (hedge or {}).get("target_semantics"),
        "soft_since_ts": st.get("soft_since_ts") or 0,
        "reduce_since_ts": st.get("reduce_since_ts") or 0,
        "add_cooldown_until": st.get("add_cooldown_until") or 0,
        "reduce_cooldown_until": st.get("reduce_cooldown_until") or 0,
        "last_fill_ts": st.get("last_fill_ts") or 0,
        "last_fill_qty": st.get("last_fill_qty") or 0.0,
        "last_fill_price": st.get("last_fill_price"),
        "episode_cost_usdc": st.get("episode_cost_usdc") or 0.0,
        "episode_cost_bps": st.get("episode_cost_bps") or 0.0,
        "p_entry": cr.get("entry_touch_probability"),
        "p_now": cr.get("touch_probability_now"),
        "drift": cr.get("touch_probability_drift"),
        "wants_action": bool(wants_action),
    }
    if (hedge or {}).get("data_gap"):
        detail["data_gap"] = hedge.get("data_gap")
    return detail


def _hedge_policy_hold(hedge, st, risk, trigger_state, reason, full_target=None,
                       eff_target=None, current=None, warnings=None,
                       resolved_fill=None):
    out = dict(hedge or {})
    out["action"] = {"action": "HEDGE_HOLD", "reduce_only": False,
                     "delta_contracts": 0.0, "blocked": reason}
    out["delta_to_trade"] = 0.0
    if resolved_fill:
        out["policy_resolved_fill"] = resolved_fill
    out["policy_detail"] = _hedge_policy_detail(
        st, out, risk, trigger_state, reason, full_target, eff_target, current,
        0.0, out["action"], HEDGE_SOFT_CROSS_BPS, warnings, wants_action=False)
    return out


def _hedge_policy_clear_pending(st):
    st["pending_order_id"] = None
    st["pending_order_side"] = None
    st["pending_order_qty"] = 0.0
    st["pending_order_created_ts"] = 0
    st["pending_is_add"] = False
    st["pending_reduce_only"] = False


def _hedge_policy_record_pending_fill(st, order, now_ms):
    filled = _hedge_policy_order_filled(order)
    st["last_fill_ts"] = now_ms
    st["last_fill_qty"] = filled
    st["last_fill_price"] = _hedge_policy_order_avg(order)
    st["last_action"] = "ADD" if st.get("pending_is_add") else "REDUCE"
    if HEDGE_COOLDOWN_ENABLED:
        if st.get("pending_is_add"):
            st["reduce_cooldown_until"] = now_ms + HEDGE_REDUCE_COOLDOWN_SECONDS * 1000
        else:
            st["add_cooldown_until"] = now_ms + HEDGE_ADD_COOLDOWN_SECONDS * 1000


def _hedge_policy_pending_fill_event(st, hedge, order, reason):
    return {
        "venue": "BINANCE",
        "instrument": (hedge or {}).get("instrument") or HEDGE_BINANCE_INSTRUMENT,
        "symbol": (hedge or {}).get("instrument") or HEDGE_BINANCE_INSTRUMENT,
        "side": st.get("pending_order_side"),
        "amount": st.get("pending_order_qty") or 0.0,
        "filled": _hedge_policy_order_filled(order),
        "avg_price": _hedge_policy_order_avg(order),
        "order_id": st.get("pending_order_id"),
        "reduce_only": bool(st.get("pending_reduce_only")),
        "dry": False,
        "reason": reason,
    }


def _hedge_policy_resolve_pending(st, hedge, risk, now_ms):
    oid = st.get("pending_order_id")
    if not oid:
        return None
    symbol = (hedge or {}).get("instrument") or HEDGE_BINANCE_INSTRUMENT
    idx = ((hedge or {}).get("venue_cfg") or {}).get("exchange_index")
    created = st.get("pending_order_created_ts") or 0
    age = max(0, now_ms - created)
    stale_ms = max(0, HEDGE_PENDING_STALE_SECONDS) * 1000
    order = bnc_get_hedge_order(symbol, oid, idx=idx)
    if order is None:
        if age >= stale_ms:
            if not bnc_cancel_hedge_order(symbol, oid, idx=idx):
                return _hedge_policy_hold(hedge, st, risk, "HOLD",
                                          "PENDING_STALE_CANCEL_FAILED")
            _hedge_policy_clear_pending(st)
            _hedge_policy_save_state(st)
            return _hedge_policy_hold(hedge, st, risk, "HOLD",
                                      "PENDING_STALE_RECOVERED")
        return _hedge_policy_hold(hedge, st, risk, "HOLD", "PENDING_ACTIVE")
    filled = _hedge_policy_order_filled(order)
    active = _hedge_policy_order_active(order)
    pending_qty = st.get("pending_order_qty") or 0.0
    remaining = max(0.0, pending_qty - filled)
    if filled > 0:
        if active and remaining > 1e-12 and age < stale_ms:
            st["last_fill_ts"] = now_ms
            st["last_fill_qty"] = filled
            st["last_fill_price"] = _hedge_policy_order_avg(order)
            _hedge_policy_save_state(st)
            return _hedge_policy_hold(hedge, st, risk, "HOLD",
                                      "PENDING_PARTIAL_ACTIVE")
        resolved = _hedge_policy_pending_fill_event(st, hedge, order,
                                                    "PENDING_FILLED")
        _hedge_policy_record_pending_fill(st, order, now_ms)
        if active and remaining > 1e-12:
            if not bnc_cancel_hedge_order(symbol, oid, idx=idx):
                return _hedge_policy_hold(hedge, st, risk, "HOLD",
                                          "PENDING_STALE_CANCEL_FAILED")
            resolved["reason"] = "PENDING_STALE_PARTIAL_FILLED"
        _hedge_policy_clear_pending(st)
        _hedge_policy_save_state(st)
        return _hedge_policy_hold(hedge, st, risk, "HOLD", resolved["reason"],
                                  resolved_fill=resolved)
    if active and age < stale_ms:
        return _hedge_policy_hold(hedge, st, risk, "HOLD", "PENDING_ACTIVE")
    if active:
        if not bnc_cancel_hedge_order(symbol, oid, idx=idx):
            return _hedge_policy_hold(hedge, st, risk, "HOLD",
                                      "PENDING_STALE_CANCEL_FAILED")
        _hedge_policy_clear_pending(st)
        _hedge_policy_save_state(st)
        return _hedge_policy_hold(hedge, st, risk, "HOLD", "PENDING_STALE_RECOVERED")
    _hedge_policy_clear_pending(st)
    _hedge_policy_save_state(st)
    return _hedge_policy_hold(hedge, st, risk, "HOLD", "PENDING_CLEARED")


def _hedge_policy_trigger_state(risk):
    risk = risk or {}
    codes = set(risk.get("reason_codes") or [])
    cr = risk.get("current_risk") or {}
    p_now = cr.get("touch_probability_now")
    drift = cr.get("touch_probability_drift")
    emergency = cr.get("emergency_probability")
    open_p = cr.get("open_probability")
    min_drift = cr.get("min_probability_drift_to_open") or 0.0
    hard = ("BOUNDARY_BREACHED" in codes or "EMERGENCY_TOUCH_PROBABILITY" in codes)
    if isinstance(p_now, (int, float)) and isinstance(emergency, (int, float)) and p_now >= emergency:
        hard = True
    if isinstance(drift, (int, float)) and drift >= HEDGE_HARD_DRIFT:
        hard = True
    if hard:
        return "HARD"
    soft = "TOUCH_PROBABILITY_DETERIORATED" in codes
    if isinstance(p_now, (int, float)) and isinstance(open_p, (int, float)) and p_now >= open_p:
        if not isinstance(drift, (int, float)) or drift >= min_drift:
            soft = True
    return "SOFT" if soft else "NONE"


def _hedge_policy_current_price(risk):
    cr = (risk or {}).get("current_risk") or {}
    inp = (risk or {}).get("display_inputs") or {}
    for value in (cr.get("current_price"), inp.get("current_price")):
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
            return float(value)
    return None


def _hedge_policy_adverse_bps(side, ref_price, current_price):
    if not (isinstance(ref_price, (int, float)) and isinstance(current_price, (int, float))):
        return 0.0
    if ref_price <= 0 or current_price <= 0:
        return 0.0
    s = str(side or "").upper()
    if s in ("CALL", "SHORT_CALL"):
        return max(0.0, (current_price - ref_price) / ref_price * 10000.0)
    if s in ("PUT", "SHORT_PUT"):
        return max(0.0, (ref_price - current_price) / ref_price * 10000.0)
    return 0.0


def _hedge_policy_crash_trigger(st, snap, risk, now_ms):
    price = _hedge_policy_current_price(risk)
    if not HEDGE_CRASH_ENABLED or price is None:
        st["last_crash_adverse_bps"] = 0.0
        return False
    window_ms = max(1, HEDGE_CRASH_SPEED_WINDOW_SECONDS) * 1000
    ref_price = st.get("crash_ref_price")
    ref_ts = st.get("crash_ref_ts") or 0
    if not isinstance(ref_price, (int, float)) or now_ms - ref_ts > window_ms:
        st["crash_ref_price"] = price
        st["crash_ref_ts"] = now_ms
        st["last_crash_adverse_bps"] = 0.0
        return False
    adverse_bps = _hedge_policy_adverse_bps((snap or {}).get("side"), ref_price, price)
    st["last_crash_adverse_bps"] = adverse_bps
    return adverse_bps >= HEDGE_CRASH_MOVE_BPS


def _hedge_policy_in_final3h(snap, now_ms):
    dte_h = _dte_hours_to((snap or {}).get("short_expiry_ts"), now_ms)
    return dte_h is not None and dte_h <= TAKE_PROFIT_MIN_DTE_HOURS + 1e-12


def _hedge_policy_action(current, eff_target, min_trade, forced_reason=None, deadband=None):
    delta = (eff_target or 0.0) - (current or 0.0)
    side = "buy" if delta > 0 else ("sell" if delta < 0 else None)
    forced_unwind = forced_reason in ("ORPHAN_HEDGE_UNWIND", "REVERSE_HEDGE_UNWIND")
    threshold = max(min_trade, 0.0) if forced_unwind else max(min_trade, deadband or 0.0)
    if abs(delta) < threshold:
        reason = "TARGET_BAND_DEADBAND" if threshold > max(min_trade, 0.0) else "LOT_DEADBAND"
        return {"action": "HEDGE_HOLD", "reduce_only": False,
                "delta_contracts": 0.0, "blocked": reason}, 0.0, None, False
    reducing = abs(eff_target or 0.0) < abs(current or 0.0)
    reduce_only = bool(reducing)
    if abs(eff_target or 0.0) <= 1e-12:
        name = "HEDGE_UNWIND"
        reduce_only = True
    elif reducing:
        name = "HEDGE_REDUCE"
    elif abs(current or 0.0) < min_trade:
        name = "HEDGE_OPEN"
    else:
        name = "HEDGE_INCREASE"
    if forced_reason in ("ORPHAN_HEDGE_UNWIND", "REVERSE_HEDGE_UNWIND"):
        name = "HEDGE_UNWIND"
        reduce_only = True
    return {"action": name, "reduce_only": reduce_only,
            "delta_contracts": abs(delta)}, delta, side, True


def _hedge_policy_plan(snap, hedge, risk, now_ms):
    if not _hedge_policy_enabled_for(hedge):
        st = _hedge_policy_state(snap)
        out = dict(hedge or {})
        current = out.get("perp_qty")
        full_target = out.get("target")
        st["current_hedge_qty"] = current
        _hedge_policy_save_state(st)
        return _hedge_policy_hold(out, st, risk, "HOLD",
                                  "HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT",
                                  full_target, current, current)
    st = _hedge_policy_state(snap)
    pending = _hedge_policy_resolve_pending(st, hedge, risk, now_ms)
    if pending is not None:
        return pending

    out = dict(hedge or {})
    current = out.get("perp_qty")
    full_target = out.get("target")
    min_trade = HEDGE_BINANCE_MIN_TRADE
    warnings = []
    unknown_ts = st.get("last_submit_unknown_ts") or 0
    unknown_window_ms = max(0, HEDGE_PENDING_STALE_SECONDS) * 1000
    if unknown_ts and now_ms - unknown_ts < unknown_window_ms:
        st["current_hedge_qty"] = current
        _hedge_policy_save_state(st)
        return _hedge_policy_hold(out, st, risk, "HOLD", "SUBMIT_UNKNOWN_RECENT",
                                  full_target, current, current)
    if unknown_ts:
        st["last_submit_unknown_ts"] = 0
        st["last_submit_unknown_reason"] = None
    if out.get("data_gap") == "HEDGE_POSITION_DATA_GAP" or current is None:
        st["current_hedge_qty"] = None
        _hedge_policy_save_state(st)
        return _hedge_policy_hold(out, st, risk, "HOLD", "POSITION_READ_FAILED",
                                  full_target, None, None)
    current = float(current or 0.0)
    if full_target is None:
        st["current_hedge_qty"] = current
        _hedge_policy_save_state(st)
        return _hedge_policy_hold(out, st, risk, "HOLD", out.get("data_gap") or "TARGET_DATA_GAP",
                                  None, None, current)
    full_target = float(full_target or 0.0)
    rebalance_deadband = hedge_rebalance_deadband(
        full_target, min_trade, HEDGE_REBALANCE_BAND_FRAC)
    soft_ratio = None
    min_hold_until = None
    rem_short = (snap or {}).get("remaining_short_qty") or 0.0
    forced_reason = None
    trigger_state = _hedge_policy_trigger_state(risk)
    if _hedge_policy_crash_trigger(st, snap, risk, now_ms):
        trigger_state = "CRASH"
    crash_adverse_bps = st.get("last_crash_adverse_bps") or 0.0
    cr = (risk or {}).get("current_risk") or {}
    p_now = cr.get("touch_probability_now")
    drift = cr.get("touch_probability_drift")

    if rem_short <= 1e-12 and abs(current) >= min_trade:
        eff_target = 0.0
        forced_reason = "ORPHAN_HEDGE_UNWIND"
        trigger_state = "HOLD"
    elif out.get("orphan") and abs(current) >= min_trade:
        eff_target = 0.0
        forced_reason = "ORPHAN_HEDGE_UNWIND"
        trigger_state = "HOLD"
    elif abs(current) >= min_trade and abs(full_target) >= min_trade and current * full_target < 0:
        eff_target = 0.0
        forced_reason = "REVERSE_HEDGE_UNWIND"
        trigger_state = "HARD"
    elif trigger_state in ("HARD", "CRASH"):
        eff_target = full_target
        forced_reason = "CRASH_TRIGGER_SPEED" if trigger_state == "CRASH" else "HARD_TRIGGER_EMERGENCY"
    elif trigger_state == "SOFT":
        if HEDGE_STAGING_ENABLED:
            if not st.get("soft_since_ts"):
                st["soft_since_ts"] = now_ms
            persisted = (now_ms - (st.get("soft_since_ts") or now_ms)) >= HEDGE_SOFT_PERSIST_SECONDS * 1000
            last_p = st.get("last_p_now")
            worsened = (isinstance(p_now, (int, float)) and isinstance(last_p, (int, float))
                        and p_now - last_p >= HEDGE_SOFT_ADD_DRIFT_STEP)
            gamma_frac = out.get("gamma_fraction")
            if not isinstance(gamma_frac, (int, float)) or isinstance(gamma_frac, bool):
                gamma_frac = HEDGE_GAMMA_FRAC_FLOOR
            soft_ratio = hedge_target_ratio_for_soft(
                HEDGE_SOFT_INITIAL_RATIO, gamma_frac, persisted, worsened)
            eff_target = full_target * soft_ratio
            forced_reason = "SOFT_TRIGGER_CONFIRMED" if soft_ratio >= 1.0 else "SOFT_TRIGGER_INITIAL"
        else:
            eff_target = full_target
            forced_reason = "SOFT_TRIGGER_CONFIRMED"
            soft_ratio = 1.0
    else:
        st["soft_since_ts"] = 0
        watch = cr.get("watch_probability")
        buffer = HEDGE_REDUCE_PROB_BUFFER if HEDGE_HYSTERESIS_ENABLED else 0.0
        if abs(current) >= min_trade and isinstance(p_now, (int, float)) \
                and isinstance(watch, (int, float)) and p_now < watch:
            if not st.get("reduce_since_ts"):
                st["reduce_since_ts"] = now_ms
            reduce_line = watch - buffer
            persisted = (now_ms - (st.get("reduce_since_ts") or now_ms)) >= HEDGE_REDUCE_PERSIST_SECONDS * 1000
            if HEDGE_HYSTERESIS_ENABLED and (p_now > reduce_line or not persisted):
                st["full_target_qty"] = full_target
                st["eff_target_qty"] = current
                st["current_hedge_qty"] = current
                st["last_trigger_state"] = trigger_state
                st["last_p_now"] = p_now
                st["last_drift"] = drift
                _hedge_policy_save_state(st)
                return _hedge_policy_hold(out, st, risk, "HOLD", "REDUCE_HYSTERESIS_WAIT",
                                          full_target, current, current)
            eff_target = 0.0
            forced_reason = "REDUCE_CONFIRMED"
            trigger_state = "HOLD"
        else:
            st["reduce_since_ts"] = 0
            eff_target = 0.0 if abs(current) < min_trade else current
            forced_reason = "NO_TRIGGER" if abs(current) < min_trade else "HOLD_EXISTING"
            trigger_state = "NONE"

    action, delta, side, wants = _hedge_policy_action(
        current, eff_target, min_trade, forced_reason, rebalance_deadband)
    reason = action.get("blocked") or forced_reason or "NO_TRIGGER"
    is_add = wants and not action.get("reduce_only")
    is_reduce = wants and action.get("reduce_only")
    if is_reduce and forced_reason not in ("ORPHAN_HEDGE_UNWIND", "REVERSE_HEDGE_UNWIND") \
            and HEDGE_MIN_HOLD_SECONDS > 0 and st.get("last_action") == "ADD":
        last_fill_ts = st.get("last_fill_ts") or 0
        if last_fill_ts:
            min_hold_until = last_fill_ts + HEDGE_MIN_HOLD_SECONDS * 1000
            if now_ms < min_hold_until:
                action = {"action": "HEDGE_HOLD", "reduce_only": False,
                          "delta_contracts": 0.0, "blocked": "REDUCE_MIN_HOLD_ACTIVE"}
                delta = 0.0
                side = None
                wants = False
                is_reduce = False
                reason = "REDUCE_MIN_HOLD_ACTIVE"
    if is_add and trigger_state == "SOFT" and HEDGE_FINAL3H_MODE == "SUPPRESS_SOFT_ADD" \
            and _hedge_policy_in_final3h(snap, now_ms):
        action = {"action": "HEDGE_HOLD", "reduce_only": False,
                  "delta_contracts": 0.0, "blocked": "FINAL3H_SOFT_ADD_SUPPRESSED"}
        delta = 0.0
        side = None
        wants = False
        is_add = False
        reason = "FINAL3H_SOFT_ADD_SUPPRESSED"
    if is_add and trigger_state not in ("HARD", "CRASH") and HEDGE_COOLDOWN_ENABLED \
            and (st.get("add_cooldown_until") or 0) > now_ms:
        action = {"action": "HEDGE_HOLD", "reduce_only": False,
                  "delta_contracts": 0.0, "blocked": "ADD_COOLDOWN_ACTIVE"}
        delta = 0.0
        side = None
        wants = False
        is_add = False
        reason = "ADD_COOLDOWN_ACTIVE"
    if is_reduce and forced_reason not in ("ORPHAN_HEDGE_UNWIND", "REVERSE_HEDGE_UNWIND") \
            and HEDGE_COOLDOWN_ENABLED and (st.get("reduce_cooldown_until") or 0) > now_ms:
        action = {"action": "HEDGE_HOLD", "reduce_only": False,
                  "delta_contracts": 0.0, "blocked": "REDUCE_COOLDOWN_ACTIVE"}
        delta = 0.0
        side = None
        wants = False
        is_reduce = False
        reason = "REDUCE_COOLDOWN_ACTIVE"
    if (st.get("episode_cost_bps") or 0.0) > HEDGE_EPISODE_COST_ALERT_BPS:
        warnings.append("EPISODE_COST_ALERT")
    cross_bps = HEDGE_HARD_CROSS_BPS if trigger_state in ("HARD", "CRASH") else HEDGE_SOFT_CROSS_BPS
    out["action"] = action
    if side:
        out["side"] = side
    out["delta_to_trade"] = delta
    st["full_target_qty"] = full_target
    st["eff_target_qty"] = eff_target
    st["current_hedge_qty"] = current
    st["last_trigger_state"] = trigger_state
    st["last_p_now"] = p_now
    st["last_drift"] = drift
    _hedge_policy_save_state(st)
    out["policy_detail"] = _hedge_policy_detail(
        st, out, risk, trigger_state, reason, full_target, eff_target,
        current, delta, action, cross_bps, warnings, wants_action=wants,
        soft_ratio=soft_ratio, rebalance_deadband=rebalance_deadband,
        min_hold_until=min_hold_until, crash_adverse_bps=crash_adverse_bps)
    return out


def _hedge_policy_submit(hedge, now_ms, allow_live=True):
    detail = (hedge or {}).get("policy_detail") or {}
    action = (hedge or {}).get("action") or {}
    amount = action.get("delta_contracts") or 0.0
    if action.get("action") == "HEDGE_HOLD" or amount <= 0:
        return {"filled": 0.0, "dry": (not allow_live), "venue": "BINANCE",
                "reason": action.get("blocked") or detail.get("reason") or "NO_OP"}
    venue_cfg = (hedge or {}).get("venue_cfg") or {}
    result = bnc_submit_hedge_order(
        symbol=(hedge or {}).get("instrument") or HEDGE_BINANCE_INSTRUMENT,
        side=(hedge or {}).get("side"),
        amount=amount,
        reduce_only=bool(action.get("reduce_only")),
        cross_bps=detail.get("cross_bps") if detail.get("cross_bps") is not None else HEDGE_SOFT_CROSS_BPS,
        allow_live=allow_live,
        idx=venue_cfg.get("exchange_index"),
        execution_style=HEDGE_OPEN_EXECUTION_STYLE)
    oid = (result or {}).get("order_id")
    if (result or {}).get("reason") == "BINANCE_ORDER_ID_MISSING":
        stored = _hedge_policy_load_state_raw()
        st = dict(stored) if isinstance(stored, dict) else _hedge_policy_default_state()
        st["last_submit_unknown_ts"] = now_ms
        st["last_submit_unknown_reason"] = "BINANCE_ORDER_ID_MISSING"
        st["pending_order_id"] = None
        _hedge_policy_save_state(st)
        return result
    if oid:
        stored = _hedge_policy_load_state_raw()
        st = dict(stored) if isinstance(stored, dict) else _hedge_policy_default_state()
        st["pending_order_id"] = oid
        st["pending_order_side"] = (hedge or {}).get("side")
        st["pending_order_qty"] = amount
        st["pending_order_created_ts"] = now_ms
        st["pending_is_add"] = not bool(action.get("reduce_only"))
        st["pending_reduce_only"] = bool(action.get("reduce_only"))
        st["last_submit_unknown_ts"] = 0
        st["last_submit_unknown_reason"] = None
        st["hedge_epoch"] = (st.get("hedge_epoch") or 0) + 1
        _hedge_policy_save_state(st)
    return result


def _exit_friction_from_short_quote(short_quote):
    sr = exec_spread_ratio(short_quote)
    return {"option_exit_friction": ("HIGH" if sr is None or sr > MAX_SPREAD_RATIO else "LOW"),
            "future_hedge_friction": "LOW"}


def _evaluate_position_risk_now(snap, now_ms, existing_hedge=False, quote_fn=None):
    """持仓后风险评估（接 hedge_risk.evaluate_position_risk）：入场风险锚 + 当前短腿行情 →
    PositionRiskPackage（触界概率/漂移/尾部加速/持续性 → tail_risk_state）。
    无快照 / 无入场锚 → None（不驱动主动退出/对冲，保守留给止盈资格 + 孤儿）。
    注：无执行侧风险上下文时 persistence 恒 LOW；有人工审计/执行风险上下文时进入持续性判定。"""
    if not snap:
        return None
    if ((snap.get("remaining_short_qty") or 0.0) <= 1e-12
            or snap.get("settlement_state") in ("SHORT_SETTLED", "BOTH_LEGS_SETTLED", "SETTLED")):
        return {"tail_risk_state": None, "market_data_gap": False,
                "current_risk": {}, "reason_codes": ["OPTION_SETTLED_NO_SHORT_RISK"]}
    anchor = snap.get("entry_risk_anchor")
    if not anchor:
        return None
    if (snap or {}).get("hedge_trigger_policy"):
        anchor = dict(anchor, hedge_trigger_policy=snap.get("hedge_trigger_policy"))
    quote = quote_fn or exec_quote
    sq = quote(snap.get("short_instrument")) or {}
    # F3：短腿盘口缺 delta 且缺 IV → 无法估触界概率 → 显式数据缺口（不静默判 NORMAL，面板红标）
    if sq.get("delta") is None and sq.get("mark_iv") is None:
        return {"tail_risk_state": None, "market_data_gap": True,
                "current_risk": {}, "reason_codes": ["RISK_MARKET_DATA_GAP"]}
    dte_h = _dte_hours_to(snap.get("short_expiry_ts"), now_ms)
    if dte_h is None:
        dte_h = anchor.get("entry_dte_hours")
    out = evaluate_position_risk(
        position_id=snap.get("position_id"),
        direction_bias=_side_to_direction_bias(snap.get("side")),
        entry_risk_anchor=anchor, current_price=_spot_price(),
        dte_hours=dte_h, short_delta=sq.get("delta"), short_gamma=sq.get("gamma"),
        iv=sq.get("mark_iv"), loss_boundary=anchor.get("entry_loss_boundary"),
        edb=None,
        gamma_regime=None,
        exit_friction=_exit_friction_from_short_quote(sq),
        existing_hedge=existing_hedge)
    if out:
        out["display_inputs"] = {
            "direction_bias": _side_to_direction_bias(snap.get("side")),
            "current_price": _spot_price(),
            "dte_hours": dte_h,
            "short_delta": sq.get("delta"),
            "iv": sq.get("mark_iv"),
            "loss_boundary": anchor.get("entry_loss_boundary"),
        }
    return out


def _manage_in_flight_orders(snap, hedge):
    instruments = set(i for i in (
        (snap or {}).get("short_instrument"),
        (snap or {}).get("long_instrument"),
        (hedge or {}).get("instrument"),
    ) if i)
    if not instruments:
        return {"count": 0, "orders": []}
    try:
        orders = dbt_get_open_orders(SETTLEMENT_CURRENCY) or []
    except Exception:
        return {"count": 0, "orders": []}
    matched = []
    for o in orders:
        if o.get("instrument_name") in instruments:
            matched.append({"instrument_name": o.get("instrument_name"),
                            "label": o.get("label")})
    return {"count": len(matched), "orders": matched[:5]}


def _safe_mul(a, b):
    return a * b if isinstance(a, (int, float)) and isinstance(b, (int, float)) else None


def _safe_usd(btc_value, spot):
    return btc_value * spot if isinstance(btc_value, (int, float)) and isinstance(spot, (int, float)) else None


def _quote_display(q):
    q = q or {}
    return {"mark": q.get("mark"), "bid": q.get("best_bid"), "ask": q.get("best_ask")}


def _hedge_pnl_display(hedge):
    hedge = hedge or {}
    qty = hedge.get("perp_qty")
    if qty is None:
        return None, "数据缺口:HEDGE_POSITION_DATA_GAP"
    if abs(qty or 0.0) <= 1e-9:
        return None, "对冲未启用"
    for k in ("unrealized_pnl_usd", "unrealizedProfitUsd", "unRealizedProfit", "unrealized_profit_usd"):
        v = hedge.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v), "OK"
    return None, "数据缺口:HEDGE_PNL_DATA_GAP"


def _probability_underlying_target(risk):
    risk = risk or {}
    policy = risk.get("hedge_trigger_policy") or {}
    line = policy.get("hedge_price_line")
    if isinstance(line, (int, float)) and not isinstance(line, bool):
        return line, "explicit_line", None
    cr = risk.get("current_risk") or {}
    target_p = cr.get("open_probability")
    inp = risk.get("display_inputs") or {}
    direction = inp.get("direction_bias")
    current = inp.get("current_price")
    boundary = inp.get("loss_boundary")
    dte = inp.get("dte_hours")
    iv = inp.get("iv")
    delta = inp.get("short_delta")
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool)
               for x in (target_p, current, boundary, dte, iv)):
        return None, "data_gap", "HEDGE_TRIGGER_PRICE_DATA_GAP"
    if direction == "SHORT_CALL":
        if current >= boundary:
            return current, "probability_bisection", None
        lo, hi = current, boundary
        for _ in range(40):
            mid = (lo + hi) / 2.0
            p = estimate_touch_probability(direction, mid, boundary, dte, iv, delta)
            if p >= target_p:
                hi = mid
            else:
                lo = mid
        return hi, "probability_bisection", None
    if direction == "SHORT_PUT":
        if current <= boundary:
            return current, "probability_bisection", None
        lo, hi = boundary, current
        for _ in range(40):
            mid = (lo + hi) / 2.0
            p = estimate_touch_probability(direction, mid, boundary, dte, iv, delta)
            if p >= target_p:
                lo = mid
            else:
                hi = mid
        return lo, "probability_bisection", None
    return None, "data_gap", "HEDGE_TRIGGER_DIRECTION_GAP"


def _position_lifecycle_cn(snap, exit_state=None, in_flight=None):
    rem_short = (snap or {}).get("remaining_short_qty") or 0.0
    long_rem = (snap or {}).get("long_remaining_qty")
    if long_rem is None:
        long_rem = (snap or {}).get("long_fill_amount") or 0.0
    if (in_flight or {}).get("count"):
        return "活动订单处理中"
    if exit_state in (EXIT_WORKING_SHORT, EXIT_PAUSED_BUDGET, EXIT_PAUSED_DATA):
        return "短腿退出中"
    if rem_short <= 1e-12 and long_rem > 1e-12:
        return "短腿已平·保护腿待回收"
    if rem_short <= 1e-12 and long_rem <= 1e-12:
        return "已归档/待归档"
    return "已保护·卖方持仓"


def _build_position_detail(snap, quote_fn, now_ms, exit_state=None, in_flight=None, hedge=None):
    if not snap:
        return None
    short_i, long_i = snap.get("short_instrument"), snap.get("long_instrument")
    quote_gaps = []
    def _display_quote(inst, label):
        if not inst:
            return None
        try:
            return quote_fn(inst)
        except Exception:
            quote_gaps.append("%s_QUOTE_DATA_GAP" % label)
            return None
    sq = _display_quote(short_i, "SHORT")
    lq = _display_quote(long_i, "LONG")
    spot = _spot_price()
    short_strike = snap.get("short_strike")
    dist = ((short_strike - spot) / spot * 100.0
            if isinstance(short_strike, (int, float)) and isinstance(spot, (int, float)) and spot else None)
    long_rem = snap.get("long_remaining_qty")
    if long_rem is None:
        long_rem = snap.get("long_fill_amount") or 0.0
    short_mark = _quote_display(sq).get("mark")
    long_mark = _quote_display(lq).get("mark")
    pnl_gaps = []
    short_pnl_btc = None
    if all(isinstance(x, (int, float)) for x in (snap.get("short_fill_price"), short_mark, snap.get("remaining_short_qty"))):
        short_pnl_btc = (snap.get("short_fill_price") - short_mark) * (snap.get("remaining_short_qty") or 0.0)
    else:
        pnl_gaps.append("OPTION_SHORT_PNL_DATA_GAP")
    long_pnl_btc = None
    if all(isinstance(x, (int, float)) for x in (snap.get("long_fill_price"), long_mark, long_rem)):
        long_pnl_btc = (long_mark - snap.get("long_fill_price")) * long_rem
    else:
        pnl_gaps.append("OPTION_LONG_PNL_DATA_GAP")
    option_pnl_btc = None
    if short_pnl_btc is not None and long_pnl_btc is not None:
        option_pnl_btc = short_pnl_btc + long_pnl_btc
    hedge_pnl_usd, hedge_pnl_state = _hedge_pnl_display(hedge)
    option_pnl_usd = _safe_usd(option_pnl_btc, spot)
    combo_pnl_usd = None
    if option_pnl_usd is not None:
        combo_pnl_usd = option_pnl_usd + (hedge_pnl_usd or 0.0)
    if hedge_pnl_state and hedge_pnl_state.startswith("数据缺口"):
        pnl_gaps.append(hedge_pnl_state.split(":", 1)[1])
    detail = {
        "lifecycle": _position_lifecycle_cn(snap, exit_state, in_flight),
        "short_instrument": short_i,
        "long_instrument": long_i,
        "remaining_short_qty": snap.get("remaining_short_qty") or 0.0,
        "long_remaining_qty": long_rem,
        "short_fill_price": snap.get("short_fill_price"),
        "long_fill_price": snap.get("long_fill_price"),
        "short_strike": short_strike,
        "long_strike": snap.get("long_strike"),
        "breakeven": snap.get("breakeven"),
        "dte_hours": _dte_hours_to(snap.get("short_expiry_ts"), now_ms),
        "short_distance_pct": dist,
        "quote_gap": ",".join(quote_gaps) if quote_gaps else None,
        "option_short_unrealized_pnl_usd": _safe_usd(short_pnl_btc, spot),
        "option_long_unrealized_pnl_usd": _safe_usd(long_pnl_btc, spot),
        "option_unrealized_pnl_usd": option_pnl_usd,
        "hedge_unrealized_pnl_usd": hedge_pnl_usd,
        "hedge_pnl_state": hedge_pnl_state,
        "combo_unrealized_pnl_usd": combo_pnl_usd,
        "pnl_data_gap": ",".join(pnl_gaps) if pnl_gaps else None,
    }
    detail.update({
        "short_mark": short_mark,
        "short_bid": _quote_display(sq).get("bid"),
        "short_ask": _quote_display(sq).get("ask"),
        "long_mark": long_mark,
        "long_bid": _quote_display(lq).get("bid"),
        "long_ask": _quote_display(lq).get("ask"),
    })
    return detail


_HEDGE_ACTION_CN = {
    "HEDGE_HOLD": "保持",
    "HEDGE_OPEN": "新开对冲",
    "HEDGE_INCREASE": "增加对冲",
    "HEDGE_REDUCE": "减少对冲",
    "HEDGE_UNWIND": "清理/反向归零",
}


def _build_hedge_detail(hedge, risk):
    hedge = hedge or {}
    action = hedge.get("action") or {}
    hp = hedge.get("policy_detail") or {}
    risk = risk or {}
    cr = risk.get("current_risk") or {}
    policy = risk.get("hedge_trigger_policy") or {}
    data_gap = hedge.get("data_gap")
    if risk.get("market_data_gap"):
        data_gap = data_gap or "RISK_MARKET_DATA_GAP"
    action_name = action.get("action") or "HEDGE_HOLD"
    action_cn = "清理孤儿对冲" if hedge.get("orphan") and action.get("reduce_only") else _HEDGE_ACTION_CN.get(action_name, action_name)
    trigger_price, trigger_method, trigger_gap = _probability_underlying_target(risk)
    hedge_pnl_usd, hedge_pnl_state = _hedge_pnl_display(hedge)
    detail = {
        "module_state": "数据缺口" if data_gap else "正常",
        "data_gap": data_gap,
        "venue": hedge.get("venue"),
        "instrument": hedge.get("instrument"),
        "side": hedge.get("side"),
        "action": action_name,
        "action_cn": action_cn,
        "reduce_only": action.get("reduce_only"),
        "delta_contracts": action.get("delta_contracts"),
        "target": hedge.get("target"),
        "perp_qty": hedge.get("perp_qty"),
        "delta_to_trade": hedge.get("delta_to_trade"),
        "net_option_delta": hedge.get("net_option_delta"),
        "net_delta": hedge.get("net_delta"),
        "orphan": hedge.get("orphan"),
        "direction_consistent": hedge.get("direction_consistent"),
        "entry_touch_probability": cr.get("entry_touch_probability"),
        "touch_probability_now": cr.get("touch_probability_now"),
        "touch_probability_drift": cr.get("touch_probability_drift"),
        "watch_probability": cr.get("watch_probability"),
        "open_probability": cr.get("open_probability"),
        "emergency_probability": cr.get("emergency_probability"),
        "hedge_price_line": policy.get("hedge_price_line"),
        "hedge_underlying_trigger_price": trigger_price,
        "hedge_underlying_trigger_method": trigger_method,
        "hedge_trigger_data_gap": trigger_gap,
        "hedge_unrealized_pnl_usd": hedge_pnl_usd,
        "hedge_pnl_state": hedge_pnl_state,
        "reason_codes": risk.get("reason_codes") or [],
    }
    if hp:
        detail.update({
            "hedge_policy": hp.get("policy"),
            "policy_state": hp.get("state") or hp.get("trigger_state"),
            "policy_reason": hp.get("reason"),
            "policy_warnings": hp.get("warnings") or [],
            "full_target_qty": hp.get("full_target_qty"),
            "eff_target_qty": hp.get("eff_target_qty"),
            "current_hedge_qty": hp.get("current_hedge_qty"),
            "policy_delta_to_trade": hp.get("delta_to_trade"),
            "soft_ratio": hp.get("soft_ratio"),
            "gamma_fraction": hp.get("gamma_fraction"),
            "gamma_data_state": hp.get("gamma_data_state"),
            "rebalance_deadband": hp.get("rebalance_deadband"),
            "final3_mode": hp.get("final3_mode"),
            "crash_adverse_bps": hp.get("crash_adverse_bps"),
            "min_hold_until": hp.get("min_hold_until"),
            "target_semantics": hp.get("target_semantics"),
            "pending_order_id": hp.get("pending_order_id"),
            "pending_order_side": hp.get("pending_order_side"),
            "pending_order_qty": hp.get("pending_order_qty"),
            "policy_cross_bps": hp.get("cross_bps"),
            "soft_since_ts": hp.get("soft_since_ts"),
            "reduce_since_ts": hp.get("reduce_since_ts"),
            "add_cooldown_until": hp.get("add_cooldown_until"),
            "reduce_cooldown_until": hp.get("reduce_cooldown_until"),
            "episode_cost_bps": hp.get("episode_cost_bps"),
            "episode_cost_usdc": hp.get("episode_cost_usdc"),
            "policy_p_entry": hp.get("p_entry"),
            "policy_p_now": hp.get("p_now"),
            "policy_drift": hp.get("drift"),
        })
    return detail


def _build_risk_exit_detail(risk_exit, exit_detail):
    exit_detail = exit_detail or {}
    max_spend = RISK_EXIT_MAX_SPEND if RISK_EXIT_MAX_SPEND > 0 else None
    return {
        "policy_code": "AUTO_CONFIG",
        "max_exit_spend": max_spend,
        "budget_source": "RISK_EXIT_MAX_SPEND" if isinstance(max_spend, (int, float)) and max_spend > 0 else "冻结退出预算",
        "remaining_budget": exit_detail.get("remaining_budget"),
        "price_cap": exit_detail.get("price_cap"),
        "within": exit_detail.get("within"),
        "within_price": exit_detail.get("within_price"),
        "quote_ok": exit_detail.get("quote_ok"),
        "ask": exit_detail.get("ask"),
        "ask_depth": exit_detail.get("ask_depth"),
        "depth_ok": exit_detail.get("depth_ok"),
        "reason": exit_detail.get("reason"),
        "risk_exit_active": bool(risk_exit),
    }


def _build_ledger_detail(snap, rec, recovery, in_flight, tp):
    snap = snap or {}
    report = snap.get("entry_execution_report") or {}
    short_credit = report.get("total_short_credit")
    if short_credit is None:
        short_credit = _safe_mul(snap.get("short_fill_price"), snap.get("short_fill_amount"))
    protection_cost = report.get("total_protection_cost")
    if protection_cost is None:
        protection_cost = _safe_mul(snap.get("long_fill_price"), snap.get("long_fill_amount"))
    entry_fees = report.get("total_fee_estimate")
    if entry_fees is None:
        entry_fees = snap.get("entry_fees")
    net_credit = report.get("actual_net_credit_after_fees")
    if net_credit is None:
        net_credit = snap.get("entry_profit_ceiling_net")
    rec = rec or {}
    recovery = recovery or {}
    legacy_gaps = []
    for key, label in (
        ("breakeven", "BREAKEVEN_MISSING"),
        ("short_strike", "SHORT_STRIKE_MISSING"),
        ("long_strike", "LONG_STRIKE_MISSING"),
        ("entry_execution_report", "ENTRY_EXECUTION_REPORT_MISSING"),
    ):
        if snap and not snap.get(key):
            legacy_gaps.append(label)
    return {
        "short_credit": short_credit,
        "protection_cost": protection_cost,
        "entry_fees": entry_fees,
        "actual_net_credit": net_credit,
        "realized_exit_spend": snap.get("realized_exit_spend") or 0.0,
        "remaining_exit_budget": (tp or {}).get("remaining_budget"),
        "entry_fill_count": report.get("fill_count") or len(report.get("fills") or []),
        "exit_fill_count": len(snap.get("exit_execution_history") or []),
        "protection_recovery_count": len(snap.get("protection_recovery_history") or []),
        "hedge_fill_count": len(snap.get("hedge_execution_history") or []),
        "settlement_event_count": len(snap.get("option_settlement_history") or []),
        "settlement_pnl_status": snap.get("settlement_pnl_status"),
        "short_settlement_cashflow_ccy": snap.get("short_settlement_cashflow_ccy"),
        "long_settlement_cashflow_ccy": snap.get("long_settlement_cashflow_ccy"),
        "option_settlement_cashflow_ccy": snap.get("option_settlement_cashflow_ccy"),
        "option_realized_pnl_status": snap.get("option_realized_pnl_status"),
        "option_realized_pnl_ccy": snap.get("option_realized_pnl_ccy"),
        "final_pnl_status": snap.get("final_pnl_status"),
        "final_option_pnl_ccy": snap.get("final_option_pnl_ccy"),
        "realized_protection_recovery_value": snap.get("realized_protection_recovery_value") or 0.0,
        "realized_protection_recovery_fees": snap.get("realized_protection_recovery_fees") or 0.0,
        "reconciled": rec.get("reconciled"),
        "reconcile_reasons": rec.get("reasons") or [],
        "recovery_state": recovery.get("state") or "OK",
        "allow_new_open": recovery.get("allow_new_open", True),
        "active_orders": (in_flight or {}).get("orders") or [],
        "data_quality_state": "恢复接管缺口" if legacy_gaps else "OK",
        "legacy_recovery_gaps": legacy_gaps,
    }


def manage_cycle(now_ms):
    """持仓管理一轮（§9.1）：对账(快照为真相) + 止盈资格；退出/对冲由四输出仲裁**单动作收口**
    （每轮仅执行 executable 的风险动作）；短腿归零后回收保护腿(清理)；两腿+对冲 perp 归零→归档 CLOSED。
    **退出活动期禁新增对冲敞口**（只许 reduce/unwind）。退出/对冲/回收真实下单均受各自门控，默认空跑。"""
    snap = _G(_POSITION_KEY)
    pos_id = (snap or {}).get("position_id")
    recovery = _recovery_verdict()
    auth = None
    authorized = bool(snap)
    opt_pos_read_ok = True
    try:
        opt_pos = dbt_get_positions_strict(SETTLEMENT_CURRENCY, "option")
    except Exception:
        opt_pos = None
        opt_pos_read_ok = False
    if opt_pos is None:
        opt_pos_read_ok = False
    if opt_pos_read_ok:
        settlement = _settlement_reconcile_snapshot(snap, opt_pos, now_ms)
        if settlement.get("changed"):
            snap = settlement.get("snap")
            _G(_POSITION_KEY, snap)
    if opt_pos_read_ok:
        rec = position_reconcile(snap, opt_pos)        # P0①：快照 vs 交易所（surfaced；不阻断风险收口）
    else:
        rec = {"reconciled": None, "reasons": ["OPTION_POSITION_QUERY_FAILED"]}

    quote_fn = _quote_cache()
    tp = _evaluate_take_profit(snap, quote_fn, now_ms)
    rem_short = tp["remaining_short_qty"]
    long_rem = (snap or {}).get("long_remaining_qty")
    if long_rem is None:
        long_rem = (snap or {}).get("long_fill_amount") or 0.0

    # 风险严重度（接 hedge_risk）：先算对冲(取 perp 持仓判 existing_hedge) → 风险包 → 仲裁输入
    hedge = _evaluate_hedge(snap, quote_fn)
    in_flight = _manage_in_flight_orders(snap, hedge)
    existing_hedge = abs(hedge.get("perp_qty") or 0.0) > 1e-9
    risk = _evaluate_position_risk_now(snap, now_ms, existing_hedge, quote_fn)
    hedge = _hedge_policy_plan(snap, hedge, risk, now_ms)
    resolved_hedge_fill = (hedge or {}).get("policy_resolved_fill")
    if resolved_hedge_fill and snap:
        _append_execution_history(snap, "hedge_execution_history", resolved_hedge_fill, now_ms)
        _G(_POSITION_KEY, snap)
    risk_state = (risk or {}).get("tail_risk_state")
    hedge_ready = risk_state == STATE_HEDGE_READY            # 风险概率相对入场锚恶化
    exit_preferred = hedge_ready                             # 风险触发时先尝试授权退出，不可执行再回退对冲
    policy_wants_hedge = bool(((hedge or {}).get("policy_detail") or {}).get("wants_action"))

    # 退出活动触发 = 止盈资格 ∨ 风险主动退出。
    # F1：风险退出用**配置/冻结预算价格上限**，且可越价吃单(within=ask≤cap)；
    #     止盈退出沿用 80% 缓冲、被动 maker(patient，恒 within)。
    risk_exit = exit_preferred                               # 风险驱动退出（区别于止盈资格退出）
    if risk_exit:
        exit_detail = _risk_exit_budget_cap(snap, auth, quote_fn)
    else:
        exit_detail = {"remaining_budget": tp["remaining_budget"], "price_cap": tp["price_cap"],
                       "within": True, "within_price": True, "quote_ok": tp["quote_ok"],
                       "ask": None, "ask_depth": None, "depth_ok": True, "reason": None}
    exit_budget = exit_detail.get("remaining_budget")
    exit_cap = exit_detail.get("price_cap") or 0.0
    exit_within = exit_detail.get("within") is True
    exit_trigger = bool(tp["qualified"] or exit_preferred)
    exit_decision = exit_campaign_decision(authorized, exit_trigger, rem_short,
                                           exit_budget, tp["quote_ok"], exit_cap)
    exit_state = exit_decision["state"]
    g = _effective_gate_cfg()
    exit_gate = gate_decision(ACTION_EXIT, g["allow_entry"], g["allow_exit"],
                              g["allow_hedge"], _effective_kill(), EMERGENCY_REDUCE_ONLY)["allowed"]
    exit_executable = bool(exit_decision["can_order"] and exit_gate and exit_within)
    exit_active = authorized and exit_state in (EXIT_WORKING_SHORT, EXIT_PAUSED_BUDGET,
                                                EXIT_PAUSED_DATA, EXIT_WORKING_LONG)

    # P0③ 退出活动期禁新增对冲——但 F1：**风险退出无法满足**(预算不足/越价不可成交)时放行对冲回退
    risk_exit_unsatisfiable = risk_exit and not exit_executable
    if exit_active and not risk_exit_unsatisfiable \
            and hedge["action"]["action"] in ("HEDGE_OPEN", "HEDGE_INCREASE"):
        hedge["action"] = {"action": "HEDGE_HOLD", "reduce_only": False, "delta_contracts": 0.0}
    h_reduce = hedge["action"]["reduce_only"]
    h_gate_act = ACTION_HEDGE_REDUCE if h_reduce else ACTION_HEDGE_OPEN
    h_gate_ok = gate_decision(h_gate_act, g["allow_entry"], g["allow_exit"],
                              g["allow_hedge"], _effective_kill(), EMERGENCY_REDUCE_ONLY)["allowed"]
    # C2：孤儿对冲(裸 perp：short=0 而 perp≠0)清理为纯降险 reduce_only，且 perp 已存在=场所已配置 →
    #     不受 allow_hedge 阻断（缺省空跑下也能清理裸敞口）。
    orphan_cleanup = bool(hedge["orphan"] and h_reduce)
    hedge_reduce_cleanup = bool(h_reduce and abs(hedge.get("perp_qty") or 0.0) > 1e-9)
    hedge_exec = (hedge["action"]["action"] != "HEDGE_HOLD"
                  and (h_gate_ok or orphan_cleanup or hedge_reduce_cleanup))
    pause = ("PAUSED_BY_BUDGET" if exit_state == EXIT_PAUSED_BUDGET else
             ("PAUSED_BY_DATA" if exit_state == EXIT_PAUSED_DATA else None))
    arb = unified_action_arbiter({
        "recovery_blocked": recovery.get("state") == "RECOVERY_BLOCKED",
        "orphan_hedge": (recovery.get("state") == "ORPHAN_HEDGE_EMERGENCY") or hedge["orphan"],
        "in_flight_order": in_flight["count"] > 0,
        "exit_preferred": exit_preferred, "hedge_ready": bool(hedge_ready or policy_wants_hedge),   # 风险严重度→仲裁（接回 hedge_risk）
        "take_profit_ready": tp["qualified"],
        "exit_authorized": authorized,
        "exit_executable": exit_executable,
        "exit_pause_reason": pause, "hedge_executable": bool(hedge_exec),
    })
    executable = arb["executable_action"]

    # P0③ 单动作收口：仅执行 executable 指定的风险动作（短腿退出 / 对冲）
    hedge_step = None
    if executable in ("TAKE_PROFIT_READY", "EXIT_PREFERRED") and rem_short > 1e-12 and exit_executable:
        step = exec_exit_buyback_step(snap.get("short_instrument"), rem_short, exit_cap,
                                      allow_live=True, allow_taker=(executable == "EXIT_PREFERRED"),
                                      label=("risk_exit" if executable == "EXIT_PREFERRED" else "exit_short"),
                                      quote=quote_fn(snap.get("short_instrument")))
        if not step.get("dry") and (step.get("filled") or 0) > 0:
            _apply_exit_fill(snap, step, now_ms)
            snap = _G(_POSITION_KEY)
            rem_short = (snap or {}).get("remaining_short_qty") or 0.0
    elif executable in ("HEDGE_READY", "ORPHAN_HEDGE_EMERGENCY") and hedge_exec:
        if _hedge_policy_enabled_for(hedge):
            hedge_step = _hedge_policy_submit(hedge, now_ms, allow_live=True)
        else:
            hedge_step = {"filled": 0.0, "dry": False,
                          "venue": hedge.get("venue"),
                          "reason": "HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT",
                          "blocked": True}
        if hedge_step and not hedge_step.get("dry") and snap \
                and ((hedge_step.get("filled") or 0) > 0 or not _hedge_policy_enabled_for(hedge)):
            _append_execution_history(snap, "hedge_execution_history", hedge_step, now_ms)
            _G(_POSITION_KEY, snap)

    # P0② 保护腿回收（短腿归零后的清理；非风险动作，不与上面竞争）
    long_state = None
    if rem_short <= 1e-12 and long_rem > 1e-12:
        li = (snap or {}).get("long_instrument")
        pb = (quote_fn(li) or {}).get("best_bid") if li else None
        prec = protection_recovery_decision(True, long_rem, pb)
        long_state = prec["state"]
        if prec["can_sell"] and exit_gate and li:
            r = exec_protection_recovery_step(li, long_rem, allow_live=True, quote=quote_fn(li))
            if (r.get("sold") or 0) > 0 and snap:
                _apply_protection_recovery_fill(snap, r, now_ms)
                long_rem = snap["long_remaining_qty"]

    # P0② CLOSED 归档：两腿 + 对冲 perp 均归零（对冲未归零不 CLOSED）
    if snap and rem_short <= 1e-12 and long_rem <= 1e-12 and abs(hedge.get("perp_qty") or 0.0) <= 1e-9:
        _archive_closed(snap, now_ms)

    tp_display = _evaluate_take_profit(snap, quote_fn, now_ms) if snap else tp
    position_detail = _build_position_detail(snap, quote_fn, now_ms, long_state or exit_state, in_flight, hedge)
    hedge_detail = _build_hedge_detail(hedge, risk)
    risk_exit_detail = _build_risk_exit_detail(risk_exit, exit_detail)
    ledger_detail = _build_ledger_detail(snap, rec, recovery, in_flight, tp_display)
    return {"arb": arb, "entry_snapshot": snap, "reconcile": rec, "executable": executable,
            "auth": auth, "authorized": authorized,
            "risk_exit": risk_exit, "exit_executable": exit_executable,
            "exit_campaign_state": (long_state or exit_state), "tp_ratio": tp["ratio"], "hedge": hedge,
            "hedge_step": hedge_step, "risk_state": risk_state, "risk": risk,
            "manage_in_flight_order": in_flight,
            "position_detail": position_detail, "take_profit_detail": tp_display,
            "risk_exit_detail": risk_exit_detail, "hedge_detail": hedge_detail,
            "ledger_detail": ledger_detail}


def run_cycle(now_ms=None):
    """Single manual-gate cycle: command, existing risk management, manual plan display, approval lock."""
    now_ms = now_ms or _now_ms()
    sid = _session_id()
    meta = {"robot_id": ROBOT_ID, "session_id": sid, "refresh_seq": _refresh_seq()}
    disp = _dispatch_command(GetCommand(), meta, now_ms)

    manual_context = _manual_context_for_cycle(now_ms)
    manual_check = validate_manual_context(manual_context, now_ms) if manual_context else {
        "valid": False,
        "errors": ["MANUAL_PLANNING_DISABLED"],
    }
    gsum = _gate_summary_now()
    kill = _effective_kill()
    state = ledger_get_state()
    has_pos = _has_position(state)
    locked = _G(_LOCKED_KEY)
    spot = _spot_price()
    lineage_invalidation = _lineage_invalidated(locked, manual_context, now_ms)
    if lineage_invalidation:
        _clear_plan_lineage()
        locked = None

    pending = []
    stable_menu, stable_meta = _load_stable_menu(manual_context)
    display_candidates = list(stable_menu or [])
    not_lockable_reason = stable_meta.get("not_lockable_reason")
    plan_vrp_blocked = 0
    plan_vrp_blocked = stable_meta.get("vrp_blocked") or 0
    plan_build_reason = stable_meta.get("reason")
    enum_diag = stable_meta.get("diag")
    menu_source = "frozen" if display_candidates else "none"
    plan_build_attempted = False
    commit_result = None
    manage_result = None
    recovery = _recovery_verdict()
    rec_ok = recovery.get("allow_new_open", True)

    if recovery.get("state") == "RECOVERY_BLOCKED":
        phase = "RECOVERY_BLOCKED"
    elif recovery.get("state") == "ORPHAN_HEDGE_EMERGENCY" and not has_pos:
        phase = "ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED"
    elif has_pos:
        manage_result = manage_cycle(now_ms)
        phase = "POSITION_MANAGE"
    elif kill:
        phase = "KILLED"
    elif locked:
        commit_result = _attempt_commit(locked, spot, manual_context, now_ms)
        phase = ("POSITION_MANAGE" if (commit_result["committed"]
                 or commit_result.get("residual_position")) else "PLAN_LOCKED")
    elif not MANUAL_PLANNING_ALLOWED:
        phase = "WAIT_MANUAL_AUDIT_GATE"
    elif not manual_check.get("valid"):
        phase = "MANUAL_CONTEXT_INVALID"
    elif not rec_ok:
        phase = "RECOVERY_BLOCKED"
    else:
        phase = "PLAN_MENU_READY"
        lib = _G(_LIB_KEY)
        if _lineage_invalidated(lib, manual_context, now_ms):
            _clear_plan_lineage(clear_menu=False)
            lib = None
        if spot and not display_candidates:
            plan_build_attempted = True
            menu, _pm_ok, _model, reason, diag = _build_menu(now_ms, spot, manual_context)
            plan_build_reason = reason
            enum_diag = diag
            market_context = (manual_context or {}).get("market_context")
            lockable = []
            if reason == "OK" and menu and market_context:
                lockable, plan_vrp_blocked = _filter_menu_by_vrp(
                    menu, {"market_context": market_context},
                    manual_context.get("direction_bias") or DIRECTION_BIAS, diag)
                if not lockable:
                    reason = "NO_VRP_PASS_CANDIDATE"
            elif reason == "OK" and menu:
                not_lockable_reason = "VRP_CONTEXT_MISSING"
            if reason == "OK" and lockable:
                rseq = _bump_refresh_seq()
                lib = build_recommendation_library(
                    lockable, sid, manual_context, rseq, now_ms,
                    config_hash=manual_context.get("config_signature"))
                _G(_LIB_KEY, lib)
                _G(_LIB_BUILD_TS_KEY, now_ms)
            else:
                _clear_plan_lineage(clear_menu=False)
                lib = None
                if reason != "OK" and not not_lockable_reason:
                    not_lockable_reason = reason
            pending_tmp = []
            if lib and lib.get("recommendations"):
                pending_tmp = [{"id": s["plan_id"], "summary": s["summary"],
                                "confirm_code": s["confirm_code"]}
                               for s in lib["recommendations"][:MENU_SIZE]]
            display_candidates = _annotate_menu_lock_state(menu or [], pending_tmp, not_lockable_reason)
            stable_meta = _store_stable_menu(display_candidates, manual_context, now_ms,
                                             reason, diag, len(pending_tmp or []),
                                             plan_vrp_blocked, not_lockable_reason)
            _store_plan_trace(now_ms, reason=reason, diag=diag, menu_count=len(menu or []),
                              lockable_count=len(pending_tmp or []),
                              vrp_blocked=plan_vrp_blocked,
                              not_lockable_reason=not_lockable_reason)
            menu_source = "built_frozen"
        elif display_candidates:
            _store_plan_trace(now_ms, reason=plan_build_reason, diag=enum_diag,
                              menu_count=len(display_candidates),
                              lockable_count=stable_meta.get("lockable_count") or 0,
                              vrp_blocked=plan_vrp_blocked,
                              not_lockable_reason=not_lockable_reason)
        if lib and lib.get("recommendations"):
            pending = [{"id": s["plan_id"], "summary": s["summary"],
                        "confirm_code": s["confirm_code"]}
                       for s in lib["recommendations"][:MENU_SIZE]]
            display_candidates = _annotate_menu_lock_state(display_candidates, pending, not_lockable_reason)
            _G(_MENU_KEY, list(display_candidates or []))
            phase = "HARD_APPROVAL_WAIT"
    if display_candidates and not pending and not_lockable_reason:
        display_candidates = _annotate_menu_lock_state(display_candidates, pending, not_lockable_reason)
        _G(_MENU_KEY, list(display_candidates or []))
    locked_display = None
    if locked and phase == "PLAN_LOCKED":
        locked_display = _locked_display_candidate(locked, display_candidates)
        if locked_display:
            display_candidates = [locked_display]
            menu_source = "locked"
            not_lockable_reason = None

    ctx = _ctx_base(state, spot, "RUN_CYCLE:" + phase)
    ctx["now_ms"] = now_ms
    _apply_manual_context_to_ctx(ctx, manual_context, manual_check)
    ctx["console_phase"] = phase
    if phase == "WAIT_MANUAL_AUDIT_GATE":
        ctx["manual_gate_status"] = "WAIT_MANUAL_AUDIT_GATE"
    ctx["gate_summary"] = gsum
    ctx["lineage_invalidation"] = lineage_invalidation
    ctx["pending_candidates"] = pending
    ctx["menu"] = display_candidates
    ctx["menu_source"] = menu_source
    ctx["plan_library_frozen"] = bool(display_candidates)
    detail_plan = locked_display or (display_candidates[0] if display_candidates else None)
    if detail_plan:
        try:
            ctx.update(_flat_plan_fields(detail_plan))
            ctx["preview_plan_detail"] = "locked_plan" if locked_display else "stable_first_candidate"
            ctx["selected_plan"] = detail_plan.get("id")
        except Exception:
            ctx["preview_plan_detail"] = None
    ctx["display_candidates_count"] = len(display_candidates)
    ctx["lockable_candidates_count"] = 1 if locked_display else len(pending)
    plan_trace = _G(_PLAN_TRACE_KEY) or {}
    ctx["not_lockable_reason"] = not_lockable_reason or plan_trace.get("not_lockable_reason")
    ctx["plan_vrp_blocked"] = plan_vrp_blocked or plan_trace.get("vrp_blocked") or 0
    ctx["plan_build_reason"] = plan_build_reason or plan_trace.get("reason")
    ctx["enum_diag"] = enum_diag or plan_trace.get("diag")
    ctx["plan_build_attempted"] = plan_build_attempted
    ctx["kill_new_risk"] = kill
    ctx["last_command"] = disp.get("action")
    ctx["last_command_outcome"] = disp.get("outcome")
    if commit_result:
        ctx["precommit"] = commit_result.get("precommit")
        ctx["order_intent"] = commit_result.get("order_intent")
        ctx["commit_reason"] = commit_result.get("reason")
        ctx["projected_budget"] = commit_result.get("budget")
        ctx["entry_state"] = commit_result.get("entry_state")
        ctx["entry_net_credit"] = commit_result.get("net_credit")
        po = commit_result.get("entry_prot_order")
        if po:
            po = dict(po)
            ws = po.get("wait_start_ms")
            if isinstance(ws, (int, float)):
                po["wait_elapsed_ms"] = max(0, now_ms - ws)
                po["taker_due"] = po["wait_elapsed_ms"] >= ENTRY_PROTECTION_TAKER_AFTER_SECONDS * 1000
        ctx["entry_prot_order"] = po
        if commit_result.get("entry_snapshot"):
            ctx["entry_snapshot"] = commit_result["entry_snapshot"]
    if manage_result:
        ctx["action_arb"] = manage_result.get("arb")
        ctx["entry_snapshot"] = manage_result.get("entry_snapshot")
        ctx["reconciled"] = (manage_result.get("reconcile") or {}).get("reconciled")
        ctx["risk_state"] = manage_result.get("risk_state")
        ctx["risk_pkg"] = manage_result.get("risk")
        ctx["manage_in_flight_order"] = manage_result.get("manage_in_flight_order")
        ctx["exit_campaign_state"] = manage_result.get("exit_campaign_state")
        _r = manage_result.get("tp_ratio")
        ctx["take_profit_ratio"] = ("%.1f%%" % (_r * 100)) if isinstance(_r, (int, float)) else "DATA_GAP"
        ctx["position_detail"] = manage_result.get("position_detail")
        ctx["take_profit_detail"] = manage_result.get("take_profit_detail")
        ctx["risk_exit_detail"] = manage_result.get("risk_exit_detail")
        ctx["hedge_detail"] = manage_result.get("hedge_detail")
        ctx["ledger_detail"] = manage_result.get("ledger_detail")
        ctx["hedge_step"] = manage_result.get("hedge_step")
        pd = ctx.get("position_detail") or {}
        if pd:
            ctx["short_instrument"] = pd.get("short_instrument")
            ctx["protection_instrument"] = pd.get("long_instrument")
            ctx["short_mark"] = pd.get("short_mark")
            ctx["protection_mark"] = pd.get("long_mark")
        _h = manage_result.get("hedge")
        if _h:
            if _h.get("data_gap"):
                ctx["hedge_data_gap"] = _h.get("data_gap")
            _risk = manage_result.get("risk") or {}
            _cr = _risk.get("current_risk") or {}
            ctx["hedge_state"] = (
                "venue=%s side=%s entry_p=%.1f%% now_p=%.1f%% drift=%+.1f%% open_p=%.1f%% "
                "target=%.4g current=%.4g delta_to_trade=%.4g action=%s style=%s reduce_only=%s"
                % (_h.get("venue") or "-", _h.get("side") or "-",
                   (_cr.get("entry_touch_probability") or 0.0) * 100,
                   (_cr.get("touch_probability_now") or 0.0) * 100,
                   (_cr.get("touch_probability_drift") or 0.0) * 100,
                   (_cr.get("open_probability") or 0.0) * 100,
                   _h.get("target") or 0.0, _h.get("perp_qty") or 0.0,
                   _h.get("delta_to_trade") or 0.0, _h["action"]["action"],
                   HEDGE_OPEN_EXECUTION_STYLE, _h["action"].get("reduce_only")))
    if recovery.get("state") != "OK":
        ctx["recovery_state"] = recovery.get("state")
    if phase == "ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED":
        ctx["orphan_hedge_cleanup"] = _orphan_hedge_cleanup_detail(recovery)
    if locked and not (commit_result and commit_result.get("committed")):
        ctx["locked_plan_summary"] = "%s %s" % (locked.get("confirm_code"), locked.get("summary"))
        if not ctx.get("preview_plan_detail"):
            ctx["preview_plan_detail"] = "locked_plan"
            ctx["selected_id"] = locked.get("plan_id")
            ctx["selected_plan"] = locked.get("plan_id")
            ctx["short_instrument"] = locked.get("short_instrument")
            ctx["protection_instrument"] = locked.get("long_instrument")
            ctx["short_strike"] = locked.get("short_strike")
            ctx["protection_strike"] = locked.get("long_strike")
            ctx["short_delta"] = locked.get("short_delta")
            ctx["amount"] = locked.get("amount")
            ctx["net_credit"] = locked.get("entry_net_credit_after_costs")
            ctx["margin_relief_ratio"] = locked.get("margin_relief_ratio")
            ctx["execution_feasibility_grade"] = locked.get("execution_feasibility_grade")
            ctx["execution_feasibility_score"] = locked.get("execution_feasibility_score")
            ctx["execution_feasibility_score_norm"] = locked.get("execution_feasibility_score_norm")
            ctx["execution_feasibility_warnings"] = locked.get("execution_feasibility_warnings") or []
        if not ctx.get("menu"):
            ctx["menu"] = [{
                "id": locked.get("plan_id"),
                "short_instrument": locked.get("short_instrument"),
                "protection_instrument": locked.get("long_instrument"),
                "short_strike": locked.get("short_strike"),
                "protection_strike": locked.get("long_strike"),
                "amount": locked.get("amount"),
                "net_credit_effective": locked.get("entry_net_credit_after_costs"),
                "margin_relief_ratio": locked.get("margin_relief_ratio"),
            }]
    _emit(ctx, "manual-gate")
    return ctx

def main():
    errs = validate_config()
    if errs:
        Log("[config] 配置错误，拒绝运行:", "; ".join(errs))
        LogStatus("配置错误：" + "; ".join(errs))
        return

    _g = _effective_gate_cfg()
    Log("[boot] S:PM manual-gate execution v%s" % STRATEGY_VERSION,
        "PROFILE=%s" % _g["profile"],
        "ALLOW_ENTRY=%s" % _g["allow_entry"],
        "currency=%s" % SETTLEMENT_CURRENCY)
    self_check = _startup_self_check(SETTLEMENT_CURRENCY)
    Log("[self-check]", disp_self_check_line(self_check))
    startup_recovery_check(SETTLEMENT_CURRENCY)        # 启动恢复：可解释映射 → OK/RECOVERY_BLOCKED/ORPHAN

    while True:
        try:
            run_cycle()
        except Exception as e:
            Log("[loop] 异常:", str(e))
        Sleep(LOOP_INTERVAL_MS)
