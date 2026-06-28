# -*- coding: utf-8 -*-
"""
Human Audit Gate 执行层配置块（FMZ 启动前手填）。

本版本只接受执行层本地人工审计配置：方向、数量、delta 范围、腿宽、
风险退出预算和分动作授权门控均来自这些 UPPER_CASE 参数。信号层不参与
执行主链路。交易员通常只需要看本文件顶部几个配置块。
"""

# ===== 当前版本 / 实例标识 =====
ROBOT_ID = "spm-exec-1"            # 命令幂等键的一部分；多机器人并行时必须各自唯一
STRATEGY_VERSION = "3.1.4-manual-gate"
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

# ===== 对冲（默认 Binance BTCUSDC 永续；Deribit BTC-PERPETUAL 仅兼容）=====
HEDGE_REDUCTION_RATIO = 0.5        # 目标覆盖剩余短腿 delta 的比例；压尾部而非全 delta-neutral
HEDGE_CONTRACT_SIZE_FALLBACK = 10.0   # Deribit BTC-PERPETUAL 合约面值回退(USD)
HEDGE_MIN_TRADE_FALLBACK = 10.0       # Deribit 最小下单回退(USD/合约)
HEDGE_OPEN_EXECUTION_STYLE = "PROMPT_LIMIT"
HEDGE_MAX_SLIPPAGE_BPS = 5
HEDGE_VENUE = "BINANCE"            # BINANCE | DERIBIT
HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"   # 交易员配置仍写 BTCUSDC；FMZ 内部会切 BTC_USDC + swap
HEDGE_BINANCE_MIN_TRADE = 0.001        # 币安 BTCUSDC 最小下单(BTC, 线性)
HEDGE_BINANCE_PRICE_TICK = 0.1         # BTCUSDC 永续限价价格最小跳动；买入向上、卖出向下取整
HEDGE_BINANCE_EXCHANGE_INDEX = 1       # FMZ exchanges[] 下标：exchanges[0]=Deribit, [1]=Binance Futures

# ===== Binance hedge controller V313 policy (strategy v3.1.4 delivery) =====
HEDGE_POLICY_V313_ENABLED = True
HEDGE_STAGING_ENABLED = True
HEDGE_HYSTERESIS_ENABLED = True
HEDGE_COOLDOWN_ENABLED = True
HEDGE_SLIPPAGE_GUARD_ENABLED = True
HEDGE_SOFT_INITIAL_RATIO = 0.50
HEDGE_SOFT_ADD_DRIFT_STEP = 0.05
HEDGE_HARD_DRIFT = 0.35
HEDGE_HARD_CROSS_BPS = 30
HEDGE_SOFT_CROSS_BPS = 3
HEDGE_LOSS_BOUNDARY_BUFFER_SIGMA = 1.0
HEDGE_SOFT_PERSIST_SECONDS = 20
HEDGE_REDUCE_PERSIST_SECONDS = 20
HEDGE_REDUCE_PROB_BUFFER = 0.05
HEDGE_ADD_COOLDOWN_SECONDS = 30
HEDGE_REDUCE_COOLDOWN_SECONDS = 60
HEDGE_SLIP_ALERT_BPS = 8
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
    if HEDGE_VENUE not in ("DERIBIT", "BINANCE"):
        errs.append("HEDGE_VENUE must be DERIBIT or BINANCE")
    if ENTRY_MAX_ATTEMPTS < 1 or ENTRY_MAX_TICK_STEPS < 0:
        errs.append("ENTRY_MAX_ATTEMPTS>=1 and ENTRY_MAX_TICK_STEPS>=0")
    if ENTRY_PROTECTION_TAKER_AFTER_SECONDS < 1 or ENTRY_SHORT_ORDER_WAIT_SECONDS < 1:
        errs.append("ENTRY_PROTECTION_TAKER_AFTER_SECONDS and ENTRY_SHORT_ORDER_WAIT_SECONDS must be >=1")
    return errs
