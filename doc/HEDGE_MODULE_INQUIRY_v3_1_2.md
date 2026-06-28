# Hedge Module Inquiry v3.1.2

This note is for GPT-5.5 Pro / Opus 4.8 review. It asks whether the current
Binance BTCUSDC hedge execution is too blunt under repeated triggers, and what
minimal changes would improve real trading behavior without expanding the
runtime command surface or changing the strategy idea.

## Current Boundary

- FMZ runtime interaction remains confirmation-code only:
  `执行:<确认码>`, `EXECUTE:<确认码>`, or a bare confirmation code.
- `POSITION_MANAGE` is a non-interactive read screen. Hedge, risk exit, and
  recovery are governed by startup config gates, not runtime operator commands.
- v3.1.2 fixes execution plumbing only:
  - Binance prompt-limit hedge prices are rounded by `HEDGE_BINANCE_PRICE_TICK`
    (`0.1`; buy up, sell down) before FMZ `Buy`/`Sell`.
  - Binance position snapshots now expose BTC quantity and unrealized PnL to
    `POSITION_MANAGE`.
  - Quantity-read failures remain fail-closed.
- v3.1.2 does not redesign hedge trigger frequency, hedge sizing, or
  maker-first/taker-first policy.

## Case: 2026-06-28 06:04:47 BTCUSDC Hedge

Operator screenshots show a BTCUSDC perpetual hedge order:

- Time: `2026-06-28 06:04:47`
- Contract: `BTCUSDC` perpetual
- Side/type: limit sell
- Order quantity / filled quantity: `1,380.0 / 1,379.4 USDC`
- Average / limit price shown by Binance app: `60,000.0 / 59,970.0`
- Status: fully filled
- Total fee shown: `0.55200000 USDC`
- Fill details visible in the screenshot include fills at `60,000.0`, for
  example `120.0 USDC` fee `0.04800000 USDC` and `480.0 USDC` fee
  `0.19200000 USDC`.

The paired chart screenshot shows BTC around a fast down move near
`2026-06-28 06:03`, with a marked low around `59,855.16` and then a bounce.
The operator's concern is that the hedge did help if the market kept falling,
but the current behavior may be "too dumb" if it fires repeatedly: pure
taker-like urgency can create poor average entries and then repeated hedge
losses during whipsaw.

## Related Log Issue Fixed in v3.1.2

The morning logs also showed Binance precision errors such as:

- `Precision is over the maximum defined for this asset`
- Raw prompt-limit examples included unrounded prices like `60067.91895` and
  `59968.6007`.

v3.1.2 treats the direct cause as price tick precision. It rounds BTCUSDC
prompt-limit prices before order submission. This should address the `-1111`
precision error class, but it does not answer whether the hedge execution style
is optimal.

## Current Mechanism To Review

- Hedge venue default: Binance BTCUSDC perpetual.
- FMZ pair selection: `IO("currency", "BTC_USDC")`, then `SetContractType("swap")`.
- Minimum hedge size: `HEDGE_BINANCE_MIN_TRADE = 0.001 BTC`.
- Price protection: prompt-limit style order around current ticker-derived
  price; not post-only.
- Reducing existing hedge should use reduce-only semantics where the venue/API
  path supports it.
- Position reading:
  - BTC quantity is read from Binance position snapshot.
  - unrealized PnL is read when available and displayed.
  - read failures fail closed; the strategy should not assume zero hedge.
- Runtime operator commands do not include hedge overrides.

## The Core Question

Should the hedge module remain immediate prompt-limit/taker-like when a hedge
trigger fires, or should it use a small maker-first / staged / hysteresis policy
before crossing the spread?

The current design favors protection during fast downside moves. The concern is
execution wear:

- A fast drop triggers hedge sell.
- The market bounces soon after.
- Hedge is now entered at an unfavorable average price and can become a drag.
- If the trigger fires repeatedly, fees and realized hedge losses may accumulate
  while the option structure has not actually crossed a durable risk boundary.

## Candidate Approaches For Review

1. Keep current prompt-limit/taker-like behavior.
   - Pros: fastest protection; simplest; less state.
   - Cons: may overpay spread/fees during noise; higher churn in whipsaw.

2. Maker-first with short escalation timer.
   - Post a maker sell/buy at a protected price for a few seconds.
   - Escalate to taker only if price keeps moving or risk grows.
   - Needs tests for stale maker, cancel/repost, late fill, and no double hedge.

3. Staged sizing.
   - Hedge only a fraction at first trigger, then add if risk persists.
   - Needs a clear cap so partial hedges do not mask fail-closed risk exits.

4. Hysteresis / cooldown.
   - Require trigger persistence or a minimum move beyond trigger before
     adding hedge.
   - Add post-fill cooldown before reducing/re-adding.
   - Reduces churn, but may underhedge sudden continuation moves.

5. Slippage and fee budget.
   - Gate hedge execution on projected spread/fee cost relative to option risk.
   - Needs reliable depth and fee assumptions; missing data should fail closed
     or choose a conservative fallback.

## Questions For External Review

- For short-dated BTC option vertical management, what is the safest minimal
  hedge execution policy: immediate prompt-limit, maker-first escalation, or
  staged sizing?
- What trigger persistence or hysteresis rule would reduce whipsaw without
  materially delaying protection during a real crash?
- Should hedge adds and hedge reductions have different urgency rules?
- What is a practical slippage/fee budget expressed in USDC or bps for this
  small live-test size?
- Which state variables are essential to prevent duplicate hedge orders,
  late-fill overhedge, and repeated churn?
- What tests should gate any future hedge-policy change before FMZ delivery?
- Should the 06:04:47 case be judged acceptable protection, poor execution, or
  a reasonable trade-off given the chart context?

## Constraints For Proposed Changes

- Do not add runtime hedge commands.
- Do not change candidate selection or the manual confirmation gate.
- Do not treat missing Binance depth/position/PnL data as zero.
- Keep fail-closed behavior for ambiguous position reads.
- Prefer changes that can be covered with deterministic local tests before any
  FMZ trial.
