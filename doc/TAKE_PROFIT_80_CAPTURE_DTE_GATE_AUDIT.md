# TAKE_PROFIT_80_CAPTURE_DTE_GATE_AUDIT

## Core Judgment

The 80% capture take-profit rule is still correct for ordinary position
management, but short-dated 24h / 48h positions should not actively ordinary-TP
inside the final delivery window.

Implemented rule:

```text
ordinary_take_profit = capture >= 80% AND remaining_dte_hours > 3h
```

If capture is already at or above 80% and remaining DTE is `<= 3h`, the robot
does not initiate ordinary take-profit. The intent is to prefer settlement
when the position is already deeply captured and close to delivery.

## Non-Negotiable Boundary

This gate only limits ordinary take-profit.

It must not limit:

- risk exit,
- hedge open/increase/reduce/unwind,
- orphan hedge cleanup,
- settlement handling,
- recovery handling.

So the final 3 hours behave like this:

- 80% captured and no risk deterioration: hold toward delivery.
- risk boundary worsens or hedge trigger fires: risk exit / hedge can still
  execute by the existing gates.

## First-Version Parameter

```python
TAKE_PROFIT_MIN_DTE_HOURS = 3.0
```

This fixed first version is intentionally simple. A future dynamic rule could
use 2h / 3h / 4h by volatility, gamma, and distance to breakeven, but that is
not part of this delivery.

## Implementation Notes

- `_evaluate_take_profit` still calculates the capture ratio first.
- `capture_qualified` records whether the 80% rule itself is met.
- `qualified` is the actionable ordinary-TP flag after the DTE gate.
- `dte_gate_active` and `dte_gate_reason` explain why ordinary TP is paused.
- `manage_cycle` still uses `exit_preferred` / `hedge_ready` independently, so
  risk exit and hedge fallback can override this ordinary-TP pause.

## Test Coverage

- Final 2h with capture above 80% and normal risk does not buy back the short
  leg.
- Final 2h with capture above 80% and deteriorated risk can still fall back to
  Binance hedge when risk exit is not executable.
