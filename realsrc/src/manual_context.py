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
