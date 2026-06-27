# -*- coding: utf-8 -*-
"""FMZ startup config for the manual-gate execution bundle.

Trader edits should normally stay in the first two blocks: live identity/risk
and the current manual directional view. Runtime safety gates remain explicit.
"""

# ===== Instance / version =====
ROBOT_ID = "spm-exec-1"
STRATEGY_VERSION = "3.0.13-manual-gate"
RUN_PROFILE = "LIVE"              # TEST=force dry-run gates off; LIVE=use ALLOW_* gates

# ===== VRP_CONTEXT data source; validity-only, not a price gate =====
GEX_CONTEXT_API_BASE = "http://13.231.16.198:8000"
GEX_CONTEXT_API_KEY = "7WkM4LBAha7di0KMCtgty3NwdQcNXI5-j3o8MymkGiE"
GEX_CONTEXT_TIMEOUT_SECONDS = 5

# ===== Core trader inputs =====
SETTLEMENT_CURRENCY = "BTC"
MANUAL_PLANNING_ALLOWED = True
DIRECTION_BIAS = "SHORT_PUT"      # SHORT_CALL | SHORT_PUT
ORDER_AMOUNT = 0.1
SHORT_DELTA_RANGE = (0.15, 0.45)
PROTECTION_WIDTH_RANGE = (2000, 2500)
RISK_EXIT_MAX_SPEND = 0.001

# ===== Expiry and ranking defaults =====
TARGET_DTE_HOURS = 24
MENU_SIZE = 10
PLAN_WEIGHTS = {"win_rate": 0.35, "rr": 0.25, "efficiency": 0.40, "manual": 0.0}
UNDERLYING_REF_PRICE = None

# ===== Candidate quality / execution guards =====
MIN_MARGIN_RELIEF_RATIO = 0.0      # soft display floor only; portfolio budget stays hard
THIN_SHORT_PREMIUM_WARN = 0.0005
DEEP_OTM_MAX_DELTA = 0.05
MAX_SPREAD_RATIO = 0.60
PROTECTION_LOW_PREMIUM_MAX = 0.0006
PROTECTION_ABS_SPREAD_MAX = 0.00015

# ===== Entry execution =====
MAX_CHASE_STEPS = 1
CHASE_WAIT_SECONDS = 8
ENTRY_MIN_NET_CREDIT = 0.0
ENTRY_MAX_TICK_STEPS = 3
ENTRY_MAX_ATTEMPTS = 20

# ===== Runtime authorization gates =====
ALLOW_ENTRY_TRADING = True
ALLOW_EXIT_TRADING = True
ALLOW_HEDGE_TRADING = True
KILL_NEW_RISK = False
EMERGENCY_REDUCE_ONLY = False
DRY_RUN_PASSED = True

# ===== Runtime cadence =====
LOOP_INTERVAL_MS = 3000
PLAN_REFRESH_SECONDS = 45
APPROVAL_TTL_MS = 30 * 60 * 1000

# ===== Portfolio projection limits =====
PORTFOLIO_LIMITS = {
    "max_open_positions": 1,
    "max_short_gamma": 0.05,
    "max_short_vega": 0.50,
    "max_margin": 0.50,
    "max_spread_loss_per_trade": 0.02,
}

# ===== Exit activity =====
EXIT_QUOTE_REFRESH_MS = 3000
EXIT_ORDER_REST_MS = 4000
EXIT_REPRICE_COOLDOWN_MS = 6000
EXIT_MAX_ACTIVE_ORDERS = 1
EXIT_MAX_PRICE_STEPS_PER_LOOP = 1
EXIT_RESERVE_RATIO = 0.15

# ===== Hedge defaults; Binance is the main flow, Deribit is compatibility =====
HEDGE_REDUCTION_RATIO = 0.5
HEDGE_CONTRACT_SIZE_FALLBACK = 10.0
HEDGE_MIN_TRADE_FALLBACK = 10.0
HEDGE_OPEN_EXECUTION_STYLE = "PROMPT_LIMIT"
HEDGE_MAX_SLIPPAGE_BPS = 5
HEDGE_VENUE = "BINANCE"            # BINANCE | DERIBIT
HEDGE_BINANCE_INSTRUMENT = "BTCUSDC"
HEDGE_BINANCE_MIN_TRADE = 0.001
HEDGE_BINANCE_EXCHANGE_INDEX = 1


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
    return errs
