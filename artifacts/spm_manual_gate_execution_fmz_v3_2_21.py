# -*- coding: utf-8 -*-
# === 自动合成产物：请勿手改，改 src/ 后重新 build_bundle.py ===
# Deribit S:PM 垂直信用价差卖方执行链 v3.2.21-manual-gate（FMZ 单文件；单一 run_cycle 主链 + 交互控制台 + 对冲生命周期）


# ===================== module: config =====================
# -*- coding: utf-8 -*-
"""
Human Audit Gate 执行层配置块（FMZ 启动前手填）。

本版本只接受执行层本地人工审计配置：方向、数量、delta 范围、腿宽、
风险退出预算和分动作授权门控均来自这些 UPPER_CASE 参数。信号层不参与
执行主链路。交易员通常只需要看本文件顶部几个配置块。
"""

# ===== 当前版本 / 实例标识 =====
ROBOT_ID = "spm-exec-1"            # 命令幂等键的一部分；多机器人并行时必须各自唯一
STRATEGY_VERSION = "3.2.21-manual-gate"
SETTLEMENT_RECONCILE_GRACE_MS = 5 * 60 * 1000
RUN_PROFILE = "LIVE"              # TEST=强制所有真实交易门关闭；LIVE=按 ALLOW_* 门控执行

# ===== VRP_CONTEXT 数据源（只检查上下文有效性，不做旧价格门控）=====
GEX_CONTEXT_API_BASE = "http://13.231.16.198:8000"
GEX_CONTEXT_API_KEY = "7WkM4LBAha7di0KMCtgty3NwdQcNXI5-j3o8MymkGiE"
GEX_CONTEXT_TIMEOUT_SECONDS = 5

# ===== 交易员核心输入（当前小额实盘测试面）=====
SETTLEMENT_CURRENCY = "BTC"        # 结算币；当前主流程为 BTC
MANUAL_PLANNING_ALLOWED = True     # True=允许按本地人工视图生成候选；False=只管持仓/退出/恢复
DIRECTION_BIAS = "SHORT_PUT"      # SHORT_CALL=偏空卖 Call；SHORT_PUT=偏多卖 Put
ORDER_AMOUNT = 0.1                 # 单结构数量（Deribit BTC 期权常用最小步长 0.1）
SHORT_DELTA_RANGE = (0.15, 0.45)   # 短腿 |delta| 接受范围
PROTECTION_WIDTH_RANGE = (2000, 2500)  # 保护腿腿宽范围(USD)，以短腿行权价为基准
RISK_EXIT_MAX_SPEND = 0.001        # 风险退出最大支出(BTC)；风险触发时的独立成本上限

# ===== 到期 / 排序默认值 =====
TARGET_DTE_HOURS = 24              # 候选围绕 24h 到期；再取之后一个更晚到期作为备选
ENDGAME_DTE_HOURS = 24             # 末日轮阈值：剩余 DTE 不高于此值时启用近到期保护腿宽容
ENDGAME_PROTECTION_WIDTH_MIN = 1500  # 末日轮保护腿最小腿宽；普通轮仍使用 PROTECTION_WIDTH_RANGE
ENDGAME_PROTECTION_CHOICES_PER_SHORT = 2  # 末日轮每个短腿最多保留的保护腿宽度候选数
MENU_SIZE = 10                     # 状态栏最多展示候选条数
PLAN_WEIGHTS = {"win_rate": 0.35, "rr": 0.25, "efficiency": 0.40, "manual": 0.0}
UNDERLYING_REF_PRICE = None        # None=走实时 index；仅测试/演练时可固定参考价

# ===== 候选质量 / 执行安全门 =====
MIN_MARGIN_RELIEF_RATIO = 0.0      # 软展示底线；组合预算仍是硬门
THIN_SHORT_PREMIUM_WARN = 0.0005   # 短腿权利金过薄提示线；不再硬挡 24h 候选
DEEP_OTM_MAX_DELTA = 0.05          # 保护腿过度虚值提示/筛选参考
MAX_SPREAD_RATIO = 0.60            # 相对价差上限；真实执行前仍 fail-closed
PROTECTION_LOW_PREMIUM_MAX = 0.0006     # 低价保护腿可用绝对价差门替代相对价差门
PROTECTION_ABS_SPREAD_MAX = 0.00025     # 保护腿绝对 bid-ask 宽度上限

# ===== 入场执行参数 =====
MAX_CHASE_STEPS = 1                # 单次下单计划价最多追价步数
CHASE_WAIT_SECONDS = 8             # 挂单后判定未成交的等待秒数
ENTRY_MIN_NET_CREDIT = 0.0         # 入场净 credit 下限；0=至少非负
ENTRY_MAX_TICK_STEPS = 3           # 开仓活动在信用底线内最多逐 tick 改价档数
ENTRY_MAX_ATTEMPTS = 20            # 开仓活动软计数上限；无成交不清锁，保护腿改由时间上限触发 taker
ENTRY_PROTECTION_TAKER_AFTER_SECONDS = 600 # 保护腿 maker 持续等待上限；超过后受控吃卖一
ENTRY_SHORT_ORDER_WAIT_SECONDS = 60        # 卖方腿 maker 挂单存续；实盘观察后延长等待

# ===== 分动作真实交易授权门控 =====
ALLOW_ENTRY_TRADING = True         # 新开垂直价差（新增风险）
ALLOW_EXIT_TRADING = True          # 买回短腿 / 卖出保护腿（降低期权风险）
ALLOW_HEDGE_TRADING = True         # Binance BTCUSDC 永续 / Deribit BTC-PERPETUAL 对冲
KILL_NEW_RISK = False              # 急停：停新风险；不阻断退出、对冲减仓、对账和孤儿清理
EMERGENCY_REDUCE_ONLY = False      # 紧急只减：禁止任何开/加仓，对冲强制 reduce_only
DRY_RUN_PASSED = True              # 实盘门开启前的人工确认项；False 时 live gates 必须关闭

# ===== 运行节奏 =====
LOOP_INTERVAL_MS = 3000            # 主循环间隔；状态栏按此刷新
PLAN_REFRESH_SECONDS = 45          # 方案库重算最小间隔：节流 API，并避免日志/状态过度刷新
APPROVAL_TTL_MS = 30 * 60 * 1000   # 方案确认码有效期；超时清锁并要求重新确认

# ===== 组合投影预算限额（fail-closed）=====
PORTFOLIO_LIMITS = {
    "max_open_positions": 1,
    "max_short_gamma": 0.05,
    "max_short_vega": 0.50,
    "max_margin": 0.50,
    "max_spread_loss_per_trade": 0.02,
}

# ===== 退出活动参数 =====
EXIT_QUOTE_REFRESH_MS = 3000
EXIT_ORDER_REST_MS = 4000
EXIT_REPRICE_COOLDOWN_MS = 6000
EXIT_MAX_ACTIVE_ORDERS = 1
EXIT_MAX_PRICE_STEPS_PER_LOOP = 1
EXIT_RESERVE_RATIO = 0.15          # 退出预算中的费用/保守预留比例
TAKE_PROFIT_MIN_DTE_HOURS = 3.0    # 普通 80% 捕获止盈要求剩余到期 > 该小时数；风险退出/对冲不受此限制

# ===== 对冲（最小 V32 生产链路只支持 Binance BTCUSDC 永续）=====
HEDGE_REDUCTION_RATIO = 0.5        # gamma-aware 关闭时的 legacy full target ratio；默认 V32 full target 使用 RAW_FULL_DELTA
HEDGE_OPEN_EXECUTION_STYLE = "PROMPT_LIMIT"
HEDGE_MAX_SLIPPAGE_BPS = 5
HEDGE_VENUE = "BINANCE"            # Minimal V32 hedge supports BINANCE only
HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"   # 交易员配置仍写 BTCUSDC；FMZ 内部会切 BTC_USDC + swap
HEDGE_BINANCE_MIN_TRADE = 0.001        # 币安 BTCUSDC 最小下单(BTC, 线性)
HEDGE_BINANCE_PRICE_TICK = 0.1         # BTCUSDC 永续限价价格最小跳动；买入向上、卖出向下取整
HEDGE_BINANCE_EXCHANGE_INDEX = 1       # FMZ exchanges[] 下标：exchanges[0]=Deribit, [1]=Binance Futures

# ===== Binance hedge controller V32 policy =====
HEDGE_POLICY_V32_ENABLED = True
# Compatibility alias for older tests/docs; V32 is the primary switch.
HEDGE_POLICY_V313_ENABLED = HEDGE_POLICY_V32_ENABLED
HEDGE_STAGING_ENABLED = True
HEDGE_HYSTERESIS_ENABLED = True
HEDGE_COOLDOWN_ENABLED = True
HEDGE_SOFT_INITIAL_RATIO = 0.40
HEDGE_SOFT_ADD_DRIFT_STEP = 0.05
HEDGE_HARD_DRIFT = 0.35
HEDGE_HARD_CROSS_BPS = 30
HEDGE_SOFT_CROSS_BPS = 3
HEDGE_GAMMA_AWARE_ENABLED = True
HEDGE_GAMMA_FRAC_FLOOR = 0.30
HEDGE_GAMMA_NORM_REF = 1_000_000.0
HEDGE_REBALANCE_BAND_FRAC = 0.20
HEDGE_MARGIN_RESERVE_RATE = 0.10
HEDGE_MIN_HOLD_SECONDS = 720
HEDGE_FINAL3H_MODE = "SUPPRESS_SOFT_ADD"
HEDGE_CRASH_ENABLED = True
HEDGE_CRASH_SPEED_WINDOW_SECONDS = 600
HEDGE_CRASH_MOVE_BPS = 110
HEDGE_SOFT_PERSIST_SECONDS = 60
HEDGE_REDUCE_PERSIST_SECONDS = 20
HEDGE_REDUCE_PROB_BUFFER = 0.05
HEDGE_ADD_COOLDOWN_SECONDS = 30
HEDGE_REDUCE_COOLDOWN_SECONDS = 60
HEDGE_EPISODE_COST_ALERT_BPS = 20
HEDGE_PENDING_STALE_SECONDS = 10


def normalize_run_profile(run_profile=None):
    return str(RUN_PROFILE if run_profile is None else run_profile).strip().upper()


def effective_trading_gates(run_profile=None, allow_entry=None, allow_exit=None, allow_hedge=None):
    profile = normalize_run_profile(run_profile)
    raw_entry = ALLOW_ENTRY_TRADING if allow_entry is None else allow_entry
    raw_exit = ALLOW_EXIT_TRADING if allow_exit is None else allow_exit
    raw_hedge = ALLOW_HEDGE_TRADING if allow_hedge is None else allow_hedge
    if profile == "TEST":
        return {"profile": profile, "allow_entry": False,
                "allow_exit": False, "allow_hedge": False}
    return {"profile": profile, "allow_entry": bool(raw_entry),
            "allow_exit": bool(raw_exit), "allow_hedge": bool(raw_hedge)}


def live_checklist_missing(run_profile=None, dry_run_passed=None,
                           allow_entry=None, allow_exit=None, risk_exit_max_spend=None):
    if normalize_run_profile(run_profile) != "LIVE":
        return []
    dry = DRY_RUN_PASSED if dry_run_passed is None else dry_run_passed
    entry = ALLOW_ENTRY_TRADING if allow_entry is None else allow_entry
    exit_ = ALLOW_EXIT_TRADING if allow_exit is None else allow_exit
    budget = RISK_EXIT_MAX_SPEND if risk_exit_max_spend is None else risk_exit_max_spend
    missing = []
    if dry is not True:
        missing.append("DRY_RUN_PASSED")
    if entry is not True:
        missing.append("ALLOW_ENTRY_TRADING")
    if exit_ is not True:
        missing.append("ALLOW_EXIT_TRADING")
    if not isinstance(budget, (int, float)) or isinstance(budget, bool) or budget <= 0:
        missing.append("RISK_EXIT_MAX_SPEND")
    return missing


def _valid_pair(pair, lo=None, hi=None, inclusive_hi=False):
    if not isinstance(pair, (tuple, list)) or len(pair) != 2:
        return False
    a, b = pair
    if not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return False
    if isinstance(a, bool) or isinstance(b, bool) or not a < b:
        return False
    if lo is not None and not (lo < a):
        return False
    if hi is not None:
        return b <= hi if inclusive_hi else b < hi
    return True


def validate_config():
    errs = []
    profile = normalize_run_profile()
    if profile not in ("TEST", "LIVE"):
        errs.append("RUN_PROFILE must be TEST or LIVE")
    if SETTLEMENT_CURRENCY not in ("BTC", "ETH"):
        errs.append("SETTLEMENT_CURRENCY must be BTC or ETH")
    if not isinstance(MANUAL_PLANNING_ALLOWED, bool):
        errs.append("MANUAL_PLANNING_ALLOWED must be bool")
    if DIRECTION_BIAS not in ("SHORT_CALL", "SHORT_PUT"):
        errs.append("DIRECTION_BIAS must be SHORT_CALL or SHORT_PUT")
    if not isinstance(TARGET_DTE_HOURS, (int, float)) or isinstance(TARGET_DTE_HOURS, bool) or TARGET_DTE_HOURS <= 0:
        errs.append("TARGET_DTE_HOURS must be > 0")
    if not isinstance(ENDGAME_DTE_HOURS, (int, float)) or isinstance(ENDGAME_DTE_HOURS, bool) or ENDGAME_DTE_HOURS <= 0:
        errs.append("ENDGAME_DTE_HOURS must be > 0")
    if not isinstance(ENDGAME_PROTECTION_WIDTH_MIN, (int, float)) or isinstance(ENDGAME_PROTECTION_WIDTH_MIN, bool) or ENDGAME_PROTECTION_WIDTH_MIN <= 0:
        errs.append("ENDGAME_PROTECTION_WIDTH_MIN must be > 0")
    if not isinstance(ENDGAME_PROTECTION_CHOICES_PER_SHORT, int) or isinstance(ENDGAME_PROTECTION_CHOICES_PER_SHORT, bool) or ENDGAME_PROTECTION_CHOICES_PER_SHORT < 1:
        errs.append("ENDGAME_PROTECTION_CHOICES_PER_SHORT must be >= 1")
    if ORDER_AMOUNT <= 0:
        errs.append("ORDER_AMOUNT must be positive")
    if not _valid_pair(SHORT_DELTA_RANGE, 0, 1):
        errs.append("SHORT_DELTA_RANGE must satisfy 0<min<max<1")
    if not isinstance(PROTECTION_WIDTH_RANGE, (tuple, list)) or len(PROTECTION_WIDTH_RANGE) != 2 \
            or PROTECTION_WIDTH_RANGE[0] > PROTECTION_WIDTH_RANGE[1]:
        errs.append("PROTECTION_WIDTH_RANGE invalid")
    if MENU_SIZE < 1:
        errs.append("MENU_SIZE must be >= 1")
    if THIN_SHORT_PREMIUM_WARN < 0:
        errs.append("THIN_SHORT_PREMIUM_WARN must be non-negative")
    if not (0 < MAX_SPREAD_RATIO <= 5):
        errs.append("MAX_SPREAD_RATIO must be in (0,5]")
    if PROTECTION_LOW_PREMIUM_MAX < 0 or PROTECTION_ABS_SPREAD_MAX < 0:
        errs.append("protection spread thresholds must be non-negative")
    if PLAN_REFRESH_SECONDS < 1:
        errs.append("PLAN_REFRESH_SECONDS must be >= 1")
    if APPROVAL_TTL_MS <= 0:
        errs.append("APPROVAL_TTL_MS must be > 0")
    if not (0.0 <= MIN_MARGIN_RELIEF_RATIO < 1.0):
        errs.append("MIN_MARGIN_RELIEF_RATIO must be in [0,1)")
    for n, v in (("ALLOW_ENTRY_TRADING", ALLOW_ENTRY_TRADING),
                 ("ALLOW_EXIT_TRADING", ALLOW_EXIT_TRADING),
                 ("ALLOW_HEDGE_TRADING", ALLOW_HEDGE_TRADING),
                 ("KILL_NEW_RISK", KILL_NEW_RISK),
                 ("EMERGENCY_REDUCE_ONLY", EMERGENCY_REDUCE_ONLY),
                 ("DRY_RUN_PASSED", DRY_RUN_PASSED)):
        if not isinstance(v, bool):
            errs.append(n + " must be bool")
    for missing in live_checklist_missing():
        errs.append("RUN_PROFILE=LIVE requires " + missing)
    gates = effective_trading_gates()
    live_gates = gates["allow_entry"] or gates["allow_exit"] or gates["allow_hedge"]
    if live_gates and not DRY_RUN_PASSED:
        errs.append("DRY_RUN_PASSED=False; live trading gates must stay disabled")
    if gates["allow_entry"]:
        if not gates["allow_exit"]:
            errs.append("ALLOW_ENTRY_TRADING=True requires ALLOW_EXIT_TRADING=True")
        if RISK_EXIT_MAX_SPEND <= 0:
            errs.append("ALLOW_ENTRY_TRADING=True requires RISK_EXIT_MAX_SPEND > 0")
    if RISK_EXIT_MAX_SPEND < 0:
        errs.append("RISK_EXIT_MAX_SPEND must be non-negative")
    if not (0 <= EXIT_RESERVE_RATIO < 1):
        errs.append("EXIT_RESERVE_RATIO must be in [0,1)")
    if not (0 < HEDGE_REDUCTION_RATIO <= 1):
        errs.append("HEDGE_REDUCTION_RATIO must be in (0,1]")
    if HEDGE_OPEN_EXECUTION_STYLE != "PROMPT_LIMIT":
        errs.append("HEDGE_OPEN_EXECUTION_STYLE must be PROMPT_LIMIT")
    if not isinstance(HEDGE_MAX_SLIPPAGE_BPS, (int, float)) or isinstance(HEDGE_MAX_SLIPPAGE_BPS, bool) or HEDGE_MAX_SLIPPAGE_BPS < 0:
        errs.append("HEDGE_MAX_SLIPPAGE_BPS must be a non-negative number")
    if not (0 <= HEDGE_SOFT_INITIAL_RATIO <= 1):
        errs.append("HEDGE_SOFT_INITIAL_RATIO must be in [0,1]")
    if not (0 <= HEDGE_GAMMA_FRAC_FLOOR <= 1):
        errs.append("HEDGE_GAMMA_FRAC_FLOOR must be in [0,1]")
    if not isinstance(HEDGE_GAMMA_NORM_REF, (int, float)) or isinstance(HEDGE_GAMMA_NORM_REF, bool) or HEDGE_GAMMA_NORM_REF <= 0:
        errs.append("HEDGE_GAMMA_NORM_REF must be > 0")
    if not (0 <= HEDGE_REBALANCE_BAND_FRAC <= 1):
        errs.append("HEDGE_REBALANCE_BAND_FRAC must be in [0,1]")
    if not isinstance(HEDGE_MARGIN_RESERVE_RATE, (int, float)) or isinstance(HEDGE_MARGIN_RESERVE_RATE, bool) or HEDGE_MARGIN_RESERVE_RATE < 0:
        errs.append("HEDGE_MARGIN_RESERVE_RATE must be a non-negative number")
    if not isinstance(HEDGE_MIN_HOLD_SECONDS, (int, float)) or isinstance(HEDGE_MIN_HOLD_SECONDS, bool) or HEDGE_MIN_HOLD_SECONDS < 0:
        errs.append("HEDGE_MIN_HOLD_SECONDS must be >= 0")
    if HEDGE_FINAL3H_MODE not in ("NORMAL", "SUPPRESS_SOFT_ADD"):
        errs.append("HEDGE_FINAL3H_MODE must be NORMAL or SUPPRESS_SOFT_ADD")
    if not isinstance(HEDGE_CRASH_MOVE_BPS, (int, float)) or isinstance(HEDGE_CRASH_MOVE_BPS, bool) or HEDGE_CRASH_MOVE_BPS < 0:
        errs.append("HEDGE_CRASH_MOVE_BPS must be >= 0")
    if not isinstance(HEDGE_CRASH_SPEED_WINDOW_SECONDS, (int, float)) or isinstance(HEDGE_CRASH_SPEED_WINDOW_SECONDS, bool) or HEDGE_CRASH_SPEED_WINDOW_SECONDS <= 0:
        errs.append("HEDGE_CRASH_SPEED_WINDOW_SECONDS must be > 0")
    if (not isinstance(HEDGE_POLICY_V32_ENABLED, bool)
            or not isinstance(HEDGE_GAMMA_AWARE_ENABLED, bool)
            or not isinstance(HEDGE_CRASH_ENABLED, bool)):
        errs.append("HEDGE_POLICY_V32_ENABLED/HEDGE_GAMMA_AWARE_ENABLED/HEDGE_CRASH_ENABLED must be bool")
    required_limits = (
        "max_open_positions",
        "max_short_gamma",
        "max_short_vega",
        "max_margin",
        "max_spread_loss_per_trade",
    )
    if not isinstance(PORTFOLIO_LIMITS, dict):
        errs.append("PORTFOLIO_LIMITS must be a dict")
    else:
        for key in required_limits:
            limit = PORTFOLIO_LIMITS.get(key)
            if not isinstance(limit, (int, float)) or isinstance(limit, bool) or limit < 0:
                errs.append("PORTFOLIO_LIMITS.%s must be a non-negative number" % key)
    if HEDGE_VENUE != "BINANCE":
        errs.append("Minimal V32 hedge supports BINANCE only")
    if ENTRY_MAX_ATTEMPTS < 1 or ENTRY_MAX_TICK_STEPS < 0:
        errs.append("ENTRY_MAX_ATTEMPTS>=1 and ENTRY_MAX_TICK_STEPS>=0")
    if ENTRY_PROTECTION_TAKER_AFTER_SECONDS < 1 or ENTRY_SHORT_ORDER_WAIT_SECONDS < 1:
        errs.append("ENTRY_PROTECTION_TAKER_AFTER_SECONDS and ENTRY_SHORT_ORDER_WAIT_SECONDS must be >=1")
    return errs

# ===================== module: manual_context =====================
# -*- coding: utf-8 -*-
"""Manual-gate context helpers."""
import hashlib
import json

SCHEMA_NAME = "ManualExecutionContext"
SCHEMA_VERSION = "nrd.execution.manual_context.v2"


def _hash(obj):
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()


def _pair(value, default=(0, 0)):
    try:
        a, b = value
        return a, b
    except Exception:
        return default


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def manual_context_hash(ctx):
    ctx = ctx or {}
    material = {
        "schema_name": ctx.get("schema_name"),
        "schema_version": ctx.get("schema_version"),
        "context_id": ctx.get("context_id"),
        "created_ts_ms": ctx.get("created_ts_ms"),
        "expires_ts_ms": ctx.get("expires_ts_ms"),
        "operator_decision": ctx.get("operator_decision"),
        "direction_bias": ctx.get("direction_bias"),
        "planning_scope": ctx.get("planning_scope") or {},
        "risk_policy": ctx.get("risk_policy") or {},
        "market_context": ctx.get("market_context") or {},
        "vrp_context_status": ctx.get("vrp_context_status"),
    }
    return _hash(material)


def manual_config_signature(planning_allowed, direction_bias, target_dte_hours,
                            delta_range, width_range, amount, approval_ttl_ms,
                            risk_policy=None):
    delta_min, delta_max = _pair(delta_range)
    width_min, width_max = _pair(width_range)
    return _hash({
        "planning_allowed": bool(planning_allowed),
        "direction_bias": direction_bias,
        "target_dte_hours": target_dte_hours,
        "short_delta": [delta_min, delta_max],
        "protection_width": [width_min, width_max],
        "amount": amount,
        "approval_ttl_ms": approval_ttl_ms,
        "risk_policy": risk_policy or {},
    })


def build_manual_context(now_ms, planning_allowed, direction_bias, target_dte_hours,
                         delta_range, width_range, amount, approval_ttl_ms,
                         risk_policy=None, market_context=None, vrp_context_status=None):
    delta_min, delta_max = _pair(delta_range)
    width_min, width_max = _pair(width_range)
    sig = manual_config_signature(
        planning_allowed, direction_bias, target_dte_hours, delta_range,
        width_range, amount, approval_ttl_ms, risk_policy)
    ttl_ms = int(approval_ttl_ms or 0) if _num(approval_ttl_ms) else 0
    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "context_id": "manual-%s" % sig[:12],
        "config_signature": sig,
        "created_ts_ms": now_ms,
        "expires_ts_ms": now_ms + ttl_ms,
        "operator_decision": "APPROVE_PLANNING" if planning_allowed else "WAIT_AUDIT_GATE",
        "direction_bias": direction_bias,
        "planning_scope": {
            "target_dte_hours": target_dte_hours,
            "short_delta_min": delta_min,
            "short_delta_max": delta_max,
            "protection_width_min": width_min,
            "protection_width_max": width_max,
            "amount": amount,
        },
        "risk_policy": risk_policy or {},
        "market_context": market_context or {},
        "vrp_context_status": vrp_context_status,
    }


def validate_manual_context(ctx, now_ms):
    errors = []
    ctx = ctx or {}
    scope = ctx.get("planning_scope") or {}
    if not ctx:
        errors.append("MANUAL_CONTEXT_MISSING")
    if ctx.get("operator_decision") != "APPROVE_PLANNING":
        errors.append("PLANNING_NOT_APPROVED")
    if ctx.get("direction_bias") not in ("SHORT_CALL", "SHORT_PUT"):
        errors.append("DIRECTION_BIAS_INVALID")
    if not (_num(scope.get("target_dte_hours")) and scope["target_dte_hours"] > 0):
        errors.append("TARGET_DTE_INVALID")
    if not (_num(scope.get("short_delta_min")) and _num(scope.get("short_delta_max"))
            and 0 < scope["short_delta_min"] < scope["short_delta_max"] < 1):
        errors.append("SHORT_DELTA_RANGE_INVALID")
    if not (_num(scope.get("protection_width_min")) and _num(scope.get("protection_width_max"))
            and scope["protection_width_min"] <= scope["protection_width_max"]):
        errors.append("PROTECTION_WIDTH_RANGE_INVALID")
    if not (_num(scope.get("amount")) and scope["amount"] > 0):
        errors.append("ORDER_AMOUNT_INVALID")
    exp = ctx.get("expires_ts_ms")
    if not _num(exp) or exp <= now_ms:
        errors.append("MANUAL_CONTEXT_EXPIRED")
    return {"valid": not errors, "errors": errors}

# ===================== module: gates =====================
# -*- coding: utf-8 -*-
"""执行授权门控（gate_*）：按动作拆分入口、退出和对冲权限，
避免「禁新开仓」误伤风险收口（退出 / 对冲减仓 / 孤儿清理）。纯函数，便于单测。

动作（action）：
  ENTRY         开立新垂直价差（**新增风险**）
  EXIT          买回卖方短腿 / 卖出保护腿（期权，**降风险**）
  HEDGE_OPEN    建立 / 增加 BTC-PERPETUAL 对冲（开 / 加仓；reduce_only 无法建仓，故非 reduce_only）
  HEDGE_REDUCE  对冲减仓 / 平仓（**强制 reduce_only**）

门控旗标（默认全安全）：
  allow_entry / allow_exit / allow_hedge   分动作总开关
  kill_new_risk         急停：停新风险并撤开仓单，但**不阻断**退出 / 对冲减仓 / 对账 / 孤儿清理
  emergency_reduce_only 紧急只减：**禁止任何开 / 加仓**，对冲强制 reduce_only

设计依据（补充意见 P0-3）：单一主门会在「禁新开仓」时连带关闭风险退出与对冲归零，
故必须拆分；急停只停新风险，恢复需重新对账并要求新的计划硬批准。
"""

ACTION_ENTRY = "ENTRY"
ACTION_EXIT = "EXIT"
ACTION_HEDGE_OPEN = "HEDGE_OPEN"
ACTION_HEDGE_REDUCE = "HEDGE_REDUCE"

ALL_ACTIONS = (ACTION_ENTRY, ACTION_EXIT, ACTION_HEDGE_OPEN, ACTION_HEDGE_REDUCE)


def _d(action, allowed, reduce_only, reason):
    return {"action": action, "allowed": bool(allowed),
            "reduce_only": bool(reduce_only), "reason": reason}


def gate_decision(action, allow_entry, allow_exit, allow_hedge,
                  kill_new_risk, emergency_reduce_only):
    """对单个动作给出门控裁决。

    返回 {"action", "allowed": bool, "reduce_only": bool, "reason": str}。
    `reduce_only` 仅对 HEDGE_* 有意义（HEDGE_REDUCE 恒 True）。
    """
    allow_entry = bool(allow_entry)
    allow_exit = bool(allow_exit)
    allow_hedge = bool(allow_hedge)
    kill = bool(kill_new_risk)
    emer = bool(emergency_reduce_only)

    if action == ACTION_ENTRY:
        if emer:
            return _d(action, False, False, "ENTRY_BLOCKED_EMERGENCY_REDUCE_ONLY")
        if kill:
            return _d(action, False, False, "ENTRY_BLOCKED_KILL_NEW_RISK")
        if not allow_entry:
            return _d(action, False, False, "ENTRY_GATE_OFF")
        return _d(action, True, False, "ENTRY_ALLOWED")

    if action == ACTION_EXIT:
        # 期权退出为降风险动作：kill / emergency 均不阻断，只由 allow_exit 控制
        if not allow_exit:
            return _d(action, False, False, "EXIT_GATE_OFF")
        return _d(action, True, False, "EXIT_ALLOWED")

    if action == ACTION_HEDGE_OPEN:
        # 紧急只减禁止开 / 加仓；但 kill_new_risk 不阻断对冲开（对冲压缩尾部 = 降险）
        if emer:
            return _d(action, False, False, "HEDGE_OPEN_BLOCKED_EMERGENCY_REDUCE_ONLY")
        if not allow_hedge:
            return _d(action, False, False, "HEDGE_GATE_OFF")
        return _d(action, True, False, "HEDGE_OPEN_ALLOWED")

    if action == ACTION_HEDGE_REDUCE:
        # 对冲减仓恒强制 reduce_only；kill / emergency 下仍允许（风险收口）
        if not allow_hedge:
            return _d(action, False, True, "HEDGE_GATE_OFF")
        return _d(action, True, True, "HEDGE_REDUCE_ALLOWED")

    return _d(action, False, False, "UNKNOWN_ACTION")


def gate_summary(allow_entry, allow_exit, allow_hedge,
                 kill_new_risk, emergency_reduce_only):
    """返回各动作裁决 dict，供面板「交互控制台」一眼看清当前可执行动作。"""
    return {a: gate_decision(a, allow_entry, allow_exit, allow_hedge,
                             kill_new_risk, emergency_reduce_only)
            for a in ALL_ACTIONS}

# ===================== module: cmd_router =====================
# -*- coding: utf-8 -*-
"""确认码命令路由 + 命令账本 + 幂等（cmd_*）。

把 FMZ `GetCommand()` 返回的 "名:参数" 解析、归一、去重并落审计账本。
唯一运行时交互入口是计划确认码：
  - `执行:<确认码>` / `EXECUTE:<确认码>`
  - 裸确认码（3-12 位字母数字）

注：FMZ `GetCommand()` 在回测系统不生效，须真实机器人空跑验收。
"""

# 中文按钮名 / 英文类型 → 规范类型
COMMAND_ALIASES = {
    "执行": "EXECUTE", "EXECUTE": "EXECUTE",
}

# 一次性消费型（触发方案锁定，不可重复）→ 严格幂等
CONSUME_TYPES = frozenset({"EXECUTE"})

_CMD_LEDGER_KEY = "spm_cmd_ledger_v1"
_CMD_LEDGER_MAX = 200


def parse_command(raw):
    """'名:参数' 或 '名' → {"raw","name","type","arg"}；空串 / None 返回 None。"""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    if ":" in s:
        name, arg = s.split(":", 1)
    else:
        name, arg = s, ""
    name = name.strip()
    ctype = COMMAND_ALIASES.get(name)
    if ctype is None and ":" not in s and 3 <= len(name) <= 12:
        if all(("0" <= ch <= "9") or ("A" <= ch.upper() <= "Z") for ch in name):
            ctype, arg = "EXECUTE", name
    return {"raw": s, "name": name,
            "type": ctype or "UNKNOWN", "arg": arg.strip()}


def is_consume(command):
    return bool(command) and command.get("type") in CONSUME_TYPES


def idempotency_key(robot_id, session_id, refresh_seq, command_type, nonce):
    """结构化幂等键：robot_id|session_id|refresh_seq|command_type|nonce。"""
    return "|".join(str(x) for x in
                    (robot_id, session_id, refresh_seq, command_type, nonce))


def _nonce_for(command):
    # 消费型用 arg（确认码）作 nonce → 一次性消费、码变即新命令
    return command.get("arg") or command.get("type")


# ---------- 命令账本（_G 持久化，跨重启可查）----------

def cmd_ledger_load():
    return list(_G(_CMD_LEDGER_KEY) or [])


def cmd_ledger_save(records):
    trimmed = records[-_CMD_LEDGER_MAX:]
    _G(_CMD_LEDGER_KEY, trimmed)
    return trimmed


def cmd_ledger_has_key(key):
    if not key:
        return False
    return any(r.get("key") == key for r in cmd_ledger_load())


def cmd_ledger_record(command, key, status, outcome, now_ts):
    recs = cmd_ledger_load()
    recs.append({"key": key, "type": (command or {}).get("type"),
                 "name": (command or {}).get("name"), "arg": (command or {}).get("arg"),
                 "status": status, "outcome": outcome, "ts": now_ts})
    return cmd_ledger_save(recs)


# ---------- 路由 ----------

def route_command(raw, ctx, now_ts):
    """解析 + 幂等判定。ctx={robot_id, session_id, refresh_seq}。
    返回 {"status", "command", "key"}；status ∈ EMPTY / UNKNOWN / DUPLICATE / ACCEPTED。
    ACCEPTED：调用方应处理该命令并在处理后调用 cmd_ledger_record 落账（消费型据此一次性消费）。"""
    cmd = parse_command(raw)
    if cmd is None:
        return {"status": "EMPTY", "command": None, "key": None}
    if cmd["type"] == "UNKNOWN":
        return {"status": "UNKNOWN", "command": cmd, "key": None}
    key = None
    if is_consume(cmd):
        key = idempotency_key(ctx.get("robot_id"), ctx.get("session_id"),
                              ctx.get("refresh_seq"), cmd["type"], _nonce_for(cmd))
        if cmd_ledger_has_key(key):
            return {"status": "DUPLICATE", "command": cmd, "key": key}
    return {"status": "ACCEPTED", "command": cmd, "key": key}

# ===================== module: recommend =====================
# -*- coding: utf-8 -*-
"""Recommendation library, approval snapshots, and precommit checks.

This manual-gate fork binds plan approval to a human-provided manual context
instead of manual package lineage. The functions stay pure so the small local
test runner can validate the approval contract without FMZ state.
"""
import base64
import hashlib
import json

QUALIFIED = "QUALIFIED"
RELIEF_BUCKET = 10
FEASIBILITY_BUCKET = 10
DEFAULT_CONFIG_HASH = "manual-gate-default-config-v1"


def _h(*parts):
    s = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _stable_json_hash(payload):
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _b32(hexstr, length):
    raw = base64.b32encode(bytes.fromhex(hexstr)).decode("ascii").rstrip("=")
    return raw[:length]


def _relief_bucket(ratio):
    if not isinstance(ratio, (int, float)):
        return "NA"
    return int(ratio * RELIEF_BUCKET)


def _feasibility_bucket(score):
    if not isinstance(score, (int, float)):
        return "NA"
    return int(max(0.0, min(100.0, score)) // FEASIBILITY_BUCKET)


def _range(scope, min_key, max_key, range_key=None):
    if range_key and range_key in scope:
        value = scope.get(range_key)
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            return [value[0], value[1]]
        return value
    return [scope.get(min_key), scope.get(max_key)]


def _manual_context_id(manual_context):
    return ((manual_context or {}).get("context_id")
            or (manual_context or {}).get("manual_context_id"))


def _config_hash(manual_context, config_hash=None):
    return (config_hash
            or (manual_context or {}).get("config_hash")
            or DEFAULT_CONFIG_HASH)


def manual_context_hash(ctx):
    """Hash only stable material manual-planning fields."""
    ctx = ctx or {}
    planning = ctx.get("planning_scope") or {}
    risk_policy = ctx.get("risk_policy") or {}
    if not isinstance(planning, dict):
        planning = {}
    if not isinstance(risk_policy, dict):
        risk_policy = {}
    material = {
        "context_id": _manual_context_id(ctx),
        "direction_bias": ctx.get("direction_bias"),
        "target_dte_hours": planning.get("target_dte_hours"),
        "delta_range": (_range(planning, "short_delta_min", "short_delta_max",
                               "short_delta_range")
                        if ("short_delta_min" in planning
                            or "short_delta_max" in planning
                            or "short_delta_range" in planning)
                        else _range(planning, "delta_min", "delta_max",
                                    "delta_range")),
        "protection_width_range": _range(planning, "protection_width_min",
                                          "protection_width_max",
                                          "protection_width_range"),
        "amount": planning.get("amount", ctx.get("amount")),
        "risk_policy": risk_policy,
        "expires_ts_ms": ctx.get("expires_ts_ms"),
        "market_context": ctx.get("market_context") or {},
        "vrp_context_status": ctx.get("vrp_context_status"),
    }
    return _stable_json_hash(material)


def side_of(short_instrument):
    s = str(short_instrument or "")
    if s.endswith("-C"):
        return "CALL"
    if s.endswith("-P"):
        return "PUT"
    return "UNK"


def strategy_code(side, expiry_label, short_strike, long_strike):
    return "VCS|%s|%s|%s|%s" % (side, expiry_label, short_strike, long_strike)


def quality_code(manual_ctx_hash, relief_ratio, vrp_state, budget_decision,
                 execution_feasibility_score=None, config_hash=None):
    """Frozen quality code bound to manual context and economic/safety buckets."""
    return _h(manual_ctx_hash, _relief_bucket(relief_ratio), vrp_state,
              budget_decision, _feasibility_bucket(execution_feasibility_score),
              "cfg:%s" % (config_hash or DEFAULT_CONFIG_HASH))[:8]


def plan_hash(strategy_code_str, quality_code_str, side,
              short_instrument, long_instrument, amount):
    return _h(strategy_code_str, quality_code_str, side,
              short_instrument, long_instrument, amount)[:16]


def confirm_code(session_id, strategy_code_str, quality_code_str, plan_hash_str, length=4):
    return _b32(_h(session_id, strategy_code_str, quality_code_str, plan_hash_str), length)


def build_approval_snapshot(candidate, session_id, manual_context, refresh_seq, now_ts,
                            config_hash=None):
    candidate = candidate or {}
    manual_context = manual_context or {}
    ctx_hash = manual_context_hash(manual_context)
    ctx_id = _manual_context_id(manual_context)
    cfg_hash = _config_hash(manual_context, config_hash)
    short_inst = candidate.get("short_instrument") or ""
    long_inst = candidate.get("protection_instrument") or ""
    side = side_of(short_inst)
    vrp_state = candidate.get("vrp_state") or candidate.get("vrp_gate")
    budget_decision = candidate.get("budget_decision")
    sc = strategy_code(side, candidate.get("short_expiry_label"),
                       candidate.get("short_strike"), candidate.get("protection_strike"))
    qc = quality_code(ctx_hash, candidate.get("margin_relief_ratio"),
                      vrp_state, budget_decision,
                      execution_feasibility_score=candidate.get("execution_feasibility_score"),
                      config_hash=cfg_hash)
    ph = plan_hash(sc, qc, side, short_inst, long_inst, candidate.get("amount"))
    approval_id = _h("approval", session_id, ctx_id, ctx_hash, ph, cfg_hash)[:16]
    cc = confirm_code(session_id, sc, qc, ph)
    return {
        "schema_name": "PlanApprovalSnapshot",
        "schema_version": "nrd.execution.plan_approval.v1",
        "approval_id": approval_id,
        "session_id": session_id,
        "manual_context_id": ctx_id,
        "manual_context_hash": ctx_hash,
        "direction_bias": manual_context.get("direction_bias"),
        "config_hash": cfg_hash,
        "refresh_seq": refresh_seq,
        "plan_id": candidate.get("id"),
        "side": side,
        "strategy_code": sc,
        "quality_code": qc,
        "plan_hash": ph,
        "confirm_code": cc,
        "recommendation_state": QUALIFIED if candidate.get("qualified", True) else "REJECTED",
        "short_instrument": short_inst,
        "long_instrument": long_inst,
        "short_strike": candidate.get("short_strike"),
        "long_strike": candidate.get("protection_strike"),
        "short_expiry": candidate.get("short_expiry"),
        "long_expiry": candidate.get("protection_expiry") or candidate.get("short_expiry"),
        "short_dte_hours": candidate.get("short_dte_hours"),
        "short_delta": candidate.get("short_delta"),
        "breakeven": candidate.get("breakeven"),
        "amount": candidate.get("amount"),
        "entry_net_credit_after_costs": candidate.get("net_credit_effective"),
        "max_loss": candidate.get("max_loss"),
        "margin_relief_ratio": candidate.get("margin_relief_ratio"),
        "execution_feasibility_grade": candidate.get("execution_feasibility_grade"),
        "execution_feasibility_score": candidate.get("execution_feasibility_score"),
        "execution_feasibility_score_norm": candidate.get("execution_feasibility_score_norm"),
        "execution_feasibility_warnings": candidate.get("execution_feasibility_warnings") or [],
        "frozen_ts": now_ts,
        "summary": "%s Δ%s 宽%s" % (side, candidate.get("short_delta"), candidate.get("width")),
    }


def ensure_unique_confirm_codes(snaps, session_id, max_len=8):
    length = 4
    while length <= max_len:
        seen = {}
        for s in snaps:
            cc = confirm_code(session_id, s["strategy_code"], s["quality_code"],
                              s["plan_hash"], length)
            seen.setdefault(cc, []).append(s)
        if all(len(v) == 1 for v in seen.values()):
            break
        length += 1
    length = min(length, max_len)
    for s in snaps:
        s["confirm_code"] = confirm_code(session_id, s["strategy_code"],
                                         s["quality_code"], s["plan_hash"], length)
    return snaps


def build_recommendation_library(menu, session_id, manual_context, refresh_seq, now_ts,
                                 config_hash=None):
    manual_context = manual_context or {}
    ctx_hash = manual_context_hash(manual_context)
    ctx_id = _manual_context_id(manual_context)
    cfg_hash = _config_hash(manual_context, config_hash)
    snaps = [build_approval_snapshot(c, session_id, manual_context, refresh_seq, now_ts,
                                     config_hash=cfg_hash)
             for c in (menu or [])]
    ensure_unique_confirm_codes(snaps, session_id)
    return {
        "schema_name": "VerticalRecommendationLibrary",
        "schema_version": "nrd.execution.recommendation_library.v1",
        "session_id": session_id,
        "manual_context_id": ctx_id,
        "manual_context_hash": ctx_hash,
        "direction_bias": manual_context.get("direction_bias"),
        "config_hash": cfg_hash,
        "refresh_seq": refresh_seq,
        "generated_ts": now_ts,
        "recommendations": snaps,
    }


def resolve_confirm_code(library, code):
    code = str(code or "").strip().upper()
    if not code:
        return None
    for s in (library or {}).get("recommendations", []):
        if str(s.get("confirm_code", "")).upper() == code:
            if s.get("recommendation_state") == QUALIFIED:
                return s
    return None


def precommit_recheck(locked_snapshot, current_library, live_checks):
    reasons = []
    match = next((s for s in (current_library or {}).get("recommendations", [])
                  if s.get("strategy_code") == locked_snapshot.get("strategy_code")
                  and s.get("recommendation_state") == QUALIFIED), None)
    if not match:
        reasons.append("STRATEGY_NO_LONGER_QUALIFIED_IN_LIBRARY")
    elif match.get("plan_hash") != locked_snapshot.get("plan_hash"):
        reasons.append("PLAN_HASH_DRIFTED_BEYOND_TOLERANCE")
    for k, ok in (live_checks or {}).items():
        if not ok:
            reasons.append("LIVE_CHECK_FAILED:" + str(k))
    return {"passed": not reasons, "reasons": reasons}


PRECOMMIT_CHECKS = (
    "manual_context_valid", "same_manual_context", "approval_not_expired",
    "locked_plan_hash_match", "locked_quality_code_match", "vertical_only",
    "vrp_rechecked", "spm_rechecked", "quotes_rechecked",
    "entry_net_credit_after_costs_positive", "projected_budget_passed",
    "ledger_reconciled", "no_unknown_orders", "spread_ok",
    "execution_feasibility_rechecked",
)


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def evaluate_precommit_checks(locked, current_library, live):
    locked = locked or {}
    live = live or {}
    match = next((s for s in (current_library or {}).get("recommendations", [])
                  if s.get("strategy_code") == locked.get("strategy_code")
                  and s.get("recommendation_state") == QUALIFIED), None)
    locked_ctx_hash = locked.get("manual_context_hash")
    live_ctx_hash = live.get("manual_context_hash")
    c = {
        "manual_context_valid": bool(live.get("manual_context_valid")),
        "same_manual_context": bool(locked_ctx_hash) and locked_ctx_hash == live_ctx_hash,
        "approval_not_expired": live.get("approval_not_expired") is True,
        "locked_plan_hash_match": bool(match) and match.get("plan_hash") == locked.get("plan_hash"),
        "locked_quality_code_match": bool(match) and match.get("quality_code") == locked.get("quality_code"),
        "vertical_only": locked.get("side") in ("CALL", "PUT") and bool(live.get("same_expiry")),
        "vrp_rechecked": live.get("vrp_pass") is True,
        "spm_rechecked": (_is_num(live.get("spm_relief")) and _is_num(live.get("min_relief"))
                          and live["spm_relief"] >= live["min_relief"]),
        "quotes_rechecked": bool(live.get("quotes_fresh")),
        "entry_net_credit_after_costs_positive": (_is_num(live.get("net_credit_after_costs"))
                                                  and live["net_credit_after_costs"] > 0),
        "projected_budget_passed": live.get("projected_budget_decision") == "ALLOW",
        "ledger_reconciled": bool(live.get("ledger_reconciled")),
        "no_unknown_orders": bool(live.get("no_unknown_orders")),
        "spread_ok": bool(live.get("spread_ok")),
        "execution_feasibility_rechecked": (
            (live.get("execution_feasibility_live") or {}).get("hard_gate_passed") is True),
    }
    failed = [k for k in PRECOMMIT_CHECKS if not c.get(k)]
    return {"checks": c, "passed": not failed, "failed": failed}

# ===================== module: position =====================
# -*- coding: utf-8 -*-
"""持仓生命周期：入场快照冻结 + 止盈预算锚（pos_*）。纯函数，便于单测。

设计稿 §2.2 / §8.3：入场成交后冻结 `entry_profit_ceiling_net` 为 80% 阈值的审计基准，
**入场后禁止重新计算或覆盖**。止盈预算由该冻结值反推：
    target_profit_amount = ceiling × take_profit_target_ratio (默认 0.80)
    max_total_exit_spend = ceiling − target_profit_amount      (= ceiling × 0.20)
保护腿回收价值默认按 0（不进入 80% 预算分母），见 E6。
"""

import math

DEFAULT_TAKE_PROFIT_RATIO = 0.80

# 退出活动状态
EXIT_IDLE = "IDLE"
EXIT_WAIT_TRIGGER = "WAIT_TRIGGER"
EXIT_WORKING_SHORT = "WORKING_SHORT"
EXIT_PAUSED_BUDGET = "PAUSED_BY_BUDGET"
EXIT_PAUSED_DATA = "PAUSED_BY_DATA"
EXIT_WORKING_LONG = "WORKING_LONG"
EXIT_LONG_RESIDUAL = "LONG_RESIDUAL_ONLY"
EXIT_COMPLETE = "COMPLETE"


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def entry_profit_ceiling_net(short_credit, long_debit, entry_fees):
    """入场利润上限（结算币）= 卖方实收 − 保护腿实付 − 入场手续费。任一缺失 → None。"""
    if short_credit is None or long_debit is None or entry_fees is None:
        return None
    return short_credit - long_debit - entry_fees


def build_vertical_entry_snapshot(locked, short_fill, long_fill, entry_fees,
                                  now_ts, take_profit_ratio=DEFAULT_TAKE_PROFIT_RATIO,
                                  entry_risk_anchor=None):
    """成交后冻结入场快照。short_fill/long_fill: {filled, avg_price}。
    `entry_profit_ceiling_net` 一经冻结即为审计基准，禁止后续覆盖（见 freeze_entry_ceiling）。
    `entry_risk_anchor`（hedge_risk.build_entry_risk_anchor）与 `short_expiry_ts` 一并冻结，
    供持仓后「风险严重度→仲裁」逐轮调用 evaluate_position_risk。"""
    locked = locked or {}
    sc = (short_fill or {}).get("avg_price")
    sa = (short_fill or {}).get("filled")
    lc = (long_fill or {}).get("avg_price")
    la = (long_fill or {}).get("filled")
    short_credit = (sc * sa) if (sc is not None and sa is not None) else None
    long_debit = (lc * la) if (lc is not None and la is not None) else None
    ceiling = entry_profit_ceiling_net(short_credit, long_debit, entry_fees)
    target_profit = (ceiling * take_profit_ratio) if ceiling is not None else None
    max_exit_spend = ((ceiling - target_profit)
                      if (ceiling is not None and target_profit is not None) else None)
    return {
        "schema_name": "VerticalEntrySnapshot",
        "position_id": "pos-%s" % now_ts,
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
        "short_strike": locked.get("short_strike"),
        "long_strike": locked.get("long_strike"),
        "breakeven": locked.get("breakeven"),
        "short_fill_amount": sa, "short_fill_price": sc,
        "long_fill_amount": la, "long_fill_price": lc,
        "entry_fees": entry_fees,
        "entry_profit_ceiling_net": ceiling,            # 不可覆盖（审计基准）
        "take_profit_target_ratio": take_profit_ratio,
        "target_profit_amount": target_profit,
        "max_total_exit_spend": max_exit_spend,
        "realized_exit_spend": 0.0,
        "remaining_short_qty": sa,
        "long_remaining_qty": la,          # 保护腿剩余（回收时递减；持仓真相之一）
        "short_expiry_ts": locked.get("short_expiry"),     # 短腿到期（持仓后 DTE/风险评估用）
        "long_expiry_ts": locked.get("long_expiry") or locked.get("short_expiry"),
        "entry_risk_anchor": entry_risk_anchor,            # 入场风险锚（风险严重度→仲裁）
        "hedge_trigger_policy": (entry_risk_anchor or {}).get("hedge_trigger_policy"),
        "frozen_ts": now_ts,
        "manual_lineage_only": True,
        "immutable": True,
    }


def freeze_entry_ceiling(existing_snapshot, recomputed_ceiling=None):
    """守卫：入场后永远返回已冻结的 entry_profit_ceiling_net，忽略任何重算值。
    返回 (frozen_value, tamper_detected)；recomputed 与冻结值不一致仅供审计标记，不改值。"""
    if not existing_snapshot:
        return None, False
    frozen = existing_snapshot.get("entry_profit_ceiling_net")
    tamper = (recomputed_ceiling is not None
              and frozen is not None
              and abs(float(recomputed_ceiling) - float(frozen)) > 1e-12)
    return frozen, tamper


# ---------- E6：止盈资格（资格与成交解耦，§2.3）----------

def reference_profit_capture_ratio(entry_ceiling, conservative_short_buyback_ref,
                                   estimated_short_exit_fee, exit_reserve):
    """止盈资格参考捕获率。保护腿价值**不进分母**（默认按 0）：
    reference_exit_spend = 保守短腿买回参考 + 短腿退出费 + 退出预留
    ratio = (entry_ceiling - reference_exit_spend) / entry_ceiling
    任一输入缺失或 ceiling<=0 → None（不触发自动止盈，标记数据缺口，仅监控）。"""
    if not _is_num(entry_ceiling) or entry_ceiling <= 0:
        return None
    parts = (conservative_short_buyback_ref, estimated_short_exit_fee, exit_reserve)
    if any(not _is_num(p) for p in parts):
        return None
    ref_spend = sum(parts)
    return (entry_ceiling - ref_spend) / entry_ceiling


def take_profit_qualified(reference_ratio, target_ratio=DEFAULT_TAKE_PROFIT_RATIO):
    """资格触发：参考捕获率 >= 目标(默认 0.80)。ratio None → 未达资格(数据缺口)。"""
    return _is_num(reference_ratio) and reference_ratio >= target_ratio


# ---------- E6：低成本退出硬预算 + 价格上限（§7.2 / §7.3）----------

def short_buyback_budget(max_total_exit_spend, realized_exit_spend, fee_reserve):
    """剩余短腿买回预算 = max_total_exit_spend − 已用 − 费用预留（不小于 0）。"""
    if not _is_num(max_total_exit_spend):
        return None
    return max(0.0, max_total_exit_spend - (realized_exit_spend or 0.0) - (fee_reserve or 0.0))


def short_buyback_price_cap(remaining_budget, fee_reserve, remaining_short_qty, tick):
    """每轮价格上限由剩余预算反推并向下取整到 tick：
    cap = floor_to_tick((remaining_budget − fee_reserve) / remaining_short_qty)。
    数量<=0 或预算不足 → 0（不下单）。"""
    if not (_is_num(remaining_budget) and _is_num(remaining_short_qty)) or remaining_short_qty <= 0:
        return 0.0
    avail = remaining_budget - (fee_reserve or 0.0)
    if avail <= 0:
        return 0.0
    raw = avail / remaining_short_qty
    if tick and tick > 0:
        return math.floor(raw / tick) * tick
    return raw


def within_exit_budget(order_price, order_amount, estimated_fee, remaining_budget):
    """订单是否在剩余预算内：price*amount + fee <= remaining_budget。"""
    if not all(_is_num(x) for x in (order_price, order_amount, estimated_fee, remaining_budget)):
        return False
    return order_price * order_amount + estimated_fee <= remaining_budget + 1e-12


def exit_campaign_decision(authorized, qualified, remaining_short_qty,
                           remaining_budget, quote_ok, price_cap):
    """退出活动下一状态/是否可下单（纯函数，不做 I/O；§7）。
    优先：短腿归零→转保护腿回收；未授权→IDLE；未达资格→WAIT_TRIGGER；
    无盘口→PAUSED_BY_DATA；预算/上限不足→PAUSED_BY_BUDGET；否则→WORKING_SHORT(可买回)。"""
    if remaining_short_qty is not None and remaining_short_qty <= 0:
        return {"state": EXIT_WORKING_LONG, "can_order": False, "reason": "SHORT_FLAT"}
    if not authorized:
        return {"state": EXIT_IDLE, "can_order": False, "reason": "UNAUTHORIZED"}
    if not qualified:
        return {"state": EXIT_WAIT_TRIGGER, "can_order": False, "reason": "NOT_QUALIFIED"}
    if not quote_ok:
        return {"state": EXIT_PAUSED_DATA, "can_order": False, "reason": "NO_RELIABLE_QUOTE"}
    if not price_cap or price_cap <= 0 or not _is_num(remaining_budget) or remaining_budget <= 0:
        return {"state": EXIT_PAUSED_BUDGET, "can_order": False, "reason": "BUDGET_EXHAUSTED"}
    return {"state": EXIT_WORKING_SHORT, "can_order": True, "reason": "BUYBACK_WITHIN_BUDGET"}


def protection_recovery_decision(short_flat, prot_qty, prot_bid):
    """短腿归零后保护腿回收决策（纯）：先平短腿；无 bid → LONG_RESIDUAL_ONLY 保持等结算。"""
    if not short_flat:
        return {"state": "HOLD_PROTECTION_UNTIL_SHORT_FLAT", "can_sell": False}
    if not prot_qty or prot_qty <= 0:
        return {"state": EXIT_COMPLETE, "can_sell": False}
    if not prot_bid or prot_bid <= 0:
        return {"state": EXIT_LONG_RESIDUAL, "can_sell": False}
    return {"state": EXIT_WORKING_LONG, "can_sell": True}


# ---------- G1：开仓活动（entry campaign）：跨轮持久 maker + 信用底线（低成本 ∧ 提高成功率）----------

ENTRY_IDLE = "ENTRY_IDLE"
ENTRY_WORKING = "ENTRY_WORKING"
ENTRY_PAUSED_DATA = "ENTRY_PAUSED_DATA"
ENTRY_PAUSED_CREDIT = "ENTRY_PAUSED_CREDIT"
ENTRY_ABANDONED = "ENTRY_ABANDONED"
ENTRY_COMPLETE = "ENTRY_COMPLETE"


def entry_net_credit(short_sell_price, prot_buy_price, amount, total_fees):
    """入场净 credit = (短腿卖价 − 保护腿买价)×数量 − 总手续费。任一缺失 → None。"""
    if not all(_is_num(x) for x in (short_sell_price, prot_buy_price, amount)):
        return None
    return (short_sell_price - prot_buy_price) * amount - (total_fees or 0.0)


def entry_credit_capped_index(prot_buy_prices, short_sell_prices, amount, total_fees, credit_floor):
    """在「逐 tick 改善」价格阶梯中返回净 credit ≥ floor 的**最激进**档 index；无则 -1。
    约定：prot_buy_prices 升序(越激进越高)、short_sell_prices 降序(越激进越低) → 净credit 随 index 递减。
    这是低成本与成功率的结合点：可向触价改善以提高成交率，但永不突破信用底线。"""
    best = -1
    n = min(len(prot_buy_prices or []), len(short_sell_prices or []))
    for i in range(n):
        nc = entry_net_credit(short_sell_prices[i], prot_buy_prices[i], amount, total_fees)
        if nc is not None and nc >= credit_floor:
            best = i
    return best


def entry_campaign_decision(has_locked, quotes_ok, credit_ok, attempts, max_attempts,
                            prot_done, short_done):
    """开仓活动下一状态 / 是否可下单（纯）。
    max_attempts 只保留为软计数提示，不代表清锁/放弃；保护腿兜底由订单等待时间触发。"""
    if not has_locked:
        return {"state": ENTRY_IDLE, "can_order": False, "reason": "NO_LOCKED_PLAN"}
    if prot_done and short_done:
        return {"state": ENTRY_COMPLETE, "can_order": False, "reason": "FILLED"}
    if not quotes_ok:
        return {"state": ENTRY_PAUSED_DATA, "can_order": False, "reason": "NO_RELIABLE_QUOTE"}
    if not credit_ok:
        return {"state": ENTRY_PAUSED_CREDIT, "can_order": False, "reason": "BELOW_CREDIT_FLOOR_WAIT"}
    if attempts >= max_attempts:
        return {"state": ENTRY_WORKING, "can_order": True, "reason": "SOFT_ATTEMPT_LIMIT_KEEP_LOCKED"}
    return {"state": ENTRY_WORKING, "can_order": True, "reason": "POST_WITHIN_CREDIT_FLOOR"}


# ---------- P0①：持仓对账（快照为唯一持仓真相 vs 交易所真实期权持仓）----------

def position_reconcile(snap, option_positions):
    """以入场快照（短腿剩余 / 保护腿剩余）为期望，与交易所真实期权持仓比对。
    返回 {reconciled, reasons}。无快照(无持仓)+交易所也无我方合约 → reconciled=True。"""
    actual = {}
    for p in (option_positions or []):
        inst, sz = p.get("instrument_name"), p.get("size")
        if inst and sz:
            actual[inst] = sz
    expected = {}
    if snap:
        si, li = snap.get("short_instrument"), snap.get("long_instrument")
        rs = snap.get("remaining_short_qty") or 0.0
        lr = snap.get("long_remaining_qty")
        if lr is None:
            lr = snap.get("long_fill_amount") or 0.0
        if si and rs > 1e-12:
            expected[si] = -rs                       # 卖方腿 = 负持仓
        if li and lr > 1e-12:
            expected[li] = lr                        # 保护腿 = 正持仓
    reasons = []
    for inst, sz in expected.items():
        a = actual.get(inst)
        if a is None or abs(a - sz) > 1e-9:
            reasons.append("MISMATCH:%s exp=%s act=%s" % (inst, sz, a))
    for inst, sz in actual.items():                  # 交易所有、快照未含 → 不可解释
        if inst not in expected:
            reasons.append("UNEXPECTED:%s=%s" % (inst, sz))
    return {"reconciled": not reasons, "reasons": reasons}

# ===================== module: deribit_io =====================
# -*- coding: utf-8 -*-
"""
Deribit IO 适配层（dbt_*）。

统一经 FMZ 的 exchange.IO("api", method, path, query) 调 Deribit 原生 REST。
FMZ 已配置好 Deribit 交易所对象与 API key，私有请求由 FMZ 自动签名，本层不处理鉴权。
若个别端点连 IO 也不通，可在此层改为手动签名 REST 兜底（v1 默认走 IO）。

返回值统一抽取 Deribit JSON-RPC 的 result 字段；error 时 Log 并返回 None。
"""

import json

try:
    from urllib.parse import urlencode  # py3
except ImportError:  # pragma: no cover
    from urllib import urlencode        # py2 (FMZ 部分环境)


DERIBIT_API_PREFIX = "/api/v2"


def _build_query(params):
    """dict -> querystring，对 JSON 值（如 simulated_positions）安全编码。"""
    flat = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, bool):
            flat[k] = "true" if v else "false"
        elif isinstance(v, (dict, list)):
            flat[k] = json.dumps(v, separators=(",", ":"))
        else:
            flat[k] = v
    return urlencode(flat)


def _result(resp, ctx=""):
    """从 IO 返回值中抽取 result；兼容 FMZ 已解包/未解包两种形态。"""
    if resp is None:
        Log("[dbt] IO 返回 None:", ctx)
        return None
    if isinstance(resp, dict):
        if "error" in resp and resp["error"]:
            Log("[dbt] Deribit error:", ctx, json.dumps(resp["error"]))
            return None
        if "result" in resp:
            return resp["result"]
    return resp


def _call(method, path, params=None, ctx="", retries=0):
    """retries>0 时对返回 None（网络/瞬时错误）做有限重试；写操作请用 retries=0。"""
    query = _build_query(params or {})
    attempt = 0
    while True:
        resp = exchange.IO("api", method, DERIBIT_API_PREFIX + path, query)
        out = _result(resp, ctx or path)
        if out is not None or attempt >= retries:
            return out
        attempt += 1


_READ_RETRIES = 2


# ---------- 公开行情 / 合约 ----------

def dbt_get_instruments(currency, kind="option", expired=False):
    return _call("GET", "/public/get_instruments",
                 {"currency": currency, "kind": kind, "expired": expired},
                 "get_instruments", _READ_RETRIES) or []


def dbt_get_instrument(instrument_name):
    """单合约元数据（含 tick_size / tick_size_steps / contract_size / min_trade_amount）。"""
    return _call("GET", "/public/get_instrument",
                 {"instrument_name": instrument_name}, "get_instrument", _READ_RETRIES)


def dbt_ticker(instrument_name):
    """含 best_bid_price / best_ask_price / mark_price / underlying_price / greeks。"""
    return _call("GET", "/public/ticker",
                 {"instrument_name": instrument_name}, "ticker", _READ_RETRIES)


def dbt_order_book(instrument_name, depth=1):
    return _call("GET", "/public/get_order_book",
                 {"instrument_name": instrument_name, "depth": depth}, "order_book", _READ_RETRIES)


def dbt_index_price(currency):
    """结算币对 USD 指数价（费用 USD 展示用）。"""
    index_name = (currency + "_usd").lower()
    r = _call("GET", "/public/get_index_price", {"index_name": index_name},
              "index_price", _READ_RETRIES)
    return (r or {}).get("index_price")


# ---------- 私有账户 / 持仓 ----------

def dbt_account_summary(currency, extended=True):
    """含 margin_model / portfolio_margining_enabled / initial_margin / maintenance_margin。"""
    return _call("GET", "/private/get_account_summary",
                 {"currency": currency, "extended": extended}, "account_summary", _READ_RETRIES)


def dbt_get_positions(currency, kind="option"):
    return dbt_get_positions_strict(currency, kind) or []


def dbt_get_positions_strict(currency, kind="option"):
    """Return a list on a successful read; return None on transport/API failure."""
    return _call("GET", "/private/get_positions",
                 {"currency": currency, "kind": kind}, "get_positions", _READ_RETRIES)


def dbt_simulate_portfolio(currency, simulated_positions, add_positions=True):
    """S:PM 模拟。simulated_positions: {instrument_name: size}（负数=short）。
    返回含 initial_margin / maintenance_margin / available_funds / margin_model。"""
    return _call("GET", "/private/simulate_portfolio",
                 {"currency": currency,
                  "add_positions": add_positions,
                  "simulated_positions": simulated_positions},
                 "simulate_portfolio", _READ_RETRIES)


# ---------- 私有交易 ----------

def dbt_place_order(side, instrument_name, amount, price,
                    post_only=True, reject_post_only=True, label=None, reduce_only=False):
    """限价单。side: 'buy'/'sell'。reduce_only=True 用于对冲减仓/平仓（不可建仓）。
    返回 result（含 order 字段）或 None。"""
    path = "/private/buy" if side == "buy" else "/private/sell"
    params = {
        "instrument_name": instrument_name,
        "amount": amount,
        "type": "limit",
        "price": price,
        "post_only": post_only,
        "reject_post_only": reject_post_only,
    }
    if reduce_only:
        params["reduce_only"] = True
    if label:
        params["label"] = label
    return _call("GET", path, params, "place_order:" + side)


def dbt_get_open_orders(currency, kind=None):
    """当前未成交挂单（按币种；kind 可选 option/future）。
    供预提交 no_unknown_orders 与启动恢复的「未知活动订单」检测。
    **读失败返回 None**（区别于"确实无挂单"的 []），便于调用方对查询失败 fail-closed。"""
    params = {"currency": currency}
    if kind:
        params["kind"] = kind
    return _call("GET", "/private/get_open_orders_by_currency", params,
                 "open_orders", _READ_RETRIES)


def dbt_get_order_state(order_id):
    return _call("GET", "/private/get_order_state", {"order_id": order_id}, "order_state")


def dbt_cancel(order_id):
    return _call("GET", "/private/cancel", {"order_id": order_id}, "cancel")

# ===================== module: binance_io =====================
# -*- coding: utf-8 -*-
"""币安 USDC 永续对冲适配（bnc_*）：经 FMZ exchanges[idx] 下对冲腿。

线性合约(单位 BTC)；风险触发对冲使用 prompt-limit，reduce_only 用平仓方向。
仅对冲腿用，不参与期权 / 人工审计。FMZ 多所：exchanges[0]=Deribit(期权)，exchanges[idx]=Binance。

注：真实下单调用形态依 FMZ 币安期货接口（SetContractType/SetDirection/Buy/Sell），**须真实机器人确认**；
默认 `ALLOW_HEDGE_TRADING=False`；跨所对账/恢复需人工核对。
"""
import math


_BINANCE_PERP_CONTRACT_TYPE = "swap"


def _ex(idx):
    try:
        return exchanges[HEDGE_BINANCE_EXCHANGE_INDEX if idx is None else idx]
    except Exception:
        return None


def _binance_pair(symbol):
    raw = str(symbol or "BTCUSDC").strip().upper()
    if "." in raw:
        raw = raw.split(".", 1)[0]
    raw = raw.replace("-", "_").replace("/", "_")
    if "_" in raw:
        parts = [p for p in raw.split("_") if p]
        if len(parts) >= 2:
            return "%s_%s" % (parts[0], parts[1])
    for quote in ("USDC", "USDT", "USD"):
        if raw.endswith(quote) and len(raw) > len(quote):
            return "%s_%s" % (raw[:-len(quote)], quote)
    return raw


def _select_binance_perp(ex, symbol):
    pair = _binance_pair(symbol)
    io = getattr(ex, "IO", None)
    if callable(io):
        io("currency", pair)
    ex.SetContractType(_BINANCE_PERP_CONTRACT_TYPE)
    return pair, _BINANCE_PERP_CONTRACT_TYPE


def _num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _position_unrealized_pnl(position):
    if not isinstance(position, dict):
        return None
    for key in ("Profit", "UnrealizedProfit", "unRealizedProfit",
                "unrealizedProfit", "unrealizedPnl", "unrealized_pnl_usd"):
        v = _num(position.get(key))
        if v is not None:
            return float(v)
    return None


def bnc_get_position_snapshot(symbol, idx=None):
    """读 BTCUSDC 永续快照；读失败 → None。qty 正=多 / 负=空。"""
    ex = _ex(idx)
    if ex is None:
        return None
    try:
        pair, contract_type = _select_binance_perp(ex, symbol)
        net = 0.0
        pnl = 0.0
        pnl_seen = False
        raw_positions = ex.GetPosition()
        if raw_positions is None:
            Log("[binance] GetPosition 返回 None，按数据缺口处理")
            return None
        positions = list(raw_positions or [])
        for p in positions:
            amt = p.get("Amount") or 0.0
            long_side = p.get("Type") in (0, "buy", "long", "Long")
            net += amt if long_side else -amt
            pp = _position_unrealized_pnl(p)
            if pp is not None:
                pnl += pp
                pnl_seen = True
        return {"qty": net, "unrealized_pnl_usd": pnl if pnl_seen else None,
                "positions": positions, "pair": pair, "contract_type": contract_type}
    except Exception as e:
        Log("[binance] GetPosition 异常:", str(e))
        return None


def bnc_get_position_btc(symbol, idx=None):
    """读 BTCUSDC 永续净持仓(BTC；正=多 / 负=空)。读失败 → None。"""
    snap = bnc_get_position_snapshot(symbol, idx)
    return None if snap is None else snap.get("qty")


def _order_id(resp):
    if isinstance(resp, dict):
        return resp.get("id") or resp.get("Id") or resp.get("order_id") or resp.get("OrderId")
    return resp


def _filled_amount(order):
    if not isinstance(order, dict):
        return 0.0
    for k in ("DealAmount", "deal_amount", "filled_amount", "filled", "Filled"):
        v = order.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return float(v)
    return 0.0


def _avg_price(order, fallback):
    if not isinstance(order, dict):
        return fallback
    for k in ("AvgPrice", "avg_price", "average_price", "Price", "price"):
        v = order.get(k)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            return float(v)
    return fallback


def _prompt_limit_price(ticker, side, max_slippage_bps):
    bid = ticker.get("Buy") or ticker.get("best_bid") or ticker.get("Bid")
    ask = ticker.get("Sell") or ticker.get("best_ask") or ticker.get("Ask")
    bps = (max_slippage_bps or 0) / 10000.0
    if side == "buy":
        return None if not ask or ask <= 0 else ask * (1.0 + bps)
    return None if not bid or bid <= 0 else bid * (1.0 - bps)


def _tick_decimals(tick):
    s = ("%.12f" % tick).rstrip("0").rstrip(".")
    return len(s.split(".", 1)[1]) if "." in s else 0


def _round_prompt_price(price, side, tick=None):
    tick = HEDGE_BINANCE_PRICE_TICK if tick is None else tick
    if not tick or tick <= 0:
        return price
    if side == "buy":
        rounded = math.ceil((price / tick) - 1e-12) * tick
    else:
        rounded = math.floor((price / tick) + 1e-12) * tick
    return round(rounded, _tick_decimals(tick))


def _get_order(ex, oid):
    fn = getattr(ex, "GetOrder", None)
    if not fn or oid is None:
        return None
    return fn(oid)


def _cancel_order(ex, oid):
    fn = getattr(ex, "CancelOrder", None)
    if not fn or oid is None:
        return False
    return bool(fn(oid))


def bnc_get_hedge_order(symbol, order_id, idx=None):
    ex = _ex(idx)
    if ex is None or order_id is None:
        return None
    try:
        if callable(getattr(ex, "SetContractType", None)):
            _select_binance_perp(ex, symbol)
        return _get_order(ex, order_id)
    except Exception as e:
        Log("[binance] GetOrder 异常:", str(e))
        return None


def bnc_cancel_hedge_order(symbol, order_id, idx=None):
    ex = _ex(idx)
    if ex is None or order_id is None:
        return False
    try:
        if callable(getattr(ex, "SetContractType", None)):
            _select_binance_perp(ex, symbol)
        return _cancel_order(ex, order_id)
    except Exception as e:
        Log("[binance] CancelOrder 异常:", str(e))
        return False


def _missing_methods(ex, names):
    return [name for name in names if not callable(getattr(ex, name, None))]


def bnc_order_lifecycle_supported(symbol, idx=None):
    ex = _ex(idx)
    if ex is None:
        return {"ok": False, "reason": "BINANCE_EXCHANGE_UNAVAILABLE",
                "missing_methods": ["exchange"]}
    missing = _missing_methods(
        ex, ("SetContractType", "GetTicker", "SetDirection", "Buy", "Sell",
             "GetOrder", "CancelOrder"))
    return {"ok": not missing,
            "reason": None if not missing else "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED",
            "missing_methods": missing,
            "symbol": symbol}


def bnc_submit_hedge_order(symbol, side, amount, reduce_only, cross_bps=5,
                           allow_live=True, idx=None,
                           execution_style="PROMPT_LIMIT"):
    """Submit one Binance hedge order and leave lifecycle resolution to caller."""
    if not side or not amount or amount <= 0:
        return {"order_id": None, "filled": 0.0, "dry": (not allow_live),
                "venue": "BINANCE", "reason": "NO_OP"}
    if not allow_live:
        return {"order_id": None, "filled": 0.0, "dry": True, "venue": "BINANCE",
                "symbol": symbol, "side": side, "amount": amount,
                "reduce_only": reduce_only, "post_only": False,
                "execution_style": execution_style,
                "cross_bps": cross_bps, "reason": "BINANCE_HEDGE_DRYRUN"}
    ex = _ex(idx)
    if ex is None:
        return {"order_id": None, "filled": 0.0, "dry": False, "venue": "BINANCE",
                "reason": "BINANCE_EXCHANGE_UNAVAILABLE"}
    missing = _missing_methods(
        ex, ("SetContractType", "GetTicker", "SetDirection", "Buy", "Sell",
             "GetOrder", "CancelOrder"))
    if missing:
        return {"order_id": None, "filled": 0.0, "dry": False, "venue": "BINANCE",
                "reason": "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED",
                "blocked": True, "missing_methods": missing}
    try:
        pair, contract_type = _select_binance_perp(ex, symbol)
        t = ex.GetTicker() or {}
        raw_price = _prompt_limit_price(t, side, cross_bps)
        if raw_price is None or raw_price <= 0:
            return {"order_id": None, "filled": 0.0, "dry": False, "venue": "BINANCE",
                    "reduce_only": reduce_only, "post_only": False,
                    "execution_style": execution_style, "reason": "NO_QUOTE"}
        price = _round_prompt_price(raw_price, side, HEDGE_BINANCE_PRICE_TICK)
        direction = ("closesell" if side == "buy" else "closebuy") if reduce_only else side
        ex.SetDirection(direction)
        resp = ex.Buy(price, amount) if side == "buy" else ex.Sell(price, amount)
        oid = _order_id(resp)
        if oid is None:
            return {"order_id": None, "filled": 0.0, "dry": False, "venue": "BINANCE",
                    "symbol": symbol, "side": side, "amount": amount, "price": price,
                    "raw_price": raw_price, "price_tick": HEDGE_BINANCE_PRICE_TICK,
                    "order": resp, "reduce_only": reduce_only, "post_only": False,
                    "execution_style": execution_style, "cross_bps": cross_bps,
                    "pair": pair, "contract_type": contract_type,
                    "reason": "BINANCE_ORDER_ID_MISSING", "blocked": True}
        return {"order_id": oid, "filled": 0.0, "dry": False, "venue": "BINANCE",
                "symbol": symbol, "side": side, "amount": amount, "price": price,
                "raw_price": raw_price, "price_tick": HEDGE_BINANCE_PRICE_TICK,
                "order": resp, "reduce_only": reduce_only, "post_only": False,
                "execution_style": execution_style, "cross_bps": cross_bps,
                "pair": pair, "contract_type": contract_type,
                "reason": "BINANCE_HEDGE_SUBMITTED"}
    except Exception as e:
        Log("[binance] 下单异常:", str(e))
        return {"order_id": None, "filled": 0.0, "dry": False, "venue": "BINANCE",
                "reason": "BINANCE_ORDER_ERROR"}

# ===================== module: leg_selection =====================
# -*- coding: utf-8 -*-
"""
选腿（legsel_*）：把方向 + DTE/Delta 范围映射为具体的「行权价 / 到期 / 合约」。

本模块为纯逻辑：输入交易所返回的合约列表与盘口，输出选腿结果，便于本地单测。
到期一律用合约自带的 expiration_timestamp，不靠解析合约名。
"""


def legsel_is_call_bias(direction_bias):
    return direction_bias == "SHORT_CALL"


def legsel_dte_hours(expiration_timestamp_ms, now_ms):
    return (expiration_timestamp_ms - now_ms) / 3600000.0


def _opt_type_match(inst, want_call):
    t = (inst.get("option_type") or "").lower()
    return (t == "call") if want_call else (t == "put")


def legsel_pick_expiry_instruments(instruments, dte_min_h, dte_max_h, center_h,
                                   now_ms, want_call):
    """选 DTE 落在 [dte_min_h, dte_max_h] 内、最接近 center_h 的**实际可用到期**，
    返回 (chosen_exp_ms, [该到期且方向匹配的合约])；无可用到期返回 (None, [])。"""
    by_exp = {}
    for inst in instruments:
        if not _opt_type_match(inst, want_call):
            continue
        exp = inst.get("expiration_timestamp")
        if exp is None:
            continue
        dte = legsel_dte_hours(exp, now_ms)
        if dte_min_h <= dte <= dte_max_h:
            by_exp.setdefault(exp, []).append(inst)
    if not by_exp:
        return None, []
    chosen = min(by_exp.keys(),
                 key=lambda e: abs(legsel_dte_hours(e, now_ms) - center_h))
    return chosen, by_exp[chosen]


def legsel_expiries_in_band(instruments, dte_min_h, dte_max_h, now_ms, want_call):
    """返回 {expiration_timestamp: [该到期且方向匹配的合约]}，覆盖 DTE 区间内的**所有**到期。"""
    by_exp = {}
    for inst in instruments:
        if not _opt_type_match(inst, want_call):
            continue
        exp = inst.get("expiration_timestamp")
        if exp is None:
            continue
        if dte_min_h <= legsel_dte_hours(exp, now_ms) <= dte_max_h:
            by_exp.setdefault(exp, []).append(inst)
    return by_exp


def legsel_target_expiries(instruments, target_dte_h, now_ms, want_call, max_expiries=2):
    """Return {expiry_ts: instruments} for nearest target DTE plus next later expiry."""
    by_exp = {}
    for inst in instruments:
        if not _opt_type_match(inst, want_call):
            continue
        exp = inst.get("expiration_timestamp")
        if exp is None:
            continue
        if legsel_dte_hours(exp, now_ms) <= 0:
            continue
        by_exp.setdefault(exp, []).append(inst)
    if not by_exp:
        return {}
    ordered = sorted(by_exp)
    nearest = min(ordered, key=lambda e: abs(legsel_dte_hours(e, now_ms) - target_dte_h))
    chosen = [nearest]
    for exp in ordered:
        if exp > nearest:
            chosen.append(exp)
            break
    return {exp: by_exp[exp] for exp in chosen[:max_expiries]}


def _otm_side_ok(strike, spot, want_call):
    """call 卖在现价上方、put 卖在现价下方（OTM 侧）。"""
    return strike > spot if want_call else strike < spot


def legsel_short_enriched(short_insts, spot, want_call, delta_of, scan_limit=15):
    """OTM 侧、距现价由近到远取前 scan_limit 档，并附 _delta（供按目标 delta 选档）。"""
    otm = [i for i in short_insts
           if i.get("strike") is not None and _otm_side_ok(i["strike"], spot, want_call)]
    otm.sort(key=lambda i: abs(i["strike"] - spot))
    enriched = []
    for i in otm[:scan_limit]:
        d = delta_of(i.get("instrument_name"))
        if d is None:
            continue
        j = dict(i)
        j["_delta"] = d
        enriched.append(j)
    return enriched


def legsel_pick_nearest_delta(enriched, target_delta):
    """在 enriched 短腿候选中选 |delta| 最接近 target_delta 的档（卖权利金主驱动）。
    返回选中合约(含 _delta) 或 None。"""
    if not enriched:
        return None
    return min(enriched, key=lambda i: abs(abs(i["_delta"]) - target_delta))


def legsel_protection_candidates(prot_insts, short_strike, want_call, width_band,
                                 delta_of=None, deep_otm_max_delta=0.05):
    """保护腿候选（以短腿行权价为基准、按腿宽选择）：
      - call: strike > short_strike；put: strike < short_strike（更外侧）
      - 腿宽 = |strike - short_strike| 优先落在 width_band；排除过度虚值(|delta|<deep_otm)
      - 排序：腿宽最接近区间中心者优先；带外档作兜底排后
        （供 spm_evaluate_candidates 逐个验证保证金释放，取首个达标）。
    返回有序候选合约列表（每项含 _width）。"""
    wlo, whi = width_band
    wcenter = (wlo + whi) / 2.0
    in_band, others = [], []
    for i in prot_insts:
        s = i.get("strike")
        if s is None:
            continue
        outside = (s > short_strike) if want_call else (s < short_strike)
        if not outside:
            continue
        if delta_of is not None:
            d = delta_of(i.get("instrument_name"))
            if d is not None and abs(d) < deep_otm_max_delta:
                continue  # 过度虚值的灾难彩票腿
        rec = dict(i)
        rec["_width"] = abs(s - short_strike)
        (in_band if wlo <= rec["_width"] <= whi else others).append(rec)

    in_band.sort(key=lambda rec: abs(rec["_width"] - wcenter))
    others.sort(key=lambda rec: abs(rec["_width"] - wcenter))
    return in_band + others

# ===================== module: accounting =====================
# -*- coding: utf-8 -*-
"""
损耗记账（acct_*，§11）+ 全量信息报告（§13）。

口径统一以**结算币（BTC/ETH）**计价；期权权利金/mark 在 Deribit 即以标的币报价。
USD 仅用 index_price 换算展示。全部为纯函数，便于单测。
"""

OPTION_FEE_CAP_CCY = 0.0003   # 每张封顶（BTC/ETH 同值，结算币计）
OPTION_FEE_RATE    = 0.125    # 权利金比例上限 12.5%


# ---------- A. 显性交易费（§1.2）----------

def acct_option_fee_ccy(option_price_ccy, amount):
    """结算币计：MIN(0.0003, 0.125*option_price) * amount。"""
    per = min(OPTION_FEE_CAP_CCY, OPTION_FEE_RATE * option_price_ccy)
    return per * amount


def acct_option_fee_usd(option_price_ccy, amount, index_price):
    """USD 展示：MIN(0.0003*index, 0.125*option_price_usd) * amount。"""
    option_price_usd = option_price_ccy * index_price
    per = min(OPTION_FEE_CAP_CCY * index_price, OPTION_FEE_RATE * option_price_usd)
    return per * amount


# ---------- B. mark 偏离 ----------

def acct_mark_slippage(side, fill_price, mark_price, amount):
    """成交价相对 mark 的不利偏离（正=不利）。"""
    if side == "buy":
        return (fill_price - mark_price) * amount
    return (mark_price - fill_price) * amount


# ---------- C. 一步追价损耗 ----------

def acct_chase_cost(side, price0, final_price, amount):
    """相对初始挂价 price0 的追价损耗（正=不利）。"""
    if side == "buy":
        return (final_price - price0) * amount
    return (price0 - final_price) * amount


# ---------- D. bid/ask 价差损耗（参考：半价差）----------

def acct_spread_cost(best_bid, best_ask, amount):
    if best_bid is None or best_ask is None:
        return None
    return (best_ask - best_bid) / 2.0 * amount


# ---------- 远期保护腿真实成本（§11.2）----------

def acct_protection_realized_cost(entry_price, entry_fee, exit_fee=0.0,
                                  spread_slippage=0.0, exit_value=0.0):
    return entry_price + entry_fee + exit_fee + spread_slippage - exit_value


def acct_protection_cost_per_day(realized_cost, protected_days):
    if not protected_days:
        return None
    return realized_cost / protected_days


def acct_protection_cost_per_short_cycle(realized_cost, covered_cycle_count):
    if not covered_cycle_count:
        return None
    return realized_cost / covered_cycle_count


# ---------- F. full-burn 压力测试（§11.3，仅压测口径，不作默认真实成本）----------

def acct_full_burn(entry_price, entry_fee):
    return entry_price + entry_fee


# ---------- §13 全量报告 ----------

def acct_build_report(ctx):
    """组装设计稿 §13 结构 + 选腿/执行/记账明细，作为每次进场前的核对载体。
    ctx 为已采集字段的 dict；缺失字段以 None 占位。"""
    g = ctx.get
    return {
        "structure_type": "VERTICAL_CREDIT_SPREAD",
        "account_margin_mode": "S:PM",
        "settlement_currency": g("currency"),
        "manual_gate_state": g("manual_gate_state"),
        "direction_bias": g("direction_bias"),
        "allow_trading": g("allow_trading"),
        "state": g("state"),
        "short_leg": {
            "instrument": g("short_instrument"),
            "strike": g("short_strike"),
            "dte_hours": g("short_dte_hours"),
            "side": "SELL",
            "role": "NEAR_TERM_SHORT_PREMIUM",
            "mark": g("short_mark"),
            "best_bid": g("short_bid"),
            "best_ask": g("short_ask"),
            "tick_size": g("short_tick"),
        },
        "protection_leg": {
            "instrument": g("protection_instrument"),
            "strike": g("protection_strike"),
            "dte_days": g("protection_dte_days"),
            "side": "BUY",
            "role": "FAR_TERM_ECONOMIC_PROTECTION",
            "is_inventory_reuse": g("is_inventory_reuse") or False,
            "delta": g("protection_delta"),
            "mark": g("protection_mark"),
            "best_bid": g("protection_bid"),
            "best_ask": g("protection_ask"),
            "tick_size": g("protection_tick"),
        },
        "spm_report": {
            "im_short_only": g("im_short_only"),
            "im_with_protection": g("im_with_protection"),
            "margin_relief_abs": g("margin_relief_abs"),
            "margin_relief_ratio": g("margin_relief_ratio"),
            "min_required_ratio": g("min_required_ratio"),
            "pm_accepted": g("pm_accepted"),
            "account_margin_model": g("account_margin_model"),
        },
        "cost_report": {
            "estimated_entry_fee": g("estimated_entry_fee"),
            "estimated_mark_slippage": g("estimated_mark_slippage"),
            "estimated_chase_slippage": g("estimated_chase_slippage"),
            "estimated_spread_cost": g("estimated_spread_cost"),
            "short_premium_income": g("short_premium_income"),
            "full_burn_cost": g("full_burn_cost"),
            "protection_cost_per_day": g("protection_cost_per_day"),
            "protection_cost_per_short_cycle": g("protection_cost_per_short_cycle"),
            "expected_recoverable_value": g("expected_recoverable_value"),
            "cost_basis_note_cn": "保护腿真实成本按退出残值与覆盖周期摊销，不按买入价一次性计入；full_burn 仅压测。",
        },
        "execution_policy": {
            "maker_only": True,
            "max_chase_steps": g("max_chase_steps"),
            "protection_first": True,
            "allow_add_on_same_direction_manual": False,
        },
    }

# ===================== module: plans =====================
# -*- coding: utf-8 -*-
"""
方案库构建、评估与排序（plan_*）。

计划轮枚举所有符合范围的同期垂直信用价差备选，每个 = 一组(短腿 + 同到期更价外保护腿)，
按 胜率 / 盈亏比 / 人工审计契合 计算综合分排序，输出方案库（含方案号 + 推荐标签）。

口径（启发式，用于排序比较；非精确定价）：
- 胜率 ≈ 1 - |短腿 delta|（短腿到期 OTM 近似概率）。
- 同期垂直：保护腿与短腿同到期、到期一起了结。
    净 credit = (短腿 mark - 保护腿 mark) × 数量；最大亏损 = 腿宽折BTC - 净credit（**硬封顶**）。
- 盈亏比 = 净credit / 最大亏损（仅二者均为正时有意义）。
纯函数，便于单测。
"""

MODE_VERTICAL = 2  # 唯一结构标识，供菜单/展示读取 p["mode"]


def plan_mode_cn(mode=MODE_VERTICAL):
    return "同期垂直"


def plan_expiry_label(instrument_name):
    """从合约名取期号(到期标签)，如 BTC-1JUN26-74000-C → 1JUN26。"""
    if not instrument_name:
        return "—"
    parts = instrument_name.split("-")
    return parts[1] if len(parts) >= 2 else "—"


def plan_id(mode, short_instrument, protection_instrument):
    """按结构内容生成**稳定唯一编号**（确定性，不随排序/进程变化）。
    下单轮按此编号匹配，避免「方案重排后选错执行」。返回 4 位数 1000-9999。"""
    key = "%s|%s|%s" % (mode, short_instrument or "", protection_instrument or "")
    h = 0
    for ch in key:
        h = (h * 131 + ord(ch)) % 1000000007
    return 1000 + (h % 9000)


def plan_win_rate(short_delta):
    return None if short_delta is None else 1.0 - abs(short_delta)


def plan_width_btc(width_usd, index_price, amount):
    if not width_usd or not index_price:
        return None
    return (width_usd / index_price) * amount


def plan_effective_credit(short_prem, prot_prem):
    """垂直：同到期了结，净credit = 短腿权利金 - 保护腿权利金。
    返回 (net_credit, net_credit, protection_premium, 0.0)。
    short_prem/prot_prem 为持仓口径权利金(已×数量)。"""
    if short_prem is None or prot_prem is None:
        return None, None, None, None
    single = short_prem - prot_prem
    return single, single, prot_prem, 0.0


def plan_max_loss(width_usd, index_price, effective_net_credit, amount):
    wb = plan_width_btc(width_usd, index_price, amount)
    if wb is None or effective_net_credit is None:
        return None
    return max(wb - effective_net_credit, 0.0)


def plan_rr(net_credit, max_loss):
    if net_credit is None or max_loss is None or max_loss <= 0 or net_credit <= 0:
        return None
    return net_credit / max_loss


def plan_ev(win_rate, net_credit, max_loss):
    """期望值/周期(BTC) = 胜率×有效净credit − (1−胜率)×最大亏损（最坏亏损口径，仅作参考）。"""
    if win_rate is None or net_credit is None or max_loss is None:
        return None
    return win_rate * net_credit - (1.0 - win_rate) * max_loss


def plan_breakeven(want_call, short_strike, short_mark, prot_mark, spot):
    """到期盈亏平衡价(近似)：短腿行权 ± 每张净credit折USD。
    call: 价格高于此开始亏；put: 价格低于此开始亏。"""
    if short_strike is None or short_mark is None or prot_mark is None or not spot:
        return None
    net_pc_usd = (short_mark - prot_mark) * spot      # 每张净credit折 USD(价格点)
    return short_strike + net_pc_usd if want_call else short_strike - net_pc_usd


def plan_credit_on_margin(net_credit_effective, im_with_protection):
    """净credit / 占用保证金（每周期保证金回报率）——本策略价值核心指标。"""
    if net_credit_effective is None or not im_with_protection or im_with_protection <= 0:
        return None
    return net_credit_effective / im_with_protection


def plan_credit_on_margin_per_24h(credit_on_margin, dte_hours):
    if credit_on_margin is None or not dte_hours or dte_hours <= 0:
        return None
    return credit_on_margin * (24.0 / dte_hours)


def plan_preferred_delta(confidence, delta_range):
    """Manual confidence -> preferred short-leg |delta| within the operator range."""
    lo, hi = delta_range
    c = (confidence if confidence is not None else 50) / 100.0
    return lo + (hi - lo) * c


def plan_delta_fit(short_delta, preferred_delta, scale=0.25):
    if short_delta is None:
        return 0.0
    return max(0.0, 1.0 - abs(abs(short_delta) - preferred_delta) / scale)


def plan_assemble(amount, spot, min_ratio,
                  preferred_delta, want_call,
                  short, sq, prot, pq, spm, pm_ok, account_model,
                  short_dte_hours=None, prot_dte_hours=None):
    """组装一个同期垂直候选方案 dict（不含综合分/方案号，由 plan_rank 补充）。"""
    sq, pq = sq or {}, pq or {}
    short_mark, prot_mark = sq.get("mark"), pq.get("mark")
    short_delta = (short or {}).get("_delta", sq.get("delta"))
    width = abs(prot.get("strike", 0) - short.get("strike", 0)) if (short and prot) else None

    premium_income = (short_mark * amount) if short_mark is not None else None
    protection_premium = (prot_mark * amount) if prot_mark is not None else None
    covered = 1
    eff_credit, single_credit, amort, residual = plan_effective_credit(
        premium_income, protection_premium)
    max_loss = plan_max_loss(width, spot, eff_credit, amount)
    rr = plan_rr(eff_credit, max_loss)

    fee = 0.0
    if short_mark is not None:
        fee += acct_option_fee_ccy(short_mark, amount)
    if prot_mark is not None:
        fee += acct_option_fee_ccy(prot_mark, amount)
    full_burn = (acct_full_burn(protection_premium, acct_option_fee_ccy(prot_mark, amount))
                 if prot_mark is not None else None)

    relief_ratio = (spm or {}).get("relief_ratio")
    relief_ok = isinstance(relief_ratio, (int, float)) and relief_ratio >= min_ratio
    no_bid = sq.get("best_bid") in (None, 0)

    reject = None
    if not short:
        reject = "无合适短腿"
    elif not prot:
        reject = "无合格保护腿"
    elif no_bid:
        reject = "短腿无买盘"
    elif not relief_ok:
        reject = "S:PM 释放不足"
    elif not pm_ok:
        reject = "账户非组合保证金"
    qualified = reject is None

    short_inst = (short or {}).get("instrument_name")
    prot_inst = (prot or {}).get("instrument_name")
    credit_on_margin = plan_credit_on_margin(eff_credit, (spm or {}).get("im_with_protection"))
    return {
        "id": plan_id(MODE_VERTICAL, short_inst, prot_inst),
        "short_expiry_label": plan_expiry_label(short_inst),
        "protection_expiry_label": plan_expiry_label(prot_inst),
        "mode": MODE_VERTICAL, "mode_cn": plan_mode_cn(),
        "short_instrument": (short or {}).get("instrument_name"),
        "short_strike": (short or {}).get("strike"), "short_delta": short_delta,
        "short_mark": short_mark, "short_bid": sq.get("best_bid"),
        "short_ask": sq.get("best_ask"), "short_tick": sq.get("tick"),
        "short_dte_hours": short_dte_hours, "short_expiry": (short or {}).get("expiration_timestamp"),
        "protection_instrument": (prot or {}).get("instrument_name"),
        "protection_strike": (prot or {}).get("strike"), "protection_delta": pq.get("delta"),
        "protection_mark": prot_mark, "protection_bid": pq.get("best_bid"),
        "protection_ask": pq.get("best_ask"), "protection_tick": pq.get("tick"),
        "protection_dte_days": (round(prot_dte_hours / 24.0, 2) if prot_dte_hours else None),
        "protection_dte_hours": prot_dte_hours,
        "protection_expiry": (prot or {}).get("expiration_timestamp"),
        "width": width, "amount": amount, "spot": spot,
        "win_rate": plan_win_rate(short_delta),
        "premium_income": premium_income, "protection_premium": protection_premium,
        "covered_cycles": covered, "residual_value": residual,
        "amortized_cost_per_cycle": amort,
        "net_credit_single": single_credit, "net_credit_effective": eff_credit,
        "max_loss": max_loss, "rr": rr,
        "ev": plan_ev(plan_win_rate(short_delta), eff_credit, max_loss),
        "breakeven": plan_breakeven(want_call, (short or {}).get("strike"),
                                    short_mark, prot_mark, spot),
        "credit_on_margin": credit_on_margin,
        "credit_on_margin_per_24h": plan_credit_on_margin_per_24h(
            credit_on_margin, short_dte_hours),
        "entry_fee": fee, "full_burn": full_burn,
        "spread_cost": acct_spread_cost(sq.get("best_bid"), sq.get("best_ask"), amount),
        "delta_fit": plan_delta_fit(short_delta, preferred_delta),
        "im_short_only": (spm or {}).get("im_short_only"),
        "im_with_protection": (spm or {}).get("im_with_protection"),
        "margin_relief_abs": (spm or {}).get("relief_abs"),
        "margin_relief_ratio": relief_ratio,
        "pm_ok": pm_ok, "account_model": account_model,
        "qualified": qualified, "reject_reason": reject,
        "composite": None, "plan_no": None, "tags": [],
    }


def plan_prelim_score(c, weights):
    """无 S:PM 的初筛分（用于枚举后裁剪 top-K）。"""
    wr = c.get("win_rate") or 0.0
    rr = c.get("rr") or 0.0
    eff = c.get("credit_on_margin_per_24h") or c.get("credit_on_margin") or 0.0
    base = (weights["win_rate"] * wr + weights["rr"] * min(rr, 1.0)
            + weights.get("efficiency", 0.0) * min(eff, 1.0)
            + weights.get("manual", 0.0) * (c.get("delta_fit") or 0.0))
    return base * (c.get("execution_feasibility_penalty") or 1.0)


def plan_rank(cands, weights, menu_size):
    """对候选打综合分、排序、确保两种模式均入选、编号、打推荐标签，返回菜单 list。"""
    pool = [c for c in cands if c.get("qualified")] or list(cands)
    rrs = [c["rr"] for c in pool if isinstance(c.get("rr"), (int, float)) and c["rr"] > 0]
    max_rr = max(rrs) if rrs else 1.0
    effs = [c["credit_on_margin_per_24h"] for c in pool
            if isinstance(c.get("credit_on_margin_per_24h"), (int, float))
            and c["credit_on_margin_per_24h"] > 0]
    max_eff = max(effs) if effs else 1.0
    for c in pool:
        wr = c.get("win_rate") or 0.0
        rr = c.get("rr") or 0.0
        rr_norm = min(rr / max_rr, 1.0) if max_rr else 0.0
        eff = c.get("credit_on_margin_per_24h") or 0.0
        eff_norm = min(eff / max_eff, 1.0) if max_eff else 0.0
        c["rr_norm"] = rr_norm
        c["efficiency_norm"] = eff_norm
        base = (weights["win_rate"] * wr + weights["rr"] * rr_norm
                + weights.get("efficiency", 0.0) * eff_norm
                + weights.get("manual", 0.0) * (c.get("delta_fit") or 0.0))
        c["surface_composite"] = base
        c["composite"] = base * (c.get("execution_feasibility_penalty") or 1.0)
    ranked = sorted(pool, key=lambda c: c["composite"], reverse=True)
    menu = ranked[:menu_size]
    for i, c in enumerate(menu, start=1):
        c["plan_no"] = i
    _assign_tags(menu)
    return menu


def _assign_tags(menu):
    for c in menu:
        c["tags"] = []
    if not menu:
        return
    max(menu, key=lambda c: c.get("win_rate") or 0.0)["tags"].append("高胜率")
    rr_c = [c for c in menu if isinstance(c.get("rr"), (int, float)) and c["rr"] > 0]
    if rr_c:
        max(rr_c, key=lambda c: c["rr"])["tags"].append("高盈亏比")
    ev_c = [c for c in menu if isinstance(c.get("ev"), (int, float))]
    if ev_c:
        max(ev_c, key=lambda c: c["ev"])["tags"].append("高期望")
    eff_c = [c for c in menu if isinstance(c.get("credit_on_margin_per_24h"), (int, float))]
    if eff_c:
        max(eff_c, key=lambda c: c["credit_on_margin_per_24h"])["tags"].append("资金效率")
    max(menu, key=lambda c: c.get("composite") or 0.0)["tags"].append("均衡")

# ===================== module: display =====================
# -*- coding: utf-8 -*-
"""
前端中文显示（disp_*）：把进场上下文 ctx 渲染为 FMZ LogStatus 表格 + 简明事件日志。

LogStatus 表格格式：`{"type":"table","title":..,"cols":[..],"rows":[[..]]}`，
用反引号包裹 JSON；多表用数组；表外文本可用 `文本#ff0000` 着色。
全部为纯函数，便于单测。
"""
import json

# ---- 文案映射 ----
MANUAL_GATE_STATE_CN = {
    "PLANNING_ALLOWED": "人工审计门已开启",
    "WAIT_MANUAL_AUDIT_GATE": "等待人工审计门",
    "MANUAL_CONTEXT_INVALID": "人工审计上下文无效",
}
BIAS_CN = {
    "SHORT_CALL": "偏空 · 卖出看涨 Call",
    "SHORT_PUT": "偏多 · 卖出看跌 Put",
}
STATE_CN = {
    "NO_POSITION": "无持仓", "MANUAL_READY": "人工审计就绪",
    "PROTECTION_SELECTION": "选保护腿", "SPM_SIMULATION": "S:PM 模拟",
    "PROTECTION_BUILDING": "建保护腿", "PROTECTION_ACTIVE_NO_SHORT": "保护腿就绪·未建卖方腿",
    "SHORT_BUILDING": "建卖方腿", "SHORT_ACTIVE_PROTECTED": "已保护·卖方持仓",
    "HOLD_MONITORING": "持仓监控", "SHORT_EXPIRED_OR_CLOSED": "卖方腿到期/平仓",
    "REUSE_DECISION": "复用决策", "EXIT_OR_WAIT_REVIEW": "退出/复核", "CLOSED": "已了结",
}
REASON_CN = {
    "DRY_RUN_PLAN_ONLY": "空跑：仅生成方案，未真实下单",
    "STRUCTURE_OPEN": "结构已建立（保护腿 + 卖方腿成交）",
    "PROTECTION_ACTIVE_NO_SHORT": "保护腿已建，卖方腿未成交（等待/人工）",
    "PROTECTION_NOT_FILLED": "保护腿未成交，继续围绕锁定方案等待",
    "MARGIN_RELIEF_INSUFFICIENT": "保证金释放不足，未达门槛，已放弃",
    "ACCOUNT_NOT_PM": "账户非组合保证金(S:PM)，已放弃",
    "NO_SPOT": "无法获取参考价",
    "NO_INSTRUMENTS": "未取到期权合约列表",
    "NO_SHORT_EXPIRY_IN_BAND": "近端到期不在设定区间(24–72h)",
    "NO_SHORT_STRIKE": "近端无合适行权价",
    "NO_PROTECTION_EXPIRY_IN_BAND": "保护腿到期不在设定区间(5–10d)",
    "NO_PROTECTION_CANDIDATE": "无合格保护腿候选（可能均过度虚值）",
    "NO_CANDIDATE": "无任何符合范围的备选（检查 delta/腿宽/到期范围）",
    "SAME_DIRECTION_CONFIRMATION": "持仓中：同向人工审计仅确认，不加仓",
    "PLAN_MENU_READY": "人工审计门：方案候选已生成，等待 VRP/预算通过后给确认码",
    "NO_PLAN_MENU(请先运行计划轮)": "人工审计门：未找到可复核方案，请重新生成候选",
    "ORDER_PREVIEW_DRY": "人工审计门·空跑预览：已复核选用方案，未真实下单",
    "NO_RISK_EXIT_BUDGET": "风险退出预算缺失",
    "EXIT_QUOTE_DATA_GAP": "风险退出报价缺口",
    "EXIT_PRICE_ABOVE_CAP": "风险退出卖一高于预算上限",
    "EXIT_DEPTH_DATA_GAP": "风险退出卖一深度缺口",
    "EXIT_DEPTH_INSUFFICIENT": "风险退出卖一深度不足",
}

_C_GREEN = "#16a34a"
_C_ORANGE = "#c2410c"
_C_RED = "#dc2626"
_C_GRAY = "#64748b"


def disp_manual_gate_state_cn(s):
    return MANUAL_GATE_STATE_CN.get(s, s or "—")


def disp_manual_hint(manual_gate_state):
    """按人工审计门状态给操作指引，降低认知负荷。"""
    if manual_gate_state == "PLANNING_ALLOWED":
        return "按 DIRECTION_BIAS、24h目标到期、delta、腿宽和数量生成候选"
    if manual_gate_state == "WAIT_MANUAL_AUDIT_GATE":
        return "开启 MANUAL_PLANNING_ALLOWED 后生成候选"
    if manual_gate_state == "MANUAL_CONTEXT_INVALID":
        return "人工审计参数无效或过期，需修正后重建候选"
    return "—"


def disp_state_cn(s):
    return STATE_CN.get(s, s)


def disp_reason_cn(reason):
    if reason is None:
        return "—"
    if reason in REASON_CN:
        return REASON_CN[reason]
    if reason.startswith("EXIT_REVIEW_MANUAL:"):
        sig = reason.split(":", 1)[1]
        return "退出/复核人工审计（%s），不再续卖新卖方腿" % disp_manual_gate_state_cn(sig)
    if reason.startswith("IDLE"):
        return "空闲：不满足进场条件 " + reason[4:]
    if reason.startswith("PLAN_NOT_QUALIFIED"):
        tail = reason.split(":", 1)[1] if ":" in reason else ""
        return "选用方案复核不合格" + (("：" + tail) if tail else "")
    if reason.startswith("PLAN_NOT_IN_MENU"):
        return "方案号不在方案库内：" + (reason.split(":", 1)[1] if ":" in reason else "")
    if reason.startswith("PLAN_MENU_READY"):
        return REASON_CN["PLAN_MENU_READY"] + reason[len("PLAN_MENU_READY"):]
    return reason


def _num(x, small=8, big=4):
    if x is None:
        return "—"
    if isinstance(x, bool):
        return "是" if x else "否"
    if isinstance(x, (int, float)):
        fmt = ("%%.%df" % (small if abs(x) < 1 else big)) % x
        return fmt.rstrip("0").rstrip(".") if "." in fmt else fmt
    return str(x)


def _usd(btc_val, spot):
    if btc_val is None or spot is None or not isinstance(btc_val, (int, float)):
        return "—"
    return "≈$%.2f" % (btc_val * spot)


def _btc_usd(btc_val, spot):
    return "%s BTC  %s" % (_num(btc_val), _usd(btc_val, spot))


def _usd0(btc_val, spot):
    """紧凑 USD（菜单用，BTC 数值过小不便肉眼比较）。"""
    if btc_val is None or spot is None or not isinstance(btc_val, (int, float)):
        return "—"
    return "$%.0f" % (btc_val * spot)


def _dist_pct(strike, spot):
    """行权价距现价百分比（带符号：上方+ / 下方−），快速判断虚值度。"""
    if strike is None or spot is None or not spot:
        return "—"
    return "%+.1f%%" % ((strike - spot) / spot * 100.0)


# ---- 健康度 / 合理性自检 ----

_NEAR_SPOT_PCT = 1.5      # 短腿距现价过近阈值(%)：高被行权风险
_HIGH_DELTA = 0.45        # 短腿 delta 偏高阈值
_LOW_RR = 0.20            # 盈亏比偏低阈值
_LOW_RELIEF = 0.20        # S:PM 释放偏低阈值
_GRADE_RANK = {"警示": 3, "提示": 2, "通过": 1}


def disp_health_notes(ctx):
    """对选用方案做综合审查，返回 [(级别, 说明)]；级别 警示>提示>通过。"""
    notes = []
    g = ctx.get
    spot = g("spot")
    ss = g("short_strike")
    # 1) 流动性 / 成交可行性
    if g("short_bid") in (None, 0):
        notes.append(("警示", "短腿无买盘(best_bid=0)：maker 卖单可能无法成交"))
    # 2) 短腿距现价过近 → 高被行权风险
    if isinstance(ss, (int, float)) and spot:
        dist = abs(ss - spot) / spot * 100.0
        if dist < _NEAR_SPOT_PCT:
            notes.append(("警示", "短腿距现价仅 %.1f%%(<%.1f%%)：过近，被行权/被突破风险高"
                          % (dist, _NEAR_SPOT_PCT)))
    # 3) 权利金 vs 手续费
    prem, fee = g("short_premium_income"), g("estimated_entry_fee")
    if isinstance(prem, (int, float)) and isinstance(fee, (int, float)) and prem <= fee:
        notes.append(("警示", "卖方权利金 ≤ 预估手续费，单笔净收益非正"))
    # 4) 短腿 delta 偏高(偏激进)
    sd = g("short_delta")
    if isinstance(sd, (int, float)) and abs(sd) > _HIGH_DELTA:
        notes.append(("提示", "短腿 |delta|=%.2f 偏高(>%.2f)：偏激进、胜率偏低" % (abs(sd), _HIGH_DELTA)))
    # 5) EV(最坏口径)为负
    ev = g("ev")
    if isinstance(ev, (int, float)) and ev < 0:
        notes.append(("提示", "EV(最坏口径)为负：单周期纯概率期望不利，正 edge 依赖方向论证 + 复用摊薄"))
    # 6) 盈亏比偏低
    rr = g("rr")
    if isinstance(rr, (int, float)) and rr < _LOW_RR:
        notes.append(("提示", "盈亏比 %.2f 偏低(<%.2f)：收益对风险偏薄" % (rr, _LOW_RR)))
    # 7) S:PM 释放偏低(虽达标)
    ratio, minr = g("margin_relief_ratio"), g("min_required_ratio")
    if isinstance(ratio, (int, float)) and isinstance(minr, (int, float)) \
            and minr <= ratio < _LOW_RELIEF:
        notes.append(("提示", "S:PM 释放 %.0f%% 偏低：达标但保证金缓释有限" % (ratio * 100)))
    # 8) 保护成本 / 权利金倍数
    pc = g("protection_entry_cost")
    if isinstance(pc, (int, float)) and isinstance(prem, (int, float)) and prem > 0 and pc / prem >= 5:
        notes.append(("提示", "保护腿成本为权利金的 %.1f 倍，净 credit 过薄时应放弃" % (pc / prem)))
    # 9) 保护腿 delta 偏低
    pdelta = g("protection_delta")
    if isinstance(pdelta, (int, float)) and abs(pdelta) < 0.08:
        notes.append(("提示", "保护腿 |delta|=%.3f 偏低：偏经济型保护而非强对冲" % abs(pdelta)))
    if not notes:
        notes.append(("通过", "综合校验通过：流动性/距离/权利金/释放/盈亏比均合理"))
    return notes


def disp_health_grade(ctx):
    """综合评级：取所有检查中的最严级别。"""
    notes = disp_health_notes(ctx)
    worst = max(notes, key=lambda n: _GRADE_RANK.get(n[0], 0))[0]
    return worst


# ---- 表格 ----

def _overview_table(ctx):
    g = ctx.get
    missing = g("live_checklist_missing") or []
    profile_line = g("run_profile") or "?"
    if profile_line == "TEST":
        profile_line += " / 测试模式：不会真实下单，全部真实交易门强制关闭"
    elif missing:
        profile_line += " / 实盘清单缺项 " + ",".join(missing)
    else:
        profile_line += " / 实盘清单就绪"
    self_check = disp_self_check_line(g("startup_self_check"))
    return {
        "type": "table", "title": "运行概览",
        "cols": ["项目", "值"],
        "rows": [
            ["版本 / 主链", "v%s ｜ 完整主链" % (g("version") or "?")],
            ["RUN_PROFILE", profile_line],
            ["启动自检", self_check],
            ["标的 / 结算币", g("currency")],
            ["目标DTE / 审批TTL", "%sh / %s分" % (g("target_dte_hours"), int((g("approval_ttl_ms") or 0) / 60000))],
            ["人工审计门", disp_manual_gate_state_cn(g("manual_gate_state"))],
            ["方向", BIAS_CN.get(g("direction_bias"), g("direction_bias"))],
            ["当前锁定/选用方案", g("selected_plan") or "—"],
            ["选用方案保护模式", g("protection_mode_cn") or "—"],
            ["执行门控", disp_gate_line(g("gate_summary"))],
            ["状态机", disp_state_cn(g("state"))],
            ["参考价", _num(g("spot"), small=2, big=2)],
            ["选档指引", disp_manual_hint(g("manual_gate_state"))],
            ["枚举漏斗", disp_diag_line(g("enum_diag")) if g("enum_diag") else "—"],
            ["选用方案综合评级", disp_health_grade(ctx) if g("short_instrument") else "—"],
            ["本轮结论", disp_reason_cn(g("reason"))],
        ],
    }


def disp_diag_line(diag):
    """枚举漏斗压成一行（放进概览，省一张表）。"""
    if not diag:
        return "—"
    return ("扫描%s → 出界%s/薄%s/宽%s/无保护%s → 候选%s → 进库%s → 合格%s" % (
        diag.get("短腿扫描", 0), diag.get("delta区间外", 0), diag.get("权利金过薄", 0),
        diag.get("价差过宽", 0), diag.get("无合格保护腿(腿宽内)", 0),
        diag.get("生成候选", 0), diag.get("进入菜单", 0), diag.get("合格", 0)))


def disp_self_check_line(self_check):
    if not self_check:
        return "未运行"
    overall = self_check.get("overall") or "UNKNOWN"
    checks = self_check.get("checks") or {}
    labels = {
        "config": "配置",
        "deribit_index": "Deribit行情",
        "deribit_options": "Deribit期权",
        "deribit_account": "Deribit账户",
        "gex_context": "GEX",
        "binance_hedge_position": "Binance对冲",
    }
    failed = []
    for key in ("config", "deribit_index", "deribit_options", "deribit_account",
                "gex_context", "binance_hedge_position"):
        item = checks.get(key)
        if item and not item.get("ok"):
            failed.append("%s:%s" % (labels.get(key, key), item.get("reason") or "FAIL"))
    if failed:
        return "%s ｜ %s" % (overall, "；".join(failed))
    return "%s ｜ 交易所/数据/模块自检通过" % overall


_PRECOMMIT_CN = {
    "manual_context_valid": "人工审计上下文有效",
    "same_manual_context": "人工审计上下文未漂移",
    "approval_not_expired": "确认码未过期",
    "locked_plan_hash_match": "锁定方案未漂移",
    "locked_quality_code_match": "方案质量码未漂移",
    "vertical_only": "同期垂直结构",
    "vrp_rechecked": "VRP/context 复核通过",
    "spm_rechecked": "S:PM 保证金复核通过",
    "quotes_rechecked": "行情复核通过",
    "entry_net_credit_after_costs_positive": "扣成本后净 credit 为正",
    "projected_budget_passed": "账户预算通过",
    "ledger_reconciled": "账本/交易所对账通过",
    "no_unknown_orders": "未知活动订单/同腿冲突订单阻断",
    "spread_ok": "买卖价差通过",
    "execution_feasibility_rechecked": "执行可行性复核通过",
}


def _precommit_line_cn(pre):
    if pre is None:
        return "未触发"
    if pre.get("passed"):
        return "通过"
    failed = pre.get("failed") or []
    if not failed:
        return "未通过：原因未明"
    parts = ["%s（%s）" % (_PRECOMMIT_CN.get(k, "预提交检查未通过"), k) for k in failed]
    return "未通过：%s" % "；".join(parts)


def _last_command_line_cn(ctx):
    action = ctx.get("last_command")
    outcome = ctx.get("last_command_outcome")
    if not action and not outcome:
        return None
    if outcome == "locked":
        return "确认码已接受：方案已锁定（locked）"
    if outcome == "confirm_code_invalid_or_stale":
        return "确认码无效或已失效：未锁定、未下单（confirm_code_invalid_or_stale）"
    if outcome == "duplicate_ignored":
        return "重复确认码已忽略：未重复执行（duplicate_ignored）"
    if action == "UNKNOWN":
        return "非确认码命令已忽略：运行时只接受确认码（UNKNOWN）"
    return "%s：%s" % (action or "命令", outcome or "已接收")


def disp_menu_table(menu, selected_no, spot):
    """方案库对比（同期垂直信用价差；★=当前选中的方案号）。"""
    def pct(x):
        return ("%.0f%%" % (x * 100)) if isinstance(x, (int, float)) else "—"

    def f2(x):
        return ("%.2f" % x) if isinstance(x, (int, float)) else "—"

    def expiry_key(p):
        return p.get("short_expiry") or p.get("short_expiry_label") or p.get("short_dte_hours")

    def expiry_sort_key(k):
        return (0, k) if isinstance(k, (int, float)) else (1, str(k))

    has_target = any((p or {}).get("expiry_role") == "TARGET_24H" for p in (menu or []))
    keys = [expiry_key(p or {}) for p in (menu or []) if expiry_key(p or {}) is not None]
    nearest_display_key = min(keys, key=expiry_sort_key) if keys else None

    def role_cn(p):
        role = p.get("expiry_role")
        if not has_target and nearest_display_key is not None and expiry_key(p) == nearest_display_key:
            return "最近可用"
        return {"TARGET_24H": "近24h", "NEXT_EXPIRY": "次日备选"}.get(role, "—")

    rows = []
    for p in menu:
        g = p.get
        star = "★" if g("id") == selected_no else ""
        qihao = "%s(同)" % g("short_expiry_label")
        code = g("_confirm_code") or g("confirm_code") or "—"
        if code == "—" and g("_not_lockable_reason"):
            code = "不可锁定:" + str(g("_not_lockable_reason"))
        tags = "/".join(g("tags") or []) or "—"
        ok = "合格" if g("qualified") else ("✗" + (g("reject_reason") or ""))
        if g("qualified") and g("execution_feasibility_grade"):
            ok = "%s/%s" % (ok, g("execution_feasibility_grade"))
        dte = ("%.1fd" % (g("short_dte_hours") / 24.0)) if g("short_dte_hours") else "—"
        rows.append([
            "%s%s" % (star, g("id")), code, tags, role_cn(p), g("mode_cn") or "—", qihao, dte,
            "%s(Δ%s)" % (_num(g("short_strike")), _num(g("short_delta"))),
            _num(g("protection_strike")), _num(g("width")),
            _dist_pct(g("short_strike"), spot), pct(g("win_rate")),
            _usd0(g("net_credit_effective"), spot), pct(g("credit_on_margin")),
            pct(g("credit_on_margin_per_24h")),
            f2(g("rr")), _num(g("breakeven"), small=2, big=2),
            pct(g("margin_relief_ratio")), ok,
        ])
    return {
        "type": "table",
        "title": "固定备选方案库（完整展示；不随实时行情重排；VRP_CONTEXT_MISSING=仅展示不可锁定；有效$=净 credit）",
        "cols": ["编号", "确认码/锁定状态", "推荐", "期号角色", "模式", "期号(短/保护)", "到期", "短行权(Δ)", "保护行权",
                 "腿宽", "短距现价", "胜率", "有效$", "信用/保证金", "24h效率", "盈亏比", "盈亏平衡价",
                 "释放", "合格"],
        "rows": rows,
    }


def _position_table(ctx):
    """选用方案·保证金 + 成本/记账（合并 S:PM 与成本，省一张表；结算币 + USD）。"""
    g = ctx.get
    spot = g("spot")
    mode = g("protection_mode")
    ratio, minr = g("margin_relief_ratio"), g("min_required_ratio")
    accepted = (isinstance(ratio, (int, float)) and isinstance(minr, (int, float))
                and ratio >= minr)
    ml_label = "最大亏损(硬封顶)" if mode == 2 else "最大亏损≈(非硬封顶)"
    cm = g("credit_on_margin")
    cm24 = g("credit_on_margin_per_24h")
    rows = [
        ["合约(短/保护)", g("short_instrument") or "—", g("protection_instrument") or "—"],
        ["仅卖方腿 IM (B)", _num(g("im_short_only")), _usd(g("im_short_only"), spot)],
        ["卖方+保护 IM (C/占用保证金)", _num(g("im_with_protection")), _usd(g("im_with_protection"), spot)],
        ["保证金释放(比例/门槛)", "%s / %s" % (
            ("%.0f%%" % (ratio * 100)) if isinstance(ratio, (int, float)) else "—",
            ("%.0f%%" % (minr * 100)) if isinstance(minr, (int, float)) else "—"),
         "达标" if accepted else "未达标"],
        ["账户(模型/组合保证金)", g("account_margin_model") or "—", "是" if g("pm_accepted") else "否"],
        ["卖方腿 mark/张(=交易所标记)", _num(g("short_mark")), _usd(g("short_mark"), spot)],
        ["保护腿 mark/张(=交易所标记)", _num(g("protection_mark")), _usd(g("protection_mark"), spot)],
        ["下单数量(每结构)", _num(g("amount")), "—"],
        ["卖方权利金收入(×数量)", _num(g("short_premium_income")), _usd(g("short_premium_income"), spot)],
        ["保护腿权利金支出(×数量)", _num(g("protection_entry_cost")), _usd(g("protection_entry_cost"), spot)],
        ["单笔净credit(×数量)", _num(g("net_credit_single")), _usd(g("net_credit_single"), spot)],
    ]
    rows += [
        ["有效净credit(每周期)", _num(g("net_credit")), _usd(g("net_credit"), spot)],
        [ml_label, _num(g("max_loss")), _usd(g("max_loss"), spot)],
        ["盈亏比 / 信用占保证金", ("%.2f" % g("rr")) if isinstance(g("rr"), (int, float)) else "—",
         ("%.1f%%" % (cm * 100)) if isinstance(cm, (int, float)) else "—"],
        ["24h资金效率", ("%.1f%%" % (cm24 * 100)) if isinstance(cm24, (int, float)) else "—", "按DTE折算"],
        ["到期盈亏平衡价(近似)", _num(g("breakeven"), small=2, big=2), "—"],
        ["预估开仓手续费", _num(g("estimated_entry_fee")), _usd(g("estimated_entry_fee"), spot)],
    ]
    if g("execution_feasibility_grade"):
        rows.append(["执行可行性", "%s / %s" % (
            g("execution_feasibility_grade"),
            ("%.0f" % g("execution_feasibility_score"))
            if isinstance(g("execution_feasibility_score"), (int, float)) else "—"),
            ",".join(g("execution_feasibility_warnings") or []) or "—"])
    title_prefix = "候选方案预览" if g("preview_plan_detail") else "选用方案"
    return {
        "type": "table", "title": "%s · 保证金与成本（编号 %s · 评级 %s · 预估）"
        % (title_prefix, g("selected_id"), disp_health_grade(ctx)),
        "cols": ["项目", "值/BTC", "≈USD/备注"], "rows": rows,
    }


def disp_order_intent_table(intent):
    """『将下达订单』意图表：真实下单前核对实际订单。"""
    rows = []
    for it in intent or []:
        prices = "/".join(_num(p) for p in (it.get("prices") or [])) or "—"
        rows.append([it.get("leg") or "", "买" if it.get("side") == "buy" else "卖",
                     it.get("instrument") or "—", prices, _num(it.get("amount")),
                     "post_only+reject"])
    return {"type": "table", "title": "将下达订单（maker-only；计划价含一步追价）",
            "cols": ["腿", "方向", "合约", "计划价(含追价)", "数量", "下单方式"], "rows": rows}


def _health_table(ctx):
    rows = [[lv, txt] for lv, txt in disp_health_notes(ctx)]
    return {"type": "table", "title": "合理性检查（综合评级：%s）" % disp_health_grade(ctx),
            "cols": ["级别", "说明"], "rows": rows}


def _pct1(x):
    return ("%.1f%%" % (x * 100)) if isinstance(x, (int, float)) else "数据缺口"


def _pct_signed(x):
    return ("%+.1f%%" % (x * 100)) if isinstance(x, (int, float)) else "数据缺口"


def _market_line(mark, bid, ask):
    if mark is None and bid is None and ask is None:
        return "数据缺口"
    return "mark %s ｜ bid %s ｜ ask %s" % (_num(mark), _num(bid), _num(ask))


def _qty_line(v):
    return _num(v) if isinstance(v, (int, float)) else "数据缺口"


def _btc_usd_gap(btc_val, spot):
    if not isinstance(btc_val, (int, float)):
        return "数据缺口"
    return _btc_usd(btc_val, spot)


def _usd_signed_value(v):
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        return "数据缺口"
    return "$%.2f" % v if v >= 0 else "-$%.2f" % abs(v)


def _num_or_gap(v, small=6, big=2):
    return _num(v, small=small, big=big) if isinstance(v, (int, float)) and not isinstance(v, bool) else "数据缺口"


def _is_position_manage(ctx):
    return ctx.get("console_phase") == "POSITION_MANAGE" or any(
        ctx.get(k) for k in ("position_detail", "take_profit_detail", "hedge_detail", "ledger_detail")
    )


def _take_profit_summary_cn(ctx):
    tp = ctx.get("take_profit_detail") or {}
    if not tp:
        ratio = ctx.get("take_profit_ratio")
        return "TP=%s" % (ratio if ratio is not None else "数据缺口")
    status = tp.get("status") or ("已达标" if tp.get("qualified") else ("未达标" if tp.get("ratio") is not None else "数据缺口"))
    if not tp.get("quote_ok", True) and tp.get("quote_gap"):
        status += "｜" + str(tp.get("quote_gap"))
    if tp.get("dte_gate_active"):
        status += "｜普通止盈暂停:%s" % (tp.get("dte_gate_reason") or "TP_DTE_GATE")
    return "%s｜捕获 %s / 目标 %s｜目标价 %s" % (
        status, _pct1(tp.get("ratio")), _pct1(tp.get("target_ratio")), _num(tp.get("price_cap")))


def _hedge_summary_cn(ctx):
    h = ctx.get("hedge_detail") or {}
    if h:
        if h.get("data_gap"):
            return "数据缺口：%s｜禁新增对冲/仅保守持仓" % h.get("data_gap")
        reduce_only = "reduce_only=%s" % ("是" if h.get("reduce_only") else "否")
        if h.get("hedge_policy"):
            return "%s｜%s｜full %s eff %s 当前 %s delta %s｜pending %s" % (
                h.get("policy_state") or "HOLD",
                h.get("policy_reason") or "—",
                _num(h.get("full_target_qty")), _num(h.get("eff_target_qty")),
                _num(h.get("current_hedge_qty")), _num(h.get("policy_delta_to_trade")),
                h.get("pending_order_id") or "—")
        return "%s｜%s/%s｜目标 %s 当前 %s 预计 %s｜%s" % (
            h.get("action_cn") or h.get("action") or "保持",
            h.get("venue") or "—", h.get("instrument") or "—",
            _num(h.get("target")), _num(h.get("perp_qty")), _num(h.get("delta_to_trade")),
            reduce_only)
    return ctx.get("hedge_state") or ("风险状态 %s" % (ctx.get("risk_state") or "—"))


def _ledger_summary_cn(ctx):
    ld = ctx.get("ledger_detail") or {}
    if not ld:
        rec = ctx.get("reconciled")
        return "状态 %s｜恢复 %s｜对账 %s" % (
            disp_state_cn(ctx.get("state")), ctx.get("recovery_state") or "OK",
            "已对齐" if rec is True else ("不一致" if rec is False else "—"))
    rec = ld.get("reconciled")
    rec_line = "已对齐" if rec is True else ("不一致" if rec is False else "数据缺口")
    recovery = ld.get("recovery_state") or "OK"
    allow = "可新开" if ld.get("allow_new_open", True) else "禁新开"
    return "%s｜恢复 %s/%s｜净credit %s｜剩余退出预算 %s" % (
        rec_line, recovery, allow,
        _btc_usd_gap(ld.get("actual_net_credit"), ctx.get("spot")),
        _btc_usd_gap(ld.get("remaining_exit_budget"), ctx.get("spot")))


def _position_manage_overview_table(ctx):
    pd = ctx.get("position_detail") or {}
    hedge_pnl = pd.get("hedge_unrealized_pnl_usd")
    hedge_state = pd.get("hedge_pnl_state")
    hedge_line = _usd_signed_value(hedge_pnl) if isinstance(hedge_pnl, (int, float)) else (hedge_state or "数据缺口")
    pnl_gap = pd.get("pnl_data_gap") or "未扣除已发生手续费/已用退出支出"
    return {"type": "table", "title": "持仓总览", "cols": ["项目", "值", "备注"], "rows": [
        ["生命周期", pd.get("lifecycle") or disp_state_cn(ctx.get("state")), ctx.get("exit_campaign_state") or "—"],
        ["短腿合约", pd.get("short_instrument") or "数据缺口", "剩余 %s" % _qty_line(pd.get("remaining_short_qty"))],
        ["保护腿合约", pd.get("long_instrument") or "数据缺口", "剩余 %s" % _qty_line(pd.get("long_remaining_qty"))],
        ["入场均价(短/保护)", "%s / %s" % (_num(pd.get("short_fill_price")), _num(pd.get("long_fill_price"))), "冻结成交均价"],
        ["短腿盘口", _market_line(pd.get("short_mark"), pd.get("short_bid"), pd.get("short_ask")), "持仓风险主参考"],
        ["保护腿盘口", _market_line(pd.get("long_mark"), pd.get("long_bid"), pd.get("long_ask")), "保护价值参考"],
        ["盘口数据", pd.get("quote_gap") or "OK", "仅影响展示，不改变持仓管理动作"],
        ["到期剩余", ("%.1fh" % pd.get("dte_hours")) if isinstance(pd.get("dte_hours"), (int, float)) else "数据缺口", "短腿 DTE"],
        ["盈亏平衡价", _num_or_gap(pd.get("breakeven"), small=2, big=2), "旧持仓缺失集中归入恢复接管缺口"],
        ["短腿距现价", ("%.1f%%" % pd.get("short_distance_pct")) if isinstance(pd.get("short_distance_pct"), (int, float)) else "数据缺口", "按当前 spot"],
        ["期权浮动盈亏", "短腿 %s ｜ 保护腿 %s ｜ 合计 %s" % (
            _usd_signed_value(pd.get("option_short_unrealized_pnl_usd")),
            _usd_signed_value(pd.get("option_long_unrealized_pnl_usd")),
            _usd_signed_value(pd.get("option_unrealized_pnl_usd"))), "按 mark 估算，折 USD"],
        ["期货对冲浮动盈亏", hedge_line, "无对冲时显示“对冲未启用”，不渲染成 0"],
        ["组合浮动盈亏", _usd_signed_value(pd.get("combo_unrealized_pnl_usd")), pnl_gap],
    ]}


def _take_profit_budget_table(ctx):
    tp = ctx.get("take_profit_detail") or {}
    risk = ctx.get("risk_exit_detail") or {}
    risk_reason = risk.get("reason")
    risk_reason_cn = disp_reason_cn(risk_reason) if risk_reason else None
    status = tp.get("status") or ("已达标" if tp.get("qualified") else ("未达标" if tp.get("ratio") is not None else "数据缺口"))
    if not tp.get("quote_ok", True) and tp.get("quote_gap"):
        status += "｜" + str(tp.get("quote_gap"))
    dte_gate_note = "剩余DTE %s；普通止盈门槛 > %sh；风险退出/对冲不受限" % (
        ("%.1fh" % tp.get("remaining_dte_hours")) if isinstance(tp.get("remaining_dte_hours"), (int, float)) else "数据缺口",
        tp.get("take_profit_min_dte_hours") if tp.get("take_profit_min_dte_hours") is not None else "—")
    if tp.get("dte_gate_active"):
        status += "｜普通止盈暂停"
    if risk.get("within"):
        risk_within = "可越价执行"
    elif risk_reason_cn:
        risk_within = "不可执行:%s" % risk_reason_cn
    else:
        risk_within = "不可越价/预算不足"
    risk_book_line = "卖一 %s ｜ 深度 %s ｜ 价格%s ｜ 深度%s" % (
        _num_or_gap(risk.get("ask")),
        _num_or_gap(risk.get("ask_depth")),
        "通过" if risk.get("within_price") else "受限",
        "通过" if risk.get("depth_ok") else "受限")
    target_underlying = tp.get("tp_underlying_target_price")
    if isinstance(target_underlying, (int, float)) and not isinstance(target_underlying, bool):
        target_underlying_line = "%s（delta线性估算）" % _num(target_underlying, small=2, big=2)
    else:
        target_underlying_line = "数据缺口:%s" % (tp.get("tp_target_data_gap") or "TP_UNDERLYING_TARGET_DATA_GAP")
    return {"type": "table", "title": "止盈/退出预算", "cols": ["项目", "值", "备注"], "rows": [
        ["止盈状态", "%s ｜ 当前捕获 %s / 目标 %s" % (status, _pct1(tp.get("ratio")), _pct1(tp.get("target_ratio"))), "保护腿价值不进分母"],
        ["临近交割止盈门", ("触发｜%s" % dte_gate_note) if tp.get("dte_gate_active") else ("未触发｜%s" % dte_gate_note), tp.get("dte_gate_reason") or "仅限制普通止盈"],
        ["本期最大盈利上限", _btc_usd_gap(tp.get("entry_profit_ceiling_net"), ctx.get("spot")), "冻结入场快照"],
        ["目标止盈金额", _btc_usd_gap(tp.get("target_profit_amount"), ctx.get("spot")), "默认 80% 捕获"],
        ["短腿参考买回成本", _btc_usd_gap(tp.get("short_buyback_ref"), ctx.get("spot")), "mark × 剩余短腿数量"],
        ["预估退出费/预留", "%s / %s" % (_btc_usd(tp.get("estimated_exit_fee"), ctx.get("spot")),
                                    _btc_usd(tp.get("exit_reserve"), ctx.get("spot"))), "预算保守项"],
        ["剩余买回预算", _btc_usd_gap(tp.get("remaining_budget"), ctx.get("spot")), "max_total_exit_spend - 已用 - 预留"],
        ["止盈目标价", "%s（预算内最高可买回价）" % _num(tp.get("price_cap")), "价格≤该值才满足止盈预算"],
        ["止盈目标标的价", target_underlying_line, "展示估算，不改变按期权买回价执行"],
        ["风险退出预算", "%s ｜ 来源 %s ｜ %s" % (
            _btc_usd_gap(risk.get("remaining_budget"), ctx.get("spot")),
            risk.get("budget_source") or "—", risk_within), "风险触发后按配置门控自动评估"],
        ["风险退出上限", "%s ｜ cap %s" % (_btc_usd_gap(risk.get("remaining_budget"), ctx.get("spot")), _num(risk.get("price_cap"))), "风险退出独立预算"],
        ["风险退出盘口", risk_book_line, risk_reason_cn or "卖一深度需覆盖剩余短腿数量"],
    ]}


def _risk_hedge_table(ctx):
    h = ctx.get("hedge_detail") or {}
    data_gap = h.get("data_gap")
    module_state = ("数据缺口：%s；禁新增对冲/仅保守持仓" % data_gap) if data_gap else (h.get("module_state") or "正常")
    trigger_line = "观察 %s ｜ 开对冲 %s ｜ 紧急 %s" % (
        _pct1(h.get("watch_probability")), _pct1(h.get("open_probability")), _pct1(h.get("emergency_probability")))
    trigger_price = h.get("hedge_underlying_trigger_price")
    if isinstance(trigger_price, (int, float)) and not isinstance(trigger_price, bool):
        method = h.get("hedge_underlying_trigger_method") or "data_gap"
        price_line = "%s（%s）" % (_num(trigger_price, small=2, big=2), method)
    elif h.get("hedge_trigger_data_gap"):
        price_line = "数据缺口:%s" % h.get("hedge_trigger_data_gap")
    elif h.get("hedge_price_line") is not None:
        price_line = _num(h.get("hedge_price_line"), small=2, big=2)
    else:
        price_line = "概率触发，无固定价线"
    reduce_only = "reduce_only=%s" % ("是" if h.get("reduce_only") else "否")
    policy_rows = []
    if h.get("hedge_policy"):
        pending = h.get("pending_order_id") or "—"
        cooldown = "add_until %s ｜ reduce_until %s" % (
            _num(h.get("add_cooldown_until"), small=0, big=0),
            _num(h.get("reduce_cooldown_until"), small=0, big=0))
        warnings = ",".join(h.get("policy_warnings") or []) or "—"
        policy_rows = [
            ["对冲控制器", "state=%s ｜ reason=%s ｜ pending=%s" % (
                h.get("policy_state") or "—", h.get("policy_reason") or "—", pending),
             "V32 gamma-aware reconciliation，读交易所仓位为真"],
            ["控制器目标", "full %s ｜ eff %s ｜ current %s ｜ delta %s" % (
                _num(h.get("full_target_qty")), _num(h.get("eff_target_qty")),
                _num(h.get("current_hedge_qty")), _num(h.get("policy_delta_to_trade"))),
             "只按 eff-current 发单"],
            ["V32 参数", "soft %s ｜ gamma %s/%s ｜ band %s ｜ crash %sbps ｜ hold_until %s" % (
                _pct1(h.get("soft_ratio")),
                _pct1(h.get("gamma_fraction")),
                h.get("gamma_data_state") or "—",
                _num(h.get("rebalance_deadband")),
                _num(h.get("crash_adverse_bps")),
                _num(h.get("min_hold_until"), small=0, big=0)),
             h.get("final3_mode") or "NORMAL"],
            ["Crash观测", "ref %s ｜ age %ss ｜ adverse %sbps" % (
                _num(h.get("crash_ref_price"), small=2, big=2),
                _num(h.get("crash_ref_age_seconds"), small=0, big=0),
                _num(h.get("crash_adverse_bps"))),
             "只读观测，不新增门控或条件单"],
            ["控制器门控", "cross_bps %s ｜ %s ｜ warn %s" % (
                _num(h.get("policy_cross_bps")), cooldown, warnings),
             "HARD 不被成本/滑点告警阻断"],
            ["成本字段", "reserved_not_computed bps %s ｜ warn %s" % (
                _num(h.get("episode_cost_bps")), warnings),
             "保留遥测，不代表真实累计滑点/手续费"],
        ]
    return {"type": "table", "title": "风险与对冲", "cols": ["项目", "值", "备注"], "rows": [
        ["模块状态", module_state, "reason=%s" % (",".join(h.get("reason_codes") or []) or "—")],
        ["触界概率(入场/当前/漂移)", "%s / %s / %s" % (
            _pct1(h.get("entry_touch_probability")),
            _pct1(h.get("touch_probability_now")),
            _pct_signed(h.get("touch_probability_drift"))), "风险严重度输入"],
        ["对冲触发阈值", trigger_line, "来自入场风险锚"],
        ["对冲触发目标价", price_line, "价格线仅作二次确认"],
        ["期权净 delta", _num(h.get("net_option_delta")), "结构 delta=%s" % _num(h.get("net_delta"))],
        ["对冲目标", "目标 %s ｜ 当前 %s ｜ 预计交易 %s" % (
            _num(h.get("target")), _num(h.get("perp_qty")), _num(h.get("delta_to_trade"))), "数量单位随场所"],
        ["对冲场所", "%s / %s / %s" % (h.get("venue") or "—", h.get("instrument") or "—", h.get("side") or "—"), "方向为将要交易方向"],
        ["对冲动作", "%s ｜ %s" % (h.get("action_cn") or h.get("action") or "保持", reduce_only), "孤儿对冲会强制清理"],
    ] + policy_rows}


def _ledger_recovery_table(ctx):
    ld = ctx.get("ledger_detail") or {}
    rec = ld.get("reconciled")
    rec_line = "已对齐" if rec is True else ("不一致" if rec is False else "数据缺口")
    reasons = ",".join(ld.get("reconcile_reasons") or []) or "—"
    orders = ld.get("active_orders") or []
    order_line = "；".join("%s/%s" % (o.get("instrument_name") or "—", o.get("label") or "—") for o in orders) or "—"
    recovery = "%s ｜ %s" % (ld.get("recovery_state") or "OK", "可新开" if ld.get("allow_new_open", True) else "禁新开")
    return {"type": "table", "title": "记账/对账/恢复", "cols": ["项目", "值", "备注"], "rows": [
        ["入场收入/成本", "短腿收入 %s ｜ 保护成本 %s" % (
            _btc_usd_gap(ld.get("short_credit"), ctx.get("spot")),
            _btc_usd_gap(ld.get("protection_cost"), ctx.get("spot"))), "冻结入场账本"],
        ["入场手续费/净credit", "%s ｜ %s" % (
            _btc_usd_gap(ld.get("entry_fees"), ctx.get("spot")),
            _btc_usd_gap(ld.get("actual_net_credit"), ctx.get("spot"))), "实际成交后"],
        ["退出支出/剩余预算", "%s ｜ %s" % (
            _btc_usd_gap(ld.get("realized_exit_spend"), ctx.get("spot")),
            _btc_usd_gap(ld.get("remaining_exit_budget"), ctx.get("spot"))), "用于止盈买回"],
        ["执行历史", "入场%s ｜ 退出%s ｜ 保护回收%s ｜ 对冲%s" % (
            ld.get("entry_fill_count") or 0, ld.get("exit_fill_count") or 0,
            ld.get("protection_recovery_count") or 0, ld.get("hedge_fill_count") or 0), "已记录条数"],
        ["交易所对账", "%s ｜ %s" % (rec_line, reasons), "快照 vs 真实期权持仓"],
        ["数据质量", "%s ｜ 恢复接管缺口：%s ｜ 行情缺口：%s" % (
            ld.get("data_quality_state") or "OK",
            ",".join(ld.get("legacy_recovery_gaps") or []) or "无",
            (ctx.get("position_detail") or {}).get("quote_gap") or (ctx.get("position_detail") or {}).get("pnl_data_gap") or "无"),
         "纯计划轮冗余项已在持仓阶段隐藏"],
        ["恢复状态", recovery, "启动恢复/孤儿状态"],
        ["活动订单", order_line, "当前持仓相关未完成订单"],
    ]}


_ledger_recovery_table_base = _ledger_recovery_table


def _ledger_recovery_table(ctx):
    table = _ledger_recovery_table_base(ctx)
    ld = (ctx or {}).get("ledger_detail") or {}
    spot = (ctx or {}).get("spot")
    rows = table.get("rows") or []
    extra_rows = [
        ["Settlement", "status=%s events=%s net=%s" % (
            ld.get("settlement_pnl_status") or "NONE",
            ld.get("settlement_event_count") or 0,
            _btc_usd_gap(ld.get("option_settlement_cashflow_ccy"), spot)),
         "short %s / long %s" % (
             _btc_usd_gap(ld.get("short_settlement_cashflow_ccy"), spot),
             _btc_usd_gap(ld.get("long_settlement_cashflow_ccy"), spot))],
        ["Protection recovery", "net %s / fees %s" % (
            _btc_usd_gap(ld.get("realized_protection_recovery_value"), spot),
            _btc_usd_gap(ld.get("realized_protection_recovery_fees"), spot)),
         "included in option realized PnL"],
        ["Option realized PnL", "status=%s value=%s" % (
            ld.get("option_realized_pnl_status") or "DATA_GAP",
            _btc_usd_gap(ld.get("option_realized_pnl_ccy"), spot)),
         "entry credit - exits + protection recovery + settlement"],
        ["Final option PnL", "status=%s value=%s" % (
            ld.get("final_pnl_status") or "OPEN",
            _btc_usd_gap(ld.get("final_option_pnl_ccy"), spot)),
         "only final when both option legs are closed"],
    ]
    insert_at = 4 if len(rows) >= 4 else len(rows)
    table["rows"] = rows[:insert_at] + extra_rows + rows[insert_at:]
    return table


def disp_position_manage_tables(ctx):
    return [
        _position_manage_overview_table(ctx),
        _take_profit_budget_table(ctx),
        _risk_hedge_table(ctx),
        _ledger_recovery_table(ctx),
    ]


def _header_color(ctx):
    reason = ctx.get("reason") or ""
    if reason == "STRUCTURE_OPEN":
        return _C_GREEN
    if reason in ("MARGIN_RELIEF_INSUFFICIENT", "ACCOUNT_NOT_PM", "PROTECTION_NOT_FILLED",
                  "NO_PLAN_MENU(请先运行计划轮)") \
            or reason.startswith("PLAN_NOT_QUALIFIED") or reason.startswith("PLAN_NOT_IN_MENU"):
        return _C_RED
    if ctx.get("short_instrument") and any(lv == "警示" for lv, _ in disp_health_notes(ctx)):
        return _C_ORANGE
    return _C_GRAY


# ---- 交互控制台（计划轮唯一交互入口；持仓后切换为当前环节摘要）----

_PHASE_CN = {
    "WAIT_MANUAL_AUDIT_GATE": "等待人工审计", "MANUAL_GATE": "人工审计门",
    "RECOMMEND_READY": "方案库就绪·待硬授权", "HARD_APPROVAL_WAIT": "待计划硬授权",
    "PLAN_LOCKED": "方案锁定·预提交", "POSITION_MANAGE": "持仓管理",
    "EXIT_CAMPAIGN": "退出活动", "LONG_RECOVERY": "保护腿回收",
    "RECOVERY_BLOCKED": "恢复阻塞", "ORPHAN_HEDGE_AUTO_CLEANUP": "孤儿对冲自动只减清理",
    "ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED": "孤儿对冲需人工清理", "KILLED": "已急停",
}

# 操作提示引擎：阶段 → 「下一步点哪个按钮、输什么」的人话提示（落实「在交互栏给出操作提示」）
_HINTS = {
    "WAIT_MANUAL_AUDIT_GATE": "等待可交易人工审计；人工审计不可用/过期时禁新开仓，持仓管理继续",
    "MANUAL_GATE": "人工审计门模式：进场依据 MANUAL_PLANNING_ALLOWED、DIRECTION_BIAS、数量与风险参数",
    "RECOMMEND_READY": "待批方案：点【执行】输入方案确认码进场",
    "HARD_APPROVAL_WAIT": "待批方案：点【执行】输入方案确认码进场",
    "PLAN_LOCKED": "方案已锁定·预提交复核中；复核通过且进场门开启才真实下单",
    "POSITION_MANAGE": "无需交互，按配置门控自动管理；运行时只阅读状态栏",
    "EXIT_CAMPAIGN": "退出活动中：逐 tick 买回短腿、不破止盈预算；预算内无法成交则暂停后重试",
    "LONG_RECOVERY": "短腿已归零·回收保护腿中；无 bid 记 LONG_RESIDUAL_ONLY，售出/结算后归档",
    "RECOVERY_BLOCKED": "启动恢复阻塞：账本与交易所持仓无法解释映射；禁开新仓，请人工核对",
    "ORPHAN_HEDGE_AUTO_CLEANUP": "已确认无期权短腿风险，正在自动提交 Binance 只减清理；无需输入运行时命令",
    "ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED": "孤儿对冲需要人工核对并手动只减清理；禁新开仓",
    "KILLED": "配置层 KILL_NEW_RISK 已开启：停新开仓；退出/对冲减仓/对账继续",
}


def _console_phase_cn(p):
    return _PHASE_CN.get(p, p or "—")


def disp_operation_hint(ctx):
    """据当前阶段 / 门控 / 人工审计裁决给出唯一操作提示串。"""
    g = ctx.get
    phase = g("console_phase")
    if phase == "POSITION_MANAGE":
        return _HINTS["POSITION_MANAGE"]
    if g("kill_new_risk"):
        return _HINTS["KILLED"]
    if phase in _HINTS:
        return _HINTS[phase]
    sv = g("manual_verdict") or {}
    if sv.get("availability") == "MANUAL_GATE":
        return _HINTS["MANUAL_GATE"]
    if sv.get("block_new_opens"):
        return _HINTS["WAIT_MANUAL_AUDIT_GATE"]
    return "—"


def disp_gate_line(gate_summary):
    """门控四动作压成一行：进场/退出/对冲开/对冲减 的 ✓✗。"""
    if not gate_summary:
        return "—"

    def mk(a):
        return "✓" if (gate_summary.get(a) or {}).get("allowed") else "✗"
    return "进场%s 退出%s 对冲开%s 对冲减%s" % (
        mk("ENTRY"), mk("EXIT"), mk("HEDGE_OPEN"), mk("HEDGE_REDUCE"))


def disp_in_flight_line(in_flight):
    if not in_flight or not in_flight.get("count"):
        return None
    labels = []
    for o in in_flight.get("orders") or []:
        labels.append("%s/%s" % (o.get("instrument_name") or "—", o.get("label") or "—"))
    return "%s 条 ｜ %s" % (in_flight.get("count"), "；".join(labels) or "—")


def disp_orphan_cleanup_line(cleanup, step=None):
    if not cleanup:
        return None
    qty = _num(cleanup.get("perp_qty"))
    side = cleanup.get("suggested_side") or "—"
    inst = cleanup.get("instrument") or "—"
    if cleanup.get("auto_cleanup_allowed"):
        if step and step.get("dry"):
            prefix = "测试模式：仅模拟自动只减清理，不会真实下单"
        elif step and step.get("blocked"):
            prefix = "自动只减清理受阻"
        elif step:
            prefix = "自动只减清理已提交"
        else:
            prefix = "自动只减清理待提交"
        reason = (step or {}).get("reason") or cleanup.get("cleanup_block_reason") or "AUTO_REDUCE_ONLY"
    else:
        prefix = "需要人工只减清理"
        reason = cleanup.get("cleanup_block_reason") or ",".join(cleanup.get("reasons") or []) or "MANUAL_CLEANUP_ONLY"
    return "%s：%s 仓位 %s，建议 %s；原因 %s" % (prefix, inst, qty, side, reason)


def disp_entry_prot_order_line(order):
    if not order:
        return None
    elapsed = order.get("wait_elapsed_ms")
    elapsed_s = ("%ss" % int(elapsed / 1000)) if isinstance(elapsed, (int, float)) else "—"
    mode = "taker兜底区" if order.get("taker_due") else "maker等待"
    return "id=%s ｜ 价=%s ｜ 已等=%s ｜ %s" % (
        order.get("order_id") or "—",
        _num(order.get("price")),
        elapsed_s,
        mode,
    )


def disp_entry_progress_line(progress):
    if not progress:
        return None
    prot = progress.get("prot_done") or 0.0
    short = progress.get("short_done") or 0.0
    target = progress.get("target_amount") or progress.get("amount") or 0.0
    if prot <= 1e-12 and short <= 1e-12:
        return None
    base = "保护腿已成交 %s/%s；卖方腿已成交 %s/%s" % (
        _num(prot), _num(target), _num(short), _num(target))
    if short > prot + 1e-12:
        return base + "；异常：短腿数量超过保护腿，恢复阻塞，禁止继续开仓"
    if short <= 1e-12:
        return base + "；卖方腿未成交，未形成期权空头，继续围绕锁定方案尝试短腿"
    if target and short < target - 1e-12:
        return base + "；开仓部分成交，已有受保护短腿风险，进入持仓管理"
    if target and short >= target - 1e-12 and prot >= target - 1e-12:
        return base + "；结构已建仓，进入持仓管理"
    return base


def disp_manual_gate_line(verdict):
    """人工审计接收裁决压成一行。"""
    if not verdict:
        return "—"
    avail = verdict.get("availability")
    if avail == "MANUAL_GATE":
        return "离线手动(人工审计)"
    block = "禁新开" if verdict.get("block_new_opens") else "可新开"
    direction = verdict.get("direction_bias") or verdict.get("manual_direction") or "NA"
    return "%s ｜ %s ｜ direction=%s" % (avail, block, direction)


_RISK_STATE_CN = {
    "NORMAL": "正常", "WATCH": "观察", "EXIT_PREFERRED": "偏退出(风险严重)",
    "HEDGE_READY": "风险触发(先退后对冲)", "HEDGE_ACTIVE": "对冲监控中",
    "MANUAL_REVIEW": "人工复核",
}


def disp_risk_line(risk):
    """持仓后风险评估压成一行：状态 + 触界概率 + 漂移。数据缺口单独标注。"""
    if not risk:
        return None
    if risk.get("market_data_gap"):
        return "数据缺口（短腿盘口缺 delta/IV，风险评估降级·未驱动主动动作）"
    cr = risk.get("current_risk") or {}
    p, d = cr.get("touch_probability_now"), cr.get("touch_probability_drift")
    state = _RISK_STATE_CN.get(risk.get("tail_risk_state"), risk.get("tail_risk_state") or "—")
    extras = []
    if isinstance(p, (int, float)):
        extras.append("触界%.0f%%" % (p * 100))
    if isinstance(d, (int, float)):
        extras.append("漂移%+.0f%%" % (d * 100))
    return "%s%s" % (state, ("｜" + " ".join(extras)) if extras else "")


def disp_pipeline_table(ctx):
    """完整主链模块总览：持仓阶段只显示模块有效摘要，计划专用字段隐藏。"""
    g = ctx.get
    position_mode = _is_position_manage(ctx)
    if position_mode:
        rows = [
            ["计划轮", "持仓管理中，暂停推新方案"],
            ["执行模块", "%s ｜ entry=%s ｜ 活动订单=%s" % (
                g("commit_reason") or "未触发",
                g("entry_state") or "—",
                (g("manage_in_flight_order") or {}).get("count") or 0)],
            ["退出模块", "%s ｜ %s" % (g("exit_campaign_state") or "空闲", _take_profit_summary_cn(ctx))],
            ["对冲模块", _hedge_summary_cn(ctx)],
            ["记账/对账", _ledger_summary_cn(ctx)],
            ["恢复模块", g("recovery_state") or (ctx.get("ledger_detail") or {}).get("recovery_state") or "OK"],
        ]
        return {"type": "table", "title": "完整主链模块回显", "cols": ["模块", "状态/关键输出"], "rows": rows}
    pending = g("pending_candidates") or []
    codes = ", ".join("#%s=%s" % (c.get("id"), c.get("confirm_code")) for c in pending) or "—"
    pre = g("precommit")
    pre_line = _precommit_line_cn(pre)
    budget = g("projected_budget") or {}
    rows = [
        ["计划轮", "%s ｜ 漏斗：%s" % (
            "持仓管理中，暂停推新方案" if position_mode else (g("plan_build_reason") or "—"),
            disp_diag_line(g("enum_diag")) if g("enum_diag") else "—")],
        ["候选展示", "展示%s / 可锁定%s / VRP阻断%s / 来源=%s ｜ %s" % (
            g("display_candidates_count") or 0,
            g("lockable_candidates_count") or 0,
            g("plan_vrp_blocked") or 0,
            "固定库" if g("plan_library_frozen") else (g("menu_source") or "实时"),
            g("not_lockable_reason") or "—")],
        ["确认码", codes],
        ["预提交", pre_line],
        ["执行模块", "%s ｜ entry=%s ｜ order_intent=%s" % (
            g("commit_reason") or "未触发", g("entry_state") or "—", len(g("order_intent") or []))],
        ["预算模块", budget.get("decision") or "—"],
        ["记账/恢复", _ledger_summary_cn(ctx)],
        ["对冲模块", _hedge_summary_cn(ctx)],
        ["退出模块", "%s ｜ %s" % (
            g("exit_campaign_state") or "空闲", _take_profit_summary_cn(ctx),
        )],
    ]
    entry_progress_line = disp_entry_progress_line(g("entry_progress"))
    if entry_progress_line:
        rows.insert(5, ["开仓进度", entry_progress_line])
    return {"type": "table", "title": "完整主链模块回显", "cols": ["模块", "状态/关键输出"], "rows": rows}


def disp_console_table(ctx):
    """计划轮显示唯一确认入口；持仓阶段显示非交互摘要。"""
    g = ctx.get
    position_mode = _is_position_manage(ctx)
    last_cmd_line = _last_command_line_cn(ctx)
    rows = [
        ["阶段", _console_phase_cn(g("console_phase"))],
        ["执行门控", disp_gate_line(g("gate_summary"))],
        ["人工审计接收", disp_manual_gate_line(g("manual_verdict"))],
    ]
    if last_cmd_line:
        rows.append(["上次命令", last_cmd_line])
    if position_mode:
        pd = g("position_detail") or {}
        rows = [
            ["阶段", _console_phase_cn(g("console_phase"))],
            ["生命周期", pd.get("lifecycle") or disp_state_cn(g("state"))],
            ["当前自动动作", str((g("action_arb") or {}).get("executable_action") or "保持观察")],
        ]
        if last_cmd_line:
            rows.append(["上次命令", last_cmd_line])
        _if = disp_in_flight_line(g("manage_in_flight_order"))
        if _if:
            rows.append(["活动订单", _if])
        if g("take_profit_detail"):
            rows.append(["止盈状态", _take_profit_summary_cn(ctx)])
        _rl = disp_risk_line(g("risk_pkg"))
        if _rl:
            rows.append(["风险状态", _rl])
        if g("hedge_detail"):
            rows.append(["对冲状态", _hedge_summary_cn(ctx)])
        elif g("hedge_data_gap"):
            rows.append(["对冲数据", "%s：无法读取对冲仓位，禁新增对冲，仅保守持仓" % g("hedge_data_gap")])
        combo = pd.get("combo_unrealized_pnl_usd")
        rows.append(["组合浮盈亏", _usd_signed_value(combo) if isinstance(combo, (int, float)) else (pd.get("pnl_data_gap") or "数据缺口")])
        rows.append(["操作提示", disp_operation_hint(ctx)])
        return {"type": "table", "title": "当前环节摘要", "cols": ["项目", "值"], "rows": rows}
    for c in (g("pending_candidates") or []):
        rows.append(["待批 #%s" % c.get("id"),
                     "%s 确认码 %s" % (c.get("summary") or "—", c.get("confirm_code") or "—")])
    pre = g("precommit")
    if pre is not None:
        rows.append(["预提交", _precommit_line_cn(pre)])
    if g("commit_reason"):
        rows.append(["开仓", g("commit_reason")])
    if g("entry_state"):
        nc = g("entry_net_credit")
        rows.append(["开仓活动", "%s%s" % (g("entry_state"),
                     ("｜净credit %.6g" % nc) if isinstance(nc, (int, float)) else "")])
    entry_progress_line = disp_entry_progress_line(g("entry_progress"))
    if entry_progress_line:
        rows.append(["开仓进度", entry_progress_line])
    prot_line = disp_entry_prot_order_line(g("entry_prot_order"))
    if prot_line:
        rows.append(["保护腿挂单", prot_line])
    arb = g("action_arb")
    if arb:
        line = str(arb.get("executable_action"))
        if arb.get("blocked_reason"):
            line += " (优先 %s 受阻:%s)" % (arb.get("preferred_action"), arb.get("blocked_reason"))
        rows.append(["风险动作", line])
    _if = disp_in_flight_line(g("manage_in_flight_order"))
    if _if:
        rows.append(["活动订单", _if])
    _rl = disp_risk_line(g("risk_pkg"))
    if _rl:
        rows.append(["风险", _rl])
    if g("hedge_data_gap"):
        rows.append(["对冲数据", "%s：无法读取对冲仓位，禁新增对冲，需人工核对" % g("hedge_data_gap")])
    orphan_line = disp_orphan_cleanup_line(g("orphan_hedge_cleanup"), g("orphan_hedge_cleanup_step"))
    if orphan_line:
        rows.append(["孤儿对冲清理", orphan_line])
    if position_mode and g("take_profit_detail"):
        rows.append(["止盈", _take_profit_summary_cn(ctx)])
    elif g("take_profit_ratio") is not None:
        rows.append(["止盈资格", g("take_profit_ratio")])
    if g("exit_campaign_state"):
        rows.append(["退出活动", g("exit_campaign_state")])
    if position_mode and g("hedge_detail"):
        rows.append(["对冲", _hedge_summary_cn(ctx)])
    elif g("hedge_state"):
        rows.append(["对冲", g("hedge_state")])
    if position_mode and g("ledger_detail"):
        rows.append(["记账/对账", _ledger_summary_cn(ctx)])
    elif g("reconciled") is False:
        rows.append(["对账", "✗ 快照与交易所持仓不符（已记录，风险收口继续）"])
    rows.append(["操作提示", disp_operation_hint(ctx)])
    return {"type": "table", "title": "交互控制台", "cols": ["项目", "值"], "rows": rows}


def disp_status_panel(ctx, note=""):
    """组装 LogStatus 字符串：标题行(着色) + 多表数组。
    有方案库时显示方案库对比表；选用/置顶方案有腿时显示其明细/模拟/成本/检查。"""
    header = "%s ｜ %s%s" % (note or "进场流水线", disp_reason_cn(ctx.get("reason")),
                            _header_color(ctx))
    position_mode = _is_position_manage(ctx)
    tables = [disp_console_table(ctx), _overview_table(ctx), disp_pipeline_table(ctx)]
    if ctx.get("menu") and not position_mode:     # 计划轮保留完整候选；持仓后不再推新方案干扰读屏。
        tables.append(disp_menu_table(ctx["menu"], ctx.get("selected_plan"), ctx.get("spot")))
    if position_mode:
        tables.extend(disp_position_manage_tables(ctx))
    elif ctx.get("short_instrument"):
        tables.append(_position_table(ctx))       # 保证金 + 成本（S:PM 与成本已合并为一张）
        if ctx.get("order_intent"):
            tables.append(disp_order_intent_table(ctx["order_intent"]))
        tables.append(_health_table(ctx))
    return header + "\n`" + json.dumps(tables, ensure_ascii=False) + "`"


def disp_log_menu(menu, spot):
    """启动时把整轮方案明细打到 Log（永久记录；便于复盘初始方案库）。"""
    lines = ["[启动方案明细] 共 %d 条：" % len(menu)]
    for p in menu:
        g = p.get
        tags = "/".join(g("tags") or []) or "-"
        lines.append("  #%s %s %s %s 短%s(Δ%s)/保%s 宽%s 距%s 胜%s 有效%s 信/保%s 盈亏%s 平衡%s 释放%s %s" % (
            g("id"), tags, g("mode_cn"),
            ("%s→%s" % (g("short_expiry_label"), g("protection_expiry_label")))
            if g("mode") == 1 else ("%s(同)" % g("short_expiry_label")),
            _num(g("short_strike")), _num(g("short_delta")), _num(g("protection_strike")),
            _num(g("width")), _dist_pct(g("short_strike"), spot),
            ("%.0f%%" % (g("win_rate") * 100)) if isinstance(g("win_rate"), (int, float)) else "-",
            _usd0(g("net_credit_effective"), spot),
            ("%.0f%%" % (g("credit_on_margin") * 100)) if isinstance(g("credit_on_margin"), (int, float)) else "-",
            ("%.2f" % g("rr")) if isinstance(g("rr"), (int, float)) else "-",
            _num(g("breakeven"), small=2, big=2),
            ("%.0f%%" % (g("margin_relief_ratio") * 100)) if isinstance(g("margin_relief_ratio"), (int, float)) else "-",
            "合格" if g("qualified") else "✗"))
    return "\n".join(lines)


def disp_log_summary(ctx, note=""):
    """简明中文事件行（写入 Log 事件流）。"""
    g = ctx.get
    if _is_position_manage(ctx):
        pd = g("position_detail") or {}
        tp = g("take_profit_detail") or {}
        hd = g("hedge_detail") or {}
        risk = g("risk_pkg") or {}
        cr = risk.get("current_risk") or {}
        tp_status = tp.get("status") or ("已达标" if tp.get("qualified") else ("未达标" if tp.get("ratio") is not None else "数据缺口"))
        risk_line = disp_risk_line(risk)
        if not risk_line and isinstance(hd.get("touch_probability_now"), (int, float)):
            risk_line = "触界%.1f%%" % (hd.get("touch_probability_now") * 100)
        if not risk_line and isinstance(cr.get("touch_probability_now"), (int, float)):
            risk_line = "触界%.1f%%" % (cr.get("touch_probability_now") * 100)
        hedge_line = hd.get("action_cn") or hd.get("hedge_pnl_state") or "保持"
        combo = _usd_signed_value(pd.get("combo_unrealized_pnl_usd"))
        return ("%s｜持仓管理｜%s｜止盈%s %s/%s｜风险%s｜对冲%s｜组合浮盈亏 %s" % (
            note or "manual-gate",
            pd.get("lifecycle") or disp_state_cn(g("state")),
            tp_status,
            _pct1(tp.get("ratio")),
            _pct1(tp.get("target_ratio")),
            risk_line or "数据缺口",
            hedge_line,
            combo,
        ))
    ratio = g("margin_relief_ratio")
    ratio_s = ("%.1f%%" % (ratio * 100)) if isinstance(ratio, (int, float)) else "—"
    return ("%s ｜ 短 %s@%s ｜ 保 %s@%s ｜ 释放 %s ｜ %s" % (
        note or "进场", g("short_instrument") or "—", _num(g("short_mark")),
        g("protection_instrument") or "—", _num(g("protection_mark")),
        ratio_s, disp_reason_cn(g("reason"))))

# ===================== module: spm_sim =====================
# -*- coding: utf-8 -*-
"""
S:PM 保证金模拟校验（spm_*，§7）。

抵消机制已联网取证确认可行（同币种同子账户跨到期 netting）；本模块只**逐笔确认幅度**：
比较 B(仅 short) 与 C(short+protection) 两个模拟场景的 IM，看远期保护腿是否带来足够的
保证金释放。逻辑保持简单，不做额外复杂回路。
"""



# ---------- 纯计算 ----------

def spm_relief(im_b, im_c):
    """返回 {relief_abs, relief_ratio}。im_b<=0 时 ratio=0（无意义）。"""
    if im_b is None or im_c is None:
        return {"relief_abs": None, "relief_ratio": None}
    relief_abs = im_b - im_c
    ratio = (relief_abs / im_b) if im_b > 0 else 0.0
    return {"relief_abs": relief_abs, "relief_ratio": ratio}


def spm_account_is_portfolio_margin(account_summary):
    """校验账户确为组合保证金（S:PM）。返回 (ok, model_str)。"""
    if not account_summary:
        return False, None
    model = account_summary.get("margin_model")
    pm_flag = account_summary.get("portfolio_margining_enabled")
    ok = bool(pm_flag) or (model is not None and "pm" in str(model).lower())
    return ok, model


# ---------- 调交易所模拟 ----------

def _im(sim_result):
    return None if not sim_result else sim_result.get("initial_margin")


def spm_simulate_structure(currency, short_instrument, protection_instrument, amount):
    """模拟 B(+short) 与 C(+short+protection)，返回完整报告 dict。"""
    sim_b = dbt_simulate_portfolio(currency, {short_instrument: -amount})
    sim_c = dbt_simulate_portfolio(
        currency, {short_instrument: -amount, protection_instrument: +amount})
    im_b, im_c = _im(sim_b), _im(sim_c)
    rep = spm_relief(im_b, im_c)
    rep.update({
        "short_instrument": short_instrument,
        "protection_instrument": protection_instrument,
        "amount": amount,
        "im_short_only": im_b,
        "im_with_protection": im_c,
        "mm_short_only": (sim_b or {}).get("maintenance_margin"),
        "mm_with_protection": (sim_c or {}).get("maintenance_margin"),
        "available_funds_b": (sim_b or {}).get("available_funds"),
        "available_funds_c": (sim_c or {}).get("available_funds"),
    })
    return rep


def spm_evaluate_candidates(currency, short_instrument, prot_candidates, amount,
                            min_ratio):
    """按顺序模拟保护腿候选（已按「锚点→逐档靠近 short」排序），
    返回第一个 relief_ratio >= min_ratio 的报告（含 accepted=True）；
    全不达标则返回最后一次尝试 + accepted=False。attempts 记录全过程。"""
    attempts = []
    best = None
    for prot in prot_candidates:
        inst = prot.get("instrument_name") if isinstance(prot, dict) else prot
        rep = spm_simulate_structure(currency, short_instrument, inst, amount)
        attempts.append(rep)
        ratio = rep.get("relief_ratio")
        if ratio is not None and (best is None or ratio > (best.get("relief_ratio") or -1)):
            best = rep
        if ratio is not None and ratio >= min_ratio:
            rep["accepted"] = True
            rep["attempts"] = attempts
            return rep
    if best is None:
        best = {"accepted": False, "attempts": attempts, "relief_ratio": None}
    else:
        best = dict(best)
        best["accepted"] = False
    best["attempts"] = attempts
    return best

# ===================== module: hedge =====================
# -*- coding: utf-8 -*-
"""BTC-PERPETUAL 对冲生命周期（hedge_*）。纯函数，便于单测。

对冲场所由操作者显式配置：
  - 默认 BINANCE BTCUSDC 永续（线性），Deribit BTC-PERPETUAL 仅作兼容；
  - 风险触发对冲使用 PROMPT_LIMIT，不由场所 maker 偏好覆盖；
  - 目标数量随**剩余卖方期权敞口**变化；短腿归零 / 结构 CLOSED|SETTLED → 目标立即归零（不等保护腿）；
  - **HEDGE_OPEN/INCREASE 非 reduce_only**（reduce_only 无法建仓）；HEDGE_REDUCE/UNWIND 强制 reduce_only；
  - 期权卖方风险消失但 perp 仍有持仓 → 孤儿对冲紧急态（持续 reduce_only 清理，会话不得 CLOSED）。
  - 换算：DERIBIT 反向(USD 合约)=delta_btc·spot/contract_size；BINANCE 线性(BTC)=delta_btc。
"""
HEDGE_INSTRUMENT = "BTC-PERPETUAL"
HEDGE_VENUE = "BINANCE"

VENUE_DERIBIT = "DERIBIT"
VENUE_BINANCE = "BINANCE"

_EPS = 1e-9


def hedge_venue_config(venue=None, binance_instrument="BTCUSDC", exchange_index=1):
    """返回场所配置 {venue, instrument, linear, exchange_index?}。
    对冲执行方式由 exec_hedge_step 的 execution_style 决定，不在场所配置里夹 maker-only。"""
    if str(venue or VENUE_BINANCE).upper() == VENUE_BINANCE:
        return {"venue": VENUE_BINANCE, "instrument": binance_instrument,
                "linear": True, "exchange_index": exchange_index}
    return {"venue": VENUE_DERIBIT, "instrument": HEDGE_INSTRUMENT,
            "linear": False}


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def hedge_side(side):
    """SHORT_CALL 风险上升(delta 正) → BUY BTC-PERP；SHORT_PUT → SELL。"""
    s = str(side or "").upper()
    if s in ("CALL", "SHORT_CALL"):
        return "buy"
    if s in ("PUT", "SHORT_PUT"):
        return "sell"
    return None


def structure_net_delta(short_delta, protection_delta):
    """结构净 delta（每单位）= 短腿 delta − 保护腿 delta（P1）。
    短腿与保护腿同类型(同 call/put)、保护腿为多头 → 部分抵消短腿敞口，对冲应按净敞口而非仅短腿。
    保护腿 delta 缺失 → 退化为短腿 delta（保守：过对冲优于欠对冲）；短腿缺失 → None。"""
    if not _is_num(short_delta):
        return None
    if not _is_num(protection_delta):
        return short_delta
    return short_delta - protection_delta


def option_net_delta(remaining_short_qty, short_delta, long_remaining_qty=0.0,
                     protection_delta=None):
    """当前期权组合净 delta(BTC)：短腿卖出取负，保护腿买入取正。"""
    if not _is_num(short_delta):
        return None
    short_qty = remaining_short_qty or 0.0
    long_qty = long_remaining_qty or 0.0
    net = -short_qty * short_delta
    if _is_num(protection_delta):
        net += long_qty * protection_delta
    return net


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def hedge_gamma_fraction(short_gamma, long_gamma, remaining_short_qty,
                         long_remaining_qty, spot, ref, floor):
    """Gamma-aware SOFT hedge fraction.

    Missing gamma falls back to floor instead of zero; protection gamma offsets
    short gamma by current remaining leg quantities.
    """
    fl = _clamp(float(floor or 0.0), 0.0, 1.0)
    if not _is_num(spot) or spot <= 0 or not _is_num(ref) or ref <= 0:
        return fl
    combo_gamma = 0.0
    has_gamma = False
    if _is_num(short_gamma):
        combo_gamma += -(remaining_short_qty or 0.0) * short_gamma
        has_gamma = True
    if _is_num(long_gamma):
        combo_gamma += (long_remaining_qty or 0.0) * long_gamma
        has_gamma = True
    if not has_gamma:
        return fl
    dollar_gamma = abs(combo_gamma) * spot * spot
    norm = _clamp(dollar_gamma / ref, 0.0, 1.0)
    return _clamp(fl + (1.0 - fl) * norm, fl, 1.0)


def hedge_rebalance_deadband(full_target, min_trade, band_frac):
    min_qty = max(0.0, min_trade or 0.0)
    frac = max(0.0, band_frac or 0.0)
    return max(min_qty, abs(full_target or 0.0) * frac)


def hedge_target_ratio_for_soft(base_ratio, gamma_fraction, persisted=False, worsened=False):
    if persisted or worsened:
        return 1.0
    base = _clamp(base_ratio or 0.0, 0.0, 1.0)
    gamma = _clamp(gamma_fraction or 0.0, 0.0, 1.0)
    return max(base, gamma)


def _round_abs_to_step(value, step):
    if not step or step <= 0:
        return value
    sign = -1.0 if value < 0 else 1.0
    units = abs(value) / step
    rounded_units = int(units + 0.5 + 1e-12)
    return sign * rounded_units * step


def hedge_target_position(net_option_delta, reduction_ratio, spot, contract_size,
                          min_trade_amount, linear=False):
    """把期权净 delta 转为目标 hedge 仓位（带方向）。
    线性 Binance：BTC 数量；反向 Deribit：USD 合约数。"""
    if not _is_num(net_option_delta):
        return 0.0
    target_delta = -net_option_delta * (reduction_ratio or 1.0)
    if linear:
        raw = target_delta
    else:
        if not (_is_num(spot) and _is_num(contract_size)) or contract_size <= 0:
            return 0.0
        raw = target_delta * spot / contract_size
    return _round_abs_to_step(raw, min_trade_amount)


def hedge_direction_consistent(side, struct_net_delta):
    """方向符号核对（P1）：卖方腿为空头 → 结构 position delta = −struct_net_delta。
    SHORT_CALL（应 buy）要求 position delta ≤ 0；SHORT_PUT（应 sell）要求 ≥ 0。
    数据缺失 / 净敞口≈0 / 无对冲方向 → True（缺 greeks 不阻断既有逻辑，仅用于挡反向加仓）。"""
    h = hedge_side(side)
    if h is None or not _is_num(struct_net_delta) or abs(struct_net_delta) <= _EPS:
        return True
    position_delta = -struct_net_delta
    if h == "buy":
        return position_delta <= _EPS
    return position_delta >= -_EPS


def hedge_target_contracts(remaining_short_qty, structure_delta, reduction_ratio,
                           spot, contract_size, min_trade_amount,
                           option_structure_state="OPEN", linear=False):
    """对冲目标数量。硬不变量：短腿归零 或 结构 CLOSED/SETTLED → 0（不等保护腿出售）。
    linear=False(Deribit 反向)：USD 合约 = |rem·delta·ratio|·spot / contract_size；
    linear=True (Binance 线性)：BTC 数量 = |rem·delta·ratio|。结果取整到 min_trade。"""
    if str(option_structure_state).upper() in ("CLOSED", "SETTLED"):
        return 0.0
    if not remaining_short_qty or remaining_short_qty <= _EPS:
        return 0.0
    if not _is_num(structure_delta):
        return 0.0
    delta_btc = abs(remaining_short_qty * structure_delta * (reduction_ratio or 1.0))
    if linear:
        raw = delta_btc
    else:
        if not (_is_num(spot) and _is_num(contract_size)) or contract_size <= 0:
            return 0.0
        raw = delta_btc * spot / contract_size
    if min_trade_amount and min_trade_amount > 0:
        return round(raw / min_trade_amount) * min_trade_amount
    return raw


def hedge_order_action(current_qty, target_qty, min_trade_amount=0.0):
    """据当前 vs 目标决定动作 + reduce_only（P0-5）。
    目标>当前 → HEDGE_OPEN/INCREASE(非 reduce_only)；目标<当前 → HEDGE_REDUCE/UNWIND(reduce_only)。"""
    cur = current_qty or 0.0
    tgt = target_qty or 0.0
    thr = max(_EPS, (min_trade_amount or 0.0) * 0.5)
    if abs(tgt - cur) <= thr:
        return {"action": "HEDGE_HOLD", "reduce_only": False, "delta_contracts": 0.0}
    if abs(cur) > thr and abs(tgt) > thr and cur * tgt < 0:
        return {"action": "HEDGE_UNWIND", "reduce_only": True,
                "delta_contracts": abs(cur)}
    if abs(tgt) <= thr:
        return {"action": "HEDGE_UNWIND", "reduce_only": True,
                "delta_contracts": abs(cur)}
    if abs(cur) <= thr:
        return {"action": "HEDGE_OPEN", "reduce_only": False,
                "delta_contracts": abs(tgt)}
    if abs(tgt) > abs(cur):
        return {"action": "HEDGE_INCREASE", "reduce_only": False,
                "delta_contracts": abs(tgt - cur)}
    return {"action": "HEDGE_REDUCE", "reduce_only": True,
            "delta_contracts": abs(tgt - cur)}


def hedge_orphan(option_short_qty, perp_qty):
    """期权卖方风险已消失(short<=0) 但 perp 仍有持仓 → 孤儿对冲（须 reduce_only 清理）。"""
    return (not option_short_qty or option_short_qty <= _EPS) and abs(perp_qty or 0.0) > _EPS


def settlement_guard(remaining_short_qty, near_expiry, settled, perp_qty):
    """到期/交割保护：已交割 → 目标强制 0（perp 未归零即孤儿）；临近到期 → 不新增、随剩余短腿归零。"""
    if settled:
        return {"target": 0.0, "orphan": abs(perp_qty or 0.0) > _EPS, "reason": "SETTLED_FORCE_ZERO"}
    if near_expiry:
        flat = (not remaining_short_qty or remaining_short_qty <= _EPS)
        return {"target": (0.0 if flat else None), "orphan": False,
                "reason": "NEAR_EXPIRY_NO_NEW_HEDGE"}
    return {"target": None, "orphan": False, "reason": "NORMAL"}

# ===================== module: execution =====================
# -*- coding: utf-8 -*-
"""
执行层（exec_*，§10）：保护腿优先、短腿 maker-only、末日保护腿受控 taker 兜底。

价格计算为纯函数（可单测）；下单/轮询/撤单走 dbt_*。
进场门控经 gates.gate_decision(ENTRY)：ALLOW_ENTRY_TRADING=False（或 KILL_NEW_RISK /
EMERGENCY_REDUCE_ONLY）时，进场真实下单短路为「记录意图」（空跑核对）。
"""

import math



# ---------- 纯价格计算（§10.3）----------

def _round_to_tick(price, tick, mode):
    if not tick:
        return price
    n = price / tick
    # 加微小 epsilon 抵消浮点误差（如 0.0013-0.0001 落在 0.00119999…，floor 会误降一格）
    n = math.floor(n + 1e-9) if mode == "down" else math.ceil(n - 1e-9)
    return round(n * tick, 10)


def _float_or_none(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def exec_effective_tick(meta, price):
    tick = _float_or_none((meta or {}).get("tick_size")) or 0.0
    pval = _float_or_none(price)
    for st in ((meta or {}).get("tick_size_steps") or []):
        above = _float_or_none((st or {}).get("above_price"))
        step = _float_or_none((st or {}).get("tick_size"))
        if pval is not None and above is not None and step and pval >= above:
            tick = step
    return tick


def exec_round_order_price(side, price, meta, tick=None):
    eff_tick = exec_effective_tick(meta, price) or tick or 0.0
    mode = "down" if side == "buy" else "up"
    return _round_to_tick(price, eff_tick, mode)


def exec_round_taker_price(side, price, meta, tick=None):
    eff_tick = exec_effective_tick(meta, price) or tick or 0.0
    mode = "up" if side == "buy" else "down"
    return _round_to_tick(price, eff_tick, mode)


def exec_buy_price(mark, best_ask, tick, step, meta=None):
    """买 protection：step0=min(mark,ask-tick)；每追一步 +tick，封顶 ask-tick。"""
    cap = best_ask - tick
    base = min(mark, cap)
    p = base + step * tick
    return exec_round_order_price("buy", min(p, cap), meta, tick)


def exec_sell_price(mark, best_bid, tick, step, meta=None):
    """卖 short：step0=max(mark,bid+tick)；每追一步 -tick，封底 bid+tick。"""
    floor_p = best_bid + tick
    base = max(mark, floor_p)
    p = base - step * tick
    return exec_round_order_price("sell", max(p, floor_p), meta, tick)


def exec_protection_maker_price(mark, best_bid, best_ask, tick, meta=None):
    """买保护腿：挂标记价；若 mark 触及卖一，则压到 ask-tick 保持 maker。"""
    cap = best_ask - tick if tick else best_ask
    return exec_round_order_price("buy", min(mark, cap), meta, tick)


def exec_price_for(side, mark, best_bid, best_ask, tick, step, meta=None):
    return (exec_buy_price(mark, best_ask, tick, step, meta) if side == "buy"
            else exec_sell_price(mark, best_bid, tick, step, meta))


# ---------- 行情快照 ----------

def exec_quote(instrument):
    """返回 {mark, best_bid, best_ask, tick} 或 None。"""
    t = dbt_ticker(instrument)
    meta = dbt_get_instrument(instrument)
    if not t or not meta:
        return None
    mark = t.get("mark_price")
    return {
        "mark": mark,
        "mark_iv": t.get("mark_iv"),
        "best_bid": t.get("best_bid_price"),
        "best_ask": t.get("best_ask_price"),
        "best_bid_amount": t.get("best_bid_amount"),
        "best_ask_amount": t.get("best_ask_amount"),
        "tick": exec_effective_tick(meta, mark),
        "meta": meta,
        "underlying": t.get("underlying_price"),
        "delta": (t.get("greeks") or {}).get("delta"),
        "gamma": (t.get("greeks") or {}).get("gamma"),
        "vega": (t.get("greeks") or {}).get("vega"),
    }


def exec_spread_ratio(q):
    """相对价差 (ask-bid)/mid；缺数据返回 None。"""
    if not q:
        return None
    bid, ask = q.get("best_bid"), q.get("best_ask")
    if bid is None or ask is None or bid <= 0 or ask <= 0:
        return None
    mid = (bid + ask) / 2.0
    return (ask - bid) / mid if mid > 0 else None


def exec_plan_prices(side, instrument, amount):
    """返回该腿的下单意图：计划价(含追价档)+盘口，供「将下达订单」意图表展示。"""
    q = exec_quote(instrument)
    if not q or q.get("best_bid") is None or q.get("best_ask") is None:
        return {"instrument": instrument, "side": side, "amount": amount, "prices": [], "quote": q}
    if side == "buy":
        prices = [exec_protection_maker_price(
            q["mark"], q["best_bid"], q["best_ask"], q["tick"], q.get("meta"))]
    else:
        prices = [exec_price_for(side, q["mark"], q["best_bid"], q["best_ask"], q["tick"], s, q.get("meta"))
                  for s in range(MAX_CHASE_STEPS + 1)]
    return {"instrument": instrument, "side": side, "amount": amount, "prices": prices,
            "mark": q.get("mark"), "best_bid": q.get("best_bid"), "best_ask": q.get("best_ask"),
            "spread_ratio": exec_spread_ratio(q)}


def _extract_order(resp):
    if not resp:
        return None
    return resp.get("order") if isinstance(resp, dict) and "order" in resp else resp


def _exec_num(v):
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _order_fee(order):
    if not isinstance(order, dict):
        return None
    for k in ("commission", "fee", "fees", "Fee", "Commission"):
        v = _exec_num(order.get(k))
        if v is not None:
            return float(v)
    return None


def _execution_detail(leg, side, instrument, amount, intended_price, final_price,
                      filled, avg_price, order_id, quote, cancelled=False,
                      remaining=None, order=None, taker=False):
    filled = filled or 0.0
    avg_price = avg_price if avg_price is not None else final_price
    q = quote or {}
    fee_actual = _order_fee(order)
    fee_est = acct_option_fee_ccy(avg_price or 0.0, filled) if filled > 0 else 0.0
    spread = acct_spread_cost(q.get("best_bid"), q.get("best_ask"), filled)
    mark_slip = (acct_mark_slippage(side, avg_price, q.get("mark"), filled)
                 if filled > 0 and avg_price is not None and q.get("mark") is not None else None)
    chase = (acct_chase_cost(side, intended_price, avg_price, filled)
             if filled > 0 and intended_price is not None and avg_price is not None else None)
    return {
        "leg": leg, "side": side, "instrument": instrument,
        "amount": amount, "filled": filled,
        "intended_price": intended_price, "final_price": final_price,
        "avg_price": avg_price, "order_id": order_id,
        "remaining": max(0.0, (amount or 0.0) - filled) if remaining is None else remaining,
        "cancelled": bool(cancelled),
        "taker": bool(taker),
        "quote_mark": q.get("mark"), "quote_bid": q.get("best_bid"),
        "quote_ask": q.get("best_ask"), "quote_tick": q.get("tick"),
        "spread_cost_estimate": spread,
        "mark_slippage": mark_slip,
        "chase_slippage": chase,
        "fee_actual": fee_actual,
        "fee_estimate": fee_est,
        "fee_used": fee_actual if fee_actual is not None else fee_est,
    }


# ---------- maker-only 成交（只追一步）----------

def exec_maker_only_fill(side, instrument, target_amount, label=None):
    """返回 dict：
       {filled, avg_price, price0, final_price, dry, steps_used, quote}
    空跑(dry)时只计算并记录意图，不下单（filled=0, dry=True）。"""
    q = exec_quote(instrument)
    if not q or q["best_bid"] is None or q["best_ask"] is None:
        Log("[exec] 盘口缺失，跳过:", instrument)
        return {"filled": 0.0, "dry": False, "quote": q, "reason": "NO_QUOTE"}

    price0 = exec_price_for(side, q["mark"], q["best_bid"], q["best_ask"], q["tick"], 0, q.get("meta"))
    # 进场门控（ENTRY）：exec_open_structure 为唯一调用方；退出/对冲执行器后续各自传专属门控
    gates = effective_trading_gates(RUN_PROFILE, ALLOW_ENTRY_TRADING, False, False)
    live = gate_decision(ACTION_ENTRY, gates["allow_entry"], False, False,
                         KILL_NEW_RISK, EMERGENCY_REDUCE_ONLY)["allowed"]

    if not live:
        intents = [exec_price_for(side, q["mark"], q["best_bid"], q["best_ask"], q["tick"], s, q.get("meta"))
                   for s in range(MAX_CHASE_STEPS + 1)]
        Log("[exec][DRY] 意图 %s %s amt=%s 计划价(含追价)=%s 盘口=%s/%s mark=%s" %
            (side, instrument, target_amount, intents, q["best_bid"], q["best_ask"], q["mark"]))
        return {"filled": 0.0, "dry": True, "price0": price0,
                "intended_prices": intents, "quote": q}

    # 实盘成交价守门：价差过宽不下单（防高磨损/难成交）
    sr = exec_spread_ratio(q)
    if sr is not None and sr > MAX_SPREAD_RATIO:
        Log("[exec] 价差过宽 %.0f%% > 上限 %.0f%%，放弃下单: %s" %
            (sr * 100, MAX_SPREAD_RATIO * 100, instrument))
        return {"filled": 0.0, "dry": False, "quote": q, "reason": "WIDE_SPREAD"}

    filled = 0.0
    avg_acc = 0.0
    final_price = price0
    steps_used = 0
    for step in range(MAX_CHASE_STEPS + 1):
        remaining = target_amount - filled
        if remaining <= 0:
            break
        price = exec_price_for(side, q["mark"], q["best_bid"], q["best_ask"], q["tick"], step, q.get("meta"))
        final_price = price
        steps_used = step
        resp = dbt_place_order(side, instrument, remaining, price,
                               post_only=True, reject_post_only=True, label=label)
        order = _extract_order(resp)
        if order is None:
            # reject_post_only 拒单（会越价）→ 视为需要追一步
            Log("[exec] 挂单被拒/失败 step=%s price=%s，尝试追价" % (step, price))
            continue
        oid = order.get("order_id")
        # 等待后查状态
        Sleep(int(CHASE_WAIT_SECONDS * 1000))
        st = _extract_order(dbt_get_order_state(oid)) or order
        fa = st.get("filled_amount") or 0.0
        if fa > 0:
            ap = st.get("average_price") or price
            avg_acc += ap * fa
            filled += fa
        state = st.get("order_state")
        if state not in ("filled",) and (target_amount - filled) > 0:
            # 未完全成交 → 撤掉残单，进入下一步追价
            dbt_cancel(oid)
        if filled >= target_amount:
            break

    avg_price = (avg_acc / filled) if filled > 0 else final_price
    return {"filled": filled, "avg_price": avg_price, "price0": price0,
            "final_price": final_price, "dry": False, "steps_used": steps_used,
            "quote": q}


# ---------- 保护腿优先开仓（§10.1）----------

def exec_open_structure(short_instrument, protection_instrument, amount):
    """先买 protection，再以 min(amount, 已成交保护量) 卖 short。
    返回 {protection_fill, short_fill, short_amount}。
    空跑下两腿都只记录意图。"""
    prot = exec_maker_only_fill("buy", protection_instrument, amount,
                                label="prot")
    if prot.get("dry"):
        short = exec_maker_only_fill("sell", short_instrument, amount, label="short")
        return {"protection_fill": prot, "short_fill": short, "short_amount": amount,
                "dry": True}

    filled_prot = prot.get("filled", 0.0)
    if filled_prot <= 0:
        Log("[exec] 保护腿未成交，按保护腿优先原则不卖 short")
        return {"protection_fill": prot, "short_fill": None, "short_amount": 0.0,
                "dry": False}

    short_amount = min(amount, filled_prot)   # 硬保证 short <= protection 可用量
    short = exec_maker_only_fill("sell", short_instrument, short_amount, label="short")
    return {"protection_fill": prot, "short_fill": short,
            "short_amount": short_amount, "dry": False}


# ---------- 开仓活动（entry campaign）：跨轮持久 maker、信用底线约束、保护腿先成交 ----------

def _post_maker_once(side, instrument, amount, price, label, meta=None, quote=None, leg=None,
                     wait_seconds=None):
    """单次 post-only 挂单(给定价)，等一周期，查成交，撤未成交后再查捕捉晚到成交。返回 filled。"""
    if not amount or amount <= 0 or price is None or price <= 0:
        return _execution_detail(leg or label, side, instrument, amount, price, price,
                                 0.0, None, None, quote)
    intended_price = price
    meta = meta or dbt_get_instrument(instrument) or {}
    rounded = exec_round_order_price(side, price, meta)
    if rounded != price:
        Log("[exec][round] leg=%s raw_price=%s rounded_price=%s tick=%s" %
            (side, price, rounded, exec_effective_tick(meta, price)))
        price = rounded
    resp = dbt_place_order(side, instrument, amount, price,
                           post_only=True, reject_post_only=True, label=label)
    order = _extract_order(resp)
    if order is None:
        return _execution_detail(leg or label, side, instrument, amount,
                                 intended_price, price, 0.0, None, None, quote)
    oid = order.get("order_id")
    wait_s = CHASE_WAIT_SECONDS if wait_seconds is None else wait_seconds
    Sleep(int(wait_s * 1000))
    st = _extract_order(dbt_get_order_state(oid)) or order
    filled = st.get("filled_amount") or 0.0
    avg = st.get("average_price") or price
    cancelled = False
    if st.get("order_state") not in ("filled",) and (amount - filled) > 0:
        dbt_cancel(oid)
        cancelled = True
        st2 = _extract_order(dbt_get_order_state(oid)) or st
        if (st2.get("filled_amount") or 0.0) > filled:
            filled = st2.get("filled_amount")
            avg = st2.get("average_price") or avg
            st = st2
    return _execution_detail(leg or label, side, instrument, amount,
                              intended_price, price, filled, avg, oid, quote,
                              cancelled=cancelled, order=st)


def _post_taker_once(side, instrument, amount, price, label, meta=None, quote=None, leg=None):
    if not amount or amount <= 0 or price is None or price <= 0:
        return _execution_detail(leg or label, side, instrument, amount, price, price,
                                 0.0, None, None, quote, taker=True)
    intended_price = price
    meta = meta or dbt_get_instrument(instrument) or {}
    price = exec_round_taker_price(side, price, meta)
    resp = dbt_place_order(side, instrument, amount, price,
                           post_only=False, reject_post_only=False, label=label)
    order = _extract_order(resp)
    if order is None:
        return _execution_detail(leg or label, side, instrument, amount,
                                 intended_price, price, 0.0, None, None, quote,
                                 taker=True)
    oid = order.get("order_id")
    Sleep(1000)
    st = _extract_order(dbt_get_order_state(oid)) or order
    filled = st.get("filled_amount") or 0.0
    avg = st.get("average_price") or price
    cancelled = False
    if st.get("order_state") not in ("filled",) and (amount - filled) > 0:
        dbt_cancel(oid)
        cancelled = True
        st2 = _extract_order(dbt_get_order_state(oid)) or st
        if (st2.get("filled_amount") or 0.0) > filled:
            filled = st2.get("filled_amount")
            avg = st2.get("average_price") or avg
            st = st2
    return _execution_detail(leg or label, side, instrument, amount,
                             intended_price, price, filled, avg, oid, quote,
                             cancelled=cancelled, order=st, taker=True)


def _level_amount(level):
    if isinstance(level, (list, tuple)) and len(level) >= 2:
        return _float_or_none(level[1])
    if isinstance(level, dict):
        for k in ("amount", "quantity", "size"):
            v = _float_or_none(level.get(k))
            if v is not None:
                return v
    return None


def _best_ask_depth(instrument, quote=None):
    q = quote or {}
    amount = _float_or_none(q.get("best_ask_amount"))
    if amount is not None:
        return amount
    book = dbt_order_book(instrument, depth=1)
    asks = (book or {}).get("asks") or []
    return _level_amount(asks[0]) if asks else None


def _entry_order_state(order_id):
    try:
        return _extract_order(dbt_get_order_state(order_id))
    except Exception:
        return None


def _entry_filled_amount(order):
    return _float_or_none((order or {}).get("filled_amount")) or 0.0


def _entry_order_closed(order, target_amount=None):
    if not order:
        return False
    state = order.get("order_state")
    filled = _entry_filled_amount(order)
    if state in ("filled", "cancelled", "rejected"):
        return True
    return target_amount is not None and filled >= target_amount - 1e-12


def _protection_order_record(order, instrument, amount, price, now_ms, wait_start_ms, label):
    oid = (order or {}).get("order_id")
    if not oid:
        return None
    return {
        "order_id": oid,
        "instrument": instrument,
        "price": price,
        "amount": amount,
        "filled_seen": _entry_filled_amount(order),
        "placed_ms": now_ms,
        "wait_start_ms": wait_start_ms,
        "label": label,
    }


def _post_protection_maker(instrument, amount, price, quote, label, meta, now_ms, wait_start_ms):
    if not amount or amount <= 0 or price is None or price <= 0:
        detail = _execution_detail("protection", "buy", instrument, amount, price, price,
                                   0.0, None, None, quote)
        detail["prot_order"] = None
        return detail
    resp = dbt_place_order("buy", instrument, amount, price,
                           post_only=True, reject_post_only=True, label=label)
    order = _extract_order(resp)
    detail = _execution_detail("protection", "buy", instrument, amount,
                               price, price, 0.0, None,
                               (order or {}).get("order_id"), quote, order=order)
    detail["prot_order"] = _protection_order_record(
        order, instrument, amount, price, now_ms, wait_start_ms, label)
    return detail


def _post_entry_protection_once(instrument, amount, maker_price, quote, attempt,
                                short_price, fees, credit_floor, label, meta=None,
                                prot_order=None, now_ms=None):
    q = quote or {}
    ask = q.get("best_ask")
    now_ms = now_ms or 0
    meta = meta or {}
    active = dict(prot_order or {})
    wait_start_ms = active.get("wait_start_ms") or now_ms
    remaining = amount
    filled_delta = 0.0
    avg_price = None

    if active.get("order_id"):
        st = _entry_order_state(active.get("order_id"))
        if st is None:
            detail = _execution_detail("protection", "buy", instrument, amount,
                                       active.get("price"), active.get("price"),
                                       0.0, None, active.get("order_id"), q)
            detail["prot_order"] = active
            detail["reason"] = "PROTECTION_ORDER_STATE_UNKNOWN"
            detail["active_order_only"] = True
            return detail
        total_filled = _entry_filled_amount(st)
        seen = active.get("filled_seen") or 0.0
        filled_delta = max(0.0, total_filled - seen)
        avg_price = st.get("average_price") or active.get("price")
        active["filled_seen"] = max(seen, total_filled)
        remaining = max(0.0, amount - filled_delta)
        if remaining <= 1e-12 or _entry_order_closed(st, active.get("amount")):
            detail = _execution_detail("protection", "buy", instrument, amount,
                                       active.get("price"), active.get("price"),
                                       filled_delta, avg_price,
                                       active.get("order_id"), q, order=st)
            detail["prot_order"] = None
            return detail

        elapsed_ms = now_ms - wait_start_ms if now_ms else 0
        target_changed = abs((active.get("price") or 0.0) - (maker_price or 0.0)) >= ((q.get("tick") or 0.0) - 1e-12)
        taker_due = elapsed_ms >= ENTRY_PROTECTION_TAKER_AFTER_SECONDS * 1000
        if not target_changed and not taker_due:
            detail = _execution_detail("protection", "buy", instrument, amount,
                                       active.get("price"), active.get("price"),
                                       filled_delta, avg_price,
                                       active.get("order_id"), q, order=st)
            detail["prot_order"] = active
            if filled_delta <= 0:
                detail["active_order_only"] = True
            return detail

        dbt_cancel(active.get("order_id"))
        st2 = _entry_order_state(active.get("order_id")) or st
        total2 = _entry_filled_amount(st2)
        if total2 > active.get("filled_seen", 0.0):
            late_delta = total2 - active.get("filled_seen", 0.0)
            filled_delta += late_delta
            active["filled_seen"] = total2
            avg_price = st2.get("average_price") or avg_price
            remaining = max(0.0, amount - filled_delta)
        if remaining <= 1e-12:
            detail = _execution_detail("protection", "buy", instrument, amount,
                                       active.get("price"), active.get("price"),
                                       filled_delta, avg_price,
                                       active.get("order_id"), q,
                                       cancelled=True, order=st2)
            detail["prot_order"] = None
            return detail

        if taker_due:
            ask_depth = _best_ask_depth(instrument, q)
            depth_ok = ask_depth is not None and ask_depth + 1e-12 >= remaining
            credit_ok = (ask is not None
                         and entry_net_credit(short_price, ask, remaining, fees) >= credit_floor)
            if ask is not None and depth_ok and credit_ok:
                taker = _post_taker_once("buy", instrument, remaining, ask,
                                         label + "_taker", meta, quote=q, leg="protection")
                taker_fill = taker.get("filled") or 0.0
                total_fill = filled_delta + taker_fill
                detail = _execution_detail("protection", "buy", instrument, amount,
                                           active.get("price"), taker.get("final_price") or ask,
                                           total_fill, taker.get("avg_price") or avg_price,
                                           taker.get("order_id"), q,
                                           cancelled=True, order=taker, taker=True)
                detail["prot_order"] = None
                detail["reason"] = "PROTECTION_TAKER_AFTER_WAIT"
                return detail
            Log("[entry][prot] taker_after_wait hold ask=%s depth=%s remaining=%s credit_ok=%s" %
                (ask, ask_depth, remaining, credit_ok))

        maker = _post_protection_maker(instrument, remaining, maker_price, q, label,
                                       meta, now_ms, wait_start_ms)
        maker["filled"] = filled_delta
        maker["avg_price"] = avg_price or maker.get("avg_price")
        return maker

    return _post_protection_maker(instrument, amount, maker_price, q, label,
                                  meta, now_ms, wait_start_ms)


def exec_entry_campaign_step(prot_inst, short_inst, amount, credit_floor, max_tick_steps,
                             attempt, prot_done_qty, short_done_qty, allow_live, label="entry",
                             prot_order=None, now_ms=None):
    """开仓活动一轮：保护腿先成交，价格在「净 credit ≥ credit_floor」内逐 tick 改善(本轮档=min(attempt,信用上限档))。
    跨轮持久（每轮一次 post-only）。allow_live=False → 仅意图(dry)。
    返回 {quotes_ok, credit_ok, dry, prot_price, short_price, net_credit, n_used, prot_fill, short_fill, reason}。"""
    pq, sq = exec_quote(prot_inst), exec_quote(short_inst)
    quotes_ok = bool(pq and sq and pq.get("mark") is not None and sq.get("mark") is not None
                     and pq.get("best_ask") is not None and pq.get("best_bid") not in (None, 0)
                     and sq.get("best_bid") not in (None, 0) and sq.get("best_ask") is not None)
    if not quotes_ok:
        return {"quotes_ok": False, "credit_ok": False, "dry": (not allow_live),
                "prot_fill": 0.0, "short_fill": 0.0, "reason": "NO_QUOTE"}
    steps = max(0, int(max_tick_steps))
    prot_maker_price = exec_protection_maker_price(
        pq["mark"], pq["best_bid"], pq["best_ask"], pq["tick"], pq.get("meta"))
    prot_buy_prices = [prot_maker_price for _n in range(steps + 1)]
    short_sell_prices = [exec_sell_price(sq["mark"], sq["best_bid"], sq["tick"], n, sq.get("meta"))
                         for n in range(steps + 1)]
    fees = acct_option_fee_ccy(pq["mark"], amount) + acct_option_fee_ccy(sq["mark"], amount)
    i_cap = entry_credit_capped_index(prot_buy_prices, short_sell_prices, amount, fees, credit_floor)
    if i_cap < 0:
        nc0 = entry_net_credit(short_sell_prices[0], prot_buy_prices[0], amount, fees)
        return {"quotes_ok": True, "credit_ok": False, "dry": (not allow_live), "net_credit": nc0,
                "prot_fill": 0.0, "short_fill": 0.0, "reason": "BELOW_CREDIT_FLOOR"}
    n = min(max(0, int(attempt)), i_cap)
    prot_price, short_price = prot_buy_prices[n], short_sell_prices[n]
    net_credit = entry_net_credit(short_price, prot_price, amount, fees)
    if not allow_live:
        return {"quotes_ok": True, "credit_ok": True, "dry": True, "prot_price": prot_price,
                "short_price": short_price, "net_credit": net_credit, "n_used": n,
                "prot_fill": 0.0, "short_fill": 0.0, "reason": "ENTRY_DRYRUN"}
    prot_detail = _execution_detail("protection", "buy", prot_inst, 0.0,
                                    prot_price, prot_price, 0.0, None, None, pq)
    prot_detail["prot_order"] = None
    if (prot_done_qty or 0.0) < amount - 1e-12:                 # 保护腿先成交（持久重挂）
        prot_detail = _post_entry_protection_once(
            prot_inst, amount - (prot_done_qty or 0.0), prot_price, pq, attempt,
            short_price, fees, credit_floor, label + "_prot", pq.get("meta"),
            prot_order=prot_order, now_ms=now_ms)
    prot_fill = prot_detail.get("filled") or 0.0
    short_cap = min(amount, (prot_done_qty or 0.0) + prot_fill) - (short_done_qty or 0.0)
    short_detail = _execution_detail("short", "sell", short_inst, 0.0,
                                     short_price, short_price, 0.0, None, None, sq)
    if short_cap > 1e-12:                                       # 短腿数量 ≤ 已成交保护腿量
        short_detail = _post_maker_once("sell", short_inst, short_cap, short_price,
                                        label + "_short", sq.get("meta"),
                                        quote=sq, leg="short",
                                        wait_seconds=ENTRY_SHORT_ORDER_WAIT_SECONDS)
    short_fill = short_detail.get("filled") or 0.0
    fills = [d for d in (prot_detail, short_detail)
             if (d.get("filled") or 0.0) > 0
             or (d.get("order_id") and not d.get("active_order_only"))]
    prot_avg = prot_detail.get("avg_price") if prot_fill > 0 else None
    short_avg = short_detail.get("avg_price") if short_fill > 0 else None
    fee_used = sum((d.get("fee_used") or 0.0) for d in fills)
    actual_before = ((short_avg or 0.0) * short_fill
                     - (prot_avg or 0.0) * prot_fill)
    actual_after = actual_before - fee_used
    return {"quotes_ok": True, "credit_ok": True, "dry": False, "prot_price": prot_price,
            "short_price": short_price, "net_credit": net_credit, "n_used": n,
            "prot_fill": prot_fill, "short_fill": short_fill,
            "prot_avg_price": prot_avg, "short_avg_price": short_avg,
            "prot_order": prot_detail.get("prot_order"),
            "entry_fees": fee_used,
            "actual_net_credit_before_fees": actual_before,
            "actual_net_credit_after_fees": actual_after,
            "fills": fills, "reason": "ENTRY_STEP"}


# ---------- 低成本退出：买回卖方短腿（§7.3；每轮一次、价格 ≤ 预算上限、post-only）----------

def exec_exit_buyback_step(short_instrument, target_amount, price_cap, allow_live,
                           allow_taker=False, label="exit_short", quote=None):
    """退出活动一轮：买回（平）卖方短腿。
    - **止盈退出**(allow_taker=False)：被动 post-only，买价 ≤ min(ask−tick, price_cap)，patient 不越价。
    - **风险退出**(allow_taker=True)：可**越价吃单**至 price_cap（限价=price_cap、非 post-only，
      扫所有 ask ≤ cap 的卖盘、残量挂 cap）；成本仍硬封在 price_cap·qty 内（由风险退出预算反推）。
    allow_live=False → 仅返回意图(dry)。撤未成交单后再查一次以捕捉晚到成交。
    返回 {filled, avg_price, dry, price, taker, reason}。"""
    q = quote if quote is not None else exec_quote(short_instrument)
    if not q or q.get("best_bid") is None or q.get("best_ask") is None or q.get("mark") is None:
        return {"filled": 0.0, "dry": (not allow_live), "reason": "NO_QUOTE"}
    tick = q.get("tick") or 0.0
    if allow_taker:
        price = price_cap                       # 限价=预算上限：≤cap 的卖盘成交、残量挂 cap（成本硬封）
        post_only = False
    else:
        maker_safe = (q["best_ask"] - tick) if tick else q["best_bid"]   # 最高仍为 maker 的买价
        price = min(maker_safe, price_cap)
        post_only = True
    if price <= 0 or price > price_cap + 1e-12:
        return {"filled": 0.0, "dry": (not allow_live), "price": price, "reason": "ABOVE_BUDGET_CAP"}
    if not allow_live:
        return {"filled": 0.0, "dry": True, "price": price, "taker": allow_taker, "reason": "EXIT_DRYRUN"}
    resp = dbt_place_order("buy", short_instrument, target_amount, price,
                           post_only=post_only, reject_post_only=post_only, label=label)
    order = _extract_order(resp)
    if order is None:
        return {"filled": 0.0, "dry": False, "price": price, "taker": allow_taker,
                "reason": ("ORDER_REJECTED" if allow_taker else "POST_ONLY_REJECTED")}
    oid = order.get("order_id")
    Sleep(int(CHASE_WAIT_SECONDS * 1000))
    st = _extract_order(dbt_get_order_state(oid)) or order
    filled = st.get("filled_amount") or 0.0
    avg = st.get("average_price") or price
    cancelled = False
    if st.get("order_state") not in ("filled",) and (target_amount - filled) > 0:
        dbt_cancel(oid)
        cancelled = True
        st2 = _extract_order(dbt_get_order_state(oid)) or st        # 撤单后再查，捕捉晚到成交
        if (st2.get("filled_amount") or 0.0) > filled:
            filled = st2.get("filled_amount")
            avg = st2.get("average_price") or avg
    detail = _execution_detail("exit_short", "buy", short_instrument, target_amount,
                               price, price, filled, avg, oid, q,
                               cancelled=cancelled, order=st, taker=allow_taker)
    return {"filled": filled, "avg_price": avg, "dry": False, "price": price,
            "taker": allow_taker, "reason": "EXIT_STEP", **detail}


# ---------- 保护腿回收（§7.5；短腿归零后 maker 卖出；无 bid → LONG_RESIDUAL_ONLY）----------

def exec_protection_recovery_step(long_inst, qty, allow_live, label="recover_long", quote=None):
    """短腿归零后回收保护腿：被动 maker 卖出(post-only，join bid)；无 bid → LONG_RESIDUAL_ONLY(保持等结算)。
    allow_live=False → 仅意图(dry)。返回 {sold, price, state, dry, reason}。"""
    if not qty or qty <= 0:
        return {"sold": 0.0, "dry": (not allow_live), "state": "COMPLETE", "reason": "NO_LONG"}
    if not long_inst:
        return {"sold": 0.0, "dry": (not allow_live), "state": "LONG_RESIDUAL_ONLY",
                "reason": "NO_LONG_INSTRUMENT"}
    q = quote if quote is not None else exec_quote(long_inst)
    bid = (q or {}).get("best_bid")
    if not q or bid in (None, 0) or bid <= 0:
        return {"sold": 0.0, "dry": (not allow_live), "state": "LONG_RESIDUAL_ONLY", "reason": "NO_BID"}
    price = bid                                    # 被动 maker 卖：join bid（不接受负净回收 → bid>0 已保证）
    if not allow_live:
        return {"sold": 0.0, "dry": True, "price": price, "state": "WORKING_LONG", "reason": "RECOVER_DRYRUN"}
    detail = _post_maker_once("sell", long_inst, qty, price, label, quote=q, leg="recover_long")
    sold = detail.get("filled") or 0.0
    return {"sold": sold, "price": price, "avg_price": detail.get("avg_price"),
            "dry": False, "execution": detail,
            "state": ("COMPLETE" if sold >= qty - 1e-12 else "WORKING_LONG"), "reason": "RECOVER_STEP"}


# ---------- BTC-PERPETUAL 对冲下单（§10.4；REDUCE/UNWIND 强制 reduce_only）----------

def exec_hedge_step(venue_cfg, side, amount, reduce_only, allow_live, label="hedge",
                    execution_style=None, max_slippage_bps=None):
    """对冲一步（场所感知）。OPEN/INCREASE 非 reduce_only；REDUCE/UNWIND 强制 reduce_only。
    venue_cfg: hedge.hedge_venue_config 结果(含 venue/instrument/linear/exchange_index)。
    BINANCE → binance_io(PROMPT_LIMIT/USDC 永续)；DERIBIT → BTC-PERPETUAL。allow_live=False → 仅意图(dry)。"""
    venue_cfg = venue_cfg or {}
    venue = venue_cfg.get("venue")
    instrument = venue_cfg.get("instrument")
    execution_style = execution_style or HEDGE_OPEN_EXECUTION_STYLE
    max_slippage_bps = HEDGE_MAX_SLIPPAGE_BPS if max_slippage_bps is None else max_slippage_bps
    if not side or not amount or amount <= 0:
        return {"filled": 0.0, "dry": (not allow_live), "venue": venue, "reason": "NO_OP"}
    if venue == "BINANCE":
        if not allow_live:
            return {"filled": 0.0, "dry": True, "venue": "BINANCE",
                    "instrument": instrument, "side": side, "amount": amount,
                    "reduce_only": reduce_only, "post_only": False,
                    "execution_style": execution_style,
                    "max_slippage_bps": max_slippage_bps,
                    "reason": "BINANCE_HEDGE_DRYRUN"}
        return {"filled": 0.0, "dry": False, "venue": "BINANCE",
                "instrument": instrument, "side": side, "amount": amount,
                "reduce_only": reduce_only, "post_only": False,
                "execution_style": execution_style, "blocked": True,
                "reason": "HEDGE_POLICY_DISABLED_NO_LEGACY_SUBMIT"}
    return {"filled": 0.0, "dry": (not allow_live), "venue": venue,
            "instrument": instrument, "side": side, "amount": amount,
            "reduce_only": reduce_only, "post_only": False,
            "execution_style": execution_style, "blocked": True,
            "reason": "DERIBIT_HEDGE_LEGACY_UNSUPPORTED"}

# ===================== module: ledger =====================
# -*- coding: utf-8 -*-
"""
库存账本 + 状态机 + 持久化 + 启动对账（§8 / §9）。

库存与状态经 FMZ `_G()` 持久化，崩溃/重启后可恢复。启动时与交易所实际持仓做基础对账，
不一致仅告警，不自动改仓（自动恢复留 v1.1）。
"""


# ---------- 状态机（§9）----------
S_NO_POSITION              = "NO_POSITION"
S_MANUAL_READY             = "MANUAL_READY"
S_PROTECTION_SELECTION     = "PROTECTION_SELECTION"
S_SPM_SIMULATION           = "SPM_SIMULATION"
S_PROTECTION_BUILDING      = "PROTECTION_BUILDING"
S_PROTECTION_ACTIVE_NO_SHORT = "PROTECTION_ACTIVE_NO_SHORT"
S_SHORT_BUILDING           = "SHORT_BUILDING"
S_SHORT_ACTIVE_PROTECTED   = "SHORT_ACTIVE_PROTECTED"
S_HOLD_MONITORING          = "HOLD_MONITORING"
S_SHORT_EXPIRED_OR_CLOSED  = "SHORT_EXPIRED_OR_CLOSED"
S_REUSE_DECISION           = "REUSE_DECISION"
S_EXIT_OR_WAIT_REVIEW      = "EXIT_OR_WAIT_REVIEW"
S_SHORT_FLAT_LONG_RESIDUAL = "SHORT_FLAT_LONG_RESIDUAL"   # 短腿归零、保护腿待回收（不可直跳 CLOSED）
S_CLOSED                   = "CLOSED"

_LEDGER_KEY = "spm_ledger_v1"
_STATE_KEY = "spm_state_v1"

_DEFAULT_LEDGER = {
    "protection": None,   # 单条保护腿库存（v1 限 1 张覆盖 1 张，§8.2）
    "short": None,        # 当前近端 short 腿
    "history": [],        # 已结束结构的记账留档
}


# ---------- 持久化 ----------

def ledger_load():
    led = _G(_LEDGER_KEY)
    if not led:
        led = dict(_DEFAULT_LEDGER)
        led["history"] = []
    return led


def ledger_save(led):
    _G(_LEDGER_KEY, led)
    return led


def ledger_get_state():
    return _G(_STATE_KEY) or S_NO_POSITION


def ledger_set_state(state):
    _G(_STATE_KEY, state)
    Log("[state] ->", state)
    return state


# ---------- 库存记录（§8.1）----------

def ledger_make_inventory(instrument, option_type, strike, expiry,
                          amount, entry_price, entry_fee, margin_relief_ratio):
    return {
        "inventory_id": "prot_" + str(instrument),
        "instrument": instrument,
        "option_type": option_type,
        "strike": strike,
        "expiry": expiry,
        "amount_total": amount,
        "amount_free": amount,
        "amount_allocated": 0.0,
        "entry_price": entry_price,
        "entry_fee": entry_fee,
        "current_mark": entry_price,
        "unrealized_pnl": 0.0,
        "realized_short_premium_against_it": 0.0,
        "reuse_count": 0,
        "last_margin_relief_ratio": margin_relief_ratio,
        "status": "AVAILABLE",
    }


def ledger_allocate_short(led, amount):
    """short 占用保护腿可用量（硬保证 short <= amount_free）。"""
    prot = led.get("protection")
    if not prot:
        return False
    if amount > prot["amount_free"] + 1e-12:
        Log("[ledger] 拒绝：short 数量 %s > 保护腿可用 %s" % (amount, prot["amount_free"]))
        return False
    prot["amount_free"] -= amount
    prot["amount_allocated"] += amount
    return True


def ledger_release_short(led, amount):
    prot = led.get("protection")
    if not prot:
        return
    prot["amount_free"] += amount
    prot["amount_allocated"] = max(0.0, prot["amount_allocated"] - amount)


# ---------- 进场门控（§4.1）----------

def ledger_can_enter(manual_gate_state, enter_manuals):
    return manual_gate_state in enter_manuals


# ---------- 启动对账（§5 缺口补强）----------

def ledger_reconcile(currency, kind="option"):
    """对比 _G 账本与交易所实际期权持仓，不一致告警，不自动改仓。"""
    led = ledger_load()
    positions = dbt_get_positions(currency, kind) or []
    actual = {}
    for p in positions:
        inst = p.get("instrument_name")
        sz = p.get("size")
        if inst and sz:
            actual[inst] = sz

    expected = {}
    prot = led.get("protection")
    if prot and prot.get("status") == "AVAILABLE":
        expected[prot["instrument"]] = prot["amount_total"]
    sh = led.get("short")
    if sh:
        expected[sh["instrument"]] = -sh.get("amount", 0.0)

    for inst, sz in expected.items():
        a = actual.get(inst)
        if a is None:
            Log("[reconcile] 告警：账本有 %s(%s) 但交易所无持仓" % (inst, sz))
        elif abs(a - sz) > 1e-9:
            Log("[reconcile] 告警：%s 账本=%s 实际=%s 不一致" % (inst, sz, a))
    for inst, sz in actual.items():
        if inst not in expected:
            Log("[reconcile] 告警：交易所有持仓 %s(%s) 但账本未记录" % (inst, sz))

    return {"ledger": led, "actual": actual, "expected": expected}


# ---------- 启动恢复裁决（§11.3；纯函数，便于单测）----------

def evaluate_startup_recovery(option_positions, perp_position_qty,
                              ledger_short_qty, active_orders=None, expected_long_qty=0.0):
    """据交易所真实持仓 / 持仓记录(快照) / 活动订单建立可解释映射并裁决：
      RECOVERY_BLOCKED：身份不明活动订单；或记录有卖方短腿但交易所无期权；
        或**交易所有期权持仓但记录无对应持仓**（P0①：防 v3 持仓未被对账/恢复看见）；
      ORPHAN_HEDGE_EMERGENCY：存在 BTC-PERPETUAL 对冲持仓但已无期权卖方风险；
      OK：可解释。allow_new_open 仅 OK 时为真（恢复完成前禁开新仓）。
    ledger_short_qty/expected_long_qty 来自持仓快照（_POSITION_KEY）的剩余短/保护腿。"""
    reasons = []
    active_orders = active_orders or []
    unknown = [o for o in active_orders if not o.get("label")]
    if unknown:
        reasons.append("UNKNOWN_ACTIVE_ORDERS:%d" % len(unknown))
    opt_qty = sum(abs(p.get("size") or 0.0) for p in (option_positions or []))
    ledger_short = abs(ledger_short_qty or 0.0)
    expected_opt = ledger_short + abs(expected_long_qty or 0.0)
    if ledger_short > 1e-9 and opt_qty <= 1e-9:
        reasons.append("RECORD_SHORT_BUT_NO_EXCHANGE_OPTION")
    if opt_qty > 1e-9 and expected_opt <= 1e-9:
        reasons.append("EXCHANGE_OPTION_BUT_NO_RECORDED_POSITION")
    if reasons:
        return {"state": "RECOVERY_BLOCKED", "reasons": reasons, "allow_new_open": False}
    if abs(perp_position_qty or 0.0) > 1e-9 and ledger_short <= 1e-9:
        return {"state": "ORPHAN_HEDGE_EMERGENCY",
                "reasons": ["PERP_HEDGE_WITHOUT_OPTION_SHORT_RISK"], "allow_new_open": False}
    return {"state": "OK", "reasons": [], "allow_new_open": True}

# ===================== module: execution_feasibility =====================
# -*- coding: utf-8 -*-
"""建仓可行性评分（execution_feasibility，纯逻辑）。

回答：当前盘口快照下，该垂直结构是否具备**完整建立所需的经济空间与报价条件**。
**不是 fill_probability**（无历史成交标签）；不读 `_G`、不下单、不改计划/人工审计。
口径与 entry campaign 一致：复用 `execution.exec_buy_price/exec_sell_price` 价格阶梯 +
`position.entry_credit_capped_index/entry_net_credit` 信用底线档；费率收口 accounting。

设计：硬门(Q1-Q6) + 软分(0~100，4 组件加权) + 排序折损(penalty)。阈值由 cfg 注入（集中在 config）。
不变量见规范 §16（EF-01..10）。
"""

SCHEMA_NAME = "ExecutionFeasibilityPackage"
SCHEMA_VERSION = "nrd.execution.feasibility.v1"

GRADE_HIGHLY = "HIGHLY_BUILDABLE"
GRADE_BUILDABLE = "BUILDABLE"
GRADE_PATIENT = "PATIENT_ONLY"
GRADE_FRAGILE = "FRAGILE"
GRADE_REJECT = "REJECT"

# 默认阈值（仅作 cfg 缺省；生产由 config.FEAS_* 注入）
DEFAULT_CFG = {
    "max_short_spread": 0.60, "max_protection_spread": 0.60,
    "protection_low_premium_max": PROTECTION_LOW_PREMIUM_MAX,
    "protection_abs_spread_max": PROTECTION_ABS_SPREAD_MAX,
    "min_net_credit": 0.0, "min_retention": 0.45, "min_survival_ticks": 0,
    "retention_bad": 0.45, "retention_good": 0.90,
    "spread_bad": 0.60, "spread_good": 0.10,
    "friction_bad": 0.60, "friction_good": 0.10,
    "weights": {"credit_retention": 0.30, "spread": 0.25, "friction": 0.25, "credit_survival": 0.20},
}


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _clamp01(v):
    return max(0.0, min(1.0, v))


def safe_spread_ratio(bid, ask):
    """相对价差 (ask-bid)/mid；缺数据/非法(<=0 或 ask<bid) → None。"""
    if not (_is_num(bid) and _is_num(ask)) or bid <= 0 or ask <= 0 or ask < bid:
        return None
    mid = (bid + ask) / 2.0
    return (ask - bid) / mid if mid > 0 else None


def _quote_abs_spread(q):
    bid = (q or {}).get("best_bid")
    ask = (q or {}).get("best_ask")
    if not (_is_num(bid) and _is_num(ask)) or ask < bid:
        return None
    return ask - bid


def _protection_spread_soft_ok(q, ratio, cfg):
    if ratio is not None and ratio <= cfg["max_protection_spread"]:
        return True
    abs_spread = _quote_abs_spread(q)
    ask = (q or {}).get("best_ask")
    return (_is_num(abs_spread) and _is_num(ask)
            and ask <= cfg["protection_low_premium_max"]
            and abs_spread <= cfg["protection_abs_spread_max"] + 1e-12)


def mark_credit_after_fees(short_mark, prot_mark, amount, fees):
    """mark 口径净 credit = (短腿 mark − 保护腿 mark)×数量 − 入场费。"""
    return (short_mark - prot_mark) * amount - (fees or 0.0)


def executable_credit_after_fees(short_bid, prot_ask, amount, fees):
    """可成交保守口径净 credit = (短腿 bid − 保护腿 ask)×数量 − 入场费（建仓更真实）。"""
    return (short_bid - prot_ask) * amount - (fees or 0.0)


def credit_retention_ratio(exec_credit, mark_credit):
    """可成交 credit / mark credit；mark<=0 → None（由硬门拒绝）。"""
    if not _is_num(mark_credit) or mark_credit <= 0:
        return None
    return exec_credit / mark_credit


def entry_friction_estimate(short_mark, short_bid, prot_ask, prot_mark, amount, fees):
    """保守入场摩擦 = [max(0,短腿 mark−bid) + max(0,保护腿 ask−mark)]×数量 + 入场费。
    任一价格偏离为负（异常 mark）按 0 处理，避免负摩擦奖励（EF-06）。"""
    short_slip = max(0.0, (short_mark - short_bid))
    prot_slip = max(0.0, (prot_ask - prot_mark))
    return (short_slip + prot_slip) * amount + (fees or 0.0)


def friction_to_credit_ratio(friction, exec_credit):
    """摩擦 / 可成交 credit；exec_credit<=0 → None（由硬门拒绝）。"""
    if not _is_num(exec_credit) or exec_credit <= 0:
        return None
    return friction / exec_credit


def credit_survival_profile(short_quote, prot_quote, amount, credit_floor, max_tick_steps, fees):
    """追价阶梯上仍满足 credit floor 的最大档（复用 entry campaign 同一阶梯与信用底线档）。
    返回 {credit_survival_ticks, max_tick_steps, credit_survival_ratio, credit_at_last_surviving_step}。
    n_survive=-1 表示第 0 档即低于底线。"""
    steps = max(0, int(max_tick_steps or 0))
    prot_buy = [exec_buy_price(prot_quote["mark"], prot_quote["best_ask"], prot_quote["tick"], n)
                for n in range(steps + 1)]
    short_sell = [exec_sell_price(short_quote["mark"], short_quote["best_bid"], short_quote["tick"], n)
                  for n in range(steps + 1)]
    i_cap = entry_credit_capped_index(prot_buy, short_sell, amount, fees, credit_floor)
    ratio = (i_cap + 1) / float(steps + 1) if i_cap >= 0 else 0.0
    last_credit = (entry_net_credit(short_sell[i_cap], prot_buy[i_cap], amount, fees)
                   if i_cap >= 0 else None)
    return {"credit_survival_ticks": i_cap, "max_tick_steps": steps,
            "credit_survival_ratio": ratio, "credit_at_last_surviving_step": last_credit}


def component_score_linear(value, bad, good):
    """线性归一到 0~100。`(value-bad)/(good-bad)` 自动适配方向：
    good>bad → 越大越好（如 retention）；good<bad → 越小越好（如 spread/friction）。value None → 0。"""
    if not _is_num(value) or bad == good:
        return 0.0
    return _clamp01((value - bad) / (good - bad)) * 100.0


def _grade(score):
    if score >= 85:
        return GRADE_HIGHLY
    if score >= 70:
        return GRADE_BUILDABLE
    if score >= 55:
        return GRADE_PATIENT
    return GRADE_FRAGILE


def _leg_quote_ok(q):
    return bool(q) and all(_is_num(q.get(k)) for k in ("mark", "best_bid", "best_ask", "tick")) \
        and q["best_bid"] > 0 and q["best_ask"] > 0 and q["best_ask"] >= q["best_bid"] and q["tick"] > 0


def _reject(failures, warnings=None):
    return {"schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION, "status": "REJECT",
            "grade": GRADE_REJECT, "score": 0.0, "score_norm": 0.0,
            "hard_gate_passed": False, "hard_failures": list(failures), "warnings": list(warnings or []),
            "economics": {}, "liquidity": {}, "campaign": {}, "components": {},
            "reason_codes": ["EXEC_FEASIBILITY_REJECT"]}


def evaluate_execution_feasibility(inp, cfg=None):
    """输入 {short_quote, protection_quote, amount, credit_floor, max_tick_steps, fee_estimate, now_ms}
    → ExecutionFeasibilityPackage（硬门 + 软分 + 等级）。缺关键报价/越价 → fail-closed(REJECT)。"""
    c = dict(DEFAULT_CFG)
    c.update(cfg or {})
    sq, pq = inp.get("short_quote"), inp.get("protection_quote")
    amount = inp.get("amount") or 0.0
    fees = inp.get("fee_estimate") or 0.0
    credit_floor = inp.get("credit_floor", 0.0)
    max_steps = inp.get("max_tick_steps", 0)

    # Q1/Q2：双腿报价完整 + 盘口合法（缺保护腿 ask 等 → 硬拒，EF-01/EF-07）
    fail = []
    warnings = []
    if not _leg_quote_ok(sq):
        fail.append("SHORT_QUOTE_INCOMPLETE")
    if not _leg_quote_ok(pq):
        fail.append("PROTECTION_QUOTE_INCOMPLETE")
    if fail:
        return _reject(fail)

    # Q3：双腿 spread 不超绝对上限（保护腿同等评估）
    ss = safe_spread_ratio(sq["best_bid"], sq["best_ask"])
    ps = safe_spread_ratio(pq["best_bid"], pq["best_ask"])
    worst = max(ss, ps)
    if ss > c["max_short_spread"]:
        fail.append("SHORT_SPREAD_TOO_WIDE")
    protection_soft = _protection_spread_soft_ok(pq, ps, c)
    if ps > c["max_protection_spread"] and not protection_soft:
        fail.append("PROTECTION_SPREAD_TOO_WIDE")
    elif ps > c["max_protection_spread"]:
        warnings.append("PROTECTION_SPREAD_SOFT_LOW_PREMIUM")

    # Q4/Q5：可成交 credit 为正且达底线；mark credit>0；保留率达标（EF-02）
    mark_credit = mark_credit_after_fees(sq["mark"], pq["mark"], amount, fees)
    exec_credit = executable_credit_after_fees(sq["best_bid"], pq["best_ask"], amount, fees)
    if mark_credit <= 0:
        fail.append("MARK_CREDIT_NON_POSITIVE")
    if exec_credit <= 0:
        fail.append("EXECUTABLE_CREDIT_NON_POSITIVE")
    elif exec_credit < c["min_net_credit"]:
        fail.append("EXECUTABLE_CREDIT_BELOW_FLOOR")
    retention = credit_retention_ratio(exec_credit, mark_credit)
    if retention is not None and retention < c["min_retention"]:
        fail.append("CREDIT_RETENTION_TOO_LOW")

    # Q6：追价后至少有最低可用空间
    surv = credit_survival_profile(sq, pq, amount, credit_floor, max_steps, fees)
    if surv["credit_survival_ticks"] < c["min_survival_ticks"]:
        fail.append("CREDIT_SURVIVAL_INSUFFICIENT")

    if fail:
        return _reject(fail, warnings)

    # 软分（depth 缺省 → None，权重在余下组件间重归一化，EF-08）
    cr_score = component_score_linear(retention, c["retention_bad"], c["retention_good"])
    sp_score = component_score_linear(worst, c["spread_bad"], c["spread_good"])
    friction = entry_friction_estimate(sq["mark"], sq["best_bid"], pq["best_ask"], pq["mark"], amount, fees)
    fr_ratio = friction_to_credit_ratio(friction, exec_credit)
    fr_score = component_score_linear(fr_ratio, c["friction_bad"], c["friction_good"])
    surv_score = surv["credit_survival_ratio"] * 100.0
    comps = {"credit_retention": cr_score, "spread": sp_score,
             "friction": fr_score, "credit_survival": surv_score, "depth": None}
    w = c["weights"]
    num = sum(w[k] * comps[k] for k in comps if comps[k] is not None and k in w)
    den = sum(w[k] for k in comps if comps[k] is not None and k in w)
    score = (num / den) if den > 0 else 0.0

    reason_codes = ["DUAL_LEG_QUOTES_OK", "EXECUTABLE_CREDIT_POSITIVE",
                    "CREDIT_SURVIVES_%d_TICKS" % (surv["credit_survival_ticks"] + 1)]
    return {
        "schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION, "status": "PASS",
        "grade": _grade(score), "score": round(score, 2), "score_norm": round(score / 100.0, 4),
        "hard_gate_passed": True, "hard_failures": [], "warnings": warnings,
        "economics": {"mark_credit_after_fees": mark_credit,
                      "executable_credit_after_fees": exec_credit,
                      "credit_retention_ratio": retention,
                      "entry_friction_estimate": friction,
                      "friction_to_credit_ratio": fr_ratio},
        "liquidity": {"short_spread_ratio": ss, "protection_spread_ratio": ps,
                      "protection_abs_spread": _quote_abs_spread(pq),
                      "protection_low_premium_soft": bool(ps > c["max_protection_spread"]
                                                          and protection_soft),
                      "worst_leg_spread_ratio": worst,
                      "depth_coverage_ratio": None, "depth_state": "NOT_EVALUATED"},
        "campaign": surv,
        "components": {"credit_retention_score": cr_score, "spread_score": sp_score,
                       "friction_score": fr_score, "credit_survival_score": surv_score,
                       "depth_score": None},
        "reason_codes": reason_codes,
    }


def feasibility_penalty(score_norm, floor=0.50):
    """排序折损：penalty = floor + (1-floor)×score_norm（满分不折损；可行性 0 最多保留 floor）。"""
    sn = _clamp01(score_norm if _is_num(score_norm) else 0.0)
    return floor + (1.0 - floor) * sn

# ===================== module: hedge_risk =====================
# -*- coding: utf-8 -*-
"""
Post-entry hedge risk evaluator.

The module is deliberately pure: it produces PositionRiskPackage only. Active
hedge sizing and order intent are owned by the strategy-layer hedge controller,
so this module never places orders, mutates the option ledger, or emits dry-run
hedge instructions.
"""
import math


SCHEMA_NAME = "PositionRiskPackage"
SCHEMA_VERSION = "nrd.integration.position_risk.v0.4"
TRIGGER_SCHEMA_VERSION = "nrd.execution.hedge_trigger.v1"

STATE_NORMAL = "NORMAL"
STATE_WATCH = "WATCH"
STATE_EXIT_PREFERRED = "EXIT_PREFERRED"
STATE_HEDGE_READY = "HEDGE_READY"
STATE_HEDGE_ACTIVE = "HEDGE_ACTIVE"
STATE_MANUAL_REVIEW = "MANUAL_REVIEW"

PERSISTENCE_LOW = "LOW"
PERSISTENCE_MEDIUM = "MEDIUM"
PERSISTENCE_HIGH = "HIGH"

SIDE_SHORT_CALL = "SHORT_CALL"
SIDE_SHORT_PUT = "SHORT_PUT"

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _safe_float(v):
    try:
        if v is None:
            return None
        out = float(v)
        if not math.isfinite(out):
            return None
        return out
    except Exception:
        return None


def _norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _normalise_iv(iv):
    vol = _safe_float(iv)
    if vol is None or vol <= 0:
        return None
    # Accept either decimal IV (0.7) or percent IV (70).
    return vol / 100.0 if vol > 3.0 else vol


def _is_short_call(direction_bias):
    return direction_bias == SIDE_SHORT_CALL


def _breached(direction_bias, price, boundary):
    if _is_short_call(direction_bias):
        return price >= boundary
    return price <= boundary


def boundary_distance_pct(direction_bias, price, loss_boundary):
    price, boundary = _safe_float(price), _safe_float(loss_boundary)
    if price is None or price <= 0 or boundary is None or boundary <= 0:
        return None
    if _is_short_call(direction_bias):
        return (boundary - price) / price * 100.0
    return (price - boundary) / price * 100.0


def estimate_touch_probability(direction_bias, price, loss_boundary,
                               dte_hours, iv=None, short_delta=None):
    """Estimate first-touch probability to the loss boundary before expiry.

    This is a risk-control estimate, not a real-world win-rate claim. IV-based
    output uses the driftless lognormal barrier approximation. Delta fallback is
    intentionally conservative and marked low-confidence by callers.
    """
    price = _safe_float(price)
    boundary = _safe_float(loss_boundary)
    dte = _safe_float(dte_hours)
    if price is None or price <= 0 or boundary is None or boundary <= 0:
        return 0.0
    if _breached(direction_bias, price, boundary):
        return 1.0
    if dte is None or dte <= 0:
        return 0.0

    vol = _normalise_iv(iv)
    if vol is not None:
        t_years = dte / (24.0 * 365.0)
        sigma_t = vol * math.sqrt(max(t_years, 1e-12))
        if sigma_t <= 1e-12:
            return 0.0
        if _is_short_call(direction_bias):
            distance = math.log(boundary / price)
        else:
            distance = math.log(price / boundary)
        if distance <= 0:
            return 1.0
        z = distance / sigma_t
        return _clamp(2.0 * (1.0 - _norm_cdf(z)), 0.0, 0.98)

    delta = _safe_float(short_delta)
    if delta is None:
        return 0.0
    return _clamp(abs(delta) * 1.8, 0.0, 0.95)


def _probability_confidence(iv):
    return "HIGH" if _normalise_iv(iv) is not None else "LOW"


def build_entry_risk_anchor(direction_bias, entry_price, entry_dte_hours,
                            entry_short_delta, entry_short_gamma, entry_iv,
                            entry_loss_boundary, entry_edb_side="",
                            entry_gamma_regime="",
                            entry_vrp_window_id="", entry_forward_vol_hurdle=None,
                            entry_candidate_vrp_edge_ccy=None,
                            entry_executable_short_iv=None, entry_vrp_reason_codes=None):
    p = estimate_touch_probability(
        direction_bias, entry_price, entry_loss_boundary, entry_dte_hours,
        entry_iv, entry_short_delta)
    return {
        "entry_price": entry_price,
        "entry_dte_hours": entry_dte_hours,
        "entry_short_delta": entry_short_delta,
        "entry_short_gamma": entry_short_gamma,
        "entry_iv": entry_iv,
        "entry_loss_boundary": entry_loss_boundary,
        "entry_touch_probability": p,
        "entry_probability_confidence": _probability_confidence(entry_iv),
        "entry_boundary_distance_pct": boundary_distance_pct(
            direction_bias, entry_price, entry_loss_boundary),
        "entry_edb_side": entry_edb_side,
        "entry_gamma_regime": entry_gamma_regime,
        # R4：VRP 入场血缘（与对冲共 IV/vol 基线；对冲只读此血缘、不反向重做 VRP）
        "entry_vrp_window_id": entry_vrp_window_id,
        "entry_forward_vol_hurdle": entry_forward_vol_hurdle,
        "entry_candidate_vrp_edge_ccy": entry_candidate_vrp_edge_ccy,
        "entry_executable_short_iv": entry_executable_short_iv,
        "entry_vrp_reason_codes": entry_vrp_reason_codes or [],
    }


def build_hedge_trigger_policy(entry_touch_probability, target_delta_reduction_ratio,
                               hedge_price_line=None):
    p_entry = _clamp(_safe_float(entry_touch_probability) or 0.0, 0.0, 0.98)
    return {
        "schema_name": "HedgeTriggerPolicy",
        "schema_version": TRIGGER_SCHEMA_VERSION,
        "entry_touch_probability": p_entry,
        "watch_probability": min(max(p_entry + 0.10, 0.40), 0.70),
        "open_probability": min(max(p_entry + 0.20, 0.50), 0.80),
        "emergency_probability": min(max(p_entry + 0.35, 0.70), 0.95),
        "min_probability_drift_to_open": 0.20,
        "target_delta_reduction_ratio": target_delta_reduction_ratio,
        "trigger_mode": "BOT_SIDE_RECHECK",
        "native_trigger": False,
        "hedge_price_line": hedge_price_line,
    }


def _price_line_touched(direction_bias, current_price, hedge_price_line):
    line = _safe_float(hedge_price_line)
    price = _safe_float(current_price)
    if line is None or price is None:
        return False
    return price >= line if _is_short_call(direction_bias) else price <= line


def evaluate_hedge_trigger(direction_bias, entry_risk_anchor, current_price,
                           probability_now, policy=None):
    anchor = entry_risk_anchor or {}
    p_entry = _safe_float(anchor.get("entry_touch_probability"))
    if p_entry is None:
        return {"tail_risk_state": STATE_MANUAL_REVIEW,
                "reason_codes": ["MISSING_ENTRY_RISK_ANCHOR"],
                "current_risk": {}, "price_line_touched": False}
    pol = policy or build_hedge_trigger_policy(p_entry, 0.5)
    p_now = _clamp(_safe_float(probability_now) or 0.0, 0.0, 1.0)
    drift = p_now - p_entry
    boundary = anchor.get("entry_loss_boundary")
    breached = _breached(direction_bias, _safe_float(current_price) or 0.0,
                         _safe_float(boundary) or 0.0)
    line_touched = _price_line_touched(
        direction_bias, current_price, pol.get("hedge_price_line"))
    reasons = []
    if breached:
        state = STATE_HEDGE_READY
        reasons.append("BOUNDARY_BREACHED")
    elif p_now >= (pol.get("emergency_probability") or 1.0):
        state = STATE_HEDGE_READY
        reasons.append("EMERGENCY_TOUCH_PROBABILITY")
    elif (p_now >= (pol.get("open_probability") or 1.0)
          and drift >= (pol.get("min_probability_drift_to_open") or 0.0)):
        state = STATE_HEDGE_READY
        reasons.append("TOUCH_PROBABILITY_DETERIORATED")
    elif line_touched:
        state = STATE_WATCH
        reasons.append("PRICE_LINE_TOUCHED_RECHECK_NOT_CONFIRMED")
    elif p_now >= (pol.get("watch_probability") or 1.0):
        state = STATE_WATCH
        reasons.append("TOUCH_PROBABILITY_WATCH")
    else:
        state = STATE_NORMAL
        reasons.append("TOUCH_PROBABILITY_NORMAL")
    return {
        "tail_risk_state": state,
        "reason_codes": reasons,
        "hedge_trigger_policy": pol,
        "price_line_touched": line_touched,
        "current_risk": {
            "touch_probability_now": p_now,
            "touch_probability_drift": drift,
            "entry_touch_probability": p_entry,
            "watch_probability": pol.get("watch_probability"),
            "open_probability": pol.get("open_probability"),
            "emergency_probability": pol.get("emergency_probability"),
        },
    }


def _recent_slope(current_probability, recent_history, now_ms,
                  recent_window_ms=30 * 60 * 1000):
    now = _safe_float(now_ms)
    if now is None:
        return 0.0
    usable = []
    for item in recent_history or []:
        ts = _safe_float((item or {}).get("ts_ms"))
        p = _safe_float((item or {}).get("touch_probability"))
        if ts is None or p is None:
            continue
        age = now - ts
        if 0 <= age <= recent_window_ms:
            usable.append((ts, p))
    if not usable:
        return 0.0
    ts, p0 = sorted(usable, key=lambda x: x[0])[0]
    hours = max((now - ts) / (60.0 * 60.0 * 1000.0), 1e-9)
    return (current_probability - p0) / hours


def _tail_exposure_acceleration(direction_bias, current_price, loss_boundary,
                                short_delta, short_gamma, entry_anchor):
    if _breached(direction_bias, _safe_float(current_price) or 0.0,
                 _safe_float(loss_boundary) or 0.0):
        return PERSISTENCE_HIGH
    delta = abs(_safe_float(short_delta) or 0.0)
    gamma = abs(_safe_float(short_gamma) or 0.0)
    entry_gamma = abs(_safe_float(
        (entry_anchor or {}).get("entry_short_gamma")) or 0.0)
    gamma_ratio = gamma / entry_gamma if entry_gamma > 0 else 0.0
    if delta >= 0.70 or gamma_ratio >= 2.0:
        return PERSISTENCE_HIGH
    if delta >= 0.50 or gamma_ratio >= 1.4:
        return PERSISTENCE_MEDIUM
    return PERSISTENCE_LOW


def _edb_adverse(direction_bias, edb):
    edb = edb or {}
    confidence = _safe_float(edb.get("confidence")) or 0.0
    coverage = _safe_float(edb.get("coverage"))
    if coverage is None:
        coverage = 1.0 if confidence >= 50 else 0.0
    if confidence < 50 or coverage < 0.50:
        return False
    lean = str(edb.get("lean") or edb.get("direction_bias") or "").upper()
    if _is_short_call(direction_bias):
        return lean in ("BULLISH", "UP", "LONG", "SHORT_PUT", "PUT_CREDIT_SPREAD")
    return lean in ("BEARISH", "DOWN", "SHORT", "SHORT_CALL", "CALL_CREDIT_SPREAD")


def _ggr_adverse(gamma_regime):
    ggr = gamma_regime or {}
    if bool(ggr.get("veto")):
        return True
    regime = str(ggr.get("regime") or "").upper()
    dist = _safe_float(ggr.get("distance_to_flip_pct"))
    if regime == "NEGATIVE_GAMMA_AMPLIFYING":
        return dist is None or abs(dist) <= 1.0
    gate = str(((ggr.get("ggr_gate") or {}).get("regime")) or "").upper()
    return gate == "NEGATIVE_GAMMA_AMPLIFYING"


def persistence_score(direction_bias, edb=None, gamma_regime=None):
    """持续性评分：{EDB_ADVERSE, GGR_ADVERSE}。
    重标定 0→LOW / 1→MEDIUM / 2→HIGH。EDB 为唯一方向证据入口、GGR 为负 Gamma 例外修正。"""
    confirmations = []
    if _edb_adverse(direction_bias, edb):
        confirmations.append("EDB_ADVERSE")
    if _ggr_adverse(gamma_regime):
        confirmations.append("GGR_ADVERSE")
    count = len(confirmations)
    if count >= 2:
        score = PERSISTENCE_HIGH
    elif count == 1:
        score = PERSISTENCE_MEDIUM
    else:
        score = PERSISTENCE_LOW
    return score, confirmations


def _friction_score(value):
    text = str(value or "").upper()
    if text in ("EXTREME", "VERY_HIGH", "BLOCKED"):
        return 4
    if text in ("HIGH", "POOR", "WIDE", "EXPENSIVE"):
        return 3
    if text in ("MEDIUM", "FAIR", "NORMAL"):
        return 2
    if text in ("LOW", "GOOD", "OK", "CHEAP"):
        return 1
    return 2


def exit_vs_hedge_friction(exit_friction):
    data = exit_friction or {}
    option_score = _friction_score(data.get("option_exit_friction"))
    hedge_score = _friction_score(data.get("future_hedge_friction"))
    return {
        "option_exit_friction": data.get("option_exit_friction"),
        "future_hedge_friction": data.get("future_hedge_friction"),
        "option_exit_score": option_score,
        "future_hedge_score": hedge_score,
    }


def _manual_review_package(position_id, entry_anchor, reason):
    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "position_id": position_id,
        "entry_risk_anchor": entry_anchor or {},
        "current_risk": {
            "touch_probability_now": 0.0,
            "touch_probability_drift": 0.0,
            "recent_deterioration_slope": 0.0,
            "tail_exposure_acceleration": PERSISTENCE_LOW,
            "persistence": PERSISTENCE_LOW,
        },
        "exit_vs_hedge_friction": {},
        "tail_risk_state": STATE_MANUAL_REVIEW,
        "hedge_intent": None,
        "reason_codes": [reason],
    }


def evaluate_position_risk(position_id, direction_bias, entry_risk_anchor,
                           current_price, dte_hours, short_delta,
                           short_gamma, iv, loss_boundary, edb=None,
                           gamma_regime=None,
                           exit_friction=None, recent_history=None,
                           now_ms=None, existing_hedge=False):
    if direction_bias not in (SIDE_SHORT_CALL, SIDE_SHORT_PUT):
        return _manual_review_package(
            position_id, entry_risk_anchor, "INVALID_DIRECTION_BIAS")
    if not entry_risk_anchor or "entry_touch_probability" not in entry_risk_anchor:
        return _manual_review_package(
            position_id, entry_risk_anchor, "MISSING_ENTRY_RISK_ANCHOR")

    p_now = estimate_touch_probability(
        direction_bias, current_price, loss_boundary, dte_hours, iv,
        short_delta)
    p_entry = _safe_float(entry_risk_anchor.get("entry_touch_probability")) or 0.0
    policy = entry_risk_anchor.get("hedge_trigger_policy") or build_hedge_trigger_policy(
        p_entry, 0.5)
    trigger = evaluate_hedge_trigger(
        direction_bias, entry_risk_anchor, current_price, p_now, policy)
    state = trigger["tail_risk_state"]

    return {
        "schema_name": SCHEMA_NAME,
        "schema_version": SCHEMA_VERSION,
        "position_id": position_id,
        "entry_risk_anchor": entry_risk_anchor,
        "current_risk": trigger["current_risk"],
        "hedge_trigger_policy": trigger["hedge_trigger_policy"],
        "price_line_touched": trigger["price_line_touched"],
        "exit_vs_hedge_friction": exit_vs_hedge_friction(exit_friction),
        "tail_risk_state": state,
        "hedge_intent": None,
        "reason_codes": trigger["reason_codes"],
    }

# ===================== module: risk_controls =====================
# -*- coding: utf-8 -*-
"""Conservative risk, position management, attribution, and replay contracts."""

from typing import Any, Dict, Iterable, List


REPLAY_BUCKET_FIELDS = ["side", "dte_bucket", "vrp_gate", "budget_decision"]


def _expectation_bucket(net_sum: float) -> str:
    if net_sum > 0:
        return "POSITIVE_NET"
    if net_sum < 0:
        return "NEGATIVE_NET"
    return "FLAT_NET"


def evaluate_portfolio_budget(
    current: Dict[str, float],
    limits: Dict[str, float],
    proposed_size: float,
) -> Dict[str, Any]:
    breaches: List[str] = []
    checks = (
        ("open_positions", "max_open_positions"),
        ("short_gamma", "max_short_gamma"),
        ("short_vega", "max_short_vega"),
        ("margin_used", "max_margin"),
    )
    for current_key, limit_key in checks:
        if current.get(current_key, 0.0) > limits.get(limit_key, float("inf")):
            breaches.append("%s>%s" % (current_key, limit_key))

    blocked = bool(breaches)
    return {
        "schema_name": "PortfolioRiskBudgetPackage",
        "schema_version": "nrd.integration.portfolio_budget.v0.1",
        "status": "PLACEHOLDER",
        "decision": "BLOCK" if blocked else "ALLOW_TEST_SIZE",
        "allowed_size": 0.0 if blocked else min(float(proposed_size), 1.0),
        "breaches": breaches,
        "reason_codes": ["PORTFOLIO_BUDGET_EXCEEDED"] if blocked else ["PORTFOLIO_BUDGET_PLACEHOLDER_CONSERVATIVE"],
    }


# ---------- 投影预算真实算法（P0-6；替代上面 PLACEHOLDER：把拟建仓位计入，fail-closed）----------

def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _budget_result(decision, projected, reasons, fail_closed):
    return {
        "schema_name": "ProjectedBudgetPackage",
        "schema_version": "nrd.integration.projected_budget.v1",
        "decision": decision,
        "projected": projected,
        "fail_closed": bool(fail_closed),
        "reason_codes": reasons,
    }


def evaluate_projected_budget(proposed, current, limits):
    """把**拟建仓位**(proposed)计入当前组合(current)后与限额(limits)比较。
    proposed 任一必填项缺失 → fail closed(BLOCK)，绝不放行不完整输入。
      proposed: {short_gamma, short_vega, structure_margin, max_spread_loss,
                 hedge_margin_reserve, fee_reserve}
      current:  {open_positions, short_gamma, short_vega, margin_used}
      limits:   {max_open_positions, max_short_gamma, max_short_vega, max_margin,
                 max_spread_loss_per_trade}"""
    required = ("short_gamma", "short_vega", "structure_margin",
                "max_spread_loss", "hedge_margin_reserve", "fee_reserve")
    missing = [k for k in required if not _is_num((proposed or {}).get(k))]
    if missing:
        return _budget_result("BLOCK", {},
                              ["BUDGET_INPUT_INCOMPLETE:" + ",".join(missing)], True)
    cur = current or {}
    proj = {
        "open_positions": int(cur.get("open_positions", 0)) + 1,
        "short_gamma": float(cur.get("short_gamma", 0.0)) + abs(float(proposed["short_gamma"])),
        "short_vega": float(cur.get("short_vega", 0.0)) + abs(float(proposed["short_vega"])),
        "margin_used": (float(cur.get("margin_used", 0.0))
                        + float(proposed["structure_margin"])
                        + float(proposed["hedge_margin_reserve"])
                        + float(proposed["fee_reserve"])),
    }
    breaches = []
    for pk, lk in (("open_positions", "max_open_positions"),
                   ("short_gamma", "max_short_gamma"),
                   ("short_vega", "max_short_vega"),
                   ("margin_used", "max_margin")):
        lim = (limits or {}).get(lk)
        if _is_num(lim) and proj[pk] > lim:
            breaches.append("%s>%s" % (pk, lk))
    msl_lim = (limits or {}).get("max_spread_loss_per_trade")
    if _is_num(msl_lim) and float(proposed["max_spread_loss"]) > msl_lim:
        breaches.append("max_spread_loss>limit")
    decision = "BLOCK" if breaches else "ALLOW"
    return _budget_result(decision, proj,
                          breaches if breaches else ["PROJECTED_BUDGET_OK"], False)


# ---------- 统一动作仲裁四输出（P0-4：退出不可执行可回退对冲，避免压住风险收口）----------

def _arb(preferred, executable, blocked_reason, fallback):
    return {"schema_name": "ActionArbitration",
            "preferred_action": preferred, "executable_action": executable,
            "blocked_reason": blocked_reason, "fallback_action": fallback}


def unified_action_arbiter(s):
    """每轮输出唯一 preferred + 实际可执行 executable + blocked_reason + fallback。
    s: recovery_blocked / orphan_hedge / in_flight_order / exit_preferred / hedge_ready /
       take_profit_ready / exit_authorized / exit_executable / exit_pause_reason / hedge_executable。
    优先级：RECOVERY_BLOCKED > ORPHAN_HEDGE_EMERGENCY > MANAGE_IN_FLIGHT >
            EXIT_PREFERRED > HEDGE_READY > TAKE_PROFIT_READY > HOLD。
    P0-4：当退出类为 preferred 但未授权/无数据/预算暂停时，executable 回退到对冲(若可执行)，
    不因退出受阻而禁止必要对冲。"""
    s = s or {}
    if s.get("recovery_blocked"):
        return _arb("RECOVERY_BLOCKED", "RECOVERY_BLOCKED", None, None)
    if s.get("orphan_hedge"):
        return _arb("ORPHAN_HEDGE_EMERGENCY", "ORPHAN_HEDGE_EMERGENCY", None, None)
    if s.get("in_flight_order"):
        return _arb("MANAGE_IN_FLIGHT", "MANAGE_IN_FLIGHT", None, None)

    if s.get("exit_preferred"):
        preferred = "EXIT_PREFERRED"
    elif s.get("hedge_ready"):
        preferred = "HEDGE_READY"
    elif s.get("take_profit_ready"):
        preferred = "TAKE_PROFIT_READY"
    else:
        return _arb("HOLD", "HOLD", None, None)

    if preferred in ("EXIT_PREFERRED", "TAKE_PROFIT_READY"):
        if not s.get("exit_authorized"):
            blocked = "EXIT_NOT_AUTHORIZED"
        elif s.get("exit_pause_reason"):
            blocked = "EXIT_" + str(s["exit_pause_reason"])
        elif not s.get("exit_executable"):
            blocked = "EXIT_NOT_EXECUTABLE"
        else:
            blocked = None
        if not blocked:
            return _arb(preferred, preferred, None, None)
        if s.get("hedge_executable"):
            return _arb(preferred, "HEDGE_READY", blocked, "HEDGE_READY")
        return _arb(preferred, "HOLD", blocked, "HOLD")

    # preferred == HEDGE_READY
    if s.get("hedge_executable"):
        return _arb("HEDGE_READY", "HEDGE_READY", None, None)
    return _arb("HEDGE_READY", "HOLD", "HEDGE_NOT_EXECUTABLE", "HOLD")


def decide_position_manage(
    premium_captured_ratio: float,
    take_profit_threshold: float,
    dte_remaining: int,
    gamma_state: str,
) -> Dict[str, Any]:
    reason_codes: List[str] = []
    decision = "HOLD_REVIEW"
    if premium_captured_ratio >= take_profit_threshold:
        decision = "TAKE_PROFIT_READY"
        reason_codes.append("TAKE_PROFIT_PLACEHOLDER_EARLY")
    elif dte_remaining <= 2 and gamma_state.upper() == "HIGH":
        decision = "GAMMA_DECAY_EXIT"
        reason_codes.append("GAMMA_DECAY_PLACEHOLDER_EARLY")
    elif dte_remaining <= 4:
        decision = "TIME_EXIT_REVIEW"
        reason_codes.append("TIME_EXIT_DRYRUN_REVIEW")
    else:
        reason_codes.append("POSITION_MANAGE_PLACEHOLDER_HOLD")

    return {
        "schema_name": "PositionManageDecision",
        "schema_version": "nrd.integration.position_manage.v0.1",
        "status": "PLACEHOLDER",
        "decision": decision,
        "inputs": {
            "premium_captured_ratio": premium_captured_ratio,
            "take_profit_threshold": take_profit_threshold,
            "dte_remaining": dte_remaining,
            "gamma_state": gamma_state,
        },
        "reason_codes": reason_codes,
    }


def build_attribution(
    session_id: str,
    theta_capture: float,
    directional_pnl: float,
    iv_rv_edge_proxy: float,
    fee_cost: float,
    spread_slippage_cost: float,
    protection_cost_or_recovery: float,
    hedge_pnl: float,
    unexplained_residual: float = 0.0,
) -> Dict[str, Any]:
    net = (
        theta_capture
        + directional_pnl
        + iv_rv_edge_proxy
        - fee_cost
        - spread_slippage_cost
        + protection_cost_or_recovery
        + hedge_pnl
        + unexplained_residual
    )
    return {
        "schema_name": "AttributionPackage",
        "schema_version": "nrd.integration.attribution.v0.1",
        "status": "PLACEHOLDER",
        "session_id": session_id,
        "theta_capture": theta_capture,
        "directional_pnl": directional_pnl,
        "iv_rv_edge_proxy": iv_rv_edge_proxy,
        "fee_cost": fee_cost,
        "spread_slippage_cost": spread_slippage_cost,
        "protection_cost_or_recovery": protection_cost_or_recovery,
        "hedge_pnl": hedge_pnl,
        "unexplained_residual": unexplained_residual,
        "net_pnl_after_costs": net,
    }


def replay_expectation(attributions: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    rows = list(attributions)
    net_sum = sum(float(row.get("net_pnl_after_costs", 0.0)) for row in rows)
    return {
        "schema_name": "ReplayExpectationPackage",
        "schema_version": "nrd.integration.replay_expectation.v0.1",
        "status": "OFFLINE",
        "sample_count": len(rows),
        "net_pnl_after_costs_sum": net_sum,
        "net_pnl_after_costs_mean": net_sum / len(rows) if rows else 0.0,
        "expectation_bucket": _expectation_bucket(net_sum),
    }


def _bucket_key(row: Dict[str, Any], bucket_fields: List[str]) -> str:
    return "|".join("%s=%s" % (field, row.get(field, "UNKNOWN")) for field in bucket_fields)


def replay_expectation_by_bucket(
    rows: Iterable[Dict[str, Any]],
    bucket_fields: List[str],
) -> Dict[str, Any]:
    materialized = list(rows)
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in materialized:
        grouped.setdefault(_bucket_key(row, bucket_fields), []).append(row)

    buckets = []
    for key in sorted(grouped):
        bucket_rows = grouped[key]
        net_sum = sum(float(row.get("net_pnl_after_costs", 0.0)) for row in bucket_rows)
        first_row = bucket_rows[0] if bucket_rows else {}
        buckets.append({
            "bucket_key": key,
            "bucket_values": {field: first_row.get(field, "UNKNOWN") for field in bucket_fields},
            "sample_count": len(bucket_rows),
            "net_pnl_after_costs_sum": net_sum,
            "net_pnl_after_costs_mean": net_sum / len(bucket_rows) if bucket_rows else 0.0,
            "expectation_bucket": _expectation_bucket(net_sum),
        })

    net_sum = sum(float(row.get("net_pnl_after_costs", 0.0)) for row in materialized)
    return {
        "schema_name": "ReplayExpectationBucketReport",
        "schema_version": "nrd.integration.replay_expectation_buckets.v0.5",
        "status": "OFFLINE",
        "sample_count": len(materialized),
        "bucket_fields": bucket_fields,
        "net_pnl_after_costs_sum": net_sum,
        "net_pnl_after_costs_mean": net_sum / len(materialized) if materialized else 0.0,
        "buckets": buckets,
    }


def _dte_bucket(expiry_hours: Any) -> str:
    if expiry_hours is None:
        return "UNKNOWN"
    try:
        return "%sh" % int(float(expiry_hours))
    except (TypeError, ValueError):
        return str(expiry_hours)


def build_replay_context_row(execution_result: Dict[str, Any]) -> Dict[str, Any]:
    session = execution_result.get("session", {})
    locked_plan = execution_result.get("locked_plan", {})
    plan = locked_plan.get("plan", {})
    vrp_gate = execution_result.get("vrp_gate", {})
    candidate = vrp_gate.get("candidate", {})
    portfolio_budget = execution_result.get("portfolio_budget", {})
    attribution = execution_result.get("attribution", {})
    approval_intent = session.get("approval_intent", {})
    vrp_state = "PASS" if vrp_gate.get("pass") else "BLOCK"
    return {
        "schema_name": "ReplayContextRow",
        "schema_version": "nrd.integration.replay_context.v0.8",
        "session_id": session.get("session_id"),
        "manual_package_id": session.get("manual_package_id"),
        "plan_hash": locked_plan.get("plan_hash"),
        "side": plan.get("side", "UNKNOWN"),
        "expiry_hours": plan.get("expiry_hours"),
        "dte_bucket": _dte_bucket(plan.get("expiry_hours")),
        "vrp_gate": vrp_state,
        "window_vrp_gate": vrp_gate.get("window", {}).get("window_vrp_gate"),
        "candidate_vrp_gate": candidate.get("candidate_vrp_gate"),
        "candidate_vrp_edge_ccy": float(candidate.get("candidate_vrp_edge_ccy", 0.0) or 0.0),
        "budget_decision": portfolio_budget.get("decision", "UNKNOWN"),
        "approval_state": approval_intent.get("approval_state", "UNKNOWN"),
        "can_commit_order": bool(execution_result.get("can_commit_order", False)),
        "net_pnl_after_costs": float(attribution.get("net_pnl_after_costs", 0.0) or 0.0),
        "reason_codes": sorted(set(vrp_gate.get("reason_codes") or [])),
    }


def replay_expectation_from_execution_result(execution_result: Dict[str, Any]) -> Dict[str, Any]:
    row = build_replay_context_row(execution_result)
    report = replay_expectation_by_bucket([row], bucket_fields=REPLAY_BUCKET_FIELDS)
    report["source"] = "execution_result"
    report["rows"] = [row]
    return report


def replay_expectation_batch_from_execution_results(
    execution_results: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    rows = [build_replay_context_row(result) for result in execution_results]
    bucket_report = replay_expectation_by_bucket(rows, bucket_fields=REPLAY_BUCKET_FIELDS)
    bucket_report["source"] = "execution_results"
    net_sum = sum(float(row.get("net_pnl_after_costs", 0.0)) for row in rows)
    return {
        "schema_name": "ReplayExpectationBatchReport",
        "schema_version": "nrd.integration.replay_batch.v0.9",
        "source": "execution_results",
        "sample_count": len(rows),
        "net_pnl_after_costs_sum": net_sum,
        "net_pnl_after_costs_mean": net_sum / len(rows) if rows else 0.0,
        "expectation_bucket": _expectation_bucket(net_sum),
        "rows": rows,
        "bucket_report": bucket_report,
    }

# ===================== module: strategy =====================
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
        return "%s｜风险退出受限｜原因=%s" % (
            note or "manual-gate", disp_reason_cn(risk_detail.get("reason")))
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


def _has_position_snapshot(snap):
    return isinstance(snap, dict) and bool(
        snap.get("position_id") or snap.get("short_instrument") or snap.get("long_instrument"))


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
    account = dbt_account_summary(SETTLEMENT_CURRENCY)
    if not isinstance(account, dict) or not account:
        return _current_portfolio_gap("ACCOUNT_SUMMARY_QUERY_FAILED")

    margin_used, margin_source = _account_margin_used(account)
    if margin_used is None:
        return _current_portfolio_gap("ACCOUNT_MARGIN_DATA_GAP")

    positions = dbt_get_positions_strict(SETTLEMENT_CURRENCY, kind="option")
    if positions is None:
        return _current_portfolio_gap("OPTION_POSITION_QUERY_FAILED")

    open_positions = 0
    short_gamma = 0.0
    short_vega = 0.0
    for pos in positions:
        if not isinstance(pos, dict):
            return _current_portfolio_gap("OPTION_POSITION_DATA_GAP")
        inst = pos.get("instrument_name") or pos.get("instrument")
        size = _position_size(pos)
        if size is None:
            return _current_portfolio_gap("OPTION_POSITION_SIZE_DATA_GAP", inst)
        if abs(size) <= 1e-12:
            continue
        open_positions += 1
        short_amount = _short_position_amount(pos, size)
        if short_amount <= 0.0:
            continue
        gamma = _position_greek(pos, "gamma")
        vega = _position_greek(pos, "vega")
        if gamma is None or vega is None:
            return _current_portfolio_gap("OPTION_GREEK_DATA_GAP", inst)
        short_gamma += short_amount * abs(gamma)
        short_vega += short_amount * abs(vega)

    return {
        "data_gap": None,
        "open_positions": open_positions,
        "short_gamma": short_gamma,
        "short_vega": short_vega,
        "margin_used": margin_used,
        "margin_used_source": margin_source,
        "account_equity": _account_equity(account),
        "option_position_count": open_positions,
    }


def _current_portfolio_gap(reason, instrument=None):
    out = {"data_gap": reason}
    if instrument:
        out["data_gap_instrument"] = instrument
    return out


def _portfolio_float(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except Exception:
            return None
    return None


def _account_margin_used(account):
    initial_margin = _portfolio_float((account or {}).get("initial_margin"))
    if initial_margin is None:
        initial_margin = _portfolio_float((account or {}).get("initial_margin_used"))
    if initial_margin is None:
        return None, None

    equity = _portfolio_float((account or {}).get("equity"))
    if equity is None:
        equity = _portfolio_float((account or {}).get("margin_balance"))
    if equity is None:
        equity = _portfolio_float((account or {}).get("balance"))
    if equity is not None and equity > 0.0:
        return initial_margin / equity, "initial_margin/equity"
    return initial_margin, "initial_margin"


def _account_equity(account):
    for key in ("equity", "margin_balance", "balance"):
        value = _portfolio_float((account or {}).get(key))
        if value is not None and value > 0.0:
            return value
    return None


def _position_size(pos):
    raw = (pos or {}).get("size")
    if raw is None:
        raw = (pos or {}).get("amount")
    return _portfolio_float(raw)


def _short_position_amount(pos, size):
    side = str((pos or {}).get("direction") or (pos or {}).get("side") or "").lower()
    if size < -1e-12:
        return abs(size)
    if side in ("sell", "short"):
        return abs(size)
    return 0.0


def _position_greek(pos, name):
    value = _portfolio_float((pos or {}).get(name))
    if value is not None:
        return value
    greeks = (pos or {}).get("greeks")
    if isinstance(greeks, dict):
        value = _portfolio_float(greeks.get(name))
        if value is not None:
            return value
    inst = (pos or {}).get("instrument_name") or (pos or {}).get("instrument")
    if not inst:
        return None
    try:
        ticker = dbt_ticker(inst)
    except Exception:
        return None
    tgreeks = (ticker or {}).get("greeks")
    if not isinstance(tgreeks, dict):
        return None
    return _portfolio_float(tgreeks.get(name))


def _current_portfolio_gap_budget(current):
    reason = (current or {}).get("data_gap") or "UNKNOWN"
    return {
        "schema_name": "ProjectedBudgetPackage",
        "schema_version": "nrd.integration.projected_budget.v1",
        "decision": "BLOCK",
        "projected": {},
        "fail_closed": True,
        "reason_codes": ["CURRENT_PORTFOLIO_DATA_GAP:" + str(reason)],
        "current": current or {},
    }


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


def _precommit_hedge_margin_reserve(amount, short_quote, protection_quote, current_portfolio):
    net_delta = option_net_delta(
        amount,
        (short_quote or {}).get("delta"),
        amount,
        (protection_quote or {}).get("delta"))
    if net_delta is None:
        return None
    reserve = abs(net_delta) * HEDGE_MARGIN_RESERVE_RATE
    if (current_portfolio or {}).get("margin_used_source") == "initial_margin/equity":
        equity = _portfolio_float((current_portfolio or {}).get("account_equity"))
        if equity is None or equity <= 0.0:
            return None
        return reserve / equity
    return reserve


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
    current_portfolio = _current_portfolio()
    hedge_margin_reserve = _precommit_hedge_margin_reserve(amount, sq, lq, current_portfolio)
    proposed = {
        "short_gamma": (sq or {}).get("gamma"),
        "short_vega": (sq or {}).get("vega"),
        "structure_margin": (spm or {}).get("im_with_protection"),
        "max_spread_loss": locked.get("max_loss"),
        "hedge_margin_reserve": hedge_margin_reserve,
        "fee_reserve": fee_reserve,
    }
    if (current_portfolio or {}).get("data_gap"):
        budget = _current_portfolio_gap_budget(current_portfolio)
    else:
        budget = evaluate_projected_budget(proposed, current_portfolio, PORTFOLIO_LIMITS)
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
        "hedge_margin_reserve": hedge_margin_reserve,
        "current_portfolio": current_portfolio,
        "current_portfolio_data_gap": (current_portfolio or {}).get("data_gap"),
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
    actual_fills = [f for f in fills if (f.get("filled") or 0.0) > 1e-12]
    total_fee = prog.get("entry_fee_used")
    if total_fee is None:
        total_fee = sum((f.get("fee_used") or f.get("fee_estimate") or 0.0) for f in fills)
    prot_cost = prog.get("prot_cost") or 0.0
    short_credit = prog.get("short_credit") or 0.0
    before_fee = short_credit - prot_cost
    return {
        "fills": fills,
        "fill_count": len(actual_fills),
        "order_event_count": len(fills),
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
    auto = recovery.get("auto_cleanup_allowed") is True
    return {
        "state": recovery.get("state") or "ORPHAN_HEDGE_EMERGENCY",
        "policy": recovery.get("cleanup_policy") or (
            "AUTO_REDUCE_ONLY" if auto else "MANUAL_CLEANUP_ONLY"),
        "mode": recovery.get("cleanup_mode") or (
            "AUTO_REDUCE_ONLY_ALLOWED" if auto else "MANUAL_REDUCE_ONLY_REQUIRED"),
        "auto_cleanup_allowed": auto,
        "cleanup_block_reason": recovery.get("cleanup_block_reason"),
        "venue": recovery.get("venue") or HEDGE_VENUE,
        "instrument": recovery.get("instrument") or (
            HEDGE_BINANCE_INSTRUMENT if HEDGE_VENUE == "BINANCE" else HEDGE_INSTRUMENT),
        "perp_qty": qty,
        "suggested_side": side,
        "reasons": recovery.get("reasons") or [],
    }


def _startup_orphan_cleanup_decision(perp_qty, active_orders):
    if HEDGE_VENUE != "BINANCE":
        return {"auto_cleanup_allowed": False, "cleanup_policy": "MANUAL_CLEANUP_ONLY",
                "cleanup_mode": "MANUAL_REDUCE_ONLY_REQUIRED",
                "cleanup_block_reason": "UNSUPPORTED_HEDGE_VENUE"}
    if not isinstance(perp_qty, (int, float)) or isinstance(perp_qty, bool) \
            or abs(perp_qty) <= 1e-9:
        return {"auto_cleanup_allowed": False, "cleanup_policy": "MANUAL_CLEANUP_ONLY",
                "cleanup_mode": "MANUAL_REDUCE_ONLY_REQUIRED",
                "cleanup_block_reason": "NO_PERP_POSITION"}
    unknown = [o for o in (active_orders or []) if not (o or {}).get("label")]
    if unknown:
        return {"auto_cleanup_allowed": False, "cleanup_policy": "MANUAL_CLEANUP_ONLY",
                "cleanup_mode": "MANUAL_REDUCE_ONLY_REQUIRED",
                "cleanup_block_reason": "UNKNOWN_ACTIVE_ORDERS"}
    support = bnc_order_lifecycle_supported(HEDGE_BINANCE_INSTRUMENT)
    if not support.get("ok"):
        return {"auto_cleanup_allowed": False, "cleanup_policy": "MANUAL_CLEANUP_ONLY",
                "cleanup_mode": "MANUAL_REDUCE_ONLY_REQUIRED",
                "cleanup_block_reason": support.get("reason") or "BINANCE_ORDER_LIFECYCLE_UNSUPPORTED",
                "missing_methods": support.get("missing_methods") or []}
    return {"auto_cleanup_allowed": True,
            "cleanup_policy": "AUTO_REDUCE_ONLY",
            "cleanup_mode": "AUTO_REDUCE_ONLY_ALLOWED",
            "cleanup_block_reason": None}


def _submit_orphan_hedge_cleanup(detail, now_ms):
    qty = detail.get("perp_qty")
    side = detail.get("suggested_side")
    if not side or not isinstance(qty, (int, float)) or isinstance(qty, bool):
        return {"filled": 0.0, "dry": True, "venue": detail.get("venue"),
                "reason": "ORPHAN_CLEANUP_NO_ACTION"}
    st = _hedge_policy_load_state_raw() or {}
    if st.get("pending_order_id"):
        return {"filled": 0.0, "dry": False, "venue": detail.get("venue"),
                "reason": "HEDGE_PENDING_ORDER_ACTIVE", "blocked": True,
                "pending_order_id": st.get("pending_order_id")}
    hedge = {
        "venue": "BINANCE",
        "instrument": detail.get("instrument") or HEDGE_BINANCE_INSTRUMENT,
        "side": side,
        "venue_cfg": {"venue": "BINANCE", "instrument": detail.get("instrument") or HEDGE_BINANCE_INSTRUMENT,
                      "linear": True, "exchange_index": HEDGE_BINANCE_EXCHANGE_INDEX},
        "action": {"action": "HEDGE_UNWIND", "reduce_only": True,
                   "delta_contracts": abs(qty)},
        "policy_detail": {"reason": "STARTUP_ORPHAN_AUTO_CLEANUP",
                          "cross_bps": HEDGE_SOFT_CROSS_BPS},
    }
    allow_live = bool(normalize_run_profile(RUN_PROFILE) == "LIVE")
    return _hedge_policy_submit(hedge, now_ms, allow_live=allow_live)


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
    unknown_order_block = (
        verdict.get("state") == "RECOVERY_BLOCKED"
        and any(str(r).startswith("UNKNOWN_ACTIVE_ORDERS") for r in (verdict.get("reasons") or []))
        and (short_qty or 0.0) <= 1e-12
        and (long_qty or 0.0) <= 1e-12
        and isinstance(perp_qty, (int, float))
        and not isinstance(perp_qty, bool)
        and abs(perp_qty) > 1e-9
    )
    if unknown_order_block:
        verdict = {"state": "ORPHAN_HEDGE_EMERGENCY",
                   "reasons": verdict.get("reasons") or ["UNKNOWN_ACTIVE_ORDERS"],
                   "allow_new_open": False}
    if verdict.get("state") == "ORPHAN_HEDGE_EMERGENCY":
        verdict.update({"perp_qty": perp_qty, "venue": HEDGE_VENUE,
                        "instrument": (HEDGE_BINANCE_INSTRUMENT if HEDGE_VENUE == "BINANCE"
                                       else HEDGE_INSTRUMENT)})
        verdict.update(_startup_orphan_cleanup_decision(perp_qty, orders))
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
    if vcfg["venue"] != "BINANCE":
        action = {"action": "HEDGE_HOLD", "reduce_only": False,
                  "delta_contracts": 0.0, "blocked": "UNSUPPORTED_HEDGE_VENUE"}
        return {"perp_qty": None, "target": None, "action": action,
                "orphan": False, "side": hedge_side((snap or {}).get("side")),
                "net_delta": None, "net_option_delta": None,
                "direction_consistent": True, "venue": vcfg["venue"],
                "instrument": vcfg["instrument"], "venue_cfg": vcfg,
                "short_gamma": None, "protection_gamma": None,
                "gamma_fraction": None, "gamma_data_state": None,
                "target_semantics": "UNSUPPORTED_HEDGE_VENUE",
                "unrealized_pnl_usd": None,
                "data_gap": "UNSUPPORTED_HEDGE_VENUE"}
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
    snap_bnc = bnc_get_position_snapshot(vcfg["instrument"])
    perp_qty = None if snap_bnc is None else snap_bnc.get("qty")
    hedge_pnl_usd = None if snap_bnc is None else snap_bnc.get("unrealized_pnl_usd")
    contract_size, min_trade = 1.0, HEDGE_BINANCE_MIN_TRADE
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
                         min_hold_until=None, crash_adverse_bps=None,
                         now_ms=None):
    cr = (risk or {}).get("current_risk") or {}
    crash_ref_ts = st.get("crash_ref_ts") or 0
    crash_ref_age_seconds = None
    if isinstance(now_ms, (int, float)) and not isinstance(now_ms, bool) and crash_ref_ts:
        crash_ref_age_seconds = max(0.0, (now_ms - crash_ref_ts) / 1000.0)
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
        "crash_ref_price": st.get("crash_ref_price"),
        "crash_ref_age_seconds": crash_ref_age_seconds,
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
        min_hold_until=min_hold_until, crash_adverse_bps=crash_adverse_bps,
        now_ms=now_ms)
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
    if (snap or {}).get("entry_completion_state") == "PARTIAL_VERTICAL":
        return "开仓部分成交·部分垂直持仓"
    if (snap or {}).get("entry_completion_state") == "PROTECTION_ONLY_RESIDUAL":
        return "保护腿残留·未形成期权空头"
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
            "crash_ref_price": hp.get("crash_ref_price"),
            "crash_ref_age_seconds": hp.get("crash_ref_age_seconds"),
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
            hedge_allow_live = bool(normalize_run_profile(RUN_PROFILE) == "LIVE")
            hedge_step = _hedge_policy_submit(hedge, now_ms, allow_live=hedge_allow_live)
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
    has_pos = _has_position(state) or _has_position_snapshot(_G(_POSITION_KEY))
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
    orphan_cleanup_detail = None
    orphan_cleanup_step = None
    recovery = _recovery_verdict()
    rec_ok = recovery.get("allow_new_open", True)

    if recovery.get("state") == "RECOVERY_BLOCKED":
        phase = "RECOVERY_BLOCKED"
    elif recovery.get("state") == "ORPHAN_HEDGE_EMERGENCY" and not has_pos:
        orphan_cleanup_detail = _orphan_hedge_cleanup_detail(recovery)
        if orphan_cleanup_detail.get("auto_cleanup_allowed"):
            orphan_cleanup_step = _submit_orphan_hedge_cleanup(orphan_cleanup_detail, now_ms)
            phase = "ORPHAN_HEDGE_AUTO_CLEANUP"
        else:
            phase = "ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED"
    elif has_pos:
        manage_result = manage_cycle(now_ms)
        phase = "POSITION_MANAGE"
    elif kill:
        phase = "KILLED"
    elif locked:
        commit_result = _attempt_commit(locked, spot, manual_context, now_ms)
        phase = ("POSITION_MANAGE" if (commit_result["committed"]
                 or commit_result.get("partial_position")
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
            if phase == "POSITION_MANAGE" and not manage_result:
                snap = commit_result["entry_snapshot"]
                qfn = _quote_cache()
                tp_display = _evaluate_take_profit(snap, qfn, now_ms)
                no_in_flight = {"count": 0, "orders": []}
                ctx["position_detail"] = _build_position_detail(
                    snap, qfn, now_ms, None, no_in_flight, None)
                ctx["take_profit_detail"] = tp_display
                ctx["ledger_detail"] = _build_ledger_detail(
                    snap,
                    {"reconciled": None, "reasons": ["POST_ENTRY_MANAGE_NEXT_LOOP"]},
                    recovery, no_in_flight, tp_display)
    if locked and locked.get("entry") and not (commit_result and commit_result.get("committed")):
        ctx["entry_progress"] = dict(locked.get("entry") or {})
        ctx["entry_progress"]["target_amount"] = locked.get("amount") or ORDER_AMOUNT
        ctx["entry_progress"]["short_instrument"] = locked.get("short_instrument")
        ctx["entry_progress"]["long_instrument"] = locked.get("long_instrument")
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
    if phase in ("ORPHAN_HEDGE_MANUAL_CLEANUP_REQUIRED", "ORPHAN_HEDGE_AUTO_CLEANUP"):
        ctx["orphan_hedge_cleanup"] = orphan_cleanup_detail or _orphan_hedge_cleanup_detail(recovery)
        if orphan_cleanup_step:
            ctx["orphan_hedge_cleanup_step"] = orphan_cleanup_step
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
