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
                      entry_campaign_decision, ENTRY_ABANDONED,
                      position_reconcile, protection_recovery_decision)
from authorization import (authorize_from_code, is_authorized, revoke, auth_code,
                          POLICY_TAKE_PROFIT, POLICY_RISK_EXIT)
from hedge import (hedge_target_contracts, hedge_target_position, hedge_order_action, hedge_orphan,
                  hedge_side, hedge_venue_config, HEDGE_INSTRUMENT,
                  structure_net_delta, hedge_direction_consistent, option_net_delta)
from binance_io import bnc_get_position_btc
from deribit_io import *
from leg_selection import *
from spm_sim import *
from accounting import *
from plans import *
from ledger import *
from execution import *
from display import *
from hedge_risk import (build_entry_risk_anchor, build_hedge_trigger_policy,
                       evaluate_position_risk,
                       STATE_EXIT_PREFERRED, STATE_HEDGE_READY)
from risk_controls import (evaluate_portfolio_budget, evaluate_projected_budget,
                          unified_action_arbiter)
from execution_feasibility import (evaluate_execution_feasibility,
                                   feasibility_penalty)

_MENU_KEY = "spm_plan_menu_v1"
_MANUAL_CONTEXT_KEY = "spm_manual_context_v1"
_LAST_COMMAND_KEY = "spm_last_command_v1"
_LAST = {"plan_ms": 0}
# 选用方案明细锁定：启动时锁定一个方案的编号，之后不随方案库刷新而改变（重启复位）
_LOCKED = {"detail_id": None}
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


def _execution_feasibility_cfg():
    return {"max_short_spread": MAX_SPREAD_RATIO,
            "max_protection_spread": MAX_SPREAD_RATIO,
            "protection_low_premium_max": PROTECTION_LOW_PREMIUM_MAX,
            "protection_abs_spread_max": PROTECTION_ABS_SPREAD_MAX,
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
    dte_min = scope.get("dte_hours_min", SHORT_DTE_HOURS[0])
    dte_max = scope.get("dte_hours_max", SHORT_DTE_HOURS[1])
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
    short_exps = legsel_expiries_in_band(instruments, dte_min, dte_max,
                                         now_ms, want_call)
    if not short_exps:
        return [], False, None, "NO_SHORT_EXPIRY_IN_BAND", diag
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
            if sq["mark"] < MIN_SHORT_PREMIUM:
                diag["权利金过薄"] += 1
                continue
            ssr = exec_spread_ratio(sq)
            if ssr is not None and ssr > MAX_SPREAD_RATIO:
                diag["价差过宽"] += 1
                continue
            # 同期垂直：保护腿取同到期、更价外、腿宽达标者；长腿是定额风险封顶，
            # 便宜的 OTM 长腿正是所需 → **不套用过度虚值过滤**
            vprot = _first_in_width(legsel_protection_candidates(
                s_insts, short["strike"], want_call, width_range,
                None, 0.0))
            if not vprot:
                diag["无合格保护腿(腿宽内)"] += 1
                continue
            pq = quote_fn(vprot["instrument_name"])
            if not pq or pq.get("mark") is None:
                continue
            c = plan_assemble(amount, spot, MIN_MARGIN_RELIEF_RATIO, pref,
                              want_call, short, sq, vprot, pq,
                              None, pm_ok, model, s_dte_h, s_dte_h)
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
        "direction_bias": DIRECTION_BIAS, "allow_trading": ALLOW_TRADING,
        "manual_gate_state": ("PLANNING_ALLOWED" if MANUAL_PLANNING_ALLOWED
                              else "WAIT_MANUAL_AUDIT_GATE"),
        "manual_context_ttl_min": MANUAL_CONTEXT_TTL_MIN,
        "round_mode": ROUND_MODE,
        "state": state,
        "max_chase_steps": MAX_CHASE_STEPS, "min_required_ratio": MIN_MARGIN_RELIEF_RATIO,
        "reason": reason, "spot": spot, "amount": ORDER_AMOUNT,
        "selected_plan": SELECTED_PLAN, "protection_mode": None,
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
        breakeven=p.get("breakeven"), credit_on_margin=p.get("credit_on_margin"),
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


def _emit(ctx, note=""):
    LogStatus(disp_status_panel(ctx, note))
    Log(disp_log_summary(ctx, note))


# ---------- 计划轮 ----------

def integrated_plan_preview(spot, market_context=None, portfolio_state=None):
    """整合执行流的 PLAN 段（执行会话式）：真实 _build_menu → VRP 双门过滤(给 market_context 时)
    → 组合硬预算(给 portfolio_state 时) → 返回可锁定方案 + 各域裁决。

    main() 在拿到实时 IV/RV(market_context) 与组合状态后调用本函数；选中方案的会话锁定/授权
    plan_hash + TTL 与 FMZ 命令栏交互由人工审计门主链接管。
    边界：VRP/预算**只过滤**，不进 PLAN_WEIGHTS、不判方向、不解 ALLOW_TRADING。"""
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
    """配置急停 KILL_NEW_RISK 或运行时【急停】命令（_G）任一为真即急停。"""
    return bool(KILL_NEW_RISK) or bool(_G(_RUNTIME_KILL_KEY))


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
        MANUAL_PLANNING_ALLOWED, DIRECTION_BIAS, SHORT_DTE_HOURS, SHORT_DELTA_RANGE,
        PROTECTION_WIDTH_RANGE, ORDER_AMOUNT, MANUAL_AUDIT_CARD_ID,
        MANUAL_AUDIT_NOTE, MANUAL_CONTEXT_TTL_MIN, _manual_risk_policy())


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
    if not ctx or ctx.get("config_signature") != sig:
        ctx = build_manual_context(
            now_ms, MANUAL_PLANNING_ALLOWED, DIRECTION_BIAS, SHORT_DTE_HOURS,
            SHORT_DELTA_RANGE, PROTECTION_WIDTH_RANGE, ORDER_AMOUNT,
            MANUAL_AUDIT_CARD_ID, MANUAL_AUDIT_NOTE, MANUAL_CONTEXT_TTL_MIN,
            _manual_risk_policy())
        _G(_MANUAL_CONTEXT_KEY, ctx)
    ctx = _refresh_vrp_context(ctx, now_ms)
    _G(_MANUAL_CONTEXT_KEY, ctx)
    return ctx


def _clear_plan_lineage():
    _G(_LOCKED_KEY, None)
    _G(_LIB_KEY, None)
    _G(_LIB_BUILD_TS_KEY, 0)


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
    if ctype == "KILL":
        _G(_RUNTIME_KILL_KEY, True)
        return "killed_new_risk"
    if ctype == "RESUME":
        _G(_RUNTIME_KILL_KEY, None)
        _G(_LOCKED_KEY, None)                          # 恢复要求重新对账 + 新的计划硬批准
        return "resumed_requires_new_plan_approval"
    if ctype == "REJECT":
        _G(_LOCKED_KEY, None)
        return "rejected_back_to_wait"
    if ctype == "EXECUTE":
        return _handle_execute(cmd.get("arg"), now_ms)
    if ctype == "EXIT_AUTHORIZE":
        return _handle_exit_authorize(cmd.get("arg"), now_ms, POLICY_TAKE_PROFIT)
    if ctype == "RISK_EXIT_AUTHORIZE":
        return _handle_exit_authorize(cmd.get("arg"), now_ms, POLICY_RISK_EXIT)
    if ctype == "EXIT_REVOKE":
        return _handle_exit_revoke(now_ms)
    return "noop"


def _handle_exit_authorize(code, now_ms, policy):
    """软授权：校验授权码与当前 position+policy 匹配 → 落 _G（与 position_id 绑定，非阻塞）。"""
    snap = _G(_POSITION_KEY)
    pos_id = (snap or {}).get("position_id")
    if not pos_id:
        return "no_position_to_authorize"
    kw = {}
    if policy == POLICY_RISK_EXIT:
        # 风险退出：RISK_EXIT_MAX_SPEND=0 时只用入场冻结预算，不额外放大止损额度。
        max_spend = RISK_EXIT_MAX_SPEND if RISK_EXIT_MAX_SPEND > 0 else (snap or {}).get("max_total_exit_spend")
        kw = {"max_exit_spend": max_spend, "allowed_order_types": ["limit"]}
    auth = authorize_from_code(code, pos_id, policy, now_ms, **kw)
    if not auth:
        return "auth_code_invalid"
    _G(_EXIT_AUTH_KEY, auth)
    return "authorized:" + policy


def _handle_exit_revoke(now_ms):
    auth = _G(_EXIT_AUTH_KEY)
    if not auth:
        return "no_authorization"
    _G(_EXIT_AUTH_KEY, revoke(auth, now_ms))
    return "revoked"


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
        "no_unknown_orders": _no_unknown_orders(SETTLEMENT_CURRENCY, [short_i, long_i]),  # C3：真实活动订单查询
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
        "audit_card_id": locked.get("audit_card_id"),
        "operator_note": locked.get("operator_note"),
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
    **跨轮持久重挂**（替代一次性追价）。预提交不过/门控关 → 仅空跑预览；两腿成交达标 → 冻结入场快照；
    超 ENTRY_MAX_ATTEMPTS 仍未成交 → 放弃(撤/回退保护腿残量、清锁回等待)。低成本 ∧ 提高成功率。"""
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
                                    allow_live=gate["allowed"], label="entry")
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
        prog["attempts"] += 1
        locked["entry"] = prog
        _G(_LOCKED_KEY, locked)
        if _has_entry_progress(prog) and not (prog["prot_done"] >= amount - 1e-12
                                             and prog["short_done"] >= amount - 1e-12):
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
    return result


_RECOVERY_KEY = "spm_recovery_verdict_v1"
_EXIT_AUTH_KEY = "spm_exit_auth_v1"          # E5 软授权
_CLOSED_HISTORY_KEY = "spm_closed_history_v1"


def _recovery_verdict():
    return _G(_RECOVERY_KEY) or {"state": "OK", "allow_new_open": True}


def _archive_closed(snap, now_ms):
    """P0②：两腿 + 对冲 perp 均归零 → 归档 closed_position_history、清快照/授权、置 CLOSED。"""
    hist = list(_G(_CLOSED_HISTORY_KEY) or [])
    rec = dict(snap or {})
    rec["closed_ts"] = now_ms
    hist.append(rec)
    _G(_CLOSED_HISTORY_KEY, hist[-50:])
    _G(_POSITION_KEY, None)
    _G(_EXIT_AUTH_KEY, None)
    ledger_set_state(S_CLOSED)


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
        opt = dbt_get_positions(currency, "option") or []
    except Exception:
        opt = []
    try:
        perp = dbt_get_positions(currency, "future") or []
    except Exception:
        perp = []
    perp_qty = sum(abs(p.get("size") or 0.0) for p in perp)
    if HEDGE_VENUE == "BINANCE":
        b_qty = bnc_get_position_btc(HEDGE_BINANCE_INSTRUMENT)
        if b_qty is None:
            return opt, None, {"state": "RECOVERY_BLOCKED",
                               "reasons": ["HEDGE_POSITION_QUERY_FAILED"],
                               "allow_new_open": False}
        perp_qty = abs(b_qty)
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
    _G(_RECOVERY_KEY, verdict)
    return verdict


def _evaluate_take_profit(snap, quote_fn=None):
    """据入场快照 + 实时短腿盘口算止盈资格(参考捕获率) 与退出预算/价格上限。保护腿价值不入分母。"""
    if not snap:
        return {"ratio": None, "qualified": False, "remaining_short_qty": 0.0,
                "remaining_budget": None, "price_cap": 0.0, "quote_ok": False}
    rem_qty = snap.get("remaining_short_qty") or 0.0
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
    qualified = take_profit_qualified(ratio, snap.get("take_profit_target_ratio") or 0.80)
    fee_reserve = reserve or 0.0
    rem_budget = short_buyback_budget(max_spend, realized, fee_reserve)
    tick = (q or {}).get("tick") or 0.0
    cap = short_buyback_price_cap(rem_budget, fee_reserve, rem_qty, tick) if rem_budget else 0.0
    return {"ratio": ratio, "qualified": qualified, "remaining_short_qty": rem_qty,
            "remaining_budget": rem_budget, "price_cap": cap, "quote_ok": quote_ok}


def _risk_exit_budget_cap(snap, auth, quote_fn=None):
    """风险退出预算/价格上限（F1）：用**风险退出授权**的 max_exit_spend(=RISK_EXIT_MAX_SPEND) 反推，
    **独立于止盈 20% 缓冲**；并判定能否越价吃单(best_ask ≤ cap)。
    无风险退出授权 / 无预算 / 无盘口 → (None, 0.0, False)（不可下单 → 仲裁回退对冲）。"""
    max_spend = (auth or {}).get("max_exit_spend")
    rem_qty = (snap or {}).get("remaining_short_qty") or 0.0
    if not isinstance(max_spend, (int, float)) or max_spend <= 0 or rem_qty <= 0:
        return None, 0.0, False
    quote = quote_fn or exec_quote
    q = quote((snap or {}).get("short_instrument")) or {}
    realized = (snap or {}).get("realized_exit_spend") or 0.0
    fee_reserve = acct_option_fee_ccy(q.get("mark") or 0.0, rem_qty)
    rem_budget = short_buyback_budget(max_spend, realized, fee_reserve)
    tick = q.get("tick") or 0.0
    cap = short_buyback_price_cap(rem_budget, fee_reserve, rem_qty, tick) if rem_budget else 0.0
    ask = q.get("best_ask")
    within = bool(ask is not None and cap > 0 and ask <= cap + 1e-12)
    return rem_budget, cap, within


def _apply_exit_fill(snap, step, now_ms):
    """把一次短腿买回成交计入入场快照：减剩余短腿、加已用退出支出；归零则转 SHORT_FLAT_LONG_RESIDUAL。"""
    filled = step.get("filled") or 0.0
    price = step.get("avg_price") or step.get("price") or 0.0
    fee = acct_option_fee_ccy(price, filled)
    snap["remaining_short_qty"] = max(0.0, (snap.get("remaining_short_qty") or 0.0) - filled)
    snap["realized_exit_spend"] = (snap.get("realized_exit_spend") or 0.0) + price * filled + fee
    snap["last_exit_ts"] = now_ms
    _append_execution_history(snap, "exit_execution_history", step, now_ms)
    if snap["remaining_short_qty"] <= 1e-12:
        ledger_set_state(S_SHORT_FLAT_LONG_RESIDUAL)   # 短腿归零，转保护腿回收（不可直跳 CLOSED）
    _G(_POSITION_KEY, snap)


def _evaluate_hedge(snap, quote_fn=None):
    """对冲决策（场所感知）：按 HEDGE_VENUE 选 Deribit(反向) 或 Binance(线性) → perp 真实持仓 +
    目标(随剩余短腿敞口) + open/reduce 动作 + 孤儿。默认不真实下单。"""
    rem_qty = (snap or {}).get("remaining_short_qty") or 0.0
    long_qty = (snap or {}).get("long_remaining_qty")
    if long_qty is None:
        long_qty = (snap or {}).get("long_fill_amount") or 0.0
    vcfg = hedge_venue_config(HEDGE_VENUE, HEDGE_BINANCE_INSTRUMENT, HEDGE_BINANCE_EXCHANGE_INDEX)
    state = "SETTLED" if rem_qty <= 0 else "OPEN"
    si, li = (snap or {}).get("short_instrument"), (snap or {}).get("long_instrument")
    quote = quote_fn or exec_quote
    short_delta = (quote(si) or {}).get("delta") if si else None
    prot_delta = (quote(li) or {}).get("delta") if li else None
    if vcfg["venue"] == "BINANCE":
        perp_qty = bnc_get_position_btc(vcfg["instrument"])
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
                "data_gap": "HEDGE_POSITION_DATA_GAP"}
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
                "data_gap": "HEDGE_DELTA_DATA_GAP"}
    else:
        net_opt = option_net_delta(rem_qty, short_delta, long_qty, prot_delta)
        target = hedge_target_position(net_opt, HEDGE_REDUCTION_RATIO, _spot_price(),
                                       contract_size, min_trade, linear=vcfg["linear"])
    action = hedge_order_action(perp_qty, target, min_trade)
    delta_to_trade = (target or 0.0) - (perp_qty or 0.0)
    side = "buy" if delta_to_trade > 0 else ("sell" if delta_to_trade < 0 else hedge_side((snap or {}).get("side")))
    struct_delta = structure_net_delta(short_delta, prot_delta)
    consistent = hedge_direction_consistent((snap or {}).get("side"), struct_delta)
    if not consistent and action["action"] in ("HEDGE_OPEN", "HEDGE_INCREASE"):
        action = {"action": "HEDGE_HOLD", "reduce_only": False, "delta_contracts": 0.0,
                  "blocked": "DIRECTION_INCONSISTENT"}
    return {"perp_qty": perp_qty, "target": target, "action": action,
            "orphan": hedge_orphan(rem_qty, perp_qty),
            "side": side,
            "net_delta": struct_delta, "net_option_delta": net_opt,
            "delta_to_trade": delta_to_trade,
            "direction_consistent": consistent,
            "venue": vcfg["venue"], "instrument": vcfg["instrument"], "venue_cfg": vcfg}


def _exit_friction_from_short_quote(short_quote):
    sr = exec_spread_ratio(short_quote)
    return {"option_exit_friction": ("HIGH" if sr is None or sr > MAX_SPREAD_RATIO else "LOW"),
            "future_hedge_friction": "LOW"}


def _evaluate_position_risk_now(snap, now_ms, existing_hedge=False, quote_fn=None):
    """持仓后风险评估（接 hedge_risk.evaluate_position_risk）：入场风险锚 + 当前短腿行情 →
    PositionRiskPackage（触界概率/漂移/尾部加速/持续性 → tail_risk_state）。
    无快照 / 无入场锚 → None（不驱动主动退出/对冲，保守留给止盈资格 + 孤儿）。
    注：无执行侧风险上下文时 persistence 恒 LOW；有人工审计/执行风险上下文时进入持续性判定。"""
    anchor = (snap or {}).get("entry_risk_anchor")
    if not snap or not anchor:
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
    return evaluate_position_risk(
        position_id=snap.get("position_id"),
        direction_bias=_side_to_direction_bias(snap.get("side")),
        entry_risk_anchor=anchor, current_price=_spot_price(),
        dte_hours=dte_h, short_delta=sq.get("delta"), short_gamma=sq.get("gamma"),
        iv=sq.get("mark_iv"), loss_boundary=anchor.get("entry_loss_boundary"),
        edb=None,
        gamma_regime=None,
        exit_friction=_exit_friction_from_short_quote(sq),
        existing_hedge=existing_hedge)


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


def manage_cycle(now_ms):
    """持仓管理一轮（§9.1）：对账(快照为真相) + 止盈资格；退出/对冲由四输出仲裁**单动作收口**
    （每轮仅执行 executable 的风险动作）；短腿归零后回收保护腿(清理)；两腿+对冲 perp 归零→归档 CLOSED。
    **退出活动期禁新增对冲敞口**（只许 reduce/unwind）。退出/对冲/回收真实下单均受各自门控，默认空跑。"""
    snap = _G(_POSITION_KEY)
    pos_id = (snap or {}).get("position_id")
    recovery = _recovery_verdict()
    auth = _G(_EXIT_AUTH_KEY)
    authorized = is_authorized(auth, pos_id, now_ms)
    tp_code = auth_code(pos_id, POLICY_TAKE_PROFIT) if pos_id else None
    risk_code = auth_code(pos_id, POLICY_RISK_EXIT) if pos_id else None
    try:
        opt_pos = dbt_get_positions(SETTLEMENT_CURRENCY, "option") or []
    except Exception:
        opt_pos = []
    rec = position_reconcile(snap, opt_pos)        # P0①：快照 vs 交易所（surfaced；不阻断风险收口）

    quote_fn = _quote_cache()
    tp = _evaluate_take_profit(snap, quote_fn)
    rem_short = tp["remaining_short_qty"]
    long_rem = (snap or {}).get("long_remaining_qty")
    if long_rem is None:
        long_rem = (snap or {}).get("long_fill_amount") or 0.0

    # 风险严重度（接 hedge_risk）：先算对冲(取 perp 持仓判 existing_hedge) → 风险包 → 仲裁输入
    hedge = _evaluate_hedge(snap, quote_fn)
    in_flight = _manage_in_flight_orders(snap, hedge)
    existing_hedge = abs(hedge.get("perp_qty") or 0.0) > 1e-9
    risk = _evaluate_position_risk_now(snap, now_ms, existing_hedge, quote_fn)
    risk_state = (risk or {}).get("tail_risk_state")
    hedge_ready = risk_state == STATE_HEDGE_READY            # 风险概率相对入场锚恶化
    exit_preferred = hedge_ready                             # 风险触发时先尝试授权退出，不可执行再回退对冲

    # 退出活动触发 = 止盈资格 ∨ 风险主动退出。
    # F1：风险退出用**独立预算/价格上限**(风险退出授权 max_exit_spend)、且可越价吃单(within=ask≤cap)；
    #     止盈退出沿用 80% 缓冲、被动 maker(patient，恒 within)。
    risk_exit = exit_preferred                               # 风险驱动退出（区别于止盈资格退出）
    if risk_exit:
        exit_budget, exit_cap, exit_within = _risk_exit_budget_cap(snap, auth, quote_fn)
    else:
        exit_budget, exit_cap, exit_within = tp["remaining_budget"], tp["price_cap"], True
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
        "exit_preferred": exit_preferred, "hedge_ready": hedge_ready,   # 风险严重度→仲裁（接回 hedge_risk）
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
        hedge_step = exec_hedge_step(hedge["venue_cfg"], hedge["side"], hedge["action"]["delta_contracts"],
                                     h_reduce, allow_live=True, label="hedge",
                                     execution_style=HEDGE_OPEN_EXECUTION_STYLE,
                                     max_slippage_bps=HEDGE_MAX_SLIPPAGE_BPS)
        if hedge_step and not hedge_step.get("dry") and snap:
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
                snap["long_remaining_qty"] = max(0.0, long_rem - r["sold"])
                _append_execution_history(snap, "protection_recovery_history",
                                          r.get("execution") or r, now_ms)
                _G(_POSITION_KEY, snap)
                long_rem = snap["long_remaining_qty"]

    # P0② CLOSED 归档：两腿 + 对冲 perp 均归零（对冲未归零不 CLOSED）
    if snap and rem_short <= 1e-12 and long_rem <= 1e-12 and abs(hedge.get("perp_qty") or 0.0) <= 1e-9:
        _archive_closed(snap, now_ms)

    return {"arb": arb, "entry_snapshot": snap, "reconcile": rec, "executable": executable,
            "auth": auth, "authorized": authorized, "tp_auth_code": tp_code,
            "risk_exit_auth_code": risk_code, "risk_exit": risk_exit, "exit_executable": exit_executable,
            "exit_campaign_state": (long_state or exit_state), "tp_ratio": tp["ratio"], "hedge": hedge,
            "hedge_step": hedge_step, "risk_state": risk_state, "risk": risk,
            "manage_in_flight_order": in_flight}


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
    display_candidates = []
    not_lockable_reason = None
    plan_vrp_blocked = 0
    commit_result = None
    manage_result = None
    recovery = _recovery_verdict()
    rec_ok = recovery.get("allow_new_open", True)

    if recovery.get("state") == "RECOVERY_BLOCKED":
        phase = "RECOVERY_BLOCKED"
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
            _clear_plan_lineage()
            lib = None
        last_build = int(_G(_LIB_BUILD_TS_KEY) or 0)
        if spot and (not lib or now_ms - last_build >= PLAN_REFRESH_SECONDS * 1000):
            menu, _pm_ok, _model, reason, diag = _build_menu(now_ms, spot, manual_context)
            display_candidates = list(menu or [])
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
                _clear_plan_lineage()
                lib = None
                if reason != "OK" and not not_lockable_reason:
                    not_lockable_reason = reason
        if lib and lib.get("recommendations"):
            pending = [{"id": s["plan_id"], "summary": s["summary"],
                        "confirm_code": s["confirm_code"]}
                       for s in lib["recommendations"][:MENU_SIZE]]
            phase = "HARD_APPROVAL_WAIT"

    ctx = _ctx_base(state, spot, "RUN_CYCLE:" + phase)
    _apply_manual_context_to_ctx(ctx, manual_context, manual_check)
    ctx["console_phase"] = phase
    if phase == "WAIT_MANUAL_AUDIT_GATE":
        ctx["manual_gate_status"] = "WAIT_MANUAL_AUDIT_GATE"
    ctx["gate_summary"] = gsum
    ctx["lineage_invalidation"] = lineage_invalidation
    ctx["pending_candidates"] = pending
    ctx["display_candidates_count"] = len(display_candidates)
    ctx["lockable_candidates_count"] = len(pending)
    ctx["not_lockable_reason"] = not_lockable_reason
    ctx["plan_vrp_blocked"] = plan_vrp_blocked
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
        if commit_result.get("entry_snapshot"):
            ctx["entry_snapshot"] = commit_result["entry_snapshot"]
    if manage_result:
        ctx["action_arb"] = manage_result.get("arb")
        ctx["entry_snapshot"] = manage_result.get("entry_snapshot")
        ctx["reconciled"] = (manage_result.get("reconcile") or {}).get("reconciled")
        ctx["risk_state"] = manage_result.get("risk_state")
        ctx["risk_pkg"] = manage_result.get("risk")
        ctx["manage_in_flight_order"] = manage_result.get("manage_in_flight_order")
        ctx["risk_exit_auth_code"] = manage_result.get("risk_exit_auth_code")
        ctx["exit_campaign_state"] = manage_result.get("exit_campaign_state")
        _r = manage_result.get("tp_ratio")
        ctx["take_profit_ratio"] = ("%.1f%%" % (_r * 100)) if isinstance(_r, (int, float)) else "DATA_GAP"
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
    if locked and not (commit_result and commit_result.get("committed")):
        ctx["locked_plan_summary"] = "%s %s" % (locked.get("confirm_code"), locked.get("summary"))
        ctx["preview_plan_detail"] = "locked_plan"
        ctx["selected_id"] = locked.get("plan_id")
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
    startup_recovery_check(SETTLEMENT_CURRENCY)        # 启动恢复：可解释映射 → OK/RECOVERY_BLOCKED/ORPHAN

    while True:
        try:
            run_cycle()
        except Exception as e:
            Log("[loop] 异常:", str(e))
        Sleep(LOOP_INTERVAL_MS)
